"""工具注册表：可用工具的集中目录。"""

from __future__ import annotations

from typing import Callable, Dict


class ToolRegistry:
    """管理可用工具及其元数据。"""
    
    def __init__(self):
        self._tools: Dict[str, dict] = {}
    
    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        requires_auth: bool = True,
    ):
        """注册一个新工具。
        
        参数：
            name: 工具标识符（如 "intelligent_search"）
            func: 要执行的可调用函数
            description: 供大模型理解的描述
            requires_auth: 是否需要 API 密钥
        """
        self._tools[name] = {
            "function": func,
            "description": description,
            "requires_auth": requires_auth,
        }
    
    def get(self, name: str) -> Callable | None:
        """按名称获取工具函数。"""
        tool = self._tools.get(name)
        if tool:
            return tool["function"]
        else:
            print(f"⚠️ 工具未找到: {name}")
            print(f"📋 可用工具: {', '.join(self.list_available())}")
            return None
    
    def get_tool(self, name: str) -> Callable | None:
        """按名称获取工具函数（别名方法）。"""
        return self.get(name)
    
    def list_available(self) -> list[str]:
        """返回所有已注册工具的名称。"""
        return list(self._tools.keys())
    
    def list_tools(self) -> list[str]:
        """返回所有已注册工具的名称（别名方法）。"""
        return self.list_available()
    
    def get_descriptions(self) -> list[dict]:
        """返回包含工具元数据的列表。"""
        return [
            {
                "name": name,
                "description": meta["description"],
                "requires_auth": meta["requires_auth"],
            }
            for name, meta in self._tools.items()
        ]


# 全局注册表实例
registry = ToolRegistry()


# 导入真实工具（如果未配置 API key 会优雅降级）
from tools.tavily_tool import tavily_search
from tools.e2b_tool import execute_python_code
from tools.firecrawl_tool import scrape_url

# 导入核心工具
from tools.browser_tool import browser_automation_sync
from tools.database_tool import sql_database
from tools.file_tool import file_operations

# 导入扩展工具
from tools.git_tool import git_operations
from tools.image_tool import image_processing
from tools.pdf_tool import pdf_operations
from tools.data_tool import data_analysis
from tools.http_tool import http_client
from tools.shell_tool import shell_command
# vision_analysis 使用 analyze_image 函数直接注册（见下方）


# 注册真实工具
registry.register(
    "intelligent_search",
    tavily_search,
    "使用 Tavily API 在网上搜索信息（需要 TAVILY_API_KEY）",
    requires_auth=True,
)

registry.register(
    "code_execution",
    execute_python_code,
    "在 E2B 沙盒中安全执行 Python 代码（需要 E2B_API_KEY）",
    requires_auth=True,
)

registry.register(
    "file_scraper",
    scrape_url,
    "使用 Firecrawl 从 URL 提取网页内容（需要 FIRECRAWL_API_KEY）",
    requires_auth=True,
)

# 注册新工具
registry.register(
    "browser_automation",
    browser_automation_sync,
    "使用 Playwright 进行浏览器自动化操作：打开网页、截图、提取内容、点击元素、填写表单",
    requires_auth=False,
)

registry.register(
    "sql_database",
    sql_database,
    "执行 SQL 数据库查询和操作，支持 SQLite/PostgreSQL/MySQL/SQL Server",
    requires_auth=False,
)

registry.register(
    "file_operations",
    file_operations,
    "文件系统操作：读取、写入、列出目录、搜索文件、复制、删除等",
    requires_auth=False,
)

# 注册扩展工具
registry.register(
    "git_operations",
    git_operations,
    "Git 仓库操作：克隆、提交、推送、拉取、分支管理、查看历史",
    requires_auth=False,
)

registry.register(
    "image_processing",
    image_processing,
    "图像处理：调整大小、裁剪、旋转、滤镜、格式转换、添加文字水印",
    requires_auth=False,
)

registry.register(
    "pdf_operations",
    pdf_operations,
    "PDF 操作：提取文本、创建PDF、合并PDF、获取信息",
    requires_auth=False,
)

registry.register(
    "data_analysis",
    data_analysis,
    "数据分析：读取CSV/Excel、统计描述、过滤、分组聚合、数据导出",
    requires_auth=False,
)

registry.register(
    "http_client",
    http_client,
    "HTTP 客户端：发送 GET/POST/PUT/DELETE 请求、自定义请求头、JSON/表单数据",
    requires_auth=False,
)

# 注册 vision_analysis：使用原始函数而不是 StructuredTool
from tools.vision_tool import analyze_image
registry.register(
    "vision_analysis",
    analyze_image,  # 直接注册函数，而不是 StructuredTool
    "AI视觉分析：识别图片内容、读取图片文字（OCR）、分析图表截图、回答图片相关问题",
    requires_auth=False,
)

registry.register(
    "shell_command",
    shell_command,
    "Shell 命令执行：安全执行系统命令（有危险命令检测）",
    requires_auth=False,
)

registry.register(
    "none",
    lambda: "无操作",
    "纯推理任务的占位符",
    requires_auth=False,
)
