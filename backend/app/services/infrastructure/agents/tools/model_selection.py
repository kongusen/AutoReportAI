from __future__ import annotations

"""
模型选择工具

让LLM自主判断任务复杂度并选择合适的模型
"""


import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, is_dataclass

from loom.interfaces.tool import BaseTool
from pydantic import BaseModel, Field

from ..config.user_model_resolver import UserModelResolver, get_user_model_config
from .llm_evaluator import LLMComplexityEvaluator, LLMModelSelector, TaskComplexityAssessment as LLMTaskComplexityAssessment, ModelSelectionDecision as LLMModelSelectionDecision

logger = logging.getLogger(__name__)


def _to_serializable(payload: Any) -> Any:
    """将模型选择结果转换为可序列化结构"""
    if is_dataclass(payload):
        return asdict(payload)
    if hasattr(payload, "dict") and callable(payload.dict):
        return payload.dict()
    if hasattr(payload, "model_dump") and callable(payload.model_dump):
        return payload.model_dump()
    return payload


class TaskComplexityAssessment(BaseModel):
    """任务复杂度评估结果"""
    complexity_score: float = Field(..., description="任务复杂度评分 (0.0-1.0)", ge=0.0, le=1.0)
    reasoning: str = Field(..., description="复杂度评估的推理过程")
    factors: List[str] = Field(..., description="影响复杂度的因素")
    confidence: float = Field(..., description="评估置信度 (0.0-1.0)", ge=0.0, le=1.0)


class ModelSelectionDecision(BaseModel):
    """模型选择决策结果"""
    selected_model: str = Field(..., description="选择的模型名称")
    model_type: str = Field(..., description="模型类型 (default/think)")
    reasoning: str = Field(..., description="选择模型的推理过程")
    expected_performance: str = Field(..., description="预期性能表现")
    fallback_model: Optional[str] = Field(None, description="备用模型")


class TaskComplexityAssessmentTool(BaseTool):
    """任务复杂度评估工具（使用真实LLM）"""
    
    def __init__(self, container, user_model_resolver: UserModelResolver):
        super().__init__()
        self.container = container
        self.user_model_resolver = user_model_resolver
        self.evaluator = LLMComplexityEvaluator(container)
        self.name = "assess_task_complexity"
        self.description = """
        使用LLM评估任务的复杂度，帮助决定是否需要使用更强大的模型。
        
        输入参数：
        - task_description: 任务描述
        - context: 任务上下文信息
        - user_preferences: 用户偏好设置
        
        返回：
        - complexity_score: 复杂度评分 (0.0-1.0)
        - reasoning: 评估推理过程
        - factors: 影响复杂度的因素
        - confidence: 评估置信度
        """
    
    async def run(self, task_description: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> LLMTaskComplexityAssessment:
        """Loom框架要求的run方法"""
        return await self.arun(task_description, context, **kwargs)
    
    async def arun(self, task_description: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> LLMTaskComplexityAssessment:
        """
        评估任务复杂度
        
        Args:
            task_description: 任务描述
            context: 任务上下文
            **kwargs: 其他参数
            
        Returns:
            TaskComplexityAssessment: 复杂度评估结果
        """
        try:
            logger.info(f"🔍 开始LLM评估任务复杂度: {task_description[:100]}...")
            
            # 使用真实LLM评估
            result = await self.evaluator.evaluate_complexity(
                task_description=task_description,
                context=context,
                user_id=kwargs.get("user_id")
            )
            
            logger.info(f"✅ LLM评估完成: {result.complexity_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ LLM评估失败: {e}")
            # 回退到规则基础评估
            return self._fallback_assessment(task_description, context)
    
    def _fallback_assessment(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> TaskComplexityAssessment:
        """回退评估方法"""
        # 使用简单规则评估
        complexity_score = 0.5

        # 基于关键词的简单评估
        keywords_complex = ["复杂", "多表", "聚合", "分析", "JOIN", "子查询", "窗口函数"]
        keywords_simple = ["简单", "单一", "基础", "查询", "统计"]

        text = task_description.lower()

        if any(kw in text for kw in keywords_complex):
            complexity_score = 0.7
        elif any(kw in text for kw in keywords_simple):
            complexity_score = 0.3

        return LLMTaskComplexityAssessment(
            complexity_score=complexity_score,
            reasoning="LLM评估失败，使用规则基础评估",
            factors=["规则评估"],
            confidence=0.6
        )


class ModelSelectionTool(BaseTool):
    """模型选择工具（使用真实LLM）"""
    
    def __init__(self, container, user_model_resolver: UserModelResolver):
        super().__init__()
        self.container = container
        self.user_model_resolver = user_model_resolver
        self.selector = LLMModelSelector(container, user_model_resolver)
        self.name = "select_optimal_model"
        self.description = """
        使用LLM选择最合适的模型。
        
        输入参数：
        - task_description: 任务描述
        - complexity_score: 任务复杂度评分
        - user_id: 用户ID
        - task_type: 任务类型
        
        返回：
        - selected_model: 选择的模型名称
        - model_type: 模型类型
        - reasoning: 选择推理过程
        - expected_performance: 预期性能
        - fallback_model: 备用模型
        """
    
    async def run(self, task_description: str, complexity_score: float, user_id: str, task_type: str = "placeholder_analysis", **kwargs) -> LLMModelSelectionDecision:
        """Loom框架要求的run方法"""
        return await self.arun(task_description, complexity_score, user_id, task_type, **kwargs)
    
    async def arun(
        self,
        task_description: str,
        complexity_score: float,
        user_id: str,
        task_type: str = "placeholder_analysis",
        **kwargs
    ) -> LLMModelSelectionDecision:
        """
        选择合适的模型
        
        Args:
            task_description: 任务描述
            complexity_score: 任务复杂度评分
            user_id: 用户ID
            task_type: 任务类型
            **kwargs: 其他参数
            
        Returns:
            ModelSelectionDecision: 模型选择决策
        """
        try:
            logger.info(f"🤖 开始LLM模型选择: complexity={complexity_score:.2f}")

            # 获取用户配置
            user_config = await get_user_model_config(user_id, task_type)

            # 准备可用模型列表
            available_models = self._prepare_available_models(user_config)

            # 创建复杂度评估对象
            complexity_assessment = LLMTaskComplexityAssessment(
                complexity_score=complexity_score,
                reasoning=kwargs.get("complexity_reasoning", ""),
                factors=kwargs.get("complexity_factors", []),
                confidence=kwargs.get("complexity_confidence", 0.8)
            )

            # 使用LLM选择模型
            decision = await self.selector.select_model(
                task_description=task_description,
                complexity_assessment=complexity_assessment,
                user_id=user_id,
                task_type=task_type,
                available_models=available_models
            )

            logger.info(f"✅ LLM选择完成: {decision.selected_model}")
            return decision

        except Exception as e:
            logger.error(f"❌ LLM模型选择失败: {e}")
            # 不再使用回退选择，直接抛出异常
            raise ValueError(f"模型选择失败: {e}")

    def _prepare_available_models(
        self,
        user_config
    ) -> List[Dict[str, Any]]:
        """准备可用模型列表"""
        models = []

        # 添加默认模型
        if user_config.default_model:
            models.append({
                "name": user_config.default_model.model_name,
                "type": user_config.default_model.model_type,
                "capabilities": "通用任务处理",
                "reasoning_level": "中等",
                "speed": "快速",
                "cost": "低",
                "use_cases": "简单到中等复杂度任务"
            })

        # 添加思考模型（如果存在且不同于默认模型）
        if user_config.think_model and user_config.think_model.model_name != user_config.default_model.model_name:
            models.append({
                "name": user_config.think_model.model_name,
                "type": user_config.think_model.model_type,
                "capabilities": "深度推理和复杂任务处理",
                "reasoning_level": "高",
                "speed": "较慢",
                "cost": "高",
                "use_cases": "复杂推理、多步骤任务"
            })

        logger.info(f"准备可用模型列表: {[m['name'] for m in models]}")
        return models

    def _fallback_selection(
        self,
        user_config,
        complexity_score: float
    ) -> ModelSelectionDecision:
        """回退选择方法"""
        # 使用规则选择
        selected_model_config = self.user_model_resolver.select_model_for_task(
            user_config, complexity_score, "placeholder_analysis"
        )

        return LLMModelSelectionDecision(
            selected_model=selected_model_config.model_name,
            model_type=selected_model_config.model_type,
            reasoning="LLM选择失败，使用规则选择",
            expected_performance="标准性能",
            fallback_model=None
        )


class DynamicModelSwitcher:
    """动态模型切换器"""
    
    def __init__(self, container, user_model_resolver: UserModelResolver):
        self.container = container
        self.user_model_resolver = user_model_resolver
        self.complexity_tool = TaskComplexityAssessmentTool(container, user_model_resolver)
        self.selection_tool = ModelSelectionTool(container, user_model_resolver)
    
    async def assess_and_select_model(
        self,
        task_description: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        task_type: str = "placeholder_analysis"
    ) -> Dict[str, Any]:
        """
        评估任务复杂度并选择合适的模型
        
        Args:
            task_description: 任务描述
            user_id: 用户ID
            context: 任务上下文
            task_type: 任务类型
            
        Returns:
            Dict[str, Any]: 包含评估结果和模型选择的结果
        """
        try:
            logger.info(f"🔄 开始动态模型评估和选择: user_id={user_id}")
            
            # 1. 评估任务复杂度
            complexity_assessment = await self.complexity_tool.arun(
                task_description=task_description,
                context=context,
                user_id=user_id  # 🔥 传递用户ID
            )
            
            # 2. 选择合适模型
            model_decision = await self.selection_tool.arun(
                task_description=task_description,
                complexity_score=complexity_assessment.complexity_score,
                user_id=user_id,
                task_type=task_type
            )
            
            # 3. 获取用户配置
            user_config = await get_user_model_config(user_id, task_type)
            selected_model_config = self.user_model_resolver.select_model_for_task(
                user_config, complexity_assessment.complexity_score, task_type
            )
            
            # 4. 计算最大上下文tokens
            max_context_tokens = self.user_model_resolver.get_max_context_tokens(
                user_config, selected_model_config
            )
            
            result = {
                "complexity_assessment": {
                    "complexity_score": complexity_assessment.complexity_score,
                    "reasoning": complexity_assessment.reasoning,
                    "factors": complexity_assessment.factors,
                    "confidence": complexity_assessment.confidence,
                    "dimension_scores": complexity_assessment.dimension_scores
                },
                "model_decision": _to_serializable(model_decision),
                "selected_model_config": {
                    "model_name": selected_model_config.model_name,
                    "model_type": selected_model_config.model_type,
                    "max_tokens": selected_model_config.max_tokens,
                    "temperature": selected_model_config.temperature,
                    "supports_function_calls": selected_model_config.supports_function_calls,
                    "supports_thinking": selected_model_config.supports_thinking
                },
                "max_context_tokens": max_context_tokens,
                "user_config": {
                    "auto_model_selection": user_config.auto_model_selection,
                    "think_model_threshold": user_config.think_model_threshold
                }
            }
            
            logger.info(f"✅ 动态模型评估完成: {model_decision.selected_model}({model_decision.model_type})")
            return result
            
        except Exception as e:
            logger.error(f"❌ 动态模型评估失败: {e}")
            raise


# 全局实例
user_model_resolver = UserModelResolver()

# 注意：dynamic_model_switcher 需要 container 参数，这里提供一个工厂函数
def create_dynamic_model_switcher(container) -> DynamicModelSwitcher:
    """创建动态模型切换器实例"""
    return DynamicModelSwitcher(container, user_model_resolver)


# 便捷函数
async def assess_task_complexity(
    task_description: str,
    context: Optional[Dict[str, Any]] = None,
    container: Optional[Any] = None
) -> LLMTaskComplexityAssessment:
    """评估任务复杂度的便捷函数"""
    if container is None:
        raise ValueError("container 参数是必需的")
    
    switcher = create_dynamic_model_switcher(container)
    return await switcher.complexity_tool.arun(
        task_description=task_description,
        context=context
    )


async def select_optimal_model(
    task_description: str,
    complexity_score: float,
    user_id: str,
    task_type: str = "placeholder_analysis",
    container: Optional[Any] = None
) -> LLMModelSelectionDecision:
    """选择最优模型的便捷函数"""
    if container is None:
        raise ValueError("container 参数是必需的")
    
    switcher = create_dynamic_model_switcher(container)
    return await switcher.selection_tool.arun(
        task_description=task_description,
        complexity_score=complexity_score,
        user_id=user_id,
        task_type=task_type
    )


async def assess_and_select_model(
    task_description: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None,
    task_type: str = "placeholder_analysis",
    container: Optional[Any] = None
) -> Dict[str, Any]:
    """评估任务复杂度并选择模型的便捷函数"""
    if container is None:
        raise ValueError("container 参数是必需的")
    
    switcher = create_dynamic_model_switcher(container)
    return await switcher.assess_and_select_model(
        task_description=task_description,
        user_id=user_id,
        context=context,
        task_type=task_type
    )
