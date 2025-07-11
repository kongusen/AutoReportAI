from pydantic import BaseSettings
import os
from typing import Dict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoReportAI"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@host:port/db")

    # Service URLs for FastMCP
    SERVICE_URLS: Dict[str, str] = {
        "ai_service": os.getenv("AI_SERVICE_URL", "http://localhost:8000/api/v1/ai"),
        # We can add other services here in the future
    }

    # Email settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER", "user@example.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "your_password")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@example.com")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "AutoReportAI")

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
