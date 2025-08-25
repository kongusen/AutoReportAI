"""
占位符处理系统

基于清晰分层架构的统一占位符处理系统
包含：提取层、配置层、分析层、执行层、缓存层、编排层
"""

# 核心功能
from .core import (
    # 数据模型
    PlaceholderRequest,
    PlaceholderResponse,
    CacheKey,
    CacheEntry,
    AgentAnalysisResult,
    AgentExecutionResult,
    RuleGenerationResult,
    ExecutionResult,
    SchemaInfo,
    
    # 枚举
    ProcessingStage,
    ResultSource,
    
    # 接口
    CacheServiceInterface,
    AgentAnalysisServiceInterface,
    TemplateRuleServiceInterface,
    DataExecutionServiceInterface,
    
    # 异常
    PlaceholderError,
    PlaceholderExtractionError,
    PlaceholderAnalysisError,
    PlaceholderExecutionError,
    PlaceholderCacheError,
    PlaceholderConfigError,
    PlaceholderValidationError,
    
    # 常量
    DEFAULT_CACHE_TTL,
    MAX_RETRY_ATTEMPTS,
    DEFAULT_TIMEOUT,
    SUPPORTED_PLACEHOLDER_TYPES,
)

# 提取层
from .extraction import (
    PlaceholderExtractor,
    PlaceholderParser,
)

# 配置层
from .config import (
    PlaceholderConfigService,
    PlaceholderConfigValidator,
)

# 分析层（使用新的Agent系统）
# AgentAnalysisService 已迁移到 app.services.ai.agents.placeholder_sql_agent
from .rule_service import TemplateRuleService

# 执行层
from .execution_service import DataExecutionService

# 缓存层
from .cache_service import CacheService

# 编排层
from .router import PlaceholderRouter, PlaceholderBatchRouter

# 容器和工厂
from .container import (
    PlaceholderServiceContainer,
    PlaceholderServiceFactory,
    GlobalContainerManager,
    global_container_manager
)

# 版本信息
__version__ = "1.0.0"
__author__ = "AutoReportAI Team"

# 导出的主要接口
__all__ = [
    # 核心模型
    "PlaceholderRequest",
    "PlaceholderResponse",
    "ResultSource",
    "ProcessingStage",
    
    # 主要服务（统一接口）
    "PlaceholderRouter",
    "PlaceholderBatchRouter",
    "PlaceholderServiceContainer",
    "PlaceholderServiceFactory",
    
    # 提取和配置层（新增）
    "PlaceholderExtractor",
    "PlaceholderParser",
    "PlaceholderConfigService",
    "PlaceholderConfigValidator",
    
    # 分析和执行层
    # "AgentAnalysisService",  # 已迁移到新的Agent系统
    "TemplateRuleService",
    "DataExecutionService",
    
    # 缓存层
    "CacheService",
    
    # 异常类
    "PlaceholderError",
    "PlaceholderExtractionError",
    "PlaceholderAnalysisError",
    "PlaceholderExecutionError",
    "PlaceholderCacheError",
    "PlaceholderConfigError",
    "PlaceholderValidationError",
    
    # 常量
    "DEFAULT_CACHE_TTL",
    "MAX_RETRY_ATTEMPTS",
    "DEFAULT_TIMEOUT",
    "SUPPORTED_PLACEHOLDER_TYPES",
    
    # 工具类
    "global_container_manager",
    
    # 工厂函数
    "create_placeholder_service",
    "create_placeholder_router", 
    "create_batch_router",
    "create_placeholder_extractor",
    "create_placeholder_config_service",
]


def create_placeholder_service(db_session, user_id=None):
    """
    快速创建占位符服务
    
    Args:
        db_session: 数据库会话
        user_id: 用户ID，可选
    
    Returns:
        PlaceholderServiceContainer: 服务容器实例
    
    Example:
        >>> from app.services.domain.placeholder import create_placeholder_service
        >>> service = create_placeholder_service(db, user_id="123")
        >>> router = service.router
        >>> result = await router.process_placeholder(request)
    """
    return PlaceholderServiceFactory.create_container(db_session, user_id)


def create_placeholder_router(db_session, user_id=None):
    """
    快速创建占位符路由器
    
    Args:
        db_session: 数据库会话
        user_id: 用户ID，可选
    
    Returns:
        PlaceholderRouter: 路由器实例
    
    Example:
        >>> from app.services.domain.placeholder import create_placeholder_router
        >>> router = create_placeholder_router(db, user_id="123")
        >>> result = await router.process_placeholder(request)
    """
    return PlaceholderServiceFactory.create_router_only(db_session, user_id)


def create_batch_router(db_session, user_id=None):
    """
    快速创建批量占位符路由器
    
    Args:
        db_session: 数据库会话
        user_id: 用户ID，可选
    
    Returns:
        PlaceholderBatchRouter: 批量路由器实例
    
    Example:
        >>> from app.services.domain.placeholder import create_batch_router
        >>> batch_router = create_batch_router(db, user_id="123")
        >>> result = await batch_router.process_template_placeholders(
        ...     template_id, data_source_id, user_id
        ... )
    """
    return PlaceholderServiceFactory.create_batch_router_only(db_session, user_id)


def create_placeholder_extractor(db_session, template_parser=None):
    """
    快速创建占位符提取器
    
    Args:
        db_session: 数据库会话
    
    Returns:
        PlaceholderExtractor: 提取器实例
    
    Example:
        >>> from app.services.domain.placeholder import create_placeholder_extractor
        >>> extractor = create_placeholder_extractor(db)
        >>> result = await extractor.extract_and_store_placeholders(template_id, content)
    """
    return PlaceholderExtractor(db_session, template_parser=template_parser)


def create_placeholder_config_service(db_session):
    """
    快速创建占位符配置服务
    
    Args:
        db_session: 数据库会话
    
    Returns:
        PlaceholderConfigService: 配置服务实例
    
    Example:
        >>> from app.services.domain.placeholder import create_placeholder_config_service
        >>> config_service = create_placeholder_config_service(db)
        >>> configs = await config_service.get_placeholder_configs(template_id)
    """
    return PlaceholderConfigService(db_session)


# 系统信息
def get_system_info():
    """获取占位符处理系统信息"""
    return {
        "name": "PlaceholderProcessingSystem",
        "version": __version__,
        "author": __author__,
        "architecture": "layered",
        "layers": [
            "router_layer",      # 路由层
            "cache_layer",       # 缓存层  
            "agent_layer",       # Agent分析层
            "rule_layer",        # 模板规则层
            "execution_layer"    # 数据执行层
        ],
        "features": [
            "ai_driven_analysis",      # AI驱动的分析
            "intelligent_caching",     # 智能缓存
            "rule_based_fallback",     # 基于规则的fallback
            "batch_processing",        # 批量处理
            "error_recovery",          # 错误恢复
            "performance_monitoring"   # 性能监控
        ],
        "supported_data_sources": [
            "doris",
            # 其他数据源可扩展
        ]
    }