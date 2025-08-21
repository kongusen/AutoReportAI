from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheInterface(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError


