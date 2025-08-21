"""
Task Domain Entity

任务领域实体，包含任务的业务逻辑
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    CREATED = "created"
    SCHEDULED = "scheduled"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ExecutionMode(Enum):
    """执行模式"""
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"
    MANUAL = "manual"


@dataclass
class TaskExecution:
    """任务执行记录"""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    execution_mode: ExecutionMode = ExecutionMode.MANUAL
    
    # 执行结果
    result_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    # 性能指标
    execution_time_seconds: Optional[float] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    
    # 上下文信息
    context: Dict[str, Any] = field(default_factory=dict)
    triggered_by: Optional[str] = None
    worker_id: Optional[str] = None
    
    @property
    def duration(self) -> Optional[timedelta]:
        """执行时长"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def start(self, worker_id: Optional[str] = None):
        """开始执行"""
        self.started_at = datetime.utcnow()
        self.status = TaskStatus.RUNNING
        self.worker_id = worker_id
    
    def complete(self, result_data: Dict[str, Any] = None):
        """完成执行"""
        self.completed_at = datetime.utcnow()
        self.status = TaskStatus.COMPLETED
        if result_data:
            self.result_data = result_data
        
        if self.started_at:
            self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def fail(self, error_message: str):
        """标记失败"""
        self.completed_at = datetime.utcnow()
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        
        if self.started_at:
            self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()


@dataclass
class ScheduleConfig:
    """调度配置"""
    cron_expression: Optional[str] = None
    enabled: bool = True
    timezone: str = "UTC"
    max_retries: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: Optional[int] = None
    
    # 执行窗口
    execution_window_start: Optional[str] = None  # HH:MM格式
    execution_window_end: Optional[str] = None    # HH:MM格式
    
    def is_valid(self) -> bool:
        """验证调度配置"""
        if not self.enabled:
            return True
        
        if not self.cron_expression:
            return False
        
        # 这里可以添加更多的cron表达式验证逻辑
        return True


class TaskEntity:
    """任务实体"""
    
    def __init__(self, task_id: str, name: str, task_type: str = "report_generation"):
        self.id = task_id
        self.name = name
        self.task_type = task_type
        
        # 基本属性
        self.description = ""
        self.priority = TaskPriority.NORMAL
        self.status = TaskStatus.CREATED
        
        # 配置信息
        self.configuration = {}
        self.parameters = {}
        self.metadata = {}
        
        # 关联信息
        self.template_id: Optional[str] = None
        self.data_source_id: Optional[str] = None
        self.owner_id: Optional[str] = None
        
        # 调度配置
        self.schedule_config: Optional[ScheduleConfig] = None
        
        # 执行历史
        self.executions: List[TaskExecution] = []
        self.current_execution: Optional[TaskExecution] = None
        
        # 审计信息
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.created_by: Optional[str] = None
        
        # 状态管理
        self.is_active = True
        self.is_deleted = False
        
        # 统计信息
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.last_successful_execution_at: Optional[datetime] = None
        self.last_failed_execution_at: Optional[datetime] = None
    
    def set_schedule(self, schedule_config: ScheduleConfig):
        """设置调度配置"""
        if not schedule_config.is_valid():
            raise ValueError("Invalid schedule configuration")
        
        self.schedule_config = schedule_config
        self.updated_at = datetime.utcnow()
        logger.info(f"Task {self.id} schedule updated: {schedule_config.cron_expression}")
    
    def remove_schedule(self):
        """移除调度配置"""
        self.schedule_config = None
        self.updated_at = datetime.utcnow()
    
    def start_execution(self, execution_mode: ExecutionMode = ExecutionMode.MANUAL,
                       triggered_by: Optional[str] = None,
                       context: Dict[str, Any] = None) -> TaskExecution:
        """开始执行"""
        if self.current_execution and self.current_execution.status == TaskStatus.RUNNING:
            raise ValueError("Task is already running")
        
        if not self.is_active:
            raise ValueError("Task is not active")
        
        execution = TaskExecution(
            execution_mode=execution_mode,
            triggered_by=triggered_by,
            context=context or {}
        )
        
        execution.start()
        self.current_execution = execution
        self.executions.append(execution)
        self.status = TaskStatus.RUNNING
        self.total_executions += 1
        self.updated_at = datetime.utcnow()
        
        logger.info(f"Task {self.id} execution started: {execution.execution_id}")
        return execution
    
    def complete_execution(self, result_data: Dict[str, Any] = None):
        """完成当前执行"""
        if not self.current_execution:
            raise ValueError("No active execution")
        
        self.current_execution.complete(result_data)
        self.status = TaskStatus.COMPLETED
        self.successful_executions += 1
        self.last_successful_execution_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        logger.info(f"Task {self.id} execution completed: {self.current_execution.execution_id}")
    
    def fail_execution(self, error_message: str):
        """标记当前执行失败"""
        if not self.current_execution:
            raise ValueError("No active execution")
        
        self.current_execution.fail(error_message)
        self.status = TaskStatus.FAILED
        self.failed_executions += 1
        self.last_failed_execution_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        logger.error(f"Task {self.id} execution failed: {error_message}")
    
    def cancel_execution(self):
        """取消当前执行"""
        if not self.current_execution:
            raise ValueError("No active execution")
        
        self.current_execution.status = TaskStatus.CANCELLED
        self.current_execution.completed_at = datetime.utcnow()
        self.status = TaskStatus.CANCELLED
        self.updated_at = datetime.utcnow()
        
        logger.info(f"Task {self.id} execution cancelled: {self.current_execution.execution_id}")
    
    def activate(self):
        """激活任务"""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """停用任务"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def delete(self):
        """软删除任务"""
        self.is_deleted = True
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def get_latest_execution(self) -> Optional[TaskExecution]:
        """获取最新执行记录"""
        if not self.executions:
            return None
        
        return max(self.executions, key=lambda e: e.started_at or datetime.min)
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_executions == 0:
            return 0.0
        
        return self.successful_executions / self.total_executions
    
    def get_average_execution_time(self) -> Optional[float]:
        """获取平均执行时间"""
        completed_executions = [
            e for e in self.executions 
            if e.execution_time_seconds is not None
        ]
        
        if not completed_executions:
            return None
        
        total_time = sum(e.execution_time_seconds for e in completed_executions)
        return total_time / len(completed_executions)
    
    def can_be_scheduled(self) -> bool:
        """检查是否可以被调度"""
        return (
            self.is_active and 
            not self.is_deleted and
            self.schedule_config is not None and
            self.schedule_config.enabled
        )
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return (
            self.current_execution is not None and
            self.current_execution.status == TaskStatus.RUNNING
        )
    
    def update_configuration(self, config: Dict[str, Any]):
        """更新配置"""
        self.configuration.update(config)
        self.updated_at = datetime.utcnow()
    
    def update_parameters(self, parameters: Dict[str, Any]):
        """更新参数"""
        self.parameters.update(parameters)
        self.updated_at = datetime.utcnow()
    
    def validate(self) -> List[str]:
        """验证任务配置"""
        errors = []
        
        if not self.name or not self.name.strip():
            errors.append("Task name is required")
        
        if not self.task_type:
            errors.append("Task type is required")
        
        if self.schedule_config and not self.schedule_config.is_valid():
            errors.append("Invalid schedule configuration")
        
        if self.task_type == "report_generation":
            if not self.template_id:
                errors.append("Template ID is required for report generation tasks")
            if not self.data_source_id:
                errors.append("Data source ID is required for report generation tasks")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "configuration": self.configuration,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "template_id": self.template_id,
            "data_source_id": self.data_source_id,
            "owner_id": self.owner_id,
            "schedule_config": self.schedule_config.__dict__ if self.schedule_config else None,
            "is_active": self.is_active,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": self.get_success_rate(),
            "average_execution_time": self.get_average_execution_time(),
            "is_running": self.is_running()
        }