"""
增强版数据查询Agent

在原有DataQueryAgent基础上增加以下功能：
- 语义理解和意图识别
- 智能查询优化
- 元数据缓存和管理
- 复杂查询构建
- 多数据源融合

Features:
- 自然语言查询理解
- 智能SQL生成和优化
- 查询结果解释
- 增量数据处理
- 跨数据源联合查询
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta

from ..core_types import BaseAgent, AgentConfig, AgentResult, AgentType, AgentError
from ..specialized.data_query_agent import DataQueryAgent, QueryRequest, QueryResult
from ..security import sandbox_manager, SandboxLevel
from ..tools import tool_registry, ToolCategory


@dataclass
class SemanticQueryRequest:
    """语义查询请求"""
    natural_language: str              # 自然语言查询
    data_source_ids: List[int] = None # 数据源ID列表
    context: Dict[str, Any] = None    # 上下文信息
    user_preferences: Dict[str, Any] = None  # 用户偏好设置
    query_hints: List[str] = None     # 查询提示
    expected_format: str = "table"    # 期望结果格式


@dataclass
class QueryIntent:
    """查询意图"""
    intent_type: str                  # 意图类型：count, sum, avg, trend, compare等
    entities: List[str]               # 实体列表（表名、字段名等）
    time_range: Optional[Dict] = None # 时间范围
    filters: Dict[str, Any] = None    # 过滤条件
    aggregations: List[str] = None    # 聚合操作
    grouping: List[str] = None        # 分组字段
    sorting: Dict[str, str] = None    # 排序规则
    confidence: float = 0.0           # 置信度


@dataclass
class MetadataInfo:
    """元数据信息"""
    table_name: str
    columns: List[Dict[str, Any]]
    indexes: List[str]
    relationships: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    last_updated: datetime


class SemanticParser:
    """语义解析器"""
    
    def __init__(self):
        # 意图识别模式
        self.intent_patterns = {
            'count': [
                r'(多少|几个|数量|总数|计数)', r'(count|total|number of)',
                r'(统计.*数量|有几)', r'(总共.*个)'
            ],
            'sum': [
                r'(总和|求和|合计|总计)', r'(sum|total)', 
                r'(加起来|总额)', r'(累计.*金额|总.*费用)'
            ],
            'avg': [
                r'(平均|均值|平均数)', r'(average|avg|mean)',
                r'(平均.*金额|平均.*数量)'
            ],
            'max': [
                r'(最大|最高|最多)', r'(max|maximum|highest)',
                r'(最大.*值|峰值)'
            ],
            'min': [
                r'(最小|最低|最少)', r'(min|minimum|lowest)',
                r'(最小.*值|最低.*价格)'
            ],
            'trend': [
                r'(趋势|变化|走势)', r'(trend|change over time)',
                r'(增长|下降|波动)', r'(按.*时间)'
            ],
            'compare': [
                r'(比较|对比|差异)', r'(compare|versus|vs)',
                r'(哪个.*更)', r'(相比之下)'
            ],
            'filter': [
                r'(筛选|过滤|条件)', r'(where|filter)',
                r'(满足.*条件|符合.*要求)'
            ]
        }
        
        # 实体识别模式
        self.entity_patterns = {
            'table': r'(用户|订单|产品|销售|客户|投诉|评价|商品)',
            'time': r'(\d{4}年|\d+月|\d+日|今天|昨天|本周|上周|本月|上月|今年|去年)',
            'number': r'(\d+\.?\d*)',
            'comparison': r'(大于|小于|等于|超过|低于|高于)'
        }
        
        # 字段映射词典
        self.field_mappings = {
            '金额': ['amount', 'price', 'cost', 'fee', 'money'],
            '数量': ['quantity', 'count', 'num', 'amount'],
            '时间': ['time', 'date', 'created_at', 'updated_at'],
            '用户': ['user_id', 'user_name', 'customer_id'],
            '类型': ['type', 'category', 'class'],
            '状态': ['status', 'state', 'condition'],
            '地区': ['region', 'province', 'city', 'area'],
            '等级': ['level', 'grade', 'rank']
        }
    
    async def parse_natural_language(self, query: str, context: Dict[str, Any] = None) -> QueryIntent:
        """解析自然语言查询"""
        try:
            intent = QueryIntent(intent_type="unknown", entities=[], confidence=0.0)
            
            # 预处理查询文本
            normalized_query = self._normalize_query(query)
            
            # 识别查询意图
            intent.intent_type, intent_confidence = self._identify_intent(normalized_query)
            
            # 提取实体
            intent.entities = self._extract_entities(normalized_query)
            
            # 提取时间范围
            intent.time_range = self._extract_time_range(normalized_query)
            
            # 提取过滤条件
            intent.filters = self._extract_filters(normalized_query)
            
            # 提取聚合操作
            intent.aggregations = self._extract_aggregations(normalized_query, intent.intent_type)
            
            # 提取分组信息
            intent.grouping = self._extract_grouping(normalized_query)
            
            # 设置置信度
            intent.confidence = self._calculate_confidence(intent, normalized_query)
            
            return intent
            
        except Exception as e:
            return QueryIntent(
                intent_type="error",
                entities=[],
                confidence=0.0
            )
    
    def _normalize_query(self, query: str) -> str:
        """规范化查询文本"""
        # 转换为小写
        query = query.lower()
        
        # 移除标点符号
        query = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', query)
        
        # 标准化空白字符
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query
    
    def _identify_intent(self, query: str) -> Tuple[str, float]:
        """识别查询意图"""
        best_intent = "unknown"
        best_score = 0.0
        
        for intent_type, patterns in self.intent_patterns.items():
            score = 0.0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, query):
                    matches += 1
                    score += 1.0
            
            # 计算匹配度
            if matches > 0:
                match_score = matches / len(patterns)
                if match_score > best_score:
                    best_score = match_score
                    best_intent = intent_type
        
        return best_intent, best_score
    
    def _extract_entities(self, query: str) -> List[str]:
        """提取实体"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, query)
            for match in matches:
                entities.append({
                    "type": entity_type,
                    "value": match
                })
        
        return entities
    
    def _extract_time_range(self, query: str) -> Optional[Dict]:
        """提取时间范围"""
        time_patterns = {
            '今天': {'days': 0},
            '昨天': {'days': -1},
            '本周': {'weeks': 0},
            '上周': {'weeks': -1},
            '本月': {'months': 0},
            '上月': {'months': -1},
            '今年': {'years': 0},
            '去年': {'years': -1}
        }
        
        for keyword, offset in time_patterns.items():
            if keyword in query:
                return {
                    "type": "relative",
                    "offset": offset
                }
        
        # 提取具体日期
        date_matches = re.findall(r'(\d{4})年?(\d{1,2})月?(\d{1,2})日?', query)
        if date_matches:
            year, month, day = date_matches[0]
            return {
                "type": "absolute",
                "date": f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            }
        
        return None
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """提取过滤条件"""
        filters = {}
        
        # 提取数值比较条件
        comparison_patterns = [
            (r'大于(\d+\.?\d*)', 'gt'),
            (r'小于(\d+\.?\d*)', 'lt'),
            (r'等于(\d+\.?\d*)', 'eq'),
            (r'超过(\d+\.?\d*)', 'gt'),
            (r'低于(\d+\.?\d*)', 'lt'),
            (r'高于(\d+\.?\d*)', 'gt')
        ]
        
        for pattern, operator in comparison_patterns:
            matches = re.findall(pattern, query)
            if matches:
                filters[operator] = float(matches[0])
        
        return filters
    
    def _extract_aggregations(self, query: str, intent_type: str) -> List[str]:
        """提取聚合操作"""
        aggregations = []
        
        # 基于意图类型添加默认聚合
        if intent_type in ['count', 'sum', 'avg', 'max', 'min']:
            aggregations.append(intent_type)
        
        return aggregations
    
    def _extract_grouping(self, query: str) -> List[str]:
        """提取分组字段"""
        grouping = []
        
        # 查找"按...分组"的模式
        group_patterns = [
            r'按(.+?)(分组|统计)',
            r'(分.*别|各.*)',
            r'(每个.*|各种.*)'
        ]
        
        for pattern in group_patterns:
            matches = re.findall(pattern, query)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        group_field = match[0].strip()
                    else:
                        group_field = match.strip()
                    
                    if group_field:
                        grouping.append(group_field)
        
        return grouping
    
    def _calculate_confidence(self, intent: QueryIntent, query: str) -> float:
        """计算解析置信度"""
        confidence = 0.0
        
        # 基于意图识别的置信度
        if intent.intent_type != "unknown":
            confidence += 0.3
        
        # 基于实体数量的置信度
        if intent.entities:
            confidence += min(0.3, len(intent.entities) * 0.1)
        
        # 基于结构完整性的置信度
        if intent.time_range:
            confidence += 0.2
        if intent.filters:
            confidence += 0.2
        
        return min(1.0, confidence)


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        self.optimization_rules = []
        self.execution_stats = {}
    
    async def optimize_query(self, sql: str, metadata: MetadataInfo = None) -> str:
        """优化SQL查询"""
        try:
            optimized_sql = sql
            
            # 应用优化规则
            optimized_sql = await self._apply_index_hints(optimized_sql, metadata)
            optimized_sql = await self._optimize_joins(optimized_sql)
            optimized_sql = await self._optimize_where_clause(optimized_sql)
            optimized_sql = await self._add_limits(optimized_sql)
            
            return optimized_sql
            
        except Exception as e:
            # 优化失败时返回原查询
            return sql
    
    async def _apply_index_hints(self, sql: str, metadata: MetadataInfo = None) -> str:
        """应用索引提示"""
        if not metadata or not metadata.indexes:
            return sql
        
        # 简单的索引提示逻辑
        # 在实际应用中应该更加智能
        for index in metadata.indexes:
            if index.lower() in sql.lower():
                # 可以添加USE INDEX提示
                pass
        
        return sql
    
    async def _optimize_joins(self, sql: str) -> str:
        """优化连接查询"""
        # 重新排列JOIN顺序以提高效率
        return sql
    
    async def _optimize_where_clause(self, sql: str) -> str:
        """优化WHERE子句"""
        # 重新排列WHERE条件以利用索引
        return sql
    
    async def _add_limits(self, sql: str) -> str:
        """添加合理的LIMIT限制"""
        if 'LIMIT' not in sql.upper() and 'SELECT' in sql.upper():
            # 为防止意外的大结果集，添加默认限制
            sql += ' LIMIT 10000'
        
        return sql


class MetadataManager:
    """元数据管理器"""
    
    def __init__(self):
        self.metadata_cache = {}
        self.cache_ttl = 3600  # 1小时缓存时间
    
    async def get_metadata(self, data_source_id: int) -> Optional[MetadataInfo]:
        """获取数据源元数据"""
        cache_key = f"metadata_{data_source_id}"
        
        # 检查缓存
        if cache_key in self.metadata_cache:
            cached_data = self.metadata_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                return cached_data['metadata']
        
        # 获取新的元数据
        try:
            metadata = await self._fetch_metadata(data_source_id)
            
            # 缓存元数据
            self.metadata_cache[cache_key] = {
                'metadata': metadata,
                'timestamp': time.time()
            }
            
            return metadata
            
        except Exception as e:
            return None
    
    async def _fetch_metadata(self, data_source_id: int) -> MetadataInfo:
        """从数据源获取元数据"""
        # 这里应该实现实际的元数据获取逻辑
        # 连接到数据库并查询表结构、索引等信息
        
        # 返回模拟的元数据
        return MetadataInfo(
            table_name="default_table",
            columns=[
                {"name": "id", "type": "int", "nullable": False},
                {"name": "category", "type": "string", "nullable": True},
                {"name": "amount", "type": "float", "nullable": True},
                {"name": "date", "type": "datetime", "nullable": True}
            ],
            indexes=["id", "category", "date"],
            relationships=[],
            statistics={"row_count": 1000},
            last_updated=datetime.now()
        )
    
    def clear_cache(self):
        """清空元数据缓存"""
        self.metadata_cache.clear()


class EnhancedDataQueryAgent(DataQueryAgent):
    """增强版数据查询Agent"""
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="enhanced_data_query_agent",
                agent_type=AgentType.DATA_QUERY,
                name="Enhanced Data Query Agent",
                description="增强版数据查询Agent，支持自然语言查询和智能优化",
                timeout_seconds=120,  # 更长的超时时间
                enable_caching=True,
                cache_ttl_seconds=1800  # 30分钟缓存
            )
        
        super().__init__(config)
        
        # 初始化增强组件
        self.semantic_parser = SemanticParser()
        self.query_optimizer = QueryOptimizer()
        self.metadata_manager = MetadataManager()
        
        # 注册工具
        self.tools = {
            'data_validator': tool_registry.get_tool('data_validator'),
            'data_transformer': tool_registry.get_tool('data_transformer'),
            'schema_detector': tool_registry.get_tool('schema_detector')
        }
    
    async def execute_semantic_query(self, semantic_request: SemanticQueryRequest) -> AgentResult:
        """执行语义查询"""
        try:
            self.logger.info(
                "执行语义查询",
                agent_id=self.agent_id,
                natural_language=semantic_request.natural_language[:100]
            )
            
            # 1. 解析自然语言查询
            query_intent = await self.semantic_parser.parse_natural_language(
                semantic_request.natural_language,
                semantic_request.context
            )
            
            if query_intent.confidence < 0.3:
                return AgentResult(
                    success=False,
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    error_message="无法理解查询意图，请使用更清晰的表达"
                )
            
            # 2. 构建结构化查询请求
            structured_request = await self._build_structured_request(
                query_intent, 
                semantic_request
            )
            
            # 3. 获取元数据信息
            metadata = None
            if semantic_request.data_source_ids:
                metadata = await self.metadata_manager.get_metadata(
                    semantic_request.data_source_ids[0]
                )
            
            # 4. 执行查询
            query_result = await self.execute(structured_request)
            
            # 5. 增强查询结果
            if query_result.success:
                enhanced_result = await self._enhance_query_result(
                    query_result.data,
                    query_intent,
                    metadata
                )
                
                query_result.data = enhanced_result
                query_result.metadata.update({
                    "semantic_analysis": {
                        "intent": query_intent.intent_type,
                        "confidence": query_intent.confidence,
                        "entities": query_intent.entities
                    }
                })
            
            return query_result
            
        except Exception as e:
            error_msg = f"语义查询执行失败: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _build_structured_request(
        self, 
        intent: QueryIntent, 
        semantic_request: SemanticQueryRequest
    ) -> QueryRequest:
        """构建结构化查询请求"""
        # 确定数据源
        data_source_id = 1  # 默认数据源
        if semantic_request.data_source_ids:
            data_source_id = semantic_request.data_source_ids[0]
        
        # 构建查询参数
        structured_request = QueryRequest(
            data_source_id=data_source_id,
            query_type="auto",  # 使用自动查询类型
            description=semantic_request.natural_language,
            filters=intent.filters or {},
            aggregations=intent.aggregations or [],
            fields=intent.grouping or [],
            limit=1000
        )
        
        # 如果意图明确，设置更具体的查询类型
        if intent.intent_type in ['count', 'sum', 'avg', 'max', 'min']:
            structured_request.query_type = "aggregation"
        
        return structured_request
    
    async def _enhance_query_result(
        self,
        query_result: QueryResult,
        intent: QueryIntent,
        metadata: MetadataInfo = None
    ) -> QueryResult:
        """增强查询结果"""
        try:
            # 添加数据解释
            explanation = await self._generate_result_explanation(
                query_result, intent, metadata
            )
            
            # 添加建议
            suggestions = await self._generate_suggestions(
                query_result, intent, metadata
            )
            
            # 更新结果元数据
            if not query_result.metadata:
                query_result.metadata = {}
            
            query_result.metadata.update({
                "explanation": explanation,
                "suggestions": suggestions,
                "confidence": intent.confidence
            })
            
            return query_result
            
        except Exception as e:
            self.logger.warning(f"查询结果增强失败: {str(e)}")
            return query_result
    
    async def _generate_result_explanation(
        self,
        query_result: QueryResult,
        intent: QueryIntent,
        metadata: MetadataInfo = None
    ) -> str:
        """生成查询结果解释"""
        try:
            explanations = []
            
            # 基于意图生成解释
            if intent.intent_type == "count":
                explanations.append(f"共找到 {query_result.row_count} 条符合条件的记录")
            elif intent.intent_type in ["sum", "avg", "max", "min"]:
                if query_result.data:
                    first_row = query_result.data[0]
                    for key, value in first_row.items():
                        if isinstance(value, (int, float)):
                            explanations.append(f"{intent.intent_type.upper()}结果: {value}")
                            break
            
            # 添加数据质量信息
            if metadata:
                explanations.append(f"数据源包含约 {metadata.statistics.get('row_count', 'unknown')} 条记录")
            
            # 添加执行信息
            explanations.append(f"查询执行时间: {query_result.execution_time:.2f}秒")
            
            return "; ".join(explanations)
            
        except Exception as e:
            return f"查询执行完成，返回 {query_result.row_count} 条结果"
    
    async def _generate_suggestions(
        self,
        query_result: QueryResult,
        intent: QueryIntent,
        metadata: MetadataInfo = None
    ) -> List[str]:
        """生成查询建议"""
        suggestions = []
        
        try:
            # 基于结果数量的建议
            if query_result.row_count == 0:
                suggestions.append("没有找到匹配的数据，建议检查查询条件或扩大搜索范围")
            elif query_result.row_count > 10000:
                suggestions.append("结果数量较大，建议添加更多过滤条件以缩小范围")
            
            # 基于查询性能的建议
            if query_result.execution_time > 5.0:
                suggestions.append("查询执行时间较长，建议优化查询条件或考虑添加索引")
            
            # 基于意图的建议
            if intent.intent_type == "trend" and not intent.time_range:
                suggestions.append("趋势分析建议指定明确的时间范围")
            
            # 基于置信度的建议
            if intent.confidence < 0.6:
                suggestions.append("查询意图识别置信度较低，建议使用更明确的表达")
            
        except Exception as e:
            self.logger.warning(f"生成建议失败: {str(e)}")
        
        return suggestions
    
    async def execute_multi_source_query(
        self,
        semantic_request: SemanticQueryRequest
    ) -> AgentResult:
        """执行多数据源联合查询"""
        try:
            if not semantic_request.data_source_ids or len(semantic_request.data_source_ids) < 2:
                return await self.execute_semantic_query(semantic_request)
            
            # 并行查询多个数据源
            query_tasks = []
            for data_source_id in semantic_request.data_source_ids:
                single_source_request = SemanticQueryRequest(
                    natural_language=semantic_request.natural_language,
                    data_source_ids=[data_source_id],
                    context=semantic_request.context
                )
                query_tasks.append(self.execute_semantic_query(single_source_request))
            
            # 等待所有查询完成
            results = await asyncio.gather(*query_tasks, return_exceptions=True)
            
            # 合并结果
            merged_result = await self._merge_multi_source_results(results)
            
            return merged_result
            
        except Exception as e:
            error_msg = f"多数据源查询失败: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _merge_multi_source_results(self, results: List) -> AgentResult:
        """合并多数据源查询结果"""
        merged_data = []
        total_row_count = 0
        execution_times = []
        errors = []
        
        for result in results:
            if isinstance(result, AgentResult):
                if result.success and result.data:
                    merged_data.extend(result.data.data)
                    total_row_count += result.data.row_count
                    execution_times.append(result.data.execution_time)
                else:
                    errors.append(result.error_message)
            else:
                errors.append(str(result))
        
        # 创建合并后的查询结果
        merged_query_result = QueryResult(
            data=merged_data,
            columns=merged_data[0].keys() if merged_data else [],
            row_count=total_row_count,
            query_executed="MULTI_SOURCE_QUERY",
            execution_time=max(execution_times) if execution_times else 0.0,
            metadata={
                "source_count": len(results),
                "successful_sources": len([r for r in results if isinstance(r, AgentResult) and r.success]),
                "errors": errors
            }
        )
        
        return AgentResult(
            success=len(merged_data) > 0,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            data=merged_query_result,
            metadata={
                "multi_source": True,
                "source_count": len(results),
                "error_count": len(errors)
            }
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        health = await super().health_check()
        
        # 增加增强功能的健康检查
        health.update({
            "semantic_parser": "healthy",
            "query_optimizer": "healthy", 
            "metadata_manager": {
                "healthy": True,
                "cache_size": len(self.metadata_manager.metadata_cache)
            },
            "tools": {
                tool_name: tool is not None 
                for tool_name, tool in self.tools.items()
            }
        })
        
        return health