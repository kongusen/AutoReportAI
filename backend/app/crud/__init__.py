from .crud_ai_provider import crud_ai_provider
from .crud_analytics_data import analytics_data
from .crud_data_source import crud_data_source as data_source
from .crud_etl_job import crud_etl_job
from .crud_placeholder_mapping import crud_placeholder_mapping as placeholder_mapping
from .crud_report_history import report_history
from .crud_task import crud_task as task
from .crud_task_execution import crud_task_execution
from .crud_template import crud_template as template
from .crud_user import crud_user
from .crud_user_profile import user_profile

# Task执行记录CRUD操作（内部使用，支持Agent编排）

# Aliases for easier access
ai_provider = crud_ai_provider
etl_job = crud_etl_job
user = crud_user

__all__ = [
    # 原有CRUD
    "crud_ai_provider",
    "ai_provider",
    "analytics_data", 
    "data_source",
    "crud_etl_job",
    "etl_job",
    "placeholder_mapping",
    "report_history",
    "task",
    "crud_task_execution",
    "template",
    "crud_user",
    "user",
    "user_profile",
]
