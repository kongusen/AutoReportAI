"""
Agent增强模板服务
集成智能占位符服务，提供基于Agent的模板处理功能
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

# 延迟导入避免循环依赖
# from ..placeholder import (
#     get_intelligent_placeholder_service,
#     analyze_template_placeholders,
#     execute_placeholder_workflow,
#     TimeContext, BusinessContext, DocumentContext
# )
from ..placeholder.models import TimeContext, BusinessContext, DocumentContext
from .template_cache_service import TemplateCacheService

logger = logging.getLogger(__name__)


class AgentEnhancedTemplateService:
    """
    Agent增强模板服务
    
    功能特性：
    1. 基于Agent的智能占位符分析
    2. 模板上下文感知处理
    3. 缓存优化和性能管理
    4. 批量模板处理
    5. 模板质量评估和优化建议
    """
    
    def __init__(self, db_session: Session, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for Agent Enhanced Template Service")
        self.db = db_session
        self.user_id = user_id
        self.cache_service = TemplateCacheService()
        self._placeholder_service = None
        self.initialized = False
    
    async def initialize(self):
        """初始化服务"""
        if self.initialized:
            return
        
        logger.info("初始化Agent增强模板服务...")
        
        try:
            # 初始化智能占位符服务（延迟导入）
            from ..placeholder import get_intelligent_placeholder_service
            self._placeholder_service = await get_intelligent_placeholder_service()
            
            # 初始化缓存服务
            await self.cache_service.initialize()
            
            self.initialized = True
            logger.info("Agent增强模板服务初始化完成")
            
        except Exception as e:
            logger.error(f"Agent增强模板服务初始化失败: {e}")
            raise
    
    async def analyze_template(
        self,
        template_id: str,
        template_content: str,
        template_metadata: Optional[Dict[str, Any]] = None,
        context_data: Optional[Dict[str, Any]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        分析模板并提取占位符
        
        Args:
            template_id: 模板ID
            template_content: 模板内容
            template_metadata: 模板元数据
            context_data: 上下文数据
            force_refresh: 是否强制刷新缓存
            
        Returns:
            模板分析结果
        """
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"开始分析模板: {template_id}")
        
        try:
            # 构建模板元数据
            metadata = template_metadata or {}
            metadata.update({
                "id": template_id,
                "analysis_timestamp": datetime.utcnow().isoformat()
            })
            
            # 解析上下文数据
            time_context = None
            business_context = None
            document_context = None
            
            if context_data:
                time_context = self._parse_time_context(context_data.get("time_context"))
                business_context = self._parse_business_context(context_data.get("business_context"))
                document_context = self._parse_document_context(context_data.get("document_context"))
            
            # 使用智能占位符服务分析（方法可能已更改）
            # analysis_result = await self._placeholder_service.analyze_template_placeholders(
            # 使用新的DAG架构方法
            analysis_result = await self._placeholder_service.analyze_template_for_sql_generation(
                template_content=template_content,
                template_metadata=metadata,
                time_context=time_context,
                business_context=business_context,
                document_context=document_context,
                force_refresh=force_refresh
            )
            
            # 转换为模板服务格式
            return self._format_template_analysis_result(analysis_result)
            
        except Exception as e:
            logger.error(f"模板分析失败: {template_id}, 错误: {e}")
            return {
                "success": False,
                "template_id": template_id,
                "error": str(e),
                "placeholders": [],
                "analysis_summary": {
                    "total_placeholders": 0,
                    "successful_analyses": 0,
                    "failed_analyses": 0,
                    "overall_confidence": 0.0
                }
            }
    
    async def execute_template_workflow(
        self,
        template_id: str,
        data_source_id: str,
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行模板工作流
        
        Args:
            template_id: 模板ID
            data_source_id: 数据源ID
            workflow_context: 工作流上下文
            
        Returns:
            工作流执行结果
        """
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"执行模板工作流: template={template_id}, data_source={data_source_id}")
        
        try:
            # 在DAG架构下，直接使用占位符服务
            # workflow_result = await execute_placeholder_workflow(
            #     template_id=template_id,
            #     data_source_id=data_source_id,  
            #     execution_context=workflow_context
            # )
            # 使用新的DAG架构方法
            workflow_result = await self._placeholder_service.analyze_task_for_chart_generation(
                template_content=workflow_context.get("template_content", ""),
                etl_data=workflow_context.get("etl_data", {}),
                task_id=template_id,
                execution_date=workflow_context.get("execution_date"),
                task_period_config=workflow_context.get("task_period_config", {})
            )
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"模板工作流执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "template_id": template_id,
                "data_source_id": data_source_id
            }
    
    async def batch_analyze_templates(
        self,
        template_specs: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """
        批量分析多个模板
        
        Args:
            template_specs: 模板规格列表，每个包含id, content, metadata等
            max_concurrent: 最大并发数
            
        Returns:
            批量分析结果
        """
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"批量分析 {len(template_specs)} 个模板")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def analyze_single_template(spec):
            async with semaphore:
                try:
                    result = await self.analyze_template(
                        template_id=spec["id"],
                        template_content=spec["content"],
                        template_metadata=spec.get("metadata"),
                        context_data=spec.get("context_data")
                    )
                    return result
                except Exception as e:
                    return {
                        "success": False,
                        "template_id": spec["id"],
                        "error": str(e)
                    }
        
        # 并发执行分析任务
        tasks = [analyze_single_template(spec) for spec in template_specs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        successful_analyses = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed_analyses = len(results) - successful_analyses
        
        return {
            "success": successful_analyses > 0,
            "total_templates": len(template_specs),
            "successful_analyses": successful_analyses,
            "failed_analyses": failed_analyses,
            "results": results,
            "processing_summary": {
                "max_concurrent": max_concurrent,
                "success_rate": successful_analyses / len(template_specs) if template_specs else 0
            }
        }
    
    async def get_template_placeholder_configs(
        self,
        template_id: str,
        include_analysis_details: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取模板的占位符配置
        
        Args:
            template_id: 模板ID
            include_analysis_details: 是否包含详细分析信息
            
        Returns:
            占位符配置列表
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # 从缓存或数据库获取配置
            cached_configs = await self.cache_service.get_template_placeholder_configs(template_id)
            
            if cached_configs:
                logger.info(f"从缓存获取模板占位符配置: {template_id}")
                return cached_configs
            
            # 如果缓存中没有，返回空列表并建议先分析
            logger.warning(f"模板 {template_id} 尚未进行占位符分析")
            return []
            
        except Exception as e:
            logger.error(f"获取模板占位符配置失败: {template_id}, 错误: {e}")
            return []
    
    async def validate_template_readiness(
        self,
        template_id: str
    ) -> Dict[str, Any]:
        """
        验证模板是否准备就绪
        
        Args:
            template_id: 模板ID
            
        Returns:
            验证结果
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            configs = await self.get_template_placeholder_configs(template_id, True)
            
            if not configs:
                return {
                    "ready": False,
                    "reason": "模板尚未进行占位符分析",
                    "recommendations": ["请先执行模板分析"]
                }
            
            # 检查分析状态
            analyzed_count = sum(1 for config in configs if config.get("agent_analyzed", False))
            validated_count = sum(1 for config in configs if config.get("sql_validated", False))
            
            total_count = len(configs)
            ready = analyzed_count == total_count and validated_count == total_count
            
            analysis_rate = analyzed_count / total_count if total_count > 0 else 0
            validation_rate = validated_count / total_count if total_count > 0 else 0
            
            avg_confidence = 0.0
            if configs:
                confidence_scores = [c.get("confidence_score", 0.0) for c in configs if c.get("confidence_score")]
                avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            recommendations = []
            if analysis_rate < 1.0:
                recommendations.append(f"还有 {total_count - analyzed_count} 个占位符需要Agent分析")
            if validation_rate < 1.0:
                recommendations.append(f"还有 {total_count - validated_count} 个占位符需要SQL验证")
            if avg_confidence < 0.7:
                recommendations.append(f"平均置信度较低 ({avg_confidence:.2f})，建议人工审核")
            
            if ready:
                recommendations.append("模板已准备就绪，可以执行工作流")
            
            return {
                "ready": ready,
                "total_placeholders": total_count,
                "analyzed_placeholders": analyzed_count,
                "validated_placeholders": validated_count,
                "analysis_rate": analysis_rate,
                "validation_rate": validation_rate,
                "average_confidence": avg_confidence,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"模板准备状态验证失败: {template_id}, 错误: {e}")
            return {
                "ready": False,
                "reason": f"验证失败: {str(e)}",
                "recommendations": ["请检查系统状态并重试"]
            }
    
    def _parse_time_context(self, time_data: Optional[Dict[str, Any]]) -> Optional[TimeContext]:
        """解析时间上下文"""
        if not time_data:
            return None
        
        try:
            return TimeContext(
                report_period=time_data.get("report_period", ""),
                period_type=time_data.get("period_type", "monthly"),
                start_date=datetime.fromisoformat(time_data.get("start_date", datetime.utcnow().isoformat())),
                end_date=datetime.fromisoformat(time_data.get("end_date", datetime.utcnow().isoformat())),
                previous_period_start=datetime.fromisoformat(time_data.get("previous_period_start", datetime.utcnow().isoformat())),
                previous_period_end=datetime.fromisoformat(time_data.get("previous_period_end", datetime.utcnow().isoformat())),
                fiscal_year=time_data.get("fiscal_year", str(datetime.utcnow().year)),
                quarter=time_data.get("quarter", "Q1")
            )
        except Exception as e:
            logger.warning(f"解析时间上下文失败: {e}")
            return None
    
    def _parse_business_context(self, business_data: Optional[Dict[str, Any]]) -> Optional[BusinessContext]:
        """解析业务上下文"""
        if not business_data:
            return None
        
        try:
            return BusinessContext(
                task_type=business_data.get("task_type", "general_report"),
                department=business_data.get("department", "general"),
                report_level=business_data.get("report_level", "summary"),
                data_granularity=business_data.get("data_granularity", "daily"),
                include_comparisons=business_data.get("include_comparisons", True),
                target_audience=business_data.get("target_audience", "analyst")
            )
        except Exception as e:
            logger.warning(f"解析业务上下文失败: {e}")
            return None
    
    def _parse_document_context(self, document_data: Optional[Dict[str, Any]]) -> Optional[DocumentContext]:
        """解析文档上下文"""
        if not document_data:
            return None
        
        try:
            return DocumentContext(
                document_id=document_data.get("document_id", "unknown"),
                paragraph_content=document_data.get("paragraph_content", ""),
                paragraph_index=document_data.get("paragraph_index", 0),
                section_title=document_data.get("section_title", ""),
                section_index=document_data.get("section_index", 0),
                surrounding_text=document_data.get("surrounding_text", ""),
                document_structure=document_data.get("document_structure", {})
            )
        except Exception as e:
            logger.warning(f"解析文档上下文失败: {e}")
            return None
    
    def _format_template_analysis_result(self, analysis_result) -> Dict[str, Any]:
        """格式化模板分析结果"""
        placeholders = []
        
        for result in analysis_result.analysis_results:
            placeholder_info = {
                "id": result.placeholder_spec.get_hash(),
                "raw_text": result.placeholder_spec.raw_text,
                "description": result.placeholder_spec.description,
                "statistical_type": result.placeholder_spec.statistical_type.value,
                "syntax_type": result.placeholder_spec.syntax_type.value,
                "confidence_score": result.confidence_score,
                "success": result.success,
                "generated_sql": result.generated_sql,
                "sql_quality_score": result.sql_quality_score,
                "analysis_insights": result.analysis_insights,
                "agent_reasoning": result.agent_reasoning,
                "processing_time_ms": result.processing_time_ms,
                "sources": result.sources
            }
            
            if result.error_message:
                placeholder_info["error"] = result.error_message
            
            # 添加参数信息（如果适用）
            if hasattr(result.placeholder_spec, 'parameters'):
                placeholder_info["parameters"] = result.placeholder_spec.parameters
            
            placeholders.append(placeholder_info)
        
        return {
            "success": analysis_result.success,
            "template_id": analysis_result.template_id,
            "placeholders": placeholders,
            "analysis_summary": {
                "total_placeholders": analysis_result.total_placeholders,
                "successful_analyses": analysis_result.successfully_analyzed,
                "failed_analyses": analysis_result.total_placeholders - analysis_result.successfully_analyzed,
                "overall_confidence": analysis_result.overall_confidence,
                "processing_time_ms": analysis_result.processing_time_ms
            },
            "error_message": analysis_result.error_message if hasattr(analysis_result, 'error_message') else None
        }
    
    async def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        if not self.initialized:
            return {"status": "not_initialized"}
        
        try:
            placeholder_status = await self._placeholder_service.get_service_status()
            cache_status = await self.cache_service.get_cache_status()
            
            return {
                "status": "running",
                "initialized": self.initialized,
                "placeholder_service": placeholder_status,
                "cache_service": cache_status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# 全局服务实例
_global_template_service: Optional[AgentEnhancedTemplateService] = None


async def get_agent_enhanced_template_service(
    db_session: Optional[Session] = None
) -> AgentEnhancedTemplateService:
    """获取全局Agent增强模板服务实例"""
    global _global_template_service
    if _global_template_service is None:
        _global_template_service = AgentEnhancedTemplateService(db_session)
        await _global_template_service.initialize()
    return _global_template_service


# 便捷函数
async def analyze_template_with_agents(
    template_id: str,
    template_content: str,
    template_metadata: Optional[Dict[str, Any]] = None,
    context_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """使用Agent分析模板的便捷函数"""
    service = await get_agent_enhanced_template_service()
    return await service.analyze_template(
        template_id, template_content, template_metadata, context_data
    )


async def execute_template_with_agents(
    template_id: str,
    data_source_id: str,
    workflow_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """使用Agent执行模板工作流的便捷函数"""
    service = await get_agent_enhanced_template_service()
    return await service.execute_template_workflow(
        template_id, data_source_id, workflow_context
    )