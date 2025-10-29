# Doris SQL生成提示词更新总结

## 更新概述

成功更新了Agent系统的SQL生成提示词，确保生成的SQL符合Doris数据库规范，并强制使用时间占位符 `{{start_date}}` 和 `{{end_date}}`，禁止硬编码日期值。

## 更新的文件

### 1. SQL生成模板
**文件**: `backend/app/services/infrastructure/agents/prompts/templates.py`

**主要更新**:
- 明确指定生成Doris SQL查询
- 添加Doris数据库规范说明
- 强制要求使用时间占位符 `{{start_date}}` 和 `{{end_date}}`
- 禁止硬编码任何日期值
- 提供Doris SQL示例和最佳实践
- 添加质量检查清单

**关键内容**:
```markdown
## 🎯 Doris 数据库规范（必须遵守）

### 1. Doris 语法特性
- 使用标准 SQL 语法，兼容 MySQL
- 支持 OLAP 分析查询
- 支持列式存储和向量化执行
- 支持多种数据类型：TINYINT, SMALLINT, INT, BIGINT, LARGEINT, FLOAT, DOUBLE, DECIMAL, DATE, DATETIME, CHAR, VARCHAR, STRING, BOOLEAN, JSON

### 2. Doris 查询优化
- 优先使用分区字段进行过滤
- 合理使用聚合函数：SUM, COUNT, AVG, MAX, MIN, GROUP_CONCAT
- 支持窗口函数：ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD
- 支持子查询和 CTE (WITH 子句)

## ⚠️ 时间占位符要求（强制遵守）

### 🔥 核心要求
**所有基于时间周期的查询必须使用时间占位符，禁止硬编码日期！**

### 必需的时间占位符
- **{{start_date}}**: 数据开始时间（YYYY-MM-DD格式）
- **{{end_date}}**: 数据结束时间（YYYY-MM-DD格式）
```

### 2. 系统提示词
**文件**: `backend/app/services/infrastructure/agents/prompts/system.py`

**主要更新**:
- 更新SQL生成能力描述，明确Doris规范
- 强调时间占位符使用要求
- 更新SQL生成阶段指导，包含Doris特定要求

**关键内容**:
```markdown
### 2. SQL 生成能力
- 生成符合Doris数据库语法规范的SQL查询
- 支持复杂查询：多表关联、子查询、窗口函数等
- 优化查询性能和可读性
- **必须使用时间占位符 {{start_date}} 和 {{end_date}}，禁止硬编码日期**
```

### 3. Agent运行时默认提示词
**文件**: `backend/app/services/infrastructure/agents/runtime.py`

**主要更新**:
- 更新默认系统提示词，强调Doris规范
- 添加时间占位符使用示例
- 更新TT递归执行流程，包含时间过滤要求

**关键内容**:
```markdown
## 🔥 关键要求
- **必须使用Doris兼容的SQL语法**
- **必须包含时间占位符 {{start_date}} 和 {{end_date}}**
- **禁止硬编码任何日期值**
- **所有时间相关查询必须使用时间过滤条件**

## Doris SQL示例
```sql
-- ✅ 正确示例
SELECT COUNT(*) AS total_count
FROM sales_table 
WHERE sale_date >= '{{start_date}}' 
  AND sale_date <= '{{end_date}}'

-- ❌ 错误示例（硬编码日期）
SELECT COUNT(*) FROM sales_table 
WHERE sale_date >= '2024-01-01' AND sale_date <= '2024-01-31'
```
```

### 4. 阶段配置管理器
**文件**: `backend/app/services/infrastructure/agents/config/stage_config.py`

**主要更新**:
- 更新SQL阶段系统提示词
- 强调Doris规范和时间占位符要求
- 添加Doris SQL示例

## 测试验证

### 测试脚本
**文件**: `backend/scripts/test_doris_sql_prompts.py`

**测试内容**:
- SQL生成模板内容检查
- 系统提示词内容检查
- SQL阶段提示词内容检查
- 提示词一致性检查

**测试结果**: ✅ 所有测试通过

## 关键特性

### 1. Doris数据库规范
- 明确指定使用Doris兼容的SQL语法
- 提供Doris特有的数据类型和函数说明
- 包含Doris性能优化建议

### 2. 强制时间占位符使用
- 必须使用 `{{start_date}}` 和 `{{end_date}}` 占位符
- 禁止硬编码任何日期值
- 提供正确和错误的SQL示例对比

### 3. 质量保证
- 添加质量检查清单
- 包含验证步骤和工具使用指导
- 提供错误示例和正确示例对比

### 4. 一致性保证
- 所有相关提示词保持一致
- 系统提示词、模板提示词、阶段提示词都包含相同要求
- 确保Agent在不同阶段都能正确理解要求

## 预期效果

### 1. SQL生成质量提升
- Agent生成的SQL将符合Doris规范
- 所有时间相关查询都会使用占位符
- 减少硬编码日期导致的维护问题

### 2. 存储策略优化
- 生成的SQL包含时间占位符，可以在不同周期重复使用
- 在ETL阶段才进行时间占位符替换
- 提高SQL的可重用性和维护性

### 3. 开发效率提升
- 减少手动修改SQL的工作量
- 提高SQL生成的一致性和准确性
- 降低因硬编码日期导致的错误

## 使用示例

### 正确的SQL生成
```sql
-- Agent将生成这样的SQL
SELECT COUNT(*) AS total_count
FROM sales_table 
WHERE sale_date >= '{{start_date}}' 
  AND sale_date <= '{{end_date}}'
```

### ETL阶段替换
```python
# 在ETL阶段进行时间占位符替换
from app.utils.sql_placeholder_utils import SqlPlaceholderReplacer

sql_replacer = SqlPlaceholderReplacer()
time_context = {
    'data_start_time': '2024-01-01',
    'data_end_time': '2024-01-31'
}

final_sql = sql_replacer.replace_time_placeholders(generated_sql, time_context)
# 结果: SELECT COUNT(*) AS total_count FROM sales_table WHERE sale_date >= '2024-01-01' AND sale_date <= '2024-01-31'
```

## 总结

通过这次提示词更新，我们确保了：

1. **Agent生成的SQL符合Doris规范**，提高数据库兼容性
2. **强制使用时间占位符**，避免硬编码日期值
3. **提高SQL的可重用性**，支持不同周期的任务执行
4. **保持提示词一致性**，确保Agent在不同阶段都能正确理解要求
5. **提供完整的示例和指导**，帮助Agent生成高质量的SQL

这些更新将显著提升占位符分析任务中SQL生成的质量和可维护性，为后续的ETL阶段提供更好的基础。
