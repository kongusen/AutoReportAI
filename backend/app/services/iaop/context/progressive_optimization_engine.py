"""
渐进式优化引擎 - 基于Claude Code的迭代改进理念

核心特性：
1. 基于反馈的持续优化 - 每次执行后收集反馈，用于下次优化
2. 自适应学习算法 - 根据成功率自动调整优化策略
3. 多维度质量评估 - 从多个角度评估优化效果
4. 智能回退机制 - 在优化失效时自动回退到稳定版本
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import numpy as np
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """优化策略类型"""
    CONSERVATIVE = "conservative"    # 保守策略，小步改进
    BALANCED = "balanced"           # 平衡策略，适度改进
    AGGRESSIVE = "aggressive"       # 激进策略，大胆改进
    ADAPTIVE = "adaptive"          # 自适应策略，根据历史表现调整


class FeedbackType(Enum):
    """反馈类型"""
    SUCCESS = "success"             # 成功反馈
    FAILURE = "failure"            # 失败反馈
    PARTIAL_SUCCESS = "partial"     # 部分成功
    USER_CORRECTION = "correction"  # 用户纠正
    PERFORMANCE = "performance"     # 性能反馈


@dataclass
class OptimizationFeedback:
    """优化反馈数据"""
    feedback_id: str
    execution_id: str
    feedback_type: FeedbackType
    quality_score: float
    performance_metrics: Dict[str, float]
    user_satisfaction: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None
    improvement_suggestions: List[str] = field(default_factory=list)
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class OptimizationTarget:
    """优化目标"""
    target_id: str
    target_type: str  # "sql_generation", "context_enhancement", "multi_placeholder"
    success_criteria: Dict[str, float]
    performance_targets: Dict[str, float]
    business_constraints: Dict[str, Any]
    optimization_priority: int = 5  # 1-10，数字越小优先级越高


class ProgressiveOptimizationEngine:
    """
    渐进式优化引擎
    
    基于Claude Code的对话式改进理念，通过持续的反馈循环来改进系统性能
    """
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        
        # 反馈历史存储（使用双端队列提高效率）
        self.feedback_history: deque = deque(maxlen=1000)
        self.success_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.failure_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # 优化策略配置
        self.current_strategy = OptimizationStrategy.BALANCED
        self.strategy_performance: Dict[OptimizationStrategy, float] = {
            strategy: 0.5 for strategy in OptimizationStrategy
        }
        
        # 自适应参数
        self.learning_rate = 0.1
        self.confidence_threshold = 0.8
        self.min_feedback_count = 5  # 最少反馈数量才开始优化
        
        # 性能跟踪
        self.optimization_metrics = {
            'total_optimizations': 0,
            'successful_optimizations': 0,
            'average_improvement': 0.0,
            'strategy_switches': 0
        }
        
        logger.info("渐进式优化引擎初始化完成")
    
    async def collect_feedback(
        self,
        execution_id: str,
        execution_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None,
        context_snapshot: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        收集执行反馈
        
        这是优化循环的第一步，收集各种形式的反馈数据
        """
        feedback_id = f"feedback_{execution_id}_{int(datetime.now().timestamp())}"
        
        try:
            # 1. 分析执行结果质量
            quality_analysis = await self._analyze_execution_quality(execution_result)
            
            # 2. 提取性能指标
            performance_metrics = self._extract_performance_metrics(execution_result)
            
            # 3. 确定反馈类型
            feedback_type = self._determine_feedback_type(execution_result, user_feedback)
            
            # 4. 处理用户反馈
            user_satisfaction = None
            if user_feedback:
                user_satisfaction = self._parse_user_satisfaction(user_feedback)
            
            # 5. 创建反馈对象
            feedback = OptimizationFeedback(
                feedback_id=feedback_id,
                execution_id=execution_id,
                feedback_type=feedback_type,
                quality_score=quality_analysis.get('overall_quality', 0.0),
                performance_metrics=performance_metrics,
                user_satisfaction=user_satisfaction,
                error_details=execution_result.get('error_details'),
                improvement_suggestions=quality_analysis.get('suggestions', []),
                context_snapshot=context_snapshot or {}
            )
            
            # 6. 存储反馈
            self.feedback_history.append(feedback)
            
            # 7. 分类存储成功/失败模式
            if feedback_type == FeedbackType.SUCCESS:
                target_type = self._infer_target_type(execution_result)
                self.success_patterns[target_type].append({
                    'feedback': feedback,
                    'context': context_snapshot,
                    'result': execution_result
                })
            elif feedback_type == FeedbackType.FAILURE:
                target_type = self._infer_target_type(execution_result)
                self.failure_patterns[target_type].append({
                    'feedback': feedback,
                    'context': context_snapshot,
                    'result': execution_result
                })
            
            logger.info(f"收集反馈完成: {feedback_id}, 类型: {feedback_type.value}, 质量: {quality_analysis.get('overall_quality', 0.0):.2f}")
            
            # 8. 触发自适应策略调整
            await self._adapt_optimization_strategy()
            
            return feedback_id
            
        except Exception as e:
            logger.error(f"收集反馈失败: {e}")
            return ""
    
    async def generate_optimization_recommendations(
        self,
        target: OptimizationTarget,
        current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成优化建议
        
        基于历史反馈和当前上下文，生成具体的优化建议
        """
        logger.info(f"生成优化建议，目标: {target.target_id}")
        
        try:
            recommendations = {
                'target_id': target.target_id,
                'optimization_strategy': self.current_strategy.value,
                'recommendations': [],
                'confidence_score': 0.0,
                'expected_improvement': 0.0,
                'risk_assessment': 'low'
            }
            
            # 1. 分析历史成功模式
            success_insights = await self._analyze_success_patterns(
                target.target_type, current_context
            )
            
            # 2. 分析失败模式以避免重复错误
            failure_insights = await self._analyze_failure_patterns(
                target.target_type, current_context
            )
            
            # 3. 基于当前策略生成具体建议
            strategy_recommendations = await self._generate_strategy_specific_recommendations(
                target, current_context, success_insights, failure_insights
            )
            
            recommendations['recommendations'].extend(strategy_recommendations)
            
            # 4. 评估建议的置信度和预期改进
            confidence_score = self._calculate_recommendation_confidence(
                strategy_recommendations, success_insights, failure_insights
            )
            
            expected_improvement = self._estimate_improvement_potential(
                strategy_recommendations, target, success_insights
            )
            
            recommendations.update({
                'confidence_score': confidence_score,
                'expected_improvement': expected_improvement,
                'risk_assessment': self._assess_optimization_risk(strategy_recommendations)
            })
            
            logger.info(f"优化建议生成完成，包含 {len(strategy_recommendations)} 项建议，置信度: {confidence_score:.2f}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            return {
                'target_id': target.target_id,
                'recommendations': [],
                'error': str(e)
            }
    
    async def apply_optimization_incrementally(
        self,
        recommendations: Dict[str, Any],
        current_context: Dict[str, Any],
        safety_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        渐进式应用优化建议
        
        不是一次性应用所有建议，而是按风险级别和重要性逐步应用
        """
        logger.info("开始渐进式优化应用")
        
        try:
            optimization_result = {
                'success': True,
                'applied_optimizations': [],
                'skipped_optimizations': [],
                'performance_impact': {},
                'rollback_plan': []
            }
            
            # 1. 按风险级别和重要性排序建议
            sorted_recommendations = self._sort_recommendations_by_risk_and_impact(
                recommendations.get('recommendations', [])
            )
            
            # 2. 创建优化前的备份
            backup_context = self._create_context_backup(current_context)
            optimization_result['rollback_plan'].append({
                'type': 'context_backup',
                'data': backup_context,
                'timestamp': datetime.now()
            })
            
            # 3. 逐步应用优化
            for i, recommendation in enumerate(sorted_recommendations):
                risk_level = recommendation.get('risk_level', 'medium')
                confidence = recommendation.get('confidence', 0.5)
                
                # 安全检查
                if confidence < safety_threshold:
                    optimization_result['skipped_optimizations'].append({
                        'recommendation': recommendation,
                        'reason': f'置信度 {confidence:.2f} 低于安全阈值 {safety_threshold}'
                    })
                    continue
                
                # 应用优化
                application_result = await self._apply_single_optimization(
                    recommendation, current_context
                )
                
                if application_result.get('success'):
                    optimization_result['applied_optimizations'].append({
                        'recommendation': recommendation,
                        'result': application_result,
                        'applied_at': datetime.now()
                    })
                    
                    # 更新上下文
                    current_context.update(application_result.get('context_updates', {}))
                    
                    # 记录性能影响
                    performance_impact = application_result.get('performance_impact', {})
                    optimization_result['performance_impact'][f'step_{i+1}'] = performance_impact
                    
                else:
                    logger.warning(f"优化应用失败: {application_result.get('error')}")
                    optimization_result['skipped_optimizations'].append({
                        'recommendation': recommendation,
                        'reason': f"应用失败: {application_result.get('error')}"
                    })
                
                # 如果是高风险优化，应用后立即验证
                if risk_level == 'high':
                    verification_result = await self._verify_optimization_safety(
                        current_context, backup_context
                    )
                    
                    if not verification_result.get('safe'):
                        logger.warning("检测到高风险优化的负面影响，执行回退")
                        await self._rollback_optimization(
                            backup_context, current_context
                        )
                        optimization_result['success'] = False
                        optimization_result['rollback_executed'] = True
                        break
            
            # 4. 生成优化总结
            optimization_summary = self._generate_optimization_summary(optimization_result)
            optimization_result['summary'] = optimization_summary
            
            logger.info(f"渐进式优化完成，应用了 {len(optimization_result['applied_optimizations'])} 项优化")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"渐进式优化应用失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'applied_optimizations': [],
                'rollback_executed': True
            }
    
    async def learn_from_feedback_batch(
        self,
        feedback_batch: List[OptimizationFeedback]
    ) -> Dict[str, Any]:
        """
        从批量反馈中学习
        
        定期分析累积的反馈，提取更深层的优化模式
        """
        logger.info(f"从 {len(feedback_batch)} 个反馈中学习")
        
        try:
            learning_results = {
                'patterns_discovered': 0,
                'strategy_adjustments': [],
                'confidence_updates': {},
                'new_optimization_rules': []
            }
            
            # 1. 分析成功模式
            success_feedbacks = [f for f in feedback_batch if f.feedback_type == FeedbackType.SUCCESS]
            if success_feedbacks:
                success_patterns = await self._extract_success_patterns_from_batch(success_feedbacks)
                learning_results['patterns_discovered'] += len(success_patterns)
                
                # 更新成功模式库
                for pattern in success_patterns:
                    target_type = pattern.get('target_type')
                    self.success_patterns[target_type].append(pattern)
            
            # 2. 分析失败模式
            failure_feedbacks = [f for f in feedback_batch if f.feedback_type == FeedbackType.FAILURE]
            if failure_feedbacks:
                failure_patterns = await self._extract_failure_patterns_from_batch(failure_feedbacks)
                
                # 生成规避规则
                avoidance_rules = self._generate_failure_avoidance_rules(failure_patterns)
                learning_results['new_optimization_rules'].extend(avoidance_rules)
            
            # 3. 评估当前策略效果
            strategy_performance = self._evaluate_strategy_performance(feedback_batch)
            
            # 4. 调整优化策略
            if len(feedback_batch) >= self.min_feedback_count:
                strategy_adjustment = await self._adjust_optimization_strategy(strategy_performance)
                if strategy_adjustment:
                    learning_results['strategy_adjustments'].append(strategy_adjustment)
            
            # 5. 更新置信度模型
            confidence_updates = self._update_confidence_models(feedback_batch)
            learning_results['confidence_updates'] = confidence_updates
            
            logger.info(f"批量学习完成，发现 {learning_results['patterns_discovered']} 个新模式")
            
            return learning_results
            
        except Exception as e:
            logger.error(f"批量学习失败: {e}")
            return {
                'patterns_discovered': 0,
                'error': str(e)
            }
    
    async def _analyze_execution_quality(
        self,
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析执行质量"""
        
        quality_metrics = {
            'accuracy': 0.0,
            'completeness': 0.0,
            'efficiency': 0.0,
            'user_experience': 0.0
        }
        
        # 1. 准确性分析
        if execution_result.get('success'):
            quality_metrics['accuracy'] = min(1.0, execution_result.get('confidence_score', 0.5) * 1.2)
        else:
            quality_metrics['accuracy'] = 0.0
        
        # 2. 完整性分析
        expected_outputs = execution_result.get('expected_outputs', [])
        actual_outputs = execution_result.get('actual_outputs', [])
        if expected_outputs:
            completeness = len(actual_outputs) / len(expected_outputs)
            quality_metrics['completeness'] = min(1.0, completeness)
        else:
            quality_metrics['completeness'] = 1.0 if execution_result.get('success') else 0.0
        
        # 3. 效率分析
        execution_time = execution_result.get('processing_time_ms', 0)
        if execution_time > 0:
            # 基于执行时间计算效率分数（假设5秒为基准）
            efficiency = max(0, 1.0 - (execution_time / 5000))
            quality_metrics['efficiency'] = efficiency
        else:
            quality_metrics['efficiency'] = 0.5
        
        # 4. 用户体验分析
        error_count = len(execution_result.get('errors', []))
        warning_count = len(execution_result.get('warnings', []))
        ux_score = max(0, 1.0 - (error_count * 0.3 + warning_count * 0.1))
        quality_metrics['user_experience'] = ux_score
        
        # 计算综合质量分数
        weights = {'accuracy': 0.4, 'completeness': 0.3, 'efficiency': 0.2, 'user_experience': 0.1}
        overall_quality = sum(quality_metrics[metric] * weight for metric, weight in weights.items())
        
        return {
            'overall_quality': overall_quality,
            'quality_metrics': quality_metrics,
            'suggestions': self._generate_quality_suggestions(quality_metrics, execution_result)
        }
    
    def _extract_performance_metrics(self, execution_result: Dict[str, Any]) -> Dict[str, float]:
        """提取性能指标"""
        return {
            'execution_time_ms': execution_result.get('processing_time_ms', 0.0),
            'memory_usage_mb': execution_result.get('memory_usage_mb', 0.0),
            'cpu_usage_percent': execution_result.get('cpu_usage_percent', 0.0),
            'success_rate': 1.0 if execution_result.get('success') else 0.0,
            'error_rate': 1.0 if execution_result.get('error') else 0.0
        }
    
    def _determine_feedback_type(
        self,
        execution_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> FeedbackType:
        """确定反馈类型"""
        
        if user_feedback:
            if user_feedback.get('corrected'):
                return FeedbackType.USER_CORRECTION
            elif user_feedback.get('satisfaction_score', 0) >= 8:
                return FeedbackType.SUCCESS
        
        if execution_result.get('success'):
            confidence = execution_result.get('confidence_score', 0.5)
            if confidence >= 0.8:
                return FeedbackType.SUCCESS
            else:
                return FeedbackType.PARTIAL_SUCCESS
        else:
            return FeedbackType.FAILURE
    
    async def _adapt_optimization_strategy(self):
        """自适应调整优化策略"""
        
        if len(self.feedback_history) < self.min_feedback_count:
            return
        
        # 计算最近反馈的成功率
        recent_feedbacks = list(self.feedback_history)[-self.min_feedback_count:]
        success_count = sum(1 for f in recent_feedbacks if f.feedback_type == FeedbackType.SUCCESS)
        success_rate = success_count / len(recent_feedbacks)
        
        # 更新当前策略的性能
        self.strategy_performance[self.current_strategy] = (
            self.strategy_performance[self.current_strategy] * (1 - self.learning_rate) +
            success_rate * self.learning_rate
        )
        
        # 如果当前策略表现不佳，考虑切换
        if success_rate < 0.6:
            best_strategy = max(self.strategy_performance.items(), key=lambda x: x[1])
            if best_strategy[0] != self.current_strategy and best_strategy[1] > success_rate + 0.1:
                logger.info(f"切换优化策略：{self.current_strategy.value} -> {best_strategy[0].value}")
                self.current_strategy = best_strategy[0]
                self.optimization_metrics['strategy_switches'] += 1


# 工厂函数
def create_progressive_optimization_engine(db_session=None) -> ProgressiveOptimizationEngine:
    """创建渐进式优化引擎"""
    return ProgressiveOptimizationEngine(db_session=db_session)