"""
Unit tests for report_generation service module
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, mock_open
from datetime import datetime
import os
import tempfile
import json

from app.services.report_generation import (
    ReportGenerationService,
    ReportGenerationStatus,
    ReportCompositionService,
    ReportQualityChecker,
    QualityCheckResult,
    QualityMetrics,
    QualityIssue,
    QualityIssueType,
    QualitySeverity,
    LanguageAnalyzer,
    DataConsistencyValidator
)


class TestReportGenerationService:
    """Test ReportGenerationService class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        self.service = ReportGenerationService(self.mock_db)

    @patch('app.services.report_generation.generator.crud')
    @patch('app.services.report_generation.generator.os.path.exists')
    def test_generate_report_success(self, mock_exists, mock_crud):
        """Test successful report generation"""
        # Setup mocks
        mock_task = Mock()
        mock_task.name = "test_task"
        mock_template = Mock()
        mock_template.file_path = "/path/to/template.docx"
        mock_data_source = Mock()
        
        mock_crud.task.get.return_value = mock_task
        mock_crud.template.get.return_value = mock_template
        mock_crud.data_source.get.return_value = mock_data_source
        mock_exists.return_value = True
        
        # Mock template parser
        self.service.template_parser.parse = Mock(return_value={
            "placeholders": [
                {"name": "test_placeholder", "type": "scalar", "description": "test"}
            ]
        })
        
        # Mock tool dispatcher
        self.service.tool_dispatcher.dispatch = Mock(return_value="test_value")
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data="Template content {{test_placeholder}}")):
            with patch('app.services.report_generation.generator.os.makedirs'):
                # Mock word generator
                self.service.word_generator.generate_report_from_content = Mock()
                
                result = self.service.generate_report(
                    task_id=1,
                    template_id=1,
                    data_source_id=1
                )
        
        assert result["status"] == ReportGenerationStatus.COMPLETED
        assert result["task_id"] == 1
        assert result["template_id"] == 1
        assert result["data_source_id"] == 1
        assert result["placeholders_processed"] == 1
        assert result["output_path"] is not None

    @patch('app.services.report_generation.generator.crud')
    def test_generate_report_task_not_found(self, mock_crud):
        """Test report generation with missing task"""
        mock_crud.task.get.return_value = None
        
        with pytest.raises(ValueError, match="Task not found"):
            self.service.generate_report(
                task_id=999,
                template_id=1,
                data_source_id=1
            )

    @patch('app.services.report_generation.generator.crud')
    def test_generate_report_template_not_found(self, mock_crud):
        """Test report generation with missing template"""
        mock_task = Mock()
        mock_crud.task.get.return_value = mock_task
        mock_crud.template.get.return_value = None
        
        with pytest.raises(ValueError, match="Template not found"):
            self.service.generate_report(
                task_id=1,
                template_id=999,
                data_source_id=1
            )

    @pytest.mark.asyncio
    @patch('app.services.report_generation.generator.crud')
    async def test_preview_report_data(self, mock_crud):
        """Test report data preview"""
        # Setup mocks
        mock_template = Mock()
        mock_template.name = "Test Template"
        mock_template.file_path = "/path/to/template.docx"
        mock_data_source = Mock()
        mock_data_source.name = "Test Data Source"
        
        mock_crud.template.get.return_value = mock_template
        mock_crud.data_source.get.return_value = mock_data_source
        
        # Mock template parser
        self.service.template_parser.parse = Mock(return_value={
            "placeholders": [
                {"name": "test_placeholder", "type": "scalar", "description": "test desc"}
            ]
        })
        
        # Mock data retrieval
        import pandas as pd
        mock_df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        self.service.data_retrieval.fetch_data = AsyncMock(return_value=mock_df)
        
        result = await self.service.preview_report_data(
            template_id=1,
            data_source_id=1
        )
        
        assert result["template_id"] == 1
        assert result["data_source_id"] == 1
        assert result["template_name"] == "Test Template"
        assert result["data_source_name"] == "Test Data Source"
        assert len(result["placeholders"]) == 1
        assert result["sample_data_shape"]["rows"] == 3
        assert result["sample_data_shape"]["columns"] == 2

    @patch('app.services.report_generation.generator.crud')
    @patch('app.services.report_generation.generator.os.path.exists')
    def test_validate_report_configuration_valid(self, mock_exists, mock_crud):
        """Test valid report configuration validation"""
        # Setup mocks
        mock_template = Mock()
        mock_template.file_path = "/path/to/template.docx"
        mock_data_source = Mock()
        mock_data_source.source_type.value = "csv"
        mock_data_source.file_path = "/path/to/data.csv"
        
        mock_crud.template.get.return_value = mock_template
        mock_crud.data_source.get.return_value = mock_data_source
        mock_exists.return_value = True
        
        # Mock template parser
        self.service.template_parser.parse = Mock(return_value={
            "placeholders": [{"name": "test", "type": "scalar"}]
        })
        
        # Mock AI service health check
        self.service.ai_service.health_check = Mock(return_value={"status": "healthy"})
        
        result = self.service.validate_report_configuration(
            template_id=1,
            data_source_id=1
        )
        
        assert result["valid"] is True
        assert result["template_id"] == 1
        assert result["data_source_id"] == 1
        assert len(result["errors"]) == 0

    @patch('app.services.report_generation.generator.crud')
    def test_validate_report_configuration_invalid(self, mock_crud):
        """Test invalid report configuration validation"""
        # Template not found
        mock_crud.template.get.return_value = None
        mock_crud.data_source.get.return_value = Mock()
        
        result = self.service.validate_report_configuration(
            template_id=999,
            data_source_id=1
        )
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "Template not found" in result["errors"][0]


class TestReportCompositionService:
    """Test ReportCompositionService class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = ReportCompositionService()

    def test_compose_report_simple(self):
        """Test simple report composition"""
        template_content = "Total count: {{count}}"
        results = {"{{count}}": "123"}
        
        composed = self.service.compose_report(template_content, results)
        
        assert composed == "Total count: 123"

    def test_compose_report_multiple_placeholders(self):
        """Test composition with multiple placeholders"""
        template_content = "Region: {{region}}, Count: {{count}}, Rate: {{rate}}"
        results = {
            "{{region}}": "云南省",
            "{{count}}": "456",
            "{{rate}}": "78.9%"
        }
        
        composed = self.service.compose_report(template_content, results)
        
        assert "云南省" in composed
        assert "456" in composed
        assert "78.9%" in composed

    def test_compose_report_with_base64_image(self):
        """Test composition with base64 image"""
        template_content = "Chart: {{chart}}"
        base64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        results = {"{{chart}}": base64_data}
        
        composed = self.service.compose_report(template_content, results)
        
        assert '<img src="data:image/png;base64,' in composed
        assert base64_data in composed

    def test_is_base64_detection(self):
        """Test base64 detection"""
        # Valid base64 image
        valid_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        assert self.service.is_base64(valid_base64) is True
        
        # Regular text
        regular_text = "This is just text"
        assert self.service.is_base64(regular_text) is False
        
        # Non-string input
        assert self.service.is_base64(123) is False
        assert self.service.is_base64(None) is False

class TestLanguageAnalyzer:
    """Test LanguageAnalyzer class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = LanguageAnalyzer()

    def test_analyze_text_basic(self):
        """Test basic text analysis"""
        text = "这是第一句话。这是第二句话！这是第三句话？"
        result = self.analyzer.analyze_text(text)
        
        assert result["word_count"] > 0
        assert result["sentence_count"] == 3
        assert result["paragraph_count"] >= 1
        assert result["avg_sentence_length"] > 0
        assert result["readability_score"] >= 0

    def test_analyze_text_empty(self):
        """Test analysis of empty text"""
        result = self.analyzer.analyze_text("")
        
        assert result["word_count"] == 0
        assert result["sentence_count"] == 0
        assert result["readability_score"] == 0

    def test_split_sentences(self):
        """Test sentence splitting"""
        text = "第一句。第二句！第三句？"
        sentences = self.analyzer._split_sentences(text)
        
        assert len(sentences) == 3
        assert "第一句" in sentences[0]
        assert "第二句" in sentences[1]
        assert "第三句" in sentences[2]

    def test_check_fluency(self):
        """Test fluency checking"""
        sentences = ["这是一个正常长度的句子。", "短。", "这是一个非常非常非常长的句子" * 10]
        issues = self.analyzer._check_fluency(sentences)
        
        # Should detect short and long sentences
        assert len(issues) >= 2
        issue_types = [issue["type"] for issue in issues]
        assert "short_sentence" in issue_types
        assert "long_sentence" in issue_types

    def test_calculate_readability(self):
        """Test readability calculation"""
        text = "这是一个测试文本。"
        sentences = ["这是一个测试文本。"]
        
        score = self.analyzer._calculate_readability(text, sentences)
        
        assert 0 <= score <= 100
        assert isinstance(score, float)


class TestDataConsistencyValidator:
    """Test DataConsistencyValidator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.validator = DataConsistencyValidator()

    def test_validate_report_basic(self):
        """Test basic report validation"""
        content = "报告显示总数为1,234件，完成率为85.5%。"
        issues = self.validator.validate_report(content)
        
        # Should not have major issues with valid data
        assert isinstance(issues, list)

    def test_extract_numbers(self):
        """Test number extraction"""
        text = "总数1,234件，平均值56.78，最大值999"
        numbers = self.validator._extract_numbers(text)
        
        assert len(numbers) >= 3
        # Check that numbers are extracted correctly
        values = [num[1] for num in numbers]
        assert 1234.0 in values
        assert 56.78 in values
        assert 999.0 in values

    def test_extract_percentages(self):
        """Test percentage extraction"""
        text = "完成率85.5%，增长率12.3%，错误率0.1%"
        percentages = self.validator._extract_percentages(text)
        
        assert len(percentages) == 3
        values = [pct[1] for pct in percentages]
        assert 85.5 in values
        assert 12.3 in values
        assert 0.1 in values

    def test_check_percentage_consistency(self):
        """Test percentage consistency checking"""
        # Valid percentages
        valid_percentages = [("85.5%", 85.5, "context")]
        issues = self.validator._check_percentage_consistency(valid_percentages)
        assert len(issues) == 0
        
        # Invalid percentages
        invalid_percentages = [("150%", 150.0, "context"), ("-5%", -5.0, "context")]
        issues = self.validator._check_percentage_consistency(invalid_percentages)
        assert len(issues) == 2

    def test_extract_dates(self):
        """Test date extraction"""
        text = "2024年3月的数据显示，4月15日完成统计。"
        dates = self.validator._extract_dates(text)
        
        assert len(dates) >= 1
        assert any("2024年3月" in date for date in dates)

    def test_check_date_consistency(self):
        """Test date consistency checking"""
        # Valid dates
        valid_dates = ["2024年3月", "2023年12月"]
        issues = self.validator._check_date_consistency(valid_dates)
        assert len(issues) == 0
        
        # Invalid dates
        invalid_dates = ["1800年3月", "2024年15月"]
        issues = self.validator._check_date_consistency(invalid_dates)
        assert len(issues) >= 1