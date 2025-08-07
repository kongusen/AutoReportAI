"""
AI供应商配置
配置用于大数据分析报告生成的AI服务
"""

import os
from typing import Dict, Any

# AI供应商配置
AI_PROVIDER_CONFIG = {
    "api_base_url": "https://xiaoai.plus/v1/chat/completions",
    "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "model": "gpt-4o-mini",
    "max_tokens": 4000,
    "temperature": 0.3,
    "timeout": 60,
    "retry_times": 3,
    "stream": False,
    "verify_ssl": False  # 如果SSL有问题可以设置为False
}

# 用于不同场景的模型配置
MODEL_CONFIGS = {
    "placeholder_analysis": {
        "model": "gpt-4o-mini",
        "max_tokens": 2000,
        "temperature": 0.1,  # 低温度保证分析准确性
        "timeout": 30
    },
    "data_analysis": {
        "model": "gpt-4o-mini", 
        "max_tokens": 3000,
        "temperature": 0.3,  # 中等温度平衡创造性和准确性
        "timeout": 60
    },
    "report_generation": {
        "model": "gpt-4o-mini",
        "max_tokens": 4000,
        "temperature": 0.5,  # 稍高温度增加表达多样性
        "timeout": 90
    }
}

def get_ai_config(scenario: str = "default") -> Dict[str, Any]:
    """
    获取AI配置
    
    Args:
        scenario: 使用场景 (placeholder_analysis, data_analysis, report_generation)
    """
    base_config = AI_PROVIDER_CONFIG.copy()
    
    if scenario in MODEL_CONFIGS:
        base_config.update(MODEL_CONFIGS[scenario])
    
    return base_config

def validate_ai_config() -> bool:
    """验证AI配置是否完整"""
    required_keys = ["api_base_url", "api_key", "model"]
    
    for key in required_keys:
        if not AI_PROVIDER_CONFIG.get(key):
            print(f"❌ AI配置缺少必要参数: {key}")
            return False
    
    print("✅ AI配置验证通过")
    return True

if __name__ == "__main__":
    print("🤖 AI供应商配置信息:")
    print(f"API地址: {AI_PROVIDER_CONFIG['api_base_url']}")
    print(f"模型: {AI_PROVIDER_CONFIG['model']}")
    print(f"API Key: {AI_PROVIDER_CONFIG['api_key'][:10]}...{AI_PROVIDER_CONFIG['api_key'][-4:]}")
    
    validate_ai_config()