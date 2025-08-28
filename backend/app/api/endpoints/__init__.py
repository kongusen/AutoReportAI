"""API v2 端点模块"""

# 导入所有端点模块
from . import (
    auth, 
    celery_monitor,
    dashboard,
    data_sources,
    etl_jobs,
    files,
    health,
    history,
    llm_monitor,
    llm_servers,  # LLM服务器管理 (替代ai_providers)
    placeholder_analysis,
    placeholders,
    reports,
    settings,
    system,
    task_scheduler,
    tasks,
    templates,
    users
)
