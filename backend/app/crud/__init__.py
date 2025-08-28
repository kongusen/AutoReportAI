from .crud_analytics_data import analytics_data
from .crud_data_source import crud_data_source as data_source
from .crud_etl_job import crud_etl_job
from .crud_llm_server import crud_llm_server
from .crud_llm_model import crud_llm_model
from .crud_placeholder_mapping import crud_placeholder_mapping as placeholder_mapping
from .crud_report_history import report_history
from .crud_task import crud_task as task
from .crud_task_execution import crud_task_execution
from .crud_template import crud_template as template
from .crud_template_placeholder import CRUDTemplatePlaceholder
from app.models.template_placeholder import TemplatePlaceholder
from .crud_user import crud_user
from .crud_user_llm_preference import crud_user_llm_preference, crud_user_llm_usage_quota
from .crud_user_profile import user_profile

# Task执行记录CRUD操作（内部使用，支持Agent编排）

# Aliases for easier access
etl_job = crud_etl_job
user = crud_user
template_placeholder = CRUDTemplatePlaceholder(TemplatePlaceholder)

__all__ = [
    # 原有CRUD
    "analytics_data", 
    "data_source",
    "crud_etl_job",
    "etl_job",
    # LLM相关CRUD
    "crud_llm_server",
    "crud_llm_model",
    "crud_user_llm_preference",
    "crud_user_llm_usage_quota",
    "placeholder_mapping",
    "report_history",
    "task",
    "crud_task_execution",
    "template",
    "template_placeholder",
    "CRUDTemplatePlaceholder",
    "crud_user",
    "user",
    "user_profile",
]
