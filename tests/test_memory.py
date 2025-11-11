"""测试记忆系统。"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from memory.rag_pipeline import (
    retrieve_context,
    augment_query_with_context,
)


def test_retrieve_context_no_weaviate():
    """测试无 Weaviate 连接时的降级处理。"""
    # 如果 Weaviate 未配置，应返回错误消息而不是崩溃
    result = retrieve_context("test query")
    
    assert isinstance(result, str)
    # 应包含错误或空结果提示
    assert "无" in result or "失败" in result or "记忆" in result


def test_augment_query():
    """测试查询增强。"""
    query = "什么是量子计算？"
    augmented = augment_query_with_context(query, top_k=2)
    
    # 应包含原始查询
    assert query in augmented
    # 应包含上下文提示
    assert "记忆" in augmented or "查询" in augmented


@pytest.mark.skip(reason="需要 Weaviate 连接")
def test_save_conversation():
    """测试对话保存（需要 Weaviate）。"""
    from memory.rag_pipeline import save_conversation
    
    save_conversation(
        user_query="测试查询",
        agent_response="测试响应",
        metadata={"test": True},
    )
    
    # 验证可以检索
    result = retrieve_context("测试查询", top_k=1)
    assert "测试" in result
