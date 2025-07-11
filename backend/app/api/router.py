from fastapi import APIRouter
from app.api.endpoints import (
    template_analysis, 
    data_sourcing, 
    report_generation, 
    task_management, 
    mapping_management,
    ai
)

api_router = APIRouter()
api_router.include_router(template_analysis.router, prefix="/templates", tags=["1. Template Management"])
api_router.include_router(mapping_management.router, prefix="", tags=["2. Data Mapping"])
# The data_sourcing endpoint might be deprecated or changed, let's tag it as internal for now
api_router.include_router(data_sourcing.router, prefix="/data", tags=["3. Data Sourcing (Internal)"])
api_router.include_router(ai.router, prefix="/ai", tags=["4. AI Service"])
api_router.include_router(report_generation.router, prefix="/reports", tags=["5. Report Generation"])
api_router.include_router(task_management.router, prefix="/tasks", tags=["6. Task Management"])
