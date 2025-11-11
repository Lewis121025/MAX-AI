"""测试 OpenRouter API 连接。"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from config.settings import settings


def test_openrouter_connection():
    """测试 OpenRouter API 连接和基本调用。"""
    
    if not settings.openrouter_api_key:
        print("❌ 错误：未配置 OPENROUTER_API_KEY")
        print("💡 请在 .env 文件中添加你的 OpenRouter API 密钥")
        return False
    
    print("🔗 测试 OpenRouter API 连接...\n")
    
    try:
        llm = ChatOpenAI(
            model="meta-llama/llama-3.3-70b-instruct:free",  # Llama 4 免费版
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.7,
            request_timeout=60,
        )
        
        # 发送简单测试消息
        messages = [HumanMessage(content="你好！请用一句话介绍你自己。")]
        
        print("📤 发送测试消息: '你好！请用一句话介绍你自己。'\n")
        print("⏳ 等待模型响应（Llama 4 免费版）...\n")
        
        response = llm.invoke(messages)
        
        print("✅ API 连接成功！\n")
        print(f"📥 模型回复: {response.content}\n")
        print(f"💰 使用模型: meta-llama/llama-3.3-70b-instruct:free (Llama 4)")
        print(f"💡 提示: 这是 70B 参数的大模型，性能很强！")
        
        return True
    
    except Exception as e:
        print(f"❌ 连接失败: {e}\n")
        print("💡 可能的原因:")
        print("  1. API 密钥无效")
        print("  2. 网络连接问题")
        print("  3. OpenRouter 服务暂时不可用")
        print("  4. 模型速率限制（免费模型有并发限制）")
        return False


if __name__ == "__main__":
    print("=" * 60)
    success = test_openrouter_connection()
    print("=" * 60)
    
    if success:
        print("\n🎉 恭喜！你的 OpenRouter API 配置正确！")
        print("💡 现在可以运行: python scripts/run_demo.py")
    else:
        print("\n⚠️  请检查配置后重试")
