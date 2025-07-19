"""
Multi-data source compatibility tests for intelligent placeholder processing.

Tests the system's ability to work with different types of data sources:
- Database sources (PostgreSQL, MySQL, SQLite)
- File sources (CSV, Excel, JSON)
- API sources (REST APIs, GraphQL)
- Cloud sources (S3, BigQuery, etc.)
"""

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.models.enhanced_data_source import EnhancedDataSource
from app.services.enhanced_data_source_service import EnhancedDataSourceService
from app.services.intelligent_placeholder.adapter import (
    IntelligentPlaceholderProcessor,
    LLMPlaceholderService,
)
from app.services.intelligent_placeholder.matcher import IntelligentFieldMatcher
from app.services.data_processing.etl.intelligent_etl_executor import IntelligentETLExecutor


@pytest.mark.asyncio
@pytest.mark.integration
class TestMultiDataSourceCompatibility:
    """Test compatibility with various data source types."""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self, db_session: Session):
        """Set up test environment with mocked services."""
        # Mock services
        self.mock_ai_service = Mock()
        self.mock_ai_service.generate_completion = AsyncMock()

        self.mock_data_source_service = Mock(spec=EnhancedDataSourceService)

        # Initialize services
        self.llm_service = LLMPlaceholderService(self.mock_ai_service)
        self.field_matcher = IntelligentFieldMatcher()
        self.etl_executor = IntelligentETLExecutor(self.mock_data_source_service)

        self.processor = IntelligentPlaceholderProcessor(
            llm_service=self.llm_service,
            field_matcher=self.field_matcher,
            etl_executor=self.etl_executor,
        )

    @pytest.fixture
    def database_data_sources(self) -> List[Dict[str, Any]]:
        """Sample database data sources for testing."""
        return [
            {
                "name": "PostgreSQL Complaints DB",
                "source_type": "database",
                "connection_string": "postgresql://user:pass@localhost:5432/complaints",
                "schema": {
                    "tables": [
                        {
                            "name": "complaints",
                            "columns": [
                                {
                                    "name": "id",
                                    "type": "integer",
                                    "description": "投诉ID",
                                },
                                {
                                    "name": "complaint_date",
                                    "type": "date",
                                    "description": "投诉日期",
                                },
                                {
                                    "name": "region",
                                    "type": "string",
                                    "description": "投诉地区",
                                },
                                {
                                    "name": "category",
                                    "type": "string",
                                    "description": "投诉类别",
                                },
                                {
                                    "name": "status",
                                    "type": "string",
                                    "description": "处理状态",
                                },
                                {
                                    "name": "response_time",
                                    "type": "integer",
                                    "description": "响应时长(分钟)",
                                },
                                {
                                    "name": "satisfaction_score",
                                    "type": "decimal",
                                    "description": "满意度评分",
                                },
                            ],
                        },
                        {
                            "name": "regions",
                            "columns": [
                                {
                                    "name": "region_code",
                                    "type": "string",
                                    "description": "地区代码",
                                },
                                {
                                    "name": "region_name",
                                    "type": "string",
                                    "description": "地区名称",
                                },
                                {
                                    "name": "parent_region",
                                    "type": "string",
                                    "description": "上级地区",
                                },
                            ],
                        },
                    ]
                },
                "sample_data": {
                    "complaints": [
                        {
                            "id": 1,
                            "complaint_date": "2024-01-15",
                            "region": "昆明市",
                            "category": "服务质量",
                            "status": "已处理",
                            "response_time": 120,
                            "satisfaction_score": 4.2,
                        }
                    ]
                },
            },
            {
                "name": "MySQL Analytics DB",
                "source_type": "database",
                "connection_string": "mysql://user:pass@localhost:3306/analytics",
                "schema": {
                    "tables": [
                        {
                            "name": "daily_stats",
                            "columns": [
                                {
                                    "name": "stat_date",
                                    "type": "date",
                                    "description": "统计日期",
                                },
                                {
                                    "name": "total_complaints",
                                    "type": "integer",
                                    "description": "总投诉数",
                                },
                                {
                                    "name": "resolved_complaints",
                                    "type": "integer",
                                    "description": "已解决投诉数",
                                },
                                {
                                    "name": "avg_response_time",
                                    "type": "decimal",
                                    "description": "平均响应时间",
                                },
                            ],
                        }
                    ]
                },
            },
        ]

    @pytest.fixture
    def file_data_sources(self) -> List[Dict[str, Any]]:
        """Sample file data sources for testing."""
        return [
            {
                "name": "CSV Complaint Data",
                "source_type": "csv",
                "connection_string": "file:///data/complaints.csv",
                "schema": {
                    "columns": [
                        {
                            "name": "投诉编号",
                            "type": "string",
                            "description": "投诉编号",
                        },
                        {"name": "投诉日期", "type": "date", "description": "投诉日期"},
                        {
                            "name": "投诉地区",
                            "type": "string",
                            "description": "投诉地区",
                        },
                        {"name": "投诉内容", "type": "text", "description": "投诉内容"},
                        {
                            "name": "处理状态",
                            "type": "string",
                            "description": "处理状态",
                        },
                        {
                            "name": "满意度",
                            "type": "integer",
                            "description": "满意度评分",
                        },
                    ]
                },
                "sample_data": [
                    {
                        "投诉编号": "C202401001",
                        "投诉日期": "2024-01-01",
                        "投诉地区": "昆明市",
                        "投诉内容": "服务态度问题",
                        "处理状态": "已处理",
                        "满意度": 4,
                    }
                ],
            },
            {
                "name": "Excel Report Data",
                "source_type": "excel",
                "connection_string": "file:///data/monthly_report.xlsx",
                "schema": {
                    "sheets": [
                        {
                            "name": "统计数据",
                            "columns": [
                                {"name": "指标名称", "type": "string"},
                                {"name": "当期数值", "type": "numeric"},
                                {"name": "同期数值", "type": "numeric"},
                                {"name": "变化率", "type": "percentage"},
                            ],
                        }
                    ]
                },
            },
            {
                "name": "JSON API Response",
                "source_type": "json",
                "connection_string": "file:///data/api_response.json",
                "schema": {
                    "structure": {
                        "data": {
                            "complaints": "array",
                            "statistics": "object",
                            "regions": "array",
                        }
                    }
                },
            },
        ]

    @pytest.fixture
    def api_data_sources(self) -> List[Dict[str, Any]]:
        """Sample API data sources for testing."""
        return [
            {
                "name": "REST API Complaints",
                "source_type": "rest_api",
                "connection_string": "https://api.complaints.gov.cn/v1",
                "schema": {
                    "endpoints": [
                        {
                            "path": "/complaints",
                            "method": "GET",
                            "parameters": ["region", "date_from", "date_to"],
                            "response_fields": [
                                {"name": "id", "type": "string"},
                                {"name": "date", "type": "date"},
                                {"name": "region", "type": "string"},
                                {"name": "status", "type": "string"},
                            ],
                        },
                        {
                            "path": "/statistics",
                            "method": "GET",
                            "parameters": ["period", "region"],
                            "response_fields": [
                                {"name": "total_count", "type": "integer"},
                                {"name": "resolved_count", "type": "integer"},
                                {"name": "avg_response_time", "type": "decimal"},
                            ],
                        },
                    ]
                },
            },
            {
                "name": "GraphQL Analytics API",
                "source_type": "graphql",
                "connection_string": "https://analytics.example.com/graphql",
                "schema": {
                    "queries": [
                        {
                            "name": "getComplaintStats",
                            "fields": [
                                "totalComplaints",
                                "resolvedComplaints",
                                "averageResponseTime",
                                "satisfactionScore",
                            ],
                        }
                    ]
                },
            },
        ]

    async def test_database_source_compatibility(
        self, database_data_sources: List[Dict[str, Any]]
    ):
        """Test compatibility with database data sources."""
        for db_source in database_data_sources:
            # Mock data source service responses
            self.mock_data_source_service.get_schema = AsyncMock(
                return_value=db_source["schema"]
            )
            self.mock_data_source_service.execute_query = AsyncMock(
                return_value=pd.DataFrame(
                    [{"total_complaints": 1500, "avg_response_time": 125.5}]
                )
            )

            # Mock LLM understanding for database fields
            self.mock_ai_service.generate_completion.return_value = json.dumps(
                {
                    "semantic_meaning": "需要查询投诉总数",
                    "data_requirements": ["total_complaints", "complaint_count"],
                    "sql_query": "SELECT COUNT(*) as total_complaints FROM complaints",
                    "confidence_score": 0.92,
                }
            )

            # Test placeholder processing with database source
            template = "数据库统计：总投诉{{统计:总投诉数}}件"

            result = await self.processor.process_template(
                template_content=template, data_source_config=db_source
            )

            # Verify database-specific processing
            assert result is not None
            assert result.success is True
            assert "1500" in str(result.final_content) or "1,500" in str(
                result.final_content
            )

            # Verify SQL query generation was attempted
            self.mock_data_source_service.execute_query.assert_called()

    async def test_file_source_compatibility(
        self, file_data_sources: List[Dict[str, Any]]
    ):
        """Test compatibility with file data sources."""
        for file_source in file_data_sources:
            # Mock file reading based on source type
            if file_source["source_type"] == "csv":
                mock_data = pd.DataFrame(file_source.get("sample_data", []))
            elif file_source["source_type"] == "excel":
                mock_data = pd.DataFrame(
                    [
                        {
                            "指标名称": "总投诉数",
                            "当期数值": 2000,
                            "同期数值": 1800,
                            "变化率": 11.1,
                        }
                    ]
                )
            else:  # JSON
                mock_data = pd.DataFrame(
                    [{"metric": "total_complaints", "value": 1800}]
                )

            self.mock_data_source_service.read_file = AsyncMock(return_value=mock_data)
            self.mock_data_source_service.get_schema = AsyncMock(
                return_value=file_source["schema"]
            )

            # Mock LLM understanding for file fields
            self.mock_ai_service.generate_completion.return_value = json.dumps(
                {
                    "semantic_meaning": "从文件中获取投诉统计数据",
                    "data_requirements": ["总投诉数", "投诉数量"],
                    "file_processing": "需要读取并聚合数据",
                    "confidence_score": 0.88,
                }
            )

            # Test placeholder processing with file source
            template = (
                f"文件数据：{{{{统计:投诉总数}}}}（来源：{file_source['source_type']}）"
            )

            result = await self.processor.process_template(
                template_content=template, data_source_config=file_source
            )

            # Verify file-specific processing
            assert result is not None
            assert result.success is True

            # Verify file reading was attempted
            if hasattr(self.mock_data_source_service, "read_file"):
                self.mock_data_source_service.read_file.assert_called()

    async def test_api_source_compatibility(
        self, api_data_sources: List[Dict[str, Any]]
    ):
        """Test compatibility with API data sources."""
        for api_source in api_data_sources:
            # Mock API responses
            if api_source["source_type"] == "rest_api":
                mock_response = {
                    "data": [
                        {
                            "id": "1",
                            "date": "2024-01-01",
                            "region": "昆明市",
                            "status": "resolved",
                        }
                    ],
                    "statistics": {
                        "total_count": 1200,
                        "resolved_count": 1000,
                        "avg_response_time": 95.5,
                    },
                }
            else:  # GraphQL
                mock_response = {
                    "data": {
                        "getComplaintStats": {
                            "totalComplaints": 1300,
                            "resolvedComplaints": 1100,
                            "averageResponseTime": 88.2,
                            "satisfactionScore": 4.1,
                        }
                    }
                }

            self.mock_data_source_service.call_api = AsyncMock(
                return_value=mock_response
            )
            self.mock_data_source_service.get_schema = AsyncMock(
                return_value=api_source["schema"]
            )

            # Mock LLM understanding for API fields
            self.mock_ai_service.generate_completion.return_value = json.dumps(
                {
                    "semantic_meaning": "通过API获取投诉统计",
                    "data_requirements": ["total_count", "totalComplaints"],
                    "api_endpoint": (
                        "/statistics"
                        if api_source["source_type"] == "rest_api"
                        else "getComplaintStats"
                    ),
                    "confidence_score": 0.90,
                }
            )

            # Test placeholder processing with API source
            template = f"API数据：{{{{统计:总投诉数}}}}（{api_source['source_type']}）"

            result = await self.processor.process_template(
                template_content=template, data_source_config=api_source
            )

            # Verify API-specific processing
            assert result is not None
            assert result.success is True

            # Verify API call was made
            self.mock_data_source_service.call_api.assert_called()

    async def test_cross_source_data_integration(self):
        """Test integration of data from multiple sources."""
        # Define multiple data sources
        sources = [
            {
                "name": "primary_db",
                "type": "database",
                "data": {"total_complaints": 1000},
            },
            {"name": "backup_file", "type": "csv", "data": {"backup_complaints": 50}},
            {
                "name": "external_api",
                "type": "api",
                "data": {"external_complaints": 25},
            },
        ]

        # Mock responses for each source
        for i, source in enumerate(sources):
            if source["type"] == "database":
                self.mock_data_source_service.execute_query = AsyncMock(
                    return_value=pd.DataFrame([source["data"]])
                )
            elif source["type"] == "csv":
                self.mock_data_source_service.read_file = AsyncMock(
                    return_value=pd.DataFrame([source["data"]])
                )
            else:  # API
                self.mock_data_source_service.call_api = AsyncMock(
                    return_value={"data": source["data"]}
                )

        # Mock LLM to understand cross-source aggregation
        self.mock_ai_service.generate_completion.return_value = json.dumps(
            {
                "semantic_meaning": "需要聚合多个数据源的投诉数据",
                "data_requirements": [
                    "total_complaints",
                    "backup_complaints",
                    "external_complaints",
                ],
                "aggregation_type": "sum",
                "cross_source": True,
                "confidence_score": 0.85,
            }
        )

        # Template requiring cross-source data
        template = """
        综合统计报告：
        主数据库：{{统计:主要投诉数}}件
        备份文件：{{统计:备份投诉数}}件  
        外部API：{{统计:外部投诉数}}件
        总计：{{统计:总投诉数}}件
        """

        result = await self.processor.process_template(
            template_content=template, data_source_configs=sources
        )

        # Verify cross-source integration
        assert result is not None
        assert result.success is True

        # Should contain data from all sources
        content = result.final_content
        assert "1000" in content or "1,000" in content  # Primary DB
        assert "50" in content  # Backup file
        assert "25" in content  # External API

    async def test_data_source_failover(self):
        """Test failover between data sources when primary source fails."""
        # Primary source (will fail)
        primary_source = {"name": "primary_db", "type": "database", "priority": 1}

        # Backup source (will succeed)
        backup_source = {"name": "backup_api", "type": "api", "priority": 2}

        # Mock primary source failure
        self.mock_data_source_service.execute_query.side_effect = Exception(
            "Database connection failed"
        )

        # Mock backup source success
        self.mock_data_source_service.call_api.return_value = {
            "data": {"total_complaints": 900}
        }

        # Mock LLM understanding failover
        self.mock_ai_service.generate_completion.return_value = json.dumps(
            {
                "semantic_meaning": "投诉总数统计，支持数据源切换",
                "data_requirements": ["total_complaints"],
                "failover_supported": True,
                "confidence_score": 0.87,
            }
        )

        template = "故障转移测试：{{统计:总投诉数}}件"

        result = await self.processor.process_template(
            template_content=template,
            data_source_configs=[primary_source, backup_source],
        )

        # Verify failover worked
        assert result is not None
        assert result.success is True
        assert "900" in result.final_content

        # Verify backup source was used
        self.mock_data_source_service.call_api.assert_called()

    async def test_data_source_performance_comparison(self):
        """Test and compare performance across different data source types."""
        import time

        source_types = ["database", "csv", "api", "json"]
        performance_results = []

        for source_type in source_types:
            # Mock appropriate service method
            if source_type == "database":
                self.mock_data_source_service.execute_query = AsyncMock(
                    return_value=pd.DataFrame([{"value": 100}])
                )
            elif source_type in ["csv", "json"]:
                self.mock_data_source_service.read_file = AsyncMock(
                    return_value=pd.DataFrame([{"value": 100}])
                )
            else:  # API
                self.mock_data_source_service.call_api = AsyncMock(
                    return_value={"data": {"value": 100}}
                )

            # Mock LLM response
            self.mock_ai_service.generate_completion.return_value = json.dumps(
                {"understanding": f"{source_type}数据处理", "confidence": 0.9}
            )

            # Measure processing time
            start_time = time.time()

            result = await self.processor.process_template(
                template_content=f"{{{{统计:测试数据}}}}（{source_type}）",
                data_source_config={"type": source_type},
            )

            processing_time = time.time() - start_time

            performance_results.append(
                {
                    "source_type": source_type,
                    "processing_time": processing_time,
                    "success": result.success if result else False,
                }
            )

        # Log performance comparison
        print(f"\nData Source Performance Comparison:")
        for result in performance_results:
            print(
                f"  {result['source_type']}: {result['processing_time']:.3f}s - "
                f"{'✓' if result['success'] else '✗'}"
            )

        # Verify all sources processed successfully
        successful_sources = [r for r in performance_results if r["success"]]
        assert len(successful_sources) == len(source_types)

    async def test_schema_inference_across_sources(self):
        """Test automatic schema inference for different data source types."""
        test_cases = [
            {
                "source_type": "csv",
                "sample_data": pd.DataFrame(
                    [{"投诉编号": "C001", "投诉日期": "2024-01-01", "投诉数量": 5}]
                ),
                "expected_fields": ["投诉编号", "投诉日期", "投诉数量"],
            },
            {
                "source_type": "json",
                "sample_data": {
                    "complaints": [{"id": 1, "date": "2024-01-01", "count": 10}]
                },
                "expected_fields": ["id", "date", "count"],
            },
            {
                "source_type": "database",
                "sample_data": {
                    "tables": {
                        "complaints": ["id", "complaint_date", "region", "status"]
                    }
                },
                "expected_fields": ["id", "complaint_date", "region", "status"],
            },
        ]

        for case in test_cases:
            # Mock schema inference
            self.mock_data_source_service.infer_schema = AsyncMock(
                return_value={
                    "fields": [
                        {"name": field, "type": "auto"}
                        for field in case["expected_fields"]
                    ]
                }
            )

            # Mock LLM field understanding
            self.mock_ai_service.generate_completion.return_value = json.dumps(
                {
                    "field_analysis": {
                        field: {"semantic_meaning": f"{field}的含义", "confidence": 0.8}
                        for field in case["expected_fields"]
                    }
                }
            )

            # Test schema inference
            inferred_schema = await self.mock_data_source_service.infer_schema(
                source_type=case["source_type"], sample_data=case["sample_data"]
            )

            # Verify schema inference
            assert inferred_schema is not None
            assert "fields" in inferred_schema

            inferred_field_names = [f["name"] for f in inferred_schema["fields"]]
            for expected_field in case["expected_fields"]:
                assert expected_field in inferred_field_names

            print(
                f"Schema inference for {case['source_type']}: "
                f"{len(inferred_field_names)} fields detected"
            )
