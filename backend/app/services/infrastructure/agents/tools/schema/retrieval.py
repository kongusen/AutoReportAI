from __future__ import annotations


from loom.interfaces.tool import BaseTool
"""
Schema 检索工具

用于检索和获取特定的表结构信息
支持按需检索和结构化查询
"""

import logging
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


@dataclass
class RetrievalQuery:
    """检索查询"""
    table_names: Optional[List[str]] = None
    column_names: Optional[List[str]] = None
    data_types: Optional[List[str]] = None
    include_relationships: bool = True
    include_constraints: bool = True
    include_indexes: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RetrievalResult:
    """检索结果"""
    tables: List[Dict[str, Any]]
    columns: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SchemaRetrievalTool(BaseTool):
    """Schema 检索工具"""
    
    def __init__(self, container: Any, connection_config: Optional[Dict[str, Any]] = None):
        """
        Args:
            container: 服务容器
            connection_config: 数据源连接配置（在初始化时注入，LLM 不需要传递）
        """
        super().__init__()

        self.name = "schema_retrieval"

        self.category = ToolCategory.SCHEMA

        self.description = "检索和获取特定的表结构信息"
        self.container = container
        self._connection_config = connection_config  # 🔥 保存连接配置
        self._data_source_service = None
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class SchemaRetrievalArgs(BaseModel):
            table_names: Optional[List[str]] = Field(
                default=None, description="要检索的表名列表"
            )
            column_names: Optional[List[str]] = Field(
                default=None, description="要检索的列名列表"
            )
            data_types: Optional[List[str]] = Field(
                default=None, description="要检索的数据类型列表"
            )
            include_relationships: bool = Field(
                default=True, description="是否包含关系信息"
            )
            include_constraints: bool = Field(
                default=True, description="是否包含约束信息"
            )
            include_indexes: bool = Field(
                default=False, description="是否包含索引信息"
            )
            format: Literal["detailed", "summary", "minimal"] = Field(
                default="detailed", description="输出格式"
            )

        # 向 Loom 暴露标准的 args_schema
        self.args_schema = SchemaRetrievalArgs
    
    async def _get_data_source_service(self):
        """获取数据源服务"""
        if self._data_source_service is None:
            self._data_source_service = getattr(
                self.container, 'data_source', None
            ) or getattr(self.container, 'data_source_service', None)
        return self._data_source_service
    
    async def _get_context_selected_tables(self) -> Optional[List[str]]:
        """从上下文中获取已选择的表"""
        try:
            # 尝试从容器中获取上下文检索器
            context_retriever = getattr(self.container, 'context_retriever', None)
            if context_retriever:
                # 获取最近检索的表
                recent_tables = getattr(context_retriever, 'recent_selected_tables', None)
                if recent_tables:
                    logger.info(f"🔍 [SchemaRetrievalTool] 从上下文检索器获取到表: {recent_tables}")
                    return recent_tables
            
            # 尝试从全局状态中获取
            import threading
            thread_local = getattr(threading.current_thread(), 'agent_context', None)
            if thread_local and 'selected_tables' in thread_local:
                tables = thread_local['selected_tables']
                logger.info(f"🔍 [SchemaRetrievalTool] 从线程上下文获取到表: {tables}")
                return tables
            
            return None
        except Exception as e:
            logger.debug(f"⚠️ [SchemaRetrievalTool] 获取上下文表信息失败: {e}")
            return None
    
    async def _validate_table_names_against_context(
        self, 
        table_names: Optional[List[str]]
    ) -> Optional[Dict[str, Any]]:
        """
        验证请求的表名是否在上下文中
        
        Args:
            table_names: 请求的表名列表
            
        Returns:
            如果有验证问题，返回错误信息字典；否则返回 None
        """
        if not table_names:
            return None
        
        context_tables = await self._get_context_selected_tables()
        if not context_tables:
            # 如果无法获取上下文，不阻止执行（可能是首次调用）
            logger.debug("⚠️ [SchemaRetrievalTool] 无法获取上下文表信息，跳过验证")
            return None
        
        # 标准化表名（转为小写进行比较）
        context_tables_normalized = [t.lower() for t in context_tables]
        requested_tables_normalized = [t.lower() for t in table_names]
        
        # 找出不在上下文中的表
        invalid_tables = [
            t for t in requested_tables_normalized 
            if t not in context_tables_normalized
        ]
        
        if invalid_tables:
            # 找到对应的原始表名（保持大小写）
            original_invalid = [
                table_names[i] 
                for i, normalized in enumerate(requested_tables_normalized)
                if normalized in invalid_tables
            ]
            
            logger.warning(
                f"🚨 [SchemaRetrievalTool] 检测到不在上下文中的表: {original_invalid}。"
                f"上下文中的表: {context_tables}"
            )
            
            return {
                "success": False,
                "error": f"表 {original_invalid} 不在系统已检索的上下文中",
                "invalid_tables": original_invalid,
                "available_tables": context_tables,
                "suggestion": f"请使用以下上下文中的表名: {', '.join(context_tables)}",
                "result": {
                    "tables": [],
                    "columns": [],
                    "relationships": [],
                    "constraints": [],
                    "indexes": []
                }
            }
        
        return None
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()  # pydantic v2
        except Exception:
            # 兼容 pydantic v1
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]

        return {
            "type": "function",
            "function": {
                "name": "schema_retrieval",
                "description": "检索和获取特定的表结构信息",
                "parameters": parameters,
            },
        }
    
    async def run(
        self,
        table_names: Optional[List[str]] = None,
        column_names: Optional[List[str]] = None,
        data_types: Optional[List[str]] = None,
        include_relationships: bool = True,
        include_constraints: bool = True,
        include_indexes: bool = False,
        format: str = "detailed",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 Schema 检索

        Args:
            table_names: 要检索的表名列表
            column_names: 要检索的列名列表
            data_types: 要检索的数据类型列表
            include_relationships: 是否包含关系信息
            include_constraints: 是否包含约束信息
            include_indexes: 是否包含索引信息
            format: 输出格式

        Returns:
            Dict[str, Any]: 检索结果
        """
        logger.info("🔍 [SchemaRetrievalTool] 开始检索 Schema 信息")
        logger.info(f"   表名: {table_names}")
        logger.info(f"   列名: {column_names}")
        logger.info(f"   数据类型: {data_types}")

        # 🔥 使用初始化时注入的 connection_config
        connection_config = self._connection_config
        if not connection_config:
            return {
                "success": False,
                "error": "未配置数据源连接，请在初始化工具时提供 connection_config",
                "result": {}
            }
        
        # 🔥 新增：验证请求的表名是否在上下文中
        if table_names:
            validation_result = await self._validate_table_names_against_context(table_names)
            if validation_result:
                logger.warning(
                    f"⚠️ [SchemaRetrievalTool] 表名验证失败，返回纠正消息: {validation_result.get('error')}"
                )
                return validation_result
        
        try:
            data_source_service = await self._get_data_source_service()
            if not data_source_service:
                return {
                    "success": False,
                    "error": "数据源服务不可用",
                    "result": {}
                }
            
            # 构建检索查询
            query = RetrievalQuery(
                table_names=table_names,
                column_names=column_names,
                data_types=data_types,
                include_relationships=include_relationships,
                include_constraints=include_constraints,
                include_indexes=include_indexes
            )
            
            # 执行检索
            retrieval_result = await self._execute_retrieval(
                data_source_service, connection_config, query, format
            )
            
            return {
                "success": True,
                "result": retrieval_result,
                "tables": retrieval_result.get("tables", []),
                "columns": retrieval_result.get("columns", []),
                "relationships": retrieval_result.get("relationships", []),
                "constraints": retrieval_result.get("constraints", []),
                "indexes": retrieval_result.get("indexes", []),
                "metadata": {
                    "query": {
                        "table_names": table_names,
                        "column_names": column_names,
                        "data_types": data_types,
                        "include_relationships": include_relationships,
                        "include_constraints": include_constraints,
                        "include_indexes": include_indexes
                    },
                    "format": format
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [SchemaRetrievalTool] 检索失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": {}
            }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """向后兼容的execute方法"""
        return await self.run(**kwargs)
    
    async def _execute_retrieval(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        query: RetrievalQuery,
        format: str
    ) -> Dict[str, Any]:
        """执行检索操作"""
        result = {
            "tables": [],
            "columns": [],
            "relationships": [],
            "constraints": [],
            "indexes": []
        }
        
        # 检索表信息
        if query.table_names:
            tables = await self._retrieve_tables(
                data_source_service, connection_config, query.table_names, format
            )
            result["tables"] = tables
        
        # 检索列信息
        if query.table_names or query.column_names or query.data_types:
            columns = await self._retrieve_columns(
                data_source_service, connection_config, query, format
            )
            result["columns"] = columns
        
        # 检索关系信息
        if query.include_relationships and query.table_names:
            relationships = await self._retrieve_relationships(
                data_source_service, connection_config, query.table_names
            )
            result["relationships"] = relationships
        
        # 检索约束信息
        if query.include_constraints and query.table_names:
            constraints = await self._retrieve_constraints(
                data_source_service, connection_config, query.table_names
            )
            result["constraints"] = constraints
        
        # 检索索引信息
        if query.include_indexes and query.table_names:
            indexes = await self._retrieve_indexes(
                data_source_service, connection_config, query.table_names
            )
            result["indexes"] = indexes
        
        return result
    
    async def _retrieve_tables(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_names: List[str],
        format: str
    ) -> List[Dict[str, Any]]:
        """检索表信息"""
        tables = []
        
        for table_name in table_names:
            try:
                # 获取表基本信息
                table_info = await self._get_table_info(
                    data_source_service, connection_config, table_name
                )
                
                if table_info:
                    # 根据格式调整输出
                    if format == "minimal":
                        table_info = {
                            "name": table_info["name"],
                            "description": table_info.get("description", "")
                        }
                    elif format == "summary":
                        table_info = {
                            "name": table_info["name"],
                            "description": table_info.get("description", ""),
                            "row_count": table_info.get("row_count"),
                            "size_bytes": table_info.get("size_bytes")
                        }
                    
                    tables.append(table_info)
                
            except Exception as e:
                logger.warning(f"⚠️ 检索表 {table_name} 失败: {e}")
                continue
        
        return tables
    
    async def _retrieve_columns(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        query: RetrievalQuery,
        format: str
    ) -> List[Dict[str, Any]]:
        """检索列信息"""
        columns = []
        
        # 确定要检索的表
        target_tables = query.table_names or []
        if not target_tables:
            # 如果没有指定表，获取所有表
            tables_result = await data_source_service.run_query(
                connection_config=connection_config,
                sql="SHOW TABLES",
                limit=1000
            )
            
            if tables_result.get("success"):
                rows = tables_result.get("rows", []) or tables_result.get("data", [])
                for row in rows:
                    table_name = self._extract_table_name(row)
                    if table_name:
                        target_tables.append(table_name)
        
        # 检索每个表的列
        for table_name in target_tables:
            try:
                table_columns = await self._get_table_columns(
                    data_source_service, connection_config, table_name, format
                )
                
                # 应用过滤条件
                filtered_columns = self._filter_columns(
                    table_columns, query.column_names, query.data_types
                )
                
                columns.extend(filtered_columns)
                
            except Exception as e:
                logger.warning(f"⚠️ 检索表 {table_name} 列信息失败: {e}")
                continue
        
        return columns
    
    async def _retrieve_relationships(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_names: List[str]
    ) -> List[Dict[str, Any]]:
        """检索关系信息"""
        try:
            # 构建查询条件
            table_conditions = " OR ".join([f"kcu.TABLE_NAME = '{name}'" for name in table_names])
            
            sql = f"""
            SELECT 
                kcu.TABLE_NAME,
                kcu.COLUMN_NAME,
                kcu.REFERENCED_TABLE_NAME,
                kcu.REFERENCED_COLUMN_NAME,
                kcu.CONSTRAINT_NAME,
                tc.CONSTRAINT_TYPE
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            LEFT JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc 
                ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
                AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA
            WHERE kcu.REFERENCED_TABLE_NAME IS NOT NULL
            AND kcu.TABLE_SCHEMA = DATABASE()
            AND ({table_conditions})
            """
            
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=sql,
                limit=1000
            )
            
            if not result.get("success"):
                return []
            
            relationships = []
            rows = result.get("rows", []) or result.get("data", [])
            
            for row in rows:
                if isinstance(row, dict):
                    relationship = {
                        "from_table": row.get("TABLE_NAME", ""),
                        "from_column": row.get("COLUMN_NAME", ""),
                        "to_table": row.get("REFERENCED_TABLE_NAME", ""),
                        "to_column": row.get("REFERENCED_COLUMN_NAME", ""),
                        "constraint_name": row.get("CONSTRAINT_NAME", ""),
                        "constraint_type": row.get("CONSTRAINT_TYPE", "FOREIGN KEY"),
                        "relationship_type": "FOREIGN_KEY"
                    }
                    relationships.append(relationship)
            
            return relationships
            
        except Exception as e:
            logger.error(f"❌ 检索关系信息失败: {e}")
            return []
    
    async def _retrieve_constraints(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_names: List[str]
    ) -> List[Dict[str, Any]]:
        """检索约束信息"""
        try:
            # 构建查询条件
            table_conditions = " OR ".join([f"tc.TABLE_NAME = '{name}'" for name in table_names])
            
            sql = f"""
            SELECT 
                tc.TABLE_NAME,
                tc.CONSTRAINT_NAME,
                tc.CONSTRAINT_TYPE,
                kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
            WHERE tc.TABLE_SCHEMA = DATABASE()
            AND ({table_conditions})
            """
            
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=sql,
                limit=1000
            )
            
            if not result.get("success"):
                return []
            
            constraints = []
            rows = result.get("rows", []) or result.get("data", [])
            
            for row in rows:
                if isinstance(row, dict):
                    constraint = {
                        "table_name": row.get("TABLE_NAME", ""),
                        "constraint_name": row.get("CONSTRAINT_NAME", ""),
                        "constraint_type": row.get("CONSTRAINT_TYPE", ""),
                        "column_name": row.get("COLUMN_NAME", "")
                    }
                    constraints.append(constraint)
            
            return constraints
            
        except Exception as e:
            logger.error(f"❌ 检索约束信息失败: {e}")
            return []
    
    async def _retrieve_indexes(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_names: List[str]
    ) -> List[Dict[str, Any]]:
        """检索索引信息"""
        indexes = []
        
        for table_name in table_names:
            try:
                sql = f"SHOW INDEX FROM `{table_name}`"
                result = await data_source_service.run_query(
                    connection_config=connection_config,
                    sql=sql,
                    limit=1000
                )
                
                if result.get("success"):
                    rows = result.get("rows", []) or result.get("data", [])
                    
                    for row in rows:
                        if isinstance(row, dict):
                            index_info = {
                                "table_name": table_name,
                                "index_name": row.get("Key_name", ""),
                                "column_name": row.get("Column_name", ""),
                                "non_unique": row.get("Non_unique", 0) == 1,
                                "seq_in_index": row.get("Seq_in_index", 0),
                                "cardinality": row.get("Cardinality", 0),
                                "index_type": row.get("Index_type", "")
                            }
                            indexes.append(index_info)
                
            except Exception as e:
                logger.warning(f"⚠️ 检索表 {table_name} 索引信息失败: {e}")
                continue
        
        return indexes
    
    async def _get_table_info(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_name: str
    ) -> Optional[Dict[str, Any]]:
        """获取表信息"""
        try:
            # 获取表状态
            status_sql = f"SHOW TABLE STATUS LIKE '{table_name}'"
            status_result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=status_sql,
                limit=1
            )
            
            table_info = {
                "name": table_name,
                "description": "",
                "table_type": "TABLE",
                "row_count": None,
                "size_bytes": None,
                "created_at": None,
                "updated_at": None
            }
            
            if status_result.get("success"):
                rows = status_result.get("rows", [])
                if rows and isinstance(rows[0], dict):
                    row = rows[0]
                    table_info.update({
                        "row_count": row.get("Rows"),
                        "size_bytes": row.get("Data_length"),
                        "created_at": row.get("Create_time"),
                        "updated_at": row.get("Update_time"),
                        "description": row.get("Comment", "")
                    })
            
            return table_info
            
        except Exception as e:
            logger.warning(f"⚠️ 获取表 {table_name} 信息失败: {e}")
            return None
    
    async def _get_table_columns(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_name: str,
        format: str
    ) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        try:
            sql = f"SHOW FULL COLUMNS FROM `{table_name}`"
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=sql,
                limit=1000
            )
            
            if not result.get("success"):
                return []
            
            columns = []
            rows = result.get("rows", []) or result.get("data", [])
            
            for row in rows:
                if isinstance(row, dict):
                    column_info = {
                        "table_name": table_name,
                        "name": row.get("Field", ""),
                        "data_type": row.get("Type", ""),
                        "nullable": row.get("Null", "YES") == "YES",
                        "default_value": row.get("Default"),
                        "is_primary_key": row.get("Key", "") == "PRI",
                        "description": row.get("Comment", "")
                    }
                    
                    # 根据格式调整输出
                    if format == "minimal":
                        column_info = {
                            "table_name": column_info["table_name"],
                            "name": column_info["name"],
                            "data_type": column_info["data_type"]
                        }
                    elif format == "summary":
                        column_info = {
                            "table_name": column_info["table_name"],
                            "name": column_info["name"],
                            "data_type": column_info["data_type"],
                            "nullable": column_info["nullable"],
                            "is_primary_key": column_info["is_primary_key"]
                        }
                    
                    columns.append(column_info)
            
            return columns
            
        except Exception as e:
            logger.warning(f"⚠️ 获取表 {table_name} 列信息失败: {e}")
            return []
    
    def _filter_columns(
        self,
        columns: List[Dict[str, Any]],
        column_names: Optional[List[str]],
        data_types: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """过滤列信息"""
        filtered_columns = columns
        
        # 按列名过滤
        if column_names:
            filtered_columns = [
                col for col in filtered_columns
                if col.get("name", "").lower() in [name.lower() for name in column_names]
            ]
        
        # 按数据类型过滤
        if data_types:
            filtered_columns = [
                col for col in filtered_columns
                if any(dt.lower() in col.get("data_type", "").lower() for dt in data_types)
            ]
        
        return filtered_columns
    
    def _extract_table_name(self, row: Any) -> Optional[str]:
        """从查询结果中提取表名"""
        if isinstance(row, dict):
            # 尝试不同的键名
            for key in ["Tables_in_*", "table_name", "TABLE_NAME", "name"]:
                if key in row:
                    return str(row[key])
            # 取第一个值
            if row:
                return str(next(iter(row.values())))
        elif isinstance(row, (list, tuple)) and row:
            return str(row[0])
        elif isinstance(row, str):
            return row
        
        return None


def create_schema_retrieval_tool(
    container: Any,
    connection_config: Optional[Dict[str, Any]] = None
) -> SchemaRetrievalTool:
    """
    创建 Schema 检索工具

    Args:
        container: 服务容器
        connection_config: 数据源连接配置（在初始化时注入）

    Returns:
        SchemaRetrievalTool 实例
    """
    return SchemaRetrievalTool(container, connection_config=connection_config)


# 导出
__all__ = [
    "SchemaRetrievalTool",
    "RetrievalQuery",
    "RetrievalResult",
    "create_schema_retrieval_tool",
]
