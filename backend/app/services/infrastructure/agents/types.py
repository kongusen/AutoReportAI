"""
Agent系统类型定义
简洁的数据结构，支持标准化的输入输出
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class PlaceholderSpec:
    """占位符规格定义"""
    id: Optional[str] = None
    description: str = ""
    type: str = "stat"  # "stat", "chart", "list", "text"
    granularity: str = "daily"  # "daily", "weekly", "monthly"


@dataclass
class SchemaInfo:
    """数据库架构信息"""
    tables: List[str] = field(default_factory=list)
    columns: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class TaskContext:
    """任务执行上下文"""
    task_time: Optional[float] = None
    timezone: str = "Asia/Shanghai"
    window: Optional[Dict[str, Any]] = None


@dataclass
class AgentConstraints:
    """Agent执行约束"""
    sql_only: bool = True
    output_kind: str = "sql"  # "sql", "chart", "report"
    max_attempts: int = 5
    policy_row_limit: Optional[int] = None
    quality_min_rows: Optional[int] = None


@dataclass
class AgentInput:
    """Agent系统标准化输入"""
    user_prompt: str
    placeholder: PlaceholderSpec
    schema: SchemaInfo
    context: TaskContext
    constraints: AgentConstraints = field(default_factory=AgentConstraints)
    template_id: Optional[str] = None
    data_source: Optional[Dict[str, Any]] = None
    task_driven_context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None  # 添加用户ID字段


@dataclass
class AgentOutput:
    """Agent系统标准化输出"""
    success: bool
    result: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# 工具执行结果类型
ToolResult = Dict[str, Any]