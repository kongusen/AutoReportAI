"""
模板API端点测试
"""

import pytest
import json
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app.models.template import Template
from app.models.user import User


@pytest.mark.api
class TestTemplateEndpoints:
    """测试模板API端点"""
    
    def test_get_templates(self, client: TestClient, auth_headers: dict, test_template: Template):
        """测试获取模板列表"""
        response = client.get("/api/v1/templates", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # 检查返回的模板数据结构
        template_data = data[0]
        required_fields = ["id", "name", "template_type", "created_at"]
        for field in required_fields:
            assert field in template_data
    
    def test_get_templates_unauthorized(self, client: TestClient):
        """测试未授权获取模板列表"""
        response = client.get("/api/v1/templates")
        assert response.status_code == 401
    
    def test_get_template_by_id(self, client: TestClient, auth_headers: dict, test_template: Template):
        """测试根据ID获取模板"""
        response = client.get(f"/api/v1/templates/{test_template.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_template.id
        assert data["name"] == test_template.name
        assert data["content"] == test_template.content
        assert data["template_type"] == test_template.template_type
    
    def test_get_nonexistent_template(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的模板"""
        response = client.get("/api/v1/templates/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_create_template(self, client: TestClient, auth_headers: dict):
        """测试创建模板"""
        template_data = {
            "name": "API Test Template",
            "description": "Created via API test",
            "content": "Hello {{user_name}}",
            "template_type": "report",
            "variables": {"user_name": "string"}
        }
        
        response = client.post("/api/v1/templates", json=template_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Template"
        assert data["description"] == "Created via API test"
        assert data["content"] == "Hello {{user_name}}"
        assert data["template_type"] == "report"
        assert data["variables"] == {"user_name": "string"}
        assert "id" in data
        assert "owner_id" in data
    
    def test_create_template_invalid_data(self, client: TestClient, auth_headers: dict):
        """测试创建无效模板"""
        invalid_data = {
            "name": "",  # 空名称
            "content": "Test content",
            "template_type": "invalid_type"  # 无效类型
        }
        
        response = client.post("/api/v1/templates", json=invalid_data, headers=auth_headers)
        assert response.status_code == 422  # 验证错误
    
    def test_update_template(self, client: TestClient, auth_headers: dict, test_template: Template):
        """测试更新模板"""
        update_data = {
            "name": "Updated Template Name",
            "description": "Updated description",
            "content": "Updated content {{new_var}}",
            "variables": {"new_var": "string"}
        }
        
        response = client.put(
            f"/api/v1/templates/{test_template.id}", 
            json=update_data, 
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Template Name"
        assert data["description"] == "Updated description"
        assert data["content"] == "Updated content {{new_var}}"
        assert data["variables"] == {"new_var": "string"}
    
    def test_update_nonexistent_template(self, client: TestClient, auth_headers: dict):
        """测试更新不存在的模板"""
        update_data = {"name": "Updated Name"}
        
        response = client.put("/api/v1/templates/99999", json=update_data, headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_template(self, client: TestClient, auth_headers: dict, test_template: Template):
        """测试删除模板"""
        template_id = test_template.id
        
        response = client.delete(f"/api/v1/templates/{template_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # 验证模板已被删除
        get_response = client.get(f"/api/v1/templates/{template_id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_template(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的模板"""
        response = client.delete("/api/v1/templates/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_template_search(self, client: TestClient, auth_headers: dict, test_user: User):
        """测试模板搜索"""
        # 创建测试模板
        search_templates = [
            {"name": "Python Report", "content": "Python analysis"},
            {"name": "Sales Dashboard", "content": "Sales data"},
            {"name": "Python Chart", "content": "Python visualization"}
        ]
        
        created_ids = []
        for template_data in search_templates:
            template_data.update({
                "template_type": "report"
            })
            response = client.post("/api/v1/templates", json=template_data, headers=auth_headers)
            assert response.status_code == 201
            created_ids.append(response.json()["id"])
        
        # 搜索Python相关模板
        response = client.get("/api/v1/templates?search=Python", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        python_templates = [t for t in data if "Python" in t["name"]]
        assert len(python_templates) == 2
    
    def test_template_filter_by_type(self, client: TestClient, auth_headers: dict):
        """测试按类型过滤模板"""
        # 创建不同类型的模板
        template_types = ["report", "email", "dashboard"]
        
        for template_type in template_types:
            template_data = {
                "name": f"Test {template_type} Template",
                "content": "Test content",
                "template_type": template_type
            }
            response = client.post("/api/v1/templates", json=template_data, headers=auth_headers)
            assert response.status_code == 201
        
        # 按类型过滤
        response = client.get("/api/v1/templates?template_type=report", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        for template in data:
            if template["name"].startswith("Test"):
                assert template["template_type"] == "report"
    
    def test_template_pagination(self, client: TestClient, auth_headers: dict):
        """测试模板分页"""
        # 创建多个模板用于分页测试
        for i in range(25):
            template_data = {
                "name": f"Pagination Template {i}",
                "content": f"Content {i}",
                "template_type": "report"
            }
            response = client.post("/api/v1/templates", json=template_data, headers=auth_headers)
            assert response.status_code == 201
        
        # 测试第一页
        response = client.get("/api/v1/templates?skip=0&limit=10", headers=auth_headers)
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1) == 10
        
        # 测试第二页
        response = client.get("/api/v1/templates?skip=10&limit=10", headers=auth_headers)
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2) == 10
        
        # 验证不重复
        page1_ids = {t["id"] for t in page1}
        page2_ids = {t["id"] for t in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0


@pytest.mark.api
@pytest.mark.integration
class TestTemplatePermissions:
    """测试模板权限控制"""
    
    async def test_user_can_only_access_own_templates(
        self, 
        async_client: AsyncClient, 
        db_session, 
        test_user: User
    ):
        """测试用户只能访问自己的模板"""
        from app.crud.crud_user import crud_user
        from app.schemas.user import UserCreate
        from app.core.security import create_access_token
        
        # 创建另一个用户
        other_user_data = UserCreate(
            username="otheruser",
            email="other@example.com",
            password="otherpassword123"
        )
        other_user = await crud_user.create(db_session, obj_in=other_user_data)
        await db_session.commit()
        
        # 为另一个用户创建模板
        from app.crud.crud_template import crud_template
        from app.schemas.template import TemplateCreate
        
        other_template_data = TemplateCreate(
            name="Other User Template",
            content="Private content",
            template_type="report"
        )
        other_template = await crud_template.create_with_owner(
            db_session, obj_in=other_template_data, owner_id=other_user.id
        )
        await db_session.commit()
        
        # 第一个用户尝试访问另一个用户的模板
        user1_token = create_access_token(subject=str(test_user.id))
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        
        response = await async_client.get(
            f"/api/v1/templates/{other_template.id}", 
            headers=user1_headers
        )
        
        # 应该返回404（找不到）或403（无权限）
        assert response.status_code in [403, 404]
    
    async def test_admin_can_access_all_templates(
        self, 
        async_client: AsyncClient, 
        admin_headers: dict, 
        test_template: Template
    ):
        """测试管理员可以访问所有模板"""
        response = await async_client.get(
            f"/api/v1/templates/{test_template.id}", 
            headers=admin_headers
        )
        
        # 管理员应该能访问任何模板
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_template.id