"""
统一智能报告生成服务

整合占位符解析、ETL规划、模板处理和AI服务，提供一站式的智能报告生成能力。
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.config import settings
from .intelligent_placeholder.processor import PlaceholderProcessor
from .intelligent_placeholder.etl_planner import IntelligentETLPlanner
from .intelligent_placeholder.template_etl_processor import TemplateETLProcessor
from .enhanced_ai_service import EnhancedAIService
from .data_processing.etl.intelligent_etl_executor import IntelligentETLExecutor
from ..schemas.placeholder_mapping import PlaceholderMatch
from ..models.data_source import DataSource
from ..models.template import Template
from ..crud.crud_data_source import crud_data_source
from ..crud.crud_template import crud_template
from ..db.session import get_db_session

logger = logging.getLogger(__name__)


class IntelligentReportService:
    """统一智能报告生成服务"""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.placeholder_processor = PlaceholderProcessor()
        self.etl_planner = IntelligentETLPlanner()
        self.template_processor = TemplateETLProcessor()
        self.enhanced_ai_service = EnhancedAIService(db)
        # 延迟初始化ETL执行器
        self.etl_executor = None
        
    def _get_etl_executor(self, db: Session):
        """获取ETL执行器实例"""
        if self.etl_executor is None:
            self.etl_executor = IntelligentETLExecutor(db)
        return self.etl_executor
        
    async def generate_intelligent_report(self, 
                                        template_text: str,
                                        data_source_id: int,
                                        task_config: Optional[Dict[str, Any]] = None,
                                        use_ai_optimization: bool = True) -> Dict[str, Any]:
        """
        生成智能报告
        
        Args:
            template_text: 模板文本
            data_source_id: 数据源ID
            task_config: 任务配置
            use_ai_optimization: 是否使用AI优化
            
        Returns:
            生成的报告和元数据
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始生成智能报告，数据源ID: {data_source_id}")
            
            # 1. 解析占位符
            logger.info("步骤 1/6: 解析占位符")
            placeholders = self.placeholder_processor.extract_placeholders(template_text)
            logger.info(f"解析到 {len(placeholders)} 个占位符")
            
            # 2. 分析占位符需求
            logger.info("步骤 2/6: 分析占位符需求")
            placeholder_analysis = await self.enhanced_ai_service.analyze_placeholder_requirements(placeholders)
            logger.info(f"复杂度分数: {placeholder_analysis['complexity_score']}")
            
            # 3. 智能ETL规划
            logger.info("步骤 3/6: 智能ETL规划")
            if use_ai_optimization:
                etl_instructions = await self.enhanced_ai_service.generate_etl_plan_with_llm(
                    template_text, data_source_id, placeholders
                )
            else:
                etl_instructions = await self.etl_planner.plan_etl_operations(
                    placeholders, data_source_id, task_config
                )
            logger.info(f"生成 {len(etl_instructions)} 个ETL指令")
            
            # 4. 执行ETL操作
            logger.info("步骤 4/6: 执行ETL操作")
            etl_results = {}
            total_etl_time = 0
            
            for instruction in etl_instructions:
                etl_start = time.time()
                # instruction 已经是字典格式，直接使用
                result = self._get_etl_executor(self.db).execute_instruction(instruction, data_source_id)
                etl_time = time.time() - etl_start
                total_etl_time += etl_time
                
                etl_results[instruction["instruction_id"]] = result
                logger.info(f"ETL指令 {instruction['instruction_id']} 执行完成，耗时: {etl_time:.2f}秒")
            
            # 5. 填充模板
            logger.info("步骤 5/6: 填充模板")
            filled_template = await self._intelligent_template_filling(
                template_text, placeholders, etl_results
            )
            
            # 6. 生成改进建议
            logger.info("步骤 6/6: 生成改进建议")
            processing_results = {
                "processing_metadata": {
                    "placeholder_count": len(placeholders),
                    "etl_operations_count": len(etl_instructions),
                    "total_processing_time": time.time() - start_time,
                    "success_count": len([r for r in etl_results.values() if r.get("status") == "success"]),
                    "failed_count": len([r for r in etl_results.values() if r.get("status") == "error"])
                }
            }
            
            improvement_suggestions = await self.enhanced_ai_service.suggest_template_improvements(
                template_text, processing_results
            )
            
            total_time = time.time() - start_time
            logger.info(f"智能报告生成完成，总耗时: {total_time:.2f}秒")
            
            return {
                "report_content": filled_template,
                "metadata": {
                    "generation_time": total_time,
                    "placeholder_analysis": placeholder_analysis,
                    "etl_performance": {
                        "total_instructions": len(etl_instructions),
                        "total_etl_time": total_etl_time,
                        "average_instruction_time": total_etl_time / len(etl_instructions) if etl_instructions else 0,
                        "success_rate": processing_results["processing_metadata"]["success_count"] / len(etl_instructions) if etl_instructions else 0
                    },
                    "optimization_used": use_ai_optimization,
                    "improvement_suggestions": improvement_suggestions
                },
                "raw_results": etl_results,
                "debug_info": {
                    "placeholders": [
                        {
                            "type": p.type.value,
                            "description": p.description,
                            "confidence": p.confidence,
                            "context_before": p.context_before[:50] + "..." if len(p.context_before) > 50 else p.context_before,
                            "context_after": p.context_after[:50] + "..." if len(p.context_after) > 50 else p.context_after
                        }
                        for p in placeholders
                    ],
                    "etl_instructions": [
                        {
                            "instruction_id": inst.instruction_id,
                            "query_type": inst.query_type,
                            "source_fields": inst.source_fields,
                            "performance_hints": inst.performance_hints
                        }
                        for inst in etl_instructions
                    ]
                }
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"智能报告生成失败: {e}")
            
            return {
                "report_content": None,
                "metadata": {
                    "generation_time": total_time,
                    "error": str(e),
                    "optimization_used": use_ai_optimization
                },
                "raw_results": {},
                "debug_info": {}
            }
    
    async def _intelligent_template_filling(self, 
                                          template_text: str,
                                          placeholders: List[PlaceholderMatch],
                                          etl_results: Dict[str, Any]) -> str:
        """
        智能模板填充
        """
        filled_text = template_text
        
        # 创建占位符到ETL结果的映射
        placeholder_result_mapping = await self._map_placeholders_to_results(
            placeholders, etl_results
        )
        
        # 按置信度排序，优先处理高置信度的占位符
        sorted_placeholders = sorted(placeholders, key=lambda x: x.confidence, reverse=True)
        
        for placeholder in sorted_placeholders:
            try:
                # 查找对应的ETL结果
                result_key = placeholder_result_mapping.get(placeholder.full_match)
                if result_key and result_key in etl_results:
                    result = etl_results[result_key]
                    if result.processed_value is not None:
                        formatted_value = self._format_placeholder_result(
                            placeholder, result.processed_value
                        )
                        filled_text = filled_text.replace(placeholder.full_match, formatted_value)
                        logger.debug(f"占位符 {placeholder.full_match} 替换为: {formatted_value}")
                    else:
                        # 处理失败的占位符
                        filled_text = filled_text.replace(placeholder.full_match, "[数据处理失败]")
                        logger.warning(f"占位符 {placeholder.full_match} 数据处理失败")
                else:
                    # 未找到对应结果的占位符
                    filled_text = filled_text.replace(placeholder.full_match, "[数据暂无]")
                    logger.warning(f"占位符 {placeholder.full_match} 未找到对应数据")
                    
            except Exception as e:
                logger.error(f"处理占位符 {placeholder.full_match} 时出错: {e}")
                filled_text = filled_text.replace(placeholder.full_match, "[处理出错]")
        
        return filled_text
    
    async def _map_placeholders_to_results(self, 
                                         placeholders: List[PlaceholderMatch],
                                         etl_results: Dict[str, Any]) -> Dict[str, str]:
        """
        创建占位符到ETL结果的映射
        """
        mapping = {}
        
        # 根据占位符类型和描述匹配ETL结果
        for placeholder in placeholders:
            # 简单的映射逻辑，根据类型匹配
            if placeholder.type.value == "统计":
                # 统计类占位符通常对应聚合查询结果
                for result_key in etl_results:
                    if "statistic" in result_key.lower():
                        mapping[placeholder.full_match] = result_key
                        break
            elif placeholder.type.value == "图表":
                # 图表类占位符对应图表数据
                for result_key in etl_results:
                    if "chart" in result_key.lower():
                        mapping[placeholder.full_match] = result_key
                        break
            elif placeholder.type.value == "周期":
                # 周期类占位符对应时间序列数据
                for result_key in etl_results:
                    if "period" in result_key.lower():
                        mapping[placeholder.full_match] = result_key
                        break
            elif placeholder.type.value == "区域":
                # 区域类占位符对应区域分析数据
                for result_key in etl_results:
                    if "region" in result_key.lower():
                        mapping[placeholder.full_match] = result_key
                        break
            
            # 如果没有找到匹配，使用第一个可用结果
            if placeholder.full_match not in mapping and etl_results:
                mapping[placeholder.full_match] = list(etl_results.keys())[0]
        
        return mapping
    
    def _format_placeholder_result(self, placeholder: PlaceholderMatch, result_value: Any) -> str:
        """
        根据占位符类型格式化结果值
        """
        try:
            if result_value is None:
                return "N/A"
            
            # 根据占位符类型进行格式化
            if placeholder.type.value == "统计":
                # 统计数据格式化
                if isinstance(result_value, (int, float)):
                    if isinstance(result_value, float):
                        return f"{result_value:,.2f}"
                    else:
                        return f"{result_value:,}"
                elif isinstance(result_value, list) and len(result_value) == 1:
                    val = result_value[0]
                    if isinstance(val, (int, float)):
                        return f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
                    return str(val)
                else:
                    return str(result_value)
                    
            elif placeholder.type.value == "图表":
                # 图表数据通常返回描述或链接
                if isinstance(result_value, dict):
                    return f"[图表数据: {len(result_value)} 项]"
                elif isinstance(result_value, list):
                    return f"[图表数据: {len(result_value)} 项]"
                else:
                    return "[图表]"
                    
            elif placeholder.type.value == "周期":
                # 周期数据格式化
                if isinstance(result_value, str):
                    return result_value
                elif isinstance(result_value, list):
                    return ", ".join(str(item) for item in result_value[:3])
                else:
                    return str(result_value)
                    
            elif placeholder.type.value == "区域":
                # 区域数据格式化
                if isinstance(result_value, dict):
                    # 如果是区域统计，显示主要信息
                    return str(list(result_value.values())[0]) if result_value else "N/A"
                else:
                    return str(result_value)
            
            return str(result_value)
            
        except Exception as e:
            logger.error(f"格式化占位符结果时出错: {e}")
            return "[格式化出错]"
    
    async def batch_generate_reports(self, 
                                   templates: List[str],
                                   data_source_id: int,
                                   task_config: Optional[Dict[str, Any]] = None,
                                   use_ai_optimization: bool = True,
                                   max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """
        批量生成报告
        
        Args:
            templates: 模板列表
            data_source_id: 数据源ID
            task_config: 任务配置
            use_ai_optimization: 是否使用AI优化
            max_concurrent: 最大并发数
            
        Returns:
            报告结果列表
        """
        logger.info(f"开始批量生成 {len(templates)} 个报告")
        
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_single_report(template: str, index: int) -> Dict[str, Any]:
            async with semaphore:
                try:
                    logger.info(f"生成报告 {index + 1}/{len(templates)}")
                    result = await self.generate_intelligent_report(
                        template, data_source_id, task_config, use_ai_optimization
                    )
                    result["template_index"] = index
                    return result
                except Exception as e:
                    logger.error(f"报告 {index + 1} 生成失败: {e}")
                    return {
                        "template_index": index,
                        "error": str(e),
                        "report_content": None
                    }
        
        # 并发执行
        tasks = [generate_single_report(template, i) for i, template in enumerate(templates)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "template_index": i,
                    "error": str(result),
                    "report_content": None
                })
            else:
                processed_results.append(result)
        
        logger.info(f"批量报告生成完成，成功: {len([r for r in processed_results if r.get('report_content')])}")
        return processed_results
    
    async def generate_intelligent_report(self, 
                                        template_id: str,
                                        data_source_id: str,
                                        user_id: str,
                                        task_config: Optional[Dict[str, Any]] = None,
                                        use_ai_optimization: bool = True) -> Dict[str, Any]:
        """
        通过模板ID和数据源ID生成智能报告
        
        Args:
            template_id: 模板ID
            data_source_id: 数据源ID
            user_id: 用户ID
            task_config: 任务配置
            use_ai_optimization: 是否使用AI优化
            
        Returns:
            生成的报告和元数据
        """
        start_time = time.time()
        
        try:
            # 1. 获取模板和数据源
            from uuid import UUID
            with get_db_session() as db:
                # 转换UUID类型
                template_uuid = UUID(template_id) if isinstance(template_id, str) else template_id
                data_source_uuid = UUID(data_source_id) if isinstance(data_source_id, str) else data_source_id
                
                template = db.query(Template).filter(Template.id == template_uuid).first()
                data_source = db.query(DataSource).filter(DataSource.id == data_source_uuid).first()
                
                if not template:
                    raise ValueError(f"模板不存在: {template_id}")
                if not data_source:
                    raise ValueError(f"数据源不存在: {data_source_id}")
            
            logger.info(f"开始生成智能报告，模板: {template.name}, 数据源: {data_source.name}")
            
            # 2. 解析占位符
            logger.info("步骤 1/6: 解析占位符")
            placeholders = self.placeholder_processor.extract_placeholders(template.content)
            logger.info(f"解析到 {len(placeholders)} 个占位符")
            
            # 3. 分析占位符需求
            logger.info("步骤 2/6: 分析占位符需求")
            placeholder_analysis = await self.enhanced_ai_service.analyze_placeholder_requirements(placeholders)
            logger.info(f"复杂度分数: {placeholder_analysis['complexity_score']}")
            
            # 4. 智能ETL规划
            logger.info("步骤 3/6: 智能ETL规划")
            if use_ai_optimization:
                etl_instructions = await self.enhanced_ai_service.generate_etl_plan_with_llm(
                    template.content, str(data_source_uuid), placeholders
                )
            else:
                etl_instructions = await self.etl_planner.plan_etl_operations(
                    placeholders, data_source, task_config
                )
            logger.info(f"生成 {len(etl_instructions)} 个ETL指令")
            
            # 5. 执行ETL操作
            logger.info("步骤 4/6: 执行ETL操作")
            etl_results = {}
            total_etl_time = 0
            
            with get_db_session() as etl_db:
                for instruction in etl_instructions:
                    etl_start = time.time()
                    # instruction 已经是字典格式，直接使用
                    result = self._get_etl_executor(etl_db).execute_instruction(instruction, str(data_source_uuid))
                    etl_time = time.time() - etl_start
                    total_etl_time += etl_time
                    
                    etl_results[instruction["instruction_id"]] = result
                    logger.info(f"ETL指令 {instruction['instruction_id']} 执行完成，耗时: {etl_time:.2f}秒")
            
            # 6. 填充模板
            logger.info("步骤 5/6: 填充模板")
            filled_template = await self._intelligent_template_filling(
                template.content, placeholders, etl_results
            )
            
            # 7. 生成改进建议
            logger.info("步骤 6/6: 生成改进建议")
            processing_results = {
                "processing_metadata": {
                    "placeholder_count": len(placeholders),
                    "etl_operations_count": len(etl_instructions),
                    "total_processing_time": time.time() - start_time,
                    "success_count": len([r for r in etl_results.values() if r.get("status") == "success"]),
                    "failed_count": len([r for r in etl_results.values() if r.get("status") == "error"])
                }
            }
            
            improvement_suggestions = await self.enhanced_ai_service.suggest_template_improvements(
                template.content, processing_results
            )
            
            total_time = time.time() - start_time
            logger.info(f"智能报告生成完成，总耗时: {total_time:.2f}秒")
            
            return {
                "filled_template": filled_template,
                "etl_results": etl_results,
                "processing_metadata": {
                    "generation_time": total_time,
                    "placeholder_analysis": placeholder_analysis,
                    "etl_performance": {
                        "total_instructions": len(etl_instructions),
                        "total_etl_time": total_etl_time,
                        "average_instruction_time": total_etl_time / len(etl_instructions) if etl_instructions else 0,
                        "success_rate": processing_results["processing_metadata"]["success_count"] / len(etl_instructions) if etl_instructions else 0
                    },
                    "optimization_used": use_ai_optimization,
                    "improvement_suggestions": improvement_suggestions
                }
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"智能报告生成失败: {e}")
            raise e
    
    async def get_generation_statistics(self, data_source_id: int) -> Dict[str, Any]:
        """
        获取报告生成统计信息
        """
        try:
            with get_db_session() as db:
                data_source = crud_data_source.get(db, id=data_source_id)
                if not data_source:
                    return {"error": "数据源不存在"}
            
            # 这里可以添加更多统计逻辑
            return {
                "data_source_id": data_source_id,
                "data_source_type": data_source.source_type,
                "estimated_performance": "good",  # 可以基于历史数据计算
                "recommended_batch_size": 5,
                "optimization_suggestions": [
                    "建议启用AI优化以获得更好的性能",
                    "对于大量模板建议使用批量处理"
                ]
            }
            
        except Exception as e:
            logger.error(f"获取生成统计失败: {e}")
            return {"error": str(e)}


# 创建全局实例
intelligent_report_service = IntelligentReportService()