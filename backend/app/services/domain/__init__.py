"""
Domain Layer

领域层入口，包含核心业务逻辑和领域服务：
- placeholder: 占位符领域（合并了业务服务）
- template: 模板领域（合并了业务服务）
- analysis: 分析领域
- reporting: 报告领域（合并了业务服务）
"""

# Placeholder领域
from .placeholder.entities.placeholder_entity import (
    PlaceholderEntity, PlaceholderType, AnalysisResult, DataType,
    PlaceholderRule, PlaceholderContext, AnalysisStatus
)
from .placeholder.services.placeholder_domain_service import (
    PlaceholderDomainService, PlaceholderParser, PlaceholderSemanticAnalyzer
)
# Placeholder业务服务（合并后）
from .placeholder.cache_service import CacheService
from .placeholder.execution_service import DataExecutionService
from .placeholder.rule_service import TemplateRuleService

# Template领域  
from .template.entities.template_entity import (
    TemplateEntity, TemplateStatus, TemplateType, TemplateSection,
    TemplateValidationRule, ValidationLevel, TemplateMetrics
)
from .template.services.template_domain_service import (
    TemplateDomainService, TemplateParser, TemplateValidator
)
# Template业务服务（合并后）
from .template.template_service import TemplateService
from .template.enhanced_template_parser import EnhancedTemplateParser
from .template.agent_sql_analysis_service import AgentSQLAnalysisService

# Analysis领域
from .analysis.services.data_analysis_domain_service import (
    DataAnalysisDomainService, DataProfile, StatisticalSummary,
    AnomalyDetectionResult, AnalysisType, DataQuality
)

# Reporting领域
from .reporting.services.report_generation_domain_service import (
    ReportGenerationDomainService, ReportEntity, ReportMetadata,
    ContentBlock, ReportSection, ReportFormat, ReportStatus, ContentType
)
# Reporting业务服务（合并后）
from .reporting.generator import ReportGenerationService
from .reporting.composer import ReportCompositionService  
from .reporting.word_generator_service import WordGeneratorService

__all__ = [
    # Placeholder领域
    "PlaceholderEntity",
    "PlaceholderType",
    "AnalysisResult", 
    "DataType",
    "PlaceholderRule",
    "PlaceholderContext",
    "AnalysisStatus",
    "PlaceholderDomainService",
    "PlaceholderParser",
    "PlaceholderSemanticAnalyzer",
    # Placeholder业务服务
    "CacheService", 
    "DataExecutionService",
    "TemplateRuleService",
    
    # Template领域
    "TemplateEntity",
    "TemplateStatus",
    "TemplateType", 
    "TemplateSection",
    "TemplateValidationRule",
    "ValidationLevel",
    "TemplateMetrics",
    "TemplateDomainService",
    "TemplateParser",
    "TemplateValidator",
    # Template业务服务
    "TemplateService",
    "EnhancedTemplateParser",
    "AgentSQLAnalysisService",
    
    # Analysis领域
    "DataAnalysisDomainService",
    "DataProfile",
    "StatisticalSummary",
    "AnomalyDetectionResult",
    "AnalysisType",
    "DataQuality",
    
    # Reporting领域
    "ReportGenerationDomainService",
    "ReportEntity",
    "ReportMetadata",
    "ContentBlock",
    "ReportSection", 
    "ReportFormat",
    "ReportStatus",
    "ContentType",
    # Reporting业务服务
    "ReportGenerationService",
    "ReportCompositionService",
    "WordGeneratorService",
]