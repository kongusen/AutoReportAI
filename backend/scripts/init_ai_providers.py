#!/usr/bin/env python3
"""
AI Provider Initialization Script
用于初始化系统中的AI提供商配置
"""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.ai_provider import AIProvider, AIProviderType
from app.models.user import User
from app.core.security_utils import encrypt_data
from app.core.config import settings

def create_ai_provider(
    db: Session,
    provider_name: str,
    provider_type: AIProviderType,
    api_key: str = None,
    api_base_url: str = None,
    default_model_name: str = None,
    is_active: bool = False,
    user_id: str = None
) -> AIProvider:
    """创建AI提供商"""
    
    # 加密API密钥
    encrypted_api_key = None
    if api_key:
        encrypted_api_key = encrypt_data(api_key)
    
    ai_provider = AIProvider(
        provider_name=provider_name,
        provider_type=provider_type,
        api_base_url=api_base_url,
        api_key=encrypted_api_key,
        default_model_name=default_model_name,
        is_active=is_active,
        user_id=user_id
    )
    
    db.add(ai_provider)
    db.commit()
    db.refresh(ai_provider)
    
    print(f"✅ Created AI Provider: {provider_name} ({provider_type.value})")
    return ai_provider

def init_ai_providers():
    """初始化AI提供商"""
    db = SessionLocal()
    
    try:
        # 检查是否已有AI提供商
        existing_providers = db.query(AIProvider).count()
        if existing_providers > 0:
            print("⚠️  AI providers already exist. Skipping initialization.")
            return
        
        # 获取现有用户ID
        user = db.query(User).first()
        if not user:
            print("❌ 没有找到用户，请先创建用户")
            return
        default_user_id = str(user.id)
        print(f"使用用户ID: {default_user_id}")
        
        # 1. XiaoAI.plus Provider
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            create_ai_provider(
                db=db,
                provider_name="XiaoAI.plus",
                provider_type=AIProviderType.openai,
                api_key=openai_api_key,
                api_base_url=os.getenv("OPENAI_BASE_URL", "https://xiaoai.plus/v1"),
                default_model_name=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
                is_active=True,
                user_id=default_user_id
            )
        else:
            print("⚠️  OpenAI API key not found. Skipping XiaoAI.plus provider.")
        
        # 2. Azure OpenAI Provider
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if azure_api_key:
            create_ai_provider(
                db=db,
                provider_name="Azure OpenAI",
                provider_type=AIProviderType.azure_openai,
                api_key=azure_api_key,
                api_base_url=os.getenv("AZURE_OPENAI_ENDPOINT"),
                default_model_name="gpt-35-turbo",
                is_active=False,
                user_id=default_user_id
            )
        else:
            print("⚠️  Azure OpenAI API key not found. Skipping Azure OpenAI provider.")
        
        # 3. Mock Provider (for testing)
        create_ai_provider(
            db=db,
            provider_name="Mock AI",
            provider_type=AIProviderType.mock,
            default_model_name="mock-model",
            is_active=False,
            user_id=default_user_id
        )
        
        print("🎉 AI providers initialization completed!")
        
    except Exception as e:
        print(f"❌ Error initializing AI providers: {e}")
        db.rollback()
    finally:
        db.close()

def list_ai_providers():
    """列出所有AI提供商"""
    db = SessionLocal()
    
    try:
        providers = db.query(AIProvider).all()
        
        if not providers:
            print("📝 No AI providers found.")
            return
        
        print("📋 AI Providers:")
        print("-" * 60)
        
        for provider in providers:
            status = "🟢 Active" if provider.is_active else "🔴 Inactive"
            print(f"{provider.provider_name} ({provider.provider_type.value}) - {status}")
            print(f"  Model: {provider.default_model_name}")
            print(f"  Base URL: {provider.api_base_url or 'Default'}")
            print()
        
    except Exception as e:
        print(f"❌ Error listing AI providers: {e}")
    finally:
        db.close()

def activate_ai_provider(provider_name: str):
    """激活指定的AI提供商"""
    db = SessionLocal()
    
    try:
        # 先停用所有提供商
        db.query(AIProvider).update({AIProvider.is_active: False})
        
        # 激活指定提供商
        provider = db.query(AIProvider).filter(
            AIProvider.provider_name == provider_name
        ).first()
        
        if provider:
            provider.is_active = True
            db.commit()
            print(f"✅ Activated AI Provider: {provider_name}")
        else:
            print(f"❌ AI Provider not found: {provider_name}")
            
    except Exception as e:
        print(f"❌ Error activating AI provider: {e}")
        db.rollback()
    finally:
        db.close()

def test_ai_provider(provider_name: str):
    """测试AI提供商连接"""
    db = SessionLocal()
    
    try:
        provider = db.query(AIProvider).filter(
            AIProvider.provider_name == provider_name
        ).first()
        
        if not provider:
            print(f"❌ AI Provider not found: {provider_name}")
            return
        
        if provider.provider_type == AIProviderType.mock:
            print("🤖 Mock provider - no real connection test needed")
            return
        
        # 这里可以添加实际的连接测试逻辑
        print(f"🧪 Testing connection to {provider_name}...")
        print("✅ Connection test completed (mock)")
        
    except Exception as e:
        print(f"❌ Error testing AI provider: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Provider Management")
    parser.add_argument("action", choices=["init", "list", "activate", "test"], 
                       help="Action to perform")
    parser.add_argument("--provider", help="Provider name for activate/test actions")
    
    args = parser.parse_args()
    
    if args.action == "init":
        init_ai_providers()
    elif args.action == "list":
        list_ai_providers()
    elif args.action == "activate":
        if not args.provider:
            print("❌ Provider name required for activate action")
            sys.exit(1)
        activate_ai_provider(args.provider)
    elif args.action == "test":
        if not args.provider:
            print("❌ Provider name required for test action")
            sys.exit(1)
        test_ai_provider(args.provider) 