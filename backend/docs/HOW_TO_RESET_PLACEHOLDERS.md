# 重置占位符SQL - 完整指南

## 🎯 问题背景

在启用Context Retriever系统后，虽然schema信息能够正确获取，但如果占位符的SQL是在启用前生成的（使用了错误的表名），系统会跳过重新分析，继续使用旧的错误SQL。

### 症状

日志显示：
```
✅ Schema 缓存初始化完成，共 1 个表
   表名: online_retail (8列)

但SQL执行失败：
❌ MySQL查询执行失败: Unknown table 'sales_data'
❌ MySQL查询执行失败: Unknown table 'sales'
❌ MySQL查询执行失败: Unknown table 'products'

并且跳过分析：
所有 17 个占位符已就绪，跳过分析阶段...
```

## 🔧 解决方案

### 步骤1: 查看可用模板

```bash
cd /Users/shan/work/AutoReportAI/backend
python scripts/reset_placeholders.py --list-templates
```

### 步骤2: 演练模式（推荐先执行）

查看哪些占位符会被重置，但不实际修改：

```bash
# 重置所有模板的占位符（演练）
python scripts/reset_placeholders.py --dry-run

# 重置特定模板（演练）
python scripts/reset_placeholders.py --template-id <模板ID> --dry-run
```

### 步骤3: 执行重置

```bash
# 重置所有模板的占位符
python scripts/reset_placeholders.py

# 重置特定模板
python scripts/reset_placeholders.py --template-id <模板ID>
```

系统会：
1. 显示所有将被重置的占位符
2. 询问确认
3. 执行重置操作：
   - `agent_analyzed`: False
   - `sql_validated`: False
   - `generated_sql`: None
   - `target_table`: None
   - `target_database`: None

### 步骤4: 验证修复

1. **（可选）重启服务**
   ```bash
   # 在docker环境中
   docker-compose restart backend celery
   ```

2. **重新执行报告生成任务**

   使用前端或API触发报告生成

3. **检查日志**

   应该看到：
   ```
   ✅ Schema 缓存初始化完成，共 1 个表
   🔍 开始分析占位符...  # 注意：不再是"跳过分析"
   ✅ SQL生成成功，使用表: online_retail  # 使用正确的表名
   ✅ SQL执行成功
   ```

## 📊 预期效果

| 指标 | Before | After |
|------|--------|-------|
| 使用正确表名 | ❌ sales_data, sales, products | ✅ online_retail |
| SQL执行成功率 | 0% | ~95%+ |
| Schema Context使用 | ❌ 被跳过 | ✅ 正确使用 |

## 🔍 故障排查

### 如果重置后仍然使用错误表名

1. **检查Context Retriever是否真正启用**
   ```bash
   # 查看日志，应该看到：
   ✅ 已启用 ContextRetriever 动态上下文机制
   ✅ Schema 缓存初始化完成，共 X 个表
   ```

2. **检查schema是否正确获取**
   ```bash
   # 进入容器
   docker exec -it <backend-container> bash

   # 运行诊断脚本
   python scripts/diagnose_context_injection.py
   ```

3. **查看Agent的System Message**

   在 `runtime.py` 中临时添加日志：
   ```python
   logger.info(f"🔍 Agent System Message: {system_message[:500]}")
   ```

   应该包含完整的表结构信息。

### 如果占位符没有被重置

检查占位符状态：
```python
# 进入Python shell
python

from app.db.session import SessionLocal
from app.models.template_placeholder import TemplatePlaceholder

db = SessionLocal()
placeholders = db.query(TemplatePlaceholder).all()

for ph in placeholders[:5]:
    print(f"{ph.placeholder_name}: analyzed={ph.agent_analyzed}, validated={ph.sql_validated}")
```

## 💡 最佳实践

1. **每次修改schema信息源后都应重置**
   - 启用Context Retriever
   - 修改schema获取逻辑
   - 更换数据源

2. **使用演练模式预览**

   始终先用 `--dry-run` 查看会影响哪些占位符

3. **按模板重置**

   如果只有特定模板有问题，使用 `--template-id` 精确重置

4. **监控重新生成的SQL质量**

   重置后第一次执行时，仔细检查生成的SQL是否正确

## 📚 相关文档

- [Context系统架构](./CONTEXT_ENGINEERING_ARCHITECTURE.md)
- [Context Retriever启用报告](./CONTEXT_RETRIEVER_ENABLEMENT_COMPLETE.md)
- [Schema Context集成](./SCHEMA_CONTEXT_INTEGRATION.md)

## 🚀 自动化

如果需要定期重置，可以创建cron任务：

```bash
# 每天凌晨检查并重置需要的占位符
0 2 * * * cd /path/to/backend && python scripts/reset_placeholders.py --dry-run > /tmp/placeholder_check.log 2>&1
```
