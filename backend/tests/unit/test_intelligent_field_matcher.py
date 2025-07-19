"""
智能字段匹配器单元测试

测试语义相似度计算、模糊匹配、缓存机制和置信度评分功能。
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.intelligent_placeholder import IntelligentFieldMatcher
from app.services.intelligent_placeholder.matcher import (
    FieldMatchingResult,
    FieldSuggestion,
    SimilarityScore,
)


class TestIntelligentFieldMatcher:
    """智能字段匹配器测试"""

    @pytest.fixture
    def matcher(self):
        """创建字段匹配器实例"""
        return IntelligentFieldMatcher(similarity_threshold=0.8)

    @pytest.fixture
    def sample_llm_suggestions(self):
        """示例LLM建议"""
        return [
            FieldSuggestion(
                field_name="complaint_count",
                confidence=0.9,
                transformation_needed=False,
                transformation_type="none",
                reasoning="直接匹配投诉数量字段",
            ),
            FieldSuggestion(
                field_name="total_complaints",
                confidence=0.8,
                transformation_needed=True,
                transformation_type="rename",
                calculation_formula=None,
                reasoning="语义相似的备选字段",
            ),
        ]

    @pytest.fixture
    def sample_available_fields(self):
        """示例可用字段"""
        return [
            "complaint_count",
            "total_complaints",
            "complaint_date",
            "region_name",
            "complaint_type",
            "resolution_status",
            "response_time_minutes",
        ]

    def test_matcher_initialization(self, matcher):
        """测试匹配器初始化"""
        assert matcher.similarity_threshold == 0.8
        assert matcher.cache_ttl == 3600 * 24 * 7  # 7天
        # 模型初始化可能失败，但不应该影响基本功能
        assert hasattr(matcher, "embedding_model")
        assert hasattr(matcher, "redis_client")

    @pytest.mark.asyncio
    async def test_match_fields_direct_match(
        self, matcher, sample_llm_suggestions, sample_available_fields
    ):
        """测试直接字段匹配"""
        result = await matcher.match_fields(
            llm_suggestions=sample_llm_suggestions,
            available_fields=sample_available_fields,
            placeholder_context="统计投诉数量相关信息",
        )

        # 验证匹配结果
        assert isinstance(result, FieldMatchingResult)
        assert result.matched_field == "complaint_count"  # 应该选择置信度最高的直接匹配
        assert result.confidence >= 0.8
        assert result.processing_time > 0
        assert not result.cache_hit  # 第一次调用不应该命中缓存

    @pytest.mark.asyncio
    async def test_match_fields_no_suggestions(self, matcher):
        """测试无建议情况"""
        result = await matcher.match_fields(
            llm_suggestions=[],
            available_fields=["field1", "field2"],
            placeholder_context="测试上下文",
        )

        assert result.matched_field == ""
        assert result.confidence == 0.0
        assert "No suggestions" in result.reasoning

    @pytest.mark.asyncio
    async def test_match_fields_no_available_fields(
        self, matcher, sample_llm_suggestions
    ):
        """测试无可用字段情况"""
        result = await matcher.match_fields(
            llm_suggestions=sample_llm_suggestions,
            available_fields=[],
            placeholder_context="测试上下文",
        )

        assert result.matched_field == ""
        assert result.confidence == 0.0
        assert "No suggestions" in result.reasoning

    @pytest.mark.asyncio
    async def test_match_fields_with_transformation(
        self, matcher, sample_available_fields
    ):
        """测试需要转换的字段匹配"""
        suggestions_with_transformation = [
            FieldSuggestion(
                field_name="complaint_total",  # 不在可用字段中
                confidence=0.9,
                transformation_needed=True,
                transformation_type="calculation",
                calculation_formula="SUM(complaint_count)",
                reasoning="需要计算总数",
            )
        ]

        result = await matcher.match_fields(
            llm_suggestions=suggestions_with_transformation,
            available_fields=sample_available_fields,
            placeholder_context="需要计算投诉总数",
        )

        # 应该通过相似度匹配找到最接近的字段
        assert result.matched_field in sample_available_fields
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_calculate_similarity_scores(
        self, matcher, sample_llm_suggestions, sample_available_fields
    ):
        """测试相似度评分计算"""
        scores = await matcher._calculate_similarity_scores(
            sample_llm_suggestions, sample_available_fields, "投诉数量统计"
        )

        assert isinstance(scores, list)
        assert len(scores) > 0

        # 验证评分结构
        for score in scores:
            assert isinstance(score, SimilarityScore)
            assert score.field_name in sample_available_fields
            assert 0 <= score.semantic_score <= 1
            assert 0 <= score.fuzzy_score <= 1
            assert 0 <= score.combined_score <= 1
            assert isinstance(score.reasoning, str)

        # 验证排序（应该按综合分数降序）
        for i in range(len(scores) - 1):
            assert scores[i].combined_score >= scores[i + 1].combined_score

    def test_calculate_fuzzy_similarity(self, matcher, sample_available_fields):
        """测试模糊匹配相似度计算"""
        query_field = "complaint_count"
        fuzzy_scores = matcher._calculate_fuzzy_similarity(
            query_field, sample_available_fields
        )

        assert isinstance(fuzzy_scores, dict)
        assert len(fuzzy_scores) == len(sample_available_fields)

        # 验证完全匹配得分最高
        assert fuzzy_scores["complaint_count"] == 1.0

        # 验证相似字段得分较高
        assert fuzzy_scores["total_complaints"] > 0.3

        # 验证所有分数在合理范围内
        for field, score in fuzzy_scores.items():
            assert 0 <= score <= 1

    def test_jaccard_similarity(self, matcher):
        """测试Jaccard相似度计算"""
        # 完全相同
        assert matcher._calculate_jaccard_similarity("test", "test") == 1.0

        # 完全不同
        assert matcher._calculate_jaccard_similarity("abc", "xyz") == 0.0

        # 部分相同
        similarity = matcher._calculate_jaccard_similarity("complaint", "complain")
        assert 0 < similarity < 1

        # 空字符串
        assert matcher._calculate_jaccard_similarity("", "test") == 0.0
        assert matcher._calculate_jaccard_similarity("test", "") == 0.0

    def test_edit_similarity(self, matcher):
        """测试编辑距离相似度计算"""
        # 完全相同
        assert matcher._calculate_edit_similarity("test", "test") == 1.0

        # 包含关系
        similarity = matcher._calculate_edit_similarity("complaint", "complain")
        assert 0 < similarity < 1

        # 空字符串
        assert matcher._calculate_edit_similarity("", "test") == 0.0
        assert matcher._calculate_edit_similarity("test", "") == 0.0

    def test_lcs_similarity(self, matcher):
        """测试最长公共子序列相似度计算"""
        # 完全相同
        assert matcher._calculate_lcs_similarity("test", "test") == 1.0

        # 有公共子序列
        similarity = matcher._calculate_lcs_similarity("complaint", "complain")
        assert 0 < similarity < 1

        # 无公共子序列
        similarity = matcher._calculate_lcs_similarity("abc", "xyz")
        assert similarity >= 0

        # 空字符串
        assert matcher._calculate_lcs_similarity("", "test") == 0.0

    def test_generate_cache_key(
        self, matcher, sample_llm_suggestions, sample_available_fields
    ):
        """测试缓存键生成"""
        cache_key1 = matcher._generate_cache_key(
            sample_llm_suggestions, sample_available_fields, "context1"
        )

        cache_key2 = matcher._generate_cache_key(
            sample_llm_suggestions, sample_available_fields, "context2"
        )

        # 不同上下文应该生成不同的缓存键
        assert cache_key1 != cache_key2
        assert cache_key1.startswith("field_match:")
        assert cache_key2.startswith("field_match:")

        # 相同输入应该生成相同的缓存键
        cache_key3 = matcher._generate_cache_key(
            sample_llm_suggestions, sample_available_fields, "context1"
        )
        assert cache_key1 == cache_key3

    @pytest.mark.asyncio
    async def test_caching_mechanism(
        self, matcher, sample_llm_suggestions, sample_available_fields
    ):
        """测试缓存机制"""
        # 第一次调用
        result1 = await matcher.match_fields(
            llm_suggestions=sample_llm_suggestions,
            available_fields=sample_available_fields,
            placeholder_context="缓存测试",
        )

        # 模拟缓存存在的情况
        if matcher.redis_client:
            # 第二次调用相同参数（应该命中缓存）
            result2 = await matcher.match_fields(
                llm_suggestions=sample_llm_suggestions,
                available_fields=sample_available_fields,
                placeholder_context="缓存测试",
            )

            # 验证结果一致
            assert result1.matched_field == result2.matched_field
            assert result1.confidence == result2.confidence

    @pytest.mark.asyncio
    async def test_error_handling(self, matcher):
        """测试错误处理"""
        # 模拟异常情况
        with patch.object(
            matcher, "_find_best_match", side_effect=Exception("测试异常")
        ):
            result = await matcher.match_fields(
                llm_suggestions=[
                    FieldSuggestion(
                        field_name="test_field",
                        confidence=0.9,
                        transformation_needed=False,
                        transformation_type="none",
                    )
                ],
                available_fields=["field1", "field2"],
                placeholder_context="错误测试",
            )

            # 应该返回默认结果而不是抛出异常
            assert result.matched_field == "test_field"
            assert result.confidence == 0.0
            assert "Error occurred" in result.reasoning

    @pytest.mark.asyncio
    async def test_semantic_similarity_without_model(
        self, matcher, sample_available_fields
    ):
        """测试无语义模型时的相似度计算"""
        # 强制禁用语义模型
        matcher.embedding_model = None

        query_text = "complaint count field"
        semantic_scores = await matcher._calculate_semantic_similarity(
            query_text, sample_available_fields
        )

        # 无模型时应该返回空字典
        assert isinstance(semantic_scores, dict)
        assert len(semantic_scores) == 0

    @pytest.mark.asyncio
    async def test_fuzzy_match_only_fallback(
        self, matcher, sample_llm_suggestions, sample_available_fields
    ):
        """测试仅使用模糊匹配的回退机制"""
        scores = await matcher._fuzzy_match_only(
            sample_llm_suggestions, sample_available_fields
        )

        assert isinstance(scores, list)
        assert len(scores) > 0

        # 验证所有分数都是模糊匹配分数
        for score in scores:
            assert score.semantic_score == 0.0
            assert score.fuzzy_score > 0
            assert score.combined_score > 0

    @pytest.mark.asyncio
    async def test_get_historical_mappings(self, matcher):
        """测试获取历史映射记录"""
        # 模拟数据库查询
        with (
            patch("app.services.intelligent_field_matcher.get_db") as mock_get_db,
            patch(
                "app.services.intelligent_field_matcher.crud_placeholder_mapping"
            ) as mock_crud,
        ):

            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db

            # 模拟查询结果
            mock_mapping = Mock()
            mock_mapping.placeholder_signature = "test_signature"
            mock_mapping.matched_field = "test_field"
            mock_mapping.confidence_score = 0.9
            mock_mapping.usage_count = 5
            mock_mapping.last_used_at = None
            mock_mapping.transformation_config = {"type": "none"}

            mock_crud.get_by_data_source.return_value = [mock_mapping]

            # 调用方法
            mappings = await matcher.get_historical_mappings(data_source_id=1, limit=10)

            # 验证结果
            assert len(mappings) == 1
            assert mappings[0]["signature"] == "test_signature"
            assert mappings[0]["matched_field"] == "test_field"
            assert mappings[0]["confidence"] == 0.9
            assert mappings[0]["usage_count"] == 5

    @pytest.mark.asyncio
    async def test_save_mapping_to_db(self, matcher, sample_llm_suggestions):
        """测试保存映射到数据库"""
        result = FieldMatchingResult(
            matched_field="test_field",
            confidence=0.9,
            requires_transformation=False,
            transformation_config={},
            fallback_options=[],
            processing_time=1.0,
        )

        with (
            patch("app.services.intelligent_field_matcher.get_db") as mock_get_db,
            patch(
                "app.services.intelligent_field_matcher.crud_placeholder_mapping"
            ) as mock_crud,
        ):

            mock_db = Mock()
            mock_get_db.return_value.__next__.return_value = mock_db
            mock_crud.get_by_signature.return_value = None  # 不存在记录

            # 调用方法
            await matcher._save_mapping_to_db(
                sample_llm_suggestions, result, data_source_id=1, context="测试上下文"
            )

            # 验证创建了新记录
            mock_crud.create.assert_called_once()
            create_args = mock_crud.create.call_args[1]["obj_in"]
            assert create_args["matched_field"] == "test_field"
            assert create_args["confidence_score"] == 0.9
            assert create_args["data_source_id"] == 1


class TestFieldSuggestion:
    """字段建议数据类测试"""

    def test_field_suggestion_creation(self):
        """测试字段建议创建"""
        suggestion = FieldSuggestion(
            field_name="test_field",
            confidence=0.9,
            transformation_needed=True,
            transformation_type="calculation",
            calculation_formula="SUM(field)",
            reasoning="测试原因",
        )

        assert suggestion.field_name == "test_field"
        assert suggestion.confidence == 0.9
        assert suggestion.transformation_needed is True
        assert suggestion.transformation_type == "calculation"
        assert suggestion.calculation_formula == "SUM(field)"
        assert suggestion.reasoning == "测试原因"

    def test_field_suggestion_defaults(self):
        """测试字段建议默认值"""
        suggestion = FieldSuggestion(
            field_name="test_field",
            confidence=0.8,
            transformation_needed=False,
            transformation_type="none",
        )

        assert suggestion.calculation_formula is None
        assert suggestion.reasoning is None


class TestFieldMatchingResult:
    """字段匹配结果数据类测试"""

    def test_field_matching_result_creation(self):
        """测试字段匹配结果创建"""
        result = FieldMatchingResult(
            matched_field="matched_field",
            confidence=0.85,
            requires_transformation=True,
            transformation_config={"type": "rename"},
            fallback_options=["option1", "option2"],
            processing_time=1.5,
            cache_hit=True,
            reasoning="匹配原因",
        )

        assert result.matched_field == "matched_field"
        assert result.confidence == 0.85
        assert result.requires_transformation is True
        assert result.transformation_config == {"type": "rename"}
        assert result.fallback_options == ["option1", "option2"]
        assert result.processing_time == 1.5
        assert result.cache_hit is True
        assert result.reasoning == "匹配原因"

    def test_field_matching_result_defaults(self):
        """测试字段匹配结果默认值"""
        result = FieldMatchingResult(
            matched_field="test_field",
            confidence=0.8,
            requires_transformation=False,
            transformation_config={},
            fallback_options=[],
            processing_time=1.0,
        )

        assert result.cache_hit is False
        assert result.reasoning is None


class TestSimilarityScore:
    """相似度评分数据类测试"""

    def test_similarity_score_creation(self):
        """测试相似度评分创建"""
        score = SimilarityScore(
            field_name="test_field",
            semantic_score=0.8,
            fuzzy_score=0.7,
            combined_score=0.75,
            reasoning="相似度计算原因",
        )

        assert score.field_name == "test_field"
        assert score.semantic_score == 0.8
        assert score.fuzzy_score == 0.7
        assert score.combined_score == 0.75
        assert score.reasoning == "相似度计算原因"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
