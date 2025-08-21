"""
占位符处理系统的核心数据模型

统一定义各层之间的数据结构和接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime


class ProcessingStage(Enum):
    """处理阶段"""
    CACHE_CHECK = "cache_check"
    AGENT_ANALYSIS = "agent_analysis"
    AGENT_EXECUTION = "agent_execution"
    RULE_FALLBACK = "rule_fallback"
    RULE_EXECUTION = "rule_execution"
    FINAL_RESULT = "final_result"


class ResultSource(Enum):
    """结果来源"""
    CACHE_HIT = "cache_hit"
    AGENT_SUCCESS = "agent_success"
    RULE_FALLBACK = "rule_fallback"
    ERROR_FALLBACK = "error_fallback"


@dataclass
class PlaceholderRequest:
    """占位符请求上下文"""
    placeholder_id: str
    placeholder_name: str
    placeholder_type: str
    data_source_id: str
    user_id: str
    force_reanalyze: bool = False
    execution_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.execution_time is None:
            self.execution_time = datetime.now()


@dataclass
class PlaceholderResponse:
    """占位符响应"""
    success: bool
    value: str
    source: ResultSource
    execution_time_ms: int
    confidence: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheKey:
    """缓存键"""
    placeholder_id: str
    data_source_id: str
    user_id: str
    time_context: str
    
    def to_string(self) -> str:
        import hashlib
        key_str = f"{self.placeholder_id}|{self.data_source_id}|{self.user_id}|{self.time_context}"
        return hashlib.md5(key_str.encode()).hexdigest()


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: str
    confidence: float
    cached_at: datetime
    expires_at: datetime
    source_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAnalysisResult:
    """Agent分析结果"""
    success: bool
    sql: Optional[str] = None
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)
    target_table: Optional[str] = None
    target_fields: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    error_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentExecutionResult:
    """Agent执行结果"""
    success: bool
    formatted_value: Optional[str] = None
    execution_time_ms: int = 0
    confidence: float = 0.0
    raw_data: Any = None
    row_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    error_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleGenerationResult:
    """规则生成结果"""
    success: bool
    sql: Optional[str] = None
    formatted_value: Optional[str] = None
    execution_time_ms: int = 0
    rule_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class ExecutionResult:
    """SQL执行结果"""
    success: bool
    formatted_value: Optional[str] = None
    execution_time_ms: int = 0
    row_count: int = 0
    raw_data: Any = None
    error_message: Optional[str] = None


@dataclass
class SchemaInfo:
    """Schema信息"""
    data_source_id: str
    tables: List[str]
    table_details: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


# 抽象接口定义

class CacheServiceInterface(ABC):
    """缓存服务接口"""
    
    @abstractmethod
    async def get_result(self, request: PlaceholderRequest) -> Optional[CacheEntry]:
        """获取缓存结果"""
        pass
    
    @abstractmethod
    async def save_result(self, request: PlaceholderRequest, result: AgentExecutionResult) -> bool:
        """保存结果到缓存"""
        pass


class AgentAnalysisServiceInterface(ABC):
    """Agent分析服务接口"""
    
    @abstractmethod
    async def analyze_and_execute(self, request: PlaceholderRequest) -> AgentExecutionResult:
        """完整的Agent分析和执行流程"""
        pass


class TemplateRuleServiceInterface(ABC):
    """模板规则服务接口"""
    
    @abstractmethod
    async def generate_and_execute(self, request: PlaceholderRequest, agent_error_context: Dict[str, Any]) -> RuleGenerationResult:
        """规则生成和执行"""
        pass


class DataExecutionServiceInterface(ABC):
    """数据执行服务接口"""
    
    @abstractmethod
    async def execute_sql(self, data_source_id: str, sql: str) -> ExecutionResult:
        """执行SQL查询"""
        pass