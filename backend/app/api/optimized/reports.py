"""
优化的报告API端点
"""

from typing import List, Optional
from uuid import UUID
from fastapi import BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.optimized.base_router import BaseRouter, APIResponse
from app.models.optimized.user import User
from app.models.optimized.report import ReportStatus, ReportFormat, ReportType
from app.schemas.report_history import ReportCreate, ReportUpdate, ReportResponse
from app.services.optimized import services


class ReportGenerationRequest(BaseModel):
    """报告生成请求"""
    template_id: UUID
    data_source_id: Optional[UUID] = None
    generation_config: Optional[dict] = None
    format: ReportFormat = ReportFormat.HTML
    title: Optional[str] = None
    description: Optional[str] = None


class ReportRouter(BaseRouter):
    """报告路由"""
    
    def __init__(self):
        super().__init__(
            service=services.report,
            prefix="/reports",
            tags=["报告管理"],
            response_model=ReportResponse,
            create_schema=ReportCreate,
            update_schema=ReportUpdate
        )
        
        # 注册自定义路由
        self._register_custom_routes()
    
    def _register_custom_routes(self):
        """注册自定义路由"""
        
        @self.router.post("/generate", response_model=APIResponse, status_code=status.HTTP_202_ACCEPTED)
        async def generate_report(
            request: ReportGenerationRequest,
            background_tasks: BackgroundTasks,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """生成报告"""
            try:
                report = await self.service.generate_report(
                    db,
                    template_id=request.template_id,
                    data_source_id=request.data_source_id,
                    user_id=current_user.id,
                    generation_config=request.generation_config,
                    format=request.format
                )
                
                return APIResponse(
                    message="报告生成已启动",
                    data={
                        "report_id": str(report.id),
                        "status": report.status.value,
                        "message": "报告正在后台生成中，请稍后查询状态"
                    }
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"报告生成失败: {str(e)}"
                )
        
        @self.router.get("/{id}/status", response_model=APIResponse)
        async def get_generation_status(
            id: UUID,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """获取报告生成状态"""
            try:
                status_info = self.service.get_generation_status(
                    db,
                    report_id=id,
                    user_id=current_user.id
                )
                return APIResponse(data=status_info)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取生成状态失败: {str(e)}"
                )
        
        @self.router.get("/status/{status}", response_model=APIResponse)
        async def get_by_status(
            status: ReportStatus,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """根据状态获取报告"""
            try:
                reports = self.service.get_by_status(
                    db,
                    status=status,
                    user_id=current_user.id
                )
                return APIResponse(data=reports)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取报告失败: {str(e)}"
                )
        
        @self.router.get("/type/{report_type}", response_model=APIResponse)
        async def get_by_type(
            report_type: ReportType,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """根据类型获取报告"""
            try:
                reports = self.service.get_by_type(
                    db,
                    report_type=report_type,
                    user_id=current_user.id
                )
                return APIResponse(data=reports)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取报告失败: {str(e)}"
                )
        
        @self.router.get("/template/{template_id}", response_model=APIResponse)
        async def get_by_template(
            template_id: UUID,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """根据模板获取报告"""
            try:
                reports = self.service.get_by_template(
                    db,
                    template_id=template_id,
                    user_id=current_user.id
                )
                return APIResponse(data=reports)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取报告失败: {str(e)}"
                )
        
        @self.router.get("/ready", response_model=APIResponse)
        async def get_ready_reports(
            format: Optional[ReportFormat] = Query(None, description="报告格式"),
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """获取就绪的报告"""
            try:
                reports = self.service.get_ready_reports(
                    db,
                    user_id=current_user.id,
                    format=format
                )
                return APIResponse(data=reports)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取就绪报告失败: {str(e)}"
                )
        
        @self.router.get("/shared", response_model=APIResponse)
        async def get_shared_reports(
            include_public: bool = Query(True, description="包含公开报告"),
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """获取共享报告"""
            try:
                reports = self.service.get_shared_reports(
                    db,
                    user_id=current_user.id,
                    include_public=include_public
                )
                return APIResponse(data=reports)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取共享报告失败: {str(e)}"
                )
        
        @self.router.post("/{id}/view", response_model=APIResponse)
        async def increment_view_count(
            id: UUID,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """增加报告查看次数"""
            try:
                report = self.service.increment_view_count(
                    db,
                    report_id=id
                )
                return APIResponse(
                    message="查看次数已更新",
                    data={"view_count": report.view_count if report else 0}
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"更新查看次数失败: {str(e)}"
                )
        
        @self.router.post("/{id}/download", response_model=APIResponse)
        async def increment_download_count(
            id: UUID,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """增加报告下载次数"""
            try:
                report = self.service.increment_download_count(
                    db,
                    report_id=id
                )
                return APIResponse(
                    message="下载次数已更新",
                    data={"download_count": report.download_count if report else 0}
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"更新下载次数失败: {str(e)}"
                )
        
        @self.router.get("/statistics", response_model=APIResponse)
        async def get_report_statistics(
            days: int = Query(30, ge=1, le=365, description="统计天数"),
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """获取报告统计信息"""
            try:
                stats = self.service.get_report_statistics(
                    db,
                    user_id=current_user.id,
                    days=days
                )
                return APIResponse(data=stats)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取统计信息失败: {str(e)}"
                )
        
        @self.router.get("/quality-summary", response_model=APIResponse)
        async def get_quality_summary(
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """获取报告质量摘要"""
            try:
                summary = self.service.get_quality_summary(
                    db,
                    user_id=current_user.id
                )
                return APIResponse(data=summary)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取质量摘要失败: {str(e)}"
                )


# 创建路由器实例
report_router = ReportRouter()
router = report_router.get_router()