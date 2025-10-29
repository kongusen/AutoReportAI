"""
智能上下文检索器

基于 Loom 0.0.3 的 ContextRetriever 机制，为 Agent 提供动态表结构上下文注入
实现零工具调用的 Schema 注入，提升 Agent 的准确性和性能
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Set
from loom.interfaces.retriever import BaseRetriever, Document

from .types import BaseContextRetriever, ContextInfo, ExecutionStage
from .intelligent_retriever import (
    IntelligentSchemaRetriever, RetrievalConfig,
    create_intelligent_retriever
)

logger = logging.getLogger(__name__)


class SchemaContextRetriever(BaseRetriever):
    """
    表结构上下文检索器
    
    功能：
    1. 初始化时获取数据源的所有表结构信息
    2. 根据用户查询检索相关的表和列信息
    3. 格式化为 Document 供 Agent 使用
    4. 支持阶段感知的上下文管理
    """

    def __init__(
        self,
        data_source_id: str,
        connection_config: Dict[str, Any],
        container: Any,
        top_k: int = 5,
        enable_stage_aware: bool = True,
        use_intelligent_retrieval: bool = True,
        enable_lazy_loading: bool = True
    ):
        """
        Args:
            data_source_id: 数据源ID
            connection_config: 数据源连接配置
            container: 服务容器，用于获取数据源服务
            top_k: 默认返回的表数量
            enable_stage_aware: 是否启用阶段感知
            use_intelligent_retrieval: 是否使用智能检索（TF-IDF）
            enable_lazy_loading: 是否启用懒加载（启动时只获取表名）
        """
        self.data_source_id = data_source_id
        self.connection_config = connection_config
        self.container = container
        self.top_k = top_k
        self.enable_stage_aware = enable_stage_aware
        self.use_intelligent_retrieval = use_intelligent_retrieval
        self.enable_lazy_loading = enable_lazy_loading

        # Schema 缓存
        self.schema_cache: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

        # 懒加载相关属性
        self.table_names: List[str] = []
        self.loaded_tables: Set[str] = set()

        # 阶段感知状态
        self.current_stage = ExecutionStage.INITIALIZATION
        self.stage_context_cache: Dict[str, List[Document]] = {}
        self.recent_selected_tables = None  # 保存最近选择的表

        # 智能检索器（延迟初始化）
        self._intelligent_retriever: Optional[IntelligentSchemaRetriever] = None

    async def initialize(self):
        """初始化：懒加载模式下只获取表名，传统模式下获取所有表结构"""
        if self._initialized:
            return

        try:
            if self.enable_lazy_loading:
                logger.info(f"🔍 开始初始化数据源 {self.data_source_id} 的表名缓存（懒加载模式）")
            else:
                logger.info(f"🔍 开始初始化数据源 {self.data_source_id} 的 schema 缓存（传统模式）")

            # 获取数据源服务
            data_source_service = getattr(self.container, 'data_source', None) or \
                                 getattr(self.container, 'data_source_service', None)

            if not data_source_service:
                logger.warning("⚠️ 未找到数据源服务，无法初始化 schema 缓存")
                self._initialized = True
                return

            # 1. 获取所有表名
            tables_sql = "SHOW TABLES"
            tables_result = await data_source_service.run_query(
                connection_config=self.connection_config,
                sql=tables_sql,
                limit=1000
            )

            if not isinstance(tables_result, dict) or not tables_result.get('success'):
                error_info = tables_result.get('error', 'Unknown error') if isinstance(tables_result, dict) else str(tables_result)
                logger.warning(f"⚠️ 获取表列表失败: {error_info}")
                self._initialized = True
                return

            # 解析表名
            tables = []
            for row in tables_result.get('rows', []) or tables_result.get('data', []):
                if isinstance(row, dict):
                    table_name = next(iter(row.values())) if row else None
                elif isinstance(row, (list, tuple)) and row:
                    table_name = row[0]
                elif isinstance(row, str):
                    table_name = row
                else:
                    table_name = None

                if table_name:
                    tables.append(str(table_name))

            self.table_names = tables
            logger.info(f"✅ 发现 {len(tables)} 个表")

            if self.enable_lazy_loading:
                # 懒加载模式：只缓存表名，不获取列信息
                logger.info(f"✅ 表名缓存初始化完成（懒加载模式）")
                logger.info(f"   表名: {tables[:10]}{'...' if len(tables) > 10 else ''}")
                self._initialized = True
                return

            # 传统模式：并行获取每个表的列信息
            async def fetch_table_columns(table_name: str):
                """获取单个表的列信息"""
                try:
                    columns_sql = f"SHOW FULL COLUMNS FROM `{table_name}`"
                    columns_result = await data_source_service.run_query(
                        connection_config=self.connection_config,
                        sql=columns_sql,
                        limit=1000
                    )

                    if isinstance(columns_result, dict) and columns_result.get('success'):
                        rows = columns_result.get('rows', []) or columns_result.get('data', [])
                        columns = []

                        for row in rows:
                            if isinstance(row, dict):
                                columns.append({
                                    'name': row.get('Field') or row.get('column_name') or row.get('COLUMN_NAME') or '',
                                    'type': row.get('Type') or row.get('column_type') or row.get('DATA_TYPE') or '',
                                    'nullable': row.get('Null') or row.get('IS_NULLABLE'),
                                    'key': row.get('Key') or row.get('COLUMN_KEY'),
                                    'default': row.get('Default'),
                                    'comment': row.get('Comment') or row.get('COLUMN_COMMENT') or '',
                                })

                        return table_name, {
                            'table_name': table_name,
                            'columns': [col for col in columns if col.get('name')],
                            'table_comment': '',
                            'table_type': 'TABLE',
                        }
                    else:
                        logger.warning(f"⚠️ 获取表 {table_name} 列信息失败")
                        return table_name, None
                except Exception as e:
                    logger.warning(f"⚠️ 获取表 {table_name} 的列信息失败: {e}")
                    return table_name, None

            # 并行执行所有表的列信息查询
            import asyncio
            tasks = [fetch_table_columns(table_name) for table_name in tables]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"❌ 并行查询出错: {result}")
                    continue
                    
                table_name, table_info = result
                if table_info:
                    self.schema_cache[table_name] = table_info
                    self.loaded_tables.add(table_name)
                    logger.info(f"  📋 表 {table_name}: {len(table_info['columns'])} 列")

            logger.info(f"✅ Schema 缓存初始化完成，共 {len(self.schema_cache)} 个表")

            # 初始化智能检索器
            if self.use_intelligent_retrieval and self.schema_cache:
                logger.info("🔧 初始化智能检索器（TF-IDF）...")
                self._intelligent_retriever = create_intelligent_retriever(
                    schema_cache=self.schema_cache,
                    config=RetrievalConfig(
                        use_tfidf=True,
                        enable_synonyms=True,
                        enable_caching=True
                    )
                )
                await self._intelligent_retriever.initialize()
                logger.info("✅ 智能检索器初始化完成")

            self._initialized = True

        except Exception as e:
            logger.error(f"❌ Schema 缓存初始化失败: {e}", exc_info=True)

    async def _load_tables_on_demand(self, table_names: List[str]):
        """按需加载表的列信息"""
        # 找出需要加载的表（未缓存的）
        tables_to_load = [name for name in table_names if name not in self.loaded_tables]
        
        if not tables_to_load:
            logger.info(f"✅ 所有表已加载，无需重复查询")
            return
        
        logger.info(f"🔄 按需加载 {len(tables_to_load)} 个表的列信息: {tables_to_load}")
        
        # 获取数据源服务
        data_source_service = getattr(self.container, 'data_source', None) or \
                             getattr(self.container, 'data_source_service', None)
        
        if not data_source_service:
            logger.warning("⚠️ 数据源服务不可用，无法加载表结构")
            return

        # 并行加载表结构
        async def load_table_columns(table_name: str):
            """加载单个表的列信息"""
            try:
                columns_sql = f"SHOW FULL COLUMNS FROM `{table_name}`"
                columns_result = await data_source_service.run_query(
                    connection_config=self.connection_config,
                    sql=columns_sql,
                    limit=1000
                )

                if isinstance(columns_result, dict) and columns_result.get('success'):
                    rows = columns_result.get('rows', []) or columns_result.get('data', [])
                    columns = []

                    for row in rows:
                        if isinstance(row, dict):
                            columns.append({
                                'name': row.get('Field') or row.get('column_name') or row.get('COLUMN_NAME') or '',
                                'type': row.get('Type') or row.get('column_type') or row.get('DATA_TYPE') or '',
                                'nullable': row.get('Null') or row.get('IS_NULLABLE'),
                                'key': row.get('Key') or row.get('COLUMN_KEY'),
                                'default': row.get('Default'),
                                'comment': row.get('Comment') or row.get('COLUMN_COMMENT') or '',
                            })

                    return table_name, {
                        'table_name': table_name,
                        'columns': [col for col in columns if col.get('name')],
                        'table_comment': '',
                        'table_type': 'TABLE',
                    }
                else:
                    logger.warning(f"⚠️ 获取表 {table_name} 列信息失败")
                    return table_name, None
            except Exception as e:
                logger.warning(f"⚠️ 获取表 {table_name} 的列信息失败: {e}")
                return table_name, None

        # 并行执行
        import asyncio
        tasks = [load_table_columns(table_name) for table_name in tables_to_load]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        loaded_count = 0
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"❌ 并行查询出错: {result}")
                continue
                
            table_name, table_info = result
            if table_info:
                self.schema_cache[table_name] = table_info
                self.loaded_tables.add(table_name)
                loaded_count += 1
                logger.info(f"  📋 表 {table_name}: {len(table_info['columns'])} 列")

        logger.info(f"✅ 按需加载完成，新增 {loaded_count} 个表结构")
        
        # 如果这是第一次加载表结构，初始化智能检索器
        if self.use_intelligent_retrieval and self.schema_cache and self._intelligent_retriever is None:
            logger.info("🔧 初始化智能检索器（LLM）...")
            self._intelligent_retriever = create_intelligent_retriever(
                schema_cache=self.schema_cache,
                config=RetrievalConfig(
                    use_llm_judgment=True,
                    llm_model="gpt-4o-mini",
                    enable_caching=True
                ),
                container=self.container
            )
            await self._intelligent_retriever.initialize()
            logger.info("✅ 智能检索器初始化完成")

    async def retrieve_for_query(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        为查询检索相关文档 - Loom ContextRetriever 标准接口

        这是 Loom TT 递归模式要求的标准方法名

        Args:
            query: 用户的业务需求描述
            top_k: 返回最相关的 top_k 个表
            filters: 可选的过滤条件

        Returns:
            Document 列表，每个 Document 包含一个表的完整结构信息
        """
        return await self.retrieve(query, top_k, filters)

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        根据查询检索相关的表结构文档 - 支持懒加载

        Args:
            query: 用户的业务需求描述
            top_k: 返回最相关的 top_k 个表
            filters: 可选的过滤条件

        Returns:
            Document 列表，每个 Document 包含一个表的完整结构信息
        """
        # 🔥 净化查询：只保留业务需求，去除系统指令和递归内容
        query = self._sanitize_query(query)
        
        logger.info(f"🔍 [SchemaContextRetriever.retrieve] 被调用")
        logger.info(f"   查询内容（前200字符）: {query[:200]}")
        logger.info(f"   懒加载模式: {'启用' if self.enable_lazy_loading else '禁用'}")

        top_k = top_k or self.top_k
        logger.info(f"   请求返回 top_k={top_k} 个表")

        if not self._initialized:
            logger.info("   Schema 缓存未初始化，正在初始化...")
            await self.initialize()

        # 懒加载模式：基于大模型的智能表名匹配和迭代优化
        if self.enable_lazy_loading:
            if not self.table_names:
                logger.warning("⚠️ 表名列表为空，无法提供上下文")
                return []
            
            # 第一步：使用大模型进行表名匹配
            candidate_tables = await self._filter_tables_by_name(query, self.table_names)
            
            # 第二步：按需加载相关表的列信息
            await self._load_tables_on_demand(candidate_tables[:top_k * 2])
            
            # 第三步：基于列信息进行验证和优化
            if not self.schema_cache:
                raise Exception("Schema缓存为空，无法进行列信息验证")
            
            # 提取列信息
            table_columns = {}
            for table_name in candidate_tables:
                if table_name in self.schema_cache:
                    table_columns[table_name] = self.schema_cache[table_name].get('columns', [])
            
            # 使用大模型验证和优化表选择
            refined_tables = await self._validate_and_refine_tables(query, candidate_tables, table_columns)
            
            # 保存最近选择的表到上下文
            self.recent_selected_tables = refined_tables
            logger.info(f"💾 [SchemaContextRetriever] 保存最近选择的表: {refined_tables}")
            
            # 使用优化后的表进行检索
            documents = await self._intelligent_retrieve(query, top_k, filters, refined_tables)
        else:
            # 传统模式
            if not self.schema_cache:
                logger.warning("⚠️ Schema 缓存为空，无法提供上下文")
                return []
            
            # 智能检索策略
            documents = await self._intelligent_retrieve(query, top_k, filters)

        # 检查阶段感知缓存
        if self.enable_stage_aware:
            cache_key = f"{query[:100]}_{top_k}"
            if cache_key in self.stage_context_cache:
                cached_docs = self.stage_context_cache[cache_key]
                # 🔥 关键修复：不要返回空缓存，重新检索
                if len(cached_docs) > 0:
                    logger.info(f"✅ 使用阶段感知缓存，返回 {len(cached_docs)} 个表")
                    return cached_docs
                else:
                    logger.warning(f"⚠️ 缓存为空，重新检索")
                    # 清除这个空缓存
                    del self.stage_context_cache[cache_key]

            # 更新阶段感知缓存（仅当结果非空时）
            if len(documents) > 0:
                self.stage_context_cache[cache_key] = documents
                # 限制缓存大小
                if len(self.stage_context_cache) > 50:
                    # 删除最旧的缓存
                    oldest_key = next(iter(self.stage_context_cache))
                    del self.stage_context_cache[oldest_key]
            else:
                logger.warning(f"⚠️ 检索结果为空，不缓存此结果")

        logger.info(f"✅ [SchemaContextRetriever] 检索到 {len(documents)} 个相关表")
        logger.info(f"   返回的表: {[d.metadata['table_name'] for d in documents]}")

        return documents

    async def _intelligent_retrieve(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
        refined_tables: Optional[List[str]] = None
    ) -> List[Document]:
        """
        智能检索策略

        使用LLM进行智能表名匹配，不再使用算法回退
        支持基于大模型优化后的表名列表
        """
        # 使用LLM智能检索器
        if self._intelligent_retriever is not None:
            # 使用LLM检索
            stage_str = self.current_stage.value if self.enable_stage_aware else None
            scored_tables = await self._intelligent_retriever.retrieve(
                query=query,
                top_k=top_k,
                stage=stage_str
            )

            # 如果提供了优化后的表名，优先使用这些表
            if refined_tables:
                # 过滤出优化后的表
                filtered_scored_tables = []
                for table_name, score in scored_tables:
                    if table_name in refined_tables:
                        filtered_scored_tables.append((table_name, score))
                
                # 如果过滤后的结果为空，使用原始结果
                if filtered_scored_tables:
                    scored_tables = filtered_scored_tables
                    logger.info(f"🎯 [LLM检索] 使用优化后的表名: {refined_tables}")

            # 转换为 Document 格式
            documents = []
            for table_name, score in scored_tables:
                if table_name not in self.schema_cache:
                    continue

                table_info = self.schema_cache[table_name]
                content = self._format_table_info(table_name, table_info)

                doc = Document(
                    content=content,
                    metadata={
                        "source": "schema",
                        "table_name": table_name,
                        "data_source_id": self.data_source_id,
                        "relevance_score": score,
                        "stage": self.current_stage.value,
                        "retrieval_method": "llm_intelligent",
                    },
                    score=score
                )
                documents.append(doc)

            if documents:
                logger.info(f"✅ [LLM检索] 返回 {len(documents)} 个表")
                return documents
            else:
                logger.warning(f"⚠️ [LLM检索] 未找到相关表")
                raise Exception(f"LLM检索未找到相关表: {query}")
        else:
            logger.error("❌ [LLM检索] 智能检索器未初始化")
            raise Exception("智能检索器未初始化，无法进行检索")

    async def _keyword_retrieve(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
        refined_tables: Optional[List[str]] = None
    ) -> List[Document]:
        """基础关键词检索（降级方案）"""
        query_lower = query.lower()
        scored_tables = []

        # 如果提供了优化后的表名，优先使用这些表
        target_tables = refined_tables if refined_tables else list(self.schema_cache.keys())

        # 1. 基础关键词匹配
        for table_name in target_tables:
            if table_name not in self.schema_cache:
                continue
            table_info = self.schema_cache[table_name]
            score = 0.0

            # 表名匹配
            if table_name.lower() in query_lower:
                score += 10.0

            # 表注释匹配
            comment = table_info.get('table_comment') or ''
            if comment and any(keyword in comment.lower() for keyword in query_lower.split()):
                score += 5.0

            # 列名匹配
            for column in table_info.get('columns', []):
                col_name = (column.get('name') or '').lower()
                col_comment = column.get('comment') or ''

                if col_name in query_lower:
                    score += 3.0
                if col_comment and any(keyword in col_comment.lower() for keyword in query_lower.split()):
                    score += 1.0

            if score > 0:
                scored_tables.append((table_name, table_info, score))

        # 2. 阶段感知优化
        if self.enable_stage_aware:
            scored_tables = self._apply_stage_aware_scoring(scored_tables, query)

        # 3. 按分数排序，取 top_k
        scored_tables.sort(key=lambda x: x[2], reverse=True)
        top_tables = scored_tables[:top_k]

        if not top_tables:
            raise Exception(f"没有表匹配查询关键词: {query}")

        # 转换为 Document 格式
        documents = []
        for table_name, table_info, score in top_tables:
            content = self._format_table_info(table_name, table_info)

            doc = Document(
                content=content,
                metadata={
                    "source": "schema",
                    "table_name": table_name,
                    "data_source_id": self.data_source_id,
                    "relevance_score": score,
                    "stage": self.current_stage.value,
                    "retrieval_method": "keyword",
                },
                score=score
            )
            documents.append(doc)

        logger.info(f"✅ 使用关键词检索，返回 {len(documents)} 个表")
        return documents

    def _apply_stage_aware_scoring(
        self, 
        scored_tables: List[tuple], 
        query: str
    ) -> List[tuple]:
        """应用阶段感知评分"""
        # 根据当前阶段调整评分
        stage_multipliers = {
            ExecutionStage.SCHEMA_DISCOVERY: 1.2,  # 表发现阶段，提高所有表的相关性
            ExecutionStage.SQL_GENERATION: 1.0,    # SQL生成阶段，保持原始评分
            ExecutionStage.SQL_VALIDATION: 0.8,     # SQL验证阶段，降低评分
            ExecutionStage.DATA_EXTRACTION: 1.1,   # 数据提取阶段，略微提高评分
        }
        
        multiplier = stage_multipliers.get(self.current_stage, 1.0)
        
        # 应用乘数
        enhanced_tables = []
        for table_name, table_info, score in scored_tables:
            enhanced_score = score * multiplier
            enhanced_tables.append((table_name, table_info, enhanced_score))
        
        return enhanced_tables

    def _format_table_info(self, table_name: str, table_info: Dict[str, Any]) -> str:
        """
        格式化表结构信息为易读的文本
        
        返回格式：
        ```
        ### 表: orders
        **说明**: 订单表
        **列信息**:
        - **order_id** (BIGINT) [NOT NULL]: 订单ID
        - **customer_id** (BIGINT): 客户ID
        - **order_date** (DATE): 订单日期
        - **total_amount** (DECIMAL(10,2)): 订单总金额
        ```
        """
        lines = [
            f"### 表: {table_name}",
        ]

        # 添加表注释
        if table_info.get('table_comment'):
            lines.append(f"**说明**: {table_info['table_comment']}")

        # 添加列信息
        columns = table_info.get('columns', [])
        if columns:
            lines.append("\n**列信息**:")
            for col in columns:
                col_name = col.get('name') or ''
                col_type = col.get('type') or ''
                col_comment = col.get('comment') or ''
                is_nullable = col.get('nullable', True)

                # 构建列描述
                col_desc = f"- **{col_name}** ({col_type})"

                if not is_nullable:
                    col_desc += " [NOT NULL]"

                if col_comment:
                    col_desc += f": {col_comment}"

                lines.append(col_desc)

        return "\n".join(lines)

    async def add_documents(self, documents: List[Document]) -> None:
        """添加文档（本实现不需要，因为我们直接从数据源获取 schema）"""
        logger.warning("SchemaContextRetriever 不支持添加文档，schema 信息来自数据源")
        pass

    def format_documents(
        self,
        documents: List[Document],
        max_length: int = 2000
    ) -> str:
        """
        格式化文档为字符串（用于上下文注入）

        这是 Loom ContextRetriever 的标准方法，用于将检索到的文档格式化为字符串注入到 LLM 上下文中

        Args:
            documents: 文档列表
            max_length: 单个文档最大长度

        Returns:
            格式化的文档字符串
        """
        if not documents:
            return ""

        lines = ["## Retrieved Schema Context\n"]
        lines.append(f"Found {len(documents)} relevant table(s):\n")

        for i, doc in enumerate(documents, 1):
            lines.append(f"### Document {i}")

            # 元数据
            if doc.metadata:
                table_name = doc.metadata.get("table_name", "Unknown")
                lines.append(f"**Table**: {table_name}")

                source = doc.metadata.get("source", "schema")
                if source:
                    lines.append(f"**Source**: {source}")

            # 相关性分数
            if doc.score is not None:
                lines.append(f"**Relevance**: {doc.score:.2%}")

            # 内容（截断）
            content = doc.content
            if len(content) > max_length:
                content = content[:max_length] + "...\n[truncated]"

            lines.append(f"\n{content}\n")

        lines.append("---\n")
        lines.append("Please use the above schema information to answer the question.\n")

        return "\n".join(lines)

    def set_stage(self, stage: ExecutionStage):
        """设置当前执行阶段"""
        self.current_stage = stage
        logger.info(f"🔄 [SchemaContextRetriever] 切换到阶段: {stage.value}")

    def clear_stage_cache(self):
        """清除阶段感知缓存"""
        self.stage_context_cache.clear()
        logger.info("🧹 [SchemaContextRetriever] 清除阶段感知缓存")
    
    def _sanitize_query(self, query: str) -> str:
        """
        净化查询文本，只保留业务需求
        
        问题：Loom框架在递归调用时会将整个prompt（包括系统指令）传递给context_retriever
        解决：提取业务需求部分，去除系统指令和递归标记
        
        Args:
            query: 原始查询文本（可能包含系统指令）
            
        Returns:
            净化后的业务需求文本
        """
        # 安全的占位符文本（如果无法提取业务需求时使用）
        DEFAULT_PLACEHOLDER_TEXT = "请基于最近的业务需求检索基础表结构"
        
        # 如果查询文本较短（<200字符），可能是纯业务需求，直接返回
        if len(query) < 200:
            logger.debug(f"✅ [Query Sanitization] 查询较短，直接使用: {query[:50]}...")
            return query
        
        # 标记需要过滤的系统关键词
        system_keywords = [
            "# 系统指令",
            "# SYSTEM INSTRUCTIONS", 
            "TT递归",
            "继续处理任务：",
            "你是一个",
            "## 关键要求",
            "## 质量标准",
            "## Doris SQL示例",
            "## 重要原则"
        ]
        
        # 检查是否包含系统指令标记
        contains_system_instructions = any(keyword in query for keyword in system_keywords)
        
        if not contains_system_instructions:
            # 不包含系统指令，返回前512字符（限制长度）
            logger.debug(f"✅ [Query Sanitization] 不包含系统指令，截取前512字符")
            return query[:512]
        
        # 包含系统指令，尝试提取业务需求
        # 策略1：提取"# 任务描述"或"## 任务描述"之后的内容
        task_markers = ["# 任务描述", "## 任务描述", "# USER", "用户查询", "业务需求", "占位符"]
        for marker in task_markers:
            if marker in query:
                parts = query.split(marker, 1)
                if len(parts) > 1:
                    extracted = parts[1].strip()
                    # 只保留前512字符的业务需求
                    if len(extracted) > 512:
                        extracted = extracted[:512]
                    logger.info(f"✅ [Query Sanitization] 提取任务描述: {extracted[:100]}...")
                    return extracted
        
        # 策略2：如果查询中有多个"继续处理任务："，提取最后一个
        if "继续处理任务：" in query:
            parts = query.split("继续处理任务：")
            if len(parts) > 1:
                # 获取最后一个部分（最可能是业务需求）
                last_part = parts[-1].strip()
                # 清理系统指令关键词
                for keyword in system_keywords:
                    if keyword in last_part:
                        last_part = last_part.split(keyword)[0].strip()
                # 限制长度
                if len(last_part) > 512:
                    last_part = last_part[:512]
                logger.info(f"✅ [Query Sanitization] 提取最后一个任务: {last_part[:100]}...")
                return last_part
        
        # 策略3：如果都无法提取，记录警告并使用默认占位符
        logger.warning(f"⚠️ [Query Sanitization] 无法提取业务需求，使用默认占位符")
        logger.debug(f"⚠️ [Query Sanitization] 原始查询前500字符: {query[:500]}")
        return DEFAULT_PLACEHOLDER_TEXT

    async def _filter_tables_by_name(self, query: str, table_names: List[str]) -> List[str]:
        """
        基于大模型的智能表名匹配

        将占位符和表名列表交给大模型，让它智能选择最相关的表
        如果大模型失败，直接抛出异常
        """
        if not table_names:
            logger.warning("⚠️ 表名列表为空，无法进行匹配")
            return []
        
        logger.info(f"🔍 [智能表名匹配] 查询: {query[:50]}...")
        logger.info(f"🔍 [智能表名匹配] 可用表名: {table_names}")
        
        # 使用大模型进行表名匹配
        matched_tables = await self._llm_table_matching(query, table_names)
        
        if not matched_tables:
            raise Exception(f"大模型表名匹配失败：无法为查询 '{query}' 找到相关表")
        
        logger.info(f"✅ [智能表名匹配] 匹配结果: {matched_tables}")
        return matched_tables

    async def _llm_table_matching(self, query: str, table_names: List[str]) -> List[str]:
        """
        使用大模型进行表名匹配
        
        Args:
            query: 占位符查询
            table_names: 可用表名列表
            
        Returns:
            匹配的表名列表
        """
        # 构建提示词
        prompt = self._build_table_matching_prompt(query, table_names)
        
        # 获取LLM适配器
        from .llm_adapter import create_llm_adapter
        llm_adapter = create_llm_adapter(self.container)
        
        # 调用大模型
        response = await llm_adapter.generate_response(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1  # 低温度确保一致性
        )
        
        # 解析响应
        matched_tables = self._parse_table_matching_response(response, table_names)
        
        return matched_tables

    def _build_table_matching_prompt(self, query: str, table_names: List[str]) -> str:
        """构建表名匹配的提示词"""
        table_list = "\n".join([f"- {name}" for name in table_names])
        
        prompt = f"""你是一个数据库专家，需要根据用户的查询需求，从给定的表名列表中选择最相关的表。

用户查询：{query}

可用表名列表：
{table_list}

请分析用户查询的业务需求，选择最相关的表名。考虑以下因素：
1. 查询的业务领域（用户、订单、产品、销售等）
2. 表名的语义含义
3. 查询可能涉及的数据类型

请以JSON格式返回结果：
{{
    "matched_tables": ["table1", "table2", "table3"],
    "reasoning": "选择这些表的原因说明"
}}

注意：
- 最多选择5个表
- 表名必须完全匹配列表中的名称
- 如果查询不明确，选择最可能相关的表
- 优先选择核心业务表"""
        
        return prompt

    def _parse_table_matching_response(self, response: str, available_tables: List[str]) -> List[str]:
        """解析大模型的表名匹配响应"""
        import json
        import re
        
        # 尝试提取JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            result = json.loads(json_str)
            
            matched_tables = result.get("matched_tables", [])
            reasoning = result.get("reasoning", "")
            
            logger.info(f"🧠 [LLM推理] {reasoning}")
            
            # 验证表名是否在可用列表中
            valid_tables = []
            for table in matched_tables:
                if table in available_tables:
                    valid_tables.append(table)
                else:
                    logger.warning(f"⚠️ 大模型返回了无效表名: {table}")
            
            return valid_tables
        else:
            # 如果没有JSON格式，尝试直接提取表名
            matched_tables = []
            for table in available_tables:
                if table.lower() in response.lower():
                    matched_tables.append(table)
            
            return matched_tables

    async def _validate_and_refine_tables(self, query: str, matched_tables: List[str], table_columns: Dict[str, List[Dict]]) -> List[str]:
        """
        验证表名匹配结果，基于列信息进行迭代优化
        
        Args:
            query: 原始查询
            matched_tables: 初步匹配的表名
            table_columns: 表的列信息
            
        Returns:
            优化后的表名列表
        """
        if not matched_tables or not table_columns:
            return matched_tables
        
        logger.info(f"🔍 [表名验证] 验证表: {matched_tables}")
        
        # 构建列信息验证提示词
        prompt = self._build_column_validation_prompt(query, matched_tables, table_columns)
        
        # 获取LLM适配器
        from .llm_adapter import create_llm_adapter
        llm_adapter = create_llm_adapter(self.container)
        
        # 调用大模型进行验证
        response = await llm_adapter.generate_response(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1
        )
        
        # 解析验证结果
        refined_tables = self._parse_column_validation_response(response, matched_tables)
        
        if refined_tables != matched_tables:
            logger.info(f"🔄 [表名优化] 原始: {matched_tables} -> 优化后: {refined_tables}")
        
        return refined_tables

    def _build_column_validation_prompt(self, query: str, matched_tables: List[str], table_columns: Dict[str, List[Dict]]) -> str:
        """构建列信息验证的提示词"""
        table_info = ""
        for table_name in matched_tables:
            if table_name in table_columns:
                columns = table_columns[table_name]
                column_list = "\n".join([f"  - {col.get('name', '')} ({col.get('data_type', '')})" for col in columns[:10]])  # 限制显示前10列
                table_info += f"\n表 {table_name}:\n{column_list}\n"
        
        prompt = f"""你是一个数据库专家，需要验证表名匹配的准确性。

用户查询：{query}

初步匹配的表名：{matched_tables}

这些表的列信息：
{table_info}

请分析：
1. 这些表是否真的与用户查询相关？
2. 列信息是否支持用户查询的需求？
3. 是否需要调整表的选择？

请以JSON格式返回结果：
{{
    "is_accurate": true/false,
    "refined_tables": ["table1", "table2"],
    "reasoning": "验证和调整的原因说明",
    "confidence": 0.8
}}

注意：
- 如果表选择准确，is_accurate设为true
- 如果需要调整，refined_tables包含优化后的表名
- confidence表示匹配的置信度（0-1）"""
        
        return prompt

    def _parse_column_validation_response(self, response: str, original_tables: List[str]) -> List[str]:
        """解析列信息验证的响应"""
        import json
        import re
        
        # 尝试提取JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            result = json.loads(json_str)
            
            is_accurate = result.get("is_accurate", True)
            refined_tables = result.get("refined_tables", original_tables)
            reasoning = result.get("reasoning", "")
            confidence = result.get("confidence", 0.5)
            
            logger.info(f"🧠 [列信息验证] 准确性: {is_accurate}, 置信度: {confidence}")
            logger.info(f"🧠 [列信息验证] 推理: {reasoning}")
            
            return refined_tables if refined_tables else original_tables
        else:
            # 如果没有JSON格式，返回原始表名
            logger.warning("⚠️ 无法解析验证响应，保持原始表名")
            return original_tables

    async def _basic_retrieve(
        self,
        query: str,
        top_k: int,
        candidate_tables: List[str]
    ) -> List[Document]:
        """
        基础检索策略

        当智能检索不可用时，使用简单的关键词匹配
        """
        documents = []
        query_lower = query.lower()

        for table_name in candidate_tables[:top_k]:
            if table_name not in self.schema_cache:
                # 如果表结构未加载，创建一个基础文档
                content = f"表名: {table_name}\n说明: 表结构信息将在需要时动态加载"
                doc = Document(
                    content=content,
                    metadata={
                        "source": "schema",
                        "table_name": table_name,
                        "data_source_id": self.data_source_id,
                        "relevance_score": 0.5,
                        "stage": self.current_stage.value,
                        "retrieval_method": "basic",
                        "lazy_loaded": True
                    },
                    score=0.5
                )
            else:
                # 使用已加载的表结构
                table_info = self.schema_cache[table_name]
                content = self._format_table_info(table_name, table_info)
                doc = Document(
                    content=content,
                    metadata={
                        "source": "schema",
                        "table_name": table_name,
                        "data_source_id": self.data_source_id,
                        "relevance_score": 0.7,
                        "stage": self.current_stage.value,
                        "retrieval_method": "basic",
                        "lazy_loaded": False
                    },
                    score=0.7
                )

            documents.append(doc)

        return documents

    def _format_table_info(self, table_name: str, table_info: Dict[str, Any]) -> str:
        """格式化表信息为文本"""
        columns = table_info.get('columns', [])

        # 构建列信息
        column_lines = []
        for col in columns:
            col_name = col.get('name', '')
            col_type = col.get('type', '')
            col_comment = col.get('comment', '')

            if col_comment:
                column_lines.append(f"  - {col_name} ({col_type}): {col_comment}")
            else:
                column_lines.append(f"  - {col_name} ({col_type})")

        # 构建完整表信息
        content = f"表名: {table_name}\n"
        content += f"类型: {table_info.get('table_type', 'TABLE')}\n"
        content += f"列数: {len(columns)}\n"

        if column_lines:
            content += "列信息:\n" + "\n".join(column_lines)

        return content

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "lazy_loading_enabled": self.enable_lazy_loading,
            "total_tables": len(self.table_names),
            "loaded_tables": len(self.loaded_tables),
            "cache_size": len(self.schema_cache),
            "stage_cache_size": len(self.stage_context_cache),
            "intelligent_retrieval_enabled": self._intelligent_retriever is not None
        }


class IntelligentContextRetriever(BaseContextRetriever):
    """
    智能上下文检索器
    
    基于 SchemaContextRetriever 的高级封装，提供更智能的上下文管理
    """

    def __init__(
        self,
        schema_retriever: SchemaContextRetriever,
        enable_context_caching: bool = True,
        max_cache_size: int = 100
    ):
        """
        Args:
            schema_retriever: Schema 检索器实例
            enable_context_caching: 是否启用上下文缓存
            max_cache_size: 最大缓存大小
        """
        self.schema_retriever = schema_retriever
        self.enable_context_caching = enable_context_caching
        self.max_cache_size = max_cache_size
        
        # 上下文缓存
        self.context_cache: Dict[str, ContextInfo] = {}
        self.query_cache: Dict[str, List[str]] = {}

    async def retrieve(
        self, 
        query: str, 
        context_type: str = "schema",
        top_k: Optional[int] = None
    ) -> List[str]:
        """
        检索上下文信息
        
        Args:
            query: 查询文本
            context_type: 上下文类型（schema, data, business等）
            top_k: 返回数量
            
        Returns:
            上下文信息字符串列表
        """
        logger.info(f"🔍 [IntelligentContextRetriever] 检索上下文: {context_type}")
        
        # 检查缓存
        cache_key = f"{query}_{context_type}_{top_k}"
        if self.enable_context_caching and cache_key in self.query_cache:
            logger.info("✅ 使用查询缓存")
            return self.query_cache[cache_key]

        # 根据上下文类型选择检索策略
        if context_type == "schema":
            documents = await self.schema_retriever.retrieve(query, top_k)
            context_strings = [doc.content for doc in documents]
        else:
            # 其他类型的上下文检索（可扩展）
            context_strings = []

        # 更新缓存
        if self.enable_context_caching:
            self.query_cache[cache_key] = context_strings
            # 限制缓存大小
            if len(self.query_cache) > self.max_cache_size:
                oldest_key = next(iter(self.query_cache))
                del self.query_cache[oldest_key]

        return context_strings

    async def update_context(self, context: ContextInfo) -> None:
        """
        更新上下文缓存
        
        Args:
            context: 上下文信息
        """
        logger.info("🔄 [IntelligentContextRetriever] 更新上下文缓存")

        # 更新 Schema 信息
        if context.tables:
            for table in context.tables:
                table_name = table.get('table_name', '')
                if table_name:
                    self.schema_retriever.schema_cache[table_name] = table

        # 更新其他上下文信息
        # TODO: 实现其他类型的上下文更新


def create_schema_context_retriever(
    data_source_id: str,
    connection_config: Dict[str, Any],
    container: Any,
    top_k: int = 5,
    # 兼容调用方传入，但本实现不直接使用
    inject_as: Optional[str] = None,
    enable_stage_aware: bool = True,
    enable_lazy_loading: bool = True
) -> SchemaContextRetriever:
    """
    创建 Schema 上下文检索器
    
    Args:
        data_source_id: 数据源ID
        connection_config: 连接配置
        container: 服务容器
        top_k: 默认返回表数量
        enable_stage_aware: 是否启用阶段感知
        enable_lazy_loading: 是否启用懒加载优化
        
    Returns:
        SchemaContextRetriever 实例
    """
    return SchemaContextRetriever(
        data_source_id=data_source_id,
        connection_config=connection_config,
        container=container,
        top_k=top_k,
        enable_stage_aware=enable_stage_aware,
        enable_lazy_loading=enable_lazy_loading
    )


def create_intelligent_context_retriever(
    schema_retriever: SchemaContextRetriever,
    enable_context_caching: bool = True
) -> IntelligentContextRetriever:
    """
    创建智能上下文检索器
    
    Args:
        schema_retriever: Schema 检索器
        enable_context_caching: 是否启用缓存
        
    Returns:
        IntelligentContextRetriever 实例
    """
    return IntelligentContextRetriever(
        schema_retriever=schema_retriever,
        enable_context_caching=enable_context_caching
    )


# 导出
__all__ = [
    "SchemaContextRetriever",
    "IntelligentContextRetriever", 
    "create_schema_context_retriever",
    "create_intelligent_context_retriever",
]