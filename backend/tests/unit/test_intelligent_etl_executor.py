"""
智能ETL执行器单元测试

测试动态查询生成、时间过滤、区域过滤、聚合计算和数据转换功能。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from app.models.enhanced_data_source import EnhancedDataSource, DataSourceType
from app.services.data_processing.etl.intelligent_etl_executor import (
    AggregationConfig,
    ETLInstructions,
    IntelligentETLExecutor,
    ProcessedData,
    RegionFilterConfig,
    TimeFilterConfig,
)


class TestIntelligentETLExecutor:
    """智能ETL执行器测试"""

    @pytest.fixture
    def executor(self):
        """创建ETL执行器实例"""
        return IntelligentETLExecutor()

    @pytest.fixture
    def sample_sql_data_source(self):
        """示例SQL数据源"""
        data_source = Mock(spec=EnhancedDataSource)
        data_source.id = 1
        data_source.source_type = Mock()
        data_source.source_type.value = "sql"
        data_source.connection_string = "postgresql://test:test@localhost/test"
        data_source.wide_table_name = "complaints"
        return data_source

    @pytest.fixture
    def sample_csv_data_source(self):
        """示例CSV数据源"""
        data_source = Mock(spec=EnhancedDataSource)
        data_source.id = 2
        data_source.source_type = Mock()
        data_source.source_type.value = "csv"
        data_source.file_path = "/path/to/data.csv"
        data_source.wide_table_name = None
        return data_source

    @pytest.fixture
    def sample_etl_instructions(self):
        """示例ETL指令"""
        return ETLInstructions(
            instruction_id="test_etl_001",
            query_type="select",
            source_fields=["complaint_count", "complaint_date", "region"],
            filters=[{"column": "status", "operator": "=", "value": "resolved"}],
            aggregations=[],
            transformations=[],
            time_config=TimeFilterConfig(
                field="complaint_date", period="monthly", relative_period="this_month"
            ),
            region_config=RegionFilterConfig(
                field="region", region_value="云南省", region_type="exact"
            ),
            output_format="dataframe",
        )

    @pytest.fixture
    def sample_aggregate_instructions(self):
        """示例聚合ETL指令"""
        return ETLInstructions(
            instruction_id="test_agg_001",
            query_type="aggregate",
            source_fields=["complaint_count"],
            filters=[],
            aggregations=[
                AggregationConfig(
                    function="sum",
                    field="complaint_count",
                    group_by=["region"],
                    having_condition="SUM(complaint_count) > 10",
                )
            ],
            transformations=[
                {"type": "cast", "field": "complaint_count", "target_type": "integer"}
            ],
            output_format="scalar",
        )

    @pytest.fixture
    def sample_dataframe(self):
        """示例数据框"""
        return pd.DataFrame(
            {
                "complaint_count": [10, 15, 8, 12, 20],
                "complaint_date": [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                ],
                "region": ["昆明市", "大理州", "丽江市", "昆明市", "大理州"],
                "status": ["resolved", "pending", "resolved", "resolved", "pending"],
            }
        )

    @pytest.mark.asyncio
    async def test_execute_etl_sql_success(
        self,
        executor,
        sample_etl_instructions,
        sample_sql_data_source,
        sample_dataframe,
    ):
        """测试SQL数据源ETL执行成功"""
        with (
            patch("app.services.intelligent_etl_executor.get_db") as mock_get_db,
            patch(
                "app.services.intelligent_etl_executor.crud_enhanced_data_source"
            ) as mock_crud,
            patch.object(
                executor, "_execute_query", return_value=sample_dataframe
            ) as mock_execute,
        ):

            # 模拟数据库查询
            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db
            mock_crud.get.return_value = sample_sql_data_source

            # 执行ETL
            result = await executor.execute_etl(
                sample_etl_instructions,
                data_source_id=1,
                task_config={
                    "time_range": {"start_date": "2024-01-01", "end_date": "2024-01-31"}
                },
            )

            # 验证结果
            assert isinstance(result, ProcessedData)
            assert result.rows_processed == 5
            assert result.confidence > 0
            assert result.processing_time > 0
            assert result.metadata["instruction_id"] == "test_etl_001"
            assert result.metadata["data_source_id"] == 1
            assert result.metadata["query_type"] == "select"

            # 验证查询被执行
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_etl_data_source_not_found(
        self, executor, sample_etl_instructions
    ):
        """测试数据源不存在的情况"""
        with (
            patch("app.services.intelligent_etl_executor.get_db") as mock_get_db,
            patch(
                "app.services.intelligent_etl_executor.crud_enhanced_data_source"
            ) as mock_crud,
        ):

            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db
            mock_crud.get.return_value = None  # 数据源不存在

            # 执行ETL
            result = await executor.execute_etl(
                sample_etl_instructions, data_source_id=999
            )

            # 验证错误处理
            assert result.processed_value is None
            assert result.confidence == 0.0
            assert "不存在" in result.metadata["error"]

    @pytest.mark.asyncio
    async def test_generate_sql_query_select(
        self, executor, sample_etl_instructions, sample_sql_data_source
    ):
        """测试生成SQL查询（SELECT）"""
        query = await executor._generate_sql_query(
            sample_etl_instructions,
            sample_sql_data_source,
            task_config={
                "time_range": {"start_date": "2024-01-01", "end_date": "2024-01-31"}
            },
        )

        # 验证查询结构
        assert "SELECT" in query
        assert "complaint_count" in query
        assert "complaint_date" in query
        assert "region" in query
        assert "FROM complaints" in query
        assert "WHERE" in query
        assert "status = 'resolved'" in query
        assert "complaint_date >= '2024-01-01'" in query
        assert "complaint_date <= '2024-01-31'" in query
        assert "region = '云南省'" in query

    @pytest.mark.asyncio
    async def test_generate_sql_query_aggregate(
        self, executor, sample_aggregate_instructions, sample_sql_data_source
    ):
        """测试生成SQL查询（聚合）"""
        query = await executor._generate_sql_query(
            sample_aggregate_instructions, sample_sql_data_source
        )

        # 验证聚合查询结构
        assert "SELECT" in query
        assert "SUM(complaint_count)" in query
        assert "region" in query  # GROUP BY字段
        assert "FROM complaints" in query
        assert "GROUP BY region" in query
        assert "HAVING SUM(complaint_count) > 10" in query

    @pytest.mark.asyncio
    async def test_generate_pandas_operations(
        self, executor, sample_etl_instructions, sample_csv_data_source
    ):
        """测试生成pandas操作"""
        operations = await executor._generate_pandas_operations(
            sample_etl_instructions, sample_csv_data_source
        )

        # 验证操作字符串
        assert "pd.read_csv" in operations
        assert "/path/to/data.csv" in operations
        assert "complaint_count" in operations
        assert "complaint_date" in operations
        assert "region" in operations

    def test_build_filter_condition(self, executor):
        """测试构建过滤条件"""
        test_cases = [
            (
                {"column": "status", "operator": "=", "value": "active"},
                "status = 'active'",
            ),
            ({"column": "count", "operator": ">", "value": "10"}, "count > '10'"),
            (
                {"column": "name", "operator": "LIKE", "value": "test"},
                "name LIKE '%test%'",
            ),
            (
                {"column": "type", "operator": "IN", "value": ["A", "B"]},
                "type IN ('A', 'B')",
            ),
            ({"column": "", "operator": "=", "value": "test"}, ""),  # 空列名
            ({"column": "test", "operator": "=", "value": ""}, ""),  # 空值
        ]

        for filter_config, expected in test_cases:
            result = executor._build_filter_condition(filter_config)
            assert result == expected

    @pytest.mark.asyncio
    async def test_build_time_filter(self, executor):
        """测试构建时间过滤条件"""
        time_config = TimeFilterConfig(
            field="created_at", start_date="2024-01-01", end_date="2024-01-31"
        )

        condition = await executor._build_time_filter(time_config)

        assert "created_at >= '2024-01-01'" in condition
        assert "created_at <= '2024-01-31'" in condition
        assert " AND " in condition

    @pytest.mark.asyncio
    async def test_build_time_filter_with_task_config(self, executor):
        """测试使用任务配置的时间过滤"""
        time_config = TimeFilterConfig(field="created_at")
        task_config = {
            "time_range": {"start_date": "2024-02-01", "end_date": "2024-02-29"}
        }

        condition = await executor._build_time_filter(time_config, task_config)

        assert "created_at >= '2024-02-01'" in condition
        assert "created_at <= '2024-02-29'" in condition

    @pytest.mark.asyncio
    async def test_build_region_filter(self, executor):
        """测试构建区域过滤条件"""
        region_config = RegionFilterConfig(
            field="region", region_value="云南省", region_type="exact"
        )

        condition = await executor._build_region_filter(region_config)
        assert condition == "region = '云南省'"

        # 测试包含匹配
        region_config.region_type = "contains"
        condition = await executor._build_region_filter(region_config)
        assert condition == "region LIKE '%云南省%'"

        # 测试开始匹配
        region_config.region_type = "starts_with"
        condition = await executor._build_region_filter(region_config)
        assert condition == "region LIKE '云南省%'"

    @pytest.mark.asyncio
    async def test_calculate_relative_period(self, executor):
        """测试计算相对时间周期"""
        # 测试上个月
        start_date, end_date = await executor._calculate_relative_period("last_month")
        assert isinstance(start_date, str)
        assert isinstance(end_date, str)
        assert len(start_date) == 10  # YYYY-MM-DD格式
        assert len(end_date) == 10

        # 测试本月
        start_date, end_date = await executor._calculate_relative_period("this_month")
        now = datetime.now()
        expected_start = f"{now.year}-{now.month:02d}-01"
        assert start_date == expected_start

        # 测试今年
        start_date, end_date = await executor._calculate_relative_period("this_year")
        now = datetime.now()
        assert start_date == f"{now.year}-01-01"
        assert end_date == f"{now.year}-12-31"

    def test_build_pandas_filter(self, executor):
        """测试构建pandas过滤条件"""
        test_cases = [
            (
                {"column": "status", "operator": "=", "value": "active"},
                "df['status'] == 'active'",
            ),
            ({"column": "count", "operator": ">", "value": "10"}, "df['count'] > '10'"),
            (
                {"column": "name", "operator": "LIKE", "value": "test"},
                "df['name'].str.contains('test')",
            ),
            (
                {"column": "type", "operator": "IN", "value": ["A", "B"]},
                "df['type'].isin(['A', 'B'])",
            ),
        ]

        for filter_config, expected in test_cases:
            result = executor._build_pandas_filter(filter_config)
            assert result == expected

    @pytest.mark.asyncio
    async def test_build_pandas_time_filter(self, executor):
        """测试构建pandas时间过滤"""
        time_config = TimeFilterConfig(
            field="date_column", start_date="2024-01-01", end_date="2024-01-31"
        )

        operations = await executor._build_pandas_time_filter(time_config)

        assert "pd.to_datetime(df['date_column'])" in operations
        assert "df['date_column'] >= '2024-01-01'" in operations
        assert "df['date_column'] <= '2024-01-31'" in operations

    @pytest.mark.asyncio
    async def test_execute_query_sql(self, executor, sample_sql_data_source):
        """测试执行SQL查询"""
        with (
            patch(
                "app.services.intelligent_etl_executor.create_engine"
            ) as mock_create_engine,
            patch("app.services.intelligent_etl_executor.pd.read_sql") as mock_read_sql,
        ):

            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine
            mock_read_sql.return_value = pd.DataFrame({"result": [42]})

            query = "SELECT COUNT(*) as result FROM complaints"
            result = await executor._execute_query(query, sample_sql_data_source)

            # 验证调用
            mock_create_engine.assert_called_once_with(
                sample_sql_data_source.connection_string
            )
            mock_read_sql.assert_called_once()
            assert isinstance(result, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_execute_pandas_operations(self, executor, sample_csv_data_source):
        """测试执行pandas操作"""
        operations = "df = pd.DataFrame({'test': [1, 2, 3]}); result = df['test'].sum()"

        result = await executor._execute_pandas_operations(
            operations, sample_csv_data_source
        )

        # 应该返回DataFrame格式的结果
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_apply_transformations(self, executor, sample_dataframe):
        """测试应用数据转换"""
        transformations = [
            {"type": "cast", "field": "complaint_count", "target_type": "integer"},
            {"type": "format", "field": "region", "pattern": "地区: {}"},
            {
                "type": "calculate",
                "formula": "complaint_count * 2",
                "target_field": "double_count",
            },
        ]

        result = await executor._apply_transformations(
            sample_dataframe.copy(), transformations
        )

        # 验证转换结果
        assert isinstance(result, pd.DataFrame)
        assert result["complaint_count"].dtype in ["int64", "Int64"]  # 类型转换
        assert "double_count" in result.columns  # 计算字段

    @pytest.mark.asyncio
    async def test_format_output_scalar(self, executor):
        """测试标量输出格式化"""
        # 单值DataFrame
        df = pd.DataFrame({"result": [42]})
        result = await executor._format_output(df, "scalar")
        assert result == 42

        # 多值DataFrame（取第一个值）
        df = pd.DataFrame({"result": [10, 20, 30]})
        result = await executor._format_output(df, "scalar")
        assert result == 10

    @pytest.mark.asyncio
    async def test_format_output_array(self, executor):
        """测试数组输出格式化"""
        # 单列DataFrame
        df = pd.DataFrame({"values": [1, 2, 3, 4, 5]})
        result = await executor._format_output(df, "array")
        assert result == [1, 2, 3, 4, 5]

        # 多列DataFrame
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = await executor._format_output(df, "array")
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_format_output_json(self, executor):
        """测试JSON输出格式化"""
        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [25, 30]})
        result = await executor._format_output(df, "json")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"name": "Alice", "age": 25}
        assert result[1] == {"name": "Bob", "age": 30}

    @pytest.mark.asyncio
    async def test_format_output_dataframe(self, executor, sample_dataframe):
        """测试DataFrame输出格式化"""
        result = await executor._format_output(sample_dataframe, "dataframe")
        assert isinstance(result, pd.DataFrame)
        assert result.equals(sample_dataframe)

    def test_calculate_confidence(
        self, executor, sample_etl_instructions, sample_dataframe
    ):
        """测试置信度计算"""
        # 正常数据
        confidence = executor._calculate_confidence(
            sample_etl_instructions, sample_dataframe, 42
        )
        assert 0.5 <= confidence <= 1.0

        # 空数据
        empty_df = pd.DataFrame()
        confidence = executor._calculate_confidence(
            sample_etl_instructions, empty_df, None
        )
        assert confidence < 0.5

        # 大量缺失数据
        missing_df = pd.DataFrame({"col1": [None, None, 1, None, None]})
        confidence = executor._calculate_confidence(
            sample_etl_instructions, missing_df, 1
        )
        assert confidence < 0.8

    @pytest.mark.asyncio
    async def test_complex_etl_workflow(self, executor, sample_sql_data_source):
        """测试复杂ETL工作流"""
        # 创建复杂的ETL指令
        complex_instructions = ETLInstructions(
            instruction_id="complex_etl_001",
            query_type="aggregate",
            source_fields=["complaint_count", "region"],
            filters=[
                {"column": "status", "operator": "=", "value": "resolved"},
                {"column": "priority", "operator": "IN", "value": ["high", "medium"]},
            ],
            aggregations=[
                AggregationConfig(
                    function="sum",
                    field="complaint_count",
                    group_by=["region"],
                    having_condition="SUM(complaint_count) > 5",
                )
            ],
            transformations=[
                {"type": "cast", "field": "complaint_count", "target_type": "integer"},
                {"type": "format", "field": "region", "pattern": "区域: {}"},
            ],
            time_config=TimeFilterConfig(
                field="created_at", relative_period="last_month"
            ),
            region_config=RegionFilterConfig(
                field="region", region_value="云南", region_type="contains"
            ),
            output_format="json",
        )

        # 模拟复杂数据
        complex_data = pd.DataFrame(
            {
                "complaint_count": [10, 15, 8, 12, 20, 5],
                "region": ["昆明市", "大理州", "丽江市", "昆明市", "大理州", "丽江市"],
                "status": [
                    "resolved",
                    "resolved",
                    "resolved",
                    "resolved",
                    "resolved",
                    "resolved",
                ],
                "priority": ["high", "medium", "high", "medium", "high", "low"],
            }
        )

        with (
            patch("app.services.intelligent_etl_executor.get_db") as mock_get_db,
            patch(
                "app.services.intelligent_etl_executor.crud_enhanced_data_source"
            ) as mock_crud,
            patch.object(executor, "_execute_query", return_value=complex_data),
        ):

            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db
            mock_crud.get.return_value = sample_sql_data_source

            # 执行复杂ETL
            result = await executor.execute_etl(complex_instructions, data_source_id=1)

            # 验证结果
            assert isinstance(result, ProcessedData)
            assert result.confidence > 0
            assert result.metadata["query_type"] == "aggregate"
            assert result.metadata["filters_applied"] == 2
            assert result.metadata["aggregations_applied"] == 1
            assert result.metadata["transformations_applied"] == 2


class TestETLInstructions:
    """ETL指令数据类测试"""

    def test_etl_instructions_creation(self):
        """测试ETL指令创建"""
        instructions = ETLInstructions(
            instruction_id="test_001",
            query_type="select",
            source_fields=["field1", "field2"],
            filters=[{"column": "status", "operator": "=", "value": "active"}],
            aggregations=[],
            transformations=[],
            output_format="dataframe",
        )

        assert instructions.instruction_id == "test_001"
        assert instructions.query_type == "select"
        assert len(instructions.source_fields) == 2
        assert len(instructions.filters) == 1
        assert instructions.output_format == "dataframe"

    def test_etl_instructions_with_configs(self):
        """测试带配置的ETL指令"""
        time_config = TimeFilterConfig(field="date", period="daily")
        region_config = RegionFilterConfig(field="region", region_value="test")

        instructions = ETLInstructions(
            instruction_id="test_002",
            query_type="aggregate",
            source_fields=["count"],
            filters=[],
            aggregations=[AggregationConfig(function="sum", field="count")],
            transformations=[],
            time_config=time_config,
            region_config=region_config,
        )

        assert instructions.time_config == time_config
        assert instructions.region_config == region_config
        assert len(instructions.aggregations) == 1


class TestTimeFilterConfig:
    """时间过滤配置测试"""

    def test_time_filter_config_creation(self):
        """测试时间过滤配置创建"""
        config = TimeFilterConfig(
            field="created_at",
            start_date="2024-01-01",
            end_date="2024-01-31",
            period="monthly",
            relative_period="this_month",
        )

        assert config.field == "created_at"
        assert config.start_date == "2024-01-01"
        assert config.end_date == "2024-01-31"
        assert config.period == "monthly"
        assert config.relative_period == "this_month"

    def test_time_filter_config_defaults(self):
        """测试时间过滤配置默认值"""
        config = TimeFilterConfig(field="date")

        assert config.field == "date"
        assert config.start_date is None
        assert config.end_date is None
        assert config.period == "monthly"
        assert config.relative_period is None


class TestRegionFilterConfig:
    """区域过滤配置测试"""

    def test_region_filter_config_creation(self):
        """测试区域过滤配置创建"""
        config = RegionFilterConfig(
            field="region",
            region_value="云南省",
            region_type="exact",
            region_level="province",
        )

        assert config.field == "region"
        assert config.region_value == "云南省"
        assert config.region_type == "exact"
        assert config.region_level == "province"

    def test_region_filter_config_defaults(self):
        """测试区域过滤配置默认值"""
        config = RegionFilterConfig(field="region", region_value="test")

        assert config.region_type == "exact"
        assert config.region_level == "province"


class TestAggregationConfig:
    """聚合配置测试"""

    def test_aggregation_config_creation(self):
        """测试聚合配置创建"""
        config = AggregationConfig(
            function="sum",
            field="amount",
            group_by=["category", "region"],
            having_condition="SUM(amount) > 1000",
        )

        assert config.function == "sum"
        assert config.field == "amount"
        assert config.group_by == ["category", "region"]
        assert config.having_condition == "SUM(amount) > 1000"

    def test_aggregation_config_defaults(self):
        """测试聚合配置默认值"""
        config = AggregationConfig(function="count", field="id")

        assert config.group_by is None
        assert config.having_condition is None


class TestProcessedData:
    """处理数据结果测试"""

    def test_processed_data_creation(self):
        """测试处理数据结果创建"""
        raw_data = pd.DataFrame({"test": [1, 2, 3]})
        processed_value = [1, 2, 3]
        metadata = {"source": "test"}

        result = ProcessedData(
            raw_data=raw_data,
            processed_value=processed_value,
            metadata=metadata,
            processing_time=1.5,
            confidence=0.9,
            query_executed="SELECT * FROM test",
            rows_processed=3,
        )

        assert result.raw_data.equals(raw_data)
        assert result.processed_value == processed_value
        assert result.metadata == metadata
        assert result.processing_time == 1.5
        assert result.confidence == 0.9
        assert result.query_executed == "SELECT * FROM test"
        assert result.rows_processed == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
