"""文件系统操作工具：安全的文件读写和管理。

功能：
- 读取文件内容
- 写入文件
- 列出目录
- 搜索文件
- 文件复制/移动/删除
"""

from __future__ import annotations

import os
import shutil
import json
from pathlib import Path
from typing import List, Optional, Dict, Any


class FileSystemTool:
    """文件系统操作工具"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化文件系统工具
        
        参数:
            base_dir: 基础目录（安全限制），默认为当前目录
        """
        self.base_dir = Path(base_dir or os.getcwd())
    
    def _is_safe_path(self, path: Path) -> bool:
        """检查路径是否在安全范围内"""
        try:
            resolved = path.resolve()
            return resolved.is_relative_to(self.base_dir)
        except (ValueError, OSError):
            return False
    
    def read_file(self, file_path: str, encoding: str = "utf-8") -> str:
        """
        读取文件内容
        
        参数:
            file_path: 文件路径（可以是绝对路径或相对于 base_dir 的路径）
            encoding: 文件编码
        """
        # 处理绝对路径和相对路径
        file_path_obj = Path(file_path)
        if file_path_obj.is_absolute():
            # 如果是绝对路径，直接使用
            path = file_path_obj
            # 检查是否在允许的目录范围内（项目目录或上传目录）
            # __file__ 是 src/tools/file_tool.py，所以 parent.parent.parent 是项目根目录
            # src/tools -> src -> 项目根目录
            project_root = Path(__file__).parent.parent.parent.resolve()
            upload_dir = project_root / 'data' / 'uploads'
            
            try:
                resolved_path = path.resolve()
                resolved_upload = upload_dir.resolve()
                resolved_project = project_root.resolve()
                
                # 检查路径是否在项目目录或上传目录内（使用字符串比较，更可靠）
                path_str = str(resolved_path).lower().replace('\\', '/')
                upload_str = str(resolved_upload).lower().replace('\\', '/')
                project_str = str(resolved_project).lower().replace('\\', '/')
                
                # 调试信息
                print(f"  🔍 文件路径安全检查:")
                print(f"     文件路径: {resolved_path}")
                print(f"     上传目录: {resolved_upload}")
                print(f"     项目目录: {resolved_project}")
                print(f"     路径字符串: {path_str}")
                print(f"     上传目录字符串: {upload_str}")
                print(f"     项目目录字符串: {project_str}")
                print(f"     在上传目录内: {path_str.startswith(upload_str)}")
                print(f"     在项目目录内: {path_str.startswith(project_str)}")
                
                if not (path_str.startswith(upload_str) or path_str.startswith(project_str)):
                    print(f"  ❌ 路径安全检查失败: 文件不在允许的目录内")
                    return f"❌ 抱歉，无法访问该文件。出于安全考虑，系统不允许访问指定路径下的文件。请确保文件位于允许的目录范围内，或尝试将文件移动到安全的工作目录后重试。\n\n文件路径: {resolved_path}\n允许的目录: {resolved_upload} 或 {resolved_project}"
            except (ValueError, OSError) as e:
                print(f"  ❌ 路径解析错误: {e}")
                return f"❌ 抱歉，无法访问该文件。路径解析错误: {e}\n\n请确保文件路径正确，或重新上传文件。"
        else:
            # 如果是相对路径，相对于 base_dir
            path = self.base_dir / file_path
            if not self._is_safe_path(path):
                return f"⚠️ 无法访问该文件\n\n系统出于安全考虑，不允许访问指定路径下的文件。建议您：\n\n检查文件路径是否正确\n确保文件具有适当的访问权限\n尝试将文件移动到允许访问的目录下\n如需继续操作，请重新上传文件或提供其他可访问的文件路径。"
        
        if not path.exists():
            return f"错误: 文件不存在 {file_path}"
        
        try:
            # 根据文件扩展名选择不同的读取方式
            file_ext = path.suffix.lower()
            
            # 处理 docx 文件
            if file_ext == '.docx':
                try:
                    from docx import Document
                    doc = Document(path)
                    content_parts = []
                    for para in doc.paragraphs:
                        if para.text.strip():
                            content_parts.append(para.text)
                    content = '\n'.join(content_parts)
                    
                    # 限制返回长度
                    if len(content) > 10000:
                        return content[:10000] + f"\n\n... (剩余 {len(content) - 10000} 字符)"
                    return content if content else "文件内容为空"
                except ImportError:
                    return "错误: 需要安装 python-docx 库来读取 .docx 文件。请运行: pip install python-docx"
                except Exception as e:
                    return f"读取 .docx 文件错误: {e}"
            
            # 处理普通文本文件（txt, py, js, html, css, json, md 等）
            elif file_ext in ['.txt', '.py', '.js', '.html', '.css', '.json', '.md', '.csv', '.log', '.doc']:
                # 尝试多种编码方式读取文本文件
                encodings_to_try = [encoding, 'utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']
                content = None
                last_error = None
                
                for enc in encodings_to_try:
                    try:
                        with open(path, 'r', encoding=enc) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError as e:
                        last_error = e
                        continue
                    except Exception as e:
                        last_error = e
                        continue
                
                if content is None:
                    return f"读取错误: 无法使用任何编码读取文件。最后错误: {last_error}"
                
                # 限制返回长度
                if len(content) > 10000:
                    return content[:10000] + f"\n\n... (剩余 {len(content) - 10000} 字符)"
                return content
            
            # 对于其他文件类型，尝试以二进制模式读取并显示基本信息
            else:
                try:
                    with open(path, 'rb') as f:
                        file_size = len(f.read())
                    return f"文件类型: {file_ext}\n文件大小: {file_size} 字节\n\n注意: 此文件类型需要特殊工具处理。对于 .docx 文件，请确保已安装 python-docx 库。"
                except Exception as e:
                    return f"读取错误: {e}"
        
        except Exception as e:
            return f"读取错误: {e}"
    
    def write_file(self, file_path: str, content: str, encoding: str = "utf-8") -> str:
        """
        写入文件
        
        参数:
            file_path: 文件路径
            content: 文件内容
            encoding: 文件编码
        """
        path = self.base_dir / file_path
        
        if not self._is_safe_path(path):
            return f"错误: 路径不安全 {file_path}"
        
        try:
            # 创建目录
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            
            return f"成功写入: {file_path} ({len(content)} 字符)"
        
        except Exception as e:
            return f"写入错误: {e}"
    
    def list_directory(self, dir_path: str = ".") -> List[Dict[str, Any]]:
        """
        列出目录内容
        
        参数:
            dir_path: 目录路径
        """
        path = self.base_dir / dir_path
        
        if not self._is_safe_path(path):
            return [{"error": f"路径不安全 {dir_path}"}]
        
        if not path.exists() or not path.is_dir():
            return [{"error": f"目录不存在 {dir_path}"}]
        
        try:
            items = []
            for item in path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": item.stat().st_mtime
                })
            
            return sorted(items, key=lambda x: (x["type"] != "dir", x["name"]))
        
        except Exception as e:
            return [{"error": str(e)}]
    
    def search_files(self, pattern: str, dir_path: str = ".") -> List[str]:
        """
        搜索文件
        
        参数:
            pattern: 文件名模式 (支持 * 通配符)
            dir_path: 搜索目录
        """
        path = self.base_dir / dir_path
        
        if not self._is_safe_path(path):
            return [f"错误: 路径不安全 {dir_path}"]
        
        try:
            matches = list(path.rglob(pattern))
            return [str(m.relative_to(self.base_dir)) for m in matches[:100]]  # 限制 100 个
        
        except Exception as e:
            return [f"搜索错误: {e}"]
    
    def delete_file(self, file_path: str) -> str:
        """删除文件"""
        path = self.base_dir / file_path
        
        if not self._is_safe_path(path):
            return f"错误: 路径不安全 {file_path}"
        
        try:
            if path.is_file():
                path.unlink()
                return f"成功删除: {file_path}"
            elif path.is_dir():
                shutil.rmtree(path)
                return f"成功删除目录: {file_path}"
            else:
                return f"错误: 路径不存在 {file_path}"
        
        except Exception as e:
            return f"删除错误: {e}"
    
    def copy_file(self, src: str, dst: str) -> str:
        """复制文件"""
        src_path = self.base_dir / src
        dst_path = self.base_dir / dst
        
        if not (self._is_safe_path(src_path) and self._is_safe_path(dst_path)):
            return "错误: 路径不安全"
        
        try:
            if src_path.is_file():
                shutil.copy2(src_path, dst_path)
            elif src_path.is_dir():
                shutil.copytree(src_path, dst_path)
            else:
                return f"错误: 源路径不存在 {src}"
            
            return f"成功复制: {src} -> {dst}"
        
        except Exception as e:
            return f"复制错误: {e}"


def file_operations(
    operation: str,
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    **kwargs
) -> str:
    """
    文件系统操作工具函数
    
    参数:
        operation: 操作类型 (read/write/list/search/delete/copy)
        file_path: 文件路径
        content: 文件内容 (仅 write 操作)
        **kwargs: 其他参数
    
    返回:
        操作结果字符串
    """
    base_dir = kwargs.get("base_dir", os.getcwd())
    fs = FileSystemTool(base_dir)
    
    try:
        if operation == "read":
            if not file_path:
                return "错误: 需要提供 file_path"
            return fs.read_file(file_path, kwargs.get("encoding", "utf-8"))
        
        elif operation == "write":
            if not file_path or content is None:
                return "错误: 需要提供 file_path 和 content"
            return fs.write_file(file_path, content, kwargs.get("encoding", "utf-8"))
        
        elif operation == "list":
            dir_path = file_path or "."
            items = fs.list_directory(dir_path)
            return json.dumps(items, ensure_ascii=False, indent=2)
        
        elif operation == "search":
            if not file_path:
                return "错误: 需要提供 pattern (作为 file_path)"
            matches = fs.search_files(file_path, kwargs.get("dir_path", "."))
            return "\n".join(matches)
        
        elif operation == "delete":
            if not file_path:
                return "错误: 需要提供 file_path"
            return fs.delete_file(file_path)
        
        elif operation == "copy":
            src = file_path
            dst = kwargs.get("destination")
            if not src or not dst:
                return "错误: 需要提供 file_path 和 destination"
            return fs.copy_file(src, dst)
        
        else:
            return f"未知操作: {operation}"
    
    except Exception as e:
        return f"文件操作错误: {e}"
