"""
真正的数据库驱动LLM管理器
替换硬编码的pure_database_manager，完全基于用户配置的模型
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.db.session import get_db
from app.models.llm_server import LLMServer, LLMModel, ModelType, ProviderType
from app.crud.crud_llm_server import crud_llm_server
from app.crud.crud_llm_model import crud_llm_model

logger = logging.getLogger(__name__)


class DatabaseDrivenLLMManager:
    """完全基于数据库的LLM管理器 - 使用用户配置的模型"""
    
    def __init__(self):
        self.is_initialized = False
    
    async def initialize(self):
        """初始化管理器"""
        if not self.is_initialized:
            logger.info("初始化数据库驱动LLM管理器")
            self.is_initialized = True
    
    async def select_best_model_for_user(
        self,
        user_id: str,
        task_type: str,
        complexity: str = "medium",
        constraints: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """为用户选择最佳模型 - 基于数据库中的真实配置"""
        await self.initialize()
        
        constraints = constraints or {}
        preferred_providers = constraints.get("preferred_providers", [])
        
        # 获取数据库会话
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            # 1. 获取所有健康且活跃的模型
            available_models = self._get_available_models(db, user_id)
            
            if not available_models:
                logger.warning(f"用户 {user_id} 没有可用的模型配置")
                raise ValueError("没有可用的模型配置，请先在系统中配置LLM Server和模型")
            
            logger.info(f"用户 {user_id} 找到 {len(available_models)} 个可用模型")
            
            # 2. 根据任务类型和复杂度筛选模型
            best_model = self._select_best_model(
                available_models, 
                task_type, 
                complexity, 
                preferred_providers
            )
            
            if not best_model:
                # 如果没找到理想模型，使用第一个可用的
                best_model = available_models[0]
                logger.warning(f"没有找到理想模型，使用默认模型: {best_model[0].name}")
            
            model, server = best_model
            
            result = {
                "model": model.name,
                "provider": model.provider_name,
                "display_name": model.display_name,
                "model_type": model.model_type,
                "server_id": server.server_id,
                "server_name": server.name,
                "base_url": server.base_url,
                "api_key": server.api_key,
                "provider_type": server.provider_type.value,
                "confidence": 0.9,  # 基于配置的置信度
                "reasoning": f"从用户配置中选择: {model.display_name} ({server.name})",
                "supports_thinking": model.supports_thinking,
                "max_tokens": model.max_tokens,
                "temperature_default": model.temperature_default
            }
            
            logger.info(f"为用户 {user_id} 选择模型: {result['provider']}:{result['model']} (类型: {result['model_type']}, 服务器: {result['server_name']}, 支持思考: {result['supports_thinking']})")
            return result
            
        except Exception as e:
            logger.error(f"为用户 {user_id} 选择模型失败: {e}")
            raise
        finally:
            db.close()
    
    def _get_available_models(self, db: Session, user_id: str) -> List[Tuple[LLMModel, LLMServer]]:
        """获取用户的所有可用模型"""
        # 查询用户的健康模型和服务器
        models_with_servers = db.query(LLMModel, LLMServer).join(
            LLMServer, LLMModel.server_id == LLMServer.id
        ).filter(
            and_(
                LLMServer.user_id == user_id,
                LLMServer.is_active == True,
                LLMServer.is_healthy == True,
                LLMModel.is_active == True,
                LLMModel.is_healthy == True
            )
        ).order_by(LLMModel.priority.asc()).all()
        
        return models_with_servers
    
    def _select_best_model(
        self,
        available_models: List[Tuple[LLMModel, LLMServer]],
        task_type: str,
        complexity: str,
        preferred_providers: List[str]
    ) -> Optional[Tuple[LLMModel, LLMServer]]:
        """从可用模型中选择最佳模型"""
        
        # 评分函数
        def score_model(model_server_pair) -> int:
            model, server = model_server_pair
            score = 0
            
            # 1. 提供商偏好 (+20分)
            if model.provider_name in preferred_providers:
                score += 20
            
            # 2. 模型类型匹配 (+20分，reasoning任务强烈偏好think模型)
            if task_type == "reasoning" and model.model_type == ModelType.THINK.value:
                score += 20  # reasoning任务优先选择think模型
                logger.debug(f"reasoning任务匹配think模型 +20分: {model.name}")
            elif task_type == "reasoning" and model.supports_thinking:
                score += 15  # 支持thinking的模型也有加分
                logger.debug(f"reasoning任务匹配支持思考的模型 +15分: {model.name}")
            elif task_type != "reasoning" and model.model_type == ModelType.DEFAULT.value:
                score += 10  # 非reasoning任务偏好default模型
            
            # 3. 复杂度匹配 (+10分)
            if complexity == "complex" and model.supports_thinking:
                score += 10
            elif complexity == "simple" and not model.supports_thinking:
                score += 5
            
            # 4. 优先级权重 (优先级越低分数越高)
            score += max(0, 50 - model.priority)
            
            # 5. 健康状态 (+5分)
            if model.is_healthy and server.is_healthy:
                score += 5
            
            return score
        
        # 按评分排序，选择得分最高的模型
        scored_models = [(score_model(pair), pair) for pair in available_models]
        scored_models.sort(key=lambda x: x[0], reverse=True)
        
        if scored_models:
            best_score, best_pair = scored_models[0]
            logger.debug(f"选择模型得分: {best_score}, 模型: {best_pair[0].name}")
            return best_pair
        
        return None
    
    async def get_user_available_models(
        self,
        user_id: str,
        model_type: Optional[str] = None,
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户可用的模型列表"""
        await self.initialize()
        
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            available_pairs = self._get_available_models(db, user_id)
            
            # 过滤条件
            if model_type:
                available_pairs = [(m, s) for m, s in available_pairs if m.model_type == model_type]
            if provider_name:
                available_pairs = [(m, s) for m, s in available_pairs if m.provider_name == provider_name]
            
            # 构建返回数据
            models_info = {}
            for model, server in available_pairs:
                models_info[f"{model.provider_name}:{model.name}"] = {
                    "name": model.name,
                    "display_name": model.display_name,
                    "provider": model.provider_name,
                    "provider_type": server.provider_type.value,
                    "model_type": model.model_type,
                    "server_name": server.name,
                    "base_url": server.base_url,
                    "supports_thinking": model.supports_thinking,
                    "max_tokens": model.max_tokens,
                    "priority": model.priority,
                    "is_healthy": model.is_healthy and server.is_healthy
                }
            
            return {
                "available_models": models_info,
                "total_count": len(models_info),
                "user_id": user_id
            }
            
        finally:
            db.close()
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户LLM偏好 - 基于用户配置的模型推断"""
        models_info = await self.get_user_available_models(user_id)
        
        if not models_info["available_models"]:
            return None
        
        # 分析用户配置的模型类型，推断偏好
        models = models_info["available_models"]
        providers = set(m["provider"] for m in models.values())
        has_thinking_models = any(m["supports_thinking"] for m in models.values())
        
        return {
            "available_providers": list(providers),
            "preferred_provider": list(providers)[0] if providers else None,
            "supports_thinking": has_thinking_models,
            "total_configured_models": models_info["total_count"]
        }
    
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
        logger.info(f"记录用户反馈: {user_id}, 模型: {provider}:{model}, 满意度: {satisfaction_score}, 成功: {success}")
        # TODO: 存储到数据库用于模型选择优化
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            # 统计所有用户的模型配置
            total_servers = db.query(LLMServer).filter(LLMServer.is_active == True).count()
            healthy_servers = db.query(LLMServer).filter(
                and_(LLMServer.is_active == True, LLMServer.is_healthy == True)
            ).count()
            
            total_models = db.query(LLMModel).filter(LLMModel.is_active == True).count()
            healthy_models = db.query(LLMModel).filter(
                and_(LLMModel.is_active == True, LLMModel.is_healthy == True)
            ).count()
            
            return {
                "status": "healthy",
                "healthy": True,
                "manager_type": "database_driven",
                "total_servers": total_servers,
                "healthy_servers": healthy_servers,
                "total_models": total_models,
                "healthy_models": healthy_models,
                "server_health_rate": (healthy_servers / total_servers * 100) if total_servers > 0 else 0,
                "model_health_rate": (healthy_models / total_models * 100) if total_models > 0 else 0,
                "initialized": self.is_initialized
            }
            
        finally:
            db.close()


# 全局管理器实例
_database_llm_manager = None

def get_database_llm_manager() -> DatabaseDrivenLLMManager:
    """获取数据库驱动LLM管理器实例"""
    global _database_llm_manager
    if _database_llm_manager is None:
        _database_llm_manager = DatabaseDrivenLLMManager()
    return _database_llm_manager


# 便捷接口函数
async def select_model_for_user_from_db(
    user_id: str,
    task_type: str,
    complexity: str = "medium",
    constraints: Optional[Dict[str, Any]] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """从数据库为用户选择模型"""
    manager = get_database_llm_manager()
    return await manager.select_best_model_for_user(
        user_id, task_type, complexity, constraints, agent_id
    )