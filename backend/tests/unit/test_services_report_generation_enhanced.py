"""
Enhanced comprehensive unit tests for report_generation service module
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, mock_open
from datetime import datetime
import os
import tempfile
import json
import uuid
import time

from app.services.report_generation.generator import (
    ReportGenerationService,
    ReportGenerationStatus,
)
from app.services.report_generation.composer import (
    ReportCompositionService,
)
from app.services.report_generation.quality_checker import (
    ReportQualityChecker,
    QualityCheckResult,
    QualityMetrics,
    QualityIssue,
    QualityIssueType,
    QualitySeverity,
    LanguageAnalyzer,
    DataConsistencyValidator,
)


class TestReportGenerationServiceEnhanced:
    """Enhanced tests for ReportGenerationService class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        self.service = ReportGenerationService(self.mock_db)

    @patch('app.services.report_generation.generator.crud')
    @patch('app.services.report_generation.generator.os.path.exists')
    @patch('app.services.report_generation.generator.os.makedirs')
    def test_generate_report_complete_workflow(self, mock_makedirs, mock_exists, mock_crud):
        """Test complete report generation workflow"""
        # Setup comprehensive mocks
        mock_task = Mock()
        mock_task.name = "comprehensive_test_task"
        mock_task.id = 1
        
        mock_template = Mock()
        mock_template.file_path = "/path/to/template.docx"
        mock_template.name = "Test Template"
        
        mock_data_source = Mock()
        mock_data_source.name = "Test Data Source"
        mock_data_source.id = 1
        
        mock_crud.task.get.return_value = mock_task
        mock_crud.template.get.return_value = mock_template
        mock_crud.data_source.get.return_value = mock_data_source
        mock_exists.return_value = True
        
        # Mock template parser with complex placeholders
        complex_placeholders = [
            {
                "name": "total_complaints",
                "type": "scalar",
                "description": "总投诉件数"
            },
            {
                "name": "region_chart",
                "type": "chart",
                "description": "地区分布图"
            },
            {
                "name": "trend_analysis",
                "type": "analysis",
                "description": "趋势分析"
            }
        ]
        self.service.template_parser.parse = Mock(return_value={
            "placeholders": complex_placeholders
        })
        
        # Mock tool dispatcher with different results
        def mock_dispatch(data_source_id, placeholder_type, placeholder_description):
            if placeholder_type == "scalar":
                return "1,234"
            elif placeholder_type == "chart":
                return "base64_chart_data_here"
            elif placeholder_type == "analysis":
                return "趋势分析显示投诉量呈下降趋势"
            return "default_value"
        
        self.service.tool_dispatcher.dispatch = Mock(side_effect=mock_dispatch)
        
        # Mock file operations
        template_content = """
        报告摘要：
        总投诉件数：{{total_complaints}}
        地区分布：[chart:region_chart]
        趋势分析：[analysis:trend_analysis]
        """
        
        with patch('builtins.open', mock_open(read_data=template_content)):
            # Mock word generator
            self.service.word_generator.generate_report_from_content = Mock()
            
            result = self.service.generate_report(
                task_id=1,
                template_id=1,
                data_source_id=1,
                output_dir="test_output"
            )
        
        # Verify comprehensive results
        assert result["status"] == ReportGenerationStatus.COMPLETED
        assert result["task_id"] == 1
        assert result["template_id"] == 1
        assert result["data_source_id"] == 1
        assert result["placeholders_processed"] == 3
        assert result["output_path"] is not None
        assert result["generation_id"] is not None
        assert result["duration_seconds"] is not None
        
        # Verify UUID format
        uuid.UUID(result["generation_id"])  # Should not raise exception

    @patch('app.services.report_generation.generator.crud')
    def test_generate_report_error_scenarios(self, mock_crud):
        """Test various error scenarios in report generation"""
        # Test missing task
        mock_crud.task.get.return_value = None
        mock_crud.template.get.return_value = Mock()
        mock_crud.data_source.get.return_value = Mock()
        
        with pytest.raises(ValueError, match="Task not found"):
            self.service.generate_report(1, 1, 1)
        
        # Test missing template
        mock_crud.task.get.return_value = Mock()
        mock_crud.template.get.return_value = None
        mock_crud.data_source.get.return_value = Mock()
        
        with pytest.raises(ValueError, match="Template not found"):
            self.service.generate_report(1, 1, 1)
        
        # Test missing data source
        mock_crud.task.get.return_value = Mock()
        mock_crud.template.get.return_value = Mock()
        mock_crud.data_source.get.return_value = None
        
        with pytest.raises(ValueError, match="Data source not found"):
            self.service.generate_report(1, 1, 1)

    @pytest.mark.asyncio
    @patch('app.services.report_generation.generator.crud')
    async def test_preview_report_data_comprehensive(self, mock_crud):
        """Test comprehensive report data preview"""
        # Setup mocks
        mock_template = Mock()
        mock_template.name = "Comprehensive Template"
        mock_template.file_path = "/path/to/template.docx"
        
        mock_data_source = Mock()
        mock_data_source.name = "Comprehensive Data Source"
        
        mock_crud.template.get.return_value = mock_template
        mock_crud.data_source.get.return_value = mock_data_source
        
        # Mock complex template structure
        complex_placeholders = [
            {
                "name": "summary_stats",
                "type": "scalar",
                "description": "汇总统计数据"
            },
            {
                "name": "regional_breakdown",
                "type": "table",
                "description": "地区分解数据"
            },
            {
                "name": "trend_chart",
                "type": "chart",
                "description": "趋势图表"
            }
        ]
        self.service.template_parser.parse = Mock(return_value={
            "placeholders": complex_placeholders
        })
        
        # Mock comprehensive sample data
        import pandas as pd
        sample_data = pd.DataFrame({
            "region": ["昆明", "大理", "丽江", "西双版纳", "香格里拉"],
            "complaint_count": [120, 95, 150, 80, 65],
            "resolution_rate": [0.85, 0.92, 0.78, 0.88, 0.91],
            "date": pd.date_range("2024-01-01", periods=5)
        })
        
        self.service.data_retrieval.fetch_data = AsyncMock(return_value=sample_data)
        
        # Mock AI interpretation
        def mock_ai_interpret(task_type, description, df_columns):
            return {
                "interpretation": f"AI解释：{description}",
                "suggested_columns": df_columns[:2],
                "confidence": 0.85
            }
        
        self.service.ai_service.interpret_description_for_tool = Mock(
            side_effect=mock_ai_interpret
        )
        
        result = await self.service.preview_report_data(
            template_id=1,
            data_source_id=1,
            limit=3
        )
        
        # Verify comprehensive preview results
        assert result["template_id"] == 1
        assert result["data_source_id"] == 1
        assert result["template_name"] == "Comprehensive Template"
        assert result["data_source_name"] == "Comprehensive Data Source"
        assert len(result["placeholders"]) == 3
        assert result["sample_data_shape"]["rows"] == 3  # Limited by limit parameter
        assert result["sample_data_shape"]["columns"] == 4
        
        # Verify placeholder analysis
        for placeholder in result["placeholders"]:
            assert "name" in placeholder
            assert "type" in placeholder
            assert "description" in placeholder
            assert "available_columns" in placeholder
            assert "sample_values" in placeholder
            assert "ai_interpretation" in placeholder

    def test_validate_report_configuration_comprehensive(self):
        """Test comprehensive report configuration validation"""
        with patch('app.services.report_generation.generator.crud') as mock_crud, \
             patch('app.services.report_generation.generator.os.path.exists') as mock_exists:
            
            # Setup valid configuration
            mock_template = Mock()
            mock_template.file_path = "/valid/template.docx"
            
            mock_data_source = Mock()
            mock_data_source.source_type.value = "sql"
            mock_data_source.connection_string = "valid_connection"
            
            mock_crud.template.get.return_value = mock_template
            mock_crud.data_source.get.return_value = mock_data_source
            mock_exists.return_value = True
            
            # Mock template parser
            self.service.template_parser.parse = Mock(return_value={
                "placeholders": [{"name": "test", "type": "scalar"}]
            })
            
            # Mock AI service health check
            self.service.ai_service.health_check = Mock(return_value={
                "status": "healthy"
            })
            
            result = self.service.validate_report_configuration(1, 1)
            
            assert result["valid"] is True
            assert len(result["errors"]) == 0
            assert len(result["warnings"]) == 0

    def test_validate_report_configuration_various_data_sources(self):
        """Test validation with various data source types"""
        test_cases = [
            # CSV data source
            {
                "source_type": "csv",
                "file_path": "/valid/data.csv",
                "should_be_valid": True
            },
            # API data source
            {
                "source_type": "api",
                "api_url": "https://api.example.com/data",
                "should_be_valid": True
            },
            # Invalid CSV (missing file)
            {
                "source_type": "csv",
                "file_path": None,
                "should_be_valid": False
            },
            # Invalid API (missing URL)
            {
                "source_type": "api",
                "api_url": None,
                "should_be_valid": False
            }
        ]
        
        for case in test_cases:
            with patch('app.services.report_generation.generator.crud') as mock_crud, \
                 patch('app.services.report_generation.generator.os.path.exists') as mock_exists:
                
                mock_template = Mock()
                mock_template.file_path = "/valid/template.docx"
                
                mock_data_source = Mock()
                mock_data_source.source_type.value = case["source_type"]
                
                # Set appropriate attributes based on source type
                if case["source_type"] == "csv":
                    mock_data_source.file_path = case.get("file_path")
                elif case["source_type"] == "api":
                    mock_data_source.api_url = case.get("api_url")
                elif case["source_type"] == "sql":
                    mock_data_source.connection_string = case.get("connection_string")
                
                mock_crud.template.get.return_value = mock_template
                mock_crud.data_source.get.return_value = mock_data_source
                mock_exists.return_value = True
                
                self.service.template_parser.parse = Mock(return_value={
                    "placeholders": [{"name": "test", "type": "scalar"}]
                })
                self.service.ai_service.health_check = Mock(return_value={
                    "status": "healthy"
                })
                
                result = self.service.validate_report_configuration(1, 1)
                
                if case["should_be_valid"]:
                    assert result["valid"] is True or len(result["errors"]) == 0
                else:
                    assert result["valid"] is False or len(result["errors"]) > 0


class TestReportCompositionServiceEnhanced:
    """Enhanced tests for ReportCompositionService class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = ReportCompositionService()

    def test_compose_report_complex_content(self):
        """Test composition with complex content types"""
        template_content = """
        # 投诉分析报告
        
        ## 总体情况
        本期共处理投诉 {{total_count}} 件，完成率达到 {{completion_rate}}。
        
        ## 地区分布
        {{region_chart}}
        
        ## 趋势分析
        {{trend_description}}
        
        ## 详细数据
        {{data_table}}
        """
        
        results = {
            "{{total_count}}": "1,234",
            "{{completion_rate}}": "95.6%",
            "{{region_chart}}": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
            "{{trend_description}}": "投诉量呈现稳定下降趋势，客户满意度持续提升。",
            "{{data_table}}": "<table><tr><th>地区</th><th>投诉量</th></tr><tr><td>昆明</td><td>456</td></tr></table>"
        }
        
        composed = self.service.compose_report(template_content, results)
        
        # Verify all placeholders are replaced
        for placeholder in results.keys():
            assert placeholder not in composed
        
        # Verify content is properly inserted
        assert "1,234" in composed
        assert "95.6%" in composed
        assert "投诉量呈现稳定下降趋势" in composed
        assert "<table>" in composed
        
        # Verify base64 image is converted to img tag
        assert '<img src="data:image/png;base64,' in composed

    def test_is_base64_detection_comprehensive(self):
        """Test comprehensive base64 detection"""
        test_cases = [
            # Valid base64 images
            ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==", True),
            ("data:image/png;base64,iVBORw0KGgo=", False),  # Has prefix, not pure base64
            ("SGVsbG8gV29ybGQ=", True),  # Simple base64
            
            # Invalid cases
            ("regular text", False),
            ("", False),
            (None, False),
            (123, False),
            ([], False),
            
            # Edge cases
            ("a", False),  # Too short
            ("====", True),  # Only padding
        ]
        
        for test_input, expected in test_cases:
            result = self.service.is_base64(test_input)
            assert result == expected, f"Failed for input: {test_input}"

    def test_compose_report_edge_cases(self):
        """Test composition with edge cases"""
        # Empty template
        assert self.service.compose_report("", {}) == ""
        
        # Template with no placeholders
        template = "这是一个没有占位符的模板。"
        assert self.service.compose_report(template, {}) == template
        
        # Empty results
        template = "模板包含{{placeholder}}但没有替换值。"
        composed = self.service.compose_report(template, {})
        assert "{{placeholder}}" in composed  # Should remain unchanged
        
        # Partial replacements
        template = "{{replaced}}和{{not_replaced}}"
        results = {"{{replaced}}": "已替换"}
        composed = self.service.compose_report(template, results)
        assert "已替换" in composed
        assert "{{not_replaced}}" in composed

    def test_compose_report_special_characters(self):
        """Test composition with special characters and encoding"""
        template = "特殊字符测试：{{emoji}}，{{chinese}}，{{symbols}}"
        results = {
            "{{emoji}}": "😊📊🎯",
            "{{chinese}}": "中文测试内容",
            "{{symbols}}": "!@#$%^&*()_+-=[]{}|;:,.<>?"
        }
        
        composed = self.service.compose_report(template, results)
        
        assert "😊📊🎯" in composed
        assert "中文测试内容" in composed
        assert "!@#$%^&*()_+-=[]{}|;:,.<>?" in composed


class TestLanguageAnalyzerEnhanced:
    """Enhanced tests for LanguageAnalyzer class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = LanguageAnalyzer()

    def test_analyze_text_comprehensive(self):
        """Test comprehensive text analysis"""
        complex_text = """
        这是第一段文字，包含了基本的句子结构。这个段落用来测试基础功能！
        
        第二段包含了更复杂的句子结构，虽然内容较长，但是应该能够正确处理？
        这里还有一些短句。以及一些非常非常长的句子，用来测试系统对于长句子的处理能力，
        看看是否能够正确识别和分析这种复杂的语言结构。
        
        第三段测试特殊情况：包含数字123，英文words，以及各种标点符号！@#$%。
        """
        
        result = self.analyzer.analyze_text(complex_text)
        
        # Verify comprehensive analysis results
        assert result["word_count"] > 0
        assert result["sentence_count"] >= 5
        assert result["paragraph_count"] >= 3
        assert result["avg_sentence_length"] > 0
        assert 0 <= result["readability_score"] <= 100
        assert isinstance(result["fluency_issues"], list)
        assert result["complex_sentences"] >= 0

    def test_sentence_splitting_various_punctuation(self):
        """Test sentence splitting with various Chinese punctuation"""
        test_cases = [
            ("第一句。第二句！第三句？", 3),
            ("句子一；句子二：句子三。", 3),
            ("问题一？问题二？问题三！", 3),
            ("声明一。声明二！声明三？声明四。", 4),
        ]
        
        for text, expected_count in test_cases:
            sentences = self.analyzer._split_sentences(text)
            assert len(sentences) == expected_count, f"Failed for: {text}"

    def test_fluency_check_comprehensive(self):
        """Test comprehensive fluency checking"""
        test_sentences = [
            "短。",  # Very short sentence
            "这是一个正常长度的句子，应该不会触发任何警告。",  # Normal sentence
            "这是一个极其冗长的句子，" + "内容重复" * 50 + "，用来测试长句子检测。",  # Very long sentence
            "重复标点符号测试。。。",  # Repeated punctuation
            "正常句子结束。",  # Normal sentence
        ]
        
        issues = self.analyzer._check_fluency(test_sentences)
        
        # Should detect various issues
        issue_types = [issue["type"] for issue in issues]
        assert "short_sentence" in issue_types
        assert "long_sentence" in issue_types
        assert "repeated_punctuation" in issue_types

    def test_readability_calculation_edge_cases(self):
        """Test readability calculation with edge cases"""
        test_cases = [
            ("", 0),  # Empty text
            ("短句。", lambda x: 0 <= x <= 100),  # Very short text
            ("正常长度的句子用于测试。", lambda x: 0 <= x <= 100),  # Normal text
            ("极长句子" + "重复内容" * 100 + "。", lambda x: 0 <= x <= 100),  # Very long sentence
        ]
        
        for text, expected in test_cases:
            sentences = self.analyzer._split_sentences(text) if text else []
            score = self.analyzer._calculate_readability(text, sentences)
            
            if callable(expected):
                assert expected(score), f"Score {score} failed validation for: {text[:50]}..."
            else:
                assert score == expected, f"Expected {expected}, got {score} for: {text}"

    def test_complex_sentence_detection(self):
        """Test complex sentence pattern detection"""
        test_sentences = [
            "虽然天气不好，但是我们还是要出门。",  # although...but
            "他不仅聪明而且勤奋。",  # not only...but also
            "如果明天下雨，那么我们就不去了。",  # if...then
            "因为时间紧急，所以我们必须加快速度。",  # because...so
            "这是一个简单的句子。",  # Simple sentence
        ]
        
        complex_count = self.analyzer._count_complex_sentences(test_sentences)
        assert complex_count == 4  # First 4 sentences are complex


class TestDataConsistencyValidatorEnhanced:
    """Enhanced tests for DataConsistencyValidator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.validator = DataConsistencyValidator()

    def test_validate_report_comprehensive(self):
        """Test comprehensive report validation"""
        report_content = """
        投诉分析报告
        
        本月共处理投诉1,234件，完成率达到95.5%。
        各地区分布如下：
        - 昆明：456件（37.0%）
        - 大理：321件（26.0%）
        - 丽江：289件（23.4%）
        - 其他：168件（13.6%）
        
        时间分析：
        2024年3月数据显示，投诉量比2024年2月下降了15.2%。
        
        异常数据测试：
        - 错误百分比：150%（应该被检测为错误）
        - 负百分比：-5%（应该被检测为错误）
        - 异常年份：1800年3月（应该被检测为异常）
        """
        
        issues = self.validator.validate_report(report_content)
        
        # Should detect various consistency issues
        issue_types = [issue.issue_type for issue in issues]
        assert QualityIssueType.DATA_INCONSISTENCY in issue_types
        
        # Check for specific issues
        issue_descriptions = [issue.description for issue in issues]
        assert any("150%" in desc for desc in issue_descriptions)
        assert any("-5%" in desc for desc in issue_descriptions)
        assert any("1800年" in desc for desc in issue_descriptions)

    def test_extract_numbers_comprehensive(self):
        """Test comprehensive number extraction"""
        text = """
        数字测试：整数123，小数45.67，千分位1,234，
        大数字1,234,567.89，百分比不算数字95%，
        负数-123.45，科学计数法不支持1.23e5。
        """
        
        numbers = self.validator._extract_numbers(text)
        
        # Verify extracted numbers
        number_values = [num[1] for num in numbers]
        assert 123.0 in number_values
        assert 45.67 in number_values
        assert 1234.0 in number_values
        assert 1234567.89 in number_values

    def test_extract_percentages_comprehensive(self):
        """Test comprehensive percentage extraction"""
        text = """
        百分比测试：正常百分比95.5%，整数百分比80%，
        小数百分比67.89%，异常百分比150%，负百分比-10%。
        """
        
        percentages = self.validator._extract_percentages(text)
        
        # Verify extracted percentages
        percentage_values = [pct[1] for pct in percentages]
        assert 95.5 in percentage_values
        assert 80.0 in percentage_values
        assert 67.89 in percentage_values
        assert 150.0 in percentage_values
        assert -10.0 in percentage_values

    def test_extract_dates_comprehensive(self):
        """Test comprehensive date extraction"""
        text = """
        日期测试：2024年3月，2023年12月，1月15日，
        12月31日，2024年2月29日（闰年），13月（无效月份）。
        """
        
        dates = self.validator._extract_dates(text)
        
        # Verify extracted dates
        assert len(dates) >= 3
        assert any("2024年3月" in date for date in dates)
        assert any("2023年12月" in date for date in dates)

    def test_percentage_consistency_validation(self):
        """Test percentage consistency validation"""
        valid_percentages = [("95.5%", 95.5, "完成率95.5%")]
        invalid_percentages = [
            ("150%", 150.0, "异常百分比150%"),
            ("-10%", -10.0, "负百分比-10%")
        ]
        
        # Test valid percentages
        valid_issues = self.validator._check_percentage_consistency(valid_percentages)
        assert len(valid_issues) == 0
        
        # Test invalid percentages
        invalid_issues = self.validator._check_percentage_consistency(invalid_percentages)
        assert len(invalid_issues) == 2
        
        # Verify issue details
        for issue in invalid_issues:
            assert issue.issue_type == QualityIssueType.DATA_INCONSISTENCY
            assert issue.severity == QualitySeverity.HIGH

    def test_date_consistency_validation(self):
        """Test date consistency validation"""
        test_dates = [
            "2024年3月",  # Valid
            "2023年12月",  # Valid
            "1800年3月",  # Invalid year (too old)
            "2024年15月",  # Invalid month
            "2025年2月",  # Valid (future but reasonable)
        ]
        
        issues = self.validator._check_date_consistency(test_dates)
        
        # Should detect invalid dates
        issue_descriptions = [issue.description for issue in issues]
        assert any("1800年" in desc for desc in issue_descriptions)
        assert any("15月" in desc for desc in issue_descriptions)

    def test_validate_against_source_data(self):
        """Test validation against source data"""
        report_content = "总投诉件数：1,234件，完成率：95.5%"
        source_data = {
            "expected_values": {
                "total_complaints": 1234,
                "completion_rate": "95.5%",
                "missing_value": 999  # This should trigger an issue
            }
        }
        
        issues = self.validator._validate_against_source(report_content, source_data)
        
        # Should detect missing expected value
        assert len(issues) >= 1
        issue_descriptions = [issue.description for issue in issues]
        assert any("999" in desc for desc in issue_descriptions)


class TestReportQualityCheckerEnhanced:
    """Enhanced tests for ReportQualityChecker class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        self.checker = ReportQualityChecker(self.mock_db)

    def test_check_report_quality_comprehensive(self):
        """Test comprehensive report quality checking"""
        report_content = """
        # 投诉处理分析报告
        
        ## 概述
        本月共处理投诉1,234件，完成率达到95.5%。整体处理效率较上月提升了12.3%。
        
        ## 详细分析
        各地区处理情况如下：昆明地区处理456件，大理地区处理321件，丽江地区处理289件。
        从时间分布来看，工作日处理量明显高于周末，平均每日处理量为41件。
        
        ## 问题识别
        发现部分地区存在处理时间过长的问题，需要进一步优化流程。
        """
        
        # Mock LLM manager
        self.checker.llm_manager.get_available_providers = Mock(return_value=["openai"])
        
        # Mock LLM analysis
        mock_llm_analysis = {
            "overall_assessment": "报告质量良好",
            "fluency_score": 85,
            "logic_score": 88,
            "accuracy_score": 92,
            "completeness_score": 87,
            "suggestions": ["建议增加更多数据支撑", "可以添加图表展示"],
            "issues": [
                {
                    "description": "部分句子较长，建议拆分",
                    "location": "详细分析部分",
                    "suggestion": "将长句拆分为多个短句"
                }
            ]
        }
        
        with patch.object(self.checker, '_perform_llm_analysis', return_value=mock_llm_analysis):
            result = self.checker.check_report_quality(report_content)
        
        # Verify comprehensive quality check results
        assert isinstance(result, QualityCheckResult)
        assert isinstance(result.metrics, QualityMetrics)
        assert result.metrics.overall_score > 0
        assert result.metrics.word_count > 0
        assert result.processing_time > 0
        assert isinstance(result.timestamp, datetime)

    def test_llm_analysis_error_handling(self):
        """Test LLM analysis error handling"""
        report_content = "测试报告内容"
        
        # Mock LLM manager with no providers
        self.checker.llm_manager.get_available_providers = Mock(return_value=[])
        
        result = self.checker.check_report_quality(report_content, enable_llm_analysis=True)
        
        # Should handle gracefully without LLM
        assert isinstance(result, QualityCheckResult)
        assert result.llm_analysis is None or result.llm_analysis == {}

    def test_optimize_content_functionality(self):
        """Test content optimization functionality"""
        content = "这是需要优化的内容，包含一些问题。"
        issues = [
            QualityIssue(
                issue_type=QualityIssueType.LANGUAGE_FLUENCY,
                severity=QualitySeverity.MEDIUM,
                description="句子结构可以改进",
                location="第一段"
            )
        ]
        
        # Mock LLM manager
        self.checker.llm_manager.get_available_providers = Mock(return_value=["openai"])
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = json.dumps({
            "optimized_content": "这是经过优化的内容，结构更加清晰。",
            "improvements": ["改进了句子结构", "提高了可读性"],
            "confidence": 85
        })
        
        self.checker.llm_manager.call_llm = Mock(return_value=mock_response)
        
        result = self.checker.optimize_content(content, issues)
        
        assert "optimized_content" in result
        assert "improvements" in result
        assert "confidence" in result
        assert result["confidence"] > 0

    def test_quality_metrics_calculation(self):
        """Test quality metrics calculation"""
        language_analysis = {
            "word_count": 150,
            "sentence_count": 8,
            "paragraph_count": 3,
            "avg_sentence_length": 18.75,
            "readability_score": 75,
            "fluency_issues": [],
            "complex_sentences": 2
        }
        
        issues = [
            QualityIssue(
                issue_type=QualityIssueType.DATA_INCONSISTENCY,
                severity=QualitySeverity.HIGH,
                description="数据不一致",
                location="第二段"
            ),
            QualityIssue(
                issue_type=QualityIssueType.LANGUAGE_FLUENCY,
                severity=QualitySeverity.MEDIUM,
                description="语言流畅性问题",
                location="第三段"
            )
        ]
        
        llm_analysis = {
            "fluency_score": 80,
            "logic_score": 85,
            "accuracy_score": 78,
            "completeness_score": 82
        }
        
        metrics = self.checker._calculate_quality_metrics(
            language_analysis, issues, llm_analysis
        )
        
        assert isinstance(metrics, QualityMetrics)
        assert 0 <= metrics.overall_score <= 100
        assert metrics.word_count == 150
        assert metrics.sentence_count == 8
        assert metrics.high_issues == 1
        assert metrics.medium_issues == 1
        assert metrics.complex_words_ratio >= 0

    def test_generate_suggestions_comprehensive(self):
        """Test comprehensive suggestion generation"""
        issues = [
            QualityIssue(
                issue_type=QualityIssueType.LANGUAGE_FLUENCY,
                severity=QualitySeverity.MEDIUM,
                description="句子过长",
                location="第一段",
                suggestion="建议拆分长句"
            ),
            QualityIssue(
                issue_type=QualityIssueType.DATA_INCONSISTENCY,
                severity=QualitySeverity.HIGH,
                description="数据不一致",
                location="第二段",
                suggestion="检查数据准确性"
            )
        ]
        
        language_analysis = {
            "avg_sentence_length": 60,  # Very long sentences
            "fluency_issues": [
                {"type": "long_sentence"},
                {"type": "repeated_punctuation"},
                {"type": "short_sentence"},
                {"type": "long_sentence"},
                {"type": "repeated_punctuation"},
                {"type": "short_sentence"}  # More than 5 issues
            ]
        }
        
        suggestions = self.checker._generate_suggestions(issues, language_analysis)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 10  # Should be limited
        assert "建议拆分长句" in suggestions
        assert "检查数据准确性" in suggestions
        assert any("缩短句子长度" in s for s in suggestions)
        assert any("语言流畅性问题" in s for s in suggestions)


class TestIntegrationAndPerformance:
    """Integration and performance tests"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()

    def test_end_to_end_report_generation_workflow(self):
        """Test complete end-to-end report generation workflow"""
        # This would be a comprehensive integration test
        # combining all components together
        pass  # Placeholder for complex integration test

    def test_large_report_processing_performance(self):
        """Test performance with large reports"""
        # Create a large report content
        large_content = """
        # 大型报告测试
        
        """ + "这是测试段落内容。" * 1000 + """
        
        ## 数据分析
        """ + "包含大量数据的分析内容。" * 500 + """
        
        ## 结论
        """ + "详细的结论部分。" * 200
        
        analyzer = LanguageAnalyzer()
        
        start_time = time.time()
        result = analyzer.analyze_text(large_content)
        processing_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert processing_time < 10.0  # 10 seconds max
        assert result["word_count"] > 10000
        assert result["sentence_count"] > 100

    def test_concurrent_quality_checking(self):
        """Test concurrent quality checking"""
        import concurrent.futures
        
        def check_quality(content_id):
            analyzer = LanguageAnalyzer()
            content = f"测试内容{content_id}：" + "这是测试句子。" * 10
            return analyzer.analyze_text(content)
        
        # Process multiple contents concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(check_quality, i) for i in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        assert len(results) == 20
        assert all(result["word_count"] > 0 for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])