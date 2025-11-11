"""性能测试：测试系统性能和响应时间。"""

import pytest
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.mark.performance
class TestPerformance:
    """性能测试"""
    
    def test_cache_performance(self):
        """测试缓存性能"""
        from utils.cache import CacheManager
        
        cache = CacheManager(db_path="data/test_perf_cache.db")
        
        write_times = []
        read_times = []
        
        for i in range(100):
            key = f"key_{i}"
            value = {"data": f"value_{i}"}
            
            start = time.time()
            cache.set(key, value)
            write_times.append(time.time() - start)
            
            start = time.time()
            cache.get(key)
            read_times.append(time.time() - start)
        
        avg_write = sum(write_times) / len(write_times)
        avg_read = sum(read_times) / len(read_times)
        
        print(f"\n平均写入时间: {avg_write*1000:.2f}ms")
        print(f"平均读取时间: {avg_read*1000:.2f}ms")
        
        assert avg_write < 0.01
        assert avg_read < 0.01
        
        cache.clear_all()
    
    def test_fast_planner_performance(self):
        """测试 FastPlanner 在多次调用下的平均耗时"""
        from orchestrator.fast_planner import fast_planner

        queries = [
            "计算 1 到 100 的和",
            "分析销售数据并生成总结",
            "抓取 example.com 的标题",
        ]

        iterations = 10
        durations = []

        for _ in range(iterations):
            start = time.time()
            fast_planner.plan(queries[_ % len(queries)])
            durations.append(time.time() - start)

        avg_time = sum(durations) / len(durations)
        print(f"\nFastPlanner 平均耗时: {avg_time*1000:.2f}ms")
        assert avg_time < 0.3  # 规划应在 300ms 内完成

    def test_parallel_executor_performance(self):
        """使用简单文件任务评估并行执行耗时"""
        from orchestrator.fast_planner import Task, ExecutionPlan, Intent
        from orchestrator.parallel_executor import parallel_executor
        from pathlib import Path

        temp_file = Path("data/test_perf_executor.txt")
        if temp_file.exists():
            temp_file.unlink()

        tasks = [
            Task(
                id="write",
                intent=Intent.FILE_OP,
                tool="file_operations",
                params={"operation": "write", "file_path": str(temp_file), "content": "perf"},
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

        start = time.time()
        results = parallel_executor.execute(plan)
        duration = time.time() - start

        assert results["write"].success
        assert results["read"].success
        assert duration < 1.0  # 整个流程应在 1 秒内完成

        if temp_file.exists():
            temp_file.unlink()
    
    def test_concurrent_requests(self):
        """测试并发请求处理"""
        import concurrent.futures
        from utils.cache import CacheManager
        
        cache = CacheManager(db_path="data/test_perf_cache.db")
        
        def worker(i):
            key = f"concurrent_key_{i}"
            value = {"data": i}
            cache.set(key, value)
            result = cache.get(key)
            return result is not None
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(worker, range(100)))
        
        duration = time.time() - start
        success_rate = sum(results) / len(results)
        
        print(f"\n100个并发请求完成时间: {duration:.2f}s")
        print(f"成功率: {success_rate*100:.1f}%")
        
        assert success_rate > 0.95
        assert duration < 5.0
        
        cache.clear_all()


@pytest.mark.performance
class TestMemoryUsage:
    """内存使用测试"""
    
    def test_session_storage_scaling(self):
        """验证会话存储在大量消息下仍然稳定"""
        from fastapi_app import save_session, load_session, delete_session_file
        from langchain_core.messages import HumanMessage

        session_id = "perf_memory_session"
        messages = [HumanMessage(content=f"消息 {i}") for i in range(200)]

        save_session(session_id, messages)
        loaded = load_session(session_id)

        assert len(loaded) == len(messages)
        assert str(loaded[-1].content) == "消息 199"

        delete_session_file(session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
