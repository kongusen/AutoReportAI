import logging
import os
import sys
import uuid

# Add the project root to the Python path
# This allows running the script from the 'scripts' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.ai_provider import AIProvider, AIProviderType
from app.models.user import User
from app.core.security import get_password_hash
from app.core.security_utils import encrypt_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db(db_session):
    """
    Initialize the database with essential data only.
    Creates superuser and AI providers based on environment configuration.
    """
    success = True
    
    try:
        # 1. 创建超级用户
        user = db_session.query(User).filter(User.username == settings.FIRST_SUPERUSER).first()
        if not user:
            logger.info(f"Creating superuser: {settings.FIRST_SUPERUSER}")
            user = User(
                id=uuid.uuid4(),
                username=settings.FIRST_SUPERUSER,
                email=settings.FIRST_SUPERUSER_EMAIL,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
                is_active=True,
                full_name="Administrator"
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            logger.info(f"✅ Superuser {settings.FIRST_SUPERUSER} created successfully.")
        else:
            logger.info(f"ℹ️  Superuser {settings.FIRST_SUPERUSER} already exists.")

        # 2. 创建AI提供商（仅在配置了API密钥时）
        ai_providers_created = 0
        
        # OpenAI Provider（如果配置了）
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key and openai_api_key not in ["sk-your-openai-api-key-here", "sk-your-api-key"]:
            provider_name = "OpenAI"
            existing_provider = db_session.query(AIProvider).filter(
                AIProvider.provider_name == provider_name
            ).first()
            
            if not existing_provider:
                logger.info(f"Creating AI provider: {provider_name}")
                encrypted_api_key = encrypt_data(openai_api_key)
                provider = AIProvider(
                    provider_name=provider_name,
                    provider_type=AIProviderType.openai,
                    api_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                    api_key=encrypted_api_key,
                    default_model_name=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo"),
                    is_active=True,
                    user_id=user.id,
                )
                db_session.add(provider)
                ai_providers_created += 1
                logger.info(f"✅ AI provider {provider_name} created successfully.")
            else:
                logger.info(f"ℹ️  AI provider {provider_name} already exists.")

        # Azure OpenAI Provider（如果配置了）
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if azure_api_key and azure_endpoint:
            provider_name = "Azure OpenAI"
            existing_provider = db_session.query(AIProvider).filter(
                AIProvider.provider_name == provider_name
            ).first()
            
            if not existing_provider:
                logger.info(f"Creating AI provider: {provider_name}")
                encrypted_api_key = encrypt_data(azure_api_key)
                provider = AIProvider(
                    provider_name=provider_name,
                    provider_type=AIProviderType.azure_openai,
                    api_base_url=azure_endpoint,
                    api_key=encrypted_api_key,
                    default_model_name=os.getenv("AZURE_OPENAI_DEFAULT_MODEL", "gpt-35-turbo"),
                    is_active=False,  # 默认不激活，避免冲突
                    user_id=user.id,
                )
                db_session.add(provider)
                ai_providers_created += 1
                logger.info(f"✅ AI provider {provider_name} created successfully.")
            else:
                logger.info(f"ℹ️  AI provider {provider_name} already exists.")

        if ai_providers_created > 0:
            db_session.commit()
        
        if ai_providers_created == 0:
            logger.warning("⚠️  No AI providers were created. Please configure API keys in environment variables.")
            logger.info("   - OPENAI_API_KEY: for OpenAI integration")
            logger.info("   - AZURE_OPENAI_API_KEY & AZURE_OPENAI_ENDPOINT: for Azure OpenAI integration")

        logger.info("🎉 Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during database initialization: {e}")
        db_session.rollback()
        return False


def main():
    """
    Main function to initialize the database.
    """
    logger.info("🚀 --- Starting Database Initialization ---")
    
    db_session = None
    try:
        db_session = SessionLocal()
        success = init_db(db_session)
        
        if success:
            logger.info("✅ --- Database Initialization Completed Successfully ---")
        else:
            logger.error("❌ --- Database Initialization Failed ---")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Critical error during database initialization: {e}")
        sys.exit(1)
    finally:
        if db_session:
            db_session.close()


if __name__ == "__main__":
    main()
