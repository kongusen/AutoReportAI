"""
综合测试所有 Decimal 修复
"""
import sys
sys.path.insert(0, '/Users/shan/work/AutoReportAI/backend')

import json
from decimal import Decimal
from app.utils.json_utils import convert_decimals, convert_for_json

print("=" * 80)
print("综合 Decimal 修复测试")
print("=" * 80)

# 测试1: 基本 Decimal 转换
print("\n测试1: 基本 Decimal 转换")
test_data = {
    "amount": Decimal("999.99"),
    "quantity": Decimal("100"),
    "price": Decimal("9.99")
}
result = convert_decimals(test_data)
print(f"原始: {test_data}")
print(f"转换: {result}")
try:
    json_str = json.dumps(result)
    print(f"JSON: {json_str}")
    print("✅ 测试通过")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试2: 嵌套列表和字典
print("\n测试2: 嵌套列表和字典")
test_data = [
    {"city": "昆明", "total": Decimal("1234.56"), "count": Decimal("100")},
    {"city": "大理", "total": Decimal("789.12"), "count": Decimal("50")},
]
result = convert_decimals(test_data)
print(f"原始: {test_data}")
print(f"转换: {result}")
try:
    json_str = json.dumps(result, ensure_ascii=False)
    print(f"JSON: {json_str}")
    print("✅ 测试通过")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试3: convert_for_json - 包含日期时间
print("\n测试3: convert_for_json - 多种类型")
from datetime import datetime
from uuid import UUID

test_data = {
    "amount": Decimal("999.99"),
    "created_at": datetime(2025, 10, 24, 13, 30, 0),
    "user_id": UUID("702334d3-402e-4fc0-8ba8-153e7ad4acef"),
    "details": [
        {"value": Decimal("100.5"), "timestamp": datetime(2025, 10, 24, 12, 0, 0)}
    ]
}
result = convert_for_json(test_data)
print(f"转换: {result}")
try:
    json_str = json.dumps(result, ensure_ascii=False)
    print(f"JSON: {json_str}")
    print("✅ 测试通过")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试4: 模拟查询结果结构
print("\n测试4: 模拟查询结果")
query_result_data = [
    {
        "city": "昆明",
        "return_count": Decimal("152"),
        "total_amount": Decimal("15234.56"),
        "avg_amount": Decimal("100.23")
    },
    {
        "city": "大理",
        "return_count": Decimal("98"),
        "total_amount": Decimal("9876.54"),
        "avg_amount": Decimal("100.78")
    }
]
result = convert_decimals(query_result_data)
print(f"转换后: {result}")
try:
    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    print(f"JSON:\n{json_str}")
    print("✅ 测试通过")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试5: 验证 execution_result 结构（模拟 tasks.py 中的场景）
print("\n测试5: 模拟 execution_result 结构")
execution_result = {
    "success": True,
    "etl_results": {
        "药材类退货数量": Decimal("152"),
        "退货金额": Decimal("15234.56"),
        "排名第二的州市": [
            {"city": "大理", "count": Decimal("98")}
        ]
    },
    "time_window": {
        "start": "2025-09-01",
        "end": "2025-09-30"
    }
}
# 转换 etl_results
execution_result["etl_results"] = convert_decimals(execution_result["etl_results"])
print(f"转换后: {execution_result}")
try:
    json_str = json.dumps(execution_result, ensure_ascii=False, indent=2)
    print(f"JSON:\n{json_str}")
    print("✅ 测试通过")
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n" + "=" * 80)
print("✅ 所有测试完成")
print("=" * 80)
