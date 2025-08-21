"""
Legacy AI Agents package

This package currently exposes only the stable `MultiDatabaseAgent` to avoid
importing incomplete legacy modules.
"""

__version__ = "2.0.0"

from .multi_database_agent import MultiDatabaseAgent

__all__ = [
    "MultiDatabaseAgent",
]