"""
配置上下文管理器
用于Agent系统与外部配置系统集成
"""

from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field


@dataclass
class AgentSystemConfig:
    """Agent系统配置"""
    # LLM相关配置
    default_model: Optional[str] = None
    model_fallback_chain: Optional[list] = None
    max_retries: int = 3
    timeout_seconds: int = 120

    # 数据源配置
    default_data_source_id: Optional[str] = None
    query_timeout: int = 30
    max_result_rows: int = 10000

    # Agent行为配置
    enable_sql_validation: bool = True
    enable_policy_check: bool = True
    enable_quality_check: bool = True

    # 调试和监控
    debug_mode: bool = False
    enable_metrics: bool = True
    log_level: str = "INFO"

    # 自定义配置
    custom_settings: Dict[str, Any] = field(default_factory=dict)


class ConfigContextManager:
    """配置上下文管理器"""

    def __init__(self):
        self._config: Optional[AgentSystemConfig] = None
        self._config_loader: Optional[Callable[[str], Dict[str, Any]]] = None

    def set_config(self, config: AgentSystemConfig) -> None:
        """设置Agent系统配置"""
        self._config = config

    def set_config_loader(self, loader: Callable[[str], Dict[str, Any]]) -> None:
        """设置配置加载器函数

        Args:
            loader: 接受user_id参数，返回用户特定配置的函数
        """
        self._config_loader = loader

    def get_config(self, user_id: Optional[str] = None) -> AgentSystemConfig:
        """获取配置

        Args:
            user_id: 用户ID，用于获取用户特定配置

        Returns:
            Agent系统配置
        """
        # 如果有配置加载器，优先使用
        if self._config_loader and user_id:
            try:
                user_config_data = self._config_loader(user_id)
                return self._create_config_from_dict(user_config_data)
            except Exception:
                # 加载失败，使用默认配置
                pass

        # 返回设置的配置或默认配置
        return self._config or AgentSystemConfig()

    def _create_config_from_dict(self, config_data: Dict[str, Any]) -> AgentSystemConfig:
        """从字典创建配置对象"""
        return AgentSystemConfig(
            default_model=config_data.get('default_model'),
            model_fallback_chain=config_data.get('model_fallback_chain'),
            max_retries=config_data.get('max_retries', 3),
            timeout_seconds=config_data.get('timeout_seconds', 120),
            default_data_source_id=config_data.get('default_data_source_id'),
            query_timeout=config_data.get('query_timeout', 30),
            max_result_rows=config_data.get('max_result_rows', 10000),
            enable_sql_validation=config_data.get('enable_sql_validation', True),
            enable_policy_check=config_data.get('enable_policy_check', True),
            enable_quality_check=config_data.get('enable_quality_check', True),
            debug_mode=config_data.get('debug_mode', False),
            enable_metrics=config_data.get('enable_metrics', True),
            log_level=config_data.get('log_level', 'INFO'),
            custom_settings=config_data.get('custom_settings', {})
        )

    def get_setting(self, key: str, default: Any = None, user_id: Optional[str] = None) -> Any:
        """获取特定配置项"""
        config = self.get_config(user_id)
        return getattr(config, key, config.custom_settings.get(key, default))


# 全局配置上下文管理器实例
config_manager = ConfigContextManager()