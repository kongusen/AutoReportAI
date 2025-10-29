"""
用户模型配置解析器

基于数据库中的用户LLM配置动态确定Agent的max_context_tokens等参数
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from app.db.session import get_db_session
from app.models.user_llm_preference import UserLLMPreference
from app.models.llm_server import LLMModel, LLMServer
from app.core.intelligent_config import get_user_llm_config, get_optimal_llm_for_task

logger = logging.getLogger(__name__)


@dataclass
class UserModelConfig:
    """用户模型配置"""
    # 默认模型配置
    default_model: ModelConfig
    # 思考模型配置
    think_model: Optional[ModelConfig]
    # 用户偏好
    preferred_temperature: float
    max_tokens_limit: int
    # 模型选择策略
    auto_model_selection: bool = True
    think_model_threshold: float = 0.7  # 复杂度阈值，超过此值使用思考模型


@dataclass
class ModelConfig:
    """单个模型配置"""
    model_name: str
    provider: str
    max_tokens: int
    temperature: float
    supports_function_calls: bool
    supports_thinking: bool
    model_type: str  # "default" or "think"
    priority: int = 50


class UserModelResolver:
    """用户模型配置解析器"""
    
    def __init__(self):
        self._cache: Dict[str, UserModelConfig] = {}
        self._cache_ttl = 300  # 5分钟缓存
    
    async def resolve_user_model_config(
        self,
        user_id: str,
        task_type: str = "placeholder_analysis",
        force_refresh: bool = False
    ) -> UserModelConfig:
        """
        解析用户模型配置
        
        Args:
            user_id: 用户ID
            task_type: 任务类型 (placeholder_analysis, data_analysis, report_generation)
            force_refresh: 是否强制刷新缓存
            
        Returns:
            UserModelConfig: 用户模型配置
        """
        cache_key = f"{user_id}:{task_type}"
        
        # 检查缓存
        if not force_refresh and cache_key in self._cache:
            logger.debug(f"使用缓存的用户模型配置: {cache_key}")
            return self._cache[cache_key]
        
        try:
            # 1. 优先从数据库获取用户偏好配置
            db_config = await self._get_user_preference_config(user_id)
            
            # 2. 如果数据库配置存在，使用数据库配置
            if db_config:
                logger.info(f"使用数据库用户配置: {user_id}")
                self._cache[cache_key] = db_config
                return db_config
            
            # 3. 回退到智能配置管理器
            intelligent_config = await self._get_intelligent_config(user_id, task_type)
            if intelligent_config:
                logger.info(f"使用智能配置管理器: {user_id}")
                self._cache[cache_key] = intelligent_config
                return intelligent_config
            
            # 4. 使用默认配置
            default_config = self._get_default_config()
            logger.warning(f"使用默认配置: {user_id}")
            self._cache[cache_key] = default_config
            return default_config
            
        except Exception as e:
            logger.error(f"解析用户模型配置失败: {e}")
            return self._get_default_config()
    
    async def _get_user_preference_config(self, user_id: str) -> Optional[UserModelConfig]:
        """从数据库获取用户偏好配置"""
        try:
            with get_db_session() as db:
                # 获取用户LLM偏好
                user_pref = db.query(UserLLMPreference).filter(
                    UserLLMPreference.user_id == user_id
                ).first()
                
                if not user_pref:
                    logger.info(f"用户 {user_id} 没有LLM偏好配置，查询可用模型")
                    # 即使没有用户偏好配置，也查询用户可用的模型
                
                # 使用与PureDatabaseLLMManager相同的查询逻辑
                # 查询用户专属的健康模型（只要求模型健康，不要求服务器健康）
                user_models = db.query(LLMModel).join(LLMServer).filter(
                    LLMModel.is_active == True,
                    LLMModel.is_healthy == True,
                    LLMModel.server.has(is_active=True, user_id=user_id)
                ).order_by(LLMModel.priority.asc()).all()
                
                if not user_models:
                    logger.warning(f"用户 {user_id} 没有专属的健康模型，查询全局模型")
                    # 回退到全局健康模型（只要求模型健康，不要求服务器健康）
                    user_models = db.query(LLMModel).join(LLMServer).filter(
                        LLMModel.is_active == True,
                        LLMModel.is_healthy == True,
                        LLMModel.server.has(is_active=True)
                    ).order_by(LLMModel.priority.asc()).all()
                
                if not user_models:
                    logger.error(f"用户 {user_id} 没有任何可用的健康模型")
                    return None
                
                logger.info(f"用户 {user_id} 找到 {len(user_models)} 个可用模型: {[m.name for m in user_models]}")
                
                # 选择默认模型和思考模型
                default_model = None
                think_model = None
                
                # 优先使用用户指定的默认模型（如果有用户偏好配置）
                if user_pref and user_pref.default_model_name:
                    default_model = next((m for m in user_models if m.name == user_pref.default_model_name), None)
                
                # 如果没有找到指定的默认模型，使用第一个default类型的模型
                if not default_model:
                    default_model = next((m for m in user_models if m.model_type == "default"), None)
                
                # 如果没有default类型的模型，使用第一个可用模型
                if not default_model:
                    default_model = user_models[0]
                
                # 查找思考模型
                think_model = next((m for m in user_models if m.model_type == "think"), None)
                
                # 构建模型配置
                default_model_config = None
                think_model_config = None
                
                if not default_model:
                    logger.error(f"用户 {user_id} 没有可用的默认模型")
                    raise ValueError(f"用户 {user_id} 没有可用的默认模型")
                
                # 使用用户偏好配置或默认值
                max_tokens = default_model.max_tokens or (user_pref.max_tokens_limit if user_pref else 4000)
                temperature = user_pref.preferred_temperature if user_pref else 0.7
                
                default_model_config = ModelConfig(
                    model_name=default_model.name,
                    provider=default_model.provider_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    supports_function_calls=default_model.supports_function_calls,
                    supports_thinking=default_model.supports_thinking,
                    model_type="default",
                    priority=default_model.priority
                )
                
                if think_model:
                    # 使用用户偏好配置或默认值
                    max_tokens = think_model.max_tokens or (user_pref.max_tokens_limit if user_pref else 4000)
                    temperature = user_pref.preferred_temperature if user_pref else 0.7
                    
                    think_model_config = ModelConfig(
                        model_name=think_model.name,
                        provider=think_model.provider_name,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        supports_function_calls=think_model.supports_function_calls,
                        supports_thinking=think_model.supports_thinking,
                        model_type="think",
                        priority=think_model.priority
                    )
                
                return UserModelConfig(
                    default_model=default_model_config,
                    think_model=think_model_config,
                    preferred_temperature=user_pref.preferred_temperature if user_pref else 0.7,
                    max_tokens_limit=user_pref.max_tokens_limit if user_pref else 4000,
                    auto_model_selection=True,
                    think_model_threshold=0.7
                )
                
        except Exception as e:
            logger.error(f"获取用户偏好配置失败: {e}")
            return None
    
    async def _get_intelligent_config(self, user_id: str, task_type: str) -> Optional[UserModelConfig]:
        """从智能配置管理器获取配置"""
        try:
            from app.core.intelligent_config import ModelCapability
            
            # 根据任务类型确定所需能力
            capabilities = []
            if task_type == "placeholder_analysis":
                capabilities = [ModelCapability.DATA_ANALYSIS, ModelCapability.CODE_GENERATION]
            elif task_type == "data_analysis":
                capabilities = [ModelCapability.DATA_ANALYSIS, ModelCapability.SUMMARIZATION]
            elif task_type == "report_generation":
                capabilities = [ModelCapability.TEXT_GENERATION, ModelCapability.SUMMARIZATION]
            
            # 获取默认模型
            default_model = get_optimal_llm_for_task(user_id, task_type, capabilities)
            
            # 获取思考模型（如果有的话）
            think_capabilities = capabilities + [ModelCapability.THINKING]
            think_model = get_optimal_llm_for_task(user_id, f"{task_type}_thinking", think_capabilities)
            
            if default_model:
                default_model_config = ModelConfig(
                    model_name=default_model.model_name,
                    provider=default_model.provider.value,
                    max_tokens=default_model.max_tokens,
                    temperature=default_model.temperature,
                    supports_function_calls=True,
                    supports_thinking=False,
                    model_type="default",
                    priority=50
                )
                
                think_model_config = None
                if think_model and think_model.model_name != default_model.model_name:
                    think_model_config = ModelConfig(
                        model_name=think_model.model_name,
                        provider=think_model.provider.value,
                        max_tokens=think_model.max_tokens,
                        temperature=think_model.temperature,
                        supports_function_calls=True,
                        supports_thinking=True,
                        model_type="think",
                        priority=40
                    )
                
                return UserModelConfig(
                    default_model=default_model_config,
                    think_model=think_model_config,
                    preferred_temperature=default_model.temperature,
                    max_tokens_limit=default_model.max_tokens,
                    auto_model_selection=True,
                    think_model_threshold=0.7
                )
            
            return None
            
        except Exception as e:
            logger.error(f"获取智能配置失败: {e}")
            return None
    
    def _calculate_context_tokens(self, max_tokens: int) -> int:
        """
        基于模型的max_tokens计算合适的context_tokens
        
        策略：
        - 如果max_tokens <= 4K: context_tokens = max_tokens * 0.8
        - 如果max_tokens <= 8K: context_tokens = max_tokens * 0.7  
        - 如果max_tokens <= 16K: context_tokens = max_tokens * 0.6
        - 如果max_tokens > 16K: context_tokens = max_tokens * 0.5
        
        但不超过32K，不低于4K
        """
        if max_tokens <= 4000:
            context_tokens = int(max_tokens * 0.8)
        elif max_tokens <= 8000:
            context_tokens = int(max_tokens * 0.7)
        elif max_tokens <= 16000:
            context_tokens = int(max_tokens * 0.6)
        else:
            context_tokens = int(max_tokens * 0.5)
        
        # 限制范围
        context_tokens = max(4000, min(32000, context_tokens))
        
        logger.debug(f"计算context_tokens: max_tokens={max_tokens} -> context_tokens={context_tokens}")
        return context_tokens
    
    def _get_default_config(self) -> UserModelConfig:
        """获取默认配置 - 从数据库查询可用的健康模型"""
        try:
            with get_db_session() as db:
                # 查询全局健康模型
                models = db.query(LLMModel).join(LLMServer).filter(
                    LLMModel.is_active == True,
                    LLMModel.is_healthy == True,
                    LLMModel.server.has(is_active=True)
                ).order_by(LLMModel.priority.asc()).all()
                
                if not models:
                    raise ValueError("没有可用的用户模型配置，请先在系统中配置LLM服务器和模型")
                
                logger.info(f"找到 {len(models)} 个全局健康模型: {[m.name for m in models]}")
                
                # 选择默认模型和思考模型
                default_model = next((m for m in models if m.model_type == "default"), None)
                think_model = next((m for m in models if m.model_type == "think"), None)
                
                # 如果没有default类型的模型，使用第一个可用模型
                if not default_model:
                    default_model = models[0]
                
                if not default_model:
                    raise ValueError("没有可用的默认模型")
                
                # 构建模型配置（补全必需字段）
                default_model_config = ModelConfig(
                    model_name=default_model.name,
                    provider=default_model.provider_name,
                    max_tokens=default_model.max_tokens or 4000,
                    temperature=default_model.temperature_default or 0.7,
                    supports_function_calls=getattr(default_model, 'supports_function_calls', True),
                    supports_thinking=getattr(default_model, 'supports_thinking', False),
                    model_type="default",
                    priority=default_model.priority
                )
                
                think_model_config = None
                if think_model:
                    think_model_config = ModelConfig(
                        model_name=think_model.name,
                        provider=think_model.provider_name,
                        max_tokens=think_model.max_tokens or 4000,
                        temperature=think_model.temperature_default or 0.7,
                        supports_function_calls=getattr(think_model, 'supports_function_calls', True),
                        supports_thinking=getattr(think_model, 'supports_thinking', True),
                        model_type="think",
                        priority=think_model.priority
                    )
                
                # 构建用户配置
                user_config = UserModelConfig(
                    default_model=default_model_config,
                    think_model=think_model_config,
                    preferred_temperature=0.7,
                    max_tokens_limit=4000,
                    auto_model_selection=True,
                    think_model_threshold=0.7
                )
                
                logger.info(f"默认配置构建成功: 默认模型={default_model_config.model_name}, 思考模型={think_model_config.model_name if think_model_config else 'None'}")
                return user_config
                
        except Exception as e:
            logger.error(f"获取默认配置失败: {e}")
            raise ValueError("没有可用的用户模型配置，请先在系统中配置LLM服务器和模型")
    
    def clear_cache(self, user_id: Optional[str] = None):
        """清除缓存"""
        if user_id:
            keys_to_remove = [key for key in self._cache.keys() if key.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()
        logger.info(f"清除用户模型配置缓存: {user_id or 'all'}")
    
    def select_model_for_task(
        self,
        user_config: UserModelConfig,
        task_complexity: float,
        task_type: str = "placeholder_analysis"
    ) -> ModelConfig:
        """
        根据任务复杂度和类型选择合适的模型
        
        Args:
            user_config: 用户模型配置
            task_complexity: 任务复杂度 (0.0-1.0)
            task_type: 任务类型
            
        Returns:
            ModelConfig: 选择的模型配置
        """
        # 如果用户禁用了自动模型选择，使用默认模型
        if not user_config.auto_model_selection:
            logger.info(f"用户禁用自动模型选择，使用默认模型: {user_config.default_model.model_name}")
            return user_config.default_model
        
        # 根据任务复杂度选择模型
        if task_complexity >= user_config.think_model_threshold:
            # 高复杂度任务，优先使用思考模型
            if user_config.think_model:
                logger.info(f"高复杂度任务({task_complexity:.2f})，使用思考模型: {user_config.think_model.model_name}")
                return user_config.think_model
            else:
                logger.info(f"高复杂度任务({task_complexity:.2f})，但无思考模型，使用默认模型: {user_config.default_model.model_name}")
                return user_config.default_model
        else:
            # 低复杂度任务，使用默认模型
            logger.info(f"低复杂度任务({task_complexity:.2f})，使用默认模型: {user_config.default_model.model_name}")
            return user_config.default_model
    
    def get_max_context_tokens(self, user_config: UserModelConfig, selected_model: ModelConfig) -> int:
        """获取最大上下文tokens"""
        return self._calculate_context_tokens(selected_model.max_tokens)


# 全局实例
user_model_resolver = UserModelResolver()


async def get_user_model_config(
    user_id: str,
    task_type: str = "placeholder_analysis"
) -> UserModelConfig:
    """
    获取用户模型配置的便捷函数
    
    Args:
        user_id: 用户ID
        task_type: 任务类型
        
    Returns:
        UserModelConfig: 用户模型配置
    """
    return await user_model_resolver.resolve_user_model_config(user_id, task_type)


def clear_user_model_cache(user_id: Optional[str] = None):
    """清除用户模型配置缓存的便捷函数"""
    user_model_resolver.clear_cache(user_id)
