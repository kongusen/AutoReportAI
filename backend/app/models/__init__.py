from .ai_provider import AIProvider
from .analytics_data import AnalyticsData
from .data_source import DataSource
from .etl_job import ETLJob
from .learning_data import (
    ErrorLog,
    KnowledgeBase,
    LearningRule,
    LLMCallLog,
    PlaceholderProcessingHistory,
    UserFeedback,
)
from .placeholder_mapping import PlaceholderMapping
from .report_history import ReportHistory
from .task import Task
from .template import Template
from .user import User
from .user_profile import UserProfile

# 确保导入顺序正确，避免外键引用问题
__all__ = [
    "User",
    "UserProfile",
    "Template",
    "DataSource",
    "ETLJob",
    "ReportHistory",
    "AIProvider",
    "AnalyticsData",
    "PlaceholderMapping",
    "Task",
    "PlaceholderProcessingHistory",
    "ErrorLog",
    "UserFeedback",
    "LearningRule",
    "KnowledgeBase",
    "LLMCallLog",
]
