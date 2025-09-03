"""
占位符解析服务 - 工具调用接口

为AI工具提供占位符解析功能的统一接口
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def parse_placeholder_text(placeholder_text: str, context: Dict = None) -> Dict[str, Any]:
    """
    解析占位符文本 - 供AI工具调用
    
    Args:
        placeholder_text: 占位符文本
        context: 上下文信息
        
    Returns:
        解析结果字典
    """
    try:
        from .parsers.placeholder_parser import PlaceholderParser
        
        parser = PlaceholderParser()
        placeholder_spec = await parser.parse(placeholder_text)
        
        # 转换为工具友好的格式
        result = {
            "original_text": placeholder_text,
            "parsed_type": placeholder_spec.statistical_type.value,
            "description": placeholder_spec.description,
            "syntax_type": placeholder_spec.syntax_type.value,
            "confidence": placeholder_spec.confidence_score,
            "context_used": bool(context)
        }
        
        # 添加特定类型的额外信息
        if hasattr(placeholder_spec, 'parameters'):
            result["parameters"] = placeholder_spec.parameters
            
        if hasattr(placeholder_spec, 'conditions'):
            result["conditions"] = [
                {
                    "field": cond.field,
                    "operator": cond.operator,
                    "value": cond.value
                } for cond in placeholder_spec.conditions
            ]
            
        if hasattr(placeholder_spec, 'sub_placeholders'):
            result["sub_placeholders"] = [
                {
                    "type": sub.statistical_type.value,
                    "description": sub.description
                } for sub in placeholder_spec.sub_placeholders
            ]
        
        logger.info(f"占位符解析成功: {placeholder_text} -> {result['parsed_type']}")
        return result
        
    except Exception as e:
        logger.error(f"占位符解析失败: {placeholder_text}, 错误: {e}")
        raise ValueError(f"占位符解析失败: {str(e)}")