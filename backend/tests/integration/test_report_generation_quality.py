"""
Report Generation Quality Tests for Intelligent Placeholder Processing.

Tests the quality of generated reports including:
- Content accuracy and consistency
- Language fluency and readability
- Format compliance and structure
- Data visualization quality
- Multi-language support
- Accessibility compliance
"""

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from app.services.ai_integration.llm_service import AIService
from app.services.ai_integration.chart_generator import ChartGenerator
from app.services.intelligent_placeholder.adapter import (
    IntelligentPlaceholderProcessor,
)
from app.services.ai_integration.content_generator import ContentGenerator
from app.services.report_generation.quality_checker import ReportQualityChecker


@dataclass
class QualityMetrics:
    """Quality metrics for report evaluation."""

    content_accuracy: float
    language_fluency: float
    format_compliance: float
    data_consistency: float
    visual_quality: float
    accessibility_score: float
    overall_score: float


@pytest.mark.asyncio
@pytest.mark.integration
class TestReportGenerationQuality:
    """Test the quality of generated reports."""

    @pytest.fixture(autouse=True)
    async def setup_quality_testing(self):
        """Set up quality testing environment."""
        # Mock AI service for quality testing
        self.mock_ai_service = Mock(spec=AIService)
        self.mock_ai_service.generate_completion = AsyncMock()

        # Initialize quality-focused services
        self.quality_checker = ReportQualityChecker(self.mock_ai_service)
        self.content_generator = ContentGenerator(None)
        self.chart_generator = Mock(spec=ChartGenerator)

        # Mock chart generation
        self.chart_generator.generate_chart = AsyncMock(
            return_value={
                "chart_path": "/tmp/test_chart.png",
                "chart_type": "line",
                "quality_score": 0.9,
            }
        )

    @pytest.fixture
    def high_quality_template(self) -> str:
        """High-quality template for testing."""
        return """{{周期:2024年第一季度}}{{区域:云南省}}投诉数据分析报告

一、总体情况概述
本季度，{{区域:云南省}}共收到各类投诉{{统计:总投诉件数}}件，较去年同期{{统计:同比变化率}}%。投诉主要集中在{{区域:主要投诉地区}}，占总投诉量的{{统计:主要地区占比}}%。

二、投诉渠道分析
微信小程序投诉{{统计:微信投诉件数}}件，占比{{统计:微信投诉占比}}%；
热线投诉{{统计:热线投诉件数}}件，占比{{统计:热线投诉占比}}%。

三、处理效率指标
- 平均响应时长：{{统计:平均响应时长}}分钟
- 24小时办结率：{{统计:24小时办结率}}%
- 处理满意度：{{统计:处理满意度}}分（满分5分）

四、趋势分析
{{图表:投诉趋势图}}

五、区域分布
{{图表:区域分布图}}

六、分析结论
{{分析:综合分析结论}}

七、改进建议
{{分析:改进建议}}
"""

    @pytest.fixture
    def sample_data_context(self) -> Dict[str, Any]:
        """Sample data context for quality testing."""
        return {
            "period": "2024年第一季度",
            "region": "云南省",
            "statistics": {
                "总投诉件数": 2141,
                "同比变化率": 8.68,
                "微信投诉件数": 356,
                "微信投诉占比": 16.63,
                "热线投诉件数": 1785,
                "热线投诉占比": 83.37,
                "平均响应时长": 15.41,
                "24小时办结率": 50.21,
                "处理满意度": 4.01,
                "主要地区占比": 35.2,
            },
            "regions": {"主要投诉地区": "昆明市"},
            "trends": [
                {"month": "2024-01", "complaints": 720},
                {"month": "2024-02", "complaints": 680},
                {"month": "2024-03", "complaints": 741},
            ],
        }

    async def test_content_accuracy_validation(
        self, high_quality_template: str, sample_data_context: Dict[str, Any]
    ):
        """Test content accuracy in generated reports."""
        # Mock high-quality LLM responses
        accurate_responses = [
            json.dumps(
                {
                    "semantic_meaning": "需要获取总投诉件数统计",
                    "data_requirements": ["总投诉件数"],
                    "confidence_score": 0.98,
                }
            ),
            json.dumps(
                {
                    "field_suggestions": [
                        {
                            "field_name": "total_complaints",
                            "confidence": 0.95,
                            "transformation_needed": False,
                        }
                    ]
                }
            ),
            "2,141件",  # Accurate formatted content
            json.dumps(
                {
                    "accuracy_score": 0.96,
                    "data_consistency": 0.94,
                    "factual_correctness": 0.98,
                    "issues": [],
                }
            ),
        ]

        self.mock_ai_service.generate_completion.side_effect = accurate_responses

        # Process template with accurate data
        processor = IntelligentPlaceholderProcessor(
            llm_service=Mock(),
            field_matcher=Mock(),
            etl_executor=Mock(),
            content_generator=self.content_generator,
            quality_checker=self.quality_checker,
        )

        # Mock ETL results with accurate data
        processor.etl_executor.execute_etl = AsyncMock(
            return_value=Mock(
                processed_value=2141,
                metadata={"confidence": 0.98, "source": "verified_database"},
            )
        )

        result = await processor.process_template(
            template_content=high_quality_template, data_context=sample_data_context
        )

        # Verify content accuracy
        assert result.success is True
        assert result.quality_score >= 0.9

        # Check specific accuracy metrics
        assert "2,141件" in result.final_content
        assert "云南省" in result.final_content
        assert "2024年第一季度" in result.final_content

        # Verify no data inconsistencies
        assert len(result.quality_issues) == 0

    async def test_language_fluency_assessment(self, high_quality_template: str):
        """Test language fluency in generated reports."""
        # Mock fluency-focused LLM responses
        fluency_responses = [
            json.dumps({"understanding": "语言流畅性测试", "confidence": 0.9}),
            "本季度投诉数据呈现稳定增长态势，各项指标均在合理范围内。",  # Fluent content
            json.dumps(
                {
                    "language_fluency": 0.95,
                    "readability_score": 0.92,
                    "grammar_correctness": 0.97,
                    "style_consistency": 0.94,
                    "suggestions": [
                        "语言表达自然流畅",
                        "句式结构合理",
                        "专业术语使用准确",
                    ],
                }
            ),
        ]

        self.mock_ai_service.generate_completion.side_effect = fluency_responses

        # Test fluency assessment
        fluency_result = await self.quality_checker.assess_language_fluency(
            content="本季度投诉数据呈现稳定增长态势，各项指标均在合理范围内。",
            language="zh-CN",
        )

        # Verify fluency metrics
        assert fluency_result.language_fluency >= 0.9
        assert fluency_result.readability_score >= 0.9
        assert fluency_result.grammar_correctness >= 0.95
        assert len(fluency_result.suggestions) > 0

    async def test_format_compliance_validation(self, high_quality_template: str):
        """Test format compliance in generated reports."""
        # Generate report with format requirements
        format_requirements = {
            "document_type": "docx",
            "font_family": "宋体",
            "font_size": 12,
            "line_spacing": 1.5,
            "margin": {"top": 2.54, "bottom": 2.54, "left": 3.17, "right": 3.17},
            "heading_styles": {
                "h1": {"font_size": 16, "bold": True},
                "h2": {"font_size": 14, "bold": True},
                "h3": {"font_size": 12, "bold": True},
            },
            "table_style": "professional",
            "chart_style": "business",
        }

        # Mock format compliance check
        self.mock_ai_service.generate_completion.return_value = json.dumps(
            {
                "format_compliance": 0.94,
                "structure_score": 0.96,
                "style_consistency": 0.92,
                "accessibility_score": 0.88,
                "compliance_issues": [
                    {
                        "type": "minor",
                        "description": "建议增加图表标题字体大小",
                        "location": "图表部分",
                    }
                ],
            }
        )

        # Test format compliance
        compliance_result = await self.quality_checker.check_format_compliance(
            content=high_quality_template, format_requirements=format_requirements
        )

        # Verify format compliance
        assert compliance_result.format_compliance >= 0.9
        assert compliance_result.structure_score >= 0.9
        assert compliance_result.accessibility_score >= 0.8
        assert len(compliance_result.compliance_issues) <= 2  # Minor issues only

    async def test_data_consistency_validation(self):
        """Test data consistency across the report."""
        # Test data with intentional consistency relationships
        consistent_data = {
            "总投诉件数": 1000,
            "已处理件数": 800,
            "未处理件数": 200,
            "处理率": 80.0,  # Should be 800/1000 = 80%
            "微信投诉": 300,
            "热线投诉": 700,
            "微信占比": 30.0,  # Should be 300/1000 = 30%
            "热线占比": 70.0,  # Should be 700/1000 = 70%
        }

        # Mock consistency validation
        self.mock_ai_service.generate_completion.return_value = json.dumps(
            {
                "data_consistency": 0.98,
                "mathematical_accuracy": 0.99,
                "logical_coherence": 0.97,
                "consistency_checks": [
                    {
                        "check": "总数与分项之和",
                        "status": "通过",
                        "expected": 1000,
                        "actual": 1000,
                    },
                    {
                        "check": "百分比计算",
                        "status": "通过",
                        "expected": 80.0,
                        "actual": 80.0,
                    },
                ],
                "inconsistencies": [],
            }
        )

        # Test consistency validation
        consistency_result = await self.quality_checker.validate_data_consistency(
            data_points=consistent_data
        )

        # Verify consistency
        assert consistency_result.data_consistency >= 0.95
        assert consistency_result.mathematical_accuracy >= 0.95
        assert len(consistency_result.inconsistencies) == 0

    async def test_visual_quality_assessment(self):
        """Test quality of generated charts and visualizations."""
        # Mock chart generation with quality metrics
        chart_configs = [
            {
                "type": "line",
                "title": "投诉趋势图",
                "data": [
                    {"month": "2024-01", "complaints": 720},
                    {"month": "2024-02", "complaints": 680},
                    {"month": "2024-03", "complaints": 741},
                ],
            },
            {
                "type": "pie",
                "title": "投诉渠道分布",
                "data": [
                    {"channel": "微信", "count": 356},
                    {"channel": "热线", "count": 1785},
                ],
            },
            {
                "type": "bar",
                "title": "地区投诉分布",
                "data": [
                    {"region": "昆明市", "count": 750},
                    {"region": "大理州", "count": 420},
                    {"region": "丽江市", "count": 380},
                ],
            },
        ]

        visual_quality_results = []

        for chart_config in chart_configs:
            # Mock chart generation
            self.chart_generator.generate_chart.return_value = {
                "chart_path": f"/tmp/{chart_config['type']}_chart.png",
                "chart_type": chart_config["type"],
                "quality_metrics": {
                    "visual_clarity": 0.92,
                    "color_scheme": 0.89,
                    "label_readability": 0.94,
                    "data_representation": 0.96,
                    "accessibility": 0.87,
                },
            }

            # Generate and assess chart
            chart_result = await self.chart_generator.generate_chart(
                chart_type=chart_config["type"],
                data=chart_config["data"],
                title=chart_config["title"],
            )

            # Assess visual quality
            quality_metrics = chart_result["quality_metrics"]
            overall_visual_quality = sum(quality_metrics.values()) / len(
                quality_metrics
            )

            visual_quality_results.append(
                {
                    "chart_type": chart_config["type"],
                    "overall_quality": overall_visual_quality,
                    "metrics": quality_metrics,
                }
            )

        # Verify visual quality standards
        for result in visual_quality_results:
            assert result["overall_quality"] >= 0.85
            assert result["metrics"]["visual_clarity"] >= 0.8
            assert result["metrics"]["accessibility"] >= 0.8

        print(f"\nVisual Quality Assessment:")
        for result in visual_quality_results:
            print(f"  {result['chart_type']}: {result['overall_quality']:.2f}")

    async def test_multi_language_support_quality(self):
        """Test quality of multi-language report generation."""
        languages = ["zh-CN", "en-US", "zh-TW"]

        template_multilang = {
            "zh-CN": "{{统计:总投诉件数}}件投诉，处理率{{统计:处理率}}%",
            "en-US": "{{statistic:total_complaints}} complaints, processing rate {{statistic:processing_rate}}%",
            "zh-TW": "{{統計:總投訴件數}}件投訴，處理率{{統計:處理率}}%",
        }

        multilang_results = []

        for lang in languages:
            # Mock language-specific LLM responses
            if lang == "zh-CN":
                response = "2,141件投诉，处理率80.5%"
            elif lang == "en-US":
                response = "2,141 complaints, processing rate 80.5%"
            else:  # zh-TW
                response = "2,141件投訴，處理率80.5%"

            self.mock_ai_service.generate_completion.return_value = response

            # Mock quality assessment for each language
            quality_response = json.dumps(
                {
                    "language_quality": 0.91,
                    "cultural_appropriateness": 0.89,
                    "terminology_accuracy": 0.93,
                    "localization_score": 0.87,
                }
            )

            # Test language-specific processing
            result = await self.quality_checker.assess_multilingual_quality(
                content=response, target_language=lang, domain="government_complaints"
            )

            multilang_results.append(
                {
                    "language": lang,
                    "quality_score": result.get("language_quality", 0.9),
                    "cultural_score": result.get("cultural_appropriateness", 0.9),
                    "terminology_score": result.get("terminology_accuracy", 0.9),
                }
            )

        # Verify multi-language quality
        for result in multilang_results:
            assert result["quality_score"] >= 0.85
            assert result["cultural_score"] >= 0.8
            assert result["terminology_score"] >= 0.85

        print(f"\nMulti-language Quality Assessment:")
        for result in multilang_results:
            print(f"  {result['language']}: quality={result['quality_score']:.2f}")

    async def test_accessibility_compliance(self, high_quality_template: str):
        """Test accessibility compliance of generated reports."""
        accessibility_requirements = {
            "wcag_level": "AA",
            "color_contrast_ratio": 4.5,
            "font_size_minimum": 12,
            "alt_text_required": True,
            "heading_structure": True,
            "table_headers": True,
            "language_declaration": True,
        }

        # Mock accessibility assessment
        self.mock_ai_service.generate_completion.return_value = json.dumps(
            {
                "accessibility_score": 0.92,
                "wcag_compliance": "AA",
                "color_contrast": 0.95,
                "text_readability": 0.89,
                "navigation_structure": 0.94,
                "accessibility_issues": [
                    {
                        "severity": "low",
                        "description": "建议为图表添加更详细的替代文本",
                        "location": "图表部分",
                        "recommendation": "增加数据表格作为图表的文本替代",
                    }
                ],
            }
        )

        # Test accessibility compliance
        accessibility_result = (
            await self.quality_checker.check_accessibility_compliance(
                content=high_quality_template, requirements=accessibility_requirements
            )
        )

        # Verify accessibility standards
        assert accessibility_result.accessibility_score >= 0.85
        assert accessibility_result.wcag_compliance in ["AA", "AAA"]
        assert accessibility_result.color_contrast >= 0.9
        assert len(accessibility_result.accessibility_issues) <= 3  # Minor issues only

    async def test_comprehensive_quality_scoring(
        self, high_quality_template: str, sample_data_context: Dict[str, Any]
    ):
        """Test comprehensive quality scoring system."""
        # Mock comprehensive quality assessment
        comprehensive_responses = [
            json.dumps(
                {
                    "content_accuracy": 0.96,
                    "language_fluency": 0.94,
                    "format_compliance": 0.92,
                    "data_consistency": 0.98,
                    "visual_quality": 0.89,
                    "accessibility_score": 0.87,
                    "overall_score": 0.93,
                    "quality_breakdown": {
                        "factual_correctness": 0.97,
                        "mathematical_accuracy": 0.99,
                        "linguistic_quality": 0.94,
                        "structural_integrity": 0.91,
                        "visual_appeal": 0.88,
                        "user_experience": 0.90,
                    },
                    "improvement_suggestions": [
                        "增强图表的视觉吸引力",
                        "优化表格的可访问性",
                        "考虑添加执行摘要",
                    ],
                }
            )
        ]

        self.mock_ai_service.generate_completion.return_value = comprehensive_responses[
            0
        ]

        # Perform comprehensive quality assessment
        quality_result = await self.quality_checker.comprehensive_quality_assessment(
            content=high_quality_template,
            data_context=sample_data_context,
            assessment_criteria={
                "accuracy_weight": 0.25,
                "fluency_weight": 0.20,
                "format_weight": 0.15,
                "consistency_weight": 0.20,
                "visual_weight": 0.10,
                "accessibility_weight": 0.10,
            },
        )

        # Verify comprehensive quality metrics
        quality_metrics = QualityMetrics(
            content_accuracy=quality_result.get("content_accuracy", 0.9),
            language_fluency=quality_result.get("language_fluency", 0.9),
            format_compliance=quality_result.get("format_compliance", 0.9),
            data_consistency=quality_result.get("data_consistency", 0.9),
            visual_quality=quality_result.get("visual_quality", 0.9),
            accessibility_score=quality_result.get("accessibility_score", 0.9),
            overall_score=quality_result.get("overall_score", 0.9),
        )

        # Assert quality thresholds
        assert quality_metrics.overall_score >= 0.85
        assert quality_metrics.content_accuracy >= 0.9
        assert quality_metrics.language_fluency >= 0.85
        assert quality_metrics.data_consistency >= 0.9

        print(f"\nComprehensive Quality Assessment:")
        print(f"  Overall Score: {quality_metrics.overall_score:.2f}")
        print(f"  Content Accuracy: {quality_metrics.content_accuracy:.2f}")
        print(f"  Language Fluency: {quality_metrics.language_fluency:.2f}")
        print(f"  Format Compliance: {quality_metrics.format_compliance:.2f}")
        print(f"  Data Consistency: {quality_metrics.data_consistency:.2f}")
        print(f"  Visual Quality: {quality_metrics.visual_quality:.2f}")
        print(f"  Accessibility: {quality_metrics.accessibility_score:.2f}")

    async def test_quality_regression_detection(self):
        """Test detection of quality regression in report generation."""
        # Baseline quality metrics
        baseline_quality = {
            "content_accuracy": 0.95,
            "language_fluency": 0.92,
            "format_compliance": 0.90,
            "overall_score": 0.92,
        }

        # Current quality metrics (with regression)
        current_quality = {
            "content_accuracy": 0.87,  # Regression
            "language_fluency": 0.94,  # Improvement
            "format_compliance": 0.85,  # Regression
            "overall_score": 0.89,  # Overall regression
        }

        # Mock regression detection
        self.mock_ai_service.generate_completion.return_value = json.dumps(
            {
                "regression_detected": True,
                "regression_areas": [
                    {
                        "metric": "content_accuracy",
                        "baseline": 0.95,
                        "current": 0.87,
                        "regression_severity": "moderate",
                        "possible_causes": ["数据源质量下降", "LLM模型变更"],
                    },
                    {
                        "metric": "format_compliance",
                        "baseline": 0.90,
                        "current": 0.85,
                        "regression_severity": "minor",
                        "possible_causes": ["模板格式更新", "样式配置变更"],
                    },
                ],
                "improvement_areas": [
                    {
                        "metric": "language_fluency",
                        "baseline": 0.92,
                        "current": 0.94,
                        "improvement": "minor",
                    }
                ],
            }
        )

        # Test regression detection
        regression_result = await self.quality_checker.detect_quality_regression(
            baseline_metrics=baseline_quality,
            current_metrics=current_quality,
            regression_threshold=0.05,
        )

        # Verify regression detection
        assert regression_result.regression_detected is True
        assert len(regression_result.regression_areas) == 2
        assert len(regression_result.improvement_areas) == 1

        # Verify specific regressions
        content_regression = next(
            (
                r
                for r in regression_result.regression_areas
                if r["metric"] == "content_accuracy"
            ),
            None,
        )
        assert content_regression is not None
        assert content_regression["regression_severity"] == "moderate"

    async def test_quality_benchmarking(self):
        """Test quality benchmarking against industry standards."""
        # Industry benchmark data
        industry_benchmarks = {
            "government_reports": {
                "content_accuracy": 0.94,
                "language_fluency": 0.89,
                "format_compliance": 0.92,
                "data_consistency": 0.96,
                "overall_score": 0.93,
            },
            "business_reports": {
                "content_accuracy": 0.91,
                "language_fluency": 0.87,
                "format_compliance": 0.88,
                "data_consistency": 0.93,
                "overall_score": 0.90,
            },
        }

        # Current system performance
        system_performance = {
            "content_accuracy": 0.96,
            "language_fluency": 0.91,
            "format_compliance": 0.89,
            "data_consistency": 0.97,
            "overall_score": 0.93,
        }

        # Mock benchmarking analysis
        self.mock_ai_service.generate_completion.return_value = json.dumps(
            {
                "benchmark_comparison": {
                    "government_reports": {
                        "performance_vs_benchmark": 1.00,  # Equal to benchmark
                        "strengths": ["content_accuracy", "data_consistency"],
                        "improvement_areas": ["format_compliance"],
                        "competitive_position": "meets_standard",
                    },
                    "business_reports": {
                        "performance_vs_benchmark": 1.03,  # Above benchmark
                        "strengths": [
                            "content_accuracy",
                            "language_fluency",
                            "data_consistency",
                        ],
                        "improvement_areas": ["format_compliance"],
                        "competitive_position": "above_standard",
                    },
                },
                "overall_ranking": "competitive",
                "recommendations": [
                    "继续保持内容准确性优势",
                    "提升格式合规性",
                    "考虑针对不同行业优化质量标准",
                ],
            }
        )

        # Test benchmarking
        benchmark_result = await self.quality_checker.benchmark_quality(
            system_metrics=system_performance, industry_benchmarks=industry_benchmarks
        )

        # Verify benchmarking results
        assert benchmark_result.overall_ranking in [
            "competitive",
            "above_average",
            "excellent",
        ]

        gov_comparison = benchmark_result.benchmark_comparison["government_reports"]
        assert (
            gov_comparison["performance_vs_benchmark"] >= 0.95
        )  # At least 95% of benchmark
        assert "content_accuracy" in gov_comparison["strengths"]

        print(f"\nQuality Benchmarking Results:")
        print(f"  Overall Ranking: {benchmark_result.overall_ranking}")
        for category, comparison in benchmark_result.benchmark_comparison.items():
            print(
                f"  {category}: {comparison['performance_vs_benchmark']:.2f} vs benchmark"
            )


@pytest.mark.asyncio
@pytest.mark.integration
class TestReportQualityMetrics:
    """Test specific quality metrics and measurements."""

    async def test_readability_scoring(self):
        """Test readability scoring for generated content."""
        test_texts = [
            {
                "content": "本报告分析了投诉数据的基本情况。数据显示投诉量有所增加。",
                "expected_readability": "high",
                "target_audience": "general_public",
            },
            {
                "content": "基于多元回归分析模型，我们对投诉数据进行了深度挖掘，发现了显著的统计学相关性。",
                "expected_readability": "medium",
                "target_audience": "professionals",
            },
            {
                "content": "通过应用机器学习算法和自然语言处理技术，我们构建了一个复合型的投诉分析框架。",
                "expected_readability": "low",
                "target_audience": "experts",
            },
        ]

        for test_case in test_texts:
            # Mock readability assessment
            mock_ai_service = Mock()
            mock_ai_service.generate_completion = AsyncMock(
                return_value=json.dumps(
                    {
                        "readability_score": (
                            0.85
                            if test_case["expected_readability"] == "high"
                            else 0.65
                        ),
                        "complexity_level": test_case["expected_readability"],
                        "sentence_length_avg": 15.2,
                        "vocabulary_complexity": "moderate",
                        "recommendations": ["保持简洁明了的表达"],
                    }
                )
            )

            quality_checker = ReportQualityChecker(mock_ai_service)

            readability_result = await quality_checker.assess_readability(
                content=test_case["content"],
                target_audience=test_case["target_audience"],
            )

            # Verify readability assessment
            if test_case["expected_readability"] == "high":
                assert readability_result.readability_score >= 0.8
            elif test_case["expected_readability"] == "medium":
                assert 0.6 <= readability_result.readability_score < 0.8
            else:  # low
                assert readability_result.readability_score < 0.7

    async def test_professional_terminology_validation(self):
        """Test validation of professional terminology usage."""
        terminology_tests = [
            {
                "domain": "government_complaints",
                "content": "投诉件数、办结率、满意度评分",
                "expected_accuracy": 0.95,
            },
            {
                "domain": "legal",
                "content": "法律条款、合规性检查、违规处理",
                "expected_accuracy": 0.90,
            },
            {
                "domain": "technical",
                "content": "数据挖掘、机器学习、算法优化",
                "expected_accuracy": 0.88,
            },
        ]

        for test_case in terminology_tests:
            # Mock terminology validation
            mock_ai_service = Mock()
            mock_ai_service.generate_completion = AsyncMock(
                return_value=json.dumps(
                    {
                        "terminology_accuracy": test_case["expected_accuracy"],
                        "validated_terms": ["投诉件数", "办结率", "满意度评分"],
                        "incorrect_terms": [],
                        "suggestions": ["术语使用准确", "符合行业标准"],
                    }
                )
            )

            quality_checker = ReportQualityChecker(mock_ai_service)

            terminology_result = await quality_checker.validate_terminology(
                content=test_case["content"], domain=test_case["domain"]
            )

            # Verify terminology validation
            assert (
                terminology_result.terminology_accuracy
                >= test_case["expected_accuracy"] - 0.05
            )
            assert len(terminology_result.incorrect_terms) == 0
