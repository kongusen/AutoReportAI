"""
优化的CRUD操作包
提供统一的数据访问接口
"""

from .crud_data_source import crud_data_source
from .crud_user import crud_user
from .crud_template import crud_template
from .crud_etl_job import crud_etl_job
from .crud_task import crud_task
from .crud_report import crud_report

# CRUD实例列表
__all__ = [
    "crud_data_source",
    "crud_user",
    "crud_template", 
    "crud_etl_job",
    "crud_task",
    "crud_report"
]

# CRUD映射字典
CRUD_MAPPING = {
    "data_source": crud_data_source,
    "user": crud_user,
    "template": crud_template,
    "etl_job": crud_etl_job,
    "task": crud_task,
    "report": crud_report
}


def get_crud_by_name(model_name: str):
    """根据模型名称获取对应的CRUD实例"""
    return CRUD_MAPPING.get(model_name.lower())