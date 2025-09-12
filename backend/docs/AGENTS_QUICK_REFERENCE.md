# Agents 系统快速参考

## 🚀 快速开始

```python
from app.services.infrastructure.agents import execute_agent_task

# 最简单的使用方式
result = await execute_agent_task(
    task_name="模板填充",
    task_description="生成业务报告", 
    context_data={
        "placeholders": {
            "company_name": "科技公司",
            "revenue": 1250.8
        }
    }
)
```

## 📊 核心数据结构速查

### 1. 输入数据结构

```python
# execute_agent_task 输入
{
    "task_name": str,                    # 任务名称
    "task_description": str,             # 任务描述
    "context_data": {
        "placeholders": Dict[str, Any],  # 占位符数据
        "templates": List[Dict],         # 模板信息
        "database_schemas": List[Dict]   # 数据库模式
    },
    "target_agent": str,                 # 目标Agent (可选)
    "timeout_seconds": int               # 超时时间 (默认300)
}
```

### 2. 模板填充输入结构

```python
# TemplateFillTool 输入
{
    "template_content": str,             # 模板内容 (必需)
    "placeholders": Dict[str, Any],      # 占位符数据 (必需)
    "template_type": str,                # "word"|"html"|"markdown" (默认"word")
    "fill_mode": str,                    # "smart"|"exact"|"descriptive" (默认"smart")
    "add_descriptions": bool,            # 是否添加描述 (默认True)
    "generate_word_document": bool,      # 是否生成Word (默认True)
    "document_title": str,               # 文档标题
    "enable_quality_check": bool         # 是否质量检查 (默认True)
}
```

### 3. 输出数据结构

```python
# 标准输出格式
{
    "success": bool,                     # 是否成功
    "result": {                          # 结果数据
        "filled_content": str,           # 填充后内容
        "word_document": {               # Word文档信息
            "success": bool,
            "word_document_path": str,   # 文档路径
            "quality_check": {           # 质量检查
                "overall_score": float,  # 总体分数
                "issues": List[str],     # 问题列表
                "recommendations": List[str]  # 建议
            }
        },
        "template_analysis": {           # 模板分析
            "total_placeholders": int,
            "filled_placeholders": int,
            "complexity_score": int
        }
    },
    "context": Dict,                     # 上下文信息
    "target_agent": str                  # 使用的Agent
}
```

## 🔧 常用枚举类型

### 上下文类型
```python
ContextType.DATA_ANALYSIS           # 数据分析
ContextType.REPORT_GENERATION       # 报告生成  
ContextType.SQL_GENERATION          # SQL生成
ContextType.TEMPLATE_FILLING        # 模板填充 ⭐
```

### 占位符类型
```python
PlaceholderType.TEMPLATE_VARIABLE   # 模板变量
PlaceholderType.FILL_MODE           # 填充模式
PlaceholderType.TEMPLATE_TYPE       # 模板类型
PlaceholderType.DATE_RANGE          # 日期范围
PlaceholderType.TABLE_NAME          # 表名
```

### 填充模式
```python
"exact"        # 精确替换
"smart"        # 智能格式化 (推荐)
"descriptive"  # 包含描述
"enhanced"     # 智能+描述
```

## 📝 支持的占位符格式

```python
{placeholder}      # 推荐格式
{{placeholder}}    # 双花括号  
<placeholder>      # 尖括号
[placeholder]      # 方括号
%placeholder%      # 百分号
${placeholder}     # 美元符号
```

## 🎯 典型使用场景

### 场景1: 简单模板填充
```python
result = await execute_agent_task(
    task_name="生成合同",
    task_description="填充合同模板",
    context_data={
        "templates": [{
            "id": "contract_template",
            "content": "甲方：{party_a}，乙方：{party_b}，签约日期：{sign_date}",
            "type": "word"
        }],
        "placeholders": {
            "party_a": "ABC公司",
            "party_b": "XYZ公司", 
            "sign_date": "2024-03-15"
        }
    }
)
```

### 场景2: 财务报告生成
```python
result = await execute_agent_task(
    task_name="季度财务报告",
    task_description="生成Q1财务分析报告",
    context_data={
        "placeholders": {
            "company_name": "创新科技",
            "revenue": 2580.5,
            "profit_margin": 15.3,
            "growth_rate": 12.8,
            "report_quarter": "2024Q1"
        }
    },
    target_agent="report_generation_agent"
)
```

### 场景3: 批量文档处理
```python
tasks = []
for doc_data in document_list:
    task = execute_agent_task(
        task_name=f"处理文档_{doc_data['id']}",
        task_description="文档模板填充",
        context_data=doc_data
    )
    tasks.append(task)

results = await asyncio.gather(*tasks)
```

## ⚡ 性能优化技巧

### 1. 批量处理
```python
# ✅ 并发执行多个任务
tasks = [execute_agent_task(...) for data in batch_data]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 2. 缓存利用  
```python
# ✅ 重用上下文构建器
builder = get_context_builder()
context = builder.build_context(...)  # 缓存复用
```

### 3. 流式处理
```python
# ✅ 处理大文档时启用流式输出
async for result in tool.execute(input_data, context):
    if result.is_partial:
        print(f"进度: {result.data.get('progress')}%")
    else:
        final_result = result.data
```

## 🚨 错误处理

### 常见错误类型
```python
ValidationError     # 输入验证失败
TimeoutError       # 执行超时  
MemoryError        # 内存不足
PermissionError    # 权限不足
ProcessingError    # 处理失败
```

### 错误处理模式
```python
try:
    result = await execute_agent_task(...)
    if not result['success']:
        handle_task_failure(result['error'])
except ValidationError:
    handle_input_error()
except TimeoutError:
    handle_timeout()  
except Exception as e:
    handle_generic_error(e)
```

## 📋 检查清单

### 输入数据检查
- [ ] task_name 是否描述清晰
- [ ] task_description 是否包含目标和期望
- [ ] placeholders 数据类型是否正确
- [ ] template_content 是否包含有效占位符
- [ ] 必需字段是否都提供

### 输出结果检查  
- [ ] success 状态是否为 True
- [ ] word_document_path 是否存在
- [ ] quality_check.overall_score 是否满足要求
- [ ] template_analysis.filled_placeholders 数量是否正确

### 性能检查
- [ ] 处理时间是否在预期范围内
- [ ] 内存使用是否正常
- [ ] 并发任务数是否合理
- [ ] 错误重试机制是否生效

## 📞 获取帮助

### 调试模式
```python
import logging
logging.getLogger('app.services.infrastructure.agents').setLevel(logging.DEBUG)
```

### 详细文档
- 完整使用指南: `docs/AGENTS_USAGE_REFERENCE.md`
- 系统架构: `agents/README.md`
- 工具开发: `agents/tools/README.md` 

### 常见问题
- Q: 模板填充失败怎么办？
  A: 检查占位符格式和数据类型是否匹配

- Q: Word文档生成失败？  
  A: 确认 generate_word_document=True 且有写入权限

- Q: 质量分数过低？
  A: 检查模板内容完整性和占位符数据质量