"""
data_processing 服务模块

提供 data_processing 相关的业务逻辑处理
"""

# 模块版本
__version__ = "1.0.0"

# 导入核心组件
from .retrieval import DataRetrievalService
from .analysis import DataAnalysisService

# 导入ETL组件
from .etl.etl_service import ETLService, ETLJobStatus
from .etl.etl_engine_service import ETLTransformationEngine
from .etl.intelligent_etl_executor import IntelligentETLExecutor
from .etl.etl_job_scheduler import ETLJobScheduler, ETLJobExecutionStatus

# 模块导出
__all__ = [
    "DataRetrievalService",
    "DataAnalysisService",
    "ETLService",
    "ETLJobStatus",
    "ETLTransformationEngine",
    "IntelligentETLExecutor",
    "ETLJobScheduler",
    "ETLJobExecutionStatus"
]