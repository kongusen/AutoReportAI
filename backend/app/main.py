import redis.asyncio as redis
from fastapi import Depends, FastAPI
from fastapi_limiter import FastAPILimiter

from app.api.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.initial_data import init_db

# Setup logging as soon as the application starts
setup_logging()

app = FastAPI(title=settings.PROJECT_NAME)


@app.on_event("startup")
async def startup():
    # setup_logging() # Can be called again if needed, it's idempotent
    init_db()
    redis_connection = redis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    await FastAPILimiter.init(redis_connection)


# All API routes are handled by the api_router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
