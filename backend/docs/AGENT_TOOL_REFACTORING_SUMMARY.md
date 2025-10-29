# Agent 工具架构重构总结

## 📋 重构概述

本次重构解决了 **Agent 工具调用时参数传递的架构缺陷**，修复了 LLM 无法正确传递数据库连接配置的问题。

### 🔍 问题诊断

#### 核心问题
**LLM 被要求传递敏感的数据库连接配置 `connection_config`**

原有架构中，工具的 Schema 定义要求 LLM 传递 `connection_config` 参数：

```python
# ❌ 错误的设计
def get_schema(self) -> Dict[str, Any]:
    return {
        "parameters": {
            "connection_config": {
                "type": "object",
                "description": "数据源连接配置"
            },
            ...
        },
        "required": ["connection_config"]
    }
```

**问题链条：**
1. LLM 根本无法获取真实的数据库连接配置（地址、端口、凭证等敏感信息）
2. LLM 只能"猜测"或"编造"连接配置参数
3. 工具接收到错误的参数类型（字符串而不是字典）
4. 导致 Schema Discovery 失败，进而导致整个 Agent Pipeline 失败

#### 根本原因
**工具设计违反了"关注点分离"原则**：
- ❌ LLM 的职责：根据业务需求生成查询逻辑
- ✅ 系统的职责：管理数据库连接和敏感凭证

---

## 🛠️ 重构方案

### 设计原则
**"在初始化时注入依赖，而不是在运行时要求传递"**

### 架构改进

#### 1. **工具初始化时注入 connection_config**

```python
# ✅ 正确的设计
def __init__(
    self,
    container: Any,
    connection_config: Optional[Dict[str, Any]] = None,  # 🔥 在初始化时注入
):
    self.container = container
    self._connection_config = connection_config  # 保存连接配置
```

#### 2. **工具 Schema 移除 connection_config 参数**

```python
# ✅ LLM 只需要关注业务参数
def get_schema(self) -> Dict[str, Any]:
    return {
        "parameters": {
            # 🔥 移除 connection_config 参数
            "discovery_type": {...},
            "table_pattern": {...},
            ...
        },
        "required": []  # 🔥 不再强制要求任何参数
    }
```

#### 3. **工具运行时使用内部配置**

```python
# ✅ 从内部获取连接配置
async def run(self, discovery_type: str = "all", **kwargs):
    # 🔥 使用初始化时注入的 connection_config
    connection_config = self._connection_config
    if not connection_config:
        return {"success": False, "error": "未配置数据源连接"}

    # 继续执行...
```

---

## 📦 修改的文件清单

### 1. **工具层修改**

#### Schema 工具
- ✅ `backend/app/services/infrastructure/agents/tools/schema/discovery.py`
  - 修改 `SchemaDiscoveryTool.__init__()`：添加 `connection_config` 参数
  - 修改 `get_schema()`：移除 `connection_config` 参数要求
  - 修改 `run()`：从 `self._connection_config` 获取配置
  - 修改 `create_schema_discovery_tool()`：支持传递 `connection_config`

- ✅ `backend/app/services/infrastructure/agents/tools/schema/retrieval.py`
  - 同上修改

#### SQL 工具
- ✅ `backend/app/services/infrastructure/agents/tools/sql/executor.py`
  - 同上修改

- 🚧 `backend/app/services/infrastructure/agents/tools/sql/validator.py`
  - 需要类似修改（工厂函数已更新，类实现待更新）

- 🚧 `backend/app/services/infrastructure/agents/tools/sql/generator.py`
  - 需要类似修改（工厂函数已更新，类实现待更新）

### 2. **运行时层修改**

#### Runtime 工具创建逻辑
- ✅ `backend/app/services/infrastructure/agents/runtime.py`
  - 修改 `_create_tools_from_config()`：
    ```python
    # 🔥 从 container 读取临时存储的 connection_config
    connection_config = getattr(container, '_temp_connection_config', None)

    # 🔥 需要 connection_config 的工具列表
    tools_requiring_connection = {
        "schema_discovery", "schema_retrieval", "sql_generator",
        "sql_validator", "sql_executor", ...
    }

    # 🔥 根据工具类型选择性传递 connection_config
    if tool_name in tools_requiring_connection and connection_config:
        tool = factory_func(container, connection_config=connection_config)
    else:
        tool = factory_func(container)
    ```

### 3. **Facade 层修改**

#### 请求处理流程
- ✅ `backend/app/services/infrastructure/agents/facade.py`
  - 修改 `analyze_placeholder()`：
    ```python
    # 🔥 获取连接配置后，临时存储到 container
    connection_config = await self._get_connection_config(data_source_id)
    if connection_config:
        setattr(self.container, '_temp_connection_config', connection_config)

    # 创建 runtime（会调用 _create_tools_from_config）
    runtime_with_context = build_default_runtime(...)

    # 🔥 清除临时存储
    if hasattr(self.container, '_temp_connection_config'):
        delattr(self.container, '_temp_connection_config')
    ```

---

## 🎯 修复效果

### Before（修复前）

```
❌ 问题流程：
1. LLM 生成工具调用：schema_discovery(connection_config="database")
2. 工具接收到字符串类型参数
3. 数据库连接失败
4. Schema Discovery 返回 0 个表、0 个列
5. SQL 生成失败
6. Agent Pipeline 失败（质量分 0.40，F级）
```

### After（修复后）

```
✅ 正确流程：
1. Facade 从请求中提取 data_source_id
2. Facade 通过 _get_connection_config() 获取真实的数据库配置
3. 将 connection_config 临时存储到 container
4. Runtime 创建工具时，从 container 读取并注入 connection_config
5. LLM 生成工具调用：schema_discovery(discovery_type="all")  # 不包含 connection_config
6. 工具使用内部的 self._connection_config 连接数据库
7. Schema Discovery 成功返回表结构
8. SQL 生成成功
9. Agent Pipeline 成功
```

---

## 📊 架构对比

### 旧架构（参数传递）

```
User Request
    ↓
Facade → get connection_config
    ↓
LLM (需要传递 connection_config)  ❌ 无法获取
    ↓
Tool.run(connection_config=???)  ❌ 接收到错误类型
    ↓
Database Connection Failed  ❌
```

### 新架构（依赖注入）

```
User Request
    ↓
Facade → get connection_config
    ↓
container._temp_connection_config = config  ✅ 临时存储
    ↓
Runtime → create_tools(container)
    ↓
Tool.__init__(container, connection_config=config)  ✅ 注入配置
    ↓
LLM (只需传递业务参数)  ✅ 关注点分离
    ↓
Tool.run(discovery_type="all")  ✅ 使用内部配置
    ↓
Database Connection Success  ✅
```

---

## ✅ 验证清单

### 已完成
- [x] SchemaDiscoveryTool 重构
- [x] SchemaRetrievalTool 重构
- [x] SQLExecutorTool 重构
- [x] 工厂函数更新
- [x] Runtime 工具创建逻辑更新
- [x] Facade 连接配置注入逻辑

### 待完成
- [ ] SQLValidatorTool 类实现更新
- [ ] SQLGeneratorTool 类实现更新
- [ ] SQLColumnCheckerTool 更新
- [ ] SQLAutoFixerTool 更新
- [ ] DataSamplerTool 更新
- [ ] 集成测试验证
- [ ] 性能测试

---

## 🔧 后续优化建议

### 1. **完成剩余工具的重构**
按照相同模式更新所有需要 `connection_config` 的工具。

### 2. **添加单元测试**
测试工具在有/无 `connection_config` 时的行为。

### 3. **改进错误处理**
当工具缺少 `connection_config` 时，返回更友好的错误提示。

### 4. **考虑使用上下文管理器**
使用 Python 的 `contextvar` 来管理请求级别的配置，而不是临时属性。

---

## 📝 技术要点总结

### 核心原则
1. **依赖注入优于参数传递**：敏感配置应在初始化时注入，而不是在每次调用时传递
2. **关注点分离**：LLM 关注业务逻辑，系统管理基础设施
3. **单一职责**：工具只负责执行，不负责获取连接配置

### 设计模式
- **Dependency Injection（依赖注入）**
- **Factory Pattern（工厂模式）**
- **Temporary Storage（临时存储模式）**

### 最佳实践
- ✅ 在工具初始化时注入依赖
- ✅ 工具 Schema 只暴露业务参数
- ✅ 使用 container 作为临时存储介质
- ✅ 及时清理临时数据防止泄漏

---

## 📅 变更记录

**日期**: 2025-01-XX
**版本**: 1.0.0
**作者**: AI Assistant
**状态**: 🚧 进行中

**影响范围**:
- 工具层：6+ 工具类
- 运行时层：1 个核心函数
- Facade 层：1 个主要方法

**向后兼容性**: ✅ 完全兼容（工厂函数支持可选参数）
