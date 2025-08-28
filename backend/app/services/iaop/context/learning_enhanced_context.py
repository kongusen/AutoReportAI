"""
学习驱动的上下文增强系统

基于Claude Code的学习理念：
1. 从每次成功执行中学习最佳实践
2. 识别并避免导致失败的上下文模式
3. 动态调整上下文优先级和权重
4. 建立领域特定的上下文知识库
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import pickle
import hashlib
from collections import defaultdict, Counter
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


class LearningMode(Enum):
    """学习模式"""
    PASSIVE = "passive"          # 被动学习，仅记录
    ACTIVE = "active"           # 主动学习，实时调整
    REINFORCEMENT = "reinforcement"  # 强化学习，基于奖励


class ContextKnowledgeType(Enum):
    """上下文知识类型"""
    PATTERN = "pattern"         # 上下文模式
    RULE = "rule"              # 上下文规则
    PREFERENCE = "preference"   # 用户偏好
    OPTIMIZATION = "optimization"  # 优化策略


@dataclass
class ContextKnowledge:
    """上下文知识条目"""
    knowledge_id: str
    knowledge_type: ContextKnowledgeType
    domain: str  # 领域，如"sql_generation", "chart_creation"
    content: Dict[str, Any]
    confidence_score: float
    usage_count: int = 0
    success_rate: float = 0.0
    last_used: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningSession:
    """学习会话"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_examples: int = 0
    successful_examples: int = 0
    knowledge_items_learned: int = 0
    domains_covered: Set[str] = field(default_factory=set)
    learning_metrics: Dict[str, float] = field(default_factory=dict)


class LearningEnhancedContextSystem:
    """
    学习驱动的上下文增强系统
    
    实现Claude Code的核心学习理念：
    - 从交互中持续学习
    - 基于成功模式改进未来性能
    - 智能适应用户偏好和业务需求
    """
    
    def __init__(
        self, 
        db_session=None,
        learning_mode: LearningMode = LearningMode.ACTIVE,
        knowledge_retention_days: int = 90
    ):
        self.db_session = db_session
        self.learning_mode = learning_mode
        self.knowledge_retention_days = knowledge_retention_days
        
        # 知识库
        self.knowledge_base: Dict[str, ContextKnowledge] = {}
        self.domain_knowledge: Dict[str, List[ContextKnowledge]] = defaultdict(list)
        
        # 学习模型
        self.pattern_vectorizer = TfidfVectorizer(max_features=1000)
        self.context_clusters: Dict[str, KMeans] = {}
        
        # 学习状态
        self.current_session: Optional[LearningSession] = None
        self.learning_stats = {
            'total_sessions': 0,
            'total_knowledge_items': 0,
            'average_session_success_rate': 0.0,
            'most_learned_domain': '',
            'learning_velocity': 0.0  # 每小时学习的知识项数
        }
        
        # 缓存和性能
        self.knowledge_cache: Dict[str, Any] = {}
        self.cache_hit_rate = 0.0
        
        logger.info(f"学习增强上下文系统初始化，学习模式: {learning_mode.value}")
    
    async def start_learning_session(
        self,
        session_context: Dict[str, Any]
    ) -> str:
        """开始学习会话"""
        
        session_id = f"learning_session_{int(datetime.now().timestamp())}"
        
        self.current_session = LearningSession(
            session_id=session_id,
            start_time=datetime.now()
        )
        
        logger.info(f"开始学习会话: {session_id}")
        return session_id
    
    async def learn_from_execution_success(
        self,
        execution_context: Dict[str, Any],
        execution_result: Dict[str, Any],
        business_domain: str
    ) -> Dict[str, Any]:
        """
        从成功执行中学习
        
        分析成功案例中的关键上下文模式，提取可复用的知识
        """
        logger.info(f"从成功执行中学习，领域: {business_domain}")
        
        try:
            learning_results = {
                'knowledge_items_extracted': 0,
                'patterns_discovered': 0,
                'rules_generated': 0,
                'confidence_scores': {}
            }
            
            # 1. 提取上下文模式
            context_patterns = await self._extract_success_context_patterns(
                execution_context, execution_result, business_domain
            )
            
            for pattern in context_patterns:
                knowledge_item = await self._create_knowledge_from_pattern(
                    pattern, business_domain, ContextKnowledgeType.PATTERN
                )
                await self._store_knowledge_item(knowledge_item)
                learning_results['patterns_discovered'] += 1
            
            # 2. 生成上下文规则
            context_rules = await self._generate_context_rules_from_success(
                execution_context, execution_result, business_domain
            )
            
            for rule in context_rules:
                knowledge_item = await self._create_knowledge_from_rule(
                    rule, business_domain, ContextKnowledgeType.RULE
                )
                await self._store_knowledge_item(knowledge_item)
                learning_results['rules_generated'] += 1
            
            # 3. 更新上下文优先级
            priority_updates = await self._update_context_priorities_from_success(
                execution_context, execution_result, business_domain
            )
            
            # 4. 学习用户偏好
            if execution_result.get('user_feedback'):
                preference_knowledge = await self._learn_user_preferences(
                    execution_context, execution_result['user_feedback'], business_domain
                )
                
                for pref in preference_knowledge:
                    knowledge_item = await self._create_knowledge_from_preference(
                        pref, business_domain, ContextKnowledgeType.PREFERENCE
                    )
                    await self._store_knowledge_item(knowledge_item)
            
            # 5. 更新聚类模型
            if self.learning_mode == LearningMode.ACTIVE:
                await self._update_context_clusters(
                    business_domain, execution_context, "success"
                )
            
            # 6. 更新学习会话统计
            if self.current_session:
                self.current_session.successful_examples += 1
                self.current_session.domains_covered.add(business_domain)
                self.current_session.knowledge_items_learned += len(context_patterns) + len(context_rules)
            
            learning_results['knowledge_items_extracted'] = (
                learning_results['patterns_discovered'] + 
                learning_results['rules_generated']
            )
            
            logger.info(f"成功学习完成，提取 {learning_results['knowledge_items_extracted']} 个知识项")
            
            return learning_results
            
        except Exception as e:
            logger.error(f"从成功执行学习失败: {e}")
            return {
                'knowledge_items_extracted': 0,
                'error': str(e)
            }
    
    async def learn_from_execution_failure(
        self,
        execution_context: Dict[str, Any],
        execution_result: Dict[str, Any],
        business_domain: str
    ) -> Dict[str, Any]:
        """
        从失败执行中学习
        
        分析失败案例，识别导致失败的上下文模式，生成避免规则
        """
        logger.info(f"从失败执行中学习，领域: {business_domain}")
        
        try:
            learning_results = {
                'failure_patterns_identified': 0,
                'avoidance_rules_created': 0,
                'context_adjustments': 0
            }
            
            # 1. 识别失败模式
            failure_patterns = await self._identify_failure_patterns(
                execution_context, execution_result, business_domain
            )
            
            learning_results['failure_patterns_identified'] = len(failure_patterns)
            
            # 2. 生成避免规则
            for pattern in failure_patterns:
                avoidance_rule = await self._create_avoidance_rule_from_failure(
                    pattern, execution_result, business_domain
                )
                
                knowledge_item = ContextKnowledge(
                    knowledge_id=f"avoidance_{pattern['pattern_id']}",
                    knowledge_type=ContextKnowledgeType.RULE,
                    domain=business_domain,
                    content={
                        'rule_type': 'avoidance',
                        'pattern_to_avoid': pattern,
                        'alternative_suggestions': avoidance_rule.get('alternatives', []),
                        'confidence': avoidance_rule.get('confidence', 0.7)
                    },
                    confidence_score=avoidance_rule.get('confidence', 0.7)
                )
                
                await self._store_knowledge_item(knowledge_item)
                learning_results['avoidance_rules_created'] += 1
            
            # 3. 降低失败上下文的优先级
            context_adjustments = await self._adjust_context_priorities_from_failure(
                execution_context, execution_result, business_domain
            )
            
            learning_results['context_adjustments'] = len(context_adjustments)
            
            # 4. 更新失败聚类
            if self.learning_mode == LearningMode.ACTIVE:
                await self._update_context_clusters(
                    business_domain, execution_context, "failure"
                )
            
            # 5. 更新学习会话统计
            if self.current_session:
                self.current_session.total_examples += 1
                self.current_session.domains_covered.add(business_domain)
            
            logger.info(f"失败学习完成，创建 {learning_results['avoidance_rules_created']} 个避免规则")
            
            return learning_results
            
        except Exception as e:
            logger.error(f"从失败执行学习失败: {e}")
            return {
                'failure_patterns_identified': 0,
                'error': str(e)
            }
    
    async def enhance_context_with_learned_knowledge(
        self,
        current_context: Dict[str, Any],
        business_domain: str,
        execution_intent: str
    ) -> Dict[str, Any]:
        """
        使用学习到的知识增强上下文
        
        基于历史学习的知识，智能增强当前执行上下文
        """
        logger.info(f"使用学习知识增强上下文，领域: {business_domain}")
        
        try:
            enhancement_result = {
                'original_context_size': len(current_context),
                'enhancements_applied': [],
                'knowledge_items_used': [],
                'confidence_improvements': {},
                'enhanced_context': current_context.copy()
            }
            
            # 1. 检索相关知识
            relevant_knowledge = await self._retrieve_relevant_knowledge(
                current_context, business_domain, execution_intent
            )
            
            # 2. 应用模式知识
            pattern_enhancements = await self._apply_pattern_knowledge(
                current_context, relevant_knowledge.get('patterns', [])
            )
            
            enhancement_result['enhanced_context'].update(pattern_enhancements)
            enhancement_result['enhancements_applied'].extend(
                [f"pattern_{p['knowledge_id']}" for p in relevant_knowledge.get('patterns', [])]
            )
            
            # 3. 应用规则知识
            rule_enhancements = await self._apply_rule_knowledge(
                enhancement_result['enhanced_context'], 
                relevant_knowledge.get('rules', [])
            )
            
            enhancement_result['enhanced_context'].update(rule_enhancements)
            enhancement_result['enhancements_applied'].extend(
                [f"rule_{r['knowledge_id']}" for r in relevant_knowledge.get('rules', [])]
            )
            
            # 4. 应用用户偏好
            preference_enhancements = await self._apply_preference_knowledge(
                enhancement_result['enhanced_context'],
                relevant_knowledge.get('preferences', [])
            )
            
            enhancement_result['enhanced_context'].update(preference_enhancements)
            enhancement_result['enhancements_applied'].extend(
                [f"preference_{p['knowledge_id']}" for p in relevant_knowledge.get('preferences', [])]
            )
            
            # 5. 计算置信度改进
            original_confidence = current_context.get('confidence_score', 0.5)
            knowledge_confidence_boost = self._calculate_knowledge_confidence_boost(
                relevant_knowledge
            )
            
            enhanced_confidence = min(1.0, original_confidence + knowledge_confidence_boost)
            enhancement_result['enhanced_context']['confidence_score'] = enhanced_confidence
            enhancement_result['confidence_improvements']['total_boost'] = knowledge_confidence_boost
            
            # 6. 记录知识使用情况
            for knowledge_category in relevant_knowledge:
                for knowledge_item in relevant_knowledge[knowledge_category]:
                    await self._record_knowledge_usage(knowledge_item['knowledge_id'])
            
            logger.info(f"上下文知识增强完成，应用了 {len(enhancement_result['enhancements_applied'])} 项增强")
            
            return {
                'success': True,
                'enhancement_result': enhancement_result,
                'knowledge_applied': len(enhancement_result['enhancements_applied']) > 0
            }
            
        except Exception as e:
            logger.error(f"上下文知识增强失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'enhanced_context': current_context
            }
    
    async def optimize_context_learning_strategy(
        self,
        performance_metrics: Dict[str, float],
        domain_feedback: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        优化上下文学习策略
        
        基于性能反馈，动态调整学习策略和参数
        """
        logger.info("优化上下文学习策略")
        
        try:
            optimization_result = {
                'strategy_adjustments': [],
                'learning_rate_changes': {},
                'knowledge_retention_updates': {},
                'clustering_improvements': {}
            }
            
            # 1. 分析领域表现
            domain_performance = {}
            for domain, feedbacks in domain_feedback.items():
                success_rate = sum(1 for f in feedbacks if f.get('success', False)) / max(len(feedbacks), 1)
                avg_confidence = sum(f.get('confidence', 0.5) for f in feedbacks) / max(len(feedbacks), 1)
                
                domain_performance[domain] = {
                    'success_rate': success_rate,
                    'average_confidence': avg_confidence,
                    'sample_size': len(feedbacks)
                }
            
            # 2. 调整学习率
            for domain, perf in domain_performance.items():
                current_lr = self.learning_stats.get(f'{domain}_learning_rate', 0.1)
                
                if perf['success_rate'] < 0.6:
                    # 表现不佳，提高学习率
                    new_lr = min(0.3, current_lr * 1.2)
                    optimization_result['strategy_adjustments'].append(
                        f"提高{domain}学习率: {current_lr:.3f} -> {new_lr:.3f}"
                    )
                elif perf['success_rate'] > 0.8:
                    # 表现良好，降低学习率以保持稳定
                    new_lr = max(0.05, current_lr * 0.9)
                    optimization_result['strategy_adjustments'].append(
                        f"降低{domain}学习率: {current_lr:.3f} -> {new_lr:.3f}"
                    )
                else:
                    new_lr = current_lr
                
                optimization_result['learning_rate_changes'][domain] = new_lr
            
            # 3. 优化知识保留策略
            knowledge_usage_stats = await self._analyze_knowledge_usage_patterns()
            
            for domain in knowledge_usage_stats:
                usage_rate = knowledge_usage_stats[domain]['usage_rate']
                if usage_rate < 0.3:
                    # 使用率低，考虑增加保留期
                    new_retention = min(180, self.knowledge_retention_days * 1.5)
                    optimization_result['knowledge_retention_updates'][domain] = new_retention
            
            # 4. 改进聚类算法
            for domain in self.context_clusters:
                cluster_quality = await self._evaluate_cluster_quality(domain)
                if cluster_quality < 0.6:
                    # 聚类质量差，重新训练
                    await self._retrain_domain_clusters(domain)
                    optimization_result['clustering_improvements'][domain] = 'retrained'
            
            # 5. 更新全局学习统计
            await self._update_global_learning_stats(domain_performance)
            
            logger.info("上下文学习策略优化完成")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"学习策略优化失败: {e}")
            return {
                'strategy_adjustments': [],
                'error': str(e)
            }
    
    async def _extract_success_context_patterns(
        self,
        context: Dict[str, Any],
        result: Dict[str, Any],
        domain: str
    ) -> List[Dict[str, Any]]:
        """从成功案例中提取上下文模式"""
        
        patterns = []
        
        # 1. 关键上下文组合模式
        key_contexts = {k: v for k, v in context.items() 
                       if k in ['data_source_context', 'semantic_analysis', 'business_intent']}
        
        if len(key_contexts) >= 2:
            pattern = {
                'pattern_id': f"success_combo_{domain}_{hash(str(sorted(key_contexts.keys())))}",
                'pattern_type': 'context_combination',
                'context_keys': list(key_contexts.keys()),
                'context_values': key_contexts,
                'success_confidence': result.get('confidence_score', 0.8),
                'domain': domain
            }
            patterns.append(pattern)
        
        # 2. 高价值单一上下文模式
        for key, value in context.items():
            if self._is_high_value_context(key, value, result):
                pattern = {
                    'pattern_id': f"success_single_{domain}_{hash(key)}",
                    'pattern_type': 'single_context',
                    'context_key': key,
                    'context_value': value,
                    'success_confidence': result.get('confidence_score', 0.8),
                    'domain': domain
                }
                patterns.append(pattern)
        
        return patterns
    
    async def _store_knowledge_item(self, knowledge_item: ContextKnowledge):
        """存储知识项"""
        
        self.knowledge_base[knowledge_item.knowledge_id] = knowledge_item
        self.domain_knowledge[knowledge_item.domain].append(knowledge_item)
        
        # 如果超过保留期限，清理旧知识
        cutoff_date = datetime.now() - timedelta(days=self.knowledge_retention_days)
        self._cleanup_old_knowledge(cutoff_date)
    
    def _is_high_value_context(
        self, 
        key: str, 
        value: Any, 
        result: Dict[str, Any]
    ) -> bool:
        """判断是否为高价值上下文"""
        
        # 基于结果质量判断
        if result.get('confidence_score', 0) < 0.7:
            return False
        
        # 关键上下文字段
        high_value_keys = [
            'data_source_context', 'semantic_analysis', 'business_intent',
            'aggregation_type', 'chart_type_hint', 'expected_result_type'
        ]
        
        return key in high_value_keys
    
    def _cleanup_old_knowledge(self, cutoff_date: datetime):
        """清理过期知识"""
        
        to_remove = []
        for knowledge_id, knowledge in self.knowledge_base.items():
            if knowledge.created_at < cutoff_date and knowledge.usage_count < 5:
                to_remove.append(knowledge_id)
        
        for knowledge_id in to_remove:
            del self.knowledge_base[knowledge_id]
            # 从领域知识中移除
            for domain_list in self.domain_knowledge.values():
                domain_list[:] = [k for k in domain_list if k.knowledge_id != knowledge_id]


# 工厂函数
def create_learning_enhanced_context_system(
    db_session=None,
    learning_mode: str = "active"
) -> LearningEnhancedContextSystem:
    """创建学习增强上下文系统"""
    
    mode_mapping = {
        'passive': LearningMode.PASSIVE,
        'active': LearningMode.ACTIVE,
        'reinforcement': LearningMode.REINFORCEMENT
    }
    
    return LearningEnhancedContextSystem(
        db_session=db_session,
        learning_mode=mode_mapping.get(learning_mode, LearningMode.ACTIVE)
    )