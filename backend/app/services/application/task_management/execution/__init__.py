"""
Task Execution Components

任务执行组件，包括：
- 智能报告生成流水线
- Agent执行器
- 回退处理机制
"""

# Legacy pipeline modules removed in DAG architecture
# from .unified_pipeline import (
#     unified_report_generation_pipeline,  # Replaced by DAG agents
#     PipelineMode
# )
# from .fallback import FallbackHandler  # Replaced by DAG agents

# All execution components disabled in pure DAG architecture
# from .enhanced_two_phase_pipeline import EnhancedTwoPhasePipeline, create_enhanced_pipeline

__all__ = [
    # All components disabled in pure DAG architecture
    # "unified_report_generation_pipeline",  # Replaced by DAG agents
    # "PipelineMode",                       # Replaced by DAG agents
    # "AgentExecutor",                      # Not available
    # "FallbackHandler",                    # Replaced by DAG agents
    # "EnhancedTwoPhasePipeline",           # Disabled - missing dependencies
    # "create_enhanced_pipeline",           # Disabled - missing dependencies
]
