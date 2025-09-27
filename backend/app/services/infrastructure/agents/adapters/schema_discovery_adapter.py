"""
Schema Discovery Adapter (Infrastructure)

Implements Domain SchemaDiscoveryPort by introspecting the live data source via
connector_factory, returning simple tables/columns for Domain consumption.
"""

from __future__ import annotations

import logging
from typing import List, Dict

from app.services.domain.placeholder.ports.schema_discovery_port import SchemaDiscoveryPort, SchemaInfo
from app.db.session import get_db_session
from app.models.data_source import DataSource
from app.services.data.connectors.connector_factory import create_connector

logger = logging.getLogger(__name__)


class SchemaDiscoveryAdapter(SchemaDiscoveryPort):
    async def introspect(self, data_source_id: str) -> SchemaInfo:
        """
        通过连接器introspect数据源schema
        增强版本，包含详细日志和错误处理
        """
        logger.info(f"🔍 开始introspect数据源schema: {data_source_id}")

        tables: List[str] = []
        columns: Dict[str, List[str]] = {}

        # Use app DB to load data source and create a connector
        try:
            with get_db_session() as db:
                ds: DataSource = db.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not ds:
                    logger.error(f"❌ 数据源不存在: {data_source_id}")
                    return SchemaInfo(tables=[], columns={})

                logger.info(f"✅ 找到数据源: {ds.name} (类型: {ds.source_type})")

                try:
                    connector = create_connector(ds)
                    logger.info(f"✅ 成功创建连接器: {type(connector).__name__}")
                except Exception as e:
                    logger.error(f"❌ 创建连接器失败: {e}")
                    return SchemaInfo(tables=[], columns={})

        except Exception as e:
            logger.error(f"❌ 获取数据源信息失败: {e}")
            return SchemaInfo(tables=[], columns={})

        # Connect and introspect
        connector_connected = False
        try:
            logger.info("🔌 尝试连接数据源...")
            await connector.connect()
            connector_connected = True
            logger.info("✅ 数据源连接成功")

            logger.info("📋 获取表列表...")
            tbls = await connector.get_tables()
            tables = tbls or []
            logger.info(f"✅ 发现 {len(tables)} 个表: {tables[:5]}{'...' if len(tables) > 5 else ''}")

            if not tables:
                logger.warning("⚠️ 未发现任何表")
                return SchemaInfo(tables=[], columns={})

            # For each table, fetch fields (best-effort)
            successful_columns = 0
            for i, table_name in enumerate(tables):
                try:
                    logger.debug(f"📋 获取表 {table_name} 的列信息 ({i+1}/{len(tables)})")
                    cols = await connector.get_fields(table_name)
                    table_columns = cols or []
                    columns[table_name] = table_columns
                    if table_columns:
                        successful_columns += 1
                        logger.debug(f"✅ 表 {table_name}: {len(table_columns)} 列")
                    else:
                        logger.warning(f"⚠️ 表 {table_name}: 无列信息")
                except Exception as e:
                    logger.warning(f"⚠️ 获取表 {table_name} 列信息失败: {e}")
                    columns[table_name] = []

            logger.info(f"✅ Schema introspect完成: {len(tables)} 表, {successful_columns} 表有列信息")

        except Exception as e:
            logger.error(f"❌ 数据源introspect失败: {e}")
            import traceback
            logger.error(f"❌ 详细错误: {traceback.format_exc()}")
            return SchemaInfo(tables=[], columns={})
        finally:
            if connector_connected:
                try:
                    logger.debug("🔌 断开数据源连接")
                    await connector.disconnect()
                except Exception as e:
                    logger.warning(f"⚠️ 断开连接失败: {e}")

        result = SchemaInfo(tables=tables, columns=columns)
        logger.info(f"🎯 Schema introspect结果: tables={len(result.tables)}, columns={len(result.columns)}")
        return result
