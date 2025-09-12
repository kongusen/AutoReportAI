"""
模板填充工具
============

用于占位符解析和模板填充的智能工具。
负责控制占位符对模版的填充，补充简短描述，并将结果传递给domain层进行Word文档构建。
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass

from ..core.base import (
    AgentTool, StreamingAgentTool, ToolDefinition, ToolResult, 
    ToolExecutionContext, ToolCategory, ToolPriority, ToolPermission,
    ValidationError, ExecutionError, create_tool_definition
)

logger = logging.getLogger(__name__)


# 输入模式
class TemplateFillInput(BaseModel):
    """模板填充的输入模式"""
    template_content: str = Field(..., min_length=1, description="模板内容")
    placeholders: Dict[str, Any] = Field(..., description="占位符数据字典")
    template_type: str = Field(default="word", description="模板类型：word, html, markdown, text")
    fill_mode: str = Field(default="smart", description="填充模式：smart, exact, descriptive")
    add_descriptions: bool = Field(default=True, description="是否添加简短描述")
    preserve_formatting: bool = Field(default=True, description="是否保持格式")
    
    # 新增domain集成参数
    generate_word_document: bool = Field(default=True, description="是否生成Word文档")
    document_title: str = Field(default="模板填充报告", description="Word文档标题")
    enable_quality_check: bool = Field(default=True, description="是否启用质量检查")
    
    @validator('template_type')
    def validate_template_type(cls, v):
        allowed_types = ["word", "html", "markdown", "text", "json"]
        if v not in allowed_types:
            raise ValueError(f"模板类型必须是以下之一: {allowed_types}")
        return v
    
    @validator('fill_mode')
    def validate_fill_mode(cls, v):
        allowed_modes = ["smart", "exact", "descriptive", "enhanced"]
        if v not in allowed_modes:
            raise ValueError(f"填充模式必须是以下之一: {allowed_modes}")
        return v


@dataclass
class PlaceholderMatch:
    """占位符匹配信息"""
    placeholder_name: str
    original_text: str
    start_pos: int
    end_pos: int
    value: Any = None
    description: str = ""
    is_filled: bool = False


@dataclass
class TemplateAnalysis:
    """模板分析结果"""
    total_placeholders: int
    found_placeholders: List[PlaceholderMatch]
    missing_placeholders: List[str]
    template_structure: Dict[str, Any]
    complexity_score: int


class TemplateFillTool(StreamingAgentTool):
    """
    智能模板填充工具
    
    专注于：
    1. 识别和解析模板中的占位符
    2. 智能填充占位符数据
    3. 添加简短描述和上下文
    4. 保持模板格式和结构
    5. 准备数据传递给domain层Word构建服务
    """
    
    def __init__(self):
        definition = create_tool_definition(
            name="template_fill_tool",
            description="智能模板填充工具，负责占位符解析、数据填充和描述生成",
            category=ToolCategory.DATA,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.READ_ONLY],
            input_schema=TemplateFillInput,
            is_read_only=True,
            supports_streaming=True,
            typical_execution_time_ms=3000,
            examples=[
                {
                    "template_content": "公司 {company_name} 在 {report_period} 期间销售额达到 {revenue} 万元。",
                    "placeholders": {
                        "company_name": "科技公司",
                        "report_period": "2024年第一季度", 
                        "revenue": 1250.8
                    },
                    "add_descriptions": True
                }
            ],
            limitations=[
                "需要提供完整的占位符数据",
                "复杂嵌套模板可能需要特殊处理",
                "大型模板处理时间较长"
            ]
        )
        super().__init__(definition)
        
        # 占位符模式定义
        self.placeholder_patterns = {
            'curly_braces': r'\{([^}]+)\}',      # {placeholder}
            'double_braces': r'\{\{([^}]+)\}\}', # {{placeholder}}
            'angle_brackets': r'<([^>]+)>',      # <placeholder>
            'square_brackets': r'\[([^\]]+)\]',  # [placeholder]
            'percent_style': r'%([^%]+)%',       # %placeholder%
            'dollar_style': r'\$\{([^}]+)\}'     # ${placeholder}
        }
        
        # 描述生成模板
        self.description_templates = {
            'financial': "金额数据，单位：{unit}，来源：{source}",
            'date': "时间数据，格式：{format}，范围：{range}",
            'percentage': "百分比数据，计算方式：{method}，基准：{baseline}",
            'count': "计数数据，统计对象：{object}，时间范围：{period}",
            'text': "文本数据，类型：{type}，长度：{length}字符",
            'default': "数据值：{value}，类型：{type}"
        }
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """验证模板填充输入"""
        try:
            validated = TemplateFillInput(**input_data)
            return validated.dict()
        except Exception as e:
            raise ValidationError(f"模板填充工具输入无效: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """检查模板填充权限"""
        # 模板填充是只读操作，通常安全
        return True
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """执行模板填充并流式传输进度"""
        
        template_content = input_data['template_content']
        placeholders = input_data['placeholders']
        template_type = input_data['template_type']
        fill_mode = input_data['fill_mode']
        add_descriptions = input_data['add_descriptions']
        preserve_formatting = input_data['preserve_formatting']
        
        # 阶段1：分析模板结构
        yield await self.stream_progress({
            'status': 'analyzing_template',
            'message': '正在分析模板结构...',
            'progress': 10
        }, context)
        
        analysis = await self._analyze_template(template_content, placeholders)
        
        # 阶段2：验证占位符
        yield await self.stream_progress({
            'status': 'validating_placeholders',
            'message': f'找到 {analysis.total_placeholders} 个占位符，验证中...',
            'progress': 25
        }, context)
        
        validation_result = await self._validate_placeholders(analysis, placeholders)
        
        # 阶段3：执行智能填充
        yield await self.stream_progress({
            'status': 'filling_template',
            'message': f'使用 {fill_mode} 模式填充模板...',
            'progress': 50
        }, context)
        
        filled_content = await self._fill_template(
            template_content, analysis, placeholders, fill_mode, preserve_formatting
        )
        
        # 阶段4：生成描述
        descriptions = {}
        if add_descriptions:
            yield await self.stream_progress({
                'status': 'generating_descriptions',
                'message': '生成占位符描述...',
                'progress': 75
            }, context)
            
            descriptions = await self._generate_descriptions(analysis, placeholders)
        
        # 阶段5：准备domain层数据
        yield await self.stream_progress({
            'status': 'preparing_output',
            'message': '准备传递给报告生成服务的数据...',
            'progress': 90
        }, context)
        
        domain_data = await self._prepare_domain_data(
            filled_content, analysis, placeholders, descriptions, template_type
        )
        
        # 阶段6：集成domain服务生成Word文档
        generate_word = input_data.get('generate_word_document', True)
        word_document_result = None
        
        if generate_word:
            yield await self.stream_progress({
                'status': 'integrating_domain_services',
                'message': '正在调用domain层服务生成Word文档...',
                'progress': 95
            }, context)
            
            try:
                # 导入集成服务
                from .template_domain_integration import process_template_to_word
                
                # 准备模板填充结果
                template_fill_result = {
                    'success': True,
                    'filled_content': filled_content,
                    'domain_data': domain_data,
                    'template_analysis': {
                        'total_placeholders': analysis.total_placeholders,
                        'filled_placeholders': len([p for p in analysis.found_placeholders if p.is_filled]),
                        'missing_placeholders': analysis.missing_placeholders,
                        'complexity_score': analysis.complexity_score
                    },
                    'metadata': {
                        'template_type': template_type,
                        'fill_mode': fill_mode,
                        'processing_time': datetime.now(timezone.utc).isoformat(),
                        'tool_version': "1.0.0"
                    }
                }
                
                # 调用domain集成服务
                word_document_result = await process_template_to_word(
                    template_fill_result=template_fill_result,
                    title=input_data.get('document_title', '模板填充报告'),
                    enable_quality_check=input_data.get('enable_quality_check', True)
                )
                
            except Exception as e:
                logger.warning(f"Word文档生成失败，但模板填充成功: {e}")
                word_document_result = {
                    'success': False,
                    'error': str(e),
                    'error_type': 'word_generation_failed'
                }
        
        # 最终结果
        result_data = {
            'success': True,
            'filled_content': filled_content,
            'original_content': template_content,
            'template_analysis': {
                'total_placeholders': analysis.total_placeholders,
                'filled_placeholders': len([p for p in analysis.found_placeholders if p.is_filled]),
                'missing_placeholders': analysis.missing_placeholders,
                'complexity_score': analysis.complexity_score
            },
            'placeholder_data': placeholders,
            'descriptions': descriptions,
            'domain_data': domain_data,
            'word_document': word_document_result,
            'metadata': {
                'template_type': template_type,
                'fill_mode': fill_mode,
                'processing_time': datetime.now(timezone.utc).isoformat(),
                'tool_version': "1.0.0",
                'word_generation_attempted': generate_word
            }
        }
        
        yield await self.stream_final_result(result_data, context)
    
    async def _analyze_template(self, template_content: str, available_placeholders: Dict[str, Any]) -> TemplateAnalysis:
        """分析模板结构和占位符"""
        
        found_placeholders = []
        all_matches = []
        
        # 使用多种模式识别占位符
        for pattern_name, pattern in self.placeholder_patterns.items():
            matches = re.finditer(pattern, template_content)
            
            for match in matches:
                placeholder_name = match.group(1).strip()
                placeholder_match = PlaceholderMatch(
                    placeholder_name=placeholder_name,
                    original_text=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    value=available_placeholders.get(placeholder_name),
                    is_filled=placeholder_name in available_placeholders
                )
                all_matches.append(placeholder_match)
        
        # 按位置排序并去重
        all_matches.sort(key=lambda x: x.start_pos)
        unique_placeholders = {}
        for match in all_matches:
            if match.placeholder_name not in unique_placeholders:
                unique_placeholders[match.placeholder_name] = match
            else:
                # 保留最早出现的位置
                if match.start_pos < unique_placeholders[match.placeholder_name].start_pos:
                    unique_placeholders[match.placeholder_name] = match
        
        found_placeholders = list(unique_placeholders.values())
        
        # 查找缺失的占位符
        found_names = {p.placeholder_name for p in found_placeholders}
        available_names = set(available_placeholders.keys())
        missing_placeholders = list(available_names - found_names)
        
        # 分析模板结构
        template_structure = {
            'length': len(template_content),
            'line_count': template_content.count('\n') + 1,
            'paragraph_count': len([p for p in template_content.split('\n\n') if p.strip()]),
            'contains_tables': '<table>' in template_content.lower() or '|' in template_content,
            'contains_images': '<img' in template_content.lower() or '![' in template_content,
            'contains_links': 'http' in template_content or '[' in template_content
        }
        
        # 计算复杂度分数
        complexity_score = self._calculate_complexity_score(len(found_placeholders), template_structure)
        
        return TemplateAnalysis(
            total_placeholders=len(found_placeholders),
            found_placeholders=found_placeholders,
            missing_placeholders=missing_placeholders,
            template_structure=template_structure,
            complexity_score=complexity_score
        )
    
    def _calculate_complexity_score(self, placeholder_count: int, structure: Dict[str, Any]) -> int:
        """计算模板复杂度分数"""
        score = 0
        
        # 基于占位符数量
        score += min(placeholder_count, 20)  # 最多20分
        
        # 基于结构复杂度
        if structure['contains_tables']:
            score += 5
        if structure['contains_images']:
            score += 3
        if structure['contains_links']:
            score += 2
        if structure['paragraph_count'] > 5:
            score += 5
        
        return min(score, 50)  # 最高50分
    
    async def _validate_placeholders(self, analysis: TemplateAnalysis, placeholders: Dict[str, Any]) -> Dict[str, Any]:
        """验证占位符数据"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {
                'total_found': len(analysis.found_placeholders),
                'total_available': len(placeholders),
                'missing_count': len(analysis.missing_placeholders),
                'match_rate': len(analysis.found_placeholders) / max(len(placeholders), 1) * 100
            }
        }
        
        # 检查缺失的占位符
        if analysis.missing_placeholders:
            validation_result['warnings'].append(
                f"以下占位符在模板中未找到: {', '.join(analysis.missing_placeholders)}"
            )
        
        # 检查模板中未提供数据的占位符
        unfilled = [p.placeholder_name for p in analysis.found_placeholders if not p.is_filled]
        if unfilled:
            validation_result['errors'].append(
                f"以下占位符缺少数据: {', '.join(unfilled)}"
            )
            validation_result['valid'] = False
        
        return validation_result
    
    async def _fill_template(
        self, 
        template_content: str, 
        analysis: TemplateAnalysis, 
        placeholders: Dict[str, Any],
        fill_mode: str,
        preserve_formatting: bool
    ) -> str:
        """智能填充模板"""
        
        filled_content = template_content
        
        # 按位置倒序替换（避免位置偏移）
        sorted_placeholders = sorted(analysis.found_placeholders, key=lambda x: x.start_pos, reverse=True)
        
        for placeholder in sorted_placeholders:
            if placeholder.is_filled:
                replacement_value = await self._format_placeholder_value(
                    placeholder.value, fill_mode, placeholder.placeholder_name
                )
                
                # 执行替换
                filled_content = (
                    filled_content[:placeholder.start_pos] + 
                    replacement_value + 
                    filled_content[placeholder.end_pos:]
                )
                
                # 标记为已填充
                placeholder.is_filled = True
        
        return filled_content
    
    async def _format_placeholder_value(self, value: Any, fill_mode: str, placeholder_name: str) -> str:
        """格式化占位符值"""
        
        if value is None:
            return "[未提供数据]"
        
        if fill_mode == "exact":
            return str(value)
        
        elif fill_mode == "smart":
            return await self._smart_format_value(value, placeholder_name)
        
        elif fill_mode == "descriptive":
            return await self._descriptive_format_value(value, placeholder_name)
        
        elif fill_mode == "enhanced":
            smart_value = await self._smart_format_value(value, placeholder_name)
            description = await self._generate_value_description(value, placeholder_name)
            return f"{smart_value} ({description})"
        
        return str(value)
    
    async def _smart_format_value(self, value: Any, placeholder_name: str) -> str:
        """智能格式化值"""
        
        name_lower = placeholder_name.lower()
        
        # 数字格式化
        if isinstance(value, (int, float)):
            if 'percentage' in name_lower or 'percent' in name_lower or 'rate' in name_lower:
                return f"{value:.1f}%"
            elif 'money' in name_lower or 'revenue' in name_lower or 'cost' in name_lower or '金额' in name_lower:
                return f"{value:,.2f}"
            elif isinstance(value, int) and ('count' in name_lower or '数量' in name_lower):
                return f"{value:,}"
            else:
                return f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
        
        # 日期格式化
        if isinstance(value, datetime):
            if 'date' in name_lower:
                return value.strftime('%Y-%m-%d')
            elif 'time' in name_lower:
                return value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return value.strftime('%Y年%m月%d日')
        
        # 字符串处理
        if isinstance(value, str):
            if len(value) > 100:
                return value[:97] + "..."
            return value
        
        # 列表处理
        if isinstance(value, list):
            if len(value) <= 3:
                return "、".join(str(item) for item in value)
            else:
                return "、".join(str(item) for item in value[:3]) + f"等{len(value)}项"
        
        return str(value)
    
    async def _descriptive_format_value(self, value: Any, placeholder_name: str) -> str:
        """描述性格式化值"""
        
        smart_value = await self._smart_format_value(value, placeholder_name)
        value_type = type(value).__name__
        
        if isinstance(value, (int, float)):
            if value > 0:
                return f"{smart_value}（正值）"
            elif value < 0:
                return f"{smart_value}（负值）"
            else:
                return f"{smart_value}（零值）"
        
        elif isinstance(value, str):
            return f"{smart_value}（文本，长度{len(value)}字符）"
        
        elif isinstance(value, list):
            return f"{smart_value}（列表，{len(value)}个项目）"
        
        elif isinstance(value, dict):
            return f"字典数据（{len(value)}个键值对）"
        
        return f"{smart_value}（{value_type}类型）"
    
    async def _generate_descriptions(self, analysis: TemplateAnalysis, placeholders: Dict[str, Any]) -> Dict[str, str]:
        """生成占位符描述"""
        
        descriptions = {}
        
        for placeholder in analysis.found_placeholders:
            if placeholder.is_filled:
                description = await self._generate_value_description(
                    placeholder.value, placeholder.placeholder_name
                )
                descriptions[placeholder.placeholder_name] = description
        
        return descriptions
    
    async def _generate_value_description(self, value: Any, placeholder_name: str) -> str:
        """生成单个值的描述"""
        
        name_lower = placeholder_name.lower()
        
        # 根据占位符名称和值类型生成描述
        if isinstance(value, (int, float)):
            if 'revenue' in name_lower or '收入' in name_lower:
                return f"收入数据，数值为{value:,.2f}"
            elif 'count' in name_lower or '数量' in name_lower:
                return f"计数数据，共{value:,}个"
            elif 'percentage' in name_lower or '百分比' in name_lower:
                return f"百分比数据，比例为{value}%"
            else:
                return f"数值数据，值为{value}"
        
        elif isinstance(value, str):
            return f"文本数据，内容长度{len(value)}字符"
        
        elif isinstance(value, datetime):
            return f"时间数据，日期为{value.strftime('%Y年%m月%d日')}"
        
        elif isinstance(value, list):
            return f"列表数据，包含{len(value)}个项目"
        
        elif isinstance(value, dict):
            return f"结构化数据，包含{len(value)}个字段"
        
        else:
            return f"{type(value).__name__}类型数据"
    
    async def _prepare_domain_data(
        self, 
        filled_content: str, 
        analysis: TemplateAnalysis,
        placeholders: Dict[str, Any],
        descriptions: Dict[str, str],
        template_type: str
    ) -> Dict[str, Any]:
        """准备传递给domain层reporting服务的数据"""
        
        domain_data = {
            # 核心内容
            'template_content': filled_content,
            'template_type': template_type,
            
            # 占位符信息
            'placeholder_data': placeholders,
            'placeholder_descriptions': descriptions,
            'placeholder_metadata': {
                placeholder.placeholder_name: {
                    'original_text': placeholder.original_text,
                    'value': placeholder.value,
                    'description': descriptions.get(placeholder.placeholder_name, ''),
                    'data_type': type(placeholder.value).__name__ if placeholder.value is not None else 'None',
                    'is_filled': placeholder.is_filled
                }
                for placeholder in analysis.found_placeholders
            },
            
            # 模板分析结果
            'template_analysis': {
                'total_placeholders': analysis.total_placeholders,
                'filled_count': len([p for p in analysis.found_placeholders if p.is_filled]),
                'missing_placeholders': analysis.missing_placeholders,
                'complexity_score': analysis.complexity_score,
                'structure': analysis.template_structure
            },
            
            # Word文档构建参数
            'word_generation_params': {
                'preserve_formatting': True,
                'include_metadata': True,
                'add_table_of_contents': analysis.template_structure.get('paragraph_count', 0) > 5,
                'add_page_numbers': True,
                'document_style': 'professional'
            },
            
            # 质量检查参数
            'quality_check_params': {
                'check_placeholder_completeness': True,
                'check_data_consistency': True,
                'check_language_quality': True,
                'generate_summary': True
            },
            
            # 处理时间戳
            'processing_timestamp': datetime.now(timezone.utc).isoformat(),
            'agent_tool_version': "1.0.0"
        }
        
        return domain_data


# 辅助工具类：模板分析器
class TemplateAnalyzer(AgentTool):
    """模板分析专用工具"""
    
    def __init__(self):
        definition = create_tool_definition(
            name="template_analyzer",
            description="分析模板结构和占位符",
            category=ToolCategory.ANALYSIS,
            priority=ToolPriority.MEDIUM,
            permissions=[ToolPermission.READ_ONLY],
            is_read_only=True
        )
        super().__init__(definition)
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> ToolResult:
        """分析模板"""
        template_content = input_data.get('template_content', '')
        
        # 执行基础分析
        fill_tool = TemplateFillTool()
        analysis = await fill_tool._analyze_template(template_content, {})
        
        return ToolResult(
            success=True,
            data={
                'analysis': analysis.__dict__,
                'recommendations': await self._generate_recommendations(analysis)
            },
            metadata={'tool': 'template_analyzer'}
        )
    
    async def _generate_recommendations(self, analysis: TemplateAnalysis) -> List[str]:
        """生成模板优化建议"""
        recommendations = []
        
        if analysis.total_placeholders > 20:
            recommendations.append("模板包含较多占位符，建议考虑分拆为多个子模板")
        
        if analysis.complexity_score > 30:
            recommendations.append("模板结构较复杂，建议增加处理时间预期")
        
        if not analysis.template_structure.get('contains_tables') and analysis.total_placeholders > 10:
            recommendations.append("考虑使用表格格式来组织大量数据占位符")
        
        return recommendations


__all__ = ["TemplateFillTool", "TemplateAnalyzer", "TemplateFillInput", "TemplateAnalysis"]