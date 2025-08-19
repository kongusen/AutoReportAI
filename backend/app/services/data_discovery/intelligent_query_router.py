"""
智能查询路由器 - Agent多库多表智能访问核心
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from app.db.session import get_db_session
from app.models.data_source import DataSource
from app.models.table_schema import Database, Table, TableColumn, TableRelation


class QueryIntent(str, Enum):
    """查询意图类型"""
    STATISTICAL = "statistical"  # 统计分析
    DETAIL = "detail"  # 明细查询
    TREND = "trend"  # 趋势分析
    COMPARISON = "comparison"  # 对比分析
    AGGREGATION = "aggregation"  # 聚合查询
    JOIN = "join"  # 关联查询


class ConfidenceLevel(str, Enum):
    """置信度级别"""
    HIGH = "high"  # 0.8+
    MEDIUM = "medium"  # 0.5-0.8
    LOW = "low"  # <0.5


@dataclass
class QueryContext:
    """查询上下文"""
    original_query: str
    parsed_entities: List[str]
    intent: QueryIntent
    confidence: float
    time_range: Optional[Tuple[str, str]] = None
    filters: Dict[str, Any] = None
    aggregation_type: Optional[str] = None
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = {}


@dataclass
class TableCandidate:
    """候选表"""
    table: Table
    relevance_score: float
    matching_columns: List[str]
    business_context: str
    required_joins: List[str] = None
    
    def __post_init__(self):
        if self.required_joins is None:
            self.required_joins = []


@dataclass
class QueryPlan:
    """查询执行计划"""
    primary_tables: List[TableCandidate]
    join_tables: List[TableCandidate]
    join_conditions: List[str]
    where_conditions: List[str]
    select_columns: List[str]
    group_by_columns: List[str]
    order_by_columns: List[str]
    estimated_complexity: str  # low, medium, high
    cross_database: bool = False
    execution_order: List[str] = None
    
    def __post_init__(self):
        if self.execution_order is None:
            self.execution_order = []


class SemanticAnalyzer:
    """语义分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 业务实体词典
        self.business_entities = {
            '用户': ['user', 'customer', 'member', '用户', '客户', '会员'],
            '订单': ['order', 'transaction', 'purchase', '订单', '交易', '购买'],
            '产品': ['product', 'item', 'goods', '产品', '商品', '物品'],
            '销售': ['sale', 'revenue', 'income', '销售', '营收', '收入'],
            '员工': ['employee', 'staff', 'worker', '员工', '职员', '工作人员'],
            '部门': ['department', 'division', 'team', '部门', '科室', '团队'],
            '财务': ['finance', 'accounting', 'budget', '财务', '会计', '预算'],
            '库存': ['inventory', 'stock', 'warehouse', '库存', '仓库', '存货']
        }
        
        # 时间表达式
        self.time_patterns = {
            r'最近(\d+)天': r'DATE_SUB(NOW(), INTERVAL \1 DAY)',
            r'最近(\d+)个月': r'DATE_SUB(NOW(), INTERVAL \1 MONTH)', 
            r'最近(\d+)年': r'DATE_SUB(NOW(), INTERVAL \1 YEAR)',
            r'今天': 'CURDATE()',
            r'昨天': 'DATE_SUB(CURDATE(), INTERVAL 1 DAY)',
            r'本月': 'MONTH(NOW())',
            r'上月': 'MONTH(DATE_SUB(NOW(), INTERVAL 1 MONTH))'
        }
        
        # 聚合函数映射
        self.aggregation_patterns = {
            r'总计|总数|总和': 'SUM',
            r'平均|均值': 'AVG',
            r'最大|最高': 'MAX',
            r'最小|最低': 'MIN',
            r'数量|个数|计数': 'COUNT',
            r'统计|汇总': 'COUNT'
        }
    
    async def analyze_query(self, query: str) -> QueryContext:
        """分析查询语句"""
        try:
            # 1. 实体识别
            entities = self._extract_entities(query)
            
            # 2. 意图分类
            intent, confidence = self._classify_intent(query)
            
            # 3. 时间范围提取
            time_range = self._extract_time_range(query)
            
            # 4. 过滤条件提取
            filters = self._extract_filters(query)
            
            # 5. 聚合类型识别
            aggregation_type = self._identify_aggregation(query)
            
            return QueryContext(
                original_query=query,
                parsed_entities=entities,
                intent=intent,
                confidence=confidence,
                time_range=time_range,
                filters=filters,
                aggregation_type=aggregation_type
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing query: {e}")
            raise
    
    def _extract_entities(self, query: str) -> List[str]:
        """提取业务实体"""
        entities = []
        query_lower = query.lower()
        
        for entity_type, keywords in self.business_entities.items():
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    entities.append(entity_type)
                    break
                    
        return list(set(entities))  # 去重
    
    def _classify_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """分类查询意图"""
        query_lower = query.lower()
        
        # 统计分析关键词
        if any(keyword in query_lower for keyword in ['统计', '汇总', '分析', '报表', '总计']):
            return QueryIntent.STATISTICAL, 0.9
            
        # 趋势分析关键词
        if any(keyword in query_lower for keyword in ['趋势', '变化', '增长', '下降', '对比']):
            return QueryIntent.TREND, 0.85
            
        # 明细查询关键词
        if any(keyword in query_lower for keyword in ['查询', '查看', '列表', '明细', '详情']):
            return QueryIntent.DETAIL, 0.8
            
        # 聚合查询关键词
        if any(keyword in query_lower for keyword in ['总数', '平均', '最大', '最小', '数量']):
            return QueryIntent.AGGREGATION, 0.85
            
        # 关联查询关键词
        if any(keyword in query_lower for keyword in ['关联', '连接', '连表', 'join']):
            return QueryIntent.JOIN, 0.9
            
        # 默认为明细查询
        return QueryIntent.DETAIL, 0.5
    
    def _extract_time_range(self, query: str) -> Optional[Tuple[str, str]]:
        """提取时间范围"""
        for pattern, replacement in self.time_patterns.items():
            if re.search(pattern, query):
                # 这里简化处理，实际应该根据具体模式生成准确的时间范围
                return (replacement, 'NOW()')
        return None
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """提取过滤条件"""
        filters = {}
        
        # VIP用户过滤
        if 'VIP' in query or 'vip' in query or '会员' in query:
            filters['user_level'] = 'VIP'
            
        # 状态过滤
        if '已完成' in query or '完成' in query:
            filters['status'] = 'completed'
        elif '进行中' in query:
            filters['status'] = 'processing'
            
        return filters
    
    def _identify_aggregation(self, query: str) -> Optional[str]:
        """识别聚合类型"""
        for pattern, agg_func in self.aggregation_patterns.items():
            if re.search(pattern, query):
                return agg_func
        return None


class TableMatcher:
    """表匹配器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def find_relevant_tables(
        self,
        context: QueryContext,
        data_source_id: str,
        max_tables: int = 5
    ) -> List[TableCandidate]:
        """查找相关表"""
        candidates = []
        
        try:
            with get_db_session() as db:
                # 获取数据源下的所有表
                tables = db.query(Table).join(Database).filter(
                    Database.data_source_id == data_source_id,
                    Table.is_active == True
                ).all()
                
                # 如果元数据中没有表，尝试直接查询数据源
                if not tables:
                    self.logger.warning(f"No tables found in metadata for data_source {data_source_id}, trying direct query")
                    candidates = await self._discover_tables_directly(context, data_source_id)
                else:
                    for table in tables:
                        score = await self._calculate_relevance_score(table, context, db)
                        if score > 0.3:  # 最低相关性阈值
                            matching_columns = await self._find_matching_columns(table, context, db)
                            business_context = self._generate_business_context(table, context)
                            
                            candidate = TableCandidate(
                                table=table,
                                relevance_score=score,
                                matching_columns=matching_columns,
                                business_context=business_context
                            )
                            candidates.append(candidate)
                    
                    # 按相关性排序
                    candidates.sort(key=lambda x: x.relevance_score, reverse=True)
                
                return candidates[:max_tables]
                
        except Exception as e:
            self.logger.error(f"Error finding relevant tables: {e}")
            raise
    
    async def _calculate_relevance_score(
        self,
        table: Table,
        context: QueryContext,
        db: Session
    ) -> float:
        """计算表的相关性得分"""
        score = 0.0
        
        try:
            # 1. 表名匹配
            table_name_lower = table.name.lower()
            display_name_lower = (table.display_name or '').lower()
            
            for entity in context.parsed_entities:
                entity_keywords = SemanticAnalyzer().business_entities.get(entity, [entity])
                for keyword in entity_keywords:
                    if keyword.lower() in table_name_lower or keyword.lower() in display_name_lower:
                        score += 0.4
                        break
            
            # 2. 业务标签匹配
            if table.business_tags:
                for entity in context.parsed_entities:
                    if entity in table.business_tags:
                        score += 0.3
            
            # 3. 字段名匹配
            columns = db.query(TableColumn).filter(TableColumn.table_id == table.id).all()
            column_names = [col.name.lower() for col in columns]
            
            for entity in context.parsed_entities:
                entity_keywords = SemanticAnalyzer().business_entities.get(entity, [entity])
                for keyword in entity_keywords:
                    if any(keyword.lower() in col_name for col_name in column_names):
                        score += 0.2
                        break
            
            # 4. 表大小和活跃度权重
            if table.row_count and table.row_count > 0:
                if table.row_count > 10000:
                    score += 0.1  # 大表通常更重要
                    
            # 5. 最近更新时间权重
            if table.last_analyzed:
                days_since_analysis = (datetime.utcnow() - table.last_analyzed).days
                if days_since_analysis < 30:
                    score += 0.1  # 最近分析过的表
                    
        except Exception as e:
            self.logger.error(f"Error calculating relevance score for table {table.name}: {e}")
            
        return min(score, 1.0)  # 确保得分不超过1.0
    
    async def _find_matching_columns(
        self,
        table: Table,
        context: QueryContext,
        db: Session
    ) -> List[str]:
        """查找匹配的字段"""
        matching_columns = []
        
        try:
            columns = db.query(TableColumn).filter(TableColumn.table_id == table.id).all()
            
            for column in columns:
                column_name_lower = column.name.lower()
                display_name_lower = (column.display_name or '').lower()
                
                # 检查是否匹配查询实体
                for entity in context.parsed_entities:
                    entity_keywords = SemanticAnalyzer().business_entities.get(entity, [entity])
                    for keyword in entity_keywords:
                        if (keyword.lower() in column_name_lower or 
                            keyword.lower() in display_name_lower):
                            matching_columns.append(column.name)
                            break
                
                # 检查时间字段
                if context.time_range and any(time_keyword in column_name_lower 
                                            for time_keyword in ['time', 'date', 'created', 'updated']):
                    matching_columns.append(column.name)
                    
                # 检查聚合字段
                if (context.aggregation_type and 
                    any(agg_keyword in column_name_lower 
                        for agg_keyword in ['amount', 'count', 'total', 'sum', 'price'])):
                    matching_columns.append(column.name)
                    
        except Exception as e:
            self.logger.error(f"Error finding matching columns for table {table.name}: {e}")
            
        return list(set(matching_columns))  # 去重
    
    async def _discover_tables_directly(
        self,
        context: QueryContext,
        data_source_id: str
    ) -> List[TableCandidate]:
        """直接从数据源发现表"""
        candidates = []
        
        try:
            from ...models.data_source import DataSource
            from ...services.connectors.connector_factory import create_connector
            
            with get_db_session() as db:
                data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
                if not data_source:
                    self.logger.error(f"Data source {data_source_id} not found")
                    return candidates
                
                # 创建连接器直接查询表列表
                connector = create_connector(data_source)
                await connector.connect()
                
                try:
                    tables = await connector.get_tables()
                    self.logger.info(f"Direct discovery found {len(tables)} tables: {tables}")
                    
                    # 为每个表创建简单的候选对象
                    for table_name in tables[:5]:  # 限制表数量
                        # 创建一个简单的Table对象用于兼容性
                        mock_table = type('Table', (), {
                            'id': f"direct_{table_name}",
                            'name': table_name,
                            'display_name': table_name,
                            'business_tags': [],
                            'row_count': 0,
                            'last_analyzed': None,
                            'data_sensitivity': 'public'
                        })()
                        
                        # 计算简单的相关性分数
                        score = self._calculate_simple_relevance_score(table_name, context)
                        
                        if score > 0.1:  # 更低的阈值，因为这是兜底方案
                            candidate = TableCandidate(
                                table=mock_table,
                                relevance_score=score,
                                matching_columns=[],
                                business_context="直接发现的表"
                            )
                            candidates.append(candidate)
                    
                finally:
                    await connector.disconnect()
                    
        except Exception as e:
            self.logger.error(f"Error in direct table discovery: {e}")
            
        return candidates
    
    def _calculate_simple_relevance_score(self, table_name: str, context: QueryContext) -> float:
        """计算简单的相关性得分（用于直接发现的表）"""
        score = 0.5  # 基础分数
        
        table_name_lower = table_name.lower()
        
        # 检查表名是否包含查询实体
        for entity in context.parsed_entities:
            entity_keywords = SemanticAnalyzer().business_entities.get(entity, [entity])
            for keyword in entity_keywords:
                if keyword.lower() in table_name_lower:
                    score += 0.3
                    break
        
        # 检查表名是否包含常见业务词汇
        business_keywords = ['user', 'order', 'product', 'customer', 'sale', 'transaction', 
                           'complaint', 'ticket', 'issue', '用户', '订单', '产品', '客户', 
                           '销售', '交易', '投诉', '工单', '问题']
        
        for keyword in business_keywords:
            if keyword in table_name_lower:
                score += 0.2
                break
                
        return min(score, 1.0)
    
    def _generate_business_context(self, table: Table, context: QueryContext) -> str:
        """生成业务上下文描述"""
        context_parts = []
        
        if table.business_tags:
            context_parts.append(f"业务标签: {', '.join(table.business_tags)}")
            
        if table.data_sensitivity:
            context_parts.append(f"敏感度: {table.data_sensitivity}")
            
        if table.row_count:
            if table.row_count > 1000000:
                context_parts.append("大表")
            elif table.row_count > 10000:
                context_parts.append("中等规模表")
            else:
                context_parts.append("小表")
                
        return "; ".join(context_parts) if context_parts else "普通业务表"


class QueryPlanner:
    """查询规划器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def create_execution_plan(
        self,
        context: QueryContext,
        candidates: List[TableCandidate],
        data_source_id: str
    ) -> QueryPlan:
        """创建执行计划"""
        try:
            # 1. 选择主表和关联表
            primary_tables = candidates[:2]  # 选择相关性最高的1-2个表作为主表
            join_tables = candidates[2:] if len(candidates) > 2 else []
            
            # 2. 计划JOIN条件
            join_conditions = await self._plan_join_conditions(primary_tables, join_tables, data_source_id)
            
            # 3. 生成WHERE条件
            where_conditions = self._generate_where_conditions(context)
            
            # 4. 选择查询字段
            select_columns = self._select_columns(context, primary_tables)
            
            # 5. GROUP BY和ORDER BY
            group_by_columns = self._generate_group_by(context, select_columns)
            order_by_columns = self._generate_order_by(context, select_columns)
            
            # 6. 评估复杂度
            complexity = self._evaluate_complexity(primary_tables, join_tables, join_conditions)
            
            # 7. 检查是否跨数据库
            cross_database = self._check_cross_database(primary_tables + join_tables)
            
            return QueryPlan(
                primary_tables=primary_tables,
                join_tables=join_tables,
                join_conditions=join_conditions,
                where_conditions=where_conditions,
                select_columns=select_columns,
                group_by_columns=group_by_columns,
                order_by_columns=order_by_columns,
                estimated_complexity=complexity,
                cross_database=cross_database
            )
            
        except Exception as e:
            self.logger.error(f"Error creating execution plan: {e}")
            raise
    
    async def _plan_join_conditions(
        self,
        primary_tables: List[TableCandidate],
        join_tables: List[TableCandidate],
        data_source_id: str
    ) -> List[str]:
        """规划JOIN条件"""
        join_conditions = []
        
        try:
            with get_db_session() as db:
                all_tables = primary_tables + join_tables
                
                for i, table1 in enumerate(all_tables):
                    for j, table2 in enumerate(all_tables[i+1:], i+1):
                        # 查找表之间的关系
                        relation = db.query(TableRelation).filter(
                            ((TableRelation.parent_table_id == table1.table.id) & 
                             (TableRelation.child_table_id == table2.table.id)) |
                            ((TableRelation.parent_table_id == table2.table.id) & 
                             (TableRelation.child_table_id == table1.table.id))
                        ).first()
                        
                        if relation:
                            join_condition = f"{table1.table.name}.{relation.parent_columns[0]} = {table2.table.name}.{relation.child_columns[0]}"
                            join_conditions.append(join_condition)
                        else:
                            # 尝试基于命名约定推断关系
                            inferred_join = self._infer_join_condition(table1.table, table2.table, db)
                            if inferred_join:
                                join_conditions.append(inferred_join)
                                
        except Exception as e:
            self.logger.error(f"Error planning join conditions: {e}")
            
        return join_conditions
    
    def _infer_join_condition(self, table1: Table, table2: Table, db: Session) -> Optional[str]:
        """基于命名约定推断JOIN条件"""
        try:
            # 获取两个表的字段
            columns1 = {col.name: col for col in db.query(TableColumn).filter(TableColumn.table_id == table1.id).all()}
            columns2 = {col.name: col for col in db.query(TableColumn).filter(TableColumn.table_id == table2.id).all()}
            
            # 查找可能的关联字段
            for col1_name, col1 in columns1.items():
                for col2_name, col2 in columns2.items():
                    # ID字段匹配
                    if col1_name == col2_name and 'id' in col1_name.lower():
                        return f"{table1.name}.{col1_name} = {table2.name}.{col2_name}"
                    
                    # 外键匹配 (table1_id 对应 table2.id)
                    if col1_name == f"{table2.name}_id" and col2_name == "id":
                        return f"{table1.name}.{col1_name} = {table2.name}.{col2_name}"
                    elif col2_name == f"{table1.name}_id" and col1_name == "id":
                        return f"{table1.name}.{col1_name} = {table2.name}.{col2_name}"
                        
        except Exception as e:
            self.logger.error(f"Error inferring join condition: {e}")
            
        return None
    
    def _generate_where_conditions(self, context: QueryContext) -> List[str]:
        """生成WHERE条件"""
        conditions = []
        
        # 时间范围条件
        if context.time_range:
            start_time, end_time = context.time_range
            conditions.append(f"created_at >= {start_time} AND created_at <= {end_time}")
        
        # 过滤条件
        for field, value in context.filters.items():
            if isinstance(value, str):
                conditions.append(f"{field} = '{value}'")
            else:
                conditions.append(f"{field} = {value}")
                
        return conditions
    
    def _select_columns(self, context: QueryContext, primary_tables: List[TableCandidate]) -> List[str]:
        """选择查询字段"""
        columns = []
        
        # 根据查询意图选择字段
        if context.intent == QueryIntent.STATISTICAL:
            # 统计查询：选择聚合字段
            columns.extend(['COUNT(*) as total_count'])
            if context.aggregation_type:
                for table in primary_tables:
                    for col in table.matching_columns:
                        if any(keyword in col.lower() for keyword in ['amount', 'price', 'total']):
                            columns.append(f"{context.aggregation_type}({col}) as {col}_{context.aggregation_type.lower()}")
        else:
            # 明细查询：选择相关字段
            for table in primary_tables:
                for col in table.matching_columns[:5]:  # 限制字段数量
                    columns.append(f"{table.table.name}.{col}")
                    
        return columns if columns else ['*']  # 默认返回所有字段
    
    def _generate_group_by(self, context: QueryContext, select_columns: List[str]) -> List[str]:
        """生成GROUP BY字段"""
        if context.intent in [QueryIntent.STATISTICAL, QueryIntent.AGGREGATION]:
            # 从SELECT字段中提取非聚合字段
            group_columns = []
            for col in select_columns:
                if not any(agg in col.upper() for agg in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']):
                    if col != '*':
                        group_columns.append(col)
            return group_columns
        return []
    
    def _generate_order_by(self, context: QueryContext, select_columns: List[str]) -> List[str]:
        """生成ORDER BY字段"""
        # 默认按时间字段降序排序
        for col in select_columns:
            if any(time_keyword in col.lower() for time_keyword in ['time', 'date', 'created']):
                return [f"{col} DESC"]
        
        # 如果有聚合字段，按聚合结果降序排序
        for col in select_columns:
            if any(agg in col.upper() for agg in ['COUNT', 'SUM', 'AVG']):
                return [f"{col} DESC"]
                
        return []
    
    def _evaluate_complexity(
        self,
        primary_tables: List[TableCandidate],
        join_tables: List[TableCandidate],
        join_conditions: List[str]
    ) -> str:
        """评估查询复杂度"""
        total_tables = len(primary_tables) + len(join_tables)
        total_joins = len(join_conditions)
        
        if total_tables <= 2 and total_joins <= 1:
            return "low"
        elif total_tables <= 4 and total_joins <= 3:
            return "medium"
        else:
            return "high"
    
    def _check_cross_database(self, tables: List[TableCandidate]) -> bool:
        """检查是否跨数据库查询"""
        database_ids = set()
        for table in tables:
            database_ids.add(table.table.database_id)
        return len(database_ids) > 1


class IntelligentQueryRouter:
    """智能查询路由器 - 主入口"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.semantic_analyzer = SemanticAnalyzer()
        self.table_matcher = TableMatcher()
        self.query_planner = QueryPlanner()
    
    async def route_query(
        self,
        natural_query: str,
        data_source_id: str,
        user_context: Optional[Dict] = None
    ) -> QueryPlan:
        """
        路由自然语言查询到具体的查询执行计划
        
        Args:
            natural_query: 自然语言查询
            data_source_id: 数据源ID
            user_context: 用户上下文（可选）
            
        Returns:
            查询执行计划
        """
        try:
            self.logger.info(f"Routing query: {natural_query}")
            
            # 1. 语义分析
            context = await self.semantic_analyzer.analyze_query(natural_query)
            self.logger.info(f"Query context: intent={context.intent}, entities={context.parsed_entities}")
            
            # 2. 表匹配
            candidates = await self.table_matcher.find_relevant_tables(context, data_source_id)
            self.logger.info(f"Found {len(candidates)} relevant tables")
            
            if not candidates:
                self.logger.warning(f"No relevant tables found for query: {natural_query}, using fallback strategy")
                # 创建一个默认的查询计划作为后备方案
                return self._create_fallback_query_plan(context, data_source_id, natural_query)
            
            # 3. 查询规划
            plan = await self.query_planner.create_execution_plan(context, candidates, data_source_id)
            self.logger.info(f"Created execution plan: complexity={plan.estimated_complexity}, cross_db={plan.cross_database}")
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Error routing query: {e}")
            raise
    
    def _create_fallback_query_plan(
        self, 
        context: QueryContext, 
        data_source_id: str, 
        natural_query: str
    ) -> QueryPlan:
        """创建后备查询计划（当找不到相关表时）"""
        
        # 创建一个默认的表候选（使用通用表名）
        fallback_table = "default_table"  # 这将被具体的连接器处理
        
        # 根据查询意图生成基础SQL
        if context.intent == QueryIntent.STATISTICAL:
            sql_template = "SELECT COUNT(*) as count FROM {table}"
        elif context.intent == QueryIntent.AGGREGATION:
            sql_template = "SELECT SUM(amount) as total FROM {table}"
        elif context.intent == QueryIntent.DETAIL:
            sql_template = "SELECT * FROM {table} LIMIT 100"
        else:
            sql_template = "SELECT COUNT(*) as count FROM {table}"
        
        # 应用表名替换
        sql_query = sql_template.format(table=fallback_table)
        
        return QueryPlan(
            primary_tables=[],
            join_tables=[],
            join_conditions=[],
            where_conditions=[],
            select_columns=["COUNT(*) as count"],
            group_by_columns=[],
            order_by_columns=[],
            estimated_complexity="low",
            cross_database=False,
            execution_order=[f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"]
        )