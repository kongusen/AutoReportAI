from __future__ import annotations
from typing import Dict, Any, List, Optional
import json
import re
from datetime import datetime

JSON_ONLY_SUFFIX = """

请严格只输出JSON，不要包含任何解释性文本、前后缀、markdown代码块，也不要输出额外说明。
如果无法给出完整结果，请输出具有错误字段的JSON并包含错误原因。
"""

def append_json_only_instruction(prompt: str) -> str:
    return f"{prompt}\n{JSON_ONLY_SUFFIX}".strip()


# 占位符分析专业提示模板
PLACEHOLDER_ANALYSIS_TEMPLATES = {
    
    # 系统角色定义
    "placeholder_analyst_system": """你是一个专业的报告占位符分析专家，擅长理解业务需求并将其转化为精确的数据查询。

核心能力：
1. 深入理解占位符的业务含义和数据需求
2. 基于数据库schema智能推荐最佳数据源
3. 生成高效、准确的SQL查询逻辑
4. 提供数据处理和展示建议
5. 识别潜在的数据质量和性能问题

分析原则：
- 准确性优先：确保分析结果符合业务逻辑
- 性能考虑：优化查询效率，避免全表扫描
- 数据完整性：考虑空值、异常值处理
- 安全性：防止SQL注入，使用参数化查询
- 可维护性：生成清晰、可读的查询逻辑

输出格式：严格遵循JSON格式，包含完整的分析结果和建议。""",

    # 占位符深度分析模板
    "deep_placeholder_analysis": """请深度分析以下占位符，提供全面的数据需求分析：

**占位符信息：**
- 占位符文本：{{ placeholder_text }}
- 占位符类型：{{ placeholder_type | default('unknown') }}
- 内容类型：{{ content_type | default('text') }}

**模板上下文：**
{{ template_context | default('无额外上下文') }}

**可用数据源信息：**
{% if data_sources %}
{% for ds in data_sources %}
- 数据源：{{ ds.name }} ({{ ds.source_type }})
  数据库：{{ ds.database }}
  表结构：{{ ds.schema_summary | truncate(200) }}
{% endfor %}
{% else %}
无可用数据源信息
{% endif %}

**数据库Schema详情：**
{% if schema_info %}
{{ schema_info | format_json }}
{% else %}
Schema信息不可用
{% endif %}

**分析要求：**
1. **语义分析**：解析占位符的确切业务含义
2. **数据映射**：识别需要的数据表和字段
3. **SQL逻辑**：设计完整的查询逻辑（包括JOIN、聚合、过滤等）
4. **性能优化**：提供查询优化建议
5. **数据处理**：建议数据清洗和格式化方案
6. **置信度评估**：评估分析结果的可信度

请输出JSON格式结果，包含以下字段：
```json
{
  "semantic_analysis": {
    "business_meaning": "占位符的业务含义",
    "data_intent": "数据意图描述",
    "complexity_level": "simple|medium|complex",
    "keywords": ["关键词列表"]
  },
  "data_mapping": {
    "recommended_sources": [
      {
        "source_name": "数据源名称",
        "database": "数据库名",
        "tables": ["相关表列表"],
        "confidence": 0.95
      }
    ],
    "required_fields": [
      {
        "table": "表名",
        "field": "字段名", 
        "purpose": "用途描述",
        "data_type": "数据类型"
      }
    ],
    "relationships": ["表关系描述"]
  },
  "sql_logic": {
    "query_template": "SQL查询模板（使用参数占位符）",
    "parameters": {
      "param_name": "参数说明"
    },
    "explanation": "查询逻辑解释",
    "complexity_score": 0.7
  },
  "performance_considerations": {
    "estimated_cost": "high|medium|low",
    "optimization_suggestions": ["优化建议列表"],
    "index_recommendations": ["索引建议"],
    "potential_issues": ["潜在问题列表"]
  },
  "data_processing": {
    "aggregation_type": "聚合类型",
    "formatting": "格式化要求",
    "validation": "数据验证规则",
    "transformation": "数据转换逻辑"
  },
  "confidence_metrics": {
    "overall_confidence": 0.85,
    "semantic_confidence": 0.9,
    "mapping_confidence": 0.8,
    "sql_confidence": 0.85,
    "reliability_factors": ["影响可信度的因素"]
  }
}
```""",

    # 占位符批量分析模板
    "batch_placeholder_analysis": """请同时分析多个相关占位符，识别它们之间的关联关系：

**占位符批次信息：**
{% for placeholder in placeholders %}
- {{ loop.index }}. {{ placeholder.text }} ({{ placeholder.type | default('unknown') }})
{% endfor %}

**模板整体上下文：**
{{ template_context }}

**数据源概览：**
{{ data_source_summary }}

**分析要求：**
1. 分析每个占位符的独立需求
2. 识别占位符之间的数据关联
3. 设计统一的查询策略
4. 优化整体查询性能

输出包含每个占位符的详细分析以及整体优化建议的JSON。""",

    # SQL查询优化模板
    "sql_optimization": """请优化以下SQL查询，提高性能和可维护性：

**原始查询：**
```sql
{{ original_sql }}
```

**数据源信息：**
- 数据库类型：{{ db_type }}
- 预估数据量：{{ estimated_rows }}
- 现有索引：{{ existing_indexes }}

**优化目标：**
{{ optimization_goals | format_list }}

请提供优化后的SQL和详细的性能改进说明。""",

    # 数据质量检查模板
    "data_quality_check": """基于占位符分析结果，设计数据质量检查方案：

**占位符：** {{ placeholder_text }}
**预期查询：** {{ sql_query }}
**数据源：** {{ data_source_info }}

请提供：
1. 数据完整性检查
2. 数据一致性验证
3. 异常值检测
4. 数据新鲜度评估

输出JSON格式的检查方案。"""
}

# 上下文提取器
def extract_schema_highlights(schema_info: Dict[str, Any]) -> List[str]:
    """从schema信息中提取关键亮点"""
    highlights = []
    
    if 'tables' in schema_info:
        for table in schema_info['tables'][:5]:  # 限制前5个表
            table_name = table.get('name', 'unknown')
            row_count = table.get('row_count', 0)
            key_columns = table.get('key_columns', [])
            
            highlight = f"表 {table_name}: {row_count:,} 行"
            if key_columns:
                highlight += f", 关键字段: {', '.join(key_columns[:3])}"
            highlights.append(highlight)
    
    return highlights

def extract_placeholder_patterns(placeholder_text: str) -> Dict[str, Any]:
    """分析占位符的模式特征"""
    patterns = {
        'has_aggregation': bool(re.search(r'(总数|总计|平均|最大|最小|count|sum|avg|max|min)', placeholder_text, re.IGNORECASE)),
        'has_time_reference': bool(re.search(r'(今日|昨日|本月|上月|年|月|日|时间|时|分|秒)', placeholder_text)),
        'has_comparison': bool(re.search(r'(比较|对比|增长|下降|变化|vs|比)', placeholder_text)),
        'has_percentage': bool(re.search(r'(百分比|占比|比例|%|percent)', placeholder_text)),
        'has_ranking': bool(re.search(r'(排名|排行|前\d+|top|rank)', placeholder_text)),
        'complexity_indicators': []
    }
    
    # 识别复杂度指示器
    if patterns['has_aggregation']:
        patterns['complexity_indicators'].append('aggregation')
    if patterns['has_time_reference']:
        patterns['complexity_indicators'].append('time_series')
    if patterns['has_comparison']:
        patterns['complexity_indicators'].append('comparison')
    
    return patterns

def build_enhanced_context(placeholder_text: str, template_context: str = None, 
                          data_sources: List[Dict] = None, schema_info: Dict = None) -> Dict[str, Any]:
    """构建增强的分析上下文"""
    context = {
        'placeholder_text': placeholder_text,
        'template_context': template_context or '',
        'analysis_timestamp': str(datetime.now()),
        'placeholder_patterns': extract_placeholder_patterns(placeholder_text)
    }
    
    if data_sources:
        context['data_sources'] = data_sources
        context['available_databases'] = list(set(ds.get('database', '') for ds in data_sources))
    
    if schema_info:
        context['schema_info'] = schema_info
        context['schema_highlights'] = extract_schema_highlights(schema_info)
    
    return context


