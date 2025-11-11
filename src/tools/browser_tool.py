"""Playwright 浏览器自动化工具：模拟真实用户操作网页。

功能：
- 打开网页并截图
- 填写表单
- 点击按钮
- 提取动态内容
- 模拟滚动和等待
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import asyncio
import base64
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BrowserAutomation:
    """浏览器自动化类"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("需要安装: pip install playwright && playwright install")
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def navigate(self, url: str, wait_until: str = "networkidle") -> Dict[str, Any]:
        """
        导航到指定 URL
        
        参数:
            url: 目标网址
            wait_until: 等待条件 (load/domcontentloaded/networkidle)
        """
        await self.page.goto(url, wait_until=wait_until)
        return {
            "url": self.page.url,
            "title": await self.page.title()
        }
    
    async def screenshot(self, full_page: bool = False) -> str:
        """
        截图并返回 base64 编码
        
        参数:
            full_page: 是否截取整个页面
        """
        screenshot_bytes = await self.page.screenshot(full_page=full_page)
        return base64.b64encode(screenshot_bytes).decode()
    
    async def extract_text(self, selector: Optional[str] = None) -> str:
        """
        提取页面文本
        
        参数:
            selector: CSS 选择器，为空则提取全部
        """
        if selector:
            element = await self.page.query_selector(selector)
            if element:
                return await element.inner_text()
            return ""
        else:
            return await self.page.inner_text("body")
    
    async def click(self, selector: str, wait_after: int = 1) -> bool:
        """
        点击元素
        
        参数:
            selector: CSS 选择器
            wait_after: 点击后等待时间（秒）
        """
        try:
            await self.page.click(selector)
            await asyncio.sleep(wait_after)
            return True
        except Exception as e:
            print(f"点击失败: {e}")
            return False
    
    async def fill_form(self, fields: Dict[str, str]) -> bool:
        """
        填写表单
        
        参数:
            fields: {选择器: 值} 字典
        """
        try:
            for selector, value in fields.items():
                await self.page.fill(selector, value)
            return True
        except Exception as e:
            print(f"表单填写失败: {e}")
            return False


async def browser_automation(
    action: str,
    url: Optional[str] = None,
    selector: Optional[str] = None,
    **kwargs
) -> str:
    """
    浏览器自动化工具函数
    
    参数:
        action: 操作类型 (navigate/screenshot/extract/click/fill)
        url: 目标 URL
        selector: CSS 选择器
        **kwargs: 其他参数
    
    返回:
        操作结果的 JSON 字符串
    """
    if not PLAYWRIGHT_AVAILABLE:
        return "错误: 请安装 playwright: pip install playwright && playwright install"
    
    try:
        async with BrowserAutomation() as browser:
            if action == "navigate":
                result = await browser.navigate(url or "about:blank")
                return f"已导航到: {result['title']} ({result['url']})"
            
            elif action == "screenshot":
                if url:
                    await browser.navigate(url)
                img_base64 = await browser.screenshot(kwargs.get("full_page", False))
                return f"截图成功 (Base64 长度: {len(img_base64)})"
            
            elif action == "extract":
                if url:
                    await browser.navigate(url)
                text = await browser.extract_text(selector)
                return text[:2000]  # 限制长度
            
            elif action == "click":
                if url:
                    await browser.navigate(url)
                success = await browser.click(selector or "button")
                return "点击成功" if success else "点击失败"
            
            elif action == "fill":
                if url:
                    await browser.navigate(url)
                fields = kwargs.get("fields", {})
                success = await browser.fill_form(fields)
                return "表单填写成功" if success else "表单填写失败"
            
            else:
                return f"未知操作: {action}"
    
    except Exception as e:
        return f"浏览器自动化错误: {e}"


# 同步包装器（供工具注册表使用）
def browser_automation_sync(**kwargs) -> str:
    """同步版本的浏览器自动化"""
    return asyncio.run(browser_automation(**kwargs))
