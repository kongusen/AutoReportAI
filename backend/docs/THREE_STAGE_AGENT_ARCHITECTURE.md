# 三阶段Agent架构设计

## 📋 概述

AutoReportAI的Agent系统不是单一的串型结构，而是由**三个独立但协作的阶段**组成的Pipeline系统。每个阶段有自己的专用Agent、工具集和提示词。

## 🎯 三个核心阶段

### 阶段1：SQL生成与验证阶段（SQL Generation Stage）

**目标**：根据模板、数据源、任务信息生成带占位符的SQL并验证

**输入**：
- 模板信息（template_context）
- 数据源配置（data_source_id）
- 任务上下文（task_context）
- 占位符描述（placeholder）

**输出**：
- 验证通过的SQL查询
- SQL质量评分
- 字段验证结果

**专用工具**：
```python
[
    "schema_discovery",      # Schema发现
    "schema_retrieval",      # Schema检索
    "schema_cache",          # Schema缓存
    "sql_generator",         # SQL生成
    "sql_validator",         # SQL验证
    "sql_column_checker",    # SQL字段检查
    "sql_auto_fixer",        # SQL自动修复
]
```

**执行流程**：
```
1. Schema Discovery -> 发现相关表结构
2. SQL Generation -> 生成带占位符的SQL
3. SQL Validation -> 验证SQL语法和语义
4. Column Checking -> 检查字段是否存在
5. Auto Fixing -> 自动修复发现的问题
6. Final Validation -> 最终验证
```

**阶段特点**：
- 高度依赖Schema上下文
- 需要精确的字段验证
- 支持迭代式修复
- 质量阈值：0.8

---

### 阶段2：图表生成阶段（Chart Generation Stage）

**目标**：基于ETL分析后的数据，生成数据统计图表

**输入**：
- ETL处理后的数据（etl_data）
- 图表占位符要求（chart_placeholder）
- 数据统计信息（statistics）
- 业务上下文（business_context）

**输出**：
- 图表配置（chart_config）
- 图表类型选择
- 数据映射关系
- 可视化参数

**专用工具**：
```python
[
    "chart_type_selector",   # 图表类型选择
    "chart_data_analyzer",   # 图表数据分析
    "chart_generator",       # 图表生成
    "chart_validator",       # 图表验证
    "data_sampler",          # 数据采样
    "data_analyzer",         # 数据分析
]
```

**执行流程**：
```
1. Data Analysis -> 分析数据特征（分布、趋势、异常）
2. Chart Type Selection -> 选择合适的图表类型
3. Data Mapping -> 建立数据字段到图表元素的映射
4. Chart Configuration -> 生成图表配置参数
5. Validation -> 验证图表配置的正确性
```

**阶段特点**：
- 专注于数据可视化
- 需要理解数据分布特征
- 支持多种图表类型（柱状图、折线图、饼图、散点图等）
- 质量阈值：0.75

---

### 阶段3：文档生成阶段（Document Generation Stage）

**目标**：基于占位符所在自然段进行分析，基于数据进行重新表达

**输入**：
- 回填数据后的模板（filled_template）
- 占位符所在段落（paragraph_context）
- 占位符数据值（placeholder_data）
- 文档上下文（document_context）

**输出**：
- 重新表达的段落文本
- 语言风格评分
- 一致性检查结果

**专用工具**：
```python
[
    "paragraph_analyzer",     # 段落分析
    "data_interpreter",       # 数据解释
    "text_generator",         # 文本生成
    "style_checker",          # 风格检查
    "consistency_validator",  # 一致性验证
]
```

**执行流程**：
```
1. Paragraph Analysis -> 分析段落的语义和风格
2. Data Interpretation -> 解释占位符数据的含义
3. Context Understanding -> 理解文档上下文
4. Text Generation -> 基于数据重新表达段落
5. Style Checking -> 检查语言风格一致性
6. Final Validation -> 验证生成文本的质量
```

**阶段特点**：
- 需要强大的自然语言理解和生成能力
- 保持文档风格一致性
- 支持多种表达方式
- 质量阈值：0.85

---

## 🏗️ 架构设计

### 1. 三阶段Agent架构

```python
class ThreeStageAgentPipeline:
    """三阶段Agent Pipeline"""

    def __init__(self, container):
        self.container = container

        # 三个独立的Agent实例
        self.sql_agent = SQLGenerationAgent(container)
        self.chart_agent = ChartGenerationAgent(container)
        self.document_agent = DocumentGenerationAgent(container)

        # 模型自主选择器
        self.model_switcher = DynamicModelSwitcher(user_model_resolver)

        # 阶段协调器
        self.stage_coordinator = StageCoordinator()

    async def execute_sql_stage(
        self,
        placeholder: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> SQLStageResult:
        """执行阶段1：SQL生成与验证"""

        # 1. LLM自主判断任务复杂度和模型选择
        model_config = await self.model_switcher.assess_and_select_model(
            task_description=f"SQL生成: {placeholder}",
            user_id=user_id,
            task_type="sql_generation"
        )

        # 2. 初始化SQL Agent
        await self.sql_agent.initialize(user_id, model_config)

        # 3. 执行SQL生成
        result = await self.sql_agent.generate_and_validate_sql(
            placeholder=placeholder,
            data_source_id=data_source_id,
            **kwargs
        )

        return result

    async def execute_chart_stage(
        self,
        etl_data: Dict[str, Any],
        chart_placeholder: str,
        user_id: str,
        **kwargs
    ) -> ChartStageResult:
        """执行阶段2：图表生成"""

        # 1. LLM自主判断任务复杂度和模型选择
        model_config = await self.model_switcher.assess_and_select_model(
            task_description=f"图表生成: {chart_placeholder}",
            user_id=user_id,
            task_type="chart_generation"
        )

        # 2. 初始化Chart Agent
        await self.chart_agent.initialize(user_id, model_config)

        # 3. 执行图表生成
        result = await self.chart_agent.generate_chart(
            etl_data=etl_data,
            chart_placeholder=chart_placeholder,
            **kwargs
        )

        return result

    async def execute_document_stage(
        self,
        filled_template: str,
        paragraph_context: str,
        placeholder_data: Dict[str, Any],
        user_id: str,
        **kwargs
    ) -> DocumentStageResult:
        """执行阶段3：文档生成"""

        # 1. LLM自主判断任务复杂度和模型选择
        model_config = await self.model_switcher.assess_and_select_model(
            task_description=f"文档生成: {paragraph_context[:100]}",
            user_id=user_id,
            task_type="document_generation"
        )

        # 2. 初始化Document Agent
        await self.document_agent.initialize(user_id, model_config)

        # 3. 执行文档生成
        result = await self.document_agent.generate_paragraph(
            filled_template=filled_template,
            paragraph_context=paragraph_context,
            placeholder_data=placeholder_data,
            **kwargs
        )

        return result

    async def execute_full_pipeline(
        self,
        template: str,
        data_source_id: int,
        user_id: str,
        **kwargs
    ) -> PipelineResult:
        """执行完整的三阶段Pipeline"""

        # 阶段1：SQL生成
        sql_result = await self.execute_sql_stage(
            placeholder=template,
            data_source_id=data_source_id,
            user_id=user_id,
            **kwargs
        )

        # 阶段2：图表生成（如果需要）
        chart_result = None
        if sql_result.has_chart_placeholders:
            chart_result = await self.execute_chart_stage(
                etl_data=sql_result.etl_data,
                chart_placeholder=sql_result.chart_placeholders,
                user_id=user_id,
                **kwargs
            )

        # 阶段3：文档生成
        document_result = await self.execute_document_stage(
            filled_template=sql_result.filled_template,
            paragraph_context=sql_result.paragraph_context,
            placeholder_data=sql_result.placeholder_data,
            user_id=user_id,
            **kwargs
        )

        return PipelineResult(
            sql_result=sql_result,
            chart_result=chart_result,
            document_result=document_result
        )
```

### 2. 每个阶段的Agent实现

```python
class SQLGenerationAgent(LoomAgentFacade):
    """阶段1：SQL生成Agent"""

    def __init__(self, container):
        config = self._create_sql_stage_config()
        super().__init__(container, config)

    def _create_sql_stage_config(self) -> AgentConfig:
        """创建SQL阶段专用配置"""
        config = create_default_agent_config()

        # 只启用SQL相关工具
        config.tools.enabled_tools = [
            "schema_discovery", "schema_retrieval", "schema_cache",
            "sql_generator", "sql_validator", "sql_column_checker",
            "sql_auto_fixer"
        ]

        # SQL阶段的特殊配置
        config.max_iterations = 8
        config.behavior.quality_threshold = 0.8
        config.behavior.enable_self_correction = True

        # SQL阶段的系统提示
        config.system_prompt = create_sql_stage_system_prompt()

        return config


class ChartGenerationAgent(LoomAgentFacade):
    """阶段2：图表生成Agent"""

    def __init__(self, container):
        config = self._create_chart_stage_config()
        super().__init__(container, config)

    def _create_chart_stage_config(self) -> AgentConfig:
        """创建图表阶段专用配置"""
        config = create_default_agent_config()

        # 只启用图表相关工具
        config.tools.enabled_tools = [
            "chart_type_selector", "chart_data_analyzer",
            "chart_generator", "chart_validator",
            "data_sampler", "data_analyzer"
        ]

        # 图表阶段的特殊配置
        config.max_iterations = 6
        config.behavior.quality_threshold = 0.75

        # 图表阶段的系统提示
        config.system_prompt = create_chart_stage_system_prompt()

        return config


class DocumentGenerationAgent(LoomAgentFacade):
    """阶段3：文档生成Agent"""

    def __init__(self, container):
        config = self._create_document_stage_config()
        super().__init__(container, config)

    def _create_document_stage_config(self) -> AgentConfig:
        """创建文档阶段专用配置"""
        config = create_default_agent_config()

        # 只启用文档相关工具
        config.tools.enabled_tools = [
            "paragraph_analyzer", "data_interpreter",
            "text_generator", "style_checker",
            "consistency_validator"
        ]

        # 文档阶段的特殊配置
        config.max_iterations = 5
        config.behavior.quality_threshold = 0.85

        # 文档阶段需要更高的language model能力
        config.llm.temperature = 0.3  # 略高于SQL阶段，允许更多创造性

        # 文档阶段的系统提示
        config.system_prompt = create_document_stage_system_prompt()

        return config
```

### 3. 阶段协调器

```python
class StageCoordinator:
    """阶段协调器 - 管理三个阶段之间的数据流和依赖"""

    def __init__(self):
        self.stage_dependencies = {
            "chart_generation": ["sql_generation"],  # 图表依赖SQL结果
            "document_generation": ["sql_generation", "chart_generation"]  # 文档依赖前两个阶段
        }

    async def coordinate_stages(
        self,
        stages: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """协调多个阶段的执行"""

        results = {}

        for stage in stages:
            # 检查依赖
            dependencies = self.stage_dependencies.get(stage, [])
            if not all(dep in results for dep in dependencies):
                raise ValueError(f"阶段 {stage} 的依赖未满足")

            # 准备阶段输入
            stage_input = self._prepare_stage_input(stage, results, context)

            # 执行阶段
            stage_result = await self._execute_stage(stage, stage_input)

            # 保存结果
            results[stage] = stage_result

        return results

    def _prepare_stage_input(
        self,
        stage: str,
        previous_results: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """准备阶段输入"""

        if stage == "chart_generation":
            return {
                "etl_data": previous_results["sql_generation"]["etl_data"],
                "chart_placeholders": previous_results["sql_generation"]["chart_placeholders"],
                **context
            }

        elif stage == "document_generation":
            return {
                "filled_template": previous_results["sql_generation"]["filled_template"],
                "chart_configs": previous_results.get("chart_generation", {}).get("chart_configs", {}),
                "paragraph_context": context.get("paragraph_context"),
                **context
            }

        return context
```

---

## 🔄 模型自主选择在三阶段中的应用

### 每个阶段的复杂度评估维度

#### 阶段1（SQL生成）复杂度评估：
```python
complexity_factors = [
    "数据表数量",           # 1表 vs 多表JOIN
    "聚合复杂度",           # 简单SUM vs 复杂GROUP BY + HAVING
    "子查询深度",           # 无子查询 vs 多层嵌套
    "窗口函数使用",         # 是否需要窗口函数
    "时间处理复杂度",       # 简单日期 vs 复杂时间序列分析
]
```

#### 阶段2（图表生成）复杂度评估：
```python
complexity_factors = [
    "数据维度数量",         # 1维 vs 多维数据
    "图表类型复杂度",       # 简单柱状图 vs 复杂组合图
    "数据转换需求",         # 直接映射 vs 复杂计算转换
    "交互功能需求",         # 静态图 vs 交互式图表
    "数据量大小",           # 少量数据 vs 大数据集
]
```

#### 阶段3（文档生成）复杂度评估：
```python
complexity_factors = [
    "段落长度",             # 短句 vs 长段落
    "数据点数量",           # 单一数据点 vs 多数据点综合
    "表达深度",             # 直接陈述 vs 深度分析
    "风格一致性要求",       # 简单 vs 需要保持特定风格
    "上下文理解需求",       # 独立段落 vs 需要理解全文上下文
]
```

### 模型选择策略

```python
# 阶段1：SQL生成
if complexity_score < 0.4:
    model = "gpt-3.5-turbo"  # 简单SQL，快速模型
elif complexity_score < 0.7:
    model = "gpt-4"           # 中等复杂SQL
else:
    model = "o1-mini"         # 复杂SQL，需要深度推理

# 阶段2：图表生成
if complexity_score < 0.5:
    model = "gpt-3.5-turbo"  # 简单图表
else:
    model = "gpt-4"           # 复杂图表配置

# 阶段3：文档生成
if complexity_score < 0.5:
    model = "gpt-4"           # 基础表达也需要好的语言能力
else:
    model = "o1-mini"         # 复杂表达需要深度推理
```

---

## 📝 实施步骤

### Step 1: 创建三个阶段的Agent类
- [ ] 创建 `SQLGenerationAgent`
- [ ] 创建 `ChartGenerationAgent`
- [ ] 创建 `DocumentGenerationAgent`

### Step 2: 为每个阶段创建专用工具
- [ ] SQL阶段：已有工具完善
- [ ] 图表阶段：实现图表相关工具
- [ ] 文档阶段：实现文档生成相关工具

### Step 3: 创建阶段协调器
- [ ] 实现 `StageCoordinator`
- [ ] 实现依赖管理
- [ ] 实现数据流转

### Step 4: 集成模型自主选择
- [ ] **修复模型选择工具的LLM评估**（关键！）
- [ ] 为每个阶段配置独立的模型选择策略
- [ ] 实现模型切换的统计和监控

### Step 5: 创建三阶段Pipeline
- [ ] 实现 `ThreeStageAgentPipeline`
- [ ] 实现完整流程编排
- [ ] 实现错误处理和重试

### Step 6: 更新Facade接口
- [ ] 添加三阶段的独立接口
- [ ] 保持向后兼容
- [ ] 添加Pipeline接口

---

## 🎯 关键优势

### 1. **清晰的职责分离**
每个阶段专注于自己的任务，避免了单一Agent承担过多职责

### 2. **独立的工具集**
每个阶段只加载需要的工具，减少上下文长度，提高效率

### 3. **灵活的模型选择**
每个阶段可以根据任务复杂度选择最合适的模型，而不是"一刀切"

### 4. **更好的可维护性**
各阶段独立开发、测试和优化

### 5. **更高的可扩展性**
未来可以轻松添加新阶段（如数据质量检查阶段、报告审核阶段等）

### 6. **更精确的提示词**
每个阶段有专门的系统提示，提供更精确的指导

---

## 🚀 下一步行动

1. **立即修复**：修复模型选择工具的LLM评估功能
2. **创建阶段Agent**：实现三个独立的Agent类
3. **实现阶段协调器**：管理阶段间的数据流
4. **创建Pipeline**：实现完整的三阶段流程
5. **测试和优化**：对每个阶段进行独立测试

---

## 📊 预期效果

- **SQL生成准确率**: 95%+（当前约85%）
- **图表配置正确率**: 90%+（当前未独立统计）
- **文档质量评分**: 4.5/5（当前未独立统计）
- **整体执行时间**: 减少30%（通过精确的工具选择和模型选择）
- **Token使用量**: 减少40%（通过阶段化的上下文管理）
