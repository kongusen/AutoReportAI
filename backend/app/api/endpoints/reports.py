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
from app.services.intelligent_report_service import IntelligentReportService

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
            items=[{
                **ReportHistoryResponse.model_validate(report).model_dump(),
                "name": f"报告 #{report.id}",  # 添加默认名称
                "file_size": 0,  # 添加默认文件大小
            } for report in reports],
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


from pydantic import BaseModel

class ReportGenerateRequest(BaseModel):
    template_id: str
    data_source_id: str
    name: Optional[str] = None
    description: Optional[str] = None

class IntelligentReportGenerateRequest(BaseModel):
    template_id: str
    data_source_id: str
    optimization_level: Optional[str] = "standard"  # standard, high_performance, memory_optimized
    enable_intelligent_etl: Optional[bool] = True
    batch_size: Optional[int] = 10000
    name: Optional[str] = None
    description: Optional[str] = None

@router.post("/generate", response_model=ApiResponse)
async def generate_report(
    request: ReportGenerateRequest,
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
        tpl_uuid = UUID(request.template_id)
        ds_uuid = UUID(request.data_source_id)
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
    
    # 在后台生成报告
    background_tasks.add_task(
        generate_report_task,
        template_id=str(tpl_uuid),
        data_source_id=str(ds_uuid),
        user_id=str(user_id),
        task_id=task.id
    )
    return ApiResponse(
        success=True,
        data={
            "task_id": task.id,
            "status": "pending",
            "message": "报告生成任务已提交"
        },
        message="报告生成任务已提交"
    )


@router.post("/generate/intelligent", response_model=ApiResponse)
async def generate_intelligent_report(
    request: IntelligentReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """智能报告生成 - 支持大数据处理和ETL优化"""
    from app.models.template import Template
    from app.models.data_source import DataSource
    from app.models.task import Task
    from uuid import UUID
    
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
        
    # 强制参数转UUID
    try:
        tpl_uuid = UUID(request.template_id)
        ds_uuid = UUID(request.data_source_id)
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
        
    # 查找或创建任务
    task = db.query(Task).filter(
        Task.owner_id == user_id,
        Task.template_id == tpl_uuid,
        Task.data_source_id == ds_uuid
    ).order_by(Task.id.desc()).first()
    
    if not task:
        # 创建新任务
        from app.schemas.task import TaskCreate
        task_data = TaskCreate(
            name=request.name or f"智能报告任务-{template.name}",
            description=request.description or f"基于模板{template.name}的智能报告生成",
            template_id=tpl_uuid,
            data_source_id=ds_uuid,
            schedule_type="once"
        )
        from app.crud.crud_task import crud_task
        task = crud_task.create_with_owner(db=db, obj_in=task_data, owner_id=user_id)
        
    # 创建报告历史记录
    task_data = ReportHistoryCreate(
        task_id=task.id,
        user_id=user_id,
        status="pending"
    )
    
    # 在后台生成智能报告
    background_tasks.add_task(
        generate_intelligent_report_task,
        template_id=str(tpl_uuid),
        data_source_id=str(ds_uuid),
        user_id=str(user_id),
        optimization_level=request.optimization_level,
        enable_intelligent_etl=request.enable_intelligent_etl,
        batch_size=request.batch_size
    )
    
    return ApiResponse(
        success=True,
        data={
            "task_id": task_data.task_id,
            "status": "pending",
            "optimization_level": request.optimization_level,
            "batch_size": request.batch_size,
            "message": "智能报告生成任务已提交"
        },
        message="智能报告生成任务已提交，支持大数据处理和ETL优化"
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
        data={
            **ReportHistoryResponse.model_validate(report).model_dump(),
            "name": f"报告 #{report.id}",
            "file_size": 0,
        },
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
    user_id: str,
    task_id: int
):
    """后台生成报告任务 - 使用智能报告服务"""
    try:
        # 首先创建报告历史记录
        from app.db.session import get_db_session
        with get_db_session() as db:
            from app.schemas.report_history import ReportHistoryCreate
            from uuid import UUID
            from app.crud.crud_report_history import report_history
            
            # 创建报告历史记录
            report_data = ReportHistoryCreate(
                task_id=task_id,
                user_id=UUID(user_id),
                status="pending"
            )
            report_record = report_history.create(db=db, obj_in=report_data)
            db.commit()
        
        # 初始化智能报告服务
        intelligent_report_service = IntelligentReportService()
        
        # 生成智能报告
        result = await intelligent_report_service.generate_intelligent_report(
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=user_id
        )
        
        # 更新报告状态
        from app.db.session import get_db_session
        with get_db_session() as db:
            report = db.query(ReportHistory).filter(
                ReportHistory.task_id == task_id
            ).order_by(ReportHistory.id.desc()).first()
            
            if report:
                report.status = "completed"
                report.result = result.get("filled_template", "")
                report.metadata = result.get("processing_metadata", {})
                db.commit()
        
        return result
        
    except Exception as e:
        # 更新报告状态为失败
        from app.db.session import get_db_session
        with get_db_session() as db:
            report = db.query(ReportHistory).filter(
                ReportHistory.task_id == task_id
            ).order_by(ReportHistory.id.desc()).first()
            
            if report:
                report.status = "failed"
                report.error_message = str(e)
                db.commit()
        
        raise e


async def generate_intelligent_report_task(
    template_id: str,
    data_source_id: str,
    user_id: str,
    optimization_level: str = "standard",
    enable_intelligent_etl: bool = True,
    batch_size: int = 10000
):
    """后台智能报告生成任务"""
    try:
        # 初始化智能报告服务，支持优化参数
        intelligent_report_service = IntelligentReportService()
        
        # 根据优化级别配置参数
        config = {
            "optimization_level": optimization_level,
            "enable_intelligent_etl": enable_intelligent_etl,
            "batch_size": batch_size
        }
        
        if optimization_level == "high_performance":
            config["batch_size"] = min(batch_size, 5000)  # 小批次处理
            config["enable_caching"] = True
            config["parallel_processing"] = True
        elif optimization_level == "memory_optimized":
            config["batch_size"] = min(batch_size, 1000)  # 极小批次
            config["streaming_mode"] = True
            config["memory_threshold"] = 0.8
        
        # 生成智能报告
        result = await intelligent_report_service.generate_intelligent_report_with_config(
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=user_id,
            config=config
        )
        
        # 更新报告状态
        from app.db.session import get_db_session
        with get_db_session() as db:
            from app.models.task import Task
            from uuid import UUID
            
            task = db.query(Task).filter(
                Task.owner_id == UUID(user_id),
                Task.template_id == UUID(template_id),
                Task.data_source_id == UUID(data_source_id)
            ).order_by(Task.id.desc()).first()
            
            if task:
                report = db.query(ReportHistory).filter(
                    ReportHistory.task_id == task.id
                ).order_by(ReportHistory.id.desc()).first()
                
                if report:
                    report.status = "completed"
                    report.result = result.get("filled_template", "")
                    report.metadata = {
                        **result.get("processing_metadata", {}),
                        "optimization_level": optimization_level,
                        "batch_size": batch_size,
                        "intelligent_etl_enabled": enable_intelligent_etl
                    }
                    db.commit()
        
        return result
        
    except Exception as e:
        # 更新报告状态为失败
        from app.db.session import get_db_session
        with get_db_session() as db:
            from app.models.task import Task
            from uuid import UUID
            
            task = db.query(Task).filter(
                Task.owner_id == UUID(user_id),
                Task.template_id == UUID(template_id),
                Task.data_source_id == UUID(data_source_id)
            ).order_by(Task.id.desc()).first()
            
            if task:
                report = db.query(ReportHistory).filter(
                    ReportHistory.task_id == task.id
                ).order_by(ReportHistory.id.desc()).first()
                
                if report:
                    report.status = "failed"
                    report.error_message = str(e)
                    report.metadata = {
                        "optimization_level": optimization_level,
                        "batch_size": batch_size,
                        "error_type": type(e).__name__
                    }
                    db.commit()
        
        raise e


async def regenerate_report_task(report_id: int):
    """后台重新生成报告任务"""
    # 这里应该实现实际的报告重新生成逻辑
    pass
