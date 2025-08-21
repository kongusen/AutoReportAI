"""
抽象接口：占位符提取与文档处理

用于在 `template` 与 `placeholder`、`report_generation` 之间建立中间抽象层，
避免直接模块间依赖以消除循环依赖风险。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DocumentPipelineInterface(ABC):
    """文档处理流水线接口抽象"""

    @abstractmethod
    async def process_document(self, content: str) -> str:
        """处理文档内容并返回结果（具体实现可自定义）"""
        raise NotImplementedError


class PlaceholderExtractorInterface(ABC):
    """占位符提取器接口抽象"""

    @abstractmethod
    async def extract_placeholders(self, template_content: str) -> List[Dict[str, Any]]:
        """从模板内容中提取占位符（不涉及持久化）"""
        raise NotImplementedError


