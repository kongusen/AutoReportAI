import logging
import os
import sys

# Add the project root to the Python path
# This allows running the script from the 'scripts' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.ai_provider import AIProvider
from app.models.user import User
from app.core.security import get_password_hash


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db(db_session):
    """
    Initialize the database with initial data.
    """
    # Check if user already exists
    user = db_session.query(User).filter(User.username == settings.FIRST_SUPERUSER).first()
    if not user:
        # Create user
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
        logger.info(f"Superuser {settings.FIRST_SUPERUSER} created successfully.")
    else:
        logger.info(f"Superuser {settings.FIRST_SUPERUSER} already exists in the database.")

    # Check if AI provider already exists
    provider = (
        db_session.query(AIProvider)
        .filter(AIProvider.provider_name == settings.DEFAULT_AI_PROVIDER_NAME)
        .first()
    )
    if not provider:
        # Create AI provider
        logger.info(f"Creating default AI provider: {settings.DEFAULT_AI_PROVIDER_NAME}")
        from app.models.ai_provider import AIProviderType
        provider = AIProvider(
            provider_name=settings.DEFAULT_AI_PROVIDER_NAME,
            provider_type=AIProviderType.openai,
            api_base_url=settings.DEFAULT_AI_PROVIDER_API_BASE,
            api_key=settings.DEFAULT_AI_PROVIDER_API_KEY,
            default_model_name=settings.DEFAULT_AI_PROVIDER_MODELS[0],
            is_active=True,
            user_id=user.id,
        )
        db_session.add(provider)
        db_session.commit()
        db_session.refresh(provider)
        logger.info(f"AI provider {settings.DEFAULT_AI_PROVIDER_NAME} created successfully.")
    else:
        logger.info(
            f"AI provider {settings.DEFAULT_AI_PROVIDER_NAME} already exists in the database."
        )


def main():
    """
    Main function to initialize the database.
    """
    logger.info("--- Starting Database Initialization ---")
    try:
        db_session = SessionLocal()
        init_db(db_session)
    except Exception as e:
        logger.error(f"An error occurred during database initialization: {e}")
    finally:
        if 'db_session' in locals() and db_session:
            db_session.close()
    logger.info("--- Database Initialization Finished ---")


if __name__ == "__main__":
    main()
