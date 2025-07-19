"""
intelligent_placeholder 服务模块

提供 intelligent_placeholder 相关的业务逻辑处理
"""

# 模块版本
__version__ = "1.0.0"

# 导入核心组件
from .processor import PlaceholderProcessor, PlaceholderMatch, PlaceholderType, ProcessingError
from .adapter import (
    IntelligentPlaceholderProcessor, 
    ProcessingResult, 
    PlaceholderUnderstanding, 
    FieldSuggestion
)
from .matcher import IntelligentFieldMatcher, FieldMatchingResult, SimilarityScore

# 模块导出
__all__ = [
    "PlaceholderProcessor",
    "PlaceholderMatch", 
    "PlaceholderType",
    "ProcessingError",
    "IntelligentPlaceholderProcessor",
    "ProcessingResult",
    "PlaceholderUnderstanding",
    "FieldSuggestion",
    "IntelligentFieldMatcher",
    "FieldMatchingResult",
    "SimilarityScore"
]