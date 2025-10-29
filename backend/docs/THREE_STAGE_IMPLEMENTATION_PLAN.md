# 三阶段Agent实施方案

## 🎯 实施概述

本文档提供详细的实施步骤，帮助将当前单一Agent架构转换为三阶段Pipeline架构。

---

## 🔥 优先级0：修复模型自主选择功能（立即执行）

### 问题诊断

当前 `model_selection.py` 中的 `_llm_assess_complexity` 方法使用**模拟评估**，而不是真正的LLM推理：

```python
# ❌ 当前实现（模拟）
async def _llm_assess_complexity(self, prompt: str) -> TaskComplexityAssessment:
    # 这里应该调用实际的LLM服务
    # 为了演示，我们使用一个简化的实现

    # 简单的关键词匹配
    if any(keyword in prompt_lower for keyword in ["复杂", "多表"]):
        complexity_score = 0.7
```

### 解决方案

创建真正的LLM评估服务：

```python
# ✅ 新实现（真实LLM评估）

from typing import Optional
import json


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
            self.llm_adapter = await get_llm_adapter(self.container)

    async def evaluate_complexity(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
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

        # 使用结构化输出
        response = await self.llm_adapter.chat_completion(
            messages=messages,
            temperature=0.0,  # 使用确定性输出
            response_format={"type": "json_object"}  # 要求JSON格式
        )

        # 解析响应
        result = self._parse_llm_response(response)

        return result

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
                confidence=data.get("confidence", 0.8)
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
            self.llm_adapter = await get_llm_adapter(self.container)

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
            user_id: 用户ID
            task_type: 任务类型
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

        response = await self.llm_adapter.chat_completion(
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        # 解析响应
        decision = self._parse_selection_response(response, available_models)

        return decision

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

        prompt += """
## 选择标准

1. **任务匹配度**: 模型能力是否匹配任务需求
2. **性能需求**: 任务复杂度与模型推理能力的匹配
3. **成本效益**: 在满足需求的前提下选择性价比最高的模型
4. **速度要求**: 考虑任务的时效性需求

## 输出格式

```json
{
    "selected_model": "gpt-4",
    "model_type": "default",
    "reasoning": "任务复杂度较高(0.75)，需要强大的推理能力...",
    "expected_performance": "高性能，预计准确率95%+",
    "fallback_model": "gpt-3.5-turbo",
    "confidence": 0.9
}
```

请根据任务特点和可用模型，选择最合适的模型。
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

            return ModelSelectionDecision(
                selected_model=data.get("selected_model", available_models[0]["name"]),
                model_type=data.get("model_type", "default"),
                reasoning=data.get("reasoning", ""),
                expected_performance=data.get("expected_performance", "标准性能"),
                fallback_model=data.get("fallback_model")
            )
        except json.JSONDecodeError as e:
            logger.error(f"解析模型选择响应失败: {e}")
            # 返回默认选择
            return ModelSelectionDecision(
                selected_model=available_models[0]["name"],
                model_type="default",
                reasoning="解析失败，使用默认模型",
                expected_performance="标准性能",
                fallback_model=available_models[1]["name"] if len(available_models) > 1 else None
            )
```

### 集成步骤

#### 1. 更新 `TaskComplexityAssessmentTool`

```python
class TaskComplexityAssessmentTool(BaseTool):
    """任务复杂度评估工具（使用真实LLM）"""

    def __init__(self, container, user_model_resolver: UserModelResolver):
        super().__init__()
        self.container = container
        self.user_model_resolver = user_model_resolver
        self.evaluator = LLMComplexityEvaluator(container)
        self.name = "assess_task_complexity"
        self.description = "使用LLM评估任务的复杂度"

    async def arun(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TaskComplexityAssessment:
        """评估任务复杂度"""
        try:
            logger.info(f"🔍 开始LLM评估任务复杂度: {task_description[:100]}...")

            # 使用真实LLM评估
            result = await self.evaluator.evaluate_complexity(
                task_description=task_description,
                context=context
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
        keywords_complex = ["复杂", "多表", "聚合", "分析", "JOIN"]
        keywords_simple = ["简单", "单一", "基础"]

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
```

#### 2. 更新 `ModelSelectionTool`

```python
class ModelSelectionTool(BaseTool):
    """模型选择工具（使用真实LLM）"""

    def __init__(self, container, user_model_resolver: UserModelResolver):
        super().__init__()
        self.container = container
        self.user_model_resolver = user_model_resolver
        self.selector = LLMModelSelector(container, user_model_resolver)
        self.name = "select_optimal_model"
        self.description = "使用LLM选择最合适的模型"

    async def arun(
        self,
        task_description: str,
        complexity_score: float,
        user_id: str,
        task_type: str = "placeholder_analysis",
        **kwargs
    ) -> ModelSelectionDecision:
        """选择合适的模型"""
        try:
            logger.info(f"🤖 开始LLM模型选择: complexity={complexity_score:.2f}")

            # 获取用户配置
            user_config = await get_user_model_config(user_id, task_type)

            # 准备可用模型列表
            available_models = self._prepare_available_models(user_config)

            # 创建复杂度评估对象
            complexity_assessment = TaskComplexityAssessment(
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
            # 回退到规则选择
            return self._fallback_selection(user_config, complexity_score)

    def _prepare_available_models(
        self,
        user_config
    ) -> List[Dict[str, Any]]:
        """准备可用模型列表"""
        models = []

        if user_config.default_model:
            models.append({
                "name": user_config.default_model.model_name,
                "type": "default",
                "capabilities": "通用任务处理",
                "reasoning_level": "中等",
                "speed": "快速",
                "cost": "低",
                "use_cases": "简单到中等复杂度任务"
            })

        if user_config.think_model:
            models.append({
                "name": user_config.think_model.model_name,
                "type": "think",
                "capabilities": "深度推理和复杂任务处理",
                "reasoning_level": "高",
                "speed": "较慢",
                "cost": "高",
                "use_cases": "复杂推理、多步骤任务"
            })

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

        return ModelSelectionDecision(
            selected_model=selected_model_config.model_name,
            model_type=selected_model_config.model_type,
            reasoning="LLM选择失败，使用规则选择",
            expected_performance="标准性能",
            fallback_model=None
        )
```

---

## 📝 优先级1：创建三阶段Agent类

### 1.1 创建基础目录结构

```bash
backend/app/services/infrastructure/agents/
├── stages/
│   ├── __init__.py
│   ├── base.py              # 基础阶段Agent
│   ├── sql_stage.py         # SQL生成阶段
│   ├── chart_stage.py       # 图表生成阶段
│   └── document_stage.py    # 文档生成阶段
├── pipeline/
│   ├── __init__.py
│   ├── coordinator.py       # 阶段协调器
│   └── pipeline.py          # 三阶段Pipeline
```

### 1.2 实现基础阶段Agent

创建 `backend/app/services/infrastructure/agents/stages/base.py`：

```python
"""
基础阶段Agent

所有阶段Agent的基类
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncGenerator

from ..facade import LoomAgentFacade
from ..types import AgentConfig, AgentEvent, ExecutionStage
from ..tools.model_selection import DynamicModelSwitcher


logger = logging.getLogger(__name__)


class BaseStageAgent(ABC):
    """基础阶段Agent"""

    def __init__(self, container, stage_name: str):
        """
        Args:
            container: 服务容器
            stage_name: 阶段名称
        """
        self.container = container
        self.stage_name = stage_name
        self.config: Optional[AgentConfig] = None
        self.facade: Optional[LoomAgentFacade] = None
        self.model_switcher = DynamicModelSwitcher(container)

        self._initialized = False

        logger.info(f"🏗️ [{self.stage_name}] 阶段Agent创建")

    @abstractmethod
    def _create_stage_config(self) -> AgentConfig:
        """创建阶段专用配置"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行阶段任务"""
        pass

    async def initialize(
        self,
        user_id: str,
        model_config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化阶段Agent

        Args:
            user_id: 用户ID
            model_config: 模型配置（由DynamicModelSwitcher生成）
        """
        if self._initialized:
            return

        try:
            logger.info(f"🚀 [{self.stage_name}] 开始初始化")

            # 创建阶段配置
            self.config = self._create_stage_config()

            # 如果提供了模型配置，更新LLM配置
            if model_config:
                self._apply_model_config(model_config)

            # 创建Facade实例
            self.facade = LoomAgentFacade(
                container=self.container,
                config=self.config,
                enable_context_retriever=self._should_enable_context_retriever()
            )

            # 初始化Facade
            await self.facade.initialize(
                user_id=user_id,
                task_type=self._get_task_type(),
                task_complexity=model_config.get("complexity_assessment", {}).get("complexity_score", 0.5)
                    if model_config else 0.5
            )

            self._initialized = True
            logger.info(f"✅ [{self.stage_name}] 初始化完成")

        except Exception as e:
            logger.error(f"❌ [{self.stage_name}] 初始化失败: {e}", exc_info=True)
            raise

    def _apply_model_config(self, model_config: Dict[str, Any]):
        """应用模型配置"""
        selected_model = model_config.get("selected_model_config", {})

        if selected_model:
            self.config.llm.model = selected_model.get("model_name", "gpt-4")
            self.config.llm.temperature = selected_model.get("temperature", 0.0)
            self.config.llm.max_tokens = selected_model.get("max_tokens")
            self.config.max_context_tokens = model_config.get("max_context_tokens", 16000)

            logger.info(
                f"📝 [{self.stage_name}] 应用模型配置: "
                f"model={self.config.llm.model}, "
                f"context_tokens={self.config.max_context_tokens}"
            )

    @abstractmethod
    def _should_enable_context_retriever(self) -> bool:
        """是否启用上下文检索器"""
        pass

    @abstractmethod
    def _get_task_type(self) -> str:
        """获取任务类型"""
        pass

    def get_metrics(self) -> Dict[str, Any]:
        """获取阶段指标"""
        if not self.facade:
            return {}

        return {
            "stage_name": self.stage_name,
            "initialized": self._initialized,
            **self.facade.get_metrics()
        }
```

### 1.3 实现SQL生成阶段Agent

创建 `backend/app/services/infrastructure/agents/stages/sql_stage.py`：

```python
"""
SQL生成阶段Agent

负责根据模板、数据源生成并验证SQL
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, AsyncGenerator

from .base import BaseStageAgent
from ..config.agent import create_default_agent_config
from ..prompts.stages import get_stage_prompt
from ..types import AgentEvent, ExecutionStage, TaskComplexity


logger = logging.getLogger(__name__)


class SQLGenerationAgent(BaseStageAgent):
    """SQL生成阶段Agent"""

    def __init__(self, container):
        super().__init__(container, "SQL生成阶段")

    def _create_stage_config(self):
        """创建SQL阶段专用配置"""
        config = create_default_agent_config()

        # SQL阶段只启用相关工具
        config.tools.enabled_tools = [
            "schema_discovery",
            "schema_retrieval",
            "schema_cache",
            "sql_generator",
            "sql_validator",
            "sql_column_checker",
            "sql_auto_fixer",
            "sql_executor",  # 用于测试SQL
        ]

        # SQL阶段配置
        config.max_iterations = 8
        config.behavior.quality_threshold = 0.8
        config.behavior.enable_self_correction = True

        # SQL阶段系统提示
        config.system_prompt = get_stage_prompt(ExecutionStage.SQL_GENERATION)

        return config

    def _should_enable_context_retriever(self) -> bool:
        """SQL阶段需要Schema上下文检索"""
        return True

    def _get_task_type(self) -> str:
        """SQL生成任务类型"""
        return "sql_generation"

    async def execute(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        task_context: Optional[Dict[str, Any]] = None,
        template_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行SQL生成阶段

        Args:
            placeholder: 占位符描述
            data_source_id: 数据源ID
            user_id: 用户ID
            task_context: 任务上下文
            template_context: 模板上下文
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: SQL生成结果
        """
        if not self._initialized:
            raise RuntimeError(f"[{self.stage_name}] Agent未初始化")

        logger.info(f"🎯 [{self.stage_name}] 开始执行")
        logger.info(f"   占位符: {placeholder[:100]}...")
        logger.info(f"   数据源ID: {data_source_id}")

        try:
            # 执行分析
            result = await self.facade.analyze_placeholder_sync(
                placeholder=placeholder,
                data_source_id=data_source_id,
                user_id=user_id,
                task_context=task_context,
                template_context=template_context,
                complexity=TaskComplexity.MEDIUM,
                **kwargs
            )

            # 提取SQL结果
            sql_query = None
            if isinstance(result.result, str):
                sql_query = result.result
            elif isinstance(result.result, dict):
                sql_query = result.result.get("sql", result.result.get("result", ""))

            logger.info(f"✅ [{self.stage_name}] 执行完成")
            logger.info(f"   生成SQL长度: {len(sql_query) if sql_query else 0}")
            logger.info(f"   质量评分: {result.quality_score:.2f}")

            return {
                "stage": "sql_generation",
                "sql": sql_query,
                "quality_score": result.quality_score,
                "reasoning": result.reasoning,
                "validation_results": result.validation_results,
                "metadata": result.metadata
            }

        except Exception as e:
            logger.error(f"❌ [{self.stage_name}] 执行失败: {e}", exc_info=True)
            raise

    async def execute_stream(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        流式执行SQL生成阶段

        Yields:
            AgentEvent: 执行事件
        """
        if not self._initialized:
            raise RuntimeError(f"[{self.stage_name}] Agent未初始化")

        logger.info(f"🎯 [{self.stage_name}] 开始流式执行")

        async for event in self.facade.analyze_placeholder(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        ):
            # 添加阶段信息
            event.data["stage_name"] = self.stage_name
            yield event
```

### 1.4 实现图表生成阶段Agent

创建 `backend/app/services/infrastructure/agents/stages/chart_stage.py`：

```python
"""
图表生成阶段Agent

负责基于ETL数据生成图表配置
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import BaseStageAgent
from ..config.agent import create_default_agent_config
from ..prompts.stages import get_stage_prompt
from ..types import ExecutionStage, TaskComplexity


logger = logging.getLogger(__name__)


class ChartGenerationAgent(BaseStageAgent):
    """图表生成阶段Agent"""

    def __init__(self, container):
        super().__init__(container, "图表生成阶段")

    def _create_stage_config(self):
        """创建图表阶段专用配置"""
        config = create_default_agent_config()

        # 图表阶段只启用相关工具
        config.tools.enabled_tools = [
            "chart_generator",
            "chart_analyzer",
            "data_sampler",
            "data_analyzer",
        ]

        # 图表阶段配置
        config.max_iterations = 6
        config.behavior.quality_threshold = 0.75

        # 图表阶段系统提示
        config.system_prompt = get_stage_prompt(ExecutionStage.CHART_GENERATION)

        return config

    def _should_enable_context_retriever(self) -> bool:
        """图表阶段不需要Schema上下文检索"""
        return False

    def _get_task_type(self) -> str:
        """图表生成任务类型"""
        return "chart_generation"

    async def execute(
        self,
        etl_data: Dict[str, Any],
        chart_placeholder: str,
        user_id: str,
        statistics: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行图表生成阶段

        Args:
            etl_data: ETL处理后的数据
            chart_placeholder: 图表占位符要求
            user_id: 用户ID
            statistics: 数据统计信息
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 图表配置结果
        """
        if not self._initialized:
            raise RuntimeError(f"[{self.stage_name}] Agent未初始化")

        logger.info(f"🎯 [{self.stage_name}] 开始执行")
        logger.info(f"   图表要求: {chart_placeholder[:100]}...")

        try:
            # 构建任务上下文
            task_context = {
                "etl_data": etl_data,
                "statistics": statistics or {},
                **kwargs.get("task_context", {})
            }

            # 执行图表生成
            result = await self.facade.generate_chart(
                data_summary=str(statistics) if statistics else str(etl_data),
                chart_requirements=chart_placeholder,
                data_source_id=kwargs.get("data_source_id", 0),
                user_id=user_id,
                task_context=task_context
            )

            logger.info(f"✅ [{self.stage_name}] 执行完成")

            return {
                "stage": "chart_generation",
                "chart_config": result,
                "quality_score": result.get("quality_score", 0.0),
                "reasoning": result.get("reasoning", "")
            }

        except Exception as e:
            logger.error(f"❌ [{self.stage_name}] 执行失败: {e}", exc_info=True)
            raise
```

### 1.5 实现文档生成阶段Agent

创建 `backend/app/services/infrastructure/agents/stages/document_stage.py`：

```python
"""
文档生成阶段Agent

负责基于数据重新表达段落文本
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import BaseStageAgent
from ..config.agent import create_default_agent_config
from ..prompts.stages import get_stage_prompt
from ..types import ExecutionStage


logger = logging.getLogger(__name__)


class DocumentGenerationAgent(BaseStageAgent):
    """文档生成阶段Agent"""

    def __init__(self, container):
        super().__init__(container, "文档生成阶段")

    def _create_stage_config(self):
        """创建文档阶段专用配置"""
        config = create_default_agent_config()

        # 文档阶段工具（目前使用LLM直接生成）
        config.tools.enabled_tools = []

        # 文档阶段配置
        config.max_iterations = 5
        config.behavior.quality_threshold = 0.85

        # 文档阶段需要更高的temperature以支持创造性表达
        config.llm.temperature = 0.3

        # 文档阶段系统提示
        config.system_prompt = get_stage_prompt(ExecutionStage.ANALYSIS)  # 暂时使用ANALYSIS

        return config

    def _should_enable_context_retriever(self) -> bool:
        """文档阶段不需要Schema上下文检索"""
        return False

    def _get_task_type(self) -> str:
        """文档生成任务类型"""
        return "document_generation"

    async def execute(
        self,
        filled_template: str,
        paragraph_context: str,
        placeholder_data: Dict[str, Any],
        user_id: str,
        document_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行文档生成阶段

        Args:
            filled_template: 回填数据后的模板
            paragraph_context: 占位符所在段落
            placeholder_data: 占位符数据
            user_id: 用户ID
            document_context: 文档上下文
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 文档生成结果
        """
        if not self._initialized:
            raise RuntimeError(f"[{self.stage_name}] Agent未初始化")

        logger.info(f"🎯 [{self.stage_name}] 开始执行")
        logger.info(f"   段落长度: {len(paragraph_context)}")

        try:
            # 构建文档生成提示
            document_prompt = f"""
基于以下信息重新表达段落：

## 原始段落
{paragraph_context}

## 占位符数据
{placeholder_data}

## 文档上下文
{document_context or '无'}

请基于占位符数据，保持段落的语言风格和逻辑结构，重新表达这个段落。
确保：
1. 数据准确性
2. 语言流畅性
3. 风格一致性
4. 逻辑连贯性
"""

            # 使用LLM生成文档
            # 这里简化处理，实际可能需要更复杂的工具
            result = await self.facade.analyze_placeholder_sync(
                placeholder=document_prompt,
                data_source_id=kwargs.get("data_source_id", 0),
                user_id=user_id,
                task_context={
                    "filled_template": filled_template,
                    "paragraph_context": paragraph_context,
                    "placeholder_data": placeholder_data,
                    "document_context": document_context or {}
                }
            )

            # 提取生成的文本
            generated_text = None
            if isinstance(result.result, str):
                generated_text = result.result
            elif isinstance(result.result, dict):
                generated_text = result.result.get("text", result.result.get("result", ""))

            logger.info(f"✅ [{self.stage_name}] 执行完成")
            logger.info(f"   生成文本长度: {len(generated_text) if generated_text else 0}")

            return {
                "stage": "document_generation",
                "generated_text": generated_text,
                "quality_score": result.quality_score,
                "reasoning": result.reasoning
            }

        except Exception as e:
            logger.error(f"❌ [{self.stage_name}] 执行失败: {e}", exc_info=True)
            raise
```

---

## 📝 优先级2：创建阶段协调器

创建 `backend/app/services/infrastructure/agents/pipeline/coordinator.py`：

```python
"""
阶段协调器

管理三个阶段之间的数据流和依赖关系
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StageCoordinator:
    """阶段协调器"""

    def __init__(self):
        # 定义阶段依赖关系
        self.stage_dependencies = {
            "sql_generation": [],  # SQL生成没有依赖
            "chart_generation": ["sql_generation"],  # 图表依赖SQL结果
            "document_generation": ["sql_generation"]  # 文档依赖SQL结果（可选依赖图表）
        }

        # 阶段执行顺序
        self.stage_order = ["sql_generation", "chart_generation", "document_generation"]

    def get_execution_order(self, requested_stages: List[str]) -> List[str]:
        """
        获取阶段执行顺序

        Args:
            requested_stages: 请求的阶段列表

        Returns:
            List[str]: 排序后的阶段列表
        """
        # 添加所有依赖
        all_stages = set(requested_stages)
        for stage in requested_stages:
            all_stages.update(self.stage_dependencies.get(stage, []))

        # 按预定义顺序排序
        ordered_stages = [s for s in self.stage_order if s in all_stages]

        logger.info(f"📋 阶段执行顺序: {ordered_stages}")
        return ordered_stages

    def validate_dependencies(self, stage: str, completed_stages: List[str]) -> bool:
        """
        验证阶段依赖是否满足

        Args:
            stage: 要执行的阶段
            completed_stages: 已完成的阶段列表

        Returns:
            bool: 依赖是否满足
        """
        dependencies = self.stage_dependencies.get(stage, [])
        missing = [d for d in dependencies if d not in completed_stages]

        if missing:
            logger.error(f"❌ 阶段 {stage} 缺少依赖: {missing}")
            return False

        return True

    def prepare_stage_input(
        self,
        stage: str,
        base_input: Dict[str, Any],
        stage_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        准备阶段输入

        Args:
            stage: 阶段名称
            base_input: 基础输入
            stage_results: 之前阶段的结果

        Returns:
            Dict[str, Any]: 准备好的阶段输入
        """
        stage_input = base_input.copy()

        if stage == "chart_generation":
            # 图表生成需要SQL结果
            sql_result = stage_results.get("sql_generation", {})
            stage_input["etl_data"] = sql_result.get("etl_data", {})
            stage_input["sql"] = sql_result.get("sql")

        elif stage == "document_generation":
            # 文档生成需要SQL和图表结果
            sql_result = stage_results.get("sql_generation", {})
            chart_result = stage_results.get("chart_generation", {})

            stage_input["filled_template"] = sql_result.get("filled_template", "")
            stage_input["placeholder_data"] = sql_result.get("placeholder_data", {})

            if chart_result:
                stage_input["chart_configs"] = chart_result.get("chart_config", {})

        return stage_input

    def merge_stage_results(self, stage_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并所有阶段结果

        Args:
            stage_results: 各阶段结果

        Returns:
            Dict[str, Any]: 合并后的结果
        """
        merged = {
            "stages": {},
            "summary": {},
            "metadata": {}
        }

        # 复制各阶段结果
        for stage, result in stage_results.items():
            merged["stages"][stage] = result

            # 提取关键信息到summary
            if stage == "sql_generation":
                merged["summary"]["sql"] = result.get("sql")
                merged["summary"]["sql_quality"] = result.get("quality_score")

            elif stage == "chart_generation":
                merged["summary"]["chart_config"] = result.get("chart_config")

            elif stage == "document_generation":
                merged["summary"]["generated_text"] = result.get("generated_text")
                merged["summary"]["text_quality"] = result.get("quality_score")

        # 计算整体质量
        quality_scores = [
            result.get("quality_score", 0.0)
            for result in stage_results.values()
            if "quality_score" in result
        ]

        if quality_scores:
            merged["summary"]["overall_quality"] = sum(quality_scores) / len(quality_scores)

        return merged
```

---

## 📝 优先级3：创建三阶段Pipeline

创建 `backend/app/services/infrastructure/agents/pipeline/pipeline.py`：

```python
"""
三阶段Agent Pipeline

协调SQL生成、图表生成、文档生成三个阶段
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .coordinator import StageCoordinator
from ..stages.sql_stage import SQLGenerationAgent
from ..stages.chart_stage import ChartGenerationAgent
from ..stages.document_stage import DocumentGenerationAgent
from ..tools.model_selection import DynamicModelSwitcher, user_model_resolver

logger = logging.getLogger(__name__)


class ThreeStageAgentPipeline:
    """三阶段Agent Pipeline"""

    def __init__(self, container):
        """
        Args:
            container: 服务容器
        """
        self.container = container

        # 创建三个阶段的Agent
        self.sql_agent = SQLGenerationAgent(container)
        self.chart_agent = ChartGenerationAgent(container)
        self.document_agent = DocumentGenerationAgent(container)

        # 模型自主选择器
        self.model_switcher = DynamicModelSwitcher(user_model_resolver)

        # 阶段协调器
        self.coordinator = StageCoordinator()

        logger.info("🏗️ [ThreeStageAgentPipeline] Pipeline创建完成")

    async def execute_sql_stage(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """执行阶段1：SQL生成与验证"""
        logger.info("🎯 开始执行阶段1：SQL生成")

        # 1. LLM自主判断任务复杂度和模型选择
        model_config = await self.model_switcher.assess_and_select_model(
            task_description=f"SQL生成: {placeholder}",
            user_id=user_id,
            context=kwargs.get("task_context"),
            task_type="sql_generation"
        )

        # 2. 初始化SQL Agent
        await self.sql_agent.initialize(user_id, model_config)

        # 3. 执行SQL生成
        result = await self.sql_agent.execute(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        )

        logger.info(f"✅ 阶段1完成: SQL质量={result.get('quality_score', 0):.2f}")
        return result

    async def execute_chart_stage(
        self,
        etl_data: Dict[str, Any],
        chart_placeholder: str,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """执行阶段2：图表生成"""
        logger.info("🎯 开始执行阶段2：图表生成")

        # 1. LLM自主判断任务复杂度和模型选择
        model_config = await self.model_switcher.assess_and_select_model(
            task_description=f"图表生成: {chart_placeholder}",
            user_id=user_id,
            context={"etl_data": etl_data, **kwargs.get("task_context", {})},
            task_type="chart_generation"
        )

        # 2. 初始化Chart Agent
        await self.chart_agent.initialize(user_id, model_config)

        # 3. 执行图表生成
        result = await self.chart_agent.execute(
            etl_data=etl_data,
            chart_placeholder=chart_placeholder,
            user_id=user_id,
            **kwargs
        )

        logger.info(f"✅ 阶段2完成: 图表质量={result.get('quality_score', 0):.2f}")
        return result

    async def execute_document_stage(
        self,
        filled_template: str,
        paragraph_context: str,
        placeholder_data: Dict[str, Any],
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """执行阶段3：文档生成"""
        logger.info("🎯 开始执行阶段3：文档生成")

        # 1. LLM自主判断任务复杂度和模型选择
        model_config = await self.model_switcher.assess_and_select_model(
            task_description=f"文档生成: {paragraph_context[:100]}",
            user_id=user_id,
            context={
                "paragraph_context": paragraph_context,
                "placeholder_data": placeholder_data,
                **kwargs.get("document_context", {})
            },
            task_type="document_generation"
        )

        # 2. 初始化Document Agent
        await self.document_agent.initialize(user_id, model_config)

        # 3. 执行文档生成
        result = await self.document_agent.execute(
            filled_template=filled_template,
            paragraph_context=paragraph_context,
            placeholder_data=placeholder_data,
            user_id=user_id,
            **kwargs
        )

        logger.info(f"✅ 阶段3完成: 文本质量={result.get('quality_score', 0):.2f}")
        return result

    async def execute_pipeline(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        stages: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行完整的Pipeline

        Args:
            placeholder: 占位符描述
            data_source_id: 数据源ID
            user_id: 用户ID
            stages: 要执行的阶段列表（默认全部执行）
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: Pipeline执行结果
        """
        logger.info("🚀 [ThreeStageAgentPipeline] 开始执行Pipeline")

        # 确定执行阶段
        if stages is None:
            stages = ["sql_generation", "chart_generation", "document_generation"]

        # 获取执行顺序
        execution_order = self.coordinator.get_execution_order(stages)

        # 准备基础输入
        base_input = {
            "placeholder": placeholder,
            "data_source_id": data_source_id,
            "user_id": user_id,
            **kwargs
        }

        # 执行各阶段
        stage_results = {}
        completed_stages = []

        for stage in execution_order:
            # 验证依赖
            if not self.coordinator.validate_dependencies(stage, completed_stages):
                logger.error(f"❌ 阶段 {stage} 依赖未满足，跳过")
                continue

            # 准备阶段输入
            stage_input = self.coordinator.prepare_stage_input(
                stage, base_input, stage_results
            )

            # 执行阶段
            try:
                if stage == "sql_generation":
                    result = await self.execute_sql_stage(**stage_input)
                elif stage == "chart_generation":
                    result = await self.execute_chart_stage(**stage_input)
                elif stage == "document_generation":
                    result = await self.execute_document_stage(**stage_input)
                else:
                    logger.warning(f"⚠️ 未知阶段: {stage}")
                    continue

                stage_results[stage] = result
                completed_stages.append(stage)

            except Exception as e:
                logger.error(f"❌ 阶段 {stage} 执行失败: {e}", exc_info=True)
                stage_results[stage] = {
                    "stage": stage,
                    "error": str(e),
                    "status": "failed"
                }

        # 合并结果
        merged_results = self.coordinator.merge_stage_results(stage_results)

        logger.info("✅ [ThreeStageAgentPipeline] Pipeline执行完成")
        logger.info(f"   执行阶段: {completed_stages}")
        logger.info(f"   整体质量: {merged_results['summary'].get('overall_quality', 0):.2f}")

        return merged_results


# 便捷函数

def create_three_stage_pipeline(container) -> ThreeStageAgentPipeline:
    """创建三阶段Pipeline"""
    return ThreeStageAgentPipeline(container)
```

---

## 📝 优先级4：更新Facade接口

更新 `facade.py` 以支持三阶段Pipeline：

```python
# 在LoomAgentFacade类中添加以下方法

from .pipeline.pipeline import ThreeStageAgentPipeline

class LoomAgentFacade:
    # ... 现有代码 ...

    def __init__(self, container, config=None, enable_context_retriever=True):
        # ... 现有代码 ...

        # 添加三阶段Pipeline
        self._pipeline: Optional[ThreeStageAgentPipeline] = None

    def get_pipeline(self) -> ThreeStageAgentPipeline:
        """获取三阶段Pipeline实例"""
        if not self._pipeline:
            self._pipeline = ThreeStageAgentPipeline(self.container)
        return self._pipeline

    async def execute_three_stage_pipeline(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        stages: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行三阶段Pipeline

        Args:
            placeholder: 占位符描述
            data_source_id: 数据源ID
            user_id: 用户ID
            stages: 要执行的阶段列表
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: Pipeline结果
        """
        pipeline = self.get_pipeline()

        return await pipeline.execute_pipeline(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            stages=stages,
            **kwargs
        )
```

---

## 📝 测试计划

创建测试脚本 `backend/scripts/test_three_stage_pipeline.py`：

```python
"""
测试三阶段Pipeline
"""

import asyncio
import logging
from app.core.container import Container
from app.services.infrastructure.agents.pipeline.pipeline import create_three_stage_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_three_stage_pipeline():
    """测试完整的三阶段Pipeline"""

    # 创建容器
    container = Container()

    # 创建Pipeline
    pipeline = create_three_stage_pipeline(container)

    # 测试数据
    test_input = {
        "placeholder": "统计2023年各部门的销售额，并按销售额降序排列",
        "data_source_id": 1,
        "user_id": "test_user_123",
        "task_context": {
            "template_name": "年度销售报告",
            "report_type": "summary"
        }
    }

    try:
        logger.info("=" * 60)
        logger.info("开始测试三阶段Pipeline")
        logger.info("=" * 60)

        # 执行Pipeline
        result = await pipeline.execute_pipeline(**test_input)

        logger.info("=" * 60)
        logger.info("Pipeline执行结果")
        logger.info("=" * 60)

        # 输出结果
        logger.info(f"执行阶段: {list(result['stages'].keys())}")
        logger.info(f"整体质量: {result['summary'].get('overall_quality', 0):.2f}")

        if "sql" in result["summary"]:
            logger.info(f"\nSQL查询:\n{result['summary']['sql']}")

        if "chart_config" in result["summary"]:
            logger.info(f"\n图表配置:\n{result['summary']['chart_config']}")

        if "generated_text" in result["summary"]:
            logger.info(f"\n生成文本:\n{result['summary']['generated_text']}")

        logger.info("=" * 60)
        logger.info("✅ 测试完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_three_stage_pipeline())
```

---

## 📊 实施时间表

| 优先级 | 任务 | 预计时间 | 依赖 |
|--------|------|----------|------|
| P0 | 修复模型自主选择功能 | 1天 | 无 |
| P1 | 创建三阶段Agent类 | 2天 | P0 |
| P2 | 创建阶段协调器 | 0.5天 | P1 |
| P3 | 创建三阶段Pipeline | 1天 | P1, P2 |
| P4 | 更新Facade接口 | 0.5天 | P3 |
| P5 | 编写测试用例 | 1天 | P4 |
| P6 | 文档和示例 | 0.5天 | P5 |

**总计**: 约6.5天

---

## 🎯 成功标准

1. ✅ 模型自主选择功能使用真实LLM评估
2. ✅ 三个阶段的Agent独立运行
3. ✅ 阶段协调器正确管理依赖
4. ✅ Pipeline能够完整执行三个阶段
5. ✅ 每个阶段的质量评分达到预期
6. ✅ 整体执行时间减少30%+
7. ✅ Token使用量减少40%+

---

## 🔄 后续优化

1. **阶段缓存**：缓存SQL生成结果，避免重复执行
2. **并行执行**：图表和文档阶段可以部分并行
3. **增量更新**：仅重新执行有变化的阶段
4. **性能监控**：添加详细的性能指标
5. **A/B测试**：对比单Agent vs 三阶段的效果
