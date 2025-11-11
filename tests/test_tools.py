"""测试工具注册表。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.registry import registry


def test_registry_has_tools():
    """验证工具已注册。"""
    available = registry.list_available()
    assert len(available) > 0, "注册表应有工具"
    
    expected_tools = ["intelligent_search", "code_execution", "file_scraper"]
    for tool in expected_tools:
        assert tool in available, f"工具 {tool} 应已注册"


def test_get_tool():
    """测试获取工具。"""
    tool = registry.get("intelligent_search")
    assert tool is not None, "应能获取已注册的工具"
    
    invalid = registry.get("nonexistent")
    assert invalid is None, "不存在的工具应返回 None"


def test_get_descriptions():
    """测试获取工具描述。"""
    descriptions = registry.get_descriptions()
    assert len(descriptions) > 0, "应有工具描述"
    
    # 验证格式
    first_desc = descriptions[0]
    assert "name" in first_desc
    assert "description" in first_desc
    assert "requires_auth" in first_desc


def test_tool_execution():
    """测试工具执行（模拟）。"""
    # 注意：真实测试需要 API keys，这里只测试错误处理
    tool = registry.get("intelligent_search")
    
    result = tool("test query")
    
    # 应返回字符串（成功或错误消息）
    assert isinstance(result, str)
