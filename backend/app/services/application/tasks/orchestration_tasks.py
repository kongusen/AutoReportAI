"""
Application层编排任务

这些Celery任务专注于编排跨领域的工作流：
1. 不包含具体业务逻辑（业务逻辑在Domain层）
2. 不直接处理数据（数据处理在Data层）
3. 不处理技术细节（技术实现在Infrastructure层）

职责：
- 编排其他层的任务执行顺序
- 管理分布式任务的状态
- 处理任务间的数据传递
- 协调事务边界
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from celery import chain, group, chord

from ...infrastructure.task_queue.celery_config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='application.orchestration.report_generation', bind=True)
def orchestrate_report_generation(
    self, 
    template_id: str, 
    data_source_ids: List[str], 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    编排报告生成的完整工作流
    
    基于新的DDD架构，使用Application层的Agent进行编排：
    1. 调用Application层的WorkflowOrchestrationAgent
    2. Agent内部协调Domain层和Infrastructure层服务
    3. 管理整个工作流的状态和进度
    """
    logger.info(f"开始编排报告生成工作流: template={template_id}, task_id={self.request.id}")
    
    async def _execute_with_agent():
        try:
            # 获取Application层的工作流编排代理
            from ..agents import get_workflow_orchestration_agent
            workflow_agent = await get_workflow_orchestration_agent()
            
            # 构建执行上下文
            execution_context = {
                'task_id': self.request.id,
                'config': config,
                'started_at': datetime.now().isoformat(),
                'orchestrator': 'celery_task'
            }
            
            # 通过代理编排整个工作流
            orchestration_result = await workflow_agent.orchestrate_report_generation(
                template_id=template_id,
                data_source_ids=data_source_ids,
                execution_context=execution_context
            )
            
            return orchestration_result
            
        except Exception as e:
            logger.error(f"报告生成工作流编排失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
    
    # 在Celery任务中运行异步代码
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_execute_with_agent())


@celery_app.task(name='application.orchestration.data_processing', bind=True)
def orchestrate_data_processing(
    self,
    pipeline_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    编排数据处理工作流
    
    基于新的DDD架构，使用Application层的Agent进行编排
    """
    logger.info(f"开始编排数据处理工作流: task_id={self.request.id}")
    
    async def _execute_with_agent():
        try:
            # 获取Application层的任务协调代理
            from ..agents import get_task_coordination_agent
            task_agent = await get_task_coordination_agent()
            
            # 构建执行上下文
            execution_context = {
                'task_id': self.request.id,
                'workflow_type': 'data_processing',
                'started_at': datetime.now().isoformat(),
                'orchestrator': 'celery_task'
            }
            
            # 通过代理协调数据处理流程
            coordination_result = await task_agent.coordinate_data_processing(
                pipeline_config=pipeline_config,
                execution_context=execution_context
            )
            
            return coordination_result
            
        except Exception as e:
            logger.error(f"数据处理工作流编排失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
    
    # 在Celery任务中运行异步代码
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_execute_with_agent())


@celery_app.task(name='application.orchestration.workflow_callback', bind=True)
def workflow_callback(self, results: List[Any], workflow_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    工作流回调任务
    
    处理编排任务的最终结果，进行清理和通知
    """
    logger.info(f"工作流回调: workflow_id={workflow_context.get('workflow_id')}")
    
    try:
        # 分析工作流执行结果
        success_count = sum(1 for result in results if result.get('success', False))
        total_count = len(results)
        
        final_status = 'completed' if success_count == total_count else 'partial_success'
        
        # 更新最终状态
        workflow_context.update({
            'status': final_status,
            'completed_at': datetime.now().isoformat(),
            'success_rate': success_count / total_count if total_count > 0 else 0,
            'results_summary': {
                'total_tasks': total_count,
                'successful_tasks': success_count,
                'failed_tasks': total_count - success_count
            }
        })
        
        return {
            'success': True,
            'final_status': final_status,
            'workflow_context': workflow_context,
            'message': f'工作流完成: {success_count}/{total_count} 任务成功'
        }
        
    except Exception as e:
        logger.error(f"工作流回调处理失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'workflow_context': workflow_context
        }


# 新增：Context-aware任务编排
@celery_app.task(name='application.orchestration.context_aware_task', bind=True)
def orchestrate_context_aware_task(self, task_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    编排上下文感知任务
    
    整合ContextAwareApplicationService的功能，使用Agent架构
    """
    logger.info(f"开始编排上下文感知任务: task_id={self.request.id}")
    
    async def _execute_with_agent():
        try:
            # 获取Application层的上下文感知代理
            from ..agents import get_context_aware_agent
            context_agent = await get_context_aware_agent()
            
            # 构建执行上下文
            execution_context = {
                'task_id': self.request.id,
                'orchestrator': 'context_aware_orchestration',
                'started_at': datetime.now().isoformat()
            }
            
            # 通过代理处理上下文感知任务
            task_result = await context_agent.execute_contextual_task(
                task_request=task_request,
                execution_context=execution_context
            )
            
            return task_result
            
        except Exception as e:
            logger.error(f"上下文感知任务编排失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
    
    # 在Celery任务中运行异步代码
    import asyncio
    try:
        loop = asyncio.get_event_loop() 
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_execute_with_agent())