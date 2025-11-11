"""图像处理工具：使用 Pillow 进行图像操作。

功能：
- 调整大小
- 裁剪
- 旋转
- 滤镜效果
- 格式转换
- 添加文字/水印
"""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Optional, Tuple

try:
    from PIL import Image, ImageFilter, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def image_processing(
    operation: str,
    image_data: Optional[str] = None,
    image_path: Optional[str] = None,
    **kwargs
) -> str:
    """
    图像处理工具函数
    
    参数:
        operation: 操作类型 (resize/crop/rotate/filter/convert/text)
        image_data: Base64 编码的图像数据
        image_path: 图像文件路径
        **kwargs: 其他参数
    
    返回:
        处理后的图像 Base64 或结果描述
    """
    if not PIL_AVAILABLE:
        return "错误: 请安装 Pillow: pip install Pillow"
    
    try:
        # 加载图像
        if image_data:
            img_bytes = base64.b64decode(image_data)
            img = Image.open(BytesIO(img_bytes))
        elif image_path:
            img = Image.open(image_path)
        else:
            return "错误: 需要提供 image_data 或 image_path"
        
        # 执行操作
        if operation == "resize":
            width = kwargs.get("width", 800)
            height = kwargs.get("height", 600)
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            result_msg = f"调整大小为 {width}x{height}"
        
        elif operation == "crop":
            box = kwargs.get("box", (0, 0, img.width // 2, img.height // 2))
            img = img.crop(box)
            result_msg = f"裁剪区域 {box}"
        
        elif operation == "rotate":
            angle = kwargs.get("angle", 90)
            img = img.rotate(angle, expand=True)
            result_msg = f"旋转 {angle} 度"
        
        elif operation == "filter":
            filter_type = kwargs.get("filter_type", "blur")
            if filter_type == "blur":
                img = img.filter(ImageFilter.BLUR)
            elif filter_type == "sharpen":
                img = img.filter(ImageFilter.SHARPEN)
            elif filter_type == "edge":
                img = img.filter(ImageFilter.FIND_EDGES)
            result_msg = f"应用 {filter_type} 滤镜"
        
        elif operation == "convert":
            mode = kwargs.get("mode", "RGB")
            img = img.convert(mode)
            result_msg = f"转换为 {mode} 模式"
        
        elif operation == "text":
            text = kwargs.get("text", "Sample Text")
            position = kwargs.get("position", (10, 10))
            draw = ImageDraw.Draw(img)
            draw.text(position, text, fill=(255, 255, 255))
            result_msg = f"添加文字: {text}"
        
        elif operation == "thumbnail":
            max_size = kwargs.get("max_size", (200, 200))
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            result_msg = f"生成缩略图 {max_size}"
        
        else:
            return f"未知操作: {operation}"
        
        # 转换为 Base64
        buffer = BytesIO()
        img.save(buffer, format=kwargs.get("format", "PNG"))
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # 如果指定了输出路径，保存文件
        output_path = kwargs.get("output_path")
        if output_path:
            img.save(output_path)
            return f"{result_msg}，已保存到 {output_path}"
        
        return f"{result_msg}，Base64 长度: {len(img_base64)}"
    
    except Exception as e:
        return f"图像处理错误: {e}"
