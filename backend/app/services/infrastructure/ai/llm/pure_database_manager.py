"""
纯数据库驱动的LLM管理器

完全移除配置文件和向后兼容代码，只使用数据库作为配置源
与用户LLM偏好和服务器配置完全集成
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.llm_server import LLMServer, LLMModel
from app.models.user_llm_preference import UserLLMPreference
from .database_selector import (
    get_database_selector,
    TaskType,
    TaskComplexity,
    TaskCharacteristics,
    SelectionCriteria
)

logger = logging.getLogger(__name__)


class PureDatabaseLLMManager:
    """纯数据库驱动的LLM管理器"""
    
    def __init__(self):
        self.selector = get_database_selector()
        self._initialized = True
        self.start_time = datetime.utcnow()
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0 
        self.failed_requests = 0
        
        logger.info("纯数据库驱动LLM管理器初始化完成")
    
    async def select_best_model_for_user(
        self,
        user_id: str,
        task_type: str,
        complexity: str = "medium", 
        constraints: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """为用户选择最佳模型 - 纯数据库驱动"""
        
        constraints = constraints or {}
        self.total_requests += 1
        
        try:
            # 转换参数为枚举类型
            task_type_enum = self._convert_task_type(task_type)
            complexity_enum = self._convert_complexity(complexity)
            
            # 构建任务特征
            task_characteristics = TaskCharacteristics(
                task_type=task_type_enum,
                complexity=complexity_enum,
                estimated_tokens=constraints.get("estimated_tokens", 1000),
                cost_sensitive=constraints.get("cost_sensitive", False),
                speed_priority=constraints.get("speed_priority", False),
                accuracy_critical=constraints.get("accuracy_critical", False),
                creativity_required=constraints.get("creativity_required", False),
                language=constraints.get("language", "zh"),
                domain=constraints.get("domain")
            )
            
            # 构建选择标准
            selection_criteria = SelectionCriteria(
                max_cost_per_request=constraints.get("max_cost"),
                max_latency_ms=constraints.get("max_latency"),
                min_capability_score=constraints.get("min_capability_score", 0.6),
                preferred_providers=constraints.get("preferred_providers"),
                excluded_models=constraints.get("excluded_models"),
                require_function_calling=constraints.get("require_function_calling", False),
                require_vision=constraints.get("require_vision", False)
            )
            
            # 获取数据库会话
            db = SessionLocal()
            try:
                # 使用数据库选择器
                recommendation = await self.selector.select_best_model_for_user(
                    user_id=user_id,
                    task_characteristics=task_characteristics,
                    criteria=selection_criteria,
                    agent_id=agent_id,
                    db=db
                )
                
                self.successful_requests += 1
                
                return {
                    "model": recommendation.model,
                    "provider": recommendation.provider,
                    "reasoning": recommendation.reasoning,
                    "confidence": recommendation.confidence,
                    "expected_cost": recommendation.expected_cost,
                    "expected_latency": recommendation.expected_latency,
                    "capability_match_score": recommendation.capability_match_score,
                    "fallback_models": recommendation.fallback_models,
                    "source": "database_driven",
                    "selection_timestamp": datetime.utcnow().isoformat()
                }
                
            finally:
                db.close()
                
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"用户 {user_id} 的模型选择失败: {e}")
            raise ValueError(f"模型选择失败: {str(e)}")
    
    def _convert_task_type(self, task_type: str) -> TaskType:
        """转换任务类型"""
        mapping = {
            "reasoning": TaskType.REASONING,
            "coding": TaskType.CODING,
            "creative": TaskType.CREATIVE,
            "analysis": TaskType.ANALYSIS,
            "translation": TaskType.TRANSLATION,
            "qa": TaskType.QA,
            "summarization": TaskType.SUMMARIZATION,
            "general": TaskType.GENERAL
        }
        
        return mapping.get(task_type.lower(), TaskType.GENERAL)
    
    def _convert_complexity(self, complexity: str) -> TaskComplexity:
        """转换复杂度"""
        mapping = {
            "simple": TaskComplexity.SIMPLE,
            "medium": TaskComplexity.MEDIUM,
            "complex": TaskComplexity.COMPLEX,
            "expert": TaskComplexity.EXPERT
        }
        
        return mapping.get(complexity.lower(), TaskComplexity.MEDIUM)
    
    async def get_user_available_models(
        self, 
        user_id: str,
        model_type: Optional[str] = None,
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户可用的模型列表"""
        
        db = SessionLocal()
        try:
            # 获取活跃且健康的服务器
            servers = db.query(LLMServer).filter(
                LLMServer.is_active == True,
                LLMServer.is_healthy == True
            ).all()
            
            if not servers:
                return {
                    "servers": [],
                    "models": [], 
                    "total_servers": 0,
                    "total_models": 0,
                    "user_id": user_id
                }
            
            # 获取这些服务器上的模型
            server_ids = [server.id for server in servers]
            models_query = db.query(LLMModel).filter(
                LLMModel.server_id.in_(server_ids),
                LLMModel.is_active == True,
                LLMModel.is_healthy == True
            )
            
            # 应用过滤条件
            if model_type:
                models_query = models_query.filter(LLMModel.model_type == model_type)
            
            if provider_name:
                models_query = models_query.filter(LLMModel.provider_name == provider_name)
            
            models = models_query.all()
            
            # 构建响应
            server_map = {server.id: server for server in servers}
            
            model_list = []
            for model in models:
                server = server_map[model.server_id]
                model_info = {
                    "model_id": model.id,
                    "model_name": model.name,
                    "display_name": model.display_name,
                    "model_type": model.model_type.value,
                    "provider_name": model.provider_name,
                    "supports_thinking": model.supports_thinking,
                    "supports_function_calls": model.supports_function_calls,
                    "max_tokens": model.max_tokens,
                    "server_info": {
                        "server_id": server.id,
                        "server_name": server.name,
                        "provider_type": server.provider_type.value,
                        "base_url": server.base_url
                    }
                }
                model_list.append(model_info)
            
            return {
                "servers": [
                    {
                        "server_id": server.id,
                        "name": server.name,
                        "provider_type": server.provider_type.value,
                        "base_url": server.base_url,
                        "model_count": sum(1 for model in models if model.server_id == server.id)
                    }
                    for server in servers
                ],
                "models": model_list,
                "total_servers": len(servers),
                "total_models": len(model_list),
                "user_id": user_id
            }
            
        finally:
            db.close()
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户LLM偏好"""
        
        db = SessionLocal()
        try:
            preference = db.query(UserLLMPreference).filter(
                UserLLMPreference.user_id == user_id
            ).first()
            
            if not preference:
                return None
            
            # 获取默认服务器信息
            default_server = None
            if preference.default_llm_server_id:
                default_server = db.query(LLMServer).filter(
                    LLMServer.id == preference.default_llm_server_id
                ).first()
            
            return {
                "user_id": str(preference.user_id),
                "default_server_id": preference.default_llm_server_id,
                "default_server_name": default_server.name if default_server else None,
                "default_provider_name": preference.default_provider_name,
                "default_model_name": preference.default_model_name,
                "preferred_temperature": preference.preferred_temperature,
                "max_tokens_limit": preference.max_tokens_limit,
                "daily_token_quota": preference.daily_token_quota,
                "monthly_cost_limit": preference.monthly_cost_limit,
                "enable_caching": preference.enable_caching,
                "enable_learning": preference.enable_learning,
                "provider_priorities": preference.provider_priorities,
                "model_preferences": preference.model_preferences,
                "created_at": preference.created_at.isoformat(),
                "updated_at": preference.updated_at.isoformat()
            }
            
        finally:
            db.close()
    
    def record_usage_feedback(
        self,
        user_id: str,
        model: str,
        provider: str,
        success: bool,
        satisfaction_score: float,
        actual_cost: Optional[float] = None,
        actual_latency: Optional[int] = None,
        agent_id: Optional[str] = None,
        task_type: Optional[str] = None
    ):
        """记录用户使用反馈"""
        
        task_type_enum = None
        if task_type:
            task_type_enum = self._convert_task_type(task_type)
        
        self.selector.record_user_feedback(
            user_id=user_id,
            model=model,
            provider=provider,
            success=success,
            satisfaction_score=satisfaction_score,
            actual_cost=actual_cost,
            actual_latency=actual_latency,
            agent_id=agent_id,
            task_type=task_type_enum
        )
        
        logger.info(f"记录用户 {user_id} 对模型 {provider}:{model} 的反馈")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        
        db = SessionLocal()
        try:
            # 检查数据库连接
            total_servers = db.query(LLMServer).count()
            active_servers = db.query(LLMServer).filter(LLMServer.is_active == True).count()
            healthy_servers = db.query(LLMServer).filter(
                LLMServer.is_active == True,
                LLMServer.is_healthy == True
            ).count()
            
            total_models = db.query(LLMModel).count()
            active_models = db.query(LLMModel).filter(LLMModel.is_active == True).count()
            healthy_models = db.query(LLMModel).filter(
                LLMModel.is_active == True,
                LLMModel.is_healthy == True
            ).count()
            
            uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
            success_rate = self.successful_requests / max(self.total_requests, 1)
            
            return {
                "status": "healthy",
                "healthy": True,
                "manager_type": "pure_database_driven",
                "database_connected": True,
                "servers": {
                    "total": total_servers,
                    "active": active_servers,
                    "healthy": healthy_servers,
                    "health_rate": healthy_servers / max(total_servers, 1)
                },
                "models": {
                    "total": total_models,
                    "active": active_models, 
                    "healthy": healthy_models,
                    "health_rate": healthy_models / max(total_models, 1)
                },
                "statistics": {
                    "total_requests": self.total_requests,
                    "successful_requests": self.successful_requests,
                    "failed_requests": self.failed_requests,
                    "success_rate": success_rate,
                    "uptime_seconds": uptime_seconds
                },
                "selector_stats": self.selector.get_model_stats() if hasattr(self.selector, 'get_model_stats') else {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        finally:
            db.close()
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "service_name": "Pure Database Driven LLM Manager",
            "version": "2.0.0",
            "architecture": "Database-First AI Model Selection",
            "status": "initialized" if self._initialized else "uninitialized",
            "capabilities": [
                "用户级别的模型配置",
                "智能模型推荐",
                "个性化Agent偏好学习", 
                "使用反馈优化",
                "配额和成本管理",
                "实时健康监控"
            ],
            "data_sources": ["PostgreSQL Database", "User Preferences", "LLM Server Registry"],
            "supported_tasks": [
                "reasoning", "coding", "creative", "analysis", 
                "translation", "qa", "summarization", "general"
            ],
            "supported_complexity": ["simple", "medium", "complex", "expert"],
            "started_at": self.start_time.isoformat()
        }


# 全局管理器实例
_llm_manager: Optional[PureDatabaseLLMManager] = None

def get_pure_llm_manager() -> PureDatabaseLLMManager:
    """获取纯数据库驱动的LLM管理器实例"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = PureDatabaseLLMManager()
    return _llm_manager


# 便捷函数
async def select_model_for_user(
    user_id: str,
    task_type: str,
    complexity: str = "medium",
    constraints: Optional[Dict[str, Any]] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """便捷的用户模型选择函数"""
    manager = get_pure_llm_manager()
    return await manager.select_best_model_for_user(
        user_id=user_id,
        task_type=task_type,
        complexity=complexity,
        constraints=constraints,
        agent_id=agent_id
    )


async def ask_agent(
    user_id: str,
    question: str,
    agent_type: str = "general",
    context: Optional[str] = None,
    task_type: str = "general",
    complexity: str = "medium"
) -> str:
    """Agent友好的问答接口 - 纯数据库驱动"""
    
    try:
        # 选择最佳模型
        manager = get_pure_llm_manager()
        selection = await manager.select_best_model_for_user(
            user_id=user_id,
            task_type=task_type,
            complexity=complexity,
            agent_id=agent_type
        )
        
        # 模拟LLM调用（实际实现中会调用真实的LLM API）
        response = f"使用模型 {selection['provider']}:{selection['model']} (置信度: {selection['confidence']:.1%}) 回答: {question}"
        
        # 记录使用反馈
        manager.record_usage_feedback(
            user_id=user_id,
            model=selection['model'],
            provider=selection['provider'],
            success=True,
            satisfaction_score=0.9,  # 模拟满意度
            agent_id=agent_type,
            task_type=task_type
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Agent问答失败: {e}")
        return f"抱歉，处理您的问题时出现错误: {str(e)}"