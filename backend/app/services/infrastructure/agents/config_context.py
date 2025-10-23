"""配置上下文管理器（保留旧接口以供新运行时使用）。"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class AgentSystemConfig:
    default_model: Optional[str] = None
    model_fallback_chain: Optional[list] = None
    max_retries: int = 3
    timeout_seconds: int = 120

    default_data_source_id: Optional[str] = None
    query_timeout: int = 30
    max_result_rows: int = 10000

    enable_sql_validation: bool = True
    enable_policy_check: bool = True
    enable_quality_check: bool = True

    debug_mode: bool = False
    enable_metrics: bool = True
    log_level: str = "INFO"

    custom_settings: Dict[str, Any] = field(default_factory=dict)


class ConfigContextManager:
    def __init__(self) -> None:
        self._config: Optional[AgentSystemConfig] = None
        self._config_loader: Optional[Callable[[str], Dict[str, Any]]] = None

    def set_config(self, config: AgentSystemConfig) -> None:
        self._config = config

    def set_config_loader(self, loader: Callable[[str], Dict[str, Any]]) -> None:
        self._config_loader = loader

    def get_config(self, user_id: Optional[str] = None) -> AgentSystemConfig:
        if self._config_loader and user_id:
            try:
                data = self._config_loader(user_id)
                return self._create_config_from_dict(data)
            except Exception:
                pass
        return self._config or AgentSystemConfig()

    def get_setting(self, key: str, default: Any = None, user_id: Optional[str] = None) -> Any:
        config = self.get_config(user_id)
        return getattr(config, key, config.custom_settings.get(key, default))

    def _create_config_from_dict(self, data: Dict[str, Any]) -> AgentSystemConfig:
        return AgentSystemConfig(
            default_model=data.get("default_model"),
            model_fallback_chain=data.get("model_fallback_chain"),
            max_retries=data.get("max_retries", 3),
            timeout_seconds=data.get("timeout_seconds", 120),
            default_data_source_id=data.get("default_data_source_id"),
            query_timeout=data.get("query_timeout", 30),
            max_result_rows=data.get("max_result_rows", 10000),
            enable_sql_validation=data.get("enable_sql_validation", True),
            enable_policy_check=data.get("enable_policy_check", True),
            enable_quality_check=data.get("enable_quality_check", True),
            debug_mode=data.get("debug_mode", False),
            enable_metrics=data.get("enable_metrics", True),
            log_level=data.get("log_level", "INFO"),
            custom_settings=data.get("custom_settings", {}),
        )


config_manager = ConfigContextManager()


__all__ = [
    "AgentSystemConfig",
    "ConfigContextManager",
    "config_manager",
]
