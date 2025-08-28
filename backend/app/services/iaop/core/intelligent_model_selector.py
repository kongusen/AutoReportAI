"""
智能模型选择器
基于任务类型、用户偏好和模型能力选择最优LLM模型
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.llm_server import LLMModel, ModelType
from app.models.user_llm_preference import UserLLMPreference
from app.crud.crud_llm_model import crud_llm_model
from app.crud.crud_user_llm_preference import crud_user_llm_preference
from app.crud.crud_llm_server import crud_llm_server

logger = logging.getLogger(__name__)


class IAOPTaskType:
    """IAOP任务类型枚举"""
    SQL_GENERATION = "sql_generation"           # SQL生成
    BUSINESS_ANALYSIS = "business_analysis"     # 业务分析
    DATA_INTERPRETATION = "data_interpretation" # 数据解释
    REPORT_WRITING = "report_writing"           # 报告撰写
    PLACEHOLDER_ANALYSIS = "placeholder_analysis" # 占位符分析
    CONTEXT_UNDERSTANDING = "context_understanding" # 上下文理解
    IMAGE_ANALYSIS = "image_analysis"           # 图像分析
    DOCUMENT_EMBEDDING = "document_embedding"   # 文档嵌入


class ModelTypeMapping:
    """任务类型到模型类型的映射"""
    
    # 任务类型优先需要的模型类型（按优先级排序）
    TASK_TO_MODEL_TYPE = {
        IAOPTaskType.SQL_GENERATION: [ModelType.THINK, ModelType.CHAT],      # 优先思考模型，备选聊天模型
        IAOPTaskType.BUSINESS_ANALYSIS: [ModelType.THINK, ModelType.CHAT],   # 优先思考模型
        IAOPTaskType.DATA_INTERPRETATION: [ModelType.THINK, ModelType.CHAT], # 优先思考模型
        IAOPTaskType.REPORT_WRITING: [ModelType.CHAT, ModelType.THINK],      # 优先聊天模型，备选思考模型
        IAOPTaskType.PLACEHOLDER_ANALYSIS: [ModelType.THINK, ModelType.CHAT], # 优先思考模型
        IAOPTaskType.CONTEXT_UNDERSTANDING: [ModelType.THINK, ModelType.CHAT], # 优先思考模型
        IAOPTaskType.IMAGE_ANALYSIS: [ModelType.IMAGE],                      # 只能用图像模型
        IAOPTaskType.DOCUMENT_EMBEDDING: [ModelType.EMBED],                  # 只能用嵌入模型
    }
    
    # 模型类型的基础适用性评分
    MODEL_TYPE_SCORES = {
        ModelType.CHAT: {
            "conversation": 1.0,
            "text_generation": 1.0,
            "reasoning": 0.7,
            "structured_output": 0.8
        },
        ModelType.THINK: {
            "conversation": 0.8,
            "text_generation": 0.9,
            "reasoning": 1.0,
            "structured_output": 1.0
        },
        ModelType.IMAGE: {
            "conversation": 0.0,
            "text_generation": 0.0,
            "reasoning": 0.0,
            "structured_output": 0.0,
            "image_processing": 1.0
        },
        ModelType.EMBED: {
            "conversation": 0.0,
            "text_generation": 0.0,
            "reasoning": 0.0,
            "structured_output": 0.0,
            "embedding": 1.0
        }
    }
    
    # 任务对能力的需求权重
    TASK_CAPABILITY_REQUIREMENTS = {
        IAOPTaskType.SQL_GENERATION: {
            "reasoning": 0.9,           # 高推理需求
            "structured_output": 0.9,   # 高结构化输出需求
            "text_generation": 0.7
        },
        IAOPTaskType.BUSINESS_ANALYSIS: {
            "reasoning": 1.0,           # 最高推理需求
            "text_generation": 0.8,
            "conversation": 0.6
        },
        IAOPTaskType.DATA_INTERPRETATION: {
            "reasoning": 0.9,
            "structured_output": 0.8,
            "text_generation": 0.7
        },
        IAOPTaskType.REPORT_WRITING: {
            "text_generation": 1.0,    # 最高文本生成需求
            "conversation": 0.8,
            "reasoning": 0.6
        },
        IAOPTaskType.PLACEHOLDER_ANALYSIS: {
            "reasoning": 0.9,
            "structured_output": 0.9,
            "text_generation": 0.6
        },
        IAOPTaskType.CONTEXT_UNDERSTANDING: {
            "reasoning": 1.0,
            "conversation": 0.7,
            "text_generation": 0.5
        },
        IAOPTaskType.IMAGE_ANALYSIS: {
            "image_processing": 1.0
        },
        IAOPTaskType.DOCUMENT_EMBEDDING: {
            "embedding": 1.0
        }
    }


class IntelligentModelSelector:
    """智能模型选择器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def select_optimal_model(
        self, 
        user_id: str, 
        task_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[LLMModel], Dict[str, Any]]:
        """
        为特定任务选择最优模型
        
        Args:
            user_id: 用户ID
            task_type: 任务类型
            context: 任务上下文信息
            
        Returns:
            (选中的模型, 选择详情)
        """
        
        logger.info(f"为用户 {user_id} 选择最优模型，任务类型: {task_type}")
        
        # 1. 获取用户偏好
        user_preference = crud_user_llm_preference.get_or_create(
            self.db, user_id=user_id
        )
        
        # 2. 获取可用的健康模型
        available_models = self._get_available_models(user_preference)
        
        if not available_models:
            logger.warning(f"用户 {user_id} 没有可用的健康模型")
            return None, {"error": "没有可用的健康模型"}
        
        # 3. 检查用户特定偏好
        specific_model = self._check_user_specific_preference(
            user_preference, task_type
        )
        if specific_model and specific_model in available_models:
            logger.info(f"使用用户特定偏好模型: {specific_model.name}")
            return specific_model, {
                "selection_reason": "user_specific_preference",
                "model_name": specific_model.name,
                "task_type": task_type
            }
        
        # 4. 基于任务类型和模型能力进行智能选择
        scored_models = self._score_models_for_task(
            available_models, task_type, context
        )
        
        if not scored_models:
            # 如果没有评分模型，使用默认模型
            default_model = self._get_default_model(user_preference, available_models)
            if default_model:
                return default_model, {
                    "selection_reason": "fallback_to_default",
                    "model_name": default_model.name,
                    "task_type": task_type
                }
            return None, {"error": "无法确定合适的模型"}
        
        # 5. 选择得分最高的模型
        best_model, score, details = scored_models[0]
        
        logger.info(f"选择最优模型: {best_model.name}，得分: {score:.3f}")
        
        return best_model, {
            "selection_reason": "intelligent_scoring",
            "model_name": best_model.name,
            "task_type": task_type,
            "score": score,
            "scoring_details": details,
            "available_models_count": len(available_models)
        }
    
    def _get_available_models(self, user_preference: UserLLMPreference) -> List[LLMModel]:
        """获取用户可用的健康模型"""
        
        # 如果用户设置了默认服务器，优先使用该服务器的模型
        if user_preference.default_llm_server_id:
            server_models = crud_llm_model.get_models_by_filter(
                self.db,
                server_id=user_preference.default_llm_server_id,
                is_active=True,
                is_healthy=True
            )
            if server_models:
                logger.info(f"使用用户默认服务器 {user_preference.default_llm_server_id} 的模型")
                return server_models
        
        # 如果用户设置了提供商偏好，按优先级获取模型
        if user_preference.provider_priorities:
            sorted_providers = sorted(
                user_preference.provider_priorities.items(),
                key=lambda x: x[1]  # 按优先级数字排序
            )
            
            for provider_name, _ in sorted_providers:
                provider_models = crud_llm_model.get_models_by_filter(
                    self.db,
                    provider_name=provider_name,
                    is_active=True,
                    is_healthy=True
                )
                if provider_models:
                    logger.info(f"使用优先级提供商 {provider_name} 的模型")
                    return provider_models
        
        # 获取所有健康的模型
        all_healthy_models = crud_llm_model.get_healthy_models(self.db)
        logger.info(f"使用所有可用的健康模型，数量: {len(all_healthy_models)}")
        return all_healthy_models
    
    def _check_user_specific_preference(
        self, 
        user_preference: UserLLMPreference, 
        task_type: str
    ) -> Optional[LLMModel]:
        """检查用户是否为特定任务类型设置了偏好模型"""
        
        if not user_preference.model_preferences:
            return None
        
        preferred_model_name = user_preference.model_preferences.get(task_type)
        if not preferred_model_name:
            return None
        
        # 查找指定的模型
        models = crud_llm_model.get_models_by_filter(
            self.db,
            is_active=True,
            is_healthy=True
        )
        
        for model in models:
            if model.name == preferred_model_name:
                return model
        
        logger.warning(f"用户偏好的模型 {preferred_model_name} 未找到或不健康")
        return None
    
    def _score_models_for_task(
        self, 
        models: List[LLMModel], 
        task_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[LLMModel, float, Dict[str, Any]]]:
        """为任务类型对模型进行评分"""
        
        # 1. 获取任务类型对应的优先模型类型
        preferred_model_types = ModelTypeMapping.TASK_TO_MODEL_TYPE.get(task_type, [ModelType.CHAT])
        
        # 2. 获取任务能力需求
        capability_requirements = ModelTypeMapping.TASK_CAPABILITY_REQUIREMENTS.get(task_type, {})
        
        if not capability_requirements:
            logger.warning(f"未知任务类型: {task_type}，使用默认评分")
            capability_requirements = ModelTypeMapping.TASK_CAPABILITY_REQUIREMENTS[IAOPTaskType.SQL_GENERATION]
        
        scored_models = []
        
        for model in models:
            score, details = self._calculate_model_type_score(
                model, preferred_model_types, capability_requirements, context
            )
            scored_models.append((model, score, details))
        
        # 按得分降序排序
        scored_models.sort(key=lambda x: x[1], reverse=True)
        
        return scored_models
    
    def _calculate_model_type_score(
        self, 
        model: LLMModel, 
        preferred_model_types: List[ModelType],
        capability_requirements: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """基于模型类型匹配计算模型适合度得分"""
        
        score = 0.0
        details = {}
        
        # 1. 模型类型匹配度评分（最重要的因素）
        model_type_score = self._calculate_type_match_score(model, preferred_model_types)
        score += model_type_score * 10.0  # 高权重
        details["model_type_match"] = {
            "model_type": str(model.model_type),
            "preferred_types": [str(t) for t in preferred_model_types],
            "match_score": model_type_score,
            "weighted_score": model_type_score * 10.0
        }
        
        # 2. 能力匹配度评分
        capability_score = self._calculate_capability_score(model, capability_requirements)
        score += capability_score * 5.0  # 中等权重
        details["capability_match"] = {
            "capability_score": capability_score,
            "weighted_score": capability_score * 5.0
        }
        
        # 3. 用户优先级权重（如果该模型在用户偏好中）
        priority_score = 1.0 / (model.priority + 1)  # 优先级越小得分越高
        score += priority_score * 1.0
        details["priority"] = {
            "model_priority": model.priority,
            "score": priority_score * 1.0
        }
        
        # 4. 健康状态加成
        if model.is_healthy:
            score += 0.5
            details["health_bonus"] = 0.5
        
        # 5. 上下文相关调整（如果需要）
        if context:
            context_adjustment = self._apply_model_type_context_adjustments(model, context)
            score += context_adjustment
            if context_adjustment != 0:
                details["context_adjustment"] = context_adjustment
        
        details["final_score"] = score
        
        return score, details
    
    def _calculate_type_match_score(self, model: LLMModel, preferred_model_types: List[ModelType]) -> float:
        """计算模型类型匹配度得分"""
        
        if not preferred_model_types:
            return 0.5  # 无偏好时给中等分
        
        for i, preferred_type in enumerate(preferred_model_types):
            if model.model_type == preferred_type:
                # 按优先级给分：第一优先级得满分，第二优先级得0.8分，以此类推
                return max(1.0 - (i * 0.2), 0.2)
        
        return 0.1  # 不匹配优先类型的得最低分
    
    def _calculate_capability_score(self, model: LLMModel, capability_requirements: Dict[str, float]) -> float:
        """计算模型能力匹配度得分"""
        
        if not capability_requirements:
            return 0.5  # 无要求时给中等分
        
        model_capabilities = ModelTypeMapping.MODEL_TYPE_SCORES.get(model.model_type, {})
        
        total_score = 0.0
        total_weight = 0.0
        
        for capability, requirement_weight in capability_requirements.items():
            capability_score = model_capabilities.get(capability, 0.0)
            total_score += capability_score * requirement_weight
            total_weight += requirement_weight
        
        # 加权平均
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _apply_model_type_context_adjustments(
        self, 
        model: LLMModel, 
        context: Dict[str, Any]
    ) -> float:
        """根据任务上下文调整模型得分"""
        
        adjustment = 0.0
        
        # 如果任务需要高精度推理，think模型得到加分
        if context.get("accuracy_requirement") == "high":
            if model.model_type == ModelType.THINK:
                adjustment += 0.5
        
        # 如果任务需要结构化输出，think模型和支持函数调用的模型得到加分
        if context.get("requires_structured_output"):
            if model.model_type == ModelType.THINK:
                adjustment += 0.3
            if model.supports_function_calls:
                adjustment += 0.2
        
        # 如果任务涉及图像，只有image模型能处理
        if context.get("has_image_content"):
            if model.model_type == ModelType.IMAGE:
                adjustment += 1.0
            else:
                adjustment -= 5.0  # 其他模型重度扣分
        
        # 如果任务需要嵌入向量，只有embed模型能处理  
        if context.get("needs_embedding"):
            if model.model_type == ModelType.EMBED:
                adjustment += 1.0
            else:
                adjustment -= 5.0  # 其他模型重度扣分
        
        # 如果任务需要对话能力，chat模型得到轻微加分
        if context.get("conversational"):
            if model.model_type == ModelType.CHAT:
                adjustment += 0.2
        
        return adjustment
    
    def _get_default_model(
        self, 
        user_preference: UserLLMPreference, 
        available_models: List[LLMModel]
    ) -> Optional[LLMModel]:
        """获取默认模型"""
        
        # 1. 检查用户设置的默认模型
        if user_preference.default_model_name:
            for model in available_models:
                if model.name == user_preference.default_model_name:
                    return model
        
        # 2. 按优先级选择第一个模型
        if available_models:
            sorted_models = sorted(available_models, key=lambda x: x.priority)
            return sorted_models[0]
        
        return None
    
    def get_model_recommendations(
        self, 
        user_id: str, 
        task_types: List[str] = None
    ) -> Dict[str, Any]:
        """获取用户的模型推荐"""
        
        if not task_types:
            task_types = list(ModelTypeMapping.TASK_CAPABILITY_REQUIREMENTS.keys())
        
        user_preference = crud_user_llm_preference.get_or_create(
            self.db, user_id=user_id
        )
        
        available_models = self._get_available_models(user_preference)
        
        recommendations = {}
        
        for task_type in task_types:
            model, details = self.select_optimal_model(user_id, task_type)
            recommendations[task_type] = {
                "recommended_model": model.name if model else None,
                "model_id": model.id if model else None,
                "selection_details": details
            }
        
        return {
            "user_id": user_id,
            "available_models_count": len(available_models),
            "recommendations": recommendations,
            "timestamp": str(datetime.utcnow())
        }