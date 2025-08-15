"""
用户LLM配置管理
提供用户侧的LLM配置能力，支持多种AI服务配置
"""
import os
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field

from app.core.config import settings


class LLMProvider(str, Enum):
    """LLM提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE = "google"
    ZHIPU = "zhipu"
    BAICHUAN = "baichuan"
    QWEN = "qwen"
    LOCAL = "local"


class ModelCapability(str, Enum):
    """模型能力"""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    CHART_DESCRIPTION = "chart_description"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"


@dataclass
class LLMModelConfig:
    """LLM模型配置"""
    provider: LLMProvider
    model_name: str
    api_key: str
    api_base: Optional[str] = None
    
    # 模型参数
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # 速率限制
    requests_per_minute: int = 60
    tokens_per_minute: int = 40000
    
    # 能力支持
    capabilities: List[ModelCapability] = field(default_factory=list)
    
    # 成本配置（每1k tokens）
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    
    # 质量配置
    quality_score: float = 0.8  # 0-1之间
    reliability_score: float = 0.9  # 0-1之间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "requests_per_minute": self.requests_per_minute,
            "tokens_per_minute": self.tokens_per_minute,
            "capabilities": [cap.value for cap in self.capabilities],
            "input_cost_per_1k": self.input_cost_per_1k,
            "output_cost_per_1k": self.output_cost_per_1k,
            "quality_score": self.quality_score,
            "reliability_score": self.reliability_score
        }


class UserLLMConfigSchema(BaseModel):
    """用户LLM配置Schema"""
    config_name: str = Field(..., description="配置名称")
    is_default: bool = Field(False, description="是否为默认配置")
    
    # 主要LLM配置
    primary_llm: LLMModelConfig = Field(..., description="主要LLM配置")
    
    # 备用LLM配置
    fallback_llms: List[LLMModelConfig] = Field(default_factory=list, description="备用LLM配置")
    
    # 任务特定配置
    task_specific_llms: Dict[str, LLMModelConfig] = Field(default_factory=dict, description="任务特定LLM配置")
    
    # 智能配置
    auto_fallback: bool = Field(True, description="自动切换到备用LLM")
    cost_optimization: bool = Field(False, description="成本优化模式")
    quality_priority: bool = Field(True, description="质量优先模式")
    
    # 安全配置
    content_filter_enabled: bool = Field(True, description="启用内容过滤")
    pii_detection_enabled: bool = Field(True, description="启用PII检测")
    
    class Config:
        schema_extra = {
            "example": {
                "config_name": "production_config",
                "is_default": True,
                "primary_llm": {
                    "provider": "openai",
                    "model_name": "gpt-4",
                    "api_key": "sk-...",
                    "max_tokens": 4096,
                    "temperature": 0.7
                },
                "auto_fallback": True,
                "cost_optimization": False,
                "quality_priority": True
            }
        }


class IntelligentConfigManager:
    """智能配置管理器"""
    
    def __init__(self):
        self._user_configs: Dict[str, UserLLMConfigSchema] = {}
        self._load_default_configs()
    
    def _load_default_configs(self):
        """加载默认配置"""
        # 创建默认的OpenAI配置
        if settings.OPENAI_API_KEY:
            default_openai = LLMModelConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                api_key=settings.OPENAI_API_KEY,
                api_base=getattr(settings, 'OPENAI_API_BASE', None),
                max_tokens=4096,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.DATA_ANALYSIS,
                    ModelCapability.SUMMARIZATION
                ],
                input_cost_per_1k=0.001,
                output_cost_per_1k=0.002
            )
            
            self._user_configs["default"] = UserLLMConfigSchema(
                config_name="default",
                is_default=True,
                primary_llm=default_openai
            )
    
    def get_user_config(self, user_id: str, config_name: str = "default") -> Optional[UserLLMConfigSchema]:
        """获取用户配置"""
        user_config_key = f"{user_id}:{config_name}"
        return self._user_configs.get(user_config_key) or self._user_configs.get("default")
    
    def save_user_config(self, user_id: str, config: UserLLMConfigSchema) -> bool:
        """保存用户配置"""
        try:
            user_config_key = f"{user_id}:{config.config_name}"
            self._user_configs[user_config_key] = config
            
            # 如果是默认配置，移除其他默认配置
            if config.is_default:
                for key, cfg in self._user_configs.items():
                    if key.startswith(f"{user_id}:") and key != user_config_key:
                        cfg.is_default = False
            
            return True
        except Exception as e:
            print(f"保存用户配置失败: {e}")
            return False
    
    def get_user_configs(self, user_id: str) -> List[UserLLMConfigSchema]:
        """获取用户所有配置"""
        user_configs = []
        for key, config in self._user_configs.items():
            if key.startswith(f"{user_id}:"):
                user_configs.append(config)
        
        # 如果用户没有配置，返回默认配置
        if not user_configs and "default" in self._user_configs:
            user_configs.append(self._user_configs["default"])
        
        return user_configs
    
    def delete_user_config(self, user_id: str, config_name: str) -> bool:
        """删除用户配置"""
        user_config_key = f"{user_id}:{config_name}"
        if user_config_key in self._user_configs:
            del self._user_configs[user_config_key]
            return True
        return False
    
    def get_optimal_llm_for_task(
        self,
        user_id: str,
        task_type: str,
        capabilities_required: List[ModelCapability],
        cost_limit: Optional[float] = None
    ) -> Optional[LLMModelConfig]:
        """为任务选择最优LLM"""
        user_config = self.get_user_config(user_id)
        if not user_config:
            return None
        
        # 检查任务特定配置
        if task_type in user_config.task_specific_llms:
            task_llm = user_config.task_specific_llms[task_type]
            if self._llm_supports_capabilities(task_llm, capabilities_required):
                return task_llm
        
        # 检查主要LLM
        if self._llm_supports_capabilities(user_config.primary_llm, capabilities_required):
            if not cost_limit or self._check_cost_limit(user_config.primary_llm, cost_limit):
                return user_config.primary_llm
        
        # 检查备用LLMs
        for fallback_llm in user_config.fallback_llms:
            if self._llm_supports_capabilities(fallback_llm, capabilities_required):
                if not cost_limit or self._check_cost_limit(fallback_llm, cost_limit):
                    return fallback_llm
        
        return user_config.primary_llm  # 兜底返回主要LLM
    
    def _llm_supports_capabilities(
        self,
        llm: LLMModelConfig,
        required_capabilities: List[ModelCapability]
    ) -> bool:
        """检查LLM是否支持所需能力"""
        for cap in required_capabilities:
            if cap not in llm.capabilities:
                return False
        return True
    
    def _check_cost_limit(self, llm: LLMModelConfig, cost_limit: float) -> bool:
        """检查成本限制"""
        # 简单的成本检查，基于输出token成本
        return llm.output_cost_per_1k <= cost_limit
    
    def estimate_cost(
        self,
        llm: LLMModelConfig,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """估算成本"""
        input_cost = (input_tokens / 1000) * llm.input_cost_per_1k
        output_cost = (output_tokens / 1000) * llm.output_cost_per_1k
        return input_cost + output_cost
    
    def get_provider_models(self, provider: LLMProvider) -> List[str]:
        """获取提供商支持的模型列表"""
        provider_models = {
            LLMProvider.OPENAI: [
                "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", 
                "gpt-3.5-turbo-16k", "text-davinci-003"
            ],
            LLMProvider.ANTHROPIC: [
                "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
                "claude-2.1", "claude-2", "claude-instant-1.2"
            ],
            LLMProvider.AZURE_OPENAI: [
                "gpt-4", "gpt-35-turbo", "text-davinci-003"
            ],
            LLMProvider.GOOGLE: [
                "gemini-pro", "gemini-pro-vision", "text-bison-001"
            ],
            LLMProvider.ZHIPU: [
                "chatglm-6b", "chatglm2-6b", "chatglm3-6b"
            ],
            LLMProvider.QWEN: [
                "qwen-7b-chat", "qwen-14b-chat", "qwen-72b-chat"
            ]
        }
        return provider_models.get(provider, [])
    
    def validate_config(self, config: UserLLMConfigSchema) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证API密钥
        if not config.primary_llm.api_key:
            errors.append("主要LLM的API密钥不能为空")
        
        # 验证模型名称
        supported_models = self.get_provider_models(config.primary_llm.provider)
        if supported_models and config.primary_llm.model_name not in supported_models:
            errors.append(f"不支持的模型: {config.primary_llm.model_name}")
        
        # 验证参数范围
        if not 0 <= config.primary_llm.temperature <= 2:
            errors.append("temperature必须在0-2之间")
        
        if not 0 <= config.primary_llm.top_p <= 1:
            errors.append("top_p必须在0-1之间")
        
        return errors


# 创建全局配置管理器实例
intelligent_config_manager = IntelligentConfigManager()


def get_user_llm_config(user_id: str, config_name: str = "default") -> Optional[UserLLMConfigSchema]:
    """获取用户LLM配置的便捷函数"""
    return intelligent_config_manager.get_user_config(user_id, config_name)


def get_optimal_llm_for_task(
    user_id: str,
    task_type: str,
    capabilities_required: List[ModelCapability],
    cost_limit: Optional[float] = None
) -> Optional[LLMModelConfig]:
    """为任务获取最优LLM的便捷函数"""
    return intelligent_config_manager.get_optimal_llm_for_task(
        user_id, task_type, capabilities_required, cost_limit
    )