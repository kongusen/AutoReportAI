"""
数据库驱动的智能模型选择器

核心理念：
1. 从数据库加载用户配置的LLM服务器和模型
2. 根据用户偏好和配额限制进行智能选择
3. 支持用户级别的个性化配置和学习
4. 与现有的LLM服务器管理API完全集成
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.llm_server import LLMServer, LLMModel
from app.models.user_llm_preference import UserLLMPreference, UserLLMUsageQuota
from app.crud.crud_llm_server import crud_llm_server
from app.crud.crud_llm_model import crud_llm_model

from .intelligent_selector import (
    TaskType, TaskComplexity, TaskCharacteristics, SelectionCriteria,
    ModelCapabilities, ModelRecommendation
)

logger = logging.getLogger(__name__)


@dataclass
class UserModelContext:
    """用户模型上下文"""
    user_id: str
    user_preference: Optional[UserLLMPreference]
    usage_quota: Optional[UserLLMUsageQuota]
    available_servers: List[LLMServer]
    available_models: List[LLMModel]


class DatabaseIntelligentSelector:
    """数据库驱动的智能模型选择器"""
    
    def __init__(self):
        self.model_capabilities: Dict[str, ModelCapabilities] = {}
        self.usage_history = defaultdict(list)
        self.agent_preferences = defaultdict(dict)
        logger.info("数据库智能模型选择器初始化完成")
    
    def _get_user_context(self, db: Session, user_id: str) -> UserModelContext:
        """获取用户上下文信息"""
        try:
            # 获取用户偏好
            from app.crud.crud_user import crud_user
            user = crud_user.get_by_id(db, id=user_id)
            if not user:
                raise ValueError(f"用户不存在: {user_id}")
            
            user_preference = db.query(UserLLMPreference).filter(
                UserLLMPreference.user_id == user_id
            ).first()
            
            # 获取用户当前配额
            current_period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            usage_quota = db.query(UserLLMUsageQuota).filter(
                UserLLMUsageQuota.user_id == user_id,
                UserLLMUsageQuota.period_start == current_period_start
            ).first()
            
            # 获取可用的LLM服务器(活跃且健康的)
            available_servers = crud_llm_server.get_multi_by_filter(
                db, is_active=True, is_healthy=True
            )
            
            # 获取可用的模型(活跃且健康的)
            available_models = []
            for server in available_servers:
                server_models = crud_llm_model.get_models_by_filter(
                    db, server_id=server.id, is_active=True, is_healthy=True
                )
                available_models.extend(server_models)
            
            return UserModelContext(
                user_id=user_id,
                user_preference=user_preference,
                usage_quota=usage_quota,
                available_servers=available_servers,
                available_models=available_models
            )
            
        except Exception as e:
            logger.error(f"获取用户上下文失败: {e}")
            raise
    
    def _build_model_capabilities_from_db(
        self, 
        models: List[LLMModel], 
        servers: List[LLMServer]
    ) -> Dict[str, ModelCapabilities]:
        """从数据库模型构建能力映射"""
        
        server_map = {server.id: server for server in servers}
        capabilities = {}
        
        for model in models:
            server = server_map.get(model.server_id)
            if not server:
                continue
            
            model_key = f"{server.name}:{model.name}"
            
            # 基于模型信息估算能力
            capability = self._estimate_model_capabilities_from_db(model, server)
            capabilities[model_key] = capability
        
        return capabilities
    
    def _estimate_model_capabilities_from_db(
        self, 
        model: LLMModel, 
        server: LLMServer
    ) -> ModelCapabilities:
        """从数据库模型估算能力"""
        
        capability = ModelCapabilities(
            model=model.name,
            provider=server.name,
            max_tokens=model.max_tokens or 4000,
            context_window=model.max_tokens or 8000,
            avg_latency_ms=server.timeout_seconds * 200,  # 估算延迟
        )
        
        # 基于模型名称进行启发式能力估计
        model_name_lower = model.name.lower()
        
        # GPT系列
        if "gpt-4" in model_name_lower:
            if "o" in model_name_lower or "turbo" in model_name_lower or "mini" in model_name_lower:
                capability.reasoning_score = 0.95
                capability.coding_score = 0.90
                capability.analysis_score = 0.90
                capability.cost_per_1k_tokens = 0.01
            else:
                capability.reasoning_score = 0.92
                capability.coding_score = 0.88
                capability.analysis_score = 0.88
                capability.cost_per_1k_tokens = 0.06
        elif "gpt-3.5" in model_name_lower:
            capability.reasoning_score = 0.75
            capability.coding_score = 0.70
            capability.analysis_score = 0.75
            capability.cost_per_1k_tokens = 0.002
        
        # Claude系列
        elif "claude" in model_name_lower:
            capability.supports_chinese = True
            if "opus" in model_name_lower or "4" in model_name_lower:
                capability.reasoning_score = 0.98
                capability.creative_score = 0.95
                capability.analysis_score = 0.95
                capability.cost_per_1k_tokens = 0.075
            elif "sonnet" in model_name_lower:
                capability.reasoning_score = 0.85
                capability.creative_score = 0.88
                capability.analysis_score = 0.88
                capability.cost_per_1k_tokens = 0.015
            elif "haiku" in model_name_lower:
                capability.reasoning_score = 0.75
                capability.creative_score = 0.80
                capability.cost_per_1k_tokens = 0.00025
                capability.avg_latency_ms = 1000
        
        # 编程专用模型
        elif "code" in model_name_lower:
            capability.coding_score = 0.90
            capability.reasoning_score = 0.75
        
        # 根据数据库中的provider_type进行调整
        if server.provider_type == "custom":
            capability.cost_per_1k_tokens = 0.001  # 自定义服务通常成本更低
        
        # 支持功能调用
        if model.supports_function_calls:
            capability.supports_function_calling = True
        
        # 思考模型
        if model.supports_thinking:
            capability.reasoning_score *= 1.2  # 思考模型推理能力更强
        
        return capability
    
    async def select_best_model_for_user(
        self,
        user_id: str,
        task_characteristics: TaskCharacteristics,
        criteria: Optional[SelectionCriteria] = None,
        agent_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> ModelRecommendation:
        """为用户选择最佳模型"""
        
        if db is None:
            db = SessionLocal()
            should_close_db = True
        else:
            should_close_db = False
        
        try:
            # 1. 获取用户上下文
            user_context = self._get_user_context(db, user_id)
            
            if not user_context.available_models:
                raise ValueError("用户没有可用的模型")
            
            # 2. 构建模型能力映射
            self.model_capabilities = self._build_model_capabilities_from_db(
                user_context.available_models,
                user_context.available_servers
            )
            
            # 3. 应用用户偏好和配额约束
            effective_criteria = self._apply_user_constraints(
                criteria or SelectionCriteria(),
                user_context
            )
            
            # 4. 过滤可用模型
            available_models = self._filter_models_by_user_context(
                self.model_capabilities, 
                user_context, 
                effective_criteria
            )
            
            if not available_models:
                raise ValueError("没有符合用户约束的可用模型")
            
            # 5. 计算模型分数并选择最佳
            model_scores = []
            for model_key, capabilities in available_models.items():
                score = self._calculate_model_score(
                    task_characteristics,
                    capabilities,
                    effective_criteria,
                    agent_id,
                    user_context
                )
                model_scores.append((model_key, capabilities, score))
            
            # 6. 排序并选择最佳模型
            model_scores.sort(key=lambda x: x[2], reverse=True)
            best_model_key, best_capabilities, best_score = model_scores[0]
            
            # 7. 生成推荐结果
            recommendation = self._generate_recommendation(
                best_capabilities,
                best_score,
                task_characteristics,
                model_scores[1:4],  # 备选方案
                user_context
            )
            
            # 8. 记录选择历史
            self._record_user_selection(user_id, agent_id, task_characteristics, recommendation)
            
            return recommendation
            
        finally:
            if should_close_db:
                db.close()
    
    def _apply_user_constraints(
        self,
        criteria: SelectionCriteria,
        user_context: UserModelContext
    ) -> SelectionCriteria:
        """应用用户偏好和配额约束"""
        
        # 基于用户偏好调整选择标准
        if user_context.user_preference:
            pref = user_context.user_preference
            
            # 应用成本限制
            if pref.monthly_cost_limit and user_context.usage_quota:
                remaining_budget = pref.monthly_cost_limit - user_context.usage_quota.total_cost
                if remaining_budget > 0:
                    if not criteria.max_cost_per_request:
                        criteria.max_cost_per_request = remaining_budget / 100  # 保守估计
                    else:
                        criteria.max_cost_per_request = min(
                            criteria.max_cost_per_request, 
                            remaining_budget / 100
                        )
            
            # 应用Token限制
            if pref.max_tokens_limit:
                # 这里可以基于Token限制调整请求大小
                pass
            
            # 应用提供商偏好
            if pref.provider_priorities:
                sorted_providers = sorted(
                    pref.provider_priorities.items(), 
                    key=lambda x: x[1]
                )
                preferred_providers = [p[0] for p in sorted_providers[:3]]
                if not criteria.preferred_providers:
                    criteria.preferred_providers = preferred_providers
        
        return criteria
    
    def _filter_models_by_user_context(
        self,
        model_capabilities: Dict[str, ModelCapabilities],
        user_context: UserModelContext,
        criteria: SelectionCriteria
    ) -> Dict[str, ModelCapabilities]:
        """根据用户上下文过滤模型"""
        
        filtered = {}
        available_server_names = {server.name for server in user_context.available_servers}
        
        for model_key, capability in model_capabilities.items():
            provider_name = capability.provider
            
            # 检查服务器是否可用
            if provider_name not in available_server_names:
                continue
            
            # 应用其他过滤条件
            if criteria.max_cost_per_request:
                estimated_cost = capability.cost_per_1k_tokens * 1  # 估算1K tokens
                if estimated_cost > criteria.max_cost_per_request:
                    continue
            
            if criteria.max_latency_ms:
                if capability.avg_latency_ms > criteria.max_latency_ms:
                    continue
            
            if criteria.preferred_providers:
                if capability.provider not in criteria.preferred_providers:
                    continue
            
            if criteria.excluded_models:
                if capability.model in criteria.excluded_models:
                    continue
            
            filtered[model_key] = capability
        
        return filtered
    
    def _calculate_model_score(
        self,
        task: TaskCharacteristics,
        capabilities: ModelCapabilities,
        criteria: SelectionCriteria,
        agent_id: Optional[str],
        user_context: UserModelContext
    ) -> float:
        """计算模型适配分数，包含用户偏好"""
        
        # 基础能力分数
        task_capability_map = {
            TaskType.REASONING: capabilities.reasoning_score,
            TaskType.CODING: capabilities.coding_score,
            TaskType.CREATIVE: capabilities.creative_score,
            TaskType.ANALYSIS: capabilities.analysis_score,
            TaskType.TRANSLATION: capabilities.translation_score,
            TaskType.QA: capabilities.qa_score,
            TaskType.SUMMARIZATION: capabilities.summarization_score,
            TaskType.GENERAL: (capabilities.reasoning_score + capabilities.analysis_score) / 2
        }
        
        capability_score = task_capability_map.get(task.task_type, 0.7)
        
        # 复杂度匹配
        complexity_score = self._get_complexity_score(task.complexity, capabilities)
        
        # 成本分数
        cost_score = self._get_cost_score(task, capabilities, criteria)
        
        # 速度分数
        speed_score = self._get_speed_score(task, capabilities)
        
        # 用户偏好分数
        user_preference_score = self._get_user_preference_score(
            capabilities, user_context
        )
        
        # Agent偏好分数
        agent_preference_score = self._get_agent_preference_score(agent_id, capabilities)
        
        # 历史性能分数
        history_score = self._get_history_score(capabilities, task.task_type)
        
        # 综合评分
        total_score = (
            capability_score * 0.25 +
            complexity_score * 0.15 +
            cost_score * 0.15 +
            speed_score * 0.10 +
            user_preference_score * 0.15 +
            agent_preference_score * 0.10 +
            history_score * 0.10
        )
        
        return total_score
    
    def _get_complexity_score(self, complexity: TaskComplexity, capabilities: ModelCapabilities) -> float:
        """复杂度匹配分数"""
        if complexity == TaskComplexity.EXPERT:
            return 1.0 if capabilities.reasoning_score > 0.90 else 0.5
        elif complexity == TaskComplexity.COMPLEX:
            return 1.0 if capabilities.reasoning_score > 0.80 else 0.7
        elif complexity == TaskComplexity.MEDIUM:
            return 1.0 if 0.70 <= capabilities.reasoning_score <= 0.90 else 0.8
        else:  # SIMPLE
            return 1.0 if capabilities.cost_per_1k_tokens < 0.01 else 0.7
    
    def _get_cost_score(
        self, 
        task: TaskCharacteristics, 
        capabilities: ModelCapabilities, 
        criteria: SelectionCriteria
    ) -> float:
        """成本效益分数"""
        if task.cost_sensitive:
            if capabilities.cost_per_1k_tokens == 0.0:
                return 1.0
            elif capabilities.cost_per_1k_tokens < 0.005:
                return 0.9
            elif capabilities.cost_per_1k_tokens < 0.02:
                return 0.7
            else:
                return 0.3
        else:
            return max(0.3, 1.0 - capabilities.cost_per_1k_tokens * 10)
    
    def _get_speed_score(self, task: TaskCharacteristics, capabilities: ModelCapabilities) -> float:
        """速度分数"""
        if task.speed_priority:
            if capabilities.avg_latency_ms < 1500:
                return 1.0
            elif capabilities.avg_latency_ms < 3000:
                return 0.8
            else:
                return 0.4
        else:
            return max(0.5, 1.0 - capabilities.avg_latency_ms / 10000)
    
    def _get_user_preference_score(
        self, 
        capabilities: ModelCapabilities, 
        user_context: UserModelContext
    ) -> float:
        """用户偏好分数"""
        if not user_context.user_preference:
            return 0.8
        
        pref = user_context.user_preference
        score = 0.8
        
        # 检查提供商优先级
        if pref.provider_priorities:
            provider_priority = pref.provider_priorities.get(capabilities.provider)
            if provider_priority:
                # 优先级越小分数越高
                max_priority = max(pref.provider_priorities.values())
                score += 0.2 * (max_priority - provider_priority) / max_priority
        
        # 检查模型偏好映射
        if pref.model_preferences:
            task_type_key = "general"  # 简化处理
            preferred_model = pref.model_preferences.get(task_type_key)
            if preferred_model == capabilities.model:
                score += 0.1
        
        return min(1.0, score)
    
    def _get_agent_preference_score(
        self, 
        agent_id: Optional[str], 
        capabilities: ModelCapabilities
    ) -> float:
        """Agent偏好分数"""
        if not agent_id:
            return 0.8
        
        preferences = self.agent_preferences.get(agent_id, {})
        model_key = f"{capabilities.provider}:{capabilities.model}"
        
        if model_key in preferences:
            pref_data = preferences[model_key]
            usage_count = pref_data.get('usage_count', 0)
            avg_satisfaction = pref_data.get('avg_satisfaction', 0.8)
            
            frequency_bonus = min(0.2, usage_count * 0.01)
            return avg_satisfaction + frequency_bonus
        
        return 0.8
    
    def _get_history_score(self, capabilities: ModelCapabilities, task_type: TaskType) -> float:
        """历史性能分数"""
        model_key = f"{capabilities.provider}:{capabilities.model}"
        
        if model_key not in self.usage_history:
            return 0.8
        
        relevant_history = [
            h for h in self.usage_history[model_key] 
            if h.get('task_type') == task_type.value
        ]
        
        if not relevant_history:
            return 0.8
        
        success_rate = sum(h.get('success', 0) for h in relevant_history) / len(relevant_history)
        avg_satisfaction = sum(h.get('satisfaction', 0.8) for h in relevant_history) / len(relevant_history)
        
        return (success_rate + avg_satisfaction) / 2
    
    def _generate_recommendation(
        self,
        capabilities: ModelCapabilities,
        score: float,
        task: TaskCharacteristics,
        alternatives: List[Tuple[str, ModelCapabilities, float]],
        user_context: UserModelContext
    ) -> ModelRecommendation:
        """生成推荐结果"""
        
        reasoning_parts = []
        
        # 能力匹配
        task_score = getattr(capabilities, f"{task.task_type.value}_score", 0.7)
        if task_score > 0.85:
            reasoning_parts.append(f"在{task.task_type.value}任务上表现优秀({task_score:.1%})")
        
        # 用户偏好匹配
        if user_context.user_preference:
            if capabilities.provider in user_context.user_preference.provider_priorities:
                reasoning_parts.append("符合用户提供商偏好")
        
        # 成本优势
        if capabilities.cost_per_1k_tokens < 0.01:
            reasoning_parts.append("成本效益优秀")
        
        # 速度优势
        if capabilities.avg_latency_ms < 2000:
            reasoning_parts.append("响应速度快")
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "综合评估最佳选择"
        
        estimated_cost = capabilities.cost_per_1k_tokens * (task.estimated_tokens / 1000)
        
        fallback_models = [
            (cap.model, cap.provider) 
            for _, cap, _ in alternatives
        ]
        
        return ModelRecommendation(
            model=capabilities.model,
            provider=capabilities.provider,
            confidence=min(0.95, score),
            reasoning=reasoning,
            expected_cost=estimated_cost,
            expected_latency=capabilities.avg_latency_ms,
            capability_match_score=score,
            fallback_models=fallback_models
        )
    
    def _record_user_selection(
        self,
        user_id: str,
        agent_id: Optional[str],
        task: TaskCharacteristics,
        recommendation: ModelRecommendation
    ):
        """记录用户选择历史"""
        selection_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "agent_id": agent_id,
            "task_type": task.task_type.value,
            "complexity": task.complexity.value,
            "model": recommendation.model,
            "provider": recommendation.provider,
            "confidence": recommendation.confidence,
            "expected_cost": recommendation.expected_cost
        }
        
        model_key = f"{recommendation.provider}:{recommendation.model}"
        self.usage_history[model_key].append(selection_record)
        
        if len(self.usage_history[model_key]) > 100:
            self.usage_history[model_key] = self.usage_history[model_key][-100:]
        
        logger.info(f"记录用户 {user_id} 的模型选择: {model_key}")
    
    def record_user_feedback(
        self,
        user_id: str,
        model: str,
        provider: str,
        success: bool,
        satisfaction_score: float,
        actual_cost: Optional[float] = None,
        actual_latency: Optional[int] = None,
        agent_id: Optional[str] = None,
        task_type: Optional[TaskType] = None
    ):
        """记录用户使用反馈"""
        
        model_key = f"{provider}:{model}"
        
        feedback_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "success": success,
            "satisfaction": satisfaction_score,
            "actual_cost": actual_cost,
            "actual_latency": actual_latency,
            "agent_id": agent_id,
            "task_type": task_type.value if task_type else None
        }
        
        self.usage_history[model_key].append(feedback_record)
        
        # 更新Agent偏好
        if agent_id:
            if agent_id not in self.agent_preferences:
                self.agent_preferences[agent_id] = {}
            
            if model_key not in self.agent_preferences[agent_id]:
                self.agent_preferences[agent_id][model_key] = {
                    'usage_count': 0,
                    'satisfaction_sum': 0,
                    'avg_satisfaction': 0.8
                }
            
            pref = self.agent_preferences[agent_id][model_key]
            pref['usage_count'] += 1
            pref['satisfaction_sum'] += satisfaction_score
            pref['avg_satisfaction'] = pref['satisfaction_sum'] / pref['usage_count']
        
        logger.info(f"记录用户 {user_id} 对模型 {model_key} 的反馈: 成功={success}, 满意度={satisfaction_score}")


# 全局数据库选择器实例
_database_selector: Optional[DatabaseIntelligentSelector] = None

def get_database_selector() -> DatabaseIntelligentSelector:
    """获取数据库智能选择器实例"""
    global _database_selector
    if _database_selector is None:
        _database_selector = DatabaseIntelligentSelector()
    return _database_selector