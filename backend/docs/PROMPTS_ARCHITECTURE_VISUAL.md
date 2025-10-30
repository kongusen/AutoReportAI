# Prompts 目录架构可视化总结

## 1. 模块关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Prompts 模块结构                                    │
└─────────────────────────────────────────────────────────────────────────┘

                                __init__.py (14行)
                                     ▲
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │  system.py   │  │  stages.py   │  │templates.py  │
            │  (673行)     │  │  (501行)     │  │  (704行)     │
            └──────────────┘  └──────────────┘  └──────────────┘
                    △                △                △
                    │                │                │
                    └────────────────┼────────────────┘
                                     │
                            应该被使用但未使用
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │    runtime.py           │
                        │ AdaptivePromptGenerator │
                        │    (1699行)             │
                        └─────────────────────────┘

```

## 2. 内部结构分解

### 2.1 system.py 架构

```
SystemPromptBuilder
├── _build_base_prompt() → 520行的基础提示
│   ├── 角色定义 (1-30行)
│   ├── 核心能力 (31-77行)
│   │   ├── 数据理解能力
│   │   ├── SQL生成能力
│   │   ├── 数据分析能力
│   │   └── 图表生成能力
│   ├── 工作原则 (78-127行)
│   │   ├── 准确性优先
│   │   ├── 效率导向
│   │   ├── 用户友好
│   │   └── 持续改进
│   ├── 工具使用规范 (128-161行)
│   │   ├── 上下文优先原则 (🔥最重要)
│   │   ├── 工具调用原则
│   │   ├── 工具使用顺序
│   │   └── 错误处理
│   ├── 输出格式规范 (162-177行)
│   └── 质量保证 (178-203行)
│
├── _build_stage_prompts() → Dict[ExecutionStage, str]
│   ├── INITIALIZATION (29-34行)
│   ├── SCHEMA_DISCOVERY (35-42行)
│   ├── SQL_GENERATION (43-95行) ← 最详细, 6步骤指导
│   ├── SQL_VALIDATION (96-106行)
│   ├── DATA_EXTRACTION (107-120行)
│   ├── ANALYSIS (121-136行)
│   ├── CHART_GENERATION (137-149行)
│   └── COMPLETION (150-162行)
│
├── _build_complexity_prompts() → Dict[TaskComplexity, str]
│   ├── SIMPLE (0.3)
│   ├── MEDIUM (0.5)
│   └── COMPLEX (0.8)
│
├── build_system_prompt(stage, complexity, custom_instructions)
│   └── 组合基础 + 阶段 + 复杂度 + 自定义指令
│
├── build_context_aware_prompt(context_info, stage, complexity)
│   └── 在系统提示基础上注入上下文信息
│
└── _build_context_section(context_info)
    ├── 数据源信息
    ├── 表结构信息
    ├── 业务上下文
    └── 约束条件

预定义常量:
├── DEFAULT_SYSTEM_PROMPT
├── SCHEMA_DISCOVERY_PROMPT
├── SQL_GENERATION_PROMPT
├── DATA_ANALYSIS_PROMPT
└── CHART_GENERATION_PROMPT
```

### 2.2 stages.py 架构

```
StagePromptManager
├── _build_stage_templates() → Dict[ExecutionStage, Dict]
│   └── 8个执行阶段，每个包含:
│       ├── objective: 阶段目标
│       ├── key_tasks: 关键任务列表 (3-5项)
│       ├── tools_to_use: 推荐工具列表
│       ├── success_criteria: 成功标准
│       ├── next_stage: 下一阶段
│       └── 元数据
│
├── _build_transition_prompts() → Dict[str, str]
│   ├── to_schema_discovery
│   ├── to_sql_generation
│   ├── to_sql_validation
│   ├── to_data_extraction
│   ├── to_analysis
│   ├── to_chart_generation
│   ├── to_completion
│   └── (8个转换提示)
│
├── get_stage_prompt(stage, context, complexity)
│   ├── 构建阶段标题和目标
│   ├── 添加关键任务列表
│   ├── 添加工具推荐
│   ├── 添加成功标准
│   ├── 添加复杂度特定指导
│   └── 添加上下文信息 (可选)
│
├── get_transition_prompt(from_stage, to_stage)
│   └── 返回阶段转换指导
│
├── _get_complexity_guidance(stage, complexity)
│   └── 返回 (stage, complexity) 组合的指导
│       (支持SQL_GENERATION, SQL_VALIDATION, ANALYSIS 3个阶段)
│
├── _build_context_guidance(context, stage)
│   ├── 表数量和名称
│   ├── 列数量
│   ├── 时间窗口
│   └── 业务上下文
│
└── get_stage_summary(stage)
    └── 返回 {stage, objective, key_tasks, tools, success_criteria, next_stage}

预定义常量:
├── INITIALIZATION_PROMPT
├── SCHEMA_DISCOVERY_PROMPT
├── SQL_GENERATION_PROMPT
├── SQL_VALIDATION_PROMPT
├── DATA_EXTRACTION_PROMPT
├── ANALYSIS_PROMPT
├── CHART_GENERATION_PROMPT
└── COMPLETION_PROMPT
```

### 2.3 templates.py 架构

```
PromptTemplate
├── __init__(template, variables)
├── format(**kwargs)
└── _template: string.Template 实例

PromptTemplateManager
├── _build_templates() → Dict[str, PromptTemplate]
│   ├── basic_request (任务请求基础)
│   ├── schema_discovery (Schema发现)
│   ├── sql_generation (SQL生成) ← 110行, 最复杂
│   ├── sql_validation (SQL验证)
│   ├── data_analysis (数据分析)
│   ├── chart_generation (图表生成)
│   ├── error_handling (错误处理)
│   ├── result_summary (结果总结)
│   └── (9个模板总共)
│
├── get_template(template_name)
├── format_template(template_name, **kwargs)
└── create_custom_template(name, template, variables)

ContextFormatter (静态方法)
├── format_schema_context(context) → Markdown表结构
├── format_business_context(context) → 关键值对列表
├── format_data_results(data) → Markdown数据表
└── format_tool_calls(tool_calls) → 编号列表

便利函数
├── format_request_prompt(request, context)
├── format_stage_prompt(stage, request, context, additional_data)
├── format_error_prompt(error_message, current_stage, ...)
└── format_result_summary(success, main_results, ...)
```

## 3. 数据流图

```
用户请求
    │
    ▼
┌─────────────────────────────────────────┐
│ 1. 系统初始化                           │
│ SystemPromptBuilder().build_system_prompt()
│ + StagePromptManager().get_stage_prompt()
│ + ContextFormatter().format_*()         │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 2. 组合多部分提示词                      │
│ - 基础系统提示 (system.py)              │
│ - 阶段特定提示 (stages.py)              │
│ - 上下文信息 (templates.py)             │
│ - 复杂度指导 (stages.py)                │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 3. 注入执行状态                          │
│ - 当前阶段和目标                        │
│ - 迭代计数和进度                        │
│ - 错误或成功反馈                        │
│ - 动态约束条件                          │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ 4. 发送给LLM                            │
│ (目前: AdaptivePromptGenerator生成,     │
│  应该: 集成prompts模块的内容)           │
└─────────────────────────────────────────┘
```

## 4. 提示词的分层结构

```
├─ 第1层: 系统级提示 (system.py)
│  ├── 基础系统提示 (160行, 固定)
│  │   ├── 角色定义
│  │   ├── 核心能力定义
│  │   ├── 工作原则
│  │   ├── 工具使用规范
│  │   ├── 输出格式
│  │   └── 质量保证
│  │
│  ├── 阶段提示 (8个, 动态选择)
│  │   └── 根据 ExecutionStage 选择
│  │
│  └── 复杂度提示 (3个, 动态选择)
│      └── 根据 TaskComplexity 选择
│
├─ 第2层: 阶段级提示 (stages.py)
│  ├── 阶段目标和任务
│  ├── 工具推荐
│  ├── 成功标准
│  ├── 复杂度特定指导
│  └── 上下文特定信息
│
├─ 第3层: 模板级提示 (templates.py)
│  ├── 9个预定义模板
│  ├── 支持变量替换 (${variable})
│  ├── 支持自定义模板
│  └── 上下文格式化工具
│
└─ 第4层: 运行时自适应提示 (runtime.py 中的 AdaptivePromptGenerator)
   ├── 目标和进度
   ├── 错误指导
   ├── 进度反馈
   ├── 行动指导
   └── 动态约束
```

## 5. 执行阶段流程图

```
┌─────────────┐
│ INITIALIZE  │ 理解业务需求，制定执行计划
└──────┬──────┘
       │ (任务理解、信息收集、规划)
       ▼
┌──────────────────┐
│ SCHEMA_DISCOVERY │ 探索数据源结构，理解表关系
└──────┬───────────┘
       │ (发现表、获取结构、理解关系)
       ▼
┌──────────────────┐
│ SQL_GENERATION   │ 生成准确的SQL查询 ← 最关键, 6步骤
└──────┬───────────┘
       │ (分析Schema → 工具探索 → 设计逻辑 → 生成SQL → 验证 → 返回)
       ▼
┌──────────────────┐
│ SQL_VALIDATION   │ 验证SQL的正确性和合理性
└──────┬───────────┘
       │ (语法检查、字段检查、类型检查、修复)
       ▼
┌──────────────────┐
│ DATA_EXTRACTION  │ 执行查询并获取数据结果
└──────┬───────────┘
       │ (执行查询、采样验证、质量检查)
       ▼
┌──────────────────┐
│ ANALYSIS         │ 分析数据并提供业务洞察
└──────┬───────────┘
       │ (数据分析、业务洞察、结果总结)
       ▼
┌──────────────────┐
│ CHART_GENERATION │ 生成数据可视化图表
└──────┬───────────┘
       │ (选择图表、配置样式、优化展示)
       ▼
┌──────────────────┐
│ COMPLETION       │ 整合结果，完成最终交付
└──────────────────┘
```

## 6. 关键创新点

### 6.1 时间占位符强制使用 🔥

```
禁止: WHERE date_column >= '2024-01-01'
推荐: WHERE date_column >= '{{start_date}}'
推荐: WHERE date_column BETWEEN '{{start_date}}' AND '{{end_date}}'

支持的占位符:
- {{start_date}}: 必需
- {{end_date}}: 必需
- {{execution_date}}: 可选
- {{current_date}}: 可选
```

### 6.2 上下文优先原则 🔥

```
第1步: 阅读和理解上下文
  ↓ (分析Schema、字段、关系)
第2步: 识别信息缺口
  ↓ (判断是否需要更多信息)
第3步: 使用工具补充
  ↓ (仅在必要时调用工具)
第4步: 执行任务
  ↓ (基于完整信息完成任务)
```

### 6.3 错误自纠正机制 🔥

```
遇到"表不存在"错误时:
1. 立即停止使用错误的表名
2. 回退到系统消息中的表名 (Context中的表名)
3. 用正确的表名重新生成SQL
4. 绝对不要重复尝试不存在的表名
```

## 7. 代码复杂度统计

```
┌──────────────┬──────┬──────────┬──────────┐
│   文件       │ 行数 │ 类数     │ 函数数   │
├──────────────┼──────┼──────────┼──────────┤
│ system.py    │ 673  │ 1        │ 6        │
│ stages.py    │ 501  │ 1        │ 5        │
│ templates.py │ 704  │ 3        │ 8        │
│ __init__.py  │ 14   │ 0        │ 0        │
├──────────────┼──────┼──────────┼──────────┤
│ 总计         │ 1892 │ 5        │ 19       │
└──────────────┴──────┴──────────┴──────────┘

代码组成:
- 硬编码提示词: ~70% (1300+ 行)
- 模板化提示词: ~15% (280+ 行)
- 工具类/函数: ~15% (280+ 行)
```

## 8. 核心改进路线图

```
现状              中期改进            长期改进
─────────         ──────────          ──────────

✅ 完成          📌 集成到runtime    📌 版本管理
   3个模块          AdaptivePrompt    📌 动态优化
                  📌 导出统一API      📌 A/B测试
                  📌 添加单元测试     📌 学习反馈
```

## 9. 与 AdaptivePromptGenerator 的关系

```
目前状态 (隔离):
┌─────────────────────────────┐
│ AdaptivePromptGenerator     │
│ - 自行生成所有提示词          │
│ - 包含目标、进度、错误等部分   │
│ - 未利用prompts模块功能       │
└─────────────────────────────┘

改进方案 (集成):
┌─────────────────────────────────────────────┐
│ AdaptivePromptGenerator                     │
├─────────────────────────────────────────────┤
│ + SystemPromptBuilder (基础系统提示)        │
│ + StagePromptManager (阶段特定提示)         │
│ + PromptTemplateManager (模板化提示)        │
│ + ContextFormatter (上下文格式化)           │
├─────────────────────────────────────────────┤
│ = 统一、可维护、可扩展的提示生成系统         │
└─────────────────────────────────────────────┘
```

---

**总结**: 这是一个组织清晰、功能完整的提示词管理系统，
但与runtime.py中的AdaptivePromptGenerator隔离，
存在代码重复和集成机会未充分利用的问题。
