"""
API端点 - 占位符分析 Celery 任务接口

提供触发占位符分析 Celery 任务的 API 接口
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.base import APIResponse
from app.services.infrastructure.task_queue.placeholder_tasks import (
    analyze_single_placeholder_task,
    batch_analyze_placeholders_task,
    analyze_placeholder_with_context_task
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze-async", response_model=APIResponse[Dict[str, Any]])
async def analyze_placeholder_async(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """
    异步分析单个占位符 - 使用 Celery 任务
    
    触发后台任务进行占位符分析，立即返回任务ID
    自动生成时间占位符，支持后续任务的时间参数替换
    
    支持的参数:
    - placeholder_name: 占位符名称
    - placeholder_text: 占位符文本
    - template_id: 模板ID
    - data_source_id: 数据源ID (可选)
    - template_context: 模板上下文 (可选)
    - time_window: 时间窗口 (可选)
    - time_column: 时间列名 (可选)
    - data_range: 数据范围 (默认: day)
    - requirements: 额外需求 (可选)
    - execute_sql: 是否执行SQL测试 (默认: false)
    - row_limit: 行数限制 (默认: 1000)
    
    返回结果包含:
    - time_placeholders: 生成的时间占位符字典
    - time_context: 时间上下文信息
    - time_placeholder_count: 时间占位符数量
    """
    try:
        # 验证必需字段
        required_fields = ["placeholder_name", "placeholder_text", "template_id"]
        for field in required_fields:
            if not request.get(field):
                raise HTTPException(
                    status_code=400,
                    detail=f"缺少必需字段: {field}"
                )
        
        placeholder_name = request.get("placeholder_name")
        placeholder_text = request.get("placeholder_text")
        template_id = request.get("template_id")
        data_source_id = request.get("data_source_id")
        
        logger.info(f"🚀 触发异步占位符分析任务: {placeholder_name}")
        
        # 触发 Celery 任务
        task = analyze_single_placeholder_task.delay(
            placeholder_name=placeholder_name,
            placeholder_text=placeholder_text,
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=str(current_user.id),
            template_context=request.get("template_context"),
            time_window=request.get("time_window"),
            time_column=request.get("time_column"),
            data_range=request.get("data_range", "day"),
            requirements=request.get("requirements"),
            execute_sql=request.get("execute_sql", False),
            row_limit=request.get("row_limit", 1000),
            **{k: v for k, v in request.items() if k not in required_fields + ["data_source_id"]}
        )
        
        logger.info(f"✅ 异步占位符分析任务已提交: {placeholder_name} (Task ID: {task.id})")
        
        return APIResponse(
            success=True,
            data={
                "task_id": task.id,
                "placeholder_name": placeholder_name,
                "template_id": template_id,
                "data_source_id": data_source_id,
                "status": "submitted",
                "message": "占位符分析任务已提交，请使用 task_id 查询进度"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 触发异步占位符分析任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"触发异步占位符分析任务失败: {str(e)}"
        )


@router.post("/batch-analyze-async", response_model=APIResponse[Dict[str, Any]])
async def batch_analyze_placeholders_async(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """
    异步批量分析占位符 - 使用 Celery 任务
    
    触发后台任务进行批量占位符分析，立即返回任务ID
    自动生成时间占位符，所有占位符共享相同的时间上下文
    
    支持的参数:
    - template_id: 模板ID
    - data_source_id: 数据源ID
    - placeholders: 占位符列表 [{"name": "...", "text": "..."}, ...]
    - template_context: 模板上下文 (可选)
    - time_window: 时间窗口 (可选)
    - time_column: 时间列名 (可选)
    - data_range: 数据范围 (默认: day)
    - requirements: 额外需求 (可选)
    - execute_sql: 是否执行SQL测试 (默认: false)
    - row_limit: 行数限制 (默认: 1000)
    
    返回结果包含:
    - time_placeholders: 生成的时间占位符字典
    - time_context: 时间上下文信息
    - time_placeholder_count: 时间占位符数量
    """
    try:
        # 验证必需字段
        required_fields = ["template_id", "data_source_id", "placeholders"]
        for field in required_fields:
            if not request.get(field):
                raise HTTPException(
                    status_code=400,
                    detail=f"缺少必需字段: {field}"
                )
        
        template_id = request.get("template_id")
        data_source_id = request.get("data_source_id")
        placeholders = request.get("placeholders", [])
        
        if not isinstance(placeholders, list) or len(placeholders) == 0:
            raise HTTPException(
                status_code=400,
                detail="placeholders 必须是非空列表"
            )
        
        # 验证占位符格式
        for i, placeholder in enumerate(placeholders):
            if not isinstance(placeholder, dict):
                raise HTTPException(
                    status_code=400,
                    detail=f"占位符 {i} 必须是字典格式"
                )
            if not placeholder.get("name") or not placeholder.get("text"):
                raise HTTPException(
                    status_code=400,
                    detail=f"占位符 {i} 缺少 name 或 text 字段"
                )
        
        logger.info(f"🚀 触发异步批量占位符分析任务: {len(placeholders)} 个占位符")
        
        # 触发 Celery 任务
        task = batch_analyze_placeholders_task.delay(
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=str(current_user.id),
            placeholder_specs=placeholders,
            template_context=request.get("template_context"),
            time_window=request.get("time_window"),
            time_column=request.get("time_column"),
            data_range=request.get("data_range", "day"),
            requirements=request.get("requirements"),
            execute_sql=request.get("execute_sql", False),
            row_limit=request.get("row_limit", 1000),
            **{k: v for k, v in request.items() if k not in required_fields}
        )
        
        logger.info(f"✅ 异步批量占位符分析任务已提交: {len(placeholders)} 个占位符 (Task ID: {task.id})")
        
        return APIResponse(
            success=True,
            data={
                "task_id": task.id,
                "template_id": template_id,
                "data_source_id": data_source_id,
                "total_placeholders": len(placeholders),
                "status": "submitted",
                "message": "批量占位符分析任务已提交，请使用 task_id 查询进度"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 触发异步批量占位符分析任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"触发异步批量占位符分析任务失败: {str(e)}"
        )


@router.post("/analyze-with-context-async", response_model=APIResponse[Dict[str, Any]])
async def analyze_placeholder_with_context_async(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """
    异步分析占位符（带上下文） - 使用 Celery 任务
    
    触发后台任务进行带上下文的占位符分析，立即返回任务ID
    自动生成时间占位符，支持从上下文数据中提取时间信息
    
    支持的参数:
    - placeholder_name: 占位符名称
    - placeholder_text: 占位符文本
    - template_id: 模板ID
    - data_source_id: 数据源ID
    - context_data: 上下文数据 (可选，可包含时间信息)
    - 其他参数同 analyze_placeholder_async
    
    返回结果包含:
    - time_placeholders: 生成的时间占位符字典
    - time_context: 时间上下文信息
    - time_placeholder_count: 时间占位符数量
    """
    try:
        # 验证必需字段
        required_fields = ["placeholder_name", "placeholder_text", "template_id", "data_source_id"]
        for field in required_fields:
            if not request.get(field):
                raise HTTPException(
                    status_code=400,
                    detail=f"缺少必需字段: {field}"
                )
        
        placeholder_name = request.get("placeholder_name")
        placeholder_text = request.get("placeholder_text")
        template_id = request.get("template_id")
        data_source_id = request.get("data_source_id")
        context_data = request.get("context_data", {})
        
        logger.info(f"🚀 触发异步带上下文占位符分析任务: {placeholder_name}")
        
        # 触发 Celery 任务
        task = analyze_placeholder_with_context_task.delay(
            placeholder_name=placeholder_name,
            placeholder_text=placeholder_text,
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=str(current_user.id),
            context_data=context_data,
            **{k: v for k, v in request.items() if k not in required_fields + ["context_data"]}
        )
        
        logger.info(f"✅ 异步带上下文占位符分析任务已提交: {placeholder_name} (Task ID: {task.id})")
        
        return APIResponse(
            success=True,
            data={
                "task_id": task.id,
                "placeholder_name": placeholder_name,
                "template_id": template_id,
                "data_source_id": data_source_id,
                "context_data": context_data,
                "status": "submitted",
                "message": "带上下文的占位符分析任务已提交，请使用 task_id 查询进度"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 触发异步带上下文占位符分析任务失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"触发异步带上下文占位符分析任务失败: {str(e)}"
        )


@router.get("/task-status/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def get_placeholder_analysis_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """
    获取占位符分析任务状态
    
    查询指定任务ID的执行状态和结果
    包含生成的时间占位符信息，用于后续任务的时间参数替换
    """
    try:
        from celery.result import AsyncResult
        
        # 获取任务结果
        result = AsyncResult(task_id)
        
        if result.state == 'PENDING':
            # 任务还在等待执行
            status_data = {
                "task_id": task_id,
                "status": "pending",
                "state": result.state,
                "message": "任务等待执行中"
            }
        elif result.state == 'PROGRESS':
            # 任务正在执行
            meta = result.info or {}
            status_data = {
                "task_id": task_id,
                "status": "running",
                "state": result.state,
                "progress": meta.get("progress", 0),
                "current_step": meta.get("current_step", "执行中"),
                "message": meta.get("current_step", "任务执行中"),
                "meta": meta
            }
        elif result.state == 'SUCCESS':
            # 任务执行成功
            task_result = result.result
            status_data = {
                "task_id": task_id,
                "status": "completed",
                "state": result.state,
                "progress": 100,
                "message": "任务执行完成",
                "result": task_result,
                # 添加时间占位符信息
                "time_placeholders": task_result.get('time_placeholders', {}),
                "time_context": task_result.get('time_context', {}),
                "time_placeholder_count": task_result.get('time_placeholder_count', 0)
            }
        elif result.state == 'FAILURE':
            # 任务执行失败
            error_info = result.info or {}
            status_data = {
                "task_id": task_id,
                "status": "failed",
                "state": result.state,
                "progress": 0,
                "message": "任务执行失败",
                "error": str(result.result) if result.result else "未知错误",
                "error_info": error_info
            }
        else:
            # 其他状态
            status_data = {
                "task_id": task_id,
                "status": "unknown",
                "state": result.state,
                "message": f"任务状态: {result.state}"
            }
        
        return APIResponse(
            success=True,
            data=status_data
        )
        
    except Exception as e:
        logger.error(f"❌ 获取任务状态失败: {task_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取任务状态失败: {str(e)}"
        )


@router.post("/cancel-task/{task_id}", response_model=APIResponse[Dict[str, Any]])
async def cancel_placeholder_analysis_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """
    取消占位符分析任务
    
    取消指定任务ID的执行
    """
    try:
        from celery.result import AsyncResult
        
        # 获取任务结果
        result = AsyncResult(task_id)
        
        # 撤销任务
        result.revoke(terminate=True)
        
        logger.info(f"✅ 占位符分析任务已取消: {task_id}")
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "cancelled",
                "message": "任务已成功取消"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 取消任务失败: {task_id}, 错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"取消任务失败: {str(e)}"
        )
