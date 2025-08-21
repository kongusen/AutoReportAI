"""
Template Domain Entities

模板领域实体，包含核心业务逻辑
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TemplateStatus(Enum):
    """模板状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class TemplateType(Enum):
    """模板类型"""
    REPORT = "report"
    DOCUMENT = "document"
    EMAIL = "email"
    DASHBOARD = "dashboard"
    PRESENTATION = "presentation"
    FORM = "form"
    CUSTOM = "custom"


class ValidationLevel(Enum):
    """验证级别"""
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    CUSTOM = "custom"


@dataclass
class TemplateMetrics:
    """模板指标"""
    placeholder_count: int = 0
    usage_count: int = 0
    success_rate: float = 0.0
    average_processing_time: float = 0.0
    last_used_at: Optional[datetime] = None
    error_count: int = 0
    
    def update_usage(self, processing_time: float, success: bool):
        """更新使用统计"""
        self.usage_count += 1
        
        # 更新平均处理时间（指数移动平均）
        alpha = 0.1
        self.average_processing_time = (
            alpha * processing_time + 
            (1 - alpha) * self.average_processing_time
        )
        
        # 更新成功率
        if success:
            # 成功率的指数移动平均
            self.success_rate = (
                alpha * 1.0 + 
                (1 - alpha) * self.success_rate
            )
        else:
            self.error_count += 1
            self.success_rate = (
                alpha * 0.0 + 
                (1 - alpha) * self.success_rate
            )
        
        self.last_used_at = datetime.now()


@dataclass
class TemplateValidationRule:
    """模板验证规则"""
    rule_id: str
    rule_type: str
    description: str
    severity: str = "error"  # error, warning, info
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self, template_content: str, placeholders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证模板"""
        return {
            'rule_id': self.rule_id,
            'passed': True,
            'message': '',
            'details': {}
        }


@dataclass
class TemplateSection:
    """模板段落"""
    section_id: str
    name: str
    content: str
    order: int = 0
    is_repeatable: bool = False
    conditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TemplateEntity:
    """模板领域实体"""
    
    def __init__(self, 
                 template_id: str,
                 name: str,
                 content: str,
                 template_type: TemplateType = TemplateType.REPORT):
        self.id = template_id
        self.name = name
        self.content = content
        self.template_type = template_type
        
        # 状态管理
        self.status = TemplateStatus.DRAFT
        self.version = 1
        self.is_active = True
        
        # 结构化信息
        self.sections: List[TemplateSection] = []
        self.global_variables: Dict[str, Any] = {}
        
        # 验证和规则
        self.validation_level = ValidationLevel.BASIC
        self.validation_rules: List[TemplateValidationRule] = []
        
        # 指标和统计
        self.metrics = TemplateMetrics()
        
        # 分类和标签
        self.category = "default"
        self.tags: Set[str] = set()
        self.description = ""
        
        # 元数据
        self.metadata: Dict[str, Any] = {}
        
        # 审计信息
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.created_by: Optional[str] = None
        self.updated_by: Optional[str] = None
    
    def update_content(self, new_content: str, updated_by: str = None):
        """更新模板内容"""
        if new_content != self.content:
            self.content = new_content
            self.version += 1
            self.updated_at = datetime.now()
            self.updated_by = updated_by
            
            # 重新分析模板结构
            self._analyze_structure()
            
            logger.info(f"Template {self.name} updated to version {self.version}")
    
    def activate(self):
        """激活模板"""
        self.status = TemplateStatus.ACTIVE
        self.is_active = True
        self.updated_at = datetime.now()
    
    def deactivate(self):
        """停用模板"""
        self.status = TemplateStatus.INACTIVE
        self.is_active = False
        self.updated_at = datetime.now()
    
    def archive(self):
        """归档模板"""
        self.status = TemplateStatus.ARCHIVED
        self.is_active = False
        self.updated_at = datetime.now()
    
    def add_section(self, section: TemplateSection):
        """添加段落"""
        self.sections.append(section)
        self.sections.sort(key=lambda s: s.order)
        self.updated_at = datetime.now()
    
    def remove_section(self, section_id: str) -> bool:
        """移除段落"""
        initial_count = len(self.sections)
        self.sections = [s for s in self.sections if s.section_id != section_id]
        
        if len(self.sections) < initial_count:
            self.updated_at = datetime.now()
            return True
        return False
    
    def add_validation_rule(self, rule: TemplateValidationRule):
        """添加验证规则"""
        # 检查是否已存在相同类型的规则
        existing_rule = next((r for r in self.validation_rules if r.rule_type == rule.rule_type), None)
        if existing_rule:
            # 替换现有规则
            self.validation_rules.remove(existing_rule)
        
        self.validation_rules.append(rule)
        self.updated_at = datetime.now()
    
    def remove_validation_rule(self, rule_id: str) -> bool:
        """移除验证规则"""
        initial_count = len(self.validation_rules)
        self.validation_rules = [r for r in self.validation_rules if r.rule_id != rule_id]
        
        if len(self.validation_rules) < initial_count:
            self.updated_at = datetime.now()
            return True
        return False
    
    def validate(self) -> Dict[str, Any]:
        """验证模板"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': [],
            'details': {}
        }
        
        # 基础验证
        if not self.name.strip():
            validation_result['valid'] = False
            validation_result['errors'].append("Template name cannot be empty")
        
        if not self.content.strip():
            validation_result['valid'] = False
            validation_result['errors'].append("Template content cannot be empty")
        
        # 应用自定义验证规则
        for rule in self.validation_rules:
            if rule.is_active:
                try:
                    # 这里需要实现具体的验证逻辑
                    # 占位符信息可以从外部传入或在实体中维护
                    rule_result = rule.validate(self.content, [])
                    
                    if not rule_result['passed']:
                        if rule.severity == 'error':
                            validation_result['valid'] = False
                            validation_result['errors'].append(rule_result['message'])
                        elif rule.severity == 'warning':
                            validation_result['warnings'].append(rule_result['message'])
                        else:
                            validation_result['info'].append(rule_result['message'])
                
                except Exception as e:
                    logger.error(f"Validation rule {rule.rule_id} failed: {e}")
                    validation_result['warnings'].append(f"Validation rule {rule.rule_id} failed to execute")
        
        return validation_result
    
    def extract_variables(self) -> Set[str]:
        """提取模板中的变量"""
        variables = set()
        
        # 提取占位符变量
        placeholder_pattern = r'\{\{\s*([^#/{}]+?)\s*\}\}'
        matches = re.findall(placeholder_pattern, self.content)
        
        for match in matches:
            # 清理变量名
            var_name = match.split('|')[0].split(':')[0].strip()
            variables.add(var_name)
        
        return variables
    
    def get_complexity_score(self) -> float:
        """计算模板复杂度分数"""
        score = 0.0
        
        # 基于内容长度
        content_length = len(self.content)
        score += min(content_length / 1000, 5.0)  # 最多5分
        
        # 基于占位符数量
        placeholders = self.extract_variables()
        score += min(len(placeholders) / 10, 3.0)  # 最多3分
        
        # 基于段落数量
        score += min(len(self.sections) / 5, 2.0)  # 最多2分
        
        # 基于验证规则数量
        score += min(len(self.validation_rules) / 5, 1.0)  # 最多1分
        
        return round(score, 2)
    
    def suggest_optimizations(self) -> List[Dict[str, Any]]:
        """建议优化"""
        suggestions = []
        
        # 检查内容长度
        if len(self.content) > 10000:
            suggestions.append({
                'type': 'content_length',
                'severity': 'warning',
                'message': 'Template content is very long, consider breaking it into sections'
            })
        
        # 检查占位符数量
        placeholders = self.extract_variables()
        if len(placeholders) > 50:
            suggestions.append({
                'type': 'placeholder_count',
                'severity': 'warning', 
                'message': 'Template has many placeholders, consider grouping or simplifying'
            })
        
        # 检查使用统计
        if self.metrics.usage_count > 0 and self.metrics.success_rate < 0.8:
            suggestions.append({
                'type': 'success_rate',
                'severity': 'error',
                'message': f'Template has low success rate ({self.metrics.success_rate:.1%}), needs review'
            })
        
        # 检查最后使用时间
        if self.metrics.last_used_at:
            days_since_use = (datetime.now() - self.metrics.last_used_at).days
            if days_since_use > 90:
                suggestions.append({
                    'type': 'unused_template',
                    'severity': 'info',
                    'message': f'Template not used for {days_since_use} days, consider archiving'
                })
        
        return suggestions
    
    def _analyze_structure(self):
        """分析模板结构"""
        # 这里可以实现模板结构分析逻辑
        # 例如：识别重复段落、条件块等
        pass
    
    def clone(self, new_name: str, cloned_by: str = None) -> 'TemplateEntity':
        """克隆模板"""
        cloned_template = TemplateEntity(
            template_id=f"{self.id}_clone_{int(datetime.now().timestamp())}",
            name=new_name,
            content=self.content,
            template_type=self.template_type
        )
        
        # 复制配置
        cloned_template.validation_level = self.validation_level
        cloned_template.category = self.category
        cloned_template.tags = self.tags.copy()
        cloned_template.description = f"Cloned from {self.name}"
        cloned_template.global_variables = self.global_variables.copy()
        
        # 复制段落
        for section in self.sections:
            cloned_section = TemplateSection(
                section_id=f"{section.section_id}_clone",
                name=section.name,
                content=section.content,
                order=section.order,
                is_repeatable=section.is_repeatable,
                conditions=section.conditions.copy(),
                metadata=section.metadata.copy()
            )
            cloned_template.sections.append(cloned_section)
        
        # 复制验证规则
        for rule in self.validation_rules:
            cloned_rule = TemplateValidationRule(
                rule_id=f"{rule.rule_id}_clone",
                rule_type=rule.rule_type,
                description=rule.description,
                severity=rule.severity,
                is_active=rule.is_active,
                metadata=rule.metadata.copy()
            )
            cloned_template.validation_rules.append(cloned_rule)
        
        cloned_template.created_by = cloned_by
        
        return cloned_template
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'template_type': self.template_type.value,
            'status': self.status.value,
            'version': self.version,
            'is_active': self.is_active,
            'sections': [
                {
                    'section_id': s.section_id,
                    'name': s.name,
                    'content': s.content,
                    'order': s.order,
                    'is_repeatable': s.is_repeatable,
                    'conditions': s.conditions,
                    'metadata': s.metadata
                } for s in self.sections
            ],
            'global_variables': self.global_variables,
            'validation_level': self.validation_level.value,
            'validation_rules': [
                {
                    'rule_id': r.rule_id,
                    'rule_type': r.rule_type,
                    'description': r.description,
                    'severity': r.severity,
                    'is_active': r.is_active,
                    'metadata': r.metadata
                } for r in self.validation_rules
            ],
            'metrics': {
                'placeholder_count': self.metrics.placeholder_count,
                'usage_count': self.metrics.usage_count,
                'success_rate': self.metrics.success_rate,
                'average_processing_time': self.metrics.average_processing_time,
                'last_used_at': self.metrics.last_used_at.isoformat() if self.metrics.last_used_at else None,
                'error_count': self.metrics.error_count
            },
            'category': self.category,
            'tags': list(self.tags),
            'description': self.description,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateEntity':
        """从字典创建实例"""
        entity = cls(
            template_id=data['id'],
            name=data['name'],
            content=data['content'],
            template_type=TemplateType(data.get('template_type', 'report'))
        )
        
        # 设置基本属性
        entity.status = TemplateStatus(data.get('status', 'draft'))
        entity.version = data.get('version', 1)
        entity.is_active = data.get('is_active', True)
        entity.validation_level = ValidationLevel(data.get('validation_level', 'basic'))
        entity.category = data.get('category', 'default')
        entity.tags = set(data.get('tags', []))
        entity.description = data.get('description', '')
        entity.metadata = data.get('metadata', {})
        entity.global_variables = data.get('global_variables', {})
        
        # 设置时间戳
        if data.get('created_at'):
            entity.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            entity.updated_at = datetime.fromisoformat(data['updated_at'])
        
        entity.created_by = data.get('created_by')
        entity.updated_by = data.get('updated_by')
        
        return entity
    
    def __str__(self) -> str:
        return f"TemplateEntity(id={self.id}, name={self.name}, status={self.status.value})"
    
    def __repr__(self) -> str:
        return self.__str__()