# -*- coding: utf-8 -*-
"""FastAPI 应用启动脚本"""
import sys
import os
import io
from pathlib import Path

# 修复Windows UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("=" * 60)
print("🚀 Max AI - FastAPI 版本启动")
print("=" * 60)

# 切换到 src 目录
src_dir = Path(__file__).parent / 'src'
os.chdir(src_dir)
sys.path.insert(0, str(src_dir))

print(f"📂 工作目录: {os.getcwd()}")
print(f"� 服务地址: http://127.0.0.1:5000")
print(f"� API 文档: http://127.0.0.1:5000/docs")
print("=" * 60)
print()

import uvicorn

# 运行 FastAPI 应用（使用app对象而不是模块字符串）
try:
    # 直接导入app对象
    from fastapi_app import app
    
    # 使用已导入的app对象运行
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5000,
        log_level="info",
        access_log=True
    )
except KeyboardInterrupt:
    print("\n👋 服务已停止")
except Exception as e:
    print(f"\n❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()
