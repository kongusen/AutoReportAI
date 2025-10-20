"""
SQL generation subpackage.

This module exposes the high-level coordinator used by the PTAV pipeline
to orchestrate multi-placeholder SQL generation with dependency resolution,
structured LLM interaction, validation, and fallback strategies.

Components:
- SQLGenerationCoordinator: SQL-First快速生成（1-2轮）
- HybridSQLGenerator: 混合策略（结合SQL-First和PTAV）
"""

from .coordinator import SQLGenerationCoordinator, SQLGenerationConfig
from .hybrid_generator import HybridSQLGenerator, generate_sql_with_hybrid_strategy

__all__ = [
    "SQLGenerationCoordinator",
    "SQLGenerationConfig",
    "HybridSQLGenerator",
    "generate_sql_with_hybrid_strategy",
]
