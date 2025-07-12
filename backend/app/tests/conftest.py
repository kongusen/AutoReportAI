import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.api.router import api_router
from app.core.config import settings
from app.db.base import Base


# Create a test app without the startup event
@pytest.fixture(scope="session")
def test_app():
    """Create a test FastAPI app without startup events"""
    app = FastAPI(title=f"{settings.PROJECT_NAME} Test")
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    @app.get("/")
    def read_root():
        return {"message": f"Welcome to {settings.PROJECT_NAME} Test"}
    
    return app


@pytest.fixture(scope="session")
def engine():
    return create_engine(settings.test_db_url, pool_pre_ping=True)


@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine, tables):
    """Returns an sqlalchemy session, and after the test tears down everything properly."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(test_app, db_session):
    """
    Returns a TestClient that can be used to test the API.
    The database dependency is overridden to use the test database.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as c:
        yield c
