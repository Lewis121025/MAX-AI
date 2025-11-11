"""零 LLM 快速规划器：使用 NLP + PDDL 实现确定性任务分解。

性能目标: <120ms
幻觉风险: 0 (纯确定性系统)
"""

from __future__ import annotations

import re
import time
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class Intent(Enum):
    """意图分类（轻量级 NLP）"""
    SEARCH = "search"
    CALCULATE = "calculate"
    CODE_EXECUTE = "code_execute"
    FILE_OP = "file_op"
    DATA_ANALYSIS = "data_analysis"
    WEB_SCRAPE = "web_scrape"
    MULTI_STEP = "multi_step"
    SIMPLE_QA = "simple_qa"


@dataclass
class Task:
    """原子任务"""
    id: str
    intent: Intent
    tool: str
    params: Dict[str, Any]
    dependencies: Set[str]
    priority: int = 5
    estimated_time_ms: int = 1000


@dataclass
class ExecutionPlan:
    """执行计划（树结构）"""
    tasks: List[Task]
    parallel_batches: List[List[str]]  # 可并行执行的任务 ID 分组
    total_estimated_ms: int
    requires_llm_polish: bool = True


class FastPlanner:
    """零 LLM 规划器"""
    
    def __init__(self):
        # 意图识别规则（确定性）
        self.intent_patterns = {
            Intent.SEARCH: [
                r"搜索|查找|找一下|查询|search|find",
                r"最新.*信息|.*进展|.*动态",
            ],
            Intent.CALCULATE: [
                r"\d+\s*[\+\-\*\/]\s*\d+",
                r"计算|求和|求积|sum|calculate",
            ],
            Intent.CODE_EXECUTE: [
                r"运行|执行|代码|python|javascript",
                r"写.*程序|生成.*脚本",
            ],
            Intent.FILE_OP: [
                r"读取|保存|文件|file|csv|txt|json",
                r"打开|写入",
            ],
            Intent.DATA_ANALYSIS: [
                r"分析|统计|对比|趋势|analyze",
                r"数据.*处理|.*可视化",
            ],
            Intent.WEB_SCRAPE: [
                r"抓取|爬取|网页|scrape|crawl",
                r"提取.*内容",
            ],
            Intent.MULTI_STEP: [
                r"然后|接着|并且|同时",
                r"首先.*其次|第一.*第二",
            ],
        }
        
        # 工具映射（确定性）
        self.intent_to_tool = {
            Intent.SEARCH: "intelligent_search",
            Intent.CALCULATE: "code_execution",
            Intent.CODE_EXECUTE: "code_execution",
            Intent.FILE_OP: "file_operations",
            Intent.DATA_ANALYSIS: "data_analysis",
            Intent.WEB_SCRAPE: "file_scraper",
        }
        
        # 参数提取规则
        self.param_extractors = {
            Intent.SEARCH: self._extract_search_params,
            Intent.CALCULATE: self._extract_calc_params,
            Intent.FILE_OP: self._extract_file_params,
            Intent.DATA_ANALYSIS: self._extract_analysis_params,
        }
    
    def plan(self, user_query: str, context: Dict[str, Any] = None) -> ExecutionPlan:
        """
        快速规划（目标 <120ms）
        
        Args:
            user_query: 用户查询
            context: 上下文（上传文件、历史、工具结果等）
        
        Returns:
            执行计划
        """
        start_time = time.time()
        context = context or {}
        
        # 检查是否有历史上下文
        has_history = bool(context.get("recent_turns") or context.get("recent_tool_results"))
        if has_history:
            print(f"🔍 检测到历史上下文，将纳入规划")
        
        # 1. 意图识别（10-20ms）
        intents = self._classify_intent(user_query, context)
        
        # 2. 任务分解（20-40ms）
        tasks = self._decompose_tasks(user_query, intents, context)
        
        # 3. 依赖分析（10-20ms）
        self._analyze_dependencies(tasks)
        
        # 4. PDDL 调度（30-40ms）
        parallel_batches = self._schedule_tasks(tasks)
        
        # 5. 估算总时间
        total_time = self._estimate_total_time(parallel_batches, tasks)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        print(f"⚡ FastPlanner 完成: {elapsed_ms}ms")
        
        return ExecutionPlan(
            tasks=tasks,
            parallel_batches=parallel_batches,
            total_estimated_ms=total_time,
            requires_llm_polish=self._needs_polish(intents)
        )
    
    def _classify_intent(self, query: str, context: Dict[str, Any] = None) -> List[Intent]:
        """
        轻量级 NLP 意图分类（确定性，<20ms）
        
        Args:
            query: 用户查询
            context: 历史上下文（可选）
        """
        query_lower = query.lower()
        detected_intents = []
        context = context or {}
        
        # 检测上传的文件类型（图片自动触发视觉分析，其他文件触发文件操作）
        uploaded_files = context.get("uploaded_files", [])
        if uploaded_files:
            for file_path in uploaded_files:
                file_lower = file_path.lower()
                # 检测图片文件
                if any(ext in file_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                    print(f"[IMAGE] 检测到图片文件: {file_path}")
                    # 如果查询中没有明确的其他意图，默认为图片分析
                    if not any(keyword in query_lower for keyword in ['搜索', '计算', '代码', '执行']):
                        # 创建特殊的图片分析意图（后续会映射到vision_analysis工具）
                        detected_intents.append(Intent.FILE_OP)  # 暂时用FILE_OP，后面特殊处理
                        break
                # 检测其他文件（txt, docx, pdf 等）
                elif any(ext in file_lower for ext in ['.txt', '.docx', '.doc', '.pdf', '.csv', '.json', '.py', '.md', '.html', '.css', '.js']):
                    print(f"[FILE] 检测到文件: {file_path}")
                    # 如果有上传的文件，自动添加文件操作意图
                    if Intent.FILE_OP not in detected_intents:
                        detected_intents.append(Intent.FILE_OP)
                        print(f"[FILE] 自动添加文件操作意图")
                    break
        
        # 检测是否为延续性查询（需要历史上下文）
        continuation_keywords = ["继续", "接着", "然后", "再", "还有", "上面", "之前", "刚才"]
        is_continuation = any(kw in query_lower for kw in continuation_keywords)
        
        # 如果是延续性查询且有历史工具结果，复用之前的意图
        if is_continuation and context.get("recent_turns"):
            recent_turns = context["recent_turns"]
            if recent_turns:
                last_tools = recent_turns[-1].get("tools_used", [])
                print(f"🔄 检测到延续性查询，上次使用工具: {last_tools}")
        
        # 规则匹配
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected_intents.append(intent)
                    print(f"  ✅ 检测到意图: {intent.value} (匹配模式: {pattern})")
                    break
        
        # 多步骤检测
        if Intent.MULTI_STEP in detected_intents:
            detected_intents.remove(Intent.MULTI_STEP)
            # 保留其他意图，标记为多步骤
        
        # 默认意图
        if not detected_intents:
            detected_intents.append(Intent.SIMPLE_QA)
            print(f"  ⚠️ 未检测到明确意图，使用默认: SIMPLE_QA")
        
        print(f"  📋 最终检测到的意图: {[i.value for i in detected_intents]}")
        return detected_intents
    
    def _decompose_tasks(
        self, 
        query: str, 
        intents: List[Intent], 
        context: Dict[str, Any]
    ) -> List[Task]:
        """
        分解为原子任务（确定性，<40ms）
        """
        tasks = []
        task_id = 0
        
        # 特殊处理：检测上传的图片文件，自动创建vision_analysis任务
        uploaded_files = context.get("uploaded_files", [])
        image_files = [f for f in uploaded_files if any(ext in f.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'])]
        
        if image_files:
            for img_path in image_files:
                # 提取查询中的问题（去掉文件路径提示）
                clean_query = re.sub(r'\[用户上传了文件:.*?\]', '', query).strip()
                question = clean_query if clean_query else None
                
                task = Task(
                    id=f"task_{task_id}",
                    intent=Intent.FILE_OP,  # 使用FILE_OP意图（图片也是文件）
                    tool="vision_analysis",
                    params={
                        "image_path": img_path,
                        "question": question
                    },
                    dependencies=set(),
                    priority=1,
                    estimated_time_ms=8000
                )
                tasks.append(task)
                task_id += 1
                print(f"[VISION] 创建图片分析任务: {img_path}")
        
        # 处理其他意图
        for intent in intents:
            # 跳过简单问答
            if intent == Intent.SIMPLE_QA:
                print(f"  ⏭️ 跳过简单问答意图")
                continue
            
            # 如果已经处理了图片，跳过FILE_OP意图（避免重复）
            if intent == Intent.FILE_OP and image_files:
                print(f"  ⏭️ 跳过文件操作意图（已处理图片）")
                continue
            
            # 获取工具
            tool = self.intent_to_tool.get(intent)
            if not tool:
                print(f"  ⚠️ 意图 {intent.value} 没有对应的工具")
                continue
            
            print(f"  🔧 为意图 {intent.value} 创建任务，工具: {tool}")
            
            # 提取参数（确定性）
            extractor = self.param_extractors.get(intent, lambda q, c: {})
            params = extractor(query, context)
            
            # 创建任务
            task = Task(
                id=f"task_{task_id}",
                intent=intent,
                tool=tool,
                params=params,
                dependencies=set(),
                priority=self._get_priority(intent),
                estimated_time_ms=self._estimate_task_time(tool)
            )
            
            tasks.append(task)
            task_id += 1
        
        return tasks
    
    def _extract_search_params(self, query: str, context: Dict) -> Dict[str, Any]:
        """提取搜索参数（确定性）"""
        # 去除噪音词，但保留查询的核心内容
        noise_words = ["搜索", "查找", "找一下", "帮我", "请"]
        clean_query = query
        for word in noise_words:
            # 只移除独立的词，避免误删查询内容
            clean_query = re.sub(rf'\b{re.escape(word)}\b', '', clean_query, flags=re.IGNORECASE)
        
        # 如果清理后为空，使用原始查询
        clean_query = clean_query.strip() or query.strip()
        
        print(f"  🔍 搜索查询: {clean_query}")
        
        return {
            "query": clean_query,
            "max_results": 5
        }
    
    def _extract_calc_params(self, query: str, context: Dict) -> Dict[str, Any]:
        """提取计算参数"""
        # 提取数字范围（如"1到100"）
        range_match = re.search(r'(\d+)\s*(?:到|至|~|-)\s*(\d+)', query)
        if range_match and any(kw in query for kw in ['和', '求和', 'sum', '加']):
            start, end = range_match.groups()
            code = f"""# 计算 {start} 到 {end} 的和
result = sum(range({start}, {end}+1))
print(f"{start} 到 {end} 的和是: {{result}}")"""
            return {"code": code}
        
        # 提取数学表达式
        math_expr = re.search(r'[\d\+\-\*\/\(\)\s]+', query)
        if math_expr:
            expr = math_expr.group().strip()
            code = f"""# 计算: {expr}
result = {expr}
print(f"计算结果: {{result}}")"""
            return {"code": code}
        
        # 其他计算
        numbers = re.findall(r'\d+', query)
        if len(numbers) >= 2:
            code = f"""# 求和
result = sum([{', '.join(numbers)}])
print(f"结果: {{result}}")"""
        else:
            code = f"print('无法识别的计算任务: {query}')"
        
        return {"code": code}
    
    def _extract_file_params(self, query: str, context: Dict) -> Dict[str, Any]:
        """提取文件操作参数"""
        # 从上下文获取文件路径
        file_path = None
        if context and "uploaded_files" in context:
            files = context["uploaded_files"]
            if files:
                file_path = files[0]  # 取第一个文件
                print(f"[FILE] 检测到上传的文件: {file_path}")
        
        # 或从查询中提取
        if not file_path:
            file_match = re.search(r'[a-zA-Z0-9_\-]+\.(csv|txt|json|xlsx|pdf|docx|doc)', query)
            if file_match:
                file_path = f"data/uploads/{file_match.group()}"
        
        # 检测操作类型
        # 如果有上传的文件，默认是读取操作
        if file_path:
            if any(word in query for word in ["保存", "写入", "write"]):
                operation = "write"
            else:
                # 默认读取上传的文件
                operation = "read"
                print(f"[FILE] 默认操作: 读取文件 {file_path}")
        else:
            if any(word in query for word in ["读取", "打开", "查看", "read"]):
                operation = "read"
            elif any(word in query for word in ["保存", "写入", "write"]):
                operation = "write"
            else:
                operation = "list"
        
        return {
            "operation": operation,
            "file_path": file_path or "data/temp.txt"
        }
    
    def _extract_analysis_params(self, query: str, context: Dict) -> Dict[str, Any]:
        """提取数据分析参数"""
        # 简化：假设需要分析上传的文件
        file_path = None
        if context and "uploaded_files" in context:
            files = context["uploaded_files"]
            if files:
                file_path = files[0]
        
        # 生成分析代码
        code = f"""
import pandas as pd
df = pd.read_csv('{file_path}')
print(df.describe())
print(df.head())
"""
        
        return {"code": code.strip()}
    
    def _analyze_dependencies(self, tasks: List[Task]):
        """
        依赖分析（确定性，<20ms）
        
        规则:
        - 文件读取 -> 数据分析
        - 搜索 -> 数据分析
        - 其他任务默认无依赖（可并行）
        """
        task_dict = {t.id: t for t in tasks}
        
        for task in tasks:
            if task.intent == Intent.DATA_ANALYSIS:
                # 查找文件操作任务
                for other in tasks:
                    if other.intent == Intent.FILE_OP and other.id != task.id:
                        task.dependencies.add(other.id)
    
    def _schedule_tasks(self, tasks: List[Task]) -> List[List[str]]:
        """
        PDDL 调度器：生成并行执行批次（<40ms）
        
        Returns:
            [[batch1_tasks], [batch2_tasks], ...]
        """
        if not tasks:
            return []
        
        # 拓扑排序 + 并行优化
        task_dict = {t.id: t for t in tasks}
        remaining = set(task_dict.keys())
        batches = []
        
        while remaining:
            # 找出当前可执行的任务（无依赖或依赖已完成）
            completed = set(task_dict.keys()) - remaining
            ready = []
            
            for task_id in remaining:
                task = task_dict[task_id]
                if not task.dependencies or task.dependencies.issubset(completed):
                    ready.append(task_id)
            
            if not ready:
                # 循环依赖，强制执行
                ready = list(remaining)
            
            # 按优先级排序
            ready.sort(key=lambda tid: task_dict[tid].priority, reverse=True)
            
            batches.append(ready)
            remaining -= set(ready)
        
        return batches
    
    def _estimate_total_time(
        self, 
        batches: List[List[str]], 
        tasks: List[Task]
    ) -> int:
        """
        估算总执行时间（并行批次）
        """
        task_dict = {t.id: t for t in tasks}
        total_ms = 0
        
        for batch in batches:
            # 批次内并行，取最长时间
            batch_time = max(
                task_dict[tid].estimated_time_ms 
                for tid in batch
            )
            total_ms += batch_time
        
        return total_ms
    
    def _get_priority(self, intent: Intent) -> int:
        """任务优先级"""
        priority_map = {
            Intent.FILE_OP: 10,       # 最高优先级
            Intent.SEARCH: 8,
            Intent.WEB_SCRAPE: 8,
            Intent.DATA_ANALYSIS: 5,
            Intent.CODE_EXECUTE: 5,
            Intent.CALCULATE: 3,
        }
        return priority_map.get(intent, 5)
    
    def _estimate_task_time(self, tool: str) -> int:
        """估算工具执行时间（ms）"""
        time_estimates = {
            "intelligent_search": 2000,
            "file_operations": 100,
            "code_execution": 1500,
            "data_analysis": 2000,
            "file_scraper": 3000,
        }
        return time_estimates.get(tool, 1000)
    
    def _needs_polish(self, intents: List[Intent]) -> bool:
        """判断是否需要 LLM 润色
        
        FastAgent 架构要求：所有查询都需要 LLM 进行最终回答
        - 简单问答：LLM 直接回答
        - 工具任务：LLM 根据工具结果进行润色和整合
        """
        # 所有查询都需要 LLM 参与
        return True


# 全局单例
fast_planner = FastPlanner()
