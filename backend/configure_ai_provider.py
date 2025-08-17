#!/usr/bin/env python3
"""
配置AI Provider
"""

import asyncio
import os
import sys
from sqlalchemy.orm import Session

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

from app.db.session import get_db_session
from app.crud import ai_provider as crud_ai_provider
from app.schemas.ai_provider import AIProviderCreate
from app.models.ai_provider import AIProviderType
from app.core.security_utils import encrypt_data

async def configure_ai_provider():
    """配置AI Provider"""
    
    print("🤖 配置AI Provider...")
    
    # AI配置
    provider_config = {
        "name": "XiaoAI Provider",
        "provider_type": AIProviderType.openai,  # 使用OpenAI兼容接口
        "api_key": "sk-7J3mcoQBWDG85CFYxDJtNzZoglnOA2tibKCTi7HLROIVPii2",
        "api_base_url": "https://xiaoai.com/api/v1",
        "default_model_name": "gpt-4o-mini",
        "is_active": True
    }
    
    try:
        with get_db_session() as db:
            # 检查是否已存在AI Provider
            existing_provider = crud_ai_provider.get_active(db)
            
            if existing_provider:
                print(f"  ✅ 发现现有AI Provider: {existing_provider.name}")
                print(f"     类型: {existing_provider.provider_type}")
                print(f"     模型: {existing_provider.default_model_name}")
                print(f"     状态: {'活跃' if existing_provider.is_active else '非活跃'}")
                
                # 更新现有Provider
                existing_provider.name = provider_config["name"]
                existing_provider.api_base_url = provider_config["api_base_url"]
                existing_provider.default_model_name = provider_config["default_model_name"]
                existing_provider.is_active = provider_config["is_active"]
                
                # 加密并更新API Key
                encrypted_key = encrypt_data(provider_config["api_key"])
                existing_provider.api_key = encrypted_key
                
                db.commit()
                print("  🔄 AI Provider配置已更新")
                
            else:
                # 创建新的AI Provider
                print("  🆕 创建新的AI Provider...")
                
                # 加密API Key
                encrypted_key = encrypt_data(provider_config["api_key"])
                
                provider_data = AIProviderCreate(
                    name=provider_config["name"],
                    provider_type=provider_config["provider_type"],
                    api_key=encrypted_key,
                    api_base_url=provider_config["api_base_url"],
                    default_model_name=provider_config["default_model_name"],
                    is_active=provider_config["is_active"]
                )
                
                new_provider = crud_ai_provider.create(db, obj_in=provider_data)
                print(f"  ✅ AI Provider创建成功: {new_provider.id}")
        
        print("🎉 AI Provider配置完成！")
        return True
        
    except Exception as e:
        print(f"❌ AI Provider配置失败: {e}")
        return False

async def test_ai_provider():
    """测试AI Provider连接"""
    print("\n🔍 测试AI Provider连接...")
    
    try:
        from app.services.ai_integration.ai_service_enhanced import EnhancedAIService
        
        with get_db_session() as db:
            ai_service = EnhancedAIService(db)
            
            # 测试健康检查
            health_result = await ai_service.health_check()
            
            if health_result["status"] == "healthy":
                print("  ✅ AI服务健康检查通过")
                print(f"     Provider: {health_result.get('provider', 'Unknown')}")
                print(f"     Model: {health_result.get('model', 'Unknown')}")
                
                # 测试简单的AI调用
                try:
                    test_result = await ai_service.analyze_with_context(
                        context="测试数据: 销售额增长了20%",
                        prompt="请分析这个业务数据",
                        task_type="test_analysis"
                    )
                    
                    print("  🤖 AI分析测试成功")
                    print(f"     响应长度: {len(test_result)} 字符")
                    print(f"     响应预览: {test_result[:100]}...")
                    
                    return True
                    
                except Exception as ai_error:
                    print(f"  ⚠️ AI分析测试失败: {ai_error}")
                    return False
                    
            else:
                print(f"  ❌ AI服务健康检查失败: {health_result}")
                return False
                
    except Exception as e:
        print(f"❌ AI Provider测试失败: {e}")
        return False

async def main():
    """主函数"""
    print("🚀 开始配置和测试AI Provider")
    print("=" * 50)
    
    # 1. 配置AI Provider
    config_success = await configure_ai_provider()
    
    if not config_success:
        print("❌ AI Provider配置失败，无法继续")
        return
    
    # 2. 测试AI Provider
    test_success = await test_ai_provider()
    
    print("\n" + "=" * 50)
    if test_success:
        print("🎉 AI Provider配置和测试完成！系统已就绪")
    else:
        print("⚠️ AI Provider配置完成，但测试失败")
        print("   这可能是由于网络连接或API密钥问题")
        print("   Agent系统将使用模拟模式运行")

if __name__ == "__main__":
    asyncio.run(main())