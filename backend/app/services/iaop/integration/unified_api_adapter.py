"""
统一API适配器 - 替换现有API端点的上下文处理逻辑

这个适配器提供了统一的接口，让现有的API端点可以无缝切换到新的智能上下文系统
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from ..context.unified_context_system import (
    UnifiedContextSystem, 
    create_unified_context_system,
    SystemIntegrationMode
)
from ..context.execution_context import EnhancedExecutionContext, ContextScope

logger = logging.getLogger(__name__)


class UnifiedAPIAdapter:
    """
    统一API适配器
    
    提供统一接口替换现有的分散上下文管理逻辑
    """
    
    def __init__(self, db_session=None, integration_mode: str = "intelligent"):
        self.db_session = db_session
        self.integration_mode = integration_mode
        
        # 创建统一上下文系统
        self.unified_system = create_unified_context_system(
            db_session=db_session,
            integration_mode=integration_mode,
            enable_performance_monitoring=True
        )
        
        logger.info(f"统一API适配器初始化，模式: {integration_mode}")
    
    async def analyze_with_agent_enhanced(
        self,
        template_id: str,
        data_source_id: str,
        user_id: str,
        force_reanalyze: bool = False,
        optimization_level: str = "enhanced",
        target_expectations: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        增强的Agent分析 - 替换现有的analyze_with_agent逻辑
        
        使用新的统一上下文系统进行智能分析
        """
        logger.info(f"增强Agent分析开始，模板: {template_id}")
        
        try:
            # 1. 构建请求上下文
            request_data = {
                'template_id': template_id,
                'data_source_id': data_source_id,
                'force_reanalyze': force_reanalyze,
                'optimization_level': optimization_level,
                'target_expectations': target_expectations,
                'analysis_type': 'agent_analysis'
            }
            
            # 2. 构建业务意图
            business_intent = self._infer_analysis_intent(target_expectations)
            
            # 3. 获取数据源上下文（这里应该从数据库或缓存获取）
            data_source_context = await self._get_data_source_context(data_source_id)
            
            # 4. 创建统一执行上下文
            session_id = f"analysis_{template_id}_{int(datetime.now().timestamp())}"
            context_result = await self.unified_system.create_execution_context(
                session_id=session_id,
                user_id=user_id,
                request_data=request_data,
                business_intent=business_intent,
                data_source_context=data_source_context,
                task_id=f"analyze_template_{template_id}"
            )
            
            if not context_result.success:
                return {
                    'success': False,
                    'error': context_result.error_message,
                    'context_creation_failed': True
                }
            
            # 5. 执行分析逻辑（这里调用原有的分析逻辑，但使用新的上下文）
            analysis_result = await self._execute_template_analysis(
                context_result.context, template_id, data_source_id, optimization_level
            )
            
            # 6. 记录执行反馈
            await self.unified_system.record_execution_feedback(
                context_result.context,
                analysis_result,
                business_domain='template_analysis'
            )
            
            # 7. 构建响应
            return {
                'success': analysis_result.get('success', False),
                'data': analysis_result,
                'context_info': {
                    'confidence_score': context_result.confidence_score,
                    'optimization_applied': context_result.optimization_applied,
                    'learning_applied': context_result.learning_applied,
                    'recommendations': context_result.recommendations
                },
                'processing_details': context_result.processing_details,
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"增强Agent分析失败: {e}")
            return {
                'success': False,
                'error': f"增强分析失败: {str(e)}",
                'analysis_failed': True
            }
    
    async def test_with_data_enhanced(
        self,
        placeholder_text: str,
        data_source_id: str,
        user_id: str,
        template_id: Optional[str] = None,
        target_expectation: Optional[str] = None,
        optimization_level: str = "enhanced"
    ) -> Dict[str, Any]:
        """
        增强的test_with_data - 替换现有的test_with_data逻辑
        
        使用新的统一上下文系统进行智能SQL生成和测试
        """
        logger.info(f"增强数据测试开始，占位符: {placeholder_text[:50]}...")
        
        try:
            # 1. 构建请求上下文
            request_data = {
                'placeholder_text': placeholder_text,
                'data_source_id': data_source_id,
                'template_id': template_id,
                'target_expectation': target_expectation,
                'optimization_level': optimization_level,
                'test_type': 'data_generation'
            }
            
            # 2. 构建业务意图
            business_intent = self._infer_test_intent(placeholder_text, target_expectation)
            
            # 3. 获取数据源上下文
            data_source_context = await self._get_data_source_context(data_source_id)
            
            # 4. 创建统一执行上下文
            session_id = f"test_data_{int(datetime.now().timestamp())}"
            context_result = await self.unified_system.create_execution_context(
                session_id=session_id,
                user_id=user_id,
                request_data=request_data,
                business_intent=business_intent,
                data_source_context=data_source_context,
                task_id=f"test_placeholder_{template_id or 'standalone'}"
            )
            
            if not context_result.success:
                return {
                    'success': False,
                    'error': context_result.error_message,
                    'context_creation_failed': True
                }
            
            # 5. 执行SQL生成和测试（使用智能上下文）
            test_result = await self._execute_intelligent_sql_generation(
                context_result.context, placeholder_text, data_source_id, target_expectation
            )
            
            # 6. 记录执行反馈
            await self.unified_system.record_execution_feedback(
                context_result.context,
                test_result,
                business_domain='sql_generation'
            )
            
            # 7. 构建响应
            return {
                'success': test_result.get('success', False),
                'data': test_result,
                'context_info': {
                    'confidence_score': context_result.confidence_score,
                    'optimization_applied': context_result.optimization_applied,
                    'learning_applied': context_result.learning_applied,
                    'recommendations': context_result.recommendations
                },
                'processing_details': context_result.processing_details,
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"增强数据测试失败: {e}")
            return {
                'success': False,
                'error': f"增强测试失败: {str(e)}",
                'test_failed': True
            }
    
    async def batch_placeholder_analysis(
        self,
        placeholders: List[Dict[str, Any]],
        global_context: Dict[str, Any],
        user_id: str,
        execution_mode: str = "batch"
    ) -> Dict[str, Any]:
        """
        批量占位符分析 - 替换现有的多占位符处理逻辑
        
        使用新的统一上下文系统进行智能批量处理
        """
        logger.info(f"批量占位符分析开始，数量: {len(placeholders)}")
        
        try:
            # 1. 使用统一上下文系统管理多占位符
            context_result = await self.unified_system.manage_multi_placeholder_context(
                placeholders, global_context, execution_mode
            )
            
            if not context_result.success:
                return {
                    'success': False,
                    'error': context_result.error_message,
                    'context_management_failed': True
                }
            
            # 2. 按照优化的执行顺序处理占位符
            batch_results = []
            execution_order = context_result.processing_details.get('execution_order', [])
            
            for placeholder_info in execution_order:
                placeholder_id = placeholder_info.get('placeholder_id')
                placeholder_data = next(
                    (p for p in placeholders if p.get('id') == placeholder_id), None
                )
                
                if not placeholder_data:
                    continue
                
                # 使用占位符特定的上下文进行处理
                placeholder_result = await self._process_single_placeholder_with_context(
                    placeholder_data, context_result.context, global_context
                )
                
                batch_results.append({
                    'placeholder_id': placeholder_id,
                    'result': placeholder_result,
                    'processing_order': placeholder_info.get('order', 0)
                })
            
            # 3. 记录批量执行反馈
            overall_success = all(r['result'].get('success', False) for r in batch_results)
            batch_execution_result = {
                'success': overall_success,
                'batch_results': batch_results,
                'total_processed': len(batch_results),
                'success_count': sum(1 for r in batch_results if r['result'].get('success', False))
            }
            
            await self.unified_system.record_execution_feedback(
                context_result.context,
                batch_execution_result,
                business_domain='batch_placeholder_analysis'
            )
            
            # 4. 构建响应
            return {
                'success': overall_success,
                'data': {
                    'batch_results': batch_results,
                    'execution_summary': {
                        'total_placeholders': len(placeholders),
                        'processed_placeholders': len(batch_results),
                        'successful_placeholders': sum(1 for r in batch_results if r['result'].get('success', False)),
                        'execution_mode': execution_mode
                    }
                },
                'context_info': {
                    'confidence_score': context_result.confidence_score,
                    'optimization_applied': context_result.optimization_applied,
                    'learning_applied': context_result.learning_applied,
                    'recommendations': context_result.recommendations
                },
                'processing_details': context_result.processing_details
            }
            
        except Exception as e:
            logger.error(f"批量占位符分析失败: {e}")
            return {
                'success': False,
                'error': f"批量分析失败: {str(e)}",
                'batch_analysis_failed': True
            }
    
    async def get_system_insights(self) -> Dict[str, Any]:
        """
        获取系统洞察 - 提供系统性能和学习状态的洞察
        """
        try:
            # 获取系统性能指标
            performance_metrics = await self.unified_system.get_system_performance_metrics()
            
            # 构建洞察报告
            insights = {
                'system_health': {
                    'success_rate': performance_metrics.get('success_rate', 0.0),
                    'average_confidence': performance_metrics.get('average_confidence_score', 0.0),
                    'average_processing_time': performance_metrics.get('average_processing_time', 0.0),
                    'total_requests': performance_metrics.get('total_requests', 0)
                },
                'optimization_insights': {},
                'learning_insights': {},
                'recommendations': []
            }
            
            # 优化引擎洞察
            if 'optimization_engine' in performance_metrics:
                opt_metrics = performance_metrics['optimization_engine']
                insights['optimization_insights'] = {
                    'total_optimizations': opt_metrics.get('total_optimizations', 0),
                    'successful_optimizations': opt_metrics.get('successful_optimizations', 0),
                    'average_improvement': opt_metrics.get('average_improvement', 0.0)
                }
            
            # 学习系统洞察
            if 'learning_system' in performance_metrics:
                learning_metrics = performance_metrics['learning_system']
                insights['learning_insights'] = {
                    'total_sessions': learning_metrics.get('total_sessions', 0),
                    'total_knowledge_items': learning_metrics.get('total_knowledge_items', 0),
                    'learning_velocity': learning_metrics.get('learning_velocity', 0.0)
                }
            
            # 生成改进建议
            insights['recommendations'] = self._generate_system_recommendations(performance_metrics)
            
            return {
                'success': True,
                'data': insights,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取系统洞察失败: {e}")
            return {
                'success': False,
                'error': f"洞察获取失败: {str(e)}"
            }
    
    def _infer_analysis_intent(self, target_expectations: Optional[Dict[str, Any]]) -> str:
        """推断分析意图"""
        if not target_expectations:
            return "通用占位符分析"
        
        intent_keywords = []
        if target_expectations.get('analysis_type'):
            intent_keywords.append(target_expectations['analysis_type'])
        if target_expectations.get('expected_output'):
            intent_keywords.append(target_expectations['expected_output'])
        
        return " ".join(intent_keywords) if intent_keywords else "占位符智能分析"
    
    def _infer_test_intent(self, placeholder_text: str, target_expectation: Optional[str]) -> str:
        """推断测试意图"""
        intent = f"SQL生成测试: {placeholder_text[:100]}"
        if target_expectation:
            intent += f" | 期望: {target_expectation}"
        return intent
    
    async def _get_data_source_context(self, data_source_id: str) -> Dict[str, Any]:
        """获取数据源上下文"""
        # 这里应该从数据库或缓存中获取数据源的详细信息
        # 暂时返回模拟数据
        return {
            'source_id': data_source_id,
            'source_type': 'doris',  # 应该从数据库获取
            'tables': {},  # 应该从schema分析服务获取
            'capabilities': ['sql_query', 'aggregation'],
            'performance_characteristics': 'high_performance'
        }
    
    async def _execute_template_analysis(
        self, 
        context: EnhancedExecutionContext, 
        template_id: str, 
        data_source_id: str, 
        optimization_level: str
    ) -> Dict[str, Any]:
        """执行模板分析（这里应该调用原有的分析逻辑）"""
        # 模拟分析结果，实际应该调用原有的分析服务
        return {
            'success': True,
            'analysis_results': {
                'placeholders_analyzed': 5,
                'sql_queries_generated': 3,
                'optimization_level': optimization_level
            },
            'confidence_score': context.get_context('confidence_score', 0.8),
            'processing_time_ms': 1500
        }
    
    async def _execute_intelligent_sql_generation(
        self,
        context: EnhancedExecutionContext,
        placeholder_text: str,
        data_source_id: str,
        target_expectation: Optional[str]
    ) -> Dict[str, Any]:
        """执行智能SQL生成（这里应该调用增强的SQL生成逻辑）"""
        # 模拟SQL生成结果，实际应该调用智能SQL生成服务
        return {
            'success': True,
            'generated_sql': "SELECT COUNT(*) FROM table_name",
            'execution_result': {'count': 1000},
            'confidence_score': context.get_context('confidence_score', 0.8),
            'processing_time_ms': 800,
            'optimization_iterations': 2
        }
    
    async def _process_single_placeholder_with_context(
        self,
        placeholder_data: Dict[str, Any],
        master_context: EnhancedExecutionContext,
        global_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理单个占位符（使用上下文信息）"""
        # 模拟占位符处理结果
        return {
            'success': True,
            'placeholder_id': placeholder_data.get('id'),
            'sql_generated': True,
            'chart_data_available': True,
            'processing_time_ms': 600
        }
    
    def _generate_system_recommendations(self, performance_metrics: Dict[str, Any]) -> List[str]:
        """生成系统改进建议"""
        recommendations = []
        
        success_rate = performance_metrics.get('success_rate', 0.0)
        if success_rate < 0.8:
            recommendations.append("系统成功率较低，建议启用更高级别的上下文优化")
        
        avg_confidence = performance_metrics.get('average_confidence_score', 0.0)
        if avg_confidence < 0.7:
            recommendations.append("平均置信度较低，建议提供更详细的业务意图和期望描述")
        
        if performance_metrics.get('total_requests', 0) > 100:
            recommendations.append("系统使用量较高，建议监控性能指标并考虑扩展")
        
        return recommendations


# 全局适配器实例
_unified_adapter: Optional[UnifiedAPIAdapter] = None

def get_unified_api_adapter(db_session=None, integration_mode: str = "intelligent") -> UnifiedAPIAdapter:
    """获取统一API适配器实例"""
    global _unified_adapter
    if _unified_adapter is None:
        _unified_adapter = UnifiedAPIAdapter(db_session=db_session, integration_mode=integration_mode)
    return _unified_adapter