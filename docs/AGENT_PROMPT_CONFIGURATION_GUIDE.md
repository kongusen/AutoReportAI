# Agent 提示词配置指南

## 概述

AutoReportAI 的 Agent 系统使用结构化的提示词来进行智能分析和SQL生成。主要的Agent提示词配置在 `MultiDatabaseAgent` 中。

## 当前提示词架构

### 1. 主要Agent类型

- **MultiDatabaseAgent**: 多数据库智能代理，负责占位符分析和SQL生成
- **DataQueryAgent**: 专门的数据查询代理
- **EnhancedDataQueryAgent**: 增强版数据查询代理，支持语义理解

### 2. 提示词配置位置

```
/backend/app/services/agents/multi_database_agent.py
├── _build_ai_analysis_prompt()    # 主要的分析提示词
├── _perform_ai_agent_analysis()   # AI分析执行逻辑
└── 其他辅助方法
```

## 当前提示词结构

### 核心提示词模板 (第434-496行)

```python
def _build_ai_analysis_prompt(self, context: Dict, enhanced_schema: Dict) -> str:
    prompt = f"""
你是专业的数据分析AI，需要分析中文占位符的业务需求并选择最合适的数据表。请进行多轮思考分析。

【数据源概况】
- 数据源: {data_source.get('name', 'unknown')}
- 业务领域: {', '.join(business_categories) if business_categories else '通用业务'}
- 语义分类: {', '.join(semantic_categories[:10]) if semantic_categories else '未分类'}
- 表总数: {enhanced_schema.get('total_tables', 0)}
- 字段总数: {enhanced_schema.get('total_columns', 0)}

【当前分析任务】
占位符: {placeholder_name}
类型: {placeholder_type}

【可用数据表详情】
{tables_text}

【业务语义映射】
{business_mappings_text}

【分析要求】
请按以下步骤进行多轮思考：

1. 【语义理解】- 分析占位符的中文含义，识别关键业务概念
2. 【表选择】- 基于真实表结构和业务分类，选择最合适的数据表
3. 【字段映射】- 根据列的业务名称和语义分类，确定目标字段
4. 【操作确定】- 确定需要的数据操作（统计、去重、聚合等）
5. 【结果验证】- 验证选择的表和字段是否能满足业务需求

请严格按以下JSON格式返回分析结果：
{json_schema}

【关键要求】
1. 仔细理解中文占位符的业务含义
2. 选择最符合业务逻辑的数据表  
3. 只返回JSON，不要任何其他文本
4. confidence值应反映分析的确定程度
5. 特别注意"去重"、"同比"、"占比"等统计需求的准确理解
"""
```

## 如何配置和修改提示词

### 1. 修改主提示词

**文件位置**: `/backend/app/services/agents/multi_database_agent.py`  
**方法**: `_build_ai_analysis_prompt()`  
**行数**: 434-496

**修改步骤**:
```python
def _build_ai_analysis_prompt(self, context: Dict, enhanced_schema: Dict) -> str:
    # 您可以在这里修改提示词模板
    prompt = f"""
    # 在这里编写您的自定义提示词
    # 支持以下变量：
    # - {placeholder_name}: 占位符名称
    # - {placeholder_type}: 占位符类型  
    # - {data_source}: 数据源信息
    # - {tables_text}: 表结构信息
    # - {business_mappings_text}: 业务映射信息
    """
    return prompt
```

### 2. 提示词自定义选项

#### A. 角色定义自定义
```python
# 当前: "你是专业的数据分析AI"
# 可修改为:
role_definition = "你是资深的业务数据分析师，具有10年+的数据建模经验"
```

#### B. 分析步骤自定义
```python
analysis_steps = """
请按以下步骤进行分析：
1. 【需求理解】- 深入理解业务需求
2. 【数据探查】- 分析可用数据表和字段
3. 【方案设计】- 设计最优的查询方案
4. 【结果验证】- 验证分析结果的合理性
"""
```

#### C. 输出格式自定义
```python
json_schema = """
{
    "business_understanding": "对业务需求的理解",
    "selected_solution": {
        "table": "选择的表",
        "fields": ["字段列表"],
        "operation": "操作类型",
        "reasoning": "选择理由"
    },
    "confidence_score": 0.95
}
"""
```

### 3. 创建专门的提示词配置文件

建议创建独立的配置文件来管理提示词：

```python
# /backend/app/config/agent_prompts.py
class AgentPromptTemplates:
    
    MULTI_DB_ANALYSIS = """
    您的自定义分析提示词模板
    """
    
    SQL_GENERATION = """
    您的SQL生成提示词模板
    """
    
    RESULT_EXPLANATION = """
    您的结果解释提示词模板
    """

# 在 multi_database_agent.py 中使用
from app.config.agent_prompts import AgentPromptTemplates

def _build_ai_analysis_prompt(self, context: Dict, enhanced_schema: Dict) -> str:
    return AgentPromptTemplates.MULTI_DB_ANALYSIS.format(
        placeholder_name=context.get("placeholder_name"),
        # ... 其他参数
    )
```

## 高级配置选项

### 1. 动态提示词选择

```python
def _select_prompt_template(self, placeholder_type: str, complexity: str) -> str:
    """根据占位符类型和复杂度选择不同的提示词模板"""
    templates = {
        ("metric", "simple"): self._build_simple_metric_prompt,
        ("metric", "complex"): self._build_complex_metric_prompt,
        ("text", "simple"): self._build_text_analysis_prompt,
        # ... 更多组合
    }
    return templates.get((placeholder_type, complexity), self._build_default_prompt)
```

### 2. 上下文感知提示词

```python
def _build_context_aware_prompt(self, context: Dict) -> str:
    """根据执行上下文调整提示词"""
    base_prompt = self._get_base_prompt()
    
    # 根据用户历史偏好调整
    if context.get("user_preferences"):
        base_prompt += self._add_user_preference_context(context["user_preferences"])
    
    # 根据数据源特性调整
    if context.get("data_source_type") == "doris":
        base_prompt += self._add_doris_specific_hints()
    
    return base_prompt
```

### 3. 多语言提示词支持

```python
class MultiLanguagePrompts:
    CHINESE = "中文提示词模板"
    ENGLISH = "English prompt template"
    
def _build_localized_prompt(self, language: str = "zh-CN") -> str:
    if language == "en-US":
        return MultiLanguagePrompts.ENGLISH
    return MultiLanguagePrompts.CHINESE
```

## 提示词优化建议

### 1. 结构化设计
- 使用明确的分段标记（【】）
- 提供具体的分析步骤
- 要求结构化的JSON输出

### 2. 上下文丰富性
- 包含完整的表结构信息
- 提供业务语义映射
- 给出具体的数据示例

### 3. 错误处理
- 提供多个备选方案
- 包含置信度评估
- 要求详细的推理过程

### 4. 性能优化
- 限制表结构信息长度
- 去重业务映射关系
- 使用缓存减少重复分析

## 测试和验证

### 1. 提示词效果测试

```python
# 创建测试脚本
async def test_prompt_effectiveness():
    test_cases = [
        {"placeholder": "用户总数", "expected_table": "users"},
        {"placeholder": "昨日销售额", "expected_operation": "sum"},
        # ... 更多测试用例
    ]
    
    for case in test_cases:
        result = await agent.analyze_placeholder_requirements(case)
        assert result["target_table"] == case["expected_table"]
```

### 2. 提示词版本管理

```python
class PromptVersionManager:
    VERSION_1_0 = "原始版本提示词"
    VERSION_1_1 = "优化后的提示词"
    
    @classmethod
    def get_prompt(cls, version: str = "latest") -> str:
        if version == "1.0":
            return cls.VERSION_1_0
        return cls.VERSION_1_1
```

## 监控和分析

### 1. 提示词效果监控

- 分析准确率统计
- 置信度分布分析
- 错误类型分类
- 响应时间监控

### 2. 持续优化

- A/B测试不同提示词版本
- 收集用户反馈
- 根据错误案例优化提示词
- 定期评估和更新

这样您就可以完全控制和自定义Agent的提示词行为了！