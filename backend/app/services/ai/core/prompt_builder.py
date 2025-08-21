"""
智能提示词构建器

用于生成高质量、结构化的AI提示词，支持：
1. 占位符分析提示词生成
2. 动态上下文注入  
3. 提示词模板管理
4. 性能优化和缓存
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """提示词类型"""
    PLACEHOLDER_ANALYSIS = "placeholder_analysis"
    SCHEMA_ANALYSIS = "schema_analysis"
    SQL_GENERATION = "sql_generation"
    DATA_VALIDATION = "data_validation"


@dataclass
class PromptContext:
    """提示词上下文"""
    placeholder_text: str
    template_content: Optional[str] = None
    available_schemas: List[Dict[str, Any]] = field(default_factory=list)
    business_domain: Optional[str] = None
    complexity_hint: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)


class BasePromptBuilder(ABC):
    """提示词构建器基类"""
    
    @abstractmethod
    def build_prompt(self, context: PromptContext) -> str:
        """构建提示词"""
        pass
    
    @abstractmethod
    def get_expected_response_format(self) -> Dict[str, Any]:
        """获取期望的响应格式"""
        pass


class PlaceholderAnalysisPromptBuilder(BasePromptBuilder):
    """占位符分析提示词构建器"""
    
    # 基础提示词模板
    BASE_TEMPLATE = """
你是一个专业的数据分析师，擅长理解业务需求并将其转换为精确的SQL查询。

请分析以下占位符的含义，并提供结构化的分析结果。

# 分析目标
占位符文本: "{placeholder_text}"

{template_context}

{schema_context}

{business_context}

# 分析要求

请提供详细的分析，包括：

1. **语义分析** - 理解占位符的业务含义
2. **数据映射** - 确定所需的数据源和字段  
3. **SQL逻辑** - 生成查询模板和执行逻辑
4. **置信度评估** - 评估分析结果的可靠性

# 响应格式

请严格按照以下JSON格式返回分析结果：

```json
{{
  "semantic_analysis": {{
    "business_meaning": "占位符的业务含义描述",
    "data_intent": "数据查询的具体意图",
    "complexity_level": "simple|medium|complex",
    "keywords": ["关键词1", "关键词2"]
  }},
  "data_mapping": {{
    "recommended_sources": [
      {{
        "table_name": "表名",
        "relevance_score": 0.95,
        "reason": "选择理由"
      }}
    ],
    "required_fields": [
      {{
        "field_name": "字段名",
        "field_type": "数据类型", 
        "importance": "high|medium|low"
      }}
    ],
    "relationships": [
      {{
        "type": "join|filter|aggregation",
        "description": "关系描述"
      }}
    ]
  }},
  "sql_logic": {{
    "query_template": "SELECT ... FROM ... WHERE ...",
    "explanation": "查询逻辑说明",
    "parameters": {{
      "param1": "参数说明"
    }},
    "complexity_score": 0.7
  }},
  "performance_considerations": {{
    "estimated_cost": "low|medium|high",
    "optimization_suggestions": ["建议1", "建议2"]
  }},
  "data_processing": {{
    "aggregation_type": "sum|count|avg|max|min|none",
    "formatting": "数据格式化要求"
  }},
  "confidence_metrics": {{
    "overall_confidence": 0.85,
    "semantic_confidence": 0.9,
    "mapping_confidence": 0.8,
    "sql_confidence": 0.85
  }}
}}
```

请确保：
- 所有置信度分数在0-1之间
- SQL模板语法正确且可执行
- 分析结果具体而有价值
- JSON格式完全正确，无语法错误
"""
    
    def build_prompt(self, context: PromptContext) -> str:
        """构建占位符分析提示词"""
        # 构建模板上下文
        template_context = self._build_template_context(context.template_content)
        
        # 构建数据库架构上下文
        schema_context = self._build_schema_context(context.available_schemas)
        
        # 构建业务上下文
        business_context = self._build_business_context(
            context.business_domain, 
            context.complexity_hint,
            context.additional_context
        )
        
        # 组装最终提示词
        prompt = self.BASE_TEMPLATE.format(
            placeholder_text=context.placeholder_text,
            template_context=template_context,
            schema_context=schema_context,
            business_context=business_context
        )
        
        return prompt.strip()
    
    def _build_template_context(self, template_content: Optional[str]) -> str:
        """构建模板上下文信息"""
        if not template_content:
            return ""
        
        return f"""
# 模板上下文
该占位符出现在以下模板中：

```
{template_content[:500]}{"..." if len(template_content) > 500 else ""}
```

请结合模板上下文理解占位符的具体用途。
"""
    
    def _build_schema_context(self, schemas: List[Dict[str, Any]]) -> str:
        """构建数据库架构上下文"""
        if not schemas:
            return """
# 数据源信息
当前没有可用的数据库架构信息。请在分析中提供通用的数据映射建议。
"""
        
        schema_info = []
        for schema in schemas[:3]:  # 限制最多3个schema避免提示词过长
            schema_text = f"""
## {schema.get('table_name', '未知表')}
- 数据库: {schema.get('database_name', '未知')}
- 字段数量: {len(schema.get('columns', []))}
- 主要字段: {', '.join([col.get('name', '') for col in schema.get('columns', [])[:5]])}
"""
            schema_info.append(schema_text)
        
        return f"""
# 可用数据源
以下是可用的数据表信息：

{''.join(schema_info)}

请基于这些数据源进行占位符映射分析。
"""
    
    def _build_business_context(self, domain: Optional[str], 
                               complexity_hint: Optional[str],
                               additional_context: Dict[str, Any]) -> str:
        """构建业务上下文"""
        context_parts = []
        
        if domain:
            context_parts.append(f"业务领域: {domain}")
        
        if complexity_hint:
            context_parts.append(f"复杂度提示: {complexity_hint}")
        
        # 处理额外上下文
        if additional_context:
            for key, value in additional_context.items():
                if isinstance(value, (str, int, float)):
                    context_parts.append(f"{key}: {value}")
        
        if not context_parts:
            return ""
        
        return f"""
# 业务上下文
{chr(10).join(f"- {part}" for part in context_parts)}
"""
    
    def get_expected_response_format(self) -> Dict[str, Any]:
        """获取期望的响应格式定义"""
        return {
            "semantic_analysis": {
                "business_meaning": "string",
                "data_intent": "string", 
                "complexity_level": "enum:simple,medium,complex",
                "keywords": "array<string>"
            },
            "data_mapping": {
                "recommended_sources": "array<object>",
                "required_fields": "array<object>",
                "relationships": "array<object>"
            },
            "sql_logic": {
                "query_template": "string",
                "explanation": "string",
                "parameters": "object",
                "complexity_score": "number:0-1"
            },
            "performance_considerations": {
                "estimated_cost": "enum:low,medium,high",
                "optimization_suggestions": "array<string>"
            },
            "data_processing": {
                "aggregation_type": "enum:sum,count,avg,max,min,none",
                "formatting": "string"
            },
            "confidence_metrics": {
                "overall_confidence": "number:0-1",
                "semantic_confidence": "number:0-1",
                "mapping_confidence": "number:0-1", 
                "sql_confidence": "number:0-1"
            }
        }


class SchemaAnalysisPromptBuilder(BasePromptBuilder):
    """数据库架构分析提示词构建器"""
    
    BASE_TEMPLATE = """
你是一个数据库专家，请分析以下数据库架构信息。

# 架构信息
{schema_data}

# 分析目标  
{analysis_target}

请提供结构化的架构分析结果，包括：
1. 表结构分析
2. 字段类型和约束
3. 关系和索引建议
4. 查询优化建议

返回JSON格式的分析结果。
"""
    
    def build_prompt(self, context: PromptContext) -> str:
        schema_data = json.dumps(context.additional_context.get('schema_data', {}), 
                                ensure_ascii=False, indent=2)
        analysis_target = context.additional_context.get('analysis_target', '通用架构分析')
        
        return self.BASE_TEMPLATE.format(
            schema_data=schema_data,
            analysis_target=analysis_target
        )
    
    def get_expected_response_format(self) -> Dict[str, Any]:
        return {
            "table_analysis": "object",
            "field_analysis": "array<object>", 
            "relationships": "array<object>",
            "optimization_suggestions": "array<string>"
        }


class PromptBuilderFactory:
    """提示词构建器工厂"""
    
    _builders = {
        PromptType.PLACEHOLDER_ANALYSIS: PlaceholderAnalysisPromptBuilder,
        PromptType.SCHEMA_ANALYSIS: SchemaAnalysisPromptBuilder,
    }
    
    @classmethod
    def get_builder(cls, prompt_type: PromptType) -> BasePromptBuilder:
        """获取指定类型的提示词构建器"""
        if prompt_type not in cls._builders:
            raise ValueError(f"不支持的提示词类型: {prompt_type}")
        
        return cls._builders[prompt_type]()
    
    @classmethod
    def register_builder(cls, prompt_type: PromptType, builder_class: type):
        """注册新的提示词构建器"""
        cls._builders[prompt_type] = builder_class


def build_placeholder_analysis_prompt(placeholder_text: str,
                                     template_content: Optional[str] = None,
                                     available_schemas: List[Dict[str, Any]] = None,
                                     business_domain: Optional[str] = None,
                                     complexity_hint: Optional[str] = None,
                                     **additional_context) -> str:
    """
    便捷函数：构建占位符分析提示词
    
    Args:
        placeholder_text: 占位符文本
        template_content: 模板内容
        available_schemas: 可用的数据库架构
        business_domain: 业务领域
        complexity_hint: 复杂度提示
        **additional_context: 额外上下文信息
    
    Returns:
        构建好的提示词
    """
    context = PromptContext(
        placeholder_text=placeholder_text,
        template_content=template_content,
        available_schemas=available_schemas or [],
        business_domain=business_domain,
        complexity_hint=complexity_hint,
        additional_context=additional_context
    )
    
    builder = PromptBuilderFactory.get_builder(PromptType.PLACEHOLDER_ANALYSIS)
    return builder.build_prompt(context)