"""Shell 命令执行工具：安全执行系统命令。

功能：
- 执行 shell 命令
- 环境变量设置
- 工作目录控制
- 超时保护
- 输出捕获
"""

from __future__ import annotations

import subprocess
import shlex
from typing import Optional, Dict


def shell_command(
    command: str,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    shell: bool = False
) -> str:
    """
    执行 shell 命令
    
    参数:
        command: 要执行的命令
        cwd: 工作目录
        env: 环境变量
        timeout: 超时时间（秒）
        shell: 是否使用 shell 模式
    
    返回:
        命令输出
    """
    try:
        # 安全检查：禁止危险命令
        dangerous = ["rm -rf", "format", "del /f", "shutdown", "reboot"]
        if any(cmd in command.lower() for cmd in dangerous):
            return "错误: 检测到危险命令，已拒绝执行"
        
        # 执行命令
        if shell:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        else:
            # 更安全的方式：不使用 shell
            args = shlex.split(command)
            result = subprocess.run(
                args,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        
        # 构建输出
        output_parts = []
        if result.stdout:
            output_parts.append(f"标准输出:\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"错误输出:\n{result.stderr}")
        if result.returncode != 0:
            output_parts.append(f"\n返回码: {result.returncode}")
        
        output = "\n".join(output_parts) if output_parts else "命令执行完成（无输出）"
        
        # 限制输出长度
        if len(output) > 2000:
            return output[:2000] + f"\n\n... (剩余 {len(output) - 2000} 字符)"
        return output
    
    except subprocess.TimeoutExpired:
        return f"错误: 命令执行超时（{timeout}秒）"
    except FileNotFoundError:
        return f"错误: 命令不存在: {command}"
    except Exception as e:
        return f"命令执行错误: {e}"


def run_python_script(
    script_path: str,
    args: Optional[list] = None,
    **kwargs
) -> str:
    """运行 Python 脚本"""
    cmd_parts = ["python", script_path]
    if args:
        cmd_parts.extend(args)
    
    return shell_command(" ".join(cmd_parts), **kwargs)


def run_npm_command(
    command: str,
    cwd: Optional[str] = None,
    **kwargs
) -> str:
    """运行 NPM 命令"""
    return shell_command(f"npm {command}", cwd=cwd, **kwargs)
