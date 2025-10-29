"""
测试 Schema Discovery 数据格式转换修复
验证 QueryResult -> 字典列表的正确转换
"""

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Any, Dict, List


# 模拟 QueryResult
@dataclass
class MockQueryResult:
    """模拟 QueryResult 对象"""
    data: pd.DataFrame
    execution_time: float
    success: bool
    error_message: str = None
    metadata: Dict[str, Any] = None


class TestContainerDataSourceAdapter:
    """测试 Container.DataSourceAdapter.run_query() 的数据格式转换"""

    @pytest.mark.asyncio
    async def test_query_result_with_dataframe_conversion(self):
        """测试 QueryResult 对象中的 DataFrame 正确转换为字典列表"""
        from app.core.container import DataSourceAdapter

        # 创建测试用的 DataFrame
        test_data = pd.DataFrame({
            'Name': ['test_table1', 'test_table2'],
            'Rows': [100, 200],
            'Data_length': [1024, 2048]
        })

        # 模拟 QueryResult
        mock_query_result = MockQueryResult(
            data=test_data,
            execution_time=0.1,
            success=True
        )

        # 模拟 connector.execute_query 返回 QueryResult
        mock_connector = AsyncMock()
        mock_connector.execute_query = AsyncMock(return_value=mock_query_result)
        mock_connector.__aenter__ = AsyncMock(return_value=mock_connector)
        mock_connector.__aexit__ = AsyncMock(return_value=None)

        # 修复：在方法内部导入，所以需要 patch 正确的路径
        with patch('app.services.data.connectors.create_connector_from_config', return_value=mock_connector):
            adapter = DataSourceAdapter()

            connection_config = {
                "source_type": "sql",
                "type": "mysql",
                "name": "test_db"
            }

            result = await adapter.run_query(connection_config, "SHOW TABLES")

            # 验证返回格式
            assert result["success"] is True
            assert "rows" in result
            assert "columns" in result

            # 验证 rows 是字典列表
            rows = result["rows"]
            assert isinstance(rows, list), f"rows 应该是列表，但是: {type(rows)}"
            assert len(rows) == 2, f"应该有 2 行数据，但是: {len(rows)}"

            # 验证每一行都是字典
            for idx, row in enumerate(rows):
                assert isinstance(row, dict), f"row[{idx}] 应该是字典，但是: {type(row)}"

            # 验证数据内容
            assert rows[0]['Name'] == 'test_table1'
            assert rows[0]['Rows'] == 100
            assert rows[1]['Name'] == 'test_table2'
            assert rows[1]['Rows'] == 200

    @pytest.mark.asyncio
    async def test_empty_dataframe_returns_empty_list(self):
        """测试空 DataFrame 返回空列表"""
        from app.core.container import DataSourceAdapter

        # 创建空 DataFrame
        empty_df = pd.DataFrame()

        # 模拟 QueryResult
        mock_query_result = MockQueryResult(
            data=empty_df,
            execution_time=0.1,
            success=True
        )

        # 模拟 connector
        mock_connector = AsyncMock()
        mock_connector.execute_query = AsyncMock(return_value=mock_query_result)
        mock_connector.__aenter__ = AsyncMock(return_value=mock_connector)
        mock_connector.__aexit__ = AsyncMock(return_value=None)

        # 修复：在方法内部导入，所以需要 patch 正确的路径
        with patch('app.services.data.connectors.create_connector_from_config', return_value=mock_connector):
            adapter = DataSourceAdapter()

            connection_config = {
                "source_type": "sql",
                "type": "mysql",
                "name": "test_db"
            }

            result = await adapter.run_query(connection_config, "SHOW TABLES")

            assert result["success"] is True
            assert result["rows"] == []
            assert result["columns"] == []


class TestSchemaDiscoveryTool:
    """测试 SchemaDiscoveryTool 的容错性"""

    @pytest.mark.asyncio
    async def test_get_table_details_with_valid_data(self):
        """测试使用有效数据获取表详情"""
        from app.services.infrastructure.agents.tools.schema.discovery import SchemaDiscoveryTool
        from types import SimpleNamespace

        # 创建模拟容器
        mock_container = SimpleNamespace()

        # 创建模拟数据源服务
        mock_data_source = AsyncMock()
        mock_data_source.run_query = AsyncMock(return_value={
            "success": True,
            "rows": [{
                "Name": "test_table",
                "Rows": 1000,
                "Data_length": 8192,
                "Create_time": "2024-01-01 00:00:00",
                "Update_time": "2024-01-02 00:00:00",
                "Comment": "Test table"
            }]
        })

        mock_container.data_source = mock_data_source

        # 创建工具
        tool = SchemaDiscoveryTool(mock_container)

        # 测试获取表详情
        result = await tool._get_table_details(
            mock_data_source,
            {"source_type": "sql"},
            "test_table"
        )

        # 验证结果
        assert result["name"] == "test_table"
        assert result["row_count"] == 1000
        assert result["size_bytes"] == 8192
        assert result["description"] == "Test table"

    @pytest.mark.asyncio
    async def test_get_table_details_with_invalid_data_format(self):
        """测试数据格式错误时的容错处理"""
        from app.services.infrastructure.agents.tools.schema.discovery import SchemaDiscoveryTool
        from types import SimpleNamespace

        mock_container = SimpleNamespace()

        # 创建返回非字典行的模拟服务
        mock_data_source = AsyncMock()
        mock_data_source.run_query = AsyncMock(return_value={
            "success": True,
            "rows": [["test_table", 1000, 8192]]  # ❌ 错误：列表而不是字典
        })

        mock_container.data_source = mock_data_source

        tool = SchemaDiscoveryTool(mock_container)

        # 应该返回基本的 table_info，不会崩溃
        result = await tool._get_table_details(
            mock_data_source,
            {"source_type": "sql"},
            "test_table"
        )

        # 验证返回了基本信息
        assert result["name"] == "test_table"
        assert result["row_count"] is None  # 因为数据格式错误，这些字段应该是 None
        assert result["size_bytes"] is None

    @pytest.mark.asyncio
    async def test_get_table_columns_with_valid_data(self):
        """测试使用有效数据获取列信息"""
        from app.services.infrastructure.agents.tools.schema.discovery import SchemaDiscoveryTool
        from types import SimpleNamespace

        mock_container = SimpleNamespace()

        mock_data_source = AsyncMock()
        mock_data_source.run_query = AsyncMock(return_value={
            "success": True,
            "rows": [
                {
                    "Field": "id",
                    "Type": "int(11)",
                    "Null": "NO",
                    "Key": "PRI",
                    "Default": None,
                    "Comment": "Primary key"
                },
                {
                    "Field": "name",
                    "Type": "varchar(255)",
                    "Null": "YES",
                    "Key": "",
                    "Default": None,
                    "Comment": "Name field"
                }
            ]
        })

        mock_container.data_source = mock_data_source

        tool = SchemaDiscoveryTool(mock_container)

        # 测试获取列信息
        result = await tool._get_table_columns(
            mock_data_source,
            {"source_type": "sql"},
            "test_table",
            include_metadata=True
        )

        # 验证结果
        assert len(result) == 2
        assert result[0]["name"] == "id"
        assert result[0]["data_type"] == "int(11)"
        assert result[0]["is_primary_key"] is True
        assert result[1]["name"] == "name"
        assert result[1]["nullable"] is True

    @pytest.mark.asyncio
    async def test_extract_table_name_from_dict(self):
        """测试从字典中提取表名"""
        from app.services.infrastructure.agents.tools.schema.discovery import SchemaDiscoveryTool
        from types import SimpleNamespace

        mock_container = SimpleNamespace()
        tool = SchemaDiscoveryTool(mock_container)

        # 测试标准字典格式
        row1 = {"Tables_in_test_db": "test_table"}
        assert tool._extract_table_name(row1) == "test_table"

        # 测试其他键名
        row2 = {"table_name": "another_table"}
        assert tool._extract_table_name(row2) == "another_table"

        # 测试列表格式
        row3 = ["list_table"]
        assert tool._extract_table_name(row3) == "list_table"

        # 测试字符串格式
        row4 = "string_table"
        assert tool._extract_table_name(row4) == "string_table"


class TestDataFormatValidation:
    """测试数据格式验证逻辑"""

    def test_dataframe_to_dict_conversion(self):
        """测试 DataFrame 到字典列表的转换"""
        # 创建测试 DataFrame
        df = pd.DataFrame({
            'Name': ['table1', 'table2'],
            'Rows': [100, 200],
            'Comment': ['Test 1', 'Test 2']
        })

        # 转换为字典列表
        rows = df.to_dict('records')

        # 验证
        assert isinstance(rows, list)
        assert len(rows) == 2
        assert all(isinstance(row, dict) for row in rows)
        assert rows[0]['Name'] == 'table1'
        assert rows[0]['Rows'] == 100

    def test_dict_update_with_valid_data(self):
        """测试字典 update 操作"""
        table_info = {
            "name": "test_table",
            "row_count": None,
            "size_bytes": None
        }

        # 模拟从 SHOW TABLE STATUS 返回的数据
        row = {
            "Rows": 1000,
            "Data_length": 8192,
            "Comment": "Test"
        }

        # update 操作
        update_data = {
            "row_count": row.get("Rows"),
            "size_bytes": row.get("Data_length"),
            "description": row.get("Comment", "")
        }

        table_info.update(update_data)

        # 验证
        assert table_info["row_count"] == 1000
        assert table_info["size_bytes"] == 8192
        assert table_info["description"] == "Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
