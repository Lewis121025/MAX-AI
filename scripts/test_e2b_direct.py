"""简单测试：直接调用 E2B 执行代码，不需要 LLM。"""

import sys
sys.path.insert(0, 'src')

from tools.e2b_tool import execute_python_code

print("=" * 60)
print("🧪 测试 E2B 代码执行（不依赖 LLM）")
print("=" * 60)

# 测试代码
code = """
# 计算 1 到 10 的平方和
total = sum(i**2 for i in range(1, 11))
print(f"1 到 10 的平方和: {total}")
total
"""

print("\n📝 执行代码:")
print(code)
print("\n" + "=" * 60)

result = execute_python_code(code)
print(result)

print("\n" + "=" * 60)
print("✅ 测试完成！")
