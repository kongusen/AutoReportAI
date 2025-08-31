"""
占位符系统测试套件

包含完整的智能占位符系统测试：
- 单元测试：占位符解析器、上下文分析引擎
- 集成测试：端到端占位符处理流程  
- 性能测试：SQL生成和执行性能
- 功能测试：各类统计类型处理功能
- 验收测试：真实用户场景模拟

测试覆盖范围：
- 7种统计类型：STATISTICAL, TREND, COMPARISON, RANKING, FORECAST, DISTRIBUTION, PROPORTION
- 4种语法类型：BASIC, PARAMETERIZED, COMPOSITE, CONDITIONAL
- 完整的处理流程：解析 -> 分析 -> 生成 -> 执行 -> 缓存
- 各种边界条件和异常情况
"""

# 测试模块导入
from .test_parsers import *
from .test_context_analysis import *
from .test_integration import *
from .test_performance import *
from .test_functional import *
from .test_acceptance import *

__all__ = [
    # 测试类
    "TestPlaceholderParser",
    "TestParameterizedParser", 
    "TestCompositeParser",
    "TestConditionalParser",
    "TestSyntaxValidator",
    "TestParserFactory",
    "TestContextAnalysisEngine",
    "TestParagraphAnalyzer",
    "TestSectionAnalyzer", 
    "TestDocumentAnalyzer",
    "TestBusinessRuleAnalyzer",
    "TestPlaceholderIntegration",
    "TestStatisticalTypeProcessing",
    "TestComplexScenarios",
    "TestPlaceholderPerformance",
    "TestScalabilityPerformance",
    "TestStatisticalTypeFunctionality",
    "TestComplexPlaceholderFunctionality",
    "TestBusinessContextFunctionality",
    "TestErrorHandlingFunctionality",
    "TestUserAcceptanceScenarios",
]