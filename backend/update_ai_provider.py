#!/usr/bin/env python3
"""
更新现有的AI Provider配置
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

from app.db.session import get_db_session
from app.crud import ai_provider as crud_ai_provider
from app.core.security_utils import encrypt_data

def update_ai_provider():
    """更新AI Provider配置"""
    
    print("🤖 更新AI Provider配置...")
    
    # 新的AI配置
    new_config = {
        "api_key": "sk-24hmsY1U3zJmGVNlB5C5FeE8790f4bF3A0D38fB72a33C9Bd",
        "api_base_url": "https://api.xi-ai.cn/v1",
        "default_model_name": "gpt-4o-mini",
    }
    
    try:
        with get_db_session() as db:
            # 获取现有的活跃Provider
            existing_provider = crud_ai_provider.get_active(db)
            
            if existing_provider:
                print(f"  ✅ 找到现有AI Provider: {existing_provider.provider_name}")
                print(f"     当前状态: {existing_provider.provider_type}")
                
                # 更新配置
                existing_provider.api_base_url = new_config["api_base_url"]
                existing_provider.default_model_name = new_config["default_model_name"]
                
                # 加密并更新API Key
                encrypted_key = encrypt_data(new_config["api_key"])
                existing_provider.api_key = encrypted_key
                
                db.commit()
                
                print(f"  🔄 AI Provider配置已更新")
                print(f"     模型: {new_config['default_model_name']}")
                print(f"     API基础URL: {new_config['api_base_url']}")
                print(f"     API Key: {new_config['api_key'][:10]}...")
                
                return True
                
            else:
                print("  ❌ 未找到活跃的AI Provider")
                return False
        
    except Exception as e:
        print(f"❌ AI Provider更新失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 更新AI Provider配置")
    print("=" * 40)
    
    success = update_ai_provider()
    
    print("=" * 40)
    if success:
        print("🎉 AI Provider配置更新完成！")
    else:
        print("❌ AI Provider配置更新失败")