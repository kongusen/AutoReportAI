from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .cache_interfaces import CacheInterface


class MemoryCache(CacheInterface):
    """简单的进程内内存缓存实现（线程不安全，适用于轻量开发环境）"""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expire_at: Dict[str, float] = {}

    async def get(self, key: str) -> Optional[Any]:
        now = time.time()
        exp = self._expire_at.get(key)
        if exp is not None and exp < now:
            self._store.pop(key, None)
            self._expire_at.pop(key, None)
            return None
        return self._store.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._store[key] = value
        self._expire_at[key] = time.time() + max(0, ttl_seconds)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._expire_at.pop(key, None)


