import logging
import os
import sys

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
    Initialize the database with initial data.
    """
    success = True
    
    try:
        # 1. 创建超级用户
        user = db_session.query(User).filter(User.username == settings.FIRST_SUPERUSER).first()
        if not user:
            logger.info(f"Creating superuser: {settings.FIRST_SUPERUSER}")
            user = User(
                username=settings.FIRST_SUPERUSER,
                email=settings.FIRST_SUPERUSER_EMAIL,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
                is_active=True,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            logger.info(f"✅ Superuser {settings.FIRST_SUPERUSER} created successfully.")
        else:
            logger.info(f"ℹ️  Superuser {settings.FIRST_SUPERUSER} already exists.")

        # 2. 创建默认AI提供商
        provider = (
            db_session.query(AIProvider)
            .filter(AIProvider.provider_name == settings.DEFAULT_AI_PROVIDER_NAME)
            .first()
        )
        if not provider:
            logger.info(f"Creating default AI provider: {settings.DEFAULT_AI_PROVIDER_NAME}")
            
            # 加密API密钥
            encrypted_api_key = None
            if settings.DEFAULT_AI_PROVIDER_API_KEY and settings.DEFAULT_AI_PROVIDER_API_KEY != "sk-your-api-key":
                encrypted_api_key = encrypt_data(settings.DEFAULT_AI_PROVIDER_API_KEY)
            
            provider = AIProvider(
                provider_name=settings.DEFAULT_AI_PROVIDER_NAME,
                provider_type=AIProviderType.openai,
                api_base_url=settings.DEFAULT_AI_PROVIDER_API_BASE,
                api_key=encrypted_api_key,
                default_model_name=settings.DEFAULT_AI_PROVIDER_MODELS[0] if settings.DEFAULT_AI_PROVIDER_MODELS else "gpt-3.5-turbo",
                is_active=True,
                user_id=user.id,
            )
            db_session.add(provider)
            db_session.commit()
            db_session.refresh(provider)
            logger.info(f"✅ AI provider {settings.DEFAULT_AI_PROVIDER_NAME} created successfully.")
        else:
            logger.info(f"ℹ️  AI provider {settings.DEFAULT_AI_PROVIDER_NAME} already exists.")

        # 3. 创建其他默认AI提供商（如果配置了的话）
        if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "sk-your-openai-api-key-here":
            openai_provider = (
                db_session.query(AIProvider)
                .filter(AIProvider.provider_name == "XiaoAI.plus")
                .first()
            )
            if not openai_provider:
                logger.info("Creating XiaoAI.plus provider...")
                encrypted_api_key = encrypt_data(os.getenv("OPENAI_API_KEY"))
                openai_provider = AIProvider(
                    provider_name="XiaoAI.plus",
                    provider_type=AIProviderType.openai,
                    api_base_url=os.getenv("OPENAI_BASE_URL", "https://xiaoai.plus/v1"),
                    api_key=encrypted_api_key,
                    default_model_name=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
                    is_active=True,
                    user_id=user.id,
                )
                db_session.add(openai_provider)
                db_session.commit()
                logger.info("✅ XiaoAI.plus provider created successfully.")

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
