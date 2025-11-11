"""真实用户复杂使用场景测试

这个测试套件模拟真实用户的复杂交互场景，包括：
1. 多轮上下文对话
2. 复杂任务执行
3. 会话管理和切换
4. 导出和快捷键功能
5. 错误恢复和重试
"""

import pytest
import asyncio
import time
from playwright.async_api import async_playwright, expect
from pathlib import Path
import sys
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.mark.asyncio
@pytest.mark.user_scenario
class TestRealUserScenarios:
    """真实用户场景测试"""
    
    @pytest.fixture
    async def browser_context(self):
        """创建浏览器上下文"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=100)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN'
            )
            page = await context.new_page()
            
            yield page
            
            await context.close()
            await browser.close()
    
    async def test_scenario_1_multi_turn_conversation(self, browser_context):
        """场景1：多轮上下文对话 - 数据分析师工作流
        
        模拟一个数据分析师使用AI助手完成复杂数据分析任务：
        1. 询问如何分析销售数据
        2. 请求生成Python代码
        3. 基于前面的代码询问优化建议
        4. 请求添加可视化功能
        """
        page = browser_context
        await page.goto('http://localhost:5000')
        
        await expect(page.locator('.welcome-message')).to_be_visible()
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        
        query_1 = "我有一份销售数据CSV文件，包含日期、产品、销量和金额列。如何进行数据分析？"
        await input_box.fill(query_1)
        await send_btn.click()
        
        await page.wait_for_selector('.message-agent', timeout=30000)
        await asyncio.sleep(3)
        
        query_2 = "请帮我生成Python代码来读取CSV并计算每个产品的总销量"
        await input_box.fill(query_2)
        await send_btn.click()
        
        await page.wait_for_selector('.message-agent:nth-of-type(2)', timeout=30000)
        await asyncio.sleep(3)
        
        query_3 = "这段代码如何优化性能？如果数据量很大怎么办？"
        await input_box.fill(query_3)
        await send_btn.click()
        
        await page.wait_for_selector('.message-agent:nth-of-type(3)', timeout=30000)
        await asyncio.sleep(2)
        
        query_4 = "请在前面的代码基础上添加柱状图可视化"
        await input_box.fill(query_4)
        await send_btn.click()
        
        await page.wait_for_selector('.message-agent:nth-of-type(4)', timeout=30000)
        await asyncio.sleep(2)
        
        messages = await page.locator('.message').all()
        assert len(messages) >= 8
        
        await page.screenshot(path='test_results/scenario_1_multi_turn.png')
    
    async def test_scenario_2_research_workflow(self, browser_context):
        """场景2：研究工作流 - 学术研究助手
        
        模拟研究人员使用AI助手进行文献调研：
        1. 搜索特定主题的最新研究
        2. 询问关键技术细节
        3. 请求对比分析
        4. 生成研究总结
        """
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        
        query_1 = "搜索2024年大语言模型（LLM）的最新进展和突破"
        await input_box.fill(query_1)
        await send_btn.click()
        
        await page.wait_for_selector('.node-card.executor', timeout=60000)
        await asyncio.sleep(5)
        
        query_2 = "GPT-4和Claude 3在架构上有什么主要区别？"
        await input_box.fill(query_2)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        query_3 = "对比这两个模型在推理能力、代码生成和多语言支持方面的表现"
        await input_box.fill(query_3)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        query_4 = "基于以上信息，总结当前LLM技术的三个主要发展方向"
        await input_box.fill(query_4)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        messages = await page.locator('.message').all()
        assert len(messages) >= 8
        
        await page.screenshot(path='test_results/scenario_2_research.png')
    
    async def test_scenario_3_code_debugging_workflow(self, browser_context):
        """场景3：代码调试工作流 - 开发者助手
        
        模拟开发者调试代码的完整流程：
        1. 提供错误代码
        2. 询问错误原因
        3. 请求修复建议
        4. 验证修复后的代码
        """
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        
        buggy_code = """我的Python代码有问题：
```python
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

result = calculate_average([])
print(result)
```
为什么会报错？"""
        
        await input_box.fill(buggy_code)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        query_2 = "如何修改这个函数使其能处理空列表的情况？"
        await input_box.fill(query_2)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        query_3 = "请给出完整的修复后代码，并添加类型注解和文档字符串"
        await input_box.fill(query_3)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        query_4 = "帮我运行修复后的代码测试几个案例"
        await input_box.fill(query_4)
        await send_btn.click()
        
        await asyncio.sleep(8)
        
        messages = await page.locator('.message').all()
        assert len(messages) >= 8
        
        await page.screenshot(path='test_results/scenario_3_debugging.png')
    
    async def test_scenario_4_session_management(self, browser_context):
        """场景4：会话管理 - 多任务切换
        
        测试用户在多个会话间切换：
        1. 创建第一个会话（技术讨论）
        2. 创建第二个会话（数学计算）
        3. 切换回第一个会话继续对话
        4. 导出会话内容
        """
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        
        query_1 = "解释什么是RESTful API的核心原则"
        await input_box.fill(query_1)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        new_session_btn = page.locator('#btn-new-session')
        await new_session_btn.click()
        
        await asyncio.sleep(1)
        
        query_2 = "计算1到1000之间所有质数的和"
        await input_box.fill(query_2)
        await send_btn.click()
        
        await asyncio.sleep(8)
        
        query_3 = "这个计算的时间复杂度是多少？"
        await input_box.fill(query_3)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        history_items = await page.locator('.history-item').all()
        assert len(history_items) >= 2
        
        if len(history_items) >= 2:
            await history_items[0].click()
            await asyncio.sleep(2)
            
            query_4 = "RESTful API和GraphQL有什么区别？"
            await input_box.fill(query_4)
            await send_btn.click()
            
            await asyncio.sleep(5)
        
        export_btn = page.locator('#btn-export')
        await export_btn.click()
        
        await asyncio.sleep(1)
        
        await page.screenshot(path='test_results/scenario_4_sessions.png')
    
    async def test_scenario_5_complex_computation(self, browser_context):
        """场景5：复杂计算任务 - 数据科学工作流
        
        测试复杂的数据处理和计算：
        1. 请求生成模拟数据
        2. 进行统计分析
        3. 可视化结果
        4. 导出分析报告
        """
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        
        query_1 = "生成1000个符合正态分布的随机数据点（均值100，标准差15）"
        await input_box.fill(query_1)
        await send_btn.click()
        
        await asyncio.sleep(8)
        
        query_2 = "计算这些数据的均值、中位数、标准差和四分位数"
        await input_box.fill(query_2)
        await send_btn.click()
        
        await asyncio.sleep(8)
        
        query_3 = "检测数据中的异常值（使用IQR方法）"
        await input_box.fill(query_3)
        await send_btn.click()
        
        await asyncio.sleep(8)
        
        query_4 = "创建直方图和箱线图展示数据分布"
        await input_box.fill(query_4)
        await send_btn.click()
        
        await asyncio.sleep(10)
        
        messages = await page.locator('.message').all()
        assert len(messages) >= 8
        
        executor_outputs = await page.locator('.executor-output').all()
        assert len(executor_outputs) >= 2
        
        await page.screenshot(path='test_results/scenario_5_computation.png')
    
    async def test_scenario_6_error_recovery(self, browser_context):
        """场景6：错误恢复 - 处理失败和重试
        
        测试系统如何处理错误和恢复：
        1. 发送可能失败的请求
        2. 观察错误处理
        3. 修改请求重试
        4. 验证恢复机制
        """
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        
        query_1 = "搜索一个不存在的网站：http://this-website-definitely-does-not-exist-12345.com"
        await input_box.fill(query_1)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        query_2 = "运行这段会报错的代码：print(undefined_variable)"
        await input_box.fill(query_2)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        query_3 = "修正上面的代码并重新运行"
        await input_box.fill(query_3)
        await send_btn.click()
        
        await asyncio.sleep(5)
        
        messages = await page.locator('.message').all()
        assert len(messages) >= 6
        
        await page.screenshot(path='test_results/scenario_6_error_recovery.png')
    
    async def test_scenario_7_keyboard_shortcuts(self, browser_context):
        """场景7：快捷键操作 - 高效用户体验
        
        测试各种快捷键功能：
        1. Ctrl+Enter 发送消息
        2. Ctrl+K 清空对话
        3. Ctrl+/ 查看帮助
        4. 主题切换
        """
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        
        await input_box.fill("测试快捷键功能")
        await page.keyboard.press('Control+Enter')
        
        await asyncio.sleep(3)
        
        await input_box.fill("第二条消息")
        await page.keyboard.press('Control+Enter')
        
        await asyncio.sleep(3)
        
        theme_btn = page.locator('#btn-theme')
        await theme_btn.click()
        await asyncio.sleep(1)
        
        body_theme = await page.evaluate('document.body.getAttribute("data-theme")')
        assert body_theme in ['light', 'dark']
        
        await theme_btn.click()
        await asyncio.sleep(1)
        
        help_btn = page.locator('#btn-help')
        await help_btn.click()
        await asyncio.sleep(2)
        
        await page.keyboard.press('Control+KeyK')
        await asyncio.sleep(2)
        
        messages = await page.locator('.message').all()
        
        await page.screenshot(path='test_results/scenario_7_shortcuts.png')
    
    async def test_scenario_8_long_conversation(self, browser_context):
        """场景8：长对话 - 上下文保持测试
        
        测试长对话中的上下文保持能力：
        1. 10轮连续对话
        2. 每轮都依赖前面的上下文
        3. 验证上下文记忆功能
        """
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        
        queries = [
            "我们来讨论Python编程。首先，什么是列表推导式？",
            "请给我一个实际例子",
            "如何在其中添加条件过滤？",
            "嵌套列表推导式怎么写？",
            "它和传统for循环相比有什么优势？",
            "性能上有多大差异？",
            "在什么情况下不应该使用列表推导式？",
            "能给我展示一个复杂的实际应用场景吗？",
            "如果数据量很大，有更好的替代方案吗？",
            "总结一下我们讨论的所有要点"
        ]
        
        for i, query in enumerate(queries):
            await input_box.fill(query)
            await send_btn.click()
            
            await asyncio.sleep(5 if i < 5 else 3)
        
        messages = await page.locator('.message').all()
        assert len(messages) >= 20
        
        last_message = await page.locator('.message-agent').last.inner_text()
        assert len(last_message) > 0
        
        await page.screenshot(path='test_results/scenario_8_long_conversation.png')


@pytest.mark.asyncio
@pytest.mark.user_scenario
@pytest.mark.performance
class TestUserExperienceMetrics:
    """用户体验指标测试"""
    
    @pytest.fixture
    async def browser_context(self):
        """创建浏览器上下文"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            yield page
            
            await context.close()
            await browser.close()
    
    async def test_page_load_time(self, browser_context):
        """测试页面加载时间"""
        page = browser_context
        
        start_time = time.time()
        await page.goto('http://localhost:5000')
        await page.wait_for_load_state('networkidle')
        load_time = time.time() - start_time
        
        assert load_time < 3.0
        print(f"\n页面加载时间: {load_time:.2f}秒")
    
    async def test_input_responsiveness(self, browser_context):
        """测试输入响应速度"""
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        
        start_time = time.time()
        await input_box.fill("测试输入响应")
        response_time = time.time() - start_time
        
        assert response_time < 0.5
        print(f"\n输入响应时间: {response_time:.3f}秒")
    
    async def test_send_button_enable_time(self, browser_context):
        """测试发送按钮启用时间"""
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        
        is_disabled = await send_btn.is_disabled()
        assert is_disabled
        
        start_time = time.time()
        await input_box.fill("测试")
        await page.wait_for_function(
            'document.querySelector("#btn-send").disabled === false',
            timeout=1000
        )
        enable_time = time.time() - start_time
        
        assert enable_time < 0.5
        print(f"\n按钮启用时间: {enable_time:.3f}秒")
    
    async def test_first_response_time(self, browser_context):
        """测试首次响应时间 (TTFB)"""
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        
        await input_box.fill("你好")
        
        start_time = time.time()
        await send_btn.click()
        
        await page.wait_for_selector('.message-agent', timeout=10000)
        first_response_time = time.time() - start_time
        
        assert first_response_time < 10.0
        print(f"\n首次响应时间: {first_response_time:.2f}秒")
    
    async def test_concurrent_sessions(self, browser_context):
        """测试并发会话处理"""
        page = browser_context
        await page.goto('http://localhost:5000')
        
        input_box = page.locator('#user-input')
        send_btn = page.locator('#btn-send')
        new_session_btn = page.locator('#btn-new-session')
        
        await input_box.fill("第一个会话")
        await send_btn.click()
        await asyncio.sleep(2)
        
        await new_session_btn.click()
        await asyncio.sleep(1)
        
        await input_box.fill("第二个会话")
        await send_btn.click()
        await asyncio.sleep(2)
        
        await new_session_btn.click()
        await asyncio.sleep(1)
        
        await input_box.fill("第三个会话")
        await send_btn.click()
        await asyncio.sleep(2)
        
        history_items = await page.locator('.history-item').all()
        assert len(history_items) >= 3
        print(f"\n创建了 {len(history_items)} 个会话")


@pytest.mark.asyncio
@pytest.mark.user_scenario
@pytest.mark.accessibility
class TestAccessibility:
    """可访问性测试"""
    
    @pytest.fixture
    async def browser_context(self):
        """创建浏览器上下文"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            yield page
            
            await context.close()
            await browser.close()
    
    async def test_keyboard_navigation(self, browser_context):
        """测试键盘导航"""
        page = browser_context
        await page.goto('http://localhost:5000')
        
        await page.keyboard.press('Tab')
        await asyncio.sleep(0.2)
        
        focused_element = await page.evaluate('document.activeElement.id')
        assert focused_element is not None
        
        for _ in range(10):
            await page.keyboard.press('Tab')
            await asyncio.sleep(0.1)
        
        print("\n键盘导航测试通过")
    
    async def test_aria_labels(self, browser_context):
        """测试ARIA标签"""
        page = browser_context
        await page.goto('http://localhost:5000')
        
        buttons = await page.locator('button').all()
        
        for button in buttons:
            title = await button.get_attribute('title')
            aria_label = await button.get_attribute('aria-label')
            
            assert title or aria_label or await button.inner_text()
        
        print(f"\n检查了 {len(buttons)} 个按钮的可访问性标签")
    
    async def test_responsive_design(self, browser_context):
        """测试响应式设计"""
        page = browser_context
        
        viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 768, 'height': 1024},
            {'width': 375, 'height': 667},
        ]
        
        for viewport in viewports:
            await page.set_viewport_size(viewport)
            await page.goto('http://localhost:5000')
            await asyncio.sleep(1)
            
            chat_container = page.locator('.chat-container')
            is_visible = await chat_container.is_visible()
            assert is_visible
            
            print(f"\n{viewport['width']}x{viewport['height']} 视口测试通过")


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-s",
        "-m", "user_scenario",
        "--tb=short",
        "--html=test_results/user_scenarios_report.html",
        "--self-contained-html"
    ])
