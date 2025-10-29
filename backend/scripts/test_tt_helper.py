"""
测试 TaskTool Helper (tt) 简化接口

演示如何使用 tt() 简化子代理调用
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.container import Container
from app.services.infrastructure.agents.task_tool_helper import tt, set_tt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_tt_generate_sql():
    """测试 tt.generate_sql() 简化接口"""
    logger.info("=" * 80)
    logger.info("测试: tt.generate_sql() - 简化的 SQL 生成")
    logger.info("=" * 80)

    # 模拟 schema
    schema = """
    Table: online_retail
    Columns:
      - InvoiceNo (VARCHAR)
      - StockCode (VARCHAR)
      - Description (VARCHAR)
      - Quantity (INT)
      - InvoiceDate (DATETIME)
      - UnitPrice (DECIMAL)
      - CustomerID (INT)
      - Country (VARCHAR)
    """

    try:
        # 使用简化接口生成 SQL
        result = await tt.generate_sql(
            prompt="查询最近一个月的销售数据，按国家分组统计总销售额",
            schema=schema
        )

        logger.info("✅ SQL 生成成功")
        logger.info(f"   SQL: {result.get('sql', 'N/A')}")
        logger.info(f"   推理: {result.get('reasoning', 'N/A')}")
        logger.info(f"   使用的表: {result.get('tables_used', [])}")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def test_tt_validate_sql():
    """测试 tt.validate_sql() 简化接口"""
    logger.info("\n" + "=" * 80)
    logger.info("测试: tt.validate_sql() - 简化的 SQL 验证")
    logger.info("=" * 80)

    schema = """
    Table: online_retail
    Columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate
    """

    # 测试有效的 SQL
    valid_sql = "SELECT * FROM online_retail WHERE Quantity > 0"

    try:
        result = await tt.validate_sql(
            sql=valid_sql,
            schema=schema
        )

        logger.info("✅ SQL 验证成功")
        logger.info(f"   是否有效: {result['is_valid']}")
        logger.info(f"   错误数: {len(result.get('errors', []))}")
        logger.info(f"   警告数: {len(result.get('warnings', []))}")

        # 测试无效的 SQL
        invalid_sql = "SELECT * FROM wrong_table WHERE col > 0"
        result2 = await tt.validate_sql(
            sql=invalid_sql,
            schema=schema
        )

        logger.info(f"\n   测试无效 SQL:")
        logger.info(f"   是否有效: {result2['is_valid']}")
        logger.info(f"   错误: {result2.get('errors', [])}")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def test_tt_generate_chart():
    """测试 tt.generate_chart() 简化接口"""
    logger.info("\n" + "=" * 80)
    logger.info("测试: tt.generate_chart() - 简化的图表生成")
    logger.info("=" * 80)

    sql = """
    SELECT Country, SUM(Quantity * UnitPrice) as TotalSales
    FROM online_retail
    WHERE InvoiceDate >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
    GROUP BY Country
    ORDER BY TotalSales DESC
    """

    try:
        result = await tt.generate_chart(
            prompt="生成一个柱状图，展示各国家的销售额",
            sql=sql
        )

        logger.info("✅ 图表配置生成成功")
        logger.info(f"   图表类型: {result.get('chart_type', 'N/A')}")
        logger.info(f"   标题: {result.get('title', 'N/A')}")
        logger.info(f"   X轴: {result.get('x_axis', {})}")
        logger.info(f"   Y轴: {result.get('y_axis', {})}")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def demo_usage_in_application():
    """演示在实际应用中如何使用 tt"""
    logger.info("\n" + "=" * 80)
    logger.info("演示: 在应用中使用 tt 简化工作流")
    logger.info("=" * 80)

    schema = """
    Table: online_retail
    Columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country
    """

    try:
        # 步骤 1: 生成 SQL
        logger.info("步骤 1: 使用 tt.generate_sql() 生成 SQL")
        sql_result = await tt.generate_sql(
            prompt="查询最近7天的订单数量",
            schema=schema
        )
        generated_sql = sql_result.get('sql', '')
        logger.info(f"  ✅ 生成的 SQL: {generated_sql[:100]}...")

        # 步骤 2: 验证 SQL
        logger.info("\n步骤 2: 使用 tt.validate_sql() 验证 SQL")
        validation_result = await tt.validate_sql(
            sql=generated_sql,
            schema=schema
        )

        if validation_result['is_valid']:
            logger.info("  ✅ SQL 验证通过")

            # 步骤 3: 生成图表
            logger.info("\n步骤 3: 使用 tt.generate_chart() 生成图表配置")
            chart_result = await tt.generate_chart(
                prompt="生成折线图展示订单趋势",
                sql=generated_sql
            )
            logger.info(f"  ✅ 图表类型: {chart_result.get('chart_type')}")

            logger.info("\n✨ 完整工作流执行成功！")
            logger.info("   使用 tt.* 方法大大简化了代码，不需要手动构建复杂的工具调用。")
            return True
        else:
            logger.error(f"  ❌ SQL 验证失败: {validation_result.get('errors')}")
            return False

    except Exception as e:
        logger.error(f"❌ 演示失败: {e}", exc_info=True)
        return False


async def main():
    """运行所有测试"""
    logger.info("🚀 开始测试 TaskTool Helper (tt) 简化接口\n")

    # 初始化 container
    container = Container()

    # 设置 tt 使用 container 中的 LLM
    try:
        llm = container.llm
        validation_service = getattr(container, 'sql_validation_service', None)
        set_tt(llm=llm, validation_service=validation_service)
        logger.info("✅ TaskTool Helper 初始化成功\n")
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}", exc_info=True)
        return 1

    # 运行测试
    results = []
    results.append(("tt.generate_sql", await test_tt_generate_sql()))
    results.append(("tt.validate_sql", await test_tt_validate_sql()))
    results.append(("tt.generate_chart", await test_tt_generate_chart()))
    results.append(("实际应用演示", await demo_usage_in_application()))

    # 总结
    logger.info("\n" + "=" * 80)
    logger.info("测试总结")
    logger.info("=" * 80)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{name}: {status}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    logger.info("")
    logger.info(f"总计: {passed}/{total} 个测试通过")

    if passed == total:
        logger.info("\n🎉 所有测试通过！tt 简化接口工作正常。")
        logger.info("\n💡 使用提示:")
        logger.info("   from app.services.infrastructure.agents.task_tool_helper import tt")
        logger.info("   result = await tt.generate_sql(prompt=..., schema=...)")
        logger.info("   validation = await tt.validate_sql(sql=..., schema=...)")
        logger.info("   chart = await tt.generate_chart(prompt=..., sql=...)")
        return 0
    else:
        logger.error("\n⚠️ 部分测试失败。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
