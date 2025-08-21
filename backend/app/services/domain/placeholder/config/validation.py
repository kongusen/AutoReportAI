"""
Placeholder Configuration Validation

占位符配置验证器
"""

import re
import logging
from typing import Dict, Any, List, Optional

from ..core.constants import SUPPORTED_PLACEHOLDER_TYPES, ContentType
from ..core.exceptions import PlaceholderValidationError

logger = logging.getLogger(__name__)


class PlaceholderConfigValidator:
    """占位符配置验证器"""
    
    def __init__(self):
        self.required_fields = ["placeholder_name"]
        self.optional_fields = [
            "placeholder_text", "placeholder_type", "content_type",
            "description", "execution_order", "is_active",
            "target_database", "target_table", "target_column",
            "suggested_sql", "default_value", "format_template"
        ]
    
    async def validate_new_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证新配置数据
        
        Args:
            config_data: 配置数据
            
        Returns:
            验证结果
        """
        errors = []
        warnings = []
        
        try:
            # 检查必需字段
            for field in self.required_fields:
                if field not in config_data or not config_data[field]:
                    errors.append(f"缺少必需字段: {field}")
            
            # 验证字段值
            field_errors = self._validate_field_values(config_data)
            errors.extend(field_errors)
            
            # 验证字段关系
            relation_errors = self._validate_field_relations(config_data)
            errors.extend(relation_errors)
            
            # 生成警告
            field_warnings = self._generate_warnings(config_data)
            warnings.extend(field_warnings)
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"配置验证异常: {e}")
            return {
                "valid": False,
                "errors": [f"验证异常: {str(e)}"],
                "warnings": warnings
            }
    
    async def validate_config_update(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证配置更新数据
        
        Args:
            update_data: 更新数据
            
        Returns:
            验证结果
        """
        errors = []
        warnings = []
        
        try:
            # 检查字段是否可更新
            for field in update_data:
                if field not in self.required_fields + self.optional_fields:
                    warnings.append(f"未知字段: {field}")
            
            # 验证字段值
            field_errors = self._validate_field_values(update_data)
            errors.extend(field_errors)
            
            # 验证字段关系（仅针对提供的字段）
            relation_errors = self._validate_field_relations(update_data)
            errors.extend(relation_errors)
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"更新验证异常: {e}")
            return {
                "valid": False,
                "errors": [f"验证异常: {str(e)}"],
                "warnings": warnings
            }
    
    def _validate_field_values(self, data: Dict[str, Any]) -> List[str]:
        """验证字段值"""
        errors = []
        
        # 验证placeholder_name
        if "placeholder_name" in data:
            name = data["placeholder_name"]
            if not isinstance(name, str) or not name.strip():
                errors.append("placeholder_name必须是非空字符串")
            elif not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
                errors.append("placeholder_name只能包含字母、数字和下划线，且必须以字母或下划线开头")
        
        # 验证placeholder_type
        if "placeholder_type" in data:
            ptype = data["placeholder_type"]
            if ptype not in SUPPORTED_PLACEHOLDER_TYPES:
                errors.append(f"不支持的占位符类型: {ptype}")
        
        # 验证content_type
        if "content_type" in data:
            ctype = data["content_type"]
            valid_content_types = [e.value for e in ContentType]
            if ctype not in valid_content_types:
                errors.append(f"不支持的内容类型: {ctype}")
        
        # 验证execution_order
        if "execution_order" in data:
            order = data["execution_order"]
            if not isinstance(order, int) or order < 0:
                errors.append("execution_order必须是非负整数")
        
        # 验证SQL
        if "suggested_sql" in data:
            sql = data["suggested_sql"]
            if sql and not isinstance(sql, str):
                errors.append("suggested_sql必须是字符串")
            elif sql and len(sql.strip()) == 0:
                errors.append("suggested_sql不能为空字符串")
        
        # 验证is_active
        if "is_active" in data:
            active = data["is_active"]
            if not isinstance(active, bool):
                errors.append("is_active必须是布尔值")
        
        return errors
    
    def _validate_field_relations(self, data: Dict[str, Any]) -> List[str]:
        """验证字段关系"""
        errors = []
        
        # 验证类型和内容类型的兼容性
        ptype = data.get("placeholder_type")
        ctype = data.get("content_type")
        
        if ptype and ctype:
            compatibility = self._check_type_compatibility(ptype, ctype)
            if not compatibility["compatible"]:
                errors.append(f"占位符类型 '{ptype}' 与内容类型 '{ctype}' 不兼容: {compatibility['reason']}")
        
        # 验证SQL和类型的一致性
        sql = data.get("suggested_sql")
        if sql and ptype:
            sql_validation = self._validate_sql_for_type(sql, ptype)
            if not sql_validation["valid"]:
                errors.append(f"SQL与占位符类型不匹配: {sql_validation['reason']}")
        
        return errors
    
    def _generate_warnings(self, data: Dict[str, Any]) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        # 检查缺少的推荐字段
        if "placeholder_type" not in data:
            warnings.append("建议指定placeholder_type")
        
        if "content_type" not in data:
            warnings.append("建议指定content_type")
        
        if "description" not in data or not data["description"]:
            warnings.append("建议提供description以便更好的分析")
        
        # 检查字段长度
        name = data.get("placeholder_name", "")
        if len(name) > 50:
            warnings.append("placeholder_name过长，建议少于50个字符")
        
        description = data.get("description", "")
        if len(description) > 500:
            warnings.append("description过长，建议少于500个字符")
        
        return warnings
    
    def _check_type_compatibility(self, placeholder_type: str, content_type: str) -> Dict[str, Any]:
        """检查类型兼容性"""
        # 定义兼容性映射
        compatibility_matrix = {
            "metric": ["number", "percentage", "currency"],
            "text": ["text", "html"],
            "date": ["date", "datetime"],
            "list": ["json", "text"],
            "table": ["json", "html"],
            "chart": ["json"],
            "calculation": ["number", "percentage", "currency"]
        }
        
        compatible_types = compatibility_matrix.get(placeholder_type, [])
        
        if content_type in compatible_types:
            return {"compatible": True}
        else:
            return {
                "compatible": False,
                "reason": f"类型 '{placeholder_type}' 通常与内容类型 {compatible_types} 兼容"
            }
    
    def _validate_sql_for_type(self, sql: str, placeholder_type: str) -> Dict[str, Any]:
        """验证SQL与类型的一致性"""
        sql_lower = sql.lower()
        
        # 基本SQL语法检查
        if not sql_lower.strip().startswith("select"):
            return {
                "valid": False,
                "reason": "SQL必须以SELECT开头"
            }
        
        # 类型特定的SQL检查
        type_patterns = {
            "metric": ["count", "sum", "avg", "max", "min"],
            "calculation": ["count", "sum", "avg", "*", "/", "%"],
            "date": ["max", "min", "date", "time"],
            "list": ["select", "from"],
            "table": ["select", "from"]
        }
        
        expected_patterns = type_patterns.get(placeholder_type)
        if expected_patterns:
            found_patterns = [pattern for pattern in expected_patterns if pattern in sql_lower]
            if not found_patterns:
                return {
                    "valid": False,
                    "reason": f"SQL不包含 '{placeholder_type}' 类型的典型模式: {expected_patterns}"
                }
        
        return {"valid": True}