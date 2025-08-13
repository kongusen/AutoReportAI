import logging
import sys
import time
import uuid
from typing import Dict, Any, Optional
from contextvars import ContextVar

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

import logging.config
import os
from pathlib import Path
from app.core.config import settings

# Context variable for request tracking
request_id_context: ContextVar[str] = ContextVar('request_id', default='')
request_start_time_context: ContextVar[float] = ContextVar('request_start_time', default=0.0)

# Module-specific logger configurations
MODULE_LOGGERS = {
    'intelligent_placeholder': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
        'propagate': False
    },
    'report_generation': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
        'propagate': False
    },
    'data_processing': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
        'propagate': False
    },
    'ai_integration': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
        'propagate': False
    },
    'notification': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
        'propagate': False
    },
    'api': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
        'propagate': False
    },
    'performance': {
        'level': 'INFO',
        'handlers': ['console', 'performance_file'],
        'propagate': False
    }
}


def add_request_context(logger, method_name, event_dict):
    """Add request context to log entries."""
    request_id = request_id_context.get('')
    if request_id:
        event_dict['request_id'] = request_id
    
    start_time = request_start_time_context.get(0.0)
    if start_time > 0:
        event_dict['request_duration'] = time.time() - start_time
    
    return event_dict


def add_performance_metrics(logger, method_name, event_dict):
    """Add performance metrics to log entries."""
    if 'duration' in event_dict or 'execution_time' in event_dict:
        event_dict['metric_type'] = 'performance'
    return event_dict


def log_startup_config():
    """记录启动配置到日志"""
    logger = logging.getLogger("startup")
    
    logger.info("=" * 80)
    logger.info("🚀 AutoReportAI 系统启动配置")
    logger.info("=" * 80)
    
    # 记录基础配置
    logger.info(f"项目名称: {settings.PROJECT_NAME}")
    logger.info(f"API版本: {settings.API_V1_STR}")
    logger.info(f"运行环境: {settings.ENVIRONMENT}")
    logger.info(f"调试模式: {settings.DEBUG}")
    
    # 记录数据库配置
    logger.info(f"数据库主机: {settings.db_host}")
    logger.info(f"数据库端口: {settings.db_port}")
    logger.info(f"数据库名称: {settings.db_name}")
    logger.info(f"数据库用户: {settings.db_user}")
    logger.info(f"数据库密码: {'*' * len(settings.db_password) if settings.db_password else 'None'}")
    
    # 记录安全配置
    logger.info(f"密钥长度: {len(settings.SECRET_KEY)} 字符")
    logger.info(f"加密密钥: {settings.ENCRYPTION_KEY[:4]}****{settings.ENCRYPTION_KEY[-4:] if len(settings.ENCRYPTION_KEY) > 8 else '****'}")
    logger.info(f"Token过期时间: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} 分钟")
    
    # 记录网络配置
    logger.info(f"Redis URL: {settings.REDIS_URL}")
    logger.info(f"API基础URL: {settings.API_BASE_URL}")
    logger.info(f"WebSocket端口: {settings.WS_PORT}")
    
    logger.info("=" * 80)
    logger.info("✅ 启动配置记录完成")
    logger.info("=" * 80)


def setup_logging(log_level: str = "INFO", enable_file_logging: bool = True):
    """
    Configures structured logging for the application with modular support.
    
    Args:
        log_level: Default log level for the application
        enable_file_logging: Whether to enable file logging
    """
    # Configure basic logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stdout,
    )

    # Setup file handlers if enabled
    handlers = {}
    if enable_file_logging:
        # Main application log file
        file_handler = logging.FileHandler('logs/app.log')
        file_handler.setLevel(logging.INFO)
        handlers['file'] = file_handler
        
        # Performance-specific log file
        perf_handler = logging.FileHandler('logs/performance.log')
        perf_handler.setLevel(logging.INFO)
        handlers['performance_file'] = perf_handler
        
        # Create logs directory if it doesn't exist
        import os
        os.makedirs('logs', exist_ok=True)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    handlers['console'] = console_handler

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            add_request_context,
            add_performance_metrics,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure module-specific loggers
    setup_module_loggers(handlers)


def setup_module_loggers(handlers: Dict[str, logging.Handler]):
    """Setup dedicated loggers for each service module."""
    for module_name, config in MODULE_LOGGERS.items():
        logger = logging.getLogger(f"app.services.{module_name}")
        logger.setLevel(getattr(logging, config['level'].upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Add configured handlers
        for handler_name in config['handlers']:
            if handler_name in handlers:
                logger.addHandler(handlers[handler_name])
        
        logger.propagate = config['propagate']


def get_module_logger(module_name: str) -> structlog.BoundLogger:
    """
    Get a structured logger for a specific module.
    
    Args:
        module_name: Name of the module (e.g., 'intelligent_placeholder', 'report_generation')
    
    Returns:
        Configured structlog logger for the module
    """
    logger_name = f"app.services.{module_name}"
    return structlog.get_logger(logger_name)


def get_performance_logger() -> structlog.BoundLogger:
    """Get a logger specifically for performance metrics."""
    return structlog.get_logger("app.services.performance")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracking and performance monitoring."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request_id_context.set(request_id)
        
        # Record start time
        start_time = time.time()
        request_start_time_context.set(start_time)
        
        # Get logger
        logger = structlog.get_logger("app.api")
        
        # Log request start
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=request_id
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request completion
            logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration=duration,
                request_id=request_id
            )
            
            # Log performance metrics for slow requests
            if duration > 1.0:  # Log requests taking more than 1 second
                perf_logger = get_performance_logger()
                perf_logger.warning(
                    "Slow request detected",
                    method=request.method,
                    url=str(request.url),
                    duration=duration,
                    status_code=response.status_code,
                    request_id=request_id
                )
            
            return response
            
        except Exception as exc:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request error
            logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                duration=duration,
                error=str(exc),
                error_type=type(exc).__name__,
                request_id=request_id,
                exc_info=True
            )
            raise
        finally:
            # Clear context
            request_id_context.set('')
            request_start_time_context.set(0.0)
