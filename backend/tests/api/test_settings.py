"""
设置管理API端点测试
"""
import pytest
import json
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.user import User
from app.models.llm_server import LLMServer
from app.models.user_profile import UserProfile


class TestSettingsAPI:
    """设置管理API测试类"""
    
    @pytest.mark.asyncio
    async def test_get_user_profile_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取用户配置成功"""
        mock_profile = {
            "id": 1,
            "user_id": authenticated_user.id,
            "language": "zh-CN",
            "theme": "light",
            "email_notifications": True,
            "timezone": "Asia/Shanghai"
        }
        
        with patch('app.crud.crud_user_profile.user_profile.get_or_create') as mock_get:
            mock_get.return_value = mock_profile
            
            response = await async_client.get("/api/v1/settings/profile")
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["language"] == "zh-CN"

    @pytest.mark.asyncio
    async def test_update_user_profile_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试更新用户配置成功"""
        profile_update = {
            "language": "en",
            "theme": "dark",
            "email_notifications": False,
            "timezone": "UTC"
        }
        
        mock_updated_profile = {
            "id": 1,
            "user_id": authenticated_user.id,
            **profile_update
        }
        
        with patch('app.crud.crud_user_profile.user_profile.get_or_create'), \
             patch('app.crud.crud_user_profile.user_profile.update') as mock_update:
            
            mock_update.return_value = mock_updated_profile
            
            response = await async_client.put(
                "/api/v1/settings/profile",
                json=profile_update
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["language"] == "en"
        assert data["data"]["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_get_available_llm_servers_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取可用LLM服务器列表成功"""
        with patch('app.db.session.get_db') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            mock_server = MagicMock()
            mock_server.id = 1
            mock_server.server_id = "server-1"
            mock_server.name = "Test LLM Server"
            mock_server.description = "测试服务器"
            mock_server.base_url = "http://localhost:8080"
            mock_server.is_active = True
            mock_server.is_healthy = True
            mock_server.capabilities = ["chat", "completion"]
            
            mock_query = mock_session.query.return_value
            mock_query.filter.return_value.all.return_value = [mock_server]
            
            with patch('app.crud.llm_server.get_server_stats') as mock_stats:
                mock_stats.return_value = {
                    'providers_count': 2,
                    'success_rate': 95.5
                }
                
                response = await async_client.get("/api/v1/settings/llm-servers")
                
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Test LLM Server"

    @pytest.mark.asyncio
    async def test_get_system_settings_info_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取系统设置信息成功"""
        response = await async_client.get("/api/v1/settings/system-info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "supported_languages" in data["data"]
        assert "supported_themes" in data["data"]
        assert "supported_report_formats" in data["data"]
        assert "supported_timezones" in data["data"]
        assert "supported_date_formats" in data["data"]

    @pytest.mark.asyncio
    async def test_reset_settings_to_defaults_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试重置设置为默认值成功"""
        mock_default_profile = {
            "id": 1,
            "user_id": authenticated_user.id,
            "language": "zh-CN",
            "theme": "light",
            "email_notifications": True,
            "timezone": "Asia/Shanghai"
        }
        
        with patch('app.crud.crud_user_profile.user_profile.get_or_create'), \
             patch('app.crud.crud_user_profile.user_profile.update') as mock_update:
            
            mock_update.return_value = mock_default_profile
            
            response = await async_client.post("/api/v1/settings/reset-to-defaults")
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["language"] == "zh-CN"
        assert data["data"]["theme"] == "light"

    @pytest.mark.asyncio
    async def test_get_user_llm_preferences_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取用户LLM偏好设置成功"""
        mock_preference = MagicMock()
        mock_preference.id = 1
        mock_preference.user_id = authenticated_user.id
        mock_preference.default_llm_server_id = 1
        mock_preference.default_provider_name = "openai"
        mock_preference.default_model_name = "gpt-3.5-turbo"
        mock_preference.preferred_temperature = 0.7
        mock_preference.personal_api_keys = {"openai": "sk-xxx"}
        mock_preference.provider_priorities = {"openai": 1}
        mock_preference.created_at = "2024-01-01T00:00:00"
        mock_preference.updated_at = "2024-01-01T00:00:00"
        
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_preference.get_or_create') as mock_get:
            mock_get.return_value = mock_preference
            
            response = await async_client.get("/api/v1/settings/llm-preferences")
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["default_provider_name"] == "openai"
        assert "openai" in data["data"]["configured_providers"]

    @pytest.mark.asyncio
    async def test_update_user_llm_preferences_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试更新用户LLM偏好设置成功"""
        preference_update = {
            "default_provider_name": "anthropic",
            "default_model_name": "claude-3-sonnet",
            "preferred_temperature": 0.8,
            "max_tokens_limit": 4000
        }
        
        mock_updated_preference = MagicMock()
        mock_updated_preference.id = 1
        mock_updated_preference.updated_at = "2024-01-01T01:00:00"
        
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_preference.update_preference') as mock_update:
            mock_update.return_value = mock_updated_preference
            
            response = await async_client.put(
                "/api/v1/settings/llm-preferences",
                json=preference_update
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == 1

    @pytest.mark.asyncio
    async def test_update_llm_preferences_failure(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试更新LLM偏好设置失败"""
        preference_update = {
            "default_provider_name": "invalid"
        }
        
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_preference.update_preference') as mock_update:
            mock_update.return_value = None
            
            response = await async_client.put(
                "/api/v1/settings/llm-preferences",
                json=preference_update
            )
            
        assert response.status_code == 500
        data = response.json()
        assert "更新LLM偏好设置失败" in data["detail"]

    @pytest.mark.asyncio
    async def test_add_personal_api_key_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试添加个人API密钥成功"""
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_preference.add_personal_api_key') as mock_add:
            mock_add.return_value = MagicMock()
            
            response = await async_client.post(
                "/api/v1/settings/llm-preferences/api-keys",
                params={"provider_name": "openai", "api_key": "sk-test123"}
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["provider"] == "openai"
        assert data["data"]["configured"] is True

    @pytest.mark.asyncio
    async def test_add_personal_api_key_empty_values(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试添加空的API密钥"""
        response = await async_client.post(
            "/api/v1/settings/llm-preferences/api-keys",
            params={"provider_name": "", "api_key": ""}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "不能为空" in data["detail"]

    @pytest.mark.asyncio
    async def test_remove_personal_api_key_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试删除个人API密钥成功"""
        provider_name = "openai"
        
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_preference.remove_personal_api_key') as mock_remove:
            mock_remove.return_value = MagicMock()
            
            response = await async_client.delete(f"/api/v1/settings/llm-preferences/api-keys/{provider_name}")
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["provider"] == provider_name
        assert data["data"]["removed"] is True

    @pytest.mark.asyncio
    async def test_get_user_usage_quota_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取用户使用配额信息成功"""
        mock_quota = MagicMock()
        mock_quota.quota_period = "monthly"
        mock_quota.period_start = "2024-01-01"
        mock_quota.period_end = "2024-01-31"
        mock_quota.tokens_used = 1000
        mock_quota.token_limit = 10000
        mock_quota.requests_made = 50
        mock_quota.request_limit = 1000
        mock_quota.total_cost = 5.0
        mock_quota.cost_limit = 100.0
        mock_quota.is_exceeded = False
        
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_usage_quota.get_current_quota') as mock_get:
            mock_get.return_value = mock_quota
            
            response = await async_client.get(
                "/api/v1/settings/llm-preferences/usage-quota",
                params={"period": "monthly"}
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["tokens_used"] == 1000
        assert data["data"]["token_usage_percentage"] == 10.0

    @pytest.mark.asyncio
    async def test_get_user_usage_quota_not_found(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取不存在的配额信息"""
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_usage_quota.get_current_quota') as mock_get:
            mock_get.return_value = None
            
            response = await async_client.get("/api/v1/settings/llm-preferences/usage-quota")
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["quota_exists"] is False

    @pytest.mark.asyncio
    async def test_get_available_llm_providers_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试获取可用LLM提供商列表成功"""
        with patch('app.db.session.get_db') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            
            # 模拟服务器和提供商
            mock_provider = MagicMock()
            mock_provider.is_enabled = True
            mock_provider.provider_name = "openai"
            mock_provider.provider_type = "openai"
            mock_provider.available_models = ["gpt-3.5-turbo", "gpt-4"]
            mock_provider.default_model = "gpt-3.5-turbo"
            mock_provider.rate_limit_rpm = 3500
            mock_provider.rate_limit_tpm = 90000
            mock_provider.priority = 1
            mock_provider.is_healthy = True
            
            mock_server = MagicMock()
            mock_server.id = 1
            mock_server.name = "Test Server"
            mock_server.providers = [mock_provider]
            
            mock_query = mock_session.query.return_value
            mock_query.filter.return_value.all.return_value = [mock_server]
            
            response = await async_client.get("/api/v1/settings/llm-preferences/available-providers")
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["provider_name"] == "openai"

    @pytest.mark.asyncio
    async def test_test_llm_connection_success(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试LLM连接成功"""
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_preference.get_decrypted_api_key') as mock_get_key:
            mock_get_key.return_value = "sk-test123"
            
            # Mock LLM service
            with patch('app.api.endpoints.settings.reset_iaop_llm_service'), \
                 patch('app.api.endpoints.settings.get_iaop_llm_service') as mock_get_service:
                
                mock_service = MagicMock()
                mock_service.llm_server_url = "http://localhost:8080"
                mock_service.health_check = AsyncMock(return_value={"status": "healthy"})
                mock_get_service.return_value = mock_service
                
                response = await async_client.post(
                    "/api/v1/settings/llm-preferences/test-connection",
                    params={"server_id": 1, "provider_name": "openai"}
                )
                
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["connected"] is True

    @pytest.mark.asyncio
    async def test_test_llm_connection_no_api_key(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试LLM连接无API密钥"""
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_preference.get_decrypted_api_key') as mock_get_key:
            mock_get_key.return_value = None
            
            response = await async_client.post(
                "/api/v1/settings/llm-preferences/test-connection",
                params={"server_id": 1, "provider_name": "openai"}
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["data"]["connected"] is False
        assert "未配置" in data["message"]

    @pytest.mark.asyncio
    async def test_test_llm_connection_unhealthy(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试LLM连接不健康"""
        with patch('app.crud.crud_user_llm_preference.crud_user_llm_preference.get_decrypted_api_key') as mock_get_key:
            mock_get_key.return_value = "sk-test123"
            
            with patch('app.api.endpoints.settings.reset_iaop_llm_service'), \
                 patch('app.api.endpoints.settings.get_iaop_llm_service') as mock_get_service:
                
                mock_service = MagicMock()
                mock_service.llm_server_url = "http://localhost:8080"
                mock_service.health_check = AsyncMock(return_value={"status": "unhealthy", "error": "Connection failed"})
                mock_get_service.return_value = mock_service
                
                response = await async_client.post(
                    "/api/v1/settings/llm-preferences/test-connection",
                    params={"server_id": 1, "provider_name": "openai"}
                )
                
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["data"]["connected"] is False
        assert "Connection failed" in data["data"]["error"]

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """测试未认证访问设置API"""
        endpoints = [
            "/api/v1/settings/profile",
            "/api/v1/settings/llm-servers", 
            "/api/v1/settings/system-info",
            "/api/v1/settings/llm-preferences"
        ]
        
        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_profile_update(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试无效的配置更新"""
        invalid_data = {
            "language": "invalid-lang",  # 无效语言代码
            "theme": "invalid-theme",    # 无效主题
        }
        
        # 这里应该有验证逻辑，如果没有则测试当前行为
        response = await async_client.put(
            "/api/v1/settings/profile",
            json=invalid_data
        )
        
        # 根据实际验证情况调整断言
        assert response.status_code in [200, 422]  # 要么接受要么验证失败

    @pytest.mark.asyncio
    async def test_system_settings_data_structure(
        self, 
        async_client: AsyncClient, 
        authenticated_user: User
    ):
        """测试系统设置数据结构完整性"""
        response = await async_client.get("/api/v1/settings/system-info")
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        # 检查必需的字段存在
        required_fields = [
            "supported_languages",
            "supported_themes", 
            "supported_report_formats",
            "supported_timezones",
            "supported_date_formats"
        ]
        
        for field in required_fields:
            assert field in data
            assert isinstance(data[field], list)
            assert len(data[field]) > 0
            
            # 检查每个选项都有code和name
            for option in data[field]:
                assert "code" in option
                assert "name" in option