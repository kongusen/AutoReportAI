# Agents目录迁移计划

## 🎯 迁移目标
将 `app/services/agents/` 重新定位到符合DDD架构的Infrastructure层，作为AI基础设施服务。

## 📊 当前状态分析

### ✅ 该目录的价值
- **核心DAG编排系统**: BackgroundController、ExecutionEngine等
- **LLM集成框架**: ReactIntelligentAgent、LLMClientAdapter等  
- **AI工具链**: 完整的工具注册和管理系统
- **现有集成**: 被placeholder、template服务广泛使用

### ❌ DDD架构问题
- 独立成层违反DDD分层原则
- 应归属到Infrastructure层作为技术基础设施
- 与新建的分层Agent服务重复

## 🚀 迁移方案

### 阶段1: 创建新的Infrastructure/AI结构
```bash
app/services/infrastructure/ai/
├── __init__.py                    # AI基础设施统一接口
├── agents/                        # 智能代理核心
│   ├── __init__.py
│   ├── dag_controller.py         # DAG编排控制器 (from background_controller)
│   ├── execution_engine.py       # 执行引擎
│   ├── task_context.py          # 任务上下文 (from placeholder_task_context)
│   └── react_agent.py           # React智能代理
├── llm/                          # LLM集成服务 (合并原llm目录)
│   ├── __init__.py
│   ├── client_adapter.py        # LLM客户端适配器
│   ├── router.py                # LLM路由器
│   └── model_manager.py         # 模型管理
├── tools/                        # AI工具系统
│   ├── __init__.py
│   ├── registry.py              # 工具注册
│   ├── factory.py               # 工具工厂
│   └── monitors.py              # 工具监控
└── execution/                    # 执行管理
    ├── __init__.py
    ├── context_manager.py       # 上下文管理
    └── step_executor.py         # 步骤执行器
```

### 阶段2: 更新导入路径
```python
# 原有路径
from app.services.agents import execute_placeholder_with_context

# 新路径  
from app.services.infrastructure.ai import execute_placeholder_with_context
```

### 阶段3: 整合分层Agent架构
```python
# Infrastructure层AI服务为其他层的Agent提供底层支持
# Application层Agent → 调用 → Infrastructure AI服务
# Domain层Agent → 调用 → Infrastructure AI服务
```

## 🔧 具体实施步骤

### Step 1: 创建新的Infrastructure/AI结构
```bash
mkdir -p app/services/infrastructure/ai/{agents,llm,tools,execution}
```

### Step 2: 迁移核心组件
- `background_controller.py` → `ai/agents/dag_controller.py`
- `execution_engine.py` → `ai/agents/execution_engine.py`  
- `placeholder_task_context.py` → `ai/agents/task_context.py`
- `react_agent.py` → `ai/agents/react_agent.py`
- `llm_adapter.py` → `ai/llm/client_adapter.py`
- `tools/` → `ai/tools/`

### Step 3: 合并LLM目录
```bash
# 将 app/services/llm/ 合并到 app/services/infrastructure/ai/llm/
mv app/services/llm/* app/services/infrastructure/ai/llm/
```

### Step 4: 更新依赖引用
- 更新 `app/api/deps.py` 中的引用路径
- 更新Domain层服务中的引用
- 更新template服务中的引用

### Step 5: 创建统一AI服务接口
```python
# app/services/infrastructure/ai/__init__.py
"""
Infrastructure层AI服务

提供统一的AI基础设施服务：
1. 智能代理执行引擎
2. LLM集成和管理
3. AI工具链和注册
4. DAG编排和控制
"""

# 导出核心AI服务
from .agents import get_dag_controller, get_execution_engine
from .llm import get_llm_client_adapter, get_model_manager
from .tools import get_tools_registry, get_tools_factory

# 保持向后兼容的主要接口
from .agents.execution_engine import execute_placeholder_with_context

__all__ = [
    'execute_placeholder_with_context',
    'get_dag_controller',
    'get_execution_engine', 
    'get_llm_client_adapter',
    'get_tools_registry'
]
```

## ⚖️ 迁移vs保留的权衡

### 选项A: 完全迁移 (推荐)
**优势:**
- ✅ 完全符合DDD架构
- ✅ 清晰的职责分离  
- ✅ 统一的AI基础设施

**劣势:**
- ⚠️ 需要更新大量引用
- ⚠️ 短期内有迁移成本

### 选项B: 渐进式重构
**阶段性方案:**
1. 保留现有 `app/services/agents/` 
2. 在Infrastructure层创建新的AI服务接口
3. 逐步将新功能迁移到新架构
4. 最终废弃旧目录

### 选项C: 保持现状 (不推荐)
**理由:**
- ❌ 违反DDD分层原则
- ❌ 与新建分层Agent架构冲突
- ❌ 长期维护成本高

## 💡 推荐方案

采用 **选项B: 渐进式重构**：

1. **立即行动**: 创建 `app/services/infrastructure/ai/` 新架构
2. **并行运行**: 保留现有agents目录，确保系统稳定
3. **逐步迁移**: 新功能使用新架构，旧功能逐步迁移
4. **最终清理**: 完成迁移后删除旧agents目录

这样既保证了架构的长期正确性，又最小化了迁移风险。

## 📅 时间规划

- **Week 1**: 创建新Infrastructure/AI架构，实现核心接口
- **Week 2-3**: 迁移核心组件和更新主要引用
- **Week 4**: 测试验证，确保功能正常
- **Week 5**: 逐步废弃旧接口，完成清理

通过这个计划，我们可以将agents目录正确地整合到DDD架构中，同时保持系统的稳定性和功能完整性。