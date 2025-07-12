from fastapi import APIRouter, Depends

from app.api import deps
from app.api.endpoints import (  # tools, # This was the old placeholder_tools, which is now obsolete
    ai,
    ai_providers,
    analysis,
    data_sources,
    data_sourcing,
    etl_jobs,
    login,
    mapping_management,
    report_generation,
    task_management,
    tasks,
    template_analysis,
    users,
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
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(etl_jobs.router, prefix="/etl-jobs", tags=["etl-jobs"])
api_router.include_router(
    report_generation.router, prefix="/reports", tags=["report-generation"]
)


# Deprecated or to be refactored routes that should be cleaned up.
# For now we can comment them out to avoid conflicts.
# api_router.include_router(
#     template_analysis.router,
#     prefix="/template-analysis",
#     tags=["template-analysis"],
# )
# api_router.include_router(
#     report_generation.router,
#     prefix="/report-generation",
#     tags=["report-generation"],
# )
# api_router.include_router(
#     data_sourcing.router, prefix="/data-sourcing", tags=["data-sourcing"]
# )
# api_router.include_router(
#     mapping_management.router,
#     prefix="/mapping-management",
#     tags=["mapping-management"],
# )
# api_router.include_router(
#     task_management.router, prefix="/task-management", tags=["task-management"]
# )
# api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
# api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

# The /tools route from placeholder_tools is now obsolete.
# api_router.include_router(
#     tools.router, prefix="/tools", tags=["placeholder-tools"]
# )
