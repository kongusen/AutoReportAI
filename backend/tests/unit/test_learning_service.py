"""
学习服务测试

测试错误处理和学习机制的各项功能
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.learning_data import (
    ErrorLog,
    KnowledgeBase,
    LearningRule,
    LLMCallLog,
    PlaceholderProcessingHistory,
)
from app.models.learning_data import UserFeedback as UserFeedbackModel
from app.models.placeholder_mapping import PlaceholderMapping
from app.services.learning_service import (
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    FeedbackType,
    LearningService,
    UserFeedback,
    get_learning_service,
)


class TestLearningService:
    """学习服务测试类"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.all.return_value = []
        db.query.return_value.count.return_value = 0
        db.commit.return_value = None
        db.rollback.return_value = None
        return db

    @pytest.fixture
    def learning_service(self, mock_db):
        """创建学习服务实例"""
        with patch("app.services.learning_service.asyncio.create_task"):
            service = LearningService(mock_db)
            return service

    @pytest.mark.asyncio
    async def test_record_error_success(self, learning_service):
        """测试成功记录错误"""
        error_id = await learning_service.record_error(
            category=ErrorCategory.PARSING_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message="测试错误消息",
            placeholder_text="{{统计:总投诉件数}}",
            placeholder_type="统计",
            placeholder_description="总投诉件数",
            context_before="前置上下文",
            context_after="后置上下文",
            data_source_id=1,
            user_id=1,
            session_id="test_session",
        )

        assert error_id is not None
        assert len(error_id) == 16  # MD5 hash前16位
        assert error_id in learning_service.error_cache

        # 验证错误上下文
        error_context = learning_service.error_cache[error_id]
        assert error_context.category == ErrorCategory.PARSING_ERROR
        assert error_context.severity == ErrorSeverity.MEDIUM
        assert error_context.message == "测试错误消息"
        assert error_context.placeholder_text == "{{统计:总投诉件数}}"

    @pytest.mark.asyncio
    async def test_collect_user_feedback_success(self, learning_service):
        """测试成功收集用户反馈"""
        feedback_id = await learning_service.collect_user_feedback(
            user_id=1,
            feedback_type=FeedbackType.CORRECTION,
            placeholder_text="{{统计:总投诉件数}}",
            original_result="错误结果",
            corrected_result="正确结果",
            suggested_field="complaint_count",
            confidence_rating=4,
            comments="这个字段匹配更准确",
        )

        assert feedback_id is not None
        assert len(feedback_id) == 16
        assert len(learning_service.feedback_cache) == 1

        # 验证反馈内容
        feedback = learning_service.feedback_cache[0]
        assert feedback.user_id == 1
        assert feedback.feedback_type == FeedbackType.CORRECTION
        assert feedback.placeholder_text == "{{统计:总投诉件数}}"
        assert feedback.corrected_result == "正确结果"

    @pytest.mark.asyncio
    async def test_learn_from_success(self, learning_service):
        """测试从成功案例学习"""
        with (
            patch.object(
                learning_service, "_update_mapping_cache"
            ) as mock_update_cache,
            patch.object(learning_service, "_update_knowledge_base") as mock_update_kb,
        ):

            await learning_service.learn_from_success(
                placeholder_text="{{统计:总投诉件数}}",
                placeholder_type="统计",
                matched_field="complaint_count",
                confidence_score=0.95,
                data_source_id=1,
                processing_time=1.5,
            )

            # 验证调用了更新方法
            mock_update_cache.assert_called_once()
            mock_update_kb.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_knowledge_base(self, learning_service):
        """测试查询知识库"""
        with (
            patch.object(learning_service, "_query_exact_match") as mock_exact,
            patch.object(learning_service, "_query_pattern_matches") as mock_pattern,
            patch.object(learning_service, "_query_semantic_matches") as mock_semantic,
        ):

            # 模拟返回结果
            mock_exact.return_value = {
                "field": "complaint_count",
                "confidence": 0.95,
                "usage_count": 10,
            }
            mock_pattern.return_value = []
            mock_semantic.return_value = []

            suggestions = await learning_service.query_knowledge_base(
                placeholder_text="{{统计:总投诉件数}}",
                placeholder_type="统计",
                data_source_id=1,
                context="投诉数据统计报告",
            )

            assert len(suggestions) == 1
            assert suggestions[0]["type"] == "exact_match"
            assert suggestions[0]["field"] == "complaint_count"
            assert suggestions[0]["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_get_error_statistics(self, learning_service):
        """测试获取错误统计"""
        # 添加一些测试错误
        await learning_service.record_error(
            category=ErrorCategory.PARSING_ERROR,
            severity=ErrorSeverity.MEDIUM,
            message="解析错误1",
            placeholder_text="{{统计:数量1}}",
            placeholder_type="统计",
        )

        await learning_service.record_error(
            category=ErrorCategory.LLM_ERROR,
            severity=ErrorSeverity.HIGH,
            message="LLM错误1",
            placeholder_text="{{周期:本月}}",
            placeholder_type="周期",
        )

        # 获取统计信息
        stats = await learning_service.get_error_statistics()

        assert stats["total_errors"] == 2
        assert "parsing_error" in stats["category_distribution"]
        assert "llm_error" in stats["category_distribution"]
        assert stats["category_distribution"]["parsing_error"] == 1
        assert stats["category_distribution"]["llm_error"] == 1

    @pytest.mark.asyncio
    async def test_get_learning_metrics(self, learning_service):
        """测试获取学习指标"""
        with patch.object(
            learning_service, "_get_cache_statistics"
        ) as mock_cache_stats:
            mock_cache_stats.return_value = {
                "total_mappings": 100,
                "average_confidence": 0.85,
            }

            metrics = await learning_service.get_learning_metrics()

            assert "cache_statistics" in metrics
            assert "feedback_statistics" in metrics
            assert "learning_rule_statistics" in metrics
            assert "knowledge_base_statistics" in metrics
            assert "learning_effectiveness" in metrics

    def test_generate_placeholder_signature(self, learning_service):
        """测试生成占位符签名"""
        signature1 = learning_service._generate_placeholder_signature(
            "{{统计:总投诉件数}}", "统计", 1
        )
        signature2 = learning_service._generate_placeholder_signature(
            "{{统计:总投诉件数}}", "统计", 1
        )
        signature3 = learning_service._generate_placeholder_signature(
            "{{统计:总投诉件数}}", "统计", 2
        )

        # 相同输入应该产生相同签名
        assert signature1 == signature2
        # 不同数据源应该产生不同签名
        assert signature1 != signature3
        # 签名应该是32位MD5哈希
        assert len(signature1) == 32

    @pytest.mark.asyncio
    async def test_auto_learning_trigger(self, learning_service):
        """测试自动学习触发"""
        with patch.object(learning_service, "_trigger_auto_learning") as mock_trigger:
            learning_service.auto_learning_enabled = True

            await learning_service.record_error(
                category=ErrorCategory.FIELD_MATCHING_ERROR,
                severity=ErrorSeverity.MEDIUM,
                message="字段匹配错误",
                placeholder_text="{{统计:总数量}}",
            )

            # 验证触发了自动学习
            mock_trigger.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_review_trigger(self, learning_service):
        """测试人工审核触发"""
        with patch.object(learning_service, "_trigger_manual_review") as mock_trigger:
            # 记录严重错误
            await learning_service.record_error(
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.CRITICAL,
                message="系统严重错误",
            )

            # 验证触发了人工审核
            mock_trigger.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_mapping_cache(self, learning_service, mock_db):
        """测试更新映射缓存"""
        # 模拟数据库查询返回None（新映射）
        mock_db.query.return_value.filter.return_value.first.return_value = None

        await learning_service._update_mapping_cache(
            signature="test_signature",
            data_source_id=1,
            matched_field="test_field",
            confidence_score=0.9,
        )

        # 验证调用了数据库操作
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_knowledge_base(self, learning_service):
        """测试更新知识库"""
        signature = "test_signature"

        # 第一次更新（创建新条目）
        await learning_service._update_knowledge_base(
            signature=signature,
            matched_field="test_field",
            confidence_score=0.9,
            success=True,
        )

        assert signature in learning_service.knowledge_base
        entry = learning_service.knowledge_base[signature]
        assert len(entry.successful_mappings) == 1
        assert entry.successful_mappings[0]["field"] == "test_field"

        # 第二次更新（添加失败案例）
        await learning_service._update_knowledge_base(
            signature=signature,
            matched_field="wrong_field",
            confidence_score=0.3,
            success=False,
        )

        assert len(entry.failed_mappings) == 1
        assert entry.failed_mappings[0]["field"] == "wrong_field"

    def test_error_categories_and_severities(self):
        """测试错误分类和严重程度枚举"""
        # 测试所有错误分类
        categories = [
            ErrorCategory.PARSING_ERROR,
            ErrorCategory.LLM_ERROR,
            ErrorCategory.FIELD_MATCHING_ERROR,
            ErrorCategory.ETL_ERROR,
            ErrorCategory.CONTENT_GENERATION_ERROR,
            ErrorCategory.VALIDATION_ERROR,
            ErrorCategory.SYSTEM_ERROR,
        ]

        for category in categories:
            assert isinstance(category.value, str)
            assert len(category.value) > 0

        # 测试所有严重程度
        severities = [
            ErrorSeverity.LOW,
            ErrorSeverity.MEDIUM,
            ErrorSeverity.HIGH,
            ErrorSeverity.CRITICAL,
        ]

        for severity in severities:
            assert isinstance(severity.value, str)
            assert len(severity.value) > 0

    def test_feedback_types(self):
        """测试反馈类型枚举"""
        feedback_types = [
            FeedbackType.CORRECTION,
            FeedbackType.IMPROVEMENT,
            FeedbackType.VALIDATION,
            FeedbackType.COMPLAINT,
        ]

        for feedback_type in feedback_types:
            assert isinstance(feedback_type.value, str)
            assert len(feedback_type.value) > 0


class TestLearningServiceIntegration:
    """学习服务集成测试"""

    @pytest.mark.asyncio
    async def test_complete_learning_workflow(self):
        """测试完整的学习工作流程"""
        # 这个测试需要真实的数据库连接
        # 在实际环境中运行
        pass

    @pytest.mark.asyncio
    async def test_error_recovery_and_learning(self):
        """测试错误恢复和学习流程"""
        # 模拟完整的错误处理和学习流程
        pass


# 便捷函数测试


@pytest.mark.asyncio
async def test_get_learning_service():
    """测试获取学习服务实例"""
    with patch("app.services.learning_service.get_db") as mock_get_db:
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db

        with patch("app.services.learning_service.asyncio.create_task"):
            service = await get_learning_service()
            assert isinstance(service, LearningService)
            assert service.db == mock_db


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
