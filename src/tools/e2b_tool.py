"""E2B 代码沙盒执行工具：安全运行 Python 代码。"""

from __future__ import annotations

from typing import Any

from config.settings import settings


def execute_python_code(code: str, timeout: int = 30) -> str:
    """在 E2B 沙盒中安全执行 Python 代码。
    
    参数：
        code: 要执行的 Python 代码
        timeout: 超时时间（秒）
    
    返回：
        执行结果（包含 stdout 和 stderr）
    """
    if not settings.e2b_api_key:
        return "❌ 错误：未配置 E2B_API_KEY，请在 .env 文件中添加"
    
    try:
        from e2b_code_interpreter import Sandbox
        
        # 设置环境变量供 SDK 使用
        import os
        old_key = os.environ.get("E2B_API_KEY")
        os.environ["E2B_API_KEY"] = settings.e2b_api_key
        
        try:
            # 新版 API 创建沙盒
            sandbox = Sandbox.create()
            
            try:
                # 执行代码
                execution = sandbox.run_code(code)
                
                # 收集结果
                results = []
                
                if execution.logs and execution.logs.stdout:
                    results.append("📤 标准输出:")
                    for line in execution.logs.stdout:
                        results.append(line)  # 移除缩进，保持原始输出
                
                if execution.logs and execution.logs.stderr:
                    results.append("\n⚠️ 错误输出:")
                    for line in execution.logs.stderr:
                        results.append(line)  # 移除缩进
                
                if execution.error:
                    error_name = getattr(execution.error, 'name', 'Error')
                    error_value = getattr(execution.error, 'value', str(execution.error))
                    results.append(f"\n❌ 执行错误: {error_name}: {error_value}")
                
                if execution.results:
                    results.append("\n✅ 返回值:")
                    for result in execution.results:
                        # 提取实际值
                        value = getattr(result, 'text', getattr(result, 'value', str(result)))
                        results.append(f"  {value}")
                
                return "\n".join(results) if results else "✅ 代码执行成功（无输出）"
            
            finally:
                # 关闭沙盒（使用 kill 方法）
                try:
                    sandbox.kill()
                except:
                    pass  # 忽略关闭错误
        
        finally:
            # 恢复原有环境变量
            if old_key:
                os.environ["E2B_API_KEY"] = old_key
            elif "E2B_API_KEY" in os.environ:
                del os.environ["E2B_API_KEY"]
    
    except ImportError:
        return "❌ 错误：未安装 e2b-code-interpreter 包，请运行: pip install e2b-code-interpreter"
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f"❌ 执行失败: {str(e)}\n详情: {error_detail[:200]}"


def run_code_with_context(code: str, description: str = "") -> dict[str, Any]:
    """带描述的代码执行（用于 Planner 提取参数）。
    
    参数：
        code: 要执行的代码
        description: 代码功能描述
    
    返回：
        包含执行结果的字典
    """
    result = execute_python_code(code)
    return {
        "code": code,
        "description": description,
        "result": result,
    }
