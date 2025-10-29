"""API endpoints module - 统一架构版本"""

# 核心业务模块
from . import (
    auth,
    users, 
    data_sources,
    templates,
    placeholders,
    placeholder_async_tasks,
    reports,
)

# 任务执行模块
from . import (
    tasks,
    task_execution,
    task_scheduler,
)

# ETL与数据处理
from . import etl_jobs

# AI/LLM服务
from . import (
    llm_servers,
    llm_monitor,
    llm_orchestration,
    simple_model_selection,
    model_execution,
    user_llm_preferences,
)

# Agent流式处理
from . import (
    agent_stream,
    agent_run,
    # sql_enhanced,  # temporarily disabled due to missing components
)

# 系统管理
from . import (
    system,
    system_health,
    system_insights,
    health,
)

# 工具与监控
from . import (
    dashboard,
    files,
    history,
    settings,
    notifications,
    celery_monitor,
    chart_test,
)
