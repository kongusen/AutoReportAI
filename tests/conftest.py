"""
AutoReportAI pytest配置文件
提供测试通用的fixtures和配置
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

# 测试环境变量
TEST_ENV_VARS = {
    "ENVIRONMENT": "test",
    "DEBUG": "true", 
    "DATABASE_URL": "postgresql://postgres:postgres123@localhost:5432/autoreport_test",
    "REDIS_URL": "redis://localhost:6379/15",  # 使用不同的Redis DB
    "MINIO_ENDPOINT": "localhost:9000",
    "MINIO_ACCESS_KEY": "minioadmin",
    "MINIO_SECRET_KEY": "minioadmin123",
    "MINIO_BUCKET_NAME": "test-bucket",
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "OPENAI_API_KEY": "test-openai-key",
    "DEFAULT_LLM_PROVIDER": "mock"
}

@pytest.fixture(scope="session")
def event_loop():
    """创建用于整个测试会话的事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """设置测试环境变量"""
    original_env = {}
    
    # 保存原始环境变量并设置测试环境变量
    for key, value in TEST_ENV_VARS.items():
        original_env[key] = os.getenv(key)
        os.environ[key] = value
    
    yield
    
    # 恢复原始环境变量
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

@pytest.fixture(scope="function")
def mock_openai_client():
    """模拟OpenAI客户端"""
    class MockOpenAIClient:
        def __init__(self):
            self.completions = MockCompletions()
        
        class MockCompletions:
            def create(self, **kwargs):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "这是测试响应"
                            }
                        }
                    ]
                }
    
    return MockOpenAIClient()

@pytest.fixture(scope="function") 
def sample_data():
    """提供测试样例数据"""
    return {
        "chart_data": {
            "title": "测试图表",
            "x_data": ["北京", "上海", "深圳", "广州"],
            "y_data": [100, 200, 150, 180],
            "x_label": "城市",
            "y_label": "数值"
        },
        "template_data": {
            "name": "测试模板",
            "content": "这是一个测试模板: {placeholder}",
            "variables": ["placeholder"]
        },
        "datasource_data": {
            "name": "测试数据源", 
            "source_type": "doris",
            "doris_fe_hosts": ["localhost"],
            "doris_username": "root",
            "doris_database": "test"
        }
    }

@pytest.fixture(scope="session")
def test_files_dir():
    """返回测试文件目录路径"""
    return ROOT_DIR / "tests" / "fixtures"

@pytest.fixture(scope="function")
def temp_storage_dir(tmp_path):
    """创建临时存储目录"""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    (storage_dir / "charts").mkdir()
    (storage_dir / "reports").mkdir()
    (storage_dir / "uploads").mkdir()
    return storage_dir

# 跳过条件
skip_if_no_docker = pytest.mark.skipif(
    os.system("docker --version") != 0,
    reason="Docker不可用"
)

skip_if_no_minio = pytest.mark.skipif(
    os.system("curl -s http://localhost:9000/minio/health/live") != 0,
    reason="Minio服务不可用"
)

skip_if_no_db = pytest.mark.skipif(
    os.system("pg_isready -h localhost -p 5432") != 0,
    reason="PostgreSQL数据库不可用"
)

skip_if_no_redis = pytest.mark.skipif(
    os.system("redis-cli -p 6379 ping") != 0,
    reason="Redis服务不可用"
)

# 测试分类标记
pytest_plugins = []

def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "e2e: 端到端测试" 
    )
    config.addinivalue_line(
        "markers", "agent: React Agent测试"
    )
    config.addinivalue_line(
        "markers", "charts: 图表生成测试"
    )
    config.addinivalue_line(
        "markers", "docker: Docker环境测试"
    )
    config.addinivalue_line(
        "markers", "minio: Minio存储测试"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试"
    )
    config.addinivalue_line(
        "markers", "network: 需要网络连接的测试"
    )