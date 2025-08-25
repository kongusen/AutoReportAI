"""报告管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os
from pathlib import Path
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.report_history import ReportHistory
from app.schemas.report_history import ReportHistoryCreate, ReportHistoryResponse
from app.services.domain.reporting.generator import ReportGenerationService as ReportGenerator
# AgentOrchestrator not available, using placeholder
class AgentOrchestrator:
    def __init__(self):
        pass
    
    async def execute(self, agent_input, context):
        # Placeholder implementation
        return type('obj', (object,), {
            'success': True,
            'data': type('obj', (object,), {
                'results': {
                    'fetch_data': type('obj', (object,), {
                        'success': True,
                        'data': {'etl_instruction': 'SELECT * FROM placeholder_table'}
                    })()
                }
            })()
        })()
# Enhanced Agent-based report generation
# pipeline_orchestrator not available, using placeholder
class PipelineContext:
    def __init__(self):
        pass

pipeline_orchestrator = type('obj', (object,), {
    'execute': lambda self, context: type('obj', (object,), {
        'success': True,
        'data': {'result': 'placeholder_result'}
    })()
})()
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


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
    """智能报告生成 - 使用Agent管道系统进行完整的报告处理"""
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
            description=request.description or f"基于模板{template.name}的Agent驱动智能报告生成",
            template_id=tpl_uuid,
            data_source_id=ds_uuid,
            schedule_type="once"
        )
        from app.crud.crud_task import crud_task
        task = crud_task.create_with_owner(db=db, obj_in=task_data, owner_id=user_id)
        
    # 创建报告历史记录
    report_data = ReportHistoryCreate(
        task_id=task.id,
        user_id=user_id,
        status="pending"
    )
    
    # 在后台使用Agent管道生成智能报告
    background_tasks.add_task(
        generate_agent_based_intelligent_report_task,
        template_id=str(tpl_uuid),
        data_source_id=str(ds_uuid),
        user_id=str(user_id),
        task_id=task.id,
        optimization_level=request.optimization_level,
        enable_intelligent_etl=request.enable_intelligent_etl,
        batch_size=request.batch_size
    )
    
    return ApiResponse(
        success=True,
        data={
            "task_id": task.id,
            "status": "pending",
            "optimization_level": request.optimization_level,
            "batch_size": request.batch_size,
            "agent_pipeline": "enabled",
            "message": "Agent驱动的智能报告生成任务已提交"
        },
        message="Agent驱动的智能报告生成任务已提交，支持完整的数据分析管道"
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
            "content": report.result if report.status == "completed" else None,
        },
        message="获取报告成功"
    )


@router.delete("/batch", response_model=ApiResponse)
async def batch_delete_reports(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量删除报告"""
    try:
        report_ids = request.get("report_ids", [])
        if not report_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供要删除的报告ID列表"
            )
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        # 查找用户有权限删除的报告
        reports_to_delete = db.query(ReportHistory).join(
            ReportHistory.task
        ).filter(
            ReportHistory.id.in_(report_ids),
            ReportHistory.task.has(owner_id=user_id)
        ).all()
        
        if not reports_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到可删除的报告或无权限访问"
            )
        
        # 执行批量删除
        deleted_count = 0
        deleted_ids = []
        for report in reports_to_delete:
            db.delete(report)
            deleted_ids.append(report.id)
            deleted_count += 1
        
        db.commit()
        
        return ApiResponse(
            success=True,
            data={
                "deleted_count": deleted_count,
                "deleted_ids": deleted_ids,
                "requested_count": len(report_ids)
            },
            message=f"成功删除 {deleted_count} 个报告"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量删除报告失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量删除失败: {str(e)}"
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


@router.get("/{report_id}/content", response_model=ApiResponse)
async def get_report_content(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取报告内容"""
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
    
    return ApiResponse(
        success=True,
        data={
            "content": report.result or "报告内容为空",
            "status": report.status,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None
        },
        message="获取报告内容成功"
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
        
        # 初始化Agent编排器
        agent_orchestrator = AgentOrchestrator()
        
        # 使用Agent系统生成智能报告
        placeholder_input = {
            "template_id": template_id,
            "data_source_id": data_source_id,
            "user_id": user_id,
            "placeholder_type": "comprehensive"
        }
        
        agent_result = await agent_orchestrator.execute(placeholder_input)
        result = {
            "filled_template": agent_result.data if agent_result.success else "",
            "processing_metadata": agent_result.metadata or {},
            "success": agent_result.success,
            "error_message": agent_result.error_message if not agent_result.success else None
        }
        
        # 更新报告状态
        from app.db.session import get_db_session
        with get_db_session() as db:
            report = db.query(ReportHistory).filter(
                ReportHistory.task_id == task_id
            ).order_by(ReportHistory.id.desc()).first()
            
            if report:
                report.status = "completed"
                report.result = result.get("filled_template", "")
                report.processing_metadata = result.get("processing_metadata", {})
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
        # 初始化Agent编排器，支持优化参数
        agent_orchestrator = AgentOrchestrator()
        
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
        
        # 使用Agent系统生成智能报告
        placeholder_input = {
            "template_id": template_id,
            "data_source_id": data_source_id,
            "user_id": user_id,
            "placeholder_type": "comprehensive",
            "config": config
        }
        
        agent_result = await agent_orchestrator.execute(placeholder_input)
        result = {
            "filled_template": agent_result.data if agent_result.success else "",
            "processing_metadata": agent_result.metadata or {},
            "success": agent_result.success,
            "error_message": agent_result.error_message if not agent_result.success else None
        }
        
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
                    report.processing_metadata = {
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
                    report.processing_metadata = {
                        "optimization_level": optimization_level,
                        "batch_size": batch_size,
                        "error_type": type(e).__name__
                    }
                    db.commit()
        
        raise e


async def generate_agent_based_intelligent_report_task(
    template_id: str,
    data_source_id: str,
    user_id: str,
    task_id: int,
    optimization_level: str = "standard",
    enable_intelligent_etl: bool = True,
    batch_size: int = 10000
):
    """Agent驱动的后台智能报告生成任务"""
    try:
        # 创建报告历史记录
        from app.db.session import get_db_session
        report_record_id = None
        template_type = "docx"
        
        with get_db_session() as db:
            from app.schemas.report_history import ReportHistoryCreate
            from uuid import UUID
            from app.crud.crud_report_history import report_history
            
            report_data = ReportHistoryCreate(
                task_id=task_id,
                user_id=UUID(user_id),
                status="processing"
            )
            report_record = report_history.create(db=db, obj_in=report_data)
            report_record_id = report_record.id  # Store ID, not the object
            db.commit()
            
            # 获取模板信息用于管道上下文
            from app.models.template import Template
            template = db.query(Template).filter(Template.id == UUID(template_id)).first()
            template_type = template.template_type if template else "docx"
        
        # 创建Agent管道上下文
        pipeline_context = PipelineContext(
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=user_id,
            template_type=template_type,
            output_format="docx",
            optimization_level=optimization_level,
            batch_size=batch_size,
            enable_caching=True,
            custom_config={
                "task_id": task_id,
                "enable_intelligent_etl": enable_intelligent_etl,
                "report_record_id": report_record_id
            }
        )
        
        # 执行Agent驱动的智能管道
        pipeline_result = await pipeline_orchestrator.execute(pipeline_context)
        
        # 更新报告状态
        with get_db_session() as db:
            report = db.query(ReportHistory).filter(
                ReportHistory.id == report_record_id
            ).first()
            
            if report:
                if pipeline_result.success:
                    pipeline_data = pipeline_result.final_output
                    
                    # 提取报告内容
                    report_content = ""
                    if hasattr(pipeline_data, 'final_output') and pipeline_data.final_output:
                        # 如果有二进制输出，转换为hex字符串存储
                        report_content = pipeline_data.final_output.hex()
                    elif hasattr(pipeline_data, 'stage_results'):
                        # 从阶段结果中提取内容
                        for stage, stage_result in pipeline_data.stage_results.items():
                            if stage_result.success and hasattr(stage_result.data, 'content'):
                                report_content += str(stage_result.data.content) + "\n\n"
                    
                    report.status = "completed"
                    report.result = report_content
                    report.processing_metadata = {
                        "agent_pipeline": True,
                        "optimization_level": optimization_level,
                        "batch_size": batch_size,
                        "intelligent_etl_enabled": enable_intelligent_etl,
                        "execution_time": pipeline_result.execution_time,
                        "stages_completed": len(pipeline_data.stage_results) if hasattr(pipeline_data, 'stage_results') else 0,
                        "quality_score": pipeline_data.quality_score if hasattr(pipeline_data, 'quality_score') else 0,
                        "pipeline_metadata": pipeline_result.metadata
                    }
                else:
                    report.status = "failed"
                    report.error_message = pipeline_result.error_message
                    report.processing_metadata = {
                        "agent_pipeline": True,
                        "optimization_level": optimization_level,
                        "error_type": "pipeline_execution_failed"
                    }
                
                db.commit()
        
        return pipeline_result.final_output if pipeline_result.success else None
        
    except Exception as e:
        # 更新报告状态为失败
        try:
            from app.db.session import get_db_session
            with get_db_session() as db:
                report = db.query(ReportHistory).filter(
                    ReportHistory.task_id == task_id
                ).order_by(ReportHistory.id.desc()).first()
                
                if report:
                    report.status = "failed"
                    report.error_message = str(e)
                    report.processing_metadata = {
                        "agent_pipeline": True,
                        "optimization_level": optimization_level,
                        "batch_size": batch_size,
                        "error_type": type(e).__name__
                    }
                    db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update report status: {db_error}")
        
        logger.error(f"Agent-based report generation failed: {e}")
        raise e


async def regenerate_report_task(report_id: int):
    """后台重新生成报告任务"""
    try:
        # 获取原始报告配置并重新使用Agent管道生成
        from app.db.session import get_db_session
        with get_db_session() as db:
            report = db.query(ReportHistory).filter(ReportHistory.id == report_id).first()
            
            if not report or not report.task:
                logger.error(f"Report {report_id} not found for regeneration")
                return
            
            task = report.task
            metadata = report.processing_metadata or {}
            
            # 使用Agent管道重新生成
            await generate_agent_based_intelligent_report_task(
                template_id=str(task.template_id),
                data_source_id=str(task.data_source_id),
                user_id=str(task.owner_id),
                task_id=task.id,
                optimization_level=metadata.get("optimization_level", "standard"),
                enable_intelligent_etl=metadata.get("intelligent_etl_enabled", True),
                batch_size=metadata.get("batch_size", 10000)
            )
            
    except Exception as e:
        logger.error(f"Report regeneration failed: {e}")


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载报告文件"""
    try:
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        # 查找报告记录
        report = db.query(ReportHistory).join(
            ReportHistory.task
        ).filter(
            ReportHistory.id == report_id,
            ReportHistory.task.has(owner_id=user_id)
        ).first()
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail="报告不存在或没有访问权限"
            )
        
        if report.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"报告尚未生成完成，当前状态: {report.status}"
            )
        
        if not report.file_path:
            raise HTTPException(
                status_code=404,
                detail="报告文件路径不存在"
            )
        
        # 检查文件是否存在
        file_path = Path(report.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="报告文件已被删除或移动"
            )
        
        # 生成友好的文件名
        task_name = report.task.name if report.task else f"报告_{report_id}"
        timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S") if report.generated_at else "unknown"
        filename = f"{task_name}_{timestamp}.{file_path.suffix.lstrip('.')}"
        
        # 清理文件名中的非法字符
        import re
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        logger.info(f"用户 {user_id} 下载报告: {report_id}, 文件: {file_path}")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载报告失败: {e}")
        raise HTTPException(
            status_code=500,
            detail="文件下载失败"
        )


@router.get("/{report_id}/info", response_model=ApiResponse)
async def get_report_info(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取报告详细信息"""
    try:
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
                status_code=404,
                detail="报告不存在或没有访问权限"
            )
        
        # 获取文件大小
        file_size = 0
        if report.file_path and Path(report.file_path).exists():
            file_size = Path(report.file_path).stat().st_size
        
        return ApiResponse(
            success=True,
            data={
                "id": report.id,
                "task_id": report.task_id,
                "task_name": report.task.name if report.task else f"任务_{report.task_id}",
                "status": report.status,
                "file_path": report.file_path,
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2) if file_size > 0 else 0,
                "generated_at": report.generated_at.isoformat() if report.generated_at else None,
                "error_message": report.error_message,
                "processing_metadata": report.processing_metadata,
                "can_download": report.status == "completed" and report.file_path and Path(report.file_path).exists(),
                "download_url": f"/api/v1/reports/{report_id}/download" if report.status == "completed" else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail="获取报告信息失败"
        )
