"""
Placeholder Extraction Module

占位符提取模块，负责从模板中识别和提取占位符
"""

from .extractor import PlaceholderExtractor
from .parser import PlaceholderParser

__all__ = [
    'PlaceholderExtractor',
    'PlaceholderParser',
]