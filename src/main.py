"""命令行主程序：支持文本和多模态输入。"""

from __future__ import annotations

import argparse
import base64
import sys
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

from langchain_core.messages import HumanMessage

from orchestrator.graph import create_graph
from agent.state import init_state


def load_image(image_path: str) -> str | None:
    """加载图像并转换为 Base64。
    
    参数：
        image_path: 图像文件路径
    
    返回：
        Base64 编码的图像，或 None（如果失败）
    """
    if not Image:
        print("⚠️ PIL 未安装，无法加载图像。请运行: pip install pillow")
        return None
    
    try:
        img_path = Path(image_path)
        if not img_path.exists():
            print(f"❌ 图像文件不存在: {image_path}")
            return None
        
        with Image.open(img_path) as img:
            # 限制大小（避免过大）
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换为 JPEG 并编码
            buffer = BytesIO()
            img.convert("RGB").save(buffer, format="JPEG", quality=85)
            img_bytes = buffer.getvalue()
            
            return base64.b64encode(img_bytes).decode("utf-8")
    
    except Exception as e:
        print(f"❌ 图像加载失败: {e}")
        return None


def run_interactive():
    """交互式模式：持续对话。"""
    print("🤖 Max AI Agent 启动（输入 'exit' 退出）")
    print("=" * 60)
    
    graph = create_graph()
    
    while True:
        try:
            user_input = input("\n👤 你: ").strip()
            
            if user_input.lower() in ["exit", "quit", "q"]:
                print("👋 再见！")
                break
            
            if not user_input:
                continue
            
            # 检查是否包含图像路径（简单实现）
            images = []
            if user_input.startswith("[img:"):
                # 格式: [img:path/to/image.jpg] 描述文本
                parts = user_input.split("]", 1)
                img_path = parts[0][5:].strip()
                user_input = parts[1].strip() if len(parts) > 1 else "请分析这张图片"
                
                img_base64 = load_image(img_path)
                if img_base64:
                    images.append(img_base64)
            
            # 初始化状态
            state = init_state(user_input, images)
            
            print("\n" + "=" * 60)
            print("🚀 开始执行任务...")
            print("=" * 60)
            
            # FastAgent 执行
            result = graph.invoke(state)
            
            # 显示最终答案
            final_answer = result.get("final_answer", "")
            print(f"\n💬 AI: {final_answer}")
            
            # 显示性能指标
            total_time = result.get("total_time_ms", 0)
            llm_calls = result.get("llm_calls", 0)
            success_rate = result.get("success_rate", "N/A")
            
            print(f"\n📊 性能: {total_time}ms | LLM: {llm_calls}次 | 成功率: {success_rate}")
            
            print("\n" + "=" * 60)
            print("✅ 任务完成")
        
        except KeyboardInterrupt:
            print("\n\n⏸️ 任务中断")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


def run_once(query: str, image_path: str | None = None):
    """单次执行模式。
    
    参数：
        query: 用户查询
        image_path: 可选的图像路径
    """
    images = []
    if image_path:
        img_base64 = load_image(image_path)
        if img_base64:
            images.append(img_base64)
    
    state = init_state(query, images)
    graph = create_graph()
    
    print("🚀 执行任务...")
    print("=" * 60)
    
    # FastAgent 执行
    result = graph.invoke(state)
    
    print(f"\n最终答案:\n{result.get('final_answer', '')}")
    print(f"\n性能: {result.get('total_time_ms', 0)}ms | LLM: {result.get('llm_calls', 0)}次")
    print("\n" + "=" * 60)
    print("✅ 完成")
    
    return result


def main():
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="Max AI Agent - 智能任务执行助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 交互模式
  python src/main.py

  # 单次查询
  python src/main.py --query "搜索最新的 AI 新闻"

  # 带图像的查询
  python src/main.py --query "分析这张图片" --image path/to/image.jpg
        """,
    )
    
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="单次查询（不提供则进入交互模式）"
    )
    
    parser.add_argument(
        "-i", "--image",
        type=str,
        help="图像路径（可选）"
    )
    
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="禁用流式输出"
    )
    
    args = parser.parse_args()
    
    # 检查配置
    from config.settings import settings
    if not settings.openrouter_api_key:
        print("⚠️ 警告: OPENROUTER_API_KEY 未配置")
        print("请在 .env 文件中设置 OPENROUTER_API_KEY")
        sys.exit(1)
    
    # 执行模式选择
    if args.query:
        run_once(args.query, args.image)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
