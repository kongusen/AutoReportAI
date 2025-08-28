"""
统一上下文编排器 - 替换现有编排器的新版本

基于新的统一上下文系统，提供：
1. 智能上下文管理
2. 渐进式优化
3. 学习驱动的改进
4. 统一的处理流程
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.iaop.context.unified_context_system import (
    UnifiedContextSystem,
    create_unified_context_system,
    SystemIntegrationMode
)
from app.services.iaop.integration.unified_api_adapter import UnifiedAPIAdapter
from app.services.domain.placeholder.models import (
    PlaceholderRequest, AgentExecutionResult, ResultSource
)
from app.services.domain.placeholder.unified_cache_service import UnifiedCacheService
from app.services.domain.placeholder.execution_service import DataExecutionService
from app.services.data.connectors.connector_factory import create_connector

logger = logging.getLogger(__name__)


class UnifiedContextOrchestrator:
    """
    统一上下文编排器
    
    完全替换现有的编排器，使用新的统一上下文系统进行智能编排
    """
    
    def __init__(
        self, 
        db: Session, 
        user_id: str = None,
        integration_mode: str = "intelligent",
        enable_caching: bool = True
    ):
        self.db = db
        self.user_id = user_id or "system"
        self.integration_mode = integration_mode
        self.enable_caching = enable_caching
        
        # 初始化统一上下文系统
        self.unified_system = create_unified_context_system(
            db_session=db,
            integration_mode=integration_mode,
            enable_performance_monitoring=True
        )
        
        # 初始化API适配器
        self.api_adapter = UnifiedAPIAdapter(
            db_session=db,
            integration_mode=integration_mode
        )
        
        # 保留必要的传统服务（用于数据执行）
        if enable_caching:
            self.cache_service = UnifiedCacheService(db)
        else:
            self.cache_service = None
            
        self.execution_service = DataExecutionService(db)
        
        # 性能监控
        self.orchestration_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'cache_hits': 0,
            'optimization_applications': 0,
            'learning_applications': 0,
            'average_processing_time': 0.0
        }
        
        logger.info(f"统一上下文编排器初始化完成，模式: {integration_mode}")
    
    async def execute_enhanced_template_analysis(
        self,
        template_id: str,
        data_source_id: str,
        force_reanalyze: bool = False,
        optimization_level: str = "enhanced",
        target_expectations: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行增强的模板分析 - 替换原有的_execute_phase1_analysis
        """
        start_time = datetime.now()
        logger.info(f"执行增强模板分析，模板: {template_id}")
        
        try:
            self.orchestration_stats['total_requests'] += 1
            
            # 使用统一API适配器进行分析
            analysis_result = await self.api_adapter.analyze_with_agent_enhanced(
                template_id=template_id,
                data_source_id=data_source_id,
                user_id=self.user_id,
                force_reanalyze=force_reanalyze,
                optimization_level=optimization_level,
                target_expectations=target_expectations
            )
            
            # 更新统计信息
            if analysis_result.get('success'):
                self.orchestration_stats['successful_requests'] += 1
                
            context_info = analysis_result.get('context_info', {})
            if context_info.get('optimization_applied'):
                self.orchestration_stats['optimization_applications'] += 1
                
            if context_info.get('learning_applied'):
                self.orchestration_stats['learning_applications'] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_average_processing_time(processing_time)
            
            # 添加编排器特定信息
            analysis_result['orchestration_info'] = {
                'orchestrator_type': 'unified_context',
                'integration_mode': self.integration_mode,
                'processing_time_ms': processing_time,
                'cache_enabled': self.enable_caching
            }
            
            logger.info(f"增强模板分析完成，成功: {analysis_result.get('success', False)}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"增强模板分析失败: {e}")
            return {
                'success': False,
                'error': f"增强分析失败: {str(e)}",
                'orchestration_error': True
            }
    
    async def execute_enhanced_placeholder_test(
        self,
        placeholder_text: str,
        data_source_id: str,
        template_id: Optional[str] = None,
        execution_mode: str = "test_with_data",
        optimization_level: str = "enhanced",
        target_expectation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行增强的占位符测试
        """
        start_time = datetime.now()
        logger.info(f"执行增强占位符测试: {placeholder_text[:50]}...")
        
        try:
            self.orchestration_stats['total_requests'] += 1
            
            # 根据执行模式选择处理方式
            if execution_mode == "test_with_data":
                # 使用统一API适配器的增强测试
                test_result = await self.api_adapter.test_with_data_enhanced(
                    placeholder_text=placeholder_text,
                    data_source_id=data_source_id,
                    user_id=self.user_id,
                    template_id=template_id,
                    target_expectation=target_expectation,
                    optimization_level=optimization_level
                )
            else:
                # 其他模式使用传统处理（如图表生成）
                test_result = await self._execute_traditional_placeholder_test(
                    placeholder_text=placeholder_text,
                    data_source_id=data_source_id,
                    template_id=template_id,
                    execution_mode=execution_mode
                )
            
            # 更新统计信息
            if test_result.get('success'):
                self.orchestration_stats['successful_requests'] += 1
                
            context_info = test_result.get('context_info', {})
            if context_info.get('optimization_applied'):
                self.orchestration_stats['optimization_applications'] += 1
                
            if context_info.get('learning_applied'):
                self.orchestration_stats['learning_applications'] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_average_processing_time(processing_time)
            
            # 添加编排器信息
            test_result['orchestration_info'] = {
                'orchestrator_type': 'unified_context',
                'execution_mode': execution_mode,
                'integration_mode': self.integration_mode,
                'processing_time_ms': processing_time
            }
            
            logger.info(f"增强占位符测试完成，成功: {test_result.get('success', False)}")
            
            return test_result
            
        except Exception as e:
            logger.error(f"增强占位符测试失败: {e}")
            return {
                'success': False,
                'error': f"增强测试失败: {str(e)}",
                'orchestration_error': True
            }
    
    async def execute_batch_placeholder_processing(
        self,
        placeholders: List[Dict[str, Any]],
        global_context: Dict[str, Any],
        execution_mode: str = "batch",
        optimization_level: str = "enhanced"
    ) -> Dict[str, Any]:
        """
        执行批量占位符处理
        """
        start_time = datetime.now()
        logger.info(f"执行批量占位符处理，数量: {len(placeholders)}")
        
        try:
            self.orchestration_stats['total_requests'] += 1
            
            # 使用统一API适配器进行批量处理
            batch_result = await self.api_adapter.batch_placeholder_analysis(
                placeholders=placeholders,
                global_context=global_context,
                user_id=self.user_id,
                execution_mode=execution_mode
            )
            
            # 更新统计信息
            if batch_result.get('success'):
                self.orchestration_stats['successful_requests'] += 1
                
            context_info = batch_result.get('context_info', {})
            if context_info.get('optimization_applied'):
                self.orchestration_stats['optimization_applications'] += 1
                
            if context_info.get('learning_applied'):
                self.orchestration_stats['learning_applications'] += 1
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_average_processing_time(processing_time)
            
            # 添加编排器信息
            batch_result['orchestration_info'] = {
                'orchestrator_type': 'unified_context',
                'batch_size': len(placeholders),
                'execution_mode': execution_mode,
                'integration_mode': self.integration_mode,
                'processing_time_ms': processing_time
            }
            
            logger.info(f"批量占位符处理完成，成功: {batch_result.get('success', False)}")
            
            return batch_result
            
        except Exception as e:
            logger.error(f"批量占位符处理失败: {e}")
            return {
                'success': False,
                'error': f"批量处理失败: {str(e)}",
                'orchestration_error': True
            }
    
    async def get_orchestration_insights(self) -> Dict[str, Any]:
        """
        获取编排器洞察信息
        """
        try:
            # 获取统一系统的性能指标
            system_insights = await self.api_adapter.get_system_insights()
            
            # 结合编排器自身的统计信息
            orchestration_insights = {
                'orchestrator_stats': self.orchestration_stats.copy(),
                'system_insights': system_insights.get('data', {}) if system_insights.get('success') else {},
                'configuration': {
                    'integration_mode': self.integration_mode,
                    'caching_enabled': self.enable_caching,
                    'user_id': self.user_id
                },
                'recommendations': self._generate_orchestration_recommendations()
            }
            
            return {
                'success': True,
                'data': orchestration_insights,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取编排器洞察失败: {e}")
            return {
                'success': False,
                'error': f"洞察获取失败: {str(e)}"
            }
    
    async def _execute_traditional_placeholder_test(
        self,
        placeholder_text: str,
        data_source_id: str,
        template_id: Optional[str],
        execution_mode: str
    ) -> Dict[str, Any]:
        """
        执行传统的占位符测试（用于非智能模式）
        """
        try:
            # 这里可以调用原有的两阶段编排器或其他传统处理逻辑
            from app.services.iaop.orchestration.two_stage_chart_orchestrator import get_two_stage_chart_orchestrator
            
            orchestrator = get_two_stage_chart_orchestrator(self.db)
            result = await orchestrator.execute_for_template_placeholder(
                placeholder_text=placeholder_text,
                data_source_id=data_source_id,
                user_id=self.user_id,
                template_id=template_id,
                execution_mode=execution_mode
            )
            
            return result
            
        except Exception as e:
            logger.error(f"传统占位符测试失败: {e}")
            return {
                'success': False,
                'error': f"传统测试失败: {str(e)}",
                'fallback_executed': True
            }
    
    def _update_average_processing_time(self, new_time: float):
        """更新平均处理时间"""
        total_requests = self.orchestration_stats['total_requests']
        current_avg = self.orchestration_stats['average_processing_time']
        
        if total_requests == 1:
            self.orchestration_stats['average_processing_time'] = new_time
        else:
            self.orchestration_stats['average_processing_time'] = (
                (current_avg * (total_requests - 1) + new_time) / total_requests
            )
    
    def _generate_orchestration_recommendations(self) -> List[str]:
        """生成编排器改进建议"""
        recommendations = []
        
        success_rate = (
            self.orchestration_stats['successful_requests'] / 
            max(self.orchestration_stats['total_requests'], 1)
        )
        
        if success_rate < 0.8:
            recommendations.append("成功率较低，建议启用更高级别的上下文优化")
        
        if self.orchestration_stats['optimization_applications'] == 0:
            recommendations.append("未使用优化功能，建议启用渐进式优化")
        
        if self.orchestration_stats['learning_applications'] == 0:
            recommendations.append("未启用学习功能，建议开启学习模式以持续改进")
        
        avg_time = self.orchestration_stats['average_processing_time']
        if avg_time > 5000:  # 5秒
            recommendations.append("处理时间较长，建议优化数据源连接或启用缓存")
        
        return recommendations
    
    # 为了向后兼容，保留原有方法名的别名
    async def _execute_phase1_analysis(
        self,
        template_id: str,
        data_source_id: str,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """向后兼容的方法别名"""
        return await self.execute_enhanced_template_analysis(
            template_id=template_id,
            data_source_id=data_source_id,
            force_reanalyze=force_reanalyze,
            optimization_level=self.integration_mode,
            target_expectations=None
        )


# 全局编排器实例管理
_orchestrator_instances: Dict[str, UnifiedContextOrchestrator] = {}

def get_unified_context_orchestrator(
    db: Session, 
    user_id: str = None,
    integration_mode: str = "intelligent",
    enable_caching: bool = True
) -> UnifiedContextOrchestrator:
    """获取统一上下文编排器实例"""
    
    # 创建实例键
    instance_key = f"{user_id}_{integration_mode}_{enable_caching}"
    
    if instance_key not in _orchestrator_instances:
        _orchestrator_instances[instance_key] = UnifiedContextOrchestrator(
            db=db,
            user_id=user_id,
            integration_mode=integration_mode,
            enable_caching=enable_caching
        )
    
    return _orchestrator_instances[instance_key]


# 为了替换现有的CachedAgentOrchestrator，提供兼容性别名
CachedAgentOrchestratorV2 = UnifiedContextOrchestrator