"""
Agent核心模块

包含Agent系统的核心组件：
- AI服务管理
- 数据库会话管理
- 性能监控
- 缓存管理
- 健康检查
- 响应解析和错误处理
"""

from .ai_service import (
    AIServiceInterface,
    UnifiedAIService,
    get_ai_service,
    get_ai_service_pool,
    clear_ai_service_cache
)

from .session_manager import (
    DatabaseSessionManager,
    get_session_manager,
    managed_session,
    ensure_session,
    SessionContextManager
)

from .performance_monitor import (
    PerformanceMonitor,
    get_performance_monitor,
    start_performance_monitoring,
    stop_performance_monitoring,
    performance_context,
    optimize_system_performance
)

from .cache_manager import (
    CacheManager,
    SmartCache,
    get_cache_manager,
    cache_query_result,
    get_cached_query_result,
    cache_ai_response,
    get_cached_ai_response
)

from .health_monitor import (
    HealthMonitor,
    HealthStatus,
    get_health_monitor,
    perform_system_health_check
)

from .response_parser import (
    ResponseParserInterface,
    JSONResponseParser,
    AnalysisResponseParser,
    ResponseParserFactory,
    get_analysis_parser
)

from .error_handler import (
    ErrorSeverity,
    ErrorType,
    ErrorInfo,
    ErrorHandler,
    AgentErrorHandler,
    get_error_handler
)

__all__ = [
    # AI服务
    "AIServiceInterface",
    "UnifiedAIService",
    "get_ai_service",
    "get_ai_service_pool",
    "clear_ai_service_cache",
    
    # 数据库会话管理
    "DatabaseSessionManager",
    "get_session_manager",
    "managed_session",
    "ensure_session",
    "SessionContextManager",
    
    # 性能监控
    "PerformanceMonitor",
    "get_performance_monitor",
    "start_performance_monitoring",
    "stop_performance_monitoring",
    "performance_context",
    "optimize_system_performance",
    
    # 缓存管理
    "CacheManager",
    "SmartCache",
    "get_cache_manager",
    "cache_query_result",
    "get_cached_query_result",
    "cache_ai_response",
    "get_cached_ai_response",
    
    # 健康检查
    "HealthMonitor",
    "HealthStatus",
    "get_health_monitor",
    "perform_system_health_check",
    
    # 响应解析
    "ResponseParserInterface",
    "JSONResponseParser",
    "AnalysisResponseParser",
    "ResponseParserFactory",
    "get_analysis_parser",
    
    # 错误处理
    "ErrorSeverity",
    "ErrorType",
    "ErrorInfo",
    "ErrorHandler",
    "AgentErrorHandler",
    "get_error_handler"
]
