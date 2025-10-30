import os
from typing import Dict, List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 安全加载 dotenv，避免在容器环境中的 AssertionError
try:
    load_dotenv()
except (AssertionError, AttributeError):
    # 在某些容器环境中直接使用环境变量
    pass


def detect_environment():
    """检测运行环境：Docker 还是本地"""
    # 检查是否在 Docker 容器内
    if os.path.exists("/.dockerenv"):
        return "docker"
    
    # 检查环境变量
    if os.getenv("DOCKER_ENV") == "true":
        return "docker"
    
    # 检查是否能连接到 Docker 服务名
    try:
        import socket
        socket.gethostbyname("db")
        return "docker"
    except:
        return "local"


def get_database_url():
    """根据环境获取数据库连接URL"""
    # 优先使用环境变量中的完整URL
    if database_url := os.getenv("DATABASE_URL"):
        return database_url
    
    # 根据环境动态生成URL
    env = detect_environment()
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "postgres123")  # 修改默认密码以匹配Docker配置
    db_name = os.getenv("POSTGRES_DB", "autoreport")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    
    if env == "docker":
        db_host = "db"  # Docker服务名
    else:
        db_host = "localhost"  # 本地环境
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_database_pool_config():
    """获取数据库连接池配置"""
    env = detect_environment()
    
    if env == "docker":
        # 生产/容器环境：更保守的连接池设置
        return {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),           # 基础连接池大小
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "30")),     # 最大溢出连接
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),     # 获取连接超时时间
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),   # 连接回收时间(1小时)
            "pool_pre_ping": True,                                       # 连接前ping测试
            "connect_args": {
                "connect_timeout": 10,                                   # 连接超时
                "application_name": "AutoReportAI"
            }
        }
    else:
        # 开发环境：较小的连接池设置
        return {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "20")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),   # 30分钟
            "pool_pre_ping": True,
            "connect_args": {
                "connect_timeout": 5,
                "application_name": "AutoReportAI-Dev"
            }
        }


def get_redis_url():
    """根据环境获取Redis连接URL"""
    # 优先使用环境变量中的完整URL
    if redis_url := os.getenv("REDIS_URL"):
        return redis_url
    
    # 根据环境动态生成URL
    env = detect_environment()
    redis_port = os.getenv("REDIS_PORT", "6379")
    
    if env == "docker":
        redis_host = "redis"  # Docker服务名
        redis_db = "1"  # Docker环境使用数据库1
    else:
        redis_host = "localhost"  # 本地环境
        redis_db = "0"  # 本地环境使用数据库0
    
    return f"redis://{redis_host}:{redis_port}/{redis_db}"


class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoReportAI"
    API_V1_STR: str = "/api/v1"

    # 环境信息和调试设置
    ENVIRONMENT_TYPE: str = detect_environment()
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database configuration - 智能环境检测
    DATABASE_URL: str = get_database_url()

    # Redis configuration - 智能环境检测  
    REDIS_URL: str = get_redis_url()

    # 时区设置
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Shanghai")

    # Email settings
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "noreply@autoreportai.com")
    SENDER_NAME: str = os.getenv("SENDER_NAME", "AutoReportAI")

    # SMTP configuration - React Agent system
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.example.com")
    SMTP_USER: str = os.getenv("SMTP_USER", "user@example.com")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@example.com")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "AutoReportAI")

    # WebSocket settings
    WS_HOST: str = os.getenv("WS_HOST", "localhost")
    WS_PORT: int = int(os.getenv("WS_PORT", 8000))
    
    # Server settings
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Notification settings
    ENABLE_EMAIL_NOTIFICATIONS: bool = (
        os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "true").lower() == "true"
    )
    ENABLE_WEBSOCKET_NOTIFICATIONS: bool = (
        os.getenv("ENABLE_WEBSOCKET_NOTIFICATIONS", "true").lower() == "true"
    )

    test_db_user: str = os.getenv("TEST_POSTGRES_USER", "testuser")
    test_db_password: str = os.getenv("TEST_POSTGRES_PASSWORD", "testpassword")
    test_db_host: str = os.getenv("TEST_POSTGRES_HOST", "localhost")
    test_db_port: str = os.getenv("TEST_POSTGRES_PORT", "5433")
    test_db_name: str = os.getenv("TEST_POSTGRES_DB", "test_app")
    test_db_url: str = (
        f"postgresql://{test_db_user}:{test_db_password}@{test_db_host}:{test_db_port}/{test_db_name}"
    )

    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    ALGORITHM: str = "HS256"
    access_token_expire_minutes: int = 60

    # Encryption key for sensitive data.
    # 优先级：环境变量 > 默认值
    # 生产环境必须在 .env 或环境变量中设置 ENCRYPTION_KEY
    # 生成新密钥命令: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = os.getenv(
        "ENCRYPTION_KEY", "DO2E-DOAveBMXpu1xMTl9fRjehX_1pbDnVZkuFRDA14="
    )

    # Celery配置
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = os.getenv("CELERY_TIMEZONE", "UTC")
    CELERY_ENABLE_UTC: bool = True
    
    # 应用时区配置
    APP_TIMEZONE: str = os.getenv("APP_TIMEZONE", "Asia/Shanghai")
    
    # ===========================================
    # React Agent 系统配置
    # ===========================================

    # React Agent 基础配置
    REACT_AGENT_ENABLED: bool = os.getenv("REACT_AGENT_ENABLED", "true").lower() == "true"
    REACT_AGENT_MAX_ITERATIONS: int = int(os.getenv("REACT_AGENT_MAX_ITERATIONS", "15"))
    REACT_AGENT_TIMEOUT: int = int(os.getenv("REACT_AGENT_TIMEOUT", "300"))
    REACT_AGENT_VERBOSE: bool = os.getenv("REACT_AGENT_VERBOSE", "false").lower() == "true"

    # 🆕 [T050] Agent上下文管理配置 - 启用ResourcePool精简记忆模式
    # True: 使用ResourcePool模式（轻量级ContextMemory，减少token使用）
    # False: 使用传统模式（完整schema累积传递）
    ENABLE_CONTEXT_CURATION: bool = os.getenv("ENABLE_CONTEXT_CURATION", "true").lower() == "true"
    
    # React Agent LlamaIndex配置
    REACT_AGENT_CACHE_DIR: str = os.getenv("REACT_AGENT_CACHE_DIR", "cache/llamaindex")
    REACT_AGENT_STORAGE_DIR: str = os.getenv("REACT_AGENT_STORAGE_DIR", "storage")
    
    # ===========================================
    # Celery 高级配置
    # ===========================================
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", 1))
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", 1000))

    # 监控配置
    ENABLE_MONITORING: bool = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    MONITORING_CHECK_INTERVAL: int = int(os.getenv("MONITORING_CHECK_INTERVAL", 300))  # 5分钟
    
    # 告警阈值配置
    ALERT_FAILURE_RATE_WARNING: float = float(os.getenv("ALERT_FAILURE_RATE_WARNING", 0.1))  # 10%
    ALERT_FAILURE_RATE_CRITICAL: float = float(os.getenv("ALERT_FAILURE_RATE_CRITICAL", 0.2))  # 20%
    ALERT_AVG_TIME_WARNING: int = int(os.getenv("ALERT_AVG_TIME_WARNING", 600))  # 10分钟
    ALERT_ERROR_COUNT_WARNING: int = int(os.getenv("ALERT_ERROR_COUNT_WARNING", 50))  # 每小时50次

    # ===========================================
    # 新Agent 编排配置
    # ===========================================
    AGENT_ENGINE: str = os.getenv("AGENT_ENGINE", "new")  # new 或 legacy
    NEW_AGENT_MODE: str = os.getenv("NEW_AGENT_MODE", "local_stub")
    
    # ===========================================
    # 占位符分析配置
    # ===========================================
    USE_CELERY_PLACEHOLDER_ANALYSIS: bool = os.getenv("USE_CELERY_PLACEHOLDER_ANALYSIS", "false").lower() == "true"
    PLACEHOLDER_ANALYSIS_TIMEOUT: int = int(os.getenv("PLACEHOLDER_ANALYSIS_TIMEOUT", "300"))  # 5分钟  # local_stub 或 http
    NEW_AGENT_ENDPOINT: str = os.getenv("NEW_AGENT_ENDPOINT", "")  # HTTP模式下的服务地址
    NEW_AGENT_API_KEY: str = os.getenv("NEW_AGENT_API_KEY", "")
    NEW_AGENT_TIMEOUT: int = int(os.getenv("NEW_AGENT_TIMEOUT", 60))
    # 并发与重试
    NEW_AGENT_MAX_CONCURRENCY: int = int(os.getenv("NEW_AGENT_MAX_CONCURRENCY", 10))
    NEW_AGENT_MAX_RETRIES: int = int(os.getenv("NEW_AGENT_MAX_RETRIES", 3))
    NEW_AGENT_BACKOFF_BASE: float = float(os.getenv("NEW_AGENT_BACKOFF_BASE", 0.5))  # 秒
    NEW_AGENT_BACKOFF_CAP: float = float(os.getenv("NEW_AGENT_BACKOFF_CAP", 5.0))  # 秒
    
    # 管理员邮件配置
    ADMIN_EMAILS: List[str] = os.getenv("ADMIN_EMAILS", "admin@autoreportai.com").split(",")
    
    # AI服务配置
    DEFAULT_AI_MODEL: str = os.getenv("DEFAULT_AI_MODEL", "gpt-3.5-turbo")
    AI_REQUEST_TIMEOUT: int = int(os.getenv("AI_REQUEST_TIMEOUT", 300))  # 5分钟
    AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", 3))
    
    # ETL配置
    ETL_BATCH_SIZE: int = int(os.getenv("ETL_BATCH_SIZE", 10000))
    ETL_QUERY_TIMEOUT: int = int(os.getenv("ETL_QUERY_TIMEOUT", 900))  # 15分钟

    # 报告生成容错配置
    # 允许的失败占位符数量（不含跳过）上限，<= 此数仍生成文档
    REPORT_MAX_FAILED_PLACEHOLDERS_FOR_DOC: int = int(os.getenv("REPORT_MAX_FAILED_PLACEHOLDERS_FOR_DOC", 5))
    # 质量闸门是否允许放行（当存在质量问题时亦可生成文档）
    REPORT_ALLOW_QUALITY_ISSUES: bool = os.getenv("REPORT_ALLOW_QUALITY_ISSUES", "false").lower() == "true"
    
    # 缓存配置
    CACHE_DEFAULT_EXPIRE: int = int(os.getenv("CACHE_DEFAULT_EXPIRE", 3600))  # 1小时
    CACHE_AI_RESPONSE_EXPIRE: int = int(os.getenv("CACHE_AI_RESPONSE_EXPIRE", 3600))  # 1小时
    
    # 文件存储配置 - MinIO优先策略
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    REPORT_OUTPUT_DIR: str = os.getenv("REPORT_OUTPUT_DIR", "./reports")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", 100 * 1024 * 1024))  # 100MB
    
    # 存储策略配置 - 默认优先MinIO
    STORAGE_STRATEGY: str = os.getenv("STORAGE_STRATEGY", "minio_first")  # minio_first, local_first, minio_only, local_only
    
    # MinIO配置 - 智能环境检测
    @property
    def MINIO_ENDPOINT(self) -> str:
        """MinIO服务端点 - 根据环境自动选择"""
        env_endpoint = os.getenv("MINIO_ENDPOINT")
        if env_endpoint:
            return env_endpoint
        
        # 环境检测
        env = detect_environment()
        if env == "docker":
            return "minio:9000"  # Docker环境使用服务名
        else:
            return "localhost:9000"  # 本地环境
    
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "autoreport")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
    # 本地存储配置 - 仅作为MinIO的备选方案
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")
    FORCE_LOCAL_STORAGE: bool = os.getenv("FORCE_LOCAL_STORAGE", "false").lower() == "true"
    
    # MinIO优先配置 - 默认启用
    PREFER_MINIO_STORAGE: bool = os.getenv("PREFER_MINIO_STORAGE", "true").lower() == "true"
    
    # API基础URL配置
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # 部署环境配置
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # API限流配置
    API_RATE_LIMIT: str = os.getenv("API_RATE_LIMIT", "100/minute")
    
    # CORS配置 - 使用ALLOWED_ORIGINS以保持与部署脚本一致
    CORS_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://0.0.0.0:3000"))
    CORS_ORIGIN_REGEX: str = os.getenv("CORS_ORIGIN_REGEX", "")
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    CORS_ALLOW_METHODS: List[str] = os.getenv("ALLOWED_METHODS", os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS,PATCH")).split(",")
    CORS_ALLOW_HEADERS: List[str] = os.getenv("ALLOWED_HEADERS", os.getenv("CORS_ALLOW_HEADERS", "*")).split(",")
    
    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的来源列表"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        
        origins = []
        if self.CORS_ORIGINS:
            origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        
        # 默认允许的来源
        if not origins:
            origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000"]
        
        return origins
    
    # 健康检查配置
    HEALTH_CHECK_ENABLED: bool = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
    
    # 用户初始化配置
    FIRST_SUPERUSER: str = os.getenv("FIRST_SUPERUSER", "admin")
    FIRST_SUPERUSER_EMAIL: str = os.getenv("FIRST_SUPERUSER_EMAIL", "admin@autoreportai.com")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "password")
    
    # 系统用户UUID配置 - 用于系统级别的任务执行
    SYSTEM_USER_ID: str = os.getenv("SYSTEM_USER_ID", "94ba5da3-ee9d-40fe-b34d-ea3a90553f54")
    
    # AI Provider初始化配置
    DEFAULT_AI_PROVIDER_NAME: str = os.getenv("DEFAULT_AI_PROVIDER_NAME", "OpenAI")
    DEFAULT_AI_PROVIDER_API_BASE: str = os.getenv("DEFAULT_AI_PROVIDER_API_BASE", "https://api.openai.com/v1")
    DEFAULT_AI_PROVIDER_API_KEY: str = os.getenv("DEFAULT_AI_PROVIDER_API_KEY", "sk-your-api-key")
    DEFAULT_AI_PROVIDER_MODELS: List[str] = os.getenv("DEFAULT_AI_PROVIDER_MODELS", "gpt-3.5-turbo,gpt-4").split(",")

    # OpenAI 配置（兼容性）
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


settings = Settings()

def get_cors_origins() -> List[str]:
    """获取CORS允许的来源列表（全局函数）"""
    return settings.get_cors_origins()
