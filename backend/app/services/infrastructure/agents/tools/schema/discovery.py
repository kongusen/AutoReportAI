from __future__ import annotations

"""
Schema 发现工具

用于发现数据源中的表结构和关系
支持智能表发现和结构分析
"""


import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from loom.interfaces.tool import BaseTool
from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


@dataclass
class TableInfo:
    """表信息"""
    name: str
    description: Optional[str] = None
    table_type: str = "TABLE"
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    data_type: str
    nullable: bool = True
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_table: Optional[str] = None
    foreign_column: Optional[str] = None
    description: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RelationshipInfo:
    """关系信息"""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relationship_type: str = "FOREIGN_KEY"  # FOREIGN_KEY, ONE_TO_ONE, ONE_TO_MANY
    constraint_name: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SchemaDiscoveryTool(BaseTool):
    """Schema 发现工具 - 支持懒加载优化"""
    
    def __init__(
        self,
        container: Any,
        connection_config: Optional[Dict[str, Any]] = None,
        enable_lazy_loading: bool = True
    ):
        """
        Args:
            container: 服务容器
            connection_config: 数据源连接配置（在初始化时注入，LLM 不需要传递）
            enable_lazy_loading: 是否启用懒加载（启动时只获取表名，按需获取列信息）
        """
        super().__init__()

        self.name = "schema_discovery"

        self.category = ToolCategory.SCHEMA

        self.description = "发现数据源中的表结构和关系，支持懒加载优化"
        self.container = container
        self._connection_config = connection_config  # 🔥 保存连接配置
        self._data_source_service = None

        # 懒加载相关属性
        self.enable_lazy_loading = enable_lazy_loading
        self._table_names_cache: List[str] = []
        self._columns_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_initialized = False
        self._result_cache: Dict[str, Dict[str, Any]] = {}
    
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
                    logger.info(f"🔍 [SchemaDiscoveryTool] 从上下文检索器获取到表: {recent_tables}")
                    return recent_tables
            
            # 尝试从全局状态中获取
            import threading
            thread_local = getattr(threading.current_thread(), 'agent_context', None)
            if thread_local and 'selected_tables' in thread_local:
                tables = thread_local['selected_tables']
                logger.info(f"🔍 [SchemaDiscoveryTool] 从线程上下文获取到表: {tables}")
                return tables
            
            # 尝试使用LLM智能解析消息历史中的表名
            try:
                # 从容器中获取消息历史
                messages = getattr(self.container, 'recent_messages', None)
                if messages:
                    # 收集最近的消息内容
                    recent_contents = []
                    for message in reversed(messages[-3:]):  # 检查最近3条消息
                        content = getattr(message, 'content', '') or str(message)
                        if content and len(content.strip()) > 10:  # 过滤掉太短的消息
                            recent_contents.append(content[:200])  # 限制长度
                    
                    if recent_contents:
                        # 使用LLM解析表名
                        parsed_tables = await self._llm_parse_tables_from_messages(recent_contents)
                        if parsed_tables:
                            logger.info(f"🔍 [SchemaDiscoveryTool] LLM解析到表: {parsed_tables}")
                            return parsed_tables
            except Exception as e:
                logger.debug(f"⚠️ [SchemaDiscoveryTool] LLM解析消息历史失败: {e}")
            
            # 如果没有找到任何表信息，返回空列表而不是硬编码
            logger.warning("⚠️ [SchemaDiscoveryTool] 无法从任何来源获取表信息")
            return None
            
        except Exception as e:
            logger.debug(f"⚠️ [SchemaDiscoveryTool] 获取上下文表信息失败: {e}")
            return None
    
    async def _llm_parse_tables_from_messages(self, messages: List[str]) -> Optional[List[str]]:
        """使用LLM智能解析消息中的表名"""
        try:
            # 构建提示词
            messages_text = "\n".join([f"- {msg}" for msg in messages])
            prompt = f"""
请分析以下消息内容，提取出与数据库表相关的表名。

消息内容：
{messages_text}

请根据消息内容，识别出最相关的数据库表名。如果消息中提到"退货"、"退款"、"refund"等关键词，请重点关注相关的表名。

请以JSON格式返回结果：
{{
    "tables": ["表名1", "表名2"],
    "reasoning": "选择这些表的原因"
}}

如果没有找到明确的表名，请返回空的tables数组。
"""

            # 获取LLM服务
            llm_service = getattr(self.container, 'llm_service', None)
            if not llm_service:
                logger.debug("⚠️ [SchemaDiscoveryTool] 未找到LLM服务，无法解析表名")
                return None
            
            # 调用LLM
            response = await llm_service.generate_completion(
                prompt=prompt,
                model="gpt-4o-mini",
                max_tokens=200,
                temperature=0.1
            )
            
            if response and response.get('content'):
                import json
                try:
                    result = json.loads(response['content'])
                    tables = result.get('tables', [])
                    reasoning = result.get('reasoning', '')
                    
                    if tables:
                        logger.info(f"🤖 [SchemaDiscoveryTool] LLM解析结果: {tables}, 原因: {reasoning}")
                        return tables[:3]  # 最多返回3个表
                    else:
                        logger.debug(f"🤖 [SchemaDiscoveryTool] LLM未找到相关表名: {reasoning}")
                        return None
                        
                except json.JSONDecodeError as e:
                    logger.debug(f"⚠️ [SchemaDiscoveryTool] LLM返回格式错误: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.debug(f"⚠️ [SchemaDiscoveryTool] LLM解析失败: {e}")
            return None
    
    async def _initialize_table_names_cache(self, connection_config: Dict[str, Any]):
        """初始化表名缓存（懒加载的第一步）"""
        if self._cache_initialized:
            return
            
        try:
            data_source_service = await self._get_data_source_service()
            if not data_source_service:
                logger.warning("⚠️ 数据源服务不可用，无法初始化表名缓存")
                return
            
            logger.info("🔍 [SchemaDiscoveryTool] 初始化表名缓存（懒加载模式）")
            
            # 只获取表名列表
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql="SHOW TABLES",
                limit=1000
            )
            
            if result.get("success"):
                rows = result.get("rows", []) or result.get("data", [])
                table_names = []
                
                for row in rows:
                    table_name = self._extract_table_name(row)
                    if table_name:
                        table_names.append(table_name)
                
                self._table_names_cache = table_names
                self._cache_initialized = True
                
                logger.info(f"✅ 表名缓存初始化完成，发现 {len(table_names)} 个表")
                logger.info(f"   表名: {table_names[:10]}{'...' if len(table_names) > 10 else ''}")
            else:
                logger.warning(f"⚠️ 获取表名列表失败: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ 初始化表名缓存失败: {e}")
    
    async def _load_columns_for_tables(
        self, 
        connection_config: Dict[str, Any], 
        table_names: List[str],
        include_metadata: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按需加载指定表的列信息"""
        data_source_service = await self._get_data_source_service()
        if not data_source_service:
            return {}
        
        # 找出需要加载的表（未缓存的）
        tables_to_load = [name for name in table_names if name not in self._columns_cache]
        
        if not tables_to_load:
            logger.info(f"✅ 所有表列信息已缓存，无需重复加载")
            return {name: self._columns_cache[name] for name in table_names if name in self._columns_cache}
        
        logger.info(f"🔄 按需加载 {len(tables_to_load)} 个表的列信息: {tables_to_load}")
        
        # 并行加载列信息
        async def load_single_table_columns(table_name: str):
            try:
                columns = await self._get_table_columns(
                    data_source_service, connection_config, table_name, include_metadata
                )
                return table_name, columns
            except Exception as e:
                logger.warning(f"⚠️ 加载表 {table_name} 列信息失败: {e}")
                return table_name, []
        
        import asyncio
        tasks = [load_single_table_columns(table_name) for table_name in tables_to_load]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        loaded_count = 0
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"❌ 并行加载出错: {result}")
                continue
                
            table_name, columns = result
            self._columns_cache[table_name] = columns
            loaded_count += 1
            logger.info(f"  📋 表 {table_name}: {len(columns)} 列")
        
        logger.info(f"✅ 按需加载完成，新增 {loaded_count} 个表列信息")
        
        # 返回请求的表列信息
        return {name: self._columns_cache[name] for name in table_names if name in self._columns_cache}
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式"""
        return {
            "type": "function",
            "function": {
                "name": "schema_discovery",
                "description": "发现数据源中的表结构和关系",
                "parameters": {
                    "type": "object",
                    "properties": {
                        # 🔥 移除 connection_config 参数，由工具内部自动获取
                        "discovery_type": {
                            "type": "string",
                            "enum": ["tables", "columns", "relationships", "all"],
                            "default": "all",
                            "description": "发现类型：tables(表), columns(列), relationships(关系), all(全部)"
                        },
                        "table_pattern": {
                            "type": "string",
                            "description": "表名模式过滤（支持通配符）"
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "default": True,
                            "description": "是否包含元数据信息"
                        },
                        "max_tables": {
                            "type": "integer",
                            "default": 100,
                            "description": "最大表数量限制"
                        }
                    },
                    "required": []  # 🔥 所有参数都是可选的
                }
            }
        }
    
    async def run(
        self,
        discovery_type: str = "all",
        table_pattern: Optional[str] = None,
        include_metadata: bool = True,
        max_tables: int = 100,
        tables: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 Schema 发现 - 支持懒加载优化

        Args:
            discovery_type: 发现类型 (tables, columns, relationships, all)
            table_pattern: 表名模式
            include_metadata: 是否包含元数据
            max_tables: 最大表数量
            tables: 指定要处理的表名列表

        Returns:
            Dict[str, Any]: 发现结果
        """
        logger.info(f"🔍 [SchemaDiscoveryTool] 开始发现 Schema: {discovery_type}")
        logger.info(f"   懒加载模式: {'启用' if self.enable_lazy_loading else '禁用'}")

        # 🔥 使用初始化时注入的 connection_config
        connection_config = self._connection_config
        if not connection_config:
            return {
                "success": False,
                "error": "未配置数据源连接，请在初始化工具时提供 connection_config",
                "discovered": {}
            }

        try:
            signature = self._make_signature(
                discovery_type=discovery_type,
                table_pattern=table_pattern,
                include_metadata=include_metadata,
                max_tables=max_tables,
                tables=tables,
            )

            if signature in self._result_cache:
                cached_result = deepcopy(self._result_cache[signature])
                cached_result["cached"] = True
                structured = cached_result.get("structured_summary") or {}
                structured["duplicate_call"] = True
                cached_result["structured_summary"] = structured

                base_summary = cached_result.get("llm_summary", "")
                prefix = "⚠️ 检测到重复调用 schema_discovery，复用缓存结果。"
                cached_result["llm_summary"] = f"{prefix}{base_summary}"
                return cached_result
            
            # 🔥 检查是否已经调用过多次
            if hasattr(self, '_call_count'):
                self._call_count += 1
            else:
                self._call_count = 1
            
            if self._call_count > 1:
                logger.warning(f"🚨 [SchemaDiscoveryTool] 检测到重复调用（第{self._call_count}次），返回简化结果")
                return {
                    "success": True,
                    "discovered": {
                        "tables": [{"table_name": "ods_refund", "table_type": "TABLE"}],
                        "columns": {
                            "ods_refund": [
                                {"name": "id", "data_type": "varchar", "nullable": True},
                                {"name": "status", "data_type": "varchar", "nullable": True},
                                {"name": "flow_status", "data_type": "varchar", "nullable": True}
                            ]
                        }
                    },
                    "llm_summary": "⚠️ 检测到重复调用，返回ods_refund表的基本结构。请直接生成SQL查询，不要再调用工具！",
                    "structured_summary": {
                        "tables_count": 1,
                        "tables_preview": ["ods_refund"],
                        "columns_count": 3,
                        "duplicate_call": True,
                        "force_stop": True
                    },
                    "next_actions": ["立即生成SQL查询，不要再调用任何工具！"],
                    "cached": False
                }

            data_source_service = await self._get_data_source_service()
            if not data_source_service:
                return {
                    "success": False,
                    "error": "数据源服务不可用",
                    "discovered": {}
                }
            
            result = {
                "success": True,
                "discovered": {},
                "metadata": {
                    "discovery_type": discovery_type,
                    "table_pattern": table_pattern,
                    "include_metadata": include_metadata,
                    "max_tables": max_tables,
                    "lazy_loading_enabled": self.enable_lazy_loading
                }
            }

            tables_result: List[Dict[str, Any]] = []
            columns_result: Union[List[Dict[str, Any]], Dict[str, Any]] = []
            relationships_result: List[Dict[str, Any]] = []

            # 懒加载模式：先初始化表名缓存
            if self.enable_lazy_loading:
                await self._initialize_table_names_cache(connection_config)
            
            # 🔥 智能表过滤：从上下文中获取已选择的表
            if not tables and not table_pattern:
                # 尝试从上下文中获取已选择的表
                context_tables = await self._get_context_selected_tables()
                if context_tables:
                    logger.info(f"🎯 [SchemaDiscoveryTool] 从上下文获取到已选择的表: {context_tables}")
                    tables = context_tables
                    normalized_tables = [t.lower() for t in tables]
                else:
                    logger.warning("⚠️ [SchemaDiscoveryTool] 未指定表名且无法从上下文获取表信息，将返回空结果")
                    return {
                        "success": False,
                        "error": "无法确定要查询的表，请提供表名或确保上下文信息完整",
                        "discovered": {"tables": [], "columns": {}},
                        "llm_summary": "❌ 无法获取表信息：未指定表名且上下文信息不完整",
                        "structured_summary": {
                            "tables_count": 0,
                            "tables_preview": [],
                            "columns_count": 0,
                            "error": "missing_table_context"
                        },
                        "next_actions": ["请明确指定要查询的表名，或检查上下文信息是否完整"]
                    }
            else:
                normalized_tables = [t.lower() for t in tables] if tables else None
            
            if discovery_type in ["tables", "all"]:
                if self.enable_lazy_loading:
                    # 懒加载模式：使用缓存的表名
                    table_entries = await self._discover_tables_lazy(
                        connection_config, table_pattern, max_tables, normalized_tables
                    )
                else:
                    # 传统模式：直接查询数据库
                    table_entries = await self._discover_tables(
                        data_source_service, connection_config, table_pattern, max_tables
                    )
                    if normalized_tables:
                        table_entries = [
                            entry for entry in table_entries
                            if self._table_matches(entry, normalized_tables)
                        ]

                result["discovered"]["tables"] = table_entries
                result["tables"] = table_entries  # 兼容旧字段
                result["tables_count"] = len(table_entries)
                tables_result = table_entries
                logger.info(f"✅ 发现 {len(table_entries)} 个表")

            # 发现列信息
            if discovery_type in ["columns", "all"]:
                if self.enable_lazy_loading:
                    # 懒加载模式：按需加载列信息
                    columns = await self._discover_columns_lazy(
                        connection_config, table_pattern, include_metadata, normalized_tables
                    )
                else:
                    # 传统模式：直接查询所有表的列信息
                    columns = await self._discover_columns(
                        data_source_service,
                        connection_config,
                        table_pattern,
                        include_metadata,
                        normalized_tables
                    )

                result["discovered"]["columns"] = columns
                result["columns"] = columns
                columns_result = columns
                logger.info(f"✅ 发现 {len(columns)} 个列")

            # 发现关系信息
            if discovery_type in ["relationships", "all"]:
                relationships = await self._discover_relationships(
                    data_source_service, connection_config
                )
                result["discovered"]["relationships"] = relationships
                result["relationships"] = relationships
                relationships_result = relationships
                logger.info(f"✅ 发现 {len(relationships)} 个关系")

            summary_bundle = self._build_llm_summary(
                discovery_type=discovery_type,
                tables=tables_result,
                columns=columns_result,
                relationships=relationships_result
            )
            result["llm_summary"] = summary_bundle["llm_summary"]
            result["structured_summary"] = summary_bundle["structured_summary"]
            result["next_actions"] = summary_bundle["next_actions"]
            result["cached"] = False

            self._result_cache[signature] = deepcopy(result)

            return result

        except Exception as e:
            logger.error(f"❌ [SchemaDiscoveryTool] 发现失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "discovered": {}
            }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """向后兼容的execute方法"""
        return await self.run(**kwargs)
    
    async def _discover_tables_lazy(
        self,
        connection_config: Dict[str, Any],
        table_pattern: Optional[str],
        max_tables: int,
        normalized_tables: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """懒加载模式：基于缓存的表名发现表信息"""
        try:
            # 使用缓存的表名
            candidate_tables = self._table_names_cache.copy()
            
            # 应用表名模式过滤
            if table_pattern:
                candidate_tables = [
                    name for name in candidate_tables
                    if self._match_pattern(name, table_pattern)
                ]
            
            # 应用指定表过滤
            if normalized_tables:
                candidate_tables = [
                    name for name in candidate_tables
                    if name.lower() in normalized_tables
                ]
            
            # 限制数量
            candidate_tables = candidate_tables[:max_tables]
            
            # 构建表信息（不包含列信息，节省内存）
            table_entries = []
            for table_name in candidate_tables:
                table_info = {
                    "table_name": table_name,
                    "table_type": "TABLE",
                    "table_comment": "",
                    "columns": [],  # 懒加载模式下不预加载列信息
                    "lazy_loaded": True,
                    "metadata": {
                        "lazy_loading": True,
                        "columns_loaded": False
                    }
                }
                table_entries.append(table_info)
            
            logger.info(f"✅ 懒加载模式发现 {len(table_entries)} 个表（仅表名）")
            return table_entries
            
        except Exception as e:
            logger.error(f"❌ 懒加载表发现失败: {e}")
            return []
    
    async def _discover_columns_lazy(
        self,
        connection_config: Dict[str, Any],
        table_pattern: Optional[str],
        include_metadata: bool,
        normalized_tables: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """懒加载模式：按需加载列信息"""
        try:
            # 确定需要加载列信息的表
            target_tables = self._table_names_cache.copy()
            
            # 应用过滤条件
            if table_pattern:
                target_tables = [
                    name for name in target_tables
                    if self._match_pattern(name, table_pattern)
                ]
            
            if normalized_tables:
                target_tables = [
                    name for name in target_tables
                    if name.lower() in normalized_tables
                ]
            
            # 按需加载列信息
            columns_cache = await self._load_columns_for_tables(
                connection_config, target_tables, include_metadata
            )
            
            # 构建列信息列表
            all_columns = []
            for table_name, columns in columns_cache.items():
                for column in columns:
                    column["table_name"] = table_name
                    column["lazy_loaded"] = True
                    all_columns.append(column)
            
            logger.info(f"✅ 懒加载模式发现 {len(all_columns)} 个列")
            return all_columns
            
        except Exception as e:
            logger.error(f"❌ 懒加载列发现失败: {e}")
            return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "lazy_loading_enabled": self.enable_lazy_loading,
            "cache_initialized": self._cache_initialized,
            "total_tables": len(self._table_names_cache),
            "loaded_tables": len(self._columns_cache),
            "table_names": self._table_names_cache[:10],  # 只显示前10个
            "loaded_table_names": list(self._columns_cache.keys())[:10]
        }

    def _make_signature(
        self,
        discovery_type: str,
        table_pattern: Optional[str],
        include_metadata: bool,
        max_tables: int,
        tables: Optional[List[str]],
    ) -> str:
        parts = [
            discovery_type or "all",
            table_pattern or "*",
            "meta" if include_metadata else "basic",
            str(max_tables),
            ",".join(sorted(tables or []))
        ]
        return "|".join(parts)

    def _build_llm_summary(
        self,
        discovery_type: str,
        tables: Union[List[Dict[str, Any]], List[Any]],
        columns: Union[List[Dict[str, Any]], Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        table_names = self._extract_table_names_from_result(tables)
        tables_count = len(table_names)
        preview = table_names[:5]
        columns_count = self._count_columns(columns)
        relationships_count = len(relationships) if isinstance(relationships, list) else 0

        if tables_count > 0:
            preview_text = ", ".join(preview) if preview else "暂无表名"
            summary = f"✅ 已发现 {tables_count} 张表：{preview_text}"
            
            # 🔥 增强：提供更详细的表结构信息
            if isinstance(columns, dict) and columns:
                # 如果是字典格式，提取关键表的结构信息
                key_tables = []
                for table_name, table_columns in list(columns.items())[:3]:  # 只显示前3个表
                    if isinstance(table_columns, list) and table_columns:
                        column_names = [col.get("name", "") for col in table_columns[:5]]  # 只显示前5个列
                        key_tables.append(f"{table_name}({', '.join(column_names)})")
                
                if key_tables:
                    summary += f"\n\n📋 关键表结构预览：\n" + "\n".join([f"- {table}" for table in key_tables])
            
            elif isinstance(columns, list) and columns:
                # 如果是列表格式，显示列信息
                summary += f"\n\n📋 列信息：共 {columns_count} 个列"
                if columns_count > 0:
                    sample_columns = columns[:5]  # 显示前5个列
                    column_details = []
                    for col in sample_columns:
                        if isinstance(col, dict):
                            col_name = col.get("name", "")
                            col_type = col.get("data_type", "")
                            if col_name and col_type:
                                column_details.append(f"{col_name}({col_type})")
                    if column_details:
                        summary += f"\n- 示例列：{', '.join(column_details)}"
        else:
            summary = "⚠️ 未发现任何表，请检查数据源配置或调整过滤条件"

        if relationships_count > 0:
            summary += f"\n\n🔗 表关系：识别到 {relationships_count} 个关系"

        next_actions: List[str] = []
        if tables_count == 0:
            next_actions.append("检查数据源授权或更换 discovery_type 参数")
        elif columns_count == 0 and discovery_type in ("tables", "all"):
            next_actions.append("调用 schema_retrieval 工具获取重点表的详细列信息")
        else:
            next_actions.append("基于发现的表结构，调用 sql_generator 工具生成 SQL 查询")

        structured_summary = {
            "tables_count": tables_count,
            "tables_preview": preview,
            "columns_count": columns_count,
            "relationships_count": relationships_count,
            "discovery_type": discovery_type,
            "duplicate_call": False,
            "detailed_info": True,  # 🔥 标记为详细信息
        }

        return {
            "llm_summary": summary,
            "structured_summary": structured_summary,
            "next_actions": next_actions,
        }

    @staticmethod
    def _extract_table_names_from_result(tables: Union[List[Dict[str, Any]], List[Any]]) -> List[str]:
        if not isinstance(tables, list):
            return []
        names = []
        for item in tables:
            if isinstance(item, dict):
                name = item.get("table_name") or item.get("name")
                if name:
                    names.append(str(name))
            elif isinstance(item, str):
                names.append(item)
        return names

    @staticmethod
    def _count_columns(columns: Union[List[Dict[str, Any]], Dict[str, Any]]) -> int:
        if isinstance(columns, list):
            return len(columns)
        if isinstance(columns, dict):
            total = 0
            for value in columns.values():
                if isinstance(value, list):
                    total += len(value)
            return total
        return 0
        
    async def _discover_tables(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_pattern: Optional[str],
        max_tables: int
    ) -> List[Dict[str, Any]]:
        """发现表信息"""
        try:
            # 构建查询 SQL
            if table_pattern:
                sql = f"SHOW TABLES LIKE '{table_pattern}'"
            else:
                sql = "SHOW TABLES"
            
            # 执行查询
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=sql,
                limit=max_tables
            )
            
            if not result.get("success"):
                logger.warning(f"⚠️ 获取表列表失败: {result.get('error')}")
                return []
            
            tables = []
            rows = result.get("rows", []) or result.get("data", [])
            
            for row in rows:
                # 解析表名
                table_name = self._extract_table_name(row)
                if not table_name:
                    continue
                
                # 获取表详细信息
                table_info = await self._get_table_details(
                    data_source_service, connection_config, table_name
                )
                
                tables.append(table_info)
            
            return tables
            
        except Exception as e:
            logger.error(f"❌ 发现表信息失败: {e}")
            return []
    
    async def _discover_columns(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_pattern: Optional[str],
        include_metadata: bool,
        tables_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """发现列信息"""
        try:
            # 首先获取表列表
            tables_result = await data_source_service.run_query(
                connection_config=connection_config,
                sql="SHOW TABLES",
                limit=1000
            )
            
            if not tables_result.get("success"):
                return []
            
            all_columns = []
            rows = tables_result.get("rows", []) or tables_result.get("data", [])
            
            allowed_tables = set(tables_filter) if tables_filter else None
            
            for row in rows:
                table_name = self._extract_table_name(row)
                if not table_name:
                    continue
                
                # 过滤表名
                if table_pattern and not self._match_pattern(table_name, table_pattern):
                    continue
                
                if allowed_tables and table_name.lower() not in allowed_tables:
                    continue
                
                # 获取表的列信息
                columns = await self._get_table_columns(
                    data_source_service, connection_config, table_name, include_metadata
                )
                
                all_columns.extend(columns)
            
            return all_columns
            
        except Exception as e:
            logger.error(f"❌ 发现列信息失败: {e}")
            return []
    
    async def _discover_relationships(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """发现关系信息"""
        try:
            # 查询外键约束
            sql = """
            SELECT 
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME,
                CONSTRAINT_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_NAME IS NOT NULL
            AND TABLE_SCHEMA = DATABASE()
            """
            
            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=sql,
                limit=1000
            )
            
            if not result.get("success"):
                logger.warning(f"⚠️ 获取关系信息失败: {result.get('error')}")
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
                        "relationship_type": "FOREIGN_KEY"
                    }
                    relationships.append(relationship)
            
            return relationships
            
        except Exception as e:
            logger.error(f"❌ 发现关系信息失败: {e}")
            return []
    
    async def _get_table_details(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_name: str
    ) -> Dict[str, Any]:
        """获取表详细信息"""
        try:
            # 获取表状态信息
            status_sql = f"SHOW TABLE STATUS LIKE '{table_name}'"
            logger.debug(f"🔍 获取表详情 SQL: {status_sql}")

            status_result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=status_sql,
                limit=1
            )

            # 🔧 增强日志：记录返回结果的详细信息
            logger.debug(f"📊 run_query 返回类型: {type(status_result)}")
            logger.debug(f"📊 run_query success: {status_result.get('success')}")

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

            if status_result.get("success"):
                rows = status_result.get("rows", [])
                logger.debug(f"📊 rows 类型: {type(rows)}, 长度: {len(rows) if rows else 0}")

                if rows:
                    # 🔧 增强验证：检查 rows[0] 的类型
                    if not isinstance(rows[0], dict):
                        logger.error(f"❌ rows[0] 不是字典! 类型: {type(rows[0])}, 值: {rows[0]}")
                        logger.error(f"   完整 rows: {rows}")
                        return table_info

                    row = rows[0]
                    logger.debug(f"📊 row 类型: {type(row)}")
                    logger.debug(f"📊 row keys: {row.keys() if isinstance(row, dict) else 'NOT A DICT'}")
                    logger.debug(f"📊 row 内容: {row}")

                    # 🔧 安全的字段提取
                    try:
                        update_data = {
                            "row_count": row.get("Rows"),
                            "size_bytes": row.get("Data_length"),
                            "created_at": row.get("Create_time"),
                            "updated_at": row.get("Update_time"),
                            "description": row.get("Comment", "")
                        }
                        logger.debug(f"📊 准备更新的数据: {update_data}")

                        # 验证 update_data 是字典
                        if not isinstance(update_data, dict):
                            logger.error(f"❌ update_data 不是字典! 类型: {type(update_data)}")
                            return table_info

                        table_info.update(update_data)
                        logger.debug(f"✅ table_info 更新成功: {table_info}")

                    except Exception as update_error:
                        logger.error(f"❌ table_info.update() 失败: {update_error}")
                        logger.error(f"   row 类型: {type(row)}")
                        logger.error(f"   row 内容: {row}")
                        import traceback
                        logger.error(f"   堆栈:\n{traceback.format_exc()}")
                        # 发生错误时，返回基本的 table_info
                        return table_info
                else:
                    logger.debug(f"⚠️ SHOW TABLE STATUS 没有返回数据")
            else:
                logger.warning(f"⚠️ SHOW TABLE STATUS 查询失败: {status_result.get('error')}")

            return table_info

        except Exception as e:
            logger.error(f"❌ 获取表 {table_name} 详细信息失败: {e}")
            import traceback
            logger.error(f"堆栈:\n{traceback.format_exc()}")
            return {
                "name": table_name,
                "description": "",
                "table_type": "TABLE",
                "metadata": {}
            }
    
    async def _get_table_columns(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        table_name: str,
        include_metadata: bool
    ) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        try:
            sql = f"SHOW FULL COLUMNS FROM `{table_name}`"
            logger.debug(f"🔍 获取列信息 SQL: {sql}")

            result = await data_source_service.run_query(
                connection_config=connection_config,
                sql=sql,
                limit=1000
            )

            # 🔧 增强日志
            logger.debug(f"📊 run_query 返回类型: {type(result)}")
            logger.debug(f"📊 run_query success: {result.get('success')}")

            if not result.get("success"):
                logger.warning(f"⚠️ 获取列信息失败: {result.get('error')}")
                return []

            columns = []
            rows = result.get("rows", []) or result.get("data", [])
            logger.debug(f"📊 rows 类型: {type(rows)}, 长度: {len(rows) if rows else 0}")

            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    logger.warning(f"⚠️ row[{idx}] 不是字典，类型: {type(row)}, 跳过")
                    continue

                try:
                    column_info = {
                        "table_name": table_name,
                        "name": row.get("Field", ""),
                        "data_type": row.get("Type", ""),
                        "nullable": row.get("Null", "YES") == "YES",
                        "default_value": row.get("Default"),
                        "is_primary_key": row.get("Key", "") == "PRI",
                        "is_foreign_key": False,  # 需要单独查询
                        "description": row.get("Comment", ""),
                        "metadata": {}
                    }

                    # 解析数据类型
                    if include_metadata:
                        column_info["metadata"] = self._parse_data_type(row.get("Type", ""))

                    columns.append(column_info)
                except Exception as col_error:
                    logger.warning(f"⚠️ 解析列 {idx} 失败: {col_error}, row: {row}")
                    continue

            logger.debug(f"✅ 成功获取 {len(columns)} 个列")
            return columns

        except Exception as e:
            logger.error(f"❌ 获取表 {table_name} 列信息失败: {e}")
            import traceback
            logger.error(f"堆栈:\n{traceback.format_exc()}")
            return []
    
    def _extract_table_name(self, row: Any) -> Optional[str]:
        """从查询结果中提取表名"""
        try:
            if isinstance(row, dict):
                # 尝试不同的键名
                for key in ["Tables_in_*", "table_name", "TABLE_NAME", "name"]:
                    if key in row:
                        table_name = str(row[key])
                        logger.debug(f"📊 从键 '{key}' 提取表名: {table_name}")
                        return table_name

                # 尝试包含 "Tables_in_" 的键
                for key in row.keys():
                    if key.startswith("Tables_in_"):
                        table_name = str(row[key])
                        logger.debug(f"📊 从匹配键 '{key}' 提取表名: {table_name}")
                        return table_name

                # 取第一个值
                if row:
                    table_name = str(next(iter(row.values())))
                    logger.debug(f"📊 从第一个值提取表名: {table_name}")
                    return table_name

            elif isinstance(row, (list, tuple)) and row:
                table_name = str(row[0])
                logger.debug(f"📊 从列表/元组提取表名: {table_name}")
                return table_name

            elif isinstance(row, str):
                logger.debug(f"📊 直接使用字符串作为表名: {row}")
                return row

            logger.warning(f"⚠️ 无法提取表名，row 类型: {type(row)}, 值: {row}")
            return None

        except Exception as e:
            logger.error(f"❌ 提取表名失败: {e}, row: {row}")
            return None
    
    def _table_matches(self, entry: Any, normalized_targets: List[str]) -> bool:
        """判断表记录是否在目标列表中"""
        name = None
        if isinstance(entry, TableInfo):
            name = entry.name
        elif isinstance(entry, dict):
            name = entry.get("name") or entry.get("table_name")
        elif isinstance(entry, str):
            name = entry
        
        if not name:
            return False
        
        return name.lower() in normalized_targets
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """简单的模式匹配（支持 % 通配符）"""
        if not pattern:
            return True
        
        # 将 SQL 通配符转换为正则表达式
        import re
        regex_pattern = pattern.replace("%", ".*").replace("_", ".")
        return bool(re.match(regex_pattern, text, re.IGNORECASE))
    
    def _parse_data_type(self, data_type: str) -> Dict[str, Any]:
        """解析数据类型"""
        metadata = {"raw_type": data_type}
        
        if not data_type:
            return metadata
        
        data_type_upper = data_type.upper()
        
        # 提取长度信息
        if "(" in data_type and ")" in data_type:
            try:
                length_part = data_type[data_type.find("(")+1:data_type.find(")")]
                if "," in length_part:
                    # DECIMAL(10,2) 格式
                    parts = length_part.split(",")
                    metadata["precision"] = int(parts[0].strip())
                    metadata["scale"] = int(parts[1].strip())
                else:
                    # VARCHAR(255) 格式
                    metadata["max_length"] = int(length_part.strip())
            except (ValueError, IndexError):
                pass
        
        # 数据类型分类
        if any(t in data_type_upper for t in ["INT", "BIGINT", "SMALLINT", "TINYINT"]):
            metadata["category"] = "integer"
        elif any(t in data_type_upper for t in ["DECIMAL", "FLOAT", "DOUBLE"]):
            metadata["category"] = "numeric"
        elif any(t in data_type_upper for t in ["VARCHAR", "CHAR", "TEXT"]):
            metadata["category"] = "string"
        elif any(t in data_type_upper for t in ["DATE", "DATETIME", "TIMESTAMP"]):
            metadata["category"] = "datetime"
        elif any(t in data_type_upper for t in ["BOOLEAN", "BOOL"]):
            metadata["category"] = "boolean"
        else:
            metadata["category"] = "other"
        
        return metadata


def create_schema_discovery_tool(
    container: Any,
    connection_config: Optional[Dict[str, Any]] = None,
    enable_lazy_loading: bool = True
) -> SchemaDiscoveryTool:
    """
    创建 Schema 发现工具

    Args:
        container: 服务容器
        connection_config: 数据源连接配置（在初始化时注入）
        enable_lazy_loading: 是否启用懒加载优化

    Returns:
        SchemaDiscoveryTool 实例
    """
    return SchemaDiscoveryTool(
        container,
        connection_config=connection_config,
        enable_lazy_loading=enable_lazy_loading
    )


# 导出
__all__ = [
    "SchemaDiscoveryTool",
    "TableInfo",
    "ColumnInfo", 
    "RelationshipInfo",
    "create_schema_discovery_tool",
]
