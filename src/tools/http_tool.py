"""HTTP 客户端工具：发送 HTTP 请求和处理响应。

功能：
- GET/POST/PUT/DELETE 请求
- 自定义请求头
- JSON/表单数据
- 文件上传
- 响应解析
"""

from __future__ import annotations

import json
from typing import Optional, Dict, Any

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


def http_client(
    method: str,
    url: str,
    **kwargs
) -> str:
    """
    HTTP 客户端工具函数
    
    参数:
        method: HTTP 方法 (GET/POST/PUT/DELETE)
        url: 请求 URL
        **kwargs: 其他参数
            - headers: 请求头字典
            - params: URL 参数
            - json: JSON 数据
            - data: 表单数据
            - timeout: 超时时间（秒）
    
    返回:
        响应内容
    """
    if not HTTPX_AVAILABLE:
        return "错误: 请安装 httpx: pip install httpx"
    
    try:
        method = method.upper()
        headers = kwargs.get("headers", {})
        params = kwargs.get("params", {})
        json_data = kwargs.get("json")
        form_data = kwargs.get("data")
        timeout = kwargs.get("timeout", 30)
        
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                response = client.get(url, headers=headers, params=params)
            elif method == "POST":
                if json_data:
                    response = client.post(url, headers=headers, json=json_data)
                else:
                    response = client.post(url, headers=headers, data=form_data)
            elif method == "PUT":
                if json_data:
                    response = client.put(url, headers=headers, json=json_data)
                else:
                    response = client.put(url, headers=headers, data=form_data)
            elif method == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return f"不支持的 HTTP 方法: {method}"
            
            # 构建结果
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url)
            }
            
            # 尝试解析 JSON
            try:
                result["json"] = response.json()
            except:
                result["text"] = response.text[:1000]  # 限制长度
            
            return json.dumps(result, ensure_ascii=False, indent=2)
    
    except httpx.TimeoutException:
        return "错误: 请求超时"
    except httpx.HTTPError as e:
        return f"HTTP 错误: {e}"
    except Exception as e:
        return f"请求错误: {e}"


def api_call(
    url: str,
    method: str = "GET",
    **kwargs
) -> str:
    """便捷的 API 调用函数"""
    return http_client(method, url, **kwargs)
