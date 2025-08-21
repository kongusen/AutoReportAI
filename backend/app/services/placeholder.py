"""
Backward Compatibility Module for Placeholder Services

This module provides backward compatibility for legacy imports from app.services.placeholder
All functionality has been moved to app.services.domain.placeholder
"""

# Re-export all available items from the new location for backward compatibility
from .domain.placeholder import (
    # Core factory functions
    create_placeholder_service,
    create_placeholder_extractor,
    create_placeholder_router,
    create_batch_router,
    create_placeholder_config_service,
    
    # Core models
    PlaceholderRequest,
    PlaceholderResponse,
    ResultSource,
    ProcessingStage,
    
    # Main services
    PlaceholderRouter,
    PlaceholderBatchRouter,
    PlaceholderServiceContainer,
    PlaceholderServiceFactory,
    
    # Extraction and config layer
    PlaceholderExtractor,
    PlaceholderParser,
    PlaceholderConfigService,
    PlaceholderConfigValidator,
    
    # Analysis and execution layer
    AgentAnalysisService,
    TemplateRuleService,
    DataExecutionService,
    
    # Cache layer
    CacheService,
    CacheMetrics,
    
    # Exception classes
    PlaceholderError,
    PlaceholderExtractionError,
    PlaceholderAnalysisError,
    PlaceholderExecutionError,
    PlaceholderCacheError,
    PlaceholderConfigError,
    PlaceholderValidationError,
    
    # Constants
    DEFAULT_CACHE_TTL,
    MAX_RETRY_ATTEMPTS,
    DEFAULT_TIMEOUT,
    SUPPORTED_PLACEHOLDER_TYPES,
    
    # Utilities
    global_container_manager,
    
    # All exports
    __all__ as domain_all
)

# Maintain the same __all__ interface
__all__ = domain_all

# Add deprecation warning (optional - can be uncommented if needed)
# import warnings
# warnings.warn(
#     "Importing from app.services.placeholder is deprecated. "
#     "Use app.services.domain.placeholder instead.",
#     DeprecationWarning,
#     stacklevel=2
# )