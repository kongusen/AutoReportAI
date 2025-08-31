"""
核心配置测试
"""

import pytest
import os
from unittest.mock import patch
from app.core.config import Settings, get_settings


@pytest.mark.unit
class TestSettings:
    """测试应用配置"""
    
    def test_default_settings(self):
        """测试默认配置"""
        settings = Settings()
        assert settings.PROJECT_NAME == "AutoReportAI"
        assert settings.API_V1_STR == "/api/v1"
        assert settings.BACKEND_CORS_ORIGINS is not None
    
    def test_database_url_validation(self):
        """测试数据库URL验证"""
        with patch.dict(os.environ, {"DATABASE_URL": "invalid_url"}):
            settings = Settings()
            # 应该有默认的fallback或验证
            assert settings.DATABASE_URL is not None
    
    def test_redis_url_validation(self):
        """测试Redis URL验证"""
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379/0"}):
            settings = Settings()
            assert "redis://" in settings.REDIS_URL
    
    def test_secret_key_generation(self):
        """测试密钥生成"""
        settings = Settings()
        assert len(settings.SECRET_KEY) > 10
        assert settings.SECRET_KEY != ""
    
    def test_cors_origins_parsing(self):
        """测试CORS源配置解析"""
        with patch.dict(os.environ, {"BACKEND_CORS_ORIGINS": "http://localhost:3000,https://example.com"}):
            settings = Settings()
            assert len(settings.BACKEND_CORS_ORIGINS) == 2
            assert "http://localhost:3000" in settings.BACKEND_CORS_ORIGINS
    
    def test_environment_override(self):
        """测试环境变量覆盖"""
        with patch.dict(os.environ, {
            "PROJECT_NAME": "CustomProject",
            "DEBUG": "true"
        }):
            settings = Settings()
            assert settings.PROJECT_NAME == "CustomProject"


@pytest.mark.unit
class TestGetSettings:
    """测试配置获取函数"""
    
    def test_settings_singleton(self):
        """测试配置单例模式"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
    
    def test_settings_caching(self):
        """测试配置缓存"""
        with patch('app.core.config.Settings') as mock_settings:
            mock_settings.return_value = Settings()
            
            # 第一次调用
            get_settings()
            # 第二次调用应该使用缓存
            get_settings()
            
            # Settings只应该被实例化一次
            assert mock_settings.call_count == 1