"""
AI Agent System for AutoReport

This module provides an extensible agent-based architecture for processing
intelligent placeholders, replacing the legacy intelligent_placeholder system.

Key Features:
- Modular agent-based design
- Pluggable agent types
- Unified processing pipeline
- Enhanced error handling and recovery
- Performance monitoring and metrics

Agents:
- BaseAgent: Core agent interface
- DataQueryAgent: Handles data retrieval and ETL operations  
- ContentGenerationAgent: Generates content from data
- AnalysisAgent: Performs statistical analysis
- VisualizationAgent: Creates charts and visualizations
"""

__version__ = "1.0.0"

from .base import BaseAgent, AgentResult, AgentConfig, AgentError
from .data_query_agent import DataQueryAgent
from .content_generation_agent import ContentGenerationAgent
from .analysis_agent import AnalysisAgent
from .visualization_agent import VisualizationAgent
from .orchestrator import AgentOrchestrator

__all__ = [
    "BaseAgent",
    "AgentResult", 
    "AgentConfig",
    "AgentError",
    "DataQueryAgent",
    "ContentGenerationAgent",
    "AnalysisAgent", 
    "VisualizationAgent",
    "AgentOrchestrator",
]