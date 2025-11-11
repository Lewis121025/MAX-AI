"""PDF 操作工具：读取和生成 PDF 文档。

功能：
- 提取文本
- 创建 PDF
- 合并 PDF
- 获取 PDF 信息
"""

from __future__ import annotations

from typing import Optional, List
import base64
from io import BytesIO

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


def pdf_operations(
    operation: str,
    pdf_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    PDF 操作工具函数
    
    参数:
        operation: 操作类型 (extract_text/create/merge/split)
        pdf_path: PDF 文件路径
        **kwargs: 其他参数
    
    返回:
        操作结果
    """
    if operation == "extract_text":
        if not PYPDF2_AVAILABLE:
            return "错误: 请安装 PyPDF2: pip install PyPDF2"
        
        if not pdf_path:
            return "错误: 需要提供 pdf_path"
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_parts = []
                
                max_pages = kwargs.get("max_pages", len(reader.pages))
                for i, page in enumerate(reader.pages[:max_pages]):
                    text_parts.append(f"--- 第 {i+1} 页 ---\n")
                    text_parts.append(page.extract_text())
                    text_parts.append("\n\n")
                
                full_text = "".join(text_parts)
                
                # 限制长度
                if len(full_text) > 5000:
                    return full_text[:5000] + f"\n\n... (剩余 {len(full_text) - 5000} 字符)"
                return full_text
        
        except Exception as e:
            return f"PDF 读取错误: {e}"
    
    elif operation == "create":
        if not REPORTLAB_AVAILABLE:
            return "错误: 请安装 reportlab: pip install reportlab"
        
        output_path = kwargs.get("output_path", "output.pdf")
        title = kwargs.get("title", "Generated PDF")
        content = kwargs.get("content", ["这是一个测试 PDF 文档"])
        
        try:
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            
            # 标题
            c.setFont("Helvetica-Bold", 24)
            c.drawString(inch, height - inch, title)
            
            # 内容
            c.setFont("Helvetica", 12)
            y_position = height - 2 * inch
            
            if isinstance(content, str):
                content = content.split('\n')
            
            for line in content:
                if y_position < inch:
                    c.showPage()
                    y_position = height - inch
                c.drawString(inch, y_position, line[:80])  # 限制每行长度
                y_position -= 20
            
            c.save()
            return f"PDF 创建成功: {output_path}"
        
        except Exception as e:
            return f"PDF 创建错误: {e}"
    
    elif operation == "merge":
        if not PYPDF2_AVAILABLE:
            return "错误: 请安装 PyPDF2: pip install PyPDF2"
        
        input_paths = kwargs.get("input_paths", [])
        output_path = kwargs.get("output_path", "merged.pdf")
        
        if len(input_paths) < 2:
            return "错误: 需要至少 2 个 PDF 文件"
        
        try:
            merger = PyPDF2.PdfMerger()
            for path in input_paths:
                merger.append(path)
            
            merger.write(output_path)
            merger.close()
            return f"PDF 合并成功: {output_path}"
        
        except Exception as e:
            return f"PDF 合并错误: {e}"
    
    elif operation == "info":
        if not PYPDF2_AVAILABLE:
            return "错误: 请安装 PyPDF2: pip install PyPDF2"
        
        if not pdf_path:
            return "错误: 需要提供 pdf_path"
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                info = {
                    "页数": len(reader.pages),
                    "元数据": reader.metadata if reader.metadata else "无"
                }
                return f"PDF 信息: {info}"
        
        except Exception as e:
            return f"PDF 信息读取错误: {e}"
    
    else:
        return f"未知操作: {operation}"
