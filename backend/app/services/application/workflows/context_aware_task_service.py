"""
上下文感知任务服务
增强现有任务管理系统，集成智能占位符系统的上下文感知能力
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

# 导入智能占位符系统组件
from app.services.domain.placeholder import (
    IntelligentPlaceholderOrchestrator,
    DocumentContext,
    BusinessContext, 
    TimeContext,
    ProcessingResult
)

# 导入上下文构建器
from app.services.application.context import (
    TimeContextBuilder,
    BusinessContextBuilder,
    DocumentContextBuilder
)

# 导入现有任务管理组件
from app.services.application.task_management.application.services.task_application_service import TaskApplicationService
from app.services.application.task_management.execution.enhanced_two_phase_pipeline import EnhancedTwoPhasePipeline
from app.services.application.task_management.core.worker.tasks.ai_analysis_tasks import analyze_template_placeholders
from app.services.application.task_management.management.task_manager import TaskManager

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
    DATA_EXTRACTION = "data_extraction"
    CONTENT_SYNTHESIS = "content_synthesis"
    QUALITY_ASSESSMENT = "quality_assessment"

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
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class ContextualTaskResult:
    """上下文任务结果"""
    task_id: str
    status: str
    success: bool
    processing_result: Optional[ProcessingResult] = None
    generated_content: Optional[str] = None
    quality_metrics: Dict[str, Any] = None
    execution_time: float = 0.0
    context_analysis: Dict[str, Any] = None
    recommendations: List[str] = None
    errors: List[str] = None
    warnings: List[str] = None

@dataclass
class TaskExecutionStrategy:
    """任务执行策略"""
    use_intelligent_routing: bool = True
    enable_context_optimization: bool = True
    enable_adaptive_timeout: bool = True
    enable_result_caching: bool = True
    max_retry_attempts: int = 3
    fallback_to_simple_processing: bool = True

class ContextAwareTaskService:
    """上下文感知任务服务"""
    
    def __init__(self, 
                 orchestrator: Optional[IntelligentPlaceholderOrchestrator] = None,
                 execution_strategy: Optional[TaskExecutionStrategy] = None):
        self.execution_strategy = execution_strategy or TaskExecutionStrategy()
        
        # 初始化组件
        self.placeholder_orchestrator = orchestrator
        self.time_builder = TimeContextBuilder()
        self.business_builder = BusinessContextBuilder()
        self.document_builder = DocumentContextBuilder()
        
        # 现有服务集成
        self.task_application_service = TaskApplicationService()
        self.task_manager = TaskManager()
        self.two_phase_pipeline = EnhancedTwoPhasePipeline()
        
        # 任务缓存和状态跟踪
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_cache: Dict[str, ContextualTaskResult] = {}
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        
        # 性能统计
        self.performance_metrics = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'avg_execution_time': 0.0,
            'context_cache_hits': 0,
            'intelligent_routing_usage': 0
        }
    
    async def submit_contextual_task(self, 
                                   request: ContextualTaskRequest) -> Dict[str, Any]:
        """
        提交上下文感知任务
        
        Args:
            request: 上下文任务请求
            
        Returns:
            任务提交结果，包含task_id等信息
        """
        try:
            # 生成任务ID
            task_id = self._generate_task_id(request)
            
            # 构建执行上下文
            execution_context = await self._build_execution_context(request)
            
            # 智能路由决策
            execution_plan = self._create_execution_plan(request, execution_context)
            
            # 注册任务
            self.active_tasks[task_id] = {
                'request': request,
                'execution_context': execution_context,
                'execution_plan': execution_plan,
                'status': 'queued',
                'created_at': datetime.now(),
                'timeout_at': datetime.now() + timedelta(minutes=request.timeout_minutes)
            }
            
            # 异步执行任务
            asyncio.create_task(self._execute_contextual_task(task_id))
            
            return {
                'task_id': task_id,
                'status': 'queued',
                'estimated_completion_time': execution_plan.get('estimated_time', 60),
                'execution_strategy': execution_plan.get('strategy', 'standard'),
                'context_analysis': {
                    'document_complexity': execution_context.get('document_complexity', 0.5),
                    'business_context_richness': execution_context.get('business_richness', 0.5),
                    'temporal_sensitivity': execution_context.get('temporal_sensitivity', 0.5)
                }
            }
            
        except Exception as e:
            logger.error(f"任务提交失败: {e}")
            return {
                'task_id': None,
                'status': 'failed',
                'error': str(e)
            }
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                return {
                    'task_id': task_id,
                    'status': task_info['status'],
                    'created_at': task_info['created_at'].isoformat(),
                    'timeout_at': task_info['timeout_at'].isoformat(),
                    'execution_plan': task_info.get('execution_plan', {}),
                    'progress': task_info.get('progress', 0.0)
                }
            
            if task_id in self.task_cache:
                cached_result = self.task_cache[task_id]
                return {
                    'task_id': task_id,
                    'status': cached_result.status,
                    'success': cached_result.success,
                    'completed': True
                }
            
            return {
                'task_id': task_id,
                'status': 'not_found',
                'error': 'Task not found'
            }
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return {
                'task_id': task_id,
                'status': 'error',
                'error': str(e)
            }
    
    async def get_task_result(self, task_id: str) -> ContextualTaskResult:
        """获取任务结果"""
        try:
            # 检查缓存
            if task_id in self.task_cache:
                return self.task_cache[task_id]
            
            # 检查活跃任务
            if task_id in self.active_tasks:
                task_info = self.active_tasks[task_id]
                if task_info['status'] == 'completed':
                    result = task_info.get('result')
                    if result:
                        # 缓存结果
                        self.task_cache[task_id] = result
                        return result
                else:
                    return ContextualTaskResult(
                        task_id=task_id,
                        status=task_info['status'],
                        success=False,
                        errors=[f"Task is still {task_info['status']}"]
                    )
            
            return ContextualTaskResult(
                task_id=task_id,
                status='not_found',
                success=False,
                errors=['Task not found']
            )
            
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return ContextualTaskResult(
                task_id=task_id,
                status='error',
                success=False,
                errors=[str(e)]
            )
    
    async def _execute_contextual_task(self, task_id: str):
        """执行上下文任务"""
        start_time = datetime.now()
        task_info = self.active_tasks[task_id]
        
        try:
            # 更新状态
            task_info['status'] = 'running'
            task_info['progress'] = 0.1
            
            request = task_info['request']
            execution_context = task_info['execution_context']
            execution_plan = task_info['execution_plan']
            
            # 根据任务类型执行不同逻辑
            if request.task_type == ContextAwareTaskType.PLACEHOLDER_ANALYSIS:
                result = await self._execute_placeholder_analysis(request, execution_context)
            elif request.task_type == ContextAwareTaskType.TEMPLATE_PROCESSING:
                result = await self._execute_template_processing(request, execution_context)
            elif request.task_type == ContextAwareTaskType.REPORT_GENERATION:
                result = await self._execute_report_generation(request, execution_context)
            elif request.task_type == ContextAwareTaskType.DATA_EXTRACTION:
                result = await self._execute_data_extraction(request, execution_context)
            elif request.task_type == ContextAwareTaskType.CONTENT_SYNTHESIS:
                result = await self._execute_content_synthesis(request, execution_context)
            elif request.task_type == ContextAwareTaskType.QUALITY_ASSESSMENT:
                result = await self._execute_quality_assessment(request, execution_context)
            else:
                raise ValueError(f"Unsupported task type: {request.task_type}")
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            # 更新状态
            task_info['status'] = 'completed'
            task_info['result'] = result
            task_info['progress'] = 1.0
            
            # 更新性能统计
            self._update_performance_metrics(execution_time, result.success)
            
            logger.info(f"任务 {task_id} 执行完成，耗时 {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"任务 {task_id} 执行失败: {e}")
            
            # 创建失败结果
            result = ContextualTaskResult(
                task_id=task_id,
                status='failed',
                success=False,
                execution_time=execution_time,
                errors=[str(e)]
            )
            
            task_info['status'] = 'failed'
            task_info['result'] = result
            task_info['progress'] = 1.0
            
            self._update_performance_metrics(execution_time, False)
    
    async def _build_execution_context(self, request: ContextualTaskRequest) -> Dict[str, Any]:
        """构建执行上下文"""
        try:
            # 检查上下文缓存
            context_key = self._generate_context_cache_key(request)
            if context_key in self.context_cache and self.execution_strategy.enable_result_caching:
                self.performance_metrics['context_cache_hits'] += 1
                return self.context_cache[context_key]
            
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
            
            # 分析上下文复杂度和特征
            context_analysis = self._analyze_context_characteristics(
                time_context, business_context, document_context, request
            )
            
            execution_context = {
                'time_context': time_context,
                'business_context': business_context,
                'document_context': document_context,
                'context_analysis': context_analysis,
                'document_complexity': document_context.structure_complexity,
                'business_richness': len(business_context.organizational_context) / 10,
                'temporal_sensitivity': 1.0 if 'real_time' in time_context.reporting_period else 0.5
            }
            
            # 缓存上下文
            if self.execution_strategy.enable_result_caching:
                self.context_cache[context_key] = execution_context
            
            return execution_context
            
        except Exception as e:
            logger.error(f"执行上下文构建失败: {e}")
            return {}
    
    def _create_execution_plan(self, 
                             request: ContextualTaskRequest, 
                             execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """创建执行计划"""
        try:
            plan = {
                'strategy': 'standard',
                'estimated_time': 60,
                'use_intelligent_processing': False,
                'enable_caching': self.execution_strategy.enable_result_caching,
                'timeout_adjustment': 1.0
            }
            
            # 智能路由决策
            if self.execution_strategy.use_intelligent_routing:
                complexity_score = execution_context.get('document_complexity', 0.5)
                business_richness = execution_context.get('business_richness', 0.5)
                
                # 复杂任务使用智能处理
                if complexity_score > 0.7 or business_richness > 0.6:
                    plan['strategy'] = 'intelligent'
                    plan['use_intelligent_processing'] = True
                    plan['estimated_time'] = 120
                    self.performance_metrics['intelligent_routing_usage'] += 1
                
                # 高优先级任务优化
                if request.priority in [TaskPriority.HIGH, TaskPriority.URGENT]:
                    plan['strategy'] = 'priority_optimized'
                    plan['timeout_adjustment'] = 1.5
                
                # 实时任务特殊处理
                if execution_context.get('temporal_sensitivity', 0) > 0.8:
                    plan['strategy'] = 'real_time_optimized'
                    plan['estimated_time'] = 30
                    plan['enable_caching'] = False
            
            # 自适应超时
            if self.execution_strategy.enable_adaptive_timeout:
                base_timeout = request.timeout_minutes
                adjusted_timeout = base_timeout * plan['timeout_adjustment']
                plan['adjusted_timeout_minutes'] = adjusted_timeout
            
            return plan
            
        except Exception as e:
            logger.error(f"执行计划创建失败: {e}")
            return {'strategy': 'fallback', 'estimated_time': 60}
    
    async def _execute_placeholder_analysis(self, 
                                          request: ContextualTaskRequest,
                                          execution_context: Dict[str, Any]) -> ContextualTaskResult:
        """执行占位符分析任务"""
        try:
            if self.placeholder_orchestrator and execution_context.get('use_intelligent_processing'):
                # 使用智能占位符系统
                processing_result = await self.placeholder_orchestrator.process_document(
                    document_content=request.content,
                    document_context=execution_context['document_context'],
                    business_context=execution_context['business_context'],
                    time_context=execution_context['time_context']
                )
                
                return ContextualTaskResult(
                    task_id="",  # 会在调用者中设置
                    status='completed',
                    success=True,
                    processing_result=processing_result,
                    quality_metrics={
                        'quality_score': processing_result.quality_score,
                        'placeholder_count': len(processing_result.processed_placeholders),
                        'processing_time': processing_result.processing_metrics.total_time
                    },
                    context_analysis=execution_context['context_analysis'],
                    recommendations=processing_result.recommendations
                )
            else:
                # 回退到传统处理
                result = await analyze_template_placeholders.delay(
                    request.content,
                    request.user_context,
                    request.business_requirements
                )
                
                return ContextualTaskResult(
                    task_id="",
                    status='completed', 
                    success=True,
                    generated_content=str(result),
                    quality_metrics={'fallback_processing': True}
                )
                
        except Exception as e:
            logger.error(f"占位符分析任务失败: {e}")
            return ContextualTaskResult(
                task_id="",
                status='failed',
                success=False,
                errors=[str(e)]
            )
    
    async def _execute_template_processing(self, 
                                         request: ContextualTaskRequest,
                                         execution_context: Dict[str, Any]) -> ContextualTaskResult:
        """执行模板处理任务"""
        try:
            if self.placeholder_orchestrator:
                # 智能模板处理
                processing_result = await self.placeholder_orchestrator.process_document(
                    document_content=request.content,
                    document_context=execution_context['document_context'],
                    business_context=execution_context['business_context'],
                    time_context=execution_context['time_context']
                )
                
                # 生成处理后的内容
                processed_content = await self._synthesize_processed_template(
                    request.content, processing_result
                )
                
                return ContextualTaskResult(
                    task_id="",
                    status='completed',
                    success=True,
                    processing_result=processing_result,
                    generated_content=processed_content,
                    quality_metrics={
                        'quality_score': processing_result.quality_score,
                        'template_complexity': execution_context.get('document_complexity', 0.5)
                    },
                    recommendations=processing_result.recommendations
                )
            else:
                # 简单模板处理
                processed_content = await self._simple_template_processing(request.content)
                return ContextualTaskResult(
                    task_id="",
                    status='completed',
                    success=True,
                    generated_content=processed_content
                )
                
        except Exception as e:
            return ContextualTaskResult(
                task_id="",
                status='failed', 
                success=False,
                errors=[str(e)]
            )
    
    def _analyze_context_characteristics(self, 
                                       time_context: TimeContext,
                                       business_context: BusinessContext,
                                       document_context: DocumentContext,
                                       request: ContextualTaskRequest) -> Dict[str, Any]:
        """分析上下文特征"""
        try:
            characteristics = {
                'temporal_complexity': 0.5,
                'business_complexity': 0.5,
                'document_complexity': document_context.structure_complexity,
                'user_sophistication': 0.5,
                'urgency_level': 0.5
            }
            
            # 时间复杂度分析
            if time_context.reporting_period in ['real_time', 'hourly']:
                characteristics['temporal_complexity'] = 0.9
            elif time_context.reporting_period in ['daily', 'weekly']:
                characteristics['temporal_complexity'] = 0.7
            elif time_context.reporting_period in ['monthly', 'quarterly']:
                characteristics['temporal_complexity'] = 0.5
            else:
                characteristics['temporal_complexity'] = 0.3
            
            # 业务复杂度分析
            org_context = business_context.organizational_context
            if len(business_context.compliance_requirements) > 3:
                characteristics['business_complexity'] += 0.2
            if len(business_context.performance_targets) > 5:
                characteristics['business_complexity'] += 0.2
            if org_context.get('company_size') in ['large', 'enterprise']:
                characteristics['business_complexity'] += 0.1
            
            # 用户成熟度分析
            user_role = request.user_context.get('role', '').lower()
            if any(keyword in user_role for keyword in ['analyst', 'manager', 'director', 'cfo']):
                characteristics['user_sophistication'] = 0.8
            elif any(keyword in user_role for keyword in ['specialist', 'coordinator']):
                characteristics['user_sophistication'] = 0.6
            
            # 紧急程度分析
            if request.priority == TaskPriority.URGENT:
                characteristics['urgency_level'] = 0.9
            elif request.priority == TaskPriority.HIGH:
                characteristics['urgency_level'] = 0.7
            elif request.priority == TaskPriority.NORMAL:
                characteristics['urgency_level'] = 0.5
            else:
                characteristics['urgency_level'] = 0.3
            
            return characteristics
            
        except Exception as e:
            logger.error(f"上下文特征分析失败: {e}")
            return {'error': str(e)}
    
    def _generate_task_id(self, request: ContextualTaskRequest) -> str:
        """生成任务ID"""
        import hashlib
        import uuid
        
        # 基于请求内容和时间戳生成唯一ID
        content_hash = hashlib.md5(request.content.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_suffix = str(uuid.uuid4())[:8]
        
        return f"{request.task_type.value}_{content_hash}_{timestamp}_{unique_suffix}"
    
    def _generate_context_cache_key(self, request: ContextualTaskRequest) -> str:
        """生成上下文缓存键"""
        import hashlib
        
        # 基于用户上下文和业务要求生成缓存键
        cache_data = {
            'user_context': request.user_context,
            'business_requirements': request.business_requirements,
            'temporal_constraints': request.temporal_constraints
        }
        
        cache_str = str(cache_data)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _update_performance_metrics(self, execution_time: float, success: bool):
        """更新性能指标"""
        self.performance_metrics['total_tasks'] += 1
        
        if success:
            self.performance_metrics['successful_tasks'] += 1
        
        # 更新平均执行时间
        total_tasks = self.performance_metrics['total_tasks']
        current_avg = self.performance_metrics['avg_execution_time']
        new_avg = (current_avg * (total_tasks - 1) + execution_time) / total_tasks
        self.performance_metrics['avg_execution_time'] = new_avg
    
    async def _synthesize_processed_template(self, 
                                           original_content: str, 
                                           processing_result: ProcessingResult) -> str:
        """合成处理后的模板（占位符方法）"""
        # TODO: 实现模板合成逻辑
        return f"处理后的模板内容基于 {len(processing_result.processed_placeholders)} 个占位符"
    
    async def _simple_template_processing(self, content: str) -> str:
        """简单模板处理（占位符方法）"""
        # TODO: 实现简单模板处理逻辑
        return f"简单处理的模板: {content[:100]}..."
    
    # 其他任务类型的执行方法（占位符实现）
    async def _execute_report_generation(self, request, context) -> ContextualTaskResult:
        return ContextualTaskResult(task_id="", status='completed', success=True, 
                                  generated_content="生成的报告")
    
    async def _execute_data_extraction(self, request, context) -> ContextualTaskResult:
        return ContextualTaskResult(task_id="", status='completed', success=True,
                                  generated_content="提取的数据")
    
    async def _execute_content_synthesis(self, request, context) -> ContextualTaskResult:
        return ContextualTaskResult(task_id="", status='completed', success=True,
                                  generated_content="合成的内容")
    
    async def _execute_quality_assessment(self, request, context) -> ContextualTaskResult:
        return ContextualTaskResult(task_id="", status='completed', success=True,
                                  quality_metrics={'score': 0.8})
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        success_rate = (self.performance_metrics['successful_tasks'] / 
                       max(self.performance_metrics['total_tasks'], 1))
        
        return {
            'performance_metrics': self.performance_metrics.copy(),
            'success_rate': success_rate,
            'active_tasks': len(self.active_tasks),
            'cached_results': len(self.task_cache),
            'cached_contexts': len(self.context_cache),
            'execution_strategy': {
                'intelligent_routing': self.execution_strategy.use_intelligent_routing,
                'context_optimization': self.execution_strategy.enable_context_optimization,
                'result_caching': self.execution_strategy.enable_result_caching
            }
        }
    
    async def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理已完成的任务"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # 清理活跃任务中的已完成任务
        completed_tasks = []
        for task_id, task_info in self.active_tasks.items():
            if (task_info['status'] in ['completed', 'failed'] and 
                task_info['created_at'] < cutoff_time):
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            del self.active_tasks[task_id]
        
        # 清理过期缓存
        # 这里可以添加更复杂的缓存清理逻辑
        
        logger.info(f"清理了 {len(completed_tasks)} 个过期任务")