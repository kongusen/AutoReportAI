"""
report_generation 服务模块

提供 report_generation 相关的业务逻辑处理
"""

# 模块版本
__version__ = "1.0.0"

# 导入核心组件
from .generator import ReportGenerationService, ReportGenerationStatus
from .composer import ReportCompositionService
from .quality_checker import (
    ReportQualityChecker, 
    QualityCheckResult, 
    QualityMetrics,
    QualityIssue,
    QualityIssueType,
    QualitySeverity,
    LanguageAnalyzer,
    DataConsistencyValidator
)
from .document_pipeline import TemplateParser
from .word_generator_service import WordGeneratorService

# 模块导出
__all__ = [
    "ReportGenerationService",
    "ReportGenerationStatus",
    "ReportCompositionService", 
    "ReportQualityChecker",
    "QualityCheckResult",
    "QualityMetrics",
    "QualityIssue",
    "QualityIssueType",
    "QualitySeverity",
    "LanguageAnalyzer",
    "DataConsistencyValidator",
    "TemplateParser",
    "WordGeneratorService"
]