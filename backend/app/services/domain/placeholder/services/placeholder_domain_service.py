"""
Placeholder Domain Service

占位符领域服务，包含纯业务逻辑
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime

from ..entities.placeholder_entity import (
    PlaceholderEntity, PlaceholderType, AnalysisResult, DataType,
    PlaceholderRule, PlaceholderContext, AnalysisStatus
)

logger = logging.getLogger(__name__)


class PlaceholderParser:
    """占位符解析器"""
    
    # 占位符模式
    PATTERNS = {
        PlaceholderType.SIMPLE: r'\{\{\s*([^#/{}]+?)\s*\}\}',
        PlaceholderType.CONDITIONAL: r'\{\{#if\s+(.+?)\}\}(.*?)\{\{/if\}\}',
        PlaceholderType.LOOP: r'\{\{#each\s+(.+?)\}\}(.*?)\{\{/each\}\}',
        PlaceholderType.EXPRESSION: r'\{\{=\s*(.+?)\s*\}\}',
        PlaceholderType.FUNCTION: r'\{\{\s*(\w+)\s*\(([^)]*)\)\s*\}\}'
    }
    
    @classmethod
    def extract_placeholders(cls, template_content: str) -> List[Dict[str, Any]]:
        """从模板内容中提取所有占位符"""
        placeholders = []
        
        for placeholder_type, pattern in cls.PATTERNS.items():
            matches = re.finditer(pattern, template_content, re.DOTALL)
            
            for match in matches:
                placeholder_data = {
                    'text': match.group(0),
                    'name': cls._extract_name(match, placeholder_type),
                    'type': placeholder_type,
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'groups': match.groups()
                }
                
                placeholders.append(placeholder_data)
        
        # 按位置排序
        placeholders.sort(key=lambda x: x['start_pos'])
        
        return placeholders
    
    @classmethod
    def _extract_name(cls, match, placeholder_type: PlaceholderType) -> str:
        """提取占位符名称"""
        if placeholder_type == PlaceholderType.SIMPLE:
            name = match.group(1).strip()
            # 移除可能的修饰符
            name = re.sub(r'[|:].+$', '', name).strip()
            return name
        elif placeholder_type == PlaceholderType.CONDITIONAL:
            return f"if_{match.group(1).strip()}"
        elif placeholder_type == PlaceholderType.LOOP:
            return f"each_{match.group(1).strip()}"
        elif placeholder_type == PlaceholderType.EXPRESSION:
            expr = match.group(1).strip()
            return f"expr_{hash(expr) % 1000:03d}"
        elif placeholder_type == PlaceholderType.FUNCTION:
            return match.group(1).strip()
        else:
            return "unknown"
    
    @classmethod
    def get_surrounding_context(cls, template_content: str, start_pos: int, 
                               end_pos: int, context_size: int = 50) -> str:
        """获取占位符周围的上下文"""
        context_start = max(0, start_pos - context_size)
        context_end = min(len(template_content), end_pos + context_size)
        
        context = template_content[context_start:context_end]
        
        # 标记占位符位置
        placeholder_start = start_pos - context_start
        placeholder_end = end_pos - context_start
        
        marked_context = (
            context[:placeholder_start] + 
            "<<<" + 
            context[placeholder_start:placeholder_end] + 
            ">>>" + 
            context[placeholder_end:]
        )
        
        return marked_context


class PlaceholderSemanticAnalyzer:
    """占位符语义分析器"""
    
    # 语义模式
    SEMANTIC_PATTERNS = {
        'numeric': [
            r'(count|total|sum|amount|quantity|number|num)',
            r'(price|cost|value|revenue|profit)',
            r'(age|year|month|day|hour)',
            r'(rate|percentage|percent|ratio)'
        ],
        'textual': [
            r'(name|title|description|comment|note)',
            r'(address|location|place)',
            r'(message|content|body|text)'
        ],
        'temporal': [
            r'(date|time|timestamp|created|updated|modified)',
            r'(start|end|begin|finish)',
            r'(expired|valid|due)'
        ],
        'identifier': [
            r'(id|key|code|reference|ref)',
            r'(uuid|guid|token)',
            r'(serial|sequence|number)'
        ],
        'boolean': [
            r'(is|has|can|should|will)',
            r'(active|enabled|disabled|valid)',
            r'(flag|status|state)'
        ]
    }
    
    # 数据类型推断
    TYPE_INFERENCE_RULES = {
        DataType.INTEGER: [
            r'(count|total|quantity|number|num|age|year)',
            r'(id|index|position|rank|level)'
        ],
        DataType.DECIMAL: [
            r'(price|cost|amount|value|rate|percentage)',
            r'(weight|height|distance|score|rating)'
        ],
        DataType.DATE: [
            r'(date|birthday|created_date|updated_date)',
            r'(start_date|end_date|due_date|expire_date)'
        ],
        DataType.DATETIME: [
            r'(created_at|updated_at|timestamp)',
            r'(start_time|end_time|logged_at)'
        ],
        DataType.BOOLEAN: [
            r'(is_|has_|can_|should_)',
            r'(active|enabled|valid|deleted)'
        ]
    }
    
    @classmethod
    def analyze_semantic_meaning(cls, placeholder_entity: PlaceholderEntity) -> AnalysisResult:
        """分析占位符的语义含义"""
        name = placeholder_entity.name.lower()
        text = placeholder_entity.text.lower()
        
        # 语义分类
        semantic_tags = set()
        for category, patterns in cls.SEMANTIC_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name) or re.search(pattern, text):
                    semantic_tags.add(category)
        
        # 数据类型推断
        inferred_type = cls._infer_data_type(name, text)
        
        # 生成业务含义描述
        business_meaning = cls._generate_business_meaning(name, semantic_tags)
        
        # 计算置信度
        confidence_score = cls._calculate_confidence(name, semantic_tags, inferred_type)
        
        # 生成验证规则
        validation_rules = cls._generate_validation_rules(inferred_type, semantic_tags)
        
        return AnalysisResult(
            business_meaning=business_meaning,
            recommended_data_type=inferred_type,
            confidence_score=confidence_score,
            validation_rules=validation_rules,
            tags=semantic_tags,
            metadata={
                'analyzed_at': datetime.now().isoformat(),
                'analyzer_version': '1.0'
            }
        )
    
    @classmethod
    def _infer_data_type(cls, name: str, text: str) -> DataType:
        """推断数据类型"""
        for data_type, patterns in cls.TYPE_INFERENCE_RULES.items():
            for pattern in patterns:
                if re.search(pattern, name) or re.search(pattern, text):
                    return data_type
        
        # 默认返回字符串类型
        return DataType.STRING
    
    @classmethod
    def _generate_business_meaning(cls, name: str, semantic_tags: Set[str]) -> str:
        """生成业务含义描述"""
        descriptions = []
        
        if 'numeric' in semantic_tags:
            if any(word in name for word in ['count', 'total', 'sum']):
                descriptions.append("表示数量或总计的数值")
            elif any(word in name for word in ['price', 'cost', 'amount']):
                descriptions.append("表示金额或价格的数值")
            else:
                descriptions.append("表示数值型数据")
        
        if 'textual' in semantic_tags:
            if any(word in name for word in ['name', 'title']):
                descriptions.append("表示名称或标题的文本")
            elif any(word in name for word in ['description', 'comment']):
                descriptions.append("表示描述性的文本内容")
            else:
                descriptions.append("表示文本型数据")
        
        if 'temporal' in semantic_tags:
            descriptions.append("表示时间相关的数据")
        
        if 'identifier' in semantic_tags:
            descriptions.append("表示唯一标识符")
        
        if 'boolean' in semantic_tags:
            descriptions.append("表示是/否或状态型数据")
        
        if descriptions:
            return "，".join(descriptions)
        else:
            return f"占位符 '{name}' 的业务含义需要进一步分析"
    
    @classmethod
    def _calculate_confidence(cls, name: str, semantic_tags: Set[str], 
                            data_type: DataType) -> float:
        """计算分析置信度"""
        base_confidence = 0.5
        
        # 有明确语义标签增加置信度
        if semantic_tags:
            base_confidence += 0.2 * len(semantic_tags)
        
        # 名称包含常见关键词增加置信度
        common_keywords = ['id', 'name', 'date', 'time', 'count', 'total', 'price', 'amount']
        for keyword in common_keywords:
            if keyword in name:
                base_confidence += 0.1
                break
        
        # 数据类型推断成功增加置信度
        if data_type != DataType.STRING:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    @classmethod
    def _generate_validation_rules(cls, data_type: DataType, 
                                 semantic_tags: Set[str]) -> List[PlaceholderRule]:
        """生成验证规则"""
        rules = []
        
        if data_type == DataType.INTEGER:
            rules.append(PlaceholderRule(
                rule_type="integer_validation",
                description="必须是整数",
                validation_pattern=r'^-?\d+$'
            ))
        
        elif data_type == DataType.DECIMAL:
            rules.append(PlaceholderRule(
                rule_type="decimal_validation",
                description="必须是数值",
                validation_pattern=r'^-?\d*\.?\d+$'
            ))
        
        elif data_type == DataType.DATE:
            rules.append(PlaceholderRule(
                rule_type="date_validation",
                description="必须是有效的日期格式",
                validation_pattern=r'^\d{4}-\d{2}-\d{2}$'
            ))
        
        elif data_type == DataType.DATETIME:
            rules.append(PlaceholderRule(
                rule_type="datetime_validation",
                description="必须是有效的日期时间格式",
                validation_pattern=r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$'
            ))
        
        # 基于语义标签的规则
        if 'identifier' in semantic_tags:
            rules.append(PlaceholderRule(
                rule_type="non_empty",
                description="标识符不能为空",
                is_required=True
            ))
        
        return rules


class PlaceholderDomainService:
    """占位符领域服务"""
    
    def __init__(self):
        self.parser = PlaceholderParser()
        self.analyzer = PlaceholderSemanticAnalyzer()
    
    def parse_template_placeholders(self, template_content: str, 
                                  template_id: str, template_name: str) -> List[PlaceholderEntity]:
        """解析模板中的占位符"""
        placeholder_data_list = self.parser.extract_placeholders(template_content)
        placeholder_entities = []
        
        for i, placeholder_data in enumerate(placeholder_data_list):
            # 创建占位符实体
            entity = PlaceholderEntity(
                placeholder_id=f"{template_id}_{i}",
                name=placeholder_data['name'],
                text=placeholder_data['text'],
                placeholder_type=placeholder_data['type']
            )
            
            # 设置上下文信息
            surrounding_context = self.parser.get_surrounding_context(
                template_content,
                placeholder_data['start_pos'],
                placeholder_data['end_pos']
            )
            
            entity.context = PlaceholderContext(
                template_id=template_id,
                template_name=template_name,
                position=placeholder_data['start_pos'],
                surrounding_text=surrounding_context
            )
            
            placeholder_entities.append(entity)
        
        return placeholder_entities
    
    def analyze_placeholder_semantics(self, placeholder_entity: PlaceholderEntity) -> AnalysisResult:
        """分析占位符语义"""
        return self.analyzer.analyze_semantic_meaning(placeholder_entity)
    
    def validate_placeholder_value(self, placeholder_entity: PlaceholderEntity, 
                                 value: Any) -> Dict[str, Any]:
        """验证占位符值"""
        return placeholder_entity.validate_value(value)
    
    def suggest_related_placeholders(self, target_placeholder: PlaceholderEntity,
                                   all_placeholders: List[PlaceholderEntity]) -> List[Tuple[PlaceholderEntity, float]]:
        """建议相关的占位符"""
        suggestions = []
        target_tags = target_placeholder.get_semantic_tags()
        target_name_parts = set(target_placeholder.name.lower().split('_'))
        
        for placeholder in all_placeholders:
            if placeholder.id == target_placeholder.id:
                continue
            
            similarity_score = 0
            
            # 语义标签相似性
            placeholder_tags = placeholder.get_semantic_tags()
            tag_intersection = target_tags & placeholder_tags
            if tag_intersection:
                similarity_score += 0.4 * (len(tag_intersection) / len(target_tags | placeholder_tags))
            
            # 名称相似性
            placeholder_name_parts = set(placeholder.name.lower().split('_'))
            name_intersection = target_name_parts & placeholder_name_parts
            if name_intersection:
                similarity_score += 0.3 * (len(name_intersection) / len(target_name_parts | placeholder_name_parts))
            
            # 数据类型相似性
            if (target_placeholder.analysis_result and placeholder.analysis_result and
                target_placeholder.analysis_result.recommended_data_type == 
                placeholder.analysis_result.recommended_data_type):
                similarity_score += 0.2
            
            # 上下文相似性（如果在同一模板）
            if (target_placeholder.context and placeholder.context and
                target_placeholder.context.template_id == placeholder.context.template_id):
                similarity_score += 0.1
            
            if similarity_score > 0.2:  # 相似性阈值
                suggestions.append((placeholder, similarity_score))
        
        # 按相似性排序
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:5]  # 返回前5个相似的占位符
    
    def generate_placeholder_documentation(self, placeholder_entity: PlaceholderEntity) -> Dict[str, Any]:
        """生成占位符文档"""
        doc = {
            'name': placeholder_entity.name,
            'text': placeholder_entity.text,
            'type': placeholder_entity.placeholder_type.value,
            'description': placeholder_entity.analysis_result.business_meaning if placeholder_entity.analysis_result else "待分析",
            'data_type': placeholder_entity.analysis_result.recommended_data_type.value if placeholder_entity.analysis_result else "未知",
            'is_required': any(rule.is_required for rule in placeholder_entity.rules),
            'validation_rules': [],
            'usage_examples': [],
            'related_placeholders': [],
            'metadata': placeholder_entity.metadata
        }
        
        # 添加验证规则文档
        for rule in placeholder_entity.rules:
            doc['validation_rules'].append({
                'type': rule.rule_type,
                'description': rule.description,
                'required': rule.is_required
            })
        
        # 添加使用示例
        if placeholder_entity.analysis_result:
            data_type = placeholder_entity.analysis_result.recommended_data_type
            if data_type == DataType.STRING:
                doc['usage_examples'] = ['"示例文本"', '"另一个示例"']
            elif data_type == DataType.INTEGER:
                doc['usage_examples'] = ['123', '456']
            elif data_type == DataType.DECIMAL:
                doc['usage_examples'] = ['123.45', '67.89']
            elif data_type == DataType.DATE:
                doc['usage_examples'] = ['2024-01-15', '2024-12-31']
            elif data_type == DataType.DATETIME:
                doc['usage_examples'] = ['2024-01-15 10:30:00', '2024-12-31 23:59:59']
            elif data_type == DataType.BOOLEAN:
                doc['usage_examples'] = ['true', 'false']
        
        return doc
    
    def batch_analyze_placeholders(self, placeholder_entities: List[PlaceholderEntity]) -> Dict[str, Any]:
        """批量分析占位符"""
        analysis_summary = {
            'total_placeholders': len(placeholder_entities),
            'analyzed': 0,
            'failed': 0,
            'high_confidence': 0,
            'by_type': {},
            'by_semantic_category': {},
            'processing_time': 0
        }
        
        start_time = datetime.now()
        
        for entity in placeholder_entities:
            try:
                analysis_result = self.analyze_placeholder_semantics(entity)
                entity.set_analysis_result(analysis_result)
                
                analysis_summary['analyzed'] += 1
                
                if analysis_result.is_high_confidence():
                    analysis_summary['high_confidence'] += 1
                
                # 统计类型分布
                data_type = analysis_result.recommended_data_type.value
                analysis_summary['by_type'][data_type] = analysis_summary['by_type'].get(data_type, 0) + 1
                
                # 统计语义分类
                for tag in analysis_result.tags:
                    analysis_summary['by_semantic_category'][tag] = analysis_summary['by_semantic_category'].get(tag, 0) + 1
                
            except Exception as e:
                entity.mark_analysis_failed(str(e))
                analysis_summary['failed'] += 1
                logger.error(f"Failed to analyze placeholder {entity.name}: {e}")
        
        end_time = datetime.now()
        analysis_summary['processing_time'] = (end_time - start_time).total_seconds()
        
        return analysis_summary