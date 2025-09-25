# 上下文实现与 Agent 提示词组装 — 深度分析

本文系统梳理 `backend/app/services/application/context` 的上下文实现，解释其如何为 Agent 输出可消费的上下文数据，以及基础设施层如何将上下文与提示词（prompt）进行组装。文末附带无外部依赖的最小实测结果与改进建议，便于快速验证与迭代。

## 总览

- 上下文由三大构建器与一个协调器组成：
  - 数据源上下文：表结构、字段特征、业务域、查询建议等
  - 模板上下文：占位符所在段落与语境、占位符类型识别
  - 任务上下文：调度/时区/时间窗口指令、业务规则、SQL 参数
  - 统一协调器：并发构建、聚合、缓存与对 Agent 友好的合并格式
- Agent 侧采用 PTOF（Plan → Tool → Observe → Finalize）编排：
  - 计划阶段使用上下文生成“计划提示词”；
  - 工具执行阶段把上下文并入每一步工具输入；
  - 最终阶段使用执行观测与上下文生成“决策提示词”。

## 模块结构与职责

### 统一协调器（ContextCoordinator）

- 位置：`backend/app/services/application/context/context_coordinator.py:29`
- 职责：并发调用三大构建器，整合为统一上下文；提供两种对 Agent 友好的表示：
  - `to_agent_format()`：分组件输出，含 meta 与错误/告警
  - `get_consolidated_context()`：拍平后的“直接可用上下文”（schema、模板、任务信息合并）
- 关键方法：
  - `build_full_context(...)` 构建完整上下文，带简易 5 分钟缓存
  - `get_placeholder_context(...)` 针对指定占位符生成合并上下文，附“占位符焦点”状态

### 数据源上下文构建器（DataSourceContextBuilder）

- 位置：`backend/app/services/application/context/data_source_context_server.py`
- 输出结构（Agent 友好）：`DataSourceContextInfo.to_agent_format()`，含：
  - 数据库信息（名称、类型、最后刷新时间）
  - 表清单与每张表的：主键/外键/时间列/度量列/维度列/字段详情
  - 查询建议与性能提示、表间关系、模式特征
- 关键类型：
  - `ColumnInfo`：字段标准化类型、业务含义推断、可聚合/可分组等特征分析
  - `TableInfo`：业务域推断、查询建议、性能提示
  - `DataSourceContextInfo`：统计、关系、常见查询模式
- 实测输出示例见“无依赖最小实测”。

注：协调器当前调用的是简化构建（仅传入 `tables_info=[]`），未对接真实数据源服务，见“问题与建议”。

### 模板上下文构建器（TemplateContextBuilder）

- 位置：`backend/app/services/application/context/template_context_service.py`
- 职责：将解析出的占位符匹配到文档段落，给出“语境段落 + 周边文本 + 位置 + 类型（统计/周期/图表）”。
- 关键方法：
  - `_find_placeholder_context()`：按“{{占位符}} / {占位符} / 直接出现”匹配段落，回退到语义近似匹配
  - `_classify_placeholder_type()`：依据关键词识别类别（金额/图/日期等）
  - `TemplateContextInfo.to_agent_format()`：输出模板信息与占位符上下文清单
- 说明：文件内有“使用预定义模板数据”的路径，但 `_mock_templates` 未定义，导致 `build_template_context()` 的这个分支无法直接运行；可回退到数据库或文档解析路径，见“问题与建议”。

### 任务驱动上下文构建器（TaskDrivenContextBuilder）

- 位置：`backend/app/services/application/context/task_context_service.py`
- 输出结构：`TaskDrivenContext.to_react_context()`，包含：
  - 模板信息（业务域/类型）
  - 数据源信息（ID/类型/DB 名称/可用表）
  - 当前占位符信息
  - 时间上下文：把 cron/时区/执行时刻封装为“Agent 推导时间窗口”的指令字符串
  - SQL 参数、业务规则、进度
- 核心思路：将“确定性的配置（cron/offset/时区）”与“执行时刻”交给 Agent 进行时间范围推导，减少后端硬编码时间推理的复杂度。

## Agent 如何消费上下文并组装 Prompt

### Agent 输入与编排总览

- Agent 统一入口：`backend/app/services/infrastructure/agents/__init__.py:24`
  - 构建 `AgentInput`（含 `user_prompt / placeholder / schema / context / constraints`）后，调用 `AgentFacade.execute()`。
- PTOF 编排：`backend/app/services/infrastructure/agents/orchestrator.py`
  - Plan：用上下文生成“计划提示词”，调用 LLM 产出 JSON 计划
  - Tool：按计划顺序执行工具；把上下文合并进每步工具输入
  - Observe：汇总观测（成功步数、当前 SQL、执行行数、图表等）
  - Finalize：用观测 + 上下文生成“决策提示词”，调用 LLM 产出 JSON 决策

### 计划提示词（Plan Prompt）的组装

- 位置：`backend/app/services/infrastructure/agents/context_prompt_controller.py:21`
- 组装要点：
  - 用户需求、占位符描述/类型、执行阶段（模板/任务/图表）、期望输出（sql/chart/report）
  - 数据上下文：schema 表清单 + 每表前若干字段名
  - 可用工具清单：针对阶段切换工具集合（见 `planner.StageType` 与 `_get_available_tools`）
  - 统一要求输出“纯 JSON 计划”，包含 steps 每步的 `tool / reason / input`

示例结构（节选、自述化）：

```
你是一个智能Agent计划生成器，需要为以下任务生成执行计划。

任务信息:
- 用户需求: <ai.user_prompt>
- 占位符描述: <ai.placeholder.description>
- 占位符类型: <ai.placeholder.type>
- 执行阶段: <stage>
- 期望输出: <ai.constraints.output_kind>

数据上下文:
可用数据表: orders, refunds
orders表字段: id, amount, created_at ...

可用工具:
- sql.draft: 根据描述和schema生成SQL
- sql.validate: 验证SQL正确性并输出问题
...

请生成一个JSON格式的执行计划，包含以下结构:
{
  "thought": "...",
  "steps": [
    {"action":"tool_call","tool":"sql.draft","reason":"...","input":{...}}
  ],
  "expected_outcome": "sql"
}
```

参考：
- Prompt 生成：`backend/app/services/infrastructure/agents/context_prompt_controller.py:21`
- 阶段/工具：`backend/app/services/infrastructure/agents/planner.py:119, 135`

### 工具执行中的上下文注入

- 位置：`backend/app/services/infrastructure/agents/executor.py`
- 每步执行时将以下上下文合并到工具输入：
  - `user_prompt / placeholder_description / tables / columns / window / data_source`
  - 执行后将关键产出写回上下文：`current_sql / execution_result(rows,columns) / chart_spec / chart_image_path`
- 该上下文随后被用于“观察报告”和“最终决策提示词”的组装。

### 决策提示词（Finalize Prompt）的组装

- 位置：`backend/app/services/infrastructure/agents/context_prompt_controller.py:78`
- 组装要点：
  - 原始任务要素（用户需求、占位符描述、期望输出）
  - 执行观测与上下文摘要（当前 SQL、执行行数、图表配置/图片路径）
  - 返回“纯 JSON 决策”（success/result/reasoning/quality_score），并包含 SQL 有效性校验

## 无依赖最小实测（已在本环境执行）

为规避第三方依赖（如 pydantic、python-docx），以下测试直接以“按文件路径加载模块”的方式调用了核心逻辑，验证 to_agent_format / 段落匹配 / 时间指令输出。

1) 数据源上下文 to_agent_format（简化字段示例）：

```json
{
  "database_name": "demo",
  "database_type": "mysql",
  "total_tables": 1,
  "tables": [
    {
      "table_name": "orders",
      "description": "订单表",
      "row_count": 123456,
      "total_columns": 3,
      "business_domain": "sales",
      "primary_keys": ["id"],
      "time_columns": ["created_at"],
      "measure_columns": ["amount"],
      "columns": [
        {"name":"id","type":"integer","is_primary_key":true},
        {"name":"amount","type":"decimal","is_measure":true},
        {"name":"created_at","type":"datetime","business_meaning":"创建时间"}
      ],
      "query_suggestions": [
        "聚合分析: 可对 amount 进行 SUM/AVG/COUNT 聚合",
        "时间序列分析: 可按 created_at 进行时间趋势分析",
        "精确查询: 使用主键 id 进行精确定位"
      ],
      "performance_hints": [
        "中等大小表(>10万行)，注意查询性能，建议添加WHERE条件",
        "已建索引字段: id"
      ]
    }
  ],
  "statistics": {"total_columns": 3, "total_rows": 123456}
}
```

2) 模板上下文：占位符类型识别与段落定位

```
_classify_placeholder_type('金额同比增长率') => 统计类
_classify_placeholder_type('月度销量走势图') => 图表类
_classify_placeholder_type('统计日期') => 周期类

_find_placeholder_context('退货总金额', para=["本报告...", "其中退货总金额为{{退货总金额}}...", "请注意..."])
→ 定位到包含 {{退货总金额}} 的段落，并返回上下文窗口与位置索引
```

3) 任务驱动上下文 to_react_context（含时间推导指令）：

```json
{
  "task_id": "task123",
  "template": {"id":"tpl_001","type":"business_report"},
  "data_source": {"id":"ds1","type":"mysql","database":"demo"},
  "current_placeholder": {"id":"ph1","name":"退货总金额","type":"aggregation"},
  "time_context": {
    "task_schedule": {"cron_expression":"0 0 * * 1","timezone":"Asia/Shanghai","data_period_offset":1},
    "agent_instructions": "基于任务调度信息推导数据时间范围..."
  },
  "sql_parameters": {"database_name":"demo", "task_type":"daily_report", ...},
  "business_rules": ["注意处理NULL值对聚合函数的影响", "考虑数据去重的必要性"]
}
```

以上三个结果说明：三大构建器的核心“对 Agent 友好的”输出形态已经具备并可工作。

## 发现的问题与改进建议

1) 协调器的数据源上下文目前为“占位实现”
   - 位置：`context_coordinator.py:176` 起，`_build_data_source_context()` 使用 `build_context_info(tables_info=[])`，没有通过 `user_data_source_service` 拉取真实表结构。
   - 建议：改为调用 `DataSourceContextBuilder.build_data_source_context(user_id, data_source_id, required_tables=None)`，并把结果合并进 `get_consolidated_context()` 的 `schema_tables / schema_columns` 供 Agent 使用。

2) TemplateContextBuilder 的 `_mock_templates` 未定义
   - 现状：`build_template_context()` 的“预定义模板数据”分支引用 `_mock_templates`，但文件内无定义。
   - 建议：
     - 要么补充 `_mock_templates` 的静态数据；
     - 要么统一走“数据库/解析”路径（已做好 `try/except` 降级），并在失败时返回空 `placeholder_contexts`。

3) 应统一 Agent 调用接口与上下文映射
   - 当前存在两种用法：
     1) `execute_agent_task(placeholder, context, schema)`（`agents/__init__.py:24`）
     2) 应用层某些服务仍调用旧签名（`context_data=...` 等）
   - 建议：提供一个应用层“桥接函数”，把 `ContextCoordinator.get_consolidated_context()` 拆解映射到 `AgentInput` 所需的 `schema.tables / schema.columns / context.window` 等字段，并在内部统一调用 `AgentFacade.execute()`。

4) 把 TaskDrivenContext 贯通到 AgentInput
   - 现状：`AgentInput` 已有 `task_driven_context` 字段，`planner._infer_stage()` 也会据此切到 `TASK_EXECUTION`，但 `execute_agent_task` 的默认实现未传入该字段。
   - 建议：桥接函数中补齐 `task_driven_context`，同时在 `StepExecutor` 的初始上下文加入 `ai.task_driven_context.get('time_context')` 等，以便 `time.window` 等工具可直接使用。

5) Prompt 内容可适度引入更多“合并上下文”
   - 例如把 `template_context.placeholder_contexts` 的“当前占位符所在段落”加入 Plan Prompt，提升 LLM 对语境的把握；
   - 把 `business_rules / data_quality_hints / performance_hints` 摘要加入 Finalize Prompt，作为质量与策略的校验提示。

## 如何进一步验证（建议）

- 安装依赖后可运行现有测试脚本：
  - `python backend/test_real_context_construction.py`（构造真实上下文并保存 JSON）
  - `python backend/test_agent_system_integration.py`（测试 `execute_agent_task` 兼容接口；API 端点检查可按需跳过）
- 也可直接调用 `execute_agent_task` 进行端到端试跑（提供一个简单的 schema 与占位符即可）：

```python
from app.services.infrastructure.agents import execute_agent_task

placeholder = {"id":"refund_total","description":"计算退货总金额","type":"stat","granularity":"daily"}
context = {"user_prompt":"计算退货总金额","timezone":"Asia/Shanghai"}
schema = {"tables":["orders"], "columns":{"orders":["id","amount","created_at"]}}

result = await execute_agent_task(placeholder=placeholder, context=context, schema=schema, user_id="tester")
# 期望返回: { success, result(sql), metadata, agent_response }
```

---

如需，我可以：
- 补齐协调器对真实数据源/模板服务的对接；
- 提供“应用层桥接函数”，把 `ContextCoordinator` 的合并上下文映射为 `AgentInput`；
- 把占位符语境/业务规则等注入 Plan/Finalize Prompt 模板，并补充最小单元测试。

