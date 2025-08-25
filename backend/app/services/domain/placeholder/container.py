"""
服务容器

管理各层依赖注入和生命周期
"""
import logging
from sqlalchemy.orm import Session
from typing import Optional

from .models import (
    CacheServiceInterface, AgentAnalysisServiceInterface,
    TemplateRuleServiceInterface, DataExecutionServiceInterface
)
from .router import PlaceholderRouter, PlaceholderBatchRouter
from .cache_service import CacheService
# 旧的AgentAnalysisService已移除，使用新的Agent系统
# from .agent_service import AgentAnalysisService
from .rule_service import TemplateRuleService
from .execution_service import DataExecutionService


class PlaceholderServiceContainer:
    """占位符服务容器 - 管理各层依赖"""
    
    def __init__(self, db_session: Session, user_id: Optional[str] = None):
        self.db_session = db_session
        self.user_id = user_id or "system"
        self.logger = logging.getLogger(__name__)
        
        # 各层服务实例
        self._cache_service: Optional[CacheServiceInterface] = None
        self._execution_service: Optional[DataExecutionServiceInterface] = None
        self._agent_service: Optional[AgentAnalysisServiceInterface] = None
        self._rule_service: Optional[TemplateRuleServiceInterface] = None
        self._router: Optional[PlaceholderRouter] = None
        self._batch_router: Optional[PlaceholderBatchRouter] = None
        
        # 初始化服务
        self._initialize_services()
    
    def _initialize_services(self):
        """初始化各层服务"""
        try:
            # 1. 数据执行层（底层）
            self._execution_service = DataExecutionService(self.db_session)
            
            # 2. 缓存层
            self._cache_service = CacheService(self.db_session)
            
            # 3. Agent分析层（使用新的Agent系统）
            # 新的Agent系统通过门面服务调用，不在容器中直接初始化
            self._agent_service = None  # 将使用新的PlaceholderSQLAgent
            
            # 4. 模板规则层
            self._rule_service = TemplateRuleService(self.db_session)
            self._rule_service.set_execution_service(self._execution_service)
            
            # 5. 路由层（顶层）
            self._router = PlaceholderRouter(
                cache_service=self._cache_service,
                agent_service=self._agent_service,
                rule_service=self._rule_service,
                execution_service=self._execution_service
            )
            
            # 6. 批量路由层
            self._batch_router = PlaceholderBatchRouter(self._router)
            
            self.logger.info("占位符服务容器初始化完成")
            
        except Exception as e:
            self.logger.error(f"服务容器初始化失败: {e}", exc_info=True)
            raise
    
    @property
    def cache_service(self) -> CacheServiceInterface:
        """获取缓存服务"""
        return self._cache_service
    
    @property
    def execution_service(self) -> DataExecutionServiceInterface:
        """获取执行服务"""
        return self._execution_service
    
    @property
    def agent_service(self) -> AgentAnalysisServiceInterface:
        """获取Agent分析服务"""
        return self._agent_service
    
    @property
    def rule_service(self) -> TemplateRuleServiceInterface:
        """获取规则服务"""
        return self._rule_service
    
    @property
    def router(self) -> PlaceholderRouter:
        """获取单个占位符路由器"""
        return self._router
    
    @property
    def batch_router(self) -> PlaceholderBatchRouter:
        """获取批量占位符路由器"""
        return self._batch_router
    
    async def health_check(self) -> dict:
        """健康检查"""
        try:
            health_status = {
                "container": "healthy",
                "services": {
                    "cache_service": "unknown",
                    "execution_service": "unknown", 
                    "agent_service": "unknown",
                    "rule_service": "unknown",
                    "router": "unknown"
                },
                "user_id": self.user_id,
                "initialized": True
            }
            
            # 检查各服务状态
            try:
                if self._cache_service:
                    # 缓存服务健康检查
                    from .cache_service import CacheMetrics
                    cache_metrics = CacheMetrics(self.db_session)
                    cache_stats = await cache_metrics.get_cache_stats()
                    health_status["services"]["cache_service"] = "healthy"
                    health_status["cache_stats"] = cache_stats
                else:
                    health_status["services"]["cache_service"] = "not_initialized"
            except Exception as e:
                health_status["services"]["cache_service"] = f"error: {str(e)}"
            
            try:
                if self._execution_service:
                    health_status["services"]["execution_service"] = "healthy"
                else:
                    health_status["services"]["execution_service"] = "not_initialized"
            except Exception as e:
                health_status["services"]["execution_service"] = f"error: {str(e)}"
            
            try:
                if self._agent_service:
                    health_status["services"]["agent_service"] = "healthy"
                else:
                    health_status["services"]["agent_service"] = "not_initialized"
            except Exception as e:
                health_status["services"]["agent_service"] = f"error: {str(e)}"
            
            try:
                if self._rule_service:
                    health_status["services"]["rule_service"] = "healthy"
                else:
                    health_status["services"]["rule_service"] = "not_initialized"
            except Exception as e:
                health_status["services"]["rule_service"] = f"error: {str(e)}"
            
            try:
                if self._router:
                    health_status["services"]["router"] = "healthy"
                else:
                    health_status["services"]["router"] = "not_initialized"
            except Exception as e:
                health_status["services"]["router"] = f"error: {str(e)}"
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            return {
                "container": "unhealthy",
                "error": str(e),
                "user_id": self.user_id,
                "initialized": False
            }
    
    async def cleanup(self):
        """清理资源"""
        try:
            self.logger.info("开始清理占位符服务容器资源")
            
            # 清理各服务资源
            if hasattr(self._execution_service, 'cleanup'):
                await self._execution_service.cleanup()
            
            if hasattr(self._cache_service, 'cleanup'):
                await self._cache_service.cleanup()
            
            if hasattr(self._agent_service, 'cleanup'):
                await self._agent_service.cleanup()
            
            if hasattr(self._rule_service, 'cleanup'):
                await self._rule_service.cleanup()
            
            self.logger.info("占位符服务容器资源清理完成")
            
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")


class PlaceholderServiceFactory:
    """占位符服务工厂"""
    
    @staticmethod
    def create_container(db_session: Session, user_id: Optional[str] = None) -> PlaceholderServiceContainer:
        """创建服务容器"""
        try:
            container = PlaceholderServiceContainer(db_session, user_id)
            return container
        except Exception as e:
            logging.getLogger(__name__).error(f"创建服务容器失败: {e}")
            raise
    
    @staticmethod
    def create_router_only(db_session: Session, user_id: Optional[str] = None) -> PlaceholderRouter:
        """只创建路由器（用于简单场景）"""
        container = PlaceholderServiceFactory.create_container(db_session, user_id)
        return container.router
    
    @staticmethod
    def create_batch_router_only(db_session: Session, user_id: Optional[str] = None) -> PlaceholderBatchRouter:
        """只创建批量路由器（用于批量处理场景）"""
        container = PlaceholderServiceFactory.create_container(db_session, user_id)
        return container.batch_router


# 全局容器管理器（可选）
class GlobalContainerManager:
    """全局容器管理器 - 用于管理多个用户的容器实例"""
    
    def __init__(self):
        self._containers = {}
        self.logger = logging.getLogger(__name__)
    
    def get_container(self, db_session: Session, user_id: str) -> PlaceholderServiceContainer:
        """获取或创建用户容器"""
        container_key = f"user_{user_id}"
        
        if container_key not in self._containers:
            self._containers[container_key] = PlaceholderServiceFactory.create_container(
                db_session, user_id
            )
            self.logger.info(f"创建新的用户容器: {user_id}")
        
        return self._containers[container_key]
    
    async def cleanup_user_container(self, user_id: str):
        """清理用户容器"""
        container_key = f"user_{user_id}"
        
        if container_key in self._containers:
            container = self._containers[container_key]
            await container.cleanup()
            del self._containers[container_key]
            self.logger.info(f"清理用户容器: {user_id}")
    
    async def cleanup_all(self):
        """清理所有容器"""
        for container_key, container in self._containers.items():
            try:
                await container.cleanup()
            except Exception as e:
                self.logger.error(f"清理容器失败 {container_key}: {e}")
        
        self._containers.clear()
        self.logger.info("清理所有容器完成")


# 单例容器管理器
global_container_manager = GlobalContainerManager()