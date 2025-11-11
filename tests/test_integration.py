"""集成测试：测试端到端工作流。"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.mark.integration
class TestEndToEnd:
    """端到端集成测试"""
    
    def test_simple_query_workflow(self):
        """测试简单查询工作流"""
        from orchestrator.graph import create_graph
        from agent.state import init_state
        
        query = "2 + 2 等于多少?"
        state = init_state(query)
        graph = create_graph()
        
        final_state = None
        for event in graph.stream(state):
            for node_name, node_output in event.items():
                final_state = node_output
        
        assert final_state is not None
        assert final_state.get("is_complete") or final_state.get("critic_status") == "done"
    
    def test_context_aware_conversation(self):
        """测试上下文感知对话"""
        from orchestrator.graph import create_graph
        from agent.state import init_state
        from langchain_core.messages import HumanMessage, AIMessage
        
        query1 = "Python是什么?"
        state = init_state(query1)
        graph = create_graph()
        
        state1 = None
        for event in graph.stream(state):
            for _, node_output in event.items():
                state1 = node_output
        
        messages = state1.get("messages", [])
        messages.append(HumanMessage(content="它有哪些特点?"))
        
        state2 = {
            "messages": messages,
            "plan": None,
            "next_action": None,
            "is_complete": False
        }
        
        final_state = None
        for event in graph.stream(state2):
            for _, node_output in event.items():
                final_state = node_output
        
        assert final_state is not None


@pytest.mark.integration
class TestWebApp:
    """Web应用集成测试"""
    
    def test_status_endpoint(self):
        """测试状态端点"""
        from fastapi.testclient import TestClient
        from fastapi_app import app
        
        client = TestClient(app)
        response = client.get('/api/status')
        
        assert response.status_code == 200
        data = response.json()
        assert 'llm' in data
        assert 'tools' in data
    
    def test_session_history(self):
        """测试会话历史"""
        from fastapi.testclient import TestClient
        from fastapi_app import app, save_session, delete_session_file
        from datetime import datetime
        from langchain_core.messages import HumanMessage
        
        client = TestClient(app)
        
        session_id = "test_history_session"
        save_session(session_id, [HumanMessage(content="测试消息")])
        
        try:
            response = client.get(f'/api/session_history?session_id={session_id}')
            
            assert response.status_code == 200
            data = response.json()
            assert 'messages' in data
        finally:
            delete_session_file(session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
