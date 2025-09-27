# 占位符系统重构架构方案

## 目录结构

```
backend/app/services/
├── domain/
│   └── placeholder/
│       ├── __init__.py
│       ├── core/                           # 核心业务服务
│       │   ├── __init__.py
│       │   ├── placeholder_domain_service.py      # 主域服务
│       │   ├── handlers/                          # 类型处理器
│       │   │   ├── __init__.py
│       │   │   ├── base_handler.py               # 基础处理器接口
│       │   │   ├── period_handler.py             # 周期类占位符处理器
│       │   │   ├── statistical_handler.py        # 统计类占位符处理器
│       │   │   └── chart_handler.py              # 图表类占位符处理器
│       │   └── models/                           # 业务模型
│       │       ├── __init__.py
│       │       ├── placeholder_types.py          # 占位符类型定义
│       │       ├── business_context.py           # 业务上下文模型
│       │       └── analysis_result.py            # 分析结果模型
│       ├── lifecycle/                      # 任务生命周期管理
│       │   ├── __init__.py
│       │   ├── scanner_service.py                # 占位符扫描服务
│       │   ├── validator_service.py              # 占位符验证服务
│       │   ├── replacer_service.py               # 占位符替换服务
│       │   └── etl_integration.py                # ETL集成服务
│       ├── context/                        # 上下文管理
│       │   ├── __init__.py
│       │   ├── template_context_service.py       # 模板上下文服务
│       │   ├── data_source_context_service.py    # 数据源上下文服务
│       │   ├── task_context_service.py           # 任务上下文服务
│       │   └── context_coordinator.py            # 上下文协调器
│       └── policies/                       # 业务策略
│           ├── __init__.py
│           ├── cache_policy.py                   # 缓存策略
│           ├── validation_policy.py              # 验证策略
│           └── replacement_policy.py             # 替换策略
│
└── infrastructure/
    └── agents/
        ├── __init__.py
        ├── facade.py                       # Agent系统门面(保持现有)
        ├── types.py                        # 类型定义(保持现有)
        ├── orchestrator.py                 # 编排器(保持现有)
        ├── planner.py                      # 规划器(保持现有)
        ├── executor.py                     # 执行器(保持现有)
        ├── tools/                          # 工具集(增强现有)
        │   ├── __init__.py
        │   ├── base.py                     # 基础工具类(保持现有)
        │   ├── registry.py                 # 工具注册(保持现有)
        │   ├── sql_tools.py                # SQL工具(增强)
        │   ├── schema_tools.py             # Schema工具(增强)
        │   ├── chart_tools.py              # 图表工具(增强)
        │   ├── time_tools.py               # 时间工具(增强)
        │   └── data_quality_tools.py       # 数据质量工具(保持现有)
        └── adapters/                       # 基础设施适配器
            ├── __init__.py
            ├── cache_adapter.py            # 缓存适配器
            ├── storage_adapter.py          # 存储适配器
            └── data_source_adapter.py      # 数据源适配器
```

## 核心设计思路

### 1. 职责分离原则

**Domain Layer 专注业务能力：**
- 周期类占位符：直接基于任务信息计算，无需SQL
- 统计类占位符：生成SQL逻辑，调用Infrastructure执行
- 图表类占位符：定义图表规则，委托Infrastructure生成

**Infrastructure Layer 专注技术能力：**
- Agent系统：提供SQL生成、Schema查询、图表创建等技术能力
- 工具集：标准化的技术工具，可复用、可扩展
- 适配器：统一外部系统接入

### 2. 三阶段处理模型

**模板分析阶段：**
```
Template Context + Placeholder Definition
         ↓ (Domain Layer)
Type Detection + Business Rule Analysis
         ↓ (Infrastructure Layer)
SQL Generation / Direct Calculation / Chart Definition
```

**任务处理阶段：**
```
All Placeholders Scan
         ↓ (Domain Layer)
Status Check + Validation + Re-analysis
         ↓ (Infrastructure Layer)
Agent Tools Execution + Cache Update
```

**报告组装阶段：**
```
Three Contexts (Template + DataSource + Task)
         ↓ (Domain Layer)
Context-aware Replacement + Description Generation
         ↓ (Infrastructure Layer)
Data Retrieval + Chart Generation + Final Assembly
```

### 3. 上下文驱动设计

**三大上下文整合：**
- Template Context：占位符定义、模板结构
- DataSource Context：实际数据、Schema信息
- Task Context：执行时间、参数、周期设置

**上下文流转：**
- 模板阶段：Template Context 主导
- 任务阶段：Task Context + DataSource Context 协调
- 组装阶段：三大上下文融合

## 关键优势

### 1. 清晰的职责边界
- Domain层专注业务逻辑和规则
- Infrastructure层专注技术实现
- 避免业务逻辑泄露到技术层

### 2. 高度可扩展性
- 新增占位符类型只需添加Handler
- Agent工具可独立演进
- 上下文服务可灵活组合

### 3. 强大的复用能力
- Agent工具集在不同业务场景复用
- 上下文服务支持多种使用模式
- 生命周期服务统一管理逻辑

### 4. 优秀的测试性
- 业务逻辑与技术实现分离，便于单元测试
- Mock Infrastructure层，专注Domain层测试
- Agent工具可独立测试验证

## 实施步骤

1. **重构Domain层核心服务** - 建立清晰的业务边界
2. **增强Infrastructure层Agent工具** - 提供更强大的技术能力
3. **建立上下文协调机制** - 三大上下文的统一管理
4. **重构API层调用方式** - 简化调用路径，提高可维护性
5. **完善测试覆盖** - 确保重构质量和系统稳定性