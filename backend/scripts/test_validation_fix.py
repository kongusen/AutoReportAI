#!/usr/bin/env python3
"""
测试修复后的SQL验证逻辑

验证点:
1. 当表不存在时，验证应该失败
2. 验证结果应该包含invalid_tables信息
3. 日志应该显示详细的失败原因
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.services.infrastructure.agents.tools.validation_tools import SQLColumnValidatorTool


async def test_invalid_table():
    """测试不存在的表"""
    print("\n" + "=" * 80)
    print("测试1: 表不存在的情况")
    print("=" * 80)

    # 模拟schema上下文 - 只有 online_retail 表
    schema_context = {
        "online_retail": {
            "columns": ["InvoiceNo", "StockCode", "Description", "Quantity",
                       "InvoiceDate", "UnitPrice", "CustomerID", "Country"],
            "comment": "在线零售数据表"
        }
    }

    # 测试SQL使用了不存在的表 'sales'
    sql = "SELECT * FROM sales WHERE sale_date BETWEEN {{start_date}} AND {{end_date}}"

    validator = SQLColumnValidatorTool(container=None)
    result = await validator.run(sql=sql, schema_context=schema_context)

    print(f"\n✅ 验证结果:")
    print(f"   - success: {result.get('success')}")
    print(f"   - valid: {result.get('valid')}")
    print(f"   - invalid_tables: {result.get('invalid_tables', [])}")
    print(f"   - invalid_columns: {result.get('invalid_columns', [])}")
    print(f"   - errors: {result.get('errors', [])}")

    # 断言：应该验证失败
    assert result.get('valid') == False, "❌ 表不存在时验证应该失败！"
    assert len(result.get('invalid_tables', [])) > 0, "❌ 应该记录不存在的表！"
    assert 'sales' in result.get('invalid_tables', []), "❌ 应该识别出 'sales' 表不存在！"

    print("\n✅ 测试1通过：表不存在时验证正确失败")


async def test_valid_table():
    """测试存在的表"""
    print("\n" + "=" * 80)
    print("测试2: 表存在的情况")
    print("=" * 80)

    schema_context = {
        "online_retail": {
            "columns": ["InvoiceNo", "StockCode", "Description", "Quantity",
                       "InvoiceDate", "UnitPrice", "CustomerID", "Country"],
            "comment": "在线零售数据表"
        }
    }

    # 使用存在的表和列
    sql = "SELECT InvoiceNo, Quantity FROM online_retail WHERE InvoiceDate BETWEEN {{start_date}} AND {{end_date}}"

    validator = SQLColumnValidatorTool(container=None)
    result = await validator.run(sql=sql, schema_context=schema_context)

    print(f"\n✅ 验证结果:")
    print(f"   - success: {result.get('success')}")
    print(f"   - valid: {result.get('valid')}")
    print(f"   - invalid_tables: {result.get('invalid_tables', [])}")
    print(f"   - invalid_columns: {result.get('invalid_columns', [])}")

    # 断言：应该验证成功
    assert result.get('valid') == True, "❌ 使用正确的表和列时验证应该成功！"
    assert len(result.get('invalid_tables', [])) == 0, "❌ 不应该有不存在的表！"
    assert len(result.get('invalid_columns', [])) == 0, "❌ 不应该有无效的列！"

    print("\n✅ 测试2通过：使用正确的表和列时验证成功")


async def test_invalid_column():
    """测试不存在的列"""
    print("\n" + "=" * 80)
    print("测试3: 列不存在的情况")
    print("=" * 80)

    schema_context = {
        "online_retail": {
            "columns": ["InvoiceNo", "StockCode", "Description", "Quantity",
                       "InvoiceDate", "UnitPrice", "CustomerID", "Country"],
            "comment": "在线零售数据表"
        }
    }

    # 使用不存在的列 'sale_date'（应该是 'InvoiceDate'）
    sql = "SELECT InvoiceNo FROM online_retail WHERE sale_date BETWEEN {{start_date}} AND {{end_date}}"

    validator = SQLColumnValidatorTool(container=None)
    result = await validator.run(sql=sql, schema_context=schema_context)

    print(f"\n✅ 验证结果:")
    print(f"   - success: {result.get('success')}")
    print(f"   - valid: {result.get('valid')}")
    print(f"   - invalid_tables: {result.get('invalid_tables', [])}")
    print(f"   - invalid_columns: {result.get('invalid_columns', [])}")
    print(f"   - errors: {result.get('errors', [])}")
    print(f"   - suggestions: {result.get('suggestions', {})}")

    # 断言：应该验证失败
    assert result.get('valid') == False, "❌ 列不存在时验证应该失败！"
    assert len(result.get('invalid_columns', [])) > 0, "❌ 应该记录无效的列！"

    print("\n✅ 测试3通过：列不存在时验证正确失败")


async def main():
    print("\n" + "=" * 80)
    print("🧪 测试修复后的SQL验证逻辑")
    print("=" * 80)

    try:
        await test_invalid_table()
        await test_valid_table()
        await test_invalid_column()

        print("\n" + "=" * 80)
        print("✅ 所有测试通过！验证逻辑修复成功")
        print("=" * 80)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
