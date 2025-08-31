"""
占位符存储模块

提供占位符分析结果的持久化存储功能
"""

from .result_storage import ResultStorage
from .version_storage import VersionStorage
from .metadata_storage import MetadataStorage
from .storage_manager import StorageManager

__all__ = [
    "ResultStorage",
    "VersionStorage",
    "MetadataStorage",
    "StorageManager"
]