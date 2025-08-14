#!/usr/bin/env python3
"""
从环境变量初始化AI提供商到数据库
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal
from app.models.ai_provider import AIProvider, AIProviderType
from app.models.user import User


def load_env_file(env_path: str):
    """加载.env文件到环境变量"""
    if not os.path.exists(env_path):
        print(f"❌ 环境文件不存在: {env_path}")
        return False
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    print(f"✅ 已加载环境文件: {env_path}")
    return True


def _create_or_update_provider(
    db, admin_user, provider_name: str, api_key_env: str, 
    base_url_env: str = None, model_env: str = None,
    default_base_url: str = None, default_model: str = 'gpt-3.5-turbo',
    is_active: bool = True
):
    """通用的AI提供商创建/更新函数，支持向后兼容"""
    from app.core.ai_url_utils import normalize_ai_provider_url, validate_ai_provider_url
    
    # 支持向后兼容：优先使用新的环境变量，然后回退到旧的
    api_key = os.getenv(api_key_env)
    if not api_key and api_key_env == 'PRIMARY_AI_API_KEY':
        api_key = os.getenv('XIAOAI_API_KEY')
    
    base_url = os.getenv(base_url_env) if base_url_env else default_base_url
    if not base_url and base_url_env == 'PRIMARY_AI_BASE_URL':
        base_url = os.getenv('XIAOAI_BASE_URL')
    
    model = os.getenv(model_env) if model_env else default_model
    if not model and model_env == 'PRIMARY_AI_MODEL':
        model = os.getenv('XIAOAI_MODEL', default_model)
    
    # 跳过无效的API密钥
    if not api_key or api_key in ['your-openai-api-key', 'your-api-key']:
        print(f"⏭️  跳过{provider_name}: 未配置有效的API密钥")
        return
    
    # 处理URL
    if base_url:
        url_validation = validate_ai_provider_url(base_url)
        if not url_validation['is_valid']:
            print(f"⚠️  {provider_name} URL有问题: {', '.join(url_validation['issues'])}")
            print(f"   原始URL: {base_url}")
        
        normalized_url = normalize_ai_provider_url(base_url, 'openai')
        print(f"🔗 {provider_name} URL处理:")
        print(f"   输入: {base_url}")
        print(f"   标准化: {normalized_url}")
    else:
        normalized_url = default_base_url
        print(f"🔗 {provider_name} 使用默认URL: {normalized_url}")
    
    # 检查是否已存在
    existing_provider = db.query(AIProvider).filter(
        AIProvider.provider_name == provider_name
    ).first()
    
    if existing_provider:
        # 更新现有配置
        existing_provider.api_base_url = normalized_url
        existing_provider.api_key = api_key
        existing_provider.default_model_name = model
        existing_provider.is_active = is_active
        print(f"✅ 已更新{provider_name} AI提供商配置")
    else:
        # 创建新的提供商
        new_provider = AIProvider(
            provider_name=provider_name,
            provider_type=AIProviderType.openai,
            api_base_url=normalized_url,
            api_key=api_key,
            default_model_name=model,
            is_active=is_active,
            user_id=admin_user.id
        )
        db.add(new_provider)
        print(f"✅ 已创建{provider_name} AI提供商")


def init_ai_providers():
    """从环境变量初始化AI提供商"""
    db = SessionLocal()
    try:
        # 获取管理员用户
        admin_user = db.query(User).filter(User.username == 'admin').first()
        if not admin_user:
            print("❌ 未找到admin用户，请先运行 init_db.py")
            return False
        
        # 处理主要AI提供商（支持通用配置和向后兼容）
        primary_provider = os.getenv('PRIMARY_AI_PROVIDER', 'xiaoai')
        _create_or_update_provider(
            db=db,
            admin_user=admin_user,
            provider_name=primary_provider,
            api_key_env='PRIMARY_AI_API_KEY',
            base_url_env='PRIMARY_AI_BASE_URL',
            model_env='PRIMARY_AI_MODEL',
            default_model='gpt-4o-mini',
            is_active=True
        )
        
        # 处理备用AI提供商 (OpenAI)
        _create_or_update_provider(
            db=db,
            admin_user=admin_user,
            provider_name='OpenAI',
            api_key_env='OPENAI_API_KEY',
            base_url_env=None,  # OpenAI使用默认URL
            model_env='OPENAI_MODEL',
            default_base_url='https://api.openai.com/v1',
            default_model='gpt-3.5-turbo',
            is_active=False  # 默认不激活
        )
        
        db.commit()
        
        # 显示所有AI提供商
        providers = db.query(AIProvider).all()
        print(f"\\n📋 当前AI提供商列表:")
        for provider in providers:
            status = "✅ 活跃" if provider.is_active else "❌ 停用"
            api_key_display = f"{provider.api_key[:10]}...{provider.api_key[-4:]}" if provider.api_key else "未设置"
            print(f"  • {provider.provider_name}")
            print(f"    - URL: {provider.api_base_url}")
            print(f"    - 模型: {provider.default_model_name}")
            print(f"    - API Key: {api_key_display}")
            print(f"    - 状态: {status}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 初始化AI提供商失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    print("🤖 正在从环境变量初始化AI提供商...")
    
    # 尝试加载docker目录的.env文件
    docker_env_path = os.path.join(os.path.dirname(__file__), '../../docker/.env')
    backend_env_path = os.path.join(os.path.dirname(__file__), '../.env')
    
    env_loaded = False
    for env_path in [docker_env_path, backend_env_path]:
        if os.path.exists(env_path):
            load_env_file(env_path)
            env_loaded = True
            break
    
    if not env_loaded:
        print("⚠️  未找到.env文件，请确保在docker或backend目录下有.env文件")
        print("💡 可以从docker/env.example复制并修改")
    
    # 初始化AI提供商
    if init_ai_providers():
        print("\\n🎉 AI提供商初始化完成！")
    else:
        print("\\n❌ AI提供商初始化失败")
        sys.exit(1)


if __name__ == "__main__":
    main()