"""
LLM执行工具 - 桥接agents和LLM服务
支持自主模型选择和智能任务执行
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

from ..core.base import (
    StreamingAgentTool, ToolDefinition, ToolResult, 
    ToolExecutionContext, ToolCategory, ToolPriority, ToolPermission,
    ValidationError, ExecutionError, create_tool_definition
)
from ..core.permissions import SecurityLevel, ResourceType

from app.services.infrastructure.llm import (
    # 新的统一接口
    get_llm_manager, select_best_model_for_user,
    ask_agent_for_user, get_user_available_models,
    
    # 必要的类型定义
    TaskRequirement, TaskComplexity, ProcessingStep, StepContext
)

logger = logging.getLogger(__name__)


class LLMTaskType(Enum):
    """LLM任务类型"""
    REASONING = "reasoning"           # 逻辑推理
    ANALYSIS = "analysis"             # 数据分析
    GENERATION = "generation"         # 内容生成
    SUMMARIZATION = "summarization"   # 摘要总结
    TRANSLATION = "translation"       # 翻译转换
    CODE = "code"                     # 代码相关
    DEBUGGING = "debugging"          # 调试修复


class LLMExecutionInput(BaseModel):
    """LLM执行输入模式"""
    prompt: str = Field(..., min_length=10, max_length=10000, description="任务提示词")
    task_type: LLMTaskType = Field(default=LLMTaskType.REASONING, description="任务类型")
    context: Optional[Dict[str, Any]] = Field(None, description="执行上下文信息")
    constraints: Optional[List[str]] = Field(None, description="约束条件")
    quality_requirement: str = Field(default="balanced", description="质量要求: balanced, high, critical")
    speed_requirement: str = Field(default="normal", description="速度要求: fast, normal, slow")
    cost_sensitivity: str = Field(default="medium", description="成本敏感度: low, medium, high")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    temperature: Optional[float] = Field(None, description="温度参数")

    @validator('quality_requirement')
    def validate_quality(cls, v):
        allowed = ['balanced', 'high', 'critical']
        if v not in allowed:
            raise ValueError(f"质量要求必须是以下之一: {allowed}")
        return v

    @validator('speed_requirement')
    def validate_speed(cls, v):
        allowed = ['fast', 'normal', 'slow']
        if v not in allowed:
            raise ValueError(f"速度要求必须是以下之一: {allowed}")
        return v

    @validator('cost_sensitivity')
    def validate_cost(cls, v):
        allowed = ['low', 'medium', 'high']
        if v not in allowed:
            raise ValueError(f"成本敏感度必须是以下之一: {allowed}")
        return v


class LLMExecutionTool(StreamingAgentTool):
    """LLM执行工具 - 智能模型选择和任务执行"""
    
    def __init__(self):
        definition = create_tool_definition(
            name="llm_execution_tool",
            description="智能LLM任务执行，支持自主模型选择和复杂任务处理",
            category=ToolCategory.AI,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.READ_ONLY],
            input_schema=LLMExecutionInput,
            is_read_only=True,
            supports_streaming=True,
            typical_execution_time_ms=15000,
            examples=[
                {
                    "prompt": "分析这个SQL查询的性能问题并提出优化建议",
                    "task_type": "analysis",
                    "quality_requirement": "high",
                    "context": {"sql": "SELECT * FROM large_table WHERE condition = 'value'"}
                },
                {
                    "prompt": "生成一个关于机器学习模型选择的详细报告",
                    "task_type": "generation",
                    "quality_requirement": "critical",
                    "cost_sensitivity": "low"
                }
            ],
            limitations=[
                "依赖配置的LLM服务可用性",
                "复杂任务可能需要多次迭代",
                "成本敏感的任务可能选择较低性能的模型"
            ]
        )
        super().__init__(definition)
        
        self.model_executor = get_model_executor()
        self.step_selector = get_step_based_model_selector()
        
        # 任务类型到处理步骤的映射
        self.task_step_mapping = {
            LLMTaskType.REASONING: ProcessingStep.GENERAL_REASONING,
            LLMTaskType.ANALYSIS: ProcessingStep.DATA_SOURCE_ANALYSIS,
            LLMTaskType.GENERATION: ProcessingStep.TASK_SUPPLEMENT,
            LLMTaskType.SUMMARIZATION: ProcessingStep.CONTEXT_COMPRESSION,
            LLMTaskType.TRANSLATION: ProcessingStep.GENERAL_REASONING,
            LLMTaskType.CODE: ProcessingStep.SQL_GENERATION,
            LLMTaskType.DEBUGGING: ProcessingStep.ERROR_HANDLING
        }
        
        # 质量要求到复杂度的映射
        self.quality_complexity_mapping = {
            "balanced": TaskComplexity.MEDIUM,
            "high": TaskComplexity.HIGH,
            "critical": TaskComplexity.CRITICAL
        }
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """验证LLM执行输入"""
        try:
            validated = LLMExecutionInput(**input_data)
            return validated.dict()
        except Exception as e:
            raise ValidationError(f"LLM执行输入无效: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """检查LLM执行权限"""
        return ToolPermission.READ_ONLY in context.permissions
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """执行LLM任务并流式传输进度"""
        
        try:
            # 阶段1: 任务分析和模型选择
            yield await self.stream_progress({
                'status': 'analyzing',
                'message': '正在分析任务需求...',
                'progress': 10
            }, context)
            
            # 构建任务需求
            task_requirement = self._build_task_requirement(input_data)
            
            # 选择处理步骤
            step_context = self._build_step_context(input_data, context)
            model_selection = self.step_selector.select_model_for_step(step_context)
            
            yield await self.stream_progress({
                'status': 'model_selection',
                'message': f'选择模型: {model_selection.model_type} ({model_selection.reason})',
                'progress': 20,
                'model_info': {
                    'type': model_selection.model_type,
                    'complexity': model_selection.complexity.value,
                    'cost_level': model_selection.cost_level,
                    'quality_level': model_selection.quality_level
                }
            }, context)
            
            # 阶段2: LLM执行
            yield await self.stream_progress({
                'status': 'executing',
                'message': '正在执行LLM任务...',
                'progress': 30
            }, context)
            
            # 构建完整的提示词
            full_prompt = self._build_full_prompt(input_data, context)
            
            # 执行LLM调用
            llm_result = await self.model_executor.execute_with_auto_selection(
                user_id=context.user_id or "system",
                prompt=full_prompt,
                task_requirement=task_requirement,
                max_tokens=input_data.get('max_tokens'),
                temperature=input_data.get('temperature')
            )
            
            if not llm_result.get("success"):
                raise ExecutionError(f"LLM执行失败: {llm_result.get('error')}", tool_name=self.name)
            
            # 阶段3: 结果处理
            yield await self.stream_progress({
                'status': 'processing',
                'message': '正在处理LLM结果...',
                'progress': 80
            }, context)
            
            # 构建最终结果
            result_data = self._build_result_data(llm_result, input_data, model_selection)
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"LLM执行工具失败: {e}", tool_name=self.name)
    
    def _build_task_requirement(self, input_data: Dict[str, Any]) -> TaskRequirement:
        """构建任务需求"""
        quality = input_data.get('quality_requirement', 'balanced')
        speed = input_data.get('speed_requirement', 'normal')
        cost = input_data.get('cost_sensitivity', 'medium')
        
        return TaskRequirement(
            requires_thinking=quality in ['high', 'critical'],
            cost_sensitive=cost == 'high',
            speed_priority=speed == 'fast'
        )
    
    def _build_step_context(self, input_data: Dict[str, Any], tool_context: ToolExecutionContext) -> StepContext:
        """构建步骤上下文"""
        task_type = LLMTaskType(input_data.get('task_type', LLMTaskType.REASONING))
        quality = input_data.get('quality_requirement', 'balanced')
        
        step = self.task_step_mapping.get(task_type, ProcessingStep.GENERAL_REASONING)
        complexity = self.quality_complexity_mapping.get(quality, TaskComplexity.MEDIUM)
        
        return StepContext(
            step=step,
            task_description=input_data.get('prompt', '')[:200],  # 截断长描述
            custom_complexity=complexity,
            time_pressure=input_data.get('speed_requirement') == 'fast',
            data_complexity='high' if input_data.get('context') else 'medium'
        )
    
    def _build_full_prompt(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> str:
        """构建完整的提示词"""
        base_prompt = input_data['prompt']
        
        # 添加上下文信息
        if input_data.get('context'):
            context_str = json.dumps(input_data['context'], ensure_ascii=False, indent=2)
            base_prompt = f"上下文信息:\n{context_str}\n\n任务要求:\n{base_prompt}"
        
        # 添加约束条件
        if input_data.get('constraints'):
            constraints_str = "\n".join([f"- {c}" for c in input_data['constraints']])
            base_prompt = f"{base_prompt}\n\n约束条件:\n{constraints_str}"
        
        # 添加工具执行上下文（如果可用）
        if hasattr(context, 'execution_context') and context.execution_context:
            tool_context = f"\n\n工具执行上下文: {json.dumps(context.execution_context, ensure_ascii=False)}"
            base_prompt += tool_context
        
        return base_prompt
    
    def _build_result_data(self, llm_result: Dict[str, Any], input_data: Dict[str, Any], 
                          model_selection: Any) -> Dict[str, Any]:
        """构建结果数据"""
        return {
            'operation': 'llm_execution',
            'task_type': input_data.get('task_type'),
            'prompt': input_data.get('prompt'),
            'result': llm_result.get('result', ''),
            'model_info': llm_result.get('selected_model', {}),
            'performance_metrics': {
                'tokens_used': llm_result.get('tokens_used', 0),
                'response_time_ms': llm_result.get('response_time_ms', 0),
                'execution_time': datetime.now().isoformat()
            },
            'selection_metrics': {
                'model_type': model_selection.model_type,
                'complexity': model_selection.complexity.value,
                'cost_level': model_selection.cost_level,
                'quality_level': model_selection.quality_level,
                'reasoning': model_selection.reason
            },
            'constraints_applied': input_data.get('constraints', []),
            'quality_requirement': input_data.get('quality_requirement'),
            'context_used': bool(input_data.get('context'))
        }


# 便捷函数
def create_llm_execution_tool() -> LLMExecutionTool:
    """创建LLM执行工具实例"""
    return LLMExecutionTool()


__all__ = ["LLMExecutionTool", "LLMTaskType", "create_llm_execution_tool"]