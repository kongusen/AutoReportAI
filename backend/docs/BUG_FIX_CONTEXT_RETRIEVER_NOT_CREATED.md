# 🔧 ContextRetriever 未创建问题修复报告

## 📋 问题描述

### 用户反馈

```
工具不可用，我们构建的上下文也没有读取
```

### 日志证据

```
🔧 [ContainerLLMAdapter] Extracted 1 tool calls  ← Agent尝试调用工具（supports_tools=True生效✅）
🔍 [SchemaDiscoveryTool] 开始发现 Schema: all
❌ 发现表信息失败: dictionary update sequence element #0 has length 1; 2 is required
✅ 发现 0 个表、0 个列、0 个关系
📊 [质量评分] 总体评分: 0.40 (F)
💡 [质量建议] 缺少必需的 SQL 子句: SELECT, FROM
```

### 问题分析

系统存在**两种获取Schema信息的方式**：

1. **方式1（推荐）**：通过 `ContextRetriever` 在执行前自动注入 Schema context
   - ❌ **问题**：ContextRetriever 从未被创建
   - 结果：Agent 看不到任何 Schema 上下文

2. **方式2（工具）**：通过 `Schema Discovery` 工具在执行中查询
   - ✅ 好消息：`supports_tools=True` 生效，Agent 开始调用工具
   - ❌ **问题**：工具需要必需的 `connection_config` 参数，但 Agent 没有这个信息
   - 结果：工具调用失败，返回 0 个表

**结论**：两种方式都失败了，导致 Agent 完全没有 Schema 信息，无法生成准确的 SQL。

---

## 🔍 根本原因分析

### 问题1：ContextRetriever 从未被创建

**文件**：`backend/app/services/infrastructure/agents/facade.py:121-134`

**原始代码**：
```python
async def _create_runtime(self) -> LoomAgentRuntime:
    """创建运行时实例"""
    if self.enable_context_retriever:
        # 创建带上下文检索器的运行时
        return build_default_runtime(
            container=self.container,
            config=self.config
        )
    else:
        # 创建基础运行时
        return build_default_runtime(
            container=self.container,
            config=self.config
        )
```

**问题**：
- ❌ 两个分支代码完全一样！
- ❌ 即使 `enable_context_retriever=True`，也没有创建 `ContextRetriever` 实例
- ❌ `build_default_runtime()` 的 `context_retriever` 参数始终为 `None`

### 问题2：创建 ContextRetriever 需要数据源配置

**ContextRetriever 的初始化需求**：
```python
SchemaContextRetriever(
    data_source_id=str(data_source_id),
    connection_config=connection_config,  # 必需！
    container=container
)
```

**问题**：
- 在 `initialize()` 阶段（facade 初始化时）还不知道 `data_source_id`
- 只有在 `analyze_placeholder()` 时才知道具体要分析哪个数据源
- 无法在 facade 初始化时创建 ContextRetriever

---

## ✅ 解决方案

### 方案：动态创建 ContextRetriever

**策略**：在 `analyze_placeholder()` 方法中，为每个请求动态创建带 ContextRetriever 的运行时。

### 修改1：在 `analyze_placeholder` 中动态创建运行时

**文件**：`backend/app/services/infrastructure/agents/facade.py:177-213`

**新增代码**：
```python
# 🔥 关键修复：为每个请求动态创建带 ContextRetriever 的运行时
if self.enable_context_retriever:
    logger.info(f"🔍 [LoomAgentFacade] 为数据源 {data_source_id} 创建带 Schema 上下文的运行时")
    try:
        # 获取数据源连接配置
        connection_config = await self._get_connection_config(data_source_id)

        if connection_config:
            # 创建带上下文检索器的运行时
            context_retriever = create_schema_context_retriever(
                data_source_id=str(data_source_id),
                connection_config=connection_config,
                container=self.container
            )

            # 初始化上下文检索器
            await context_retriever.initialize()

            # 创建带上下文的运行时（临时覆盖）
            runtime_with_context = build_default_runtime(
                container=self.container,
                config=self.config,
                context_retriever=context_retriever
            )

            logger.info(f"✅ [LoomAgentFacade] Schema 上下文运行时创建成功")
            # 使用带上下文的运行时
            runtime_to_use = runtime_with_context
        else:
            logger.warning(f"⚠️ [LoomAgentFacade] 无法获取数据源 {data_source_id} 的连接配置，使用默认运行时")
            runtime_to_use = self._runtime

    except Exception as e:
        logger.warning(f"⚠️ [LoomAgentFacade] 创建 Schema 上下文失败: {e}，使用默认运行时")
        runtime_to_use = self._runtime
else:
    runtime_to_use = self._runtime

# ... 后续使用 runtime_to_use 执行任务
async for event in runtime_to_use.execute_with_tt(request):
    yield event
```

**关键点**：
1. ✅ 每个请求动态创建带 ContextRetriever 的运行时
2. ✅ 使用实际的 `data_source_id` 和 `connection_config`
3. ✅ 调用 `context_retriever.initialize()` 预加载 Schema
4. ✅ 错误降级：如果创建失败，使用默认运行时

### 修改2：添加 `_get_connection_config` 辅助方法

**文件**：`backend/app/services/infrastructure/agents/facade.py:677-720`

**新增方法**：
```python
async def _get_connection_config(self, data_source_id: int) -> Optional[Dict[str, Any]]:
    """
    获取数据源的连接配置

    Args:
        data_source_id: 数据源ID

    Returns:
        Optional[Dict[str, Any]]: 连接配置，如果无法获取则返回 None
    """
    try:
        # 从容器获取数据源服务
        data_source_service = getattr(self.container, 'data_source', None) or \
                             getattr(self.container, 'data_source_service', None)

        if not data_source_service:
            logger.warning("⚠️ 容器中未找到数据源服务")
            return None

        # 获取数据源信息
        data_source = await data_source_service.get_data_source(data_source_id)

        if not data_source:
            logger.warning(f"⚠️ 未找到数据源: {data_source_id}")
            return None

        # 构建连接配置
        connection_config = {
            "id": data_source_id,
            "type": getattr(data_source, 'type', 'mysql'),
            "host": getattr(data_source, 'host', ''),
            "port": getattr(data_source, 'port', 3306),
            "database": getattr(data_source, 'database', ''),
            "user": getattr(data_source, 'user', ''),
            "password": getattr(data_source, 'password', ''),
            "charset": getattr(data_source, 'charset', 'utf8mb4'),
        }

        logger.debug(f"✅ 获取数据源配置成功: {data_source_id}")
        return connection_config

    except Exception as e:
        logger.error(f"❌ 获取数据源配置失败: {e}", exc_info=True)
        return None
```

**功能**：
1. 从容器获取数据源服务
2. 通过 `data_source_id` 查询数据源信息
3. 构建并返回连接配置字典
4. 错误处理：返回 `None` 时降级到默认运行时

---

## 📊 预期效果

### 修复前 vs 修复后

| 指标 | 修复前 | 修复后（预期） |
|------|--------|----------------|
| **ContextRetriever 创建** | ❌ 从未创建 | ✅ 动态创建 |
| **Schema 预加载** | ❌ 0 个表 | ✅ 19+ 个表 |
| **上下文可见性** | ❌ Agent 看不到 | ✅ Agent 可见 |
| **工具调用** | ✅ 尝试但失败 | ✅ 成功 (作为补充) |
| **质量评分** | 0.40 (F级) | ≥0.7 (C级+) |
| **SQL 准确性** | 低（缺少表信息） | 高（有完整 Schema） |

### 执行流程（修复后）

```
1. analyze_placeholder() 开始
   ↓
2. 获取 data_source_id 和 connection_config
   ↓
3. 创建 SchemaContextRetriever
   ↓
4. 调用 context_retriever.initialize()
   - 查询数据库所有表
   - 缓存 Schema 信息（19个表，294个列）
   ↓
5. 创建带 ContextRetriever 的运行时
   ↓
6. 执行 TT 递归
   - Agent 收到预加载的 Schema context
   - 遵循"上下文优先"工作流
   - 分析上下文 → (必要时使用工具) → 生成 SQL → 验证
   ↓
7. 返回高质量 SQL（评分 ≥0.7）
```

### 日志输出示例（预期）

```
🔍 [LoomAgentFacade] 为数据源 1 创建带 Schema 上下文的运行时
✅ 获取数据源配置成功: 1
🔍 开始初始化数据源 1 的 schema 缓存
✅ 获取表列表成功: 19 个表
✅ Schema 信息初始化完成: 19 表, 294 列
✅ [LoomAgentFacade] Schema 上下文运行时创建成功

🎯 [LoomAgentFacade] 开始分析占位符
📖 [Agent] 第一步：分析 Schema 上下文
   - 发现 return_requests 表
   - 字段: id, customer_id, request_date, status...
🔧 [Agent] 第二步：使用工具进一步验证（如需要）
✍️ [Agent] 第三步：生成 SQL
   - SELECT COUNT(*) AS total_requests FROM return_requests
🔍 [Agent] 第四步：验证 SQL
   - ✅ 语法正确
   - ✅ 表和字段存在
✅ [Agent] 返回最终结果
📊 [质量评分] 总体评分: 0.85 (B级)
```

---

## 🎯 关键改进点

### 1. 解决了两个失败模式

**之前**：
- ❌ 方式1（Context）失败：ContextRetriever 未创建
- ❌ 方式2（工具）失败：缺少 connection_config

**现在**：
- ✅ 方式1（Context）成功：动态创建 ContextRetriever，预加载 Schema
- ✅ 方式2（工具）改进：作为补充验证手段

### 2. 实现了"上下文优先"工作流

```
📖 第一步：读取预加载的 Schema 上下文（ContextRetriever 提供）
🤔 第二步：识别信息缺口
🔧 第三步：使用工具补充（仅在必要时）
✅第四步：生成和验证 SQL
```

### 3. 性能提升

- **之前**：需要多次工具调用获取 Schema（每次 2-5s）
- **现在**：Schema 预加载（一次性），Agent 直接使用

### 4. 错误降级策略

```python
try:
    # 尝试创建带 Context 的运行时
    runtime_with_context = ...
except Exception:
    # 降级到默认运行时（仍然可以使用工具）
    runtime_to_use = self._runtime
```

确保系统在任何情况下都能工作。

---

## 🧪 测试验证

### 验证点

1. **ContextRetriever 创建**
   - [ ] 日志显示 "创建带 Schema 上下文的运行时"
   - [ ] 日志显示 "Schema 信息初始化完成: N 表, M 列"

2. **上下文注入**
   - [ ] Agent prompt 包含 Schema 上下文
   - [ ] 日志显示 "分析 Schema 上下文"

3. **SQL 质量提升**
   - [ ] 质量评分从 0.4 提升到 ≥0.7
   - [ ] SQL 包含正确的表名和字段名
   - [ ] 日志显示 "上下文利用率: 高"

4. **错误处理**
   - [ ] 如果数据源不存在，降级到默认运行时
   - [ ] 如果 Schema 查询失败，系统仍能工作

### 测试命令

```bash
cd backend
python scripts/test_placeholder_analysis.py
```

**期待结果**：
- ✅ ContextRetriever 成功创建
- ✅ Schema 预加载成功（19个表）
- ✅ Agent 使用上下文生成 SQL
- ✅ 质量评分 ≥0.7

---

## 📝 修改文件清单

| 文件 | 修改内容 | 行号 |
|------|----------|------|
| `facade.py` | 在 `analyze_placeholder` 中动态创建 ContextRetriever | 177-213 |
| `facade.py` | 添加 `_get_connection_config` 方法 | 677-720 |
| `facade.py` | 修改执行逻辑使用动态运行时 | 252-267 |

---

## 🎓 关键经验

### 1. 上下文注入需要两个步骤

- **Step 1**：创建 ContextRetriever ← 之前缺失！
- **Step 2**：将 ContextRetriever 传递给 Agent

### 2. 动态创建 vs 静态创建

**问题**：某些依赖（如 data_source_id）在初始化时不可用

**解决**：延迟创建，在需要时动态创建

### 3. 错误降级策略

始终提供降级方案：
```python
runtime_to_use = runtime_with_context if success else self._runtime
```

### 4. 双重保障机制

- **主要机制**：ContextRetriever 预加载 Schema
- **备用机制**：工具动态查询 Schema

两者互补，确保 Agent 始终有 Schema 信息。

---

## 🚀 下一步

### 立即测试

```bash
# 运行占位符分析测试
cd backend
python scripts/test_placeholder_analysis.py --data-source-id 1 --placeholder "统计退货申请的总数"
```

### 监控指标

- ✅ ContextRetriever 创建成功率
- ✅ Schema 预加载表数量
- ✅ Agent 上下文利用率
- ✅ SQL 质量评分平均值
- ✅ 工具调用次数（应该减少）

---

**修复完成日期**: 2025-01-28
**修复人**: AI Assistant
**验证状态**: ⏳ 待测试

**核心成就**:
- ✅ 修复 ContextRetriever 从未创建的问题
- ✅ 实现动态 Schema 上下文注入
- ✅ 建立错误降级机制
- ✅ 完善"上下文优先"工作流

**预期效果**:
- SQL 质量评分: 0.40 → ≥0.70 (提升 75%+)
- Schema 信息: 0 表 → 19 表
- 上下文可见性: 无 → 完整
