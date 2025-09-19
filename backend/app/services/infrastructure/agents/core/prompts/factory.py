"""
Prompt工厂模式

提供简洁的接口来创建各种类型的prompt，
隐藏复杂的上下文构建逻辑
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from .context import (
    PromptContext, TaskType,
    SQLAnalysisContext, ContextUpdateContext, DataCompletionContext,
    ComplexityJudgeContext, OrchestrationContext,
    ReActReasoningContext, ReActObservationContext, ReActReflectionContext
)
from .templates import (
    AnalysisPromptTemplate, UpdatePromptTemplate, CompletionPromptTemplate,
    ComplexityJudgeTemplate, ReActReasoningTemplate, 
    ReActObservationTemplate, ReActReflectionTemplate
)


class PromptFactory:
    """
    Prompt工厂 - 提供简洁优雅的prompt创建接口
    
    隐藏复杂的上下文构建，对外提供简单的方法调用
    """
    
    def __init__(self):
        # 模板注册表
        self._templates = {
            TaskType.SQL_ANALYSIS: AnalysisPromptTemplate(),
            TaskType.CONTEXT_UPDATE: UpdatePromptTemplate(),
            TaskType.DATA_COMPLETION: CompletionPromptTemplate(),
            TaskType.COMPLEXITY_JUDGE: ComplexityJudgeTemplate(),
            TaskType.REACT_REASONING: ReActReasoningTemplate(),
            TaskType.REACT_OBSERVATION: ReActObservationTemplate(),
            TaskType.REACT_REFLECTION: ReActReflectionTemplate()
        }
    
    # ==================== 业务流程Prompt ====================
    
    def create_sql_analysis_prompt(
        self,
        business_command: str,
        requirements: str,
        target_objective: str,
        context_info: str = "",
        data_source_info: Optional[str] = None,
        user_id: str = "agent_system"
    ) -> str:
        """创建SQL分析prompt - 简洁接口"""
        
        context = SQLAnalysisContext(
            objective=target_objective,
            user_id=user_id,
            business_command=business_command,
            requirements=requirements,
            target_objective=target_objective,
            context_info=context_info,
            data_source_info=data_source_info
        )
        
        return self._templates[TaskType.SQL_ANALYSIS].build(context)
    
    def create_context_update_prompt(
        self,
        task_context: str,
        current_task_info: str,
        target_objective: str,
        stored_placeholders: List[Dict[str, str]],
        user_id: str = "agent_system"
    ) -> str:
        """创建上下文更新分析prompt - 简洁接口"""
        
        context = ContextUpdateContext(
            objective=target_objective,
            user_id=user_id,
            task_context=task_context,
            current_task_info=current_task_info,
            target_objective=target_objective,
            stored_placeholders=stored_placeholders
        )
        
        return self._templates[TaskType.CONTEXT_UPDATE].build(context)
    
    def create_data_completion_prompt(
        self,
        placeholder_requirements: str,
        template_section: str,
        etl_data: List[Dict[str, Any]],
        chart_generation_needed: bool = False,
        target_chart_type: Optional[str] = None,
        user_id: str = "agent_system"
    ) -> str:
        """创建数据完成prompt - 简洁接口"""
        
        context = DataCompletionContext(
            objective="完善占位符内容",
            user_id=user_id,
            placeholder_requirements=placeholder_requirements,
            template_section=template_section,
            etl_data=etl_data,
            chart_generation_needed=chart_generation_needed,
            target_chart_type=target_chart_type
        )
        
        return self._templates[TaskType.DATA_COMPLETION].build(context)
    
    # ==================== 编排复杂度判断Prompt ====================
    
    def create_complexity_judge_prompt(
        self,
        orchestration_metadata: Optional[Dict[str, Any]] = None,
        current_step: Optional[Dict[str, Any]] = None,
        orchestration_chain: Optional[Dict[str, Any]] = None,
        context_accumulation: Optional[Dict[str, Any]] = None,
        dependency_analysis: Optional[Dict[str, Any]] = None,
        impact_assessment: Optional[Dict[str, Any]] = None,
        user_id: str = "agent_system"
    ) -> str:
        """创建编排复杂度判断prompt - 简洁接口"""
        
        orchestration_context = OrchestrationContext(
            orchestration_metadata=orchestration_metadata or {},
            current_step=current_step or {},
            orchestration_chain=orchestration_chain or {},
            context_accumulation=context_accumulation or {},
            dependency_analysis=dependency_analysis or {},
            impact_assessment=impact_assessment or {}
        )
        
        context = ComplexityJudgeContext(
            objective="判断编排复杂度",
            user_id=user_id,
            orchestration_context=orchestration_context
        )
        
        return self._templates[TaskType.COMPLEXITY_JUDGE].build(context)
    
    # ==================== ReAct阶段Prompt ====================
    
    def create_react_reasoning_prompt(
        self,
        objective: str,
        current_attempt: int = 1,
        max_attempts: int = 3,
        previous_steps: Optional[List[Dict[str, Any]]] = None,
        success_criteria: Optional[Dict[str, Any]] = None,
        failure_patterns: Optional[List[str]] = None,
        user_id: str = "agent_system"
    ) -> str:
        """创建ReAct推理prompt - 简洁接口"""
        
        context = ReActReasoningContext(
            objective=objective,
            user_id=user_id,
            current_attempt=current_attempt,
            max_attempts=max_attempts,
            previous_steps=previous_steps or [],
            success_criteria=success_criteria or {},
            failure_patterns=failure_patterns or []
        )
        
        return self._templates[TaskType.REACT_REASONING].build(context)
    
    def create_react_observation_prompt(
        self,
        objective: str,
        tool_results: List[Dict[str, Any]],
        success_criteria: Optional[Dict[str, Any]] = None,
        current_attempt: int = 1,
        max_attempts: int = 3,
        user_id: str = "agent_system"
    ) -> str:
        """创建ReAct观察prompt - 简洁接口"""
        
        context = ReActObservationContext(
            objective=objective,
            user_id=user_id,
            current_attempt=current_attempt,
            max_attempts=max_attempts,
            success_criteria=success_criteria or {},
            tool_results=tool_results
        )
        
        return self._templates[TaskType.REACT_OBSERVATION].build(context)
    
    def create_react_reflection_prompt(
        self,
        objective: str,
        observation_results: List[Dict[str, Any]],
        overall_quality: float,
        meets_criteria: bool,
        current_attempt: int = 1,
        max_attempts: int = 3,
        success_criteria: Optional[Dict[str, Any]] = None,
        user_id: str = "agent_system"
    ) -> str:
        """创建ReAct反思prompt - 简洁接口"""
        
        context = ReActReflectionContext(
            objective=objective,
            user_id=user_id,
            current_attempt=current_attempt,
            max_attempts=max_attempts,
            success_criteria=success_criteria or {},
            observation_results=observation_results,
            overall_quality=overall_quality,
            meets_criteria=meets_criteria
        )
        
        return self._templates[TaskType.REACT_REFLECTION].build(context)
    
    # ==================== 快速创建方法 ====================
    
    def sql_analysis(self, business_command: str, requirements: str, target_objective: str, **kwargs) -> str:
        """快速创建SQL分析prompt"""
        return self.create_sql_analysis_prompt(business_command, requirements, target_objective, **kwargs)
    
    def context_update(self, task_context: str, current_task_info: str, target_objective: str, stored_placeholders: List[Dict], **kwargs) -> str:
        """快速创建上下文更新prompt"""
        return self.create_context_update_prompt(task_context, current_task_info, target_objective, stored_placeholders, **kwargs)
    
    def complexity_judge(self, **orchestration_context) -> str:
        """快速创建复杂度判断prompt"""
        return self.create_complexity_judge_prompt(**orchestration_context)
    
    def react_reasoning(self, objective: str, **kwargs) -> str:
        """快速创建ReAct推理prompt"""
        return self.create_react_reasoning_prompt(objective, **kwargs)
    
    def react_observation(self, objective: str, tool_results: List[Dict], **kwargs) -> str:
        """快速创建ReAct观察prompt"""
        return self.create_react_observation_prompt(objective, tool_results, **kwargs)
    
    def react_reflection(self, objective: str, observation_results: List[Dict], overall_quality: float, meets_criteria: bool, **kwargs) -> str:
        """快速创建ReAct反思prompt"""
        return self.create_react_reflection_prompt(objective, observation_results, overall_quality, meets_criteria, **kwargs)
    
    # ==================== 扩展接口 ====================
    
    def register_template(self, task_type: TaskType, template):
        """注册新的prompt模板"""
        self._templates[task_type] = template
    
    def get_supported_task_types(self) -> List[TaskType]:
        """获取支持的任务类型"""
        return list(self._templates.keys())
    
    def build_with_context(self, task_type: TaskType, context: PromptContext) -> str:
        """使用上下文对象构建prompt"""
        if task_type not in self._templates:
            raise ValueError(f"Unsupported task type: {task_type}")
        
        return self._templates[task_type].build(context)