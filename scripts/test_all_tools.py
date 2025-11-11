"""测试所有工具的 API 连接。"""

import sys
sys.path.insert(0, 'src')

from config.settings import settings

print("=" * 60)
print("🧪 测试所有工具 API 连接")
print("=" * 60)

# 1. 测试 Tavily 搜索
print("\n1️⃣ 测试 Tavily 搜索工具...")
try:
    from tools.tavily_tool import tavily_search
    result = tavily_search("Python programming", max_results=2)
    if "错误" in result or "未配置" in result:
        print(f"   ❌ {result}")
    else:
        print(f"   ✅ 成功！返回 {len(result)} 字符")
        print(f"   预览: {result[:150]}...")
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 2. 测试 E2B 代码执行
print("\n2️⃣ 测试 E2B 代码执行工具...")
try:
    from tools.e2b_tool import execute_python_code
    test_code = "print('Hello from E2B!')\nresult = 2 + 2\nresult"
    result = execute_python_code(test_code, timeout=10)
    if "错误" in result or "未配置" in result:
        print(f"   ❌ {result}")
    else:
        print(f"   ✅ 成功！")
        print(f"   结果: {result[:200]}")
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 3. 测试 Firecrawl 网页抓取
print("\n3️⃣ 测试 Firecrawl 网页抓取工具...")
try:
    from tools.firecrawl_tool import scrape_url
    result = scrape_url("https://example.com")
    if "错误" in result or "未配置" in result:
        print(f"   ❌ {result}")
    else:
        print(f"   ✅ 成功！返回 {len(result)} 字符")
        print(f"   预览: {result[:150]}...")
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 4. 测试 Weaviate 连接
print("\n4️⃣ 测试 Weaviate 向量数据库...")
try:
    from memory.weaviate_client import get_weaviate_client
    client = get_weaviate_client()
    # 尝试创建 schema
    client.create_schema()
    print("   ✅ Weaviate 连接成功！")
except Exception as e:
    print(f"   ⚠️ Weaviate 错误: {e}")

print("\n" + "=" * 60)
print("✅ 测试完成！")
print("=" * 60)
