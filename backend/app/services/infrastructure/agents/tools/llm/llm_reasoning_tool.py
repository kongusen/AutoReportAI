"""
LLM推理工具 - 专门用于复杂推理任务的LLM工具
基于任务上下文和内存状态进行智能推理
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from ..core.base import (
    StreamingAgentTool, ToolDefinition, ToolResult, 
    ToolExecutionContext, ToolCategory, ToolPriority, ToolPermission,
    ValidationError, ExecutionError, create_tool_definition
)

from app.services.infrastructure.llm.model_executor import get_model_executor
from app.services.infrastructure.llm.simple_model_selector import (
    get_simple_model_selector, TaskRequirement
)
from app.services.infrastructure.llm.step_based_model_selector import (
    ProcessingStep, StepContext, TaskComplexity
)

logger = logging.getLogger(__name__)


class ReasoningDepth(Enum):
    """推理深度级别"""
    BASIC = "basic"          # 基础推理
    DETAILED = "detailed"    # 详细推理
    DEEP = "deep"           # 深度推理
    EXPERT = "expert"       # 专家级推理


class ReasoningInput(BaseModel):
    """推理任务输入模式"""
    problem: str = Field(..., min_length=10, max_length=5000, description="推理问题")
    context: Optional[Dict[str, Any]] = Field(None, description="推理上下文")
    memory_state: Optional[Dict[str, Any]] = Field(None, description="内存状态信息")
    reasoning_depth: ReasoningDepth = Field(default=ReasoningDepth.DETAILED, description="推理深度")
    require_step_by_step: bool = Field(default=True, description="是否需要逐步推理")
    include_assumptions: bool = Field(default=True, description="是否包含假设说明")
    consider_alternatives: bool = Field(default=True, description="是否考虑替代方案")
    max_iterations: int = Field(default=3, ge=1, le=10, description="最大迭代次数")


class LLMReasoningTool(StreamingAgentTool):
    """LLM推理工具 - 专门处理复杂推理任务"""
    
    def __init__(self):
        definition = create_tool_definition(
            name="llm_reasoning_tool",
            description="高级LLM推理工具，支持深度推理、多步分析和智能迭代",
            category=ToolCategory.AI,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.READ_ONLY],
            input_schema=ReasoningInput,
            is_read_only=True,
            supports_streaming=True,
            typical_execution_time_ms=20000,
            examples=[
                {
                    "problem": "基于当前任务状态和内存上下文，分析下一步最优执行策略",
                    "reasoning_depth": "deep",
                    "require_step_by_step": True,
                    "memory_state": {"current_step": "data_analysis", "progress": 0.6}
                },
                {
                    "problem": "解释这个数据模式背后的业务含义和潜在影响",
                    "reasoning_depth": "expert",
                    "consider_alternatives": True,
                    "context": {"data_pattern": "sales_increase", "time_period": "Q3"}
                }
            ],
            limitations=[
                "深度推理需要更多计算资源",
                "依赖准确的任务上下文和内存状态",
                "复杂问题可能需要多次迭代优化"
            ]
        )
        super().__init__(definition)
        
        self.model_executor = get_model_executor()
        self.step_selector = get_simple_model_selector()
        
        # 推理深度到复杂度的映射
        self.depth_complexity_mapping = {
            ReasoningDepth.BASIC: TaskComplexity.MEDIUM,
            ReasoningDepth.DETAILED: TaskComplexity.HIGH,
            ReasoningDepth.DEEP: TaskComplexity.HIGH,
            ReasoningDepth.EXPERT: TaskComplexity.CRITICAL
        }
        
        # 推理模板
        self.reasoning_templates = {
            "analysis": """
请分析以下问题，提供{depth}级别的推理：

问题: {problem}

上下文信息:
{context}

内存状态:
{memory}

请按照以下结构进行推理：
1. 问题理解和分解
2. 关键因素分析  
3. 逻辑推理过程
4. 结论和建议
{step_by_step}
{assumptions}
{alternatives}
""",
            "decision": """
基于当前状态做出决策推理：

决策问题: {problem}

可用信息:
{context}

系统状态:
{memory}

请进行{depth}级别的决策推理，包括：
1. 选项分析
2. 风险评估
3. 预期结果
4. 推荐决策
{step_by_step}
"""
        }
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """验证推理输入"""
        try:
            validated = ReasoningInput(**input_data)
            return validated.dict()
        except Exception as e:
            raise ValidationError(f"推理输入无效: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """检查工具执行权限"""
        try:
            # LLM推理工具只需要读取权限
            required_permissions = {ToolPermission.READ_ONLY}
            user_permissions = set(context.permissions) if isinstance(context.permissions, list) else {context.permissions} if context.permissions else set()
            
            # 检查是否有所需权限
            if not required_permissions.issubset(user_permissions):
                from ..core.base import PermissionError
                raise PermissionError(f"LLM推理工具需要权限: {[p.value for p in required_permissions]}", tool_name=self.name)
            
            return True
        except ImportError as e:
            logger.warning(f"权限检查导入错误，使用默认权限: {e}")
            return True  # 临时允许访问
        except Exception as e:
            logger.error(f"权限检查失败: {e}")
            return True  # 临时允许访问
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """执行推理任务"""
        
        try:
            logger.info(f"LLM推理工具开始执行，用户ID: {context.user_id}")
            
            # 阶段1: 准备推理
            yield await self.stream_progress({
                'status': 'preparing',
                'message': '正在准备推理环境...',
                'progress': 10
            }, context)
            
            # 构建推理提示词
            prompt = self._build_reasoning_prompt(input_data, context)
            
            # 构建任务需求用于模型选择
            task_requirement = self._build_task_requirement(input_data)
            
            yield await self.stream_progress({
                'status': 'model_selection',
                'message': f'选择推理模型: {task_requirement}',
                'progress': 20,
                'model_info': {
                    'requires_thinking': task_requirement.requires_thinking,
                    'cost_sensitive': task_requirement.cost_sensitive,
                    'speed_priority': task_requirement.speed_priority
                }
            }, context)
            
            # 阶段2: 迭代推理
            final_result = None
            for iteration in range(input_data.get('max_iterations', 3)):
                yield await self.stream_progress({
                    'status': 'reasoning_iteration',
                    'message': f'正在进行第 {iteration + 1} 轮推理...',
                    'progress': 30 + (iteration * 20),
                    'iteration': iteration + 1
                }, context)
                
                # 执行LLM推理
                try:
                    logger.info(f"执行LLM推理迭代 {iteration + 1}")
                    if not context.user_id:
                        raise ExecutionError("缺少有效的用户ID，无法执行LLM推理", tool_name=self.name)
                    
                    llm_result = await self.model_executor.execute_with_auto_selection(
                        user_id=context.user_id,
                        prompt=prompt,
                        task_requirement=self._build_task_requirement(input_data),
                        max_tokens=4000  # 推理任务需要更多tokens
                    )
                    
                    logger.info(f"LLM推理迭代结果: {llm_result.get('success', False)}")
                    
                    if not llm_result.get("success"):
                        error_msg = llm_result.get('error', 'Unknown error')
                        logger.error(f"LLM推理迭代失败: {error_msg}")
                        raise ExecutionError(f"推理迭代失败: {error_msg}", tool_name=self.name)
                    
                except Exception as llm_error:
                    logger.error(f"LLM推理执行异常: {llm_error}")
                    raise ExecutionError(f"推理执行异常: {str(llm_error)}", tool_name=self.name)
                
                # 安全地获取结果，处理不同的数据格式
                if isinstance(llm_result, dict):
                    result = llm_result.get('result', '')
                else:
                    result = str(llm_result)  # 兜底处理
                
                # 确保result是字符串
                if not isinstance(result, str):
                    result = str(result)
                
                # 检查是否需要进一步迭代
                if self._needs_more_iteration(result, iteration, input_data):
                    # 更新提示词进行下一轮迭代
                    prompt = self._update_prompt_for_iteration(prompt, result, iteration)
                else:
                    final_result = result
                    break
            
            # 阶段3: 结果处理
            yield await self.stream_progress({
                'status': 'finalizing',
                'message': '正在整理最终推理结果...',
                'progress': 90
            }, context)
            
            # 构建结构化结果
            result_data = self._structure_reasoning_result(
                final_result or result, input_data, task_requirement
            )
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"推理工具执行失败: {e}", tool_name=self.name)
    
    def _build_reasoning_prompt(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> str:
        """构建推理提示词"""
        problem = input_data['problem']
        reasoning_depth = input_data.get('reasoning_depth', ReasoningDepth.DETAILED)
        
        # 选择模板
        template_type = "analysis"
        if "决策" in problem or "选择" in problem or "决定" in problem:
            template_type = "decision"
        
        template = self.reasoning_templates[template_type]
        
        # 准备模板变量
        template_vars = {
            'problem': problem,
            'depth': self._get_depth_description(reasoning_depth),
            'context': json.dumps(input_data.get('context', {}), ensure_ascii=False, indent=2),
            'memory': json.dumps(input_data.get('memory_state', {}), ensure_ascii=False, indent=2),
            'step_by_step': "请提供详细的逐步推理过程。" if input_data.get('require_step_by_step') else "",
            'assumptions': "请明确说明所做的假设。" if input_data.get('include_assumptions') else "",
            'alternatives': "请考虑并分析替代方案。" if input_data.get('consider_alternatives') else ""
        }
        
        return template.format(**template_vars)
    
    
    def _build_task_requirement(self, input_data: Dict[str, Any]) -> TaskRequirement:
        """构建任务需求"""
        reasoning_depth = input_data.get('reasoning_depth', ReasoningDepth.DETAILED)
        
        return TaskRequirement(
            requires_thinking=reasoning_depth in [ReasoningDepth.DEEP, ReasoningDepth.EXPERT],
            cost_sensitive=False,  # 推理任务通常不敏感成本
            speed_priority=False   # 推理任务优先质量
        )
    
    def _get_depth_description(self, depth: ReasoningDepth) -> str:
        """获取深度描述"""
        descriptions = {
            ReasoningDepth.BASIC: "基础",
            ReasoningDepth.DETAILED: "详细", 
            ReasoningDepth.DEEP: "深度",
            ReasoningDepth.EXPERT: "专家级"
        }
        return descriptions.get(depth, "详细")
    
    def _needs_more_iteration(self, result: str, iteration: int, input_data: Dict[str, Any]) -> bool:
        """判断是否需要更多迭代"""
        max_iterations = input_data.get('max_iterations', 3)
        
        # 检查结果质量
        if iteration >= max_iterations - 1:
            return False
        
        # 简单启发式：检查结果是否包含不确定的表述
        uncertainty_indicators = [
            "不确定", "可能需要", "建议进一步", "有待验证",
            "possibly", "might need", "recommend further", "requires validation"
        ]
        
        result_lower = result.lower()
        return any(indicator in result_lower for indicator in uncertainty_indicators)
    
    def _update_prompt_for_iteration(self, current_prompt: str, previous_result: str, iteration: int) -> str:
        """更新提示词进行下一轮迭代"""
        iteration_prompt = f"""

--- 第 {iteration + 1} 轮迭代反馈 ---

上一轮推理结果:
{previous_result}

请基于以上结果进行更深入的分析和推理，特别关注：
1. 验证之前的结论
2. 深入分析不确定的方面  
3. 提供更具体的建议
4. 考虑更多潜在因素
"""
        
        return current_prompt + iteration_prompt
    
    def _structure_reasoning_result(self, result: str, input_data: Dict[str, Any], 
                                  task_requirement: TaskRequirement) -> Dict[str, Any]:
        """结构化推理结果"""
        return {
            'operation': 'llm_reasoning',
            'problem': input_data['problem'],
            'reasoning_depth': input_data.get('reasoning_depth'),
            'result': result,
            'structured_analysis': self._extract_analysis_structure(result),
            'execution_metrics': {
                'iterations_used': input_data.get('max_iterations', 3),
                'requires_thinking': task_requirement.requires_thinking,
                'cost_sensitive': task_requirement.cost_sensitive,
                'speed_priority': task_requirement.speed_priority,
                'execution_time': datetime.now().isoformat()
            },
            'context_used': bool(input_data.get('context')),
            'memory_used': bool(input_data.get('memory_state')),
            'step_by_step': input_data.get('require_step_by_step'),
            'assumptions_included': input_data.get('include_assumptions')
        }
    
    def _extract_analysis_structure(self, result: str) -> Dict[str, Any]:
        """从结果中提取分析结构"""
        # 简单的内容分析
        lines = result.split('\n')
        
        return {
            'sections_count': len([l for l in lines if l.strip().startswith(('#', '##', '###'))]),
            'key_points': len([l for l in lines if l.strip().startswith('-')]),
            'recommendations': len([l for l in lines if '建议' in l or 'recommend' in l.lower()]),
            'assumptions': len([l for l in lines if '假设' in l or 'assum' in l.lower()]),
            'analysis_depth': 'deep' if len(lines) > 20 else 'medium' if len(lines) > 10 else 'basic'
        }


def create_llm_reasoning_tool() -> LLMReasoningTool:
    """创建LLM推理工具实例"""
    return LLMReasoningTool()


__all__ = ["LLMReasoningTool", "ReasoningDepth", "create_llm_reasoning_tool"]