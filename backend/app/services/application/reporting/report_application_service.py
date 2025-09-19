"""
报告应用服务 - DDD架构v2.0

基于新DDD架构的报告应用服务，集成报告生成领域服务和基础设施层
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.application.base_application_service import (
    TransactionalApplicationService, 
    ApplicationResult, 
    PaginationRequest, 
    PaginationResult
)
from app.services.domain.reporting.services.report_generation_domain_service import (
    ReportGenerationDomainService,
    ReportEntity,
    ReportMetadata,
    ReportFormat,
    ReportStatus
)
from app.models.report_history import ReportHistory
from app.models.task import Task
from app.models.template import Template
from app.models.user import User

logger = logging.getLogger(__name__)


class ReportApplicationService(TransactionalApplicationService):
    """报告应用服务 - DDD架构v2.0版本"""
    
    def __init__(self):
        super().__init__("ReportApplicationService")
        self.domain_service = ReportGenerationDomainService()
    
    def create_report(
        self,
        db: Session,
        user_id: str,
        title: str,
        template_id: str,
        task_id: Optional[str] = None,
        description: str = "",
        target_formats: List[str] = None,
        generation_config: Dict[str, Any] = None
    ) -> ApplicationResult[ReportEntity]:
        """
        创建新报告
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            title: 报告标题
            template_id: 模板ID
            task_id: 关联任务ID（可选）
            description: 报告描述
            target_formats: 目标格式列表
            generation_config: 生成配置
            
        Returns:
            ApplicationResult[ReportEntity]: 创建结果
        """
        # 验证必需参数
        validation_result = self.validate_required_params(
            user_id=user_id,
            title=title,
            template_id=template_id
        )
        if not validation_result.success:
            return validation_result
        
        def _create_report_internal():
            # 验证用户存在
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return ApplicationResult.not_found_result(f"用户 {user_id} 不存在")
            
            # 验证模板存在
            template = db.query(Template).filter(Template.id == template_id).first()
            if not template:
                return ApplicationResult.not_found_result(f"模板 {template_id} 不存在")
            
            # 验证任务存在（如果提供）
            task = None
            if task_id:
                task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
                if not task:
                    return ApplicationResult.not_found_result(f"任务 {task_id} 不存在或无权限")
            
            # 创建报告元数据
            metadata = ReportMetadata(
                title=title,
                description=description,
                author=user.username if hasattr(user, 'username') else str(user_id),
                template_id=template_id
            )
            
            # 创建报告实体
            report_id = f"report_{datetime.now().timestamp()}"
            report = self.domain_service.create_report(report_id, metadata)
            
            # 设置目标格式
            if target_formats:
                report.target_formats = {ReportFormat(fmt) for fmt in target_formats}
            
            # 设置生成配置
            if generation_config:
                report.generation_config.update(generation_config)
            
            # 创建数据库记录
            report_history = ReportHistory(
                task_id=int(task_id) if task_id else None,
                status=report.status.value,
                generated_at=datetime.now(),
                metadata={
                    "title": title,
                    "description": description,
                    "template_id": template_id,
                    "report_entity_id": report_id
                }
            )
            
            db.add(report_history)
            db.refresh(report_history)
            
            return ApplicationResult.success_result(
                data=report,
                message=f"报告 '{title}' 创建成功"
            )
        
        return self.execute_in_transaction(db, "create_report", _create_report_internal)
    
    def get_report_list(
        self,
        db: Session,
        user_id: str,
        pagination: PaginationRequest,
        status_filter: Optional[str] = None,
        template_id_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> ApplicationResult[PaginationResult[Dict[str, Any]]]:
        """
        获取报告列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            pagination: 分页参数
            status_filter: 状态过滤
            template_id_filter: 模板ID过滤
            search: 搜索关键词
            
        Returns:
            ApplicationResult[PaginationResult]: 报告列表
        """
        def _get_report_list_internal():
            # 构建查询
            query = db.query(ReportHistory).join(
                Task, ReportHistory.task_id == Task.id, isouter=True
            ).filter(
                (Task.owner_id == user_id) | (ReportHistory.task_id.is_(None))
            )
            
            # 应用过滤器
            if status_filter:
                query = query.filter(ReportHistory.status == status_filter)
            
            if template_id_filter:
                query = query.filter(
                    ReportHistory.metadata['template_id'].astext == template_id_filter
                )
            
            if search:
                query = query.filter(
                    ReportHistory.metadata['title'].astext.contains(search)
                )
            
            # 获取总数
            total = query.count()
            
            # 应用分页
            reports = query.offset(pagination.skip).limit(pagination.size).all()
            
            # 转换为字典格式
            report_dicts = []
            for report in reports:
                report_dict = {
                    "id": report.id,
                    "title": report.metadata.get("title", "未命名报告"),
                    "description": report.metadata.get("description", ""),
                    "status": report.status,
                    "template_id": report.metadata.get("template_id"),
                    "generated_at": report.generated_at.isoformat() if report.generated_at else None,
                    "file_path": report.file_path,
                    "file_size": report.file_size,
                    "task_id": report.task_id
                }
                report_dicts.append(report_dict)
            
            paginated_result = PaginationResult.create(report_dicts, total, pagination)
            
            return ApplicationResult.success_result(
                data=paginated_result,
                message=f"获取报告列表成功，共 {total} 条记录"
            )
        
        return self.handle_domain_exceptions("get_report_list", _get_report_list_internal)
    
    def get_report_detail(
        self,
        db: Session,
        user_id: str,
        report_id: int
    ) -> ApplicationResult[Dict[str, Any]]:
        """
        获取报告详情
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            report_id: 报告ID
            
        Returns:
            ApplicationResult[Dict]: 报告详情
        """
        def _get_report_detail_internal():
            # 查找报告
            report = db.query(ReportHistory).filter(ReportHistory.id == report_id).first()
            if not report:
                return ApplicationResult.not_found_result(f"报告 {report_id} 不存在")
            
            # 检查权限（通过关联任务）
            if report.task_id:
                task = db.query(Task).filter(
                    Task.id == report.task_id,
                    Task.owner_id == user_id
                ).first()
                if not task:
                    return ApplicationResult.not_found_result("报告不存在或无权限访问")
            
            # 构建详情
            report_detail = {
                "id": report.id,
                "title": report.metadata.get("title", "未命名报告"),
                "description": report.metadata.get("description", ""),
                "status": report.status,
                "template_id": report.metadata.get("template_id"),
                "task_id": report.task_id,
                "generated_at": report.generated_at.isoformat() if report.generated_at else None,
                "file_path": report.file_path,
                "file_size": report.file_size,
                "error_message": report.error_message,
                "metadata": report.metadata,
                "download_available": bool(report.file_path and report.status == "completed"),
                "preview_available": bool(report.file_path and report.status == "completed")
            }
            
            return ApplicationResult.success_result(
                data=report_detail,
                message="获取报告详情成功"
            )
        
        return self.handle_domain_exceptions("get_report_detail", _get_report_detail_internal)
    
    def delete_report(
        self,
        db: Session,
        user_id: str,
        report_id: int
    ) -> ApplicationResult[bool]:
        """
        删除报告
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            report_id: 报告ID
            
        Returns:
            ApplicationResult[bool]: 删除结果
        """
        def _delete_report_internal():
            # 查找报告
            report = db.query(ReportHistory).filter(ReportHistory.id == report_id).first()
            if not report:
                return ApplicationResult.not_found_result(f"报告 {report_id} 不存在")
            
            # 检查权限
            if report.task_id:
                task = db.query(Task).filter(
                    Task.id == report.task_id,
                    Task.owner_id == user_id
                ).first()
                if not task:
                    return ApplicationResult.not_found_result("报告不存在或无权限删除")
            
            # 删除文件（如果存在）
            if report.file_path:
                try:
                    # 这里可以集成文件存储服务来删除实际文件
                    from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
                    storage_service = get_hybrid_storage_service()
                    # storage_service.delete_file(report.file_path)  # 取消注释以启用文件删除
                    self.logger.info(f"文件删除标记: {report.file_path}")
                except Exception as e:
                    self.logger.warning(f"删除报告文件失败: {e}")
            
            # 删除数据库记录
            db.delete(report)
            
            return ApplicationResult.success_result(
                data=True,
                message=f"报告 {report_id} 删除成功"
            )
        
        return self.execute_in_transaction(db, "delete_report", _delete_report_internal)
    
    def generate_report_from_template(
        self,
        db: Session,
        user_id: str,
        template_id: str,
        placeholder_values: Dict[str, Any],
        task_id: Optional[str] = None,
        target_formats: List[str] = None
    ) -> ApplicationResult[ReportEntity]:
        """
        基于模板生成报告
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            template_id: 模板ID
            placeholder_values: 占位符值
            task_id: 关联任务ID
            target_formats: 目标格式
            
        Returns:
            ApplicationResult[ReportEntity]: 生成结果
        """
        def _generate_report_internal():
            # 验证模板存在
            template = db.query(Template).filter(Template.id == template_id).first()
            if not template:
                return ApplicationResult.not_found_result(f"模板 {template_id} 不存在")
            
            # 创建报告
            create_result = self.create_report(
                db=db,
                user_id=user_id,
                title=f"基于模板 {template.name} 的报告",
                template_id=template_id,
                task_id=task_id,
                target_formats=target_formats or ["html"]
            )
            
            if not create_result.success:
                return create_result
            
            report = create_result.data
            
            # 设置占位符值
            report.set_placeholder_values(placeholder_values)
            
            # 使用领域服务处理占位符替换
            substitution_result = self.domain_service.process_placeholder_substitution(report)
            if not substitution_result['success']:
                return ApplicationResult.failure_result(
                    message="占位符替换失败",
                    errors=substitution_result['errors']
                )
            
            # 验证报告内容
            validation_result = self.domain_service.validate_report_content(report)
            if not validation_result['valid']:
                return ApplicationResult.validation_error_result(
                    message="报告内容验证失败",
                    errors=validation_result['errors']
                )
            
            return ApplicationResult.success_result(
                data=report,
                message="报告生成成功"
            )
        
        return self.handle_domain_exceptions("generate_report_from_template", _generate_report_internal)
    
    def get_report_metrics(
        self,
        db: Session,
        user_id: str,
        report_id: int
    ) -> ApplicationResult[Dict[str, Any]]:
        """
        获取报告指标
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            report_id: 报告ID
            
        Returns:
            ApplicationResult[Dict]: 报告指标
        """
        def _get_metrics_internal():
            # 这里可以从报告实体中获取指标
            # 由于我们没有存储完整的报告实体，这里返回基础指标
            report = db.query(ReportHistory).filter(ReportHistory.id == report_id).first()
            if not report:
                return ApplicationResult.not_found_result(f"报告 {report_id} 不存在")
            
            metrics = {
                "basic_info": {
                    "id": report.id,
                    "status": report.status,
                    "file_size": report.file_size or 0,
                    "generated_at": report.generated_at.isoformat() if report.generated_at else None
                },
                "generation_metrics": {
                    "has_errors": bool(report.error_message),
                    "error_count": 1 if report.error_message else 0
                },
                "content_metrics": {
                    "estimated_pages": max(1, (report.file_size or 0) // 1024) if report.file_size else 1
                }
            }
            
            return ApplicationResult.success_result(
                data=metrics,
                message="获取报告指标成功"
            )
        
        return self.handle_domain_exceptions("get_report_metrics", _get_metrics_internal)


logger.info("✅ Report Application Service DDD架构v2.0加载完成")