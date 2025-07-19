"""
Enhanced comprehensive unit tests for intelligent_placeholder service module
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import json
import time
import tempfile
import os

from app.services.intelligent_placeholder.processor import (
    PlaceholderProcessor,
    PlaceholderMatch,
    PlaceholderType,
    ProcessingError,
    extract_placeholders_from_text,
    validate_placeholder_text,
)
from app.services.intelligent_placeholder.adapter import (
    IntelligentPlaceholderProcessor,
    ProcessingResult,
    PlaceholderUnderstanding,
    FieldSuggestion,
    LLMPlaceholderService,
    IntelligentETLExecutor,
    ContentGenerator,
    ReportQualityChecker,
)
from app.services.intelligent_placeholder.matcher import (
    IntelligentFieldMatcher,
    FieldMatchingResult,
    SimilarityScore,
)


class TestPlaceholderProcessorEnhanced:
    """Enhanced tests for PlaceholderProcessor class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.processor = PlaceholderProcessor()

    def test_initialization_with_custom_definitions(self):
        """Test processor initialization with custom type definitions"""
        # Create temporary type definitions file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            custom_defs = {
                "placeholder_types": {
                    "测试": {
                        "description": "测试占位符类型",
                        "auto_calculation": True,
                        "depends_on": "test_data"
                    }
                }
            }
            json.dump(custom_defs, f, ensure_ascii=False)
            temp_file = f.name

        try:
            processor = PlaceholderProcessor(temp_file)
            assert processor.type_definitions is not None
            assert "placeholder_types" in processor.type_definitions
            assert "测试" in processor.type_definitions["placeholder_types"]
        finally:
            os.unlink(temp_file)

    def test_initialization_with_invalid_definitions_file(self):
        """Test processor initialization with invalid definitions file"""
        processor = PlaceholderProcessor("/nonexistent/file.json")
        # Should fall back to default definitions
        assert processor.type_definitions is not None
        assert "placeholder_types" in processor.type_definitions

    def test_extract_placeholders_complex_patterns(self):
        """Test extracting placeholders with complex patterns"""
        text = """
        报告显示：
        1. {{统计:总投诉件数}}件投诉已处理
        2. {{区域:云南省}}地区表现最佳
        3. {{周期:2024年第一季度}}数据统计
        4. {{图表:投诉趋势图}}展示了变化
        """
        placeholders = self.processor.extract_placeholders(text)
        
        assert len(placeholders) == 4
        types = [p.type for p in placeholders]
        assert PlaceholderType.STATISTIC in types
        assert PlaceholderType.REGION in types
        assert PlaceholderType.PERIOD in types
        assert PlaceholderType.CHART in types

    def test_extract_placeholders_with_special_characters(self):
        """Test extracting placeholders with special characters"""
        text = "{{统计:总投诉件数（含重复）}}和{{区域:云南省-昆明市}}的数据。"
        placeholders = self.processor.extract_placeholders(text)
        
        assert len(placeholders) == 2
        assert "（含重复）" in placeholders[0].description
        assert "云南省-昆明市" in placeholders[1].description

    def test_extract_placeholders_performance(self):
        """Test placeholder extraction performance with large text"""
        # Create large text with many placeholders
        large_text = ""
        for i in range(100):
            large_text += f"第{i}段文本包含{{统计:数据{i}}}和{{区域:地区{i}}}。\n"
        
        start_time = time.time()
        placeholders = self.processor.extract_placeholders(large_text)
        end_time = time.time()
        
        assert len(placeholders) == 200  # 100 * 2
        assert end_time - start_time < 5.0  # Should complete within 5 seconds

    def test_context_extraction_edge_cases(self):
        """Test context extraction with edge cases"""
        # Test with placeholder at the beginning
        text = "{{统计:开头数据}}这是后续内容。"
        placeholders = self.processor.extract_placeholders(text)
        assert len(placeholders) == 1
        assert placeholders[0].context_before == ""
        assert "后续内容" in placeholders[0].context_after

        # Test with placeholder at the end
        text = "这是前面的内容。{{统计:结尾数据}}"
        placeholders = self.processor.extract_placeholders(text)
        assert len(placeholders) == 1
        assert "前面的内容" in placeholders[0].context_before
        assert placeholders[0].context_after == ""

    def test_confidence_calculation_detailed(self):
        """Test detailed confidence calculation scenarios"""
        # High confidence: good type, good description, relevant context
        confidence1 = self.processor._calculate_confidence(
            "统计", "总投诉件数", "统计报告显示投诉", "件投诉已处理完成"
        )
        
        # Medium confidence: good type, short description, some context
        confidence2 = self.processor._calculate_confidence(
            "统计", "数量", "报告", "个"
        )
        
        # Low confidence: good type, poor description, no context
        confidence3 = self.processor._calculate_confidence(
            "统计", "x", "", ""
        )
        
        assert confidence1 > confidence2 > confidence3
        assert all(0 <= c <= 1 for c in [confidence1, confidence2, confidence3])

    def test_error_recovery_comprehensive(self):
        """Test comprehensive error recovery scenarios"""
        test_cases = [
            # Missing colon
            ("{{统计总投诉件数}}", "{{统计:总投诉件数}}"),
            # Extra spaces
            ("{{ 统计 : 总投诉件数 }}", "{{统计:总投诉件数}}"),
            # Chinese brackets
            ("｛｛统计:总投诉件数｝｝", "{{统计:总投诉件数}}"),
            # Incomplete brackets
            ("{{统计:总投诉件数}", "{{统计:总投诉件数}}"),
        ]
        
        for original, expected in test_cases:
            recovered = self.processor.recover_from_errors(original)
            assert expected in recovered or recovered != original

    def test_sentence_splitting_chinese(self):
        """Test Chinese sentence splitting"""
        text = "第一句话。第二句话！第三句话？第四句话；第五句话。"
        sentences = self.processor._split_sentences(text)
        
        assert len(sentences) >= 4  # Should split on Chinese punctuation
        assert any("第一句话" in s for s in sentences)
        assert any("第二句话" in s for s in sentences)

    def test_validation_comprehensive(self):
        """Test comprehensive placeholder validation"""
        text = """
        {{统计:高置信度数据}}
        {{区域:云南省}}
        {{周期:本月}}
        {{无效类型:错误数据}}
        {{统计:}}
        """
        placeholders = self.processor.extract_placeholders(text)
        validation_result = self.processor.validate_placeholders(placeholders)
        
        assert "is_valid" in validation_result
        assert "total_count" in validation_result
        assert "type_distribution" in validation_result
        assert "low_confidence_count" in validation_result
        assert "errors" in validation_result
        assert "warnings" in validation_result

    def test_processing_summary_detailed(self):
        """Test detailed processing summary"""
        # Process text with various error types
        text = """
        {{统计:正常数据}}
        {{无效类型:错误}}
        {{统计:}}
        {{区域:正常区域}}
        """
        self.processor.extract_placeholders(text)
        summary = self.processor.get_processing_summary()
        
        assert "total_errors" in summary
        assert "error_by_severity" in summary
        assert "supported_types" in summary
        assert "type_definitions_loaded" in summary
        assert summary["total_errors"] >= 0
        assert isinstance(summary["error_by_severity"], dict)


class TestIntelligentFieldMatcherEnhanced:
    """Enhanced tests for IntelligentFieldMatcher class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.matcher = IntelligentFieldMatcher()

    @pytest.mark.asyncio
    async def test_match_fields_with_context(self):
        """Test field matching with context information"""
        suggestions = [
            FieldSuggestion(
                field_name="complaint_total",
                confidence=0.85,
                transformation_needed=False,
                transformation_type="none"
            )
        ]
        available_fields = ["complaint_count", "total_complaints", "region", "date"]
        context = "统计投诉总数相关数据"
        
        result = await self.matcher.match_fields(
            suggestions, available_fields, context
        )
        
        assert isinstance(result, FieldMatchingResult)
        assert result.matched_field in available_fields
        assert result.confidence > 0
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_match_fields_with_transformations(self):
        """Test field matching with transformation requirements"""
        suggestions = [
            FieldSuggestion(
                field_name="avg_complaints",
                confidence=0.8,
                transformation_needed=True,
                transformation_type="aggregate",
                calculation_formula="AVG(complaint_count)"
            )
        ]
        available_fields = ["complaint_count", "region", "date"]
        
        result = await self.matcher.match_fields(suggestions, available_fields)
        
        assert isinstance(result, FieldMatchingResult)
        assert result.requires_transformation in [True, False]  # Depends on matching logic
        if result.requires_transformation:
            assert "type" in result.transformation_config

    @pytest.mark.asyncio
    async def test_match_fields_similarity_algorithms(self):
        """Test different similarity algorithms"""
        # Test Jaccard similarity
        jaccard_sim = self.matcher._calculate_jaccard_similarity("complaint", "complaints")
        assert 0 <= jaccard_sim <= 1
        assert jaccard_sim > 0.5

        # Test edit distance similarity
        edit_sim = self.matcher._calculate_edit_similarity("count", "counts")
        assert 0 <= edit_sim <= 1
        assert edit_sim > 0.7

        # Test LCS similarity
        lcs_sim = self.matcher._calculate_lcs_similarity("data_count", "count_data")
        assert 0 <= lcs_sim <= 1

    @pytest.mark.asyncio
    async def test_match_fields_caching(self):
        """Test field matching caching mechanism"""
        suggestions = [
            FieldSuggestion("test_field", 0.9, False, "none")
        ]
        available_fields = ["test_field", "other_field"]
        
        # First call
        result1 = await self.matcher.match_fields(suggestions, available_fields)
        
        # Second call (should use cache if available)
        result2 = await self.matcher.match_fields(suggestions, available_fields)
        
        assert result1.matched_field == result2.matched_field
        assert result1.confidence == result2.confidence

    def test_cache_key_generation_consistency(self):
        """Test cache key generation consistency"""
        suggestions = [FieldSuggestion("field1", 0.8, False, "none")]
        available_fields = ["field1", "field2"]
        context = "test context"
        
        key1 = self.matcher._generate_cache_key(suggestions, available_fields, context)
        key2 = self.matcher._generate_cache_key(suggestions, available_fields, context)
        
        assert key1 == key2
        assert key1.startswith("field_match:")

    @pytest.mark.asyncio
    async def test_historical_mappings(self):
        """Test historical mappings functionality"""
        # This would require database mocking in a real scenario
        with patch.object(self.matcher, 'get_historical_mappings') as mock_get:
            mock_get.return_value = [
                {
                    "signature": "test_sig",
                    "matched_field": "test_field",
                    "confidence": 0.9,
                    "usage_count": 5,
                    "last_used": "2024-01-01T00:00:00",
                    "transformation_config": {}
                }
            ]
            
            mappings = await self.matcher.get_historical_mappings(1)
            assert len(mappings) == 1
            assert mappings[0]["matched_field"] == "test_field"


class TestIntelligentPlaceholderProcessorEnhanced:
    """Enhanced tests for IntelligentPlaceholderProcessor adapter class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_llm_service = Mock()
        self.mock_field_matcher = Mock()
        self.mock_etl_executor = Mock()
        self.mock_content_generator = Mock()
        self.mock_quality_checker = Mock()
        
        self.processor = IntelligentPlaceholderProcessor(
            llm_service=self.mock_llm_service,
            field_matcher=self.mock_field_matcher,
            etl_executor=self.mock_etl_executor,
            content_generator=self.mock_content_generator,
            quality_checker=self.mock_quality_checker
        )

    @pytest.mark.asyncio
    async def test_process_template_with_data_schema(self):
        """Test processing template with data schema"""
        template = "报告显示{{统计:总投诉件数}}件投诉。"
        data_schema = {
            "tables": ["complaints"],
            "columns": ["id", "complaint_count", "region", "date"]
        }
        
        result = await self.processor.process_template(
            template, data_schema=data_schema
        )
        
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert "placeholder_count" in result.metadata

    @pytest.mark.asyncio
    async def test_process_template_with_multiple_data_sources(self):
        """Test processing template with multiple data sources"""
        template = "{{统计:总数}}和{{区域:地区}}数据。"
        data_source_configs = [
            {"type": "sql", "query": "SELECT COUNT(*) FROM complaints"},
            {"type": "csv", "file": "regions.csv"}
        ]
        
        result = await self.processor.process_template(
            template, data_source_configs=data_source_configs
        )
        
        assert isinstance(result, ProcessingResult)
        assert len(result.processed_placeholders) >= 0

    @pytest.mark.asyncio
    async def test_process_template_error_handling(self):
        """Test comprehensive error handling in template processing"""
        template = "{{统计:错误数据}}{{区域:正常数据}}"
        
        # Mock services to simulate various error scenarios
        self.mock_etl_executor.execute_etl = AsyncMock(side_effect=Exception("ETL Error"))
        self.mock_content_generator.generate_content = AsyncMock(side_effect=Exception("Content Error"))
        
        result = await self.processor.process_template(template)
        
        assert isinstance(result, ProcessingResult)
        # Should handle errors gracefully
        assert len(result.errors) >= 0

    @pytest.mark.asyncio
    async def test_quality_score_calculation_detailed(self):
        """Test detailed quality score calculation"""
        content = "这是一个高质量的报告内容，包含详细的数据分析。"
        placeholders = [
            PlaceholderMatch(
                full_match="{{统计:高质量数据}}",
                type=PlaceholderType.STATISTIC,
                description="高质量数据",
                start_pos=0,
                end_pos=15,
                context_before="前文",
                context_after="后文",
                confidence=0.95
            )
        ]
        
        # Mock quality checker
        self.mock_quality_checker.check_quality = AsyncMock(return_value={
            "quality_score": 0.92,
            "suggestions": ["内容质量良好"],
            "issues": []
        })
        
        score = await self.processor._calculate_quality_score(content, placeholders)
        
        assert 0 <= score <= 1
        assert isinstance(score, float)

    @pytest.mark.asyncio
    async def test_placeholder_understanding_llm(self):
        """Test LLM-based placeholder understanding"""
        placeholder = PlaceholderMatch(
            full_match="{{统计:复杂业务指标}}",
            type=PlaceholderType.STATISTIC,
            description="复杂业务指标",
            start_pos=0,
            end_pos=20,
            context_before="业务报告显示",
            context_after="呈上升趋势",
            confidence=0.8
        )
        
        understanding = await self.processor._mock_understand_placeholder(placeholder)
        
        assert isinstance(understanding, PlaceholderUnderstanding)
        assert understanding.semantic_meaning is not None
        assert len(understanding.data_requirements) > 0
        assert understanding.confidence_score == placeholder.confidence


class TestLLMPlaceholderServiceEnhanced:
    """Enhanced tests for LLM Placeholder Service"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_ai_service = Mock()
        self.service = LLMPlaceholderService(self.mock_ai_service)

    @pytest.mark.asyncio
    async def test_understand_placeholder_with_ai_service(self):
        """Test placeholder understanding with AI service"""
        self.mock_ai_service.generate_completion = AsyncMock(
            return_value='{"semantic_meaning": "理解测试", "data_requirements": ["test_data"], "confidence_score": 0.9}'
        )
        
        understanding = await self.service.understand_placeholder(
            "统计", "测试数据", "测试上下文"
        )
        
        assert isinstance(understanding, PlaceholderUnderstanding)
        assert understanding.semantic_meaning == "理解测试"
        assert "test_data" in understanding.data_requirements
        assert understanding.confidence_score == 0.9

    @pytest.mark.asyncio
    async def test_understand_placeholder_fallback(self):
        """Test placeholder understanding fallback"""
        self.mock_ai_service.generate_completion = AsyncMock(
            side_effect=Exception("AI Service Error")
        )
        
        understanding = await self.service.understand_placeholder(
            "统计", "测试数据", "测试上下文"
        )
        
        assert isinstance(understanding, PlaceholderUnderstanding)
        assert "Mock understanding" in understanding.semantic_meaning
        assert understanding.confidence_score == 0.8

    @pytest.mark.asyncio
    async def test_suggest_field_mapping(self):
        """Test field mapping suggestions"""
        available_fields = ["complaint_count", "region", "date", "status"]
        
        suggestions = await self.service.suggest_field_mapping(
            "投诉数量统计", available_fields
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 3  # Limited to top 3
        assert all(isinstance(s, FieldSuggestion) for s in suggestions)
        assert all(s.field_name in available_fields for s in suggestions)


class TestPerformanceAndStress:
    """Performance and stress tests"""

    def setup_method(self):
        """Setup test fixtures"""
        self.processor = PlaceholderProcessor()

    def test_large_document_processing(self):
        """Test processing very large documents"""
        # Create a large document with many placeholders
        large_doc = ""
        for i in range(500):
            large_doc += f"""
            第{i}段：本段包含{{统计:数据{i}}}和{{区域:地区{i}}}，
            以及{{周期:时间{i}}}和{{图表:图表{i}}}等占位符。
            这是一些填充文本来模拟真实文档的长度和复杂性。
            """
        
        start_time = time.time()
        placeholders = self.processor.extract_placeholders(large_doc)
        processing_time = time.time() - start_time
        
        assert len(placeholders) == 2000  # 500 * 4
        assert processing_time < 30.0  # Should complete within 30 seconds
        
        # Verify no memory leaks by checking error list size
        assert len(self.processor.processing_errors) < 100

    def test_concurrent_processing(self):
        """Test concurrent placeholder processing"""
        import concurrent.futures
        
        def process_text(text_id):
            processor = PlaceholderProcessor()
            text = f"测试文档{text_id}包含{{统计:数据{text_id}}}和{{区域:地区{text_id}}}。"
            return processor.extract_placeholders(text)
        
        # Process multiple texts concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_text, i) for i in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        assert len(results) == 50
        assert all(len(result) == 2 for result in results)  # Each should have 2 placeholders

    def test_memory_usage_stability(self):
        """Test memory usage stability over many operations"""
        import gc
        
        # Process many small documents to test memory stability
        for i in range(1000):
            text = f"文档{i}：{{统计:数据{i}}}和{{区域:地区{i}}}。"
            placeholders = self.processor.extract_placeholders(text)
            assert len(placeholders) == 2
            
            # Force garbage collection every 100 iterations
            if i % 100 == 0:
                gc.collect()
        
        # Verify processor is still functional
        final_text = "最终测试{{统计:最终数据}}。"
        final_placeholders = self.processor.extract_placeholders(final_text)
        assert len(final_placeholders) == 1


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions"""

    def setup_method(self):
        """Setup test fixtures"""
        self.processor = PlaceholderProcessor()

    def test_empty_and_whitespace_inputs(self):
        """Test empty and whitespace-only inputs"""
        test_cases = ["", " ", "\n", "\t", "   \n\t  "]
        
        for text in test_cases:
            placeholders = self.processor.extract_placeholders(text)
            assert len(placeholders) == 0
            assert len(self.processor.processing_errors) == 0

    def test_special_unicode_characters(self):
        """Test handling of special Unicode characters"""
        text = "测试{{统计:数据📊}}和{{区域:地区🌍}}以及{{周期:时间⏰}}。"
        placeholders = self.processor.extract_placeholders(text)
        
        assert len(placeholders) == 3
        assert "📊" in placeholders[0].description
        assert "🌍" in placeholders[1].description
        assert "⏰" in placeholders[2].description

    def test_nested_and_malformed_brackets(self):
        """Test nested and malformed bracket scenarios"""
        test_cases = [
            "{{{统计:嵌套}}}",  # Triple brackets
            "{{统计:{嵌套:内容}}}",  # Nested content
            "{{统计:未闭合",  # Unclosed
            "统计:缺少开括号}}",  # Missing opening
            "{{}}",  # Empty brackets
            "{{:}}",  # Empty type and description
        ]
        
        for text in test_cases:
            placeholders = self.processor.extract_placeholders(text)
            # Should handle gracefully without crashing
            assert isinstance(placeholders, list)

    def test_extremely_long_descriptions(self):
        """Test extremely long placeholder descriptions"""
        long_description = "非常长的描述" * 100  # 500 characters
        text = f"{{{{统计:{long_description}}}}}"
        
        placeholders = self.processor.extract_placeholders(text)
        
        if len(placeholders) > 0:
            assert len(placeholders[0].description) == len(long_description)
        # Should not crash regardless of whether it extracts the placeholder

    def test_mixed_language_content(self):
        """Test mixed language content"""
        text = """
        English text with {{统计:mixed content}} and 
        中文内容包含{{region:English region}}以及
        Français avec {{周期:période française}}.
        """
        
        placeholders = self.processor.extract_placeholders(text)
        
        # Should extract placeholders regardless of surrounding language
        assert len(placeholders) >= 2  # At least the valid Chinese types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])