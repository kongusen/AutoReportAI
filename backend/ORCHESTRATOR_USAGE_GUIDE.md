# Orchestrator 执行模式使用指南

UnifiedOrchestrator 现在支持四种不同的执行模式，每种模式针对不同的使用场景进行了优化：

## 1. PTOF模式 (Plan-Tool-Observe-Finalize)
**使用场景**: 简单的一次性任务，如基础SQL生成、简单数据查询

```python
# 传统模式 - 默认模式
result = await orchestrator.execute(ai_input, mode="ptof")
```

**特点**:
- 一次性执行完整计划
- 适合确定性强的简单任务
- 执行速度快，开销小
- 适合模板生成场景

## 2. PTAV循环模式 (Plan-Tool-Active-Validate)
**使用场景**: 复杂SQL生成、需要多轮验证和修正的任务

```python
# 单步骤循环模式 - 用于复杂任务
result = await orchestrator.execute(ai_input, mode="ptav")
```

**特点**:
- Agent主导的单步骤循环
- 每步执行后立即返回Agent分析
- 真实数据库验证确保SQL正确性
- 自动修正和优化
- 适合复杂业务逻辑的SQL生成

**流程**:
1. **Plan**: Agent分析当前状态，决策下一步行动
2. **Tool**: 执行单个工具/动作
3. **Active**: Agent分析工具执行结果
4. **Validate**: Agent验证是否达到目标，决定继续或结束

## 3. Task SQL验证模式
**使用场景**: 任务执行过程中验证现有SQL的有效性

```python
# SQL验证模式 - 用于任务中SQL更新
ai_input.current_sql = "SELECT * FROM ods_users WHERE..."
result = await orchestrator.execute(ai_input, mode="task_sql_validation")
```

**特点**:
- 检查现有SQL是否过时或有缺陷
- 基于最新schema和业务需求验证
- 最小化修正，保持原有逻辑
- 针对性验证，不做完整重建

**返回结果**:
```python
# 验证通过
{
    "validation_status": "passed",
    "current_sql": "原SQL",
    "message": "现有SQL验证通过，无需更新"
}

# 需要修正
{
    "validation_status": "corrected",
    "original_sql": "原SQL",
    "current_sql": "修正后SQL",
    "issues_fixed": ["问题列表"],
    "message": "SQL已修正，解决了N个问题"
}
```

## 4. 报告图表生成模式
**使用场景**: 报告生成中将查询数据转换为图表

```python
# 图表生成模式 - 用于报告中数据可视化
ai_input.data_rows = query_result_rows
ai_input.data_columns = query_result_columns
result = await orchestrator.execute(ai_input, mode="report_chart_generation")
```

## 5. 任务验证智能模式 (推荐) ⭐
**使用场景**: 任务执行时的智能SQL验证和生成

```python
# 智能任务验证模式 - SQL验证 + PTAV回退机制
result = await agent_facade.execute_task_validation(ai_input)
```

**核心优势**:
- **自动化运维**: 维护存量任务健康 + 自动初始化新任务
- **时间属性智能更新**: 自动检查和更新SQL中的日期时间
- **零配置回退**: 缺失SQL时自动生成，无需人工干预

**完整工作流**:
1. **检查现有SQL**: 任务触发时自动检查是否存在SQL
2. **健康验证**:
   - ✅ 时间属性检查和动态更新 (如每日报告的日期更新)
   - ✅ Schema兼容性验证
   - ✅ 语法和数据库连通性验证
3. **智能回退**:
   - 如果SQL缺失 → PTAV模式从零生成
   - 如果SQL不可修复 → PTAV模式重新生成
4. **结果优化**: 标记生成方法，便于监控和调试

**适用场景**:
- 定时任务执行前的SQL健康检查
- 新创建任务的SQL自动生成
- 数据源变更后的SQL兼容性检查
- 生产环境的自动化运维

**特点**:
- 验证查询结果数据的完整性和格式
- 根据数据特征选择合适的图表类型
- 生成图表配置和样式
- 生成最终图表文件
- 添加图例说明和格式化

**管道流程**:
1. **data.quality**: 验证数据质量和格式
2. **chart.spec**: 生成图表配置
3. **word_chart_generator**: 生成最终图表文件

## 模式选择建议

| 任务类型 | 推荐模式 | 理由 |
|---------|---------|------|
| 🎯 **定时任务执行** | **任务验证智能模式** ⭐ | 自动SQL健康检查+回退生成，零配置运维 |
| 🎯 **生产任务运维** | **任务验证智能模式** ⭐ | 时间属性更新+兼容性检查+智能修复 |
| 模板SQL生成 | PTOF | 确定性强，一次性完成 |
| 复杂业务SQL | PTAV循环 | 需要多轮验证和修正 |
| 数据可视化 | 报告图表生成 | 专门的图表生成管道 |
| 实验性需求 | PTAV循环 | Agent可以探索最佳方案 |
| 手动SQL检查 | Task SQL验证 | 针对性验证现有SQL |

**⭐ 最佳实践**: 对于所有生产环境的任务执行，推荐使用**任务验证智能模式**，它结合了SQL健康检查和自动生成的优势，实现真正的自动化运维。

## 错误处理

每种模式都有专门的错误处理机制：

```python
result = await orchestrator.execute(ai_input, mode="ptav")

if result.success:
    print(f"执行成功: {result.content}")
    print(f"详细信息: {result.metadata}")
else:
    print(f"执行失败: {result.metadata.get('error')}")
    print(f"部分结果: {result.metadata.get('partial_result', '')}")
```

## 日志和调试

每种模式都有详细的日志记录：

- `🚀` - 开始执行
- `📋` - PTOF模式
- `🔄` - PTAV循环模式
- `🔍` - SQL验证模式
- `📊` - 图表生成模式
- `✅` - 执行成功
- `❌` - 执行失败
- `⚠️` - 警告

## 性能考虑

1. **PTOF模式**: 最快，单次执行
2. **PTAV循环模式**: 较慢，多轮迭代，但结果质量最高
3. **Task SQL验证**: 中等，针对性验证
4. **图表生成**: 取决于数据量和图表复杂度

建议根据实际需求选择合适的模式，在质量和性能之间找到平衡。