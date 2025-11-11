"""Firecrawl 网页爬取工具：智能提取网页内容。"""

from __future__ import annotations

from typing import Any

from config.settings import settings


def scrape_url(url: str, formats: list[str] = None) -> str:
    """使用 Firecrawl 爬取网页内容。
    
    参数：
        url: 要爬取的网页 URL
        formats: 返回格式列表，如 ['markdown', 'html', 'text']
    
    返回：
        格式化的网页内容
    """
    if not settings.firecrawl_api_key:
        return "❌ 错误：未配置 FIRECRAWL_API_KEY，请在 .env 文件中添加"
    
    if formats is None:
        formats = ["markdown"]
    
    try:
        from firecrawl import FirecrawlApp
        
        app = FirecrawlApp(api_key=settings.firecrawl_api_key)
        
        # 爬取页面（最新 API 直接传递格式参数）
        result = app.scrape(url, formats=formats)
        
        # 格式化输出
        outputs = []
        outputs.append(f"🔗 URL: {url}\n")
        
        # 处理返回的 Document 对象
        markdown_content = None
        metadata = {}
        
        # 新版 API 返回 Document 对象，直接访问属性
        if hasattr(result, 'markdown'):
            markdown_content = result.markdown
        elif hasattr(result, 'html'):
            markdown_content = result.html
        elif isinstance(result, dict):
            # 兼容旧版 API
            data = result.get("data", result)
            markdown_content = data.get("markdown") or data.get("content") or data.get("text")
            metadata = data.get("metadata", {})
        else:
            markdown_content = str(result)
        
        # 提取元数据
        if hasattr(result, 'metadata') and result.metadata:
            metadata = result.metadata if isinstance(result.metadata, dict) else {}
        
        # 添加标题和描述（如果有）
        if metadata:
            if "title" in metadata:
                outputs.append(f"📌 标题: {metadata['title']}")
            if "description" in metadata:
                outputs.append(f"📝 描述: {metadata['description']}\n")
        
        # 添加内容
        if markdown_content:
            content = str(markdown_content)[:1000]  # 限制长度
            outputs.append("� 内容:")
            outputs.append(content)
            if len(str(markdown_content)) > 1000:
                outputs.append("\n... (内容已截断)")
        
        return "\n".join(outputs) if outputs else "⚠️ 未提取到内容"
    
    except ImportError:
        return "❌ 错误：未安装 firecrawl-py 包，请运行: pip install firecrawl-py"
    
    except Exception as e:
        return f"❌ 爬取失败: {str(e)}"


def scrape_multiple_urls(urls: list[str]) -> dict[str, Any]:
    """批量爬取多个 URL。
    
    参数：
        urls: URL 列表
    
    返回：
        包含所有爬取结果的字典
    """
    results = {}
    for url in urls:
        results[url] = scrape_url(url)
    return results
