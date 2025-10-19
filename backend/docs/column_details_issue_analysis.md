# Column_details 丢失问题分析

## 问题现象

用户报告的错误日志：
```
🧠 [Agent思考] 当前无现有SQL且schema信息充足，需要生成统计总交易记录数的SQL以进行下一步验证。
🚫 [Gating] 字段详情不满足: 缺少字段详情（column_details），需要先获取表字段信息
🧠 [PTAV循环] 第6轮分析结果: 成功=True
🚨 [PTAV智能退出] 5轮后仍无SQL生成
```

关键模式：
- Agent每轮都调用schema.get_columns（成功执行）
- 每轮都显示"缺少表列信息"
- 6轮后仍无SQL生成

## 上下文传递流程

### 第1轮：Agent调用schema.get_columns

1. **Executor执行工具** (`executor.py:230-387`)
   ```python
   result = await self._execute_tool_with_retry(tool_name, tool, enriched_input)
   ```

2. **更新context** (`executor.py:395-400`)
   ```python
   self._update_context_state(context, result, step.get("tool"))
   # 在 _update_context_state 中 (executor.py:1100-1117):
   if result.get("column_details"):
       context["column_details"] = result["column_details"]
       self._logger.info(f"📋 [Executor] 存储schema.get_columns详细字段信息: {len(result['column_details'])}张表")
   ```

3. **裁剪context** (`executor.py:398`)
   ```python
   self._reduce_context(context, step.get("tool"), result)
   # _reduce_context中 (executor.py:1349-1450):
   # 🔧 关键修复：只要有column_details，就保留它
   if new_details:
       context["column_details"] = new_details
       self._logger.debug(f"🔍 [_reduce_context] 保留column_details: {len(new_details)}张表 - {list(new_details.keys())}")
   elif details:
       # 即使new_details为空，如果原始details存在，也保留它
       context["column_details"] = details
       self._logger.debug(f"🔍 [_reduce_context] 保留原始column_details（未裁剪）: {len(details)}张表")
   ```

4. **返回给Orchestrator** (`executor.py:405-412`)
   ```python
   return {
       "success": True,
       "step_result": result,
       "context": context,  # ✅ context包含column_details
       "observations": observations,
       "decision_info": decision_info,
       "execution_time": step_duration
   }
   ```

### 第2轮准备：Orchestrator传递context

5. **Orchestrator收到exec_result** (`orchestrator.py:230-270`)
   ```python
   exec_result = await self.executor.execute(plan, ai)

   # 更新执行上下文状态 - 包括SQL和schema信息
   context = exec_result.get("context", {})

   # 传递schema信息到下一轮
   if context.get("column_details"):
       execution_context["column_details"] = context["column_details"]
       self._logger.info(f"📋 [PTAV循环] 传递column_details到execution_context: {len(context['column_details'])}张表")
   ```

6. **更新AI输入** (`orchestrator.py:295`)
   ```python
   ai = self._update_ai_with_context(ai, execution_context)

   # 在 _update_ai_with_context 中 (orchestrator.py:510-516):
   if execution_context.get("column_details"):
       tdc["column_details"] = execution_context["column_details"]
       self._logger.info(f"📋 [Orchestrator] 从execution_context传递column_details: {len(execution_context['column_details'])}张表")
   elif last_ctx.get("column_details"):
       tdc["column_details"] = last_ctx["column_details"]
       self._logger.info(f"📋 [Orchestrator] 从last_ctx传递column_details: {len(last_ctx['column_details'])}张表")
   ```

### 第2轮：Executor接收context

7. **Executor构建执行上下文** (`executor.py:128-205`)
   ```python
   async def _build_execution_context(self, ai: AgentInput, user_id: str, ds: Dict[str, Any]) -> Dict[str, Any]:
       # ...
       try:
           tdc = ai.task_driven_context or {}
           if isinstance(tdc, dict):
               # 从task_driven_context获取累积的schema信息
               if tdc.get("column_details"):
                   context["column_details"] = tdc["column_details"]
                   self._logger.info(f"📋 [Executor] 从task_driven_context获取column_details: {len(tdc['column_details'])}张表")
       except Exception:
           pass

       return context
   ```

8. **Gating检查** (`executor.py:257-261`)
   ```python
   missing_schema = (
       not context.get("schema_summary") and
       not (context.get("columns") and len(context.get("columns")) > 0) and
       not (context.get("column_details") and len(context.get("column_details")) > 0)
   )
   ```

## 问题诊断

### 可能原因1：schema.get_columns工具未返回column_details

**检查点**：
- schema.get_columns工具的返回值中是否包含column_details字段
- 字段格式是否正确（应该是 `{"table_name": {"field": {...}}}`）

**验证方法**：
```python
# 在 executor.py:1100-1117 的 _update_context_state 中添加调试日志
self._logger.info(f"📋 [Executor] 处理schema.get_columns结果: success={result.get('success')}")
self._logger.info(f"📋 [Executor] 结果包含的键: {list(result.keys()) if isinstance(result, dict) else 'Not dict'}")
```

### 可能原因2：_reduce_context误删column_details

**检查点**：
- _reduce_context中的条件判断是否正确
- selected_tables是否为空导致column_details被删除

**修复方案**：
已在 executor.py:1422-1450 添加保护逻辑：
```python
# 🔧 修复：如果仍然没有选中表，保留 column_details 中已有的所有表
if not selected_tables:
    selected_tables.update(details.keys())
    self._logger.debug(f"🔍 [_reduce_context] 未找到指定表，保留column_details中的所有表: {list(selected_tables)}")
```

### 可能原因3：Agent决策的tool_call未正确传递tables参数

**检查点**：
- Agent在Plan阶段调用schema.get_columns时，input中是否指定了tables参数
- 如果未指定，兜底策略是否能正确选择表

**验证方法**：
```python
# 在 executor.py:214-276 的表选择逻辑中添加调试日志
if tool_name in ("schema.list_columns", "schema.get_columns"):
    tables_input = enriched_input.get("tables") or []
    if tables_input:
        self._logger.info(f"✅ [PTAV-Tool] 使用Plan指定的tables: {tables_input}")
    else:
        self._logger.warning(f"⚠️ [PTAV-违规] Plan未指定tables，Tool阶段被迫使用兜底策略智能选择")
```

### 可能原因4：gating主动获取与Agent tool_call冲突

**检查点**：
- 当Agent决定调用schema.get_columns时，是否会被gating逻辑拦截
- gating主动获取的结果是否会被Agent的tool_call覆盖

**关键问题**：
Gating检查在`sql_generation`动作时才触发，而Agent调用schema.get_columns是`tool_call`动作，不会触发gating。

但是，当Agent在上一轮成功获取了column_details后，下一轮如果Agent决定`sql_generation`，此时如果column_details已丢失，就会触发gating主动获取。

## 调试建议

### 立即添加的日志

1. **在executor.py的_update_context_state中**（schema.get_columns部分）：
   ```python
   elif tool_name == "schema.get_columns":
       self._logger.info(f"📋 [Executor] 处理schema.get_columns结果: success={result.get('success')}")
       self._logger.info(f"📋 [Executor] 结果包含的键: {list(result.keys()) if isinstance(result, dict) else 'Not dict'}")
       self._logger.info(f"📋 [Executor] column_details存在: {bool(result.get('column_details'))}")
       if result.get('column_details'):
           self._logger.info(f"📋 [Executor] column_details表数量: {len(result['column_details'])}")
           self._logger.info(f"📋 [Executor] column_details表名: {list(result['column_details'].keys())}")
   ```

2. **在executor.py的_reduce_context中**（column_details处理部分）：
   ```python
   if isinstance(context.get("column_details"), dict):
       details = context["column_details"]
       self._logger.info(f"🔍 [_reduce_context开始] 当前column_details: {len(details)}张表 - {list(details.keys())}")

       # ... 处理逻辑 ...

       if new_details:
           self._logger.info(f"🔍 [_reduce_context结束] 保留new_details: {len(new_details)}张表 - {list(new_details.keys())}")
       elif details:
           self._logger.info(f"🔍 [_reduce_context结束] 保留原始details: {len(details)}张表 - {list(details.keys())}")
       else:
           self._logger.warning(f"❌ [_reduce_context结束] column_details被清空！")
   ```

3. **在executor.py的_build_execution_context中**：
   ```python
   tdc = ai.task_driven_context or {}
   if isinstance(tdc, dict):
       self._logger.info(f"📋 [构建上下文] task_driven_context包含的键: {list(tdc.keys())}")
       if tdc.get("column_details"):
           self._logger.info(f"📋 [构建上下文] 从tdc获取column_details: {len(tdc['column_details'])}张表 - {list(tdc['column_details'].keys())}")
       else:
           self._logger.warning(f"⚠️ [构建上下文] task_driven_context中没有column_details")
   ```

4. **在orchestrator.py的_update_ai_with_context中**：
   ```python
   if execution_context.get("column_details"):
       tdc["column_details"] = execution_context["column_details"]
       self._logger.info(f"📋 [Orchestrator] 从execution_context传递column_details: {len(execution_context['column_details'])}张表 - {list(execution_context['column_details'].keys())}")
   elif last_ctx.get("column_details"):
       tdc["column_details"] = last_ctx["column_details"]
       self._logger.info(f"📋 [Orchestrator] 从last_ctx传递column_details: {len(last_ctx['column_details'])}张表 - {list(last_ctx['column_details'].keys())}")
   else:
       self._logger.warning(f"⚠️ [Orchestrator] 既没有execution_context.column_details，也没有last_ctx.column_details")
   ```

### 验证测试用例

创建一个测试用例，模拟PTAV循环：
1. 第1轮：schema.list_tables
2. 第2轮：schema.get_columns（验证返回值）
3. 第3轮：sql_generation（验证column_details是否可用）

## 解决方案

根据调试日志的结果，可能需要：

1. **如果schema.get_columns未返回column_details**：
   - 检查SchemaGetColumnsTool的实现
   - 确保返回格式正确

2. **如果_reduce_context误删**：
   - 已添加保护逻辑，确保column_details持久化
   - 验证selected_tables的计算逻辑

3. **如果Agent未正确传递tables参数**：
   - 强化Plan提示词，要求Agent必须指定tables
   - 改进兜底策略的表选择算法

4. **如果Orchestrator传递丢失**：
   - 检查AgentInput的dataclass定义
   - 确保task_driven_context正确序列化/反序列化
