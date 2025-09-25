"""
生产级配置提供器
基于真实数据库的用户LLM偏好和系统配置
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from .config_context import AgentSystemConfig
from app.crud.crud_user_llm_preference import crud_user_llm_preference
from app.db.session import SessionLocal


logger = logging.getLogger(__name__)


class ProductionConfigProvider:
    """生产级配置提供器"""

    def __init__(self):
        """初始化配置提供器"""
        self.logger = logging.getLogger(self.__class__.__name__)

        # 系统默认配置
        self.default_config = AgentSystemConfig(
            # LLM默认配置
            default_model="gpt-4o-mini",
            model_fallback_chain=["gpt-4o-mini", "gpt-3.5-turbo"],
            max_retries=3,
            timeout_seconds=120,

            # 数据源默认配置
            query_timeout=30,
            max_result_rows=10000,

            # Agent行为默认配置
            enable_sql_validation=True,
            enable_policy_check=True,
            enable_quality_check=True,

            # 调试和监控默认配置
            debug_mode=False,
            enable_metrics=True,
            log_level="INFO"
        )

    def get_user_config(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户特定配置

        Args:
            user_id: 用户UUID

        Returns:
            用户配置字典
        """
        db: Session = SessionLocal()
        try:
            # 获取用户LLM偏好
            preference = crud_user_llm_preference.get_by_user_id(db, user_id)

            if not preference:
                # 用户没有偏好设置，返回默认配置
                return self._config_to_dict(self.default_config)

            # 构建用户特定配置
            user_config = self._build_user_config(preference)

            # 与默认配置合并
            merged_config = self._merge_with_defaults(user_config)

            return merged_config

        except Exception as e:
            self.logger.error(f"获取用户配置失败 (user_id: {user_id}): {e}")
            # 返回默认配置作为后备
            return self._config_to_dict(self.default_config)
        finally:
            db.close()

    def _build_user_config(self, preference) -> Dict[str, Any]:
        """
        从数据库偏好记录构建用户配置

        Args:
            preference: UserLLMPreference对象

        Returns:
            用户配置字典
        """
        config = {}

        # LLM模型配置
        if preference.default_model_name:
            config["default_model"] = preference.default_model_name

        # 温度和Token限制
        if preference.preferred_temperature is not None:
            config["temperature"] = preference.preferred_temperature

        if preference.max_tokens_limit:
            config["max_tokens"] = preference.max_tokens_limit

        # 配额配置
        if preference.daily_token_quota:
            config["daily_token_quota"] = preference.daily_token_quota

        if preference.monthly_cost_limit:
            config["monthly_cost_limit"] = preference.monthly_cost_limit

        # 高级设置
        config["enable_caching"] = preference.enable_caching
        if preference.cache_ttl_hours:
            config["cache_ttl_hours"] = preference.cache_ttl_hours

        config["enable_learning"] = preference.enable_learning

        # 提供商优先级
        if preference.provider_priorities:
            config["provider_priorities"] = preference.provider_priorities

        # 模型偏好映射
        if preference.model_preferences:
            config["model_preferences"] = preference.model_preferences

        # 自定义设置
        if preference.custom_settings:
            config["custom_settings"] = preference.custom_settings

            # 从自定义设置中提取Agent相关配置
            custom = preference.custom_settings

            # Agent行为配置
            if "enable_sql_validation" in custom:
                config["enable_sql_validation"] = custom["enable_sql_validation"]
            if "enable_policy_check" in custom:
                config["enable_policy_check"] = custom["enable_policy_check"]
            if "enable_quality_check" in custom:
                config["enable_quality_check"] = custom["enable_quality_check"]

            # 查询配置
            if "max_result_rows" in custom:
                config["max_result_rows"] = custom["max_result_rows"]
            if "query_timeout" in custom:
                config["query_timeout"] = custom["query_timeout"]

            # 调试配置
            if "debug_mode" in custom:
                config["debug_mode"] = custom["debug_mode"]
            if "log_level" in custom:
                config["log_level"] = custom["log_level"]

        return config

    def _merge_with_defaults(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        将用户配置与默认配置合并

        Args:
            user_config: 用户配置字典

        Returns:
            合并后的配置字典
        """
        # 从默认配置开始
        merged = self._config_to_dict(self.default_config)

        # 用户配置覆盖默认配置
        merged.update(user_config)

        return merged

    def _config_to_dict(self, config: AgentSystemConfig) -> Dict[str, Any]:
        """
        将AgentSystemConfig对象转换为字典

        Args:
            config: 配置对象

        Returns:
            配置字典
        """
        return {
            "default_model": config.default_model,
            "model_fallback_chain": config.model_fallback_chain,
            "max_retries": config.max_retries,
            "timeout_seconds": config.timeout_seconds,
            "default_data_source_id": config.default_data_source_id,
            "query_timeout": config.query_timeout,
            "max_result_rows": config.max_result_rows,
            "enable_sql_validation": config.enable_sql_validation,
            "enable_policy_check": config.enable_policy_check,
            "enable_quality_check": config.enable_quality_check,
            "debug_mode": config.debug_mode,
            "enable_metrics": config.enable_metrics,
            "log_level": config.log_level,
            "custom_settings": config.custom_settings
        }

    def get_agent_config(self, user_id: str) -> AgentSystemConfig:
        """
        获取用户的Agent系统配置对象

        Args:
            user_id: 用户UUID

        Returns:
            AgentSystemConfig配置对象
        """
        user_config_dict = self.get_user_config(user_id)

        return AgentSystemConfig(
            default_model=user_config_dict.get("default_model"),
            model_fallback_chain=user_config_dict.get("model_fallback_chain"),
            max_retries=user_config_dict.get("max_retries", 3),
            timeout_seconds=user_config_dict.get("timeout_seconds", 120),
            default_data_source_id=user_config_dict.get("default_data_source_id"),
            query_timeout=user_config_dict.get("query_timeout", 30),
            max_result_rows=user_config_dict.get("max_result_rows", 10000),
            enable_sql_validation=user_config_dict.get("enable_sql_validation", True),
            enable_policy_check=user_config_dict.get("enable_policy_check", True),
            enable_quality_check=user_config_dict.get("enable_quality_check", True),
            debug_mode=user_config_dict.get("debug_mode", False),
            enable_metrics=user_config_dict.get("enable_metrics", True),
            log_level=user_config_dict.get("log_level", "INFO"),
            custom_settings=user_config_dict.get("custom_settings", {})
        )

    def get_llm_policy_config(self, user_id: str, stage: str, complexity: str) -> Dict[str, Any]:
        """
        获取用户的LLM策略配置

        Args:
            user_id: 用户ID
            stage: Agent执行阶段 (plan/tool/finalize)
            complexity: 任务复杂度 (low/medium/high)

        Returns:
            LLM策略配置
        """
        user_config = self.get_user_config(user_id)

        # 基础策略配置
        policy_config = {
            "user_id": user_id,
            "stage": stage,
            "complexity": complexity,
        }

        # 根据用户偏好设置模型选择策略
        model_preferences = user_config.get("model_preferences", {})

        # 根据阶段和复杂度选择模型类型
        if stage in ["plan", "finalize"]:
            # 计划和最终决策阶段使用think模型（更可靠的JSON输出）
            policy_config["preferred_model_type"] = "think"
        elif complexity == "high":
            # 高复杂度任务使用think模型
            policy_config["preferred_model_type"] = "think"
        else:
            # 其他情况使用default模型
            policy_config["preferred_model_type"] = "default"

        # 用户特定模型偏好覆盖
        if f"{stage}_{complexity}" in model_preferences:
            policy_config["preferred_model"] = model_preferences[f"{stage}_{complexity}"]
        elif stage in model_preferences:
            policy_config["preferred_model"] = model_preferences[stage]

        # 添加其他策略参数
        policy_config.update({
            "temperature": user_config.get("temperature", 0.7),
            "max_tokens": user_config.get("max_tokens", 4000),
            "enable_caching": user_config.get("enable_caching", True),
            "timeout_seconds": user_config.get("timeout_seconds", 120),
        })

        return policy_config


# 创建全局实例
production_config_provider = ProductionConfigProvider()