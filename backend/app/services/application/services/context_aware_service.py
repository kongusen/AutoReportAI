"""
上下文感知应用服务

Application Service负责：
1. 整合上下文构建和分析
2. 协调智能占位符系统
3. 提供上下文感知的任务执行
4. 管理复杂的上下文工作流

从原workflows/context_aware_task_service.py重构而来
遵循DDD原则，专注于应用层的协调职责
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


@dataclass
class ContextualTaskResult:
    """上下文任务结果"""
    task_id: str
    status: str
    success: bool
    generated_content: Optional[str] = None
    quality_metrics: Dict[str, Any] = None
    execution_time: float = 0.0
    context_analysis: Dict[str, Any] = None
    recommendations: List[str] = None
    errors: List[str] = None


class ContextAwareApplicationService:
    """
    上下文感知应用服务
    
    负责协调上下文构建和智能处理的复杂工作流
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # 初始化上下文构建器
        self._initialize_context_builders()
        # 性能统计
        self.performance_metrics = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'avg_execution_time': 0.0,
            'context_cache_hits': 0
        }
    
    def _initialize_context_builders(self):
        """初始化上下文构建器"""
        try:
            from ..context import (
                TimeContextBuilder,
                BusinessContextBuilder,
                DocumentContextBuilder
            )
            self.time_builder = TimeContextBuilder()
            self.business_builder = BusinessContextBuilder()
            self.document_builder = DocumentContextBuilder()
        except ImportError:
            self.logger.warning("Context builders not available, using mock implementations")
            # 创建占位符实现
            class MockContextBuilder:
                def build_from_request(self, *args, **kwargs):
                    return {'mock': True}
                def build_from_user_context(self, *args, **kwargs):
                    return {'mock': True}
                def build_from_content_analysis(self, *args, **kwargs):
                    return {'mock': True}
            
            self.time_builder = MockContextBuilder()
            self.business_builder = MockContextBuilder()
            self.document_builder = MockContextBuilder()
    
    async def submit_contextual_task(self, request: ContextualTaskRequest) -> Dict[str, Any]:
        """
        提交上下文感知任务
        
        Application Service职责：
        1. 构建执行上下文
        2. 选择合适的编排策略
        3. 启动相应的工作流
        """
        try:
            task_id = self._generate_task_id(request)
            self.logger.info(f"提交上下文感知任务: {task_id}, type: {request.task_type}")
            
            # 构建执行上下文
            execution_context = await self._build_execution_context(request)
            
            # 根据任务类型选择编排策略
            if request.task_type == ContextAwareTaskType.REPORT_GENERATION:
                result = await self._handle_report_generation(task_id, request, execution_context)
            elif request.task_type == ContextAwareTaskType.PLACEHOLDER_ANALYSIS:
                result = await self._handle_placeholder_analysis(task_id, request, execution_context)
            elif request.task_type == ContextAwareTaskType.TEMPLATE_PROCESSING:
                result = await self._handle_template_processing(task_id, request, execution_context)
            else:
                result = await self._handle_generic_task(task_id, request, execution_context)
            
            # 更新性能统计
            self.performance_metrics['total_tasks'] += 1
            if result.get('success'):
                self.performance_metrics['successful_tasks'] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"上下文任务提交失败: {e}")
            return {
                'task_id': None,
                'success': False,
                'error': str(e),
                'status': 'submission_failed'
            }
    
    async def _build_execution_context(self, request: ContextualTaskRequest) -> Dict[str, Any]:
        """
        构建执行上下文
        
        整合各种上下文信息，为任务执行提供丰富的上下文
        """
        try:
            # 构建时间上下文
            time_context = self.time_builder.build_from_request(
                time_range_str=request.temporal_constraints.get('time_range'),
                reporting_period=request.temporal_constraints.get('reporting_period'),
                timezone=request.user_context.get('timezone')
            )
            
            # 构建业务上下文  
            business_context = self.business_builder.build_from_user_context(
                user_role=request.user_context.get('role'),
                department=request.user_context.get('department'),
                company_info=request.user_context.get('company_info'),
                project_context=request.business_requirements
            )
            
            # 构建文档上下文
            document_context = self.document_builder.build_from_content_analysis(
                content=request.content,
                user_intent=request.business_requirements,
                document_specs=request.quality_requirements
            )
            
            return {
                'time_context': time_context,
                'business_context': business_context, 
                'document_context': document_context,
                'priority': request.priority.value,
                'timeout_minutes': request.timeout_minutes,
                'quality_requirements': request.quality_requirements
            }
            
        except Exception as e:
            self.logger.error(f"构建执行上下文失败: {e}")
            return {'error': str(e), 'fallback': True}
    
    async def _handle_report_generation(self, task_id: str, request: ContextualTaskRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理报告生成任务"""
        try:
            # 调用报告编排器
            from ..orchestrators.report_orchestrator import ReportOrchestrator
            orchestrator = ReportOrchestrator()
            
            # 从请求中提取必要参数
            template_id = request.business_requirements.get('template_id')
            data_source_ids = request.business_requirements.get('data_source_ids', [])
            
            if not template_id:
                return {
                    'task_id': task_id,
                    'success': False,
                    'error': '缺少模板ID',
                    'status': 'validation_failed'
                }
            
            # 启动报告生成编排
            orchestration_result = await orchestrator.orchestrate_report_generation(
                template_id=template_id,
                data_source_ids=data_source_ids,
                execution_context={
                    'context': context,
                    'user_id': request.user_context.get('user_id'),
                    'contextual_task': True
                },
                user_id=request.user_context.get('user_id', '')
            )
            
            return {
                'task_id': task_id,
                'success': orchestration_result['success'],
                'celery_task_id': orchestration_result.get('celery_task_id'),
                'status': orchestration_result.get('status', 'started'),
                'message': '上下文感知报告生成已启动',
                'context_analysis': self._analyze_context(context)
            }
            
        except Exception as e:
            return {
                'task_id': task_id,
                'success': False,
                'error': str(e),
                'status': 'orchestration_failed'
            }
    
    async def _handle_placeholder_analysis(self, task_id: str, request: ContextualTaskRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理占位符分析任务"""
        try:
            # 调用Domain层的占位符分析服务
            # TODO: 集成智能占位符系统
            
            return {
                'task_id': task_id,
                'success': True,
                'status': 'completed',
                'message': '占位符分析完成（占位符实现）',
                'context_analysis': self._analyze_context(context),
                'recommendations': ['建议优化占位符命名', '建议增加业务上下文']
            }
            
        except Exception as e:
            return {
                'task_id': task_id,
                'success': False,
                'error': str(e),
                'status': 'analysis_failed'
            }
    
    async def _handle_template_processing(self, task_id: str, request: ContextualTaskRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理模板处理任务"""
        # 占位符实现
        return {
            'task_id': task_id,
            'success': True,
            'status': 'completed',
            'message': '模板处理完成（占位符实现）',
            'generated_content': f"处理后的模板内容基于上下文: {len(str(context))} 字符"
        }
    
    async def _handle_generic_task(self, task_id: str, request: ContextualTaskRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理通用任务"""
        return {
            'task_id': task_id,
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
    
    def _generate_task_id(self, request: ContextualTaskRequest) -> str:
        """生成任务ID"""
        import hashlib
        import uuid
        
        content_hash = hashlib.md5(request.content.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_suffix = str(uuid.uuid4())[:8]
        
        return f"ctx_{request.task_type.value}_{content_hash}_{timestamp}_{unique_suffix}"