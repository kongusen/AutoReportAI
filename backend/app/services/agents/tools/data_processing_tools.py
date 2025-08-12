"""
数据处理工具集

提供数据验证、转换、清洗等功能的工具集合。
这些工具主要为DataQueryAgent和AnalysisAgent提供支持。

Features:
- 数据验证工具
- 数据转换工具
- 数据清洗工具
- 模式检测工具
- 元数据管理工具
"""

import re
import json
import pandas as pd
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from .base_tool import BaseTool, ToolMetadata, ToolCategory, ToolConfig, ToolResult


class DataValidationTool(BaseTool):
    """数据验证工具"""
    
    @classmethod
    def default_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            tool_id="data_validator",
            name="数据验证工具",
            description="验证数据格式、类型和完整性",
            version="1.0.0",
            category=ToolCategory.DATA_PROCESSING,
            tags=["validation", "data_quality", "schema"]
        )
    
    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> ToolResult:
        """执行数据验证"""
        try:
            validation_rules = context.get("validation_rules", {}) if context else {}
            
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "statistics": {}
            }
            
            # 基础数据类型检查
            data_type = type(input_data).__name__
            validation_results["statistics"]["data_type"] = data_type
            
            if isinstance(input_data, list):
                validation_results.update(await self._validate_list_data(input_data, validation_rules))
            elif isinstance(input_data, dict):
                validation_results.update(await self._validate_dict_data(input_data, validation_rules))
            else:
                validation_results.update(await self._validate_scalar_data(input_data, validation_rules))
            
            return ToolResult(
                success=True,
                data=validation_results
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"数据验证失败: {str(e)}"
            )
    
    async def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        return input_data is not None
    
    async def _validate_list_data(self, data: List, rules: Dict) -> Dict:
        """验证列表数据"""
        results = {"valid": True, "errors": [], "warnings": [], "statistics": {}}
        
        results["statistics"]["item_count"] = len(data)
        
        if not data:
            results["warnings"].append("数据列表为空")
            return results
        
        # 检查数据一致性
        if len(data) > 0:
            first_item_type = type(data[0])
            inconsistent_types = []
            
            for i, item in enumerate(data):
                if not isinstance(item, first_item_type):
                    inconsistent_types.append(f"第{i}项类型不一致: {type(item).__name__}")
            
            if inconsistent_types:
                results["errors"].extend(inconsistent_types)
                results["valid"] = False
            
            results["statistics"]["consistent_types"] = len(inconsistent_types) == 0
        
        # 如果是字典列表，检查字段一致性
        if data and isinstance(data[0], dict):
            results.update(await self._validate_dict_list(data, rules))
        
        return results
    
    async def _validate_dict_list(self, data: List[Dict], rules: Dict) -> Dict:
        """验证字典列表"""
        results = {"errors": [], "warnings": [], "statistics": {}}
        
        # 收集所有字段
        all_fields = set()
        for item in data:
            all_fields.update(item.keys())
        
        results["statistics"]["total_fields"] = len(all_fields)
        
        # 检查字段完整性
        field_presence = {}
        for field in all_fields:
            count = sum(1 for item in data if field in item and item[field] is not None)
            field_presence[field] = {
                "count": count,
                "percentage": count / len(data) * 100,
                "missing": len(data) - count
            }
        
        results["statistics"]["field_presence"] = field_presence
        
        # 检查必需字段
        required_fields = rules.get("required_fields", [])
        for field in required_fields:
            if field not in all_fields:
                results["errors"].append(f"缺少必需字段: {field}")
            elif field_presence[field]["percentage"] < 100:
                results["warnings"].append(f"必需字段 {field} 有缺失值")
        
        return results
    
    async def _validate_dict_data(self, data: Dict, rules: Dict) -> Dict:
        """验证字典数据"""
        results = {"valid": True, "errors": [], "warnings": [], "statistics": {}}
        
        results["statistics"]["field_count"] = len(data)
        
        # 检查必需字段
        required_fields = rules.get("required_fields", [])
        for field in required_fields:
            if field not in data:
                results["errors"].append(f"缺少必需字段: {field}")
                results["valid"] = False
            elif data[field] is None:
                results["warnings"].append(f"必需字段 {field} 为空")
        
        # 检查字段类型
        field_types = rules.get("field_types", {})
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    results["errors"].append(f"字段 {field} 类型错误: 期望 {expected_type.__name__}, 实际 {type(data[field]).__name__}")
                    results["valid"] = False
        
        return results
    
    async def _validate_scalar_data(self, data: Any, rules: Dict) -> Dict:
        """验证标量数据"""
        results = {"valid": True, "errors": [], "warnings": [], "statistics": {}}
        
        data_type = type(data).__name__
        results["statistics"]["data_type"] = data_type
        
        # 检查数据类型
        expected_type = rules.get("expected_type")
        if expected_type and not isinstance(data, expected_type):
            results["errors"].append(f"数据类型错误: 期望 {expected_type.__name__}, 实际 {data_type}")
            results["valid"] = False
        
        # 检查数值范围
        if isinstance(data, (int, float)):
            min_val = rules.get("min_value")
            max_val = rules.get("max_value")
            
            if min_val is not None and data < min_val:
                results["errors"].append(f"数值小于最小值: {data} < {min_val}")
                results["valid"] = False
            
            if max_val is not None and data > max_val:
                results["errors"].append(f"数值大于最大值: {data} > {max_val}")
                results["valid"] = False
        
        return results


class DataTransformTool(BaseTool):
    """数据转换工具"""
    
    @classmethod
    def default_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            tool_id="data_transformer",
            name="数据转换工具", 
            description="转换数据格式和结构",
            version="1.0.0",
            category=ToolCategory.DATA_PROCESSING,
            tags=["transformation", "format", "conversion"]
        )
    
    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> ToolResult:
        """执行数据转换"""
        try:
            transform_type = context.get("transform_type", "auto") if context else "auto"
            target_format = context.get("target_format", "dict") if context else "dict"
            
            transformed_data = await self._transform_data(input_data, transform_type, target_format)
            
            return ToolResult(
                success=True,
                data=transformed_data,
                metadata={
                    "original_type": type(input_data).__name__,
                    "transform_type": transform_type,
                    "target_format": target_format
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"数据转换失败: {str(e)}"
            )
    
    async def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        return input_data is not None
    
    async def _transform_data(self, data: Any, transform_type: str, target_format: str) -> Any:
        """执行具体的数据转换"""
        if transform_type == "normalize":
            return await self._normalize_data(data)
        elif transform_type == "flatten":
            return await self._flatten_data(data)
        elif transform_type == "aggregate":
            return await self._aggregate_data(data)
        elif transform_type == "format":
            return await self._format_data(data, target_format)
        else:
            # 自动转换
            return await self._auto_transform(data, target_format)
    
    async def _normalize_data(self, data: Any) -> Any:
        """标准化数据"""
        if isinstance(data, list):
            # 如果是字典列表，标准化字段名
            if data and isinstance(data[0], dict):
                normalized = []
                for item in data:
                    normalized_item = {}
                    for key, value in item.items():
                        # 标准化字段名：小写，下划线分隔
                        normalized_key = re.sub(r'[^a-zA-Z0-9_]', '_', key.lower())
                        normalized_key = re.sub(r'_+', '_', normalized_key).strip('_')
                        normalized_item[normalized_key] = value
                    normalized.append(normalized_item)
                return normalized
        
        return data
    
    async def _flatten_data(self, data: Any) -> Any:
        """扁平化数据"""
        if isinstance(data, dict):
            flattened = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    # 递归扁平化嵌套字典
                    for nested_key, nested_value in value.items():
                        flattened[f"{key}_{nested_key}"] = nested_value
                else:
                    flattened[key] = value
            return flattened
        
        return data
    
    async def _aggregate_data(self, data: List[Dict]) -> Dict:
        """聚合数据"""
        if not isinstance(data, list) or not data:
            return {}
        
        aggregated = {
            "count": len(data),
            "fields": {}
        }
        
        # 收集所有字段
        all_fields = set()
        for item in data:
            if isinstance(item, dict):
                all_fields.update(item.keys())
        
        # 对每个字段进行聚合
        for field in all_fields:
            values = [item.get(field) for item in data if isinstance(item, dict) and field in item]
            non_null_values = [v for v in values if v is not None]
            
            field_stats = {
                "count": len(values),
                "non_null_count": len(non_null_values),
                "null_count": len(values) - len(non_null_values)
            }
            
            if non_null_values:
                # 检查是否为数值类型
                numeric_values = []
                for v in non_null_values:
                    try:
                        numeric_values.append(float(v))
                    except (ValueError, TypeError):
                        break
                
                if len(numeric_values) == len(non_null_values):
                    # 数值字段统计
                    field_stats.update({
                        "sum": sum(numeric_values),
                        "avg": sum(numeric_values) / len(numeric_values),
                        "min": min(numeric_values),
                        "max": max(numeric_values)
                    })
                else:
                    # 分类字段统计
                    value_counts = {}
                    for v in non_null_values:
                        str_v = str(v)
                        value_counts[str_v] = value_counts.get(str_v, 0) + 1
                    
                    field_stats["value_counts"] = value_counts
                    field_stats["unique_values"] = len(value_counts)
            
            aggregated["fields"][field] = field_stats
        
        return aggregated
    
    async def _format_data(self, data: Any, target_format: str) -> Any:
        """格式化数据"""
        if target_format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        elif target_format == "csv":
            if isinstance(data, list) and data and isinstance(data[0], dict):
                # 转换为CSV格式的字符串
                import io
                import csv
                
                output = io.StringIO()
                if data:
                    fieldnames = data[0].keys()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                
                return output.getvalue()
        
        return data
    
    async def _auto_transform(self, data: Any, target_format: str) -> Any:
        """自动转换"""
        # 基于数据类型和目标格式自动选择转换方法
        if isinstance(data, str):
            try:
                # 尝试解析JSON
                parsed = json.loads(data)
                return await self._format_data(parsed, target_format)
            except json.JSONDecodeError:
                return data
        
        return await self._format_data(data, target_format)


class DataCleaningTool(BaseTool):
    """数据清洗工具"""
    
    @classmethod
    def default_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            tool_id="data_cleaner",
            name="数据清洗工具",
            description="清洗和预处理数据，处理缺失值和异常值",
            version="1.0.0",
            category=ToolCategory.DATA_PROCESSING,
            tags=["cleaning", "preprocessing", "quality"]
        )
    
    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> ToolResult:
        """执行数据清洗"""
        try:
            cleaning_options = context.get("cleaning_options", {}) if context else {}
            
            cleaned_data = await self._clean_data(input_data, cleaning_options)
            
            cleaning_report = {
                "original_size": self._get_data_size(input_data),
                "cleaned_size": self._get_data_size(cleaned_data),
                "operations_applied": []
            }
            
            return ToolResult(
                success=True,
                data=cleaned_data,
                metadata=cleaning_report
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"数据清洗失败: {str(e)}"
            )
    
    async def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        return input_data is not None
    
    async def _clean_data(self, data: Any, options: Dict) -> Any:
        """执行数据清洗"""
        if isinstance(data, list):
            return await self._clean_list_data(data, options)
        elif isinstance(data, dict):
            return await self._clean_dict_data(data, options)
        else:
            return await self._clean_scalar_data(data, options)
    
    async def _clean_list_data(self, data: List, options: Dict) -> List:
        """清洗列表数据"""
        cleaned = []
        
        for item in data:
            # 移除空值
            if options.get("remove_empty", True) and self._is_empty(item):
                continue
            
            # 清洗单个项目
            if isinstance(item, dict):
                cleaned_item = await self._clean_dict_data(item, options)
                if cleaned_item:  # 确保清洗后不为空
                    cleaned.append(cleaned_item)
            else:
                cleaned_item = await self._clean_scalar_data(item, options)
                if not self._is_empty(cleaned_item):
                    cleaned.append(cleaned_item)
        
        return cleaned
    
    async def _clean_dict_data(self, data: Dict, options: Dict) -> Dict:
        """清洗字典数据"""
        cleaned = {}
        
        for key, value in data.items():
            # 清洗键名
            clean_key = key.strip() if isinstance(key, str) else key
            
            # 处理值
            if self._is_empty(value) and options.get("remove_empty", True):
                continue
            
            # 清洗值
            if isinstance(value, str):
                cleaned_value = await self._clean_string(value, options)
            elif isinstance(value, (int, float)):
                cleaned_value = await self._clean_numeric(value, options)
            elif isinstance(value, dict):
                cleaned_value = await self._clean_dict_data(value, options)
            elif isinstance(value, list):
                cleaned_value = await self._clean_list_data(value, options)
            else:
                cleaned_value = value
            
            if not self._is_empty(cleaned_value):
                cleaned[clean_key] = cleaned_value
        
        return cleaned
    
    async def _clean_scalar_data(self, data: Any, options: Dict) -> Any:
        """清洗标量数据"""
        if isinstance(data, str):
            return await self._clean_string(data, options)
        elif isinstance(data, (int, float)):
            return await self._clean_numeric(data, options)
        else:
            return data
    
    async def _clean_string(self, text: str, options: Dict) -> str:
        """清洗字符串"""
        if not isinstance(text, str):
            return text
        
        # 去除前后空格
        text = text.strip()
        
        # 标准化空白字符
        if options.get("normalize_whitespace", True):
            text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符
        if options.get("remove_special_chars", False):
            text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        
        # 转换大小写
        case_option = options.get("case_conversion")
        if case_option == "lower":
            text = text.lower()
        elif case_option == "upper":
            text = text.upper()
        elif case_option == "title":
            text = text.title()
        
        return text
    
    async def _clean_numeric(self, value: Union[int, float], options: Dict) -> Union[int, float]:
        """清洗数值"""
        # 处理异常值
        min_val = options.get("min_value")
        max_val = options.get("max_value")
        
        if min_val is not None and value < min_val:
            return min_val if options.get("clip_outliers", False) else None
        
        if max_val is not None and value > max_val:
            return max_val if options.get("clip_outliers", False) else None
        
        return value
    
    def _is_empty(self, value: Any) -> bool:
        """检查值是否为空"""
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False
    
    def _get_data_size(self, data: Any) -> int:
        """获取数据大小"""
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict):
            return len(data)
        else:
            return 1


class SchemaDetectionTool(BaseTool):
    """模式检测工具"""
    
    @classmethod
    def default_metadata(cls) -> ToolMetadata:
        return ToolMetadata(
            tool_id="schema_detector",
            name="模式检测工具",
            description="自动检测数据结构和模式",
            version="1.0.0",
            category=ToolCategory.DATA_PROCESSING,
            tags=["schema", "structure", "detection"]
        )
    
    async def execute(self, input_data: Any, context: Dict[str, Any] = None) -> ToolResult:
        """执行模式检测"""
        try:
            schema = await self._detect_schema(input_data)
            
            return ToolResult(
                success=True,
                data=schema
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error_message=f"模式检测失败: {str(e)}"
            )
    
    async def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        return input_data is not None
    
    async def _detect_schema(self, data: Any) -> Dict:
        """检测数据模式"""
        schema = {
            "type": type(data).__name__,
            "structure": "unknown",
            "fields": {},
            "statistics": {}
        }
        
        if isinstance(data, list):
            schema.update(await self._detect_list_schema(data))
        elif isinstance(data, dict):
            schema.update(await self._detect_dict_schema(data))
        else:
            schema.update(await self._detect_scalar_schema(data))
        
        return schema
    
    async def _detect_list_schema(self, data: List) -> Dict:
        """检测列表模式"""
        schema = {
            "structure": "list",
            "statistics": {
                "length": len(data),
                "item_types": {}
            }
        }
        
        if not data:
            return schema
        
        # 分析项目类型
        type_counts = {}
        for item in data:
            item_type = type(item).__name__
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
        
        schema["statistics"]["item_types"] = type_counts
        
        # 如果是字典列表，分析字段结构
        if data and isinstance(data[0], dict):
            schema.update(await self._detect_dict_list_schema(data))
        
        return schema
    
    async def _detect_dict_list_schema(self, data: List[Dict]) -> Dict:
        """检测字典列表模式"""
        schema = {"fields": {}}
        
        # 收集所有字段信息
        field_info = {}
        
        for item in data:
            for field, value in item.items():
                if field not in field_info:
                    field_info[field] = {
                        "types": {},
                        "null_count": 0,
                        "total_count": 0,
                        "sample_values": []
                    }
                
                field_info[field]["total_count"] += 1
                
                if value is None:
                    field_info[field]["null_count"] += 1
                else:
                    value_type = type(value).__name__
                    field_info[field]["types"][value_type] = field_info[field]["types"].get(value_type, 0) + 1
                    
                    # 保存样例值
                    if len(field_info[field]["sample_values"]) < 3:
                        field_info[field]["sample_values"].append(value)
        
        # 生成字段模式
        for field, info in field_info.items():
            field_schema = {
                "required": info["null_count"] == 0,
                "nullable": info["null_count"] > 0,
                "presence_rate": (info["total_count"] - info["null_count"]) / len(data),
                "types": info["types"],
                "primary_type": max(info["types"].items(), key=lambda x: x[1])[0] if info["types"] else "unknown",
                "sample_values": info["sample_values"]
            }
            
            schema["fields"][field] = field_schema
        
        return schema
    
    async def _detect_dict_schema(self, data: Dict) -> Dict:
        """检测字典模式"""
        schema = {
            "structure": "dict",
            "fields": {},
            "statistics": {
                "field_count": len(data)
            }
        }
        
        for field, value in data.items():
            field_schema = {
                "type": type(value).__name__,
                "nullable": value is None,
                "sample_value": value
            }
            
            # 对嵌套结构递归检测
            if isinstance(value, (dict, list)):
                field_schema["nested_schema"] = await self._detect_schema(value)
            
            schema["fields"][field] = field_schema
        
        return schema
    
    async def _detect_scalar_schema(self, data: Any) -> Dict:
        """检测标量模式"""
        return {
            "structure": "scalar",
            "value_type": type(data).__name__,
            "sample_value": data
        }