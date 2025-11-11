"""
Executor 节点：根据 planner 的 next_action 调用工具。
经过重构，使用 LLM 动态提取参数，而不是依赖脆弱的硬编码规则。
"""
from __future__ import annotations

import json
import inspect
from typing import Any, Dict

from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI

from agent.state import AgentState
from tools.registry import registry
from config.settings import settings

# 延迟初始化 LLM 避免启动时阻塞
_param_llm = None

def get_param_llm():
    """获取用于参数提取的 LLM 实例（延迟初始化）"""
    global _param_llm
    if _param_llm is None:
        _param_llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            default_headers={"HTTP-Referer": "https://maxai.cc", "X-Title": "Max AI"},
        )
    return _param_llm

def get_tool_arguments(tool_func: callable, user_query: str, plan: list[str], state: AgentState) -> Dict[str, Any]:
    """
    使用 LLM 智能提取工具所需的参数。

    Args:
        tool_func: 目标工具的函数对象。
        user_query: 用户的原始查询。
        plan: Planner 生成的执行计划。
        state: 当前 Agent 状态，用于提供更丰富的上下文。

    Returns:
        一个包含工具所需参数的字典。
    """
    # 1. 将函数转换为 OpenAI 工具格式，以便 LLM 理解其结构
    # LangChain 的 convert_to_openai_tool 在处理某些函数签名时存在问题
    # 我们手动构建一个更可靠的 schema
    sig = inspect.signature(tool_func)
    description = tool_func.__doc__ or f"执行 {tool_func.__name__}."
    
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    
    for param in sig.parameters.values():
        if param.name in ("state", "kwargs"):  # 忽略特殊参数
            continue
        
        param_info = {"type": "string"} # 默认为 string
        if param.annotation != inspect.Parameter.empty:
            if param.annotation == int:
                param_info["type"] = "integer"
            elif param.annotation == bool:
                param_info["type"] = "boolean"
            elif param.annotation == list:
                param_info["type"] = "array"
                param_info["items"] = {"type": "string"}

        parameters["properties"][param.name] = param_info
        
        if param.default == inspect.Parameter.empty:
            parameters["required"].append(param.name)

    tool_schema = {
        "name": tool_func.__name__,
        "description": description,
        "parameters": parameters,
    }

    # 2. 构建一个专门用于参数提取的 LLM chain
    structured_llm = get_param_llm().with_structured_output(tool_schema)

    # 3. 构建 Prompt
    # 提取最近的几条消息作为上下文
    recent_messages = "\n".join([f"{msg.type}: {msg.content}" for msg in state.get("messages", [])[-5:]])

    prompt = f"""
    你是一个智能的参数提取助手。你的任务是根据用户请求、执行计划和最近的对话历史，为给定的工具提取正确的参数。

    **最近对话历史:**
    {recent_messages}

    **当前执行计划:**
    {chr(10).join(f'- {step}' for step in plan)}

    **特别注意**:
    - 如果用户上传了文件（例如 `[用户上传了文件: 'data/uploads/report.txt']`），你需要从这个路径中提取出 `file_path` 参数。
    - `file_path` 应该是相对于项目根目录的路径，例如 `'data/uploads/report.txt'`。

    请根据以上所有信息，为名为 `{tool_func.__name__}` 的工具提取参数。
    确保所有必需的参数都被填充，并符合指定的类型。
    """

    # 4. 调用 LLM 并获取结构化输出
    try:
        print(f"🤖 正在为工具 '{tool_func.__name__}' 提取参数...")
        # LangChain 的 with_structured_output 会自动处理 prompt 和 schema 的结合
        response = structured_llm.invoke(prompt)
        print(f"✅ 成功提取参数: {response}")
        return response
    except Exception as e:
        print(f"⚠️ LLM 参数提取失败: {e}")
        # 降级处理：返回一个空字典，让工具使用默认值或报告错误
        return {}


def executor_node(state: AgentState) -> dict[str, Any]:
    """
    执行 next_action 中指定的工具，并使用 LLM 动态解析参数。

    Args:
        state: 包含 next_action 和 plan 的当前状态。

    Returns:
        更新后的状态，包含 last_tool_output。
    """
    action = state.get("next_action", "none")
    user_query = state["messages"][-1].content if state["messages"] else ""
    plan = state.get("plan", [])

    if action == "none" or not action:
        return {
            "last_tool_output": "无需执行工具",
            "last_action": "none",
            "last_action_input": None,
        }

    # 1. 从注册表中获取工具函数
    tool_func = registry.get(action)

    if not tool_func:
        available = ", ".join(registry.list_available())
        error_message = f"错误：工具 '{action}' 未找到。可用工具: {available}"
        return {
            "last_tool_output": error_message,
            "last_action": action,
            "last_action_input": None,
        }

    try:
        # 2. 使用 LLM 智能提取参数，并传入完整的 state
        tool_args = get_tool_arguments(tool_func, user_query, plan, state)

        # 3. 执行工具
        print(f"🚀 正在执行工具: {action}，参数: {tool_args}")
        output = tool_func(**tool_args)

        return {
            "last_tool_output": str(output),
            "last_action": action,
            "last_action_input": tool_args,
            # 如果工具是代码执行器，也传递生成的代码
            "generated_code": tool_args.get("code", "") if action == "code_execution" else ""
        }

    except Exception as e:
        # 捕获工具执行期间的任何异常
        error_message = f"执行工具 '{action}' 时出错: {e}"
        print(f"❌ {error_message}")
        import traceback
        traceback.print_exc()
        return {
            "last_tool_output": error_message,
            "last_action": action,
            "last_action_input": tool_args if 'tool_args' in locals() else "参数提取失败",
        }
