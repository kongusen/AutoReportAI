"""
Unit tests for data_processing service module
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pandas as pd
import httpx
from datetime import datetime

from app.services.data_processing import (
    DataRetrievalService,
    DataAnalysisService,
    ETLService,
    ETLJobStatus,
    ETLTransformationEngine,
    IntelligentETLExecutor,
    ETLJobScheduler,
    ETLJobExecutionStatus
)


class TestDataRetrievalService:
    """Test DataRetrievalService class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = DataRetrievalService()

    @pytest.mark.asyncio
    async def test_fetch_data_sql(self):
        """Test fetching data from SQL source"""
        # Create mock data source
        mock_source = Mock()
        mock_source.source_type = "sql"
        mock_source.db_query = "SELECT * FROM regions"
        
        result = await self.service.fetch_data(mock_source)
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "region" in result.columns
        assert "sales" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_data_csv(self):
        """Test fetching data from CSV source"""
        # Create mock data source
        mock_source = Mock()
        mock_source.source_type = "csv"
        mock_source.file_path = "/path/to/test.csv"
        
        # Mock pandas read_csv
        test_data = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        with patch('pandas.read_csv', return_value=test_data):
            result = await self.service.fetch_data(mock_source)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "col1" in result.columns
        assert "col2" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_data_csv_file_not_found(self):
        """Test CSV fetch with missing file"""
        mock_source = Mock()
        mock_source.source_type = "csv"
        mock_source.file_path = "/nonexistent/file.csv"
        
        with patch('pandas.read_csv', side_effect=FileNotFoundError()):
            result = await self.service.fetch_data(mock_source)
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @pytest.mark.asyncio
    async def test_fetch_data_api_success(self):
        """Test successful API data fetch"""
        mock_source = Mock()
        mock_source.source_type = "api"
        mock_source.api_method = "GET"
        mock_source.api_url = "https://api.example.com/data"
        mock_source.api_headers = {"Authorization": "Bearer token"}
        mock_source.api_body = None
        
        # Mock API response
        mock_response_data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )
            
            result = await self.service.fetch_data(mock_source)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "id" in result.columns
        assert "name" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_data_api_error(self):
        """Test API fetch with request error"""
        mock_source = Mock()
        mock_source.source_type = "api"
        mock_source.api_method = "GET"
        mock_source.api_url = "https://api.example.com/data"
        mock_source.api_headers = {}
        mock_source.api_body = None
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=httpx.RequestError("Connection failed")
            )
            
            result = await self.service.fetch_data(mock_source)
        
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @pytest.mark.asyncio
    async def test_fetch_data_unsupported_type(self):
        """Test fetch with unsupported source type"""
        mock_source = Mock()
        mock_source.source_type = "unsupported"
        
        with pytest.raises(ValueError, match="Unsupported data source type"):
            await self.service.fetch_data(mock_source)

    def test_fetch_from_sql_region_query(self):
        """Test SQL fetch with region query"""
        mock_source = Mock()
        mock_source.db_query = "SELECT region, sales FROM data WHERE region IS NOT NULL"
        
        result = self.service._fetch_from_sql(mock_source)
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "region" in result.columns
        assert len(result) == 5  # Expected number of regions

    def test_fetch_from_sql_total_query(self):
        """Test SQL fetch with total query"""
        mock_source = Mock()
        mock_source.db_query = "SELECT SUM(sales) as total_sales FROM data"
        
        result = self.service._fetch_from_sql(mock_source)
        
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "total" in result.columns


class TestDataAnalysisService:
    """Test DataAnalysisService class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        self.service = DataAnalysisService(self.mock_db)

    @patch('app.services.data_processing.analysis.models')
    def test_analyze_success(self, mock_models):
        """Test successful data analysis"""
        # Setup mock data source
        mock_data_source = Mock()
        mock_data_source.id = 1
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_data_source
        
        # Mock data retrieval
        test_df = pd.DataFrame({
            "numeric_col": [1, 2, 3, 4, 5],
            "text_col": ["a", "b", "c", "d", "e"]
        })
        self.service.retrieval_service.get_data = Mock(return_value=test_df)
        
        # Mock statistics service
        self.service.statistics_service.get_basic_stats = Mock(return_value={
            "mean": 3.0,
            "std": 1.58
        })
        
        result = self.service.analyze(data_source_id=1)
        
        assert "row_count" in result
        assert "column_count" in result
        assert "columns" in result
        assert "data_types" in result
        assert "summary_stats" in result
        assert result["row_count"] == 5
        assert result["column_count"] == 2

    @patch('app.services.data_processing.analysis.models')
    def test_analyze_data_source_not_found(self, mock_models):
        """Test analysis with missing data source"""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.service.analyze(data_source_id=999)
        
        assert "error" in result
        assert "not found" in result["error"]

    @patch('app.services.data_processing.analysis.models')
    def test_analyze_empty_data(self, mock_models):
        """Test analysis with empty data"""
        mock_data_source = Mock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_data_source
        
        # Mock empty dataframe
        empty_df = pd.DataFrame()
        self.service.retrieval_service.get_data = Mock(return_value=empty_df)
        
        result = self.service.analyze(data_source_id=1)
        
        assert "error" in result
        assert "No data available" in result["error"]

    @patch('app.services.data_processing.analysis.models')
    def test_get_summary_statistics(self, mock_models):
        """Test getting summary statistics"""
        mock_data_source = Mock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_data_source
        
        # Create test dataframe with mixed data types
        test_df = pd.DataFrame({
            "numeric_col": [1.5, 2.5, 3.5, 4.5, 5.5],
            "integer_col": [1, 2, 3, 4, 5],
            "text_col": ["cat", "dog", "cat", "bird", "cat"],
            "mixed_col": [1, "text", 3, "more", 5]
        })
        self.service.retrieval_service.get_data = Mock(return_value=test_df)
        
        result = self.service.get_summary_statistics(data_source_id=1)
        
        assert "basic_info" in result
        assert "numeric_summary" in result
        assert "categorical_summary" in result
        assert "data_quality" in result
        
        # Check basic info
        assert result["basic_info"]["total_rows"] == 5
        assert result["basic_info"]["total_columns"] == 4
        assert result["basic_info"]["numeric_columns"] >= 2
        
        # Check numeric summary
        assert "numeric_col" in result["numeric_summary"]
        assert "mean" in result["numeric_summary"]["numeric_col"]
        assert "std" in result["numeric_summary"]["numeric_col"]
        
        # Check categorical summary
        assert "text_col" in result["categorical_summary"]
        assert "unique_values" in result["categorical_summary"]["text_col"]
        assert "most_frequent" in result["categorical_summary"]["text_col"]

    @patch('app.services.data_processing.analysis.models')
    def test_create_visualization_bar_chart(self, mock_models):
        """Test creating bar chart visualization"""
        mock_data_source = Mock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_data_source
        
        # Create test data suitable for bar chart
        test_df = pd.DataFrame({
            "category": ["A", "B", "C"],
            "value": [10, 20, 15]
        })
        self.service.retrieval_service.get_data = Mock(return_value=test_df)
        
        # Mock visualization service
        expected_chart = {
            "type": "bar",
            "title": "Test Chart",
            "data": [{"x": "A", "y": 10}, {"x": "B", "y": 20}, {"x": "C", "y": 15}]
        }
        self.service.visualization_service.generate_bar_chart = Mock(return_value=expected_chart)
        
        result = self.service.create_visualization(data_source_id=1, chart_type="bar")
        
        assert result["type"] == "bar"
        assert result["title"] == "Test Chart"
        assert len(result["data"]) == 3

    @patch('app.services.data_processing.analysis.models')
    def test_create_visualization_pie_chart(self, mock_models):
        """Test creating pie chart visualization"""
        mock_data_source = Mock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_data_source
        
        # Create test data suitable for pie chart
        test_df = pd.DataFrame({
            "category": ["A", "A", "B", "B", "B", "C"],
            "other_col": [1, 2, 3, 4, 5, 6]
        })
        self.service.retrieval_service.get_data = Mock(return_value=test_df)
        
        result = self.service.create_visualization(data_source_id=1, chart_type="pie")
        
        assert result["type"] == "pie"
        assert "data" in result
        assert len(result["data"]) > 0
        assert all("label" in item and "value" in item for item in result["data"])

    @patch('app.services.data_processing.analysis.models')
    def test_create_visualization_unsupported_type(self, mock_models):
        """Test creating visualization with unsupported chart type"""
        mock_data_source = Mock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_data_source
        
        test_df = pd.DataFrame({"col": [1, 2, 3]})
        self.service.retrieval_service.get_data = Mock(return_value=test_df)
        
        result = self.service.create_visualization(data_source_id=1, chart_type="unsupported")
        
        assert "error" in result
        assert "Unsupported chart type" in result["error"]


class TestETLService:
    """Test ETL Service classes"""

    def test_etl_job_status_enum(self):
        """Test ETL job status enumeration"""
        assert ETLJobStatus.PENDING == "pending"
        assert ETLJobStatus.RUNNING == "running"
        assert ETLJobStatus.COMPLETED == "completed"
        assert ETLJobStatus.FAILED == "failed"

    def test_etl_job_execution_status_enum(self):
        """Test ETL job execution status enumeration"""
        assert ETLJobExecutionStatus.QUEUED == "queued"
        assert ETLJobExecutionStatus.PROCESSING == "processing"
        assert ETLJobExecutionStatus.SUCCESS == "success"
        assert ETLJobExecutionStatus.ERROR == "error"


class TestModuleImports:
    """Test module imports and exports"""

    def test_module_exports(self):
        """Test that all expected classes are exported"""
        from app.services.data_processing import (
            DataRetrievalService,
            DataAnalysisService,
            ETLService,
            ETLJobStatus,
            ETLTransformationEngine,
            IntelligentETLExecutor,
            ETLJobScheduler,
            ETLJobExecutionStatus
        )
        
        # Verify classes can be imported
        assert DataRetrievalService is not None
        assert DataAnalysisService is not None
        assert ETLService is not None
        assert ETLJobStatus is not None
        assert ETLTransformationEngine is not None
        assert IntelligentETLExecutor is not None
        assert ETLJobScheduler is not None
        assert ETLJobExecutionStatus is not None

    def test_module_version(self):
        """Test module version"""
        import app.services.data_processing as module
        assert hasattr(module, '__version__')
        assert module.__version__ == "1.0.0"


class TestErrorHandling:
    """Test error handling scenarios"""

    def setup_method(self):
        """Setup test fixtures"""
        self.retrieval_service = DataRetrievalService()

    @pytest.mark.asyncio
    async def test_fetch_data_with_exception(self):
        """Test data fetch with unexpected exception"""
        mock_source = Mock()
        mock_source.source_type = "sql"
        
        # Mock an exception in the SQL fetch method
        with patch.object(self.retrieval_service, '_fetch_from_sql', side_effect=Exception("Database error")):
            with pytest.raises(Exception):
                await self.retrieval_service.fetch_data(mock_source)

    def test_analysis_service_with_db_error(self):
        """Test analysis service with database error"""
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database connection failed")
        
        service = DataAnalysisService(mock_db)
        result = service.analyze(data_source_id=1)
        
        assert "error" in result
        assert "failed" in result["error"].lower()


class TestIntegrationScenarios:
    """Test integration scenarios"""

    @pytest.mark.asyncio
    async def test_end_to_end_data_processing(self):
        """Test end-to-end data processing workflow"""
        # Setup
        retrieval_service = DataRetrievalService()
        
        # Create mock data source
        mock_source = Mock()
        mock_source.source_type = "sql"
        mock_source.db_query = "SELECT region, sales FROM data"
        
        # Fetch data
        data = await retrieval_service.fetch_data(mock_source)
        
        # Verify data structure
        assert isinstance(data, pd.DataFrame)
        if not data.empty:
            assert "region" in data.columns
            assert "sales" in data.columns
            assert len(data) > 0

    def test_data_analysis_workflow(self):
        """Test complete data analysis workflow"""
        # Setup
        mock_db = Mock()
        analysis_service = DataAnalysisService(mock_db)
        
        # Mock data source
        mock_data_source = Mock()
        mock_data_source.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_data_source
        
        # Mock data
        test_df = pd.DataFrame({
            "sales": [100, 200, 150, 300, 250],
            "region": ["A", "B", "A", "C", "B"],
            "date": pd.date_range("2024-01-01", periods=5)
        })
        analysis_service.retrieval_service.get_data = Mock(return_value=test_df)
        analysis_service.statistics_service.get_basic_stats = Mock(return_value={"mean": 200})
        
        # Run analysis
        result = analysis_service.analyze(data_source_id=1)
        
        # Verify results
        assert result["row_count"] == 5
        assert result["column_count"] == 3
        assert "sales" in result["columns"]
        assert "region" in result["columns"]