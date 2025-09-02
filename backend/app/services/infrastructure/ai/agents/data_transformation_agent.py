"""
数据转换代理
基于React Agent架构的数据转换和处理服务
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataTransformationAgent:
    """
    数据转换代理
    基于React Agent架构的数据处理服务
    """
    
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for DataTransformationAgent")
            
        self.user_id = user_id
        self.logger = logging.getLogger(self.__class__.__name__)
        self._react_agent = None
    
    async def _get_react_agent(self):
        """获取React Agent实例"""
        if self._react_agent is None:
            from .react_agent import ReactAgent
            self._react_agent = ReactAgent(self.user_id)
            await self._react_agent.initialize()
        return self._react_agent
    
    async def extract_data_for_placeholders(
        self,
        data_source_ids: List[str],
        placeholder_specs: List[Dict[str, Any]],
        extraction_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        为占位符提取数据
        """
        try:
            self.logger.info(f"开始为 {len(placeholder_specs)} 个占位符提取数据")
            
            agent = await self._get_react_agent()
            
            # 构建数据提取提示
            prompt = f"""
            数据提取任务：
            - 数据源: {data_source_ids}
            - 占位符数量: {len(placeholder_specs)}
            - 提取上下文: {extraction_context}
            
            请为以下占位符提取相应数据：
            {placeholder_specs}
            """
            
            result = await agent.chat(prompt)
            
            return {
                "success": True,
                "extracted_data": result,
                "processed_placeholders": len(placeholder_specs),
                "data_sources_used": data_source_ids
            }
            
        except Exception as e:
            self.logger.error(f"数据提取失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_placeholders": 0
            }
    
    async def transform_raw_data(
        self,
        raw_data: Dict[str, Any],
        transformation_rules: List[Dict[str, Any]],
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        转换原始数据
        """
        try:
            agent = await self._get_react_agent()
            
            prompt = f"""
            数据转换任务：
            - 原始数据: {raw_data}
            - 转换规则: {transformation_rules}
            - 输出格式: {output_format}
            
            请按照规则转换数据并输出为指定格式。
            """
            
            result = await agent.chat(prompt)
            
            return {
                "success": True,
                "transformed_data": result,
                "output_format": output_format
            }
            
        except Exception as e:
            self.logger.error(f"数据转换失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def aggregate_multi_source_data(
        self,
        data_sources: List[Dict[str, Any]],
        aggregation_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        聚合多源数据
        """
        try:
            agent = await self._get_react_agent()
            
            prompt = f"""
            多源数据聚合任务：
            - 数据源: {data_sources}
            - 聚合规则: {aggregation_rules}
            
            请将多个数据源的数据按照规则进行聚合处理。
            """
            
            result = await agent.chat(prompt)
            
            return {
                "success": True,
                "aggregated_data": result,
                "sources_count": len(data_sources)
            }
            
        except Exception as e:
            self.logger.error(f"数据聚合失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def create_data_transformation_agent(user_id: str) -> DataTransformationAgent:
    """创建数据转换代理"""
    return DataTransformationAgent(user_id)