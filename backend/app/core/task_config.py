"""
Task配置管理
提供Task执行和Agent编排的配置支持
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from app.models.task import ProcessingMode, AgentWorkflowType


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TaskExecutionConfig:
    """任务执行配置"""
    # 基本配置
    processing_mode: ProcessingMode = ProcessingMode.INTELLIGENT
    workflow_type: AgentWorkflowType = AgentWorkflowType.SIMPLE_REPORT
    priority: TaskPriority = TaskPriority.NORMAL
    
    # 超时配置
    execution_timeout_seconds: int = 600  # 10分钟
    agent_timeout_seconds: int = 120      # 2分钟每个Agent
    
    # 重试配置
    max_retries: int = 3
    retry_delay_seconds: int = 60
    
    # Agent配置
    max_context_tokens: int = 32000
    enable_compression: bool = True
    compression_threshold: float = 0.8
    
    # 输出配置
    output_format: str = "docx"
    include_charts: bool = True
    include_analysis: bool = True
    
    # 额外配置
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "processing_mode": self.processing_mode.value,
            "workflow_type": self.workflow_type.value,
            "priority": self.priority.value,
            "execution_timeout_seconds": self.execution_timeout_seconds,
            "agent_timeout_seconds": self.agent_timeout_seconds,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "max_context_tokens": self.max_context_tokens,
            "enable_compression": self.enable_compression,
            "compression_threshold": self.compression_threshold,
            "output_format": self.output_format,
            "include_charts": self.include_charts,
            "include_analysis": self.include_analysis,
            "custom_config": self.custom_config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskExecutionConfig":
        """从字典创建配置"""
        return cls(
            processing_mode=ProcessingMode(data.get("processing_mode", ProcessingMode.INTELLIGENT)),
            workflow_type=AgentWorkflowType(data.get("workflow_type", AgentWorkflowType.SIMPLE_REPORT)),
            priority=TaskPriority(data.get("priority", TaskPriority.NORMAL)),
            execution_timeout_seconds=data.get("execution_timeout_seconds", 600),
            agent_timeout_seconds=data.get("agent_timeout_seconds", 120),
            max_retries=data.get("max_retries", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 60),
            max_context_tokens=data.get("max_context_tokens", 32000),
            enable_compression=data.get("enable_compression", True),
            compression_threshold=data.get("compression_threshold", 0.8),
            output_format=data.get("output_format", "docx"),
            include_charts=data.get("include_charts", True),
            include_analysis=data.get("include_analysis", True),
            custom_config=data.get("custom_config", {})
        )


@dataclass
class AgentOrchestrationConfig:
    """Agent编排配置"""
    # 工作流配置
    parallel_execution: bool = False
    continue_on_error: bool = False
    
    # Agent选择策略
    auto_agent_selection: bool = True
    preferred_agents: Optional[list] = None
    excluded_agents: Optional[list] = None
    
    # 性能配置
    max_concurrent_agents: int = 3
    memory_limit_mb: int = 1024
    
    # 质量控制
    enable_result_validation: bool = True
    min_quality_score: float = 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "parallel_execution": self.parallel_execution,
            "continue_on_error": self.continue_on_error,
            "auto_agent_selection": self.auto_agent_selection,
            "preferred_agents": self.preferred_agents,
            "excluded_agents": self.excluded_agents,
            "max_concurrent_agents": self.max_concurrent_agents,
            "memory_limit_mb": self.memory_limit_mb,
            "enable_result_validation": self.enable_result_validation,
            "min_quality_score": self.min_quality_score
        }


class TaskConfigManager:
    """任务配置管理器"""
    
    _default_configs = {
        AgentWorkflowType.SIMPLE_REPORT: TaskExecutionConfig(
            workflow_type=AgentWorkflowType.SIMPLE_REPORT,
            execution_timeout_seconds=300,
            include_charts=False,
            include_analysis=False
        ),
        AgentWorkflowType.STATISTICAL_ANALYSIS: TaskExecutionConfig(
            workflow_type=AgentWorkflowType.STATISTICAL_ANALYSIS,
            execution_timeout_seconds=600,
            include_charts=True,
            include_analysis=True
        ),
        AgentWorkflowType.CHART_GENERATION: TaskExecutionConfig(
            workflow_type=AgentWorkflowType.CHART_GENERATION,
            execution_timeout_seconds=400,
            include_charts=True,
            include_analysis=False
        ),
        AgentWorkflowType.COMPREHENSIVE_ANALYSIS: TaskExecutionConfig(
            workflow_type=AgentWorkflowType.COMPREHENSIVE_ANALYSIS,
            execution_timeout_seconds=900,
            include_charts=True,
            include_analysis=True,
            max_context_tokens=64000
        )
    }
    
    @classmethod
    def get_default_config(cls, workflow_type: AgentWorkflowType) -> TaskExecutionConfig:
        """获取默认配置"""
        return cls._default_configs.get(workflow_type, cls._default_configs[AgentWorkflowType.SIMPLE_REPORT])
    
    @classmethod
    def create_config_from_task(cls, task_data: Dict[str, Any]) -> TaskExecutionConfig:
        """从任务数据创建配置"""
        workflow_type = AgentWorkflowType(task_data.get("workflow_type", AgentWorkflowType.SIMPLE_REPORT))
        
        # 获取默认配置
        config = cls.get_default_config(workflow_type)
        
        # 应用任务特定的配置
        if "orchestration_config" in task_data and task_data["orchestration_config"]:
            custom_config = task_data["orchestration_config"]
            for key, value in custom_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # 应用其他字段
        if "max_context_tokens" in task_data:
            config.max_context_tokens = task_data["max_context_tokens"]
        if "enable_compression" in task_data:
            config.enable_compression = task_data["enable_compression"]
        if "compression_threshold" in task_data:
            config.compression_threshold = task_data["compression_threshold"]
        
        return config
    
    @classmethod 
    def get_orchestration_config(cls, workflow_type: AgentWorkflowType) -> AgentOrchestrationConfig:
        """获取编排配置"""
        if workflow_type == AgentWorkflowType.COMPREHENSIVE_ANALYSIS:
            return AgentOrchestrationConfig(
                parallel_execution=True,
                continue_on_error=True,
                max_concurrent_agents=4
            )
        elif workflow_type == AgentWorkflowType.CHART_GENERATION:
            return AgentOrchestrationConfig(
                parallel_execution=False,
                continue_on_error=False,
                max_concurrent_agents=2
            )
        else:
            return AgentOrchestrationConfig()


# 全局配置管理器实例
task_config_manager = TaskConfigManager()