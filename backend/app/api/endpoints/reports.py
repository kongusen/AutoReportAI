"""报告管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.report_history import ReportHistory
from app.schemas.report_history import ReportHistoryCreate, ReportHistoryResponse
from app.services.report_generation.generator import ReportGenerationService as ReportGenerator

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_reports(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    status: Optional[str] = Query(None, description="报告状态"),
    template_id: Optional[str] = Query(None, description="模板ID"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取报告历史列表"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    query = db.query(ReportHistory).join(
        ReportHistory.task
    ).filter(
        ReportHistory.task.has(owner_id=user_id)
    )
    
    if status:
        query = query.filter(ReportHistory.status == status)
    
    if template_id:
        query = query.filter(ReportHistory.task.has(template_id=template_id))
    
    if search:
        query = query.filter(ReportHistory.task.has(name=search))
    
    total = query.count()
    reports = query.offset(skip).limit(limit).all()
    
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=reports,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


@router.post("/generate", response_model=ApiResponse)
async def generate_report(
    template_id: str,
    data_source_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成报告"""
    from app.models.template import Template
    from app.models.data_source import DataSource
    from app.models.task import Task
    from uuid import UUID
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    # 强制参数转UUID
    try:
        tpl_uuid = UUID(template_id)
        ds_uuid = UUID(data_source_id)
    except Exception:
        raise HTTPException(status_code=422, detail="模板ID或数据源ID格式错误")
    # 验证模板和数据源
    template = db.query(Template).filter(
        Template.id == tpl_uuid,
        Template.user_id == user_id
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    data_source = db.query(DataSource).filter(
        DataSource.id == ds_uuid,
        DataSource.user_id == user_id
    ).first()
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
    # 查找当前用户下与模板和数据源匹配的任务
    task = db.query(Task).filter(
        Task.owner_id == user_id,
        Task.template_id == tpl_uuid,
        Task.data_source_id == ds_uuid
    ).order_by(Task.id.desc()).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到匹配的任务"
        )
    # 创建报告历史记录（仅作示例，实际生成后再插入更合理）
    task_data = ReportHistoryCreate(
        task_id=task.id,
        user_id=user_id,
        status="pending"
    )
    # 在后台生成报告
    background_tasks.add_task(
        generate_report_task,
        template_id=str(tpl_uuid),
        data_source_id=str(ds_uuid),
        user_id=str(user_id)
    )
    return ApiResponse(
        success=True,
        data={
            "task_id": task_data.task_id,
            "status": "pending",
            "message": "报告生成任务已提交"
        },
        message="报告生成任务已提交"
    )


@router.get("/{report_id}", response_model=ApiResponse)
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取特定报告"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    report = db.query(ReportHistory).join(
        ReportHistory.task
    ).filter(
        ReportHistory.id == report_id,
        ReportHistory.task.has(owner_id=user_id)
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在或无权限访问"
        )
    
    return ApiResponse(
        success=True,
        data=report,
        message="获取报告成功"
    )


@router.delete("/{report_id}", response_model=ApiResponse)
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除报告"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    report = db.query(ReportHistory).join(
        ReportHistory.task
    ).filter(
        ReportHistory.id == report_id,
        ReportHistory.task.has(owner_id=user_id)
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在或无权限访问"
        )
    
    db.delete(report)
    db.commit()
    
    return ApiResponse(
        success=True,
        data={"report_id": report_id},
        message="报告删除成功"
    )


@router.post("/{report_id}/regenerate", response_model=ApiResponse)
async def regenerate_report(
    report_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重新生成报告"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    report = db.query(ReportHistory).join(
        ReportHistory.task
    ).filter(
        ReportHistory.id == report_id,
        ReportHistory.task.has(owner_id=user_id)
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在或无权限访问"
        )
    
    # 更新状态为重新生成
    report.status = "regenerating"
    db.commit()
    
    # 在后台重新生成
    background_tasks.add_task(
        regenerate_report_task,
        report_id=report_id
    )
    
    return ApiResponse(
        success=True,
        data={
            "report_id": report_id,
            "status": "regenerating",
            "message": "报告重新生成任务已提交"
        },
        message="报告重新生成任务已提交"
    )


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载报告"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    report = db.query(ReportHistory).join(
        ReportHistory.task
    ).filter(
        ReportHistory.id == report_id,
        ReportHistory.task.has(owner_id=user_id)
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告不存在或无权限访问"
        )
    
    if report.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="报告尚未完成生成"
        )
    
    # 这里应该实现实际的文件下载逻辑
    return ApiResponse(
        success=True,
        data={
            "download_url": f"/api/v2/reports/{report_id}/download/file",
            "filename": f"report_{report_id}.docx"
        },
        message="报告下载链接已生成"
    )


async def generate_report_task(
    template_id: str,
    data_source_id: str,
    user_id: str
):
    """后台生成报告任务"""
    # 这里应该实现实际的报告生成逻辑
    pass


async def regenerate_report_task(report_id: int):
    """后台重新生成报告任务"""
    # 这里应该实现实际的报告重新生成逻辑
    pass
