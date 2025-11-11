"""智能工具选择器：基于任务自动选择最优工具组合。

功能：
- 分析任务需求
- 匹配最佳工具
- 估算成本和时间
- 生成工具调用序列
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from tools.registry import registry


@dataclass
class ToolRecommendation:
    """工具推荐结果"""
    tool_name: str
    confidence: float  # 置信度 0-1
    reason: str
    estimated_time: int  # 预计时间（秒）
    cost_level: str  # 成本等级 (free/low/medium/high)


class ToolSelector:
    """智能工具选择器"""
    
    def __init__(self):
        """初始化工具选择器"""
        # 工具关键词映射
        self.tool_keywords = {
            "intelligent_search": [
                "搜索", "查找", "查询", "了解", "什么是", "search", "find", "google"
            ],
            "code_execution": [
                "代码", "执行", "运行", "计算", "算法", "程序", "python", "code", "script"
            ],
            "file_scraper": [
                "网页", "抓取", "爬虫", "提取", "scrape", "crawl", "webpage", "url"
            ],
            "browser_automation": [
                "浏览器", "点击", "填写", "表单", "截图", "自动化", "browser", "screenshot"
            ],
            "sql_database": [
                "数据库", "sql", "查询", "表", "database", "query", "select", "insert"
            ],
            "file_operations": [
                "文件", "读取", "写入", "保存", "目录", "file", "read", "write", "save"
            ],
            "git_operations": [
                "git", "仓库", "提交", "推送", "拉取", "分支", "commit", "push", "pull"
            ],
            "image_processing": [
                "调整", "裁剪", "旋转", "滤镜", "resize", "crop", "rotate", "filter"
            ],
            "vision_analysis": [
                "图片", "图像", "照片", "识别", "看", "描述", "分析图", "图表", "截图",
                "image", "photo", "picture", "recognize", "看看", "what", "识图", "ocr"
            ],
            "pdf_operations": [
                "pdf", "文档", "提取", "合并", "拆分", "document"
            ],
            "data_analysis": [
                "数据分析", "统计", "csv", "excel", "pandas", "分析", "analysis"
            ],
            "http_client": [
                "api", "请求", "http", "接口", "调用", "post", "get", "rest"
            ],
            "shell_command": [
                "命令", "终端", "shell", "bash", "cmd", "执行命令"
            ]
        }
        
        # 工具成本估算
        self.tool_costs = {
            "intelligent_search": "low",  # 需要 API key
            "code_execution": "medium",  # 需要 API key
            "file_scraper": "low",  # 需要 API key
            "vision_analysis": "medium",  # 需要视觉模型API
            "browser_automation": "free",
            "sql_database": "free",
            "file_operations": "free",
            "git_operations": "free",
            "image_processing": "free",
            "pdf_operations": "free",
            "data_analysis": "free",
            "http_client": "free",
            "shell_command": "free",
            "none": "free"
        }
        
        # 工具执行时间估算（秒）
        self.tool_times = {
            "intelligent_search": 5,
            "code_execution": 15,
            "file_scraper": 10,
            "vision_analysis": 8,
            "browser_automation": 8,
            "sql_database": 3,
            "file_operations": 2,
            "git_operations": 5,
            "image_processing": 3,
            "pdf_operations": 5,
            "data_analysis": 8,
            "http_client": 3,
            "shell_command": 5,
            "none": 0
        }
    
    def analyze_task(self, task: str) -> List[ToolRecommendation]:
        """
        分析任务并推荐工具
        
        参数:
            task: 任务描述
        
        返回:
            工具推荐列表（按置信度降序）
        """
        task_lower = task.lower()
        recommendations = []
        
        # 遍历所有工具，计算匹配度
        for tool_name, keywords in self.tool_keywords.items():
            # 计算关键词匹配数
            matches = sum(1 for kw in keywords if kw in task_lower)
            
            if matches > 0:
                # 置信度 = 匹配数 / 关键词总数
                confidence = min(matches / len(keywords) * 2, 1.0)  # 最高1.0
                
                # 生成推荐原因
                matched_keywords = [kw for kw in keywords if kw in task_lower]
                reason = f"匹配关键词: {', '.join(matched_keywords[:3])}"
                
                recommendation = ToolRecommendation(
                    tool_name=tool_name,
                    confidence=confidence,
                    reason=reason,
                    estimated_time=self.tool_times.get(tool_name, 5),
                    cost_level=self.tool_costs.get(tool_name, "free")
                )
                recommendations.append(recommendation)
        
        # 按置信度排序
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        # 如果没有匹配，默认推荐搜索
        if not recommendations:
            recommendations.append(ToolRecommendation(
                tool_name="intelligent_search",
                confidence=0.3,
                reason="默认使用搜索工具",
                estimated_time=5,
                cost_level="low"
            ))
        
        return recommendations
    
    def select_best_tool(self, task: str) -> str:
        """
        选择最佳工具
        
        参数:
            task: 任务描述
        
        返回:
            工具名称
        """
        recommendations = self.analyze_task(task)
        return recommendations[0].tool_name if recommendations else "none"
    
    def recommend_tool_chain(self, task: str, max_tools: int = 3) -> List[str]:
        """
        推荐工具链（多个工具组合）
        
        参数:
            task: 任务描述
            max_tools: 最大工具数量
        
        返回:
            工具名称列表
        """
        recommendations = self.analyze_task(task)
        
        # 取前 N 个高置信度的工具
        selected = [
            rec.tool_name 
            for rec in recommendations[:max_tools]
            if rec.confidence > 0.3
        ]
        
        return selected if selected else ["intelligent_search"]
    
    def estimate_total_cost(self, tools: List[str]) -> Dict[str, Any]:
        """
        估算工具链的总成本
        
        参数:
            tools: 工具名称列表
        
        返回:
            成本估算字典
        """
        total_time = sum(self.tool_times.get(tool, 5) for tool in tools)
        
        # 成本等级统计
        cost_levels = [self.tool_costs.get(tool, "free") for tool in tools]
        has_paid = any(level in ["low", "medium", "high"] for level in cost_levels)
        
        return {
            "total_time": total_time,
            "tool_count": len(tools),
            "has_paid_tools": has_paid,
            "cost_level": "paid" if has_paid else "free"
        }


# 全局实例
tool_selector = ToolSelector()
