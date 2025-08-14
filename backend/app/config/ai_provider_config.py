"""
AI供应商配置模块
所有AI提供商配置均从数据库读取，此文件保留用于场景化配置
"""

from typing import Dict, Any

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

def get_scenario_config(scenario: str = "default") -> Dict[str, Any]:
    """
    获取特定场景的模型配置
    
    Args:
        scenario: 使用场景 (placeholder_analysis, data_analysis, report_generation)
    
    Returns:
        场景特定的配置参数，需要与数据库配置合并使用
    """
    if scenario in MODEL_CONFIGS:
        return MODEL_CONFIGS[scenario].copy()
    
    # 返回默认配置
    return {
        "model": "gpt-4o-mini",
        "max_tokens": 4000,
        "temperature": 0.3,
        "timeout": 60
    }


def get_default_model_params() -> Dict[str, Any]:
    """获取默认模型参数"""
    return {
        "max_tokens": 4000,
        "temperature": 0.3,
        "timeout": 60,
        "retry_times": 3,
        "stream": False,
        "verify_ssl": True
    }


if __name__ == "__main__":
    print("🤖 AI场景配置模块")
    print("此模块提供不同场景下的AI模型参数配置")
    print(f"可用场景: {', '.join(MODEL_CONFIGS.keys())}")
    
    for scenario, config in MODEL_CONFIGS.items():
        print(f"\n📋 {scenario}:")
        for key, value in config.items():
            print(f"  {key}: {value}")