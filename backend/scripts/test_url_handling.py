#!/usr/bin/env python3
"""
测试智能URL处理功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.ai_url_utils import normalize_ai_provider_url, validate_ai_provider_url


def test_url_normalization():
    """测试URL标准化功能"""
    test_cases = [
        # 简单域名
        "xiaoai.com",
        "api.openai.com", 
        
        # 带协议
        "https://xiaoai.com",
        "https://api.openai.com",
        "http://localhost:8080",
        
        # 完整URL
        "https://xiaoai.com/v1/chat/completions",
        "https://api.openai.com/v1/chat/completions",
        
        # 自定义端口
        "https://my-ai.local:8080",
        
        # 带路径的基础URL
        "https://api.example.com/ai",
        
        # 错误格式
        "",
        "invalid-url",
    ]
    
    print("🧪 测试URL标准化功能")
    print("=" * 80)
    
    for i, url in enumerate(test_cases, 1):
        print(f"\n{i}. 测试URL: '{url}'")
        
        # 验证URL
        validation = validate_ai_provider_url(url)
        print(f"   验证结果: {'✅ 有效' if validation['is_valid'] else '❌ 无效'}")
        if validation['provider_type']:
            print(f"   检测到的提供商: {validation['provider_type']}")
        if validation['issues']:
            print(f"   问题: {', '.join(validation['issues'])}")
        
        # 标准化URL
        if validation['is_valid']:
            normalized = normalize_ai_provider_url(url)
            print(f"   标准化URL: {normalized}")
            
            # 测试不同提供商类型
            for provider_type in ['openai', 'anthropic']:
                normalized_typed = normalize_ai_provider_url(url, provider_type)
                if normalized_typed != normalized:
                    print(f"   {provider_type}格式: {normalized_typed}")


def main():
    print("🔗 AI提供商URL智能处理测试")
    print()
    
    test_url_normalization()
    
    print(f"\n✅ 测试完成")
    print(f"\n💡 使用说明:")
    print(f"  - 您可以在配置中使用简化的URL格式")
    print(f"  - 系统会自动检测提供商类型并补全标准端点")
    print(f"  - 支持的格式包括：域名、带协议的URL、完整的API URL")


if __name__ == "__main__":
    main()