"""
增强的AI服务

实现LLM与ETL工具的深度集成，提供智能ETL规划和优化功能。
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from ..core.config import settings
from .ai_integration import AIService
from .intelligent_placeholder.etl_planner import IntelligentETLPlanner
from .data_processing.etl.intelligent_etl_executor import (
    ETLInstructions,
    AggregationConfig,
    TimeFilterConfig,
    RegionFilterConfig
)
from ..schemas.placeholder_mapping import PlaceholderMatch, PlaceholderType
from ..models.data_source import DataSource
from ..crud.crud_data_source import crud_data_source
from ..db.session import get_db_session

logger = logging.getLogger(__name__)


class EnhancedAIService:
    """增强的AI服务"""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.ai_service = AIService(db) if db else None
        self.etl_planner = IntelligentETLPlanner()
        
    async def generate_etl_plan_with_llm(self, template_text: str, 
                                       data_source_id: int,
                                       placeholders: List[PlaceholderMatch] = None) -> List[ETLInstructions]:
        """
        使用LLM生成更智能的ETL计划
        
        Args:
            template_text: 模板文本
            data_source_id: 数据源ID
            placeholders: 已解析的占位符列表
            
        Returns:
            ETL指令列表
        """
        try:
            # 获取数据源信息
            with get_db_session() as db:
                data_source = crud_data_source.get(db, id=data_source_id)
                if not data_source:
                    raise ValueError(f"数据源 {data_source_id} 不存在")
                
                # 获取数据源详细信息
                data_source_info = await self._get_data_source_info(data_source)
            
            # 1. 让LLM分析模板和数据源，生成ETL需求
            llm_prompt = self._build_etl_analysis_prompt(
                template_text, data_source_info, placeholders
            )
            
            # 2. 调用LLM获取分析结果
            llm_response = await self._call_llm(llm_prompt)
            logger.info(f"LLM ETL分析完成")
            
            # 3. 将LLM的分析结果转换为ETL指令
            etl_instructions = await self._parse_llm_etl_plan(llm_response, data_source)
            
            # 4. 根据数据量优化ETL指令
            optimized_instructions = []
            for instruction in etl_instructions:
                optimized = await self.optimize_etl_for_large_data(
                    instruction, data_source_info.get('row_count', 0)
                )
                optimized_instructions.append(optimized)
            
            logger.info(f"生成 {len(optimized_instructions)} 个优化的ETL指令")
            return optimized_instructions
            
        except Exception as e:
            logger.error(f"LLM ETL规划失败: {e}")
            # 回退到传统规划方式
            if placeholders:
                return await self.etl_planner.plan_etl_operations(placeholders, data_source_id)
            return []
    
    def _build_etl_analysis_prompt(self, template_text: str, 
                                 data_source_info: Dict[str, Any],
                                 placeholders: List[PlaceholderMatch] = None) -> str:
        """
        构建ETL分析提示词
        """
        placeholder_info = ""
        if placeholders:
            placeholder_info = "\n已识别的占位符:\n"
            for i, ph in enumerate(placeholders, 1):
                placeholder_info += f"{i}. 类型: {ph.type.value}, 描述: {ph.description}, 置信度: {ph.confidence:.2f}\n"
        
        return f"""
作为数据分析专家，请分析以下模板和数据源信息，生成最优的ETL操作计划。

模板内容:
{template_text}

{placeholder_info}

数据源信息:
- 类型: {data_source_info.get('source_type', '未知')}
- 预估记录数: {data_source_info.get('row_count', '未知')}
- 主要字段: {', '.join(data_source_info.get('main_fields', []))}
- 数值字段: {', '.join(data_source_info.get('numeric_fields', []))}
- 时间字段: {', '.join(data_source_info.get('date_fields', []))}
- 区域字段: {', '.join(data_source_info.get('region_fields', []))}

请分析并返回JSON格式的ETL操作计划，包含以下信息:
1. 需要的数据操作类型 (select, aggregate, group_by等)
2. 所需字段和聚合函数
3. 过滤条件
4. 性能优化建议
5. 预期输出格式

返回格式:
{{
    "etl_operations": [
        {{
            "operation_id": "统计操作1",
            "query_type": "aggregate",
            "fields": ["字段1", "字段2"],
            "aggregations": [
                {{
                    "function": "sum",
                    "field": "字段1",
                    "alias": "总计"
                }}
            ],
            "filters": [
                {{
                    "column": "字段名",
                    "operator": "=",
                    "value": "条件值"
                }}
            ],
            "time_filter": {{
                "field": "时间字段",
                "period": "monthly"
            }},
            "region_filter": {{
                "field": "区域字段",
                "type": "exact"
            }},
            "output_format": "scalar",
            "performance_hints": ["batch_processing", "index_suggestion"]
        }}
    ],
    "optimization_suggestions": [
        "建议1",
        "建议2"
    ]
}}
"""
    
    async def _get_data_source_info(self, data_source: DataSource) -> Dict[str, Any]:
        """
        获取数据源详细信息
        """
        info = {
            "source_type": data_source.source_type,
            "row_count": 0,
            "main_fields": [],
            "numeric_fields": [],
            "date_fields": [],
            "region_fields": []
        }
        
        try:
            # 这里应该实现实际的数据源分析逻辑
            # 目前返回示例数据
            if data_source.source_type == "sql":
                # 可以通过INFORMATION_SCHEMA获取表结构信息
                info.update({
                    "main_fields": ["id", "name", "value", "date", "region"],
                    "numeric_fields": ["value", "amount", "count"],
                    "date_fields": ["date", "created_at", "updated_at"],
                    "region_fields": ["region", "province", "city"]
                })
            elif data_source.source_type == "csv":
                # 可以读取CSV头部获取字段信息
                info.update({
                    "main_fields": ["column1", "column2", "column3"],
                    "numeric_fields": ["column2"],
                    "date_fields": ["column3"],
                    "region_fields": ["column1"]
                })
                
        except Exception as e:
            logger.warning(f"获取数据源信息失败: {e}")
            
        return info
    
    async def _call_llm(self, prompt: str) -> str:
        """
        调用LLM
        """
        try:
            if self.ai_service:
                # 使用现有的AI服务
                response = await self.ai_service.analyze_with_context(prompt)
                return response
            else:
                # 直接调用OpenAI API或其他LLM服务
                # 这里需要根据实际配置实现
                return await self._direct_llm_call(prompt)
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return "{}"
    
    async def _direct_llm_call(self, prompt: str) -> str:
        """
        直接调用LLM API
        """
        # 这里应该实现实际的LLM API调用
        # 目前返回示例响应
        return """
        {
            "etl_operations": [
                {
                    "operation_id": "统计分析",
                    "query_type": "aggregate",
                    "fields": ["value"],
                    "aggregations": [
                        {
                            "function": "sum",
                            "field": "value",
                            "alias": "总计"
                        }
                    ],
                    "filters": [],
                    "output_format": "scalar",
                    "performance_hints": ["batch_processing"]
                }
            ],
            "optimization_suggestions": [
                "建议为value字段创建索引",
                "对于大数据集启用分批处理"
            ]
        }
        """
    
    async def _parse_llm_etl_plan(self, llm_response: str, 
                                data_source: DataSource) -> List[ETLInstructions]:
        """
        解析LLM的ETL计划
        """
        try:
            # 解析JSON响应
            plan_data = json.loads(llm_response.strip())
            etl_operations = plan_data.get("etl_operations", [])
            
            instructions_list = []
            
            for i, operation in enumerate(etl_operations):
                # 转换为ETLInstructions对象
                aggregations = []
                for agg_config in operation.get("aggregations", []):
                    aggregations.append(AggregationConfig(
                        function=agg_config.get("function", "sum"),
                        field=agg_config.get("field", ""),
                        group_by=agg_config.get("group_by")
                    ))
                
                time_config = None
                if operation.get("time_filter"):
                    time_filter = operation["time_filter"]
                    time_config = TimeFilterConfig(
                        field=time_filter.get("field", "date"),
                        period=time_filter.get("period", "monthly")
                    )
                
                region_config = None
                if operation.get("region_filter"):
                    region_filter = operation["region_filter"]
                    region_config = RegionFilterConfig(
                        field=region_filter.get("field", "region"),
                        region_value=region_filter.get("value", ""),
                        region_type=region_filter.get("type", "exact")
                    )
                
                instructions = ETLInstructions(
                    instruction_id=operation.get("operation_id", f"llm_op_{i}"),
                    query_type=operation.get("query_type", "select"),
                    source_fields=operation.get("fields", []),
                    filters=operation.get("filters", []),
                    aggregations=aggregations,
                    transformations=operation.get("transformations", []),
                    time_config=time_config,
                    region_config=region_config,
                    output_format=operation.get("output_format", "dataframe"),
                    performance_hints=operation.get("performance_hints", [])
                )
                
                instructions_list.append(instructions)
            
            return instructions_list
            
        except Exception as e:
            logger.error(f"解析LLM ETL计划失败: {e}")
            return []
    
    async def optimize_etl_for_large_data(self, etl_instructions: ETLInstructions, 
                                        data_size_estimate: int) -> ETLInstructions:
        """
        根据数据量优化ETL操作
        
        Args:
            etl_instructions: 原始ETL指令
            data_size_estimate: 数据量估计
            
        Returns:
            优化后的ETL指令
        """
        optimized_instructions = etl_instructions
        
        # 对于大数据集，应用优化策略
        if data_size_estimate > 100000:  # 超过10万行
            logger.info(f"检测到大数据集({data_size_estimate}行)，应用优化策略")
            
            # 1. 启用分批处理
            if not optimized_instructions.performance_hints:
                optimized_instructions.performance_hints = []
            optimized_instructions.performance_hints.append("batch_processing")
            
            # 2. 添加适当的索引建议
            if optimized_instructions.filters:
                for filter_config in optimized_instructions.filters:
                    column = filter_config.get("column")
                    if column:
                        optimized_instructions.performance_hints.append(f"index_{column}")
            
            # 3. 优化聚合操作
            if optimized_instructions.query_type == "aggregate":
                optimized_instructions.performance_hints.append("pre_aggregate")
                
            # 4. 对于超大数据集，建议使用流式处理
            if data_size_estimate > 1000000:  # 超过100万行
                optimized_instructions.performance_hints.append("streaming_processing")
                
        return optimized_instructions
    
    async def analyze_placeholder_requirements(self, placeholders: List[PlaceholderMatch]) -> Dict[str, Any]:
        """
        分析占位符需求，提供智能建议
        
        Args:
            placeholders: 占位符列表
            
        Returns:
            分析结果
        """
        analysis = {
            "total_count": len(placeholders),
            "type_distribution": {},
            "complexity_score": 0,
            "suggested_optimizations": [],
            "resource_requirements": {}
        }
        
        # 统计类型分布
        for placeholder in placeholders:
            type_name = placeholder.type.value
            analysis["type_distribution"][type_name] = analysis["type_distribution"].get(type_name, 0) + 1
        
        # 计算复杂度分数
        complexity_factors = {
            PlaceholderType.STATISTIC: 1,
            PlaceholderType.CHART: 2,
            PlaceholderType.PERIOD: 2,
            PlaceholderType.REGION: 1
        }
        
        for placeholder in placeholders:
            analysis["complexity_score"] += complexity_factors.get(placeholder.type, 1)
        
        # 提供优化建议
        if analysis["complexity_score"] > 10:
            analysis["suggested_optimizations"].append("建议启用并行处理")
            
        if analysis["type_distribution"].get("图表", 0) > 3:
            analysis["suggested_optimizations"].append("建议预先计算图表数据")
            
        if analysis["type_distribution"].get("统计", 0) > 5:
            analysis["suggested_optimizations"].append("建议合并相似的统计查询")
        
        # 估算资源需求
        analysis["resource_requirements"] = {
            "estimated_memory": analysis["complexity_score"] * 100,  # MB
            "estimated_time": analysis["complexity_score"] * 0.5,    # 秒
            "cpu_intensive": analysis["complexity_score"] > 15
        }
        
        return analysis
    
    async def suggest_template_improvements(self, template_text: str, 
                                          processing_results: Dict[str, Any]) -> List[str]:
        """
        基于处理结果建议模板改进
        
        Args:
            template_text: 原始模板
            processing_results: 处理结果
            
        Returns:
            改进建议列表
        """
        suggestions = []
        
        metadata = processing_results.get("processing_metadata", {})
        
        # 基于处理时间提供建议
        if metadata.get("total_processing_time", 0) > 30:  # 超过30秒
            suggestions.append("模板处理时间较长，建议简化复杂的统计计算")
            
        # 基于失败率提供建议
        failed_count = metadata.get("failed_count", 0)
        total_count = metadata.get("etl_operations_count", 1)
        if failed_count / total_count > 0.3:  # 失败率超过30%
            suggestions.append("部分占位符处理失败，建议检查字段名称和数据格式")
            
        # 基于占位符数量提供建议
        placeholder_count = metadata.get("placeholder_count", 0)
        if placeholder_count > 20:
            suggestions.append("占位符数量较多，建议分解为多个模板")
            
        return suggestions


# 创建全局实例
enhanced_ai_service = EnhancedAIService()