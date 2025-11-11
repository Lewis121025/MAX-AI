"""RAG 管道：检索增强生成。"""

from __future__ import annotations

from typing import Any

from memory.weaviate_client import get_weaviate_client


def retrieve_context(query: str, top_k: int = 3) -> str:
    """从 Weaviate 检索相关上下文。
    
    参数：
        query: 用户查询
        top_k: 返回的文档数量
    
    返回:
        格式化的上下文字符串
    """
    try:
        client = get_weaviate_client()
        results = client.search_similar(query, limit=top_k)
        
        if not results:
            return "（无相关历史记忆）"
        
        context_parts = ["**相关历史记忆**:"]
        for i, result in enumerate(results, 1):
            content = result["content"][:200]  # 限制长度
            source = result["source"]
            context_parts.append(f"{i}. [{source}] {content}...")
        
        return "\n".join(context_parts)
    
    except Exception as e:
        return f"（记忆检索失败: {e}）"


def save_conversation(user_query: str, agent_response: str, metadata: dict | None = None):
    """保存对话到 Weaviate。
    
    参数：
        user_query: 用户查询
        agent_response: Agent 响应
        metadata: 额外元数据
    """
    try:
        client = get_weaviate_client()
        
        # 保存用户查询
        client.add_memory(
            content=f"用户: {user_query}",
            source="conversation",
            metadata={"type": "user_query", **(metadata or {})},
        )
        
        # 保存 Agent 响应
        client.add_memory(
            content=f"Agent: {agent_response}",
            source="conversation",
            metadata={"type": "agent_response", **(metadata or {})},
        )
    
    except Exception as e:
        print(f"⚠️ 对话保存失败: {e}")


def ingest_document(content: str, source: str, metadata: dict | None = None) -> bool:
    """摄入文档到向量数据库（分块）。
    
    参数：
        content: 文档内容
        source: 来源标识
        metadata: 元数据
    
    返回：
        是否成功
    """
    try:
        # 简单分块策略（每 500 字符）
        chunk_size = 500
        chunks = [
            content[i:i+chunk_size]
            for i in range(0, len(content), chunk_size)
        ]
        
        client = get_weaviate_client()
        
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "source": source,
                "chunk_id": i,
                "total_chunks": len(chunks),
                **(metadata or {}),
            }
            
            client.add_memory(
                content=chunk,
                source="document",
                metadata=chunk_metadata,
            )
        
        print(f"✅ 文档摄入成功: {len(chunks)} 个分块")
        return True
    
    except Exception as e:
        print(f"❌ 文档摄入失败: {e}")
        return False


def augment_query_with_context(query: str, top_k: int = 3) -> str:
    """为查询增强上下文（RAG 核心）。
    
    参数：
        query: 原始查询
        top_k: 检索文档数量
    
    返回：
        增强后的查询字符串
    """
    context = retrieve_context(query, top_k)
    
    augmented = f"""
{context}

**当前查询**: {query}

请结合上述历史记忆回答问题。如果记忆不相关，请忽略。
""".strip()
    
    return augmented
