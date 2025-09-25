"""
数据源上下文应用服务

用于获取数据库表结构的完整信息，并构造Agent便于理解的上下文结构
支持实时获取表结构信息，确保数据源信息不会过时

基于backup2的原始实现，适配当前系统架构
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ColumnType(Enum):
    """列类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    BOOLEAN = "boolean"
    JSON = "json"
    TEXT = "text"
    UNKNOWN = "unknown"


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    type: str
    nullable: bool
    default_value: Optional[str] = None
    comment: Optional[str] = None
    key: Optional[str] = None  # PRI, UNI, MUL等
    extra: Optional[str] = None  # auto_increment等
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None

    def to_agent_format(self) -> Dict[str, Any]:
        """转换为Agent易于理解的格式"""
        return {
            "name": self.name,
            "type": self._normalize_type(),
            "nullable": self.nullable,
            "description": self.comment or f"{self.name}字段",
            "is_primary_key": self.key == "PRI",
            "is_unique": self.key in ["PRI", "UNI"],
            "is_indexed": self.key in ["PRI", "UNI", "MUL"],
            "is_auto_increment": "auto_increment" in (self.extra or "").lower(),
            "default_value": self.default_value,
            "constraints": self._get_constraints(),
            "business_meaning": self._infer_business_meaning(),
            "data_characteristics": self._analyze_data_characteristics()
        }

    def _normalize_type(self) -> str:
        """标准化数据类型"""
        type_lower = self.type.lower()

        if "varchar" in type_lower or "char" in type_lower or "text" in type_lower:
            return ColumnType.STRING.value
        elif "int" in type_lower or "bigint" in type_lower or "smallint" in type_lower:
            return ColumnType.INTEGER.value
        elif "decimal" in type_lower or "numeric" in type_lower or "float" in type_lower or "double" in type_lower:
            return ColumnType.DECIMAL.value
        elif "date" in type_lower and "time" not in type_lower:
            return ColumnType.DATE.value
        elif "datetime" in type_lower:
            return ColumnType.DATETIME.value
        elif "timestamp" in type_lower:
            return ColumnType.TIMESTAMP.value
        elif "boolean" in type_lower or "bool" in type_lower or "tinyint(1)" in type_lower:
            return ColumnType.BOOLEAN.value
        elif "json" in type_lower:
            return ColumnType.JSON.value
        else:
            return ColumnType.UNKNOWN.value

    def _get_constraints(self) -> List[str]:
        """获取约束信息"""
        constraints = []

        if not self.nullable:
            constraints.append("NOT NULL")
        if self.key == "PRI":
            constraints.append("PRIMARY KEY")
        elif self.key == "UNI":
            constraints.append("UNIQUE")
        if "auto_increment" in (self.extra or "").lower():
            constraints.append("AUTO_INCREMENT")

        return constraints

    def _infer_business_meaning(self) -> str:
        """推断业务含义"""
        name_lower = self.name.lower()

        # 时间相关
        if any(keyword in name_lower for keyword in ["created", "create_time", "created_at"]):
            return "创建时间"
        elif any(keyword in name_lower for keyword in ["updated", "update_time", "updated_at", "modified"]):
            return "更新时间"
        elif any(keyword in name_lower for keyword in ["deleted", "delete_time", "deleted_at"]):
            return "删除时间"
        elif "time" in name_lower or "date" in name_lower:
            return "时间字段"

        # ID相关
        elif name_lower == "id" or name_lower.endswith("_id"):
            return "标识符"

        # 状态相关
        elif "status" in name_lower or "state" in name_lower:
            return "状态字段"

        # 金额相关
        elif any(keyword in name_lower for keyword in ["amount", "price", "cost", "fee", "money"]):
            return "金额字段"

        # 数量相关
        elif any(keyword in name_lower for keyword in ["count", "num", "quantity", "qty"]):
            return "数量字段"

        # 名称相关
        elif "name" in name_lower or "title" in name_lower:
            return "名称字段"

        else:
            return self.comment or f"{self.name}字段"

    def _analyze_data_characteristics(self) -> Dict[str, bool]:
        """分析数据特征"""
        name_lower = self.name.lower()
        type_normalized = self._normalize_type()

        return {
            "suitable_for_grouping": (
                type_normalized in [ColumnType.STRING.value, ColumnType.INTEGER.value, ColumnType.DATE.value] or
                any(keyword in name_lower for keyword in ["status", "type", "category", "country", "region"])
            ),
            "suitable_for_aggregation": (
                type_normalized in [ColumnType.INTEGER.value, ColumnType.DECIMAL.value] and
                any(keyword in name_lower for keyword in ["amount", "price", "count", "quantity", "num"])
            ),
            "suitable_for_filtering": (
                self.key in ["PRI", "UNI", "MUL"] or
                type_normalized in [ColumnType.DATE.value, ColumnType.DATETIME.value, ColumnType.TIMESTAMP.value]
            ),
            "suitable_for_ordering": (
                type_normalized in [ColumnType.DATE.value, ColumnType.DATETIME.value, ColumnType.TIMESTAMP.value, ColumnType.INTEGER.value, ColumnType.DECIMAL.value]
            ),
            "is_measure": (
                type_normalized in [ColumnType.INTEGER.value, ColumnType.DECIMAL.value] and
                any(keyword in name_lower for keyword in ["amount", "price", "count", "quantity", "total", "sum"])
            ),
            "is_dimension": (
                type_normalized == ColumnType.STRING.value or
                any(keyword in name_lower for keyword in ["name", "type", "category", "status", "country", "region"])
            )
        }


@dataclass
class TableInfo:
    """表信息"""
    name: str
    columns: List[ColumnInfo]
    comment: Optional[str] = None
    engine: Optional[str] = None
    charset: Optional[str] = None
    row_count: Optional[int] = None
    last_updated: Optional[datetime] = None

    def to_agent_format(self) -> Dict[str, Any]:
        """转换为Agent易于理解的格式"""
        # 分类列信息
        primary_keys = [col.name for col in self.columns if col.key == "PRI"]
        foreign_keys = [col.name for col in self.columns if col.name.endswith("_id") and col.key != "PRI"]
        time_columns = [col.name for col in self.columns if any(t in col.type.lower() for t in ["date", "time", "timestamp"])]
        measure_columns = [col.name for col in self.columns if col._analyze_data_characteristics()["is_measure"]]
        dimension_columns = [col.name for col in self.columns if col._analyze_data_characteristics()["is_dimension"]]

        return {
            "table_name": self.name,
            "description": self.comment or f"{self.name}表",
            "row_count": self.row_count,
            "total_columns": len(self.columns),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "business_domain": self._infer_business_domain(),

            # 关键字段分类
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "time_columns": time_columns,
            "measure_columns": measure_columns,
            "dimension_columns": dimension_columns,

            # 详细列信息
            "columns": [col.to_agent_format() for col in self.columns],

            # 查询建议
            "query_suggestions": self._generate_query_suggestions(),

            # 性能提示
            "performance_hints": self._generate_performance_hints()
        }

    def _infer_business_domain(self) -> str:
        """推断业务域"""
        table_name = self.name.lower()

        if "order" in table_name or "retail" in table_name or "sales" in table_name:
            return "sales"
        elif "user" in table_name or "customer" in table_name:
            return "customer"
        elif "product" in table_name or "goods" in table_name or "item" in table_name:
            return "product"
        elif "payment" in table_name or "pay" in table_name:
            return "payment"
        elif "refund" in table_name:
            return "refund"
        elif "log" in table_name:
            return "logging"
        elif any(prefix in table_name for prefix in ["ods_", "dwd_", "dws_", "ads_"]):
            return "datawarehouse"
        else:
            return "general"

    def _generate_query_suggestions(self) -> List[str]:
        """生成查询建议"""
        suggestions = []

        # 基于度量字段的建议
        measure_cols = [col for col in self.columns if col._analyze_data_characteristics()["is_measure"]]
        if measure_cols:
            suggestions.append(f"聚合分析: 可对 {', '.join([col.name for col in measure_cols])} 进行 SUM/AVG/COUNT 聚合")

        # 基于时间字段的建议
        time_cols = [col for col in self.columns if any(t in col.type.lower() for t in ["date", "time", "timestamp"])]
        if time_cols:
            suggestions.append(f"时间序列分析: 可按 {', '.join([col.name for col in time_cols])} 进行时间趋势分析")

        # 基于维度字段的建议
        dim_cols = [col for col in self.columns if col._analyze_data_characteristics()["is_dimension"]]
        if dim_cols:
            suggestions.append(f"分组分析: 可按 {', '.join([col.name for col in dim_cols[:3]])} 进行分组统计")

        # 基于主键的建议
        pk_cols = [col for col in self.columns if col.key == "PRI"]
        if pk_cols:
            suggestions.append(f"精确查询: 使用主键 {', '.join([col.name for col in pk_cols])} 进行精确定位")

        return suggestions

    def _generate_performance_hints(self) -> List[str]:
        """生成性能提示"""
        hints = []

        if self.row_count:
            if self.row_count > 1000000:
                hints.append("大表(>100万行)，建议使用索引字段过滤，限制返回行数")
            elif self.row_count > 100000:
                hints.append("中等大小表(>10万行)，注意查询性能，建议添加WHERE条件")

        # 索引提示
        indexed_cols = [col for col in self.columns if col.key in ["PRI", "UNI", "MUL"]]
        if indexed_cols:
            hints.append(f"已建索引字段: {', '.join([col.name for col in indexed_cols])}")

        return hints


@dataclass
class DataSourceContextInfo:
    """数据源上下文信息"""
    tables: List[TableInfo]
    database_name: str
    database_type: str
    last_refresh: Optional[datetime] = None

    def to_agent_format(self) -> Dict[str, Any]:
        """转换为Agent友好的格式"""
        return {
            "database_name": self.database_name,
            "database_type": self.database_type,
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
            "total_tables": len(self.tables),

            "tables": [table.to_agent_format() for table in self.tables],

            "statistics": {
                "total_columns": sum(len(table.columns) for table in self.tables),
                "total_rows": sum(table.row_count or 0 for table in self.tables),
                "avg_columns_per_table": round(sum(len(table.columns) for table in self.tables) / len(self.tables), 1) if self.tables else 0,
                "domain_distribution": self._get_domain_distribution()
            },

            "relationships": self._infer_relationships(),
            "common_patterns": self._identify_common_patterns()
        }

    def _get_domain_distribution(self) -> Dict[str, int]:
        """获取业务域分布"""
        domains = {}
        for table in self.tables:
            domain = table._infer_business_domain()
            domains[domain] = domains.get(domain, 0) + 1
        return domains

    def _infer_relationships(self) -> List[Dict[str, str]]:
        """推断表关系"""
        relationships = []

        for table in self.tables:
            for col in table.columns:
                if col.name.endswith("_id") and col.key != "PRI":
                    # 寻找可能的主表
                    entity_name = col.name[:-3]  # 去掉 "_id"
                    for other_table in self.tables:
                        if entity_name in other_table.name.lower() or other_table.name.lower().endswith(entity_name):
                            relationships.append({
                                "from_table": table.name,
                                "from_column": col.name,
                                "to_table": other_table.name,
                                "to_column": "id",
                                "type": "foreign_key"
                            })
                            break

        return relationships

    def _identify_common_patterns(self) -> List[str]:
        """识别常见查询模式"""
        patterns = []

        # 检查时间序列模式
        time_tables = [table for table in self.tables if any(
            any(t in col.type.lower() for t in ["date", "time", "timestamp"])
            for col in table.columns
        )]
        if time_tables:
            patterns.append("支持时间序列分析")

        # 检查聚合模式
        measure_tables = [table for table in self.tables if any(
            col._analyze_data_characteristics()["is_measure"]
            for col in table.columns
        )]
        if measure_tables:
            patterns.append("支持聚合统计分析")

        # 检查关联模式
        if len(self.tables) > 1:
            patterns.append("支持多表关联查询")

        return patterns


class DataSourceContextBuilder:
    """数据源上下文构建器"""

    def __init__(self, container=None):
        self.container = container
        self._table_cache: Dict[str, TableInfo] = {}
        self._cache_ttl = 300  # 5分钟缓存

    async def build_context_info(self,
                                tables_info: List[TableInfo],
                                database_name: str,
                                database_type: str = "mysql") -> DataSourceContextInfo:
        """从TableInfo列表构建上下文信息"""
        return DataSourceContextInfo(
            tables=tables_info,
            database_name=database_name,
            database_type=database_type,
            last_refresh=datetime.now()
        )

    async def build_data_source_context(
        self,
        user_id: str,
        data_source_id: str,
        required_tables: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """构建数据源上下文（backup2原始接口）"""

        try:
            # 1. 获取数据源基本信息
            if self.container and hasattr(self.container, 'user_data_source_service'):
                data_source = await self.container.user_data_source_service.get_user_data_source(
                    user_id=user_id,
                    data_source_id=data_source_id
                )

                if not data_source:
                    raise ValueError(f"Data source {data_source_id} not found")

                # 2. 获取表信息
                if required_tables:
                    table_infos = []
                    for table_name in required_tables:
                        table_info = await self.get_table_info(
                            data_source_id=data_source_id,
                            table_name=table_name,
                            connection_config=data_source.connection_config,
                            force_refresh=force_refresh
                        )
                        if table_info:
                            table_infos.append(table_info)
                else:
                    # 获取所有表
                    table_infos = await self.get_all_tables_info(
                        data_source_id=data_source_id,
                        connection_config=data_source.connection_config,
                        force_refresh=force_refresh
                    )

                # 3. 构建Agent上下文
                context_info = DataSourceContextInfo(
                    tables=table_infos,
                    database_name=data_source.connection_config.get("database", "unknown"),
                    database_type=data_source.source_type,
                    last_refresh=datetime.now()
                )

                ctx = context_info.to_agent_format()
                ctx["success"] = True
                return ctx

            else:
                logger.warning("Container or user_data_source_service not available, using fallback mode")
                return await self._build_fallback_data_source_context(user_id, data_source_id)

        except Exception as e:
            logger.error(f"构建数据源上下文失败: {e}")
            return {"success": False, "error": str(e)}

    async def _build_fallback_data_source_context(
        self,
        user_id: str,
        data_source_id: str
    ) -> Dict[str, Any]:
        """回退模式构建数据源上下文 - 连接真实数据源获取表结构"""

        try:
            # 直接查询数据库获取数据源信息
            from app.db.session import get_db_session
            from app.models.data_source import DataSource

            with get_db_session() as db:
                data_source = db.query(DataSource).filter(
                    DataSource.id == data_source_id,
                    DataSource.user_id == user_id
                ).first()

                if not data_source:
                    logger.warning(f"Data source {data_source_id} not found for user {user_id}")
                    return {"success": False, "error": "data_source_not_found"}

                # 获取真实表结构
                real_tables = await self._get_real_table_info(data_source)

                if not real_tables:
                    # 如果获取真实表结构失败，直接返回错误，不使用模拟表结构
                    logger.error(f"Failed to get real table info for {data_source_id}, no fallback available")
                    return {
                        "success": False,
                        "error": "no_real_tables_available",
                        "message": f"Unable to retrieve table structures from data source {data_source_id}",
                        "fallback_mode": True
                    }

                # 构建上下文信息
                context_info = DataSourceContextInfo(
                    tables=real_tables,
                    database_name=data_source.display_name or "fallback_database",
                    database_type=data_source.source_type.value if data_source.source_type else "mysql",
                    last_refresh=datetime.now()
                )

                ctx = context_info.to_agent_format()
                ctx["success"] = True
                ctx["fallback_mode"] = True
                ctx["real_tables"] = len(real_tables) > 0
                logger.info(f"Successfully built fallback data source context for {data_source_id} with {len(real_tables)} tables")
                return ctx

        except Exception as e:
            logger.error(f"Fallback data source context build failed: {e}")
            return {
                "success": False,
                "error": f"fallback_failed: {str(e)}",
                "fallback_mode": True
            }


    async def _get_real_table_info(self, data_source) -> List[TableInfo]:
        """连接真实数据源获取表结构信息"""

        try:
            # 根据数据源类型选择连接器
            if data_source.source_type.value == "doris":
                return await self._get_doris_table_info(data_source)
            elif data_source.source_type.value == "sql":
                return await self._get_sql_table_info(data_source)
            else:
                logger.warning(f"Unsupported data source type: {data_source.source_type}")
                return []

        except Exception as e:
            logger.error(f"Failed to get real table info: {e}")
            return []

    async def _get_doris_table_info(self, data_source) -> List[TableInfo]:
        """获取Doris数据源的表结构"""

        try:
            from app.services.data.connectors.doris_connector import DorisConnector, DorisConfig
            from app.core.data_source_utils import DataSourcePasswordManager

            # 构建Doris配置
            password = ""
            if data_source.doris_password:
                password = DataSourcePasswordManager.get_password(data_source.doris_password)

            config = DorisConfig(
                source_type="doris",
                name=data_source.name,
                fe_hosts=data_source.doris_fe_hosts or ["localhost"],
                http_port=data_source.doris_http_port or 8030,
                query_port=data_source.doris_query_port or 9030,
                database=data_source.doris_database or "default",
                username=data_source.doris_username or "root",
                password=password,
                use_mysql_protocol=False  # 使用HTTP API更稳定
            )

            connector = DorisConnector(config)
            tables = []

            try:
                await connector.__aenter__()

                # 获取所有表名
                tables_result = await connector.execute_query("SHOW TABLES")
                table_names = []

                for row in tables_result.to_dict().get('data', []):
                    if isinstance(row, dict):
                        table_name = list(row.values())[0]
                    elif isinstance(row, list):
                        table_name = row[0]
                    else:
                        table_name = str(row)
                    table_names.append(table_name)

                logger.info(f"Found {len(table_names)} tables in Doris: {table_names}")

                # 获取每个表的结构（限制前10个表避免超时）
                for table_name in table_names[:10]:
                    try:
                        desc_result = await connector.execute_query(f"DESCRIBE {table_name}")
                        columns = []

                        for row in desc_result.to_dict().get('data', []):
                            if isinstance(row, dict):
                                field = row.get('Field', '')
                                type_info = row.get('Type', '')
                                null_info = row.get('Null', 'YES')
                                key_info = row.get('Key', '')
                                default = row.get('Default')
                                extra = row.get('Extra', '')
                            elif isinstance(row, list) and len(row) >= 4:
                                field = row[0] or ''
                                type_info = row[1] or ''
                                null_info = row[2] or 'YES'
                                key_info = row[3] or ''
                                default = row[4] if len(row) > 4 else None
                                extra = row[5] if len(row) > 5 else ''
                            else:
                                continue

                            column = ColumnInfo(
                                name=field,
                                type=type_info,
                                nullable=null_info.upper() != 'NO',
                                default_value=str(default) if default is not None else None,
                                key=key_info if key_info else None,
                                extra=extra if extra else None
                            )
                            columns.append(column)

                        if columns:
                            table_info = TableInfo(
                                name=table_name,
                                columns=columns,
                                comment=f"{table_name}表",
                                engine="Doris"
                            )
                            tables.append(table_info)
                            logger.debug(f"Added table {table_name} with {len(columns)} columns")

                    except Exception as e:
                        logger.warning(f"Failed to get structure for table {table_name}: {e}")
                        continue

            finally:
                await connector.__aexit__(None, None, None)

            logger.info(f"Successfully retrieved {len(tables)} table structures from Doris")
            return tables

        except Exception as e:
            logger.error(f"Failed to connect to Doris data source: {e}")
            return []

    async def _get_sql_table_info(self, data_source) -> List[TableInfo]:
        """获取SQL数据源的表结构（PostgreSQL/MySQL等）"""

        # TODO: 实现SQL数据源的表结构获取
        logger.info("SQL data source table info retrieval not implemented yet")
        return []

    async def get_table_info(
        self,
        data_source_id: str,
        table_name: str,
        connection_config: Dict[str, Any],
        force_refresh: bool = False
    ) -> Optional[TableInfo]:
        """获取单个表的详细信息"""

        cache_key = f"{data_source_id}:{table_name}"

        # 检查缓存
        if not force_refresh and cache_key in self._table_cache:
            cached_table = self._table_cache[cache_key]
            if cached_table.last_updated and (datetime.now() - cached_table.last_updated).seconds < self._cache_ttl:
                return cached_table

        try:
            # 执行SHOW FULL COLUMNS查询
            columns_sql = f"SHOW FULL COLUMNS FROM {table_name}"
            columns_result = await self._execute_sql(connection_config, columns_sql)

            if not columns_result.get("success"):
                return None

            # 解析列信息
            columns = []
            for row in columns_result.get("rows", []):
                column = ColumnInfo(
                    name=row.get("Field", ""),
                    type=row.get("Type", ""),
                    nullable=row.get("Null", "NO") == "YES",
                    default_value=row.get("Default"),
                    comment=row.get("Comment"),
                    key=row.get("Key"),
                    extra=row.get("Extra")
                )
                columns.append(column)

            # 获取表注释和行数
            table_status_sql = f"SHOW TABLE STATUS LIKE '{table_name}'"
            status_result = await self._execute_sql(connection_config, table_status_sql)

            table_comment = None
            row_count = None
            engine = None
            charset = None

            if status_result.get("success") and status_result.get("rows"):
                status_row = status_result["rows"][0]
                table_comment = status_row.get("Comment")
                row_count = status_row.get("Rows")
                engine = status_row.get("Engine")
                charset = status_row.get("Collation")

            # 创建表信息对象
            table_info = TableInfo(
                name=table_name,
                columns=columns,
                comment=table_comment,
                engine=engine,
                charset=charset,
                row_count=row_count,
                last_updated=datetime.now()
            )

            # 缓存结果
            self._table_cache[cache_key] = table_info

            return table_info

        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {str(e)}")
            return None

    async def get_all_tables_info(
        self,
        data_source_id: str,
        connection_config: Dict[str, Any],
        force_refresh: bool = False
    ) -> List[TableInfo]:
        """获取所有表的信息"""

        try:
            # 首先获取所有表名
            tables_sql = "SHOW TABLES"
            tables_result = await self._execute_sql(connection_config, tables_sql)

            if not tables_result.get("success"):
                return []

            table_names = [list(row.values())[0] for row in tables_result.get("rows", [])]

            # 获取每个表的详细信息
            table_infos = []
            for table_name in table_names:
                table_info = await self.get_table_info(
                    data_source_id=data_source_id,
                    table_name=table_name,
                    connection_config=connection_config,
                    force_refresh=force_refresh
                )
                if table_info:
                    table_infos.append(table_info)

            return table_infos

        except Exception as e:
            logger.error(f"Error getting all tables info: {str(e)}")
            return []

    async def _execute_sql(self, connection_config: Dict[str, Any], sql: str) -> Dict[str, Any]:
        """执行SQL查询"""
        try:
            if self.container and hasattr(self.container, 'data_source'):
                # 使用容器中的数据源服务执行查询
                result = await self.container.data_source.run_query(
                    connection_config=connection_config,
                    sql=sql,
                    limit=1000
                )
                return result
            else:
                logger.warning("Container or data_source service not available")
                return {"success": False, "error": "Data source service not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_fallback_context(self, database_name: str, error: Optional[str] = None) -> Dict[str, Any]:
        """创建降级上下文"""
        return {
            "database_name": database_name,
            "database_type": "unknown",
            "last_refresh": datetime.now().isoformat(),
            "total_tables": 0,
            "tables": [],
            "statistics": {
                "total_columns": 0,
                "total_rows": 0,
                "avg_columns_per_table": 0,
                "domain_distribution": {}
            },
            "relationships": [],
            "common_patterns": [],
            "error": error,
            "fallback": True
        }

    async def refresh_table_cache(self, data_source_id: str, table_name: Optional[str] = None):
        """刷新表缓存"""
        if table_name:
            cache_key = f"{data_source_id}:{table_name}"
            if cache_key in self._table_cache:
                del self._table_cache[cache_key]
        else:
            # 清除该数据源的所有缓存
            keys_to_remove = [key for key in self._table_cache.keys() if key.startswith(f"{data_source_id}:")]
            for key in keys_to_remove:
                del self._table_cache[key]
