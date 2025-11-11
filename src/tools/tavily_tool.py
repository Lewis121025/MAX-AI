"""Tavily 智能搜索工具：AI 优化的网络搜索引擎。"""

from __future__ import annotations

from typing import Any, Optional

from config.settings import settings


def tavily_search(query: str, max_results: int = 5) -> str:
    """使用 Tavily API 进行智能搜索。
    
    参数：
        query: 搜索查询
        max_results: 返回结果数量
    
    返回：
        格式化的搜索结果字符串
    """
    if not settings.tavily_api_key:
        return "❌ 错误：未配置 TAVILY_API_KEY，请在 .env 文件中添加"
    
    try:
        from tavily import TavilyClient
        
        client = TavilyClient(api_key=settings.tavily_api_key)
        
        # 执行搜索
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",  # 深度搜索模式
            include_answer=True,  # 包含 AI 生成的答案
        )
        
        # 格式化结果
        results = []
        
        # 添加 AI 答案（如果有）
        if response.get("answer"):
            results.append(f"🤖 AI 总结: {response['answer']}\n")
        
        # 添加搜索结果
        results.append("📚 搜索结果:")
        for i, item in enumerate(response.get("results", []), 1):
            title = item.get("title", "无标题")
            url = item.get("url", "")
            content = item.get("content", "")[:200]  # 限制长度
            results.append(f"\n{i}. {title}")
            results.append(f"   🔗 {url}")
            results.append(f"   📄 {content}...")
        
        return "\n".join(results)
    
    except ImportError:
        return "❌ 错误：未安装 tavily-python 包，请运行: pip install tavily-python"
    
    except Exception as e:
        return f"❌ 搜索失败: {str(e)}"


def search_with_context(query: str, context: Optional[str] = None) -> dict[str, Any]:
    """带上下文的智能搜索（用于 Planner 提取参数）。
    
    参数：
        query: 搜索查询
        context: 可选的上下文信息
    
    返回：
        包含搜索结果的字典
    """
    result = tavily_search(query)
    return {
        "query": query,
        "result": result,
        "context": context,
    }
