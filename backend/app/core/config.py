from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoReportAI"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@host:port/db")

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
