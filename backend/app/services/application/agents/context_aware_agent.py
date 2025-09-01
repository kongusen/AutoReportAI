"""
上下文感知代理

Application层的代理服务，整合原有ContextAwareApplicationService的功能，
负责协调上下文构建和智能处理的复杂工作流。
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    URGENT = "urgent"


class ContextAwareTaskType(Enum):
    """上下文感知任务类型"""
    PLACEHOLDER_ANALYSIS = "placeholder_analysis"
    TEMPLATE_PROCESSING = "template_processing" 
    REPORT_GENERATION = "report_generation"
    CONTENT_SYNTHESIS = "content_synthesis"


@dataclass
class ContextualTaskRequest:
    """上下文任务请求"""
    task_type: ContextAwareTaskType
    content: str
    user_context: Dict[str, Any]
    business_requirements: Dict[str, Any]
    temporal_constraints: Dict[str, Any]
    quality_requirements: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_minutes: int = 30


class ContextAwareAgent:
    """
    上下文感知代理
    
    Application层的代理服务，负责：
    1. 协调上下文构建和智能处理
    2. 管理复杂的上下文工作流
    3. 整合Domain层和Infrastructure层的上下文服务
    """
    
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for Context Aware Agent")
        self.user_id = user_id
        self.logger = logging.getLogger(self.__class__.__name__)
        # 延迟初始化各层的服务
        self._domain_services = {}
        self._infrastructure_services = {}
        
        # 性能统计
        self.performance_metrics = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'avg_execution_time': 0.0,
            'context_cache_hits': 0
        }
    
    async def execute_contextual_task(
        self, 
        task_request: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行上下文感知任务
        
        Args:
            task_request: 任务请求（来自Celery任务）
            execution_context: 执行上下文
            
        Returns:
            任务执行结果
        """
        try:
            # 解析任务请求
            contextual_request = self._parse_task_request(task_request)
            
            self.logger.info(f"执行上下文感知任务: {contextual_request.task_type}")
            
            # 构建执行上下文
            enriched_context = await self._build_execution_context(
                contextual_request, execution_context
            )
            
            # 根据任务类型协调相应的服务
            if contextual_request.task_type == ContextAwareTaskType.REPORT_GENERATION:
                result = await self._coordinate_report_generation(
                    contextual_request, enriched_context
                )
            elif contextual_request.task_type == ContextAwareTaskType.PLACEHOLDER_ANALYSIS:
                result = await self._coordinate_placeholder_analysis(
                    contextual_request, enriched_context
                )
            elif contextual_request.task_type == ContextAwareTaskType.TEMPLATE_PROCESSING:
                result = await self._coordinate_template_processing(
                    contextual_request, enriched_context
                )
            else:
                result = await self._coordinate_generic_task(
                    contextual_request, enriched_context
                )
            
            # 更新性能统计
            self.performance_metrics['total_tasks'] += 1
            if result.get('success'):
                self.performance_metrics['successful_tasks'] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"上下文任务执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'execution_failed',
                'failed_at': datetime.now().isoformat()
            }
    
    def _parse_task_request(self, task_request: Dict[str, Any]) -> ContextualTaskRequest:
        """解析任务请求"""
        try:
            return ContextualTaskRequest(
                task_type=ContextAwareTaskType(task_request.get('task_type')),
                content=task_request.get('content', ''),
                user_context=task_request.get('user_context', {}),
                business_requirements=task_request.get('business_requirements', {}),
                temporal_constraints=task_request.get('temporal_constraints', {}),
                quality_requirements=task_request.get('quality_requirements', {}),
                priority=TaskPriority(task_request.get('priority', 'normal')),
                timeout_minutes=task_request.get('timeout_minutes', 30)
            )
        except Exception as e:
            self.logger.error(f"任务请求解析失败: {e}")
            raise ValueError(f"Invalid task request format: {e}")
    
    async def _build_execution_context(
        self, 
        request: ContextualTaskRequest,
        base_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        构建丰富的执行上下文
        
        整合各种上下文信息，为任务执行提供丰富的上下文
        """
        try:
            # 获取Application层的上下文构建服务
            context_builders = await self._get_context_builders()
            
            # 构建时间上下文
            time_context = context_builders['time'].build_from_request(
                time_range_str=request.temporal_constraints.get('time_range'),
                reporting_period=request.temporal_constraints.get('reporting_period'),
                timezone=request.user_context.get('timezone')
            )
            
            # 构建业务上下文  
            business_context = context_builders['business'].build_from_user_context(
                user_role=request.user_context.get('role'),
                department=request.user_context.get('department'),
                company_info=request.user_context.get('company_info'),
                project_context=request.business_requirements
            )
            
            # 构建文档上下文
            document_context = context_builders['document'].build_from_content_analysis(
                content=request.content,
                user_intent=request.business_requirements,
                document_specs=request.quality_requirements
            )
            
            return {
                **base_context,
                'contextual_request': request,
                'time_context': time_context,
                'business_context': business_context, 
                'document_context': document_context,
                'priority': request.priority.value,
                'timeout_minutes': request.timeout_minutes,
                'quality_requirements': request.quality_requirements,
                'context_built_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"构建执行上下文失败: {e}")
            return {**base_context, 'context_error': str(e), 'fallback': True}
    
    async def _coordinate_report_generation(
        self, 
        request: ContextualTaskRequest,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """协调报告生成任务"""
        try:
            # 获取Application层的报告编排器
            from ..orchestrators.report_orchestrator import ReportOrchestrator
            orchestrator = ReportOrchestrator()
            
            # 从请求中提取必要参数
            template_id = request.business_requirements.get('template_id')
            data_source_ids = request.business_requirements.get('data_source_ids', [])
            
            if not template_id:
                return {
                    'success': False,
                    'error': '缺少模板ID',
                    'status': 'validation_failed'
                }
            
            # 启动报告生成编排
            orchestration_result = await orchestrator.orchestrate_report_generation(
                template_id=template_id,
                data_source_ids=data_source_ids,
                execution_context={
                    **context,
                    'contextual_task': True,
                    'context_aware_processing': True
                },
                user_id=request.user_context.get('user_id', '')
            )
            
            return {
                'success': orchestration_result['success'],
                'celery_task_id': orchestration_result.get('celery_task_id'),
                'status': orchestration_result.get('status', 'started'),
                'message': '上下文感知报告生成已启动',
                'context_analysis': self._analyze_context(context)
            }
            
        except Exception as e:
            self.logger.error(f"报告生成协调失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'report_coordination_failed'
            }
    
    async def _coordinate_placeholder_analysis(
        self, 
        request: ContextualTaskRequest,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """协调占位符分析任务"""
        try:
            # 获取Domain层的占位符分析服务
            placeholder_service = await self._get_domain_service('placeholder_analysis')
            
            # 使用上下文信息进行智能占位符分析
            analysis_result = await placeholder_service.analyze_contextual_placeholders(
                content=request.content,
                context=context,
                analysis_options={
                    'use_context': True,
                    'quality_level': request.quality_requirements.get('quality_level', 'standard')
                }
            )
            
            return {
                'success': True,
                'status': 'completed',
                'analysis_result': analysis_result,
                'context_analysis': self._analyze_context(context),
                'recommendations': analysis_result.get('recommendations', [])
            }
            
        except Exception as e:
            self.logger.error(f"占位符分析协调失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'placeholder_analysis_failed'
            }
    
    async def _coordinate_template_processing(
        self, 
        request: ContextualTaskRequest,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """协调模板处理任务"""
        try:
            # 获取Domain层的模板处理服务
            template_service = await self._get_domain_service('template_processing')
            
            # 使用上下文信息进行智能模板处理
            processing_result = await template_service.process_contextual_template(
                content=request.content,
                context=context,
                processing_options={
                    'use_context': True,
                    'output_format': request.quality_requirements.get('output_format', 'html')
                }
            )
            
            return {
                'success': True,
                'status': 'completed',
                'processing_result': processing_result,
                'generated_content': processing_result.get('processed_content'),
                'context_analysis': self._analyze_context(context)
            }
            
        except Exception as e:
            self.logger.error(f"模板处理协调失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'template_processing_failed'
            }
    
    async def _coordinate_generic_task(
        self, 
        request: ContextualTaskRequest,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """协调通用任务"""
        return {
            'success': True,
            'status': 'completed',
            'message': f'通用{request.task_type.value}任务完成',
            'context_analysis': self._analyze_context(context)
        }
    
    def _analyze_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析上下文特征"""
        return {
            'context_richness': len(str(context)) / 1000,  # 简单的复杂度指标
            'has_time_context': 'time_context' in context,
            'has_business_context': 'business_context' in context,
            'has_document_context': 'document_context' in context,
            'quality_score': 0.8  # 占位符评分
        }
    
    async def _get_context_builders(self) -> Dict[str, Any]:
        """获取上下文构建器"""
        if 'context_builders' not in self._infrastructure_services:
            from ..context import (
                TimeContextBuilder,
                BusinessContextBuilder,
                DocumentContextBuilder
            )
            
            self._infrastructure_services['context_builders'] = {
                'time': TimeContextBuilder(),
                'business': BusinessContextBuilder(),
                'document': DocumentContextBuilder()
            }
        
        return self._infrastructure_services['context_builders']
    
    async def _get_domain_service(self, service_type: str):
        """获取Domain层服务实例"""
        if service_type not in self._domain_services:
            if service_type == 'placeholder_analysis':
                from ...domain.placeholder import get_intelligent_placeholder_service
                self._domain_services[service_type] = await get_intelligent_placeholder_service()
            elif service_type == 'template_processing':
                from ...domain.template import get_agent_enhanced_template_service
                self._domain_services[service_type] = await get_agent_enhanced_template_service()
            else:
                raise ValueError(f"Unknown domain service type: {service_type}")
        
        return self._domain_services[service_type]
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        success_rate = (self.performance_metrics['successful_tasks'] / 
                       max(self.performance_metrics['total_tasks'], 1))
        
        return {
            'performance_metrics': self.performance_metrics.copy(),
            'success_rate': success_rate,
            'service_status': 'running',
            'last_updated': datetime.now().isoformat()
        }