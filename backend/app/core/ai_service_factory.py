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
import openai
import threading
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session

from app import crud
from app.services.ai.integration.llm_service import LLMProviderManager, AIService
from app.core.security_utils import decrypt_data
from app.db.session import SessionLocal
from app.services.ai.integration.ai_service_enhanced import EnhancedAIService

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
        # 系统默认LLM管理器
        self._system_llm_manager: Optional[LLMProviderManager] = None
        # 线程锁，确保线程安全
        self._lock = threading.RLock()
        # 系统默认LLM管理器
        self._system_llm_manager: Optional[LLMProviderManager] = None
        # 线程锁，确保线程安全
        self._lock = threading.RLock()
        
    def get_user_ai_service(self, user_id: str, refresh_cache: bool = False) -> AIService:
        """
        获取用户专属的AI服务实例
        
        Args:
            user_id: 用户ID
            refresh_cache: 是否刷新缓存
            
        Returns:
            AIService: 用户专属的AI服务实例
        """
        with self._lock:
            # 如果需要刷新缓存或者缓存中没有，则重新创建
            if refresh_cache or user_id not in self._user_ai_services:
                try:
                    # 检查是否已经存在服务实例
                    if user_id in self._user_ai_services and not refresh_cache:
                        logger.debug(f"Using cached AI service for user {user_id}")
                        return self._user_ai_services[user_id]
                    
                    ai_service = self._create_user_ai_service(user_id)
                    self._user_ai_services[user_id] = ai_service
                    logger.info(f"Created AI service for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to create AI service for user {user_id}: {e}")
                    # 回退到系统默认AI服务
                    return self._get_system_ai_service()
            else:
                logger.debug(f"Using cached AI service for user {user_id}")
        
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
        with self._lock:
            if refresh_cache or user_id not in self._user_llm_managers:
                try:
                    # 检查是否已经存在管理器实例
                    if user_id in self._user_llm_managers and not refresh_cache:
                        logger.debug(f"Using cached LLM manager for user {user_id}")
                        return self._user_llm_managers[user_id]
                    
                    llm_manager = self._create_user_llm_manager(user_id)
                    self._user_llm_managers[user_id] = llm_manager
                    logger.info(f"Created LLM manager for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to create LLM manager for user {user_id}: {e}")
                    # 回退到系统级别的LLM管理器
                    return self._get_system_llm_manager()
            else:
                logger.debug(f"Using cached LLM manager for user {user_id}")
                
        return self._user_llm_managers[user_id]
    
    def _create_user_ai_service(self, user_id: str) -> AIService:
        """创建用户专属的AI服务"""
        db = SessionLocal()
        try:
            return UserSpecificAIService(db, user_id)
        except Exception as e:
            db.close()
            raise e
    
    def _create_user_llm_manager(self, user_id: str) -> LLMProviderManager:
        """创建用户专属的LLM管理器"""
        db = SessionLocal()
        try:
            return UserSpecificLLMProviderManager(db, user_id)
        except Exception as e:
            db.close()
            raise e
    
    def _get_system_ai_service(self) -> AIService:
        """获取系统默认AI服务"""
        if self._system_ai_service is None:
            db = SessionLocal()
            try:
                self._system_ai_service = EnhancedAIService(db)
                logger.info("Created system default AI service")
            except Exception as e:
                logger.error(f"Failed to create system AI service: {e}")
                # 返回模拟服务
                return MockAIService()
        return self._system_ai_service
    
    def _get_system_llm_manager(self) -> LLMProviderManager:
        """获取系统默认LLM管理器"""
        if self._system_llm_manager is None:
            db = SessionLocal()
            try:
                self._system_llm_manager = LLMProviderManager(db)
                logger.info("Created system default LLM manager")
            except Exception as e:
                logger.error(f"Failed to create system LLM manager: {e}")
                # 返回一个基本的LLM管理器
                return LLMProviderManager(db)
        return self._system_llm_manager
    
    def clear_user_cache(self, user_id: str = None):
        """清除用户缓存"""
        with self._lock:
            if user_id:
                if user_id in self._user_ai_services:
                    del self._user_ai_services[user_id]
                if user_id in self._user_llm_managers:
                    del self._user_llm_managers[user_id]
                logger.info(f"Cleared cache for user {user_id}")
            else:
                self._user_ai_services.clear()
                self._user_llm_managers.clear()
                logger.info("Cleared all user caches")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                "ai_services_count": len(self._user_ai_services),
                "llm_managers_count": len(self._user_llm_managers),
                "cached_users": list(self._user_ai_services.keys()),
                "has_system_ai_service": self._system_ai_service is not None,
                "has_system_llm_manager": self._system_llm_manager is not None
            }
    
    def get_user_provider_summary(self, user_id: str) -> Dict[str, any]:
        """获取用户提供商摘要"""
        db = SessionLocal()
        try:
            user_providers = crud.ai_provider.get_by_user_id(db, user_id=user_id)
            
            summary = {
                "user_id": user_id,
                "total_providers": len(user_providers),
                "active_providers": 0,
                "providers": []
            }
            
            for provider in user_providers:
                provider_info = {
                    "id": str(provider.id),
                    "name": provider.provider_name,
                    "type": provider.provider_type.value,
                    "is_active": provider.is_active,
                    "has_api_key": bool(provider.api_key),
                    "base_url": str(provider.api_base_url) if provider.api_base_url else None
                }
                summary["providers"].append(provider_info)
                
                if provider.is_active:
                    summary["active_providers"] += 1
                
            return summary
            
        finally:
            db.close()


class UserSpecificAIService(EnhancedAIService):
    """用户专属的AI服务，继承自EnhancedAIService"""
    
    def __init__(self, db: Session, user_id: str):
        self.user_id = user_id
        
        # 获取用户的激活AI提供商
        user_providers = crud.ai_provider.get_by_user_id(db, user_id=user_id)
        active_provider = None
        
        for provider in user_providers:
            if provider.is_active:
                active_provider = provider
                break
        
        if not active_provider:
            raise ValueError(f"No active AI provider found for user {user_id}")
        
        # 调用父类构造函数，传入数据库会话
        super().__init__(db)
        
        # 覆盖为用户特定的提供商
        self.provider = active_provider
        
        # 重新初始化客户端以使用用户特定的配置
        self._initialize_client()
        
        logger.info(f"Initialized user-specific AI service for user {user_id} with provider {active_provider.provider_name}")
    
    def _initialize_client(self):
        """初始化AI客户端 - 用户特定版本"""
        if not self.provider:
            raise ValueError("No active AI Provider found for user.")

        decrypted_api_key = None
        if self.provider.api_key:
            try:
                decrypted_api_key = decrypt_data(self.provider.api_key)
            except Exception as e:
                raise ValueError(f"Failed to decrypt API key: {e}")

        if self.provider.provider_type.value == "openai":
            if not decrypted_api_key:
                raise ValueError("Active OpenAI provider has no API key.")

            self.client = openai.AsyncOpenAI(
                api_key=decrypted_api_key,
                base_url=(
                    str(self.provider.api_base_url)
                    if self.provider.api_base_url
                    else None
                ),
            )
        else:
            self.client = None


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
    
    async def analyze_with_context(self, context: str, prompt: str, task_type: str, **kwargs) -> str:
        """模拟分析响应"""
        try:
            return "{}"
        except Exception:
            return "{}"


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