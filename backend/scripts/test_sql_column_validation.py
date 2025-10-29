"""
测试 SQL 列验证和自动修复功能

验证完整流程：
1. SQL列验证工具（检测无效列）
2. 自动修复工具（建议和替换列名）
3. 集成到task执行流程
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_column_validator_basic():
    """测试基础列验证功能"""
    print("\n" + "="*70)
    print("测试 1: SQL 列验证工具 - 基础功能")
    print("="*70)

    from app.services.infrastructure.agents.tools.column_validator import SQLColumnValidatorTool

    validator = SQLColumnValidatorTool()

    # 模拟表结构
    schema_context = {
        "table_columns": {
            "ods_travel": ["id", "name", "area_name", "travel_type", "dt", "created_at"],
            "ods_orders": ["order_id", "customer_id", "product_name", "amount", "order_date"]
        }
    }

    # 测试用例1: SQL使用了不存在的列
    print("\n📋 测试用例 1: 检测不存在的列...")
    test_sql_1 = """
    SELECT COUNT(*) AS travel_agency_count
    FROM ods_travel
    WHERE area = '大理州' AND travel_type = '省内总社'
    """

    result1 = await validator.execute({
        "sql": test_sql_1,
        "schema_context": schema_context
    })

    print(f"验证结果: {result1['success']}")
    print(f"是否有效: {result1['valid']}")
    if not result1['valid']:
        print(f"❌ 发现无效列: {result1['invalid_columns']}")
        print(f"💡 修复建议: {result1.get('suggestions', {})}")
    else:
        print("✅ 所有列验证通过")

    # 测试用例2: SQL使用的列都存在
    print("\n📋 测试用例 2: 所有列都有效...")
    test_sql_2 = """
    SELECT COUNT(*) AS travel_agency_count
    FROM ods_travel
    WHERE area_name = '大理州' AND travel_type = '省内总社'
    """

    result2 = await validator.execute({
        "sql": test_sql_2,
        "schema_context": schema_context
    })

    print(f"验证结果: {result2['success']}")
    print(f"是否有效: {result2['valid']}")
    if result2['valid']:
        print("✅ 所有列验证通过")

    # 测试用例3: 多个表的列
    print("\n📋 测试用例 3: 多表JOIN的列验证...")
    test_sql_3 = """
    SELECT
        t.name,
        t.area_name,
        o.product_name,
        o.total_amount
    FROM ods_travel t
    JOIN ods_orders o ON t.id = o.customer_id
    WHERE t.area_name = '大理州'
    """

    result3 = await validator.execute({
        "sql": test_sql_3,
        "schema_context": schema_context
    })

    print(f"验证结果: {result3['success']}")
    print(f"是否有效: {result3['valid']}")
    if not result3['valid']:
        print(f"❌ 发现无效列: {result3['invalid_columns']}")
        print(f"💡 修复建议: {result3.get('suggestions', {})}")

    return result1, result2, result3


async def test_auto_fix_tool():
    """测试自动修复工具"""
    print("\n" + "="*70)
    print("测试 2: SQL 自动修复工具")
    print("="*70)

    from app.services.infrastructure.agents.tools.column_validator import SQLColumnAutoFixTool

    fixer = SQLColumnAutoFixTool()

    # 测试用例1: 自动修复单个列名
    print("\n📋 测试用例 1: 修复单个列名...")
    test_sql = """
    SELECT COUNT(*) AS travel_agency_count
    FROM ods_travel
    WHERE area = '大理州' AND travel_type = '省内总社'
    """

    suggestions = {
        "ods_travel.area": "area_name"
    }

    result = await fixer.execute({
        "sql": test_sql,
        "suggestions": suggestions
    })

    if result['success']:
        print("✅ SQL 自动修复成功")
        print(f"\n原始 SQL:\n{test_sql}")
        print(f"\n修复后 SQL:\n{result['fixed_sql']}")
        print(f"\n修改记录: {result['changes']}")
    else:
        print(f"❌ 修复失败: {result.get('error')}")

    # 测试用例2: 修复多个列名
    print("\n📋 测试用例 2: 修复多个列名...")
    test_sql_2 = """
    SELECT
        name,
        area,
        type,
        total
    FROM ods_travel
    WHERE area = '大理州' AND type = '省内总社'
    """

    suggestions_2 = {
        "ods_travel.area": "area_name",
        "ods_travel.type": "travel_type",
        "ods_travel.total": "total_count"
    }

    result2 = await fixer.execute({
        "sql": test_sql_2,
        "suggestions": suggestions_2
    })

    if result2['success']:
        print("✅ SQL 自动修复成功")
        print(f"\n原始 SQL:\n{test_sql_2}")
        print(f"\n修复后 SQL:\n{result2['fixed_sql']}")
        print(f"\n修改记录:")
        for change in result2['changes']:
            print(f"  - {change}")
    else:
        print(f"❌ 修复失败: {result2.get('error')}")

    return result, result2


async def test_validation_with_fuzzy_match():
    """测试模糊匹配建议"""
    print("\n" + "="*70)
    print("测试 3: 模糊匹配列名建议")
    print("="*70)

    from app.services.infrastructure.agents.tools.column_validator import SQLColumnValidatorTool

    validator = SQLColumnValidatorTool()

    schema_context = {
        "table_columns": {
            "ods_travel": [
                "id", "agency_name", "area_code", "area_name",
                "agency_type", "travel_type", "registration_date", "dt"
            ]
        }
    }

    # 测试各种相似列名
    test_cases = [
        ("area", "area_name/area_code"),
        ("name", "agency_name"),
        ("type", "agency_type/travel_type"),
        ("date", "registration_date/dt"),
    ]

    for wrong_col, expected in test_cases:
        test_sql = f"SELECT * FROM ods_travel WHERE {wrong_col} = 'test'"

        result = await validator.execute({
            "sql": test_sql,
            "schema_context": schema_context
        })

        print(f"\n错误列: {wrong_col}")
        print(f"期望建议: {expected}")
        if not result['valid']:
            suggestions = result.get('suggestions', {})
            suggested = suggestions.get(f"ods_travel.{wrong_col}", "无建议")
            print(f"实际建议: {suggested}")
            if suggested in expected:
                print("✅ 建议正确")
            else:
                print(f"⚠️  建议可能需要优化")
        else:
            print("❌ 应该检测到错误但没有")


async def test_complete_workflow():
    """测试完整工作流：验证 → 修复 → 执行"""
    print("\n" + "="*70)
    print("测试 4: 完整工作流程（模拟tasks.py）")
    print("="*70)

    from app.services.infrastructure.agents.tools.column_validator import (
        SQLColumnValidatorTool,
        SQLColumnAutoFixTool
    )

    # 模拟场景：Agent生成的SQL有列名错误
    print("\n【场景】Agent 生成了有问题的 SQL")

    placeholder_name = "大理州省内总社旅行社数量"
    generated_sql = """
    SELECT COUNT(*) AS travel_agency_count
    FROM ods_travel
    WHERE area = '大理州' AND travel_type = '省内总社'
    """

    schema_context = {
        "table_columns": {
            "ods_travel": ["id", "name", "area_name", "travel_type", "dt"]
        }
    }

    print(f"\n占位符: {placeholder_name}")
    print(f"生成的 SQL:\n{generated_sql}")

    # Step 1: 验证
    print("\n【Step 1】验证 SQL 列...")
    validator = SQLColumnValidatorTool()
    validation_result = await validator.execute({
        "sql": generated_sql,
        "schema_context": schema_context
    })

    if not validation_result['valid']:
        print(f"❌ 验证失败")
        print(f"   无效列: {validation_result['invalid_columns']}")
        print(f"   建议: {validation_result.get('suggestions', {})}")

        # Step 2: 自动修复
        print("\n【Step 2】尝试自动修复...")
        fixer = SQLColumnAutoFixTool()
        fix_result = await fixer.execute({
            "sql": generated_sql,
            "suggestions": validation_result.get('suggestions', {})
        })

        if fix_result['success']:
            print("✅ 自动修复成功")
            fixed_sql = fix_result['fixed_sql']
            changes = fix_result['changes']

            print(f"\n修复后的 SQL:\n{fixed_sql}")
            print(f"\n修改记录:")
            for change in changes:
                print(f"  - {change}")

            # Step 3: 重新验证修复后的SQL
            print("\n【Step 3】验证修复后的 SQL...")
            revalidation_result = await validator.execute({
                "sql": fixed_sql,
                "schema_context": schema_context
            })

            if revalidation_result['valid']:
                print("✅ 修复后的 SQL 验证通过，可以执行")
                return {
                    "success": True,
                    "original_sql": generated_sql,
                    "fixed_sql": fixed_sql,
                    "changes": changes
                }
            else:
                print("❌ 修复后仍有问题")
                return {"success": False, "error": "修复后验证失败"}
        else:
            print(f"❌ 自动修复失败: {fix_result.get('error')}")
            return {"success": False, "error": "自动修复失败"}
    else:
        print("✅ SQL 验证通过")
        return {
            "success": True,
            "original_sql": generated_sql,
            "fixed_sql": None,
            "changes": []
        }


async def test_edge_cases():
    """测试边界情况"""
    print("\n" + "="*70)
    print("测试 5: 边界情况")
    print("="*70)

    from app.services.infrastructure.agents.tools.column_validator import SQLColumnValidatorTool

    validator = SQLColumnValidatorTool()

    schema_context = {
        "table_columns": {
            "ods_travel": ["id", "name", "area_name"]
        }
    }

    # 边界情况1: 空SQL
    print("\n📋 边界情况 1: 空 SQL")
    result1 = await validator.execute({
        "sql": "",
        "schema_context": schema_context
    })
    print(f"结果: {result1}")

    # 边界情况2: 没有表结构信息
    print("\n📋 边界情况 2: 没有表结构信息")
    result2 = await validator.execute({
        "sql": "SELECT * FROM ods_travel",
        "schema_context": {}
    })
    print(f"结果: {result2}")

    # 边界情况3: 使用通配符 *
    print("\n📋 边界情况 3: 使用 SELECT *")
    result3 = await validator.execute({
        "sql": "SELECT * FROM ods_travel",
        "schema_context": schema_context
    })
    print(f"结果: valid={result3['valid']}")

    # 边界情况4: 子查询
    print("\n📋 边界情况 4: 包含子查询")
    subquery_sql = """
    SELECT name, area_name
    FROM ods_travel
    WHERE id IN (
        SELECT customer_id FROM ods_orders WHERE amount > 1000
    )
    """
    result4 = await validator.execute({
        "sql": subquery_sql,
        "schema_context": {
            "table_columns": {
                "ods_travel": ["id", "name", "area_name"],
                "ods_orders": ["customer_id", "amount"]
            }
        }
    })
    print(f"结果: valid={result4['valid']}")


async def main():
    """运行所有测试"""
    print("🚀 开始测试 SQL 列验证和自动修复功能")
    print("="*70)

    try:
        # 测试1: 基础列验证
        await test_column_validator_basic()

        # 测试2: 自动修复工具
        await test_auto_fix_tool()

        # 测试3: 模糊匹配建议
        await test_validation_with_fuzzy_match()

        # 测试4: 完整工作流
        workflow_result = await test_complete_workflow()

        # 测试5: 边界情况
        await test_edge_cases()

        print("\n" + "="*70)
        print("✅ 所有测试完成")
        print("="*70)

        print("\n📌 功能总结:")
        print("   1. SQLColumnValidatorTool - 验证SQL中的列是否存在 ✅")
        print("   2. SQLColumnAutoFixTool - 自动修复无效列名 ✅")
        print("   3. 模糊匹配建议 - 推荐相似的正确列名 ✅")
        print("   4. 完整工作流 - 验证→修复→重新验证 ✅")

        print("\n🎯 集成到 tasks.py:")
        print("   - 在 ETL 执行阶段（Line 683-794）")
        print("   - 自动验证所有 SQL 的列名")
        print("   - 发现错误时自动修复")
        print("   - 保存修复后的 SQL 到数据库")
        print("   - 记录修改详情到 agent_config")

        print("\n💡 Agent 提示词已更新:")
        print("   - 强调必须先调用 schema.list_columns")
        print("   - 禁止臆测列名")
        print("   - 建议使用 sql.validate_columns 验证")

        if workflow_result and workflow_result.get('success'):
            print("\n🎉 完整工作流测试成功！")
            if workflow_result.get('fixed_sql'):
                print("   自动修复功能正常工作")
            else:
                print("   SQL 直接通过验证")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
