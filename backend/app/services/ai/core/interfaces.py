from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod


@dataclass
class AIResponse:
    success: bool
    text: str
    raw: Optional[Any] = None
    usage: Optional[Dict[str, Any]] = None


class AIServiceInterface(ABC):
    @abstractmethod
    async def complete(self, prompt: str, *, model: Optional[str] = None, **kwargs) -> AIResponse:
        raise NotImplementedError


