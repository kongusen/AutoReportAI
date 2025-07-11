import logging
from app.db.session import engine
from app.db.base import Base
# Import all models here so that Base has them registered
from app.models.task import Task
from app.models.template import Template
from app.models.placeholder_mapping import PlaceholderMapping

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    logger.info("Creating initial database tables")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

if __name__ == "__main__":
    init_db() 