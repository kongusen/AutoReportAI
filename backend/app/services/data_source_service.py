import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from app import crud
from app.core.security_utils import (
    decrypt_data,
    encrypt_data,
    validate_connection_string,
)
from app.db.session import get_db_session
from app.models.data_source import DataSourceType, SQLQueryType
from .connectors.doris_connector import create_doris_connector

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """数据库连接池管理器"""

    def __init__(self):
        self._pools: Dict[str, Engine] = {}

    def get_engine(self, connection_string: str, pool_size: int = 5) -> Engine:
        """获取数据库引擎（带连接池）"""
        pool_key = f"{connection_string}_{pool_size}"

        if pool_key not in self._pools:
            self._pools[pool_key] = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=10,
                pool_pre_ping=True,  # 连接前检查
                pool_recycle=3600,  # 1小时回收连接
                echo=False,
            )

        return self._pools[pool_key]

    def close_all_pools(self):
        """关闭所有连接池"""
        for engine in self._pools.values():
            engine.dispose()
        self._pools.clear()


class DataSourceService:
    """数据源服务"""

    def __init__(self):
        self.connection_manager = ConnectionPoolManager()
        self.logger = logger

    async def create_data_source(
        self, source_config: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """创建数据源"""
        try:
            with get_db_session() as db:
                # 验证配置
                validated_config = await self._validate_source_config(source_config)

                # 加密敏感信息
                if validated_config.get("connection_string"):
                    validated_config["connection_string"] = encrypt_data(
                        validated_config["connection_string"]
                    )

                # 创建数据源
                from app.schemas.data_source import DataSourceCreate

                source_data = DataSourceCreate(
                    **validated_config, user_id=user_id
                )

                data_source = crud.data_source.create(
                    db=db, obj_in=source_data
                )

                # 测试连接
                test_result = await self.test_connection(str(data_source.id))

                return {
                    "id": data_source.id,
                    "name": data_source.name,
                    "source_type": data_source.source_type,
                    "connection_test": test_result,
                    "created_at": data_source.created_at,
                }

        except Exception as e:
            self.logger.error(f"Failed to create data source: {e}")
            raise ValueError(f"Failed to create data source: {str(e)}")

    async def _validate_source_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证数据源配置"""
        source_type = config.get("source_type")

        if source_type == DataSourceType.sql:
            return await self._validate_sql_config(config)
        elif source_type == DataSourceType.api:
            return await self._validate_api_config(config)
        elif source_type == DataSourceType.csv:
            return await self._validate_csv_config(config)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    async def _validate_sql_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证SQL数据源配置"""
        connection_string = config.get("connection_string")
        if not connection_string:
            raise ValueError("SQL data source requires connection_string")

        # 验证连接字符串格式
        validate_connection_string(connection_string)

        # 验证SQL查询配置
        query_type = config.get("sql_query_type", SQLQueryType.single_table)

        if query_type == SQLQueryType.multi_table:
            join_config = config.get("join_config")
            if not join_config:
                raise ValueError("Multi-table query requires join_config")

            # 验证联表配置
            await self._validate_join_config(join_config)

        return config

    async def _validate_join_config(self, join_config: Dict[str, Any]):
        """验证联表配置"""
        required_fields = ["tables", "joins"]
        for field in required_fields:
            if field not in join_config:
                raise ValueError(f"Join config missing required field: {field}")

        # 验证表配置
        tables = join_config["tables"]
        if not isinstance(tables, list) or len(tables) < 2:
            raise ValueError("Join config requires at least 2 tables")

        # 验证连接配置
        joins = join_config["joins"]
        if not isinstance(joins, list) or len(joins) < 1:
            raise ValueError("Join config requires at least 1 join condition")

    async def _validate_api_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证API数据源配置"""
        api_url = config.get("api_url")
        if not api_url:
            raise ValueError("API data source requires api_url")

        # 验证URL格式
        if not api_url.startswith(("http://", "https://")):
            raise ValueError("API URL must start with http:// or https://")

        return config

    async def _validate_csv_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证CSV数据源配置"""
        file_path = config.get("file_path")
        if not file_path:
            raise ValueError("CSV data source requires file_path")

        # 验证文件存在性
        import os

        if not os.path.exists(file_path):
            raise ValueError(f"CSV file not found: {file_path}")

        return config

    async def test_connection(self, source_id: str) -> Dict[str, Any]:
        """测试数据源连接"""
        try:
            with get_db_session() as db:
                data_source = crud.data_source.get(db, id=source_id)
                if not data_source:
                    raise ValueError("Data source not found")

                if data_source.source_type == DataSourceType.sql:
                    return await self._test_sql_connection(data_source)
                elif data_source.source_type == DataSourceType.doris:
                    return await self._test_doris_connection(data_source)
                elif data_source.source_type == DataSourceType.api:
                    return await self._test_api_connection(data_source)
                elif data_source.source_type == DataSourceType.csv:
                    return await self._test_csv_connection(data_source)
                else:
                    raise ValueError(
                        f"Unsupported source type: {data_source.source_type}"
                    )

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _test_sql_connection(self, data_source) -> Dict[str, Any]:
        """测试SQL连接"""
        try:
            # 解密连接字符串
            connection_string = decrypt_data(data_source.connection_string)

            # 获取引擎
            engine = self.connection_manager.get_engine(connection_string)

            # 测试连接
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                test_value = result.fetchone()[0]

                if test_value == 1:
                    return {
                        "success": True,
                        "message": "SQL connection successful",
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    raise ValueError("Unexpected test result")

        except Exception as e:
            raise ValueError(f"SQL connection failed: {str(e)}")

    async def _test_doris_connection(self, data_source) -> Dict[str, Any]:
        """测试Doris连接"""
        try:
            # 创建Doris连接器
            connector = create_doris_connector(data_source)
            
            # 测试连接
            async with connector:
                result = await connector.test_connection()
                
                if result["success"]:
                    return {
                        "success": True,
                        "message": "Doris connection successful",
                        "fe_host": result.get("fe_host", ""),
                        "database": result.get("database", ""),
                        "execution_time": result.get("execution_time", 0),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise ValueError(result.get("error", "Unknown error"))
                    
        except Exception as e:
            raise ValueError(f"Doris connection failed: {str(e)}")

    async def _test_api_connection(self, data_source) -> Dict[str, Any]:
        """测试API连接"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method=data_source.api_method or "GET",
                    url=data_source.api_url,
                    headers=data_source.api_headers or {},
                    json=data_source.api_body,
                )
                response.raise_for_status()

                return {
                    "success": True,
                    "message": "API connection successful",
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            raise ValueError(f"API connection failed: {str(e)}")

    async def _test_csv_connection(self, data_source) -> Dict[str, Any]:
        """测试CSV文件访问"""
        try:
            # 尝试读取文件头部
            df = pd.read_csv(data_source.file_path, nrows=1)

            return {
                "success": True,
                "message": "CSV file access successful",
                "columns": df.columns.tolist(),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            raise ValueError(f"CSV file access failed: {str(e)}")

    async def fetch_data(
        self, source_id: str, query_params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """从数据源获取数据"""
        with get_db_session() as db:
            data_source = crud.data_source.get(db, id=source_id)
            if not data_source:
                raise ValueError("Data source not found")

            if data_source.source_type == DataSourceType.sql:
                return await self._fetch_sql_data(data_source, query_params)
            elif data_source.source_type == DataSourceType.doris:
                return await self._fetch_doris_data(data_source, query_params)
            elif data_source.source_type == DataSourceType.api:
                return await self._fetch_api_data(data_source, query_params)
            elif data_source.source_type == DataSourceType.csv:
                return await self._fetch_csv_data(data_source, query_params)
            else:
                raise ValueError(f"Unsupported source type: {data_source.source_type}")

    async def _fetch_sql_data(
        self, data_source, query_params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """从SQL数据源获取数据"""
        try:
            # 解密连接字符串
            connection_string = decrypt_data(data_source.connection_string)

            # 获取引擎
            engine = self.connection_manager.get_engine(connection_string)

            # 构建查询
            if data_source.sql_query_type == SQLQueryType.multi_table:
                query = await self._build_multi_table_query(data_source, query_params)
            else:
                query = data_source.base_query or "SELECT * FROM your_table LIMIT 1000"

            # 执行查询
            df = pd.read_sql(query, engine)

            # 应用列映射
            if data_source.column_mapping:
                df = self._apply_column_mapping(df, data_source.column_mapping)

            return df

        except Exception as e:
            self.logger.error(f"Failed to fetch SQL data: {e}")
            raise ValueError(f"Failed to fetch SQL data: {str(e)}")

    async def _fetch_doris_data(
        self, data_source, query_params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """从Doris数据源获取数据"""
        try:
            # 创建Doris连接器
            connector = create_doris_connector(data_source)
            
            # 构建查询
            query = data_source.base_query or f"SELECT * FROM {data_source.wide_table_name or 'default_table'} LIMIT 1000"
            
            # 应用查询参数
            if query_params:
                if "limit" in query_params:
                    # 替换或添加LIMIT子句
                    if "LIMIT" not in query.upper():
                        query += f" LIMIT {query_params['limit']}"
                    else:
                        # 简单替换LIMIT值
                        import re
                        query = re.sub(r'LIMIT\s+\d+', f'LIMIT {query_params["limit"]}', query, flags=re.IGNORECASE)
            
            # 执行查询（使用优化提示）
            optimization_hints = ["vectorization", "partition_pruning"]
            
            async with connector:
                result = await connector.execute_optimized_query(query, optimization_hints)
                
                self.logger.info(
                    f"Doris query executed: {len(result.data)} rows in {result.execution_time:.3f}s, "
                    f"scanned {result.rows_scanned} rows, cached: {result.is_cached}"
                )
                
                return result.data
                
        except Exception as e:
            self.logger.error(f"Failed to fetch Doris data: {e}")
            raise ValueError(f"Failed to fetch Doris data: {str(e)}")

    async def _build_multi_table_query(
        self, data_source, query_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建多表联查SQL"""
        join_config = data_source.join_config
        if not join_config:
            raise ValueError("Multi-table query requires join_config")

        # 构建SELECT子句
        tables = join_config["tables"]
        select_fields = []

        for table in tables:
            table_name = table["name"]
            fields = table.get("fields", ["*"])

            for field in fields:
                if field == "*":
                    select_fields.append(f"{table_name}.*")
                else:
                    alias = field.get("alias") if isinstance(field, dict) else None
                    field_name = field.get("name") if isinstance(field, dict) else field

                    if alias:
                        select_fields.append(f"{table_name}.{field_name} AS {alias}")
                    else:
                        select_fields.append(f"{table_name}.{field_name}")

        # 构建FROM子句
        main_table = tables[0]["name"]
        query = f"SELECT {', '.join(select_fields)} FROM {main_table}"

        # 构建JOIN子句
        joins = join_config["joins"]
        for join in joins:
            join_type = join.get("type", "INNER")
            left_table = join["left_table"]
            right_table = join["right_table"]
            condition = join["condition"]

            query += f" {join_type} JOIN {right_table} ON {condition}"

        # 添加WHERE条件
        if data_source.where_conditions:
            conditions = []
            for condition in data_source.where_conditions:
                conditions.append(condition["expression"])

            if conditions:
                query += f" WHERE {' AND '.join(conditions)}"

        # 添加查询参数
        if query_params:
            limit = query_params.get("limit", 1000)
            query += f" LIMIT {limit}"

        return query

    def _apply_column_mapping(
        self, df: pd.DataFrame, column_mapping: Dict[str, str]
    ) -> pd.DataFrame:
        """应用列映射"""
        try:
            # 重命名列
            df = df.rename(columns=column_mapping)
            return df
        except Exception as e:
            self.logger.warning(f"Failed to apply column mapping: {e}")
            return df

    async def _fetch_api_data(
        self, data_source, query_params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """从API数据源获取数据"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 合并查询参数
                params = query_params or {}

                response = await client.request(
                    method=data_source.api_method or "GET",
                    url=data_source.api_url,
                    headers=data_source.api_headers or {},
                    json=data_source.api_body,
                    params=params,
                )
                response.raise_for_status()

                data = response.json()

                # 转换为DataFrame
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                elif isinstance(data, dict):
                    # 尝试找到数据数组
                    if "data" in data:
                        df = pd.DataFrame(data["data"])
                    elif "items" in data:
                        df = pd.DataFrame(data["items"])
                    else:
                        df = pd.DataFrame([data])
                else:
                    df = pd.DataFrame([{"value": data}])

                return df

        except Exception as e:
            self.logger.error(f"Failed to fetch API data: {e}")
            raise ValueError(f"Failed to fetch API data: {str(e)}")

    async def _fetch_csv_data(
        self, data_source, query_params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """从CSV文件获取数据"""
        try:
            # 读取CSV文件
            read_params = {}

            if query_params:
                if "nrows" in query_params:
                    read_params["nrows"] = query_params["nrows"]
                if "skiprows" in query_params:
                    read_params["skiprows"] = query_params["skiprows"]

            df = pd.read_csv(data_source.file_path, **read_params)

            return df

        except Exception as e:
            self.logger.error(f"Failed to fetch CSV data: {e}")
            raise ValueError(f"Failed to fetch CSV data: {str(e)}")

    async def sync_data_source(self, source_id: str) -> Dict[str, Any]:
        """同步数据源"""
        try:
            # 获取数据预览以验证数据源连接
            preview_data = await self.get_data_preview(source_id, limit=10)
            
            return {
                "success": True,
                "message": "数据源同步成功",
                "records_count": preview_data.get("row_count", 0),
                "columns_count": preview_data.get("total_columns", 0),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to sync data source: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_data_preview(self, source_id: str, limit: int = 10) -> Dict[str, Any]:
        """获取数据预览"""
        try:
            df = await self.fetch_data(source_id, {"limit": limit, "nrows": limit})

            return {
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
                "row_count": len(df),
                "total_columns": len(df.columns),
                "data_types": df.dtypes.astype(str).to_dict(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get data preview: {e}")
            raise ValueError(f"Failed to get data preview: {str(e)}")

    def __del__(self):
        """清理连接池"""
        self.connection_manager.close_all_pools()


# 全局服务实例
data_source_service = DataSourceService()
