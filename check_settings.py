"""Enhanced configuration checker with API connectivity tests."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.settings import settings

print("=" * 60)
print("🔍 Max AI Agent - 配置状态检查")
print("=" * 60)
print()

# LLM API
print("🤖 大模型 API:")
print(f"  OpenRouter: {'✅ 已配置' if settings.openrouter_api_key else '❌ 未配置'}")
print(f"  Gemini: {'✅ 已配置' if settings.gemini_api_key else '❌ 未配置'}")
print(f"  OpenAI: {'✅ 已配置' if settings.openai_api_key else '❌ 未配置'}")

# 工具 API
print("\n🔧 工具 API:")
e2b_ok = bool(settings.e2b_api_key)
tavily_ok = bool(settings.tavily_api_key)
firecrawl_ok = bool(settings.firecrawl_api_key)
zapier_ok = bool(settings.zapier_api_key)

print(f"  E2B (代码执行): {'✅ 已配置' if e2b_ok else '❌ 未配置'}")
print(f"  Tavily (搜索): {'✅ 已配置' if tavily_ok else '❌ 未配置'}")
print(f"  Firecrawl (爬虫): {'✅ 已配置' if firecrawl_ok else '❌ 未配置'}")
print(f"  Zapier (自动化): {'✅ 已配置' if zapier_ok else '❌ 未配置'}")

# 向量存储
print("\n🧠 记忆系统:")
print(f"  Weaviate URL: {'✅ 已配置' if settings.weaviate_url else '❌ 未配置'}")
print(f"  Weaviate Key: {'✅ 已配置' if settings.weaviate_api_key else '❌ 未配置'}")

# 已配置的工具
print(f"\n✅ 已配置的服务: {', '.join(settings.configured_tooling) if settings.configured_tooling else '无'}")

# 缺失的关键凭据
if settings.missing_credentials:
    print(f"\n⚠️  缺失的凭据: {', '.join(settings.missing_credentials)}")
else:
    print("\n🎉 所有关键凭据已配置！")

# API 连通性测试
print("\n" + "=" * 60)
print("� API 连通性测试 (可选)")
print("=" * 60)

test_apis = input("\n是否测试 API 连通性? (y/n): ").lower().strip()

if test_apis == 'y':
    print()
    
    # 测试 E2B
    if e2b_ok:
        print("🧪 测试 E2B API...", end=" ", flush=True)
        try:
            from e2b_code_interpreter import Sandbox
            import os
            os.environ["E2B_API_KEY"] = settings.e2b_api_key
            sandbox = Sandbox.create()
            sandbox.close()
            print("✅ 连接成功")
        except Exception as e:
            print(f"❌ 失败: {str(e)[:50]}")
    
    # 测试 Tavily
    if tavily_ok:
        print("🧪 测试 Tavily API...", end=" ", flush=True)
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.tavily_api_key)
            # 简单搜索测试
            result = client.search("test", max_results=1)
            print("✅ 连接成功")
        except Exception as e:
            print(f"❌ 失败: {str(e)[:50]}")
    
    # 测试 OpenRouter
    if settings.openrouter_api_key:
        print("🧪 测试 OpenRouter API...", end=" ", flush=True)
        try:
            import requests
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                timeout=5
            )
            if response.status_code == 200:
                print("✅ 连接成功")
            else:
                print(f"❌ 失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ 失败: {str(e)[:50]}")
    
    print("\n✅ 连通性测试完成!")

print("\n" + "=" * 60)
print("�💡 提示:")
print("  • 编辑 .env 文件来添加/修改 API 密钥")
print("  • 运行 python start_web.py 启动 Web 界面")
print("  • 查看 QUICK_START.md 了解更多信息")
print("=" * 60)


