"""
Schema相关工具

提供数据库架构查询和分析功能
"""

import logging
from typing import Dict, Any, List

from .base import Tool


class SchemaListColumnsTool(Tool):
    """数据库表列信息查询工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "schema.list_columns"
        self.description = "列出数据库表的列信息"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """查询表列信息"""
        try:
            tables = input_data.get("tables", [])
            if not tables:
                # 从上下文中获取表信息
                tables = input_data.get("schema", {}).get("tables", [])

            if not tables:
                return {
                    "success": True,
                    "tables": [],
                    "columns": {},
                    "message": "未指定查询表"
                }

            # 获取数据源服务
            data_source_service = getattr(self.container, 'data_source_service', None) or getattr(self.container, 'data_source', None)
            if not data_source_service:
                # 如果没有数据源服务，返回已有的列信息
                existing_columns = input_data.get("columns", {})
                return {
                    "success": True,
                    "tables": tables,
                    "columns": existing_columns,
                    "message": "使用已有列信息"
                }

            # 查询每个表的列信息
            all_columns = {}
            for table in tables:
                try:
                    columns = await self._get_table_columns(data_source_service, table, input_data)
                    all_columns[table] = columns
                except Exception as e:
                    self._logger.warning(f"获取表 {table} 列信息失败: {str(e)}")
                    all_columns[table] = []

            return {
                "success": True,
                "tables": tables,
                "columns": all_columns,
                "message": f"已获取 {len(tables)} 个表的列信息"
            }

        except Exception as e:
            self._logger.error(f"查询列信息失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _get_table_columns(self, data_source_service, table: str, context: Dict[str, Any]) -> List[str]:
        """获取指定表的列信息"""
        try:
            data_source_config = context.get("data_source", {})

            # 尝试不同的列查询方法
            if hasattr(data_source_service, 'get_table_columns'):
                result = await data_source_service.get_table_columns(table, data_source_config)
                return result if isinstance(result, list) else result.get("columns", [])
            elif hasattr(data_source_service, 'list_columns'):
                result = await data_source_service.list_columns(data_source_config, table)
                return result if isinstance(result, list) else result.get("columns", [])
            else:
                # 通过SQL查询获取列信息
                sql = f"SELECT * FROM {table} LIMIT 0"
                if hasattr(data_source_service, 'execute_query'):
                    result = await data_source_service.execute_query(sql, data_source_config)
                    return result.get("columns", [])

            return []

        except Exception as e:
            self._logger.error(f"获取表 {table} 列信息异常: {str(e)}")
            return []


class EnhancedSchemaListColumnsTool(Tool):
    """增强的数据库架构查询工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "enhanced_schema.list_columns"
        self.description = "增强的数据库表列信息查询，包含类型和约束信息"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """查询增强的表列信息"""
        try:
            tables = input_data.get("tables", [])
            if not tables:
                tables = input_data.get("schema", {}).get("tables", [])

            if not tables:
                return {
                    "success": True,
                    "tables": [],
                    "schema_info": {},
                    "message": "未指定查询表"
                }

            # 获取数据源服务
            data_source_service = getattr(self.container, 'data_source_service', None) or getattr(self.container, 'data_source', None)
            if not data_source_service:
                return {"success": False, "error": "Data source service not available"}

            # 查询每个表的详细信息
            schema_info = {}
            for table in tables:
                try:
                    table_info = await self._get_enhanced_table_info(data_source_service, table, input_data)
                    schema_info[table] = table_info
                except Exception as e:
                    self._logger.warning(f"获取表 {table} 详细信息失败: {str(e)}")
                    schema_info[table] = {"columns": [], "types": {}, "constraints": {}}

            return {
                "success": True,
                "tables": tables,
                "schema_info": schema_info,
                "message": f"已获取 {len(tables)} 个表的详细架构信息"
            }

        except Exception as e:
            self._logger.error(f"查询增强列信息失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _get_enhanced_table_info(self, data_source_service, table: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """获取表的详细信息"""
        try:
            data_source_config = context.get("data_source", {})

            # 基础列信息
            columns = []
            column_types = {}
            constraints = {}

            # 尝试获取详细架构信息的SQL
            schema_sql = f"""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """

            if hasattr(data_source_service, 'execute_query'):
                try:
                    result = await data_source_service.execute_query(schema_sql, data_source_config)
                    rows = result.get("rows", [])

                    for row in rows:
                        if len(row) >= 4:
                            col_name, data_type, is_nullable, default_val = row[0], row[1], row[2], row[3]
                            columns.append(col_name)
                            column_types[col_name] = data_type
                            constraints[col_name] = {
                                "nullable": is_nullable == "YES",
                                "default": default_val
                            }
                except Exception:
                    # 如果schema查询失败，降级到基础查询
                    basic_result = await data_source_service.execute_query(f"SELECT * FROM {table} LIMIT 0", data_source_config)
                    columns = basic_result.get("columns", [])

            return {
                "columns": columns,
                "types": column_types,
                "constraints": constraints
            }

        except Exception as e:
            self._logger.error(f"获取表 {table} 详细信息异常: {str(e)}")
            return {"columns": [], "types": {}, "constraints": {}}