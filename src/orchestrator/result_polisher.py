"""LLM 润色器：仅调用一次，将结构化结果转换为自然语言。

性能目标: <500ms
LLM 调用: 仅 1 次
"""

from __future__ import annotations

import time
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from config.settings import settings
from orchestrator.parallel_executor import ToolResult
from orchestrator.fast_planner import ExecutionPlan


POLISH_SYSTEM_PROMPT = """你是一个结果润色专家。你的任务是将结构化的工具执行结果转换为自然、流畅的回答。

**核心原则**：
1. 直接回答用户问题，不要描述"执行了什么"
2. 提取关键信息，忽略技术细节
3. 使用 Markdown 格式美化输出
4. 简洁明了，避免冗余

**输入格式**：
- 用户问题
- 工具执行结果（结构化数据）

**输出要求**：
- 自然语言回答
- 突出核心信息
- 适当格式化（代码块、列表等）
- 不要说"根据工具返回..."之类的话

**示例**：

输入：
```
用户: 搜索量子计算最新进展
工具结果: {"results": [
  {"title": "Google Willow 芯片突破", "snippet": "..."},
  {"title": "IBM 量子云服务", "snippet": "..."}
]}
```

❌ 差的回答：
"根据搜索工具返回的结果，找到了2条信息..."

✅ 好的回答：
"量子计算最新进展：

1. **Google Willow 芯片**：实现了量子纠错突破...
2. **IBM 量子云服务**：推出商业化平台..."

---

现在请润色以下结果：
"""


class ResultPolisher:
    """结果润色器（仅调用 1 次 LLM）"""
    
    def __init__(self):
        self.llm = None
        
        # 延迟初始化 LLM（仅在需要时）
        if settings.openrouter_api_key:
            try:
                self.llm = ChatOpenAI(
                    model="anthropic/claude-3.5-sonnet",
                    api_key=settings.openrouter_api_key,
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0.7,  # 稍高温度，增加自然度
                    max_tokens=2048,
                    request_timeout=10,  # 10秒超时
                    default_headers={
                        "HTTP-Referer": "https://maxai.cc",
                        "X-Title": "Max AI Agent"
                    }
                )
            except Exception as e:
                print(f"⚠️ LLM 初始化失败: {e}")
                self.llm = None
    
    def polish(
        self, 
        user_query: str, 
        plan: ExecutionPlan,
        results: Dict[str, ToolResult],
        history_messages: list = None
    ) -> str:
        """
        润色结果（单次 LLM 调用，<500ms）
        
        Args:
            user_query: 用户问题
            plan: 执行计划
            results: 工具执行结果
        
        Returns:
            自然语言回答
        """
        start_time = time.time()
        
        # 1. 构建结构化上下文
        context = self._build_context(user_query, plan, results)
        
        # 2. 单次 LLM 调用
        if not self.llm:
            print("⚠️ LLM 未配置，使用降级格式化")
            return self._fallback_format(user_query, results)
        
        try:
            # 构建消息列表，包含历史上下文
            llm_messages = [SystemMessage(content=POLISH_SYSTEM_PROMPT)]
            
            # 添加历史消息（最近5轮，避免过长）
            if history_messages:
                # 只取最近的历史消息
                recent_history = history_messages[-10:]  # 最多10条历史消息
                for msg in recent_history:
                    if hasattr(msg, 'type'):
                        if msg.type == 'human':
                            llm_messages.append(HumanMessage(content=msg.content))
                        elif msg.type == 'ai':
                            llm_messages.append(AIMessage(content=msg.content))
                    elif hasattr(msg, 'content'):
                        # 兼容不同的消息格式
                        if isinstance(msg, HumanMessage):
                            llm_messages.append(msg)
                        elif isinstance(msg, AIMessage):
                            llm_messages.append(msg)
            
            # 添加当前查询和工具结果
            llm_messages.append(HumanMessage(content=context))
            
            response = self.llm.invoke(llm_messages)
            answer = response.content
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            print(f"✨ 结果润色完成: {elapsed_ms}ms")
            
            return answer
        
        except Exception as e:
            print(f"⚠️ 润色失败: {e}")
            # 降级：返回原始结果
            return self._fallback_format(user_query, results)
    
    def _build_context(
        self, 
        user_query: str, 
        plan: ExecutionPlan,
        results: Dict[str, ToolResult]
    ) -> str:
        """
        构建结构化上下文
        """
        lines = [
            f"**用户问题**: {user_query}",
            "",
            "**工具执行结果**:",
        ]
        
        # 按任务顺序展示结果
        for task in plan.tasks:
            result = results.get(task.id)
            if not result:
                continue
            
            lines.append(f"\n{task.id} ({task.tool}):")
            
            if result.success:
                output = str(result.output)
                # 截断过长的输出
                if len(output) > 1000:
                    output = output[:1000] + "...(已截断)"
                lines.append(f"```\n{output}\n```")
            else:
                lines.append(f"❌ 错误: {result.error}")
        
        return "\n".join(lines)
    
    def _fallback_format(
        self, 
        user_query: str, 
        results: Dict[str, ToolResult]
    ) -> str:
        """
        降级格式化（无 LLM，确保有用的输出）
        """
        success_results = [r for r in results.values() if r.success]
        
        if not success_results:
            return f"❌ 任务执行失败\n\n问题: {user_query}\n\n请检查工具配置或重试。"
        
        # 智能格式化：直接返回有用的结果
        if len(success_results) == 1:
            result = success_results[0]
            output = str(result.output)
            
            # 简单结果直接返回
            if len(output) < 500 and '\n' not in output[:100]:
                return output
            
            # 复杂结果带格式
            return f"**{result.tool} 执行结果**:\n\n{output}"
        
        # 多个结果
        lines = [f"**问题**: {user_query}\n"]
        for i, result in enumerate(success_results, 1):
            lines.append(f"**步骤 {i} ({result.tool})**:")
            output = str(result.output)
            if len(output) > 500:
                output = output[:500] + "...(已截断)"
            lines.append(f"{output}\n")
        
        return "\n".join(lines)


# 全局单例 - 使用延迟初始化避免启动时阻塞
_result_polisher_instance = None

def get_result_polisher():
    """获取 ResultPolisher 单例"""
    global _result_polisher_instance
    if _result_polisher_instance is None:
        _result_polisher_instance = ResultPolisher()
    return _result_polisher_instance

# 为了向后兼容，保留 result_polisher 属性
class _ResultPolisherProxy:
    def __getattr__(self, name):
        return getattr(get_result_polisher(), name)

result_polisher = _ResultPolisherProxy()
