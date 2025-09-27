"""
AI SQL Repair Port (Domain Port)

Allows Domain to request SQL repair (e.g., after validation failure) without
importing Infrastructure. Implementations live in Infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AiSqlRepairPort(ABC):
    @abstractmethod
    async def repair_sql(
        self,
        *,
        user_id: str,
        placeholder_name: str,
        placeholder_text: str,
        template_id: str,
        original_sql: str,
        error_message: str,
        data_source_info: Dict[str, Any],
        time_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Returns repaired SQL or None if not repairable."""
        pass

