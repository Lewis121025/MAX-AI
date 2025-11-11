"""任务模板系统：预定义常用任务的执行模板。"""

from __future__ import annotations

from typing import Dict, List, Any
import json
from pathlib import Path


class TaskTemplate:
    """任务模板"""
    
    def __init__(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        variables: List[str],
        category: str = "general"
    ):
        self.name = name
        self.description = description
        self.steps = steps
        self.variables = variables
        self.category = category
    
    def render(self, **kwargs) -> List[Dict[str, Any]]:
        """渲染模板（替换变量）
        
        Args:
            **kwargs: 模板变量值
            
        Returns:
            渲染后的步骤列表
        """
        rendered_steps = []
        
        # 添加默认的 previous_output 占位符
        default_kwargs = {
            'previous_output': '{previous_output}',  # 保留占位符供后续替换
            **kwargs
        }
        
        for step in self.steps:
            rendered_step = {}
            for key, value in step.items():
                if isinstance(value, str):
                    try:
                        rendered_step[key] = value.format(**default_kwargs)
                    except KeyError as e:
                        # 如果缺少变量，保留原始占位符
                        rendered_step[key] = value
                elif isinstance(value, dict):
                    rendered_step[key] = {}
                    for k, v in value.items():
                        if isinstance(v, str):
                            try:
                                rendered_step[key][k] = v.format(**default_kwargs)
                            except KeyError:
                                rendered_step[key][k] = v
                        else:
                            rendered_step[key][k] = v
                else:
                    rendered_step[key] = value
            
            rendered_steps.append(rendered_step)
        
        return rendered_steps


class TemplateManager:
    """模板管理器"""
    
    def __init__(self, templates_dir: str = "data/templates"):
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, TaskTemplate] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """加载内置模板"""
        
        self.templates["web_scraping"] = TaskTemplate(
            name="网页数据抓取",
            description="抓取网页内容并提取结构化数据",
            steps=[
                {
                    "tool": "file_scraper",
                    "params": {"url": "{url}"}
                },
                {
                    "tool": "data_analysis",
                    "params": {"operation": "parse_html", "data": "{previous_output}"}
                }
            ],
            variables=["url"],
            category="data_extraction"
        )
        
        self.templates["code_generation"] = TaskTemplate(
            name="代码生成与测试",
            description="生成代码并执行测试",
            steps=[
                {
                    "tool": "code_execution",
                    "params": {"code": "{code}"}
                },
                {
                    "tool": "code_execution",
                    "params": {"code": "{test_code}"}
                }
            ],
            variables=["code", "test_code"],
            category="development"
        )
        
        self.templates["research_summary"] = TaskTemplate(
            name="研究总结",
            description="搜索信息并生成摘要",
            steps=[
                {
                    "tool": "intelligent_search",
                    "params": {"query": "{topic}"}
                },
                {
                    "tool": "intelligent_search",
                    "params": {"query": "{topic} latest developments"}
                }
            ],
            variables=["topic"],
            category="research"
        )
        
        self.templates["file_analysis"] = TaskTemplate(
            name="文件分析",
            description="读取和分析文件内容",
            steps=[
                {
                    "tool": "file_operations",
                    "params": {"operation": "read", "path": "{file_path}"}
                },
                {
                    "tool": "data_analysis",
                    "params": {"operation": "analyze", "data": "{previous_output}"}
                }
            ],
            variables=["file_path"],
            category="data_analysis"
        )
    
    def get_template(self, name: str) -> TaskTemplate:
        """获取模板"""
        return self.templates.get(name)
    
    def list_templates(self, category: str = None) -> List[str]:
        """列出所有模板"""
        if category:
            return [
                name for name, template in self.templates.items()
                if template.category == category
            ]
        return list(self.templates.keys())
    
    def create_template(self, template: TaskTemplate):
        """创建新模板"""
        self.templates[template.name] = template
    
    def save_template(self, name: str, file_path: str):
        """保存模板到文件"""
        template = self.templates.get(name)
        if not template:
            raise ValueError(f"Template {name} not found")
        
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            "name": template.name,
            "description": template.description,
            "steps": template.steps,
            "variables": template.variables,
            "category": template.category
        }
        
        with open(self.templates_dir / file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_template(self, file_path: str):
        """从文件加载模板"""
        with open(self.templates_dir / file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        template = TaskTemplate(**data)
        self.templates[template.name] = template


template_manager = TemplateManager()
