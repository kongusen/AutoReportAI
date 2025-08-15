"""
Worker Module

Celery Worker模块，提供：
- Celery应用配置
- 任务定义
- 任务执行器
- 进度管理
"""

# 导入核心组件
from .config.celery_app import celery_app
from .config.task_status import TaskStatus

# 导入任务定义
from .tasks.basic_tasks import (
    template_parsing,
    placeholder_analysis,
    data_query,
    content_filling,
    report_generation,
    execute_etl_job,
    test_celery_task
)

from .tasks.enhanced_tasks import (
    execute_scheduled_task,
    intelligent_report_generation_pipeline,
    enhanced_intelligent_report_generation_pipeline
)

# 导入工具函数
from .utils.progress_utils import (
    update_task_progress,
    update_task_progress_dict,
    send_error_notification,
    safe_update_progress_with_fallback
)

# 模块导出
__all__ = [
    # 核心配置
    "celery_app",
    "TaskStatus",
    
    # 基础任务
    "template_parsing",
    "placeholder_analysis", 
    "data_query",
    "content_filling",
    "report_generation",
    "execute_etl_job",
    "test_celery_task",
    
    # 增强任务
    "execute_scheduled_task",
    "intelligent_report_generation_pipeline",
    "enhanced_intelligent_report_generation_pipeline",
    
    # 工具函数
    "update_task_progress",
    "update_task_progress_dict", 
    "send_error_notification",
    "safe_update_progress_with_fallback",
]
