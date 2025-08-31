"""
Task Management Service Module

提供完整的任务管理功能，包括：
- 任务调度和执行
- 进度管理和状态跟踪
- Agent执行和回退机制
- 通知和文件处理
"""

# 模块版本
__version__ = "1.0.0"

# 导入核心组件
from .core.worker import celery_app, TaskStatus
from .core.scheduler import TaskScheduler
from .core.progress_manager import TaskProgressManager, EnhancedTaskProgressManager

# 导入执行组件 - Legacy modules replaced by DAG agents
# from .execution.unified_pipeline import (
#     unified_report_generation_pipeline  # Replaced by DAG agents
# )
# from .execution.fallback import FallbackHandler  # Replaced by DAG agents

# from .execution import EnhancedTwoPhasePipeline, create_enhanced_pipeline  # Disabled - too many missing dependencies

# 导入管理组件
from .management.task_manager import TaskManager
from .management.status_tracker import StatusTracker

# 导入工具组件
from .utils.notifications import NotificationUtils
from .utils.file_handlers import FileHandlers

# 模块导出
__all__ = [
    # 核心组件
    "celery_app",
    "TaskStatus",
    "TaskScheduler",
    "TaskProgressManager",
    "EnhancedTaskProgressManager",
    
    # 执行组件 - Legacy components replaced by DAG agents
    # "unified_report_generation_pipeline",  # Replaced by DAG agents
    # "AgentExecutor",                       # Not available
    # "FallbackHandler",                     # Replaced by DAG agents
    "EnhancedTwoPhasePipeline",
    "create_enhanced_pipeline",
    
    # 管理组件
    "TaskManager",
    "StatusTracker",
    
    # 工具组件
    "NotificationUtils",
    "FileHandlers",
]
