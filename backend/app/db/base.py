# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base
from app.models.ai_provider import AIProvider  # noqa
from app.models.analytics_data import AnalyticsData  # noqa
from app.models.data_source import DataSource  # noqa  # DataSource必须在ETLJob之前
from app.models.etl_job import ETLJob  # noqa  # 依赖DataSource

# 学习数据模型 - 依赖User, Template, DataSource
from app.models.learning_data import (  # noqa
    ErrorLog,
    FieldMappingCache,
    KnowledgeBase,
    LearningRule,
    LLMCallLog,
    PlaceholderProcessingHistory,
    ReportQualityScore,
    UserFeedback,
)
from app.models.placeholder_mapping import (  # noqa  # 依赖Template和DataSource
    PlaceholderMapping,
)
from app.models.report_history import ReportHistory  # noqa
from app.models.task import Task  # noqa
from app.models.template import Template  # noqa  # Template必须在PlaceholderMapping之前

# 导入顺序很重要 - 被引用的模型必须先导入
from app.models.user import User  # noqa
from app.models.user_profile import UserProfile  # noqa
