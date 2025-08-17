"""
AI服务统一接口

提供统一的AI服务接口，支持多种AI提供商
包含智能缓存、连接池管理和性能优化
"""

import logging
import weakref
from typing import Dict, Any, Optional, Set
from abc import ABC, abstractmethod
from threading import Lock
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services.ai_integration import EnhancedAIService
from .cache_manager import get_cached_ai_response, cache_ai_response
from .performance_monitor import performance_context


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
    
    def __init__(self, db_session=None, suppress_warning=False):
        """
        初始化AI服务
        
        Args:
            db_session: 数据库会话，如果为None则使用默认会话
            suppress_warning: 如果为True，则不显示未提供数据库会话的警告
        """
        self.db_session = db_session
        self.ai_service = None
        self.logger = logging.getLogger(__name__)
        self.suppress_warning = suppress_warning
        self._initialize_ai_service()
    
    def _initialize_ai_service(self):
        """初始化AI服务"""
        try:
            if self.db_session is not None:
                self.ai_service = EnhancedAIService(self.db_session)
            else:
                # 如果没有提供数据库会话，根据配置决定是否记录警告
                if not self.suppress_warning:
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
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """使用上下文进行分析"""
        if self.ai_service is None:
            raise RuntimeError("AI服务未初始化，请提供有效的数据库会话")
        
        # 检查缓存
        if use_cache:
            cached_response = get_cached_ai_response(
                prompt=prompt,
                context=context,
                task_type=task_type,
                **kwargs
            )
            if cached_response:
                self.logger.debug("使用缓存的AI分析结果")
                return cached_response
        
        try:
            with performance_context(f"ai_analyze_{task_type}"):
                response = await self.ai_service.analyze_with_context(
                    context=context,
                    prompt=prompt,
                    task_type=task_type,
                    **kwargs
                )
                
                # 缓存响应
                if use_cache and response:
                    cache_ai_response(
                        response=response,
                        prompt=prompt,
                        context=context,
                        task_type=task_type,
                        **kwargs
                    )
                
                return response
        except Exception as e:
            self.logger.error(f"AI分析失败: {e}")
            raise
    
    async def generate_response(
        self,
        prompt: str,
        use_cache: bool = True,
        **kwargs
    ) -> str:
        """生成响应"""
        if self.ai_service is None:
            raise RuntimeError("AI服务未初始化，请提供有效的数据库会话")
        
        # 检查缓存
        if use_cache:
            cached_response = get_cached_ai_response(
                prompt=prompt,
                task_type="generate_response",
                **kwargs
            )
            if cached_response:
                self.logger.debug("使用缓存的AI响应")
                return cached_response
        
        try:
            with performance_context("ai_generate_response"):
                response = await self.ai_service.generate_response(
                    prompt=prompt,
                    **kwargs
                )
                
                # 缓存响应
                if use_cache and response:
                    cache_ai_response(
                        response=response,
                        prompt=prompt,
                        task_type="generate_response",
                        **kwargs
                    )
                
                return response
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


@dataclass
class AIServiceCacheEntry:
    """AI服务缓存条目"""
    service: UnifiedAIService
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    
    def touch(self):
        """更新访问时间"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class AIServicePool:
    """AI服务连接池管理器"""
    
    def __init__(self, max_instances: int = 10, ttl_hours: int = 24):
        self.max_instances = max_instances
        self.ttl = timedelta(hours=ttl_hours)
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        
        # 服务实例缓存
        self._instances: Dict[str, AIServiceCacheEntry] = {}
        
        # 弱引用集合，用于跟踪活跃实例
        self._active_refs: Set[weakref.ref] = set()
    
    def _generate_cache_key(self, db_session_id: Optional[str], suppress_warning: bool) -> str:
        """生成缓存键"""
        session_key = db_session_id or "no_session"
        warning_key = "no_warn" if suppress_warning else "warn"
        return f"{session_key}_{warning_key}"
    
    def _cleanup_expired_instances(self):
        """清理过期实例"""
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self._instances.items():
            if now - entry.created_at > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._instances[key]
            self.logger.debug(f"Cleaned up expired AI service instance: {key}")
    
    def _evict_least_used_instance(self):
        """驱逐最少使用的实例"""
        if not self._instances:
            return
        
        # 找到最少使用的实例
        least_used_key = min(
            self._instances.keys(),
            key=lambda k: (self._instances[k].access_count, self._instances[k].last_accessed)
        )
        
        del self._instances[least_used_key]
        self.logger.debug(f"Evicted least used AI service instance: {least_used_key}")
    
    def get_service(self, db_session=None, suppress_warning=False) -> UnifiedAIService:
        """
        获取AI服务实例（带连接池管理）
        
        Args:
            db_session: 数据库会话
            suppress_warning: 是否抑制警告
            
        Returns:
            UnifiedAIService实例
        """
        with self.lock:
            # 生成缓存键
            session_id = str(id(db_session)) if db_session else None
            cache_key = self._generate_cache_key(session_id, suppress_warning)
            
            # 清理过期实例
            self._cleanup_expired_instances()
            
            # 检查是否存在缓存实例
            if cache_key in self._instances:
                entry = self._instances[cache_key]
                entry.touch()
                self.logger.debug(f"Reusing cached AI service: {cache_key}")
                return entry.service
            
            # 检查实例数量限制
            if len(self._instances) >= self.max_instances:
                self._evict_least_used_instance()
            
            # 创建新实例
            service = UnifiedAIService(db_session, suppress_warning)
            entry = AIServiceCacheEntry(
                service=service,
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
            
            self._instances[cache_key] = entry
            
            # 添加弱引用
            weak_ref = weakref.ref(service, self._cleanup_weak_ref)
            self._active_refs.add(weak_ref)
            
            self.logger.debug(f"Created new AI service instance: {cache_key}")
            return service
    
    def _cleanup_weak_ref(self, ref):
        """清理弱引用"""
        self._active_refs.discard(ref)
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        with self.lock:
            now = datetime.now()
            return {
                "total_instances": len(self._instances),
                "max_instances": self.max_instances,
                "active_references": len(self._active_refs),
                "instance_details": [
                    {
                        "key": key,
                        "created_at": entry.created_at.isoformat(),
                        "last_accessed": entry.last_accessed.isoformat(),
                        "access_count": entry.access_count,
                        "age_hours": (now - entry.created_at).total_seconds() / 3600
                    }
                    for key, entry in self._instances.items()
                ]
            }
    
    def clear_cache(self):
        """清空缓存"""
        with self.lock:
            self._instances.clear()
            self._active_refs.clear()
            self.logger.info("AI service cache cleared")


# 全局AI服务池
_ai_service_pool = AIServicePool()


def get_ai_service(db_session=None, suppress_warning=False) -> UnifiedAIService:
    """
    获取AI服务实例（智能连接池模式）
    
    Args:
        db_session: 数据库会话，如果为None则使用默认会话
        suppress_warning: 如果为True，则不显示未提供数据库会话的警告
        
    Returns:
        UnifiedAIService实例
    """
    return _ai_service_pool.get_service(db_session, suppress_warning)


def get_ai_service_pool() -> AIServicePool:
    """获取AI服务连接池"""
    return _ai_service_pool


def clear_ai_service_cache():
    """清空AI服务缓存"""
    _ai_service_pool.clear_cache()
