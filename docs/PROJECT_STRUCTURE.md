# AutoReportAI Backend 项目结构

## 项目概述

AutoReportAI是一个基于AI的智能报告生成系统，采用两阶段架构设计：Template → Placeholder → Agent → ETL → Report。

## 核心架构

### 两阶段流水线架构
- **阶段1**: 模板分析 → 占位符提取 → Agent智能分析
- **阶段2**: 数据提取 → ETL处理 → 报告生成

### 多级缓存系统
- Template级缓存
- Placeholder级缓存  
- Agent Analysis级缓存
- Data Extraction级缓存

## 目录结构

```
backend/
├── app/
│   ├── api/                     # API接口层
│   │   ├── endpoints/           # 各模块API端点
│   │   │   ├── templates.py     # 模板管理API (包含占位符管理)
│   │   │   ├── data_sources.py  # 数据源管理API
│   │   │   ├── tasks.py         # 任务管理API
│   │   │   └── ...
│   │   └── router.py            # API路由配置
│   │
│   ├── core/                    # 核心功能模块
│   │   ├── config.py            # 应用配置
│   │   ├── dependencies.py      # 依赖注入
│   │   ├── architecture.py      # 架构定义
│   │   └── ...
│   │
│   ├── models/                  # 数据模型
│   │   ├── template.py          # 模板模型
│   │   ├── data_source.py       # 数据源模型
│   │   ├── task.py              # 任务模型
│   │   └── ...
│   │
│   ├── schemas/                 # Pydantic数据验证
│   │   ├── template.py          # 模板Schema
│   │   ├── data_source.py       # 数据源Schema
│   │   └── ...
│   │
│   ├── crud/                    # 数据库CRUD操作
│   │   ├── crud_template.py     # 模板CRUD
│   │   ├── crud_data_source.py  # 数据源CRUD
│   │   └── ...
│   │
│   └── services/                # 业务逻辑服务层
│       ├── agents/              # AI Agent系统
│       │   ├── orchestration/   # Agent编排
│       │   ├── specialized/     # 专门化Agent
│       │   └── ...
│       │
│       ├── task/                # 任务执行系统
│       │   ├── execution/       # 执行引擎
│       │   │   ├── unified_pipeline.py    # 统一流水线
│       │   │   └── two_phase_pipeline.py  # 两阶段流水线
│       │   ├── core/worker/     # Celery任务队列
│       │   └── ...
│       │
│       ├── template/            # 模板处理服务
│       │   ├── enhanced_template_parser.py      # 增强模板解析器
│       │   ├── placeholder_config_service.py    # 占位符配置服务
│       │   └── ...
│       │
│       ├── connectors/          # 数据连接器
│       │   ├── doris_connector.py    # Doris连接器
│       │   ├── sql_connector.py      # SQL连接器
│       │   └── ...
│       │
│       ├── cache/               # 缓存管理
│       │   └── pipeline_cache_manager.py
│       │
│       └── ...
│
├── migrations/                  # 数据库迁移文件
├── scripts/                     # 工具脚本
├── requirements.txt             # Python依赖
├── alembic.ini                  # 数据库迁移配置
└── main.py                      # 应用入口
```

## 核心模块说明

### 1. API层 (`app/api/`)
- **统一的RESTful API设计**
- **模板管理**: 包含完整的占位符-ETL脚本管理功能
- **数据源管理**: 支持多种数据源类型
- **任务调度**: 异步任务执行和监控

### 2. Agent系统 (`app/services/agents/`)
- **智能编排**: 自动分析占位符需求
- **专门化Agent**: 数据查询、内容生成、可视化等
- **缓存优化**: Agent分析结果缓存

### 3. 任务执行系统 (`app/services/task/`)
- **统一流水线**: 整合多种执行模式
- **两阶段架构**: Template→Placeholder→Agent→ETL
- **Celery集成**: 异步任务队列支持

### 4. 模板处理 (`app/services/template/`)
- **智能解析**: 自动识别占位符类型
- **配置管理**: 占位符持久化和缓存
- **SQL生成**: Agent自动生成查询语句

### 5. 数据连接 (`app/services/connectors/`)
- **多数据源支持**: Doris、SQL、API、CSV等
- **连接池管理**: 高效的数据库连接复用
- **查询优化**: 智能查询路由和优化

## 特性亮点

### 1. 架构优势
- **模块化设计**: 高内聚低耦合
- **可扩展性**: 易于添加新的数据源和Agent
- **缓存优化**: 多级缓存提升性能

### 2. 智能化
- **AI Agent**: 自动分析用户需求生成SQL
- **智能路由**: 根据模板状态选择最优执行路径
- **自适应缓存**: 根据使用频率调整缓存策略

### 3. 用户体验
- **占位符管理**: 可视化的ETL脚本编辑界面
- **实时监控**: 任务执行状态和性能监控
- **错误处理**: 详细的错误信息和建议

### 4. 性能优化
- **异步处理**: Celery任务队列支持
- **连接池**: 数据库连接复用
- **缓存策略**: 多级缓存减少重复计算

## 开发指南

### 添加新的数据源
1. 在 `app/services/connectors/` 创建新的连接器
2. 在 `app/models/data_source.py` 添加数据源类型
3. 更新 `connector_factory.py` 注册新连接器

### 添加新的Agent
1. 在 `app/services/agents/specialized/` 创建新Agent
2. 在编排器中注册新Agent
3. 更新Agent工厂方法

### 扩展API功能
1. 在相应的 `app/api/endpoints/` 文件中添加端点
2. 创建对应的Schema和CRUD操作
3. 更新API路由配置

## 部署配置

### 环境变量
- `DATABASE_URL`: 数据库连接字符串
- `REDIS_URL`: Redis连接字符串（用于Celery）
- `AI_PROVIDER_CONFIG`: AI服务配置

### 依赖服务
- **PostgreSQL**: 主数据库
- **Redis**: 缓存和消息队列
- **Celery**: 异步任务队列

## 维护说明

### 定期清理
- **缓存**: 定期清理过期缓存数据
- **日志**: 清理旧的日志文件
- **报告**: 清理测试生成的报告文件

### 监控指标
- **任务执行时间**: 监控流水线性能
- **缓存命中率**: 优化缓存策略
- **错误率**: 及时发现和修复问题

这个项目结构体现了现代微服务架构的最佳实践，同时保持了代码的简洁性和可维护性。