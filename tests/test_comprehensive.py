"""综合测试套件：测试所有核心功能。"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestSessionStorage:
    """测试会话存储体系"""

    def test_save_and_load(self):
        """验证会话可以持久化并读取"""
        from fastapi_app import save_session, load_session, delete_session_file
        from langchain_core.messages import HumanMessage

        session_id = "test_session_store"
        messages = [HumanMessage(content="测试消息 1")]

        save_session(session_id, messages)
        loaded = load_session(session_id)

        assert len(loaded) == 1
        assert str(loaded[0].content) == "测试消息 1"

        delete_session_file(session_id)

    def test_session_listing(self):
        """验证新会话出现在列表中"""
        from fastapi_app import save_session, list_sessions, delete_session_file
        from langchain_core.messages import HumanMessage

        session_id = "test_session_listing"
        save_session(session_id, [HumanMessage(content="列表测试")])

        sessions = list_sessions()
        assert any(sess["id"] == session_id for sess in sessions)

        delete_session_file(session_id)

    def test_delete_session(self):
        """验证删除会话会移除持久化文件"""
        from fastapi_app import save_session, load_session, delete_session_file
        from pathlib import Path
        from langchain_core.messages import HumanMessage

        session_id = "test_session_delete"
        save_session(session_id, [HumanMessage(content="删除测试")])

        delete_session_file(session_id)
        assert load_session(session_id) == []
        session_path = Path("data/sessions") / f"{session_id}.json"
        assert not session_path.exists()


class TestFastPlanner:
    """测试快速规划器"""

    def test_detects_simple_query(self):
        """简单问题不应生成工具任务"""
        from orchestrator.fast_planner import fast_planner

        # 使用明确的非工具查询
        plan = fast_planner.plan("什么是人工智能?")
        assert len(plan.tasks) == 0
        assert plan.requires_llm_polish is True

    def test_generates_complex_plan(self):
        """复杂查询应生成包含文件操作的计划"""
        from orchestrator.fast_planner import fast_planner, Intent

        plan = fast_planner.plan(
            "读取 dataset.csv 并分析销量趋势",
            context={"uploaded_files": ["data/uploads/dataset.csv"]},
        )

        intents = {task.intent for task in plan.tasks}
        assert Intent.FILE_OP in intents or Intent.DATA_ANALYSIS in intents
        assert plan.parallel_batches, "应生成并行批次"


class TestParallelExecutor:
    """测试新的并行执行器"""

    def test_file_pipeline(self):
        """写入文件后读取，确保依赖执行正确"""
        from orchestrator.fast_planner import Task, ExecutionPlan, Intent
        from orchestrator.parallel_executor import parallel_executor
        from pathlib import Path

        temp_file = Path("data/test_comprehensive_executor.txt")
        if temp_file.exists():
            temp_file.unlink()

        tasks = [
            Task(
                id="write",
                intent=Intent.FILE_OP,
                tool="file_operations",
                params={"operation": "write", "file_path": str(temp_file), "content": "hello"},
                dependencies=set(),
                priority=10,
                estimated_time_ms=50,
            ),
            Task(
                id="read",
                intent=Intent.FILE_OP,
                tool="file_operations",
                params={"operation": "read", "file_path": str(temp_file)},
                dependencies={"write"},
                priority=9,
                estimated_time_ms=50,
            ),
        ]

        plan = ExecutionPlan(
            tasks=tasks,
            parallel_batches=[["write"], ["read"]],
            total_estimated_ms=100,
            requires_llm_polish=False,
        )

        results = parallel_executor.execute(plan)

        assert results["write"].success
        assert results["read"].success
        assert "hello" in str(results["read"].output)

        if temp_file.exists():
            temp_file.unlink()


class TestCacheManager:
    """测试缓存系统"""
    
    def test_cache_set_get(self):
        """测试缓存设置和获取"""
        from utils.cache import CacheManager
        
        cache = CacheManager(db_path="data/test_cache.db", ttl=10)
        
        cache.set("test_key", {"data": "test_value"})
        value = cache.get("test_key")
        
        assert value is not None
        assert value["data"] == "test_value"
        
        cache.clear_all()
    
    def test_cache_expiration(self):
        """测试缓存过期"""
        import time
        from utils.cache import CacheManager
        
        cache = CacheManager(db_path="data/test_cache.db", ttl=1)
        
        cache.set("expire_key", "value")
        time.sleep(2)
        
        value = cache.get("expire_key")
        assert value is None
        
        cache.clear_all()


class TestErrorHandler:
    """测试错误处理"""
    
    def test_error_classification(self):
        """测试错误分类"""
        from utils.error_handling import classify_error, ErrorCategory as ErrorType
        
        timeout_error = TimeoutError("Connection timeout")
        error_type = classify_error(timeout_error)
        
        assert error_type == ErrorType.TIMEOUT_ERROR
    
    def test_retry_mechanism(self):
        """测试重试机制"""
        from utils.error_handling import retry_with_backoff
        
        attempts = []
        
        @retry_with_backoff(max_retries=3, initial_delay=0.1, backoff_factor=1.5)
        def failing_func():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("Test error")
            return "success"
        
        result = failing_func()
        assert result == "success"
        assert len(attempts) == 3


class TestTaskTemplates:
    """测试任务模板"""
    
    def test_template_rendering(self):
        """测试模板渲染"""
        from utils.task_templates import template_manager
        
        template = template_manager.get_template("web_scraping")
        assert template is not None
        
        rendered = template.render(url="https://example.com")
        assert rendered[0]["params"]["url"] == "https://example.com"
    
    def test_template_list(self):
        """测试模板列表"""
        from utils.task_templates import template_manager
        
        templates = template_manager.list_templates()
        assert len(templates) > 0
        assert "web_scraping" in templates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
