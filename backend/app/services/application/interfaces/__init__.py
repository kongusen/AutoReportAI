"""
服务层接口包

包含解耦跨模块依赖所需的抽象接口定义。
"""

from .extraction_interfaces import (
    DocumentPipelineInterface,
    PlaceholderExtractorInterface,
)

__all__ = [
    "DocumentPipelineInterface",
    "PlaceholderExtractorInterface",
]


