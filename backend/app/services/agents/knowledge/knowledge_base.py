"""
知识库系统

实现Agent间的知识共享和学习机制，包括：
- 模式识别和存储
- 用户偏好学习
- 最佳实践积累
- 智能推荐
- 知识图谱构建

Features:
- 持久化存储
- 实时学习更新
- 智能检索
- 知识推理
- 协作学习
"""

import asyncio
import json
import hashlib
import pickle
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union, Tuple, Set
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque
import sqlite3
import threading

from ..base import AgentError


@dataclass
class KnowledgeItem:
    """知识项"""
    knowledge_id: str
    knowledge_type: str  # "pattern", "preference", "insight", "best_practice"
    content: Dict[str, Any]
    tags: List[str]
    confidence_score: float
    usage_count: int = 0
    success_rate: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source_agent: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class UserPattern:
    """用户模式"""
    user_id: str
    pattern_type: str  # "preference", "behavior", "style", "workflow"
    pattern_data: Dict[str, Any]
    frequency: int = 1
    last_seen: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    context_tags: List[str] = field(default_factory=list)


@dataclass
class AgentInsight:
    """Agent洞察"""
    agent_id: str
    insight_type: str
    insight_content: str
    data_context: Dict[str, Any]
    performance_impact: float  # 对性能的影响
    applicability_score: float  # 适用性评分
    validation_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BestPractice:
    """最佳实践"""
    practice_id: str
    domain: str  # "data_query", "content_generation", "analysis", "visualization"
    scenario: str
    solution: Dict[str, Any]
    success_metrics: Dict[str, float]
    usage_statistics: Dict[str, int] = field(default_factory=dict)
    effectiveness_score: float = 1.0
    last_validated: datetime = field(default_factory=datetime.now)


class KnowledgeStorage:
    """知识存储管理器"""
    
    def __init__(self, db_path: str = "knowledge.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 知识项表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    knowledge_id TEXT PRIMARY KEY,
                    knowledge_type TEXT,
                    content TEXT,
                    tags TEXT,
                    confidence_score REAL,
                    usage_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 1.0,
                    created_at TEXT,
                    updated_at TEXT,
                    source_agent TEXT,
                    context TEXT,
                    metadata TEXT
                )
            ''')
            
            # 用户模式表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_patterns (
                    user_id TEXT,
                    pattern_type TEXT,
                    pattern_data TEXT,
                    frequency INTEGER DEFAULT 1,
                    last_seen TEXT,
                    confidence REAL DEFAULT 1.0,
                    context_tags TEXT,
                    PRIMARY KEY (user_id, pattern_type)
                )
            ''')
            
            # Agent洞察表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    insight_type TEXT,
                    insight_content TEXT,
                    data_context TEXT,
                    performance_impact REAL,
                    applicability_score REAL,
                    validation_count INTEGER DEFAULT 0,
                    created_at TEXT
                )
            ''')
            
            # 最佳实践表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS best_practices (
                    practice_id TEXT PRIMARY KEY,
                    domain TEXT,
                    scenario TEXT,
                    solution TEXT,
                    success_metrics TEXT,
                    usage_statistics TEXT,
                    effectiveness_score REAL DEFAULT 1.0,
                    last_validated TEXT
                )
            ''')
            
            conn.commit()
    
    async def store_knowledge_item(self, item: KnowledgeItem):
        """存储知识项"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO knowledge_items 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item.knowledge_id,
                    item.knowledge_type,
                    json.dumps(item.content),
                    json.dumps(item.tags),
                    item.confidence_score,
                    item.usage_count,
                    item.success_rate,
                    item.created_at.isoformat(),
                    item.updated_at.isoformat(),
                    item.source_agent,
                    json.dumps(item.context),
                    json.dumps(item.metadata)
                ))
                conn.commit()
    
    async def get_knowledge_items(
        self, 
        knowledge_type: str = None,
        tags: List[str] = None,
        min_confidence: float = 0.5,
        limit: int = 100
    ) -> List[KnowledgeItem]:
        """获取知识项"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM knowledge_items WHERE confidence_score >= ?"
                params = [min_confidence]
                
                if knowledge_type:
                    query += " AND knowledge_type = ?"
                    params.append(knowledge_type)
                
                query += " ORDER BY confidence_score DESC, usage_count DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                items = []
                for row in rows:
                    item = KnowledgeItem(
                        knowledge_id=row[0],
                        knowledge_type=row[1],
                        content=json.loads(row[2]),
                        tags=json.loads(row[3]),
                        confidence_score=row[4],
                        usage_count=row[5],
                        success_rate=row[6],
                        created_at=datetime.fromisoformat(row[7]),
                        updated_at=datetime.fromisoformat(row[8]),
                        source_agent=row[9],
                        context=json.loads(row[10]),
                        metadata=json.loads(row[11])
                    )
                    
                    # 标签过滤
                    if tags:
                        if any(tag in item.tags for tag in tags):
                            items.append(item)
                    else:
                        items.append(item)
                
                return items
    
    async def store_user_pattern(self, pattern: UserPattern):
        """存储用户模式"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_patterns 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pattern.user_id,
                    pattern.pattern_type,
                    json.dumps(pattern.pattern_data),
                    pattern.frequency,
                    pattern.last_seen.isoformat(),
                    pattern.confidence,
                    json.dumps(pattern.context_tags)
                ))
                conn.commit()
    
    async def get_user_patterns(self, user_id: str, pattern_type: str = None) -> List[UserPattern]:
        """获取用户模式"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if pattern_type:
                    cursor.execute(
                        "SELECT * FROM user_patterns WHERE user_id = ? AND pattern_type = ?",
                        (user_id, pattern_type)
                    )
                else:
                    cursor.execute("SELECT * FROM user_patterns WHERE user_id = ?", (user_id,))
                
                rows = cursor.fetchall()
                patterns = []
                
                for row in rows:
                    pattern = UserPattern(
                        user_id=row[0],
                        pattern_type=row[1],
                        pattern_data=json.loads(row[2]),
                        frequency=row[3],
                        last_seen=datetime.fromisoformat(row[4]),
                        confidence=row[5],
                        context_tags=json.loads(row[6])
                    )
                    patterns.append(pattern)
                
                return patterns


class PatternLearner:
    """模式学习器"""
    
    def __init__(self, storage: KnowledgeStorage):
        self.storage = storage
        self.learning_threshold = 3  # 最少出现次数
        self.confidence_threshold = 0.6
    
    async def learn_query_patterns(self, user_id: str, queries: List[Dict[str, Any]]):
        """学习查询模式"""
        try:
            # 分析查询模式
            patterns = self._analyze_query_patterns(queries)
            
            for pattern_type, pattern_data in patterns.items():
                # 创建或更新用户模式
                existing_patterns = await self.storage.get_user_patterns(user_id, f"query_{pattern_type}")
                
                if existing_patterns:
                    # 更新现有模式
                    pattern = existing_patterns[0]
                    pattern.frequency += 1
                    pattern.last_seen = datetime.now()
                    pattern.pattern_data.update(pattern_data)
                else:
                    # 创建新模式
                    pattern = UserPattern(
                        user_id=user_id,
                        pattern_type=f"query_{pattern_type}",
                        pattern_data=pattern_data,
                        frequency=1,
                        confidence=0.7,
                        context_tags=[f"query", pattern_type]
                    )
                
                await self.storage.store_user_pattern(pattern)
        
        except Exception as e:
            raise AgentError(f"学习查询模式失败: {str(e)}", "pattern_learner", "LEARNING_ERROR")
    
    def _analyze_query_patterns(self, queries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """分析查询模式"""
        patterns = {}
        
        # 字段使用模式
        field_usage = defaultdict(int)
        for query in queries:
            if 'fields' in query:
                for field in query['fields']:
                    field_usage[field] += 1
        
        patterns['field_preference'] = {
            'preferred_fields': sorted(field_usage.items(), key=lambda x: x[1], reverse=True)[:5],
            'total_queries': len(queries)
        }
        
        # 过滤条件模式
        filter_patterns = defaultdict(int)
        for query in queries:
            if 'filters' in query:
                for filter_item in query['filters']:
                    if 'operator' in filter_item:
                        filter_patterns[filter_item['operator']] += 1
        
        patterns['filter_preference'] = {
            'preferred_operators': dict(filter_patterns),
            'usage_frequency': len(queries)
        }
        
        # 时间范围模式
        time_ranges = []
        for query in queries:
            if 'time_range' in query:
                time_ranges.append(query['time_range'])
        
        if time_ranges:
            patterns['time_preference'] = {
                'common_ranges': list(set(time_ranges)),
                'usage_count': len(time_ranges)
            }
        
        return patterns
    
    async def learn_content_preferences(self, user_id: str, content_feedback: List[Dict[str, Any]]):
        """学习内容偏好"""
        try:
            # 分析内容偏好
            preferences = self._analyze_content_preferences(content_feedback)
            
            # 存储学习到的偏好
            for pref_type, pref_data in preferences.items():
                pattern = UserPattern(
                    user_id=user_id,
                    pattern_type=f"content_{pref_type}",
                    pattern_data=pref_data,
                    frequency=len(content_feedback),
                    confidence=min(1.0, len(content_feedback) / 10.0),  # 基于反馈数量计算置信度
                    context_tags=["content", "preference", pref_type]
                )
                
                await self.storage.store_user_pattern(pattern)
        
        except Exception as e:
            raise AgentError(f"学习内容偏好失败: {str(e)}", "pattern_learner", "LEARNING_ERROR")
    
    def _analyze_content_preferences(self, content_feedback: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """分析内容偏好"""
        preferences = {}
        
        # 风格偏好分析
        style_scores = defaultdict(list)
        for feedback in content_feedback:
            if 'style' in feedback and 'score' in feedback:
                style_scores[feedback['style']].append(feedback['score'])
        
        preferred_styles = {}
        for style, scores in style_scores.items():
            avg_score = sum(scores) / len(scores)
            if avg_score > 0.6:  # 只保留评分较高的风格
                preferred_styles[style] = avg_score
        
        preferences['style'] = {
            'preferred_styles': preferred_styles,
            'feedback_count': len(content_feedback)
        }
        
        # 长度偏好分析
        length_feedback = [f for f in content_feedback if 'length' in f and 'score' in f]
        if length_feedback:
            length_scores = defaultdict(list)
            for feedback in length_feedback:
                length_scores[feedback['length']].append(feedback['score'])
            
            optimal_length = max(length_scores.items(), key=lambda x: sum(x[1]) / len(x[1]))[0]
            preferences['length'] = {
                'optimal_length': optimal_length,
                'length_feedback': dict(length_scores)
            }
        
        return preferences


class InsightEngine:
    """洞察引擎"""
    
    def __init__(self, storage: KnowledgeStorage):
        self.storage = storage
        self.insight_cache = {}
        self.cache_ttl = 3600  # 1小时缓存
    
    async def generate_cross_agent_insights(
        self, 
        agent_results: List[Dict[str, Any]]
    ) -> List[AgentInsight]:
        """生成跨Agent洞察"""
        insights = []
        
        try:
            # 性能模式分析
            performance_insights = await self._analyze_performance_patterns(agent_results)
            insights.extend(performance_insights)
            
            # 协作模式分析
            collaboration_insights = await self._analyze_collaboration_patterns(agent_results)
            insights.extend(collaboration_insights)
            
            # 数据流分析
            dataflow_insights = await self._analyze_dataflow_patterns(agent_results)
            insights.extend(dataflow_insights)
            
            # 存储洞察
            for insight in insights:
                await self.storage.store_knowledge_item(
                    KnowledgeItem(
                        knowledge_id=f"insight_{insight.agent_id}_{int(datetime.now().timestamp())}",
                        knowledge_type="insight",
                        content=asdict(insight),
                        tags=[insight.insight_type, insight.agent_id],
                        confidence_score=insight.applicability_score,
                        source_agent="insight_engine"
                    )
                )
            
            return insights
        
        except Exception as e:
            raise AgentError(f"生成跨Agent洞察失败: {str(e)}", "insight_engine", "INSIGHT_ERROR")
    
    async def _analyze_performance_patterns(self, results: List[Dict[str, Any]]) -> List[AgentInsight]:
        """分析性能模式"""
        insights = []
        
        # 按Agent分组分析
        agent_performance = defaultdict(list)
        for result in results:
            if 'agent_id' in result and 'execution_time' in result:
                agent_performance[result['agent_id']].append({
                    'execution_time': result['execution_time'],
                    'success': result.get('success', True),
                    'data_size': result.get('data_size', 0)
                })
        
        for agent_id, performances in agent_performance.items():
            if len(performances) > 3:  # 至少3次执行才分析
                avg_time = sum(p['execution_time'] for p in performances) / len(performances)
                success_rate = sum(1 for p in performances if p['success']) / len(performances)
                
                if success_rate > 0.9 and avg_time < 5.0:  # 高成功率且快速
                    insight = AgentInsight(
                        agent_id=agent_id,
                        insight_type="high_performance",
                        insight_content=f"Agent {agent_id} 表现优秀，平均执行时间 {avg_time:.2f}s，成功率 {success_rate:.2%}",
                        data_context={'avg_time': avg_time, 'success_rate': success_rate},
                        performance_impact=0.8,
                        applicability_score=0.9
                    )
                    insights.append(insight)
        
        return insights
    
    async def _analyze_collaboration_patterns(self, results: List[Dict[str, Any]]) -> List[AgentInsight]:
        """分析协作模式"""
        insights = []
        
        # 找出经常一起使用的Agent
        collaboration_pairs = defaultdict(int)
        for i, result1 in enumerate(results):
            for result2 in results[i+1:]:
                if (result1.get('timestamp') and result2.get('timestamp') and 
                    abs(result1['timestamp'] - result2['timestamp']) < 300):  # 5分钟内
                    
                    agent1 = result1.get('agent_id')
                    agent2 = result2.get('agent_id')
                    if agent1 and agent2 and agent1 != agent2:
                        pair = tuple(sorted([agent1, agent2]))
                        collaboration_pairs[pair] += 1
        
        # 生成协作洞察
        for (agent1, agent2), count in collaboration_pairs.items():
            if count > 5:  # 频繁协作
                insight = AgentInsight(
                    agent_id=f"{agent1}+{agent2}",
                    insight_type="collaboration_pattern",
                    insight_content=f"Agent {agent1} 和 {agent2} 经常协作使用，共 {count} 次",
                    data_context={'agents': [agent1, agent2], 'collaboration_count': count},
                    performance_impact=0.6,
                    applicability_score=0.8
                )
                insights.append(insight)
        
        return insights
    
    async def _analyze_dataflow_patterns(self, results: List[Dict[str, Any]]) -> List[AgentInsight]:
        """分析数据流模式"""
        insights = []
        
        # 分析数据类型和大小模式
        data_patterns = defaultdict(list)
        for result in results:
            agent_id = result.get('agent_id')
            data_type = result.get('data_type')
            data_size = result.get('data_size', 0)
            
            if agent_id and data_type:
                data_patterns[agent_id].append({
                    'type': data_type,
                    'size': data_size,
                    'timestamp': result.get('timestamp', 0)
                })
        
        # 生成数据流洞察
        for agent_id, data_list in data_patterns.items():
            if len(data_list) > 10:
                common_types = defaultdict(int)
                avg_size = 0
                
                for data in data_list:
                    common_types[data['type']] += 1
                    avg_size += data['size']
                
                avg_size /= len(data_list)
                most_common_type = max(common_types, key=common_types.get)
                
                insight = AgentInsight(
                    agent_id=agent_id,
                    insight_type="data_pattern",
                    insight_content=f"Agent {agent_id} 主要处理 {most_common_type} 类型数据，平均大小 {avg_size:.2f}",
                    data_context={
                        'common_type': most_common_type,
                        'avg_size': avg_size,
                        'type_distribution': dict(common_types)
                    },
                    performance_impact=0.5,
                    applicability_score=0.7
                )
                insights.append(insight)
        
        return insights


class KnowledgeRetriever:
    """知识检索器"""
    
    def __init__(self, storage: KnowledgeStorage):
        self.storage = storage
        self.retrieval_cache = {}
        self.cache_ttl = 1800  # 30分钟缓存
    
    async def retrieve_relevant_knowledge(
        self,
        context: Dict[str, Any],
        knowledge_types: List[str] = None,
        max_results: int = 10
    ) -> List[KnowledgeItem]:
        """检索相关知识"""
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(context, knowledge_types, max_results)
            
            # 检查缓存
            if cache_key in self.retrieval_cache:
                cached_result, timestamp = self.retrieval_cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                    return cached_result
            
            # 提取上下文特征
            tags = self._extract_context_tags(context)
            
            # 检索知识项
            relevant_items = []
            
            if knowledge_types:
                for knowledge_type in knowledge_types:
                    items = await self.storage.get_knowledge_items(
                        knowledge_type=knowledge_type,
                        tags=tags,
                        limit=max_results // len(knowledge_types)
                    )
                    relevant_items.extend(items)
            else:
                relevant_items = await self.storage.get_knowledge_items(
                    tags=tags,
                    limit=max_results
                )
            
            # 排序和过滤
            sorted_items = sorted(
                relevant_items,
                key=lambda x: self._calculate_relevance_score(x, context),
                reverse=True
            )
            
            result = sorted_items[:max_results]
            
            # 更新缓存
            self.retrieval_cache[cache_key] = (result, datetime.now())
            
            return result
        
        except Exception as e:
            raise AgentError(f"知识检索失败: {str(e)}", "knowledge_retriever", "RETRIEVAL_ERROR")
    
    def _generate_cache_key(self, context: Dict[str, Any], knowledge_types: List[str], max_results: int) -> str:
        """生成缓存键"""
        key_data = {
            'context_hash': hashlib.md5(str(sorted(context.items())).encode()).hexdigest(),
            'knowledge_types': knowledge_types,
            'max_results': max_results
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def _extract_context_tags(self, context: Dict[str, Any]) -> List[str]:
        """提取上下文标签"""
        tags = []
        
        # 基于上下文键提取标签
        for key in context.keys():
            if key in ['agent_id', 'user_id', 'content_type', 'data_type']:
                tags.append(key)
        
        # 基于上下文值提取标签
        for value in context.values():
            if isinstance(value, str) and len(value) < 50:
                tags.append(value.lower())
        
        return list(set(tags))
    
    def _calculate_relevance_score(self, item: KnowledgeItem, context: Dict[str, Any]) -> float:
        """计算相关性分数"""
        score = item.confidence_score
        
        # 标签匹配加分
        context_tags = self._extract_context_tags(context)
        tag_matches = len(set(item.tags) & set(context_tags))
        score += tag_matches * 0.1
        
        # 使用频率加分
        score += min(item.usage_count / 100.0, 0.2)
        
        # 成功率加分
        score += (item.success_rate - 0.5) * 0.2
        
        # 时间衰减
        age_days = (datetime.now() - item.updated_at).days
        if age_days > 30:
            score *= 0.8
        elif age_days > 7:
            score *= 0.9
        
        return min(score, 1.0)


class KnowledgeShareManager:
    """知识共享管理器"""
    
    def __init__(self, db_path: str = "knowledge.db"):
        self.storage = KnowledgeStorage(db_path)
        self.pattern_learner = PatternLearner(self.storage)
        self.insight_engine = InsightEngine(self.storage)
        self.knowledge_retriever = KnowledgeRetriever(self.storage)
        
        # 性能统计
        self.usage_stats = {
            'knowledge_items_created': 0,
            'patterns_learned': 0,
            'insights_generated': 0,
            'knowledge_retrieved': 0
        }
    
    async def share_knowledge(
        self,
        agent_id: str,
        knowledge_type: str,
        content: Dict[str, Any],
        tags: List[str] = None,
        confidence: float = 0.8
    ) -> str:
        """分享知识"""
        try:
            knowledge_id = f"{agent_id}_{knowledge_type}_{int(datetime.now().timestamp())}"
            
            knowledge_item = KnowledgeItem(
                knowledge_id=knowledge_id,
                knowledge_type=knowledge_type,
                content=content,
                tags=tags or [],
                confidence_score=confidence,
                source_agent=agent_id
            )
            
            await self.storage.store_knowledge_item(knowledge_item)
            
            self.usage_stats['knowledge_items_created'] += 1
            return knowledge_id
        
        except Exception as e:
            raise AgentError(f"分享知识失败: {str(e)}", "knowledge_share_manager", "SHARE_ERROR")
    
    async def learn_from_interactions(
        self,
        user_id: str,
        interactions: List[Dict[str, Any]]
    ):
        """从交互中学习"""
        try:
            # 学习查询模式
            queries = [i for i in interactions if i.get('type') == 'query']
            if queries:
                await self.pattern_learner.learn_query_patterns(user_id, queries)
            
            # 学习内容偏好
            content_feedback = [i for i in interactions if i.get('type') == 'content_feedback']
            if content_feedback:
                await self.pattern_learner.learn_content_preferences(user_id, content_feedback)
            
            self.usage_stats['patterns_learned'] += len(queries) + len(content_feedback)
        
        except Exception as e:
            raise AgentError(f"从交互中学习失败: {str(e)}", "knowledge_share_manager", "LEARNING_ERROR")
    
    async def generate_insights(self, agent_results: List[Dict[str, Any]]) -> List[AgentInsight]:
        """生成洞察"""
        try:
            insights = await self.insight_engine.generate_cross_agent_insights(agent_results)
            self.usage_stats['insights_generated'] += len(insights)
            return insights
        
        except Exception as e:
            raise AgentError(f"生成洞察失败: {str(e)}", "knowledge_share_manager", "INSIGHT_ERROR")
    
    async def get_recommendations(
        self,
        agent_id: str,
        context: Dict[str, Any],
        recommendation_type: str = "best_practice"
    ) -> List[Dict[str, Any]]:
        """获取推荐"""
        try:
            knowledge_items = await self.knowledge_retriever.retrieve_relevant_knowledge(
                context,
                knowledge_types=[recommendation_type],
                max_results=5
            )
            
            recommendations = []
            for item in knowledge_items:
                recommendation = {
                    'id': item.knowledge_id,
                    'type': item.knowledge_type,
                    'content': item.content,
                    'confidence': item.confidence_score,
                    'source': item.source_agent,
                    'usage_count': item.usage_count
                }
                recommendations.append(recommendation)
            
            self.usage_stats['knowledge_retrieved'] += len(recommendations)
            return recommendations
        
        except Exception as e:
            raise AgentError(f"获取推荐失败: {str(e)}", "knowledge_share_manager", "RECOMMENDATION_ERROR")
    
    async def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """获取用户洞察"""
        try:
            patterns = await self.storage.get_user_patterns(user_id)
            
            insights = {
                'user_id': user_id,
                'total_patterns': len(patterns),
                'patterns_by_type': defaultdict(list),
                'recommendations': []
            }
            
            for pattern in patterns:
                insights['patterns_by_type'][pattern.pattern_type].append({
                    'data': pattern.pattern_data,
                    'frequency': pattern.frequency,
                    'confidence': pattern.confidence,
                    'last_seen': pattern.last_seen.isoformat()
                })
            
            # 基于模式生成个性化推荐
            if patterns:
                context = {'user_id': user_id, 'pattern_count': len(patterns)}
                recommendations = await self.get_recommendations(
                    'user_insight_agent',
                    context,
                    'preference'
                )
                insights['recommendations'] = recommendations[:3]
            
            return insights
        
        except Exception as e:
            raise AgentError(f"获取用户洞察失败: {str(e)}", "knowledge_share_manager", "USER_INSIGHT_ERROR")
    
    async def update_knowledge_usage(self, knowledge_id: str, success: bool = True):
        """更新知识使用情况"""
        try:
            items = await self.storage.get_knowledge_items()
            for item in items:
                if item.knowledge_id == knowledge_id:
                    item.usage_count += 1
                    if success:
                        # 更新成功率
                        total_uses = item.usage_count
                        current_successes = item.success_rate * (total_uses - 1)
                        item.success_rate = (current_successes + 1) / total_uses
                    else:
                        # 降低成功率
                        total_uses = item.usage_count
                        current_successes = item.success_rate * (total_uses - 1)
                        item.success_rate = current_successes / total_uses
                    
                    item.updated_at = datetime.now()
                    await self.storage.store_knowledge_item(item)
                    break
        
        except Exception as e:
            # 不抛出异常，避免影响主流程
            pass
    
    async def get_knowledge_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            all_items = await self.storage.get_knowledge_items(limit=10000)
            
            stats = {
                'total_knowledge_items': len(all_items),
                'by_type': defaultdict(int),
                'by_agent': defaultdict(int),
                'avg_confidence': 0.0,
                'avg_usage': 0.0,
                'recent_items': 0,
                'usage_stats': self.usage_stats
            }
            
            if all_items:
                total_confidence = 0
                total_usage = 0
                recent_threshold = datetime.now() - timedelta(days=7)
                
                for item in all_items:
                    stats['by_type'][item.knowledge_type] += 1
                    stats['by_agent'][item.source_agent] += 1
                    total_confidence += item.confidence_score
                    total_usage += item.usage_count
                    
                    if item.created_at > recent_threshold:
                        stats['recent_items'] += 1
                
                stats['avg_confidence'] = total_confidence / len(all_items)
                stats['avg_usage'] = total_usage / len(all_items)
            
            return stats
        
        except Exception as e:
            raise AgentError(f"获取知识库统计失败: {str(e)}", "knowledge_share_manager", "STATS_ERROR")
    
    async def cleanup_old_knowledge(self, days_threshold: int = 90):
        """清理旧知识"""
        try:
            # 这里可以实现清理逻辑
            # 删除超过阈值且使用率低的知识项
            pass
        
        except Exception as e:
            raise AgentError(f"清理旧知识失败: {str(e)}", "knowledge_share_manager", "CLEANUP_ERROR")