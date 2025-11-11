"""测试基本的图执行流程。"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.state import init_state
from orchestrator.graph import create_graph


def test_graph_basic_invoke():
    """验证图可以处理简单请求。"""
    graph = create_graph()
    
    initial_state = init_state("搜索最新的 AI 新闻")
    
    result = graph.invoke(initial_state)
    
    assert "plan" in result
    assert isinstance(result["plan"], list)
    assert len(result["plan"]) > 0
    print(f"✅ 生成的计划: {result['plan']}")
    print(f"✅ 下一步动作: {result.get('next_action')}")
    print(f"✅ 是否完成: {result.get('is_complete')}")


if __name__ == "__main__":
    print("🧪 开始测试基本图执行...\n")
    test_graph_basic_invoke()
    print("\n✅ 测试通过！")
