"""
全局测试配置 - 提供测试fixtures、数据库配置和通用工具
"""

import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
# Removed async SQLAlchemy imports to simplify testing
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient

# 设置测试环境变量
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.db.base import Base


# 测试数据库引擎
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

test_engine = create_engine(
    "sqlite:///test.db",
    connect_args={"check_same_thread": False},
    echo=False
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def event_loop():
    """创建会话级别的事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def setup_database():
    """设置测试数据库"""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(setup_database):
    """提供数据库会话"""
    session = TestSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def override_get_db(db_session):
    """覆盖数据库依赖"""
    def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db) -> Generator[TestClient, None, None]:
    """提供同步测试客户端"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def async_client(override_get_db):
    """提供异步测试客户端"""
    return AsyncClient(app=app, base_url="http://test")


@pytest.fixture
def test_user():
    """创建测试用户对象"""
    from app.models.user import User
    return User(
        id="user_123",
        username="testuser",
        email="test@example.com",
        is_active=True
    )


@pytest.fixture
def admin_user():
    """创建管理员用户对象"""
    from app.models.user import User
    return User(
        id="admin_123",
        username="admin",
        email="admin@example.com",
        is_active=True,
        is_admin=True
    )


@pytest.fixture
def auth_headers():
    """生成认证头"""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
def admin_headers():
    """生成管理员认证头"""
    return {"Authorization": "Bearer admin_token"}


@pytest.fixture
def test_template():
    """创建测试模板对象"""
    from app.models.template import Template
    return Template(
        id="template_001",
        name="Test Template",
        description="A test template for unit testing",
        content="Hello {{name}}, your age is {{age}}",
        user_id="user_123",
        is_active=True
    )


@pytest.fixture
def test_data_source():
    """创建测试数据源对象"""
    from app.models.data_source import DataSource
    return DataSource(
        id="ds_001",
        name="Test DataSource",
        source_type="postgresql",
        connection_string="postgresql://test:test@localhost:5432/testdb",
        user_id="user_123",
        is_active=True
    )


@pytest.fixture
def test_task():
    """创建测试任务对象"""
    from app.models.task import Task
    return Task(
        id="task_001",
        name="Test Task",
        description="A test task for unit testing",
        template_id="template_001",
        status="pending",
        task_type="generate_report",
        user_id="user_123"
    )


@pytest.fixture
def mock_redis():
    """模拟Redis连接"""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=False)
    mock.expire = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_celery():
    """模拟Celery任务"""
    mock = MagicMock()
    mock.delay = MagicMock()
    mock.apply_async = MagicMock()
    return mock


@pytest.fixture
def mock_llm_client():
    """模拟LLM客户端"""
    mock = AsyncMock()
    mock.complete = AsyncMock(return_value="Mocked LLM response")
    mock.is_healthy = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_data_connector():
    """模拟数据连接器"""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.execute = AsyncMock(return_value=[{"col1": "value1", "col2": "value2"}])
    mock.test_connection = AsyncMock(return_value=True)
    mock.get_schema = AsyncMock(return_value={"tables": ["table1", "table2"]})
    return mock


# 测试数据工厂
class TestDataFactory:
    """测试数据工厂类"""
    
    @staticmethod
    def create_user_data(**kwargs):
        """创建用户测试数据"""
        default_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
            "is_admin": False
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_template_data(**kwargs):
        """创建模板测试数据"""
        default_data = {
            "name": "Test Template",
            "description": "Test description",
            "content": "Hello {{name}}",
            "template_type": "report",
            "variables": {"name": "string"}
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_data_source_data(**kwargs):
        """创建数据源测试数据"""
        default_data = {
            "name": "Test DataSource",
            "source_type": "postgresql",
            "connection_string": "postgresql://test:test@localhost:5432/testdb",
            "is_active": True
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_task_data(**kwargs):
        """创建任务测试数据"""
        default_data = {
            "name": "Test Task",
            "description": "Test task description",
            "status": "pending",
            "task_type": "generate_report"
        }
        default_data.update(kwargs)
        return default_data


@pytest.fixture
def test_data_factory():
    """提供测试数据工厂"""
    return TestDataFactory


# 测试环境清理
@pytest.fixture(autouse=True)
def cleanup_test_files():
    """自动清理测试文件"""
    yield
    # 清理测试过程中创建的临时文件
    import shutil
    import tempfile
    test_dirs = [
        "/tmp/test_reports",
        "/tmp/test_templates", 
        "/tmp/test_uploads"
    ]
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir, ignore_errors=True)


# 性能测试helpers
@pytest.fixture
def performance_monitor():
    """性能监控工具"""
    import time
    import psutil
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            
        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.Process().memory_info().rss
            
        def stop(self):
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            return {
                "duration": end_time - self.start_time if self.start_time else 0,
                "memory_used": end_memory - self.start_memory if self.start_memory else 0
            }
    
    return PerformanceMonitor()


# 异步测试配置
pytest_plugins = ["pytest_asyncio"]