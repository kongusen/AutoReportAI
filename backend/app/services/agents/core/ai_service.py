"""
AI服务统一接口

提供统一的AI服务接口，支持多种AI提供商
"""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from app.services.ai_integration import EnhancedAIService


class AIServiceInterface(ABC):
    """AI服务接口抽象类"""
    
    @abstractmethod
    async def analyze_with_context(
        self,
        context: str,
        prompt: str,
        task_type: str,
        **kwargs
    ) -> str:
        """使用上下文进行分析"""
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """生成响应"""
        pass


class UnifiedAIService(AIServiceInterface):
    """统一的AI服务实现"""
    
    def __init__(self, db_session=None):
        """
        初始化AI服务
        
        Args:
            db_session: 数据库会话，如果为None则使用默认会话
        """
        self.db_session = db_session
        self.ai_service = None
        self.logger = logging.getLogger(__name__)
        self._initialize_ai_service()
    
    def _initialize_ai_service(self):
        """初始化AI服务"""
        try:
            if self.db_session is not None:
                self.ai_service = EnhancedAIService(self.db_session)
            else:
                # 如果没有提供数据库会话，记录警告但不创建服务
                self.logger.warning("未提供数据库会话，AI服务将不可用")
                self.ai_service = None
        except Exception as e:
            self.logger.error(f"初始化AI服务失败: {e}")
            self.ai_service = None
    
    async def analyze_with_context(
        self,
        context: str,
        prompt: str,
        task_type: str,
        **kwargs
    ) -> str:
        """使用上下文进行分析"""
        if self.ai_service is None:
            raise RuntimeError("AI服务未初始化，请提供有效的数据库会话")
        
        try:
            return await self.ai_service.analyze_with_context(
                context=context,
                prompt=prompt,
                task_type=task_type,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"AI分析失败: {e}")
            raise
    
    async def generate_response(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """生成响应"""
        if self.ai_service is None:
            raise RuntimeError("AI服务未初始化，请提供有效的数据库会话")
        
        try:
            return await self.ai_service.generate_response(
                prompt=prompt,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"AI响应生成失败: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if self.ai_service is None:
            return {
                "status": "unhealthy",
                "service": "UnifiedAIService",
                "error": "AI服务未初始化"
            }
        
        try:
            # 简单的健康检查
            test_response = await self.generate_response("测试")
            return {
                "status": "healthy",
                "service": "UnifiedAIService",
                "test_response": test_response[:100] if test_response else "无响应"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "UnifiedAIService",
                "error": str(e)
            }


# 全局AI服务实例
_ai_service_instance = None


def get_ai_service(db_session=None) -> UnifiedAIService:
    """
    获取AI服务实例（单例模式）
    
    Args:
        db_session: 数据库会话，如果为None则使用默认会话
        
    Returns:
        UnifiedAIService实例
    """
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = UnifiedAIService(db_session)
    return _ai_service_instance
