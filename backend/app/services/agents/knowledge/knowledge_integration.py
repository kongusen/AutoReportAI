"""
知识集成模块

将知识共享机制集成到各个增强Agent中，提供：
- 智能知识推荐
- 自动学习反馈
- 跨Agent协作优化
- 用户行为适应

Features:
- 无缝集成到现有Agent
- 实时学习和适应
- 智能推荐系统
- 性能优化建议
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from .knowledge_base import KnowledgeShareManager, KnowledgeItem, BestPractice
from ..base import AgentResult, AgentError


@dataclass
class KnowledgeContext:
    """知识上下文"""
    agent_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    task_type: str = ""
    data_characteristics: Dict[str, Any] = None
    performance_metrics: Dict[str, float] = None
    user_preferences: Dict[str, Any] = None


class AgentKnowledgeIntegrator:
    """Agent知识集成器"""
    
    def __init__(self, knowledge_manager: KnowledgeShareManager = None):
        self.knowledge_manager = knowledge_manager or KnowledgeShareManager()
        self.integration_stats = {
            'recommendations_applied': 0,
            'knowledge_shared': 0,
            'patterns_learned': 0,
            'performance_improvements': 0
        }
    
    async def get_pre_execution_recommendations(
        self,
        context: KnowledgeContext
    ) -> List[Dict[str, Any]]:
        """获取执行前推荐"""
        try:
            # 构建推荐上下文
            recommendation_context = {
                'agent_id': context.agent_id,
                'task_type': context.task_type,
                'user_id': context.user_id,
                'session_id': context.session_id
            }
            
            if context.data_characteristics:
                recommendation_context.update(context.data_characteristics)
            
            # 获取最佳实践推荐
            best_practices = await self.knowledge_manager.get_recommendations(
                context.agent_id,
                recommendation_context,
                "best_practice"
            )
            
            # 获取性能优化建议
            performance_tips = await self.knowledge_manager.get_recommendations(
                context.agent_id,
                recommendation_context,
                "performance_tip"
            )
            
            # 获取用户偏好建议
            preference_suggestions = []
            if context.user_id:
                user_insights = await self.knowledge_manager.get_user_insights(context.user_id)
                preference_suggestions = user_insights.get('recommendations', [])
            
            # 合并并排序推荐
            all_recommendations = []
            
            for bp in best_practices:
                all_recommendations.append({
                    'type': 'best_practice',
                    'priority': 'high',
                    'confidence': bp['confidence'],
                    'recommendation': bp['content'],
                    'source': bp['source']
                })
            
            for pt in performance_tips:
                all_recommendations.append({
                    'type': 'performance',
                    'priority': 'medium',
                    'confidence': pt['confidence'],
                    'recommendation': pt['content'],
                    'source': pt['source']
                })
            
            for ps in preference_suggestions:
                all_recommendations.append({
                    'type': 'user_preference',
                    'priority': 'low',
                    'confidence': ps['confidence'],
                    'recommendation': ps['content'],
                    'source': ps['source']
                })
            
            # 按置信度和优先级排序
            priority_order = {'high': 3, 'medium': 2, 'low': 1}
            all_recommendations.sort(
                key=lambda x: (priority_order.get(x['priority'], 0), x['confidence']),
                reverse=True
            )
            
            return all_recommendations[:5]  # 返回前5个推荐
        
        except Exception as e:
            # 推荐失败不应影响主流程
            return []
    
    async def record_execution_result(
        self,
        context: KnowledgeContext,
        result: AgentResult,
        applied_recommendations: List[str] = None
    ):
        """记录执行结果"""
        try:
            # 记录Agent执行结果
            execution_data = {
                'agent_id': context.agent_id,
                'task_type': context.task_type,
                'success': result.success,
                'execution_time': result.metadata.get('execution_time', 0),
                'data_size': result.metadata.get('data_size', 0),
                'timestamp': datetime.now().timestamp()
            }
            
            # 如果有性能指标，记录性能知识
            if context.performance_metrics:
                await self._record_performance_knowledge(context, execution_data)
            
            # 记录用户交互模式
            if context.user_id and result.success:
                await self._record_user_interaction(context, result)
            
            # 更新推荐使用情况
            if applied_recommendations:
                for rec_id in applied_recommendations:
                    await self.knowledge_manager.update_knowledge_usage(rec_id, result.success)
                    if result.success:
                        self.integration_stats['recommendations_applied'] += 1
            
            # 如果执行失败，记录失败模式
            if not result.success:
                await self._record_failure_pattern(context, result)
        
        except Exception as e:
            # 记录失败不应影响主流程
            pass
    
    async def _record_performance_knowledge(
        self,
        context: KnowledgeContext,
        execution_data: Dict[str, Any]
    ):
        """记录性能知识"""
        try:
            performance_content = {
                'task_type': context.task_type,
                'performance_metrics': context.performance_metrics,
                'execution_time': execution_data['execution_time'],
                'data_characteristics': context.data_characteristics or {},
                'success': execution_data['success']
            }
            
            # 如果性能表现优秀，分享为最佳实践
            if (execution_data['success'] and 
                context.performance_metrics and
                context.performance_metrics.get('efficiency', 0) > 0.8):
                
                await self.knowledge_manager.share_knowledge(
                    context.agent_id,
                    'performance_optimization',
                    performance_content,
                    tags=[context.task_type, 'high_performance', context.agent_id],
                    confidence=0.9
                )
                self.integration_stats['knowledge_shared'] += 1
        
        except Exception:
            pass
    
    async def _record_user_interaction(
        self,
        context: KnowledgeContext,
        result: AgentResult
    ):
        """记录用户交互"""
        try:
            interaction_data = {
                'type': 'agent_execution',
                'agent_id': context.agent_id,
                'task_type': context.task_type,
                'success': result.success,
                'user_preferences': context.user_preferences or {},
                'result_metadata': result.metadata
            }
            
            await self.knowledge_manager.learn_from_interactions(
                context.user_id,
                [interaction_data]
            )
            self.integration_stats['patterns_learned'] += 1
        
        except Exception:
            pass
    
    async def _record_failure_pattern(
        self,
        context: KnowledgeContext,
        result: AgentResult
    ):
        """记录失败模式"""
        try:
            failure_content = {
                'task_type': context.task_type,
                'error_message': result.error_message,
                'data_characteristics': context.data_characteristics or {},
                'context': context.user_preferences or {}
            }
            
            await self.knowledge_manager.share_knowledge(
                context.agent_id,
                'failure_pattern',
                failure_content,
                tags=[context.task_type, 'failure', context.agent_id],
                confidence=0.7
            )
        
        except Exception:
            pass
    
    async def get_collaborative_insights(
        self,
        agent_ids: List[str],
        time_window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """获取协作洞察"""
        try:
            # 这里可以分析多个Agent的协作模式
            # 目前返回基本信息
            return [
                {
                    'type': 'collaboration_opportunity',
                    'agents': agent_ids,
                    'suggestion': f'检测到 {len(agent_ids)} 个Agent可能存在协作优化机会',
                    'confidence': 0.6
                }
            ]
        
        except Exception:
            return []
    
    async def optimize_agent_parameters(
        self,
        context: KnowledgeContext,
        current_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """优化Agent参数"""
        try:
            # 获取相关的性能优化知识
            optimization_context = {
                'agent_id': context.agent_id,
                'task_type': context.task_type,
                'current_params': list(current_parameters.keys())
            }
            
            optimizations = await self.knowledge_manager.get_recommendations(
                context.agent_id,
                optimization_context,
                'parameter_optimization'
            )
            
            optimized_params = current_parameters.copy()
            
            # 应用优化建议
            for opt in optimizations:
                if opt['confidence'] > 0.8:
                    param_suggestions = opt['content'].get('parameter_adjustments', {})
                    for param, value in param_suggestions.items():
                        if param in optimized_params:
                            optimized_params[param] = value
                            self.integration_stats['performance_improvements'] += 1
            
            return optimized_params
        
        except Exception:
            return current_parameters
    
    async def get_integration_statistics(self) -> Dict[str, Any]:
        """获取集成统计"""
        kb_stats = await self.knowledge_manager.get_knowledge_statistics()
        
        return {
            'knowledge_integration': self.integration_stats,
            'knowledge_base': kb_stats,
            'total_integrations': sum(self.integration_stats.values())
        }


class KnowledgeEnhancedAgent:
    """知识增强Agent基类"""
    
    def __init__(self, agent_id: str, knowledge_manager: KnowledgeShareManager = None):
        self.agent_id = agent_id
        self.knowledge_integrator = AgentKnowledgeIntegrator(knowledge_manager)
        self.knowledge_enabled = True
    
    async def execute_with_knowledge(
        self,
        execution_func,
        context: KnowledgeContext,
        *args,
        **kwargs
    ) -> AgentResult:
        """带知识增强的执行"""
        if not self.knowledge_enabled:
            return await execution_func(*args, **kwargs)
        
        try:
            # 1. 获取执行前推荐
            recommendations = await self.knowledge_integrator.get_pre_execution_recommendations(context)
            applied_recommendations = []
            
            # 2. 应用高置信度推荐
            for rec in recommendations:
                if rec['confidence'] > 0.8 and rec['type'] == 'best_practice':
                    # 这里可以根据推荐调整执行参数
                    applied_recommendations.append(rec.get('id', 'unknown'))
            
            # 3. 执行原始功能
            start_time = datetime.now()
            result = await execution_func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 4. 更新上下文性能指标
            if result.metadata is None:
                result.metadata = {}
            result.metadata['execution_time'] = execution_time
            result.metadata['knowledge_recommendations'] = len(recommendations)
            result.metadata['applied_recommendations'] = len(applied_recommendations)
            
            # 5. 记录执行结果
            await self.knowledge_integrator.record_execution_result(
                context, result, applied_recommendations
            )
            
            return result
        
        except Exception as e:
            # 知识增强失败时，至少执行原始功能
            try:
                return await execution_func(*args, **kwargs)
            except Exception as original_error:
                raise original_error
    
    async def get_knowledge_recommendations(
        self,
        task_type: str,
        user_id: str = None,
        data_characteristics: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """获取知识推荐"""
        context = KnowledgeContext(
            agent_id=self.agent_id,
            user_id=user_id,
            task_type=task_type,
            data_characteristics=data_characteristics
        )
        
        return await self.knowledge_integrator.get_pre_execution_recommendations(context)
    
    async def share_execution_insight(
        self,
        insight_type: str,
        insight_content: Dict[str, Any],
        confidence: float = 0.8
    ):
        """分享执行洞察"""
        await self.knowledge_integrator.knowledge_manager.share_knowledge(
            self.agent_id,
            insight_type,
            insight_content,
            tags=[insight_type, self.agent_id],
            confidence=confidence
        )
    
    def enable_knowledge_integration(self):
        """启用知识集成"""
        self.knowledge_enabled = True
    
    def disable_knowledge_integration(self):
        """禁用知识集成"""
        self.knowledge_enabled = False


# 便用函数
async def create_knowledge_enhanced_execution(
    agent_id: str,
    execution_func,
    context: KnowledgeContext,
    *args,
    **kwargs
):
    """创建知识增强执行"""
    enhancer = KnowledgeEnhancedAgent(agent_id)
    return await enhancer.execute_with_knowledge(execution_func, context, *args, **kwargs)


async def get_cross_agent_insights(
    agent_results: List[Dict[str, Any]],
    knowledge_manager: KnowledgeShareManager = None
) -> List[Dict[str, Any]]:
    """获取跨Agent洞察"""
    if not knowledge_manager:
        knowledge_manager = KnowledgeShareManager()
    
    try:
        insights = await knowledge_manager.generate_insights(agent_results)
        return [
            {
                'agent_id': insight.agent_id,
                'type': insight.insight_type,
                'content': insight.insight_content,
                'confidence': insight.applicability_score,
                'impact': insight.performance_impact
            }
            for insight in insights
        ]
    except Exception:
        return []