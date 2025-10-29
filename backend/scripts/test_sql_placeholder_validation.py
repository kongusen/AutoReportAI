"""
测试SQL占位符验证和修复逻辑（独立版本）
"""
import re
from typing import Optional

def validate_sql_placeholders(sql: str) -> Optional[str]:
    """验证SQL中的占位符格式"""
    # 检查是否有带引号的占位符: '{{...}}' 或 "{{...}}"
    quoted_placeholder_pattern = r"""['"]{{[^}]+}}['"]"""
    matches = re.findall(quoted_placeholder_pattern, sql)
    
    if matches:
        return f"发现占位符周围有引号: {matches}，这会导致双重引号错误"
    
    return None

def fix_sql_placeholder_quotes(sql: str) -> str:
    """自动修复SQL中占位符周围的引号"""
    # 移除占位符周围的引号
    fixed_sql = re.sub(r"""['"](\{\{[^}]+\}\})['"]""", r'\1', sql)
    return fixed_sql

# 测试用例
test_cases = [
    {
        "name": "正确格式 - 无引号",
        "sql": "SELECT * FROM table WHERE date BETWEEN {{start_date}} AND {{end_date}}",
        "should_have_issue": False,
    },
    {
        "name": "错误格式 - 单引号",
        "sql": "SELECT * FROM table WHERE date BETWEEN '{{start_date}}' AND '{{end_date}}'",
        "should_have_issue": True,
        "expected_fix": "SELECT * FROM table WHERE date BETWEEN {{start_date}} AND {{end_date}}",
    },
    {
        "name": "错误格式 - 双引号",
        "sql": 'SELECT * FROM table WHERE date BETWEEN "{{start_date}}" AND "{{end_date}}"',
        "should_have_issue": True,
        "expected_fix": "SELECT * FROM table WHERE date BETWEEN {{start_date}} AND {{end_date}}",
    },
    {
        "name": "混合格式",
        "sql": "SELECT * FROM table WHERE date >= '{{start_date}}' AND date <= {{end_date}}",
        "should_have_issue": True,
        "expected_fix": "SELECT * FROM table WHERE date >= {{start_date}} AND date <= {{end_date}}",
    },
    {
        "name": "实际错误SQL",
        "sql": "SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM orders WHERE order_date BETWEEN '{{start_date}}' AND '{{end_date}}') AS return_ratio FROM orders WHERE return_status = '游客撤销' AND order_date BETWEEN '{{start_date}}' AND '{{end_date}}'",
        "should_have_issue": True,
    },
]

print("=" * 80)
print("SQL占位符验证和修复测试")
print("=" * 80)

print("\n测试1: SQL占位符格式验证")
print("-" * 80)
all_passed = True

for i, test in enumerate(test_cases, 1):
    print(f"\n测试 {i}: {test['name']}")
    print(f"SQL: {test['sql'][:100]}...")
    
    issue = validate_sql_placeholders(test['sql'])
    
    if test['should_have_issue']:
        if issue:
            print(f"✅ 正确检测到问题: {issue}")
        else:
            print(f"❌ 应该检测到问题但没有")
            all_passed = False
    else:
        if not issue:
            print(f"✅ 正确判断无问题")
        else:
            print(f"❌ 不应该有问题但检测到: {issue}")
            all_passed = False

print("\n" + "=" * 80)
print("测试2: SQL自动修复")
print("-" * 80)

for i, test in enumerate(test_cases, 1):
    if not test.get('should_have_issue'):
        continue
        
    print(f"\n测试 {i}: {test['name']}")
    print(f"原SQL: {test['sql'][:80]}...")
    
    fixed_sql = fix_sql_placeholder_quotes(test['sql'])
    print(f"修复后: {fixed_sql[:80]}...")
    
    if 'expected_fix' in test:
        if fixed_sql == test['expected_fix']:
            print(f"✅ 修复结果正确")
        else:
            print(f"❌ 修复结果不符合预期")
            all_passed = False
    
    # 验证修复后是否还有问题
    issue_after_fix = validate_sql_placeholders(fixed_sql)
    if not issue_after_fix:
        print(f"✅ 修复后无问题")
    else:
        print(f"❌ 修复后仍有问题: {issue_after_fix}")
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("✅ 所有测试通过!")
else:
    print("❌ 部分测试失败!")
print("=" * 80)
