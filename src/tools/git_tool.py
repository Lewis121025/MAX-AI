"""Git 操作工具：自动化 Git 仓库管理。

功能：
- 克隆仓库
- 提交更改
- 推送/拉取
- 分支管理
- 查看历史
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, List


def run_git_command(args: List[str], cwd: Optional[str] = None) -> tuple[bool, str]:
    """
    执行 Git 命令
    
    参数:
        args: Git 命令参数列表
        cwd: 工作目录
    
    返回:
        (成功标志, 输出内容)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    
    except subprocess.TimeoutExpired:
        return False, "命令执行超时"
    except Exception as e:
        return False, f"执行错误: {e}"


def git_operations(
    operation: str,
    repo_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    Git 操作工具函数
    
    参数:
        operation: 操作类型 (clone/status/add/commit/push/pull/branch/log)
        repo_path: 仓库路径
        **kwargs: 其他参数
    
    返回:
        操作结果
    """
    if operation == "clone":
        url = kwargs.get("url")
        target = kwargs.get("target", "./")
        if not url:
            return "错误: 需要提供 url 参数"
        
        success, output = run_git_command(["clone", url, target])
        return f"克隆{'成功' if success else '失败'}: {output}"
    
    elif operation == "status":
        success, output = run_git_command(["status"], cwd=repo_path)
        return output if success else f"错误: {output}"
    
    elif operation == "add":
        files = kwargs.get("files", ".")
        success, output = run_git_command(["add", files], cwd=repo_path)
        return f"添加{'成功' if success else '失败'}: {output}"
    
    elif operation == "commit":
        message = kwargs.get("message", "Auto commit")
        success, output = run_git_command(
            ["commit", "-m", message], 
            cwd=repo_path
        )
        return f"提交{'成功' if success else '失败'}: {output}"
    
    elif operation == "push":
        branch = kwargs.get("branch", "main")
        success, output = run_git_command(
            ["push", "origin", branch], 
            cwd=repo_path
        )
        return f"推送{'成功' if success else '失败'}: {output}"
    
    elif operation == "pull":
        success, output = run_git_command(["pull"], cwd=repo_path)
        return f"拉取{'成功' if success else '失败'}: {output}"
    
    elif operation == "branch":
        action = kwargs.get("action", "list")
        if action == "list":
            success, output = run_git_command(["branch"], cwd=repo_path)
            return output if success else f"错误: {output}"
        elif action == "create":
            name = kwargs.get("name")
            if not name:
                return "错误: 需要提供 name 参数"
            success, output = run_git_command(["branch", name], cwd=repo_path)
            return f"创建分支{'成功' if success else '失败'}: {output}"
        elif action == "switch":
            name = kwargs.get("name")
            if not name:
                return "错误: 需要提供 name 参数"
            success, output = run_git_command(["checkout", name], cwd=repo_path)
            return f"切换分支{'成功' if success else '失败'}: {output}"
    
    elif operation == "log":
        limit = kwargs.get("limit", 10)
        success, output = run_git_command(
            ["log", f"-{limit}", "--oneline"], 
            cwd=repo_path
        )
        return output if success else f"错误: {output}"
    
    else:
        return f"未知操作: {operation}"
