from fastapi import APIRouter
from app.api.versioning import create_versioned_router, APIVersion, create_version_info_router
from app.api.endpoints import (
    users,
    data_sources,
    templates,
    placeholders,
    reports,
    tasks,  # 重新启用
    etl_jobs,
    llm_servers,  # LLM服务器管理 (替代ai_providers)
    dashboard,
    system,
    auth,
    files,
    history,
    health,
    settings,
    task_scheduler,  # 重新启用
    celery_monitor,  # Celery 监控 - 重新启用
    llm_monitor,  # LLM监控
    chart_test,  # 图表测试
    system_insights,  # 统一上下文系统洞察
    user_llm_preferences,  # 用户LLM偏好管理
    # REMOVED: toolbox - functionality migrated to MCP
    # 如有其它业务模块可继续添加
)
# TEMPORARILY DISABLED: MCP has file encoding issues
# from app.api.endpoints import placeholder_analysis_mcp

api_router = APIRouter()

# 版本信息、健康检查等基础路由
api_router.include_router(create_version_info_router())
api_router.include_router(create_versioned_router(APIVersion.V1))
api_router.include_router(health.router, tags=["健康检查"])

# 业务路由全部加 prefix="/v1"
api_router.include_router(users.router, prefix="/v1/users", tags=["用户管理"])
api_router.include_router(data_sources.router, prefix="/v1/data-sources", tags=["数据源"])
api_router.include_router(templates.router, prefix="/v1/templates", tags=["模板管理"])
api_router.include_router(placeholders.router, prefix="/v1/placeholders", tags=["占位符管理"])
api_router.include_router(reports.router, prefix="/v1/reports", tags=["报告管理"])
api_router.include_router(tasks.router, prefix="/v1/tasks", tags=["任务管理"])  # 重新启用
api_router.include_router(etl_jobs.router, prefix="/v1/etl-jobs", tags=["ETL作业"])
api_router.include_router(llm_servers.router, prefix="/v1/llm-servers", tags=["LLM服务器管理"])
api_router.include_router(dashboard.router, prefix="/v1/dashboard", tags=["仪表盘"])
api_router.include_router(system.router, prefix="/v1/system", tags=["系统管理"])
api_router.include_router(auth.router, prefix="/v1/auth", tags=["认证"])
api_router.include_router(files.router, prefix="/v1/files", tags=["文件管理"])
api_router.include_router(history.router, prefix="/v1/history", tags=["历史记录"])
# 智能占位符功能已整合到templates.router中
api_router.include_router(settings.router, prefix="/v1/settings", tags=["用户设置"])
api_router.include_router(task_scheduler.router, prefix="/v1/task-scheduler", tags=["任务调度"])
api_router.include_router(chart_test.router, prefix="/v1/chart-test", tags=["图表测试"])
api_router.include_router(system_insights.router, prefix="/v1/system-insights", tags=["系统洞察"])
api_router.include_router(celery_monitor.router, prefix="/v1/celery", tags=["Celery监控"])  # 重新启用
api_router.include_router(llm_monitor.router, prefix="/v1/llm", tags=["LLM监控"])
api_router.include_router(user_llm_preferences.router, prefix="/v1/user-llm-preferences", tags=["用户LLM偏好"])
# api_router.include_router(intelligent_agents.router, tags=["智能代理"])  # Disabled legacy llm_agents
# api_router.include_router(intelligent_templates.router, prefix="/v1/intelligent-templates", tags=["智能模板"])
# REMOVED: Toolbox router - functionality migrated to MCP


# MCP版本的占位符分析API - TEMPORARILY DISABLED: encoding issues
# api_router.include_router(
#     placeholder_analysis_mcp.router,
#     prefix="/placeholders-mcp", 
#     tags=["placeholders-mcp"]
# )