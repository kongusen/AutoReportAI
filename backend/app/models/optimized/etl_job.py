"""
优化的ETL作业模型
统一ETL作业管理，支持多种数据处理模式
"""

import enum
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class_optimized import UserOwnedModel


class ETLJobType(str, enum.Enum):
    """ETL作业类型枚举"""
    EXTRACT = "extract"        # 数据提取
    TRANSFORM = "transform"    # 数据转换
    LOAD = "load"             # 数据加载
    FULL_ETL = "full_etl"     # 完整ETL流程
    SYNC = "sync"             # 数据同步
    MIGRATION = "migration"   # 数据迁移


class ETLJobStatus(str, enum.Enum):
    """ETL作业状态枚举"""
    PENDING = "pending"        # 等待执行
    RUNNING = "running"        # 执行中
    SUCCESS = "success"        # 执行成功
    FAILED = "failed"         # 执行失败
    CANCELLED = "cancelled"   # 已取消
    TIMEOUT = "timeout"       # 执行超时
    RETRYING = "retrying"     # 重试中


class ETLJobPriority(str, enum.Enum):
    """ETL作业优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ETLJob(UserOwnedModel):
    """ETL作业模型"""
    
    __tablename__ = "etl_jobs"
    
    # 基本信息
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    job_type = Column(Enum(ETLJobType), nullable=False, index=True)
    
    # 关联数据源
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False, index=True)
    target_data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True)
    
    # 作业配置
    source_config = Column(JSON, nullable=False)  # 源数据配置
    transform_config = Column(JSON, nullable=True)  # 转换配置
    target_config = Column(JSON, nullable=True)  # 目标配置
    
    # 执行状态
    status = Column(Enum(ETLJobStatus), default=ETLJobStatus.PENDING, nullable=False, index=True)
    priority = Column(Enum(ETLJobPriority), default=ETLJobPriority.MEDIUM, nullable=False)
    
    # 调度配置
    schedule_config = Column(JSON, nullable=True)  # 调度配置
    is_scheduled = Column(Boolean, default=False, nullable=False)
    next_run_time = Column(String, nullable=True)
    last_run_time = Column(String, nullable=True)
    
    # 执行统计
    execution_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    
    # 性能指标
    avg_execution_time = Column(Float, default=0.0, nullable=False)  # 平均执行时间（秒）
    last_execution_time = Column(Float, default=0.0, nullable=False)  # 最后执行时间（秒）
    processed_records = Column(Integer, default=0, nullable=False)  # 处理记录数
    
    # 错误处理
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # 数据质量
    data_quality_checks = Column(JSON, nullable=True)  # 数据质量检查配置
    quality_score = Column(Float, default=100.0, nullable=False)  # 数据质量评分
    
    # 监控和日志
    monitoring_config = Column(JSON, nullable=True)  # 监控配置
    log_level = Column(String(20), default="INFO", nullable=False)
    
    # 扩展配置
    tags = Column(JSON, nullable=True)  # 标签
    extra_metadata = Column(JSON, nullable=True)  # 扩展元数据
    
    # 关联关系
    data_source = relationship("DataSource", foreign_keys=[data_source_id], back_populates="etl_jobs")
    target_data_source = relationship("DataSource", foreign_keys=[target_data_source_id])
    
    @property
    def is_active(self) -> bool:
        """作业是否活跃"""
        return self.status in [ETLJobStatus.PENDING, ETLJobStatus.RUNNING, ETLJobStatus.RETRYING]
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100
    
    @property
    def is_healthy(self) -> bool:
        """作业是否健康"""
        return (
            self.success_rate >= 80.0 and 
            self.quality_score >= 80.0 and 
            self.retry_count < self.max_retries
        )
    
    @property
    def performance_grade(self) -> str:
        """性能等级"""
        if self.avg_execution_time < 60:  # < 1分钟
            return "excellent"
        elif self.avg_execution_time < 300:  # < 5分钟
            return "good"
        elif self.avg_execution_time < 900:  # < 15分钟
            return "fair"
        else:
            return "poor"
    
    def can_retry(self) -> bool:
        """是否可以重试"""
        return (
            self.status == ETLJobStatus.FAILED and 
            self.retry_count < self.max_retries
        )
    
    def record_execution(self, status: ETLJobStatus, execution_time: float, 
                        records_processed: int = 0, error_message: str = None):
        """记录执行结果"""
        from datetime import datetime
        
        self.status = status
        self.execution_count += 1
        self.last_execution_time = execution_time
        self.last_run_time = datetime.utcnow().isoformat()
        
        if records_processed > 0:
            self.processed_records = records_processed
        
        # 更新平均执行时间
        if self.avg_execution_time == 0:
            self.avg_execution_time = execution_time
        else:
            self.avg_execution_time = (
                (self.avg_execution_time * (self.execution_count - 1) + execution_time) 
                / self.execution_count
            )
        
        if status == ETLJobStatus.SUCCESS:
            self.success_count += 1
            self.retry_count = 0  # 重置重试计数
            self.error_message = None
            self.error_details = None
        elif status == ETLJobStatus.FAILED:
            self.failure_count += 1
            self.error_message = error_message
            if self.can_retry():
                self.retry_count += 1
                self.status = ETLJobStatus.RETRYING
    
    def get_schedule_info(self) -> dict:
        """获取调度信息"""
        if not self.is_scheduled or not self.schedule_config:
            return {"is_scheduled": False}
        
        return {
            "is_scheduled": True,
            "schedule_config": self.schedule_config,
            "next_run_time": self.next_run_time,
            "last_run_time": self.last_run_time
        }
    
    def estimate_next_execution_time(self) -> float:
        """预估下次执行时间"""
        if self.avg_execution_time > 0:
            # 基于历史平均时间，考虑数据量增长
            growth_factor = 1.1  # 假设10%的增长
            return self.avg_execution_time * growth_factor
        return 300.0  # 默认5分钟
    
    def to_status_dict(self) -> dict:
        """转换为状态字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "execution_count": self.execution_count,
            "success_rate": round(self.success_rate, 2),
            "quality_score": round(self.quality_score, 2),
            "performance_grade": self.performance_grade,
            "is_healthy": self.is_healthy,
            "avg_execution_time": round(self.avg_execution_time, 2),
            "processed_records": self.processed_records,
            "next_run_time": self.next_run_time,
            "last_run_time": self.last_run_time,
            "data_source_name": self.data_source.name if self.data_source else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }