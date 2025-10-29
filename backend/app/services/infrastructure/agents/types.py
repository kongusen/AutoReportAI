"""
核心类型定义

定义 Loom Agent 系统的核心数据类型和接口
基于 Loom 0.0.3 的 TT 递归执行机制设计
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExecutionStage(str, Enum):
    """执行阶段枚举"""
    INITIALIZATION = "initialization"
    SCHEMA_DISCOVERY = "schema_discovery"
    SQL_GENERATION = "sql_generation"
    SQL_VALIDATION = "sql_validation"
    DATA_EXTRACTION = "data_extraction"
    ANALYSIS = "analysis"
    CHART_GENERATION = "chart_generation"
    COMPLETION = "completion"


class TaskComplexity(float, Enum):
    """任务复杂度枚举

    每个复杂度级别对应一个0-1之间的数值
    """
    SIMPLE = 0.3   # 简单任务
    MEDIUM = 0.5   # 中等任务
    COMPLEX = 0.8  # 复杂任务

    @classmethod
    def from_value(cls, value: Union[str, float, 'TaskComplexity']) -> 'TaskComplexity':
        """从不同类型的值创建 TaskComplexity

        Args:
            value: 字符串名称、float值或TaskComplexity实例

        Returns:
            TaskComplexity 实例
        """
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            # 尝试从字符串名称匹配
            value_lower = value.lower()
            for item in cls:
                if item.name.lower() == value_lower:
                    return item
            # 默认返回 MEDIUM
            return cls.MEDIUM

        if isinstance(value, (int, float)):
            # 根据数值范围选择最接近的级别
            if value <= 0.4:
                return cls.SIMPLE
            elif value <= 0.6:
                return cls.MEDIUM
            else:
                return cls.COMPLEX

        return cls.MEDIUM


class ToolCategory(str, Enum):
    """工具类别枚举"""
    SCHEMA = "schema"
    SQL = "sql"
    DATA = "data"
    TIME = "time"
    CHART = "chart"


@dataclass
class AgentRequest:
    """Agent 请求类型
    
    包含执行任务所需的所有信息
    """
    # 核心信息
    placeholder: str  # 占位符文本
    data_source_id: int  # 数据源ID
    user_id: str  # 用户ID
    
    # 任务上下文
    task_context: Dict[str, Any] = field(default_factory=dict)
    template_context: Optional[Dict[str, Any]] = None
    
    # 执行配置
    max_iterations: int = 10
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    stage: ExecutionStage = ExecutionStage.INITIALIZATION
    
    # 约束条件
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Agent 响应类型
    
    包含执行结果和相关信息
    """
    # 核心结果
    success: bool
    result: Any  # 主要结果（SQL、数据、图表等）
    
    # 执行信息
    stage: ExecutionStage
    iterations_used: int
    execution_time_ms: int
    
    # 详细信息
    reasoning: str = ""  # 推理过程
    quality_score: float = 0.0  # 质量评分 (0-1)
    
    # 工具调用历史
    tool_calls: List[ToolCall] = field(default_factory=list)
    
    # 错误信息
    error: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    tool_category: ToolCategory
    arguments: Dict[str, Any]
    result: Any
    execution_time_ms: int
    success: bool
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ContextInfo:
    """上下文信息"""
    # Schema 信息
    tables: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    
    # 数据样本
    sample_data: Dict[str, Any] = field(default_factory=dict)
    
    # 时间窗口
    time_window: Optional[Dict[str, Any]] = None
    
    # 业务上下文
    business_context: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionState:
    """执行状态"""
    # 当前状态
    current_stage: ExecutionStage
    iteration_count: int
    start_time: float
    
    # 上下文状态
    context: ContextInfo
    accumulated_results: List[Any] = field(default_factory=list)
    
    # 工具调用历史
    tool_call_history: List[ToolCall] = field(default_factory=list)
    
    # 错误和重试
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    
    # 配置
    max_iterations: int = 10
    max_context_tokens: Optional[int] = None  # 将基于用户配置的模型动态确定
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoordinationConfig:
    """协调配置"""
    # 递归控制
    max_recursion_depth: int = 5
    complexity_threshold: float = 0.8
    
    # 上下文管理
    context_cache_size: int = 100
    context_refresh_interval: int = 300  # 秒
    
    # Token 预算
    max_tokens_per_iteration: int = 4000
    max_total_tokens: int = 16000
    
    # 性能优化
    enable_parallel_execution: bool = True
    max_concurrent_tools: int = 3
    
    # 调试和监控
    enable_detailed_logging: bool = True
    enable_metrics_collection: bool = True


@dataclass
class LLMConfig:
    """LLM 配置"""
    # 基础配置
    provider: str = "container"  # 使用容器LLM服务
    model: str = "auto"  # 自动选择模型
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    
    # 高级配置
    enable_tool_calling: bool = True
    enable_streaming: bool = False
    
    # 策略配置
    selection_policy: Dict[str, Any] = field(default_factory=dict)
    fallback_strategy: str = "auto_retry"


@dataclass
class ToolConfig:
    """工具配置"""
    # 工具启用状态
    enabled_tools: List[str] = field(default_factory=lambda: [
        "schema_discovery", "schema_retrieval", "schema_cache",
        "sql_generator", "sql_validator", "sql_column_checker", 
        "sql_auto_fixer", "sql_executor",
        "data_sampler", "data_analyzer",
        "time_window", "chart_generator", "chart_analyzer"
    ])
    
    # 工具超时
    tool_timeout: int = 30  # 秒
    
    # 工具重试
    max_retries: int = 3
    retry_delay: float = 1.0  # 秒
    
    # 工具限制
    max_tool_calls_per_iteration: int = 5
    max_total_tool_calls: int = 50


@dataclass
class AgentConfig:
    """Agent 配置"""
    # 核心配置
    llm: LLMConfig = field(default_factory=LLMConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    coordination: CoordinationConfig = field(default_factory=CoordinationConfig)
    
    # 执行配置
    max_iterations: int = 10
    max_context_tokens: int = 16000
    
    # 系统提示
    system_prompt: Optional[str] = None
    
    # 回调函数
    callbacks: List[Callable] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


# 事件类型定义
@dataclass
class AgentEvent:
    """Agent 事件"""
    event_type: str
    stage: ExecutionStage
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


# 工具接口定义
class BaseTool:
    """工具基类接口"""
    
    def __init__(self, name: str, category: ToolCategory, description: str):
        self.name = name
        self.category = category
        self.description = description
    
    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        raise NotImplementedError
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式"""
        raise NotImplementedError


# 上下文检索器接口
class BaseContextRetriever:
    """上下文检索器基类"""
    
    async def retrieve(
        self, 
        query: str, 
        context_type: str = "schema",
        top_k: Optional[int] = None
    ) -> List[str]:
        """检索上下文信息"""
        raise NotImplementedError
    
    async def update_context(self, context: ContextInfo) -> None:
        """更新上下文缓存"""
        raise NotImplementedError


# 类型别名
ToolFactory = Callable[..., BaseTool]
ContextRetrieverFactory = Callable[..., BaseContextRetriever]
EventCallback = Callable[[AgentEvent], None]


# 默认配置创建函数
def create_default_agent_config() -> AgentConfig:
    """创建默认 Agent 配置"""
    return AgentConfig()


def create_default_coordination_config() -> CoordinationConfig:
    """创建默认协调配置"""
    return CoordinationConfig()


def create_default_llm_config() -> LLMConfig:
    """创建默认 LLM 配置"""
    return LLMConfig()


def create_default_tool_config() -> ToolConfig:
    """创建默认工具配置"""
    return ToolConfig()


# 导出所有类型
__all__ = [
    # 枚举类型
    "ExecutionStage",
    "TaskComplexity", 
    "ToolCategory",
    
    # 核心数据类型
    "AgentRequest",
    "AgentResponse",
    "ToolCall",
    "ContextInfo",
    "ExecutionState",
    
    # 配置类型
    "CoordinationConfig",
    "LLMConfig",
    "ToolConfig",
    "AgentConfig",
    
    # 事件类型
    "AgentEvent",
    
    # 接口类型
    "BaseTool",
    "BaseContextRetriever",
    
    # 类型别名
    "ToolFactory",
    "ContextRetrieverFactory", 
    "EventCallback",
    
    # 工厂函数
    "create_default_agent_config",
    "create_default_coordination_config",
    "create_default_llm_config",
    "create_default_tool_config",
]