"""
优化的报告模型
统一报告管理，支持多种报告格式和输出方式
"""

import enum
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class_optimized import UserOwnedModel


class ReportType(str, enum.Enum):
    """报告类型枚举"""
    STANDARD = "standard"      # 标准报告
    DASHBOARD = "dashboard"    # 仪表盘报告
    ANALYTICS = "analytics"    # 分析报告
    SUMMARY = "summary"        # 摘要报告
    DETAILED = "detailed"      # 详细报告
    COMPARISON = "comparison"  # 对比报告
    TREND = "trend"           # 趋势报告


class ReportStatus(str, enum.Enum):
    """报告状态枚举"""
    DRAFT = "draft"           # 草稿
    GENERATING = "generating" # 生成中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 生成失败
    ARCHIVED = "archived"    # 已归档
    EXPIRED = "expired"      # 已过期


class ReportFormat(str, enum.Enum):
    """报告格式枚举"""
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "markdown"


class Report(UserOwnedModel):
    """报告模型"""
    
    __tablename__ = "reports"
    
    # 基本信息
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    report_type = Column(Enum(ReportType), nullable=False, index=True)
    
    # 关联模板和数据源
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=True, index=True)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)
    
    # 报告状态
    status = Column(Enum(ReportStatus), default=ReportStatus.DRAFT, nullable=False, index=True)
    format = Column(Enum(ReportFormat), default=ReportFormat.HTML, nullable=False)
    
    # 报告内容
    content = Column(Text, nullable=True)  # 报告内容
    raw_data = Column(JSON, nullable=True)  # 原始数据
    processed_data = Column(JSON, nullable=True)  # 处理后的数据
    
    # 生成配置
    generation_config = Column(JSON, nullable=True)  # 生成配置
    placeholder_values = Column(JSON, nullable=True)  # 占位符值
    filters_applied = Column(JSON, nullable=True)  # 应用的过滤器
    
    # 质量指标
    quality_score = Column(Float, default=0.0, nullable=False)  # 质量评分 0-100
    completeness_score = Column(Float, default=0.0, nullable=False)  # 完整性评分
    accuracy_score = Column(Float, default=0.0, nullable=False)  # 准确性评分
    
    # 性能指标
    generation_time = Column(Float, default=0.0, nullable=False)  # 生成时间（秒）
    data_size = Column(Integer, default=0, nullable=False)  # 数据大小（字节）
    record_count = Column(Integer, default=0, nullable=False)  # 记录数量
    
    # 访问控制
    is_public = Column(Boolean, default=False, nullable=False)
    is_shared = Column(Boolean, default=False, nullable=False)
    shared_with = Column(JSON, nullable=True)  # 共享给的用户列表
    
    # 缓存和存储
    file_path = Column(String(500), nullable=True)  # 文件存储路径
    file_size = Column(Integer, default=0, nullable=False)  # 文件大小
    cache_key = Column(String(255), nullable=True)  # 缓存键
    expires_at = Column(String, nullable=True)  # 过期时间
    
    # 使用统计
    view_count = Column(Integer, default=0, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    last_viewed_at = Column(String, nullable=True)
    last_downloaded_at = Column(String, nullable=True)
    
    # 错误处理
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # 扩展配置
    tags = Column(JSON, nullable=True)  # 标签
    extra_metadata = Column(JSON, nullable=True)  # 扩展元数据
    
    # 关联关系
    template = relationship("Template", back_populates="reports")
    data_source = relationship("DataSource", back_populates="reports")
    task = relationship("Task", back_populates="reports")
    
    @property
    def is_ready(self) -> bool:
        """报告是否就绪"""
        return self.status == ReportStatus.COMPLETED and bool(self.content)
    
    @property
    def is_generating(self) -> bool:
        """报告是否正在生成"""
        return self.status == ReportStatus.GENERATING
    
    @property
    def file_size_mb(self) -> float:
        """文件大小（MB）"""
        return round(self.file_size / (1024 * 1024), 2) if self.file_size > 0 else 0.0
    
    @property
    def data_size_mb(self) -> float:
        """数据大小（MB）"""
        return round(self.data_size / (1024 * 1024), 2) if self.data_size > 0 else 0.0
    
    @property
    def overall_quality_grade(self) -> str:
        """整体质量等级"""
        avg_score = (self.quality_score + self.completeness_score + self.accuracy_score) / 3
        if avg_score >= 90:
            return "excellent"
        elif avg_score >= 80:
            return "good"
        elif avg_score >= 70:
            return "fair"
        elif avg_score >= 60:
            return "poor"
        else:
            return "critical"
    
    @property
    def performance_grade(self) -> str:
        """性能等级"""
        if self.generation_time < 10:  # < 10秒
            return "excellent"
        elif self.generation_time < 30:  # < 30秒
            return "good"
        elif self.generation_time < 60:  # < 1分钟
            return "fair"
        else:
            return "poor"
    
    def increment_view_count(self):
        """增加查看次数"""
        self.view_count += 1
        from datetime import datetime
        self.last_viewed_at = datetime.utcnow().isoformat()
    
    def increment_download_count(self):
        """增加下载次数"""
        self.download_count += 1
        from datetime import datetime
        self.last_downloaded_at = datetime.utcnow().isoformat()
    
    def calculate_quality_scores(self) -> dict:
        """计算质量评分"""
        scores = {
            "quality_score": 0.0,
            "completeness_score": 0.0,
            "accuracy_score": 0.0
        }
        
        # 质量评分基于内容长度、数据完整性等
        if self.content:
            content_length = len(self.content)
            if content_length > 1000:
                scores["quality_score"] = min(100.0, content_length / 100)
            else:
                scores["quality_score"] = content_length / 10
        
        # 完整性评分基于占位符替换情况
        if self.placeholder_values:
            total_placeholders = len(self.placeholder_values)
            filled_placeholders = sum(1 for v in self.placeholder_values.values() if v)
            if total_placeholders > 0:
                scores["completeness_score"] = (filled_placeholders / total_placeholders) * 100
        else:
            scores["completeness_score"] = 100.0  # 无占位符时认为完整
        
        # 准确性评分基于数据验证和错误率
        if self.error_message:
            scores["accuracy_score"] = 60.0  # 有错误时降低评分
        elif self.record_count > 0:
            scores["accuracy_score"] = 95.0  # 有数据且无错误
        else:
            scores["accuracy_score"] = 80.0  # 默认评分
        
        # 更新模型字段
        self.quality_score = scores["quality_score"]
        self.completeness_score = scores["completeness_score"]
        self.accuracy_score = scores["accuracy_score"]
        
        return scores
    
    def start_generation(self):
        """开始生成报告"""
        from datetime import datetime
        
        self.status = ReportStatus.GENERATING
        self.error_message = None
        self.error_details = None
        start_time = datetime.utcnow()
        # 可以在metadata中记录开始时间
        if not self.metadata:
            self.metadata = {}
        self.metadata["generation_started_at"] = start_time.isoformat()
    
    def complete_generation(self, content: str, data_size: int = 0, 
                          record_count: int = 0, file_path: str = None):
        """完成报告生成"""
        from datetime import datetime
        
        self.status = ReportStatus.COMPLETED
        self.content = content
        self.data_size = data_size
        self.record_count = record_count
        
        if file_path:
            self.file_path = file_path
        
        # 计算生成时间
        if self.metadata and "generation_started_at" in self.metadata:
            start_time = datetime.fromisoformat(self.metadata["generation_started_at"])
            end_time = datetime.utcnow()
            self.generation_time = (end_time - start_time).total_seconds()
        
        # 计算质量评分
        self.calculate_quality_scores()
    
    def fail_generation(self, error_message: str, error_details: dict = None):
        """生成失败"""
        self.status = ReportStatus.FAILED
        self.error_message = error_message
        self.error_details = error_details
    
    def can_be_shared_with(self, user_id: str) -> bool:
        """检查是否可以与指定用户共享"""
        if not self.is_shared:
            return False
        
        if not self.shared_with:
            return False
        
        return user_id in self.shared_with
    
    def to_summary_dict(self) -> dict:
        """转换为摘要字典"""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "report_type": self.report_type.value,
            "status": self.status.value,
            "format": self.format.value,
            "quality_grade": self.overall_quality_grade,
            "performance_grade": self.performance_grade,
            "file_size_mb": self.file_size_mb,
            "data_size_mb": self.data_size_mb,
            "record_count": self.record_count,
            "generation_time": round(self.generation_time, 2),
            "view_count": self.view_count,
            "download_count": self.download_count,
            "is_public": self.is_public,
            "is_shared": self.is_shared,
            "template_id": str(self.template_id) if self.template_id else None,
            "data_source_id": str(self.data_source_id) if self.data_source_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_viewed_at": self.last_viewed_at,
            "tags": self.tags or []
        }