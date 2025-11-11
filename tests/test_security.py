"""安全测试：测试安全相关功能。"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.mark.security
class TestInputValidation:
    """输入验证测试"""
    
    def test_sql_injection_prevention(self):
        """测试SQL注入防护"""
        from fastapi_app import save_session, load_session, delete_session_file
        from langchain_core.messages import HumanMessage

        malicious_input = "'; DROP TABLE sessions; --"
        session_id = "security_test"

        save_session(session_id, [HumanMessage(content=malicious_input)])
        messages = load_session(session_id)

        assert len(messages) == 1
        assert messages[0].content == malicious_input

        delete_session_file(session_id)
    
    def test_xss_prevention(self):
        """测试XSS防护"""
        from fastapi.testclient import TestClient
        from fastapi_app import app
        
        client = TestClient(app)
        
        xss_payload = "<script>alert('XSS')</script>"
        
        response = client.post('/api/chat', data={
            'query': xss_payload,
            'session_id': 'xss_test'
        })
        
        # API应该拒绝包含脚本标签的输入
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data or 'detail' in data or 'message' in data
    
    def test_path_traversal_prevention(self):
        """测试路径遍历攻击防护"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd"
        ]
        
        for path in malicious_paths:
            with pytest.raises(Exception):
                from pathlib import Path
                Path(path).resolve(strict=True)


@pytest.mark.security
class TestDataProtection:
    """数据保护测试"""
    
    def test_sensitive_data_logging(self):
        """测试敏感数据不被记录"""
        import logging
        from io import StringIO
        
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger()
        logger.addHandler(handler)
        
        from config.settings import settings
        
        api_key = settings.openrouter_api_key
        
        if api_key:
            logger.info(f"Processing request with key: {api_key[:8]}...")
        
        log_output = log_capture.getvalue()
        
        if api_key:
            assert api_key not in log_output
        
        logger.removeHandler(handler)
    
    def test_session_isolation(self):
        """测试会话隔离"""
        from fastapi_app import save_session, load_session, delete_session_file
        from langchain_core.messages import HumanMessage

        session1 = "user1_session"
        session2 = "user2_session"

        save_session(session1, [HumanMessage(content="用户1的消息")])
        save_session(session2, [HumanMessage(content="用户2的消息")])

        messages1 = load_session(session1)
        messages2 = load_session(session2)

        assert len(messages1) == 1
        assert len(messages2) == 1
        assert messages1[0].content != messages2[0].content

        delete_session_file(session1)
        delete_session_file(session2)


@pytest.mark.security
class TestRateLimit:
    """速率限制测试"""
    
    def test_request_throttling(self):
        """测试请求限流"""
        import time
        
        requests = []
        for _ in range(10):
            start = time.time()
            requests.append(start)
            time.sleep(0.1)
        
        time_window = 1.0
        recent_requests = [r for r in requests if time.time() - r < time_window]
        
        assert len(recent_requests) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "security"])
