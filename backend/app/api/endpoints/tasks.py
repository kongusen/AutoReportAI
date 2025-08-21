from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.crud.crud_task import crud_task
from app.services.application.task_management.core.worker import celery_app

# 引入统一的占位符处理架构
from app.services.domain.placeholder import create_batch_router

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_tasks(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务列表"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    query = db.query(Task).filter(Task.owner_id == user_id)
    
    if is_active is not None:
        query = query.filter(Task.is_active == is_active)
    
    if search:
        query = query.filter(Task.name.contains(search))
    
    total = query.count()
    tasks = query.offset(skip).limit(limit).all()
    
    # 转换为TaskResponse格式，保持向后兼容
    task_dicts = []
    for task in tasks:
        # 构建兼容的任务数据，包含新字段但有默认值
        task_dict = {
            # 原有字段
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "template_id": str(task.template_id) if task.template_id else None,
            "data_source_id": str(task.data_source_id) if task.data_source_id else None,
            "schedule": task.schedule,
            "report_period": task.report_period.value if task.report_period else "monthly",
            "recipients": task.recipients or [],
            "owner_id": str(task.owner_id) if task.owner_id else None,
            "is_active": task.is_active,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "unique_id": str(task.id),
            
            # 新增字段（可选，有默认值，保持前端兼容）
            "status": task.status.value if hasattr(task, 'status') and task.status else "pending",
            "processing_mode": task.processing_mode.value if hasattr(task, 'processing_mode') and task.processing_mode else "intelligent",
            "workflow_type": task.workflow_type.value if hasattr(task, 'workflow_type') and task.workflow_type else "simple_report",
            "execution_count": getattr(task, 'execution_count', 0),
            "success_count": getattr(task, 'success_count', 0),
            "failure_count": getattr(task, 'failure_count', 0),
            "success_rate": task.success_rate if hasattr(task, 'success_rate') else 0.0,
            "last_execution_at": task.last_execution_at.isoformat() if hasattr(task, 'last_execution_at') and task.last_execution_at else None,
            "average_execution_time": getattr(task, 'average_execution_time', 0.0),
            "max_context_tokens": getattr(task, 'max_context_tokens', 32000),
            "enable_compression": getattr(task, 'enable_compression', True)
        }
        task_dicts.append(task_dict)
    
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=task_dicts,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


@router.post("/", response_model=ApiResponse)
async def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建任务"""
    try:
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        task = crud_task.create_with_user(db, obj_in=task_in, user_id=user_id)
        task_schema = TaskResponse.model_validate(task)
        task_dict = task_schema.model_dump()
        return ApiResponse(
            success=True,
            data=task_dict,
            message="任务创建成功"
        )
    except Exception as e:
        db.rollback()
        return ApiResponse(
            success=False,
            error=str(e),
            message="任务创建失败"
        )


@router.put("/{task_id}", response_model=ApiResponse)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新任务"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = crud_task.update(db, db_obj=task, obj_in=task_in)
    task_schema = TaskResponse.model_validate(task)
    task_dict = task_schema.model_dump()
    return ApiResponse(
        success=True,
        data=task_dict,
        message="任务更新成功"
    )


@router.get("/{task_id}", response_model=ApiResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个任务"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_schema = TaskResponse.model_validate(task)
    task_dict = task_schema.model_dump()
    return ApiResponse(
        success=True,
        data=task_dict,
        message="获取任务成功"
    )


@router.delete("/{task_id}", response_model=ApiResponse)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除任务"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    crud_task.remove(db, id=task_id)
    return ApiResponse(
        success=True,
        data={"task_id": task_id},
        message="任务删除成功"
    )


@router.post("/{task_id}/execute", response_model=ApiResponse)
async def execute_task(
    task_id: int,
    execution_time: Optional[str] = Query(None, description="任务执行时间 (YYYY-MM-DD HH:MM:SS，默认为当前时间)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """执行任务 - 统一使用智能占位符驱动的流水线"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权限访问")

    # 处理执行时间参数
    try:
        if execution_time:
            parsed_execution_time = datetime.fromisoformat(execution_time.replace('Z', '+00:00'))
        else:
            parsed_execution_time = datetime.now()
            
        # 从任务设置中获取报告周期
        report_period = task.report_period.value if task.report_period else "monthly"
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"无效的时间格式: {str(e)}")

    # 发送一个Celery任务来异步执行智能报告生成
    try:
        # 在Redis中保存任务所有者信息以便进度通知
        from app.core.config import settings
        import redis.asyncio as redis
        
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        import asyncio
        asyncio.create_task(redis_client.set(f"report_task:{task.id}:owner", str(user_id), ex=3600))
        
        # 立即设置初始任务状态
        initial_status = {
            "status": "processing", 
            "progress": "0",
            "message": "任务已提交，正在初始化...",
            "current_step": "任务初始化",
            "user_id": str(user_id),
            "execution_time": parsed_execution_time.isoformat(),
            "report_period": report_period,
            "updated_at": datetime.now().isoformat()
        }
        asyncio.create_task(redis_client.hset(f"report_task:{task.id}:status", mapping=initial_status))
        
        # 统一使用智能占位符驱动的报告生成流水线
        execution_context = {
            "execution_time": parsed_execution_time.isoformat(),
            "report_period": report_period,
            "period_start": None,  # 稍后计算
            "period_end": None     # 稍后计算
        }
        
        task_result = celery_app.send_task(
            "app.services.application.task_management.core.worker.tasks.enhanced_tasks.intelligent_report_generation_pipeline", 
            args=[task.id, str(user_id), execution_context]
        )
        
        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "celery_task_id": str(task_result.id),
                "status": "queued",
                "processing_mode": "intelligent"
            },
            message="智能占位符报告生成任务已加入队列"
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            error=str(e),
            message="任务执行失败"
        )


@router.post("/{task_id}/run", response_model=ApiResponse)
async def run_task(
    task_id: int,
    execution_time: Optional[str] = Query(None, description="任务执行时间 (YYYY-MM-DD HH:MM:SS，默认为当前时间)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """运行任务 - /execute 接口的别名，提供更直观的接口"""
    # 直接调用 execute_task 函数，复用相同的逻辑
    return await execute_task(task_id, execution_time, db, current_user)


@router.get("/{task_id}/status", response_model=ApiResponse)
async def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务执行状态"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权限访问")
    
    # 从Redis获取任务状态
    import redis.asyncio as redis
    from app.core.config import settings
    
    redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        status_data = await redis_client.hgetall(f"report_task:{task_id}:status")
        if not status_data:
            status_data = {"status": "not_started", "progress": 0}
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取任务状态失败: {e}")
        status_data = {"status": "unknown", "progress": 0}
    finally:
        await redis_client.close()
    
    return ApiResponse(
        success=True,
        data={
            "task_id": task_id,
            "task_name": task.name,
            **status_data
        },
        message="获取任务状态成功"
    )


@router.post("/{task_id}/analyze-placeholders", response_model=ApiResponse)
async def analyze_task_placeholders(
    task_id: int,
    force_reanalyze: bool = Query(False, description="是否强制重新分析"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    使用新架构分析任务模板的占位符
    
    这是一个同步操作，会立即返回占位符分析结果
    """
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 获取任务并验证权限
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权限访问")

    # 检查任务状态
    if not task.is_active:
        raise HTTPException(status_code=400, detail="任务未激活，无法分析")

    # 验证模板和数据源
    if not task.template_id or not task.data_source_id:
        raise HTTPException(status_code=400, detail="任务缺少模板或数据源配置")

    try:
        # 使用新架构批量处理模板占位符
        batch_router = create_batch_router(db, str(current_user.id))
        
        execution_context = {
            "execution_time": datetime.now().isoformat(),
            "task_id": str(task_id),
            "task_name": task.name,
            "report_period": task.report_period.value if task.report_period else "monthly",
            "mode": "analysis_only"
        }
        
        result = await batch_router.process_template_placeholders(
            template_id=str(task.template_id),
            data_source_id=str(task.data_source_id),
            user_id=str(current_user.id),
            force_reanalyze=force_reanalyze,
            execution_context=execution_context
        )

        return ApiResponse(
            success=result["success"],
            data={
                "task_id": task_id,
                "task_name": task.name,
                "placeholder_analysis": result,
                "analysis_mode": "new_architecture"
            },
            message="占位符分析完成" if result["success"] else "占位符分析失败"
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"任务占位符分析失败: {task_id}, 错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/{task_id}/dry-run", response_model=ApiResponse)
async def dry_run_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    任务试运行 - 使用新架构进行占位符分析，不生成实际报告
    """
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 获取任务并验证权限
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权限访问")

    # 验证配置
    if not task.template_id or not task.data_source_id:
        raise HTTPException(status_code=400, detail="任务缺少模板或数据源配置")

    try:
        # 使用新架构进行试运行（只分析，不缓存）
        batch_router = create_batch_router(db, str(current_user.id))
        
        execution_context = {
            "execution_time": datetime.now().isoformat(),
            "task_id": str(task_id),
            "dry_run": True,
            "metadata": {"mode": "dry_run"}
        }
        
        result = await batch_router.process_template_placeholders(
            template_id=str(task.template_id),
            data_source_id=str(task.data_source_id),
            user_id=str(current_user.id),
            force_reanalyze=True,  # 试运行总是重新分析
            execution_context=execution_context
        )

        # 生成试运行分析报告
        analysis = _analyze_dry_run_results(result)

        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "task_name": task.name,
                "dry_run_results": result,
                "analysis": analysis,
                "recommendations": _generate_dry_run_recommendations(analysis)
            },
            message="任务试运行完成"
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"任务试运行失败: {task_id}, 错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"试运行失败: {str(e)}")


# 辅助函数

def _analyze_dry_run_results(result: Dict) -> Dict:
    """分析试运行结果"""
    summary = result.get("execution_summary", {})
    results = result.get("results", {})
    
    # 分析各种结果来源
    source_analysis = {
        "cache_hit": 0,
        "agent_success": 0,
        "rule_fallback": 0,
        "error_fallback": 0
    }
    
    confidence_scores = []
    execution_times = []
    
    for placeholder_name, placeholder_result in results.items():
        source = placeholder_result.get("source", "unknown")
        if source in source_analysis:
            source_analysis[source] += 1
        
        confidence = placeholder_result.get("confidence", 0)
        if confidence > 0:
            confidence_scores.append(confidence)
        
        exec_time = placeholder_result.get("execution_time_ms", 0)
        if exec_time > 0:
            execution_times.append(exec_time)
    
    return {
        "source_distribution": source_analysis,
        "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
        "average_execution_time_ms": sum(execution_times) / len(execution_times) if execution_times else 0,
        "total_placeholders": len(results),
        "success_rate": summary.get("success_rate", 0),
        "performance_grade": _calculate_performance_grade(summary, source_analysis)
    }


def _calculate_performance_grade(summary: Dict, source_analysis: Dict) -> str:
    """计算性能评级"""
    success_rate = summary.get("success_rate", 0)
    agent_ratio = source_analysis.get("agent_success", 0) / max(summary.get("total_placeholders", 1), 1)
    
    if success_rate >= 95 and agent_ratio >= 0.8:
        return "A"
    elif success_rate >= 85 and agent_ratio >= 0.6:
        return "B"
    elif success_rate >= 70 and agent_ratio >= 0.4:
        return "C"
    elif success_rate >= 50:
        return "D"
    else:
        return "F"


def _generate_dry_run_recommendations(analysis: Dict) -> List[str]:
    """生成试运行优化建议"""
    recommendations = []
    
    success_rate = analysis.get("success_rate", 0)
    source_dist = analysis.get("source_distribution", {})
    performance_grade = analysis.get("performance_grade", "F")
    
    if success_rate < 80:
        recommendations.append("成功率较低，建议检查数据源连接和占位符配置")
    
    if source_dist.get("rule_fallback", 0) > source_dist.get("agent_success", 0):
        recommendations.append("Agent分析成功率较低，建议优化占位符命名和数据源schema")
    
    if analysis.get("average_execution_time_ms", 0) > 5000:
        recommendations.append("执行时间较长，建议优化SQL查询和数据源性能")
    
    if performance_grade in ["D", "F"]:
        recommendations.append("整体性能较差，建议全面检查系统配置")
    
    if not recommendations:
        recommendations.append("系统运行良好，无需特殊优化")
    
    return recommendations
