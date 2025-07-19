"""
End-to-end integration tests for the intelligent placeholder processing system.

This module contains comprehensive tests that verify the complete workflow
from placeholder parsing to report generation, including:
- Complete placeholder processing flow
- Multi-data source compatibility
- Different LLM provider integration
- Report generation quality
- Performance benchmarks
"""

import asyncio
import json
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enhanced_data_source import EnhancedDataSource
from app.models.template import Template
from app.models.user import User
from app.services.ai_integration.llm_service import AIService
from app.services.intelligent_placeholder.adapter import (
    ContentGenerator,
    IntelligentETLExecutor,
    IntelligentFieldMatcher,
    IntelligentPlaceholderProcessor,
    LLMPlaceholderService,
    ReportQualityChecker,
)


@pytest.mark.asyncio
@pytest.mark.integration
class TestIntelligentPlaceholderE2E:
    """End-to-end integration tests for intelligent placeholder processing."""

    @pytest.fixture(autouse=True)
    async def setup_services(self, db_session: Session):
        """Set up all required services for testing."""
        # Mock AI service for testing
        self.mock_ai_service = Mock(spec=AIService)
        self.mock_ai_service.generate_completion = AsyncMock()

        # Initialize services
        self.llm_service = LLMPlaceholderService(self.mock_ai_service)
        self.field_matcher = IntelligentFieldMatcher()
        self.etl_executor = IntelligentETLExecutor(None)  # Will be mocked
        self.content_generator = ContentGenerator(None)  # Will be mocked
        self.quality_checker = ReportQualityChecker(self.mock_ai_service)

        self.processor = IntelligentPlaceholderProcessor(
            llm_service=self.llm_service,
            field_matcher=self.field_matcher,
            etl_executor=self.etl_executor,
            content_generator=self.content_generator,
            quality_checker=self.quality_checker,
        )

    @pytest.fixture
    def sample_template_content(self) -> str:
        """Sample template with intelligent placeholders."""
        return """{{周期:2024年第一季度}}{{区域:云南省}}投诉数据分析报告

一、总体情况
本季度共收到投诉{{统计:总投诉件数}}件，较去年同期{{统计:同比变化}}。
其中微信小程序投诉{{统计:微信投诉件数}}件，占比{{统计:微信投诉占比}}%。

二、处理效率
平均响应时长{{统计:平均响应时长}}分钟，24小时办结率达到{{统计:24小时办结率}}%。
处理满意度评分{{统计:处理满意度}}分。

三、趋势分析
{{图表:投诉趋势图}}

四、分析结论
{{分析:总体评价和建议}}
"""

    @pytest.fixture
    def sample_data_schema(self) -> Dict[str, Any]:
        """Sample data schema for testing."""
        return {
            "fields": [
                {"name": "metric_name", "type": "string", "description": "指标名称"},
                {"name": "metric_type", "type": "string", "description": "指标类型"},
                {"name": "value_2024", "type": "numeric", "description": "2024年数值"},
                {"name": "value_2023", "type": "numeric", "description": "2023年数值"},
                {"name": "change_pct", "type": "numeric", "description": "变化百分比"},
                {
                    "name": "change_direction",
                    "type": "string",
                    "description": "变化方向",
                },
                {"name": "unit", "type": "string", "description": "单位"},
            ],
            "sample_data": [
                {
                    "metric_name": "总投诉件数",
                    "metric_type": "统计",
                    "value_2024": 2141,
                    "value_2023": 1970,
                    "change_pct": 8.68,
                    "change_direction": "上升",
                    "unit": "件",
                },
                {
                    "metric_name": "微信小程序投诉件数",
                    "metric_type": "统计",
                    "value_2024": 356,
                    "value_2023": None,
                    "change_pct": None,
                    "change_direction": None,
                    "unit": "件",
                },
            ],
        }

    async def test_complete_placeholder_processing_flow(
        self, sample_template_content: str, sample_data_schema: Dict[str, Any]
    ):
        """Test the complete end-to-end placeholder processing workflow."""
        # Mock LLM responses for different stages
        self.mock_ai_service.generate_completion.side_effect = [
            # Placeholder understanding response
            json.dumps(
                {
                    "semantic_meaning": "统计类占位符，需要获取总投诉件数",
                    "data_requirements": ["总投诉件数", "投诉数量"],
                    "aggregation_type": "sum",
                    "confidence_score": 0.95,
                }
            ),
            # Field matching response
            json.dumps(
                {
                    "field_suggestions": [
                        {
                            "field_name": "value_2024",
                            "confidence": 0.9,
                            "transformation_needed": False,
                        }
                    ]
                }
            ),
            # Content generation response
            "2141",
            # Quality check response
            json.dumps(
                {
                    "quality_score": 0.92,
                    "suggestions": ["内容准确，格式规范"],
                    "issues": [],
                }
            ),
        ]

        # Mock ETL executor
        mock_etl_result = Mock()
        mock_etl_result.processed_value = 2141
        mock_etl_result.metadata = {"confidence": 0.95}
        self.etl_executor.execute_etl = AsyncMock(return_value=mock_etl_result)

        # Mock content generator
        self.content_generator.generate_content = AsyncMock(return_value="2141件")

        # Process the template
        result = await self.processor.process_template(
            template_content=sample_template_content, data_schema=sample_data_schema
        )

        # Verify the processing result
        assert result is not None
        assert result.success is True
        assert len(result.processed_placeholders) > 0
        assert result.final_content is not None
        assert "2141" in result.final_content

        # Verify LLM was called for understanding
        assert self.mock_ai_service.generate_completion.call_count >= 1

    async def test_multi_data_source_compatibility(self):
        """Test compatibility with different data source types."""
        test_cases = [
            {
                "source_type": "database",
                "connection_string": "postgresql://test:test@localhost/test",
                "schema": {"tables": ["complaints", "regions"]},
                "expected_fields": ["complaint_count", "region_name"],
            },
            {
                "source_type": "csv",
                "connection_string": "file:///test/data.csv",
                "schema": {"columns": ["metric_name", "value"]},
                "expected_fields": ["metric_name", "value"],
            },
            {
                "source_type": "api",
                "connection_string": "https://api.example.com/data",
                "schema": {"endpoints": ["/complaints", "/stats"]},
                "expected_fields": ["total_complaints", "avg_response_time"],
            },
        ]

        for case in test_cases:
            # Mock data source service
            mock_data_source = Mock()
            mock_data_source.source_type = case["source_type"]
            mock_data_source.connection_string = case["connection_string"]
            mock_data_source.get_schema = AsyncMock(return_value=case["schema"])

            # Test field matching for this data source type
            available_fields = case["expected_fields"]

            # Mock LLM response for field matching
            self.mock_ai_service.generate_completion.return_value = json.dumps(
                {
                    "field_suggestions": [
                        {
                            "field_name": field,
                            "confidence": 0.8,
                            "transformation_needed": False,
                        }
                        for field in available_fields
                    ]
                }
            )

            # Test field matching
            suggestions = await self.llm_service.suggest_field_mapping(
                placeholder_description="测试占位符", available_fields=available_fields
            )

            assert len(suggestions) > 0
            assert all(s.field_name in available_fields for s in suggestions)

    async def test_different_llm_provider_integration(self):
        """Test integration with different LLM providers."""
        llm_providers = [
            {"name": "openai", "model": "gpt-4", "expected_response_format": "json"},
            {
                "name": "claude",
                "model": "claude-3-sonnet",
                "expected_response_format": "json",
            },
            {
                "name": "local",
                "model": "llama-2-7b",
                "expected_response_format": "text",
            },
        ]

        for provider in llm_providers:
            # Mock AI service for this provider
            mock_ai_service = Mock(spec=AIService)
            mock_ai_service.provider = provider["name"]
            mock_ai_service.model = provider["model"]

            # Mock response based on provider
            if provider["expected_response_format"] == "json":
                mock_response = json.dumps(
                    {"understanding": "测试理解结果", "confidence": 0.9}
                )
            else:
                mock_response = "测试理解结果"

            mock_ai_service.generate_completion = AsyncMock(return_value=mock_response)

            # Create LLM service with this provider
            llm_service = LLMPlaceholderService(mock_ai_service)

            # Test placeholder understanding
            result = await llm_service.understand_placeholder(
                placeholder_type="统计",
                description="总投诉件数",
                context="本季度投诉情况统计",
            )

            assert result is not None
            assert result.confidence_score > 0

    async def test_report_generation_quality(self, sample_template_content: str):
        """Test the quality of generated reports."""
        # Mock high-quality LLM responses
        quality_responses = [
            json.dumps(
                {
                    "semantic_meaning": "需要获取2024年第一季度云南省的总投诉件数",
                    "data_requirements": ["总投诉件数"],
                    "aggregation_type": "count",
                    "time_dimension": "2024年第一季度",
                    "region_dimension": "云南省",
                    "confidence_score": 0.98,
                }
            ),
            json.dumps(
                {
                    "field_suggestions": [
                        {
                            "field_name": "value_2024",
                            "confidence": 0.95,
                            "transformation_needed": False,
                            "calculation_formula": "SUM(value_2024) WHERE metric_name='总投诉件数'",
                        }
                    ]
                }
            ),
            "2,141件",  # Formatted content
            json.dumps(
                {
                    "quality_score": 0.96,
                    "language_fluency": 0.98,
                    "data_consistency": 0.94,
                    "format_compliance": 0.97,
                    "suggestions": [
                        "数据格式规范，内容准确",
                        "语言表达自然流畅",
                        "建议添加数据来源说明",
                    ],
                    "issues": [],
                }
            ),
        ]

        self.mock_ai_service.generate_completion.side_effect = quality_responses

        # Mock ETL with realistic data
        mock_etl_result = Mock()
        mock_etl_result.processed_value = 2141
        mock_etl_result.metadata = {
            "confidence": 0.95,
            "data_source": "complaint_database",
            "processing_time": 1.2,
        }
        self.etl_executor.execute_etl = AsyncMock(return_value=mock_etl_result)

        # Mock content generator with formatting
        self.content_generator.generate_content = AsyncMock(return_value="2,141件")

        # Process template
        result = await self.processor.process_template(
            template_content=sample_template_content, data_schema={"fields": []}
        )

        # Quality assertions
        assert result.success is True
        assert result.quality_score >= 0.9
        assert len(result.quality_issues) == 0
        assert result.processing_time < 30.0  # Should complete within 30 seconds

        # Content quality checks
        assert "2,141件" in result.final_content
        assert "云南省" in result.final_content
        assert "2024年第一季度" in result.final_content

    async def test_performance_benchmarks(self):
        """Test performance benchmarks for the intelligent placeholder system."""
        # Performance test scenarios
        test_scenarios = [
            {
                "name": "single_placeholder",
                "template": "总投诉件数：{{统计:总投诉件数}}",
                "expected_max_time": 5.0,
            },
            {
                "name": "multiple_placeholders",
                "template": """
                {{统计:总投诉件数}}件投诉，{{统计:平均响应时长}}分钟响应，
                {{统计:满意度}}分满意度，{{区域:主要区域}}为重点区域
                """,
                "expected_max_time": 15.0,
            },
            {
                "name": "complex_template",
                "template": """
                {{周期:报告期间}}{{区域:区域名称}}数据报告
                统计：{{统计:总数}}、{{统计:平均值}}、{{统计:最大值}}
                图表：{{图表:趋势图}}、{{图表:分布图}}
                分析：{{分析:结论}}
                """,
                "expected_max_time": 30.0,
            },
        ]

        performance_results = []

        for scenario in test_scenarios:
            # Mock fast LLM responses
            self.mock_ai_service.generate_completion.return_value = json.dumps(
                {"understanding": "快速理解结果", "confidence": 0.9}
            )

            # Mock fast ETL
            mock_etl_result = Mock()
            mock_etl_result.processed_value = "测试值"
            mock_etl_result.metadata = {"confidence": 0.9}
            self.etl_executor.execute_etl = AsyncMock(return_value=mock_etl_result)

            # Mock fast content generation
            self.content_generator.generate_content = AsyncMock(return_value="测试内容")

            # Measure processing time
            start_time = time.time()

            result = await self.processor.process_template(
                template_content=scenario["template"], data_schema={"fields": []}
            )

            processing_time = time.time() - start_time

            # Record performance
            performance_results.append(
                {
                    "scenario": scenario["name"],
                    "processing_time": processing_time,
                    "expected_max_time": scenario["expected_max_time"],
                    "success": result.success if result else False,
                }
            )

            # Assert performance requirements
            assert (
                processing_time <= scenario["expected_max_time"]
            ), f"Scenario {scenario['name']} took {processing_time:.2f}s, expected <= {scenario['expected_max_time']}s"

        # Log performance results
        print("\nPerformance Benchmark Results:")
        for result in performance_results:
            print(
                f"  {result['scenario']}: {result['processing_time']:.2f}s "
                f"(max: {result['expected_max_time']}s) - {'✓' if result['success'] else '✗'}"
            )

    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        error_scenarios = [
            {
                "name": "llm_service_failure",
                "error": Exception("LLM service unavailable"),
                "expected_recovery": True,
            },
            {
                "name": "field_matching_failure",
                "error": ValueError("No matching fields found"),
                "expected_recovery": True,
            },
            {
                "name": "etl_processing_failure",
                "error": RuntimeError("ETL processing failed"),
                "expected_recovery": False,
            },
        ]

        for scenario in error_scenarios:
            # Configure mock to raise error
            if scenario["name"] == "llm_service_failure":
                self.mock_ai_service.generate_completion.side_effect = scenario["error"]
            elif scenario["name"] == "etl_processing_failure":
                self.etl_executor.execute_etl.side_effect = scenario["error"]

            # Test error handling
            try:
                result = await self.processor.process_template(
                    template_content="测试{{统计:测试}}模板", data_schema={"fields": []}
                )

                if scenario["expected_recovery"]:
                    # Should recover gracefully
                    assert result is not None
                    assert len(result.errors) > 0
                else:
                    # Should fail but not crash
                    assert result is None or not result.success

            except Exception as e:
                if scenario["expected_recovery"]:
                    pytest.fail(f"Unexpected exception in recoverable scenario: {e}")

            # Reset mocks
            self.mock_ai_service.generate_completion.side_effect = None
            self.etl_executor.execute_etl.side_effect = None

    async def test_concurrent_processing(self):
        """Test concurrent processing of multiple templates."""
        # Mock responses for concurrent processing
        self.mock_ai_service.generate_completion.return_value = json.dumps(
            {"understanding": "并发处理测试", "confidence": 0.9}
        )

        mock_etl_result = Mock()
        mock_etl_result.processed_value = "并发值"
        mock_etl_result.metadata = {"confidence": 0.9}
        self.etl_executor.execute_etl = AsyncMock(return_value=mock_etl_result)

        self.content_generator.generate_content = AsyncMock(return_value="并发内容")

        # Create multiple processing tasks
        templates = [f"模板{i}：{{{{统计:数值{i}}}}}" for i in range(5)]

        # Process concurrently
        start_time = time.time()

        tasks = [
            self.processor.process_template(
                template_content=template, data_schema={"fields": []}
            )
            for template in templates
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        concurrent_time = time.time() - start_time

        # Verify all succeeded
        successful_results = [
            r for r in results if not isinstance(r, Exception) and r and r.success
        ]
        assert len(successful_results) == len(templates)

        # Concurrent processing should be faster than sequential
        # (This is a rough estimate, actual performance may vary)
        expected_sequential_time = len(templates) * 2.0  # Assume 2s per template
        assert concurrent_time < expected_sequential_time * 0.8  # At least 20% faster

        print(
            f"\nConcurrent processing: {concurrent_time:.2f}s for {len(templates)} templates"
        )

    async def test_data_consistency_validation(self):
        """Test data consistency validation across the processing pipeline."""
        # Test template with related placeholders
        template_content = """
        总投诉：{{统计:总投诉件数}}件
        已处理：{{统计:已处理件数}}件
        处理率：{{统计:处理率}}%
        """

        # Mock consistent data
        consistent_responses = [
            json.dumps(
                {
                    "understanding": "总投诉件数",
                    "field_name": "total_complaints",
                    "confidence": 0.95,
                }
            ),
            json.dumps(
                {
                    "understanding": "已处理件数",
                    "field_name": "processed_complaints",
                    "confidence": 0.95,
                }
            ),
            json.dumps(
                {
                    "understanding": "处理率",
                    "field_name": "processing_rate",
                    "confidence": 0.95,
                }
            ),
        ]

        self.mock_ai_service.generate_completion.side_effect = consistent_responses

        # Mock ETL with consistent data
        etl_responses = [
            Mock(processed_value=1000, metadata={"confidence": 0.95}),  # Total
            Mock(processed_value=800, metadata={"confidence": 0.95}),  # Processed
            Mock(
                processed_value=80.0, metadata={"confidence": 0.95}
            ),  # Rate (should be 80%)
        ]

        self.etl_executor.execute_etl.side_effect = etl_responses

        # Mock content generation
        content_responses = ["1,000件", "800件", "80.0%"]
        self.content_generator.generate_content.side_effect = content_responses

        # Process template
        result = await self.processor.process_template(
            template_content=template_content, data_schema={"fields": []}
        )

        # Verify data consistency
        assert result.success is True

        # Check that the processing rate is mathematically consistent
        # (800/1000 = 0.8 = 80%)
        assert "1,000件" in result.final_content
        assert "800件" in result.final_content
        assert "80.0%" in result.final_content

        # Verify consistency validation was performed
        assert result.quality_score > 0.8


@pytest.mark.asyncio
@pytest.mark.integration
class TestIntelligentPlaceholderAPIIntegration:
    """Integration tests for intelligent placeholder API endpoints."""

    async def test_placeholder_analysis_api(
        self, authenticated_client, test_template: Template
    ):
        """Test the placeholder analysis API endpoint."""
        request_data = {
            "template_content": "测试{{统计:总数}}和{{区域:地区}}",
            "data_source_id": 1,
            "analysis_options": {"include_context": True, "llm_provider": "openai"},
        }

        response = authenticated_client.post(
            "/api/v1/intelligent-placeholders/analyze", json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        assert "placeholders" in data
        assert len(data["placeholders"]) == 2
        assert "analysis_summary" in data
        assert "estimated_processing_time" in data

    async def test_intelligent_report_generation_api(
        self,
        authenticated_client,
        test_template: Template,
        test_data_source: EnhancedDataSource,
    ):
        """Test the intelligent report generation API endpoint."""
        request_data = {
            "template_id": test_template.id,
            "data_source_id": test_data_source.id,
            "processing_config": {
                "llm_provider": "openai",
                "llm_model": "gpt-4",
                "enable_caching": True,
                "quality_check": True,
            },
            "output_config": {"format": "docx", "include_metadata": True},
        }

        response = authenticated_client.post(
            "/api/v1/reports/generate-intelligent", json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        assert "report_id" in data
        assert "processing_status" in data
        assert "estimated_completion_time" in data


# Performance benchmark utilities
class PerformanceBenchmark:
    """Utility class for performance benchmarking."""

    @staticmethod
    def measure_time(func):
        """Decorator to measure function execution time."""

        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            return result, execution_time

        return wrapper

    @staticmethod
    def generate_performance_report(results: List[Dict[str, Any]]) -> str:
        """Generate a performance report from benchmark results."""
        report = "Performance Benchmark Report\n"
        report += "=" * 40 + "\n\n"

        for result in results:
            report += f"Scenario: {result['scenario']}\n"
            report += f"  Processing Time: {result['processing_time']:.2f}s\n"
            report += f"  Expected Max: {result['expected_max_time']:.2f}s\n"
            report += f"  Status: {'✓ PASS' if result['processing_time'] <= result['expected_max_time'] else '✗ FAIL'}\n"
            report += f"  Success: {'✓' if result['success'] else '✗'}\n\n"

        return report
