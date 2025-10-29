"""
占位符业务类型定义 - 领域层类型
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# 占位符业务枚举
# ============================================================================

class PlaceholderType(str, Enum):
    """占位符类型"""
    TEXT = "text"
    CHART = "chart" 
    TABLE = "table"
    METRIC = "metric"
    IMAGE = "image"


class ChartType(str, Enum):
    """图表类型"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    TABLE = "table"
    HEATMAP = "heatmap"


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================================
# 占位符核心数据结构
# ============================================================================

@dataclass
class PlaceholderInfo:
    """占位符信息"""
    placeholder_id: str
    name: str
    type: PlaceholderType
    description: str
    sql_query: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    data_source_id: Optional[str] = None
    template_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PlaceholderAnalysisRequest:
    """占位符分析请求"""
    placeholder_id: str
    business_command: str
    requirements: str
    # 统一的任务上下文字段：供上层传入真实执行上下文（时间窗、调度等）
    task_context: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    target_objective: str = ""
    data_source_info: Optional[Dict[str, Any]] = None
    priority: TaskPriority = TaskPriority.MEDIUM


@dataclass
class PlaceholderUpdateRequest:
    """占位符更新请求"""
    placeholder_id: str
    task_context: Dict[str, Any]
    current_task_info: Dict[str, Any]
    target_objective: str
    stored_placeholders: List[PlaceholderInfo]
    update_criteria: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaceholderCompletionRequest:
    """占位符完成请求"""
    placeholder_id: str
    etl_data: List[Dict[str, Any]]
    placeholder_requirements: str
    template_section: str
    chart_generation_needed: bool = False
    target_chart_type: Optional[ChartType] = None


# ============================================================================
# 结果类型
# ============================================================================

@dataclass
class SQLGenerationResult:
    """SQL生成结果"""
    sql_query: str
    validation_status: str
    optimization_applied: bool
    estimated_performance: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaceholderUpdateResult:
    """占位符更新结果"""
    placeholder_id: str
    update_needed: bool
    updated_sql: Optional[str] = None
    update_reason: str = ""
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartGenerationResult:
    """图表生成结果"""
    chart_type: ChartType
    chart_config: Dict[str, Any]
    chart_data: List[Dict[str, Any]]
    chart_title: str
    chart_description: str
    placement_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaceholderCompletionResult:
    """占位符完成结果"""
    placeholder_id: str
    completed_content: str
    chart_result: Optional[ChartGenerationResult] = None
    template_updates: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 专用Agent定义
# ============================================================================

@dataclass
class PlaceholderAgent:
    """占位符处理专用智能体"""
    agent_id: str
    name: str
    capabilities: List[str] = field(default_factory=list)
    specialization: str = ""
    business_flow: str = ""  # analysis, update, completion
    supported_placeholders: List[PlaceholderType] = field(default_factory=list)
    data_source_capabilities: List[str] = field(default_factory=list)