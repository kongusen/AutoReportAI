"""
AI Content Port (Domain Port)

Provides natural language generation and interpretation capabilities for
reporting and placeholder content without coupling Domain to Infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AiContentPort(ABC):
    @abstractmethod
    async def generate_placeholder_content(
        self,
        *,
        placeholder_name: str,
        placeholder_type: str,
        description: str,
        data_source_id: str,
        task_id: Optional[str] = None,
        template_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate report content for a placeholder."""
        pass

    @abstractmethod
    async def interpret_placeholder(
        self,
        *,
        placeholder_name: str,
        placeholder_type: str,
        description: str,
        analysis_results: Dict[str, Any],
        target_audience: str = "business",
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a short interpretation/explanation for a placeholder."""
        pass

