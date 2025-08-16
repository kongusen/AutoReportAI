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
from .table_schema import TableSchema, ColumnSchema, TableRelationship, ColumnType
from .task import Task, TaskExecution, TaskStatus, ProcessingMode, AgentWorkflowType
from .template import Template
from .user import User
from .user_profile import UserProfile

# Task模型现在包含Agent编排支持，无需独立的Agent模型

# 确保导入顺序正确，避免外键引用问题
__all__ = [
    # 原有模型
    "User",
    "UserProfile",
    "Template",
    "DataSource",
    "ETLJob",
    "ReportHistory",
    "AIProvider",
    "AnalyticsData",
    "PlaceholderMapping",
    # 表结构模型
    "TableSchema",
    "ColumnSchema", 
    "TableRelationship",
    "ColumnType",
    # 任务模型
    "Task",
    "TaskExecution", 
    "TaskStatus",
    "ProcessingMode",
    "AgentWorkflowType",
    # 学习模型
    "PlaceholderProcessingHistory",
    "ErrorLog",
    "UserFeedback",
    "LearningRule",
    "KnowledgeBase",
    "LLMCallLog",
]