# Task Management Module

任务管理模块，提供完整的任务生命周期管理功能。

## 模块结构

```
task/
├── __init__.py                 # 模块初始化
├── core/                       # 核心组件
│   ├── __init__.py
│   ├── worker/                 # Celery Worker模块
│   │   ├── __init__.py
│   │   ├── config/             # 配置
│   │   │   ├── celery_app.py   # Celery应用配置
│   │   │   └── task_status.py  # 任务状态常量
│   │   ├── tasks/              # 任务定义
│   │   │   ├── basic_tasks.py  # 基础任务
│   │   │   └── enhanced_tasks.py # 增强任务
│   │   └── utils/              # 工具函数
│   │       └── progress_utils.py # 进度管理工具
│   ├── scheduler.py            # 任务调度器
│   └── progress_manager.py     # 进度管理器
├── execution/                  # 执行组件
│   ├── __init__.py
│   ├── pipeline.py             # 智能报告生成流水线
│   ├── agent_executor.py       # Agent执行器
│   └── fallback.py             # 回退处理机制
├── management/                 # 管理组件
│   ├── __init__.py
│   ├── task_manager.py         # 任务管理器
│   └── status_tracker.py       # 状态跟踪器
└── utils/                      # 工具组件
    ├── __init__.py
    ├── notifications.py        # 通知工具
    └── file_handlers.py        # 文件处理工具
```

## 核心功能

### 1. Celery Worker模块 (`core/worker/`)

#### 配置 (`config/`)
- **celery_app.py**: Celery应用实例和配置
- **task_status.py**: 任务状态常量定义

#### 任务定义 (`tasks/`)
- **basic_tasks.py**: 基础任务
  - `template_parsing`: 模板解析
  - `placeholder_analysis`: 占位符分析
  - `data_query`: 数据查询
  - `content_filling`: 内容填充
  - `report_generation`: 报告生成
  - `execute_etl_job`: ETL作业执行
  - `test_celery_task`: 测试任务

- **enhanced_tasks.py**: 增强任务
  - `execute_scheduled_task`: 调度任务执行
  - `intelligent_report_generation_pipeline`: 智能报告生成流水线
  - `enhanced_intelligent_report_generation_pipeline`: 增强版智能报告生成流水线

#### 工具函数 (`utils/`)
- **progress_utils.py**: 进度管理工具函数

### 2. 执行组件 (`execution/`)

- **pipeline.py**: 智能报告生成流水线
- **agent_executor.py**: Agent执行器
- **fallback.py**: 回退处理机制

### 3. 管理组件 (`management/`)

- **task_manager.py**: 任务生命周期管理
- **status_tracker.py**: 任务状态监控和统计

### 4. 工具组件 (`utils/`)

- **notifications.py**: 通知工具
- **file_handlers.py**: 文件处理工具

## 使用示例

### 启动Celery Worker

```bash
# 启动Worker
celery -A app.services.task.core.worker.celery_app worker --loglevel=info

# 启动Beat调度器
celery -A app.services.task.core.worker.celery_app beat --loglevel=info
```

### 在代码中使用

```python
from app.services.task import (
    celery_app,
    TaskStatus,
    TaskManager,
    StatusTracker,
    AgentExecutor
)

# 创建任务
task_manager = TaskManager()
task = task_manager.create_task(task_data, user_id)

# 执行任务
from app.services.task.core.worker.tasks.enhanced_tasks import enhanced_intelligent_report_generation_pipeline
result = enhanced_intelligent_report_generation_pipeline.delay(task_id, user_id)

# 跟踪状态
status_tracker = StatusTracker()
status = status_tracker.get_task_status(task_id)
```

## 主要特性

1. **模块化设计**: 清晰的职责分离，便于维护和扩展
2. **Agent集成**: 支持智能Agent系统进行任务处理
3. **进度管理**: 实时任务进度跟踪和状态同步
4. **错误处理**: 完善的错误处理和回退机制
5. **通知系统**: 任务状态变更通知
6. **文件管理**: 报告文件生成和管理
7. **性能监控**: 任务执行性能统计

## 配置说明

### Celery配置
- Broker: Redis
- Backend: Redis
- 时区: Asia/Shanghai
- 序列化: JSON
- 重试机制: 自动重试，递增等待时间

### 任务状态
- `pending`: 等待中
- `analyzing`: 分析中
- `querying`: 查询中
- `processing`: 处理中
- `generating`: 生成中
- `completed`: 已完成
- `failed`: 失败
- `retrying`: 重试中

## 扩展指南

### 添加新任务类型

1. 在 `core/worker/tasks/` 下创建新的任务文件
2. 使用 `@celery_app.task` 装饰器定义任务
3. 在 `core/worker/__init__.py` 中导入并导出
4. 更新相关文档

### 添加新的执行组件

1. 在 `execution/` 下创建新的执行器
2. 实现标准的接口方法
3. 在 `execution/__init__.py` 中导出
4. 更新依赖注入配置

### 添加新的管理功能

1. 在 `management/` 下创建新的管理器
2. 实现相应的管理方法
3. 在 `management/__init__.py` 中导出
4. 更新API依赖配置
