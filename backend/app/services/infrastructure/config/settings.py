from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ServiceLayerSettings:
    AI_SERVICE_TIMEOUT: int = 30
    CACHE_DEFAULT_TTL: int = 3600
    MAX_RETRY_ATTEMPTS: int = 3


