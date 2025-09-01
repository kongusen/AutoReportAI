"""API v2 端点模块"""

# 导入所有端点模块
from . import (
    auth, 
    celery_monitor,  # 重新启用
    dashboard,
    data_sources,
    etl_jobs,
    files,
    health,
    history,
    # intelligent_agents,  # Disabled - uses legacy llm_agents modules
    # intelligent_templates,  # Disabled - might depend on legacy modules
    llm_monitor,
    llm_servers,  # LLM服务器管理 (替代ai_providers)
    # placeholder_analysis,  # File does not exist
    placeholders,
    reports,
    settings,
    system,
    system_insights,  # 系统洞察端点
    task_scheduler,
    tasks,  # 重新启用
    templates,
    user_llm_preferences,  # 用户LLM偏好管理
    users,
    chart_test  # 图表测试端点
)
