"""
优化版报告生成器
集成批量AI处理、查询优化器和异步MCP客户端
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from ..intelligent_placeholder.processor import PlaceholderProcessor
from ..intelligent_placeholder.batch_processor import BatchPlaceholderProcessor
from ..data_processing.query_optimizer import query_optimizer
from ..async_mcp_client import get_async_mcp_client, MCPToolType, MCPRequest
from ..ai_integration.ai_service_enhanced import AIService
from .composer import ReportCompositionService
from ...crud.crud_data_source import crud_data_source
from ...db.session import get_db_session


@dataclass
class OptimizedReportResult:
    """优化报告生成结果"""
    success: bool
    report_content: str
    generation_time: float
    placeholders_processed: int
    llm_calls_saved: int
    data_queries_executed: int
    cache_hits: int
    errors: List[str]
    performance_metrics: Dict[str, Any]


class OptimizedReportGenerator:
    """优化版报告生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.placeholder_processor = PlaceholderProcessor()
        self.report_composer = ReportCompositionService()
        
    async def generate_report_optimized(
        self,
        template_content: str,
        data_source_id: str,
        user_id: str,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> OptimizedReportResult:
        """
        优化版报告生成
        
        Args:
            template_content: 模板内容
            data_source_id: 数据源ID
            user_id: 用户ID  
            generation_config: 生成配置
            
        Returns:
            优化报告生成结果
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting optimized report generation for user {user_id}")
            
            # 阶段1: 批量提取和分析占位符
            phase1_start = time.time()
            placeholders = self.placeholder_processor.extract_placeholders(template_content)
            
            if not placeholders:
                return OptimizedReportResult(
                    success=True,
                    report_content=template_content,
                    generation_time=time.time() - start_time,
                    placeholders_processed=0,
                    llm_calls_saved=0,
                    data_queries_executed=0,
                    cache_hits=0,
                    errors=[],
                    performance_metrics={"no_placeholders": True}
                )
            
            # 获取数据源信息
            with get_db_session() as db:
                data_source = crud_data_source.get(db, id=data_source_id)
                if not data_source:
                    raise ValueError(f"Data source not found: {data_source_id}")
            
            # 创建AI服务和批量处理器
            ai_service = AIService(db)
            batch_processor = BatchPlaceholderProcessor(ai_service)
            
            # 批量处理占位符
            batch_result = await batch_processor.process_placeholders_batch(
                placeholders=placeholders,
                data_source_id=data_source_id,
                max_batch_size=generation_config.get('batch_size', 10) if generation_config else 10
            )
            
            phase1_time = time.time() - phase1_start
            self.logger.info(f"Phase 1 completed in {phase1_time:.2f}s, saved {batch_result.llm_calls_saved} LLM calls")
            
            # 阶段2: 并行数据查询和MCP工具调用
            phase2_start = time.time()
            
            async with get_async_mcp_client() as mcp_client:
                placeholder_results = await self._process_placeholders_parallel(
                    batch_result.processed_placeholders,
                    data_source,
                    mcp_client
                )
            
            phase2_time = time.time() - phase2_start
            self.logger.info(f"Phase 2 completed in {phase2_time:.2f}s")
            
            # 阶段3: 组合最终报告
            phase3_start = time.time()
            
            final_content = self.report_composer.compose_report(
                template_content=template_content,
                results=placeholder_results
            )
            
            phase3_time = time.time() - phase3_start
            total_time = time.time() - start_time
            
            # 统计性能指标
            cache_hits = sum(1 for result in placeholder_results.values() 
                           if isinstance(result, dict) and result.get('cache_hit', False))
            
            return OptimizedReportResult(
                success=True,
                report_content=final_content,
                generation_time=total_time,
                placeholders_processed=len(placeholders),
                llm_calls_saved=batch_result.llm_calls_saved,
                data_queries_executed=len([r for r in placeholder_results.values() 
                                         if isinstance(r, dict) and 'query_result' in r]),
                cache_hits=cache_hits,
                errors=[],
                performance_metrics={
                    "phase1_time": phase1_time,
                    "phase2_time": phase2_time, 
                    "phase3_time": phase3_time,
                    "total_time": total_time,
                    "placeholders_per_second": len(placeholders) / total_time,
                    "batch_processing_efficiency": batch_result.llm_calls_saved / len(placeholders) if placeholders else 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"Optimized report generation failed: {e}")
            return OptimizedReportResult(
                success=False,
                report_content="",
                generation_time=time.time() - start_time,
                placeholders_processed=0,
                llm_calls_saved=0,
                data_queries_executed=0,
                cache_hits=0,
                errors=[str(e)],
                performance_metrics={}
            )
    
    async def _process_placeholders_parallel(
        self,
        processed_placeholders: Dict[str, Any],
        data_source,
        mcp_client
    ) -> Dict[str, Any]:
        """并行处理占位符"""
        
        results = {}
        
        # 按类型分组占位符
        query_tasks = []
        mcp_tasks = []
        
        for placeholder, analysis in processed_placeholders.items():
            if analysis.get('error'):
                # 处理有错误的占位符
                results[placeholder] = f"[错误: {analysis['error']}]"
                continue
                
            # 判断处理类型
            if self._needs_data_query(analysis):
                # 需要数据查询
                task = self._create_data_query_task(placeholder, analysis, data_source)
                query_tasks.append(task)
            else:
                # 需要MCP工具处理
                task = self._create_mcp_task(placeholder, analysis, mcp_client)
                mcp_tasks.append(task)
        
        # 并行执行所有任务
        all_tasks = query_tasks + mcp_tasks
        if all_tasks:
            task_results = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            # 处理任务结果
            for i, result in enumerate(task_results):
                if isinstance(result, Exception):
                    placeholder = list(processed_placeholders.keys())[i]
                    results[placeholder] = f"[处理错误: {str(result)}]"
                else:
                    results.update(result)
        
        return results
    
    def _needs_data_query(self, analysis: Dict[str, Any]) -> bool:
        """判断是否需要数据查询"""
        # 根据分析结果判断是否需要直接查询数据
        calculation_type = analysis.get('calculation_type', '')
        return calculation_type in ['sum', 'count', 'avg', 'max', 'min']
    
    async def _create_data_query_task(self, placeholder: str, analysis: Dict[str, Any], data_source):
        """创建数据查询任务"""
        
        async def query_task():
            try:
                # 构建查询参数
                filters = {}
                aggregations = []
                
                if analysis.get('calculation_type'):
                    aggregations.append({
                        'function': analysis['calculation_type'],
                        'field': analysis.get('field_suggestions', [placeholder])[0]
                    })
                
                # 使用查询优化器执行查询
                result = await query_optimizer.optimize_and_execute(
                    data_source=data_source,
                    base_query=f"SELECT * FROM {data_source.wide_table_name or 'main_table'}",
                    filters=filters,
                    aggregations=aggregations
                )
                
                # 提取结果值
                if not result.data.empty:
                    if analysis.get('calculation_type') == 'count':
                        value = len(result.data)
                    else:
                        # 获取聚合结果
                        value = result.data.iloc[0, 0] if len(result.data) > 0 else 0
                else:
                    value = 0
                
                return {
                    placeholder: {
                        'value': value,
                        'query_result': True,
                        'execution_time': result.execution_time,
                        'cache_hit': result.cache_hit
                    }
                }
                
            except Exception as e:
                return {placeholder: f"[查询错误: {str(e)}]"}
        
        return query_task()
    
    async def _create_mcp_task(self, placeholder: str, analysis: Dict[str, Any], mcp_client):
        """创建MCP工具任务"""
        
        async def mcp_task():
            try:
                # 根据占位符类型选择MCP工具
                tool_type = MCPToolType.TEXT_SUMMARY
                endpoint = "/tools/generate-text"
                
                # 检查是否需要图表生成
                if '图表' in placeholder or 'chart' in placeholder.lower():
                    tool_type = MCPToolType.CHART_GENERATION
                    endpoint = "/tools/generate-chart"
                
                payload = {
                    'description': analysis.get('field_suggestions', [placeholder])[0],
                    'context': placeholder,
                    'analysis': analysis
                }
                
                # 调用MCP工具
                response = await mcp_client.call_tool(
                    tool_type=tool_type,
                    endpoint=endpoint,
                    payload=payload
                )
                
                if response.success:
                    return {
                        placeholder: {
                            'value': response.data,
                            'mcp_result': True,
                            'execution_time': response.execution_time,
                            'cache_hit': response.cached
                        }
                    }
                else:
                    return {placeholder: f"[MCP错误: {response.error}]"}
                    
            except Exception as e:
                return {placeholder: f"[MCP任务错误: {str(e)}]"}
        
        return mcp_task()


# 创建全局优化生成器实例
optimized_report_generator = OptimizedReportGenerator()