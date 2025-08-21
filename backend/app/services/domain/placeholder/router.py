"""
占位符处理路由层

负责流程协调、参数验证、响应封装
"""
import logging
from typing import Dict, Any
from datetime import datetime

from .models import (
    PlaceholderRequest, PlaceholderResponse, ResultSource,
    CacheServiceInterface, AgentAnalysisServiceInterface, 
    TemplateRuleServiceInterface, DataExecutionServiceInterface
)


class PlaceholderRouter:
    """占位符处理路由器 - 纯粹的流程协调"""
    
    def __init__(
        self, 
        cache_service: CacheServiceInterface,
        agent_service: AgentAnalysisServiceInterface,
        rule_service: TemplateRuleServiceInterface,
        execution_service: DataExecutionServiceInterface
    ):
        self.cache_service = cache_service
        self.agent_service = agent_service
        self.rule_service = rule_service
        self.execution_service = execution_service
        self.logger = logging.getLogger(__name__)
    
    async def process_placeholder(self, request: PlaceholderRequest) -> PlaceholderResponse:
        """处理占位符请求 - 纯粹的流程协调"""
        start_time = datetime.now()
        
        try:
            # 1. 参数验证
            self._validate_request(request)
            self.logger.info(f"开始处理占位符: {request.placeholder_name}")
            
            # 2. 缓存检查
            if not request.force_reanalyze:
                self.logger.debug("检查缓存...")
                cached_result = await self.cache_service.get_result(request)
                if cached_result:
                    self.logger.info(f"缓存命中: {request.placeholder_name}")
                    return self._create_response_from_cache(cached_result)
            
            # 3. Agent分析和执行
            self.logger.info("开始Agent分析...")
            agent_result = await self.agent_service.analyze_and_execute(request)
            
            if agent_result.success:
                # Agent成功 - 缓存结果
                self.logger.info(f"Agent处理成功: {request.placeholder_name}")
                await self.cache_service.save_result(request, agent_result)
                return self._create_response_from_agent(agent_result, start_time)
            
            # 4. 规则模板fallback (不缓存)
            self.logger.info(f"Agent失败，使用规则fallback: {agent_result.error_message}")
            rule_result = await self.rule_service.generate_and_execute(
                request, agent_result.error_context
            )
            
            if rule_result.success:
                self.logger.info(f"规则处理成功: {request.placeholder_name}")
                return self._create_response_from_rule(rule_result, start_time)
            
            # 5. 最终错误fallback
            self.logger.error(f"所有处理方式都失败: {rule_result.error_message}")
            return self._create_error_response(rule_result.error_message, start_time)
            
        except Exception as e:
            self.logger.error(f"处理占位符异常: {request.placeholder_name}, 错误: {str(e)}", exc_info=True)
            return self._create_error_response(f"处理异常: {str(e)}", start_time)
    
    def _validate_request(self, request: PlaceholderRequest):
        """验证请求参数"""
        if not request.placeholder_id:
            raise ValueError("placeholder_id is required")
        if not request.data_source_id:
            raise ValueError("data_source_id is required")
        if not request.user_id:
            raise ValueError("user_id is required")
    
    def _create_response_from_cache(self, cached_result) -> PlaceholderResponse:
        """从缓存结果创建响应"""
        return PlaceholderResponse(
            success=True,
            value=cached_result.value,
            source=ResultSource.CACHE_HIT,
            execution_time_ms=0,  # 缓存读取时间忽略不计
            confidence=cached_result.confidence,
            metadata={
                "cached_at": cached_result.cached_at.isoformat(),
                "source_metadata": cached_result.source_metadata
            }
        )
    
    def _create_response_from_agent(self, agent_result, start_time: datetime) -> PlaceholderResponse:
        """从Agent结果创建响应"""
        total_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return PlaceholderResponse(
            success=True,
            value=agent_result.formatted_value,
            source=ResultSource.AGENT_SUCCESS,
            execution_time_ms=total_time_ms,
            confidence=agent_result.confidence,
            metadata={
                "agent_execution_time_ms": agent_result.execution_time_ms,
                "row_count": agent_result.row_count,
                "agent_metadata": agent_result.metadata
            }
        )
    
    def _create_response_from_rule(self, rule_result, start_time: datetime) -> PlaceholderResponse:
        """从规则结果创建响应"""
        total_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return PlaceholderResponse(
            success=True,
            value=rule_result.formatted_value,
            source=ResultSource.RULE_FALLBACK,
            execution_time_ms=total_time_ms,
            confidence=0.5,  # 规则生成的置信度较低
            metadata={
                "rule_type": rule_result.rule_type,
                "rule_execution_time_ms": rule_result.execution_time_ms,
                "rule_metadata": rule_result.metadata
            }
        )
    
    def _create_error_response(self, error_message: str, start_time: datetime) -> PlaceholderResponse:
        """创建错误响应"""
        total_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return PlaceholderResponse(
            success=False,
            value="数据获取失败",
            source=ResultSource.ERROR_FALLBACK,
            execution_time_ms=total_time_ms,
            error_message=error_message
        )


class PlaceholderBatchRouter:
    """批量占位符处理路由器"""
    
    def __init__(self, single_router: PlaceholderRouter):
        self.single_router = single_router
        self.logger = logging.getLogger(__name__)
    
    async def process_template_placeholders(
        self,
        template_id: str,
        data_source_id: str,
        user_id: str,
        force_reanalyze: bool = False,
        execution_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """批量处理模板的所有占位符"""
        import asyncio
        from app.models.template_placeholder import TemplatePlaceholder
        from app.db.session import SessionLocal
        
        start_time = datetime.now()
        
        try:
            # 获取模板的所有激活占位符
            db = SessionLocal()
            try:
                placeholders = db.query(TemplatePlaceholder).filter(
                    TemplatePlaceholder.template_id == template_id,
                    TemplatePlaceholder.is_active == True
                ).all()
                
                if not placeholders:
                    return {
                        "success": False,
                        "error": "模板没有激活的占位符",
                        "template_id": template_id,
                        "results": {}
                    }
                
                # 准备批量请求
                requests = []
                for placeholder in placeholders:
                    request = PlaceholderRequest(
                        placeholder_id=str(placeholder.id),
                        placeholder_name=placeholder.placeholder_name,
                        placeholder_type=placeholder.placeholder_type,
                        data_source_id=data_source_id,
                        user_id=user_id,
                        force_reanalyze=force_reanalyze,
                        execution_time=datetime.fromisoformat(
                            execution_context.get("execution_time", datetime.now().isoformat())
                        ) if execution_context else datetime.now(),
                        metadata=execution_context or {}
                    )
                    requests.append(request)
                
                # 并行处理所有占位符
                self.logger.info(f"开始批量处理 {len(requests)} 个占位符")
                tasks = [
                    self.single_router.process_placeholder(request)
                    for request in requests
                ]
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 整理结果
                execution_results = {}
                successful_count = 0
                total_execution_time = 0
                cache_hits = 0
                agent_successes = 0
                rule_fallbacks = 0
                
                for placeholder, response in zip(placeholders, responses):
                    if isinstance(response, Exception):
                        response = PlaceholderResponse(
                            success=False,
                            value=f"处理异常: {str(response)}",
                            source=ResultSource.ERROR_FALLBACK,
                            execution_time_ms=0,
                            error_message=str(response)
                        )
                    
                    execution_results[placeholder.placeholder_name] = {
                        "success": response.success,
                        "value": response.value,
                        "source": response.source.value,
                        "execution_time_ms": response.execution_time_ms,
                        "confidence": response.confidence,
                        "error_message": response.error_message,
                        "metadata": response.metadata
                    }
                    
                    if response.success:
                        successful_count += 1
                    
                    total_execution_time += response.execution_time_ms
                    
                    # 统计结果来源
                    if response.source == ResultSource.CACHE_HIT:
                        cache_hits += 1
                    elif response.source == ResultSource.AGENT_SUCCESS:
                        agent_successes += 1
                    elif response.source == ResultSource.RULE_FALLBACK:
                        rule_fallbacks += 1
                
                total_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    "success": True,
                    "template_id": template_id,
                    "data_source_id": data_source_id,
                    "execution_summary": {
                        "total_placeholders": len(placeholders),
                        "successful_placeholders": successful_count,
                        "success_rate": (successful_count / len(placeholders)) * 100,
                        "total_execution_time_ms": total_execution_time,
                        "total_processing_time_seconds": total_time,
                        "cache_hits": cache_hits,
                        "agent_successes": agent_successes,
                        "rule_fallbacks": rule_fallbacks,
                        "execution_time": start_time.isoformat()
                    },
                    "results": execution_results
                }
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"批量处理占位符失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "template_id": template_id,
                "data_source_id": data_source_id
            }