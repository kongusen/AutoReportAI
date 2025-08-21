"""
Enhanced Response Parser for AI Agent Outputs

智能响应解析器，支持：
1. 结构化JSON响应解析  
2. 占位符分析结果验证
3. 响应质量评估
4. 错误处理和修复建议
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ResponseQuality(Enum):
    """响应质量等级"""
    EXCELLENT = "excellent"     # 完整、准确、高置信度
    GOOD = "good"              # 基本完整、可用
    ACCEPTABLE = "acceptable"   # 部分可用，需要补充
    POOR = "poor"              # 质量差，难以使用
    INVALID = "invalid"        # 无效响应


@dataclass
class ResponseValidation:
    """响应验证结果"""
    is_valid: bool
    quality: ResponseQuality
    confidence_score: float
    missing_fields: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    parsed_data: Optional[Dict[str, Any]] = None


class PlaceholderAnalysisParser:
    """占位符分析响应解析器"""
    
    # 必需字段定义
    REQUIRED_FIELDS = {
        'semantic_analysis': {
            'business_meaning': str,
            'data_intent': str,
            'complexity_level': str
        },
        'data_mapping': {
            'recommended_sources': list,
            'required_fields': list
        },
        'sql_logic': {
            'query_template': str,
            'explanation': str
        },
        'confidence_metrics': {
            'overall_confidence': (int, float)
        }
    }
    
    # 可选字段定义
    OPTIONAL_FIELDS = {
        'semantic_analysis': ['keywords'],
        'data_mapping': ['relationships'],
        'sql_logic': ['parameters', 'complexity_score'],
        'performance_considerations': ['estimated_cost', 'optimization_suggestions'],
        'data_processing': ['aggregation_type', 'formatting'],
        'confidence_metrics': ['semantic_confidence', 'mapping_confidence', 'sql_confidence']
    }
    
    @classmethod
    def parse_response(cls, raw_response: str) -> ResponseValidation:
        """解析AI响应并验证结构"""
        try:
            # 清理响应文本
            cleaned_response = cls._clean_response(raw_response)
            
            # 解析JSON
            parsed_data = json.loads(cleaned_response)
            
            # 验证结构
            validation = cls._validate_structure(parsed_data)
            validation.parsed_data = parsed_data
            
            # 评估质量
            validation.quality = cls._assess_quality(validation, parsed_data)
            
            return validation
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
            return cls._handle_json_error(raw_response, str(e))
        except Exception as e:
            logger.error(f"响应解析异常: {e}")
            return ResponseValidation(
                is_valid=False,
                quality=ResponseQuality.INVALID,
                confidence_score=0.0,
                validation_errors=[f"解析异常: {str(e)}"]
            )
    
    @classmethod
    def _clean_response(cls, raw_response: str) -> str:
        """清理响应文本，提取JSON部分"""
        # 移除markdown代码块
        cleaned = re.sub(r'```json\s*', '', raw_response)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        
        # 移除前后的解释文字
        lines = cleaned.split('\n')
        json_start = -1
        json_end = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                json_start = i
                break
        
        for i in range(len(lines) - 1, -1, -1):
            if line.strip().endswith('}'):
                json_end = i + 1
                break
        
        if json_start >= 0 and json_end > json_start:
            return '\n'.join(lines[json_start:json_end])
        
        return cleaned.strip()
    
    @classmethod
    def _validate_structure(cls, data: Dict[str, Any]) -> ResponseValidation:
        """验证响应结构完整性"""
        is_valid = True
        missing_fields = []
        validation_errors = []
        confidence_scores = []
        
        # 检查必需字段
        for section, fields in cls.REQUIRED_FIELDS.items():
            if section not in data:
                missing_fields.append(section)
                is_valid = False
                continue
            
            section_data = data[section]
            if not isinstance(section_data, dict):
                validation_errors.append(f"'{section}' 应该是对象类型")
                is_valid = False
                continue
            
            for field_name, field_type in fields.items():
                if field_name not in section_data:
                    missing_fields.append(f"{section}.{field_name}")
                    continue
                
                field_value = section_data[field_name]
                if not isinstance(field_value, field_type):
                    validation_errors.append(
                        f"'{section}.{field_name}' 类型错误，期望 {field_type.__name__}"
                    )
        
        # 提取置信度分数
        if 'confidence_metrics' in data:
            metrics = data['confidence_metrics']
            if 'overall_confidence' in metrics:
                confidence_scores.append(metrics['overall_confidence'])
            
            # 收集其他置信度分数
            for conf_field in ['semantic_confidence', 'mapping_confidence', 'sql_confidence']:
                if conf_field in metrics:
                    confidence_scores.append(metrics[conf_field])
        
        # 计算平均置信度
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return ResponseValidation(
            is_valid=is_valid,
            quality=ResponseQuality.GOOD,  # 临时设置，后续会重新评估
            confidence_score=avg_confidence,
            missing_fields=missing_fields,
            validation_errors=validation_errors
        )
    
    @classmethod
    def _assess_quality(cls, validation: ResponseValidation, data: Dict[str, Any]) -> ResponseQuality:
        """评估响应质量"""
        if not validation.is_valid:
            return ResponseQuality.INVALID
        
        # 质量评分因子
        completeness_score = 1.0 - (len(validation.missing_fields) / 10)  # 完整性
        confidence_score = validation.confidence_score  # 置信度
        
        # SQL质量评估
        sql_quality_score = 0.5
        if 'sql_logic' in data:
            sql_logic = data['sql_logic']
            if 'query_template' in sql_logic:
                query = sql_logic['query_template']
                # 简单的SQL质量检查
                if any(keyword in query.upper() for keyword in ['SELECT', 'FROM', 'WHERE']):
                    sql_quality_score = 0.8
                if 'JOIN' in query.upper():
                    sql_quality_score = 0.9
                if any(func in query.upper() for func in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']):
                    sql_quality_score = 1.0
        
        # 综合评分
        overall_score = (completeness_score * 0.4 + confidence_score * 0.4 + sql_quality_score * 0.2)
        
        if overall_score >= 0.9:
            return ResponseQuality.EXCELLENT
        elif overall_score >= 0.7:
            return ResponseQuality.GOOD
        elif overall_score >= 0.5:
            return ResponseQuality.ACCEPTABLE
        else:
            return ResponseQuality.POOR
    
    @classmethod
    def _handle_json_error(cls, raw_response: str, error_message: str) -> ResponseValidation:
        """处理JSON解析错误"""
        suggestions = []
        
        # 尝试修复常见的JSON错误
        if "Expecting ',' delimiter" in error_message:
            suggestions.append("检查JSON对象中是否缺少逗号分隔符")
        elif "Expecting property name enclosed in double quotes" in error_message:
            suggestions.append("确保所有属性名都用双引号包围")
        elif "Unterminated string" in error_message:
            suggestions.append("检查字符串是否正确闭合")
        
        # 尝试提取部分有用信息
        partial_data = cls._extract_partial_json(raw_response)
        
        return ResponseValidation(
            is_valid=False,
            quality=ResponseQuality.INVALID,
            confidence_score=0.0,
            validation_errors=[f"JSON格式错误: {error_message}"],
            suggestions=suggestions,
            parsed_data=partial_data
        )
    
    @classmethod
    def _extract_partial_json(cls, raw_response: str) -> Optional[Dict[str, Any]]:
        """尝试从损坏的响应中提取部分数据"""
        try:
            # 使用正则表达式提取关键信息
            partial_data = {}
            
            # 提取business_meaning
            meaning_match = re.search(r'"business_meaning"\s*:\s*"([^"]+)"', raw_response)
            if meaning_match:
                partial_data['business_meaning'] = meaning_match.group(1)
            
            # 提取query_template
            query_match = re.search(r'"query_template"\s*:\s*"([^"]+)"', raw_response)
            if query_match:
                partial_data['query_template'] = query_match.group(1)
            
            # 提取overall_confidence
            conf_match = re.search(r'"overall_confidence"\s*:\s*([0-9.]+)', raw_response)
            if conf_match:
                partial_data['overall_confidence'] = float(conf_match.group(1))
            
            return partial_data if partial_data else None
            
        except Exception:
            return None


class ResponseEnhancer:
    """响应增强器 - 用于改善不完整的响应"""
    
    @classmethod
    def enhance_response(cls, validation: ResponseValidation, 
                        original_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """增强不完整的响应"""
        if not validation.parsed_data:
            return cls._create_fallback_response(original_context)
        
        enhanced_data = validation.parsed_data.copy()
        
        # 填充缺失的必需字段
        for missing_field in validation.missing_fields:
            cls._add_missing_field(enhanced_data, missing_field, original_context)
        
        # 增强置信度信息
        if 'confidence_metrics' not in enhanced_data:
            enhanced_data['confidence_metrics'] = {
                'overall_confidence': 0.5,
                'reliability_factors': ['系统自动补充的数据']
            }
        
        return enhanced_data
    
    @classmethod
    def _add_missing_field(cls, data: Dict[str, Any], field_path: str, 
                          context: Dict[str, Any] = None):
        """添加缺失的字段"""
        parts = field_path.split('.')
        
        if len(parts) == 1:
            # 顶级字段
            section = parts[0]
            if section == 'semantic_analysis':
                data[section] = {
                    'business_meaning': '需要进一步分析的占位符',
                    'data_intent': '数据查询需求',
                    'complexity_level': 'medium'
                }
        elif len(parts) == 2:
            # 二级字段
            section, field = parts
            if section not in data:
                data[section] = {}
            
            # 根据字段类型提供默认值
            default_values = {
                'business_meaning': '待分析的业务含义',
                'data_intent': '数据查询意图',
                'complexity_level': 'medium',
                'query_template': 'SELECT * FROM table_name WHERE condition',
                'explanation': '查询逻辑说明',
                'overall_confidence': 0.5,
                'recommended_sources': [],
                'required_fields': []
            }
            
            data[section][field] = default_values.get(field, '待补充')
    
    @classmethod
    def _create_fallback_response(cls, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建兜底响应"""
        placeholder_text = context.get('placeholder_text', '未知占位符') if context else '未知占位符'
        
        return {
            'semantic_analysis': {
                'business_meaning': f'占位符 "{placeholder_text}" 的业务含义需要进一步分析',
                'data_intent': '数据查询需求',
                'complexity_level': 'medium',
                'keywords': []
            },
            'data_mapping': {
                'recommended_sources': [],
                'required_fields': []
            },
            'sql_logic': {
                'query_template': 'SELECT placeholder_value FROM data_table',
                'explanation': '基础查询模板，需要根据具体需求调整',
                'parameters': {}
            },
            'confidence_metrics': {
                'overall_confidence': 0.3,
                'reliability_factors': ['系统兜底响应', '需要人工审核']
            }
        }


def parse_placeholder_analysis_response(raw_response: str, 
                                       context: Dict[str, Any] = None) -> Tuple[Dict[str, Any], ResponseValidation]:
    """
    解析占位符分析响应的便捷函数
    
    Returns:
        Tuple[解析后的数据, 验证结果]
    """
    validation = PlaceholderAnalysisParser.parse_response(raw_response)
    
    if validation.quality in [ResponseQuality.POOR, ResponseQuality.INVALID]:
        # 对质量差的响应进行增强
        enhanced_data = ResponseEnhancer.enhance_response(validation, context)
        return enhanced_data, validation
    
    return validation.parsed_data, validation