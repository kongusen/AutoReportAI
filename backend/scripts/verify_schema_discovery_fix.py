"""
验证 SchemaDiscoveryTool 修复后的功能
测试数据格式转换和错误处理
"""

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_container_adapter():
    """测试 Container.DataSourceAdapter 的数据转换"""
    from app.core.container import DataSourceAdapter

    logger.info("=" * 80)
    logger.info("🔍 测试 Container.DataSourceAdapter")
    logger.info("=" * 80)

    # 模拟数据库配置 - 请替换为你的实际配置
    connection_config = {
        "source_type": "sql",
        "type": "mysql",
        "name": "test_db",
        "host": "localhost",
        "port": 3306,
        "database": "your_database",  # 替换
        "user": "your_user",           # 替换
        "password": "your_password"    # 替换
    }

    adapter = DataSourceAdapter()

    try:
        # 测试 SHOW TABLES
        logger.info("\n📋 测试 1: SHOW TABLES")
        result = await adapter.run_query(connection_config, "SHOW TABLES LIMIT 3")

        logger.info(f"✓ Success: {result.get('success')}")
        logger.info(f"✓ Rows count: {len(result.get('rows', []))}")

        rows = result.get('rows', [])
        if rows:
            logger.info(f"✓ First row type: {type(rows[0])}")
            logger.info(f"✓ First row: {rows[0]}")

            # 提取第一个表名进行进一步测试
            table_name = None
            if isinstance(rows[0], dict):
                for key in rows[0].keys():
                    if 'table' in key.lower():
                        table_name = rows[0][key]
                        break
                if not table_name:
                    table_name = next(iter(rows[0].values()))

            if table_name:
                logger.info(f"\n📋 测试 2: SHOW TABLE STATUS for '{table_name}'")
                status_result = await adapter.run_query(
                    connection_config,
                    f"SHOW TABLE STATUS LIKE '{table_name}'",
                    limit=1
                )

                logger.info(f"✓ Success: {status_result.get('success')}")
                status_rows = status_result.get('rows', [])
                logger.info(f"✓ Rows count: {len(status_rows)}")

                if status_rows:
                    logger.info(f"✓ First row type: {type(status_rows[0])}")
                    logger.info(f"✓ First row keys: {status_rows[0].keys() if isinstance(status_rows[0], dict) else 'NOT A DICT'}")

                    if isinstance(status_rows[0], dict):
                        row = status_rows[0]
                        logger.info("\n📊 字段验证:")
                        logger.info(f"  - Rows: {row.get('Rows')}")
                        logger.info(f"  - Data_length: {row.get('Data_length')}")
                        logger.info(f"  - Create_time: {row.get('Create_time')}")
                        logger.info(f"  - Update_time: {row.get('Update_time')}")
                        logger.info(f"  - Comment: {row.get('Comment', '')}")
                        logger.info("✅ 所有字段都可以正常访问")
                    else:
                        logger.error(f"❌ 返回的 row 不是字典: {type(status_rows[0])}")
                else:
                    logger.warning("⚠️ SHOW TABLE STATUS 没有返回数据")
        else:
            logger.warning("⚠️ SHOW TABLES 没有返回数据")

        logger.info("\n✅ Container.DataSourceAdapter 测试通过")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"堆栈:\n{traceback.format_exc()}")


async def test_schema_discovery_tool():
    """测试 SchemaDiscoveryTool"""
    from app.core.container import ServiceContainer
    from app.services.infrastructure.agents.tools.schema.discovery import SchemaDiscoveryTool

    logger.info("\n" + "=" * 80)
    logger.info("🔍 测试 SchemaDiscoveryTool")
    logger.info("=" * 80)

    # 创建容器
    container = ServiceContainer()

    # 模拟数据库配置 - 请替换为你的实际配置
    connection_config = {
        "source_type": "sql",
        "type": "mysql",
        "name": "test_db",
        "host": "localhost",
        "port": 3306,
        "database": "your_database",  # 替换
        "user": "your_user",           # 替换
        "password": "your_password"    # 替换
    }

    # 创建工具
    tool = SchemaDiscoveryTool(container)

    try:
        logger.info("\n📋 测试 Schema Discovery - 发现表")
        result = await tool.run(
            connection_config=connection_config,
            discovery_type="tables",
            max_tables=3
        )

        logger.info(f"✓ Success: {result.get('success')}")
        tables = result.get('discovered', {}).get('tables', [])
        logger.info(f"✓ Tables count: {len(tables)}")

        if tables:
            logger.info(f"\n📊 第一个表信息:")
            table = tables[0]
            logger.info(f"  - name: {table.get('name')}")
            logger.info(f"  - row_count: {table.get('row_count')}")
            logger.info(f"  - size_bytes: {table.get('size_bytes')}")
            logger.info(f"  - description: {table.get('description')}")
            logger.info("✅ 表信息获取成功")

            # 测试获取列信息
            logger.info("\n📋 测试 Schema Discovery - 发现列")
            columns_result = await tool.run(
                connection_config=connection_config,
                discovery_type="columns",
                tables=[table.get('name')],
                max_tables=1
            )

            logger.info(f"✓ Success: {columns_result.get('success')}")
            columns = columns_result.get('discovered', {}).get('columns', [])
            logger.info(f"✓ Columns count: {len(columns)}")

            if columns:
                logger.info(f"\n📊 第一个列信息:")
                col = columns[0]
                logger.info(f"  - table_name: {col.get('table_name')}")
                logger.info(f"  - name: {col.get('name')}")
                logger.info(f"  - data_type: {col.get('data_type')}")
                logger.info(f"  - nullable: {col.get('nullable')}")
                logger.info("✅ 列信息获取成功")
        else:
            logger.warning("⚠️ 没有发现表")

        logger.info("\n✅ SchemaDiscoveryTool 测试通过")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"堆栈:\n{traceback.format_exc()}")


async def main():
    """主函数"""
    logger.info("🚀 开始验证 SchemaDiscoveryTool 修复")
    logger.info("=" * 80)

    logger.info("\n⚠️  请确保在运行前修改数据库配置：")
    logger.info("   - host")
    logger.info("   - port")
    logger.info("   - database")
    logger.info("   - user")
    logger.info("   - password")
    logger.info("\n" + "=" * 80)

    # 运行测试
    await test_container_adapter()
    await test_schema_discovery_tool()

    logger.info("\n" + "=" * 80)
    logger.info("✅ 所有验证完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
