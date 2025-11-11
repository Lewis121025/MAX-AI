"""并行调度器：零 LLM，一次性触发所有工具。

性能目标: <5秒（取决于最慢工具）
可靠性: 100%（无 LLM 决策）
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from dataclasses import dataclass

from orchestrator.fast_planner import ExecutionPlan, Task
from tools.registry import registry


# 配置
DEFAULT_TIMEOUT = 60  # 默认超时 60 秒
SEARCH_TIMEOUT = 30   # 搜索任务超时 30 秒
FILE_TIMEOUT = 10     # 文件操作超时 10 秒


@dataclass
class ToolResult:
    """工具执行结果"""
    task_id: str
    tool: str
    success: bool
    output: Any
    error: Optional[str] = None
    elapsed_ms: int = 0


class ParallelExecutor:
    """并行执行器"""
    
    def __init__(self, max_workers: int = 10, default_timeout: int = DEFAULT_TIMEOUT):
        self.max_workers = max_workers
        self.default_timeout = default_timeout
    
    def execute(self, plan: ExecutionPlan) -> Dict[str, ToolResult]:
        """
        执行计划（并行批次）
        
        Args:
            plan: 执行计划
        
        Returns:
            任务 ID -> 执行结果
        """
        start_time = time.time()
        results = {}
        
        print(f"🚀 并行执行器启动: {len(plan.tasks)} 个任务")
        
        # 按批次执行
        for batch_idx, batch in enumerate(plan.parallel_batches):
            print(f"\n📦 批次 {batch_idx + 1}: {len(batch)} 个任务并行执行")
            
            # 并行执行当前批次
            batch_results = self._execute_batch(
                [t for t in plan.tasks if t.id in batch],
                results  # 传递前面批次的结果
            )
            
            results.update(batch_results)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        print(f"\n✅ 并行执行完成: {elapsed_ms}ms")
        
        return results
    
    def _execute_batch(
        self, 
        tasks: List[Task], 
        previous_results: Dict[str, ToolResult]
    ) -> Dict[str, ToolResult]:
        """
        执行一个批次的任务（并行）
        """
        results = {}
        
        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(
                    self._execute_task, 
                    task, 
                    previous_results
                ): task
                for task in tasks
            }
            
            # 收集结果
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    # 根据任务类型设置超时
                    timeout = self._get_timeout(task)
                    result = future.result(timeout=timeout)
                    results[task.id] = result
                    
                    status = "✅" if result.success else "❌"
                    if result.success:
                        print(f"  {status} {task.id} ({task.tool}): {result.elapsed_ms}ms")
                    else:
                        error_info = result.error or "未知错误"
                        print(f"  {status} {task.id} ({task.tool}): {result.elapsed_ms}ms")
                        print(f"     错误: {error_info}")
                    
                except TimeoutError:
                    print(f"  ⏱️ {task.id} 超时 ({self._get_timeout(task)}s)")
                    results[task.id] = ToolResult(
                        task_id=task.id,
                        tool=task.tool,
                        success=False,
                        output=None,
                        error=f"任务超时 ({self._get_timeout(task)}秒)",
                        elapsed_ms=self._get_timeout(task) * 1000
                    )
                except Exception as e:
                    print(f"  ❌ {task.id} 执行异常: {type(e).__name__}: {e}")
                    results[task.id] = ToolResult(
                        task_id=task.id,
                        tool=task.tool,
                        success=False,
                        output=None,
                        error=f"{type(e).__name__}: {str(e)}",
                        elapsed_ms=0
                    )
        
        return results
    
    def _execute_task(
        self, 
        task: Task, 
        previous_results: Dict[str, ToolResult]
    ) -> ToolResult:
        """
        执行单个任务（确定性，无 LLM）
        """
        start_time = time.time()
        
        try:
            # 从注册表获取工具
            tool_func = registry.get(task.tool)
            
            if not tool_func:
                return ToolResult(
                    task_id=task.id,
                    tool=task.tool,
                    success=False,
                    output=None,
                    error=f"工具 {task.tool} 未找到"
                )
            
            # 处理依赖：如果依赖其他任务，注入结果
            params = self._resolve_params(task, previous_results)
            
            # 调试信息
            if task.tool in ["vision_analysis", "intelligent_search"]:
                print(f"  🔍 调试: 准备调用 {task.tool}")
                print(f"     参数: {params}")
                print(f"     工具函数: {tool_func}")
            
            # 执行工具
            output = tool_func(**params)
            
            # 记录工具执行结果
            if task.tool == "intelligent_search":
                print(f"  ✅ 搜索完成，结果长度: {len(str(output))} 字符")
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                task_id=task.id,
                tool=task.tool,
                success=True,
                output=output,
                elapsed_ms=elapsed_ms
            )
        
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return ToolResult(
                task_id=task.id,
                tool=task.tool,
                success=False,
                output=None,
                error=str(e),
                elapsed_ms=elapsed_ms
            )
    
    def _get_timeout(self, task: Task) -> int:
        """
        根据任务类型获取超时时间（秒）
        """
        if task.intent.value == "search":
            return SEARCH_TIMEOUT
        elif task.intent.value in ["file_op", "data_analysis"]:
            return FILE_TIMEOUT
        else:
            return self.default_timeout
    
    def _resolve_params(
        self, 
        task: Task, 
        previous_results: Dict[str, ToolResult]
    ) -> Dict[str, Any]:
        """
        解析参数（依赖注入）
        """
        params = task.params.copy()
        
        # 处理文件路径：确保路径格式正确（图片路径和文件路径）
        if "image_path" in params:
            # 清理路径中的引号（如果有）
            image_path = params["image_path"]
            if isinstance(image_path, str):
                # 移除可能的引号
                image_path = image_path.strip("'\"")
                # 确保路径存在
                from pathlib import Path
                path = Path(image_path)
                if not path.exists():
                    # 尝试解析为绝对路径
                    path = path.resolve()
                    if not path.exists():
                        # 如果还是不存在，记录警告但继续
                        print(f"  ⚠️ 警告: 图片路径不存在: {image_path} (解析后: {path})")
                params["image_path"] = str(path)
                print(f"  🔍 调试: 图片路径处理: {image_path} -> {params['image_path']} (存在: {path.exists()})")
        
        # 处理文件路径（file_path）
        if "file_path" in params:
            file_path = params["file_path"]
            if isinstance(file_path, str):
                # 移除可能的引号
                file_path = file_path.strip("'\"")
                from pathlib import Path
                path = Path(file_path)
                
                # 如果是绝对路径，直接使用
                if path.is_absolute():
                    if not path.exists():
                        # 尝试解析
                        path = path.resolve()
                    params["file_path"] = str(path)
                    print(f"  🔍 调试: 文件路径处理（绝对路径）: {file_path} -> {params['file_path']} (存在: {path.exists()})")
                else:
                    # 如果是相对路径，尝试解析
                    if not path.exists():
                        path = path.resolve()
                    params["file_path"] = str(path)
                    print(f"  🔍 调试: 文件路径处理（相对路径）: {file_path} -> {params['file_path']} (存在: {path.exists()})")
        
        # 如果有依赖，注入前面任务的输出
        if task.dependencies:
            for dep_id in task.dependencies:
                if dep_id in previous_results:
                    result = previous_results[dep_id]
                    if result.success:
                        # 根据任务类型注入不同参数
                        if task.intent.value == "data_analysis":
                            # 数据分析任务需要数据输入
                            params["data"] = result.output
                        elif task.intent.value == "file_op":
                            # 文件操作可能需要前一步的输出作为内容
                            if task.params.get("operation") == "write":
                                params["content"] = result.output
        
        return params


# 全局单例
parallel_executor = ParallelExecutor(max_workers=10)
