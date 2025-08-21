"""
Placeholder System Constants

占位符系统的常量定义
"""

from enum import Enum
from typing import List, Dict, Any

# 缓存相关常量
DEFAULT_CACHE_TTL = 3600  # 1小时
CACHE_KEY_PREFIX = "placeholder"
CACHE_VERSION = "v1"

# 重试和超时常量
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30  # 秒
AGENT_ANALYSIS_TIMEOUT = 60  # Agent分析超时
SQL_EXECUTION_TIMEOUT = 30  # SQL执行超时

# 占位符类型
class PlaceholderType(str, Enum):
    """占位符类型枚举"""
    METRIC = "metric"           # 数值指标
    TEXT = "text"               # 文本内容  
    DATE = "date"               # 日期时间
    LIST = "list"               # 列表数据
    TABLE = "table"             # 表格数据
    CHART = "chart"             # 图表数据
    CALCULATION = "calculation" # 计算结果

# 支持的占位符类型列表
SUPPORTED_PLACEHOLDER_TYPES: List[str] = [e.value for e in PlaceholderType]

# 内容类型
class ContentType(str, Enum):
    """内容类型枚举"""
    NUMBER = "number"
    PERCENTAGE = "percentage"
    CURRENCY = "currency"
    TEXT = "text"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    HTML = "html"

# 分析结果置信度阈值
CONFIDENCE_THRESHOLDS = {
    "high": 0.8,
    "medium": 0.6,
    "low": 0.4
}

# Agent分析相关常量
AGENT_ANALYSIS_CONFIG = {
    "max_context_tokens": 32000,
    "temperature": 0.1,
    "max_retries": 3,
    "enable_compression": True,
    "compression_threshold": 0.8
}

# 规则模板配置
RULE_TEMPLATE_CONFIG = {
    "enable_intelligent_fallback": True,
    "enable_keyword_matching": True,
    "enable_template_generation": True,
    "max_template_variations": 5
}

# SQL生成配置
SQL_GENERATION_CONFIG = {
    "max_sql_length": 10000,
    "enable_query_optimization": True,
    "enable_schema_validation": True,
    "default_limit": 1000
}

# 性能监控配置
PERFORMANCE_CONFIG = {
    "enable_metrics": True,
    "log_slow_queries": True,
    "slow_query_threshold_ms": 5000,
    "enable_cache_hit_logging": True
}

# 错误处理配置
ERROR_HANDLING_CONFIG = {
    "max_error_context_length": 1000,
    "enable_error_recovery": True,
    "enable_fallback_on_error": True,
    "log_stack_traces": True
}

# 数据源配置
DATASOURCE_CONFIG = {
    "connection_timeout": 30,
    "query_timeout": 60,
    "max_connections": 10,
    "connection_retry_attempts": 3
}

# 默认占位符配置
DEFAULT_PLACEHOLDER_CONFIG: Dict[str, Any] = {
    "cache_enabled": True,
    "cache_ttl": DEFAULT_CACHE_TTL,
    "enable_agent_analysis": True,
    "enable_rule_fallback": True,
    "max_execution_time": DEFAULT_TIMEOUT,
    "retry_attempts": MAX_RETRY_ATTEMPTS
}