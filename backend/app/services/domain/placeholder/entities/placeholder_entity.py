"""
Placeholder Domain Entities

占位符领域实体，包含核心业务逻辑
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PlaceholderType(Enum):
    """占位符类型"""
    SIMPLE = "simple"           # 简单占位符 {{name}}
    CONDITIONAL = "conditional" # 条件占位符 {{#if condition}}
    LOOP = "loop"              # 循环占位符 {{#each items}}
    EXPRESSION = "expression"   # 表达式占位符 {{= expression}}
    FUNCTION = "function"       # 函数占位符 {{function(args)}}


class DataType(Enum):
    """数据类型"""
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"


class AnalysisStatus(Enum):
    """分析状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass
class PlaceholderRule:
    """占位符规则"""
    rule_type: str
    description: str
    validation_pattern: Optional[str] = None
    default_value: Any = None
    is_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self, value: Any) -> bool:
        """验证值是否符合规则"""
        if self.is_required and value is None:
            return False
        
        if self.validation_pattern and isinstance(value, str):
            return bool(re.match(self.validation_pattern, value))
        
        return True


@dataclass
class PlaceholderContext:
    """占位符上下文"""
    template_id: str
    template_name: str
    section: Optional[str] = None
    position: Optional[int] = None
    surrounding_text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """分析结果"""
    business_meaning: str
    recommended_data_type: DataType
    confidence_score: float
    sql_suggestion: Optional[str] = None
    data_source_suggestions: List[str] = field(default_factory=list)
    validation_rules: List[PlaceholderRule] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """是否高置信度"""
        return self.confidence_score >= threshold


class PlaceholderEntity:
    """占位符领域实体"""
    
    def __init__(self, 
                 placeholder_id: str,
                 name: str,
                 text: str,
                 placeholder_type: PlaceholderType = PlaceholderType.SIMPLE):
        self.id = placeholder_id
        self.name = name
        self.text = text
        self.placeholder_type = placeholder_type
        
        # 分析相关
        self.analysis_status = AnalysisStatus.PENDING
        self.analysis_result: Optional[AnalysisResult] = None
        self.last_analyzed_at: Optional[datetime] = None
        
        # 上下文信息
        self.context: Optional[PlaceholderContext] = None
        
        # 规则和配置
        self.rules: List[PlaceholderRule] = []
        self.is_active = True
        self.priority = 0
        
        # 元数据
        self.metadata: Dict[str, Any] = {}
        
        # 审计信息
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.version = 1
    
    def set_analysis_result(self, result: AnalysisResult):
        """设置分析结果"""
        self.analysis_result = result
        self.analysis_status = AnalysisStatus.COMPLETED
        self.last_analyzed_at = datetime.now()
        self.updated_at = datetime.now()
        self.version += 1
        
        logger.info(f"Analysis completed for placeholder {self.name} with confidence {result.confidence_score}")
    
    def mark_analysis_failed(self, error_message: str):
        """标记分析失败"""
        self.analysis_status = AnalysisStatus.FAILED
        self.last_analyzed_at = datetime.now()
        self.metadata['last_error'] = error_message
        self.updated_at = datetime.now()
        self.version += 1
        
        logger.warning(f"Analysis failed for placeholder {self.name}: {error_message}")
    
    def add_rule(self, rule: PlaceholderRule):
        """添加验证规则"""
        self.rules.append(rule)
        self.updated_at = datetime.now()
    
    def remove_rule(self, rule_type: str) -> bool:
        """移除指定类型的规则"""
        initial_count = len(self.rules)
        self.rules = [rule for rule in self.rules if rule.rule_type != rule_type]
        
        if len(self.rules) < initial_count:
            self.updated_at = datetime.now()
            return True
        return False
    
    def validate_value(self, value: Any) -> Dict[str, Any]:
        """验证值"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        for rule in self.rules:
            if not rule.validate(value):
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Value violates rule '{rule.rule_type}': {rule.description}"
                )
        
        return validation_result
    
    def extract_parameters(self) -> List[str]:
        """从占位符文本中提取参数"""
        parameters = []
        
        if self.placeholder_type == PlaceholderType.FUNCTION:
            # 提取函数参数
            match = re.search(r'\{\{\s*(\w+)\s*\(([^)]*)\)\s*\}\}', self.text)
            if match:
                args_str = match.group(2)
                if args_str:
                    parameters = [arg.strip() for arg in args_str.split(',')]
        elif self.placeholder_type == PlaceholderType.CONDITIONAL:
            # 提取条件参数
            match = re.search(r'\{\{#if\s+(.+?)\}\}', self.text)
            if match:
                parameters = [match.group(1).strip()]
        elif self.placeholder_type == PlaceholderType.LOOP:
            # 提取循环参数
            match = re.search(r'\{\{#each\s+(.+?)\}\}', self.text)
            if match:
                parameters = [match.group(1).strip()]
        
        return parameters
    
    def get_semantic_tags(self) -> Set[str]:
        """获取语义标签"""
        tags = set()
        
        # 基于名称的标签
        name_lower = self.name.lower()
        
        if any(keyword in name_lower for keyword in ['count', 'total', 'sum', 'amount']):
            tags.add('numeric')
            tags.add('aggregate')
        
        if any(keyword in name_lower for keyword in ['date', 'time', 'created', 'updated']):
            tags.add('temporal')
        
        if any(keyword in name_lower for keyword in ['name', 'title', 'description']):
            tags.add('textual')
        
        if any(keyword in name_lower for keyword in ['id', 'key', 'reference']):
            tags.add('identifier')
        
        if any(keyword in name_lower for keyword in ['user', 'customer', 'person']):
            tags.add('personal')
        
        # 基于分析结果的标签
        if self.analysis_result:
            tags.update(self.analysis_result.tags)
        
        return tags
    
    def suggest_data_source_tables(self, available_tables: List[str]) -> List[Dict[str, Any]]:
        """建议相关的数据源表"""
        suggestions = []
        semantic_tags = self.get_semantic_tags()
        name_keywords = self.name.lower().split('_')
        
        for table_name in available_tables:
            table_lower = table_name.lower()
            score = 0
            reasons = []
            
            # 名称匹配
            for keyword in name_keywords:
                if keyword in table_lower:
                    score += 0.3
                    reasons.append(f"Name keyword '{keyword}' matches table name")
            
            # 语义标签匹配
            if 'personal' in semantic_tags and any(word in table_lower for word in ['user', 'customer', 'person']):
                score += 0.4
                reasons.append("Personal data semantic match")
            
            if 'temporal' in semantic_tags and any(word in table_lower for word in ['log', 'event', 'history']):
                score += 0.3
                reasons.append("Temporal data semantic match")
            
            if score > 0.2:  # 阈值
                suggestions.append({
                    'table_name': table_name,
                    'relevance_score': min(score, 1.0),
                    'reasons': reasons
                })
        
        # 按相关性排序
        suggestions.sort(key=lambda x: x['relevance_score'], reverse=True)
        return suggestions[:5]  # 返回前5个建议
    
    def needs_reanalysis(self, analysis_ttl_hours: int = 24) -> bool:
        """是否需要重新分析"""
        if self.analysis_status == AnalysisStatus.PENDING:
            return True
        
        if self.analysis_status == AnalysisStatus.FAILED:
            return True
        
        if self.last_analyzed_at:
            elapsed = datetime.now() - self.last_analyzed_at
            if elapsed.total_seconds() > analysis_ttl_hours * 3600:
                return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'text': self.text,
            'placeholder_type': self.placeholder_type.value,
            'analysis_status': self.analysis_status.value,
            'analysis_result': self.analysis_result.__dict__ if self.analysis_result else None,
            'context': self.context.__dict__ if self.context else None,
            'rules': [rule.__dict__ for rule in self.rules],
            'is_active': self.is_active,
            'priority': self.priority,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaceholderEntity':
        """从字典创建实例"""
        entity = cls(
            placeholder_id=data['id'],
            name=data['name'],
            text=data['text'],
            placeholder_type=PlaceholderType(data.get('placeholder_type', 'simple'))
        )
        
        # 设置其他属性
        entity.analysis_status = AnalysisStatus(data.get('analysis_status', 'pending'))
        entity.is_active = data.get('is_active', True)
        entity.priority = data.get('priority', 0)
        entity.metadata = data.get('metadata', {})
        entity.version = data.get('version', 1)
        
        # 设置时间戳
        if data.get('created_at'):
            entity.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            entity.updated_at = datetime.fromisoformat(data['updated_at'])
        
        return entity
    
    def __str__(self) -> str:
        return f"PlaceholderEntity(id={self.id}, name={self.name}, status={self.analysis_status.value})"
    
    def __repr__(self) -> str:
        return self.__str__()