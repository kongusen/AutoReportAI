from fastapi import APIRouter
from app.api.endpoints import (
    template_analysis, 
    data_sourcing, 
    task_management, 
    mapping_management,
    ai,
    login,
    ai_providers,
    data_sources,
    tools
)
from fastapi import Depends
from app.api import deps

api_router = APIRouter()

# Authentication Router
api_router.include_router(login.router, tags=["0. Authentication"])

# Protected Routers
protected_router = APIRouter(dependencies=[Depends(deps.get_current_user)])
protected_router.include_router(template_analysis.router, prefix="/templates", tags=["1. Template Management"])
protected_router.include_router(mapping_management.router, prefix="", tags=["2. Data Mapping"])
protected_router.include_router(data_sourcing.router, prefix="/sourcing", tags=["3. Data Sourcing (Internal)"])
protected_router.include_router(ai.router, prefix="/ai", tags=["4. AI Service"])
protected_router.include_router(task_management.router, prefix="/tasks", tags=["6. Task Management"])
protected_router.include_router(ai_providers.router, prefix="/ai-providers", tags=["7. AI Provider Management"])
protected_router.include_router(data_sources.router, prefix="/data-sources", tags=["8. Data Source Management"])
protected_router.include_router(tools.router, prefix="/tools", tags=["9. AI Agent Tools"])


api_router.include_router(protected_router)
