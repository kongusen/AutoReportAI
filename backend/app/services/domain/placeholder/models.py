"""
智能占位符系统核心数据模型

定义新架构下的数据结构和接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from datetime import datetime
import hashlib


class StatisticalType(Enum):
    """统计类型枚举"""
    STATISTICS = "统计"      # 总和、平均值、计数
    TREND = "趋势"          # 增长率、变化趋势
    EXTREME = "极值"        # 最大值、最小值、异常值
    LIST = "列表"          # 排行榜、明细列表
    CHART = "统计图"       # 柱状图、折线图、饼图
    COMPARISON = "对比"     # 同比、环比
    FORECAST = "预测"      # 趋势预测、预估值


class SyntaxType(Enum):
    """占位符语法类型"""
    BASIC = "basic"              # {{统计：需求描述}}
    PARAMETERIZED = "parameterized"   # {{统计：需求|参数=值}}
    COMPOSITE = "composite"       # {{组合：{统计：A}占{统计：B}比例}}
    CONDITIONAL = "conditional"   # {{统计：需求|条件=XX}}


class ProcessingStage(Enum):
    """处理阶段"""
    PARSING = "parsing"
    CONTEXT_ANALYSIS = "context_analysis"
    WEIGHT_CALCULATION = "weight_calculation"
    AGENT_ANALYSIS = "agent_analysis"
    SQL_GENERATION = "sql_generation"
    EXECUTION = "execution"
    RESULT_FORMATTING = "result_formatting"
    CACHING = "caching"


class ResultSource(Enum):
    """结果来源"""
    CACHE_HIT = "cache_hit"
    FRESH_ANALYSIS = "fresh_analysis"
    FALLBACK = "fallback"
    ERROR_RECOVERY = "error_recovery"


# ==================== 基础数据结构 ====================

@dataclass
class PlaceholderSpec:
    """占位符规格说明基类"""
    statistical_type: StatisticalType
    description: str
    raw_text: str
    syntax_type: SyntaxType
    confidence_score: float = 0.0
    
    def get_hash(self) -> str:
        """获取占位符哈希值"""
        content = f"{self.statistical_type.value}|{self.description}|{self.syntax_type.value}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class ParameterizedPlaceholder(PlaceholderSpec):
    """参数化占位符"""
    parameters: Dict[str, str] = field(default_factory=dict)
    
    def get_time_range(self) -> Optional['TimeRange']:
        """获取时间范围参数"""
        if '时间范围' in self.parameters:
            return TimeRange.parse(self.parameters['时间范围'])
        return None
        
    def get_filter_conditions(self) -> List['FilterCondition']:
        """获取过滤条件"""
        conditions = []
        if '条件' in self.parameters:
            conditions.append(FilterCondition.parse(self.parameters['条件']))
        if '部门' in self.parameters:
            conditions.append(FilterCondition('department', '=', self.parameters['部门']))
        return conditions
        
    def get_grouping(self) -> Optional[str]:
        """获取分组字段"""
        return self.parameters.get('分组')
        
    def get_sorting(self) -> Optional['SortSpec']:
        """获取排序规格"""
        if '排序' in self.parameters and '数量' in self.parameters:
            return SortSpec(
                order=self.parameters['排序'],
                limit=int(self.parameters['数量'])
            )
        return None


@dataclass
class CompositePlaceholder(PlaceholderSpec):
    """组合占位符"""
    sub_placeholders: List[PlaceholderSpec] = field(default_factory=list)
    composition_logic: str = ""
    
    def get_dependency_order(self) -> List[str]:
        """获取依赖执行顺序"""
        return [ph.get_hash() for ph in self.sub_placeholders]


@dataclass
class ConditionalPlaceholder(PlaceholderSpec):
    """条件占位符"""
    conditions: List['FilterCondition'] = field(default_factory=list)
    fallback_logic: Optional[str] = None


# ==================== 上下文相关数据结构 ====================

@dataclass
class TimeContext:
    """时间上下文"""
    report_period: str          # "2024-01" 
    period_type: str           # "monthly", "weekly", "daily"
    start_date: datetime
    end_date: datetime
    previous_period_start: datetime  # 对比期间
    previous_period_end: datetime
    fiscal_year: str
    quarter: str
    
    def to_agent_prompt(self) -> str:
        """转换为Agent提示"""
        return f"""
        报告时间范围: {self.start_date} 至 {self.end_date}
        统计周期: {self.period_type}
        对比基准期: {self.previous_period_start} 至 {self.previous_period_end}
        财年: {self.fiscal_year}, 季度: {self.quarter}
        """
    
    def get_hash(self) -> str:
        """获取时间上下文哈希"""
        content = f"{self.report_period}|{self.period_type}|{self.start_date}|{self.end_date}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass  
class BusinessContext:
    """业务上下文"""
    task_type: str             # "sales_report", "financial_summary"
    department: str            # "sales", "finance", "marketing" 
    report_level: str          # "summary", "detailed", "executive"
    data_granularity: str      # "daily", "weekly", "monthly"
    include_comparisons: bool   # 是否包含同比环比
    target_audience: str       # "management", "analyst", "client"
    
    def to_agent_prompt(self) -> str:
        """转换为Agent提示"""
        return f"""
        业务类型: {self.task_type}
        部门: {self.department}  
        报告层级: {self.report_level}
        数据粒度: {self.data_granularity}
        需要对比分析: {self.include_comparisons}
        目标受众: {self.target_audience}
        """
    
    def get_hash(self) -> str:
        """获取业务上下文哈希"""
        content = f"{self.task_type}|{self.department}|{self.report_level}|{self.data_granularity}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class DocumentContext:
    """文档上下文"""
    document_id: str
    paragraph_content: str
    paragraph_index: int
    section_title: str
    section_index: int
    surrounding_text: str
    document_structure: Dict[str, Any] = field(default_factory=dict)
    
    def to_agent_prompt(self) -> str:
        """转换为Agent提示"""
        return f"""
        文档段落: {self.paragraph_content}
        所在章节: {self.section_title}
        前后文本: {self.surrounding_text}
        文档结构: {self.document_structure}
        """
    
    def get_hash(self) -> str:
        """获取文档上下文哈希"""
        content = f"{self.document_id}|{self.paragraph_index}|{self.section_index}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class ContextWeight:
    """上下文权重配置"""
    paragraph_weight: float = 0.4      # 段落上下文权重
    section_weight: float = 0.3        # 章节上下文权重  
    document_weight: float = 0.2       # 文档全局上下文权重
    business_weight: float = 0.1       # 业务规则上下文权重
    
    def normalize(self):
        """归一化权重"""
        total = self.paragraph_weight + self.section_weight + self.document_weight + self.business_weight
        if total > 0:
            self.paragraph_weight /= total
            self.section_weight /= total
            self.document_weight /= total
            self.business_weight /= total


@dataclass
class AgentContext:
    """传递给智能代理的上下文"""
    template_content: str
    template_metadata: Dict[str, Any]
    data_source_schema: Dict[str, Any]
    time_context_prompt: str
    business_context_prompt: str
    document_context_prompt: str
    sql_optimization_hints: List[str]
    user_id: str = "system"
    
    def get_hash(self) -> str:
        """获取上下文哈希用于缓存"""
        content = f"{self.template_content}|{self.time_context_prompt}|{self.business_context_prompt}"
        return hashlib.md5(content.encode()).hexdigest()


# ==================== 分析结果数据结构 ====================

@dataclass
class ContextAnalysisResult:
    """上下文分析结果"""
    paragraph_analysis: Dict[str, Any]
    section_analysis: Dict[str, Any]
    document_analysis: Dict[str, Any]
    business_analysis: Dict[str, Any]
    integrated_context: Dict[str, Any]
    confidence_score: float
    processing_time_ms: int


@dataclass
class PlaceholderAnalysisResult:
    """占位符分析结果"""
    success: bool
    placeholder_spec: PlaceholderSpec
    context_analysis: ContextAnalysisResult
    generated_sql: str
    sql_quality_score: float
    execution_plan: Dict[str, Any]
    analysis_insights: str
    confidence_score: float
    agent_reasoning: str
    processing_time_ms: int
    sources: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class BatchAnalysisResult:
    """批量分析结果"""
    success: bool
    template_id: str
    total_placeholders: int
    successfully_analyzed: int
    analysis_results: List[PlaceholderAnalysisResult]
    overall_confidence: float
    processing_time_ms: int
    error_message: Optional[str] = None


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    validated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingMetrics:
    """处理指标"""
    total_time: float = 0.0
    parsing_time: float = 0.0
    analysis_time: float = 0.0
    generation_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    

@dataclass
class ProcessedPlaceholder:
    """已处理占位符"""
    placeholder_spec: PlaceholderSpec
    final_weight: float
    weight_components: 'WeightComponents'
    processing_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WeightComponents:
    """权重组件"""
    confidence_score: float = 0.0
    context_score: float = 0.0
    complexity_score: float = 0.0
    business_score: float = 0.0


@dataclass
class ProcessingResult:
    """处理结果"""
    processed_placeholders: List[ProcessedPlaceholder]
    processing_metrics: ProcessingMetrics
    quality_score: float
    recommendations: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    success: bool = True


# ==================== 辅助数据结构 ====================

@dataclass
class TimeRange:
    """时间范围"""
    start: datetime
    end: datetime
    period_type: str
    
    @classmethod
    def parse(cls, time_str: str) -> 'TimeRange':
        """解析时间范围字符串"""
        # 实现时间字符串解析逻辑
        # 例如: "2024-01" -> 2024年1月的开始和结束
        # 这里简化实现，实际需要更复杂的解析逻辑
        if "-" in time_str and len(time_str) == 7:  # YYYY-MM格式
            year, month = map(int, time_str.split("-"))
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)
            return cls(start=start, end=end, period_type="monthly")
        
        raise ValueError(f"Unsupported time format: {time_str}")


@dataclass
class FilterCondition:
    """过滤条件"""
    field: str
    operator: str
    value: str
    
    @classmethod
    def parse(cls, condition_str: str) -> 'FilterCondition':
        """解析条件字符串"""
        # 简化实现，实际需要更复杂的解析逻辑
        if "=" in condition_str:
            field, value = condition_str.split("=", 1)
            return cls(field=field.strip(), operator="=", value=value.strip())
        elif ">" in condition_str:
            field, value = condition_str.split(">", 1)
            return cls(field=field.strip(), operator=">", value=value.strip())
        
        raise ValueError(f"Unsupported condition format: {condition_str}")


@dataclass
class SortSpec:
    """排序规格"""
    order: str  # "asc" or "desc"
    limit: int


@dataclass
class TemplateAnalysis:
    """模板分析结果"""
    template_id: str
    placeholder_count: int
    complexity_score: float
    quality_score: float
    syntax_types: Dict[str, int] = field(default_factory=dict)
    statistical_types: Dict[str, int] = field(default_factory=dict)
    issues_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    analysis_timestamp: datetime = field(default_factory=datetime.now)


# ==================== 接口定义 ====================

class PlaceholderParserInterface(ABC):
    """占位符解析器接口"""
    
    @abstractmethod
    async def parse(self, placeholder_text: str) -> PlaceholderSpec:
        """解析占位符文本"""
        pass
    
    @abstractmethod
    def supports_syntax(self, syntax_type: SyntaxType) -> bool:
        """是否支持指定语法类型"""
        pass


class ContextAnalyzerInterface(ABC):
    """上下文分析器接口"""
    
    @abstractmethod
    async def analyze(
        self, 
        placeholder: PlaceholderSpec,
        document_context: DocumentContext,
        business_context: BusinessContext,
        time_context: TimeContext
    ) -> ContextAnalysisResult:
        """分析上下文"""
        pass


class WeightCalculatorInterface(ABC):
    """权重计算器接口"""
    
    @abstractmethod
    async def calculate_weights(
        self,
        placeholder_spec: PlaceholderSpec,
        context_analysis: ContextAnalysisResult
    ) -> ContextWeight:
        """计算上下文权重"""
        pass


class PlaceholderOrchestratorInterface(ABC):
    """占位符编排器接口"""
    
    @abstractmethod
    async def analyze_with_context(
        self,
        template_id: str,
        time_context: TimeContext,
        business_context: BusinessContext,
        document_context: DocumentContext
    ) -> BatchAnalysisResult:
        """带上下文的占位符分析"""
        pass
    
    @abstractmethod
    async def analyze_for_debug(
        self,
        template_content: str,
        debug_context: Dict[str, Any]
    ) -> BatchAnalysisResult:
        """调试模式分析"""
        pass


# ==================== 异常定义 ====================

class PlaceholderError(Exception):
    """占位符处理基础异常"""
    pass


class PlaceholderSyntaxError(PlaceholderError):
    """占位符语法错误"""
    pass


class PlaceholderAnalysisError(PlaceholderError):
    """占位符分析错误"""
    pass


class ContextAnalysisError(PlaceholderError):
    """上下文分析错误"""
    pass


class WeightCalculationError(PlaceholderError):
    """权重计算错误"""
    pass