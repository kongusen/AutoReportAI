"""
Prompt上下文定义

定义各种prompt所需的上下文数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class TaskType(str, Enum):
    """任务类型"""
    SQL_ANALYSIS = "sql_analysis"
    CONTEXT_UPDATE = "context_update" 
    DATA_COMPLETION = "data_completion"
    COMPLEXITY_JUDGE = "complexity_judge"
    REACT_REASONING = "react_reasoning"
    REACT_OBSERVATION = "react_observation"
    REACT_REFLECTION = "react_reflection"


class ComplexityLevel(str, Enum):
    """复杂度级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    COMPLEX = "complex"


@dataclass
class PromptContext:
    """基础prompt上下文"""
    task_type: TaskType
    objective: str
    user_id: str = "agent_system"
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationContext:
    """编排上下文 - 用于复杂度判断"""
    
    # 元数据
    orchestration_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 当前步骤信息
    current_step: Dict[str, Any] = field(default_factory=dict)
    
    # 编排链信息
    orchestration_chain: Dict[str, Any] = field(default_factory=dict)
    
    # 上下文累积
    context_accumulation: Dict[str, Any] = field(default_factory=dict)
    
    # 依赖分析
    dependency_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # 影响评估
    impact_assessment: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "orchestration_metadata": self.orchestration_metadata,
            "current_step": self.current_step,
            "orchestration_chain": self.orchestration_chain,
            "context_accumulation": self.context_accumulation,
            "dependency_analysis": self.dependency_analysis,
            "impact_assessment": self.impact_assessment
        }


@dataclass  
class SQLAnalysisContext(PromptContext):
    """SQL分析上下文"""
    task_type: TaskType = TaskType.SQL_ANALYSIS
    objective: str = ""
    business_command: str = ""
    requirements: str = ""
    target_objective: str = ""
    context_info: str = ""
    data_source_info: Optional[str] = None


@dataclass
class ContextUpdateContext(PromptContext):
    """上下文更新分析上下文"""
    task_type: TaskType = TaskType.CONTEXT_UPDATE
    objective: str = ""
    task_context: str = ""
    current_task_info: str = ""
    target_objective: str = ""
    stored_placeholders: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class DataCompletionContext(PromptContext):
    """数据完成上下文"""
    task_type: TaskType = TaskType.DATA_COMPLETION
    objective: str = ""
    placeholder_requirements: str = ""
    template_section: str = ""
    etl_data: List[Dict[str, Any]] = field(default_factory=list)
    chart_generation_needed: bool = False
    target_chart_type: Optional[str] = None


@dataclass
class ComplexityJudgeContext(PromptContext):
    """复杂度判断上下文"""
    task_type: TaskType = TaskType.COMPLEXITY_JUDGE
    objective: str = ""
    orchestration_context: OrchestrationContext = field(default_factory=OrchestrationContext)


@dataclass
class ReActContext(PromptContext):
    """ReAct上下文"""
    task_type: TaskType = TaskType.REACT_REASONING  # 默认值，子类会覆盖
    objective: str = ""
    current_attempt: int = 1
    max_attempts: int = 3
    previous_steps: List[Dict[str, Any]] = field(default_factory=list)
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    failure_patterns: List[str] = field(default_factory=list)
    
    # 具体阶段的上下文
    reasoning_context: Optional[Dict[str, Any]] = None
    action_context: Optional[Dict[str, Any]] = None
    observation_context: Optional[Dict[str, Any]] = None
    reflection_context: Optional[Dict[str, Any]] = None


@dataclass
class ReActReasoningContext(ReActContext):
    """ReAct推理阶段上下文"""
    task_type: TaskType = TaskType.REACT_REASONING


@dataclass
class ReActObservationContext(ReActContext):
    """ReAct观察阶段上下文"""
    task_type: TaskType = TaskType.REACT_OBSERVATION
    tool_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ReActReflectionContext(ReActContext):
    """ReAct反思阶段上下文"""
    task_type: TaskType = TaskType.REACT_REFLECTION
    observation_results: List[Dict[str, Any]] = field(default_factory=list)
    overall_quality: float = 0.0
    meets_criteria: bool = False