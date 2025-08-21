"""
Placeholder System Exceptions

统一的占位符系统异常定义
"""


class PlaceholderError(Exception):
    """占位符系统基础异常"""
    
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "PLACEHOLDER_ERROR"
        self.context = context or {}


class PlaceholderExtractionError(PlaceholderError):
    """占位符提取异常"""
    
    def __init__(self, message: str, template_id: str = None, **kwargs):
        super().__init__(message, "EXTRACTION_ERROR", **kwargs)
        self.template_id = template_id


class PlaceholderAnalysisError(PlaceholderError):
    """占位符分析异常"""
    
    def __init__(self, message: str, placeholder_id: str = None, analysis_type: str = None, **kwargs):
        super().__init__(message, "ANALYSIS_ERROR", **kwargs)
        self.placeholder_id = placeholder_id
        self.analysis_type = analysis_type


class PlaceholderExecutionError(PlaceholderError):
    """占位符执行异常"""
    
    def __init__(self, message: str, placeholder_id: str = None, sql: str = None, **kwargs):
        super().__init__(message, "EXECUTION_ERROR", **kwargs)
        self.placeholder_id = placeholder_id
        self.sql = sql


class PlaceholderCacheError(PlaceholderError):
    """占位符缓存异常"""
    
    def __init__(self, message: str, cache_key: str = None, **kwargs):
        super().__init__(message, "CACHE_ERROR", **kwargs)
        self.cache_key = cache_key


class PlaceholderConfigError(PlaceholderError):
    """占位符配置异常"""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        super().__init__(message, "CONFIG_ERROR", **kwargs)
        self.config_key = config_key


class PlaceholderValidationError(PlaceholderError):
    """占位符验证异常"""
    
    def __init__(self, message: str, validation_type: str = None, **kwargs):
        super().__init__(message, "VALIDATION_ERROR", **kwargs)
        self.validation_type = validation_type