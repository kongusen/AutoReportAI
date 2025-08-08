from fastapi import APIRouter
from app.api.versioning import create_versioned_router, APIVersion, create_version_info_router
from app.api.endpoints import (
    users,
    data_sources,
    templates,
    reports,
    tasks,
    etl_jobs,
    ai_providers,
    dashboard,
    system,
    auth,
    files,
    history,
    intelligent_placeholders,
    health,
    settings,
    # 如有其它业务模块可继续添加
)

api_router = APIRouter()

# 版本信息、健康检查等基础路由
api_router.include_router(create_version_info_router())
api_router.include_router(create_versioned_router(APIVersion.V1))
api_router.include_router(health.router, tags=["健康检查"])

# 业务路由全部加 prefix="/v1"
api_router.include_router(users.router, prefix="/v1/users", tags=["用户管理"])
api_router.include_router(data_sources.router, prefix="/v1/data-sources", tags=["数据源"])
api_router.include_router(templates.router, prefix="/v1/templates", tags=["模板管理"])
api_router.include_router(reports.router, prefix="/v1/reports", tags=["报告管理"])
api_router.include_router(tasks.router, prefix="/v1/tasks", tags=["任务管理"])
api_router.include_router(etl_jobs.router, prefix="/v1/etl-jobs", tags=["ETL作业"])
api_router.include_router(ai_providers.router, prefix="/v1/ai-providers", tags=["AI提供商"])
api_router.include_router(dashboard.router, prefix="/v1/dashboard", tags=["仪表盘"])
api_router.include_router(system.router, prefix="/v1/system", tags=["系统管理"])
api_router.include_router(auth.router, prefix="/v1/auth", tags=["认证"])
api_router.include_router(files.router, prefix="/v1/files", tags=["文件管理"])
api_router.include_router(history.router, prefix="/v1/history", tags=["历史记录"])
api_router.include_router(intelligent_placeholders.router, prefix="/v1/intelligent-placeholders", tags=["智能占位符"])
api_router.include_router(settings.router, prefix="/v1/settings", tags=["用户设置"])
