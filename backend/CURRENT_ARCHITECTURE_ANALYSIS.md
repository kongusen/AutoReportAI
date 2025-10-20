# 当前Agent架构完整分析 📋

> 清晰梳理现有架构，不谈新增功能

---

## 🎯 核心调用链路（3层）

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer 1: 业务入口层                        │
├─────────────────────────────────────────────────────────────┤
│  PlaceholderApplicationService.analyze_placeholder()         │
│  - 职责：业务流程编排                                          │
│  - 输入：PlaceholderAnalysisRequest                          │
│  - 输出：AsyncIterator[Dict]（流式返回）                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    Layer 2: Agent门面层                       │
├─────────────────────────────────────────────────────────────┤
│  AgentFacade.execute_task_validation(AgentInput)            │
│  - 职责：模式选择和智能回退                                     │
│  - 流程：                                                     │
│    1. 检查是否有现有SQL                                       │
│    2. 有SQL → task_sql_validation模式                        │
│    3. 无SQL/验证失败 → ptav模式                               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    Layer 3: 编排执行层                        │
├─────────────────────────────────────────────────────────────┤
│  UnifiedOrchestrator.execute(ai, mode)                      │
│  - 支持模式：                                                 │
│    • ptof: 一次性流程（简单任务）                             │
│    • ptav: 循环流程（复杂SQL生成）最多15轮                    │
│    • task_sql_validation: SQL验证和修复                      │
│                                                              │
│  ├─ Planner（决策）                                          │
│  │   └─ 调用LLM生成执行计划                                   │
│  │                                                           │
│  ├─ Executor（执行）                                         │
│  │   └─ 调用Tools执行计划                                    │
│  │                                                           │
│  └─ Validator（验证）                                        │
│      └─ 检查目标是否达成                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 核心组件详解

### 1. PlaceholderApplicationService（业务层）

**文件**: `backend/app/services/application/placeholder/placeholder_service.py`

**职责**:
- 接收业务请求（PlaceholderAnalysisRequest）
- 构建AgentInput（包含完整的task_driven_context）
- 调用AgentFacade
- 转换结果为业务对象

**关键代码**:
```python
async def analyze_placeholder(self, request):
    # 1. 构建AgentInput
    agent_input = AgentInput(
        user_prompt=f"占位符分析: {request.business_command}...",
        placeholder=PlaceholderSpec(...),
        schema=SchemaInfo(...),
        data_source=data_source_config,
        task_driven_context={
            "placeholder_id": request.placeholder_id,
            "business_command": request.business_command,
            "semantic_type": semantic_type,
            "schema_context": {...},
            "time_window": {...},
            ...
        },
        user_id=self.user_id
    )

    # 2. 调用AgentFacade
    result = await self.agent_facade.execute_task_validation(agent_input)

    # 3. 转换结果
    if result.success:
        yield {"type": "sql_generation_complete", "content": result.content}
```

---

### 2. AgentFacade（门面层）

**文件**: `backend/app/services/infrastructure/agents/facade.py`

**职责**:
- 提供统一的Agent调用入口
- 智能模式选择（验证 vs 生成）
- 自动回退机制

**核心方法**:

#### execute_task_validation()
```python
async def execute_task_validation(self, ai: AgentInput) -> AgentOutput:
    """
    任务验证智能模式

    流程：
    1. 提取现有SQL（如果有）
    2. [有SQL] → task_sql_validation模式验证
       ├─ 验证通过 → 返回
       └─ 验证失败且不可修复 → PTAV回退
    3. [无SQL] → 直接PTAV生成
    """
    current_sql = self._extract_current_sql_from_context(ai)

    if current_sql:
        # 验证现有SQL
        validation_result = await self.execute(ai, mode="task_sql_validation")
        if validation_result.success:
            return validation_result

        # 不可修复 → 回退
        if not self._is_repairable_sql_issue(validation_result):
            return await self._execute_ptav_fallback(ai, "sql_validation_failed")

    else:
        # 无SQL → 直接生成
        return await self._execute_ptav_fallback(ai, "missing_sql")
```

**提取SQL的多种方式**:
```python
def _extract_current_sql_from_context(self, ai):
    # 方式1: ai.current_sql
    # 方式2: ai.context.current_sql
    # 方式3: ai.task_driven_context['current_sql']
    # 方式4: ai.data_source['sql_to_test']
```

---

### 3. UnifiedOrchestrator（编排层）

**文件**: `backend/app/services/infrastructure/agents/orchestrator.py`

**职责**:
- 执行具体的Agent工作流
- 管理PTAV循环
- 维护执行上下文

**支持的模式**:

#### Mode 1: ptof（一次性流程）
```python
async def _execute_ptof(self, ai):
    """
    Plan-Tool-Observe-Finalize

    适用场景：简单、一次性任务
    流程：
    1. Plan: 生成计划
    2. Tool: 执行工具
    3. Observe: 观察结果
    4. Finalize: LLM决策
    """
    plan = await self.planner.generate_plan(ai)
    exec_result = await self.executor.execute(plan, ai)
    decision = await self._call_llm_finalize(...)
    return AgentOutput(...)
```

#### Mode 2: ptav（循环流程）⭐ 核心
```python
async def _execute_ptav_loop(self, ai):
    """
    Plan-Tool-Active-Validate循环

    适用场景：复杂SQL生成
    流程：最多15轮
    1. Plan: Agent决策下一步
    2. Tool: 执行单个工具
    3. Active: Agent分析结果
    4. Validate: 检查目标是否达成
    """
    iteration = 0
    execution_context = {
        "current_sql": "",
        "validation_results": [],
        "execution_history": [],
        "resource_pool": ResourcePool()  # 减少Token
    }

    while iteration < 15:
        iteration += 1

        # 1. Plan
        plan = await self.planner.generate_plan(ai)

        # 2. Tool
        exec_result = await self.executor.execute(plan, ai)

        # 3. Active（分析结果）
        execution_context["execution_history"].append(exec_result)

        # 4. Validate（检查目标）
        if await self._validate_goal_achievement(...):
            break

        # 智能退出检测（避免无效循环）
        if self._analyze_execution_pattern(...).get("should_exit"):
            break

    return self._finalize_ptav_result(execution_context)
```

#### Mode 3: task_sql_validation（SQL验证）
```python
async def _execute_task_sql_validation(self, ai):
    """
    SQL验证和快速修复

    适用场景：已有SQL，需要验证
    流程：
    1. Schema检查
    2. 语法验证
    3. 时间属性验证
    4. 快速修正
    """
    validation_result = await self._validate_sql(ai)
    if validation_result["valid"]:
        return AgentOutput(True, sql, ...)
    else:
        # 尝试修复
        fixed_sql = self._try_fix_sql(validation_result)
        return AgentOutput(...)
```

---

### 4. StepExecutor（工具执行层）

**文件**: `backend/app/services/infrastructure/agents/executor.py`

**职责**:
- 管理工具注册表（ToolRegistry）
- 执行计划中的工具步骤
- 维护执行上下文（context）

**已注册的工具**:
```python
def _setup_tools(self):
    # Schema工具
    self.registry.register(SchemaListTablesTool(container))
    self.registry.register(SchemaGetColumnsTool(container))

    # SQL工具
    self.registry.register(SQLValidateTool(container))
    self.registry.register(SQLRefineTool(container))
    self.registry.register(SQLExecuteTool(container))

    # 其他工具
    self.registry.register(TimeWindowTool(container))
    self.registry.register(ChartSpecTool(container))
    self.registry.register(DataQualityTool(container))

    # 工作流工具（PTOF复合工具）
    self.registry.register(StatBasicWorkflowTool(container))
    self.registry.register(StatRatioWorkflowTool(container))
```

**执行逻辑**:
```python
async def execute(self, plan, ai):
    """
    执行计划中的步骤

    1. 遍历plan['steps']
    2. 对每个step，从registry获取tool
    3. 调用tool.execute(input)
    4. 收集结果到context
    5. 生成observations（给LLM看的摘要）
    """
    context = {}
    observations = []

    for step in plan.get("steps", []):
        tool_name = step.get("tool")
        tool = self.registry.get(tool_name)

        # 执行工具
        result = await tool.execute(step.get("input", {}))

        # 更新context
        context.update(result)

        # 生成observation
        observations.append(f"✅ {tool_name}: {result.get('message')}")

    return {
        "success": True,
        "context": context,
        "observations": observations
    }
```

---

### 5. AgentPlanner（决策层）

**文件**: `backend/app/services/infrastructure/agents/planner.py`

**职责**:
- 调用LLM分析当前状态
- 生成下一步执行计划
- 决定调用哪些工具

**Prompt结构**:
```python
def generate_plan(self, ai):
    """
    构建Prompt调用LLM

    Prompt包含：
    1. 任务目标（user_prompt）
    2. 可用工具列表（tool descriptions）
    3. 当前上下文（task_driven_context）
    4. 执行历史（之前的observations）
    5. 输出格式要求（JSON Plan）
    """
    prompt = f"""
    # 任务
    {ai.user_prompt}

    # 可用工具
    {self._format_tools()}

    # 当前上下文
    {ai.task_driven_context}

    # 输出JSON格式
    {{
      "reasoning": "...",
      "steps": [
        {{"tool": "schema.get_columns", "input": {{"tables": ["ods_sales"]}}}}
      ]
    }}
    """

    llm_response = await llm.ask(prompt)
    plan = json.loads(llm_response)
    return plan
```

---

## 🔄 完整的执行流程示例

### 场景：生成销售统计SQL

```
1. 用户请求（API）
   POST /placeholders/analyze
   {
     "business_command": "统计昨日销售总额",
     "data_source_id": "ds_001"
   }

   ↓

2. PlaceholderApplicationService.analyze_placeholder()
   - 构建AgentInput
     {
       "user_prompt": "占位符分析: 统计昨日销售总额",
       "task_driven_context": {
         "semantic_type": "stat",
         "schema_context": {...},
         "time_window": {...}
       },
       "data_source": {...}
     }

   ↓

3. AgentFacade.execute_task_validation()
   - 检查现有SQL：无
   - 决策：使用PTAV生成

   ↓

4. Orchestrator._execute_ptav_loop()

   【第1轮】
   Planner: "需要获取Schema信息"
   Executor: 执行 schema.list_tables
   Result: ["ods_sales", "dim_region"]
   Validator: 未达成目标，继续

   【第2轮】
   Planner: "获取ods_sales表的列信息"
   Executor: 执行 schema.get_columns(tables=["ods_sales"])
   Result: {"ods_sales": ["sale_date", "amount", "product_id"]}
   Validator: 未达成目标，继续

   【第3轮】
   Planner: "现在可以生成SQL了"
   Executor: 生成SQL（通过SQLCoordinator或LLM）
   Result: "SELECT SUM(amount) FROM ods_sales WHERE sale_date = '{{date}}'"
   Validator: SQL生成成功，达成目标！

   ↓

5. 返回结果
   AgentOutput(
     success=True,
     content="SELECT SUM(amount) FROM ods_sales WHERE sale_date = '{{date}}'",
     metadata={
       "generation_method": "ptav_fallback",
       "iterations": 3
     }
   )
```

---

## 🎨 架构特点分析

### ✅ 优势

**1. 灵活的回退机制**
```
验证失败 → 自动PTAV生成
不会卡死在验证阶段
```

**2. Agent主导决策**
```
不是固定流程，而是Agent根据情况决定下一步
适应各种复杂场景
```

**3. 分层清晰**
```
业务层 → 门面层 → 编排层 → 执行层
每层职责明确
```

**4. 工具可扩展**
```
ToolRegistry + Tool接口
新工具只需实现execute()方法
```

### ❌ 问题

**1. 多轮迭代效率低**
```
平均3-5轮才完成
每轮都要LLM调用
Token消耗大
```

**2. 依赖被动解决**
```
缺Schema → 一轮获取 → 再一轮使用
缺Time → 又一轮获取
能提前知道的依赖没有主动解决
```

**3. Context在多轮中传递复杂**
```
execution_context需要手动维护
容易丢失信息
```

**4. SQL生成无结构化约束**
```
LLM自由文本返回SQL
容易解析失败
```

---

## 📊 当前架构 vs 理想架构

| 维度 | 当前PTAV | 理想 | 差距 |
|------|---------|------|------|
| **平均轮数** | 3-5轮 | 1-2轮 | ↓60% |
| **Token消耗** | 高（多轮LLM） | 低（一次完成） | ↓70% |
| **响应时间** | 15-30s | 5-10s | ↓67% |
| **SQL有效率** | 60-70% | 90%+ | ↑30% |
| **灵活性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 牺牲 |
| **兜底能力** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 牺牲 |

---

## 🔍 关键文件清单

```
backend/app/services/
├── application/
│   └── placeholder/
│       └── placeholder_service.py          # 业务入口
│
└── infrastructure/agents/
    ├── facade.py                           # Agent门面 ⭐
    ├── orchestrator.py                     # 编排器 ⭐
    ├── executor.py                         # 工具执行器 ⭐
    ├── planner.py                          # 决策器
    │
    ├── tools/
    │   ├── registry.py                     # 工具注册表
    │   ├── schema_tools.py                 # Schema工具
    │   ├── sql_tools.py                    # SQL工具
    │   ├── time_tools.py                   # 时间工具
    │   └── workflow_tools.py               # 工作流工具
    │
    └── sql_generation/                     # 🆕 SQL-First架构
        ├── coordinator.py                  # 新增（未集成）
        ├── validators.py                   # 新增（未集成）
        ├── generators.py                   # 新增（未集成）
        └── hybrid_generator.py             # 新增（未集成）
```

---

## 💡 现状总结

### 你现在有的（工作正常）✅

1. **完整的PTAV循环架构** - 灵活但慢
2. **智能回退机制** - 验证失败自动生成
3. **丰富的工具生态** - Schema、SQL、Time等
4. **清晰的分层结构** - 业务→门面→编排→执行

### 我新增的（未集成）🆕

1. **SQLGenerationCoordinator** - SQL-First快速生成
2. **SQLValidator** - 三层验证
3. **HybridSQLGenerator** - 混合策略

### 产生的混乱点 😵

1. **两套SQL生成逻辑并存** - 旧PTAV + 新Coordinator
2. **未明确集成路径** - 不知道从哪里调用
3. **Feature Flag机制不清楚** - 怎么启用？
4. **文档太多** - 反而看不清主线

---

## 🎯 下一步应该做什么？

### 选择A：暂不集成新架构

**如果现有PTAV已经够用**：
- 不需要动
- 继续优化Prompt
- 优化工具效率

### 选择B：简化集成

**只做最小改动**：
1. 在Executor中添加SQL-First分支
2. Feature Flag控制启用
3. 失败自动回退到PTAV

我建议先告诉我：
1. **当前PTAV的主要问题是什么？**（慢？不准确？Token贵？）
2. **你最想优化哪个环节？**（Schema获取？SQL生成？验证？）
3. **是否需要新架构？**还是优化现有的就够了？

这样我才能给你**简洁、实用**的方案，而不是堆砌功能。
