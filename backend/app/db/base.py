# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base
from app.models.analytics_data import AnalyticsData  # noqa
# 导入新的LLM服务器和模型
from app.models.llm_server import (  # noqa
    LLMServer,
    LLMModel,
    ModelType
)
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
from app.models.template_placeholder import (  # noqa  # 依赖Template
    TemplatePlaceholder,
    PlaceholderValue,
    TemplateExecutionHistory
)
from app.models.placeholder_chart_cache import PlaceholderChartCache  # noqa  # 依赖TemplatePlaceholder
from app.models.user_llm_preference import UserLLMPreference, UserLLMUsageQuota  # noqa
from app.models.table_schema import TableSchema, ColumnSchema, TableRelationship, ColumnType  # noqa
from app.models.task import TaskExecution, TaskStatus, ProcessingMode, AgentWorkflowType  # noqa

# 导入顺序很重要 - 被引用的模型必须先导入
from app.models.user import User  # noqa
from app.models.user_profile import UserProfile  # noqa
