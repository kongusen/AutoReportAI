"""
Domain Layer

领域层入口，包含核心业务逻辑和领域服务：
- placeholder: 占位符领域（合并了业务服务）
- template: 模板领域（合并了业务服务）
- analysis: 分析领域
- reporting: 报告领域（合并了业务服务）
- data_source: 数据源领域（新增）
"""

# Placeholder领域 - 使用新架构的模型
from .placeholder.models import (
    StatisticalType, SyntaxType, ProcessingStage, ResultSource,
    TimeContext, BusinessContext, DocumentContext, ContextWeight, AgentContext,
    PlaceholderAnalysisResult, ContextAnalysisResult, BatchAnalysisResult,
    PlaceholderSpec, ParameterizedPlaceholder, CompositePlaceholder, ConditionalPlaceholder,
    ProcessingResult, ProcessedPlaceholder, TemplateAnalysis
)
from .placeholder.parsers import (
    PlaceholderParser, CompositeParser, ConditionalParser,
    ParameterizedParser, ParserFactory, SyntaxValidator
)
from .placeholder.semantic import (
    SemanticAnalyzer, SemanticPlaceholderParser, IntentClassifier,
    ImplicitParameterInferencer
)
from .placeholder.context import (
    ContextAnalysisEngine, DocumentAnalyzer, BusinessRuleAnalyzer,
    ParagraphAnalyzer, SectionAnalyzer
)

# Template领域  
from .template.entities.template_entity import (
    TemplateEntity, TemplateStatus, TemplateType, TemplateSection,
    TemplateValidationRule, ValidationLevel, TemplateMetrics
)
from .template.services.template_domain_service import (
    TemplateDomainService, TemplateParser, TemplateValidator
)
# Template业务服务（合并后）
# TEMPORARILY DISABLED: Migrated to React Agent system
# from .template.template_service import TemplateService
# from .enhanced_template_parser import EnhancedTemplateParser
# from .template.agent_sql_analysis_service import AgentSQLAnalysisService

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

# Data Source领域（新增）
from .data_source.entities.data_source_entity import (
    DataSourceEntity, DataSourceType, DataSourceStatus
)
from .data_source.value_objects.connection_config import ConnectionConfig
from .data_source.value_objects.data_source_credentials import (
    DataSourceCredentials, CredentialType
)
from .data_source.services.data_source_domain_service import DataSourceDomainService

__all__ = [
    # Placeholder领域 - 新架构
    "StatisticalType",
    "SyntaxType", 
    "ProcessingStage",
    "ResultSource",
    "TimeContext",
    "BusinessContext",
    "DocumentContext", 
    "ContextWeight",
    "AgentContext",
    "PlaceholderAnalysisResult",
    "ContextAnalysisResult",
    "BatchAnalysisResult",
    "PlaceholderSpec",
    "ParameterizedPlaceholder",
    "CompositePlaceholder",
    "ConditionalPlaceholder",
    "ProcessingResult",
    "ProcessedPlaceholder", 
    "TemplateAnalysis",
    # Placeholder解析器
    "PlaceholderParser",
    "CompositeParser",
    "ConditionalParser",
    "ParameterizedParser",
    "ParserFactory",
    "SyntaxValidator",
    # Placeholder语义分析
    "SemanticAnalyzer",
    "SemanticPlaceholderParser", 
    "IntentClassifier",
    "ImplicitParameterInferencer",
    # Placeholder上下文分析
    "ContextAnalysisEngine",
    "DocumentAnalyzer",
    "BusinessRuleAnalyzer",
    "ParagraphAnalyzer",
    "SectionAnalyzer",
    
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
    # Template业务服务 (TEMPORARILY DISABLED)
    # "TemplateService",
    # "EnhancedTemplateParser", 
    # "AgentSQLAnalysisService",
    
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
    
    # Data Source领域（新增）
    "DataSourceEntity",
    "DataSourceType",
    "DataSourceStatus",
    "ConnectionConfig",
    "DataSourceCredentials",
    "CredentialType",
    "DataSourceDomainService",
]