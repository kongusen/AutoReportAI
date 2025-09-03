from .analytics_data import AnalyticsData
from .data_source import DataSource
from .etl_job import ETLJob
from .llm_server import LLMServer, LLMModel, ModelType
from .user_llm_preference import UserLLMPreference, UserLLMUsageQuota
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
from .template_placeholder import TemplatePlaceholder, PlaceholderValue, TemplateExecutionHistory
from .placeholder_chart_cache import PlaceholderChartCache
from .user import User
from .user_profile import UserProfile
from .notification import Notification, NotificationPreference, NotificationStatus, NotificationType, NotificationPriority

# Task模型现在包含Agent编排支持，无需独立的Agent模型

# 确保导入顺序正确，避免外键引用问题
__all__ = [
    # 原有模型
    "User",
    "UserProfile",
    "Template",
    "TemplatePlaceholder",
    "PlaceholderValue", 
    "TemplateExecutionHistory",
    "PlaceholderChartCache",
    "DataSource",
    "ETLJob",
    "ReportHistory",
    "AnalyticsData",
    "PlaceholderMapping",
    # LLM模型
    "LLMServer",
    "LLMModel",
    "ModelType",
    "UserLLMPreference",
    "UserLLMUsageQuota",
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
    # 通知模型
    "Notification",
    "NotificationPreference",
    "NotificationStatus",
    "NotificationType",
    "NotificationPriority",
]