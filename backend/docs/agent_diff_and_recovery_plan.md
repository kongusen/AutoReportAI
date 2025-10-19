# Backend Agent 差异对比和恢复计划

> 对比当前backend与backend-old的agent机制差异（排除delete相关字段处理）

## 一、已恢复的机制 ✅

### 1. executor.py 核心修复

| 项目 | 状态 | 说明 |
|------|------|------|
| column_details保护 | ✅ 已恢复 | line 1568-1588: 保留所有表，不删除 |
| 字段完整显示 | ✅ 已恢复 | line 640-667: 显示所有字段带类型注释 |
| LLM智能表选择 | ✅ 已恢复 | line 887-995: _select_tables_with_llm方法 |
| _infer_table_keywords | ✅ 已恢复 | line 997-1045: 支持template_context参数 |
| ResourcePool导入 | ✅ 已恢复 | line 18-20: 导入ResourcePool, ContextMemory |

**关键代码片段**：
```python
# line 1568-1588: column_details保留所有表
if isinstance(context.get("column_details"), dict):
    details = context["column_details"]
    # 不再删除任何表的信息，保留完整的column_details
    self._logger.debug(f"🔍 [_reduce_context] 保留column_details: {len(details)}张表")

    # 如果某些表的列数过多（超过100列），可以适当裁剪
    for table, cols in list(details.items()):
        if isinstance(cols, dict) and len(cols) > 100:
            limited = {}
            for i, (col, meta) in enumerate(cols.items()):
                if i >= 100:
                    break
                limited[col] = meta
            details[table] = limited
```

### 2. orchestrator.py 基础修复

| 项目 | 状态 | 说明 |
|------|------|------|
| SQL修复循环 | ✅ 已有基础实现 | line 397-433: 3次修复尝试 |
| 智能退出机制 | ✅ 已有基础实现 | line 309-356: 多种退出条件 |
| column_details传递 | ✅ 已恢复 | line 251-260: 传递到execution_context |

**关键代码片段**：
```python
# line 397-433: SQL修复循环
if not exec_result.get("success") and current_sql:
    issues = context.get("issues", [])
    if issues:
        sql_fix_attempts = execution_context.get("sql_fix_attempts", 0)
        if sql_fix_attempts < 3:  # 最多3次
            execution_context["sql_fix_attempts"] = sql_fix_attempts + 1
            # ... 修复逻辑
```

---

## 二、尚未恢复的机制 ❌

### 1. orchestrator.py 缺少ResourcePool模式

**backend-old实现** (line 199-217):
```python
# 🆕 [T045] 初始化ResourcePool - 使用精简记忆模式
use_resource_pool = getattr(settings, 'ENABLE_CONTEXT_CURATION', True)
resource_pool = ResourcePool() if use_resource_pool else None

if use_resource_pool:
    self._logger.info(f"🗄️ [PTAV循环] 启用ResourcePool模式（精简记忆）")
else:
    self._logger.info(f"📋 [PTAV循环] 使用传统累积上下文模式")

execution_context = {
    "resource_pool": resource_pool  # 🆕 传递ResourcePool引用
}
```

**当前backend实现** (line 196-205):
```python
# ❌ 缺少ResourcePool初始化
execution_context = {
    "session_id": session_id,
    "current_sql": "",
    "validation_results": [],
    "execution_history": [],
    "goal_achieved": False,
    "last_error": None,
    "accumulated_observations": []
}
# 没有resource_pool字段
```

**影响**：
- 上下文会累积增大，导致token消耗过高
- 无法使用精简记忆模式优化性能

---

### 2. orchestrator.py 缺少ResourcePool更新逻辑

**backend-old实现** (line 258-291):
```python
# 🆕 [T046-T047] 使用ResourcePool更新上下文，替代累积模式
context = exec_result.get("context", {})

if use_resource_pool and resource_pool:
    # 🗄️ ResourcePool模式：存储详细信息到资源池
    updates = {}

    if context.get("current_sql"):
        execution_context["current_sql"] = context["current_sql"]
        updates["current_sql"] = context["current_sql"]

    if context.get("column_details"):
        updates["column_details"] = context["column_details"]
        self._logger.info(f"🗄️ [ResourcePool] 存储column_details: {len(context['column_details'])}张表")

    # ... 其他字段更新

    # 批量更新ResourcePool
    if updates:
        resource_pool.update(updates)
```

**当前backend实现** (line 245-260):
```python
# ❌ 直接累积到execution_context
context = exec_result.get("context", {})
if context.get("current_sql"):
    execution_context["current_sql"] = context["current_sql"]

# 传递schema信息到下一轮
if context.get("column_details"):
    execution_context["column_details"] = context["column_details"]
# ... 直接存储，没有使用ResourcePool
```

**影响**：
- execution_context不断膨胀
- 每轮迭代都传递完整的column_details

---

### 3. orchestrator.py 缺少智能错误诊断

**backend-old实现** (line 359-383):
```python
def _summarize_sql_errors(self, issues: list, database_error: Dict[str, Any]) -> str:
    """简单总结SQL错误（仅用于日志，不做决策 - 决策由Agent完成）"""
    # 合并所有错误信息
    all_error_text = " ".join(str(i) for i in issues)
    if database_error:
        original_error = database_error.get("original_error", "")
        all_error_text += " " + str(original_error)

    error_lower = all_error_text.lower()

    # 简单关键词匹配（仅用于分类，不影响修复策略）
    if any(kw in error_lower for kw in ["unknown column", "column.*not found"]):
        return "字段名不存在"
    elif any(kw in error_lower for kw in ["table.*not found"]):
        return "表名不存在"
    elif any(kw in error_lower for kw in ["syntax", "parse"]):
        return "SQL语法错误"
    # ...
```

**当前backend实现**:
```python
# ❌ 没有错误诊断方法
# SQL修复循环中没有错误分类
```

**影响**：
- 无法向Agent提供错误类型提示
- 修复策略不够精准

---

### 4. orchestrator.py 缺少修复策略标记

**backend-old实现** (line 489-497):
```python
# 🔍 简单的错误类型识别（用于日志和提示，不做决策）
error_summary = self._summarize_sql_errors(issues, database_error)
execution_context["last_error_summary"] = error_summary
self._logger.info(f"📋 [SQL修复循环] 错误摘要: {error_summary}")

# 标记schema状态供Agent参考
has_column_details = bool(execution_context.get("column_details"))
execution_context["needs_schema_refresh"] = not has_column_details
execution_context["needs_sql_regeneration"] = has_column_details
```

**当前backend实现** (line 397-425):
```python
# ❌ 没有错误摘要和策略标记
if not exec_result.get("success") and current_sql:
    issues = context.get("issues", [])
    if issues:
        sql_fix_attempts = execution_context.get("sql_fix_attempts", 0)
        if sql_fix_attempts < 3:
            execution_context["sql_fix_attempts"] = sql_fix_attempts + 1
            execution_context["last_sql_issues"] = issues
            # 缺少error_summary, needs_schema_refresh, needs_sql_regeneration
```

**影响**：
- Agent无法获得修复策略提示
- 缺少智能修复引导

---

### 5. orchestrator.py _update_ai_with_context缺少ResourcePool支持

**backend-old实现** (line 622-669):
```python
def _update_ai_with_context(self, ai, execution_context):
    # ... 省略前面的代码

    # 🆕 [T048] 根据feature flag选择传递模式
    resource_pool = execution_context.get("resource_pool")
    use_resource_pool = getattr(settings, 'ENABLE_CONTEXT_CURATION', True)

    if use_resource_pool and resource_pool:
        # 🗄️ ResourcePool模式：传递轻量级ContextMemory
        context_memory = resource_pool.build_context_memory()
        tdc["context_memory"] = context_memory.to_dict()

        self._logger.info(
            f"🗄️ [Orchestrator] 使用轻量级ContextMemory传递上下文: "
            f"has_sql={context_memory.has_sql}, "
            f"schema_available={context_memory.schema_available}"
        )
    else:
        # 📋 传统模式：传递完整schema信息
        if execution_context.get("column_details"):
            tdc["column_details"] = execution_context["column_details"]
```

**当前backend实现** (line 450-522):
```python
def _update_ai_with_context(self, ai, execution_context):
    # ... 省略前面的代码

    # ❌ 只有传统模式，没有ResourcePool支持
    # 传递schema信息 - 优先使用execution_context的累积信息
    if execution_context.get("column_details"):
        tdc["column_details"] = execution_context["column_details"]
        self._logger.info(f"📋 [Orchestrator] 从execution_context传递column_details")
```

**影响**：
- 无法使用精简记忆模式
- 每轮都传递完整的column_details

---

### 6. planner.py 缺少增强的SQL修复提示词

**backend-old实现** (line 256-369):
```python
async def _build_sql_fix_prompt(self, ai, fix_context, available_tools):
    """构建SQL修复专用提示词 - Agent驱动的智能分析"""
    needs_schema_refresh = fix_context.get("needs_schema_refresh", False)
    needs_sql_regeneration = fix_context.get("needs_sql_regeneration", False)
    error_summary = fix_context.get("error_summary", "")

    # 构建修复策略提示
    strategy_hint = ""
    if needs_schema_refresh:
        strategy_hint = "\n🔍 **修复策略提示**: 缺少详细字段信息，建议先调用 schema.get_columns"
    elif needs_sql_regeneration:
        strategy_hint = "\n🔄 **修复策略提示**: 有详细字段信息但SQL使用了错误的字段名，建议重新生成SQL"

    return f"""
你是SQL修复专家。当前SQL验证失败，需要你**智能分析错误原因**并制定修复策略。

## 当前状态
**修复尝试次数**: {sql_fix_attempts}/3
**Schema信息状态**: {schema_status}
**当前SQL**: ...
**验证失败的问题**: ...
{strategy_hint}

## 你的任务
请**仔细分析**上述错误信息，判断错误的**根本原因**，然后制定**单步骤**修复计划。

### 常见错误类型和修复策略
1. **字段名/表名不存在**
   - 没有详细字段信息 → schema.get_columns
   - 已有详细字段信息 → sql_generation 重新生成
   - **不要**用 sql.refine 修复字段名错误

2. **SQL语法错误** → sql.refine

3. **时间字段选择错误** → sql_generation (有schema) 或 schema.get_columns

4. **权限/连接错误** → 无法修复
```

**当前backend实现**:
```python
# ❌ planner.py中没有_build_sql_fix_prompt方法
# 使用通用的build_plan_prompt，缺少SQL修复专用指导
```

**影响**：
- Agent缺少精准的修复策略引导
- 修复成功率降低

---

### 7. planner.py _analyze_sql_fix_context缺少修复策略标记

**backend-old实现** (line 220-254):
```python
def _analyze_sql_fix_context(self, ai):
    """分析SQL修复上下文 - 增强版，支持智能修复策略"""
    # ... 省略前面的代码

    # 新增：获取修复策略标记（由Agent做最终决策）
    needs_schema_refresh = planning_hints.get('needs_schema_refresh', False)
    needs_sql_regeneration = planning_hints.get('needs_sql_regeneration', False)
    sql_fix_attempts = planning_hints.get('sql_fix_attempts', 0)
    error_summary = planning_hints.get('last_error_summary', '')

    return {
        "in_fix_cycle": in_fix_cycle,
        "current_sql": current_sql,
        "issues": validation_issues,
        # 新增：修复策略标记
        "needs_schema_refresh": needs_schema_refresh,
        "needs_sql_regeneration": needs_sql_regeneration,
        "sql_fix_attempts": sql_fix_attempts,
        "error_summary": error_summary,
    }
```

**当前backend实现**:
```python
# ❌ planner.py中没有_analyze_sql_fix_context方法
# 没有修复策略标记提取
```

**影响**：
- 无法传递修复策略提示给Agent
- 缺少修复上下文分析

---

### 8. context_prompt_controller.py 缺少ResourcePool模式支持

**backend-old实现** (line 24-76):
```python
async def build_plan_prompt(self, ai, stage, available_tools):
    """构建计划生成提示词

    🆕 [T067-T068] 支持ResourcePool模式：使用ContextMemory代替全量schema传递
    """
    # ... 工具列表和基础上下文

    # 🆕 [T069-T070] 检测ResourcePool模式
    use_resource_pool = getattr(settings, 'ENABLE_CONTEXT_CURATION', True)
    context_memory: Optional[ContextMemory] = None

    # 从task_driven_context提取ContextMemory或column_details
    if hasattr(ai, 'task_driven_context') and ai.task_driven_context:
        if isinstance(ai.task_driven_context, dict):
            # 🆕 [T071] 优先检测ContextMemory（ResourcePool模式）
            if use_resource_pool and ai.task_driven_context.get('context_memory'):
                context_memory_dict = ai.task_driven_context.get('context_memory')
                if isinstance(context_memory_dict, dict):
                    context_memory = ContextMemory.from_dict(context_memory_dict)

    # 🆕 [T072-T073] 根据模式选择上下文构建方式
    if use_resource_pool and context_memory:
        # 🗄️ ResourcePool模式：使用轻量级状态指引
        if context_memory.schema_available:
            context_info.append(f"✅ Schema信息已获取: {len(context_memory.available_tables)}张表可用")
        else:
            context_info.append("❌ Schema信息未获取，请先调用 schema.list_tables")
    else:
        # 📋 传统模式：使用详细字段信息
        if isinstance(column_details, dict) and column_details:
            # 显示所有字段...
```

**当前backend实现**:
```python
# ❌ context_prompt_controller.py缺少ResourcePool模式检测和支持
# 只有传统模式的column_details处理
```

**影响**：
- 提示词中无法使用ContextMemory状态
- 缺少schema状态的清晰展示

---

## 三、差异总结表

| 文件 | 功能模块 | Backend-Old | Backend当前 | 状态 | 优先级 |
|------|----------|-------------|-------------|------|--------|
| executor.py | column_details保留 | ✅ 保留所有表 | ✅ 已恢复 | ✅ 完成 | P0 |
| executor.py | 字段显示 | ✅ 显示所有字段+类型 | ✅ 已恢复 | ✅ 完成 | P0 |
| executor.py | LLM智能表选择 | ✅ _select_tables_with_llm | ✅ 已恢复 | ✅ 完成 | P1 |
| orchestrator.py | ResourcePool初始化 | ✅ 支持 | ❌ 缺少 | ⏳ 待恢复 | P1 |
| orchestrator.py | ResourcePool更新 | ✅ 支持 | ❌ 缺少 | ⏳ 待恢复 | P1 |
| orchestrator.py | 错误诊断 | ✅ _summarize_sql_errors | ❌ 缺少 | ⏳ 待恢复 | P1 |
| orchestrator.py | 修复策略标记 | ✅ needs_schema_refresh等 | ❌ 缺少 | ⏳ 待恢复 | P1 |
| orchestrator.py | ContextMemory传递 | ✅ 支持 | ❌ 缺少 | ⏳ 待恢复 | P1 |
| planner.py | SQL修复提示词 | ✅ _build_sql_fix_prompt | ❌ 缺少 | ⏳ 待恢复 | P1 |
| planner.py | 修复上下文分析 | ✅ _analyze_sql_fix_context | ❌ 缺少 | ⏳ 待恢复 | P1 |
| context_prompt_controller.py | ResourcePool支持 | ✅ ContextMemory检测 | ❌ 缺少 | ⏳ 待恢复 | P2 |

---

## 四、恢复方案

### 方案A：全面恢复（推荐）

**优势**：
- 完整恢复backend-old的稳定机制
- 获得最佳的SQL生成能力和修复能力
- 支持ResourcePool精简记忆模式

**步骤**：
1. 更新orchestrator.py：
   - 添加ResourcePool初始化 (line 199-217)
   - 添加ResourcePool更新逻辑 (line 258-291)
   - 添加_summarize_sql_errors方法 (line 359-383)
   - 更新修复循环添加策略标记 (line 489-497)
   - 更新_update_ai_with_context支持ContextMemory (line 622-669)

2. 更新planner.py：
   - 添加_analyze_sql_fix_context方法 (line 220-254)
   - 添加_build_sql_fix_prompt方法 (line 256-369)
   - 更新_build_plan_prompt调用修复提示词 (line 208-218)

3. 更新context_prompt_controller.py：
   - 添加ResourcePool模式检测 (line 33-76)
   - 更新build_plan_prompt支持ContextMemory (line 24-157)

4. 添加配置项：
   - backend/app/core/config.py添加ENABLE_CONTEXT_CURATION配置

**工作量**：约2-3小时

---

### 方案B：最小恢复（不推荐）

**仅恢复orchestrator.py的SQL修复增强**：
- 添加_summarize_sql_errors方法
- 添加修复策略标记

**缺点**：
- 无法使用ResourcePool精简记忆
- 上下文会累积增大
- 缺少SQL修复专用提示词
- Agent引导不够精准

**工作量**：约30分钟

---

## 五、实施计划（方案A）

### 阶段1：orchestrator.py核心增强 (60分钟)

```bash
# 1. 添加ResourcePool初始化和更新
- line 196-217: 初始化resource_pool
- line 245-291: ResourcePool更新逻辑

# 2. 添加错误诊断
- line 359-383: _summarize_sql_errors方法

# 3. 增强修复循环
- line 489-497: 添加error_summary和策略标记

# 4. 更新_update_ai_with_context
- line 622-669: 支持ContextMemory传递
```

### 阶段2：planner.py SQL修复增强 (45分钟)

```bash
# 1. 添加修复上下文分析
- line 220-254: _analyze_sql_fix_context方法

# 2. 添加SQL修复提示词
- line 256-369: _build_sql_fix_prompt方法

# 3. 更新_build_plan_prompt
- line 208-218: 检测修复循环并调用专用提示词
```

### 阶段3：context_prompt_controller.py ResourcePool支持 (30分钟)

```bash
# 1. 添加ResourcePool检测
- line 33-76: 检测context_memory并使用

# 2. 更新build_plan_prompt
- line 24-157: 支持ContextMemory状态展示
```

### 阶段4：配置和测试 (15分钟)

```bash
# 1. 添加配置
- backend/app/core/config.py: ENABLE_CONTEXT_CURATION = True

# 2. 测试验证
- 基础SQL生成测试
- SQL修复循环测试
- ResourcePool模式测试
```

---

## 六、测试验证计划

### 测试1：基础SQL生成
```
输入：简单统计需求
期望：
- ✅ column_details完整传递
- ✅ 显示所有字段
- ✅ SQL生成成功
```

### 测试2：SQL修复循环
```
输入：生成一个使用错误字段名的SQL
期望：
- ✅ 检测到字段名错误
- ✅ 错误摘要：字段名不存在
- ✅ needs_schema_refresh或needs_sql_regeneration标记
- ✅ Agent接收修复提示词
- ✅ 3次内修复成功
```

### 测试3：ResourcePool模式
```
输入：多轮复杂SQL生成
期望：
- ✅ ResourcePool初始化
- ✅ ContextMemory传递生效
- ✅ execution_context不膨胀
- ✅ 日志显示ResourcePool更新
```

### 测试4：智能退出
```
输入：无法修复的SQL错误
期望：
- ✅ 3次修复后停止
- ✅ 智能退出检测生效
- ✅ 返回部分结果
```

---

## 七、风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| ResourcePool引入bug | 中 | 低 | feature flag控制，可回退传统模式 |
| ContextMemory字段映射错误 | 低 | 低 | 已有向后兼容处理（resource_pool.py line 75-121） |
| SQL修复提示词过长 | 低 | 低 | 提示词已优化，删除冗余内容 |
| 配置项缺失导致启动失败 | 中 | 低 | 提供默认值，向后兼容 |

---

## 八、回滚计划

如果恢复后出现问题：

### 快速回滚（5分钟）
```bash
# 1. 关闭ResourcePool模式
backend/app/core/config.py:
ENABLE_CONTEXT_CURATION = False  # 回退到传统模式

# 2. 重启服务
# ResourcePool相关代码会被跳过，使用传统模式
```

### 完全回滚（15分钟）
```bash
# 1. Git回退到恢复前的commit
git log --oneline  # 找到恢复前的commit
git checkout <commit_hash> -- backend/app/services/infrastructure/agents/

# 2. 重启服务
```

---

## 九、后续优化建议

### 1. 监控指标
- SQL生成成功率
- 修复循环成功率（3次内成功比例）
- ResourcePool命中率
- 平均token消耗

### 2. 性能优化
- ContextMemory序列化优化
- ResourcePool缓存策略
- LLM调用次数优化

### 3. 可观测性
- 添加详细的日志
- 修复循环可视化
- ResourcePool状态监控

---

**文档版本**: 1.0
**创建日期**: 2025-10-17
**作者**: Claude Code
**目的**: 指导backend agent机制恢复工作
