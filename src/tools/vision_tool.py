"""视觉识别工具：使用LLM理解图片内容。"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from config.settings import settings


def encode_image(image_path: str) -> tuple[str, str]:
    """将图片编码为base64并检测MIME类型。
    
    Args:
        image_path: 图片文件路径（支持绝对路径和相对路径）
        
    Returns:
        (base64_string, mime_type)
    """
    # 处理路径：支持绝对路径和相对路径
    path = Path(image_path)
    
    # 如果路径不存在，尝试作为相对路径
    if not path.exists():
        # 尝试相对于项目根目录
        project_root = Path(__file__).parent.parent.parent
        relative_path = project_root / image_path
        if relative_path.exists():
            path = relative_path
        else:
            # 尝试直接使用传入的路径（可能是绝对路径但格式问题）
            path = Path(image_path).resolve()
            if not path.exists():
                raise FileNotFoundError(f"图片文件不存在: {image_path} (尝试了: {path})")
    
    # 检测MIME类型
    suffix = path.suffix.lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    mime_type = mime_map.get(suffix, 'image/jpeg')
    
    # 读取并编码
    with open(path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    return image_data, mime_type


def analyze_image(
    image_path: str,
    question: Optional[str] = None,
) -> str:
    """使用视觉模型分析图片内容。
    
    Args:
        image_path: 图片文件路径
        question: 可选的具体问题，如果不提供则进行通用描述
        
    Returns:
        图片分析结果
        
    Examples:
        >>> analyze_image("photo.jpg")
        "这是一张海滩日落的照片..."
        
        >>> analyze_image("chart.png", "图表显示了什么趋势？")
        "根据图表，数据呈现上升趋势..."
    """
    try:
        # 清理路径（移除可能的引号）
        if isinstance(image_path, str):
            image_path = image_path.strip("'\"")
        
        # 编码图片
        image_data, mime_type = encode_image(image_path)
        
        # 构建提示词
        if question:
            prompt = question
        else:
            prompt = "请详细描述这张图片的内容，包括主要物体、场景、文字（如有）、颜色、构图等关键信息。"
        
        # 初始化视觉模型
        if not settings.openrouter_api_key:
            return "❌ 错误：未配置 OpenRouter API Key，无法使用视觉识别功能"
        
        # 临时禁用代理（避免Mihomo干扰OpenRouter API）
        import os
        old_http_proxy = os.environ.pop('HTTP_PROXY', None)
        old_https_proxy = os.environ.pop('HTTPS_PROXY', None)
        
        try:
            llm = ChatOpenAI(
                model="anthropic/claude-3.5-sonnet",  # Claude 3.5 支持视觉
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.3,
                max_tokens=1024,
                request_timeout=30,
                default_headers={
                    "HTTP-Referer": "https://maxai.cc",
                    "X-Title": "Max AI Agent - Vision"
                }
            )
            
            # 构建多模态消息
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    }
                ]
            )
            
            # 调用模型
            response = llm.invoke([message])
            
            return f"📸 图片分析结果：\n{response.content}"
        finally:
            # 恢复代理设置
            if old_http_proxy:
                os.environ['HTTP_PROXY'] = old_http_proxy
            if old_https_proxy:
                os.environ['HTTPS_PROXY'] = old_https_proxy
        
    except FileNotFoundError as e:
        return f"❌ 错误：{e}"
    except Exception as e:
        return f"❌ 图片分析失败：{type(e).__name__}: {str(e)}"


# LangChain 工具包装
if __name__ != "__main__":
    from langchain_core.tools import StructuredTool
    
    vision_analysis = StructuredTool.from_function(
        func=analyze_image,
        name="vision_analysis",
        description="""使用AI视觉模型分析图片内容。
        
适用场景：
- 识别图片中的物体、人物、场景
- 读取图片中的文字（OCR）
- 分析图表、表格、截图
- 回答关于图片的具体问题
- 描述照片、插图、示意图

输入：
- image_path（必需）：图片文件路径
- question（可选）：关于图片的具体问题

示例：
- analyze_image("screenshot.png") - 通用描述
- analyze_image("chart.jpg", "这个图表的主要趋势是什么？") - 针对性分析
        """,
    )
