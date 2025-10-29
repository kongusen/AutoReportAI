"""
Infrastructure层 - 占位符分析 Celery 任务

复用现有的单占位符分析能力到 Celery 任务机制中
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from celery import Task as CeleryTask
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.container import container
from app.services.infrastructure.task_queue.celery_config import celery_app
from app.services.infrastructure.task_queue.tasks import run_async, DatabaseTask

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=DatabaseTask, name='tasks.infrastructure.analyze_single_placeholder')
def analyze_single_placeholder_task(
    self,
    db: Session,
    placeholder_name: str,
    placeholder_text: str,
    template_id: str,
    data_source_id: str,
    user_id: str,
    template_context: Optional[Dict[str, Any]] = None,
    time_window: Optional[Dict[str, str]] = None,
    time_column: Optional[str] = None,
    data_range: str = "day",
    requirements: Optional[str] = None,
    execute_sql: bool = False,
    row_limit: int = 1000,
    **kwargs
) -> Dict[str, Any]:
    """
    单个占位符分析 Celery 任务
    
    复用现有的 PlaceholderOrchestrationService.analyze_placeholder_with_full_pipeline 能力
    
    Args:
        placeholder_name: 占位符名称
        placeholder_text: 占位符文本
        template_id: 模板ID
        data_source_id: 数据源ID
        user_id: 用户ID
        template_context: 模板上下文
        time_window: 时间窗口
        time_column: 时间列名
        data_range: 数据范围
        requirements: 额外需求
        execute_sql: 是否执行SQL测试
        row_limit: 行数限制
        **kwargs: 其他参数
    
    Returns:
        Dict[str, Any]: 分析结果
    """
    task_id = self.request.id
    logger.info(f"🚀 开始占位符分析任务: {placeholder_name} (Task ID: {task_id})")
    
    try:
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '初始化占位符分析',
                'progress': 10,
                'placeholder_name': placeholder_name,
                'started_at': datetime.now().isoformat()
            }
        )
        
        # 导入编排服务
        from app.api.endpoints.placeholders import PlaceholderOrchestrationService
        
        # 创建编排服务实例
        orchestration_service = PlaceholderOrchestrationService()
        
        # 构建分析参数
        analysis_params = {
            'placeholder_name': placeholder_name,
            'placeholder_text': placeholder_text,
            'template_id': template_id,
            'data_source_id': data_source_id,
            'user_id': user_id,
            'template_context': template_context,
            'time_window': time_window,
            'time_column': time_column,
            'data_range': data_range,
            'requirements': requirements,
            'execute_sql': execute_sql,
            'row_limit': row_limit,
            **kwargs
        }
        
        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '生成时间占位符',
                'progress': 25,
                'placeholder_name': placeholder_name,
            }
        )
        
        # 生成时间占位符
        from app.utils.time_placeholder_generator import generate_time_placeholders
        
        time_placeholder_result = generate_time_placeholders(
            time_window=time_window,
            cron_expression=template_context.get('cron_expression') if template_context else None,
            execution_time=datetime.now(),
            data_range=data_range,
            time_column=time_column
        )
        
        # 将时间占位符添加到分析参数中
        analysis_params['time_placeholders'] = time_placeholder_result.get('time_placeholders', {})
        analysis_params['time_context'] = time_placeholder_result.get('time_context', {})
        
        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '执行Agent Pipeline分析',
                'progress': 30,
                'placeholder_name': placeholder_name,
                'time_placeholders_generated': len(time_placeholder_result.get('time_placeholders', {}))
            }
        )
        
        # 执行异步分析
        async def run_analysis():
            return await orchestration_service.analyze_placeholder_with_full_pipeline(**analysis_params)
        
        result = run_async(run_analysis())
        
        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '处理分析结果',
                'progress': 80,
                'placeholder_name': placeholder_name,
                'analysis_success': result.get('status') == 'success'
            }
        )
        
        # 构建返回结果
        task_result = {
            'status': 'completed',
            'task_id': task_id,
            'placeholder_name': placeholder_name,
            'template_id': template_id,
            'data_source_id': data_source_id,
            'user_id': user_id,
            'analysis_result': result,
            'time_placeholders': time_placeholder_result.get('time_placeholders', {}),
            'time_context': time_placeholder_result.get('time_context', {}),
            'time_placeholder_count': time_placeholder_result.get('placeholder_count', 0),
            'completed_at': datetime.now().isoformat(),
            'success': result.get('status') == 'success'
        }
        
        # 更新最终状态
        self.update_state(
            state='SUCCESS',
            meta={
                'current_step': '分析完成',
                'progress': 100,
                'placeholder_name': placeholder_name,
                'success': result.get('status') == 'success',
                'completed_at': datetime.now().isoformat()
            }
        )
        
        logger.info(f"✅ 占位符分析任务完成: {placeholder_name} (Task ID: {task_id})")
        return task_result
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"❌ 占位符分析任务失败: {placeholder_name} (Task ID: {task_id}), 错误: {error_message}", exc_info=True)
        
        # 更新失败状态
        self.update_state(
            state='FAILURE',
            meta={
                'current_step': '分析失败',
                'progress': 0,
                'placeholder_name': placeholder_name,
                'error': error_message,
                'failed_at': datetime.now().isoformat()
            }
        )
        
        # 返回失败结果
        return {
            'status': 'failed',
            'task_id': task_id,
            'placeholder_name': placeholder_name,
            'template_id': template_id,
            'data_source_id': data_source_id,
            'user_id': user_id,
            'error': error_message,
            'failed_at': datetime.now().isoformat(),
            'success': False
        }


@celery_app.task(bind=True, base=DatabaseTask, name='tasks.infrastructure.batch_analyze_placeholders')
def batch_analyze_placeholders_task(
    self,
    db: Session,
    template_id: str,
    data_source_id: str,
    user_id: str,
    placeholder_specs: list,
    template_context: Optional[Dict[str, Any]] = None,
    time_window: Optional[Dict[str, str]] = None,
    time_column: Optional[str] = None,
    data_range: str = "day",
    requirements: Optional[str] = None,
    execute_sql: bool = False,
    row_limit: int = 1000,
    **kwargs
) -> Dict[str, Any]:
    """
    批量占位符分析 Celery 任务
    
    并行处理多个占位符的分析
    
    Args:
        template_id: 模板ID
        data_source_id: 数据源ID
        user_id: 用户ID
        placeholder_specs: 占位符规格列表 [{"name": "...", "text": "..."}, ...]
        template_context: 模板上下文
        time_window: 时间窗口
        time_column: 时间列名
        data_range: 数据范围
        requirements: 额外需求
        execute_sql: 是否执行SQL测试
        row_limit: 行数限制
        **kwargs: 其他参数
    
    Returns:
        Dict[str, Any]: 批量分析结果
    """
    task_id = self.request.id
    total_placeholders = len(placeholder_specs)
    logger.info(f"🚀 开始批量占位符分析任务: {total_placeholders} 个占位符 (Task ID: {task_id})")
    
    try:
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '初始化批量分析',
                'progress': 5,
                'total_placeholders': total_placeholders,
                'processed': 0,
                'started_at': datetime.now().isoformat()
            }
        )
        
        # 生成时间占位符（批量分析共享）
        from app.utils.time_placeholder_generator import generate_time_placeholders
        
        time_placeholder_result = generate_time_placeholders(
            time_window=time_window,
            cron_expression=template_context.get('cron_expression') if template_context else None,
            execution_time=datetime.now(),
            data_range=data_range,
            time_column=time_column
        )
        
        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '时间占位符生成完成',
                'progress': 8,
                'total_placeholders': total_placeholders,
                'processed': 0,
                'time_placeholders_generated': len(time_placeholder_result.get('time_placeholders', {}))
            }
        )
        
        # 导入编排服务
        from app.api.endpoints.placeholders import PlaceholderOrchestrationService
        
        # 创建编排服务实例
        orchestration_service = PlaceholderOrchestrationService()
        
        # 存储所有分析结果
        results = []
        success_count = 0
        failed_count = 0
        
        # 逐个处理占位符
        for idx, placeholder_spec in enumerate(placeholder_specs):
            try:
                placeholder_name = placeholder_spec.get('name', f'placeholder_{idx}')
                placeholder_text = placeholder_spec.get('text', '')
                
                # 更新进度
                progress = 10 + int(80 * idx / total_placeholders)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current_step': f'分析占位符: {placeholder_name}',
                        'progress': progress,
                        'total_placeholders': total_placeholders,
                        'processed': idx,
                        'current_placeholder': placeholder_name
                    }
                )
                
                # 构建分析参数
                analysis_params = {
                    'placeholder_name': placeholder_name,
                    'placeholder_text': placeholder_text,
                    'template_id': template_id,
                    'data_source_id': data_source_id,
                    'user_id': user_id,
                    'template_context': template_context,
                    'time_window': time_window,
                    'time_column': time_column,
                    'data_range': data_range,
                    'requirements': requirements,
                    'execute_sql': execute_sql,
                    'row_limit': row_limit,
                    'time_placeholders': time_placeholder_result.get('time_placeholders', {}),
                    'time_context': time_placeholder_result.get('time_context', {}),
                    **kwargs
                }
                
                # 执行异步分析
                async def run_single_analysis():
                    return await orchestration_service.analyze_placeholder_with_full_pipeline(**analysis_params)
                
                result = run_async(run_single_analysis())
                
                # 记录结果
                placeholder_result = {
                    'placeholder_name': placeholder_name,
                    'placeholder_text': placeholder_text,
                    'analysis_result': result,
                    'success': result.get('status') == 'success',
                    'processed_at': datetime.now().isoformat()
                }
                
                results.append(placeholder_result)
                
                if result.get('status') == 'success':
                    success_count += 1
                    logger.info(f"✅ 占位符分析成功: {placeholder_name} ({idx + 1}/{total_placeholders})")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ 占位符分析失败: {placeholder_name} ({idx + 1}/{total_placeholders})")
                
            except Exception as e:
                failed_count += 1
                error_message = str(e)
                logger.error(f"❌ 占位符分析异常: {placeholder_spec.get('name', f'placeholder_{idx}')}, 错误: {error_message}")
                
                # 记录失败结果
                placeholder_result = {
                    'placeholder_name': placeholder_spec.get('name', f'placeholder_{idx}'),
                    'placeholder_text': placeholder_spec.get('text', ''),
                    'analysis_result': {'status': 'error', 'error': error_message},
                    'success': False,
                    'processed_at': datetime.now().isoformat(),
                    'error': error_message
                }
                results.append(placeholder_result)
        
        # 构建最终结果
        batch_result = {
            'status': 'completed',
            'task_id': task_id,
            'template_id': template_id,
            'data_source_id': data_source_id,
            'user_id': user_id,
            'total_placeholders': total_placeholders,
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results,
            'time_placeholders': time_placeholder_result.get('time_placeholders', {}),
            'time_context': time_placeholder_result.get('time_context', {}),
            'time_placeholder_count': time_placeholder_result.get('placeholder_count', 0),
            'completed_at': datetime.now().isoformat(),
            'success': success_count > 0
        }
        
        # 更新最终状态
        self.update_state(
            state='SUCCESS',
            meta={
                'current_step': '批量分析完成',
                'progress': 100,
                'total_placeholders': total_placeholders,
                'success_count': success_count,
                'failed_count': failed_count,
                'completed_at': datetime.now().isoformat()
            }
        )
        
        logger.info(f"✅ 批量占位符分析任务完成: {success_count}/{total_placeholders} 成功 (Task ID: {task_id})")
        return batch_result
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"❌ 批量占位符分析任务失败: (Task ID: {task_id}), 错误: {error_message}", exc_info=True)
        
        # 更新失败状态
        self.update_state(
            state='FAILURE',
            meta={
                'current_step': '批量分析失败',
                'progress': 0,
                'error': error_message,
                'failed_at': datetime.now().isoformat()
            }
        )
        
        # 返回失败结果
        return {
            'status': 'failed',
            'task_id': task_id,
            'template_id': template_id,
            'data_source_id': data_source_id,
            'user_id': user_id,
            'total_placeholders': total_placeholders,
            'success_count': 0,
            'failed_count': total_placeholders,
            'error': error_message,
            'failed_at': datetime.now().isoformat(),
            'success': False
        }


@celery_app.task(bind=True, name='tasks.infrastructure.analyze_placeholder_with_context')
def analyze_placeholder_with_context_task(
    self,
    placeholder_name: str,
    placeholder_text: str,
    template_id: str,
    data_source_id: str,
    user_id: str,
    context_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    带上下文的占位符分析任务
    
    支持更丰富的上下文信息传递
    
    Args:
        placeholder_name: 占位符名称
        placeholder_text: 占位符文本
        template_id: 模板ID
        data_source_id: 数据源ID
        user_id: 用户ID
        context_data: 上下文数据
        **kwargs: 其他参数
    
    Returns:
        Dict[str, Any]: 分析结果
    """
    task_id = self.request.id
    logger.info(f"🚀 开始带上下文的占位符分析任务: {placeholder_name} (Task ID: {task_id})")
    
    try:
        # 更新任务状态
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '初始化上下文分析',
                'progress': 10,
                'placeholder_name': placeholder_name,
                'started_at': datetime.now().isoformat()
            }
        )
        
        # 生成时间占位符
        from app.utils.time_placeholder_generator import generate_time_placeholders
        
        # 从上下文数据中提取时间信息
        time_window = context_data.get('time_window') if context_data else None
        cron_expression = context_data.get('cron_expression') if context_data else None
        data_range = context_data.get('data_range', 'day') if context_data else 'day'
        time_column = context_data.get('time_column') if context_data else None
        
        time_placeholder_result = generate_time_placeholders(
            time_window=time_window,
            cron_expression=cron_expression,
            execution_time=datetime.now(),
            data_range=data_range,
            time_column=time_column
        )
        
        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '时间占位符生成完成',
                'progress': 15,
                'placeholder_name': placeholder_name,
                'time_placeholders_generated': len(time_placeholder_result.get('time_placeholders', {}))
            }
        )
        
        # 导入编排服务
        from app.api.endpoints.placeholders import PlaceholderOrchestrationService
        
        # 创建编排服务实例
        orchestration_service = PlaceholderOrchestrationService()
        
        # 构建分析参数，合并上下文数据
        analysis_params = {
            'placeholder_name': placeholder_name,
            'placeholder_text': placeholder_text,
            'template_id': template_id,
            'data_source_id': data_source_id,
            'user_id': user_id,
            'time_placeholders': time_placeholder_result.get('time_placeholders', {}),
            'time_context': time_placeholder_result.get('time_context', {}),
            **kwargs
        }
        
        # 合并上下文数据
        if context_data:
            analysis_params.update(context_data)
        
        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '执行上下文感知分析',
                'progress': 30,
                'placeholder_name': placeholder_name,
            }
        )
        
        # 执行异步分析
        async def run_context_analysis():
            return await orchestration_service.analyze_placeholder_with_full_pipeline(**analysis_params)
        
        result = run_async(run_context_analysis())
        
        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': '处理上下文分析结果',
                'progress': 80,
                'placeholder_name': placeholder_name,
                'analysis_success': result.get('status') == 'success'
            }
        )
        
        # 构建返回结果
        task_result = {
            'status': 'completed',
            'task_id': task_id,
            'placeholder_name': placeholder_name,
            'template_id': template_id,
            'data_source_id': data_source_id,
            'user_id': user_id,
            'context_data': context_data,
            'analysis_result': result,
            'time_placeholders': time_placeholder_result.get('time_placeholders', {}),
            'time_context': time_placeholder_result.get('time_context', {}),
            'time_placeholder_count': time_placeholder_result.get('placeholder_count', 0),
            'completed_at': datetime.now().isoformat(),
            'success': result.get('status') == 'success'
        }
        
        # 更新最终状态
        self.update_state(
            state='SUCCESS',
            meta={
                'current_step': '上下文分析完成',
                'progress': 100,
                'placeholder_name': placeholder_name,
                'success': result.get('status') == 'success',
                'completed_at': datetime.now().isoformat()
            }
        )
        
        logger.info(f"✅ 带上下文的占位符分析任务完成: {placeholder_name} (Task ID: {task_id})")
        return task_result
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"❌ 带上下文的占位符分析任务失败: {placeholder_name} (Task ID: {task_id}), 错误: {error_message}", exc_info=True)
        
        # 更新失败状态
        self.update_state(
            state='FAILURE',
            meta={
                'current_step': '上下文分析失败',
                'progress': 0,
                'placeholder_name': placeholder_name,
                'error': error_message,
                'failed_at': datetime.now().isoformat()
            }
        )
        
        # 返回失败结果
        return {
            'status': 'failed',
            'task_id': task_id,
            'placeholder_name': placeholder_name,
            'template_id': template_id,
            'data_source_id': data_source_id,
            'user_id': user_id,
            'context_data': context_data,
            'error': error_message,
            'failed_at': datetime.now().isoformat(),
            'success': False
        }


# 任务注册和配置
@celery_app.on_after_configure.connect
def setup_placeholder_tasks(sender, **kwargs):
    """设置占位符分析任务的配置"""
    
    # 配置任务路由
    sender.conf.task_routes.update({
        'tasks.infrastructure.analyze_single_placeholder': {'queue': 'infrastructure_queue'},
        'tasks.infrastructure.batch_analyze_placeholders': {'queue': 'infrastructure_queue'},
        'tasks.infrastructure.analyze_placeholder_with_context': {'queue': 'infrastructure_queue'},
    })
    
    logger.info("✅ 占位符分析 Celery 任务配置完成")


logger.info("✅ 占位符分析 Celery 任务模块加载完成")
