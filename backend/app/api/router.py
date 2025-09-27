from fastapi import APIRouter
from app.api.versioning import create_versioned_router, APIVersion, create_version_info_router
from app.api.endpoints import (
    # 核心业务模块
    auth,
    users,
    data_sources,
    templates,
    placeholders,
    reports,

    # 任务执行
    tasks,
    task_execution,
    task_scheduler,

    # ETL与数据处理
    etl_jobs,

    # AI/LLM服务
    llm_servers,
    llm_monitor,
    llm_orchestration,
    simple_model_selection,
    model_execution,
    user_llm_preferences,

    # Agent流式处理
    agent_stream,
    agent_run,
    # sql_enhanced,

    # 系统管理
    system,
    system_health,
    system_insights,
    health,

    # 流水线管理
    pipeline_management,
    template_analysis_adapter,
    pipeline_websocket,

    # 报告工作流
    report_workflow,

    # 系统验证
    system_validation,

    # 工具与监控
    dashboard,
    files,
    history,
    settings,
    notifications,
    celery_monitor,
    chart_test,
)

api_router = APIRouter()

# 版本信息和健康检查
api_router.include_router(create_version_info_router())
api_router.include_router(create_versioned_router(APIVersion.V1))
api_router.include_router(health.router, tags=["健康检查"])

# 核心业务路由 - /v1/
api_router.include_router(auth.router, prefix="/v1/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/v1/users", tags=["用户管理"])
api_router.include_router(data_sources.router, prefix="/v1/data-sources", tags=["数据源"])
api_router.include_router(templates.router, prefix="/v1/templates", tags=["模板管理"])
api_router.include_router(placeholders.router, prefix="/v1/placeholders", tags=["占位符管理"])
api_router.include_router(reports.router, prefix="/v1/reports", tags=["报告管理"])

# 任务执行路由
api_router.include_router(tasks.router, prefix="/v1/tasks", tags=["任务管理"])
api_router.include_router(task_execution.router, prefix="/v1/task-execution", tags=["任务执行"])
api_router.include_router(task_scheduler.router, prefix="/v1/task-scheduler", tags=["任务调度"])

# ETL与数据处理
api_router.include_router(etl_jobs.router, prefix="/v1/etl-jobs", tags=["ETL作业"])

# AI/LLM服务路由
api_router.include_router(llm_servers.router, prefix="/v1/llm-servers", tags=["LLM服务器"])
api_router.include_router(llm_monitor.router, prefix="/v1/llm-monitor", tags=["LLM监控"])
api_router.include_router(llm_orchestration.router, prefix="/v1/llm-orchestration", tags=["LLM编排"])
api_router.include_router(simple_model_selection.router, prefix="/v1/model-selection", tags=["模型选择"])

# Agent API路由（版本化路径）
api_router.include_router(agent_stream.router, prefix="/v1/agent", tags=["Agent流式处理（已废弃）"])
api_router.include_router(agent_run.router, prefix="/v1/agent", tags=["Agent执行"])

# Agent API路由（无版本别名，为生产稳定路径）
# 提供 /api/agent/* 以匹配外部集成与示例文档
api_router.include_router(agent_run.router, prefix="/agent", tags=["Agent执行（稳定别名）"])

# SQL增强处理API路由 - temporarily disabled due to missing components
# api_router.include_router(sql_enhanced.router, prefix="/v1/sql", tags=["SQL增强处理"])
api_router.include_router(model_execution.router, prefix="/v1/model-execution", tags=["模型执行"])
api_router.include_router(user_llm_preferences.router, prefix="/v1/llm-preferences", tags=["LLM偏好"])

# 系统管理路由
api_router.include_router(system.router, prefix="/v1/system", tags=["系统管理"])
api_router.include_router(system_health.router, prefix="/v1/system-health", tags=["系统健康"])
api_router.include_router(system_insights.router, prefix="/v1/system-insights", tags=["系统洞察"])

# 流水线管理路由
api_router.include_router(pipeline_management.router, prefix="/v1/pipeline", tags=["流水线管理"])

# 模板分析适配器路由 - 前端兼容性
api_router.include_router(template_analysis_adapter.router, prefix="/v1", tags=["模板分析"])

# 流水线WebSocket路由 - 实时更新
api_router.include_router(pipeline_websocket.router, prefix="/v1/pipeline/ws", tags=["流水线实时通信"])

# 报告工作流路由 - 模板化SQL报告生成
api_router.include_router(report_workflow.router, prefix="/v1/report-workflow", tags=["报告工作流"])

# 系统验证路由 - 验证新功能
api_router.include_router(system_validation.router, prefix="/v1/system-validation", tags=["系统验证"])

# 工具与监控路由
api_router.include_router(dashboard.router, prefix="/v1/dashboard", tags=["仪表盘"])
api_router.include_router(files.router, prefix="/v1/files", tags=["文件管理"])
api_router.include_router(history.router, prefix="/v1/history", tags=["历史记录"])
api_router.include_router(settings.router, prefix="/v1/settings", tags=["用户设置"])
api_router.include_router(notifications.router, prefix="/v1/notifications", tags=["通知系统"])
api_router.include_router(celery_monitor.router, prefix="/v1/celery-monitor", tags=["Celery监控"])
api_router.include_router(chart_test.router, prefix="/v1/chart-test", tags=["图表测试"])
