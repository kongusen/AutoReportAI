"""
优化的数据模型包
统一导出所有优化后的模型类
"""

from .data_source import DataSource, DataSourceType, ConnectionStatus
from .user import User, UserStatus, UserRole
from .template import Template, TemplateType, TemplateStatus, TemplateCategory
from .etl_job import ETLJob, ETLJobType, ETLJobStatus, ETLJobPriority
from .task import Task, TaskType, TaskStatus, TaskPriority
from .report import Report, ReportType, ReportStatus, ReportFormat

# 模型类列表
__all__ = [
    # 模型类
    "DataSource",
    "User", 
    "Template",
    "ETLJob",
    "Task",
    "Report",
    
    # 枚举类
    "DataSourceType",
    "ConnectionStatus",
    "UserStatus",
    "UserRole",
    "TemplateType",
    "TemplateStatus", 
    "TemplateCategory",
    "ETLJobType",
    "ETLJobStatus",
    "ETLJobPriority",
    "TaskType",
    "TaskStatus",
    "TaskPriority",
    "ReportType",
    "ReportStatus",
    "ReportFormat"
]

# 模型映射字典，便于动态访问
MODEL_MAPPING = {
    "data_source": DataSource,
    "user": User,
    "template": Template,
    "etl_job": ETLJob,
    "task": Task,
    "report": Report
}

# 枚举映射字典
ENUM_MAPPING = {
    "data_source_type": DataSourceType,
    "connection_status": ConnectionStatus,
    "user_status": UserStatus,
    "user_role": UserRole,
    "template_type": TemplateType,
    "template_status": TemplateStatus,
    "template_category": TemplateCategory,
    "etl_job_type": ETLJobType,
    "etl_job_status": ETLJobStatus,
    "etl_job_priority": ETLJobPriority,
    "task_type": TaskType,
    "task_status": TaskStatus,
    "task_priority": TaskPriority,
    "report_type": ReportType,
    "report_status": ReportStatus,
    "report_format": ReportFormat
}


def get_model_by_name(model_name: str):
    """根据名称获取模型类"""
    return MODEL_MAPPING.get(model_name.lower())


def get_enum_by_name(enum_name: str):
    """根据名称获取枚举类"""
    return ENUM_MAPPING.get(enum_name.lower())


def get_all_models():
    """获取所有模型类"""
    return list(MODEL_MAPPING.values())


def get_all_enums():
    """获取所有枚举类"""
    return list(ENUM_MAPPING.values())