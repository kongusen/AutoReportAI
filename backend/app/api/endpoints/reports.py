"""报告管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
import uuid
import os
from pathlib import Path
from uuid import UUID
from datetime import datetime
import io
import zipfile
import csv
import re

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.report_history import ReportHistory
from app.schemas.report_history import ReportHistoryCreate, ReportHistoryResponse
# 使用统一服务门面替代直接跨层调用
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
    
    # 优化：一次性获取数据和总数，避免重复查询
    reports = query.offset(skip).limit(limit).all()
    
    # 如果返回的数据少于limit，且skip为0，则total就是返回数量
    # 否则需要单独查询总数
    if len(reports) < limit and skip == 0:
        total = len(reports)
    else:
        # 重构查询以避免JOIN的count性能问题
        base_filter = ReportHistory.task.has(owner_id=user_id)
        count_query = db.query(ReportHistory).filter(base_filter)
        
        if status:
            count_query = count_query.filter(ReportHistory.status == status)
        if template_id:
            count_query = count_query.filter(ReportHistory.task.has(template_id=template_id))
        if search:
            count_query = count_query.filter(ReportHistory.task.has(name=search))
            
        total = count_query.count()
    
    # 使用统一服务门面获取增强信息
    try:
        from app.services.application.facades.unified_service_facade import create_unified_service_facade
        facade = create_unified_service_facade(db, str(current_user.id))
        
        enhanced_reports = []
        for report in reports:
            report_data = ReportHistoryResponse.model_validate(report).model_dump()
            
            # 添加增强信息
            report_data.update({
                "name": f"报告 #{report.id}",
                "file_size": 0,  # TODO: 从文件存储服务获取实际大小
                "download_url": f"/api/v1/reports/{report.id}/download",
                "preview_available": report.status == "completed"
            })
            enhanced_reports.append(report_data)
            
    except Exception as e:
        logger.warning(f"获取增强信息失败，使用基础信息: {e}")
        enhanced_reports = [{
            **ReportHistoryResponse.model_validate(report).model_dump(),
            "name": f"报告 #{report.id}",
            "file_size": 0,
        } for report in reports]
    
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=enhanced_reports,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


@router.post("/batch/zip", response_model=ApiResponse)
async def download_reports_as_zip(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量打包下载报告为ZIP，并包含清单CSV。

    请求体:
      - report_ids: List[int]
      - filename: Optional[str] 自定义zip文件名（不含扩展名）
      - expires: Optional[int] 预签名链接有效期(秒)，默认86400

    返回:
      ApiResponse: 包含zip文件的预签名下载URL等信息
    """
    try:
        report_ids: List[int] = request.get("report_ids", []) or []
        if not isinstance(report_ids, list) or not report_ids:
            raise HTTPException(status_code=400, detail="请提供要打包的报告ID列表")

        # 限制单次批量数量，避免内存压力
        MAX_BUNDLE = 100
        if len(report_ids) > MAX_BUNDLE:
            raise HTTPException(status_code=400, detail=f"单次最多支持 {MAX_BUNDLE} 个报告")

        expires: int = int(request.get("expires", 86400))
        custom_filename: Optional[str] = request.get("filename")

        # 查询用户有权限的报告
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        reports = db.query(ReportHistory).join(
            ReportHistory.task
        ).filter(
            ReportHistory.id.in_(report_ids),
            ReportHistory.task.has(owner_id=user_id)
        ).all()

        if not reports:
            raise HTTPException(status_code=404, detail="未找到可下载的报告或无权限访问")

        # 存储服务
        from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
        storage = get_hybrid_storage_service()

        # 准备zip与清单
        zip_buffer = io.BytesIO()
        manifest_rows: List[Tuple[int, str, str]] = []  # (序号, 日期, 报告名称)
        included_ids: List[int] = []
        skipped_ids: List[int] = []

        def safe_filename(name: str) -> str:
            # 去除非法字符，保留中英文、数字、-_.和空格
            return re.sub(r'[^\w\-\.\u4e00-\u9fa5\s]', '_', name).strip()

        with zipfile.ZipFile(zip_buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            idx = 1
            for rep in reports:
                # 确保有文件可下载；若无file_path但有内容，生成临时报告文件并上传
                file_path = rep.file_path
                if not file_path:
                    report_content = rep.result
                    if report_content:
                        filename = f"report_{rep.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                        try:
                            upload_info = storage.upload_file(
                                file_data=io.BytesIO(report_content.encode('utf-8')),
                                original_filename=filename,
                                file_type="reports",
                                content_type="text/markdown"
                            )
                            file_path = upload_info.get("file_path")
                            # 更新记录
                            rep.file_path = file_path
                            db.add(rep)
                            db.commit()
                        except Exception as e:
                            logger.error(f"生成报告文件失败: report_id={rep.id}, error={e}")
                            skipped_ids.append(rep.id)
                            continue
                    else:
                        skipped_ids.append(rep.id)
                        continue

                # 下载文件数据
                try:
                    file_data, backend_type = storage.download_file(file_path)
                except Exception as e:
                    logger.error(f"下载报告文件失败: report_id={rep.id}, path={file_path}, error={e}")
                    skipped_ids.append(rep.id)
                    continue

                # 友好文件名
                base = os.path.basename(file_path)
                # 保留原始扩展名
                if '.' in base:
                    name_wo_ext = base.rsplit('.', 1)[0]
                    ext = '.' + base.rsplit('.', 1)[1]
                else:
                    name_wo_ext = base
                    ext = ''

                # 报告生成日期（yyyy-mm-dd）
                gen_dt = rep.generated_at or rep.created_at or datetime.utcnow()
                date_str = gen_dt.strftime('%Y-%m-%d')

                # 压缩内的文件名
                zipped_filename = safe_filename(f"{name_wo_ext}{ext}") or f"report_{rep.id}{ext}"
                # 写入zip，放在reports/目录下
                zf.writestr(f"reports/{zipped_filename}", file_data)

                # 清单行：序号、日期、报告名称（不含扩展名）
                manifest_rows.append((idx, date_str, name_wo_ext))
                included_ids.append(rep.id)
                idx += 1

            # 生成manifest.csv（UTF-8）
            manifest_io = io.StringIO()
            writer = csv.writer(manifest_io)
            writer.writerow(["序号", "日期", "报告名称"])  # 表头
            for row in manifest_rows:
                writer.writerow(list(row))
            zf.writestr("manifest.csv", manifest_io.getvalue().encode('utf-8'))

        # 上传ZIP到存储
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        zip_name = custom_filename.strip() if isinstance(custom_filename, str) and custom_filename.strip() else f"reports_bundle_{ts}"
        zip_name = safe_filename(zip_name) + ".zip"
        zip_buffer.seek(0)
        upload_info = storage.upload_file(
            file_data=zip_buffer,
            original_filename=zip_name,
            file_type="reports",
            content_type="application/zip"
        )
        zip_path = upload_info.get("file_path")
        download_url = storage.get_download_url(zip_path, expires=expires)

        return ApiResponse(
            success=True,
            data={
                "zip_file_path": zip_path,
                "download_url": download_url,
                "included_count": len(included_ids),
                "included_report_ids": included_ids,
                "skipped_report_ids": skipped_ids,
                "expires": expires,
                "filename": zip_name
            },
            message=f"打包完成，包含 {len(included_ids)} 个报告"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量打包下载失败: {e}")
        raise HTTPException(status_code=500, detail="批量打包失败")


@router.get("/{task_id}/download-url", response_model=ApiResponse)
async def get_latest_report_download_url(
    task_id: int,
    expires: int = Query(86400, ge=60, le=7*24*3600, description="下载链接有效期(秒)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务最近一次报告的预签名下载URL（基于存储路径生成）。"""
    try:
        from app.models.task import Task, TaskExecution, TaskStatus
        from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
        
        # 校验任务归属
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.owner_id == current_user.id
        ).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在或无权限")

        # 最近执行记录（完成态优先）
        execution = db.query(TaskExecution).filter(
            TaskExecution.task_id == task_id,
            TaskExecution.execution_status == TaskStatus.COMPLETED
        ).order_by(TaskExecution.completed_at.desc().nullslast(), TaskExecution.id.desc()).first()

        if not execution or not execution.execution_result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到可下载的报告")

        report_info = (execution.execution_result or {}).get("report") or {}
        storage_path = report_info.get("storage_path")
        if not storage_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告未包含存储路径")

        storage = get_hybrid_storage_service()
        url = storage.get_download_url(storage_path, expires=expires)

        return ApiResponse(
            success=True,
            data={
                "task_id": task_id,
                "url": url,
                "storage_path": storage_path,
                "expires": expires
            },
            message="获取下载URL成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告下载URL失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取下载URL失败")


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


@router.get("/{report_id}/download-info")
async def get_report_download_info(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取报告下载信息"""
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
    
    # 检查是否有文件路径存储
    if not report.file_path:
        # 如果没有文件，生成一个临时的内容文件
        try:
            from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
            from io import BytesIO
            import tempfile
            import os
            
            storage_service = get_hybrid_storage_service()
            
            # 创建报告内容文件
            report_content = report.result or "报告内容为空"
            filename = f"report_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            # 上传到存储系统
            file_info = storage_service.upload_file(
                file_data=BytesIO(report_content.encode('utf-8')),
                original_filename=filename,
                file_type="reports",
                content_type="text/plain"
            )
            
            # 更新报告记录
            report.file_path = file_info["file_path"]
            db.commit()
            
            logger.info(f"为报告 {report_id} 创建了临时文件: {file_info['file_path']}")
            
        except Exception as e:
            logger.error(f"创建报告文件失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="无法准备报告下载"
            )
    
    return ApiResponse(
        success=True,
        data={
            "report_id": report_id,
            "download_url": f"/api/v1/reports/{report_id}/download",
            "filename": f"report_{report_id}.txt",
            "file_size": len(report.result.encode('utf-8')) if report.result else 0,
            "has_file": bool(report.file_path)
        },
        message="报告下载信息已准备"
    )


async def generate_report_task(
    template_id: str,
    data_source_id: str,
    user_id: str,
    task_id: int
):
    """后台生成报告任务 - 使用统一服务门面"""
    try:
        from app.db.session import get_db_session
        from app.services.application.facades.unified_service_facade import create_unified_service_facade
        from app.schemas.report_history import ReportHistoryCreate
        from app.crud.crud_report_history import report_history
        from uuid import UUID
        
        # 创建报告历史记录
        with get_db_session() as db:
            report_data = ReportHistoryCreate(
                task_id=task_id,
                user_id=UUID(user_id),
                status="pending"
            )
            report_record = report_history.create(db=db, obj_in=report_data)
            db.commit()
            report_id = report_record.id
        
        # 使用统一服务门面生成报告
        with get_db_session() as db:
            facade = create_unified_service_facade(db, user_id)
            
            # 获取模板内容
            from app.crud import template as crud_template
            template = crud_template.get(db, id=template_id)
            if not template:
                raise Exception(f"模板 {template_id} 不存在")
            
            # 生成图表数据
            chart_result = await facade.generate_charts(
                data_source=f"SELECT * FROM data_source_{data_source_id}",
                requirements="生成基础报告图表",
                output_format="json"
            )
            
            # 模拟报告生成结果
            filled_template = f"""
            # 报告标题: {template.name}
            
            ## 数据分析结果
            模板 ID: {template_id}
            数据源 ID: {data_source_id}
            生成时间: {datetime.now().isoformat()}
            
            ## 图表数据
            {chart_result.get('generated_charts', [])}
            
            ## 结论
            报告生成完成。
            """
            
            # 更新报告状态
            report = db.query(ReportHistory).filter(ReportHistory.id == report_id).first()
            if report:
                report.status = "completed"
                report.result = filled_template
                report.processing_metadata = {
                    "chart_generation": chart_result,
                    "processing_time": datetime.now().isoformat(),
                    "template_name": template.name
                }
                db.commit()
            
            return {
                "success": True,
                "filled_template": filled_template,
                "processing_metadata": report.processing_metadata
            }
        
    except Exception as e:
        # 更新报告状态为失败
        with get_db_session() as db:
            report = db.query(ReportHistory).filter(
                ReportHistory.task_id == task_id
            ).order_by(ReportHistory.id.desc()).first()
            
            if report:
                report.status = "failed"
                report.error_message = str(e)
                db.commit()
        
        logger.error(f"报告生成任务失败: {e}")
        raise e


async def generate_intelligent_report_task(
    template_id: str,
    data_source_id: str,
    user_id: str,
    task_id: int,
    optimization_config: dict
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
            report_record_id = report_record.id
            db.commit()
            
            # 获取模板和数据源信息
            from app.models.template import Template
            from app.models.data_source import DataSource
            template = db.query(Template).filter(Template.id == UUID(template_id)).first()
            data_source = db.query(DataSource).filter(DataSource.id == UUID(data_source_id)).first()
        
        # 使用新的agents系统生成智能报告内容
        try:
            from app.api.utils.agent_context_helpers import create_report_generation_context
            # Updated to use new Agent system
            from app.services.infrastructure.agents import AgentFacade, AgentInput, PlaceholderSpec, SchemaInfo, TaskContext, AgentConstraints
            from app.core.container import Container
            
            # 创建报告生成上下文
            data_source_info = {
                "name": data_source.name if data_source else '未知数据源',
                "type": data_source.source_type.value if data_source and hasattr(data_source.source_type, 'value') else 'unknown',
                "schema": {
                    "table_name": getattr(data_source, 'doris_database', 'main_table') if data_source else 'main_table',
                    "columns": [],  # Could be populated from actual schema
                    "relationships": []
                }
            }
            
            user_requirements = {
                "optimization_level": optimization_level,
                "batch_size": batch_size,
                "enable_intelligent_etl": enable_intelligent_etl,
                "report_sections": [
                    "执行摘要", "数据概览", "关键指标", "趋势分析", "洞察建议", "结论"
                ]
            }
            
            template_info = {
                "id": template_id,
                "name": template.name if template else '未知模板',
                "content": template.content if template else "",
                "metadata": {
                    "template_type": template.template_type if template else 'docx',
                    "original_filename": getattr(template, 'original_filename', None)
                }
            } if template else None
            
            context = create_report_generation_context(
                report_type="business_intelligence",
                data_source_info=data_source_info,
                user_requirements=user_requirements,
                template_info=template_info
            )
            
            # 构建报告生成内容
            report_content = f"""
            业务分析报告生成请求 - 报告ID: {report_record_id}
            
            模板信息:
            - 模板名称: {template.name if template else '未知模板'}
            - 模板类型: {template.template_type if template else 'docx'}
            - 模板ID: {template_id}
            
            数据源信息:
            - 数据源名称: {data_source.name if data_source else '未知数据源'}
            - 数据源类型: {data_source.source_type if data_source else 'unknown'}
            - 主机地址: {data_source.doris_fe_hosts[0] if data_source and data_source.doris_fe_hosts else '192.168.31.160'}
            - 数据源ID: {data_source_id}
            
            优化配置:
            - 优化级别: {optimization_level}
            - 批处理大小: {batch_size}
            - 智能ETL: {enable_intelligent_etl}
            
            生成要求：
            1. 执行摘要
            2. 数据概览和统计
            3. 关键业务指标分析
            4. 趋势分析（包含图表描述）
            5. 业务洞察和建议
            6. 结论
            
            报告应该专业、详细，包含数据驱动的洞察和可视化图表的描述。
            使用Markdown格式生成报告内容。
            
            用户ID: {user_id}
            生成时间: {datetime.utcnow().isoformat()}
            """
            
            agent_result = await execute_agent_task(
                task_name="intelligent_report_generation",
                task_description=f"生成基于模板 {template.name if template else '未知'} 的智能业务分析报告",
                context_data=context,
                additional_data={
                    "template_content": report_content,
                    "data_source_info": {
                        "type": data_source.source_type.value if data_source and hasattr(data_source.source_type, 'value') else 'unknown',
                        "database": getattr(data_source, 'doris_database', 'unknown') if data_source else 'unknown',
                        "name": data_source.name if data_source else 'unknown',
                        "optimization_level": optimization_level,
                        "task_type": "report_generation",
                        "data_source_id": data_source_id
                    }
                }
            )
            
            # 提取实际的响应内容
            raw_response = agent_result.get('response', str(agent_result))
            # 如果响应是特殊格式，提取真实内容
            if isinstance(raw_response, str) and '基于claude-3-5-sonnet-20241022的回答:' in raw_response:
                # 尝试从响应中提取实际内容（跳过前缀）
                try:
                    parts = raw_response.split('基于claude-3-5-sonnet-20241022的回答:')
                    if len(parts) > 1:
                        # 获取实际回答部分
                        actual_content = parts[1].strip()
                        # 进一步处理，移除上下文信息部分
                        if 'task_type:' in actual_content:
                            content_lines = actual_content.split('\n')
                            # 找到实际内容开始的地方（跳过上下文行）
                            content_start = 0
                            for i, line in enumerate(content_lines):
                                if not line.strip().startswith(('task_type:', 'template_id:', 'data_source_id:', 'optimization_level:')):
                                    content_start = i
                                    break
                            actual_content = '\n'.join(content_lines[content_start:]).strip()
                        
                        report_content = actual_content if actual_content else "报告内容生成中，请稍后查看完整版本。"
                    else:
                        report_content = raw_response
                except:
                    report_content = raw_response
            else:
                report_content = raw_response
            
            # 生成图表数据描述
            chart_prompt = f"""
            为上面的报告生成相应的图表配置和数据描述：
            
            请为报告生成以下类型的图表描述：
            1. 柱状图：显示关键指标对比
            2. 折线图：展示趋势变化
            3. 饼图：显示构成分析
            4. 面积图：显示累计效果
            
            每个图表请提供：
            - 图表标题
            - 数据系列描述
            - 建议的颜色主题
            - 交互性配置
            
            格式：JSON配置 + 图表说明
            """
            
            # 使用agents系统生成图表描述
            from app.api.utils.agent_context_helpers import create_data_analysis_context
            
            chart_context = create_data_analysis_context(
                analysis_type="chart_generation",
                data_info=data_source_info,
                analysis_parameters={
                    "chart_types": ["bar", "line", "pie", "area"],
                    "optimization_level": optimization_level,
                    "report_content": report_content[:1000]  # First 1000 chars for context
                }
            )
            
            chart_result = await execute_agent_task(
                task_name="chart_generation",
                task_description="为报告生成相应的图表配置和数据描述",
                context_data=chart_context
            )
            
            # 提取图表响应内容
            raw_chart_response = chart_result.get('response', str(chart_result))
            # 同样处理图表响应的特殊格式
            if isinstance(raw_chart_response, str) and '基于claude-3-5-sonnet-20241022的回答:' in raw_chart_response:
                try:
                    parts = raw_chart_response.split('基于claude-3-5-sonnet-20241022的回答:')
                    if len(parts) > 1:
                        actual_content = parts[1].strip()
                        if 'task_type:' in actual_content:
                            content_lines = actual_content.split('\n')
                            content_start = 0
                            for i, line in enumerate(content_lines):
                                if not line.strip().startswith(('task_type:', 'chart_types:')):
                                    content_start = i
                                    break
                            actual_content = '\n'.join(content_lines[content_start:]).strip()
                        
                        chart_content = actual_content if actual_content else "图表配置生成中，请稍后查看完整版本。"
                    else:
                        chart_content = raw_chart_response
                except:
                    chart_content = raw_chart_response
            else:
                chart_content = raw_chart_response
            
            # 组合最终报告内容
            final_content = f"""
# 智能业务分析报告

{report_content}

---

## 📊 图表配置和可视化

{chart_content}

---

## 📋 报告元数据

- **生成时间**: {datetime.now().isoformat()}
- **数据源**: {data_source.name if data_source else '未知'} ({data_source.source_type if data_source else 'unknown'})
- **模板**: {template.name if template else '未知模板'}
- **优化级别**: {optimization_level}
- **Agent系统**: React Agent (claude-3-5-sonnet-20241022)
- **生成模式**: 智能分析 + 图表生成
- **AI响应统计**: 分析耗时{agent_result.get('conversation_time', 0)*1000:.2f}ms, 图表耗时{chart_result.get('conversation_time', 0)*1000:.2f}ms

---

*本报告由AutoReportAI系统自动生成，采用React Agent智能分析技术*
            """.strip()
            
        except Exception as agent_error:
            logger.error(f"Agent报告生成失败: {agent_error}")
            # 生成一个简化的报告作为降级方案
            final_content = f"""
# 业务分析报告

## 执行摘要
基于{data_source.name if data_source else '数据源'}的业务分析报告已生成。

## 数据源信息
- 数据源: {data_source.name if data_source else '未知数据源'}
- 类型: {data_source.source_type if data_source else 'unknown'}
- 状态: {'活跃' if data_source and data_source.is_active else '未知'}

## 模板信息
- 模板名称: {template.name if template else '未知模板'}
- 模板类型: {template.template_type if template else 'docx'}

## 分析配置
- 优化级别: {optimization_level}
- 批处理大小: {batch_size}
- 智能ETL启用: {enable_intelligent_etl}

## 系统信息
- 生成时间: {datetime.now().isoformat()}
- 任务ID: {task_id}
- Agent错误: {str(agent_error)}

本报告使用简化模式生成。如需完整分析，请检查Agent系统配置。
            """.strip()
        
        # 更新报告状态
        with get_db_session() as db:
            report = db.query(ReportHistory).filter(
                ReportHistory.id == report_record_id
            ).first()
            
            if report:
                report.status = "completed"
                report.result = final_content
                report.processing_metadata = {
                    "agent_pipeline": True,
                    "optimization_level": optimization_level,
                    "batch_size": batch_size,
                    "intelligent_etl_enabled": enable_intelligent_etl,
                    "generation_method": "react_agent",
                    "template_name": template.name if template else "unknown",
                    "data_source_name": data_source.name if data_source else "unknown",
                    "content_length": len(final_content),
                    "generated_at": datetime.now().isoformat()
                }
                db.commit()
        
        return final_content
        
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
        
        # 如果没有文件路径，尝试从存储服务获取
        if not report.file_path:
            # 先尝试准备文件
            try:
                from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
                from io import BytesIO
                
                storage_service = get_hybrid_storage_service()
                
                # 创建报告内容文件
                report_content = report.result or "报告内容为空"
                filename = f"report_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                
                # 上传到存储系统
                file_info = storage_service.upload_file(
                    file_data=BytesIO(report_content.encode('utf-8')),
                    original_filename=filename,
                    file_type="reports",
                    content_type="text/markdown"
                )
                
                # 更新报告记录
                report.file_path = file_info["file_path"]
                db.commit()
                
            except Exception as prep_error:
                logger.error(f"准备报告文件失败: {prep_error}")
                raise HTTPException(
                    status_code=500,
                    detail="报告文件准备失败"
                )
        
        # 从存储系统下载文件
        try:
            from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
            from fastapi.responses import StreamingResponse
            import io
            
            storage_service = get_hybrid_storage_service()
            
            # 检查文件是否存在
            if not storage_service.file_exists(report.file_path):
                raise HTTPException(
                    status_code=404,
                    detail="报告文件在存储系统中不存在"
                )
            
            # 下载文件
            file_data, backend_type = storage_service.download_file(report.file_path)
            
            # 生成友好的文件名
            task_name = report.task.name if report.task else f"报告_{report_id}"
            timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S") if report.generated_at else "unknown"
            
            # 根据文件路径确定扩展名
            file_ext = report.file_path.split('.')[-1] if '.' in report.file_path else 'txt'
            filename = f"{task_name}_{timestamp}.{file_ext}"
            
            # 清理文件名中的非法字符
            import re
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # 确定Content-Type
            content_type = "application/octet-stream"
            if file_ext == 'md':
                content_type = "text/markdown"
            elif file_ext == 'txt':
                content_type = "text/plain"
            elif file_ext == 'html':
                content_type = "text/html"
            elif file_ext == 'docx':
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif file_ext == 'pdf':
                content_type = "application/pdf"
            
            # 创建响应
            file_stream = io.BytesIO(file_data)
            
            logger.info(f"用户 {user_id} 下载报告: {report_id}, 文件: {report.file_path}")
            
            return StreamingResponse(
                file_stream,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "X-Storage-Backend": backend_type,
                    "X-Report-ID": str(report_id)
                }
            )
            
        except Exception as download_error:
            logger.error(f"从存储系统下载报告文件失败: {download_error}")
            raise HTTPException(
                status_code=500,
                detail="报告文件下载失败"
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
