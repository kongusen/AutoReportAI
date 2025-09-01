"""仪表板API端点 - v2版本"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID

from app.core.architecture import ApiResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.services.infrastructure.cache import cache_service, cached
from app.models.user import User
from app.models.data_source import DataSource
from app.models.template import Template
from app.models.task import Task
from app.models.report_history import ReportHistory
from app.models.etl_job import ETLJob
from app.models.llm_server import LLMServer

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_dashboard_overview(
    db: Session = Depends(get_db)
):
    """
    获取仪表盘概览（无需认证）
    """
    # 使用CRUD层获取系统统计
    from app.crud import user as crud_user, template as crud_template, task as crud_task
    from app.crud.crud_data_source import crud_data_source
    
    total_users = crud_user.get_count(db)
    total_data_sources = crud_data_source.get_count(db)
    total_templates = crud_template.get_count(db)
    total_tasks = crud_task.get_count(db)
    
    return ApiResponse(
        success=True,
        data={
            "system_stats": {
                "total_users": total_users,
                "total_data_sources": total_data_sources,
                "total_templates": total_templates,
                "total_tasks": total_tasks,
                "status": "operational"
            },
            "system_info": {
                "version": "v1.0.0",
                "uptime": "系统运行中",
                "features": [
                    "AI报告生成",
                    "智能数据处理", 
                    "多数据源支持",
                    "模板管理"
                ]
            }
        },
        message="系统概览获取成功"
    )


@router.get("/stats", response_model=ApiResponse)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取仪表盘统计数据（严格用户隔离）
    带缓存优化：数据缓存5分钟
    """
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)

    # 尝试从缓存获取数据
    cache_key = f"dashboard_stats:{user_id}"
    cached_data = cache_service.get_dashboard_data(str(user_id))
    
    if cached_data is not None:
        return ApiResponse(
            success=True,
            data=cached_data,
            message="获取仪表盘统计数据成功（缓存）"
        )

    # 缓存未命中，从数据库获取
    from app.crud import template as crud_template, task as crud_task
    from app.crud.crud_data_source import crud_data_source
    from app.crud.crud_report_history import report_history
    
    data_sources_count = crud_data_source.get_count_by_user(db, user_id=user_id)
    templates_count = crud_template.get_count_by_user(db, user_id=user_id)
    tasks_count = crud_task.get_count_by_user(db, user_id=user_id)
    reports_count = report_history.get_count_by_user(db, user_id=user_id)
    active_tasks_count = crud_task.get_active_count_by_user(db, user_id=user_id)
    
    # 计算成功率
    total_reports = reports_count
    successful_reports = report_history.get_successful_count_by_user(db, user_id=user_id)
    success_rate = (successful_reports / total_reports * 100) if total_reports > 0 else 0

    # 构建响应数据
    dashboard_data = {
        "data_sources": data_sources_count,
        "templates": templates_count,
        "tasks": tasks_count,
        "reports": reports_count,
        "active_tasks": active_tasks_count,
        "success_rate": round(success_rate, 2)
    }
    
    # 缓存数据（5分钟TTL）
    cache_service.cache_dashboard_data(str(user_id), dashboard_data, ttl=300)

    return ApiResponse(
        success=True,
        data=dashboard_data,
        message="获取仪表盘统计数据成功"
    )


@router.get("/recent-activity", response_model=ApiResponse)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="返回的记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取最近活动（严格用户隔离）
    """
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)

    # 优化：使用更高效的查询，避免不必要的JOIN
    # 最近生成的报告 - 使用EXISTS而非JOIN以提高性能
    from sqlalchemy import exists
    recent_reports = (
        db.query(ReportHistory)
        .filter(
            db.query(Task)
            .filter(Task.id == ReportHistory.task_id, Task.owner_id == user_id)
            .exists()
        )
        .order_by(ReportHistory.generated_at.desc())
        .limit(limit)
        .all()
    )
    
    # 最近创建的任务 - 添加索引提示
    recent_tasks = (
        db.query(Task)
        .filter(Task.owner_id == user_id)
        .order_by(Task.created_at.desc())
        .limit(limit)
        .all()
    )
    
    # 最近创建的数据源
    recent_data_sources = (
        db.query(DataSource)
        .filter(DataSource.user_id == user_id)
        .order_by(DataSource.created_at.desc())
        .limit(limit)
        .all()
    )

    return ApiResponse(
        success=True,
        data={
            "recent_reports": [
                {
                    "id": report.id,
                    "status": report.status,
                    "generated_at": report.generated_at.isoformat() if report.generated_at else None,
                    "task_name": report.task.name if report.task else None
                }
                for report in recent_reports
            ],
            "recent_tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "created_at": task.created_at.isoformat() if task.created_at else None
                }
                for task in recent_tasks
            ],
            "recent_data_sources": [
                {
                    "id": ds.id,
                    "name": ds.name,
                    "source_type": ds.source_type,
                    "created_at": ds.created_at.isoformat() if ds.created_at else None
                }
                for ds in recent_data_sources
            ]
        },
        message="获取最近活动成功"
    )


@router.get("/chart-data", response_model=ApiResponse)
async def get_chart_data(
    days: int = Query(7, ge=1, le=30, description="天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取图表数据"""
    user_id = current_user.id
    
    # 计算日期范围
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 按日期统计报告生成数量
    report_stats = db.query(
        func.date(ReportHistory.generated_at).label('date'),
        func.count(ReportHistory.id).label('count')
    ).join(
        ReportHistory.task
    ).filter(
        ReportHistory.task.has(owner_id=user_id),
        ReportHistory.generated_at >= start_date,
        ReportHistory.generated_at <= end_date
    ).group_by(
        func.date(ReportHistory.generated_at)
    ).all()
    
    # 按状态统计任务数量
    task_stats = db.query(
        Task.is_active,
        func.count(Task.id).label('count')
    ).filter(
        Task.owner_id == user_id
    ).group_by(
        Task.is_active
    ).all()
    
    # 按类型统计数据源数量
    data_source_stats = db.query(
        DataSource.source_type,
        func.count(DataSource.id).label('count')
    ).filter(
        DataSource.user_id == user_id
    ).group_by(
        DataSource.source_type
    ).all()
    
    return ApiResponse(
        success=True,
        data={
            "report_trend": [
                {
                    "date": str(stat.date),
                    "count": stat.count
                }
                for stat in report_stats
            ],
            "task_status": [
                {
                    "status": "active" if stat.is_active else "inactive",
                    "count": stat.count
                }
                for stat in task_stats
            ],
            "data_source_types": [
                {
                    "type": stat.source_type,
                    "count": stat.count
                }
                for stat in data_source_stats
            ]
        },
        message="获取图表数据成功"
    )


@router.get("/system-health", response_model=ApiResponse)
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取系统健康状态"""
    user_id = current_user.id
    
    # 检查数据源连接状态
    data_sources = db.query(DataSource).filter(
        DataSource.user_id == user_id,
        DataSource.is_active == True
    ).all()
    
    # 检查LLM服务器状态 (替代原AI提供商)
    llm_servers = db.query(LLMServer).filter(
        LLMServer.is_active == True,
        LLMServer.is_healthy == True
    ).all()
    
    # 检查失败的任务
    failed_tasks = db.query(Task).join(
        Task.reports
    ).filter(
        Task.owner_id == user_id,
        ReportHistory.status == "failed"
    ).count()
    
    return ApiResponse(
        success=True,
        data={
            "data_sources": {
                "total": len(data_sources),
                "active": len([ds for ds in data_sources if ds.is_active])
            },
            "llm_servers": {
                "total": len(llm_servers),
                "healthy": len([ls for ls in llm_servers if ls.is_healthy])
            },
            "failed_tasks": failed_tasks,
            "system_status": "healthy"
        },
        message="获取系统健康状态成功"
    )
