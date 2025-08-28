"""
IAOP AI服务适配器 - 将IAOP平台集成为主要AI处理引擎

这个适配器替代现有的AI服务，提供兼容的接口，但使用IAOP平台进行实际处理
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..core.integration import get_iaop_integrator
from ..api.schemas import (
    ReportGenerationRequest,
    PlaceholderRequest, 
    TaskType,
    ExecutionMode,
    AgentExecutionRequest
)

# AI服务数据结构 - 直接定义避免循环导入
from app.models.data_source import DataSource
from app import crud

logger = logging.getLogger(__name__)


@dataclass
class AIRequest:
    """AI请求数据结构"""
    content: str
    task_type: str
    context: Dict[str, Any] = None
    metadata: Dict[str, Any] = None


@dataclass  
class AIResponse:
    """AI响应数据结构"""
    success: bool
    data: Dict[str, Any] = None
    error: str = None
    metadata: Dict[str, Any] = None
    

@dataclass
class AIServiceMetrics:
    """AI服务指标"""
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0


@dataclass
class IAOPAIRequest:
    """IAOP AI请求 - 扩展版"""
    placeholder_text: str
    context: Dict[str, Any]
    task_type: Optional[str] = None
    data_source_id: Optional[str] = None
    template_id: Optional[str] = None
    execution_mode: str = "sequential"


@dataclass 
class IAOPAIResponse:
    """IAOP AI响应 - 扩展版"""
    content: str
    success: bool
    execution_time: float
    confidence_score: float
    chart_config: Optional[Dict[str, Any]] = None
    narrative: Optional[str] = None
    raw_data: Optional[Any] = None
    error_message: Optional[str] = None
    source: str = "iaop"


class IAOPAIService:
    """IAOP AI服务 - 替代现有AI服务的主要类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.integrator = get_iaop_integrator()
        self.metrics = AIServiceMetrics()
        self._initialized = False
        
        logger.info("IAOP AI服务初始化")
    
    async def _ensure_initialized(self):
        """确保IAOP系统已初始化"""
        if not self._initialized:
            if not self.integrator._initialized:
                await self.integrator.initialize()
            self._initialized = True
    
    async def chat_completion(self, request: AIRequest, use_cache: bool = True) -> AIResponse:
        """
        聊天完成 - 使用IAOP平台处理
        保持与原有AI服务相同的接口签名
        """
        await self._ensure_initialized()
        
        start_time = datetime.utcnow()
        
        try:
            # 将传统AI请求转换为IAOP请求
            iaop_request = await self._convert_ai_request_to_iaop(request)
            
            # 使用IAOP平台处理
            result = await self._process_with_iaop(iaop_request)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 转换为兼容的AI响应格式
            ai_response = AIResponse(
                content=result.content,
                model="iaop-integrated",
                usage={
                    "prompt_tokens": len(str(request.messages)),
                    "completion_tokens": len(result.content),
                    "total_tokens": len(str(request.messages)) + len(result.content)
                },
                response_time=execution_time,
                timestamp=start_time
            )
            
            # 记录指标
            self.metrics.record_request(
                "iaop-integrated", 
                ai_response.usage["total_tokens"], 
                0.0,  # IAOP不计费
                execution_time,
                result.success
            )
            
            return ai_response
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics.record_request("iaop-integrated", 0, 0, execution_time, False)
            logger.error(f"IAOP AI请求失败: {e}")
            raise ValueError(f"AI请求失败: {str(e)}")
    
    async def analyze_placeholder_requirements(
        self, 
        placeholder_data: Dict[str, Any], 
        data_source_id: str
    ) -> Dict[str, Any]:
        """
        占位符需求分析 - 使用IAOP平台的核心功能
        这是替代原有AI服务的核心方法
        """
        await self._ensure_initialized()
        
        start_time = datetime.utcnow()
        
        try:
            # 获取数据源信息
            data_source = self.db.query(DataSource).filter(DataSource.id == data_source_id).first()
            if not data_source:
                raise ValueError(f"数据源 {data_source_id} 不存在")
            
            # 创建IAOP处理请求
            iaop_request = ReportGenerationRequest(
                placeholder_text=placeholder_data.get('name', '') + ': ' + placeholder_data.get('description', ''),
                task_type=self._map_placeholder_type_to_task_type(placeholder_data.get('type', 'text')),
                data_source_context={
                    "data_source_id": data_source_id,
                    "data_source_name": data_source.name,
                    "source_type": data_source.source_type.value,
                    "doris_database": getattr(data_source, 'doris_database', ''),
                    "doris_fe_hosts": getattr(data_source, 'doris_fe_hosts', [])
                },
                template_context={
                    "placeholder_data": placeholder_data
                },
                execution_mode=ExecutionMode.SEQUENTIAL
            )
            
            # 使用IAOP服务处理
            service_factory = self.integrator.get_service_factory()
            iaop_service = await service_factory.get_iaop_service()
            
            result = await iaop_service.generate_report(iaop_request)
            
            if result.success:
                # 构造兼容的ETL指令格式
                etl_instruction = self._convert_iaop_result_to_etl_instruction(
                    result, placeholder_data, data_source
                )
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                return {
                    "placeholder": placeholder_data,
                    "etl_instruction": etl_instruction,
                    "data_source_id": data_source_id,
                    "analysis_time": start_time.isoformat(),
                    "execution_time": execution_time,
                    "source": "iaop_platform",
                    "confidence_score": result.confidence_score,
                    "success": True
                }
            else:
                raise ValueError(f"IAOP处理失败: {result.error_message}")
                
        except Exception as e:
            logger.error(f"IAOP占位符分析失败: {placeholder_data.get('name', '')}, 错误: {e}")
            
            # 使用传统方法作为fallback
            return await self._fallback_placeholder_analysis(placeholder_data, data_source_id)
    
    async def interpret_natural_language_query(
        self,
        query: str,
        context: Dict[str, Any],
        available_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """自然语言查询解释 - 使用IAOP平台"""
        await self._ensure_initialized()
        
        try:
            # 使用IAOP的PlaceholderParserAgent
            service_factory = self.integrator.get_service_factory()
            agent_registry = await service_factory.get_agent_registry()
            
            parser_agent = agent_registry.get_agent("placeholder_parser")
            if parser_agent:
                # 创建执行上下文
                context_manager = await service_factory.get_context_manager()
                execution_context = context_manager.create_context("nlq_user", f"nlq_{datetime.utcnow().timestamp()}")
                
                # 准备输入数据
                input_data = {
                    "natural_language_query": query,
                    "context": context,
                    "available_columns": available_columns or [],
                    "task": "query_interpretation"
                }
                
                result = await parser_agent.execute(execution_context, input_data)
                
                if result.get("success"):
                    parsed_query = result.get("output", {})
                    return self._format_nlq_result(parsed_query, available_columns)
            
            # Fallback到默认解析
            return self._default_nlq_interpretation(query, available_columns)
            
        except Exception as e:
            logger.error(f"IAOP自然语言查询解释失败: {e}")
            return self._default_nlq_interpretation(query, available_columns)
    
    async def generate_insights(
        self, data_summary: Dict[str, Any], context: str = ""
    ) -> str:
        """生成洞察 - 使用IAOP的InsightNarratorAgent"""
        await self._ensure_initialized()
        
        try:
            service_factory = self.integrator.get_service_factory()
            agent_registry = await service_factory.get_agent_registry()
            
            narrator_agent = agent_registry.get_agent("insight_narrator")
            if narrator_agent:
                # 创建执行上下文
                context_manager = await service_factory.get_context_manager()
                execution_context = context_manager.create_context("insight_user", f"insight_{datetime.utcnow().timestamp()}")
                
                # 准备输入数据
                input_data = {
                    "data_summary": data_summary,
                    "context": context,
                    "language": "zh",
                    "format": "professional_insights"
                }
                
                result = await narrator_agent.execute(execution_context, input_data)
                
                if result.get("success"):
                    return result.get("output", {}).get("insights", "未能生成洞察")
            
            # Fallback
            return self._generate_default_insights(data_summary, context)
            
        except Exception as e:
            logger.error(f"IAOP洞察生成失败: {e}")
            return self._generate_default_insights(data_summary, context)
    
    async def generate_chart_config(
        self,
        data: List[Dict[str, Any]],
        description: str,
        chart_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成图表配置 - 使用IAOP的ChartGeneratorAgent"""
        await self._ensure_initialized()
        
        try:
            service_factory = self.integrator.get_service_factory()
            agent_registry = await service_factory.get_agent_registry()
            
            chart_agent = agent_registry.get_agent("chart_generator")
            if chart_agent:
                # 创建执行上下文
                context_manager = await service_factory.get_context_manager()
                execution_context = context_manager.create_context("chart_user", f"chart_{datetime.utcnow().timestamp()}")
                
                # 准备输入数据
                input_data = {
                    "data": data,
                    "description": description,
                    "preferred_chart_type": chart_type,
                    "data_columns": list(data[0].keys()) if data else []
                }
                
                result = await chart_agent.execute(execution_context, input_data)
                
                if result.get("success"):
                    return result.get("output", {}).get("chart_config", {})
            
            # Fallback到默认配置
            return self._generate_default_chart_config(data, description, chart_type)
            
        except Exception as e:
            logger.error(f"IAOP图表配置生成失败: {e}")
            return self._generate_default_chart_config(data, description, chart_type)
    
    async def analyze_with_context(
        self,
        context: str,
        prompt: str,
        task_type: str,
        **kwargs
    ) -> str:
        """上下文分析 - 使用IAOP平台的综合分析能力"""
        await self._ensure_initialized()
        
        try:
            # 创建IAOP分析请求
            iaop_request = ReportGenerationRequest(
                placeholder_text=f"{task_type}: {prompt}",
                task_type=TaskType.DATA_ANALYSIS,
                template_context={
                    "analysis_context": context,
                    "task_type": task_type,
                    "additional_params": kwargs
                },
                execution_mode=ExecutionMode.SEQUENTIAL
            )
            
            # 使用IAOP服务处理
            service_factory = self.integrator.get_service_factory()
            iaop_service = await service_factory.get_iaop_service()
            
            result = await iaop_service.generate_report(iaop_request)
            
            if result.success:
                return result.narrative or result.content or "分析完成但无具体内容"
            else:
                raise ValueError(f"IAOP分析失败: {result.error_message}")
                
        except Exception as e:
            logger.error(f"IAOP上下文分析失败: {e}")
            return f"分析失败: {str(e)}"
    
    # 健康检查和兼容性方法
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            await self._ensure_initialized()
            status = self.integrator.get_system_status()
            
            return {
                "status": "healthy" if status.get("status") == "running" else "unhealthy",
                "provider": "IAOP Platform",
                "model": "iaop-integrated",
                "iaop_status": status,
                "metrics": self.metrics.get_metrics()
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": "IAOP Platform", 
                "message": str(e)
            }
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型 - 返回IAOP Agent列表"""
        try:
            await self._ensure_initialized()
            
            service_factory = self.integrator.get_service_factory()
            iaop_service = await service_factory.get_iaop_service()
            
            agents = await iaop_service.list_agents()
            
            # 转换为模型格式
            models = []
            for agent in agents:
                models.append({
                    "id": f"iaop-{agent.get('name', '')}",
                    "name": agent.get('name', ''),
                    "description": agent.get('description', ''),
                    "owned_by": "IAOP Platform",
                    "pricing": {"input": 0, "output": 0}  # IAOP不计费
                })
            
            return models
            
        except Exception as e:
            logger.error(f"获取IAOP模型列表失败: {e}")
            return [{
                "id": "iaop-integrated",
                "name": "IAOP Integrated Service",
                "owned_by": "IAOP Platform",
                "pricing": {"input": 0, "output": 0}
            }]
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """获取服务指标"""
        base_metrics = self.metrics.get_metrics()
        base_metrics.update({
            "service_type": "IAOP Platform",
            "initialized": self._initialized,
            "integrator_status": self.integrator.get_system_status() if self._initialized else None
        })
        return base_metrics
    
    def clear_cache(self):
        """清空缓存"""
        # IAOP平台有自己的缓存管理
        if self._initialized:
            middleware_manager = self.integrator.get_middleware_manager()
            if middleware_manager:
                logger.info("IAOP缓存清理由中间件管理器处理")
    
    def refresh_provider(self):
        """刷新提供商配置"""
        # IAOP使用配置管理系统
        if self._initialized:
            config_manager = self.integrator.config_manager
            logger.info("IAOP配置由配置管理器处理，无需刷新提供商")
    
    # 私有辅助方法
    
    async def _convert_ai_request_to_iaop(self, request: AIRequest) -> IAOPAIRequest:
        """将传统AI请求转换为IAOP请求"""
        # 从消息中提取占位符文本
        user_messages = [msg["content"] for msg in request.messages if msg.get("role") == "user"]
        placeholder_text = " ".join(user_messages)
        
        # 从系统消息中提取上下文
        system_messages = [msg["content"] for msg in request.messages if msg.get("role") == "system"]
        context = {"system_instructions": system_messages}
        
        return IAOPAIRequest(
            placeholder_text=placeholder_text,
            context=context,
            task_type="analysis",
            execution_mode="sequential"
        )
    
    async def _process_with_iaop(self, iaop_request: IAOPAIRequest) -> IAOPAIResponse:
        """使用IAOP平台处理请求"""
        try:
            # 创建IAOP报告生成请求
            report_request = ReportGenerationRequest(
                placeholder_text=iaop_request.placeholder_text,
                task_type=TaskType.CONTENT_GENERATION,
                template_context=iaop_request.context,
                execution_mode=ExecutionMode.SEQUENTIAL
            )
            
            # 执行处理
            service_factory = self.integrator.get_service_factory()
            iaop_service = await service_factory.get_iaop_service()
            
            result = await iaop_service.generate_report(report_request)
            
            return IAOPAIResponse(
                content=result.content or result.narrative or "处理完成",
                success=result.success,
                execution_time=result.execution_time_ms / 1000.0,
                confidence_score=result.confidence_score,
                chart_config=result.chart_config,
                narrative=result.narrative,
                error_message=result.error_message if not result.success else None
            )
            
        except Exception as e:
            return IAOPAIResponse(
                content="",
                success=False,
                execution_time=0,
                confidence_score=0,
                error_message=str(e)
            )
    
    def _map_placeholder_type_to_task_type(self, placeholder_type: str) -> TaskType:
        """映射占位符类型到IAOP任务类型"""
        type_mapping = {
            "统计": TaskType.DATA_QUERY,
            "图表": TaskType.CHART_GENERATION,
            "表格": TaskType.DATA_QUERY,
            "分析": TaskType.DATA_ANALYSIS,
            "日期时间": TaskType.DATA_QUERY,
            "标题": TaskType.CONTENT_GENERATION,
            "摘要": TaskType.CONTENT_GENERATION,
            "作者": TaskType.CONTENT_GENERATION,
            "变量": TaskType.DATA_EXTRACTION,
            "中文": TaskType.CONTENT_GENERATION,
            "文本": TaskType.CONTENT_GENERATION,
            "区域": TaskType.DATA_QUERY,
            "周期": TaskType.DATA_QUERY,
            "排行": TaskType.DATA_QUERY,
            "比较": TaskType.DATA_ANALYSIS
        }
        
        return type_mapping.get(placeholder_type.lower(), TaskType.DATA_QUERY)
    
    def _convert_iaop_result_to_etl_instruction(
        self, 
        result, 
        placeholder_data: Dict[str, Any], 
        data_source
    ) -> Dict[str, Any]:
        """将IAOP结果转换为ETL指令格式"""
        placeholder_name = placeholder_data.get('name', '')
        
        # 基于IAOP结果构造ETL指令
        etl_instruction = {
            "query_type": "sql",
            "description": f"IAOP处理结果: {placeholder_name}",
            "confidence": result.confidence_score,
            "iaop_processed": True
        }
        
        # 如果有具体的数据内容，尝试构造SQL
        if result.content:
            try:
                # 尝试解析结果中的SQL或查询信息
                content_lower = result.content.lower()
                if "select" in content_lower and "from" in content_lower:
                    etl_instruction["sql_query"] = result.content
                else:
                    # 生成基本SQL模板
                    etl_instruction["sql_query"] = f"-- IAOP生成的查询\n-- {result.content}"
            except:
                etl_instruction["sql_query"] = "SELECT 1 as iaop_result"
        
        # 添加其他IAOP特有信息
        if result.chart_config:
            etl_instruction["chart_config"] = result.chart_config
        
        if result.narrative:
            etl_instruction["narrative"] = result.narrative
        
        return etl_instruction
    
    async def _fallback_placeholder_analysis(
        self, 
        placeholder_data: Dict[str, Any], 
        data_source_id: str
    ) -> Dict[str, Any]:
        """Fallback占位符分析"""
        logger.warning("使用fallback占位符分析方法")
        
        placeholder_name = placeholder_data.get('name', '')
        placeholder_type = placeholder_data.get('type', 'text')
        
        # 生成基本ETL指令
        etl_instruction = {
            "query_type": "sql",
            "sql_query": f"-- Fallback查询 for {placeholder_name}\nSELECT * FROM your_table LIMIT 10",
            "description": f"Fallback分析: {placeholder_name}",
            "fallback": True
        }
        
        return {
            "placeholder": placeholder_data,
            "etl_instruction": etl_instruction,
            "data_source_id": data_source_id,
            "analysis_time": datetime.utcnow().isoformat(),
            "source": "fallback",
            "success": False
        }
    
    def _default_nlq_interpretation(self, query: str, available_columns: List[str]) -> Dict[str, Any]:
        """默认自然语言查询解释"""
        return {
            "intent": "summary",
            "filters": [],
            "metrics": available_columns[:2] if available_columns else ["value"],
            "dimensions": available_columns[2:4] if available_columns and len(available_columns) > 2 else ["category"],
            "chart_type": "bar",
            "aggregation": "sum",
            "iaop_fallback": True
        }
    
    def _format_nlq_result(self, parsed_query: Dict[str, Any], available_columns: List[str]) -> Dict[str, Any]:
        """格式化自然语言查询结果"""
        # 确保结果包含必要字段
        result = {
            "intent": parsed_query.get("intent", "summary"),
            "filters": parsed_query.get("filters", []),
            "metrics": parsed_query.get("metrics", available_columns[:1] if available_columns else ["value"]),
            "dimensions": parsed_query.get("dimensions", available_columns[1:2] if available_columns and len(available_columns) > 1 else ["category"]),
            "chart_type": parsed_query.get("chart_type", "bar"),
            "aggregation": parsed_query.get("aggregation", "sum"),
            "iaop_processed": True
        }
        
        return result
    
    def _generate_default_insights(self, data_summary: Dict[str, Any], context: str) -> str:
        """生成默认洞察"""
        return f"基于提供的数据摘要，观察到以下关键信息：{str(data_summary)[:200]}..."
    
    def _generate_default_chart_config(
        self, 
        data: List[Dict[str, Any]], 
        description: str, 
        chart_type: Optional[str]
    ) -> Dict[str, Any]:
        """生成默认图表配置"""
        columns = list(data[0].keys()) if data else ["x", "y"]
        
        return {
            "chart_type": chart_type or "bar",
            "title": description,
            "x_axis": {"column": columns[0], "label": "X轴"},
            "y_axis": {"column": columns[1] if len(columns) > 1 else columns[0], "label": "Y轴"},
            "limit": 20,
            "iaop_fallback": True
        }


# 全局服务实例
_global_iaop_ai_service = None

def get_iaop_ai_service(db: Session) -> IAOPAIService:
    """获取IAOP AI服务实例"""
    global _global_iaop_ai_service
    if _global_iaop_ai_service is None:
        _global_iaop_ai_service = IAOPAIService(db)
    return _global_iaop_ai_service