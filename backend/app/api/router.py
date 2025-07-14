from fastapi import APIRouter, Depends

from app.api import deps
from app.api.endpoints import (
    ai_providers,
    data_sources,
    etl_jobs,
    history,
    login,
    report_generation,
    tasks,
    template_analysis,
    users,
    enhanced_data_sources,
    mcp_analytics,
)

api_router = APIRouter()
api_router.include_router(login.router, prefix="/auth", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(
    ai_providers.router, prefix="/ai-providers", tags=["ai-providers"]
)
api_router.include_router(
    data_sources.router, prefix="/data-sources", tags=["data-sources"]
)
api_router.include_router(
    enhanced_data_sources.router, 
    prefix="/enhanced-data-sources", 
    tags=["enhanced-data-sources"]
)
api_router.include_router(
    mcp_analytics.router,
    prefix="/mcp-analytics",
    tags=["mcp-analytics"]
)
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(etl_jobs.router, prefix="/etl-jobs", tags=["etl-jobs"])
api_router.include_router(
    report_generation.router, prefix="/reports", tags=["report-generation"]
)
api_router.include_router(
    template_analysis.router, prefix="/templates", tags=["templates"]
)
api_router.include_router(
    history.router, prefix="/history", tags=["history"]
)
