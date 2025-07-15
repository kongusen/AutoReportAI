# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base

# 导入顺序很重要 - 被引用的模型必须先导入
from app.models.user import User  # noqa
from app.models.user_profile import UserProfile  # noqa
from app.models.template import Template  # noqa  # Template必须在PlaceholderMapping之前
from app.models.data_source import DataSource  # noqa  # DataSource必须在PlaceholderMapping之前
from app.models.enhanced_data_source import EnhancedDataSource  # noqa
from app.models.ai_provider import AIProvider  # noqa
from app.models.analytics_data import AnalyticsData  # noqa
from app.models.placeholder_mapping import PlaceholderMapping  # noqa  # 依赖Template和DataSource
from app.models.etl_job import ETLJob  # noqa
from app.models.report_history import ReportHistory  # noqa
from app.models.task import Task  # noqa
