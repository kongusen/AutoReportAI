"""
Template Domain Service

模板领域服务，包含纯业务逻辑，不依赖外部AI服务
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta

from ..entities.template_entity import (
    TemplateEntity, TemplateStatus, TemplateType, TemplateSection,
    TemplateValidationRule, ValidationLevel
)

logger = logging.getLogger(__name__)


class TemplateParser:
    """模板解析器"""
    
    # 模板语法模式
    SYNTAX_PATTERNS = {
        'placeholder': r'\{\{\s*([^#/{}]+?)\s*\}\}',
        'conditional': r'\{\{#if\s+(.+?)\}\}(.*?)\{\{/if\}\}',
        'loop': r'\{\{#each\s+(.+?)\}\}(.*?)\{\{/each\}\}',
        'section': r'\{\{#section\s+([^}]+)\}\}(.*?)\{\{/section\}\}',
        'comment': r'\{\{!--(.*?)--\}\}',
        'variable': r'\{\{@(\w+)\s*=\s*(.+?)\}\}'
    }
    
    @classmethod
    def parse_template_structure(cls, content: str) -> Dict[str, Any]:
        """解析模板结构"""
        structure = {
            'placeholders': [],
            'sections': [],
            'conditionals': [],
            'loops': [],
            'variables': {},
            'comments': [],
            'complexity_score': 0
        }
        
        # 解析占位符
        placeholder_matches = re.finditer(cls.SYNTAX_PATTERNS['placeholder'], content)
        for match in placeholder_matches:
            placeholder_name = match.group(1).strip()
            structure['placeholders'].append({
                'name': placeholder_name,
                'text': match.group(0),
                'start': match.start(),
                'end': match.end()
            })
        
        # 解析段落
        section_matches = re.finditer(cls.SYNTAX_PATTERNS['section'], content, re.DOTALL)
        for i, match in enumerate(section_matches):
            section_config = match.group(1).strip()
            section_content = match.group(2).strip()
            
            structure['sections'].append({
                'id': f"section_{i}",
                'config': section_config,
                'content': section_content,
                'start': match.start(),
                'end': match.end()
            })
        
        # 解析条件语句
        conditional_matches = re.finditer(cls.SYNTAX_PATTERNS['conditional'], content, re.DOTALL)
        for match in conditional_matches:
            condition = match.group(1).strip()
            conditional_content = match.group(2).strip()
            
            structure['conditionals'].append({
                'condition': condition,
                'content': conditional_content,
                'start': match.start(),
                'end': match.end()
            })
        
        # 解析循环
        loop_matches = re.finditer(cls.SYNTAX_PATTERNS['loop'], content, re.DOTALL)
        for match in loop_matches:
            loop_expression = match.group(1).strip()
            loop_content = match.group(2).strip()
            
            structure['loops'].append({
                'expression': loop_expression,
                'content': loop_content,
                'start': match.start(),
                'end': match.end()
            })
        
        # 解析变量定义
        variable_matches = re.finditer(cls.SYNTAX_PATTERNS['variable'], content)
        for match in variable_matches:
            var_name = match.group(1).strip()
            var_value = match.group(2).strip()
            structure['variables'][var_name] = var_value
        
        # 解析注释
        comment_matches = re.finditer(cls.SYNTAX_PATTERNS['comment'], content, re.DOTALL)
        for match in comment_matches:
            comment_text = match.group(1).strip()
            structure['comments'].append({
                'text': comment_text,
                'start': match.start(),
                'end': match.end()
            })
        
        # 计算复杂度
        structure['complexity_score'] = cls._calculate_complexity(structure)
        
        return structure
    
    @classmethod
    def _calculate_complexity(cls, structure: Dict[str, Any]) -> float:
        """计算模板复杂度"""
        complexity = 0
        
        # 占位符复杂度
        complexity += len(structure['placeholders']) * 0.1
        
        # 段落复杂度
        complexity += len(structure['sections']) * 0.3
        
        # 条件语句复杂度
        complexity += len(structure['conditionals']) * 0.5
        
        # 循环复杂度
        complexity += len(structure['loops']) * 0.7
        
        # 嵌套复杂度（简化版）
        nested_count = 0
        for conditional in structure['conditionals']:
            if any(loop['start'] > conditional['start'] and loop['end'] < conditional['end'] 
                  for loop in structure['loops']):
                nested_count += 1
        
        complexity += nested_count * 0.8
        
        return round(complexity, 2)
    
    def extract_placeholders(self, content: str) -> List[Dict[str, Any]]:
        """提取占位符（兼容方法）"""
        structure = self.parse_template_structure(content)
        
        # 转换为兼容格式
        result = []
        for placeholder in structure['placeholders']:
            result.append({
                "name": placeholder['name'],
                "text": placeholder['text'],
                "start_index": placeholder['start'],
                "end_index": placeholder['end'],
                "type": "simple"
            })
        
        return result
    
    @classmethod
    def extract_dependencies(cls, content: str) -> Set[str]:
        """提取模板依赖"""
        dependencies = set()
        
        # 查找包含语句
        include_pattern = r'\{\{>\s*([^}]+)\s*\}\}'
        includes = re.findall(include_pattern, content)
        dependencies.update(includes)
        
        # 查找继承语句
        extends_pattern = r'\{\{<\s*([^}]+)\s*\}\}'
        extends = re.findall(extends_pattern, content)
        dependencies.update(extends)
        
        return dependencies


class TemplateValidator:
    """模板验证器"""
    
    @classmethod
    def create_default_rules(cls) -> List[TemplateValidationRule]:
        """创建默认验证规则"""
        rules = []
        
        # 基础语法验证
        rules.append(TemplateValidationRule(
            rule_id="syntax_balance",
            rule_type="syntax",
            description="检查占位符语法平衡",
            severity="error"
        ))
        
        # 占位符命名规范
        rules.append(TemplateValidationRule(
            rule_id="placeholder_naming",
            rule_type="naming",
            description="检查占位符命名规范",
            severity="warning"
        ))
        
        # 内容长度检查
        rules.append(TemplateValidationRule(
            rule_id="content_length",
            rule_type="content",
            description="检查模板内容长度",
            severity="info"
        ))
        
        return rules
    
    @classmethod
    def validate_syntax(cls, content: str) -> Dict[str, Any]:
        """验证模板语法"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查占位符平衡
        open_braces = content.count('{{')
        close_braces = content.count('}}')
        
        if open_braces != close_braces:
            result['valid'] = False
            result['errors'].append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
        
        # 检查条件语句平衡
        if_count = len(re.findall(r'\{\{#if\b', content))
        endif_count = len(re.findall(r'\{\{/if\}\}', content))
        
        if if_count != endif_count:
            result['valid'] = False
            result['errors'].append(f"Unbalanced if statements: {if_count} #if, {endif_count} /if")
        
        # 检查循环语句平衡
        each_count = len(re.findall(r'\{\{#each\b', content))
        endeach_count = len(re.findall(r'\{\{/each\}\}', content))
        
        if each_count != endeach_count:
            result['valid'] = False
            result['errors'].append(f"Unbalanced each statements: {each_count} #each, {endeach_count} /each")
        
        return result
    
    @classmethod
    def validate_placeholders(cls, placeholders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证占位符"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        placeholder_names = [p['name'] for p in placeholders]
        
        # 检查重复占位符
        duplicates = set([name for name in placeholder_names if placeholder_names.count(name) > 1])
        if duplicates:
            result['warnings'].append(f"Duplicate placeholders found: {', '.join(duplicates)}")
        
        # 检查命名规范
        invalid_names = []
        for placeholder in placeholders:
            name = placeholder['name']
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
                invalid_names.append(name)
        
        if invalid_names:
            result['warnings'].append(f"Invalid placeholder names: {', '.join(invalid_names)}")
        
        return result


class TemplateDomainService:
    """模板领域服务"""
    
    def __init__(self):
        self.parser = TemplateParser()
        self.validator = TemplateValidator()
    
    def create_template(self, name: str, content: str, 
                       template_type: TemplateType = TemplateType.REPORT,
                       created_by: str = None) -> TemplateEntity:
        """创建新模板"""
        template_id = f"template_{int(datetime.now().timestamp())}"
        
        template = TemplateEntity(
            template_id=template_id,
            name=name,
            content=content,
            template_type=template_type
        )
        
        template.created_by = created_by
        
        # 分析模板结构
        structure = self.analyze_template_structure(template)
        template.metadata['structure'] = structure
        
        # 设置默认验证规则
        default_rules = self.validator.create_default_rules()
        for rule in default_rules:
            template.add_validation_rule(rule)
        
        logger.info(f"Created template: {name} with {len(structure['placeholders'])} placeholders")
        
        return template
    
    def analyze_template_structure(self, template: TemplateEntity) -> Dict[str, Any]:
        """分析模板结构"""
        structure = self.parser.parse_template_structure(template.content)
        
        # 更新模板指标
        template.metrics.placeholder_count = len(structure['placeholders'])
        
        # 创建段落
        template.sections.clear()
        for i, section_data in enumerate(structure['sections']):
            section = TemplateSection(
                section_id=section_data['id'],
                name=f"Section {i+1}",
                content=section_data['content'],
                order=i,
                metadata={'config': section_data['config']}
            )
            template.sections.append(section)
        
        # 更新全局变量
        template.global_variables.update(structure['variables'])
        
        return structure
    
    def validate_template(self, template: TemplateEntity) -> Dict[str, Any]:
        """验证模板"""
        validation_result = template.validate()
        
        # 语法验证
        syntax_result = self.validator.validate_syntax(template.content)
        validation_result['errors'].extend(syntax_result['errors'])
        validation_result['warnings'].extend(syntax_result['warnings'])
        
        if not syntax_result['valid']:
            validation_result['valid'] = False
        
        # 占位符验证
        structure = self.parser.parse_template_structure(template.content)
        placeholder_result = self.validator.validate_placeholders(structure['placeholders'])
        validation_result['warnings'].extend(placeholder_result['warnings'])
        
        return validation_result
    
    def compare_templates(self, template1: TemplateEntity, 
                         template2: TemplateEntity) -> Dict[str, Any]:
        """比较两个模板"""
        comparison = {
            'content_similarity': 0.0,
            'structure_similarity': 0.0,
            'placeholder_overlap': 0.0,
            'differences': {
                'content_diff': [],
                'placeholder_diff': [],
                'section_diff': []
            }
        }
        
        # 内容相似度（简化版本）
        content1_words = set(template1.content.lower().split())
        content2_words = set(template2.content.lower().split())
        
        if content1_words or content2_words:
            intersection = len(content1_words & content2_words)
            union = len(content1_words | content2_words)
            comparison['content_similarity'] = intersection / union if union > 0 else 0.0
        
        # 占位符重叠度
        placeholders1 = template1.extract_variables()
        placeholders2 = template2.extract_variables()
        
        if placeholders1 or placeholders2:
            intersection = len(placeholders1 & placeholders2)
            union = len(placeholders1 | placeholders2)
            comparison['placeholder_overlap'] = intersection / union if union > 0 else 0.0
        
        # 占位符差异
        comparison['differences']['placeholder_diff'] = {
            'only_in_template1': list(placeholders1 - placeholders2),
            'only_in_template2': list(placeholders2 - placeholders1),
            'common': list(placeholders1 & placeholders2)
        }
        
        # 段落差异
        sections1 = {s.name for s in template1.sections}
        sections2 = {s.name for s in template2.sections}
        
        comparison['differences']['section_diff'] = {
            'only_in_template1': list(sections1 - sections2),
            'only_in_template2': list(sections2 - sections1),
            'common': list(sections1 & sections2)
        }
        
        # 结构相似度（基于段落和占位符）
        structure_score = (
            comparison['placeholder_overlap'] * 0.6 +
            (len(sections1 & sections2) / max(len(sections1 | sections2), 1)) * 0.4
        )
        comparison['structure_similarity'] = structure_score
        
        return comparison
    
    def suggest_template_improvements(self, template: TemplateEntity) -> List[Dict[str, Any]]:
        """建议模板改进"""
        suggestions = []
        
        # 获取模板优化建议
        base_suggestions = template.suggest_optimizations()
        suggestions.extend(base_suggestions)
        
        # 分析模板结构
        structure = self.parser.parse_template_structure(template.content)
        
        # 检查复杂度
        if structure['complexity_score'] > 5.0:
            suggestions.append({
                'type': 'complexity',
                'severity': 'warning',
                'message': f'Template complexity is high ({structure["complexity_score"]}), consider simplification'
            })
        
        # 检查占位符密度
        placeholder_density = len(structure['placeholders']) / max(len(template.content), 1)
        if placeholder_density > 0.1:  # 10%以上是占位符
            suggestions.append({
                'type': 'placeholder_density',
                'severity': 'info',
                'message': 'High placeholder density, ensure all placeholders are necessary'
            })
        
        # 检查段落平衡
        if len(template.sections) > 0:
            section_lengths = [len(s.content) for s in template.sections]
            if section_lengths:
                avg_length = sum(section_lengths) / len(section_lengths)
                imbalanced_sections = [
                    i for i, length in enumerate(section_lengths)
                    if abs(length - avg_length) > avg_length * 0.8
                ]
                
                if imbalanced_sections:
                    suggestions.append({
                        'type': 'section_balance',
                        'severity': 'info',
                        'message': f'Sections {imbalanced_sections} have unbalanced content length'
                    })
        
        return suggestions
    
    def extract_template_dependencies(self, template: TemplateEntity) -> Dict[str, Any]:
        """提取模板依赖"""
        dependencies = self.parser.extract_dependencies(template.content)
        
        return {
            'external_templates': list(dependencies),
            'required_variables': list(template.extract_variables()),
            'global_variables': list(template.global_variables.keys()),
            'dependency_count': len(dependencies)
        }
    
    def merge_templates(self, primary_template: TemplateEntity,
                       secondary_template: TemplateEntity,
                       merge_strategy: str = "append") -> TemplateEntity:
        """合并模板"""
        merged_name = f"{primary_template.name}_merged_{secondary_template.name}"
        
        if merge_strategy == "append":
            merged_content = primary_template.content + "\n\n" + secondary_template.content
        elif merge_strategy == "prepend":
            merged_content = secondary_template.content + "\n\n" + primary_template.content
        elif merge_strategy == "interleave":
            # 简化版本的交替合并
            primary_parts = primary_template.content.split('\n\n')
            secondary_parts = secondary_template.content.split('\n\n')
            
            merged_parts = []
            max_parts = max(len(primary_parts), len(secondary_parts))
            
            for i in range(max_parts):
                if i < len(primary_parts):
                    merged_parts.append(primary_parts[i])
                if i < len(secondary_parts):
                    merged_parts.append(secondary_parts[i])
            
            merged_content = '\n\n'.join(merged_parts)
        else:
            raise ValueError(f"Unknown merge strategy: {merge_strategy}")
        
        merged_template = self.create_template(
            name=merged_name,
            content=merged_content,
            template_type=primary_template.template_type
        )
        
        # 合并元数据
        merged_template.tags = primary_template.tags | secondary_template.tags
        merged_template.global_variables.update(primary_template.global_variables)
        merged_template.global_variables.update(secondary_template.global_variables)
        
        # 合并验证规则（去重）
        rule_types = set()
        for rule in primary_template.validation_rules + secondary_template.validation_rules:
            if rule.rule_type not in rule_types:
                merged_template.add_validation_rule(rule)
                rule_types.add(rule.rule_type)
        
        logger.info(f"Merged templates: {primary_template.name} + {secondary_template.name}")
        
        return merged_template
    
    def create_template_variant(self, base_template: TemplateEntity,
                              variant_name: str, modifications: Dict[str, Any]) -> TemplateEntity:
        """创建模板变体"""
        variant = base_template.clone(variant_name)
        
        # 应用修改
        if 'content_replacements' in modifications:
            for old_text, new_text in modifications['content_replacements'].items():
                variant.content = variant.content.replace(old_text, new_text)
        
        if 'add_tags' in modifications:
            variant.tags.update(modifications['add_tags'])
        
        if 'remove_tags' in modifications:
            variant.tags -= set(modifications['remove_tags'])
        
        if 'global_variables' in modifications:
            variant.global_variables.update(modifications['global_variables'])
        
        if 'description' in modifications:
            variant.description = modifications['description']
        
        # 重新分析结构
        self.analyze_template_structure(variant)
        
        logger.info(f"Created template variant: {variant_name} from {base_template.name}")
        
        return variant