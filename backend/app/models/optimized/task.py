"""
优化的任务模型
统一任务管理，支持多种任务类型和状态跟踪
"""

import enum
from sqlalchemy import Boolean, Column, Enum, Integer, String, Text, JSON, Float
from sqlalchemy.orm import relationship

from app.db.base_class_optimized import UserOwnedModel


class TaskType(str, enum.Enum):
    """任务类型枚举"""
    REPORT_GENERATION = "report_generation"  # 报告生成
    DATA_EXPORT = "data_export"             # 数据导出
    ETL_EXECUTION = "etl_execution"         # ETL执行
    DATA_SYNC = "data_sync"                 # 数据同步
    TEMPLATE_ANALYSIS = "template_analysis"  # 模板分析
    PLACEHOLDER_PROCESSING = "placeholder_processing"  # 占位符处理
    BATCH_OPERATION = "batch_operation"     # 批量操作
    SYSTEM_MAINTENANCE = "system_maintenance"  # 系统维护


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 待处理
    QUEUED = "queued"         # 队列中
    RUNNING = "running"       # 执行中
    SUCCESS = "success"       # 成功完成
    FAILED = "failed"         # 执行失败
    CANCELLED = "cancelled"   # 已取消
    TIMEOUT = "timeout"       # 执行超时
    PAUSED = "paused"        # 已暂停


class TaskPriority(str, enum.Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class Task(UserOwnedModel):
    """任务模型"""
    
    __tablename__ = "tasks"
    
    # 基本信息
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    task_type = Column(Enum(TaskType), nullable=False, index=True)
    
    # 任务状态
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    
    # 进度跟踪
    progress = Column(Integer, default=0, nullable=False)  # 进度百分比 0-100
    current_step = Column(String(200), nullable=True)  # 当前执行步骤
    total_steps = Column(Integer, default=1, nullable=False)  # 总步骤数
    completed_steps = Column(Integer, default=0, nullable=False)  # 已完成步骤数
    
    # 时间管理
    estimated_duration = Column(Integer, nullable=True)  # 预估执行时间（秒）
    actual_duration = Column(Integer, nullable=True)  # 实际执行时间（秒）
    started_at = Column(String, nullable=True)
    completed_at = Column(String, nullable=True)
    expires_at = Column(String, nullable=True)  # 过期时间
    
    # 任务配置
    task_config = Column(JSON, nullable=True)  # 任务配置参数
    input_data = Column(JSON, nullable=True)  # 输入数据
    output_data = Column(JSON, nullable=True)  # 输出数据
    
    # 执行结果
    result = Column(Text, nullable=True)  # 执行结果
    error_message = Column(Text, nullable=True)  # 错误信息
    error_details = Column(JSON, nullable=True)  # 详细错误信息
    
    # 资源使用
    cpu_usage = Column(Float, default=0.0, nullable=False)  # CPU使用率
    memory_usage = Column(Float, default=0.0, nullable=False)  # 内存使用（MB）
    
    # 重试机制
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # 依赖关系
    parent_task_id = Column(String, nullable=True)  # 父任务ID
    dependencies = Column(JSON, nullable=True)  # 依赖的任务ID列表
    
    # 通知配置
    notification_config = Column(JSON, nullable=True)  # 通知配置
    should_notify_on_success = Column(Boolean, default=False, nullable=False)
    should_notify_on_failure = Column(Boolean, default=True, nullable=False)
    
    # 扩展信息
    tags = Column(JSON, nullable=True)  # 标签
    extra_metadata = Column(JSON, nullable=True)  # 扩展元数据
    
    # 关联关系
    reports = relationship("Report", back_populates="task")
    
    @property
    def is_active(self) -> bool:
        """任务是否活跃"""
        return self.status in [
            TaskStatus.PENDING, TaskStatus.QUEUED, 
            TaskStatus.RUNNING, TaskStatus.PAUSED
        ]
    
    @property
    def is_completed(self) -> bool:
        """任务是否已完成"""
        return self.status in [
            TaskStatus.SUCCESS, TaskStatus.FAILED, 
            TaskStatus.CANCELLED, TaskStatus.TIMEOUT
        ]
    
    @property
    def is_successful(self) -> bool:
        """任务是否成功"""
        return self.status == TaskStatus.SUCCESS
    
    @property
    def progress_percentage(self) -> int:
        """进度百分比"""
        if self.total_steps <= 0:
            return self.progress
        return min(100, int((self.completed_steps / self.total_steps) * 100))
    
    @property
    def execution_efficiency(self) -> float:
        """执行效率"""
        if not self.estimated_duration or not self.actual_duration:
            return 1.0
        if self.actual_duration <= 0:
            return 1.0
        return min(2.0, self.estimated_duration / self.actual_duration)
    
    @property
    def can_retry(self) -> bool:
        """是否可以重试"""
        return (
            self.status == TaskStatus.FAILED and 
            self.retry_count < self.max_retries
        )
    
    def update_progress(self, progress: int = None, current_step: str = None, 
                       completed_steps: int = None):
        """更新任务进度"""
        if progress is not None:
            self.progress = max(0, min(100, progress))
        
        if current_step is not None:
            self.current_step = current_step
        
        if completed_steps is not None:
            self.completed_steps = completed_steps
            if self.total_steps > 0:
                self.progress = min(100, int((self.completed_steps / self.total_steps) * 100))
    
    def start_execution(self):
        """开始执行任务"""
        from datetime import datetime
        
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow().isoformat()
        self.progress = 0
        self.current_step = "任务启动中..."
    
    def complete_execution(self, success: bool = True, result: str = None, 
                          error_message: str = None):
        """完成任务执行"""
        from datetime import datetime
        
        completion_time = datetime.utcnow().isoformat()
        self.completed_at = completion_time
        
        if success:
            self.status = TaskStatus.SUCCESS
            self.progress = 100
            self.current_step = "任务完成"
            if result:
                self.result = result
        else:
            self.status = TaskStatus.FAILED
            self.error_message = error_message
            
            # 检查是否需要重试
            if self.can_retry():
                self.retry_count += 1
                self.status = TaskStatus.PENDING
                self.started_at = None
                self.completed_at = None
                self.current_step = f"准备第{self.retry_count}次重试..."
        
        # 计算实际执行时间
        if self.started_at:
            from datetime import datetime
            start_time = datetime.fromisoformat(self.started_at.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(completion_time.replace('Z', '+00:00'))
            self.actual_duration = int((end_time - start_time).total_seconds())
    
    def cancel_task(self, reason: str = None):
        """取消任务"""
        if self.is_active:
            self.status = TaskStatus.CANCELLED
            if reason:
                self.error_message = f"任务被取消: {reason}"
            from datetime import datetime
            self.completed_at = datetime.utcnow().isoformat()
    
    def pause_task(self):
        """暂停任务"""
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.PAUSED
    
    def resume_task(self):
        """恢复任务"""
        if self.status == TaskStatus.PAUSED:
            self.status = TaskStatus.RUNNING
    
    def get_execution_summary(self) -> dict:
        """获取执行摘要"""
        return {
            "task_id": str(self.id),
            "name": self.name,
            "type": self.task_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "progress": self.progress_percentage,
            "current_step": self.current_step,
            "execution_time": self.actual_duration,
            "efficiency": round(self.execution_efficiency, 2),
            "retry_count": self.retry_count,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "is_successful": self.is_successful,
            "can_retry": self.can_retry()
        }
    
    def to_status_dict(self) -> dict:
        """转换为状态字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "progress": self.progress_percentage,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
            "is_completed": self.is_completed,
            "can_retry": self.can_retry()
        }