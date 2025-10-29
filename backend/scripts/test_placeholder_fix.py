"""
测试占位符替换修复
"""
import sys
sys.path.insert(0, '/Users/shan/work/AutoReportAI/backend')

from app.utils.sql_placeholder_utils import SqlPlaceholderReplacer

# 测试用例
test_cases = [
    {
        "name": "原SQL已有单引号",
        "sql": "SELECT * FROM table WHERE dt BETWEEN '{{start_date}}' AND '{{end_date}}'",
        "time_context": {
            "data_start_time": "2025-09-01",
            "data_end_time": "2025-09-30"
        },
        "expected": "SELECT * FROM table WHERE dt BETWEEN '2025-09-01' AND '2025-09-30'",
    },
    {
        "name": "原SQL无引号",
        "sql": "SELECT * FROM table WHERE dt BETWEEN {{start_date}} AND {{end_date}}",
        "time_context": {
            "data_start_time": "2025-09-01",
            "data_end_time": "2025-09-30"
        },
        "expected": "SELECT * FROM table WHERE dt BETWEEN '2025-09-01' AND '2025-09-30'",
    },
    {
        "name": "混合情况 - 一个有引号一个没有",
        "sql": "SELECT * FROM table WHERE dt >= '{{start_date}}' AND dt <= {{end_date}}",
        "time_context": {
            "data_start_time": "2025-09-01",
            "data_end_time": "2025-09-30"
        },
        "expected": "SELECT * FROM table WHERE dt >= '2025-09-01' AND dt <= '2025-09-30'",
    },
]

print("=" * 80)
print("占位符替换修复验证")
print("=" * 80)

all_passed = True
for i, test in enumerate(test_cases, 1):
    print(f"\n测试 {i}: {test['name']}")
    print(f"原始SQL: {test['sql']}")

    result = SqlPlaceholderReplacer.replace_time_placeholders(
        test['sql'],
        test['time_context']
    )

    print(f"结果SQL: {result}")
    print(f"期望SQL: {test['expected']}")

    # 检查双重引号
    has_double_quotes = "''" in result or '""' in result
    matches_expected = result == test['expected']

    if has_double_quotes:
        print("❌ 发现双重引号问题!")
        all_passed = False
    elif not matches_expected:
        print("❌ 结果与期望不匹配!")
        all_passed = False
    else:
        print("✅ 通过!")

print("\n" + "=" * 80)
if all_passed:
    print("✅ 所有测试通过!")
else:
    print("❌ 部分测试失败!")
print("=" * 80)
