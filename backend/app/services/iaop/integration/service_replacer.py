"""
IAOP服务替换器 - 无缝替换现有AI服务

这个模块提供透明的服务替换功能，将现有系统中的AI服务调用重定向到IAOP平台
"""

import logging
from typing import Dict, Any, Optional, Union
from sqlalchemy.orm import Session

from .ai_service_adapter import get_iaop_ai_service, IAOPAIService
# 避免循环导入，直接引用本地类
from .ai_service_adapter import IAOPAIService as EnhancedAIService

logger = logging.getLogger(__name__)


class AIServiceProxy:
    """AI服务代理 - 智能路由到IAOP或传统AI服务"""
    
    def __init__(self, db: Session, use_iaop: bool = True):
        self.db = db
        self.use_iaop = use_iaop
        self._iaop_service: Optional[IAOPAIService] = None
        self._traditional_service: Optional[EnhancedAIService] = None
        
    def _get_iaop_service(self) -> IAOPAIService:
        """获取IAOP服务"""
        if self._iaop_service is None:
            self._iaop_service = get_iaop_ai_service(self.db)
        return self._iaop_service
    
    def _get_traditional_service(self) -> EnhancedAIService:
        """获取传统AI服务"""
        if self._traditional_service is None:
            self._traditional_service = EnhancedAIService(self.db)
        return self._traditional_service
    
    async def analyze_placeholder_requirements(
        self, 
        placeholder_data: Dict[str, Any], 
        data_source_id: str
    ) -> Dict[str, Any]:
        """
        占位符需求分析 - 智能路由
        优先使用IAOP，失败时fallback到传统服务
        """
        if self.use_iaop:
            try:
                logger.info(f"使用IAOP分析占位符: {placeholder_data.get('name', '')}")
                result = await self._get_iaop_service().analyze_placeholder_requirements(
                    placeholder_data, data_source_id
                )
                result["processing_method"] = "iaop"
                return result
            except Exception as e:
                logger.warning(f"IAOP分析失败，fallback到传统服务: {e}")
                result = await self._get_traditional_service().analyze_placeholder_requirements(
                    placeholder_data, data_source_id
                )
                result["processing_method"] = "traditional_fallback"
                result["iaop_error"] = str(e)
                return result
        else:
            logger.info("使用传统AI服务分析占位符")
            result = await self._get_traditional_service().analyze_placeholder_requirements(
                placeholder_data, data_source_id
            )
            result["processing_method"] = "traditional"
            return result
    
    async def interpret_natural_language_query(
        self,
        query: str,
        context: Dict[str, Any],
        available_columns: Optional[list] = None,
    ) -> Dict[str, Any]:
        """自然语言查询解释 - 智能路由"""
        if self.use_iaop:
            try:
                logger.info("使用IAOP解释自然语言查询")
                result = await self._get_iaop_service().interpret_natural_language_query(
                    query, context, available_columns
                )
                if not result.get("iaop_fallback"):
                    result["processing_method"] = "iaop"
                    return result
                else:
                    logger.info("IAOP返回fallback结果，尝试传统服务")
                    raise Exception("IAOP fallback triggered")
            except Exception as e:
                logger.warning(f"IAOP NLQ解释失败，fallback到传统服务: {e}")
                result = await self._get_traditional_service().interpret_natural_language_query(
                    query, context, available_columns
                )
                result["processing_method"] = "traditional_fallback"
                result["iaop_error"] = str(e)
                return result
        else:
            result = await self._get_traditional_service().interpret_natural_language_query(
                query, context, available_columns
            )
            result["processing_method"] = "traditional"
            return result
    
    async def generate_insights(
        self, data_summary: Dict[str, Any], context: str = ""
    ) -> str:
        """生成洞察 - 智能路由"""
        if self.use_iaop:
            try:
                logger.info("使用IAOP生成洞察")
                insights = await self._get_iaop_service().generate_insights(data_summary, context)
                if insights and len(insights.strip()) > 10:  # 确保有实质内容
                    return f"[IAOP生成] {insights}"
                else:
                    raise Exception("IAOP生成的洞察内容不足")
            except Exception as e:
                logger.warning(f"IAOP洞察生成失败，fallback到传统服务: {e}")
                insights = await self._get_traditional_service().generate_insights(data_summary, context)
                return f"[传统服务] {insights}"
        else:
            insights = await self._get_traditional_service().generate_insights(data_summary, context)
            return f"[传统服务] {insights}"
    
    async def generate_chart_config(
        self,
        data: list,
        description: str,
        chart_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成图表配置 - 智能路由"""
        if self.use_iaop:
            try:
                logger.info("使用IAOP生成图表配置")
                config = await self._get_iaop_service().generate_chart_config(data, description, chart_type)
                if not config.get("iaop_fallback"):
                    config["processing_method"] = "iaop"
                    return config
                else:
                    raise Exception("IAOP返回fallback配置")
            except Exception as e:
                logger.warning(f"IAOP图表配置生成失败，fallback到传统服务: {e}")
                config = await self._get_traditional_service().generate_chart_config(data, description, chart_type)
                config["processing_method"] = "traditional_fallback"
                config["iaop_error"] = str(e)
                return config
        else:
            config = await self._get_traditional_service().generate_chart_config(data, description, chart_type)
            config["processing_method"] = "traditional"
            return config
    
    async def analyze_with_context(
        self,
        context: str,
        prompt: str,
        task_type: str,
        **kwargs
    ) -> str:
        """上下文分析 - 智能路由"""
        if self.use_iaop:
            try:
                logger.info(f"使用IAOP进行上下文分析: {task_type}")
                result = await self._get_iaop_service().analyze_with_context(
                    context, prompt, task_type, **kwargs
                )
                if result and len(result.strip()) > 10:
                    return f"[IAOP分析] {result}"
                else:
                    raise Exception("IAOP分析结果不足")
            except Exception as e:
                logger.warning(f"IAOP上下文分析失败，fallback到传统服务: {e}")
                result = await self._get_traditional_service().analyze_with_context(
                    context, prompt, task_type, **kwargs
                )
                return f"[传统服务] {result}"
        else:
            result = await self._get_traditional_service().analyze_with_context(
                context, prompt, task_type, **kwargs
            )
            return f"[传统服务] {result}"
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查 - 综合状态"""
        iaop_status = None
        traditional_status = None
        
        try:
            iaop_status = await self._get_iaop_service().health_check()
        except Exception as e:
            iaop_status = {"status": "error", "error": str(e)}
        
        try:
            traditional_status = await self._get_traditional_service().health_check()
        except Exception as e:
            traditional_status = {"status": "error", "error": str(e)}
        
        return {
            "proxy_status": "healthy" if self.use_iaop and iaop_status.get("status") == "healthy" else "degraded",
            "use_iaop": self.use_iaop,
            "iaop_service": iaop_status,
            "traditional_service": traditional_status,
            "routing_mode": "iaop_primary" if self.use_iaop else "traditional_only"
        }
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """获取服务指标 - 综合指标"""
        metrics = {
            "proxy_mode": "iaop_primary" if self.use_iaop else "traditional_only",
            "services": {}
        }
        
        try:
            if self._iaop_service:
                metrics["services"]["iaop"] = self._iaop_service.get_service_metrics()
        except Exception as e:
            metrics["services"]["iaop"] = {"error": str(e)}
        
        try:
            if self._traditional_service:
                metrics["services"]["traditional"] = self._traditional_service.get_service_metrics()
        except Exception as e:
            metrics["services"]["traditional"] = {"error": str(e)}
        
        return metrics
    
    def switch_to_iaop(self):
        """切换到IAOP模式"""
        self.use_iaop = True
        logger.info("AI服务代理切换到IAOP模式")
    
    def switch_to_traditional(self):
        """切换到传统AI服务模式"""
        self.use_iaop = False
        logger.info("AI服务代理切换到传统AI服务模式")
    
    def clear_cache(self):
        """清空所有缓存"""
        if self._iaop_service:
            self._iaop_service.clear_cache()
        if self._traditional_service:
            self._traditional_service.clear_cache()


# 全局代理实例
_global_ai_proxy = None

def get_ai_service_proxy(db: Session, use_iaop: bool = True) -> AIServiceProxy:
    """获取AI服务代理"""
    global _global_ai_proxy
    if _global_ai_proxy is None:
        _global_ai_proxy = AIServiceProxy(db, use_iaop)
    return _global_ai_proxy


def create_enhanced_ai_service(db: Session) -> Union[IAOPAIService, EnhancedAIService]:
    """
    创建增强AI服务 - 这是替换现有AI服务的主要入口点
    
    这个函数可以直接替换现有代码中的 EnhancedAIService(db) 调用
    """
    try:
        # 尝试使用IAOP服务
        iaop_service = get_iaop_ai_service(db)
        logger.info("使用IAOP AI服务")
        return iaop_service
    except Exception as e:
        logger.warning(f"IAOP服务初始化失败，fallback到传统服务: {e}")
        # Fallback到传统服务
        return EnhancedAIService(db)


# 用于配置的环境变量和设置
class IAOPServiceConfig:
    """IAOP服务配置"""
    
    @staticmethod
    def is_iaop_enabled() -> bool:
        """检查是否启用IAOP"""
        import os
        return os.getenv("USE_IAOP_SERVICE", "true").lower() in ["true", "1", "yes", "on"]
    
    @staticmethod
    def get_fallback_mode() -> str:
        """获取fallback模式"""
        import os
        return os.getenv("IAOP_FALLBACK_MODE", "traditional")  # traditional, none
    
    @staticmethod
    def get_routing_strategy() -> str:
        """获取路由策略"""
        import os
        return os.getenv("IAOP_ROUTING_STRATEGY", "smart")  # smart, iaop_only, traditional_only


def configure_ai_service_routing(db: Session) -> AIServiceProxy:
    """配置AI服务路由"""
    use_iaop = IAOPServiceConfig.is_iaop_enabled()
    proxy = AIServiceProxy(db, use_iaop)
    
    routing_strategy = IAOPServiceConfig.get_routing_strategy()
    if routing_strategy == "iaop_only":
        proxy.switch_to_iaop()
    elif routing_strategy == "traditional_only":
        proxy.switch_to_traditional()
    # smart 模式保持默认行为
    
    logger.info(f"AI服务路由配置: 使用IAOP={use_iaop}, 策略={routing_strategy}")
    return proxy