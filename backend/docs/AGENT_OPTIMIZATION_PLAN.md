# Agent引用优化计划

## 🎯 核心观点
基于TT递归自动迭代特性，很多Agent引用是不必要的。我们的分析过程完全可以在TT递归中闭环。

**三步骤Agent架构**：
1. **第一阶段**：SQL生成（placeholder中调用）- 对还没有SQL的占位符分析生成SQL
2. **第二阶段**：图表生成（task中调用）- ETL后基于ETL结果，对图表占位符进行图表生成  
3. **第三阶段**：文档生成（基于图表数据回填模板）- 进行基于数据的小范围描述改写

## 🔍 当前问题分析

### 1. 重复的Agent调用模式
很多地方都在重复这些步骤：
```python
# 当前模式：每个地方都要重复
container = Container()
agent_facade = create_stage_aware_facade(container=container, enable_context_retriever=True)
await agent_facade.initialize(user_id=user_id, task_type="task", task_complexity=complexity)

result = None
async for event in agent_facade.execute_sql_generation_stage(...):
    if event.event_type == 'execution_completed':
        result = event.data
        break
```

### 2. TT递归已经可以闭环
我们的TT递归机制本身就是一个完整的分析过程：
- **Thought**: 分析问题
- **Tool**: 调用工具获取信息  
- **Thought**: 分析工具结果
- **Tool**: 继续调用工具
- **...**: 直到达到质量阈值

### 3. 不必要的中间层
很多地方在Agent外面又套了一层"分析服务"，这些实际上是不必要的。

## 💡 优化方案

### 方案1: 三步骤TT递归接口
```python
# 第一阶段：SQL生成（placeholder中调用）
sql_result = await execute_sql_generation_tt(
    placeholder="分析销售数据，生成月度销售报表",
    data_source_id=1,
    user_id="user_123"
)

# 第二阶段：图表生成（task中调用，基于ETL结果）
chart_result = await execute_chart_generation_tt(
    chart_placeholder="生成销售趋势图表",
    etl_data=etl_processed_data,
    user_id="user_123"
)

# 第三阶段：文档生成（基于图表数据回填模板）
document_result = await execute_document_generation_tt(
    paragraph_context="生成销售报告描述",
    placeholder_data={"sql": sql_result, "chart": chart_result},
    user_id="user_123"
)
```

### 方案2: 消除重复的分析服务
可以简化的服务：
- `DataAnalysisService.analyze_with_intelligence()` - 直接使用TT递归
- `SchemaAnalysisService` 中的多个分析方法 - 合并到TT递归中
- `PipelineHealthService._check_agent_system()` - 简化检查逻辑

### 方案2: 统一TT递归接口
```python
# 统一的TT递归调用接口，支持三步骤
async def execute_tt_recursion(
    question: str,
    data_source_id: int, 
    user_id: str,
    stage: str = "sql_generation",  # sql_generation/chart_generation/completion
    context: Optional[Dict[str, Any]] = None
) -> TTRecursionResponse:
    """统一的TT递归执行接口"""
    # 根据stage自动选择对应的执行方法
    # 每个阶段内部都使用TT递归自动迭代到满意结果
```

## 🚀 实施步骤

### 步骤1: 识别可简化的服务
- [ ] `DataAnalysisService` - 简化智能分析逻辑
- [ ] `SchemaAnalysisService` - 合并多个分析方法
- [ ] `PipelineHealthService` - 简化健康检查
- [ ] `WordTemplateService` - 简化文档优化

### 步骤2: 创建统一调用接口
- [ ] 创建 `execute_tt_recursion()` 统一接口
- [ ] 替换重复的Agent调用模式
- [ ] 简化错误处理逻辑

### 步骤3: 测试验证
- [ ] 验证TT递归的自动迭代能力
- [ ] 确保分析质量不降低
- [ ] 验证性能提升

## 📊 预期效果

### 代码简化
- 减少50%的Agent调用代码
- 消除重复的初始化逻辑
- 统一错误处理模式

### 性能提升
- 减少不必要的中间层
- 利用TT递归的自动优化
- 更好的上下文管理

### 维护性提升
- 统一的调用模式
- 更少的代码重复
- 更清晰的架构

## 🎯 关键洞察

**TT递归的核心价值**：
1. **自动迭代**：无需手动管理迭代过程
2. **质量保证**：自动达到质量阈值
3. **上下文管理**：自动管理工具调用和上下文
4. **错误恢复**：自动处理执行错误

**因此**：我们只需要定义输入需求，TT递归会自动迭代到满意结果，无需复杂的中间层和重复调用。
