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
                # 强约束：旧工具不再负责列举表，请先列出表再指定 tables
                return {
                    "success": False,
                    "error": "tables_required",
                    "message": "请先调用 schema.list_tables 获取表名，然后使用 schema.get_columns 并在 input.tables 指定目标表名"
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

            # 优先使用已经传递的列信息，避免重复查询（仅当结构为 {table: [cols]} 且至少一个非空时）
            all_columns = {}
            existing_columns = input_data.get("columns", {})

            def _is_valid_columns_map(obj) -> bool:
                return isinstance(obj, dict) and all(
                    isinstance(v, list) for v in obj.values()
                )

            def _has_any_columns(obj) -> bool:
                try:
                    return any(isinstance(v, list) and len(v) > 0 for v in obj.values())
                except Exception:
                    return False

            explicit_tables = isinstance(input_data.get("tables"), list) and len(input_data.get("tables")) > 0

            if (not explicit_tables) and _is_valid_columns_map(existing_columns) and _has_any_columns(existing_columns):
                self._logger.info(
                    f"🔍 [SchemaListColumnsTool] 使用已传递的列信息: {len(existing_columns)}个表（含非空列）"
                )
                all_columns = existing_columns
            else:
                # 否则查询每个表的列信息
                self._logger.info(f"🔍 [SchemaListColumnsTool] 需要重新查询列信息")
                for table in tables:
                    try:
                        # 优先使用 SHOW FULL COLUMNS 获取更完整信息
                        if hasattr(self.container, 'data_source') and hasattr(self.container.data_source, 'run_query'):
                            try:
                                result = await self.container.data_source.run_query(
                                    connection_config=input_data.get("data_source", {}),
                                    sql=f"SHOW FULL COLUMNS FROM {table}",
                                    limit=1000
                                )
                                cols = []
                                detailed_cols = []  # 存储详细的字段信息

                                for row in result.get("rows", []) or result.get("data", []) or []:
                                    if isinstance(row, dict):
                                        field_name = row.get("Field")
                                        if field_name:
                                            cols.append(field_name)
                                            # 构建详细的字段信息
                                            field_info = {
                                                "name": field_name,
                                                "type": row.get("Type", ""),
                                                "nullable": row.get("Null", ""),
                                                "key": row.get("Key", ""),
                                                "default": row.get("Default", ""),
                                                "extra": row.get("Extra", ""),
                                                "comment": row.get("Comment", "")
                                            }
                                            detailed_cols.append(field_info)
                                    elif isinstance(row, list) and len(row) > 0:
                                        field_name = row[0]
                                        cols.append(field_name)
                                        # 尝试从列表中提取详细信息
                                        field_info = {
                                            "name": field_name,
                                            "type": row[1] if len(row) > 1 else "",
                                            "nullable": row[2] if len(row) > 2 else "",
                                            "key": row[3] if len(row) > 3 else "",
                                            "default": row[4] if len(row) > 4 else "",
                                            "extra": row[5] if len(row) > 5 else "",
                                            "comment": row[8] if len(row) > 8 else ""  # SHOW FULL COLUMNS的Comment在第9列
                                        }
                                        detailed_cols.append(field_info)

                                if not cols:
                                    # 回退到基础方式
                                    cols = await self._get_table_columns(data_source_service, table, input_data)
                                    detailed_cols = [{"name": col, "type": "", "comment": ""} for col in cols]

                                all_columns[table] = cols
                                # 存储详细信息，供schema_summary使用
                                if not hasattr(self, '_detailed_columns'):
                                    self._detailed_columns = {}
                                self._detailed_columns[table] = detailed_cols
                            except Exception:
                                cols = await self._get_table_columns(data_source_service, table, input_data)
                                all_columns[table] = cols
                        else:
                            columns = await self._get_table_columns(data_source_service, table, input_data)
                            all_columns[table] = columns
                    except Exception as e:
                        self._logger.warning(f"获取表 {table} 列信息失败: {str(e)}")
                        all_columns[table] = []

            # 为LLM构建友好的schema描述
            schema_descriptions = []
            table_count = 0
            column_count = 0

            for table in tables:
                table_columns = all_columns.get(table, []) if _is_valid_columns_map(all_columns) else []
                if table_columns:
                    table_count += 1
                    column_count += len(table_columns)

                    # 构建表描述，包含详细字段信息
                    detailed_cols = getattr(self, '_detailed_columns', {}).get(table, [])

                    if detailed_cols:
                        # 使用详细信息构建更丰富的描述
                        column_details = []
                        for col_info in detailed_cols:
                            name = col_info.get("name", "")
                            col_type = col_info.get("type", "")
                            comment = col_info.get("comment", "")
                            key_info = col_info.get("key", "")

                            # 构建字段描述
                            col_desc = name
                            if col_type:
                                col_desc += f"({col_type})"
                            if key_info == "PRI":
                                col_desc += "[主键]"
                            elif key_info:
                                col_desc += f"[{key_info}]"
                            if comment:
                                col_desc += f" '{comment}'"

                            column_details.append(col_desc)

                        columns_text = '; '.join(column_details)
                        schema_descriptions.append(f"**{table}** ({len(table_columns)}列):\n  {columns_text}")
                    else:
                        # 回退到简单列表
                        column_list = ', '.join(table_columns)
                        schema_descriptions.append(f"**{table}** ({len(table_columns)}列): {column_list}")
                else:
                    schema_descriptions.append(f"**{table}**: 无列信息")

            # LLM友好的schema总结
            schema_summary = f"数据库包含 {table_count} 个表，共 {column_count} 个列。\n" + \
                           "\n".join(schema_descriptions)

            result = {
                "success": True,
                "tables": tables,
                "columns": all_columns,
                "column_details": getattr(self, '_detailed_columns', {}),  # 详细字段信息
                "schema_summary": schema_summary,  # 新增：LLM友好的描述
                "table_count": table_count,
                "column_count": column_count,
                "schema_descriptions": schema_descriptions,  # 新增：结构化描述
                "message": f"已获取 {table_count} 个表的列信息，共 {column_count} 个列"
            }

            self._logger.info(f"🔍 [SchemaListColumnsTool] 输出结果: {table_count}个表, {column_count}个列")
            self._logger.info(f"🔍 [SchemaListColumnsTool] 表名: {tables}")
            self._logger.info(f"🔍 [SchemaListColumnsTool] Schema摘要前200字符: {schema_summary[:200]}...")
            self._logger.info(f"🔍 [SchemaListColumnsTool] 详细列信息: {all_columns}")

            return result

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


class SchemaListTablesTool(Tool):
    """列出数据库中的所有表（仅表名，不含列）。"""

    def __init__(self, container):
        super().__init__()
        self.name = "schema.list_tables"
        self.description = "列出数据库中的所有表名"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 🔍 [Debug] 检查数据源配置
            conn_cfg = input_data.get("data_source", {})
            self._logger.info(f"🔍 [SchemaListTables Debug] input_data keys: {list(input_data.keys())}")
            self._logger.info(f"🔍 [SchemaListTables Debug] data_source存在: {bool(conn_cfg)}")
            if conn_cfg:
                self._logger.info(f"🔍 [SchemaListTables Debug] data_source keys: {list(conn_cfg.keys())}")
                self._logger.info(f"🔍 [SchemaListTables Debug] host: {conn_cfg.get('host', 'N/A')}")
            else:
                self._logger.warning(f"❌ [SchemaListTables Debug] 缺少data_source配置！")

            if not (hasattr(self.container, 'data_source') and hasattr(self.container.data_source, 'run_query')):
                return {"success": False, "error": "Data source service not available"}

            result = await self.container.data_source.run_query(
                connection_config=conn_cfg,
                sql="SHOW TABLES",
                limit=10000
            )
            raw_rows = result.get("rows") or result.get("data") or []
            tables: List[str] = []
            for row in raw_rows:
                if isinstance(row, dict):
                    tables.append(list(row.values())[0])
                elif isinstance(row, list) and len(row) > 0:
                    tables.append(row[0])
                elif isinstance(row, str):
                    tables.append(row)

            tables = [t for t in tables if t]
            self._logger.info(f"🔍 [SchemaListTablesTool] 共发现 {len(tables)} 个表")
            return {
                "success": True,
                "tables": tables,
                "message": f"已发现 {len(tables)} 个表"
            }
        except Exception as e:
            self._logger.error(f"列出表失败: {e}")
            return {"success": False, "error": str(e)}


class UnifiedSchemaTool(Tool):
    """统一的schema查询工具 - 一次调用获取表名和列信息"""

    def __init__(self, container):
        super().__init__()
        self.name = "schema.unified_query"
        self.description = "统一查询数据库schema信息，包含表名和列信息"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """统一查询schema信息"""
        try:
            # 检查数据源
            if not (hasattr(self.container, 'data_source') and hasattr(self.container.data_source, 'run_query')):
                return {"success": False, "error": "Data source service not available"}

            # 获取指定表或所有表
            target_tables = input_data.get("tables", [])
            if isinstance(target_tables, str):
                target_tables = [target_tables]

            # 如果没有指定表，先获取所有表
            if not target_tables:
                try:
                    tables_result = await self.container.data_source.run_query(
                        connection_config=input_data.get("data_source", {}),
                        sql="SHOW TABLES",
                        limit=10000
                    )

                    raw_rows = tables_result.get("rows", []) or tables_result.get("data", []) or []
                    for row in raw_rows:
                        if isinstance(row, dict):
                            target_tables.append(list(row.values())[0])
                        elif isinstance(row, list) and len(row) > 0:
                            target_tables.append(row[0])
                        elif isinstance(row, str):
                            target_tables.append(row)

                    target_tables = [t for t in target_tables if t]
                    self._logger.info(f"🔍 [UnifiedSchemaTool] 发现 {len(target_tables)} 个表")

                except Exception as e:
                    self._logger.error(f"获取表列表失败: {e}")
                    return {"success": False, "error": f"Failed to get tables list: {str(e)}"}

            if not target_tables:
                return {
                    "success": True,
                    "tables": [],
                    "columns": {},
                    "schema_summary": "数据库中未发现任何表",
                    "table_count": 0,
                    "column_count": 0,
                    "message": "数据库中未发现任何表"
                }

            # 获取每个表的列信息（包含多重回退）
            columns_map = {}
            conn_cfg = input_data.get("data_source", {})
            db_name = conn_cfg.get("database") or conn_cfg.get("db") or conn_cfg.get("schema")
            for table in target_tables:
                try:
                    # 尝试SHOW FULL COLUMNS查询
                    result = await self.container.data_source.run_query(
                        connection_config=conn_cfg,
                        sql=f"SHOW FULL COLUMNS FROM {table}",
                        limit=1000
                    )

                    cols = []
                    rows = result.get("rows", []) or result.get("data", []) or []

                    for row in rows:
                        if isinstance(row, dict) and row.get("Field"):
                            cols.append(row.get("Field"))
                        elif isinstance(row, list) and len(row) > 0:
                            cols.append(str(row[0]))
                        elif isinstance(row, str):
                            cols.append(row)

                    columns_map[table] = cols
                    if cols:
                        self._logger.info(f"🔍 [UnifiedSchemaTool] 表 {table}: {len(cols)} 列")
                    if not cols:
                        # 回退1：DESC
                        try:
                            # DESC命令不支持LIMIT，不传递limit参数
                            desc_result = await self.container.data_source.run_query(
                                connection_config=conn_cfg,
                                sql=f"DESC {table}"
                            )
                            drows = desc_result.get("rows", []) or desc_result.get("data", []) or []

                            # 处理DataFrame对象（UnifiedSchemaTool版本）
                            import pandas as pd
                            if isinstance(drows, pd.DataFrame):
                                if not drows.empty:
                                    drows = drows.to_dict('records')
                                else:
                                    drows = []
                            desc_cols = []
                            for row in drows:
                                if isinstance(row, dict) and row.get("Field"):
                                    desc_cols.append(row.get("Field"))
                                elif isinstance(row, list) and len(row) > 0:
                                    desc_cols.append(str(row[0]))
                            columns_map[table] = desc_cols
                            cols = desc_cols
                            if desc_cols:
                                self._logger.info(f"🔍 [UnifiedSchemaTool] 表 {table} (via DESC): {len(desc_cols)} 列")
                        except Exception as desc_e:
                            self._logger.warning(f"DESC {table} 也失败: {desc_e}")

                    if not cols:
                        # 回退2：information_schema.columns
                        try:
                            if db_name:
                                info_sql = (
                                    "SELECT COLUMN_NAME FROM information_schema.columns "
                                    f"WHERE TABLE_SCHEMA='{db_name}' AND TABLE_NAME='{table}' ORDER BY ORDINAL_POSITION"
                                )
                            else:
                                info_sql = (
                                    "SELECT COLUMN_NAME FROM information_schema.columns "
                                    f"WHERE TABLE_NAME='{table}' ORDER BY ORDINAL_POSITION"
                                )
                            info_result = await self.container.data_source.run_query(
                                connection_config=conn_cfg,
                                sql=info_sql,
                                limit=5000
                            )
                            irows = info_result.get("rows", []) or info_result.get("data", []) or []
                            info_cols = []
                            for row in irows:
                                if isinstance(row, dict):
                                    info_cols.append(row.get("COLUMN_NAME") or row.get("column_name") or list(row.values())[0])
                                elif isinstance(row, list) and len(row) > 0:
                                    info_cols.append(str(row[0]))
                                elif isinstance(row, str):
                                    info_cols.append(row)
                            columns_map[table] = info_cols
                            if info_cols:
                                self._logger.info(f"🔍 [UnifiedSchemaTool] 表 {table} (via information_schema): {len(info_cols)} 列")
                        except Exception as info_e:
                            self._logger.warning(f"information_schema 查询失败: table={table}, err={info_e}")

                except Exception as e:
                    self._logger.warning(f"获取表 {table} 列信息失败: {e}")
                    columns_map[table] = []

            # 构建友好的schema描述
            schema_descriptions = []
            table_count = 0
            total_column_count = 0

            for table in target_tables:
                table_cols = columns_map.get(table, [])
                if table_cols:
                    table_count += 1
                    total_column_count += len(table_cols)
                    col_list = ', '.join(table_cols[:10])  # 只显示前10列避免太长
                    if len(table_cols) > 10:
                        col_list += f"... (+{len(table_cols) - 10} more)"
                    schema_descriptions.append(f"**{table}** ({len(table_cols)}列): {col_list}")
                else:
                    schema_descriptions.append(f"**{table}**: 无列信息")

            schema_summary = f"数据库包含 {table_count} 个有效表，共 {total_column_count} 个列。\n" + "\n".join(schema_descriptions)

            result = {
                "success": True,
                "tables": target_tables,
                "columns": columns_map,
                "schema_summary": schema_summary,
                "table_count": table_count,
                "column_count": total_column_count,
                "schema_descriptions": schema_descriptions,
                "message": f"已获取 {table_count} 个表的schema信息，共 {total_column_count} 个列"
            }

            self._logger.info(f"🎯 [UnifiedSchemaTool] 成功返回: {table_count}个表, {total_column_count}个列")
            return result

        except Exception as e:
            self._logger.error(f"统一schema查询失败: {str(e)}")
            return {"success": False, "error": str(e)}


class SchemaGetColumnsTool(Tool):
    """获取一个或多个指定表的列信息（强制需要 tables）。"""

    def __init__(self, container):
        super().__init__()
        self.name = "schema.get_columns"
        self.description = "获取指定表的列信息（SHOW FULL COLUMNS）"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            tables = input_data.get("tables")
            if isinstance(tables, str):
                tables = [tables]
            if not tables or not isinstance(tables, list):
                return {"success": False, "error": "tables_required", "message": "请在 input.tables 指定要查询的表名数组或字符串"}

            if not (hasattr(self.container, 'data_source') and hasattr(self.container.data_source, 'run_query')):
                return {"success": False, "error": "Data source service not available"}

            columns_map: Dict[str, List[str]] = {}
            details_map: Dict[str, Dict[str, Dict[str, Any]]] = {}
            conn_cfg = input_data.get("data_source", {})
            db_name = conn_cfg.get("database") or conn_cfg.get("db") or conn_cfg.get("schema")

            # 详细检查连接配置
            if not conn_cfg:
                self._logger.warning(f"📋 [SchemaGetColumns] ⚠️ 没有提供data_source连接配置，无法查询真实数据库")
                return {
                    "success": True,  # 保持成功状态以避免阻塞
                    "tables": tables,
                    "columns": {table: [] for table in tables},
                    "column_details": {},
                    "schema_summary": {table: f"⚠️ 表{table}: 无连接配置，未获取列信息" for table in tables},
                    "table_count": len(tables),
                    "column_count": 0,
                    "schema_descriptions": [f"⚠️ 缺少数据库连接配置，建议检查data_source_id参数"],
                    "message": f"⚠️ 缺少连接配置，返回空列信息。表数量: {len(tables)}"
                }

            # 记录连接配置信息（安全日志）
            self._logger.info(f"📋 [SchemaGetColumns] 连接配置键: {list(conn_cfg.keys())}")
            if conn_cfg.get("host"):
                self._logger.info(f"📋 [SchemaGetColumns] 连接目标: {conn_cfg.get('host')}:{conn_cfg.get('port', 'default')}")
            if db_name:
                self._logger.info(f"📋 [SchemaGetColumns] 目标数据库: {db_name}")

            for table in tables:
                try:
                    query_sql = f"SHOW FULL COLUMNS FROM {table}"
                    self._logger.info(f"📋 [SchemaGetColumns] 执行查询: {query_sql}")
                    # SHOW FULL COLUMNS不支持LIMIT，不传递limit参数
                    result = await self.container.data_source.run_query(
                        connection_config=conn_cfg,
                        sql=query_sql
                    )
                    self._logger.info(f"📋 [SchemaGetColumns] 查询结果键: {list(result.keys()) if isinstance(result, dict) else 'Not dict'}")

                    cols: List[str] = []
                    details: Dict[str, Dict[str, Any]] = {}
                    rows = result.get("rows", []) or result.get("data", []) or []

                    # 处理DataFrame对象
                    import pandas as pd
                    if isinstance(rows, pd.DataFrame):
                        if not rows.empty:
                            rows = rows.to_dict('records')  # 转换为字典列表
                        else:
                            rows = []

                    row_count = len(rows) if hasattr(rows, '__len__') else 0
                    self._logger.info(f"📋 [SchemaGetColumns] 表{table}返回{row_count}行数据")
                    if row_count > 0:
                        self._logger.info(f"📋 [SchemaGetColumns] 第一行样例: {rows[0]}")
                    else:
                        self._logger.warning(f"📋 [SchemaGetColumns] 表{table}没有返回列信息，result结构: {result}")

                    for row in rows:
                        if isinstance(row, dict) and row.get("Field"):
                            col = row.get("Field")
                            cols.append(col)
                            details[col] = {
                                "type": row.get("Type"),
                                "nullable": True if str(row.get("Null")).upper() == "YES" else (False if str(row.get("Null")).upper() == "NO" else None),
                                "key": row.get("Key"),
                                "default": row.get("Default"),
                                "extra": row.get("Extra"),
                                "comment": row.get("Comment"),
                            }
                        elif isinstance(row, list) and len(row) > 0:
                            cols.append(row[0])
                    columns_map[table] = cols
                    if details:
                        details_map[table] = details
                    if not cols:
                        # 尝试 DESC 作为回退
                        self._logger.info(f"📋 [SchemaGetColumns] SHOW FULL COLUMNS失败，尝试DESC回退 - 表{table}")
                        try:
                            desc_sql = f"DESC {table}"
                            self._logger.info(f"📋 [SchemaGetColumns] 执行DESC查询: {desc_sql}")
                            # DESC命令不支持LIMIT，不传递limit参数
                            desc_result = await self.container.data_source.run_query(
                                connection_config=conn_cfg,
                                sql=desc_sql
                            )
                            drows = desc_result.get("rows", []) or desc_result.get("data", []) or []

                            # 处理DataFrame对象
                            if isinstance(drows, pd.DataFrame):
                                if not drows.empty:
                                    drows = drows.to_dict('records')
                                else:
                                    drows = []

                            drow_count = len(drows) if hasattr(drows, '__len__') else 0
                            self._logger.info(f"📋 [SchemaGetColumns] DESC查询返回{drow_count}行")
                            desc_cols: List[str] = []
                            ddetails: Dict[str, Dict[str, Any]] = {}
                            for row in drows:
                                if isinstance(row, dict) and row.get("Field"):
                                    col = row.get("Field")
                                    desc_cols.append(col)
                                    ddetails[col] = {
                                        "type": row.get("Type"),
                                        "nullable": True if str(row.get("Null")).upper() == "YES" else (False if str(row.get("Null")).upper() == "NO" else None),
                                        "key": row.get("Key"),
                                        "default": row.get("Default"),
                                        "extra": row.get("Extra"),
                                        "comment": None,
                                    }
                                elif isinstance(row, list) and len(row) > 0:
                                    desc_cols.append(row[0])
                            columns_map[table] = desc_cols
                            cols = desc_cols
                            if ddetails:
                                details_map[table] = ddetails
                        except Exception:
                            pass
                    if not cols:
                        # 最后回退到 information_schema.columns
                        try:
                            if db_name:
                                info_sql = (
                                    "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT "
                                    "FROM information_schema.columns "
                                    f"WHERE TABLE_SCHEMA='{db_name}' AND TABLE_NAME='{table}' ORDER BY ORDINAL_POSITION"
                                )
                            else:
                                info_sql = (
                                    "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT "
                                    "FROM information_schema.columns "
                                    f"WHERE TABLE_NAME='{table}' ORDER BY ORDINAL_POSITION"
                                )
                            info_result = await self.container.data_source.run_query(
                                connection_config=conn_cfg,
                                sql=info_sql,
                                limit=5000
                            )
                            irows = info_result.get("rows", []) or info_result.get("data", []) or []
                            info_cols: List[str] = []
                            idetails: Dict[str, Dict[str, Any]] = {}
                            for row in irows:
                                if isinstance(row, dict):
                                    col = row.get("COLUMN_NAME") or row.get("column_name") or list(row.values())[0]
                                    info_cols.append(col)
                                    idetails[col] = {
                                        "type": row.get("DATA_TYPE") or row.get("data_type"),
                                        "nullable": True if str(row.get("IS_NULLABLE")).upper() == "YES" else (False if str(row.get("IS_NULLABLE")).upper() == "NO" else None),
                                        "key": None,
                                        "default": row.get("COLUMN_DEFAULT"),
                                        "extra": None,
                                        "comment": row.get("COLUMN_COMMENT") or row.get("column_comment"),
                                    }
                                elif isinstance(row, list) and len(row) > 0:
                                    col = str(row[0])
                                    info_cols.append(col)
                            columns_map[table] = info_cols
                            if idetails:
                                details_map[table] = idetails
                        except Exception:
                            self._logger.warning(f"information_schema 查询失败: table={table}")
                except Exception as e:
                    self._logger.error(f"📋 [SchemaGetColumns] 获取表 {table} 列失败: {e}")
                    self._logger.error(f"📋 [SchemaGetColumns] 异常详情: {type(e).__name__}: {str(e)}")
                    columns_map[table] = []

            # 构造简要摘要
            schema_descriptions = []
            total_cols = 0
            for t, cols in columns_map.items():
                total_cols += len(cols)
                if cols:
                    # 使用详情（若有）展示类型/注释片段
                    det = details_map.get(t, {})
                    items: List[str] = []
                    for col in cols[:10]:
                        meta = det.get(col) or {}
                        tp = meta.get("type") or ""
                        cmt = meta.get("comment") or ""
                        cmt_short = (cmt[:20] + "…") if (isinstance(cmt, str) and len(cmt) > 20) else cmt
                        if tp or cmt_short:
                            items.append(f"{col}({tp}{', '+cmt_short if cmt_short else ''})")
                        else:
                            items.append(col)
                    schema_descriptions.append(f"**{t}** ({len(cols)}列): {', '.join(items)}{'...' if len(cols) > 10 else ''}")
                else:
                    schema_descriptions.append(f"**{t}**: 无列信息")

            summary = f"共 {len(columns_map)} 张表, 合计 {total_cols} 列\n" + "\n".join(schema_descriptions)

            # 添加详细调试日志
            self._logger.info(f"📋 [SchemaGetColumns] 成功获取 {len(columns_map)} 张表的列信息")
            self._logger.info(f"📋 [SchemaGetColumns] 表名: {list(columns_map.keys())}")
            self._logger.info(f"📋 [SchemaGetColumns] 列信息摘要: {columns_map}")
            self._logger.info(f"📋 [SchemaGetColumns] 详细字段信息: {len(details_map)} 张表有详情")

            return {
                "success": True,
                "tables": list(columns_map.keys()),
                "columns": columns_map,
                "column_details": details_map,
                "schema_summary": summary,
                "table_count": len(columns_map),
                "column_count": total_cols,
                "schema_descriptions": schema_descriptions,
                "message": f"列信息获取完成，{len(columns_map)}张表，{total_cols}列"
            }
        except Exception as e:
            self._logger.error(f"获取列信息失败: {e}")
            return {"success": False, "error": str(e)}
