"""
任务管理应用服务

Application Service负责：
1. 协调Domain层的任务业务逻辑
2. 编排异步任务的执行流程
3. 管理任务的生命周期
4. 处理任务相关的用例场景

不直接包含Celery任务，而是通过调用其他层的任务服务
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TaskExecutionRequest:
    """任务执行请求"""
    task_id: str
    user_id: str
    template_id: str
    data_source_ids: List[str]
    execution_context: Dict[str, Any]
    priority: str = 'normal'


@dataclass 
class TaskExecutionResult:
    """任务执行结果"""
    success: bool
    celery_task_id: Optional[str] = None
    status: str = 'pending'
    message: str = ''
    error: Optional[str] = None


class TaskApplicationService:
    """
    任务管理应用服务
    
    负责编排任务相关的用例，协调各层服务
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def execute_report_generation_task(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        """
        执行报告生成任务
        
        应用服务职责：编排工作流，不包含具体业务逻辑
        """
        self.logger.info(f"开始执行报告生成任务: {request.task_id}")
        
        try:
            # 1. 调用Domain层验证任务
            validation_result = await self._validate_task_execution(request)
            if not validation_result['valid']:
                return TaskExecutionResult(
                    success=False,
                    status='validation_failed', 
                    error=validation_result['error']
                )
            
            # 2. 调用Application层编排器执行工作流
            from ..orchestrators.report_orchestrator import ReportOrchestrator
            orchestrator = ReportOrchestrator()
            
            orchestration_result = await orchestrator.orchestrate_report_generation(
                template_id=request.template_id,
                data_source_ids=request.data_source_ids,
                execution_context=request.execution_context,
                user_id=request.user_id
            )
            
            return TaskExecutionResult(
                success=orchestration_result['success'],
                celery_task_id=orchestration_result.get('celery_task_id'),
                status=orchestration_result.get('status', 'started'),
                message='报告生成任务已启动'
            )
            
        except Exception as e:
            self.logger.error(f"任务执行失败: {e}")
            return TaskExecutionResult(
                success=False,
                status='error',
                error=str(e)
            )
    
    async def get_task_status(self, task_id: str, celery_task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取任务状态
        
        编排多个服务来获取完整的任务状态信息
        """
        try:
            status_info = {
                'task_id': task_id,
                'status': 'unknown'
            }
            
            # 从Infrastructure层获取Celery任务状态
            if celery_task_id:
                from ...infrastructure.task_queue.celery_config import celery_app
                result = celery_app.AsyncResult(celery_task_id)
                status_info.update({
                    'celery_status': result.status,
                    'celery_result': result.result if result.ready() else None
                })
            
            # 从Domain层获取业务状态
            # TODO: 调用Domain服务获取业务相关状态
            
            return status_info
            
        except Exception as e:
            self.logger.error(f"获取任务状态失败: {e}")
            return {
                'task_id': task_id,
                'status': 'error',
                'error': str(e)
            }
    
    async def _validate_task_execution(self, request: TaskExecutionRequest) -> Dict[str, Any]:
        """
        验证任务执行条件
        
        调用Domain层的验证服务
        """
        try:
            # TODO: 调用Domain层的任务验证服务
            # from ...domain.task.validation_service import TaskValidationService
            # validation_service = TaskValidationService()
            # return await validation_service.validate_execution_request(request)
            
            # 临时实现
            if not request.template_id:
                return {'valid': False, 'error': '缺少模板ID'}
            if not request.data_source_ids:
                return {'valid': False, 'error': '缺少数据源ID'}
                
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': f'验证失败: {str(e)}'}


# 提供向后兼容的工厂函数
def create_task_application_service() -> TaskApplicationService:
    """创建任务应用服务实例"""
    return TaskApplicationService()