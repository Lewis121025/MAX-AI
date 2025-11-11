"""快速演示脚本：端到端测试图。"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.state import init_state
from orchestrator.graph import create_graph


def main():
    print("🚀 Max AI Agent 演示\n")
    
    graph = create_graph()
    
    # 测试用例
    user_request = "查找 2024 年量子计算的突破性进展"
    
    print(f"📝 用户请求: {user_request}\n")
    print("=" * 60)
    
    initial_state = init_state(user_request)
    
    # 流式执行
    for event in graph.stream(initial_state):
        for node_name, node_output in event.items():
            print(f"\n🔹 节点: {node_name}")
            if "plan" in node_output and node_output["plan"]:
                print(f"   📋 计划: {node_output['plan']}")
            if "next_action" in node_output:
                print(f"   ⚡ 下一步动作: {node_output['next_action']}")
            if "last_tool_output" in node_output:
                print(f"   🔧 工具输出: {node_output['last_tool_output']}")
            if "reflection" in node_output:
                print(f"   💭 反思: {node_output['reflection']}")
            if "is_complete" in node_output:
                print(f"   ✅ 是否完成: {node_output['is_complete']}")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")


if __name__ == "__main__":
    main()
