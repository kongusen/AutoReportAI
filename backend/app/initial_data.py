import logging

from app.crud.crud_user import user as crud_user
from app.db.base import Base  # noqa: F401
from app.db.session import SessionLocal, engine
from app.models.ai_provider import AIProvider  # noqa: F401
from app.models.data_source import DataSource  # noqa: F401
from app.models.placeholder_mapping import PlaceholderMapping  # noqa: F401

# Import all models here so that Base has them registered
from app.models.task import Task  # noqa: F401
from app.models.template import Template  # noqa: F401
from app.models.user import User  # noqa: F401
from app.schemas.user import UserCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    db = SessionLocal()
    logger.info("Creating initial database tables")
    Base.metadata.create_all(bind=engine)

    # Create a first superuser
    user = crud_user.get_by_username(db, username="admin")
    if not user:
        user_in = UserCreate(username="admin", password="password", is_superuser=True)
        user = crud_user.create(db, obj_in=user_in)
        logger.info("First superuser created")

    logger.info("Database initialization finished.")
    db.close()


if __name__ == "__main__":
    init_db()
