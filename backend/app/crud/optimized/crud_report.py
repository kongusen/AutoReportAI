"""
优化的报告CRUD操作
"""

from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.crud.base_optimized import CRUDComplete
from app.models.optimized.report import Report, ReportType, ReportStatus, ReportFormat
from app.schemas.report_history import ReportCreate, ReportUpdate


class CRUDReport(CRUDComplete[Report, ReportCreate, ReportUpdate]):
    """报告CRUD操作类"""
    
    def __init__(self):
        super().__init__(Report, search_fields=["title", "description"])
    
    def get_by_status(
        self,
        db: Session,
        *,
        status: ReportStatus,
        user_id: Union[UUID, str] = None
    ) -> List[Report]:
        """根据状态获取报告"""
        query = db.query(self.model).filter(
            self.model.status == status,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_by_type(
        self,
        db: Session,
        *,
        report_type: ReportType,
        user_id: Union[UUID, str] = None
    ) -> List[Report]:
        """根据类型获取报告"""
        query = db.query(self.model).filter(
            self.model.report_type == report_type,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_by_template(
        self,
        db: Session,
        *,
        template_id: Union[UUID, str],
        user_id: Union[UUID, str] = None
    ) -> List[Report]:
        """根据模板获取报告"""
        if isinstance(template_id, str):
            template_id = UUID(template_id)
        
        query = db.query(self.model).filter(
            self.model.template_id == template_id,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_by_data_source(
        self,
        db: Session,
        *,
        data_source_id: Union[UUID, str],
        user_id: Union[UUID, str] = None
    ) -> List[Report]:
        """根据数据源获取报告"""
        if isinstance(data_source_id, str):
            data_source_id = UUID(data_source_id)
        
        query = db.query(self.model).filter(
            self.model.data_source_id == data_source_id,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_ready_reports(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None,
        format: ReportFormat = None
    ) -> List[Report]:
        """获取就绪的报告"""
        query = db.query(self.model).filter(
            self.model.status == ReportStatus.COMPLETED,
            self.model.content.isnot(None),
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        if format:
            query = query.filter(self.model.format == format)
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_shared_reports(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str],
        include_public: bool = True
    ) -> List[Report]:
        """获取与用户共享的报告"""
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        user_id_str = str(user_id)
        
        query = db.query(self.model).filter(
            self.model.status == ReportStatus.COMPLETED,
            self.model.is_deleted == False
        )
        
        if include_public:
            # 包含公开报告和与用户共享的报告
            query = query.filter(
                (self.model.is_public == True) |
                (self.model.is_shared == True) & 
                (self.model.shared_with.contains([user_id_str]))
            )
        else:
            # 只包含与用户共享的报告
            query = query.filter(
                self.model.is_shared == True,
                self.model.shared_with.contains([user_id_str])
            )
        
        return query.order_by(desc(self.model.created_at)).all()
    
    def get_generating_reports(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[Report]:
        """获取正在生成的报告"""
        query = db.query(self.model).filter(
            self.model.status == ReportStatus.GENERATING,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        return query.all()
    
    def increment_view_count(
        self,
        db: Session,
        *,
        report_id: Union[UUID, str]
    ) -> Optional[Report]:
        """增加报告查看次数"""
        report = self.get(db, id=report_id)
        if not report:
            return None
        
        report.increment_view_count()
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return report
    
    def increment_download_count(
        self,
        db: Session,
        *,
        report_id: Union[UUID, str]
    ) -> Optional[Report]:
        """增加报告下载次数"""
        report = self.get(db, id=report_id)
        if not report:
            return None
        
        report.increment_download_count()
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return report
    
    def start_generation(
        self,
        db: Session,
        *,
        report_id: Union[UUID, str]
    ) -> Optional[Report]:
        """开始生成报告"""
        report = self.get(db, id=report_id)
        if not report:
            return None
        
        report.start_generation()
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return report
    
    def complete_generation(
        self,
        db: Session,
        *,
        report_id: Union[UUID, str],
        content: str,
        data_size: int = 0,
        record_count: int = 0,
        file_path: str = None
    ) -> Optional[Report]:
        """完成报告生成"""
        report = self.get(db, id=report_id)
        if not report:
            return None
        
        report.complete_generation(content, data_size, record_count, file_path)
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return report
    
    def fail_generation(
        self,
        db: Session,
        *,
        report_id: Union[UUID, str],
        error_message: str,
        error_details: dict = None
    ) -> Optional[Report]:
        """报告生成失败"""
        report = self.get(db, id=report_id)
        if not report:
            return None
        
        report.fail_generation(error_message, error_details)
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return report
    
    def search_by_tags(
        self,
        db: Session,
        *,
        tags: List[str],
        user_id: Union[UUID, str] = None
    ) -> List[Report]:
        """根据标签搜索报告"""
        query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            query = query.filter(self.model.user_id == user_id)
        
        # 使用JSON操作符查询包含指定标签的报告
        for tag in tags:
            query = query.filter(self.model.tags.contains([tag]))
        
        return query.all()
    
    def get_report_statistics(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None,
        days: int = 30
    ) -> dict:
        """获取报告统计信息"""
        from datetime import datetime, timedelta
        
        base_query = db.query(self.model).filter(self.model.is_deleted == False)
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            base_query = base_query.filter(self.model.user_id == user_id)
        
        # 最近N天的报告
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        recent_query = base_query.filter(self.model.created_at >= cutoff_date)
        
        stats = {
            "total": base_query.count(),
            "recent": recent_query.count(),
            "completed": base_query.filter(self.model.status == ReportStatus.COMPLETED).count(),
            "generating": base_query.filter(self.model.status == ReportStatus.GENERATING).count(),
            "failed": base_query.filter(self.model.status == ReportStatus.FAILED).count(),
            "total_views": base_query.with_entities(db.func.sum(self.model.view_count)).scalar() or 0,
            "total_downloads": base_query.with_entities(db.func.sum(self.model.download_count)).scalar() or 0,
            "by_type": {},
            "by_format": {},
            "quality_distribution": {}
        }
        
        # 按类型统计
        for report_type in ReportType:
            count = base_query.filter(self.model.report_type == report_type).count()
            if count > 0:
                stats["by_type"][report_type.value] = count
        
        # 按格式统计
        for format in ReportFormat:
            count = base_query.filter(self.model.format == format).count()
            if count > 0:
                stats["by_format"][format.value] = count
        
        return stats
    
    def get_quality_summary(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> dict:
        """获取报告质量摘要"""
        base_query = db.query(self.model).filter(
            self.model.status == ReportStatus.COMPLETED,
            self.model.is_deleted == False
        )
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            base_query = base_query.filter(self.model.user_id == user_id)
        
        reports = base_query.all()
        
        if not reports:
            return {
                "total_reports": 0,
                "avg_quality_score": 0,
                "avg_completeness_score": 0,
                "avg_accuracy_score": 0,
                "quality_grades": {}
            }
        
        avg_quality = sum(r.quality_score for r in reports) / len(reports)
        avg_completeness = sum(r.completeness_score for r in reports) / len(reports)
        avg_accuracy = sum(r.accuracy_score for r in reports) / len(reports)
        
        # 质量等级分布
        grade_counts = {}
        for report in reports:
            grade = report.overall_quality_grade
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        return {
            "total_reports": len(reports),
            "avg_quality_score": round(avg_quality, 2),
            "avg_completeness_score": round(avg_completeness, 2),
            "avg_accuracy_score": round(avg_accuracy, 2),
            "quality_grades": grade_counts
        }


# 创建CRUD实例
crud_report = CRUDReport()