"""
Prompt构建器模块

提供fluent API风格的prompt构建器，
支持链式调用和动态参数配置
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from .context import (
    PromptContext, TaskType,
    SQLAnalysisContext, ContextUpdateContext, DataCompletionContext,
    ComplexityJudgeContext, OrchestrationContext,
    ReActReasoningContext, ReActObservationContext, ReActReflectionContext
)
from .factory import PromptFactory


class BasePromptBuilder:
    """基础prompt构建器"""
    
    def __init__(self, factory: PromptFactory = None):
        self._factory = factory or PromptFactory()
        self._context_data = {}
    
    def with_user(self, user_id: str) -> 'BasePromptBuilder':
        """设置用户ID"""
        self._context_data['user_id'] = user_id
        return self
    
    def with_session(self, session_id: str) -> 'BasePromptBuilder':
        """设置会话ID"""
        self._context_data['session_id'] = session_id
        return self
    
    def with_metadata(self, **metadata) -> 'BasePromptBuilder':
        """设置元数据"""
        if 'metadata' not in self._context_data:
            self._context_data['metadata'] = {}
        self._context_data['metadata'].update(metadata)
        return self


class SQLAnalysisPromptBuilder(BasePromptBuilder):
    """SQL分析prompt构建器"""
    
    def __init__(self, factory: PromptFactory = None):
        super().__init__(factory)
        self._context_data.update({
            'user_id': 'agent_system',
            'business_command': '',
            'requirements': '',
            'target_objective': '',
            'context_info': '',
            'data_source_info': None
        })
    
    def business_command(self, command: str) -> 'SQLAnalysisPromptBuilder':
        """设置业务命令"""
        self._context_data['business_command'] = command
        return self
    
    def requirements(self, requirements: str) -> 'SQLAnalysisPromptBuilder':
        """设置需求描述"""
        self._context_data['requirements'] = requirements
        return self
    
    def target_objective(self, objective: str) -> 'SQLAnalysisPromptBuilder':
        """设置目标"""
        self._context_data['target_objective'] = objective
        return self
    
    def context_info(self, info: str) -> 'SQLAnalysisPromptBuilder':
        """设置上下文信息"""
        self._context_data['context_info'] = info
        return self
    
    def data_source_info(self, info: str) -> 'SQLAnalysisPromptBuilder':
        """设置数据源信息"""
        self._context_data['data_source_info'] = info
        return self
    
    def build(self) -> str:
        """构建SQL分析prompt"""
        return self._factory.create_sql_analysis_prompt(**self._context_data)


class ContextUpdatePromptBuilder(BasePromptBuilder):
    """上下文更新prompt构建器"""
    
    def __init__(self, factory: PromptFactory = None):
        super().__init__(factory)
        self._context_data.update({
            'user_id': 'agent_system',
            'task_context': '',
            'current_task_info': '',
            'target_objective': '',
            'stored_placeholders': []
        })
    
    def task_context(self, context: str) -> 'ContextUpdatePromptBuilder':
        """设置任务上下文"""
        self._context_data['task_context'] = context
        return self
    
    def current_task_info(self, info: str) -> 'ContextUpdatePromptBuilder':
        """设置当前任务信息"""
        self._context_data['current_task_info'] = info
        return self
    
    def target_objective(self, objective: str) -> 'ContextUpdatePromptBuilder':
        """设置目标"""
        self._context_data['target_objective'] = objective
        return self
    
    def stored_placeholders(self, placeholders: List[Dict[str, str]]) -> 'ContextUpdatePromptBuilder':
        """设置已存储的占位符"""
        self._context_data['stored_placeholders'] = placeholders
        return self
    
    def add_placeholder(self, name: str, description: str) -> 'ContextUpdatePromptBuilder':
        """添加单个占位符"""
        self._context_data['stored_placeholders'].append({
            'name': name,
            'description': description
        })
        return self
    
    def build(self) -> str:
        """构建上下文更新prompt"""
        return self._factory.create_context_update_prompt(**self._context_data)


class DataCompletionPromptBuilder(BasePromptBuilder):
    """数据完成prompt构建器"""
    
    def __init__(self, factory: PromptFactory = None):
        super().__init__(factory)
        self._context_data.update({
            'user_id': 'agent_system',
            'placeholder_requirements': '',
            'template_section': '',
            'etl_data': [],
            'chart_generation_needed': False,
            'target_chart_type': None
        })
    
    def placeholder_requirements(self, requirements: str) -> 'DataCompletionPromptBuilder':
        """设置占位符要求"""
        self._context_data['placeholder_requirements'] = requirements
        return self
    
    def template_section(self, section: str) -> 'DataCompletionPromptBuilder':
        """设置模板段落"""
        self._context_data['template_section'] = section
        return self
    
    def etl_data(self, data: List[Dict[str, Any]]) -> 'DataCompletionPromptBuilder':
        """设置ETL数据"""
        self._context_data['etl_data'] = data
        return self
    
    def add_data_record(self, record: Dict[str, Any]) -> 'DataCompletionPromptBuilder':
        """添加单条数据记录"""
        self._context_data['etl_data'].append(record)
        return self
    
    def chart_generation_needed(self, needed: bool = True) -> 'DataCompletionPromptBuilder':
        """设置是否需要图表生成"""
        self._context_data['chart_generation_needed'] = needed
        return self
    
    def target_chart_type(self, chart_type: str) -> 'DataCompletionPromptBuilder':
        """设置目标图表类型"""
        self._context_data['target_chart_type'] = chart_type
        return self
    
    def build(self) -> str:
        """构建数据完成prompt"""
        return self._factory.create_data_completion_prompt(**self._context_data)


class ComplexityJudgePromptBuilder(BasePromptBuilder):
    """复杂度判断prompt构建器"""
    
    def __init__(self, factory: PromptFactory = None):
        super().__init__(factory)
        self._context_data.update({
            'user_id': 'agent_system',
            'orchestration_metadata': {},
            'current_step': {},
            'orchestration_chain': {},
            'context_accumulation': {},
            'dependency_analysis': {},
            'impact_assessment': {}
        })
    
    def orchestration_metadata(self, metadata: Dict[str, Any]) -> 'ComplexityJudgePromptBuilder':
        """设置编排元数据"""
        self._context_data['orchestration_metadata'] = metadata
        return self
    
    def current_step(self, step_info: Dict[str, Any]) -> 'ComplexityJudgePromptBuilder':
        """设置当前步骤信息"""
        self._context_data['current_step'] = step_info
        return self
    
    def orchestration_chain(self, chain_info: Dict[str, Any]) -> 'ComplexityJudgePromptBuilder':
        """设置编排链信息"""
        self._context_data['orchestration_chain'] = chain_info
        return self
    
    def context_accumulation(self, accumulation: Dict[str, Any]) -> 'ComplexityJudgePromptBuilder':
        """设置上下文累积"""
        self._context_data['context_accumulation'] = accumulation
        return self
    
    def dependency_analysis(self, analysis: Dict[str, Any]) -> 'ComplexityJudgePromptBuilder':
        """设置依赖分析"""
        self._context_data['dependency_analysis'] = analysis
        return self
    
    def impact_assessment(self, assessment: Dict[str, Any]) -> 'ComplexityJudgePromptBuilder':
        """设置影响评估"""
        self._context_data['impact_assessment'] = assessment
        return self
    
    def with_step_complexity(self, step_type: str, complexity_factors: List[str]) -> 'ComplexityJudgePromptBuilder':
        """设置步骤复杂度因子"""
        self._context_data['current_step'].update({
            'step_type': step_type,
            'complexity_factors': complexity_factors
        })
        return self
    
    def with_chain_length(self, length: int, position: int) -> 'ComplexityJudgePromptBuilder':
        """设置编排链长度和位置"""
        self._context_data['orchestration_chain'].update({
            'total_length': length,
            'current_position': position,
            'completion_ratio': position / length if length > 0 else 0.0
        })
        return self
    
    def build(self) -> str:
        """构建复杂度判断prompt"""
        return self._factory.create_complexity_judge_prompt(**self._context_data)


class ReActReasoningPromptBuilder(BasePromptBuilder):
    """ReAct推理prompt构建器"""
    
    def __init__(self, factory: PromptFactory = None):
        super().__init__(factory)
        self._context_data.update({
            'user_id': 'agent_system',
            'objective': '',
            'current_attempt': 1,
            'max_attempts': 3,
            'previous_steps': [],
            'success_criteria': {},
            'failure_patterns': []
        })
    
    def objective(self, objective: str) -> 'ReActReasoningPromptBuilder':
        """设置任务目标"""
        self._context_data['objective'] = objective
        return self
    
    def current_attempt(self, attempt: int) -> 'ReActReasoningPromptBuilder':
        """设置当前尝试次数"""
        self._context_data['current_attempt'] = attempt
        return self
    
    def max_attempts(self, max_attempts: int) -> 'ReActReasoningPromptBuilder':
        """设置最大尝试次数"""
        self._context_data['max_attempts'] = max_attempts
        return self
    
    def previous_steps(self, steps: List[Dict[str, Any]]) -> 'ReActReasoningPromptBuilder':
        """设置前序步骤"""
        self._context_data['previous_steps'] = steps
        return self
    
    def add_previous_step(self, step: Dict[str, Any]) -> 'ReActReasoningPromptBuilder':
        """添加前序步骤"""
        self._context_data['previous_steps'].append(step)
        return self
    
    def success_criteria(self, criteria: Dict[str, Any]) -> 'ReActReasoningPromptBuilder':
        """设置成功标准"""
        self._context_data['success_criteria'] = criteria
        return self
    
    def add_success_criterion(self, name: str, description: str, weight: float = 1.0) -> 'ReActReasoningPromptBuilder':
        """添加成功标准"""
        self._context_data['success_criteria'][name] = {
            'description': description,
            'weight': weight
        }
        return self
    
    def failure_patterns(self, patterns: List[str]) -> 'ReActReasoningPromptBuilder':
        """设置失败模式"""
        self._context_data['failure_patterns'] = patterns
        return self
    
    def add_failure_pattern(self, pattern: str) -> 'ReActReasoningPromptBuilder':
        """添加失败模式"""
        self._context_data['failure_patterns'].append(pattern)
        return self
    
    def build(self) -> str:
        """构建ReAct推理prompt"""
        return self._factory.create_react_reasoning_prompt(**self._context_data)


class ReActObservationPromptBuilder(BasePromptBuilder):
    """ReAct观察prompt构建器"""
    
    def __init__(self, factory: PromptFactory = None):
        super().__init__(factory)
        self._context_data.update({
            'user_id': 'agent_system',
            'objective': '',
            'tool_results': [],
            'success_criteria': {},
            'current_attempt': 1,
            'max_attempts': 3
        })
    
    def objective(self, objective: str) -> 'ReActObservationPromptBuilder':
        """设置任务目标"""
        self._context_data['objective'] = objective
        return self
    
    def tool_results(self, results: List[Dict[str, Any]]) -> 'ReActObservationPromptBuilder':
        """设置工具执行结果"""
        self._context_data['tool_results'] = results
        return self
    
    def add_tool_result(self, tool_name: str, success: bool, result: Any = None, error: str = None) -> 'ReActObservationPromptBuilder':
        """添加工具执行结果"""
        tool_result = {
            'tool_name': tool_name,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        if success and result is not None:
            tool_result['result'] = result
        if not success and error:
            tool_result['error'] = error
            
        self._context_data['tool_results'].append(tool_result)
        return self
    
    def success_criteria(self, criteria: Dict[str, Any]) -> 'ReActObservationPromptBuilder':
        """设置成功标准"""
        self._context_data['success_criteria'] = criteria
        return self
    
    def current_attempt(self, attempt: int) -> 'ReActObservationPromptBuilder':
        """设置当前尝试次数"""
        self._context_data['current_attempt'] = attempt
        return self
    
    def max_attempts(self, max_attempts: int) -> 'ReActObservationPromptBuilder':
        """设置最大尝试次数"""
        self._context_data['max_attempts'] = max_attempts
        return self
    
    def build(self) -> str:
        """构建ReAct观察prompt"""
        return self._factory.create_react_observation_prompt(**self._context_data)


class ReActReflectionPromptBuilder(BasePromptBuilder):
    """ReAct反思prompt构建器"""
    
    def __init__(self, factory: PromptFactory = None):
        super().__init__(factory)
        self._context_data.update({
            'user_id': 'agent_system',
            'objective': '',
            'observation_results': [],
            'overall_quality': 0.0,
            'meets_criteria': False,
            'current_attempt': 1,
            'max_attempts': 3,
            'success_criteria': {}
        })
    
    def objective(self, objective: str) -> 'ReActReflectionPromptBuilder':
        """设置任务目标"""
        self._context_data['objective'] = objective
        return self
    
    def observation_results(self, results: List[Dict[str, Any]]) -> 'ReActReflectionPromptBuilder':
        """设置观察结果"""
        self._context_data['observation_results'] = results
        return self
    
    def add_observation_result(self, item: str, quality_score: float, meets_criteria: bool, 
                              issues: List[str] = None, suggestions: List[str] = None) -> 'ReActReflectionPromptBuilder':
        """添加观察结果"""
        result = {
            'item': item,
            'quality_score': quality_score,
            'meets_criteria': meets_criteria
        }
        
        if issues:
            result['issues'] = issues
        if suggestions:
            result['suggestions'] = suggestions
            
        self._context_data['observation_results'].append(result)
        return self
    
    def overall_quality(self, quality: float) -> 'ReActReflectionPromptBuilder':
        """设置整体质量分数"""
        self._context_data['overall_quality'] = max(0.0, min(1.0, quality))
        return self
    
    def meets_criteria(self, meets: bool) -> 'ReActReflectionPromptBuilder':
        """设置是否符合标准"""
        self._context_data['meets_criteria'] = meets
        return self
    
    def current_attempt(self, attempt: int) -> 'ReActReflectionPromptBuilder':
        """设置当前尝试次数"""
        self._context_data['current_attempt'] = attempt
        return self
    
    def max_attempts(self, max_attempts: int) -> 'ReActReflectionPromptBuilder':
        """设置最大尝试次数"""
        self._context_data['max_attempts'] = max_attempts
        return self
    
    def success_criteria(self, criteria: Dict[str, Any]) -> 'ReActReflectionPromptBuilder':
        """设置成功标准"""
        self._context_data['success_criteria'] = criteria
        return self
    
    def build(self) -> str:
        """构建ReAct反思prompt"""
        return self._factory.create_react_reflection_prompt(**self._context_data)


# ==================== 便利工厂函数 ====================

def sql_analysis_prompt(factory: PromptFactory = None) -> SQLAnalysisPromptBuilder:
    """创建SQL分析prompt构建器"""
    return SQLAnalysisPromptBuilder(factory)

def context_update_prompt(factory: PromptFactory = None) -> ContextUpdatePromptBuilder:
    """创建上下文更新prompt构建器"""
    return ContextUpdatePromptBuilder(factory)

def data_completion_prompt(factory: PromptFactory = None) -> DataCompletionPromptBuilder:
    """创建数据完成prompt构建器"""
    return DataCompletionPromptBuilder(factory)

def complexity_judge_prompt(factory: PromptFactory = None) -> ComplexityJudgePromptBuilder:
    """创建复杂度判断prompt构建器"""
    return ComplexityJudgePromptBuilder(factory)

def react_reasoning_prompt(factory: PromptFactory = None) -> ReActReasoningPromptBuilder:
    """创建ReAct推理prompt构建器"""
    return ReActReasoningPromptBuilder(factory)

def react_observation_prompt(factory: PromptFactory = None) -> ReActObservationPromptBuilder:
    """创建ReAct观察prompt构建器"""
    return ReActObservationPromptBuilder(factory)

def react_reflection_prompt(factory: PromptFactory = None) -> ReActReflectionPromptBuilder:
    """创建ReAct反思prompt构建器"""
    return ReActReflectionPromptBuilder(factory)