"""
智能ETL规划器

基于占位符需求智能规划ETL操作，优化大数据处理性能。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from ...models.data_source import DataSource
from ...schemas.placeholder_mapping import PlaceholderMatch, PlaceholderType
from ..data_processing.etl.intelligent_etl_executor import (
    AggregationConfig,
    ETLInstructions,
    TimeFilterConfig,
    RegionFilterConfig
)
from ...crud.crud_data_source import crud_data_source
from ...db.session import get_db_session

logger = logging.getLogger(__name__)


class IntelligentETLPlanner:
    """智能ETL规划器"""
    
    def __init__(self):
        self.etl_executor = None  # 按需初始化
        
    async def plan_etl_operations(self, placeholders: List[PlaceholderMatch], 
                                data_source_id: int,
                                task_config: Optional[Dict[str, Any]] = None) -> List[ETLInstructions]:
        """
        基于占位符需求规划ETL操作
        
        Args:
            placeholders: 占位符列表
            data_source_id: 数据源ID
            task_config: 任务配置（包含时间范围、区域等）
            
        Returns:
            ETL指令列表
        """
        try:
            # 获取数据源信息
            with get_db_session() as db:
                data_source = crud_data_source.get(db, id=data_source_id)
                if not data_source:
                    raise ValueError(f"数据源 {data_source_id} 不存在")
            
            etl_operations = []
            
            # 按类型分组占位符
            grouped_placeholders = self._group_placeholders_by_type(placeholders)
            
            # 为每组占位符生成ETL指令
            for placeholder_type, placeholder_list in grouped_placeholders.items():
                if placeholder_type == PlaceholderType.STATISTIC:
                    # 统计类占位符 - 生成聚合查询
                    etl_instructions = await self._plan_statistic_etl(
                        placeholder_list, data_source, task_config
                    )
                    if etl_instructions:
                        etl_operations.append(etl_instructions)
                        
                elif placeholder_type == PlaceholderType.CHART:
                    # 图表类占位符 - 生成适合可视化的查询
                    etl_instructions = await self._plan_chart_etl(
                        placeholder_list, data_source, task_config
                    )
                    if etl_instructions:
                        etl_operations.append(etl_instructions)
                        
                elif placeholder_type == PlaceholderType.PERIOD:
                    # 周期类占位符 - 生成时间序列查询
                    etl_instructions = await self._plan_period_etl(
                        placeholder_list, data_source, task_config
                    )
                    if etl_instructions:
                        etl_operations.append(etl_instructions)
                        
                elif placeholder_type == PlaceholderType.REGION:
                    # 区域类占位符 - 生成区域分析查询
                    etl_instructions = await self._plan_region_etl(
                        placeholder_list, data_source, task_config
                    )
                    if etl_instructions:
                        etl_operations.append(etl_instructions)
            
            logger.info(f"规划完成，生成 {len(etl_operations)} 个ETL操作")
            return etl_operations
            
        except Exception as e:
            logger.error(f"ETL规划失败: {e}")
            raise
    
    def _group_placeholders_by_type(self, placeholders: List[PlaceholderMatch]) -> Dict[PlaceholderType, List[PlaceholderMatch]]:
        """按类型分组占位符"""
        grouped = {}
        for placeholder in placeholders:
            placeholder_type = placeholder.type
            if placeholder_type not in grouped:
                grouped[placeholder_type] = []
            grouped[placeholder_type].append(placeholder)
        return grouped
    
    async def _plan_statistic_etl(self, placeholders: List[PlaceholderMatch], 
                                data_source: DataSource,
                                task_config: Optional[Dict[str, Any]] = None) -> Optional[ETLInstructions]:
        """
        为统计类占位符规划ETL操作
        """
        if not placeholders:
            return None
            
        # 分析占位符需求，生成聚合查询
        aggregations = []
        filters = []
        source_fields = []
        
        # 添加时间过滤配置（如果需要）
        time_config = None
        if task_config and "time_range" in task_config:
            time_config = TimeFilterConfig(
                field=self._detect_date_field(data_source),
                start_date=task_config["time_range"].get("start_date"),
                end_date=task_config["time_range"].get("end_date")
            )
        
        # 添加区域过滤配置（如果需要）
        region_config = None
        if task_config and "region" in task_config:
            region_config = RegionFilterConfig(
                field=self._detect_region_field(data_source),
                region_value=task_config["region"]
            )
        
        for placeholder in placeholders:
            # 根据描述生成聚合操作
            agg_config = self._generate_aggregation_from_description(
                placeholder.description, data_source
            )
            if agg_config:
                aggregations.append(agg_config)
                source_fields.append(agg_config.field)
        
        if not aggregations:
            return None
            
        return ETLInstructions(
            instruction_id=f"statistic_{len(placeholders)}",
            query_type="aggregate",
            source_fields=list(set(source_fields)),  # 去重
            filters=filters,
            aggregations=aggregations,
            transformations=[],
            time_config=time_config,
            region_config=region_config,
            output_format="scalar"
        )
    
    async def _plan_chart_etl(self, placeholders: List[PlaceholderMatch], 
                            data_source: DataSource,
                            task_config: Optional[Dict[str, Any]] = None) -> Optional[ETLInstructions]:
        """
        为图表类占位符规划ETL操作
        """
        if not placeholders:
            return None
            
        # 图表通常需要分组数据
        aggregations = []
        filters = []
        group_by_fields = []
        source_fields = []
        
        # 添加时间过滤配置
        time_config = None
        if task_config and "time_range" in task_config:
            time_config = TimeFilterConfig(
                field=self._detect_date_field(data_source),
                start_date=task_config["time_range"].get("start_date"),
                end_date=task_config["time_range"].get("end_date")
            )
        
        # 添加区域过滤配置
        region_config = None
        if task_config and "region" in task_config:
            region_config = RegionFilterConfig(
                field=self._detect_region_field(data_source),
                region_value=task_config["region"]
            )
        
        # 检测可能的分组字段（时间、区域等）
        date_field = self._detect_date_field(data_source)
        region_field = self._detect_region_field(data_source)
        
        if date_field:
            group_by_fields.append(date_field)
        if region_field:
            group_by_fields.append(region_field)
            
        for placeholder in placeholders:
            # 为图表生成聚合操作
            agg_config = self._generate_aggregation_from_description(
                placeholder.description, data_source
            )
            if agg_config:
                # 为图表添加分组
                agg_config.group_by = group_by_fields if group_by_fields else None
                aggregations.append(agg_config)
                source_fields.append(agg_config.field)
        
        if not aggregations:
            return None
            
        return ETLInstructions(
            instruction_id=f"chart_{len(placeholders)}",
            query_type="aggregate",
            source_fields=list(set(source_fields)),
            filters=filters,
            aggregations=aggregations,
            transformations=[],
            time_config=time_config,
            region_config=region_config,
            output_format="json"  # 图表数据通常需要JSON格式
        )
    
    async def _plan_period_etl(self, placeholders: List[PlaceholderMatch], 
                             data_source: DataSource,
                             task_config: Optional[Dict[str, Any]] = None) -> Optional[ETLInstructions]:
        """
        为周期类占位符规划ETL操作
        """
        if not placeholders:
            return None
            
        # 周期分析通常需要时间序列数据
        filters = []
        source_fields = []
        
        # 必须有时间字段
        date_field = self._detect_date_field(data_source)
        if not date_field:
            return None
            
        # 添加时间过滤配置
        time_config = TimeFilterConfig(
            field=date_field,
            start_date=task_config["time_range"].get("start_date") if task_config and "time_range" in task_config else None,
            end_date=task_config["time_range"].get("end_date") if task_config and "time_range" in task_config else None
        )
        
        # 添加区域过滤配置（如果需要）
        region_config = None
        if task_config and "region" in task_config:
            region_config = RegionFilterConfig(
                field=self._detect_region_field(data_source),
                region_value=task_config["region"]
            )
        
        # 收集需要的字段
        for placeholder in placeholders:
            field_name = self._extract_field_name(placeholder.description)
            if field_name and field_name in self._get_available_fields(data_source):
                source_fields.append(field_name)
        
        if not source_fields:
            # 如果没有明确字段，使用日期字段
            source_fields.append(date_field)
            
        return ETLInstructions(
            instruction_id=f"period_{len(placeholders)}",
            query_type="select",
            source_fields=list(set(source_fields)),
            filters=filters,
            aggregations=[],
            transformations=[],
            time_config=time_config,
            region_config=region_config,
            output_format="array"
        )
    
    async def _plan_region_etl(self, placeholders: List[PlaceholderMatch], 
                             data_source: DataSource,
                             task_config: Optional[Dict[str, Any]] = None) -> Optional[ETLInstructions]:
        """
        为区域类占位符规划ETL操作
        """
        if not placeholders:
            return None
            
        # 区域分析通常需要按区域分组
        aggregations = []
        filters = []
        source_fields = []
        
        # 必须有区域字段
        region_field = self._detect_region_field(data_source)
        if not region_field:
            return None
            
        # 添加时间过滤配置
        time_config = None
        if task_config and "time_range" in task_config:
            time_config = TimeFilterConfig(
                field=self._detect_date_field(data_source),
                start_date=task_config["time_range"].get("start_date"),
                end_date=task_config["time_range"].get("end_date")
            )
        
        # 区域过滤配置
        region_config = RegionFilterConfig(
            field=region_field,
            region_value=task_config["region"] if task_config and "region" in task_config else ""
        )
        
        # 为区域分析生成聚合操作
        for placeholder in placeholders:
            agg_config = self._generate_aggregation_from_description(
                placeholder.description, data_source
            )
            if agg_config:
                # 按区域分组
                agg_config.group_by = [region_field]
                aggregations.append(agg_config)
                source_fields.append(agg_config.field)
        
        if not aggregations:
            return None
            
        return ETLInstructions(
            instruction_id=f"region_{len(placeholders)}",
            query_type="aggregate",
            source_fields=list(set(source_fields)),
            filters=filters,
            aggregations=aggregations,
            transformations=[],
            time_config=time_config,
            region_config=region_config,
            output_format="json"
        )
    
    def _generate_aggregation_from_description(self, description: str, 
                                             data_source: DataSource) -> Optional[AggregationConfig]:
        """
        根据描述生成聚合操作配置
        """
        available_fields = self._get_available_fields(data_source)
        
        # 简单的关键词匹配
        if "总" in description or "总计" in description or "合计" in description:
            field = self._extract_field_name(description)
            if field in available_fields:
                return AggregationConfig(function="sum", field=field)
                
        elif "平均" in description or "均值" in description:
            field = self._extract_field_name(description)
            if field in available_fields:
                return AggregationConfig(function="avg", field=field)
                
        elif "最大" in description:
            field = self._extract_field_name(description)
            if field in available_fields:
                return AggregationConfig(function="max", field=field)
                
        elif "最小" in description:
            field = self._extract_field_name(description)
            if field in available_fields:
                return AggregationConfig(function="min", field=field)
                
        elif "数量" in description or "件数" in description or "次数" in description:
            field = self._extract_field_name(description)
            if field in available_fields:
                return AggregationConfig(function="count", field=field)
                
        # 默认使用第一个数值字段
        numeric_fields = self._get_numeric_fields(available_fields)
        if numeric_fields:
            return AggregationConfig(function="sum", field=numeric_fields[0])
            
        return None
    
    def _extract_field_name(self, description: str) -> str:
        """
        从描述中提取字段名
        """
        # 这里可以实现更复杂的字段名提取逻辑
        # 目前简单返回描述本身
        return description
    
    def _get_available_fields(self, data_source: DataSource) -> List[str]:
        """
        获取数据源的可用字段
        """
        # 这里应该从数据源获取实际的字段信息
        # 目前返回示例字段
        return ["value", "amount", "count", "date", "region"]
    
    def _get_numeric_fields(self, fields: List[str]) -> List[str]:
        """
        从字段列表中筛选数值字段
        """
        numeric_keywords = ["value", "amount", "count", "sum", "total"]
        return [field for field in fields if any(keyword in field.lower() for keyword in numeric_keywords)]
    
    def _detect_date_field(self, data_source: DataSource) -> str:
        """
        检测日期字段
        """
        # 这里应该实现实际的日期字段检测逻辑
        return "date"
    
    def _detect_region_field(self, data_source: DataSource) -> str:
        """
        检测区域字段
        """
        # 这里应该实现实际的区域字段检测逻辑
        return "region"


# 创建全局实例
intelligent_etl_planner = IntelligentETLPlanner()