"""定义在整个图中流转的 Agent 工作状态。"""

from __future__ import annotations

from typing import Annotated, Any, List, Literal, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """在 planner → executor → critic 节点之间流转的状态。
    
    字段说明：
        messages: 对话历史（使用 LangGraph 的消息合并器）
        plan: 规划器生成的任务步骤列表
        next_action: 下一个要调用的工具名（如 "intelligent_search"）
        last_tool_output: 最近一次工具执行的结果
        generated_code: 生成的代码（仅用于code_execution）
        reflection: 评估器给规划器的反馈/建议
        is_complete: 任务是否已完成
        critic_status: 评估器的决策（continue/retry/done）
        loop_counter: 循环计数器，防止死循环
        iterations: 循环计数器别名，与loop_counter等价
        plan_reasoning: 规划器生成计划的底层推理
        plan_complexity: 任务复杂度级别
        plan_estimated_time: 估算执行时间
        last_action: 最近一次工具名称
        last_action_input: 最近一次工具输入摘要
        critic_quality_score: 评估器主观评分
        critic_improvements: 评估器给出的改进建议
        critic_reasoning: 评估器的详细推理
    """
    
    messages: Annotated[List[BaseMessage], add_messages]
    plan: Optional[List[str]]
    next_action: Optional[str]
    last_tool_output: Optional[Any]
    generated_code: Optional[str]  # 新增：保存生成的代码
    reflection: Optional[str]
    is_complete: bool
    critic_status: Optional[Literal["continue", "retry", "done"]]
    loop_counter: int  # 主要字段
    iterations: int  # 别名，兼容旧代码
    plan_reasoning: Optional[str]
    plan_complexity: Optional[str]
    plan_estimated_time: Optional[str]
    last_action: Optional[str]
    last_action_input: Optional[str]
    critic_quality_score: Optional[int]
    critic_improvements: Optional[List[str]]
    critic_reasoning: Optional[str]


def init_state(user_input: str, image_path: Optional[str] = None) -> AgentState:
    """用用户请求初始化 agent 状态。
    
    参数：
        user_input: 用户的任务描述
        image_path: 可选的图片路径（用于多模态输入）
    
    返回：
        准备好的 AgentState，可直接用于 graph.invoke()
    """
    from langchain_core.messages import HumanMessage
    
    content: List[dict] | str = user_input
    
    # 多模态支持：如果提供了图片，添加到消息中
    if image_path:
        from pathlib import Path
        import base64
        
        image_data = base64.b64encode(Path(image_path).read_bytes()).decode()
        content = [
            {"type": "text", "text": user_input},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
        ]
    
    return {
        "messages": [HumanMessage(content=content)],
        "plan": None,
        "next_action": None,
        "last_tool_output": None,
        "reflection": None,
        "is_complete": False,
        "critic_status": None,
        "loop_counter": 0,
        "iterations": 0,
    }
