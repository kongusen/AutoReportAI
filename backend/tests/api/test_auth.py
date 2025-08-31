"""
认证API端点测试
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.api
@pytest.mark.auth
class TestAuthEndpoints:
    """测试认证API端点"""
    
    def test_register_user(self, client: TestClient):
        """测试用户注册"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "password" not in data  # 密码不应该返回
        assert "id" in data
    
    def test_register_duplicate_username(self, client: TestClient):
        """测试注册重复用户名"""
        user_data = {
            "username": "duplicate",
            "email": "user1@example.com", 
            "password": "password123"
        }
        
        # 第一次注册成功
        response1 = client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # 第二次注册相同用户名应该失败
        user_data["email"] = "user2@example.com"  # 不同邮箱
        response2 = client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 400
    
    def test_register_duplicate_email(self, client: TestClient):
        """测试注册重复邮箱"""
        user_data = {
            "username": "user1",
            "email": "duplicate@example.com",
            "password": "password123"
        }
        
        # 第一次注册成功
        response1 = client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # 第二次注册相同邮箱应该失败
        user_data["username"] = "user2"  # 不同用户名
        response2 = client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 400
    
    def test_register_invalid_email(self, client: TestClient):
        """测试注册无效邮箱"""
        user_data = {
            "username": "testuser",
            "email": "invalid_email",
            "password": "password123"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422  # 验证错误
    
    def test_register_weak_password(self, client: TestClient):
        """测试注册弱密码"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"  # 太短
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422  # 验证错误
    
    def test_login_success(self, client: TestClient, test_user):
        """测试登录成功"""
        login_data = {
            "username": test_user.username,
            "password": "testpassword123"  # 原始密码
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 50
    
    def test_login_wrong_username(self, client: TestClient):
        """测试错误用户名登录"""
        login_data = {
            "username": "nonexistentuser",
            "password": "anypassword"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
    
    def test_login_wrong_password(self, client: TestClient, test_user):
        """测试错误密码登录"""
        login_data = {
            "username": test_user.username,
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
    
    def test_login_inactive_user(self, client: TestClient, db_session: AsyncSession):
        """测试非活跃用户登录"""
        from app.crud.crud_user import crud_user
        from app.schemas.user import UserCreate, UserUpdate
        
        # 创建用户
        user_data = UserCreate(
            username="inactiveuser",
            email="inactive@example.com",
            password="password123"
        )
        user = await crud_user.create(db_session, obj_in=user_data)
        
        # 设为非活跃
        await crud_user.update(
            db_session, db_obj=user, obj_in=UserUpdate(is_active=False)
        )
        await db_session.commit()
        
        # 尝试登录
        login_data = {
            "username": "inactiveuser",
            "password": "password123"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 400  # 账户未激活
    
    def test_get_current_user(self, client: TestClient, auth_headers: dict):
        """测试获取当前用户信息"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "username" in data
        assert "email" in data
        assert "is_active" in data
        assert "password" not in data  # 密码不应该返回
    
    def test_get_current_user_without_token(self, client: TestClient):
        """测试无token获取当前用户"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """测试无效token获取当前用户"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
    
    def test_logout(self, client: TestClient, auth_headers: dict):
        """测试登出"""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("message") == "Successfully logged out" or "success" in data


@pytest.mark.api
@pytest.mark.auth
@pytest.mark.integration
class TestAuthIntegration:
    """测试认证集成功能"""
    
    async def test_full_auth_workflow(self, async_client: AsyncClient):
        """测试完整认证工作流"""
        # 1. 注册用户
        register_data = {
            "username": "workflowuser",
            "email": "workflow@example.com",
            "password": "workflowpassword123"
        }
        
        register_response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 201
        
        # 2. 登录获取token
        login_data = {
            "username": "workflowuser",
            "password": "workflowpassword123"
        }
        
        login_response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        access_token = token_data["access_token"]
        
        # 3. 使用token访问受保护资源
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        user_data = me_response.json()
        assert user_data["username"] == "workflowuser"
        assert user_data["email"] == "workflow@example.com"
    
    async def test_token_expiration_workflow(self, async_client: AsyncClient):
        """测试token过期工作流"""
        # 这个测试需要短期token设置，实际实现可能需要修改配置
        # 或者使用mock来模拟过期token
        pass  # 根据实际token过期策略实现
    
    async def test_protected_endpoint_access(self, async_client: AsyncClient, auth_headers: dict):
        """测试受保护端点访问"""
        # 测试需要认证的端点
        protected_endpoints = [
            ("/api/v1/templates", "GET"),
            ("/api/v1/data-sources", "GET"),
            ("/api/v1/tasks", "GET"),
        ]
        
        for endpoint, method in protected_endpoints:
            # 无token访问
            if method == "GET":
                response = await async_client.get(endpoint)
            else:
                response = await async_client.request(method, endpoint)
            
            assert response.status_code == 401  # 未认证
            
            # 有token访问
            if method == "GET":
                response = await async_client.get(endpoint, headers=auth_headers)
            else:
                response = await async_client.request(method, endpoint, headers=auth_headers)
            
            assert response.status_code in [200, 201, 204]  # 认证成功