"""
测试SQL生成修复
- 验证占位符格式检查
- 验证自动修复功能
"""
import sys
sys.path.insert(0, '/Users/shan/work/AutoReportAI/backend')

from app.services.application.placeholder.placeholder_service import PlaceholderApplicationService
import re

print("=" * 80)
print("SQL生成修复功能测试")
print("=" * 80)

# 创建服务实例（用于访问方法）
service = PlaceholderApplicationService(user_id="test-user")

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
        "name": "混合格式 - 部分有引号",
        "sql": "SELECT * FROM table WHERE date >= '{{start_date}}' AND date <= {{end_date}}",
        "should_have_issue": True,
        "expected_fix": "SELECT * FROM table WHERE date >= {{start_date}} AND date <= {{end_date}}",
    },
    {
        "name": "复杂SQL - 多个占位符",
        "sql": """SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM orders WHERE order_date BETWEEN '{{start_date}}' AND '{{end_date}}') AS return_ratio 
FROM orders WHERE return_status = '游客撤销' AND order_date BETWEEN '{{start_date}}' AND '{{end_date}}'""",
        "should_have_issue": True,
    },
]

print("\n测试1: SQL占位符格式验证")
print("-" * 80)
for i, test in enumerate(test_cases, 1):
    print(f"\n测试 {i}: {test['name']}")
    print(f"SQL: {test['sql'][:100]}...")
    
    issue = service._validate_sql_placeholders(test['sql'])
    
    if test['should_have_issue']:
        if issue:
            print(f"✅ 正确检测到问题: {issue}")
        else:
            print(f"❌ 应该检测到问题但没有")
    else:
        if not issue:
            print(f"✅ 正确判断无问题")
        else:
            print(f"❌ 不应该有问题但检测到: {issue}")

print("\n" + "=" * 80)
print("测试2: SQL自动修复")
print("-" * 80)
for i, test in enumerate(test_cases, 1):
    if not test.get('should_have_issue'):
        continue
        
    print(f"\n测试 {i}: {test['name']}")
    print(f"原SQL: {test['sql'][:100]}...")
    
    fixed_sql = service._fix_sql_placeholder_quotes(test['sql'])
    print(f"修复后: {fixed_sql[:100]}...")
    
    if 'expected_fix' in test:
        if fixed_sql == test['expected_fix']:
            print(f"✅ 修复结果正确")
        else:
            print(f"❌ 修复结果不符合预期")
            print(f"   期望: {test['expected_fix']}")
            print(f"   实际: {fixed_sql}")
    
    # 验证修复后是否还有问题
    issue_after_fix = service._validate_sql_placeholders(fixed_sql)
    if not issue_after_fix:
        print(f"✅ 修复后无问题")
    else:
        print(f"❌ 修复后仍有问题: {issue_after_fix}")

print("\n" + "=" * 80)
print("✅ 所有测试完成")
print("=" * 80)
