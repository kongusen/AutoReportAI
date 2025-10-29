"""
诊断 SchemaDiscoveryTool 的数据格式问题
测试 SHOW TABLE STATUS 返回的实际数据格式
"""

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_show_table_status():
    """测试 SHOW TABLE STATUS 返回的数据格式"""
    from app.services.data.connectors import create_connector_from_config
    import pandas as pd

    # 使用测试数据库配置
    connection_config = {
        "source_type": "sql",
        "type": "mysql",
        "name": "test_db",
        "host": "localhost",
        "port": 3306,
        "database": "test_database",  # 替换为你的测试数据库
        "user": "root",
        "password": "password"  # 替换为你的密码
    }

    logger.info("=" * 80)
    logger.info("🔍 测试 1: 直接测试 SQLConnector.execute_query()")
    logger.info("=" * 80)

    try:
        # 创建连接器
        connector = create_connector_from_config(
            connection_config["source_type"],
            connection_config["name"],
            connection_config
        )

        async with connector:
            # 执行 SHOW TABLES 查询
            logger.info("\n📋 Step 1: 执行 SHOW TABLES")
            result = await connector.execute_query("SHOW TABLES LIMIT 5")

            logger.info(f"✓ Result type: {type(result)}")
            logger.info(f"✓ Result class: {result.__class__.__name__}")
            logger.info(f"✓ Result attributes: {dir(result)}")

            if hasattr(result, 'data'):
                logger.info(f"✓ result.data type: {type(result.data)}")
                logger.info(f"✓ result.data:\n{result.data}")

                # 转换为字典
                if isinstance(result.data, pd.DataFrame):
                    logger.info("\n📋 Step 2: 转换 DataFrame 为字典列表")
                    rows = result.data.to_dict('records')
                    logger.info(f"✓ rows type: {type(rows)}")
                    logger.info(f"✓ rows length: {len(rows)}")
                    if rows:
                        logger.info(f"✓ rows[0] type: {type(rows[0])}")
                        logger.info(f"✓ rows[0]: {rows[0]}")
                        logger.info(f"✓ rows[0].keys(): {rows[0].keys() if isinstance(rows[0], dict) else 'NOT A DICT'}")

            # 现在测试 SHOW TABLE STATUS
            logger.info("\n" + "=" * 80)
            logger.info("📋 Step 3: 执行 SHOW TABLE STATUS")
            logger.info("=" * 80)

            # 首先获取一个表名
            tables_result = await connector.execute_query("SHOW TABLES LIMIT 1")
            if not tables_result.data.empty:
                table_name = tables_result.data.iloc[0, 0]
                logger.info(f"✓ Testing with table: {table_name}")

                # 执行 SHOW TABLE STATUS
                status_sql = f"SHOW TABLE STATUS LIKE '{table_name}'"
                logger.info(f"✓ SQL: {status_sql}")

                status_result = await connector.execute_query(status_sql)
                logger.info(f"✓ Result type: {type(status_result)}")
                logger.info(f"✓ result.data type: {type(status_result.data)}")
                logger.info(f"✓ result.data shape: {status_result.data.shape}")
                logger.info(f"✓ result.data columns: {status_result.data.columns.tolist()}")
                logger.info(f"✓ result.data:\n{status_result.data}")

                # 转换为字典
                if isinstance(status_result.data, pd.DataFrame) and not status_result.data.empty:
                    logger.info("\n📋 Step 4: 转换 SHOW TABLE STATUS 结果为字典")
                    rows = status_result.data.to_dict('records')
                    logger.info(f"✓ rows type: {type(rows)}")
                    logger.info(f"✓ rows length: {len(rows)}")
                    if rows:
                        row = rows[0]
                        logger.info(f"✓ row type: {type(row)}")
                        logger.info(f"✓ row: {row}")
                        logger.info(f"✓ row.keys(): {row.keys() if isinstance(row, dict) else 'NOT A DICT'}")

                        # 测试字段访问
                        logger.info("\n📋 Step 5: 测试字段访问")
                        logger.info(f"✓ row.get('Rows'): {row.get('Rows')}")
                        logger.info(f"✓ row.get('Data_length'): {row.get('Data_length')}")
                        logger.info(f"✓ row.get('Create_time'): {row.get('Create_time')}")
                        logger.info(f"✓ row.get('Update_time'): {row.get('Update_time')}")
                        logger.info(f"✓ row.get('Comment'): {row.get('Comment', '')}")

                        # 测试 update 操作
                        logger.info("\n📋 Step 6: 测试字典 update 操作")
                        table_info = {
                            "name": table_name,
                            "description": "",
                            "table_type": "TABLE",
                            "row_count": None,
                            "size_bytes": None,
                            "created_at": None,
                            "updated_at": None,
                            "metadata": {}
                        }

                        try:
                            table_info.update({
                                "row_count": row.get("Rows"),
                                "size_bytes": row.get("Data_length"),
                                "created_at": row.get("Create_time"),
                                "updated_at": row.get("Update_time"),
                                "description": row.get("Comment", "")
                            })
                            logger.info("✅ table_info.update() 成功!")
                            logger.info(f"✓ table_info: {table_info}")
                        except Exception as e:
                            logger.error(f"❌ table_info.update() 失败: {e}")
                            logger.error(f"   错误类型: {type(e)}")
                            import traceback
                            logger.error(f"   堆栈:\n{traceback.format_exc()}")
            else:
                logger.warning("⚠️ 没有找到表，跳过 SHOW TABLE STATUS 测试")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"堆栈:\n{traceback.format_exc()}")


async def test_container_run_query():
    """测试 Container.DataSourceAdapter.run_query() 的数据流"""
    from app.core.container import DataSourceAdapter

    logger.info("\n" + "=" * 80)
    logger.info("🔍 测试 2: 测试 Container.DataSourceAdapter.run_query()")
    logger.info("=" * 80)

    # 使用测试数据库配置
    connection_config = {
        "source_type": "sql",
        "type": "mysql",
        "name": "test_db",
        "host": "localhost",
        "port": 3306,
        "database": "test_database",  # 替换为你的测试数据库
        "user": "root",
        "password": "password"  # 替换为你的密码
    }

    adapter = DataSourceAdapter()

    try:
        # 测试 SHOW TABLES
        logger.info("\n📋 Step 1: 测试 SHOW TABLES")
        result = await adapter.run_query(connection_config, "SHOW TABLES LIMIT 5")

        logger.info(f"✓ Result type: {type(result)}")
        logger.info(f"✓ Result keys: {result.keys()}")
        logger.info(f"✓ success: {result.get('success')}")
        logger.info(f"✓ rows type: {type(result.get('rows'))}")
        logger.info(f"✓ rows length: {len(result.get('rows', []))}")

        rows = result.get('rows', [])
        if rows:
            logger.info(f"✓ rows[0] type: {type(rows[0])}")
            logger.info(f"✓ rows[0]: {rows[0]}")

        # 获取第一个表名
        if rows and isinstance(rows[0], dict):
            # 尝试提取表名
            table_name = None
            for key in rows[0].keys():
                if 'table' in key.lower():
                    table_name = rows[0][key]
                    break

            if not table_name and rows[0]:
                # 取第一个值
                table_name = next(iter(rows[0].values()))

            if table_name:
                logger.info(f"\n📋 Step 2: 测试 SHOW TABLE STATUS for {table_name}")
                status_sql = f"SHOW TABLE STATUS LIKE '{table_name}'"
                status_result = await adapter.run_query(connection_config, status_sql, limit=1)

                logger.info(f"✓ Result type: {type(status_result)}")
                logger.info(f"✓ success: {status_result.get('success')}")
                logger.info(f"✓ rows type: {type(status_result.get('rows'))}")
                logger.info(f"✓ rows length: {len(status_result.get('rows', []))}")

                status_rows = status_result.get('rows', [])
                if status_rows:
                    logger.info(f"✓ rows[0] type: {type(status_rows[0])}")
                    logger.info(f"✓ rows[0]: {status_rows[0]}")
                    logger.info(f"✓ rows[0].keys(): {status_rows[0].keys() if isinstance(status_rows[0], dict) else 'NOT A DICT'}")

                    # 测试字段访问
                    if isinstance(status_rows[0], dict):
                        row = status_rows[0]
                        logger.info("\n📋 Step 3: 测试字段访问")
                        logger.info(f"✓ row.get('Rows'): {row.get('Rows')}")
                        logger.info(f"✓ row.get('Data_length'): {row.get('Data_length')}")
                        logger.info(f"✓ row.get('Create_time'): {row.get('Create_time')}")
                        logger.info(f"✓ row.get('Update_time'): {row.get('Update_time')}")
                        logger.info(f"✓ row.get('Comment'): {row.get('Comment', '')}")
                else:
                    logger.warning("⚠️ SHOW TABLE STATUS 没有返回数据")
        else:
            logger.warning("⚠️ SHOW TABLES 没有返回有效数据")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"堆栈:\n{traceback.format_exc()}")


async def main():
    """主函数"""
    logger.info("🚀 开始诊断 SchemaDiscoveryTool 数据格式问题")
    logger.info("=" * 80)

    # 运行测试
    await test_show_table_status()
    await test_container_run_query()

    logger.info("\n" + "=" * 80)
    logger.info("✅ 诊断完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
