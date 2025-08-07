"""
模板ETL处理器

基于模板自动组织和执行ETL操作，实现智能数据处理。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from ...models.data_source import DataSource
from ...schemas.placeholder_mapping import PlaceholderMatch
from ..intelligent_placeholder.processor import PlaceholderProcessor
from ..intelligent_placeholder.etl_planner import IntelligentETLPlanner
from ..data_processing.etl.intelligent_etl_executor import (
    IntelligentETLExecutor, ProcessedData
)
from ...crud.crud_data_source import crud_data_source
from ...db.session import get_db_session

logger = logging.getLogger(__name__)


class TemplateETLProcessor:
    """模板ETL处理器"""
    
    def __init__(self):
        self.placeholder_processor = PlaceholderProcessor()
        self.etl_planner = IntelligentETLPlanner()
        # 延迟初始化ETL执行器，在需要时创建
        self.etl_executor = None
        
    def _get_etl_executor(self, db: Session):
        """获取ETL执行器实例"""
        if self.etl_executor is None:
            self.etl_executor = IntelligentETLExecutor(db)
        return self.etl_executor
        
    async def process_template_with_etl(self, template_text: str, 
                                      data_source_id: int,
                                      task_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        基于模板自动处理ETL操作
        
        Args:
            template_text: 模板文本
            data_source_id: 数据源ID
            task_config: 任务配置
            
        Returns:
            处理结果
        """
        try:
            logger.info(f"开始处理模板，数据源ID: {data_source_id}")
            
            # 1. 解析模板中的占位符
            placeholders = self.placeholder_processor.extract_placeholders(template_text)
            logger.info(f"解析到 {len(placeholders)} 个占位符")
            
            # 2. 规划ETL操作
            etl_operations = await self.etl_planner.plan_etl_operations(
                placeholders, data_source_id, task_config
            )
            logger.info(f"规划了 {len(etl_operations)} 个ETL操作")
            
            # 3. 执行ETL操作
            results = {}
            total_processing_time = 0
            
            # 获取数据库会话
            from ...db.session import get_db_session
            with get_db_session() as db:
                etl_executor = self._get_etl_executor(db)
                
                for i, operation in enumerate(etl_operations):
                    logger.info(f"执行ETL操作 {i+1}/{len(etl_operations)}: {operation.get('instruction_id', f'op_{i}')}")
                    try:
                        # 使用execute_instruction方法而不是execute_etl
                        processed_data = etl_executor.execute_instruction(operation, str(data_source_id))
                        results[operation.get('instruction_id', f'op_{i}')] = processed_data
                        total_processing_time += processed_data.get('metadata', {}).get('execution_time', 0)
                        logger.info(f"ETL操作 {operation.get('instruction_id', f'op_{i}')} 执行完成")
                    except Exception as e:
                        logger.error(f"ETL操作 {operation.get('instruction_id', f'op_{i}')} 执行失败: {e}")
                        # 创建失败的处理结果
                        results[operation.get('instruction_id', f'op_{i}')] = {
                            "data": None,
                            "metadata": {"error": str(e)},
                            "status": "error",
                            "error_message": str(e)
                        }
            
            # 4. 将结果填充到模板中
            filled_template = await self._fill_template_with_results(template_text, results)
            
            logger.info("模板ETL处理完成")
            return {
                "filled_template": filled_template,
                "etl_results": results,
                "processing_metadata": {
                    "placeholder_count": len(placeholders),
                    "etl_operations_count": len(etl_operations),
                    "total_processing_time": total_processing_time,
                    "success_count": len([r for r in results.values() if r.get('status') == 'success']),
                    "failed_count": len([r for r in results.values() if r.get('status') == 'error'])
                }
            }
            
        except Exception as e:
            logger.error(f"模板ETL处理失败: {e}")
            raise
    
    async def _fill_template_with_results(self, template_text: str, 
                                        results: Dict[str, Any]) -> str:
        """
        将ETL结果填充到模板中
        """
        filled_text = template_text
        
        # 根据结果类型和占位符类型进行智能填充
        for instruction_id, result in results.items():
            if result.get('status') == 'success' and result.get('data') is not None:
                # 根据输出格式进行适当转换
                formatted_value = self._format_result_value(result)
                
                # 在模板中替换对应的占位符
                # 这里需要更复杂的逻辑来匹配占位符和结果
                # 暂时使用简单的替换方式
                filled_text = filled_text.replace(
                    f"{{{{{instruction_id}}}}}", 
                    str(formatted_value)
                )
                
        return filled_text
    
    def _format_result_value(self, result: Dict[str, Any]) -> str:
        """
        格式化结果值
        """
        data = result.get('data')
        if data is None:
            return "N/A"
            
        # 根据输出格式进行适当转换
        if isinstance(data, (int, float)):
            # 数值格式化
            if isinstance(data, float):
                return f"{data:,.2f}"
            else:
                return f"{data:,}"
        elif isinstance(data, pd.DataFrame):
            # 对于DataFrame，转换为表格格式
            if len(data) <= 10:
                return data.to_string(index=False)
            else:
                # 大表格只显示前几行
                return data.head(5).to_string(index=False) + "\n..."
        elif isinstance(data, list):
            # 列表格式化
            if len(data) <= 5:
                return ", ".join(str(item) for item in data)
            else:
                return ", ".join(str(item) for item in data[:5]) + "..."
        elif isinstance(data, dict):
            # 字典格式化
            return str(data)
        else:
            return str(data)
    
    async def process_multiple_templates(self, templates: List[str], 
                                       data_source_id: int,
                                       task_config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        批量处理多个模板
        
        Args:
            templates: 模板文本列表
            data_source_id: 数据源ID
            task_config: 任务配置
            
        Returns:
            处理结果列表
        """
        results = []
        
        for i, template in enumerate(templates):
            logger.info(f"处理模板 {i+1}/{len(templates)}")
            try:
                result = await self.process_template_with_etl(template, data_source_id, task_config)
                results.append(result)
            except Exception as e:
                logger.error(f"模板 {i+1} 处理失败: {e}")
                results.append({
                    "error": str(e),
                    "template_index": i
                })
                
        return results


# 创建全局实例
template_etl_processor = TemplateETLProcessor()