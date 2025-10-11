import enum
from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, DateTime, Enum, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base_class import Base


class TaskStatus(str, enum.Enum):
    """任务状态"""
    PENDING = "pending"          # 待执行
    PROCESSING = "processing"    # 处理中
    AGENT_ORCHESTRATING = "agent_orchestrating"  # Agent编排中
    GENERATING = "generating"    # 生成中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"      # 已取消


class ProcessingMode(str, enum.Enum):
    """处理模式"""
    SIMPLE = "simple"           # 简单模式，传统处理
    INTELLIGENT = "intelligent" # 智能模式，使用Agent编排
    HYBRID = "hybrid"          # 混合模式


class AgentWorkflowType(str, enum.Enum):
    """Agent工作流类型"""
    SIMPLE_REPORT = "simple_report"                    # 简单报告生成
    STATISTICAL_ANALYSIS = "statistical_analysis"      # 统计分析
    CHART_GENERATION = "chart_generation"              # 图表生成
    COMPREHENSIVE_ANALYSIS = "comprehensive_analysis"   # 综合分析
    CUSTOM_WORKFLOW = "custom_workflow"                # 自定义工作流


class ReportPeriod(str, enum.Enum):
    """报告周期"""
    DAILY = "daily"         # 日报
    WEEKLY = "weekly"       # 周报
    MONTHLY = "monthly"     # 月报
    YEARLY = "yearly"       # 年报


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    schedule = Column(String, nullable=True)
    report_period = Column(Enum(ReportPeriod, name='reportperiod', values_callable=lambda obj: [e.value for e in obj]), default=ReportPeriod.MONTHLY)  # 报告周期
    recipients = Column(JSON, nullable=True)  # Store list of emails as JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # Foreign key relationships
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False)

    # 新增：Agent编排相关字段
    status = Column(Enum(TaskStatus, name='taskstatus', values_callable=lambda obj: [e.value for e in obj]), default=TaskStatus.PENDING)
    processing_mode = Column(Enum(ProcessingMode, name='processingmode', values_callable=lambda obj: [e.value for e in obj]), default=ProcessingMode.INTELLIGENT)
    workflow_type = Column(Enum(AgentWorkflowType, name='agentworkflowtype', values_callable=lambda obj: [e.value for e in obj]), default=AgentWorkflowType.SIMPLE_REPORT)
    
    # Agent编排配置（内部使用，不对外暴露API）
    orchestration_config = Column(JSON, nullable=True)  # Agent编排配置
    max_context_tokens = Column(Integer, default=32000)
    enable_compression = Column(Boolean, default=True)
    compression_threshold = Column(Float, default=0.8)
    
    # 执行统计
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_execution_at = Column(DateTime, nullable=True)
    
    # 性能指标
    average_execution_time = Column(Float, default=0.0)
    average_token_usage = Column(Integer, default=0)
    last_execution_duration = Column(Float, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="tasks", foreign_keys=[owner_id])
    data_source = relationship("DataSource")
    template = relationship("Template", back_populates="tasks")
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
    report_histories = relationship("ReportHistory", back_populates="task", cascade="all, delete-orphan")

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count
    
    def to_orchestration_context(self) -> dict:
        """转换为Agent编排上下文"""
        return {
            "task_id": self.id,
            "task_name": self.name,
            "processing_mode": self.processing_mode.value if self.processing_mode else "intelligent",
            "workflow_type": self.workflow_type.value if self.workflow_type else "simple_report",
            "template_id": str(self.template_id),
            "data_source_id": str(self.data_source_id),
            "max_context_tokens": self.max_context_tokens,
            "enable_compression": self.enable_compression,
            "compression_threshold": self.compression_threshold,
            "orchestration_config": self.orchestration_config or {},
            "user_id": str(self.owner_id)
        }


class TaskExecution(Base):
    """任务执行记录"""
    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # 关联的任务
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    
    # 执行信息
    execution_status = Column(Enum(TaskStatus, values_callable=lambda obj: [e.value for e in obj]), default=TaskStatus.PENDING)
    workflow_type = Column(Enum(AgentWorkflowType, values_callable=lambda obj: [e.value for e in obj]), default=AgentWorkflowType.SIMPLE_REPORT)
    
    # Agent编排信息（内部使用，不对外暴露）
    workflow_definition = Column(JSON, nullable=True)  # 工作流定义
    agent_execution_plan = Column(JSON, nullable=True)  # Agent执行计划
    current_step = Column(String(255), nullable=True)  # 当前执行步骤
    
    # 执行上下文
    execution_context = Column(JSON, nullable=True)   # 执行上下文
    input_parameters = Column(JSON, nullable=True)    # 输入参数
    processing_config = Column(JSON, nullable=True)   # 处理配置
    
    # 结果信息
    execution_result = Column(JSON, nullable=True)    # 执行结果
    output_artifacts = Column(JSON, nullable=True)    # 输出产物（文件路径、图表等）
    error_details = Column(Text, nullable=True)       # 错误详情
    error_trace = Column(Text, nullable=True)         # 错误堆栈
    
    # 性能指标
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_duration = Column(Integer, nullable=True)   # 总耗时（秒）
    agent_execution_times = Column(JSON, nullable=True)  # 各Agent执行时间
    
    # 进度跟踪
    progress_percentage = Column(Integer, default=0)   # 进度百分比
    progress_details = Column(JSON, nullable=True)     # 详细进度信息
    
    # 系统信息
    celery_task_id = Column(String(255), nullable=True)  # Celery任务ID
    worker_node = Column(String(255), nullable=True)     # 执行节点
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    task = relationship("Task", back_populates="executions")
