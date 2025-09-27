"""
Schema Discovery Port (Domain Port)

Provides schema information for a data source.
Implementation belongs to Infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SchemaInfo:
    tables: List[str] = field(default_factory=list)
    columns: Dict[str, List[str]] = field(default_factory=dict)


class SchemaDiscoveryPort(ABC):
    @abstractmethod
    async def introspect(self, data_source_id: str) -> SchemaInfo:
        pass

