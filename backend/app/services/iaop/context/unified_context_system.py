"""
统一智能上下文系统 - 完全替换原有上下文管理

这个系统整合了：
1. 智能上下文管理器
2. 渐进式优化引擎 
3. 学习增强系统

提供统一的接口，替换原有的分散的上下文管理组件
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from .execution_context import EnhancedExecutionContext, ContextScope, ContextEntry
from .intelligent_context_manager import (
    IntelligentContextManager, 
    ContextIntelligenceLevel,
    ContextOptimizationResult
)
from .progressive_optimization_engine import (
    ProgressiveOptimizationEngine,
    OptimizationTarget,
    OptimizationStrategy,
    OptimizationFeedback,
    FeedbackType
)
from .learning_enhanced_context import (
    LearningEnhancedContextSystem,
    LearningMode,
    ContextKnowledge
)

logger = logging.getLogger(__name__)


class SystemIntegrationMode(Enum):
    """系统集成模式"""
    BASIC = "basic"              # 基础模式，仅使用智能上下文管理
    ENHANCED = "enhanced"        # 增强模式，添加优化引擎
    INTELLIGENT = "intelligent"   # 智能模式，全功能集成
    LEARNING = "learning"        # 学习模式，启用学习系统


@dataclass
class UnifiedContextResult:
    """统一上下文系统处理结果"""
    success: bool
    context: EnhancedExecutionContext
    optimization_applied: bool
    learning_applied: bool
    confidence_score: float
    processing_details: Dict[str, Any]
    recommendations: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class UnifiedContextSystem:
    """
    统一智能上下文系统
    
    完全替换原有的上下文管理，提供：
    1. 统一的上下文管理接口
    2. 智能的上下文推理和优化
    3. 基于学习的持续改进
    4. 渐进式的系统优化
    """
    
    def __init__(
        self,
        db_session=None,
        integration_mode: SystemIntegrationMode = SystemIntegrationMode.INTELLIGENT,
        enable_performance_monitoring: bool = True
    ):
        self.db_session = db_session
        self.integration_mode = integration_mode
        self.enable_performance_monitoring = enable_performance_monitoring
        
        # 初始化核心组件
        self.context_manager = IntelligentContextManager(
            db_session=db_session,
            intelligence_level=self._get_intelligence_level(integration_mode),
            enable_learning=integration_mode in [SystemIntegrationMode.INTELLIGENT, SystemIntegrationMode.LEARNING]
        )
        
        if integration_mode in [SystemIntegrationMode.ENHANCED, SystemIntegrationMode.INTELLIGENT, SystemIntegrationMode.LEARNING]:
            self.optimization_engine = ProgressiveOptimizationEngine(db_session=db_session)
        else:
            self.optimization_engine = None
            
        if integration_mode in [SystemIntegrationMode.INTELLIGENT, SystemIntegrationMode.LEARNING]:
            self.learning_system = LearningEnhancedContextSystem(
                db_session=db_session,
                learning_mode=LearningMode.ACTIVE if integration_mode == SystemIntegrationMode.LEARNING else LearningMode.PASSIVE
            )
        else:
            self.learning_system = None
            
        # 性能监控
        self.performance_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'optimization_applications': 0,
            'learning_applications': 0,
            'average_processing_time': 0.0,
            'average_confidence_score': 0.0
        }
        
        logger.info(f"统一上下文系统初始化完成，集成模式: {integration_mode.value}")
    
    async def create_execution_context(
        self,
        session_id: str,
        user_id: str,
        request_data: Dict[str, Any],
        business_intent: Optional[str] = None,
        data_source_context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None
    ) -> UnifiedContextResult:
        """
        创建执行上下文
        
        替换原有的上下文创建逻辑，提供智能化的上下文管理
        """
        start_time = datetime.now()
        logger.info(f"创建统一执行上下文，会话: {session_id}")
        
        try:
            self.performance_metrics['total_requests'] += 1
            
            # 1. 创建基础执行上下文
            context = EnhancedExecutionContext(
                session_id=session_id,
                user_id=user_id,
                request=request_data.copy(),
                task_id=task_id
            )
            
            # 设置基础上下文信息
            context.set_context('business_intent', business_intent or '', ContextScope.REQUEST)
            context.set_context('data_source_context', data_source_context or {}, ContextScope.REQUEST)
            context.set_context('creation_time', datetime.now().isoformat(), ContextScope.SESSION)
            context.set_context('integration_mode', self.integration_mode.value, ContextScope.GLOBAL)
            
            processing_details = {
                'context_creation_time': (datetime.now() - start_time).total_seconds() * 1000,
                'intelligence_enhancements': [],
                'optimization_applied': False,
                'learning_applied': False
            }
            
            # 2. 智能上下文增强
            if business_intent and data_source_context:
                enhancement_result = await self.context_manager.enhance_context_with_intelligence(
                    context, business_intent, data_source_context
                )
                
                if enhancement_result.get('success'):
                    processing_details['intelligence_enhancements'] = enhancement_result.get('enhancement_details', {}).get('enhancements_applied', [])
                    logger.info(f"智能上下文增强完成，增强项: {len(processing_details['intelligence_enhancements'])}")
            
            # 3. 上下文优化（如果启用）
            optimization_applied = False
            if self.optimization_engine and business_intent:
                optimization_result = await self.context_manager.optimize_execution_context(
                    context, business_intent or 'general_analysis'
                )
                
                if optimization_result.success:
                    context = optimization_result.optimized_context
                    optimization_applied = True
                    processing_details['optimization_applied'] = True
                    processing_details['optimization_details'] = {
                        'iterations': optimization_result.optimization_iterations,
                        'improvements': optimization_result.improvements_made,
                        'confidence_score': optimization_result.confidence_score
                    }
                    logger.info(f"上下文优化完成，迭代次数: {optimization_result.optimization_iterations}")
            
            # 4. 学习系统记录（如果启用）
            learning_applied = False
            if self.learning_system:
                session_id_learning = await self.learning_system.start_learning_session({
                    'session_id': session_id,
                    'user_id': user_id,
                    'business_intent': business_intent
                })
                
                context.set_context('learning_session_id', session_id_learning, ContextScope.SESSION)
                learning_applied = True
                processing_details['learning_applied'] = True
                logger.info(f"学习会话启动: {session_id_learning}")
            
            # 5. 计算总体置信度分数
            confidence_score = self._calculate_overall_confidence(context, optimization_applied, learning_applied)
            context.set_context('confidence_score', confidence_score, ContextScope.REQUEST)
            
            # 6. 更新性能指标
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            processing_details['total_processing_time'] = processing_time
            
            if self.enable_performance_monitoring:
                await self._update_performance_metrics(True, confidence_score, processing_time)
            
            # 7. 生成使用建议
            recommendations = self._generate_usage_recommendations(context, processing_details)
            
            logger.info(f"统一上下文创建成功，置信度: {confidence_score:.2f}")
            
            return UnifiedContextResult(
                success=True,
                context=context,
                optimization_applied=optimization_applied,
                learning_applied=learning_applied,
                confidence_score=confidence_score,
                processing_details=processing_details,
                recommendations=recommendations
            )
            
        except Exception as e:
            error_message = f"统一上下文创建失败: {e}"
            logger.error(error_message)
            
            if self.enable_performance_monitoring:
                await self._update_performance_metrics(False, 0.0, (datetime.now() - start_time).total_seconds() * 1000)
            
            return UnifiedContextResult(
                success=False,
                context=context if 'context' in locals() else None,
                optimization_applied=False,
                learning_applied=False,
                confidence_score=0.0,
                processing_details={'error': str(e)},
                error_message=error_message
            )
    
    async def manage_multi_placeholder_context(
        self,
        placeholders: List[Dict[str, Any]],
        global_context: Dict[str, Any],
        execution_mode: str = "batch"
    ) -> UnifiedContextResult:
        """
        管理多占位符上下文
        
        替换原有的多占位符处理逻辑
        """
        start_time = datetime.now()
        logger.info(f"管理多占位符统一上下文，数量: {len(placeholders)}")
        
        try:
            # 使用智能上下文管理器处理多占位符
            management_result = await self.context_manager.manage_multi_placeholder_context(
                placeholders, global_context, execution_mode
            )
            
            if not management_result.get('success'):
                return UnifiedContextResult(
                    success=False,
                    context=None,
                    optimization_applied=False,
                    learning_applied=False,
                    confidence_score=0.0,
                    processing_details=management_result,
                    error_message=management_result.get('error', '多占位符上下文管理失败')
                )
            
            # 应用优化和学习
            processing_details = {
                'placeholder_count': len(placeholders),
                'execution_mode': execution_mode,
                'dependency_analysis': management_result.get('dependency_analysis', {}),
                'execution_order': management_result.get('execution_order', []),
                'processing_time': (datetime.now() - start_time).total_seconds() * 1000
            }
            
            # 计算整体置信度
            confidence_score = self._calculate_multi_placeholder_confidence(management_result)
            
            logger.info(f"多占位符上下文管理完成，置信度: {confidence_score:.2f}")
            
            return UnifiedContextResult(
                success=True,
                context=management_result.get('master_context'),
                optimization_applied=management_result.get('context_optimization_applied', False),
                learning_applied=self.learning_system is not None,
                confidence_score=confidence_score,
                processing_details=processing_details,
                recommendations=self._generate_multi_placeholder_recommendations(management_result)
            )
            
        except Exception as e:
            error_message = f"多占位符上下文管理失败: {e}"
            logger.error(error_message)
            
            return UnifiedContextResult(
                success=False,
                context=None,
                optimization_applied=False,
                learning_applied=False,
                confidence_score=0.0,
                processing_details={'error': str(e)},
                error_message=error_message
            )
    
    async def record_execution_feedback(
        self,
        context: EnhancedExecutionContext,
        execution_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None,
        business_domain: str = "general"
    ) -> Dict[str, Any]:
        """
        记录执行反馈并触发学习和优化
        
        替换原有的反馈处理逻辑
        """
        logger.info("记录执行反馈到统一上下文系统")
        
        try:
            feedback_results = {
                'optimization_feedback_recorded': False,
                'learning_feedback_recorded': False,
                'system_improvements': []
            }
            
            # 1. 记录到优化引擎
            if self.optimization_engine:
                feedback_id = await self.optimization_engine.collect_feedback(
                    execution_id=context.session_id,
                    execution_result=execution_result,
                    user_feedback=user_feedback,
                    context_snapshot=self._create_context_snapshot(context)
                )
                
                if feedback_id:
                    feedback_results['optimization_feedback_recorded'] = True
                    feedback_results['optimization_feedback_id'] = feedback_id
                    logger.info(f"优化引擎反馈记录: {feedback_id}")
            
            # 2. 记录到学习系统
            if self.learning_system:
                if execution_result.get('success', False):
                    learning_result = await self.learning_system.learn_from_execution_success(
                        context_snapshot := self._create_context_snapshot(context),
                        execution_result,
                        business_domain
                    )
                else:
                    learning_result = await self.learning_system.learn_from_execution_failure(
                        context_snapshot := self._create_context_snapshot(context),
                        execution_result,
                        business_domain
                    )
                
                if learning_result.get('knowledge_items_extracted', 0) > 0:
                    feedback_results['learning_feedback_recorded'] = True
                    feedback_results['learning_results'] = learning_result
                    logger.info(f"学习系统反馈记录，提取知识项: {learning_result.get('knowledge_items_extracted', 0)}")
            
            # 3. 生成系统改进建议
            if self.optimization_engine and len(self.optimization_engine.feedback_history) >= 5:
                recent_feedbacks = list(self.optimization_engine.feedback_history)[-5:]
                batch_learning = await self.optimization_engine.learn_from_feedback_batch(recent_feedbacks)
                feedback_results['system_improvements'] = batch_learning.get('strategy_adjustments', [])
            
            return feedback_results
            
        except Exception as e:
            logger.error(f"执行反馈记录失败: {e}")
            return {
                'optimization_feedback_recorded': False,
                'learning_feedback_recorded': False,
                'error': str(e)
            }
    
    async def get_system_performance_metrics(self) -> Dict[str, Any]:
        """获取系统性能指标"""
        
        metrics = self.performance_metrics.copy()
        
        # 添加组件特定指标
        if self.optimization_engine:
            metrics['optimization_engine'] = self.optimization_engine.optimization_metrics
        
        if self.learning_system:
            metrics['learning_system'] = self.learning_system.learning_stats
        
        # 计算成功率
        if metrics['total_requests'] > 0:
            metrics['success_rate'] = metrics['successful_requests'] / metrics['total_requests']
        else:
            metrics['success_rate'] = 0.0
        
        return metrics
    
    def _get_intelligence_level(self, integration_mode: SystemIntegrationMode) -> ContextIntelligenceLevel:
        """根据集成模式获取智能级别"""
        mapping = {
            SystemIntegrationMode.BASIC: ContextIntelligenceLevel.BASIC,
            SystemIntegrationMode.ENHANCED: ContextIntelligenceLevel.ENHANCED,
            SystemIntegrationMode.INTELLIGENT: ContextIntelligenceLevel.ADAPTIVE,
            SystemIntegrationMode.LEARNING: ContextIntelligenceLevel.INTELLIGENT
        }
        return mapping.get(integration_mode, ContextIntelligenceLevel.ENHANCED)
    
    def _calculate_overall_confidence(
        self, 
        context: EnhancedExecutionContext, 
        optimization_applied: bool, 
        learning_applied: bool
    ) -> float:
        """计算总体置信度分数"""
        base_confidence = 0.5
        
        # 基于上下文完整性
        context_completeness = len(context.context_entries) / 10.0  # 假设10个是完整的上下文项数量
        context_completeness = min(1.0, context_completeness)
        
        # 优化加成
        optimization_bonus = 0.2 if optimization_applied else 0.0
        
        # 学习加成
        learning_bonus = 0.1 if learning_applied else 0.0
        
        # 业务意图清晰度
        business_intent = context.get_context('business_intent', '')
        intent_clarity = min(1.0, len(business_intent) / 20.0) * 0.2  # 基于业务意图长度评估清晰度
        
        total_confidence = base_confidence + context_completeness * 0.3 + optimization_bonus + learning_bonus + intent_clarity
        
        return min(1.0, total_confidence)
    
    def _calculate_multi_placeholder_confidence(self, management_result: Dict[str, Any]) -> float:
        """计算多占位符处理的置信度"""
        base_confidence = 0.6
        
        # 依赖分析质量
        dependency_analysis = management_result.get('dependency_analysis', {})
        dependency_quality = 0.2 if dependency_analysis else 0.0
        
        # 上下文优化应用
        optimization_applied = management_result.get('context_optimization_applied', False)
        optimization_bonus = 0.2 if optimization_applied else 0.0
        
        # 占位符数量因子（过多的占位符可能降低置信度）
        placeholder_count = management_result.get('total_placeholders', 1)
        complexity_factor = max(0.0, 1.0 - (placeholder_count - 3) * 0.1) if placeholder_count > 3 else 1.0
        
        total_confidence = (base_confidence + dependency_quality + optimization_bonus) * complexity_factor
        
        return min(1.0, total_confidence)
    
    def _create_context_snapshot(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """创建上下文快照"""
        return {
            'session_id': context.session_id,
            'user_id': context.user_id,
            'context_entries': {k: v.value for k, v in context.context_entries.items()},
            'context_metadata': {k: v.metadata for k, v in context.context_entries.items()},
            'execution_history_count': len(context.execution_history),
            'creation_time': context.created_at.isoformat(),
            'capabilities': context.capabilities
        }
    
    def _generate_usage_recommendations(
        self, 
        context: EnhancedExecutionContext, 
        processing_details: Dict[str, Any]
    ) -> List[str]:
        """生成使用建议"""
        recommendations = []
        
        # 基于上下文完整性的建议
        context_count = len(context.context_entries)
        if context_count < 5:
            recommendations.append("考虑提供更多的业务上下文信息以提高处理质量")
        
        # 基于优化应用的建议
        if not processing_details.get('optimization_applied'):
            recommendations.append("可以启用上下文优化以获得更好的处理效果")
        
        # 基于置信度的建议
        confidence = context.get_context('confidence_score', 0.0)
        if confidence < 0.7:
            recommendations.append("建议提供更清晰的业务意图描述以提升处理置信度")
        
        return recommendations
    
    def _generate_multi_placeholder_recommendations(self, management_result: Dict[str, Any]) -> List[str]:
        """生成多占位符处理建议"""
        recommendations = []
        
        placeholder_count = management_result.get('total_placeholders', 0)
        if placeholder_count > 5:
            recommendations.append("建议将复杂的多占位符任务拆分为较小的批次处理")
        
        dependency_analysis = management_result.get('dependency_analysis', {})
        if dependency_analysis.get('complex_dependencies'):
            recommendations.append("检测到复杂的占位符依赖关系，建议优化占位符设计")
        
        return recommendations
    
    async def _update_performance_metrics(self, success: bool, confidence_score: float, processing_time: float):
        """更新性能指标"""
        if success:
            self.performance_metrics['successful_requests'] += 1
        
        # 更新平均置信度
        total_requests = self.performance_metrics['total_requests']
        current_avg_confidence = self.performance_metrics['average_confidence_score']
        self.performance_metrics['average_confidence_score'] = (
            (current_avg_confidence * (total_requests - 1) + confidence_score) / total_requests
        )
        
        # 更新平均处理时间
        current_avg_time = self.performance_metrics['average_processing_time']
        self.performance_metrics['average_processing_time'] = (
            (current_avg_time * (total_requests - 1) + processing_time) / total_requests
        )


# 工厂函数
def create_unified_context_system(
    db_session=None,
    integration_mode: str = "intelligent",
    enable_performance_monitoring: bool = True
) -> UnifiedContextSystem:
    """创建统一上下文系统"""
    
    mode_mapping = {
        'basic': SystemIntegrationMode.BASIC,
        'enhanced': SystemIntegrationMode.ENHANCED,
        'intelligent': SystemIntegrationMode.INTELLIGENT,
        'learning': SystemIntegrationMode.LEARNING
    }
    
    return UnifiedContextSystem(
        db_session=db_session,
        integration_mode=mode_mapping.get(integration_mode, SystemIntegrationMode.INTELLIGENT),
        enable_performance_monitoring=enable_performance_monitoring
    )