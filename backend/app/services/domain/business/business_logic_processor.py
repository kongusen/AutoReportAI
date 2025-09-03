"""
业务逻辑处理器

负责处理业务规则和逻辑操作
"""

import logging
import json
from typing import Any, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RuleType(Enum):
    """业务规则类型"""
    VALIDATION = "validation"      # 数据验证规则
    TRANSFORMATION = "transformation"  # 数据转换规则
    CALCULATION = "calculation"    # 计算规则
    FORMATTING = "formatting"      # 格式化规则
    CONDITIONAL = "conditional"    # 条件规则
    AGGREGATION = "aggregation"   # 聚合规则


@dataclass
class BusinessRule:
    """业务规则"""
    rule_id: str
    rule_type: RuleType
    description: str
    condition: Optional[str] = None
    action: Optional[str] = None
    parameters: Dict[str, Any] = None


@dataclass  
class ProcessingResult:
    """处理结果"""
    processed_data: Any
    rules_applied: List[str]
    status: str
    execution_time: float
    warnings: List[str]


class BusinessLogicProcessor:
    """业务逻辑处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 内置业务规则
        self.built_in_rules = {
            "data_validation": BusinessRule(
                rule_id="data_validation",
                rule_type=RuleType.VALIDATION,
                description="基础数据验证",
                parameters={"required_fields": [], "data_types": {}}
            ),
            "number_formatting": BusinessRule(
                rule_id="number_formatting", 
                rule_type=RuleType.FORMATTING,
                description="数字格式化",
                parameters={"decimal_places": 2, "thousand_separator": ","}
            ),
            "currency_conversion": BusinessRule(
                rule_id="currency_conversion",
                rule_type=RuleType.TRANSFORMATION,
                description="货币转换",
                parameters={"from_currency": "CNY", "to_currency": "USD"}
            ),
            "percentage_calculation": BusinessRule(
                rule_id="percentage_calculation",
                rule_type=RuleType.CALCULATION,
                description="百分比计算",
                parameters={"base_field": "total", "target_field": "amount"}
            )
        }
    
    async def process(self, data: Any, rules: List[str] = None) -> Dict[str, Any]:
        """
        处理业务逻辑
        
        Args:
            data: 待处理的数据
            rules: 要应用的规则列表
            
        Returns:
            处理结果字典
        """
        import time
        start_time = time.time()
        
        try:
            self.logger.info(f"开始业务逻辑处理，规则数量: {len(rules) if rules else 0}")
            
            processed_data = data
            applied_rules = []
            warnings = []
            
            # 如果没有指定规则，应用默认规则
            if not rules:
                rules = ["data_validation", "number_formatting"]
            
            # 逐个应用规则
            for rule_name in rules:
                try:
                    processed_data, rule_warnings = await self._apply_rule(
                        processed_data, rule_name
                    )
                    applied_rules.append(rule_name)
                    warnings.extend(rule_warnings)
                    
                except Exception as e:
                    self.logger.warning(f"规则 {rule_name} 应用失败: {e}")
                    warnings.append(f"规则 {rule_name} 应用失败: {str(e)}")
            
            execution_time = time.time() - start_time
            
            result = {
                "processed_data": processed_data,
                "rules_applied": applied_rules,
                "status": "success" if applied_rules else "partial",
                "execution_time": execution_time,
                "warnings": warnings,
                "metadata": {
                    "original_data_type": type(data).__name__,
                    "processed_data_type": type(processed_data).__name__,
                    "rules_requested": len(rules) if rules else 0,
                    "rules_successful": len(applied_rules)
                }
            }
            
            self.logger.info(f"业务逻辑处理完成，应用规则: {applied_rules}")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"业务逻辑处理失败: {e}")
            
            return {
                "processed_data": data,  # 返回原始数据
                "rules_applied": [],
                "status": "error",
                "execution_time": execution_time,
                "warnings": [f"处理失败: {str(e)}"],
                "error": str(e)
            }
    
    async def _apply_rule(self, data: Any, rule_name: str) -> tuple[Any, List[str]]:
        """应用单个业务规则"""
        warnings = []
        
        if rule_name not in self.built_in_rules:
            # 尝试解析为动态规则
            return await self._apply_dynamic_rule(data, rule_name)
        
        rule = self.built_in_rules[rule_name]
        
        if rule.rule_type == RuleType.VALIDATION:
            return await self._apply_validation_rule(data, rule, warnings)
        elif rule.rule_type == RuleType.FORMATTING:
            return await self._apply_formatting_rule(data, rule, warnings)
        elif rule.rule_type == RuleType.TRANSFORMATION:
            return await self._apply_transformation_rule(data, rule, warnings)
        elif rule.rule_type == RuleType.CALCULATION:
            return await self._apply_calculation_rule(data, rule, warnings)
        else:
            warnings.append(f"不支持的规则类型: {rule.rule_type}")
            return data, warnings
    
    async def _apply_validation_rule(
        self, 
        data: Any, 
        rule: BusinessRule, 
        warnings: List[str]
    ) -> tuple[Any, List[str]]:
        """应用验证规则"""
        if isinstance(data, dict):
            # 验证必需字段
            required_fields = rule.parameters.get("required_fields", [])
            for field in required_fields:
                if field not in data:
                    warnings.append(f"缺少必需字段: {field}")
            
            # 验证数据类型
            data_types = rule.parameters.get("data_types", {})
            for field, expected_type in data_types.items():
                if field in data:
                    actual_type = type(data[field]).__name__
                    if actual_type != expected_type:
                        warnings.append(f"字段 {field} 类型不匹配: 期望 {expected_type}, 实际 {actual_type}")
        
        elif isinstance(data, list):
            # 验证列表中的每个项目
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    item_data, item_warnings = await self._apply_validation_rule(item, rule, [])
                    warnings.extend([f"项目{i}: {w}" for w in item_warnings])
        
        return data, warnings
    
    async def _apply_formatting_rule(
        self, 
        data: Any, 
        rule: BusinessRule, 
        warnings: List[str]
    ) -> tuple[Any, List[str]]:
        """应用格式化规则"""
        if rule.rule_id == "number_formatting":
            decimal_places = rule.parameters.get("decimal_places", 2)
            thousand_separator = rule.parameters.get("thousand_separator", ",")
            
            formatted_data = self._format_numbers(data, decimal_places, thousand_separator)
            return formatted_data, warnings
        
        return data, warnings
    
    async def _apply_transformation_rule(
        self, 
        data: Any, 
        rule: BusinessRule, 
        warnings: List[str]
    ) -> tuple[Any, List[str]]:
        """应用转换规则"""
        if rule.rule_id == "currency_conversion":
            # 模拟货币转换
            from_currency = rule.parameters.get("from_currency", "CNY")
            to_currency = rule.parameters.get("to_currency", "USD")
            
            # 简单的转换率（实际应该从汇率API获取）
            conversion_rates = {
                ("CNY", "USD"): 0.14,
                ("USD", "CNY"): 7.1,
                ("CNY", "EUR"): 0.13,
                ("EUR", "CNY"): 7.7
            }
            
            rate = conversion_rates.get((from_currency, to_currency), 1.0)
            converted_data = self._apply_currency_conversion(data, rate)
            
            if rate != 1.0:
                warnings.append(f"应用汇率转换: {from_currency} -> {to_currency} (率: {rate})")
            
            return converted_data, warnings
        
        return data, warnings
    
    async def _apply_calculation_rule(
        self, 
        data: Any, 
        rule: BusinessRule, 
        warnings: List[str]
    ) -> tuple[Any, List[str]]:
        """应用计算规则"""
        if rule.rule_id == "percentage_calculation":
            base_field = rule.parameters.get("base_field", "total")
            target_field = rule.parameters.get("target_field", "amount")
            
            calculated_data = self._calculate_percentages(data, base_field, target_field)
            return calculated_data, warnings
        
        return data, warnings
    
    async def _apply_dynamic_rule(self, data: Any, rule_expression: str) -> tuple[Any, List[str]]:
        """应用动态规则（基于表达式）"""
        warnings = []
        
        try:
            # 解析规则表达式（简化版本）
            if ":" in rule_expression:
                rule_type, rule_action = rule_expression.split(":", 1)
                
                if rule_type == "filter" and isinstance(data, list):
                    # 过滤规则: filter:field=value
                    if "=" in rule_action:
                        field, value = rule_action.split("=", 1)
                        filtered_data = [
                            item for item in data 
                            if isinstance(item, dict) and str(item.get(field)) == value
                        ]
                        return filtered_data, warnings
                
                elif rule_type == "sort" and isinstance(data, list):
                    # 排序规则: sort:field
                    field = rule_action.strip()
                    try:
                        sorted_data = sorted(
                            data,
                            key=lambda x: x.get(field, 0) if isinstance(x, dict) else 0
                        )
                        return sorted_data, warnings
                    except Exception as e:
                        warnings.append(f"排序失败: {e}")
        
        except Exception as e:
            warnings.append(f"动态规则解析失败: {e}")
        
        return data, warnings
    
    def _format_numbers(self, data: Any, decimal_places: int, thousand_separator: str) -> Any:
        """格式化数字"""
        if isinstance(data, (int, float)):
            return f"{data:,.{decimal_places}f}".replace(",", thousand_separator)
        
        elif isinstance(data, dict):
            return {
                k: self._format_numbers(v, decimal_places, thousand_separator)
                for k, v in data.items()
            }
        
        elif isinstance(data, list):
            return [
                self._format_numbers(item, decimal_places, thousand_separator)
                for item in data
            ]
        
        return data
    
    def _apply_currency_conversion(self, data: Any, rate: float) -> Any:
        """应用货币转换"""
        if isinstance(data, (int, float)):
            return data * rate
        
        elif isinstance(data, dict):
            # 只转换看起来像金额的字段
            currency_fields = ['amount', 'total', 'price', 'cost', 'revenue', 'profit']
            return {
                k: (v * rate if k.lower() in currency_fields and isinstance(v, (int, float)) else v)
                for k, v in data.items()
            }
        
        elif isinstance(data, list):
            return [self._apply_currency_conversion(item, rate) for item in data]
        
        return data
    
    def _calculate_percentages(self, data: Any, base_field: str, target_field: str) -> Any:
        """计算百分比"""
        if isinstance(data, dict):
            base_value = data.get(base_field)
            target_value = data.get(target_field)
            
            if isinstance(base_value, (int, float)) and isinstance(target_value, (int, float)) and base_value != 0:
                percentage = (target_value / base_value) * 100
                result = data.copy()
                result[f"{target_field}_percentage"] = round(percentage, 2)
                return result
        
        elif isinstance(data, list):
            return [self._calculate_percentages(item, base_field, target_field) for item in data]
        
        return data


# 全局实例
business_logic_processor = BusinessLogicProcessor()