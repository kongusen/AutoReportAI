"""
诊断占位符替换双重引号问题
"""
import re

# 模拟问题场景
placeholder = "start_date"
formatted_time = "2025-09-01"

# 测试不同的 SQL 格式
test_cases = [
    ("BETWEEN '{{start_date}}' AND", "原SQL已有单引号"),
    ('BETWEEN "{{start_date}}" AND', "原SQL已有双引号"),
    ("BETWEEN {{start_date}} AND", "原SQL无引号"),
]

print("=" * 80)
print("占位符替换引号问题诊断")
print("=" * 80)

for sql, description in test_cases:
    print(f"\n测试用例: {description}")
    print(f"原始SQL: {sql}")

    # 当前代码中的正则表达式
    quoted_pattern = rf"""['"]{{{{{{placeholder}}}}}}['"]"""
    print(f"正则模式: {quoted_pattern}")
    print(f"正则模式(实际): {repr(quoted_pattern)}")

    # 检查是否匹配
    match = re.search(quoted_pattern, sql)
    print(f"是否匹配到已有引号: {match is not None}")
    if match:
        print(f"匹配内容: {match.group()}")

    # 模拟替换
    placeholder_pattern = f"{{{{{placeholder}}}}}"
    if re.search(quoted_pattern, sql):
        result = re.sub(quoted_pattern, f"'{formatted_time}'", sql)
        print(f"替换方式: 保留原引号")
    else:
        result = sql.replace(placeholder_pattern, f"'{formatted_time}'")
        print(f"替换方式: 添加引号")

    print(f"替换后SQL: {result}")

    # 检查是否有双重引号问题
    if "''" in result or '""' in result:
        print("⚠️ 发现双重引号问题!")
    else:
        print("✅ 未发现双重引号问题")

print("\n" + "=" * 80)
print("建议的修复方案:")
print("=" * 80)
print("""
问题原因:
当前正则表达式 rf\"""['"]{{{{{{placeholder}}}}}}['\"]\"""
需要正确转义花括号以匹配字面字符 {{placeholder}}

正确的正则表达式应该是:
rf"['\"]\\{{\\{{{placeholder}\\}}\\}}['\"]"

或者使用 re.escape 来转义占位符:
rf"['\"]" + re.escape(f"{{{{{placeholder}}}}}") + rf"['\"]"
""")
