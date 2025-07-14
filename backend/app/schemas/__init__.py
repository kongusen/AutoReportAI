# 通用消息模式
from pydantic import BaseModel

from .ai_provider import AIProvider, AIProviderCreate, AIProviderUpdate
from .analytics_data import AnalyticsData, AnalyticsDataCreate, AnalyticsDataUpdate
from .data_source import DataSource, DataSourceCreate, DataSourceUpdate
from .enhanced_data_source import (
    EnhancedDataSource,
    EnhancedDataSourceCreate,
    EnhancedDataSourceUpdate,
)
from .etl_job import ETLJob, ETLJobCreate, ETLJobUpdate
from .placeholder_mapping import (
    PlaceholderMapping,
    PlaceholderMappingCreate,
    PlaceholderMappingUpdate,
)
from .report_history import ReportHistory, ReportHistoryCreate
from .task import Task, TaskCreate, TaskRead, TaskUpdate
from .template import Template, TemplateCreate, TemplateUpdate
from .token import Token, TokenPayload
from .user import User, UserCreate, UserUpdate


class Msg(BaseModel):
    msg: str
