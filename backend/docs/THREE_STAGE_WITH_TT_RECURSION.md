# 基于TT递归的三阶段Agent架构

## 🎯 核心理念

**保留Loom Agent的TT递归能力，通过Stage-Aware机制在不同阶段使用不同的工具集和提示词。**

---

## ❌ 错误的设计（损失TT递归）

```python
# 错误：创建三个独立的Agent
sql_agent = SQLGenerationAgent()      # ❌ 独立Agent
chart_agent = ChartGenerationAgent()  # ❌ 独立Agent
doc_agent = DocumentAgent()           # ❌ 独立Agent

# 问题：每个Agent独立执行，无法利用TT递归的迭代优化能力
```

---

## ✅ 正确的设计（保留TT递归）

```python
# 正确：一个支持TT递归的Agent，阶段感知
stage_aware_agent = StageAwareAgent()

# 阶段1：SQL生成（内部使用TT递归优化）
async for event in stage_aware_agent.execute_stage(
    stage=ExecutionStage.SQL_GENERATION,
    placeholder="统计各部门销售额"
):
    # TT递归自动迭代：
    # Thought -> Tool(schema) -> Thought -> Tool(sql_gen) ->
    # Thought -> Tool(sql_validate) -> Thought -> Tool(sql_fix) ->
    # Thought -> 输出最优SQL
    pass

# 阶段2：图表生成（内部使用TT递归优化）
async for event in stage_aware_agent.execute_stage(
    stage=ExecutionStage.CHART_GENERATION,
    etl_data=sql_result
):
    # TT递归自动迭代：
    # Thought -> Tool(data_analyze) -> Thought -> Tool(chart_type_select) ->
    # Thought -> Tool(chart_gen) -> Thought -> 输出最优图表配置
    pass

# 阶段3：文档生成（内部使用TT递归优化）
async for event in stage_aware_agent.execute_stage(
    stage=ExecutionStage.DOCUMENT_GENERATION,
    paragraph=paragraph_context
):
    # TT递归自动迭代：
    # Thought -> Tool(paragraph_analyze) -> Thought -> Tool(text_gen) ->
    # Thought -> Tool(style_check) -> Thought -> 输出最优文本
    pass
```

**关键**：每个阶段内部都是完整的TT递归流程！

---

## 🏗️ 架构设计

### 1. Stage-Aware Runtime

```python
class StageAwareRuntime(LoomAgentRuntime):
    """
    阶段感知的Runtime

    保留TT递归能力，根据当前阶段动态切换配置
    """

    def __init__(self, container, config: AgentConfig):
        super().__init__(container, config)

        # 当前执行阶段
        self.current_stage: Optional[ExecutionStage] = None

        # 阶段配置管理器
        self.stage_config_manager = StageConfigManager()

    async def execute_with_stage(
        self,
        request: AgentRequest,
        stage: ExecutionStage
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        在指定阶段执行（保留TT递归）

        Args:
            request: Agent请求
            stage: 执行阶段

        Yields:
            AgentEvent: 执行事件（包含TT递归的所有步骤）
        """
        # 1. 切换到对应阶段配置
        self.current_stage = stage
        stage_config = self.stage_config_manager.get_stage_config(stage)
        self._apply_stage_config(stage_config)

        logger.info(f"🎯 进入阶段: {stage.value}")
        logger.info(f"   启用工具: {stage_config['enabled_tools']}")
        logger.info(f"   质量阈值: {stage_config['quality_threshold']}")

        # 2. 使用TT递归执行（这是核心！）
        async for event in self.execute_with_tt(request):
            # 添加阶段信息到事件
            event.data['current_stage'] = stage.value
            yield event

        logger.info(f"✅ 阶段完成: {stage.value}")

    def _apply_stage_config(self, stage_config: Dict[str, Any]):
        """应用阶段配置"""
        # 切换工具集
        self._config.tools.enabled_tools = stage_config['enabled_tools']

        # 切换系统提示
        self._system_prompt = stage_config['system_prompt']

        # 切换质量阈值
        self._config.behavior.quality_threshold = stage_config['quality_threshold']

        # 切换迭代次数
        self._config.max_iterations = stage_config['max_iterations']

        logger.debug(f"📝 已应用阶段配置: {list(stage_config.keys())}")


class StageConfigManager:
    """阶段配置管理器"""

    def __init__(self):
        self.stage_configs = {
            ExecutionStage.SQL_GENERATION: {
                'enabled_tools': [
                    'schema_discovery',
                    'schema_retrieval',
                    'schema_cache',
                    'sql_generator',
                    'sql_validator',
                    'sql_column_checker',
                    'sql_auto_fixer',
                    'sql_executor',
                ],
                'system_prompt': self._get_sql_stage_prompt(),
                'quality_threshold': 0.8,
                'max_iterations': 8,
                'stage_goal': '生成准确、高效的SQL查询',
            },

            ExecutionStage.CHART_GENERATION: {
                'enabled_tools': [
                    'data_analyzer',
                    'chart_type_selector',
                    'chart_generator',
                    'chart_validator',
                    'data_sampler',
                ],
                'system_prompt': self._get_chart_stage_prompt(),
                'quality_threshold': 0.75,
                'max_iterations': 6,
                'stage_goal': '生成合适的数据可视化配置',
            },

            ExecutionStage.DOCUMENT_GENERATION: {
                'enabled_tools': [
                    'paragraph_analyzer',
                    'text_generator',
                    'style_checker',
                    'consistency_validator',
                ],
                'system_prompt': self._get_document_stage_prompt(),
                'quality_threshold': 0.85,
                'max_iterations': 5,
                'stage_goal': '生成流畅、准确的文档文本',
            }
        }

    def get_stage_config(self, stage: ExecutionStage) -> Dict[str, Any]:
        """获取阶段配置"""
        return self.stage_configs.get(stage, {})

    def _get_sql_stage_prompt(self) -> str:
        """SQL阶段系统提示"""
        return """你是一个SQL生成专家。

# 你的任务
根据业务需求生成准确的SQL查询。

# TT递归流程
1. **Thought**: 分析需求，理解数据关系
2. **Tool**: 使用schema工具了解表结构
3. **Thought**: 设计查询逻辑
4. **Tool**: 使用sql_generator生成SQL
5. **Thought**: 评估SQL质量
6. **Tool**: 使用sql_validator验证SQL
7. **Thought**: 如果有问题，分析原因
8. **Tool**: 使用sql_auto_fixer修复问题
9. **Thought**: 再次验证，直到达到质量阈值

# 质量标准
- 语法正确性: 100%
- 字段存在性: 100%
- 逻辑正确性: 90%+
- 性能优化: 80%+

持续使用TT递归迭代，直到SQL达到最优状态！
"""

    def _get_chart_stage_prompt(self) -> str:
        """图表阶段系统提示"""
        return """你是一个数据可视化专家。

# 你的任务
根据数据特征选择并生成最合适的图表配置。

# TT递归流程
1. **Thought**: 分析数据特征（分布、趋势、关系）
2. **Tool**: 使用data_analyzer分析数据
3. **Thought**: 根据数据特征选择图表类型
4. **Tool**: 使用chart_type_selector确定最佳图表
5. **Thought**: 设计图表元素映射
6. **Tool**: 使用chart_generator生成配置
7. **Thought**: 评估图表合理性
8. **Tool**: 使用chart_validator验证配置
9. **Thought**: 如果需要，优化配置
10. **Tool**: 重新生成，直到达到最优效果

# 质量标准
- 图表类型适配度: 90%+
- 数据映射正确性: 100%
- 可读性: 85%+
- 美观度: 80%+

持续迭代，选择最能表达数据的可视化方式！
"""

    def _get_document_stage_prompt(self) -> str:
        """文档阶段系统提示"""
        return """你是一个专业文档写作专家。

# 你的任务
基于数据，生成流畅、准确、专业的文档段落。

# TT递归流程
1. **Thought**: 理解段落上下文和数据含义
2. **Tool**: 使用paragraph_analyzer分析段落结构
3. **Thought**: 设计表达方式
4. **Tool**: 使用text_generator生成文本
5. **Thought**: 评估文本质量
6. **Tool**: 使用style_checker检查风格
7. **Thought**: 识别改进点
8. **Tool**: 使用consistency_validator检查一致性
9. **Thought**: 如果有问题，重新生成
10. **Tool**: 迭代优化，直到达到最优

# 质量标准
- 数据准确性: 100%
- 语言流畅性: 90%+
- 风格一致性: 85%+
- 专业度: 85%+

持续优化，生成高质量的专业文档！
"""
```

---

### 2. Stage-Aware Facade

```python
class StageAwareFacade(LoomAgentFacade):
    """
    阶段感知的Facade

    对外提供三阶段接口，内部保留TT递归能力
    """

    def __init__(self, container, config=None):
        super().__init__(container, config)

        # 创建Stage-Aware Runtime
        self._runtime = StageAwareRuntime(container, self.config)

        # 模型选择器
        self.model_switcher = DynamicModelSwitcher(user_model_resolver)

        # 阶段结果缓存
        self.stage_results: Dict[str, Any] = {}

    async def execute_sql_generation_stage(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行SQL生成阶段（使用TT递归）

        内部会自动迭代优化：
        - 发现Schema
        - 生成SQL
        - 验证SQL
        - 修复问题
        - 再次验证
        - ... 直到达到质量阈值

        Yields:
            AgentEvent: 包含所有TT递归步骤的事件
        """
        logger.info("🎯 [SQL生成阶段] 开始执行（TT递归模式）")

        # 1. 模型自主选择
        model_config = await self.model_switcher.assess_and_select_model(
            task_description=f"SQL生成: {placeholder}",
            user_id=user_id,
            task_type="sql_generation"
        )

        # 2. 初始化（如果需要）
        if not self._initialized:
            await self.initialize(
                user_id=user_id,
                task_type="sql_generation",
                task_complexity=model_config['complexity_assessment']['complexity_score']
            )

        # 3. 创建请求
        request = AgentRequest(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            task_context=kwargs.get('task_context', {}),
            template_context=kwargs.get('template_context'),
            max_iterations=8,  # SQL阶段的迭代次数
            complexity=TaskComplexity.MEDIUM,
            constraints=kwargs.get('constraints', {})
        )

        # 4. 使用TT递归执行（核心！）
        async for event in self._runtime.execute_with_stage(
            request=request,
            stage=ExecutionStage.SQL_GENERATION
        ):
            # 记录TT递归的每一步
            if event.event_type == 'thought_generated':
                logger.debug(f"💭 [SQL阶段] Thought: {event.data.get('thought', '')[:100]}...")
            elif event.event_type == 'tool_called':
                logger.debug(f"🔧 [SQL阶段] Tool: {event.data.get('tool_name')}")
            elif event.event_type == 'iteration_completed':
                logger.info(f"🔄 [SQL阶段] 迭代 {event.data.get('iteration')}: 质量={event.data.get('quality_score', 0):.2f}")

            yield event

        logger.info("✅ [SQL生成阶段] 完成（TT递归自动优化）")

    async def execute_chart_generation_stage(
        self,
        etl_data: Dict[str, Any],
        chart_placeholder: str,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行图表生成阶段（使用TT递归）

        内部会自动迭代优化：
        - 分析数据特征
        - 选择图表类型
        - 生成图表配置
        - 验证配置
        - 优化配置
        - ... 直到达到最优

        Yields:
            AgentEvent: 包含所有TT递归步骤的事件
        """
        logger.info("🎯 [图表生成阶段] 开始执行（TT递归模式）")

        # 1. 模型自主选择
        model_config = await self.model_switcher.assess_and_select_model(
            task_description=f"图表生成: {chart_placeholder}",
            user_id=user_id,
            task_type="chart_generation"
        )

        # 2. 创建请求
        request = AgentRequest(
            placeholder=chart_placeholder,
            data_source_id=kwargs.get('data_source_id', 0),
            user_id=user_id,
            task_context={
                'etl_data': etl_data,
                'statistics': kwargs.get('statistics', {}),
                **kwargs.get('task_context', {})
            },
            max_iterations=6,  # 图表阶段的迭代次数
            complexity=TaskComplexity.MEDIUM,
            constraints={'output_format': 'chart_config'}
        )

        # 3. 使用TT递归执行
        async for event in self._runtime.execute_with_stage(
            request=request,
            stage=ExecutionStage.CHART_GENERATION
        ):
            if event.event_type == 'thought_generated':
                logger.debug(f"💭 [图表阶段] Thought: {event.data.get('thought', '')[:100]}...")
            elif event.event_type == 'tool_called':
                logger.debug(f"🔧 [图表阶段] Tool: {event.data.get('tool_name')}")

            yield event

        logger.info("✅ [图表生成阶段] 完成（TT递归自动优化）")

    async def execute_document_generation_stage(
        self,
        paragraph_context: str,
        placeholder_data: Dict[str, Any],
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行文档生成阶段（使用TT递归）

        内部会自动迭代优化：
        - 分析段落结构
        - 生成文本
        - 检查风格
        - 验证一致性
        - 优化表达
        - ... 直到达到最优

        Yields:
            AgentEvent: 包含所有TT递归步骤的事件
        """
        logger.info("🎯 [文档生成阶段] 开始执行（TT递归模式）")

        # 1. 模型自主选择
        model_config = await self.model_switcher.assess_and_select_model(
            task_description=f"文档生成: {paragraph_context[:100]}",
            user_id=user_id,
            task_type="document_generation"
        )

        # 2. 创建请求
        request = AgentRequest(
            placeholder=paragraph_context,
            data_source_id=kwargs.get('data_source_id', 0),
            user_id=user_id,
            task_context={
                'paragraph_context': paragraph_context,
                'placeholder_data': placeholder_data,
                'document_context': kwargs.get('document_context', {}),
                **kwargs.get('task_context', {})
            },
            max_iterations=5,  # 文档阶段的迭代次数
            complexity=TaskComplexity.MEDIUM,
            constraints={'output_format': 'text'}
        )

        # 3. 使用TT递归执行
        async for event in self._runtime.execute_with_stage(
            request=request,
            stage=ExecutionStage.DOCUMENT_GENERATION
        ):
            if event.event_type == 'thought_generated':
                logger.debug(f"💭 [文档阶段] Thought: {event.data.get('thought', '')[:100]}...")
            elif event.event_type == 'tool_called':
                logger.debug(f"🔧 [文档阶段] Tool: {event.data.get('tool_name')}")

            yield event

        logger.info("✅ [文档生成阶段] 完成（TT递归自动优化）")

    async def execute_full_pipeline(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        执行完整的三阶段Pipeline

        每个阶段内部都使用TT递归自动优化

        Yields:
            AgentEvent: 所有阶段的所有事件
        """
        logger.info("🚀 [三阶段Pipeline] 开始执行（每个阶段都使用TT递归）")

        # 阶段1：SQL生成（TT递归）
        sql_result = None
        async for event in self.execute_sql_generation_stage(
            placeholder=placeholder,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        ):
            if event.event_type == 'execution_completed':
                sql_result = event.data.get('response')
            yield event

        # 阶段2：图表生成（TT递归）- 如果需要
        chart_result = None
        if sql_result and kwargs.get('need_chart', False):
            async for event in self.execute_chart_generation_stage(
                etl_data=sql_result.get('etl_data', {}),
                chart_placeholder=kwargs.get('chart_placeholder', ''),
                user_id=user_id,
                **kwargs
            ):
                if event.event_type == 'execution_completed':
                    chart_result = event.data.get('response')
                yield event

        # 阶段3：文档生成（TT递归）
        if sql_result:
            async for event in self.execute_document_generation_stage(
                paragraph_context=kwargs.get('paragraph_context', ''),
                placeholder_data=sql_result.get('placeholder_data', {}),
                user_id=user_id,
                **kwargs
            ):
                yield event

        logger.info("✅ [三阶段Pipeline] 完成")
```

---

## 🔄 TT递归在每个阶段的体现

### 阶段1：SQL生成的TT递归

```
Iteration 1:
  💭 Thought: "我需要先了解表结构"
  🔧 Tool: schema_discovery() -> 发现3个相关表
  💭 Thought: "现在我知道了表结构，可以生成SQL了"
  🔧 Tool: sql_generator() -> 生成初始SQL
  💭 Thought: "让我验证一下这个SQL"
  🔧 Tool: sql_validator() -> 发现字段名错误
  📊 Quality Score: 0.4 (未达到阈值0.8)

Iteration 2:
  💭 Thought: "发现字段名错误，我需要修复"
  🔧 Tool: sql_auto_fixer() -> 修复字段名
  💭 Thought: "让我再次验证"
  🔧 Tool: sql_validator() -> 验证通过
  💭 Thought: "再检查一下性能"
  🔧 Tool: sql_executor(dry_run=True) -> 性能良好
  📊 Quality Score: 0.85 (达到阈值！)

✅ 输出最优SQL
```

### 阶段2：图表生成的TT递归

```
Iteration 1:
  💭 Thought: "首先分析数据特征"
  🔧 Tool: data_analyzer() -> 数据是时间序列，有明显趋势
  💭 Thought: "时间序列适合用折线图"
  🔧 Tool: chart_type_selector() -> 推荐折线图
  💭 Thought: "生成折线图配置"
  🔧 Tool: chart_generator() -> 生成基础配置
  📊 Quality Score: 0.65 (未达到阈值0.75)

Iteration 2:
  💭 Thought: "配置太简单，需要优化"
  🔧 Tool: chart_validator() -> 建议添加趋势线和数据标签
  💭 Thought: "添加高级特性"
  🔧 Tool: chart_generator(enhanced=True) -> 生成增强配置
  📊 Quality Score: 0.82 (达到阈值！)

✅ 输出最优图表配置
```

### 阶段3：文档生成的TT递归

```
Iteration 1:
  💭 Thought: "分析段落的语义和风格"
  🔧 Tool: paragraph_analyzer() -> 正式商务风格，需要数据支撑
  💭 Thought: "基于数据生成文本"
  🔧 Tool: text_generator() -> 生成初始文本
  💭 Thought: "检查风格是否一致"
  🔧 Tool: style_checker() -> 发现语气不够正式
  📊 Quality Score: 0.70 (未达到阈值0.85)

Iteration 2:
  💭 Thought: "需要调整为更正式的语气"
  🔧 Tool: text_generator(style='formal') -> 重新生成
  💭 Thought: "验证一致性"
  🔧 Tool: consistency_validator() -> 检查通过
  📊 Quality Score: 0.88 (达到阈值！)

✅ 输出最优文档文本
```

---

## 🎯 关键优势

### 1. **保留TT递归的核心能力**
- 每个阶段内部都是完整的TT递归流程
- Agent能够自动迭代优化，直到达到质量阈值
- 不需要人工干预，完全自动化

### 2. **阶段专用工具和提示词**
- 每个阶段只加载相关工具，减少上下文
- 每个阶段有专门的系统提示，提供精确指导
- 提高执行效率和结果质量

### 3. **灵活的模型选择**
- 每个阶段独立进行复杂度评估和模型选择
- 可以为不同阶段使用不同的模型
- 优化成本和性能

### 4. **完整的可观测性**
- 可以观察到每个阶段的每一步TT递归
- 便于调试和优化
- 提供详细的执行日志

---

## 📊 与原架构对比

| 特性 | 单一Agent | 三个独立Agent❌ | Stage-Aware Agent✅ |
|------|-----------|----------------|---------------------|
| TT递归能力 | ✅ 有 | ❌ 丢失 | ✅ 保留 |
| 工具专用性 | ❌ 所有工具混在一起 | ✅ 专用工具 | ✅ 专用工具 |
| 提示词精确性 | ❌ 通用提示 | ✅ 专用提示 | ✅ 专用提示 |
| 上下文大小 | ❌ 大 | ✅ 小 | ✅ 小 |
| 自动优化 | ✅ TT递归 | ❌ 无 | ✅ TT递归 |
| 阶段协调 | ❌ 无阶段概念 | ❌ 需要外部协调 | ✅ 内置协调 |
| 质量保证 | ⚠️ 通用阈值 | ⚠️ 难以迭代 | ✅ 阶段专用阈值+迭代 |

---

## 🔧 实施步骤

### Step 1: 创建StageAwareRuntime
```bash
backend/app/services/infrastructure/agents/
└── runtime.py  # 扩展现有的LoomAgentRuntime
```

### Step 2: 创建StageConfigManager
```bash
backend/app/services/infrastructure/agents/config/
└── stage_config.py  # 管理各阶段配置
```

### Step 3: 扩展Facade
```bash
backend/app/services/infrastructure/agents/
└── facade.py  # 添加Stage-Aware方法
```

### Step 4: 更新Prompts
```bash
backend/app/services/infrastructure/agents/prompts/
└── stages.py  # 添加各阶段专用提示词
```

---

## ✅ 成功标准

1. ✅ 每个阶段内部保留完整的TT递归能力
2. ✅ 阶段之间可以正确切换工具集和提示词
3. ✅ 可以观察到每个阶段的迭代优化过程
4. ✅ 每个阶段都能达到预设的质量阈值
5. ✅ 整体执行时间和Token使用量优化
6. ✅ 代码简洁，易于维护

---

## 🎉 总结

**这个设计的核心思想是：**

1. **不创建独立Agent** - 避免丢失TT递归能力
2. **Stage-Aware配置切换** - 根据阶段动态调整工具和提示
3. **保留TT递归** - 每个阶段内部完整的迭代优化流程
4. **自动质量保证** - TT递归自动迭代直到达到阈值

这样既保留了Loom Agent的核心优势（TT递归），又实现了三阶段的清晰分离！🚀
