"""
测试 Decimal 类型 JSON 序列化
"""
import json
from decimal import Decimal

# 模拟查询结果中的 Decimal 类型
def convert_decimals(obj):
    """递归转换 Decimal 为 float"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    return obj

# 测试用例
test_cases = [
    {
        "name": "单个 Decimal 值",
        "data": Decimal("123.45"),
        "expected_type": float,
    },
    {
        "name": "字典中的 Decimal",
        "data": {"amount": Decimal("999.99"), "count": Decimal("100")},
        "expected_type": dict,
    },
    {
        "name": "列表中的 Decimal",
        "data": [
            {"city": "昆明", "amount": Decimal("1234.56")},
            {"city": "大理", "amount": Decimal("789.12")},
        ],
        "expected_type": list,
    },
    {
        "name": "嵌套结构",
        "data": {
            "summary": {"total": Decimal("5000.00"), "avg": Decimal("250.50")},
            "details": [
                {"name": "A", "value": Decimal("100.5")},
                {"name": "B", "value": Decimal("200.3")},
            ]
        },
        "expected_type": dict,
    },
]

print("=" * 80)
print("Decimal 类型 JSON 序列化测试")
print("=" * 80)

all_passed = True
for i, test in enumerate(test_cases, 1):
    print(f"\n测试 {i}: {test['name']}")
    print(f"原始数据类型: {type(test['data'])}")
    print(f"原始数据: {test['data']}")

    # 转换 Decimal
    converted = convert_decimals(test['data'])
    print(f"转换后类型: {type(converted)}")
    print(f"转换后数据: {converted}")

    # 检查类型是否正确
    if not isinstance(converted, test['expected_type']):
        print(f"❌ 类型错误: 期望 {test['expected_type']}, 实际 {type(converted)}")
        all_passed = False
        continue

    # 尝试 JSON 序列化
    try:
        json_str = json.dumps(converted, ensure_ascii=False)
        print(f"JSON 序列化成功: {json_str[:100]}...")
        
        # 验证没有 Decimal 类型
        def check_no_decimals(obj):
            if isinstance(obj, Decimal):
                return False
            elif isinstance(obj, dict):
                return all(check_no_decimals(v) for v in obj.values())
            elif isinstance(obj, list):
                return all(check_no_decimals(item) for item in obj)
            return True
        
        if not check_no_decimals(converted):
            print("❌ 转换后仍包含 Decimal 类型!")
            all_passed = False
        else:
            print("✅ 测试通过!")
    
    except TypeError as e:
        print(f"❌ JSON 序列化失败: {e}")
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("✅ 所有测试通过!")
else:
    print("❌ 部分测试失败!")
print("=" * 80)
