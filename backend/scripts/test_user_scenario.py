"""
测试用户报告的具体场景
"""
import sys
sys.path.insert(0, '/Users/shan/work/AutoReportAI/backend')

from app.utils.sql_placeholder_utils import SqlPlaceholderReplacer

# 用户报告的具体SQL
user_sql = "SELECT city, COUNT(*) AS return_count FROM returns WHERE category = '药材' AND return_date BETWEEN '{{start_date}}' AND '2025-09-30' GROUP BY city ORDER BY return_count DESC LIMIT 1 OFFSET 1"

time_context = {
    "data_start_time": "2025-09-01",
}

print("=" * 80)
print("用户场景测试 - 药材类退货申请排名第二的州市")
print("=" * 80)
print(f"\n原始SQL:\n{user_sql}")

result = SqlPlaceholderReplacer.replace_time_placeholders(user_sql, time_context)

print(f"\n替换后SQL:\n{result}")

# 检查问题
if "''" in result:
    print("\n❌ 发现双重引号问题: ''")
    # 找出问题位置
    import re
    matches = re.finditer(r"''", result)
    for match in matches:
        start = max(0, match.start() - 20)
        end = min(len(result), match.end() + 20)
        print(f"   位置 {match.start()}: ...{result[start:end]}...")
else:
    print("\n✅ 未发现双重引号问题!")

# 尝试验证SQL语法（基本检查）
if "BETWEEN '2025-09-01' AND" in result:
    print("✅ 日期格式正确!")
else:
    print(f"⚠️ 日期格式可能有问题，请检查")

print("\n" + "=" * 80)
