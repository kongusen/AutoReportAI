import pytest

from app.services.infrastructure.agents.tools.schema_tools import SchemaGetColumnsTool


class _StubDataSource:
    def __init__(self):
        self.calls = []

    async def run_query(self, connection_config, sql, limit=1000):
        self.calls.append({"config": connection_config, "sql": sql, "limit": limit})
        # 返回模拟的SHOW FULL COLUMNS结果
        return {
            "success": True,
            "rows": [
                {
                    "Field": "id",
                    "Type": "INT",
                    "Null": "NO",
                    "Key": "PRI",
                    "Default": None,
                    "Extra": "",
                    "Comment": "标识",
                },
                {
                    "Field": "amount",
                    "Type": "DECIMAL(10,2)",
                    "Null": "YES",
                    "Key": "",
                    "Default": None,
                    "Extra": "",
                    "Comment": "金额",
                },
            ],
        }


class _StubUserDataSourceService:
    def __init__(self, config):
        self._config = config
        self.calls = []

    async def get_user_data_source(self, user_id, data_source_id):
        self.calls.append({"user_id": user_id, "data_source_id": data_source_id})

        class _DS:
            def __init__(self, connection_config):
                self.connection_config = connection_config

        return _DS(self._config)


class _StubContainer:
    def __init__(self, connection_config=None):
        self.data_source = _StubDataSource()
        self._fetched_config = connection_config or {}
        self.user_data_source_service = _StubUserDataSourceService(self._fetched_config)


@pytest.mark.asyncio
async def test_schema_get_columns_with_ready_connection_config():
    container = _StubContainer()
    tool = SchemaGetColumnsTool(container)

    result = await tool.execute(
        {
            "tables": ["orders"],
            "data_source": {
                "source_type": "sql",
                "connection_string": "sqlite:///:memory:",
                "database": "demo",
            },
        }
    )

    assert result["success"] is True
    assert result["columns"]["orders"] == ["id", "amount"]
    assert container.data_source.calls[0]["config"]["source_type"] == "sql"
    assert "SHOW FULL COLUMNS FROM orders" in container.data_source.calls[0]["sql"]


@pytest.mark.asyncio
async def test_schema_get_columns_auto_loads_connection_config_when_missing():
    fetched_config = {
        "source_type": "sql",
        "connection_string": "postgresql://user:pwd@localhost:5432/postgres",
        "database": "primary_db",
    }
    container = _StubContainer(connection_config=fetched_config)
    tool = SchemaGetColumnsTool(container)

    result = await tool.execute(
        {
            "tables": ["sales"],
            "data_source": {
                "id": "ds-123",
                "database": "override_db",
            },
            "user_id": "user-42",
        }
    )

    assert result["success"] is True
    assert result["columns"]["sales"] == ["id", "amount"]

    call = container.data_source.calls[0]
    assert call["config"]["source_type"] == "sql"
    assert call["config"]["database"] == "override_db"
    assert "SHOW FULL COLUMNS FROM sales" in call["sql"]

    fetch_call = container.user_data_source_service.calls[0]
    assert fetch_call == {"user_id": "user-42", "data_source_id": "ds-123"}
