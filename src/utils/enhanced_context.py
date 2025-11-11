"""增强的上下文管理器：支持多轮对话和历史结果传递。

功能：
1. 会话历史管理
2. 工具执行结果缓存
3. 上下文压缩和摘要
4. 相关历史提取
"""

from __future__ import annotations

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


@dataclass
class ToolExecution:
    """工具执行记录"""
    tool_name: str
    params: Dict[str, Any]
    result: Any
    success: bool
    timestamp: datetime
    elapsed_ms: int


@dataclass
class ConversationTurn:
    """对话轮次"""
    query: str
    response: str
    tool_executions: List[ToolExecution]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedContextManager:
    """增强的上下文管理器"""
    
    def __init__(self, max_turns: int = 10, max_tool_results: int = 20):
        """初始化上下文管理器。
        
        Args:
            max_turns: 保留的最大对话轮次
            max_tool_results: 保留的最大工具执行结果
        """
        self.max_turns = max_turns
        self.max_tool_results = max_tool_results
        
        # 对话历史
        self.turns: deque[ConversationTurn] = deque(maxlen=max_turns)
        
        # 工具执行缓存（最近的结果，供后续查询使用）
        self.tool_cache: deque[ToolExecution] = deque(maxlen=max_tool_results)
        
        # 当前会话元数据
        self.session_metadata: Dict[str, Any] = {}
    
    def add_turn(
        self,
        query: str,
        response: str,
        tool_executions: List[ToolExecution] = None,
        metadata: Dict[str, Any] = None
    ):
        """添加一轮对话。
        
        Args:
            query: 用户查询
            response: AI 响应
            tool_executions: 本轮使用的工具
            metadata: 额外的元数据
        """
        tool_executions = tool_executions or []
        metadata = metadata or {}
        
        turn = ConversationTurn(
            query=query,
            response=response,
            tool_executions=tool_executions,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        self.turns.append(turn)
        
        # 更新工具缓存
        for execution in tool_executions:
            self.tool_cache.append(execution)
    
    def get_recent_turns(self, n: int = 5) -> List[ConversationTurn]:
        """获取最近的 N 轮对话。
        
        Args:
            n: 返回的轮次数量
            
        Returns:
            最近的对话轮次列表
        """
        return list(self.turns)[-n:]
    
    def get_relevant_tool_results(self, query: str, top_k: int = 3) -> List[ToolExecution]:
        """获取与当前查询相关的工具执行结果。
        
        Args:
            query: 当前查询
            top_k: 返回的最大结果数
            
        Returns:
            相关的工具执行结果
        """
        # 简单实现：返回最近的工具执行
        # TODO: 未来可以基于语义相似度进行智能匹配
        recent_executions = list(self.tool_cache)[-top_k:]
        return [exe for exe in recent_executions if exe.success]
    
    def build_context_summary(self, max_length: int = 500) -> str:
        """构建上下文摘要。
        
        Args:
            max_length: 摘要的最大字符长度
            
        Returns:
            上下文摘要字符串
        """
        if not self.turns:
            return ""
        
        summary_parts = []
        recent_turns = self.get_recent_turns(3)
        
        for i, turn in enumerate(recent_turns, 1):
            summary_parts.append(f"轮次 {i}:")
            summary_parts.append(f"  用户: {turn.query[:100]}")
            summary_parts.append(f"  AI: {turn.response[:100]}")
            
            if turn.tool_executions:
                tools_used = [exe.tool_name for exe in turn.tool_executions if exe.success]
                if tools_used:
                    summary_parts.append(f"  工具: {', '.join(tools_used)}")
        
        summary = "\n".join(summary_parts)
        
        # 截断到最大长度
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    
    def extract_context_for_planning(self) -> Dict[str, Any]:
        """为规划器提取相关上下文。
        
        Returns:
            包含历史信息的上下文字典
        """
        context = {
            "has_history": len(self.turns) > 0,
            "recent_turns": [],
            "recent_tool_results": [],
            "session_metadata": self.session_metadata.copy()
        }
        
        # 添加最近的对话
        for turn in self.get_recent_turns(3):
            context["recent_turns"].append({
                "query": turn.query,
                "response": turn.response[:200],  # 截断响应
                "tools_used": [exe.tool_name for exe in turn.tool_executions]
            })
        
        # 添加最近的工具结果
        for execution in list(self.tool_cache)[-5:]:
            if execution.success:
                context["recent_tool_results"].append({
                    "tool": execution.tool_name,
                    "params": execution.params,
                    "result_preview": str(execution.result)[:200],
                    "timestamp": execution.timestamp.isoformat()
                })
        
        return context
    
    def should_reference_history(self, query: str) -> bool:
        """判断查询是否需要引用历史。
        
        Args:
            query: 用户查询
            
        Returns:
            是否需要引用历史
        """
        # 检测继续/修改/补充类关键词
        continuation_keywords = [
            "继续", "接着", "然后", "再", "还有",
            "上面", "之前", "刚才", "这个", "那个",
            "修改", "改", "补充", "添加", "更新",
            "详细", "展开", "具体", "进一步"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in continuation_keywords)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。
        
        Returns:
            可序列化的字典
        """
        return {
            "turns": [
                {
                    "query": turn.query,
                    "response": turn.response,
                    "tool_executions": [
                        {
                            "tool_name": exe.tool_name,
                            "params": exe.params,
                            "result": str(exe.result)[:500],  # 截断结果
                            "success": exe.success,
                            "timestamp": exe.timestamp.isoformat(),
                            "elapsed_ms": exe.elapsed_ms
                        }
                        for exe in turn.tool_executions
                    ],
                    "timestamp": turn.timestamp.isoformat(),
                    "metadata": turn.metadata
                }
                for turn in self.turns
            ],
            "session_metadata": self.session_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedContextManager':
        """从字典反序列化。
        
        Args:
            data: 序列化的字典
            
        Returns:
            恢复的上下文管理器
        """
        manager = cls()
        
        for turn_data in data.get("turns", []):
            tool_executions = [
                ToolExecution(
                    tool_name=exe["tool_name"],
                    params=exe["params"],
                    result=exe["result"],
                    success=exe["success"],
                    timestamp=datetime.fromisoformat(exe["timestamp"]),
                    elapsed_ms=exe["elapsed_ms"]
                )
                for exe in turn_data.get("tool_executions", [])
            ]
            
            manager.add_turn(
                query=turn_data["query"],
                response=turn_data["response"],
                tool_executions=tool_executions,
                metadata=turn_data.get("metadata", {})
            )
        
        manager.session_metadata = data.get("session_metadata", {})
        
        return manager
    
    def clear(self):
        """清空所有上下文。"""
        self.turns.clear()
        self.tool_cache.clear()
        self.session_metadata.clear()


# 全局会话管理器字典
_session_managers: Dict[str, EnhancedContextManager] = {}


def get_context_manager(session_id: str) -> EnhancedContextManager:
    """获取或创建会话的上下文管理器。
    
    Args:
        session_id: 会话 ID
        
    Returns:
        上下文管理器实例
    """
    if session_id not in _session_managers:
        _session_managers[session_id] = EnhancedContextManager()
    
    return _session_managers[session_id]


def clear_context_manager(session_id: str):
    """清除会话的上下文管理器。
    
    Args:
        session_id: 会话 ID
    """
    if session_id in _session_managers:
        _session_managers[session_id].clear()
        del _session_managers[session_id]
