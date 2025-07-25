"""
批量占位符处理器
优化AI调用效率，将多个占位符合并为单次LLM调用
"""

import asyncio
from typing import List, Dict, Any
from dataclasses import dataclass
import json

from .processor import PlaceholderMatch, PlaceholderProcessor
from ..ai_integration.ai_service_enhanced import AIService


@dataclass
class BatchProcessingResult:
    """批量处理结果"""
    processed_placeholders: Dict[str, Any]
    total_processing_time: float
    llm_calls_saved: int
    success_count: int
    error_count: int


class BatchPlaceholderProcessor:
    """批量占位符处理器"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.base_processor = PlaceholderProcessor()
        
    async def process_placeholders_batch(
        self, 
        placeholders: List[PlaceholderMatch],
        data_source_id: str,
        max_batch_size: int = 10
    ) -> BatchProcessingResult:
        """
        批量处理占位符
        
        Args:
            placeholders: 占位符列表
            data_source_id: 数据源ID
            max_batch_size: 最大批次大小
            
        Returns:
            批量处理结果
        """
        start_time = asyncio.get_event_loop().time()
        
        # 按类型分组占位符
        grouped_placeholders = self._group_placeholders_by_type(placeholders)
        
        processed_results = {}
        success_count = 0
        error_count = 0
        total_llm_calls = 0
        
        # 按类型批量处理
        for placeholder_type, type_placeholders in grouped_placeholders.items():
            try:
                batch_result = await self._process_type_batch(
                    placeholder_type, 
                    type_placeholders, 
                    data_source_id,
                    max_batch_size
                )
                
                processed_results.update(batch_result['results'])
                success_count += batch_result['success_count']
                error_count += batch_result['error_count']
                total_llm_calls += batch_result['llm_calls']
                
            except Exception as e:
                error_count += len(type_placeholders)
                # 记录错误但继续处理其他类型
                
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        # 计算节省的LLM调用次数
        original_calls = len(placeholders)
        calls_saved = original_calls - total_llm_calls
        
        return BatchProcessingResult(
            processed_placeholders=processed_results,
            total_processing_time=processing_time,
            llm_calls_saved=calls_saved,
            success_count=success_count,
            error_count=error_count
        )
    
    def _group_placeholders_by_type(
        self, 
        placeholders: List[PlaceholderMatch]
    ) -> Dict[str, List[PlaceholderMatch]]:
        """按类型分组占位符"""
        groups = {}
        for placeholder in placeholders:
            type_name = placeholder.type.value
            if type_name not in groups:
                groups[type_name] = []
            groups[type_name].append(placeholder)
        return groups
    
    async def _process_type_batch(
        self,
        placeholder_type: str,
        placeholders: List[PlaceholderMatch],
        data_source_id: str,
        max_batch_size: int
    ) -> Dict[str, Any]:
        """处理同类型占位符批次"""
        
        results = {}
        success_count = 0
        error_count = 0
        llm_calls = 0
        
        # 将占位符分割为批次
        for i in range(0, len(placeholders), max_batch_size):
            batch = placeholders[i:i + max_batch_size]
            
            try:
                # 构建批量提示词
                batch_prompt = self._build_batch_prompt(placeholder_type, batch)
                
                # 单次LLM调用处理整个批次
                batch_response = await self.ai_service.call_llm_with_retry(
                    prompt=batch_prompt,
                    response_format="json"
                )
                
                llm_calls += 1
                
                # 解析批量响应
                batch_results = self._parse_batch_response(batch_response, batch)
                
                results.update(batch_results)
                success_count += len(batch_results)
                
            except Exception as e:
                error_count += len(batch)
                # 为失败的占位符设置默认值
                for placeholder in batch:
                    results[placeholder.full_match] = {
                        "error": str(e),
                        "fallback_value": f"[{placeholder.description}]"
                    }
        
        return {
            "results": results,
            "success_count": success_count,
            "error_count": error_count,
            "llm_calls": llm_calls
        }
    
    def _build_batch_prompt(
        self, 
        placeholder_type: str, 
        placeholders: List[PlaceholderMatch]
    ) -> str:
        """构建批量处理提示词"""
        
        prompt = f"""
你是一个智能数据分析助手。请批量分析以下{placeholder_type}类型的占位符，为每个占位符提供处理建议。

占位符信息：
"""
        
        for i, placeholder in enumerate(placeholders, 1):
            prompt += f"""
{i}. 占位符: {placeholder.full_match}
   描述: {placeholder.description}
   上下文: {placeholder.context_before[:100]}...{placeholder.context_after[:100]}
"""
        
        prompt += f"""
请为每个占位符返回JSON格式的分析结果，包含：
- field_suggestions: 推荐的数据字段列表
- calculation_type: 计算类型(sum/count/avg/max/min)
- requires_grouping: 是否需要分组
- time_filter_needed: 是否需要时间过滤
- confidence: 分析置信度(0-1)

返回格式:
{{
  "placeholder_1": {{...}},
  "placeholder_2": {{...}},
  ...
}}
"""
        
        return prompt
    
    def _parse_batch_response(
        self, 
        response: str, 
        placeholders: List[PlaceholderMatch]
    ) -> Dict[str, Any]:
        """解析批量响应"""
        
        try:
            parsed_response = json.loads(response)
            results = {}
            
            for i, placeholder in enumerate(placeholders, 1):
                key = f"placeholder_{i}"
                if key in parsed_response:
                    results[placeholder.full_match] = parsed_response[key]
                else:
                    # 设置默认值
                    results[placeholder.full_match] = {
                        "field_suggestions": [placeholder.description],
                        "calculation_type": "count",
                        "confidence": 0.5
                    }
            
            return results
            
        except json.JSONDecodeError:
            # JSON解析失败，返回默认值
            results = {}
            for placeholder in placeholders:
                results[placeholder.full_match] = {
                    "field_suggestions": [placeholder.description],
                    "calculation_type": "count", 
                    "confidence": 0.3,
                    "error": "Failed to parse LLM response"
                }
            return results


# 创建全局实例
def create_batch_processor(ai_service: AIService) -> BatchPlaceholderProcessor:
    """创建批量处理器实例"""
    return BatchPlaceholderProcessor(ai_service)