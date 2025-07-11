from fastapi import FastAPI
from app.api.router import api_router
from app.core.config import settings
from app.initial_data import init_db
from app.api.endpoints import (
    login,
    templates,
    data_sources,
    ai_providers,
    tasks,
    report_generation,
    analysis,
)

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(data_sources.router, prefix="/api/v1", tags=["data-sources"])
app.include_router(ai_providers.router, prefix="/api/v1", tags=["ai-providers"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(
    report_generation.router, prefix="/api/v1", tags=["report-generation"]
)
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
