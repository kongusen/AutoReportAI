# 图表生成集成方案 - 完整总结

## 📋 概述

本方案实现了基于ETL数据的智能图表生成功能，让Agent能够识别`{{图表：xxx}}`格式的占位符，自动生成图表并嵌入Word文档。

---

## 🎯 你的流程编排（tasks.py）

### 阶段1：Agent生成SQL (Line 400-500)
```python
# 1. 扫描模板占位符
# 2. Agent为每个占位符生成SQL
# 3. 验证并保存SQL到数据库
```

### 阶段2：ETL数据处理 (Line 600-900)
```python
# 执行所有占位符的SQL
for ph in placeholders:
    # 替换时间占位符
    final_sql = sql.replace("{{start_date}}", time_ctx['start_date'])

    # 执行查询
    query_result = await connector.execute_query(final_sql)

    # 存储结果
    etl_results[ph.placeholder_name] = actual_value
```

**关键点**：此时`etl_results`字典包含所有占位符的查询结果，包括图表占位符的数据。

### 阶段3：文档生成 (Line 918-996)
```python
# 调用WordTemplateService处理文档
assemble_res = await word_service.process_document_template(
    template_path=tpl_meta['path'],
    placeholder_data=etl_results,  # 传入ETL结果
    output_path=docx_out,
    container=container,
    use_agent_charts=True,  # 启用智能图表生成
    use_agent_optimization=True
)
```

---

## 🔧 实现的组件

### 1. ChartGenerationTool (chart_tools.py)
**Agent工具**，提供图表生成能力：

```python
# 调用示例
chart_tool = ChartGenerationTool()
result = await chart_tool.execute({
    "chart_type": "bar",
    "data": [{"州市": "北京", "申请量": 523}, ...],
    "title": "州市退货申请量",
    "x_column": "州市",
    "y_column": "申请量",
    "user_id": "user_123"
})

# 返回
{
    "success": True,
    "chart_path": "/tmp/charts/user_123/chart_bar_xxx.png",
    "chart_type": "bar",
    "generation_time_ms": 245
}
```

**支持的图表类型**：
- `bar` - 柱状图
- `line` - 折线图
- `pie` - 饼图
- `scatter` - 散点图
- `area` - 面积图

### 2. ChartDataAnalyzerTool (chart_tools.py)
**数据分析工具**，推荐合适的图表类型：

```python
analyzer = ChartDataAnalyzerTool()
result = await analyzer.execute({
    "data": [...],
    "intent": "显示月度销售趋势"
})

# 返回
{
    "success": True,
    "recommended_chart_type": "line",
    "x_column": "month",
    "y_column": "sales",
    "reasoning": "数据包含时间序列，推荐使用折线图展示趋势"
}
```

### 3. ChartPlaceholderProcessor (chart_placeholder_processor.py)
**图表占位符处理器**，处理文档中的图表占位符：

```python
processor = ChartPlaceholderProcessor(user_id="user_123")

# 处理单个图表占位符
result = await processor.process_chart_placeholder(
    placeholder_text="{{图表：州市退货申请量由高到低排列并显示对应申请量的柱状图}}",
    data=etl_results[placeholder_key]
)
```

**功能**：
1. 从占位符文本提取图表意图（类型、标题、描述）
2. 调用ChartDataAnalyzerTool分析数据
3. 调用ChartGenerationTool生成图表
4. 返回图表文件路径

### 4. WordTemplateService (word_template_service.py)
**文档模板服务**，已修改为使用ChartPlaceholderProcessor：

```python
# _replace_chart_placeholders_with_agent方法（Line 422-514）
async def _replace_chart_placeholders_with_agent(self, doc, data, ...):
    chart_processor = ChartPlaceholderProcessor(user_id=user_id)

    for p in doc.paragraphs:
        if p.text.startswith("{{图表："):
            # 获取ETL数据
            chart_data = data.get(placeholder)

            # 生成图表
            chart_result = await chart_processor.process_chart_placeholder(
                placeholder_text=placeholder,
                data=chart_data
            )

            # 插入图表到文档
            if chart_result["success"]:
                run = p.add_run()
                run.add_picture(chart_result["chart_path"], width=Inches(6.0))
```

---

## 📝 占位符格式

### 标准格式
```
{{图表：[描述][图表类型]}}
```

### 示例
```
{{图表：州市退货申请量由高到低排列并显示对应申请量的柱状图}}
{{图表：月度销售额趋势折线图}}
{{图表：产品类别销售占比饼图}}
{{图表：价格与销量关系散点图}}
```

### 提取逻辑
`ChartPlaceholderProcessor._extract_chart_intent()`会从占位符中提取：

1. **图表类型**：通过关键词识别
   - "柱状图" → bar
   - "折线图" → line
   - "饼图" → pie
   - "散点图" → scatter

2. **标题**：取描述的前半部分
   - "州市退货申请量由高到低排列..." → "州市退货申请量"

3. **完整描述**：用于数据分析

---

## 🔄 完整流程图

```
┌─────────────────────────────────────────────────────────────┐
│  阶段1: Agent生成SQL (tasks.py Line 400-500)               │
│  - 扫描占位符                                                │
│  - Agent生成SQL                                              │
│  - 保存到数据库                                              │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段2: ETL执行 (tasks.py Line 600-900)                    │
│  - 执行所有SQL查询                                           │
│  - 替换时间占位符                                            │
│  - 存储到 etl_results 字典                                  │
│                                                              │
│  etl_results = {                                            │
│    "图表：州市退货申请量...": [                              │
│      {"州市": "北京", "申请量": 523},                       │
│      {"州市": "上海", "申请量": 412},                       │
│      ...                                                     │
│    ]                                                         │
│  }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段3: 文档生成 (tasks.py Line 958)                        │
│  word_service.process_document_template(                    │
│    template_path=...,                                        │
│    placeholder_data=etl_results,  ← ETL数据                 │
│    use_agent_charts=True                                     │
│  )                                                           │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段4: 图表处理 (word_template_service.py Line 422)        │
│                                                              │
│  for 文档中的每个段落:                                        │
│    if 段落.text.startswith("{{图表："):                      │
│      ├─ 从etl_results获取数据                               │
│      ├─ ChartPlaceholderProcessor.process_chart_placeholder │
│      │   ├─ 提取图表意图 (类型、标题、描述)                  │
│      │   ├─ ChartDataAnalyzerTool.execute()                 │
│      │   │   └─ 分析数据，推荐图表类型                       │
│      │   ├─ ChartGenerationTool.execute()                   │
│      │   │   ├─ 验证参数                                     │
│      │   │   ├─ 准备数据                                     │
│      │   │   ├─ 使用matplotlib生成图表                       │
│      │   │   └─ 保存到 /tmp/charts/user_id/chart_xxx.png   │
│      │   └─ 返回图表路径                                     │
│      └─ 插入图片到Word文档                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ 已完成的集成

### 1. ✅ Agent工具注册
```python
# app/services/infrastructure/agents/tools/__init__.py (Line 95-96)
DEFAULT_TOOL_SPECS: Tuple[Tuple[str, str], ...] = (
    ...
    ("app.services.infrastructure.agents.tools.chart_tools", "ChartGenerationTool"),
    ("app.services.infrastructure.agents.tools.chart_tools", "ChartDataAnalyzerTool"),
)
```

### 2. ✅ WordTemplateService集成
```python
# app/services/infrastructure/document/word_template_service.py (Line 422-514)
# 已修改为使用ChartPlaceholderProcessor
```

### 3. ✅ tasks.py流程
```python
# app/services/infrastructure/task_queue/tasks.py (Line 958)
# 已经调用process_document_template with use_agent_charts=True
```

---

## 🧪 测试

### 运行集成测试
```bash
cd /Users/shan/work/AutoReportAI/backend
python scripts/test_chart_integration.py
```

### 测试覆盖
1. ✅ 图表占位符提取测试
2. ✅ 数据分析和类型推荐测试
3. ✅ 图表生成工具测试
4. ✅ Word文档集成测试
5. ✅ 完整流程测试（模拟tasks.py）

---

## 📊 性能考虑

### 图表生成时间追踪
```python
# ChartGenerationTool返回
{
    "generation_time_ms": 245  # 图表生成耗时
}

# 可以添加到chart_cache_service.py的TODO实现中
chart_generation_time_ms = chart_result.get("generation_time_ms", 0)
```

### 缓存建议
对于相同的数据和配置，可以考虑：
1. 缓存图表文件（使用数据hash作为key）
2. 使用PlaceholderChartCache模型存储图表结果
3. 添加TTL管理过期图表

---

## 🎯 使用示例

### 在模板中添加图表占位符
```docx
# 销售分析报告

## 统计数据
总销售额: {{total_sales}}
平均销售额: {{avg_sales}}

## 数据可视化
{{图表：州市退货申请量由高到低排列并显示对应申请量的柱状图}}

## 趋势分析
{{图表：月度销售额趋势折线图}}
```

### Agent SQL生成
Agent会为图表占位符生成SQL：
```sql
-- 为"州市退货申请量"占位符生成的SQL
SELECT 州市, COUNT(*) as 申请量
FROM 退货申请表
WHERE 申请日期 >= {{start_date}} AND 申请日期 <= {{end_date}}
GROUP BY 州市
ORDER BY 申请量 DESC
```

### ETL执行
```python
# ETL结果
etl_results = {
    "total_sales": 1780000,
    "avg_sales": 356000,
    "图表：州市退货申请量由高到低排列并显示对应申请量的柱状图": [
        {"州市": "北京", "申请量": 523},
        {"州市": "上海", "申请量": 412},
        {"州市": "广州", "申请量": 335},
        ...
    ]
}
```

### 文档生成
WordTemplateService自动：
1. 替换文本占位符（`{{total_sales}}` → 1780000）
2. 识别图表占位符（`{{图表：...}}`）
3. 调用ChartGenerationTool生成图表
4. 将图表插入文档

---

## 🔍 故障排除

### 问题1：图表数据未找到
```
❌ 没有找到图表数据: {{图表：xxx}}
```
**原因**：ETL结果中的key与占位符文本不匹配

**解决**：检查ETL结果的key格式，确保与模板中的占位符文本完全一致

### 问题2：图表生成失败
```
❌ 图表生成失败: 数据格式错误
```
**原因**：数据格式不正确

**解决**：确保ETL返回的数据是字典列表格式：
```python
[
    {"列1": 值1, "列2": 值2},
    {"列1": 值3, "列2": 值4},
    ...
]
```

### 问题3：matplotlib未安装
```
⚠️ 图表库未安装，请安装 matplotlib
```
**解决**：
```bash
pip install matplotlib
```

---

## 📚 相关文件

### 核心文件
- `app/services/infrastructure/agents/tools/chart_tools.py` - Agent图表工具
- `app/services/infrastructure/document/chart_placeholder_processor.py` - 图表占位符处理器
- `app/services/infrastructure/document/word_template_service.py` - Word模板服务
- `app/services/infrastructure/task_queue/tasks.py` - 任务执行流程

### 测试文件
- `scripts/test_chart_tool.py` - 基础工具测试
- `scripts/test_chart_integration.py` - 集成测试

### 模型
- `app/models/placeholder_chart_cache.py` - 图表缓存模型（待完善）
- `app/services/cache/chart_cache_service.py` - 图表缓存服务（TODO未完成）

---

## 🚀 下一步优化

1. **图表缓存实现**
   - 完成`chart_cache_service.py`中的TODO
   - 实现图表结果缓存
   - 添加`chart_generation_time_ms`追踪

2. **更多图表类型**
   - 堆叠柱状图
   - 双Y轴折线图
   - 漏斗图
   - 雷达图

3. **图表样式配置**
   - 支持自定义颜色方案
   - 支持图表尺寸配置
   - 支持中文字体配置

4. **错误处理增强**
   - 更详细的错误信息
   - 自动重试机制
   - 降级方案优化

---

## 📝 总结

✅ **已完成**：
1. 创建了3个Agent工具（ChartGenerationTool, ChartDataAnalyzerTool, ChartPlaceholderProcessor）
2. 集成到WordTemplateService
3. 注册到Agent工具系统
4. 完整的测试套件

✅ **工作流程**：
1. 模板中使用`{{图表：描述}}`格式的占位符
2. Agent生成SQL查询数据
3. ETL执行SQL并存储结果到etl_results
4. 文档生成时，WordTemplateService识别图表占位符
5. ChartPlaceholderProcessor调用图表工具生成图表
6. 图表自动插入Word文档

✅ **特点**：
- 智能图表类型推荐
- 基于ETL数据生成
- 支持多种图表类型
- 完整的错误处理和回退机制
- 详细的日志记录

🎉 **现在你的系统已经支持智能图表生成了！**
