#!/usr/bin/env python3
"""
LLM复杂度评估器和模型选择器

使用真实的LLM服务进行任务复杂度评估和模型选择
"""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, is_dataclass

logger = logging.getLogger(__name__)

from app.services.infrastructure.agents.llm_adapter import _CURRENT_STAGE


def _to_serializable(payload: Any) -> Any:  # noqa: F841
    """
    将数据对象转换为可序列化格式（支持dataclass和Pydantic）

    Note: 此函数保留用于未来的序列化需求
    """
    if is_dataclass(payload):
        return asdict(payload)
    if hasattr(payload, "dict") and callable(payload.dict):
        return payload.dict()
    if hasattr(payload, "model_dump") and callable(payload.model_dump):
        return payload.model_dump()
    return payload


@dataclass
class TaskComplexityAssessment:
    """任务复杂度评估结果"""
    complexity_score: float  # 0.0-1.0
    reasoning: str
    factors: List[str]
    confidence: float  # 0.0-1.0
    dimension_scores: Optional[Dict[str, float]] = None


@dataclass
class ModelSelectionDecision:
    """模型选择决策结果"""
    selected_model: str
    model_type: str  # "default" or "think"
    reasoning: str
    expected_performance: str
    fallback_model: Optional[str] = None
    confidence: float = 0.8


class LLMComplexityEvaluator:
    """使用LLM进行任务复杂度评估"""

    def __init__(self, container):
        """
        Args:
            container: 服务容器，包含llm_adapter
        """
        self.container = container
        self.llm_adapter = None

    async def initialize(self):
        """初始化LLM适配器"""
        if not self.llm_adapter:
            from ..llm_adapter import get_llm_adapter
            self.llm_adapter = get_llm_adapter(self.container)

    async def evaluate_complexity(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        *,
        user_id: Optional[str] = None
    ) -> TaskComplexityAssessment:
        """
        使用LLM评估任务复杂度

        Args:
            task_description: 任务描述
            context: 任务上下文

        Returns:
            TaskComplexityAssessment: 复杂度评估结果
        """
        await self.initialize()

        # 构建评估提示
        evaluation_prompt = self._build_evaluation_prompt(task_description, context)

        # 调用LLM
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的任务复杂度评估专家。你需要分析任务并评估其复杂度。"
            },
            {
                "role": "user",
                "content": evaluation_prompt
            }
        ]

        try:
            # 🔥 设置用户ID和阶段的context variables
            from ..llm_adapter import _CURRENT_USER_ID
            if not user_id:
                raise ValueError("evaluate_complexity 需要提供有效的 user_id")
            user_token = _CURRENT_USER_ID.set(user_id)
            stage_token = _CURRENT_STAGE.set("complexity_assessment")
            try:
                response = await self.llm_adapter.chat_completion(
                    messages=messages,
                    temperature=0.0,  # 使用确定性输出
                    response_format={"type": "json_object"}  # 要求JSON格式
                )
            finally:
                _CURRENT_STAGE.reset(stage_token)
                _CURRENT_USER_ID.reset(user_token)

            # 检查空响应
            if not response or not response.strip():
                logger.error("❌ LLM返回空响应，无法进行复杂度评估")
                raise ValueError("LLM returned empty response")

            # 解析响应
            result = self._parse_llm_response(response)
            logger.info(f"✅ LLM复杂度评估完成: {result.complexity_score:.2f}")
            return result

        except Exception as e:
            logger.error(f"❌ LLM复杂度评估失败: {e}")
            # 回退到规则基础评估
            return self._fallback_assessment(task_description, context)

    def _build_evaluation_prompt(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """构建评估提示"""

        prompt = f"""请评估以下任务的复杂度：

## 任务描述
{task_description}

## 评估维度

### 1. 数据查询复杂度 (0.0-0.3)
- 0.0-0.1: 单表查询，简单条件
- 0.1-0.2: 多表JOIN，基础聚合
- 0.2-0.3: 复杂JOIN，子查询，窗口函数

### 2. 业务逻辑复杂度 (0.0-0.3)
- 0.0-0.1: 单一指标，直接计算
- 0.1-0.2: 多个指标，简单逻辑
- 0.2-0.3: 复杂业务规则，多维度分析

### 3. 计算复杂度 (0.0-0.2)
- 0.0-0.1: 基础统计（SUM, AVG, COUNT）
- 0.1-0.2: 复杂计算（同比、环比、趋势分析）

### 4. 上下文理解复杂度 (0.0-0.2)
- 0.0-0.1: 直接明确的需求
- 0.1-0.2: 需要推理和理解隐含需求

"""

        if context:
            prompt += f"\n## 任务上下文\n{json.dumps(context, ensure_ascii=False, indent=2)}\n"

        prompt += """
## 输出格式

请以JSON格式返回评估结果：

```json
{
    "complexity_score": 0.75,  // 总复杂度评分 (0.0-1.0)
    "reasoning": "任务涉及多表关联查询和复杂的时间序列分析...",
    "factors": [
        "多表JOIN查询",
        "时间序列分析",
        "复杂聚合计算"
    ],
    "confidence": 0.85,  // 评估置信度 (0.0-1.0)
    "dimension_scores": {
        "data_query": 0.25,
        "business_logic": 0.20,
        "computation": 0.15,
        "context_understanding": 0.15
    }
}
```

请根据上述评估维度，综合分析任务复杂度。
"""

        return prompt

    def _parse_llm_response(self, response: str) -> TaskComplexityAssessment:
        """解析LLM响应"""
        try:
            # 尝试解析JSON
            data = json.loads(response)

            return TaskComplexityAssessment(
                complexity_score=data.get("complexity_score", 0.5),
                reasoning=data.get("reasoning", ""),
                factors=data.get("factors", []),
                confidence=data.get("confidence", 0.8),
                dimension_scores=data.get("dimension_scores")
            )
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {e}")
            # 返回默认值
            return TaskComplexityAssessment(
                complexity_score=0.5,
                reasoning="解析失败，使用默认复杂度",
                factors=["解析失败"],
                confidence=0.3
            )

    def _fallback_assessment(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]]  # noqa: ARG002 - 保留用于接口一致性
    ) -> TaskComplexityAssessment:
        """回退评估方法（当LLM评估失败时使用）

        Args:
            task_description: 任务描述
            context: 上下文信息（保留参数，未来可能使用）

        Returns:
            TaskComplexityAssessment: 复杂度评估结果
        """
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

        return TaskComplexityAssessment(
            complexity_score=complexity_score,
            reasoning="LLM评估失败，使用规则基础评估",
            factors=["规则评估"],
            confidence=0.6
        )


class LLMModelSelector:
    """使用LLM进行模型选择"""

    def __init__(self, container, user_model_resolver):
        self.container = container
        self.user_model_resolver = user_model_resolver
        self.llm_adapter = None

    async def initialize(self):
        """初始化LLM适配器"""
        if not self.llm_adapter:
            from ..llm_adapter import get_llm_adapter
            self.llm_adapter = get_llm_adapter(self.container)

    async def select_model(
        self,
        task_description: str,
        complexity_assessment: TaskComplexityAssessment,
        user_id: str,
        task_type: str,
        available_models: List[Dict[str, Any]]
    ) -> ModelSelectionDecision:
        """
        使用LLM选择最合适的模型

        Args:
            task_description: 任务描述
            complexity_assessment: 复杂度评估结果
            user_id: 用户ID（保留参数，未来可能用于个性化）
            task_type: 任务类型（保留参数，未来可能用于分类）
            available_models: 可用模型列表

        Returns:
            ModelSelectionDecision: 模型选择决策
        """
        await self.initialize()

        # 构建选择提示
        selection_prompt = self._build_selection_prompt(
            task_description,
            complexity_assessment,
            available_models
        )

        # 调用LLM
        messages = [
            {
                "role": "system",
                "content": "你是一个AI模型选择专家，能够根据任务特点选择最合适的模型。"
            },
            {
                "role": "user",
                "content": selection_prompt
            }
        ]

        try:
            # 🔥 设置用户ID和阶段的context variables
            from ..llm_adapter import _CURRENT_USER_ID
            if not user_id:
                raise ValueError("select_model 需要提供有效的 user_id")
            user_token = _CURRENT_USER_ID.set(user_id)
            stage_token = _CURRENT_STAGE.set("model_selection")
            try:
                response = await self.llm_adapter.chat_completion(
                    messages=messages,
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
            finally:
                _CURRENT_STAGE.reset(stage_token)
                _CURRENT_USER_ID.reset(user_token)

            # 检查空响应
            if not response or not response.strip():
                logger.error("❌ LLM返回空响应，无法进行模型选择")
                raise ValueError("LLM returned empty response")

            # 解析响应
            decision = self._parse_selection_response(response, available_models)
            logger.info(f"✅ LLM模型选择完成: {decision.selected_model}")
            return decision

        except Exception as e:
            logger.error(f"❌ LLM模型选择失败: {e}")
            # 不再使用回退选择，直接抛出异常
            raise ValueError(f"模型选择失败: {e}")

    def _build_selection_prompt(
        self,
        task_description: str,
        complexity_assessment: TaskComplexityAssessment,
        available_models: List[Dict[str, Any]]
    ) -> str:
        """构建模型选择提示"""

        prompt = f"""请为以下任务选择最合适的AI模型：

## 任务描述
{task_description}

## 复杂度评估
- 复杂度评分: {complexity_assessment.complexity_score:.2f}
- 评估推理: {complexity_assessment.reasoning}
- 影响因素: {', '.join(complexity_assessment.factors)}
- 评估置信度: {complexity_assessment.confidence:.2f}

## 可用模型

"""

        for i, model in enumerate(available_models, 1):
            prompt += f"""
### {i}. {model['name']}
- 类型: {model['type']}
- 能力: {model['capabilities']}
- 推理能力: {model['reasoning_level']}
- 速度: {model['speed']}
- 成本: {model['cost']}
- 适用场景: {model['use_cases']}
"""

        prompt += f"""
## ⚠️ 重要提示

**你必须从上面列出的 {len(available_models)} 个可用模型中选择一个！**

可用模型名称：{', '.join([f'"{m["name"]}"' for m in available_models])}

**不要返回其他模型名称，否则选择将被视为无效！**

## 选择标准

1. **任务匹配度**: 模型能力是否匹配任务需求
2. **性能需求**: 任务复杂度与模型推理能力的匹配
3. **成本效益**: 在满足需求的前提下选择性价比最高的模型
4. **速度要求**: 考虑任务的时效性需求

## 输出格式

```json
{{
    "selected_model": "必须是可用模型之一",
    "model_type": "default 或 think",
    "reasoning": "任务复杂度较高(0.75)，需要强大的推理能力...",
    "expected_performance": "高性能，预计准确率95%+",
    "fallback_model": "default",
    "confidence": 0.9
}}
```

请根据任务特点和可用模型，从可用模型列表中选择最合适的模型。
"""

        return prompt

    def _parse_selection_response(
        self,
        response: str,
        available_models: List[Dict[str, Any]]
    ) -> ModelSelectionDecision:
        """解析模型选择响应"""
        try:
            data = json.loads(response)

            # 🔥 关键修复：验证 LLM 返回的模型是否在用户配置的模型列表中
            selected_model_name = data.get("selected_model", "")
            available_model_names = [m["name"] for m in available_models]

            # 如果 LLM 选择的模型不在可用列表中，直接报错而不是回退
            if selected_model_name not in available_model_names:
                logger.error(
                    f"❌ LLM 选择的模型 '{selected_model_name}' 不在用户配置的模型列表中: {available_model_names}"
                )
                raise ValueError(f"选择的模型 '{selected_model_name}' 不在用户配置的模型列表中")

            # 根据选择的模型名称查找模型类型
            selected_model_type = "default"
            for model in available_models:
                if model["name"] == selected_model_name:
                    selected_model_type = model.get("type", "default")
                    break

            return ModelSelectionDecision(
                selected_model=selected_model_name,
                model_type=selected_model_type,
                reasoning=data.get("reasoning", ""),
                expected_performance=data.get("expected_performance", "标准性能"),
                fallback_model=data.get("fallback_model"),
                confidence=data.get("confidence", 0.8)
            )
        except json.JSONDecodeError as e:
            logger.error(f"解析模型选择响应失败: {e}")
            raise ValueError(f"无法解析LLM响应: {e}")
        except ValueError as e:
            # 重新抛出验证错误
            raise e

    def _fallback_selection(
        self,
        available_models: List[Dict[str, Any]],
        complexity_assessment: TaskComplexityAssessment
    ) -> ModelSelectionDecision:
        """回退选择方法"""
        # 使用规则选择
        if complexity_assessment.complexity_score > 0.7:
            # 高复杂度任务，优先选择思考模型
            for model in available_models:
                if model.get("type") == "think":
                    return ModelSelectionDecision(
                        selected_model=model["name"],
                        model_type="think",
                        reasoning="LLM选择失败，使用规则选择（高复杂度）",
                        expected_performance="高性能",
                        fallback_model=available_models[0]["name"] if available_models else None
                    )
        
        # 默认选择第一个模型
        return ModelSelectionDecision(
            selected_model=available_models[0]["name"],
            model_type=available_models[0].get("type", "default"),
            reasoning="LLM选择失败，使用规则选择",
            expected_performance="标准性能",
            fallback_model=available_models[1]["name"] if len(available_models) > 1 else None
        )
