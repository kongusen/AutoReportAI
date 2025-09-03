"""
简化的模型选择器 - 基于模型特性和用户配置
专注于实际场景：用户可能只配置1-2个模型，基于ModelType进行智能选择
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.llm_server import LLMServer, LLMModel, ModelType
from app.models.user_llm_preference import UserLLMPreference
from app.crud.crud_llm_server import crud_llm_server
from app.crud.crud_llm_model import crud_llm_model

logger = logging.getLogger(__name__)


@dataclass
class TaskRequirement:
    """任务需求"""
    requires_thinking: bool = False  # 是否需要深度思考
    cost_sensitive: bool = False     # 是否对成本敏感
    speed_priority: bool = False     # 是否优先速度
    

@dataclass
class ModelSelection:
    """模型选择结果"""
    model_id: int
    model_name: str
    model_type: ModelType
    server_id: int
    server_name: str
    provider_type: str
    reasoning: str
    fallback_model_id: Optional[int] = None


class SimpleModelSelector:
    """简化的模型选择器"""
    
    def __init__(self):
        logger.info("简化模型选择器初始化完成")
    
    def select_model_for_user(
        self,
        user_id: str,
        task_requirement: TaskRequirement,
        db: Optional[Session] = None
    ) -> Optional[ModelSelection]:
        """为用户选择最适合的模型"""
        
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
        
        try:
            # 1. 获取用户配置的可用模型
            available_models = self._get_user_available_models(db, user_id)
            
            if not available_models:
                logger.warning(f"用户 {user_id} 没有可用的模型")
                return None
            
            logger.info(f"用户 {user_id} 有 {len(available_models)} 个可用模型")
            
            # 2. 基于任务需求选择模型
            selected_model = self._select_by_task_requirement(
                available_models, task_requirement
            )
            
            # 3. 生成选择结果
            if selected_model:
                return self._build_selection_result(selected_model, available_models, task_requirement)
            
            return None
            
        except Exception as e:
            logger.error(f"模型选择失败: {e}")
            return None
        finally:
            if should_close_db:
                db.close()
    
    def _get_user_available_models(self, db: Session, user_id: str) -> List[Tuple[LLMModel, LLMServer]]:
        """获取用户配置的可用模型"""
        
        # 获取用户的活跃且健康的服务器
        servers = crud_llm_server.get_multi_by_filter(
            db, user_id=user_id, is_active=True, is_healthy=True
        )
        
        if not servers:
            return []
        
        # 获取这些服务器上的活跃且健康的模型（排除IMAGE模型）
        available_models = []
        for server in servers:
            models = crud_llm_model.get_models_by_filter(
                db, 
                server_id=server.id,
                is_active=True,
                is_healthy=True
            )
            
            # 过滤掉IMAGE模型，只保留CHAT和THINK模型
            for model in models:
                if model.model_type in [ModelType.CHAT, ModelType.THINK]:
                    available_models.append((model, server))
        
        return available_models
    
    def _select_by_task_requirement(
        self,
        available_models: List[Tuple[LLMModel, LLMServer]],
        task_requirement: TaskRequirement
    ) -> Optional[Tuple[LLMModel, LLMServer]]:
        """基于任务需求选择模型"""
        
        if not available_models:
            return None
        
        # 1. 优先级：如果需要思考，优先选择THINK模型
        if task_requirement.requires_thinking:
            think_models = [
                (model, server) for model, server in available_models
                if model.model_type == ModelType.THINK and model.supports_thinking
            ]
            if think_models:
                # 选择优先级最高的THINK模型
                return min(think_models, key=lambda x: x[0].priority)
        
        # 2. 如果对成本敏感，选择优先级较低的模型（通常成本更低）
        if task_requirement.cost_sensitive:
            chat_models = [
                (model, server) for model, server in available_models
                if model.model_type == ModelType.CHAT
            ]
            if chat_models:
                # 选择优先级数字最大的（成本最低的）
                return max(chat_models, key=lambda x: x[0].priority)
        
        # 3. 如果优先速度，选择优先级最高的CHAT模型
        if task_requirement.speed_priority:
            chat_models = [
                (model, server) for model, server in available_models
                if model.model_type == ModelType.CHAT
            ]
            if chat_models:
                return min(chat_models, key=lambda x: x[0].priority)
        
        # 4. 默认策略：选择优先级最高的模型
        return min(available_models, key=lambda x: x[0].priority)
    
    def _build_selection_result(
        self,
        selected: Tuple[LLMModel, LLMServer],
        all_available: List[Tuple[LLMModel, LLMServer]],
        task_requirement: TaskRequirement
    ) -> ModelSelection:
        """构建选择结果"""
        
        model, server = selected
        
        # 生成选择理由
        reasoning_parts = []
        
        if model.model_type == ModelType.THINK and task_requirement.requires_thinking:
            reasoning_parts.append("选择思考模型以支持深度推理")
        elif model.model_type == ModelType.CHAT:
            reasoning_parts.append("选择对话模型处理常规任务")
        
        if task_requirement.cost_sensitive:
            reasoning_parts.append("考虑成本效益")
        
        if task_requirement.speed_priority:
            reasoning_parts.append("优先响应速度")
        
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "基于用户配置选择"
        
        # 寻找备选模型
        fallback_model_id = None
        remaining_models = [(m, s) for m, s in all_available if m.id != model.id]
        if remaining_models:
            fallback_model, _ = min(remaining_models, key=lambda x: x[0].priority)
            fallback_model_id = fallback_model.id
        
        return ModelSelection(
            model_id=model.id,
            model_name=model.name,
            model_type=model.model_type,
            server_id=server.id,
            server_name=server.name,
            provider_type=server.provider_type,
            reasoning=reasoning,
            fallback_model_id=fallback_model_id
        )
    
    def get_user_model_stats(self, user_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """获取用户模型配置统计"""
        
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
        
        try:
            available_models = self._get_user_available_models(db, user_id)
            
            stats = {
                "total_models": len(available_models),
                "chat_models": len([(m, s) for m, s in available_models if m.model_type == ModelType.CHAT]),
                "think_models": len([(m, s) for m, s in available_models if m.model_type == ModelType.THINK]),
                "servers_count": len(set(s.id for m, s in available_models)),
                "models_by_server": {}
            }
            
            # 按服务器分组统计
            for model, server in available_models:
                server_name = server.name
                if server_name not in stats["models_by_server"]:
                    stats["models_by_server"][server_name] = {
                        "chat": 0,
                        "think": 0,
                        "total": 0
                    }
                
                stats["models_by_server"][server_name]["total"] += 1
                if model.model_type == ModelType.CHAT:
                    stats["models_by_server"][server_name]["chat"] += 1
                elif model.model_type == ModelType.THINK:
                    stats["models_by_server"][server_name]["think"] += 1
            
            return stats
            
        finally:
            if should_close_db:
                db.close()


# 全局实例
_simple_selector: Optional[SimpleModelSelector] = None


def get_simple_model_selector() -> SimpleModelSelector:
    """获取简化模型选择器实例"""
    global _simple_selector
    if _simple_selector is None:
        _simple_selector = SimpleModelSelector()
    return _simple_selector