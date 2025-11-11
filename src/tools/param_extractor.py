"""智能参数提取器：从任务描述中提取工具调用参数。

功能：
- 基于规则的参数提取
- 参数验证
- 默认值填充
- 错误提示
"""

from __future__ import annotations

import re
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse


class ParamExtractor:
    """智能参数提取器"""
    
    def __init__(self):
        """初始化参数提取器"""
        # URL 正则
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # 文件路径正则
        self.file_pattern = re.compile(
            r'[a-zA-Z]:[\\\/](?:[^\\\/\n]+[\\\/])*[^\\\/\n]+|\.{1,2}[\\\/](?:[^\\\/\n]+[\\\/])*[^\\\/\n]+'
        )
        
        # 数字正则
        self.number_pattern = re.compile(r'\d+')
    
    def extract_urls(self, text: str) -> List[str]:
        """提取 URL"""
        return self.url_pattern.findall(text)
    
    def extract_file_paths(self, text: str) -> List[str]:
        """提取文件路径"""
        return self.file_pattern.findall(text)
    
    def extract_numbers(self, text: str) -> List[int]:
        """提取数字"""
        return [int(n) for n in self.number_pattern.findall(text)]
    
    def extract_for_search(self, task: str) -> Dict[str, Any]:
        """为搜索工具提取参数"""
        # 移除常见的搜索前缀
        query = task
        prefixes = ["搜索", "查找", "search", "find", "google"]
        for prefix in prefixes:
            if query.lower().startswith(prefix):
                query = query[len(prefix):].strip()
        
        return {
            "query": query,
            "max_results": 5
        }
    
    def extract_for_code_execution(self, task: str) -> Dict[str, Any]:
        """为代码执行提取参数"""
        # 提取代码块（如果有）
        code_match = re.search(r'```(?:python)?\n(.*?)\n```', task, re.DOTALL)
        if code_match:
            code = code_match.group(1)
        else:
            # 如果没有代码块，使用整个任务作为描述
            code = f"# {task}\n# 请在这里编写代码"
        
        return {
            "code": code
        }
    
    def extract_for_browser(self, task: str) -> Dict[str, Any]:
        """为浏览器自动化提取参数"""
        urls = self.extract_urls(task)
        
        # 判断操作类型
        operation = "navigate"
        if "截图" in task or "screenshot" in task.lower():
            operation = "screenshot"
        elif "提取" in task or "extract" in task.lower():
            operation = "extract"
        elif "点击" in task or "click" in task.lower():
            operation = "click"
        
        params = {
            "action": operation
        }
        
        if urls:
            params["url"] = urls[0]
        
        return params
    
    def extract_for_database(self, task: str) -> Dict[str, Any]:
        """为数据库操作提取参数"""
        # 提取 SQL 查询
        sql_match = re.search(r'```sql\n(.*?)\n```', task, re.DOTALL)
        if sql_match:
            query = sql_match.group(1)
        else:
            # 尝试找到 SELECT/INSERT/UPDATE 等关键词
            sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE"]
            query = None
            for keyword in sql_keywords:
                if keyword in task.upper():
                    # 提取从关键词开始的部分
                    idx = task.upper().index(keyword)
                    query = task[idx:].split('\n')[0]
                    break
        
        # 默认使用 SQLite
        return {
            "operation": "query" if query and "SELECT" in query.upper() else "command",
            "connection_string": "sqlite:///./data.db",
            "query": query if query else "SELECT * FROM users LIMIT 5"
        }
    
    def extract_for_file_ops(self, task: str) -> Dict[str, Any]:
        """为文件操作提取参数"""
        file_paths = self.extract_file_paths(task)
        
        # 判断操作类型
        operation = "read"
        if "写" in task or "write" in task.lower() or "保存" in task:
            operation = "write"
        elif "列出" in task or "list" in task.lower():
            operation = "list"
        elif "搜索" in task or "search" in task.lower():
            operation = "search"
        elif "删除" in task or "delete" in task.lower():
            operation = "delete"
        elif "复制" in task or "copy" in task.lower():
            operation = "copy"
        
        params = {
            "operation": operation
        }
        
        if file_paths:
            params["file_path"] = file_paths[0]
        
        return params
    
    def extract_for_git(self, task: str) -> Dict[str, Any]:
        """为 Git 操作提取参数"""
        urls = self.extract_urls(task)
        
        # 判断操作类型
        operation = "status"
        if "克隆" in task or "clone" in task.lower():
            operation = "clone"
        elif "提交" in task or "commit" in task.lower():
            operation = "commit"
        elif "推送" in task or "push" in task.lower():
            operation = "push"
        elif "拉取" in task or "pull" in task.lower():
            operation = "pull"
        elif "分支" in task or "branch" in task.lower():
            operation = "branch"
        
        params = {
            "operation": operation
        }
        
        if urls and operation == "clone":
            params["url"] = urls[0]
        
        return params
    
    def extract_for_http(self, task: str) -> Dict[str, Any]:
        """为 HTTP 请求提取参数"""
        urls = self.extract_urls(task)
        
        # 判断请求方法
        method = "GET"
        if "post" in task.lower():
            method = "POST"
        elif "put" in task.lower():
            method = "PUT"
        elif "delete" in task.lower():
            method = "DELETE"
        
        params = {
            "method": method
        }
        
        if urls:
            params["url"] = urls[0]
        else:
            params["url"] = "https://api.example.com/data"
        
        return params
    
    def extract_params(self, tool_name: str, task: str) -> Dict[str, Any]:
        """
        根据工具名称提取参数
        
        参数:
            tool_name: 工具名称
            task: 任务描述
        
        返回:
            参数字典
        """
        extractors = {
            "intelligent_search": self.extract_for_search,
            "code_execution": self.extract_for_code_execution,
            "browser_automation": self.extract_for_browser,
            "sql_database": self.extract_for_database,
            "file_operations": self.extract_for_file_ops,
            "git_operations": self.extract_for_git,
            "http_client": self.extract_for_http,
        }
        
        extractor = extractors.get(tool_name)
        if extractor:
            try:
                return extractor(task)
            except Exception as e:
                print(f"⚠️ 参数提取失败: {e}")
                return {}
        
        return {}
    
    def validate_params(self, tool_name: str, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证参数
        
        参数:
            tool_name: 工具名称
            params: 参数字典
        
        返回:
            (是否有效, 错误消息)
        """
        # 定义必需参数
        required_params = {
            "intelligent_search": ["query"],
            "code_execution": ["code"],
            "browser_automation": ["action"],
            "sql_database": ["operation", "connection_string"],
            "file_operations": ["operation"],
            "http_client": ["method", "url"],
        }
        
        required = required_params.get(tool_name, [])
        
        for param in required:
            if param not in params or not params[param]:
                return False, f"缺少必需参数: {param}"
        
        return True, None


# 全局实例
param_extractor = ParamExtractor()
