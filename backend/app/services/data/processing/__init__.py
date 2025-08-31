"""
data_processing 服务模块

提供 data_processing 相关的业务逻辑处理
"""

# 模块版本
__version__ = "1.0.0"

# 导入核心组件
from .retrieval import DataRetrievalService
from .analysis import DataAnalysisService
from .schema_aware_analysis import SchemaAwareAnalysisService

# 导入数据处理组件
from .statistics_service import StatisticsService
from .visualization_service import VisualizationService
from .data_sanitization_service import data_sanitizer

# 导入ETL组件
# from .etl.etl_service import ETLService, ETLJobStatus  # 临时禁用避免IAOP依赖
# from .etl.etl_engine_service import ETLTransformationEngine  # 临时禁用避免IAOP依赖
# from .etl.intelligent_etl_executor import IntelligentETLExecutor  # 临时禁用避免IAOP依赖
# from .etl.celery_etl_scheduler import CeleryETLScheduler, ETLJobExecutionStatus  # 临时禁用避免IAOP依赖

# 模块导出
__all__ = [
    "DataRetrievalService",
    "DataAnalysisService",
    "SchemaAwareAnalysisService",
    "StatisticsService",
    "VisualizationService",
    "data_sanitizer",
    # "ETLService",  # 临时禁用
    # "ETLJobStatus",  # 临时禁用
    # "ETLTransformationEngine",  # 临时禁用
    # "IntelligentETLExecutor",  # 临时禁用
    # "CeleryETLScheduler",  # 临时禁用
    # "ETLJobExecutionStatus"  # 临时禁用
]