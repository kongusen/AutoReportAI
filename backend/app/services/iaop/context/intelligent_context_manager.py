"""
智能上下文管理器 - 基于Claude Code最佳实践

核心改进：
1. 渐进式上下文优化 - 基于执行反馈持续改进上下文质量
2. 学习驱动的上下文增强 - 从成功案例中提取有价值的上下文模式
3. 依赖感知的上下文管理 - 自动识别和管理上下文依赖关系
4. 智能上下文推理 - 基于业务逻辑和历史数据推理缺失的上下文
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import networkx as nx

from .execution_context import EnhancedExecutionContext, ContextScope, ContextEntry

logger = logging.getLogger(__name__)


class ContextIntelligenceLevel(Enum):
    """上下文智能级别"""
    BASIC = "basic"              # 基础上下文管理
    ENHANCED = "enhanced"        # 增强上下文推理
    ADAPTIVE = "adaptive"        # 自适应上下文优化
    INTELLIGENT = "intelligent"   # 智能上下文学习


class ContextRelevance(Enum):
    """上下文相关性评级"""
    CRITICAL = "critical"        # 关键上下文，缺失会导致失败
    IMPORTANT = "important"      # 重要上下文，影响质量
    HELPFUL = "helpful"          # 有用上下文，提升效果
    OPTIONAL = "optional"        # 可选上下文，不影响核心功能


@dataclass
class ContextPattern:
    """上下文模式"""
    pattern_id: str
    pattern_name: str
    context_keys: Set[str]
    success_conditions: Dict[str, Any]
    failure_indicators: List[str]
    confidence_score: float
    usage_count: int = 0
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextDependency:
    """上下文依赖关系"""
    source_key: str
    target_key: str
    dependency_type: str  # "prerequisite", "derived", "related"
    strength: float  # 0.0-1.0，依赖强度
    reasoning: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ContextOptimizationResult:
    """上下文优化结果"""
    success: bool
    optimized_context: EnhancedExecutionContext
    optimization_iterations: int
    improvements_made: List[str]
    learned_patterns: List[ContextPattern]
    confidence_score: float
    processing_time_ms: float
    error_analysis: Optional[Dict[str, Any]] = None


class IntelligentContextManager:
    """
    智能上下文管理器
    
    基于Claude Code的最佳实践：
    1. 对话式上下文优化 - 基于执行结果反馈迭代改进上下文
    2. 上下文模式学习 - 从成功案例中提取可复用的上下文模式
    3. 依赖关系推理 - 自动识别和管理上下文间的依赖关系
    4. 智能上下文补全 - 基于业务逻辑推理和补全缺失的上下文
    """
    
    def __init__(
        self, 
        db_session=None, 
        intelligence_level: ContextIntelligenceLevel = ContextIntelligenceLevel.ENHANCED,
        enable_learning: bool = True
    ):
        self.db_session = db_session
        self.intelligence_level = intelligence_level
        self.enable_learning = enable_learning
        
        # 上下文模式存储
        self.context_patterns: Dict[str, ContextPattern] = {}
        self.dependency_graph = nx.DiGraph()
        
        # 优化配置
        self.max_optimization_iterations = 5
        self.confidence_threshold = 0.8
        self.pattern_usage_decay = 0.95  # 模式使用衰减因子
        
        # 缓存和性能优化
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(hours=24)
        
        logger.info(f"智能上下文管理器初始化，智能级别: {intelligence_level.value}")
    
    async def optimize_execution_context(
        self,
        context: EnhancedExecutionContext,
        execution_target: str,
        optimization_hints: Optional[Dict[str, Any]] = None
    ) -> ContextOptimizationResult:
        """
        优化执行上下文
        
        基于Claude Code的渐进式改进理念，通过多轮迭代优化上下文质量
        """
        start_time = datetime.now()
        logger.info(f"开始智能上下文优化，目标: {execution_target}")
        
        try:
            optimization_history = []
            current_context = self._deep_copy_context(context)
            iteration = 0
            
            while iteration < self.max_optimization_iterations:
                iteration += 1
                logger.debug(f"上下文优化迭代 {iteration}")
                
                # 1. 分析当前上下文质量
                quality_analysis = await self._analyze_context_quality(
                    current_context, execution_target
                )
                
                optimization_history.append({
                    'iteration': iteration,
                    'quality_analysis': quality_analysis,
                    'context_snapshot': self._create_context_snapshot(current_context),
                    'timestamp': datetime.now()
                })
                
                # 2. 检查是否已达到满意质量
                if quality_analysis.get('confidence_score', 0) >= self.confidence_threshold:
                    logger.info(f"上下文优化成功，置信度: {quality_analysis.get('confidence_score')}")
                    
                    # 提取成功模式
                    if self.enable_learning:
                        learned_patterns = await self._extract_context_patterns(
                            current_context, execution_target, quality_analysis
                        )
                        await self._save_learned_patterns(learned_patterns)
                    else:
                        learned_patterns = []
                    
                    return ContextOptimizationResult(
                        success=True,
                        optimized_context=current_context,
                        optimization_iterations=iteration,
                        improvements_made=quality_analysis.get('improvements', []),
                        learned_patterns=learned_patterns,
                        confidence_score=quality_analysis.get('confidence_score', 0),
                        processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                    )
                
                # 3. 执行上下文改进
                improvement_result = await self._improve_context_iteration(
                    current_context, quality_analysis, execution_target, optimization_hints
                )
                
                if not improvement_result.get('success'):
                    logger.warning(f"上下文改进失败: {improvement_result.get('error')}")
                    break
                
                # 4. 应用改进结果
                current_context = improvement_result.get('improved_context', current_context)
            
            # 优化未能在最大迭代次数内达到期望质量
            logger.warning(f"上下文优化未能在{self.max_optimization_iterations}次迭代内达到期望质量")
            
            return ContextOptimizationResult(
                success=False,
                optimized_context=current_context,
                optimization_iterations=iteration,
                improvements_made=[],
                learned_patterns=[],
                confidence_score=quality_analysis.get('confidence_score', 0.5),
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_analysis=await self._analyze_optimization_failure(optimization_history)
            )
            
        except Exception as e:
            logger.error(f"智能上下文优化异常: {e}")
            return ContextOptimizationResult(
                success=False,
                optimized_context=context,
                optimization_iterations=0,
                improvements_made=[],
                learned_patterns=[],
                confidence_score=0.0,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_analysis={'exception': str(e)}
            )
    
    async def enhance_context_with_intelligence(
        self,
        context: EnhancedExecutionContext,
        business_intent: str,
        data_source_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用智能推理增强上下文
        
        基于业务意图和数据源信息，智能推理和补全缺失的上下文信息
        """
        logger.info("使用智能推理增强上下文")
        
        try:
            enhancement_results = {
                'original_context_keys': list(context.context_entries.keys()),
                'enhancements_applied': [],
                'confidence_scores': {},
                'reasoning': {}
            }
            
            # 1. 基于业务意图推理上下文
            business_enhancements = await self._infer_business_context(
                business_intent, context, data_source_context
            )
            
            for key, value in business_enhancements.items():
                context.set_context(
                    key, value['value'], ContextScope.REQUEST, 
                    metadata={'confidence': value['confidence'], 'source': 'business_inference'}
                )
                enhancement_results['enhancements_applied'].append(key)
                enhancement_results['confidence_scores'][key] = value['confidence']
                enhancement_results['reasoning'][key] = value['reasoning']
            
            # 2. 基于数据源schema推理技术上下文
            schema_enhancements = await self._infer_schema_context(
                data_source_context, context, business_intent
            )
            
            for key, value in schema_enhancements.items():
                context.set_context(
                    key, value['value'], ContextScope.REQUEST,
                    metadata={'confidence': value['confidence'], 'source': 'schema_inference'}
                )
                enhancement_results['enhancements_applied'].append(key)
                enhancement_results['confidence_scores'][key] = value['confidence']
                enhancement_results['reasoning'][key] = value['reasoning']
            
            # 3. 应用历史成功模式
            if self.enable_learning and self.context_patterns:
                pattern_enhancements = await self._apply_learned_patterns(
                    context, business_intent, data_source_context
                )
                
                for key, value in pattern_enhancements.items():
                    context.set_context(
                        key, value['value'], ContextScope.REQUEST,
                        metadata={'confidence': value['confidence'], 'source': 'learned_pattern'}
                    )
                    enhancement_results['enhancements_applied'].append(key)
                    enhancement_results['confidence_scores'][key] = value['confidence']
                    enhancement_results['reasoning'][key] = value['reasoning']
            
            # 4. 建立上下文依赖关系
            await self._build_context_dependencies(context, enhancement_results)
            
            logger.info(f"上下文智能增强完成，新增 {len(enhancement_results['enhancements_applied'])} 个上下文项")
            
            return {
                'success': True,
                'enhanced_context': context,
                'enhancement_details': enhancement_results,
                'total_context_items': len(context.context_entries),
                'new_context_items': len(enhancement_results['enhancements_applied'])
            }
            
        except Exception as e:
            logger.error(f"上下文智能增强失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'enhanced_context': context
            }
    
    async def manage_multi_placeholder_context(
        self,
        placeholders: List[Dict[str, Any]],
        global_context: Dict[str, Any],
        execution_mode: str = "batch"
    ) -> Dict[str, Any]:
        """
        管理多占位符的上下文
        
        基于Claude Code的上下文保持理念，管理复杂的多占位符执行上下文
        """
        logger.info(f"管理多占位符上下文，数量: {len(placeholders)}")
        
        try:
            # 1. 创建全局执行上下文
            master_context = EnhancedExecutionContext(
                session_id=f"multi_placeholder_{datetime.now().timestamp()}",
                user_id=global_context.get('user_id', 'system'),
                request=global_context
            )
            
            # 设置全局上下文
            for key, value in global_context.items():
                master_context.set_context(key, value, ContextScope.GLOBAL)
            
            # 2. 分析占位符依赖关系
            dependency_analysis = await self._analyze_placeholder_dependencies(placeholders)
            
            # 3. 为每个占位符创建独立上下文
            placeholder_contexts = {}
            for placeholder in placeholders:
                placeholder_id = placeholder.get('id', placeholder.get('name'))
                
                # 创建独立上下文
                placeholder_context = self._create_placeholder_context(
                    placeholder, master_context, dependency_analysis
                )
                
                # 智能增强上下文
                enhancement_result = await self.enhance_context_with_intelligence(
                    placeholder_context,
                    placeholder.get('business_intent', ''),
                    global_context.get('data_source_context', {})
                )
                
                placeholder_contexts[placeholder_id] = {
                    'context': enhancement_result.get('enhanced_context'),
                    'dependencies': dependency_analysis.get('dependencies', {}).get(placeholder_id, []),
                    'enhancement_details': enhancement_result.get('enhancement_details', {})
                }
            
            # 4. 建立上下文共享机制
            shared_context = await self._create_shared_context_space(
                placeholder_contexts, master_context
            )
            
            # 5. 优化执行顺序
            execution_order = await self._optimize_execution_order(
                placeholders, dependency_analysis, execution_mode
            )
            
            return {
                'success': True,
                'master_context': master_context,
                'placeholder_contexts': placeholder_contexts,
                'shared_context': shared_context,
                'execution_order': execution_order,
                'dependency_analysis': dependency_analysis,
                'total_placeholders': len(placeholders),
                'context_optimization_applied': True
            }
            
        except Exception as e:
            logger.error(f"多占位符上下文管理失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'placeholder_contexts': {}
            }
    
    async def _analyze_context_quality(
        self,
        context: EnhancedExecutionContext,
        execution_target: str
    ) -> Dict[str, Any]:
        """分析上下文质量"""
        
        quality_metrics = {
            'completeness': 0.0,
            'relevance': 0.0,
            'consistency': 0.0,
            'freshness': 0.0
        }
        
        # 1. 完整性分析 - 检查关键上下文是否存在
        required_contexts = await self._get_required_contexts(execution_target)
        present_contexts = set(context.context_entries.keys())
        missing_contexts = required_contexts - present_contexts
        
        completeness = 1.0 - (len(missing_contexts) / max(len(required_contexts), 1))
        quality_metrics['completeness'] = completeness
        
        # 2. 相关性分析 - 评估上下文与执行目标的相关性
        relevance_scores = []
        for key, entry in context.context_entries.items():
            relevance = await self._calculate_context_relevance(key, entry.value, execution_target)
            relevance_scores.append(relevance)
        
        quality_metrics['relevance'] = sum(relevance_scores) / max(len(relevance_scores), 1)
        
        # 3. 一致性分析 - 检查上下文间的一致性
        consistency_score = await self._check_context_consistency(context)
        quality_metrics['consistency'] = consistency_score
        
        # 4. 新鲜度分析 - 评估上下文的时效性
        freshness_scores = []
        current_time = datetime.now()
        for entry in context.context_entries.values():
            age_hours = (current_time - entry.updated_at).total_seconds() / 3600
            freshness = max(0, 1 - (age_hours / 24))  # 24小时后完全过期
            freshness_scores.append(freshness)
        
        quality_metrics['freshness'] = sum(freshness_scores) / max(len(freshness_scores), 1)
        
        # 计算综合质量分数
        weights = {'completeness': 0.4, 'relevance': 0.3, 'consistency': 0.2, 'freshness': 0.1}
        confidence_score = sum(quality_metrics[metric] * weight for metric, weight in weights.items())
        
        return {
            'confidence_score': confidence_score,
            'quality_metrics': quality_metrics,
            'missing_contexts': list(missing_contexts),
            'suggestions': await self._generate_quality_improvement_suggestions(
                quality_metrics, missing_contexts, execution_target
            )
        }
    
    async def _improve_context_iteration(
        self,
        context: EnhancedExecutionContext,
        quality_analysis: Dict[str, Any],
        execution_target: str,
        optimization_hints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行一次上下文改进迭代"""
        
        try:
            improvements_made = []
            
            # 1. 补充缺失的关键上下文
            missing_contexts = quality_analysis.get('missing_contexts', [])
            for missing_key in missing_contexts:
                inferred_value = await self._infer_missing_context(
                    missing_key, context, execution_target, optimization_hints
                )
                
                if inferred_value is not None:
                    context.set_context(
                        missing_key, inferred_value, ContextScope.REQUEST,
                        metadata={'source': 'inference', 'confidence': 0.7}
                    )
                    improvements_made.append(f"补充缺失上下文: {missing_key}")
            
            # 2. 修正不一致的上下文
            consistency_issues = quality_analysis.get('consistency_issues', [])
            for issue in consistency_issues:
                correction_result = await self._correct_context_inconsistency(
                    issue, context, execution_target
                )
                if correction_result.get('success'):
                    improvements_made.append(f"修正一致性问题: {issue.get('description')}")
            
            # 3. 优化低相关性的上下文
            low_relevance_contexts = quality_analysis.get('low_relevance_contexts', [])
            for context_key in low_relevance_contexts:
                optimization_result = await self._optimize_context_relevance(
                    context_key, context, execution_target
                )
                if optimization_result.get('success'):
                    improvements_made.append(f"优化上下文相关性: {context_key}")
            
            # 4. 应用优化提示
            if optimization_hints:
                hint_applications = await self._apply_optimization_hints(
                    optimization_hints, context, execution_target
                )
                improvements_made.extend(hint_applications)
            
            return {
                'success': True,
                'improved_context': context,
                'improvements_made': improvements_made,
                'iteration_summary': f"应用了 {len(improvements_made)} 项改进"
            }
            
        except Exception as e:
            logger.error(f"上下文改进迭代失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'improved_context': context
            }
    
    async def _infer_business_context(
        self,
        business_intent: str,
        context: EnhancedExecutionContext,
        data_source_context: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """基于业务意图推理上下文"""
        
        inferred_contexts = {}
        
        # 业务意图关键词映射
        intent_patterns = {
            '统计': {
                'aggregation_type': {'value': 'statistical', 'confidence': 0.9, 'reasoning': '基于统计意图推理'},
                'data_processing_mode': {'value': 'aggregate', 'confidence': 0.8, 'reasoning': '统计需要聚合处理'}
            },
            '图表': {
                'output_format': {'value': 'chart', 'confidence': 0.9, 'reasoning': '基于图表意图推理'},
                'visualization_type': {'value': 'chart', 'confidence': 0.8, 'reasoning': '需要可视化输出'}
            },
            '分析': {
                'analysis_depth': {'value': 'detailed', 'confidence': 0.7, 'reasoning': '分析需要详细结果'},
                'output_format': {'value': 'analytical', 'confidence': 0.8, 'reasoning': '分析类输出格式'}
            },
            '总数': {
                'aggregation_function': {'value': 'COUNT', 'confidence': 0.95, 'reasoning': '总数表明需要计数'},
                'expected_result_type': {'value': 'single_value', 'confidence': 0.9, 'reasoning': '总数通常是单一数值'}
            }
        }
        
        # 根据业务意图匹配模式
        for pattern, contexts in intent_patterns.items():
            if pattern in business_intent:
                for key, context_data in contexts.items():
                    if key not in context.context_entries:
                        inferred_contexts[key] = context_data
        
        # 基于数据源特征推理技术上下文
        if data_source_context.get('source_type') == 'doris':
            inferred_contexts.update({
                'query_optimization_hints': {
                    'value': ['vectorization', 'partition_pruning'],
                    'confidence': 0.8,
                    'reasoning': 'Doris支持向量化和分区裁剪优化'
                },
                'expected_performance': {
                    'value': 'high_performance',
                    'confidence': 0.7,
                    'reasoning': 'Doris是高性能分析数据库'
                }
            })
        
        return inferred_contexts
    
    async def _infer_schema_context(
        self,
        data_source_context: Dict[str, Any],
        context: EnhancedExecutionContext,
        business_intent: str
    ) -> Dict[str, Dict[str, Any]]:
        """基于数据源schema推理技术上下文"""
        
        inferred_contexts = {}
        
        # 获取表结构信息
        tables = data_source_context.get('tables', {})
        if not tables:
            return inferred_contexts
        
        # 分析可用的表和字段
        available_tables = list(tables.keys())
        all_columns = []
        for table_columns in tables.values():
            all_columns.extend(table_columns)
        
        # 基于表结构推理查询上下文
        inferred_contexts.update({
            'available_tables': {
                'value': available_tables,
                'confidence': 1.0,
                'reasoning': '从数据源schema获取的可用表列表'
            },
            'available_columns': {
                'value': all_columns,
                'confidence': 1.0,
                'reasoning': '从数据源schema获取的可用字段列表'
            }
        })
        
        # 基于字段类型推理聚合函数
        numeric_columns = [col for col in all_columns if any(t in col.lower() for t in ['int', 'float', 'decimal', 'number'])]
        if numeric_columns:
            inferred_contexts['numeric_columns'] = {
                'value': numeric_columns,
                'confidence': 0.9,
                'reasoning': '识别的数值类型字段，适合聚合计算'
            }
        
        # 基于业务意图和schema匹配推荐表
        if '零售' in business_intent or 'retail' in business_intent.lower():
            retail_tables = [t for t in available_tables if 'retail' in t.lower() or 'order' in t.lower()]
            if retail_tables:
                inferred_contexts['recommended_tables'] = {
                    'value': retail_tables,
                    'confidence': 0.8,
                    'reasoning': '基于业务意图匹配的推荐表'
                }
        
        return inferred_contexts
    
    def _deep_copy_context(self, context: EnhancedExecutionContext) -> EnhancedExecutionContext:
        """深度复制上下文"""
        # 创建新的上下文实例
        new_context = EnhancedExecutionContext(
            session_id=context.session_id,
            user_id=context.user_id,
            request=context.request.copy(),
            task_id=context.task_id
        )
        
        # 复制上下文条目
        for key, entry in context.context_entries.items():
            new_context.context_entries[key] = ContextEntry(
                key=entry.key,
                value=entry.value,
                scope=entry.scope,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                metadata=entry.metadata.copy()
            )
        
        # 复制其他字段
        new_context.execution_history = context.execution_history.copy()
        new_context.capabilities = context.capabilities.copy()
        new_context.execution_metadata = context.execution_metadata.copy()
        
        return new_context


# 工厂函数
async def create_intelligent_context_manager(
    db_session=None,
    intelligence_level: str = "enhanced",
    enable_learning: bool = True
) -> IntelligentContextManager:
    """创建智能上下文管理器"""
    
    level_mapping = {
        'basic': ContextIntelligenceLevel.BASIC,
        'enhanced': ContextIntelligenceLevel.ENHANCED,
        'adaptive': ContextIntelligenceLevel.ADAPTIVE,
        'intelligent': ContextIntelligenceLevel.INTELLIGENT
    }
    
    return IntelligentContextManager(
        db_session=db_session,
        intelligence_level=level_mapping.get(intelligence_level, ContextIntelligenceLevel.ENHANCED),
        enable_learning=enable_learning
    )