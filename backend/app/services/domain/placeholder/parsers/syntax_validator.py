"""
占位符语法验证器

提供全面的占位符语法验证功能
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from ..models import (
    SyntaxType, StatisticalType, PlaceholderSyntaxError
)

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """验证严重程度"""
    ERROR = "error"         # 语法错误，无法解析
    WARNING = "warning"     # 语法警告，可能影响结果
    INFO = "info"          # 信息提示，建议优化


class ValidationRule:
    """验证规则"""
    
    def __init__(self, rule_id: str, severity: ValidationSeverity, message: str, check_func: callable):
        self.rule_id = rule_id
        self.severity = severity
        self.message = message
        self.check_func = check_func


class ValidationResult:
    """验证结果"""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.infos: List[str] = []
        self.suggested_fixes: List[str] = []
    
    def add_issue(self, severity: ValidationSeverity, message: str, suggested_fix: str = None):
        """添加验证问题"""
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False
            self.errors.append(message)
        elif severity == ValidationSeverity.WARNING:
            self.warnings.append(message)
        elif severity == ValidationSeverity.INFO:
            self.infos.append(message)
        
        if suggested_fix:
            self.suggested_fixes.append(suggested_fix)
    
    def get_summary(self) -> str:
        """获取验证结果摘要"""
        if self.is_valid:
            if self.warnings or self.infos:
                return f"语法有效，但有 {len(self.warnings)} 个警告和 {len(self.infos)} 个提示"
            return "语法完全有效"
        else:
            return f"语法无效，有 {len(self.errors)} 个错误"


class SyntaxValidator:
    """占位符语法验证器"""
    
    def __init__(self):
        self.syntax_patterns = {
            SyntaxType.BASIC: r'\{\{(\w+)：([^}|]+)\}\}',
            SyntaxType.PARAMETERIZED: r'\{\{(\w+)：([^|}]+)(\|([^}]+))?\}\}',
            SyntaxType.COMPOSITE: r'\{\{组合：(.+)\}\}',
            SyntaxType.CONDITIONAL: r'\{\{(\w+)：([^|}]+)\|条件=([^|}]+)((\|[^}]+)*)\}\}'
        }
        
        self.statistical_types = {
            '统计', '趋势', '极值', '列表', '统计图', '对比', '预测'
        }
        
        self.validation_rules = self._initialize_rules()
    
    def _initialize_rules(self) -> List[ValidationRule]:
        """初始化验证规则"""
        rules = []
        
        # 基础语法规则
        rules.extend([
            ValidationRule(
                "R001", ValidationSeverity.ERROR, "占位符必须以{{开始，}}结束",
                lambda text: text.strip().startswith('{{') and text.strip().endswith('}}')
            ),
            ValidationRule(
                "R002", ValidationSeverity.ERROR, "占位符不能为空",
                lambda text: len(text.strip()) > 4  # 至少包含{{}}
            ),
            ValidationRule(
                "R003", ValidationSeverity.ERROR, "占位符必须包含冒号分隔符",
                lambda text: '：' in text or ':' in text
            ),
        ])
        
        # 统计类型规则
        rules.extend([
            ValidationRule(
                "R101", ValidationSeverity.ERROR, "必须指定有效的统计类型",
                self._check_statistical_type
            ),
            ValidationRule(
                "R102", ValidationSeverity.WARNING, "建议使用标准统计类型名称",
                self._check_standard_type_names
            ),
        ])
        
        # 参数格式规则
        rules.extend([
            ValidationRule(
                "R201", ValidationSeverity.ERROR, "参数格式必须为 键=值",
                self._check_parameter_format
            ),
            ValidationRule(
                "R202", ValidationSeverity.WARNING, "参数值不应为空",
                self._check_parameter_values
            ),
            ValidationRule(
                "R203", ValidationSeverity.INFO, "建议使用标准参数名称",
                self._check_standard_parameter_names
            ),
        ])
        
        # 条件逻辑规则
        rules.extend([
            ValidationRule(
                "R301", ValidationSeverity.ERROR, "条件表达式格式不正确",
                self._check_condition_format
            ),
            ValidationRule(
                "R302", ValidationSeverity.WARNING, "建议为条件占位符提供回退逻辑",
                self._check_fallback_logic
            ),
        ])
        
        # 组合占位符规则
        rules.extend([
            ValidationRule(
                "R401", ValidationSeverity.ERROR, "组合占位符必须包含至少2个子占位符",
                self._check_composite_sub_placeholders
            ),
            ValidationRule(
                "R402", ValidationSeverity.WARNING, "组合逻辑应该明确指定运算关系",
                self._check_composite_logic_clarity
            ),
        ])
        
        return rules
    
    def validate(self, placeholder_text: str) -> ValidationResult:
        """验证占位符语法"""
        result = ValidationResult()
        
        try:
            # 识别语法类型
            syntax_type = self._identify_syntax_type(placeholder_text)
            
            # 应用相关的验证规则
            for rule in self.validation_rules:
                try:
                    if not rule.check_func(placeholder_text):
                        suggested_fix = self._get_suggested_fix(rule.rule_id, placeholder_text)
                        result.add_issue(rule.severity, f"[{rule.rule_id}] {rule.message}", suggested_fix)
                except Exception as e:
                    logger.warning(f"验证规则 {rule.rule_id} 执行失败: {e}")
            
            # 特定语法类型的验证
            self._validate_specific_syntax(placeholder_text, syntax_type, result)
            
        except Exception as e:
            result.add_issue(ValidationSeverity.ERROR, f"语法验证过程中出现错误: {e}")
        
        return result
    
    def validate_batch(self, placeholder_texts: List[str]) -> Dict[str, ValidationResult]:
        """批量验证占位符语法"""
        results = {}
        
        for i, text in enumerate(placeholder_texts):
            key = f"placeholder_{i+1}"
            results[key] = self.validate(text)
        
        return results
    
    def _identify_syntax_type(self, text: str) -> Optional[SyntaxType]:
        """识别语法类型"""
        for syntax_type, pattern in self.syntax_patterns.items():
            if re.match(pattern, text):
                return syntax_type
        return None
    
    def _validate_specific_syntax(self, text: str, syntax_type: SyntaxType, result: ValidationResult):
        """验证特定语法类型"""
        if syntax_type == SyntaxType.PARAMETERIZED:
            self._validate_parameterized_syntax(text, result)
        elif syntax_type == SyntaxType.CONDITIONAL:
            self._validate_conditional_syntax(text, result)
        elif syntax_type == SyntaxType.COMPOSITE:
            self._validate_composite_syntax(text, result)
    
    def _validate_parameterized_syntax(self, text: str, result: ValidationResult):
        """验证参数化语法"""
        # 提取参数部分
        match = re.match(self.syntax_patterns[SyntaxType.PARAMETERIZED], text)
        if match and match.group(4):
            params_str = match.group(4)
            self._validate_parameters(params_str, result)
    
    def _validate_conditional_syntax(self, text: str, result: ValidationResult):
        """验证条件语法"""
        # 检查条件表达式
        if '条件=' in text:
            condition_match = re.search(r'条件=([^|}]+)', text)
            if condition_match:
                condition = condition_match.group(1)
                if not any(op in condition for op in ['=', '>', '<', '包含', '属于']):
                    result.add_issue(
                        ValidationSeverity.WARNING, 
                        "条件表达式建议包含明确的比较操作符",
                        f"将 '{condition}' 修改为包含 =, >, < 等操作符的表达式"
                    )
    
    def _validate_composite_syntax(self, text: str, result: ValidationResult):
        """验证组合语法"""
        # 检查是否包含子占位符
        sub_placeholders = re.findall(r'\{[^{}]+\}', text)
        if len(sub_placeholders) < 2:
            result.add_issue(
                ValidationSeverity.ERROR,
                "组合占位符应包含至少2个子占位符"
            )
    
    def _validate_parameters(self, params_str: str, result: ValidationResult):
        """验证参数格式"""
        params = params_str.split('|')
        
        for param in params:
            param = param.strip()
            if not param:
                continue
                
            if '=' not in param:
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"参数 '{param}' 缺少值",
                    f"将 '{param}' 修改为 '{param}=值'"
                )
            else:
                key, value = param.split('=', 1)
                if not value.strip():
                    result.add_issue(
                        ValidationSeverity.WARNING,
                        f"参数 '{key}' 的值为空"
                    )
    
    # 验证规则检查函数
    def _check_statistical_type(self, text: str) -> bool:
        """检查统计类型是否有效"""
        match = re.match(r'\{\{(\w+)：', text)
        if match:
            stat_type = match.group(1)
            return stat_type in self.statistical_types
        return False
    
    def _check_standard_type_names(self, text: str) -> bool:
        """检查是否使用标准类型名称"""
        return self._check_statistical_type(text)
    
    def _check_parameter_format(self, text: str) -> bool:
        """检查参数格式"""
        if '|' not in text:
            return True  # 没有参数时跳过检查
            
        params_match = re.search(r'\|([^}]+)', text)
        if params_match:
            params_str = params_match.group(1)
            params = params_str.split('|')
            
            for param in params:
                param = param.strip()
                if param and '=' not in param:
                    return False
        
        return True
    
    def _check_parameter_values(self, text: str) -> bool:
        """检查参数值不为空"""
        if '|' not in text:
            return True
            
        params_match = re.search(r'\|([^}]+)', text)
        if params_match:
            params_str = params_match.group(1)
            params = params_str.split('|')
            
            for param in params:
                if '=' in param:
                    _, value = param.split('=', 1)
                    if not value.strip():
                        return False
        
        return True
    
    def _check_standard_parameter_names(self, text: str) -> bool:
        """检查是否使用标准参数名称"""
        standard_params = {
            '时间范围', '部门', '条件', '分组', '排序', '数量', '类型', '对比期'
        }
        
        if '|' not in text:
            return True
            
        params_match = re.search(r'\|([^}]+)', text)
        if params_match:
            params_str = params_match.group(1)
            params = params_str.split('|')
            
            for param in params:
                if '=' in param:
                    key = param.split('=', 1)[0].strip()
                    if key not in standard_params:
                        return False
        
        return True
    
    def _check_condition_format(self, text: str) -> bool:
        """检查条件格式"""
        if '条件=' not in text:
            return True
            
        condition_match = re.search(r'条件=([^|}]+)', text)
        if condition_match:
            condition = condition_match.group(1)
            # 检查是否包含基本的比较操作
            operators = ['=', '>', '<', '!=', '包含', '属于', '开始于', '结束于']
            return any(op in condition for op in operators)
        
        return False
    
    def _check_fallback_logic(self, text: str) -> bool:
        """检查是否有回退逻辑"""
        if '条件=' not in text:
            return True
            
        fallback_indicators = ['否则=', '默认=', 'fallback=', 'else=']
        return any(indicator in text for indicator in fallback_indicators)
    
    def _check_composite_sub_placeholders(self, text: str) -> bool:
        """检查组合占位符的子占位符数量"""
        if '组合：' not in text:
            return True
            
        sub_placeholders = re.findall(r'\{[^{}]+\}', text)
        return len(sub_placeholders) >= 2
    
    def _check_composite_logic_clarity(self, text: str) -> bool:
        """检查组合逻辑清晰度"""
        if '组合：' not in text:
            return True
            
        logic_keywords = ['占', '比例', '差值', '增长', '总计', '平均', '对比']
        return any(keyword in text for keyword in logic_keywords)
    
    def _get_suggested_fix(self, rule_id: str, text: str) -> Optional[str]:
        """获取建议的修复方案"""
        fixes = {
            "R001": "确保占位符以{{开始，}}结束",
            "R002": "添加占位符内容，如 {{统计：销售总额}}",
            "R003": "添加冒号分隔符，如 {{统计：描述}}",
            "R101": f"使用有效的统计类型：{', '.join(self.statistical_types)}",
            "R201": "参数格式应为 键=值，如 |时间范围=2024-01",
            "R301": "条件格式应包含比较操作符，如 |条件=销售额>1000",
            "R401": "组合占位符应包含多个子占位符，如 {{组合：{统计：A}占{统计：B}比例}}"
        }
        
        return fixes.get(rule_id)
    
    def get_syntax_help(self, syntax_type: SyntaxType = None) -> str:
        """获取语法帮助信息"""
        if syntax_type is None:
            return """
占位符语法帮助：

基础格式：{{统计类型：描述}}
- 例如：{{统计：本月销售总额}}

参数化格式：{{统计类型：描述|参数=值}}
- 例如：{{统计：销售额|时间范围=2024-01|部门=华东区}}

组合格式：{{组合：组合逻辑}}
- 例如：{{组合：{统计：销售额}占{统计：目标}比例}}

条件格式：{{统计类型：描述|条件=条件表达式}}
- 例如：{{统计：高销售额|条件=销售额>10000}}

支持的统计类型：统计、趋势、极值、列表、统计图、对比、预测
"""
        
        help_texts = {
            SyntaxType.BASIC: "基础格式：{{统计类型：描述}}\n例如：{{统计：本月销售总额}}",
            SyntaxType.PARAMETERIZED: "参数化格式：{{统计类型：描述|参数=值}}\n例如：{{列表：销售排行|数量=10|排序=desc}}",
            SyntaxType.COMPOSITE: "组合格式：{{组合：组合逻辑}}\n例如：{{组合：{统计：实际}占{统计：目标}比例}}",
            SyntaxType.CONDITIONAL: "条件格式：{{统计类型：描述|条件=表达式}}\n例如：{{统计：高销售额|条件=销售额>10000}}"
        }
        
        return help_texts.get(syntax_type, "未知语法类型")