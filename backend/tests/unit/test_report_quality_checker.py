"""
Tests for Report Quality Checker Service
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from app.services.report_generation.quality_checker import (
    DataConsistencyValidator,
    LanguageAnalyzer,
    QualityIssue,
    QualityIssueType,
    QualitySeverity,
    ReportQualityChecker,
    quick_quality_check,
)


class TestLanguageAnalyzer:
    def setup_method(self):
        self.analyzer = LanguageAnalyzer()

    def test_analyze_text_basic(self):
        text = "这是一个测试报告。报告包含多个句子。每个句子都有不同的内容。"
        result = self.analyzer.analyze_text(text)

        assert result["word_count"] > 0
        assert result["sentence_count"] == 3
        assert result["paragraph_count"] == 1
        assert result["avg_sentence_length"] > 0
        assert "readability_score" in result

    def test_split_sentences(self):
        text = "第一句话。第二句话！第三句话？"
        sentences = self.analyzer._split_sentences(text)

        assert len(sentences) == 3
        assert sentences[0] == "第一句话"
        assert sentences[1] == "第二句话"
        assert sentences[2] == "第三句话"

    def test_check_fluency_short_sentence(self):
        sentences = ["短句", "这是一个正常长度的句子", "另一个正常句子"]
        issues = self.analyzer._check_fluency(sentences)

        assert len(issues) > 0
        assert issues[0]["type"] == "short_sentence"


class TestDataConsistencyValidator:
    def setup_method(self):
        self.validator = DataConsistencyValidator()

    def test_extract_numbers(self):
        text = "总数为1,234个，增长了56.7%，达到了890万。"
        numbers = self.validator._extract_numbers(text)

        assert len(numbers) >= 2  # Should find 1,234 and 56.7
        assert any(num[1] == 1234 for num in numbers)

    def test_extract_percentages(self):
        text = "增长了25.5%，下降了10%，总体上升了3.2%。"
        percentages = self.validator._extract_percentages(text)

        assert len(percentages) == 3
        assert any(pct[1] == 25.5 for pct in percentages)
        assert any(pct[1] == 10.0 for pct in percentages)

    def test_check_percentage_consistency_invalid(self):
        percentages = [("150%", 150.0, "增长了150%"), ("-5%", -5.0, "下降了-5%")]
        issues = self.validator._check_percentage_consistency(percentages)

        assert len(issues) == 2
        assert any(issue.description.startswith("百分比超过100%") for issue in issues)
        assert any(issue.description.startswith("百分比为负数") for issue in issues)


@pytest.fixture
def mock_db():
    return Mock()


@pytest.fixture
def quality_checker(mock_db):
    with patch("app.services.report_quality_checker.LLMProviderManager"):
        checker = ReportQualityChecker(mock_db)
        return checker


class TestReportQualityChecker:
    def test_check_report_quality_basic(self, quality_checker):
        report_content = "这是一个测试报告。报告质量良好。数据显示增长了25%。"

        result = quality_checker.check_report_quality(
            report_content, enable_llm_analysis=False
        )

        assert result.metrics.overall_score >= 0
        assert result.metrics.word_count > 0
        assert isinstance(result.issues, list)
        assert isinstance(result.suggestions, list)
        assert result.processing_time >= 0

    def test_quality_feedback_generation(self, quality_checker):
        # Create a mock result
        from app.services.report_quality_checker import (
            QualityCheckResult,
            QualityMetrics,
        )

        metrics = QualityMetrics(
            overall_score=85.0,
            fluency_score=90.0,
            consistency_score=80.0,
            completeness_score=85.0,
            accuracy_score=88.0,
            readability_score=82.0,
            word_count=100,
            sentence_count=5,
            paragraph_count=2,
            avg_sentence_length=20.0,
            complex_words_ratio=0.1,
        )

        result = QualityCheckResult(
            metrics=metrics,
            issues=[],
            suggestions=["建议1", "建议2"],
            processing_time=1.5,
            timestamp=datetime.now(),
        )

        feedback = quality_checker.get_quality_feedback(result)

        assert feedback["overall_rating"] == "良好"
        assert "summary" in feedback
        assert "metrics_breakdown" in feedback
        assert len(feedback["recommendations"]) <= 5


def test_quick_quality_check(mock_db):
    with patch(
        "app.services.report_quality_checker.ReportQualityChecker"
    ) as mock_checker_class:
        mock_checker = Mock()
        mock_checker_class.return_value = mock_checker

        # Mock the return value
        from app.services.report_quality_checker import (
            QualityCheckResult,
            QualityMetrics,
        )

        mock_result = QualityCheckResult(
            metrics=QualityMetrics(
                overall_score=75.0,
                fluency_score=80.0,
                consistency_score=70.0,
                completeness_score=75.0,
                accuracy_score=78.0,
                readability_score=72.0,
                word_count=50,
                sentence_count=3,
                paragraph_count=1,
                avg_sentence_length=16.7,
                complex_words_ratio=0.05,
            ),
            issues=[],
            suggestions=[],
            processing_time=0.5,
            timestamp=datetime.now(),
        )
        mock_checker.check_report_quality.return_value = mock_result

        result = quick_quality_check("测试内容", mock_db)

        assert result.metrics.overall_score == 75.0
        mock_checker.check_report_quality.assert_called_once()
