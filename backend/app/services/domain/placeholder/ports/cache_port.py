"""
Cache Port (Domain Port)

Domain-specified cache keys and invalidation rules, Infra provides storage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class CachePort(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        pass

    @abstractmethod
    async def evict(self, key: str) -> None:
        pass

