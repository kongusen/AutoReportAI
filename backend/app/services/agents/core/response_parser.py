"""
统一的响应解析器
提供标准化的AI响应解析功能，支持多种格式和错误处理
"""

import json
import logging
from typing import Dict, Any, Optional, Union, List
from abc import ABC, abstractmethod


class ResponseParserInterface(ABC):
    """响应解析器接口"""
    
    @abstractmethod
    def parse(self, response: str) -> Dict[str, Any]:
        """解析响应"""
        pass
    
    @abstractmethod
    def validate(self, response: str) -> bool:
        """验证响应格式"""
        pass


class JSONResponseParser(ResponseParserInterface):
    """JSON响应解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, response: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            if isinstance(response, dict):
                return response
            
            if isinstance(response, str):
                # 尝试提取JSON部分
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start != -1 and json_end != 0:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
                else:
                    # 如果没有找到JSON，返回文本响应
                    return {"text_response": response, "insights": [response]}
            
            return {"error": "不支持的响应格式"}
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            return {"error": f"JSON解析失败: {str(e)}", "raw_response": response}
        except Exception as e:
            self.logger.error(f"响应解析失败: {e}")
            return {"error": f"解析失败: {str(e)}", "raw_response": response}
    
    def validate(self, response: str) -> bool:
        """验证JSON响应格式"""
        try:
            if isinstance(response, dict):
                return True
            
            if isinstance(response, str):
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start != -1 and json_end != 0:
                    json_str = response[json_start:json_end]
                    json.loads(json_str)  # 测试解析
                    return True
            
            return False
            
        except Exception:
            return False


class AnalysisResponseParser(JSONResponseParser):
    """分析响应解析器 - 专门用于分析任务"""
    
    def parse_analysis_response(self, response: str, analysis_type: str) -> Dict[str, Any]:
        """解析分析响应"""
        base_result = self.parse(response)
        
        if "error" in base_result:
            return self._get_error_result(base_result["error"], analysis_type)
        
        # 根据分析类型标准化结果
        if analysis_type == "relationship":
            return self._standardize_relationship_result(base_result)
        elif analysis_type == "semantic":
            return self._standardize_semantic_result(base_result)
        elif analysis_type == "quality":
            return self._standardize_quality_result(base_result)
        else:
            return base_result
    
    def _standardize_relationship_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化关系分析结果"""
        return {
            "relationships": result.get("relationships", []),
            "insights": result.get("insights", []),
            "confidence_scores": result.get("confidence_scores", {}),
            "recommendations": result.get("recommendations", [])
        }
    
    def _standardize_semantic_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化语义分析结果"""
        return {
            "business_categories": result.get("business_categories", {}),
            "semantic_patterns": result.get("semantic_patterns", {}),
            "data_entities": result.get("data_entities", []),
            "domain_insights": result.get("domain_insights", []),
            "naming_conventions": result.get("naming_conventions", {})
        }
    
    def _standardize_quality_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化质量分析结果"""
        return {
            "overall_score": result.get("overall_score", 0.0),
            "table_quality": result.get("table_quality", []),
            "recommendations": result.get("recommendations", []),
            "quality_insights": result.get("quality_insights", []),
            "best_practices": result.get("best_practices", [])
        }
    
    def _get_error_result(self, error_message: str, analysis_type: str) -> Dict[str, Any]:
        """获取错误结果"""
        base_error = {
            "error": error_message,
            "success": False,
            "insights": [f"分析失败: {error_message}"]
        }
        
        if analysis_type == "relationship":
            base_error.update({
                "relationships": [],
                "confidence_scores": {},
                "recommendations": []
            })
        elif analysis_type == "semantic":
            base_error.update({
                "business_categories": {},
                "semantic_patterns": {},
                "data_entities": [],
                "domain_insights": [f"分析失败: {error_message}"]
            })
        elif analysis_type == "quality":
            base_error.update({
                "overall_score": 0.0,
                "table_quality": [],
                "recommendations": [f"分析失败: {error_message}"],
                "quality_insights": [],
                "best_practices": []
            })
        
        return base_error


class ResponseParserFactory:
    """响应解析器工厂"""
    
    _parsers = {
        "json": JSONResponseParser,
        "analysis": AnalysisResponseParser
    }
    
    @classmethod
    def get_parser(cls, parser_type: str = "json") -> ResponseParserInterface:
        """获取解析器实例"""
        parser_class = cls._parsers.get(parser_type, JSONResponseParser)
        return parser_class()
    
    @classmethod
    def register_parser(cls, parser_type: str, parser_class: type):
        """注册新的解析器"""
        cls._parsers[parser_type] = parser_class


# 全局解析器实例
_analysis_parser = None


def get_analysis_parser() -> AnalysisResponseParser:
    """获取分析解析器实例（单例模式）"""
    global _analysis_parser
    if _analysis_parser is None:
        _analysis_parser = AnalysisResponseParser()
    return _analysis_parser
