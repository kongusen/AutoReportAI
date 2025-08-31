"""
数据源API端点测试
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app.models.data_source import DataSource
from app.models.user import User


@pytest.mark.api
class TestDataSourceEndpoints:
    """测试数据源API端点"""
    
    def test_get_data_sources(self, client: TestClient, auth_headers: dict, test_data_source: DataSource):
        """测试获取数据源列表"""
        response = client.get("/api/v1/data-sources", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # 检查数据源数据结构
        ds_data = data[0]
        required_fields = ["id", "name", "source_type", "is_active", "created_at"]
        for field in required_fields:
            assert field in ds_data
        
        # 敏感信息不应该返回
        assert "connection_string" not in ds_data or "password" not in ds_data.get("connection_string", "")
    
    def test_create_postgresql_data_source(self, client: TestClient, auth_headers: dict):
        """测试创建PostgreSQL数据源"""
        ds_data = {
            "name": "Test PostgreSQL",
            "description": "Test PostgreSQL database",
            "source_type": "postgresql",
            "connection_string": "postgresql://user:pass@localhost:5432/testdb",
            "is_active": True
        }
        
        response = client.post("/api/v1/data-sources", json=ds_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test PostgreSQL"
        assert data["source_type"] == "postgresql"
        assert data["is_active"] is True
        assert "id" in data
    
    def test_create_doris_data_source(self, client: TestClient, auth_headers: dict):
        """测试创建Doris数据源"""
        ds_data = {
            "name": "Test Doris",
            "description": "Test Doris database",
            "source_type": "doris",
            "doris_fe_hosts": ["192.168.1.100"],
            "doris_query_port": 9030,
            "doris_database": "test_db",
            "doris_username": "root",
            "doris_password": "password",
            "is_active": True
        }
        
        response = client.post("/api/v1/data-sources", json=ds_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Doris"
        assert data["source_type"] == "doris"
        assert data["doris_fe_hosts"] == ["192.168.1.100"]
        assert data["doris_query_port"] == 9030
    
    def test_create_invalid_data_source(self, client: TestClient, auth_headers: dict):
        """测试创建无效数据源"""
        invalid_data = {
            "name": "",  # 空名称
            "source_type": "invalid_type",  # 无效类型
        }
        
        response = client.post("/api/v1/data-sources", json=invalid_data, headers=auth_headers)
        assert response.status_code == 422  # 验证错误
    
    def test_test_data_source_connection(self, client: TestClient, auth_headers: dict, mock_data_connector):
        """测试数据源连接测试"""
        ds_data = {
            "name": "Test Connection DS",
            "source_type": "postgresql",
            "connection_string": "postgresql://user:pass@localhost:5432/testdb"
        }
        
        # 创建数据源
        create_response = client.post("/api/v1/data-sources", json=ds_data, headers=auth_headers)
        assert create_response.status_code == 201
        ds_id = create_response.json()["id"]
        
        # 测试连接
        with pytest.mock.patch('app.services.data.connectors.connector_factory.ConnectorFactory.get_connector') as mock_factory:
            mock_factory.return_value = mock_data_connector
            
            response = client.post(f"/api/v1/data-sources/{ds_id}/test", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["success"] is True
            assert "message" in data
    
    def test_get_data_source_schema(self, client: TestClient, auth_headers: dict, mock_data_connector):
        """测试获取数据源结构"""
        ds_data = {
            "name": "Schema Test DS",
            "source_type": "postgresql",
            "connection_string": "postgresql://user:pass@localhost:5432/testdb"
        }
        
        # 创建数据源
        create_response = client.post("/api/v1/data-sources", json=ds_data, headers=auth_headers)
        ds_id = create_response.json()["id"]
        
        # 获取结构
        with pytest.mock.patch('app.services.data.connectors.connector_factory.ConnectorFactory.get_connector') as mock_factory:
            mock_data_connector.get_schema.return_value = {
                "tables": ["users", "orders"],
                "views": ["user_stats"],
                "columns": {
                    "users": ["id", "name", "email"],
                    "orders": ["id", "user_id", "amount"]
                }
            }
            mock_factory.return_value = mock_data_connector
            
            response = client.get(f"/api/v1/data-sources/{ds_id}/schema", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "tables" in data
            assert "users" in data["tables"]
            assert "orders" in data["tables"]
    
    def test_update_data_source(self, client: TestClient, auth_headers: dict, test_data_source: DataSource):
        """测试更新数据源"""
        update_data = {
            "name": "Updated Data Source",
            "description": "Updated description",
            "is_active": False
        }
        
        response = client.put(
            f"/api/v1/data-sources/{test_data_source.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Data Source"
        assert data["description"] == "Updated description"
        assert data["is_active"] is False
    
    def test_delete_data_source(self, client: TestClient, auth_headers: dict, test_data_source: DataSource):
        """测试删除数据源"""
        ds_id = test_data_source.id
        
        response = client.delete(f"/api/v1/data-sources/{ds_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # 验证数据源已被删除
        get_response = client.get(f"/api/v1/data-sources/{ds_id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_data_source_unauthorized_access(self, client: TestClient, test_data_source: DataSource):
        """测试未授权访问数据源"""
        response = client.get("/api/v1/data-sources")
        assert response.status_code == 401
        
        response = client.get(f"/api/v1/data-sources/{test_data_source.id}")
        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.performance
class TestDataSourcePerformance:
    """测试数据源API性能"""
    
    async def test_bulk_data_source_creation_performance(
        self, 
        async_client: AsyncClient, 
        auth_headers: dict,
        performance_monitor
    ):
        """测试批量创建数据源的性能"""
        performance_monitor.start()
        
        # 创建100个数据源
        for i in range(100):
            ds_data = {
                "name": f"Performance Test DS {i}",
                "source_type": "postgresql",
                "connection_string": f"postgresql://user:pass@localhost:5432/db{i}",
                "is_active": True
            }
            
            response = await async_client.post("/api/v1/data-sources", json=ds_data, headers=auth_headers)
            assert response.status_code == 201
        
        stats = performance_monitor.stop()
        
        # 性能断言（可根据实际需求调整）
        assert stats["duration"] < 30.0  # 30秒内完成
        assert stats["memory_used"] < 100 * 1024 * 1024  # 内存增长不超过100MB
    
    @pytest.mark.slow
    async def test_data_source_list_performance_with_large_dataset(
        self, 
        async_client: AsyncClient, 
        auth_headers: dict,
        performance_monitor
    ):
        """测试大数据集下的数据源列表性能"""
        # 创建大量数据源（如果数据库中已有大量数据）
        performance_monitor.start()
        
        response = await async_client.get("/api/v1/data-sources", headers=auth_headers)
        
        stats = performance_monitor.stop()
        
        assert response.status_code == 200
        assert stats["duration"] < 2.0  # 2秒内返回结果