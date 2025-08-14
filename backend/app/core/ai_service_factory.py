"""
User-specific AI Service Factory for Dynamic Configuration Loading

实现Worker内动态用户配置加载的核心组件，支持：
1. 根据用户ID获取用户专属AI配置
2. 为每个用户创建独立的AI服务实例
3. 缓存AI服务实例以提高性能
4. 回退到系统默认配置
"""

import logging
import os
from typing import Dict, Optional, List
from sqlalchemy.orm import Session

from app import crud
from app.services.ai_integration.llm_service import LLMProviderManager, AIService
from app.core.security_utils import decrypt_data
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class UserAIServiceFactory:
    """用户专属AI服务工厂"""
    
    def __init__(self):
        # 缓存用户AI服务实例，避免重复创建
        self._user_ai_services: Dict[str, AIService] = {}
        # 缓存用户的LLM Provider Manager
        self._user_llm_managers: Dict[str, LLMProviderManager] = {}
        # 系统默认AI服务
        self._system_ai_service: Optional[AIService] = None
        
    def get_user_ai_service(self, user_id: str, refresh_cache: bool = False) -> AIService:
        """
        获取用户专属的AI服务实例
        
        Args:
            user_id: 用户ID
            refresh_cache: 是否刷新缓存
            
        Returns:
            AIService: 用户专属的AI服务实例
        """
        # 如果需要刷新缓存或者缓存中没有，则重新创建
        if refresh_cache or user_id not in self._user_ai_services:
            try:
                ai_service = self._create_user_ai_service(user_id)
                self._user_ai_services[user_id] = ai_service
                logger.info(f"Created AI service for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to create AI service for user {user_id}: {e}")
                # 回退到系统默认AI服务
                return self._get_system_ai_service()
        
        return self._user_ai_services[user_id]
    
    def get_user_llm_manager(self, user_id: str, refresh_cache: bool = False) -> LLMProviderManager:
        """
        获取用户专属的LLM Provider Manager
        
        Args:
            user_id: 用户ID
            refresh_cache: 是否刷新缓存
            
        Returns:
            LLMProviderManager: 用户专属的LLM管理器
        """
        if refresh_cache or user_id not in self._user_llm_managers:
            try:
                llm_manager = self._create_user_llm_manager(user_id)
                self._user_llm_managers[user_id] = llm_manager
                logger.info(f"Created LLM manager for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to create LLM manager for user {user_id}: {e}")
                # 回退到系统级别的LLM管理器
                return self._get_system_llm_manager()
                
        return self._user_llm_managers[user_id]
    
    def _create_user_ai_service(self, user_id: str) -> AIService:
        """创建用户专属的AI服务"""
        db = SessionLocal()
        try:
            # 获取用户的AI配置
            user_providers = crud.ai_provider.get_by_user_id(db, user_id=user_id)
            
            if not user_providers:
                logger.info(f"No AI providers found for user {user_id}, using system default")
                return self._get_system_ai_service()
            
            # 找到用户激活的AI提供商
            active_provider = None
            for provider in user_providers:
                if provider.is_active:
                    active_provider = provider
                    break
                    
            if not active_provider:
                logger.info(f"No active AI provider for user {user_id}, using system default")
                return self._get_system_ai_service()
            
            # 创建用户专属的AI服务
            user_ai_service = UserSpecificAIService(db, user_id)
            logger.info(f"Successfully created AI service for user {user_id} using provider {active_provider.provider_name}")
            return user_ai_service
            
        finally:
            db.close()
    
    def _create_user_llm_manager(self, user_id: str) -> LLMProviderManager:
        """创建用户专属的LLM管理器"""
        db = SessionLocal()
        try:
            # 创建用户专属的LLM管理器，只加载该用户的配置
            user_llm_manager = UserSpecificLLMProviderManager(db, user_id)
            return user_llm_manager
        finally:
            db.close()
    
    def _get_system_ai_service(self) -> AIService:
        """获取系统默认AI服务"""
        if self._system_ai_service is None:
            db = SessionLocal()
            try:
                self._system_ai_service = AIService(db)
                logger.info("Created system default AI service")
            except Exception as e:
                logger.error(f"Failed to create system AI service: {e}")
                # 如果连系统服务都创建不了，创建一个模拟的服务
                self._system_ai_service = MockAIService()
            finally:
                db.close()
                
        return self._system_ai_service
    
    def _get_system_llm_manager(self) -> LLMProviderManager:
        """获取系统默认LLM管理器"""
        db = SessionLocal()
        try:
            return LLMProviderManager(db)
        finally:
            db.close()
    
    def clear_user_cache(self, user_id: str):
        """清理特定用户的缓存"""
        if user_id in self._user_ai_services:
            del self._user_ai_services[user_id]
            logger.info(f"Cleared AI service cache for user {user_id}")
            
        if user_id in self._user_llm_managers:
            del self._user_llm_managers[user_id]
            logger.info(f"Cleared LLM manager cache for user {user_id}")
    
    def clear_all_cache(self):
        """清理所有缓存"""
        self._user_ai_services.clear()
        self._user_llm_managers.clear()
        self._system_ai_service = None
        logger.info("Cleared all AI service caches")
    
    def get_user_provider_summary(self, user_id: str) -> Dict[str, any]:
        """获取用户AI配置摘要"""
        db = SessionLocal()
        try:
            user_providers = crud.ai_provider.get_by_user_id(db, user_id=user_id)
            
            summary = {
                "user_id": user_id,
                "total_providers": len(user_providers),
                "active_providers": [],
                "inactive_providers": [],
                "system_fallback": False
            }
            
            for provider in user_providers:
                provider_info = {
                    "name": provider.provider_name,
                    "type": provider.provider_type.value,
                    "model": provider.default_model_name
                }
                
                if provider.is_active:
                    summary["active_providers"].append(provider_info)
                else:
                    summary["inactive_providers"].append(provider_info)
            
            # 如果没有激活的提供商，将使用系统回退
            if not summary["active_providers"]:
                summary["system_fallback"] = True
                
            return summary
            
        finally:
            db.close()


class UserSpecificAIService(AIService):
    """用户专属的AI服务，继承自基础AIService"""
    
    def __init__(self, db: Session, user_id: str):
        self.user_id = user_id
        self.db = db
        
        # 获取用户的激活AI提供商
        user_providers = crud.ai_provider.get_by_user_id(db, user_id=user_id)
        active_provider = None
        
        for provider in user_providers:
            if provider.is_active:
                active_provider = provider
                break
        
        if not active_provider:
            raise ValueError(f"No active AI provider found for user {user_id}")
            
        # 设置用户专属的提供商
        self.provider = active_provider
        self.client = None
        
        # 创建用户专属的LLM管理器
        self.llm_manager = UserSpecificLLMProviderManager(db, user_id)
        
        # 初始化客户端
        self._initialize_client()
        
        logger.info(f"Initialized user-specific AI service for user {user_id} with provider {active_provider.provider_name}")


class UserSpecificLLMProviderManager(LLMProviderManager):
    """用户专属的LLM提供商管理器"""
    
    def __init__(self, db: Session, user_id: str):
        self.user_id = user_id
        super().__init__(db)
        
    def _load_providers(self):
        """只加载特定用户的AI配置"""
        try:
            # 获取用户专属的AI提供商
            user_providers = crud.ai_provider.get_by_user_id(self.db, user_id=self.user_id)
            
            for provider in user_providers:
                if provider.api_key and provider.is_active:
                    try:
                        decrypted_key = decrypt_data(provider.api_key)
                        self.api_keys[provider.provider_name] = decrypted_key
                        self.providers[provider.provider_name] = provider
                        logger.info(f"Loaded user provider: {provider.provider_name} for user {self.user_id}")
                    except Exception as e:
                        logger.error(
                            f"Failed to decrypt key for {provider.provider_name} (user {self.user_id}): {e}"
                        )
            
            logger.info(f"Loaded {len(self.providers)} providers for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to load providers for user {self.user_id}: {e}")


class MockAIService:
    """模拟AI服务，当所有配置都失败时使用"""
    
    def __init__(self):
        self.provider = None
        self.client = None
    
    def health_check(self):
        return {
            "status": "mock",
            "message": "Using mock AI service due to configuration issues"
        }
    
    def call_llm_unified(self, request, provider_name=None):
        from app.services.ai_integration.llm_service import LLMResponse
        return LLMResponse(
            content="Mock response: AI service is not properly configured",
            model="mock-model",
            provider="mock",
            usage={"input_tokens": 0, "output_tokens": 10},
            response_time=0.1,
            cost_estimate=0.0
        )


# 全局AI服务工厂实例
ai_service_factory = UserAIServiceFactory()


def get_user_ai_service(user_id: str, refresh_cache: bool = False) -> AIService:
    """
    获取用户专属AI服务的便捷函数
    
    Args:
        user_id: 用户ID
        refresh_cache: 是否刷新缓存
        
    Returns:
        AIService: 用户专属的AI服务实例
    """
    return ai_service_factory.get_user_ai_service(user_id, refresh_cache)


def get_user_llm_manager(user_id: str, refresh_cache: bool = False) -> LLMProviderManager:
    """
    获取用户专属LLM管理器的便捷函数
    
    Args:
        user_id: 用户ID  
        refresh_cache: 是否刷新缓存
        
    Returns:
        LLMProviderManager: 用户专属的LLM管理器
    """
    return ai_service_factory.get_user_llm_manager(user_id, refresh_cache)


def get_user_provider_summary(user_id: str) -> Dict[str, any]:
    """获取用户AI配置摘要的便捷函数"""
    return ai_service_factory.get_user_provider_summary(user_id)


def clear_user_ai_cache(user_id: str):
    """清理用户AI服务缓存的便捷函数"""
    ai_service_factory.clear_user_cache(user_id)