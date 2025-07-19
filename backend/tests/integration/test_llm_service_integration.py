"""
LLM服务集成框架单元测试

测试多LLM提供商支持、统一接口、错误处理和成本跟踪功能。
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.services.ai_integration.llm_service import (
    AIService,
    LLMCallLog,
    LLMProviderError,
    LLMProviderManager,
    LLMRequest,
    LLMResponse,
)


class TestLLMProviderManager:
    """LLM提供商管理器测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def mock_providers(self):
        """模拟AI提供商数据"""
        openai_provider = Mock()
        openai_provider.provider_name = "openai-test"
        openai_provider.provider_type.value = "openai"
        openai_provider.default_model_name = "gpt-3.5-turbo"
        openai_provider.is_active = True
        openai_provider.api_key = "encrypted_openai_key"
        openai_provider.api_base_url = None

        claude_provider = Mock()
        claude_provider.provider_name = "claude-test"
        claude_provider.provider_type.value = "anthropic"
        claude_provider.default_model_name = "claude-3-haiku-20240307"
        claude_provider.is_active = True
        claude_provider.api_key = "encrypted_claude_key"
        claude_provider.api_base_url = None

        return [openai_provider, claude_provider]

    @patch("app.services.ai_service.crud.ai_provider.get_all")
    @patch("app.services.ai_service.decrypt_data")
    def test_load_providers(self, mock_decrypt, mock_get_all, mock_db, mock_providers):
        """测试提供商加载"""
        mock_get_all.return_value = mock_providers
        mock_decrypt.side_effect = ["decrypted_openai_key", "decrypted_claude_key"]

        manager = LLMProviderManager(mock_db)

        assert len(manager.providers) == 2
        assert "openai-test" in manager.providers
        assert "claude-test" in manager.providers
        assert len(manager.api_keys) == 2

    @patch("app.services.ai_service.crud.ai_provider.get_all")
    @patch("app.services.ai_service.decrypt_data")
    def test_get_available_providers(
        self, mock_decrypt, mock_get_all, mock_db, mock_providers
    ):
        """测试获取可用提供商"""
        mock_get_all.return_value = mock_providers
        mock_decrypt.side_effect = ["decrypted_openai_key", "decrypted_claude_key"]

        manager = LLMProviderManager(mock_db)
        available = manager.get_available_providers()

        assert len(available) == 2
        assert "openai-test" in available
        assert "claude-test" in available

    def test_estimate_cost(self, mock_db):
        """测试成本估算"""
        manager = LLMProviderManager(mock_db)

        # 测试已知模型
        cost = manager._estimate_cost("gpt-3.5-turbo", 1000, 500)
        expected_cost = (1000 / 1000 * 0.0015) + (500 / 1000 * 0.002)
        assert cost == expected_cost

        # 测试未知模型
        cost = manager._estimate_cost("unknown-model", 1000, 500)
        assert cost == 0.0

    @patch("app.services.ai_service.openai.OpenAI")
    @patch("app.services.ai_service.crud.ai_provider.get_all")
    @patch("app.services.ai_service.decrypt_data")
    def test_call_openai_success(
        self, mock_decrypt, mock_get_all, mock_openai_client, mock_db, mock_providers
    ):
        """测试OpenAI调用成功"""
        # 设置模拟
        mock_get_all.return_value = [mock_providers[0]]  # 只返回OpenAI提供商
        mock_decrypt.return_value = "decrypted_key"

        # 模拟OpenAI响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client

        manager = LLMProviderManager(mock_db)

        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=100,
            temperature=0.7,
        )

        response = manager._call_openai("openai-test", request)

        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.provider == "openai-test"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 5
        assert response.cost_estimate > 0

    @patch("app.services.ai_service.openai.OpenAI")
    @patch("app.services.ai_service.crud.ai_provider.get_all")
    @patch("app.services.ai_service.decrypt_data")
    def test_call_openai_error(
        self, mock_decrypt, mock_get_all, mock_openai_client, mock_db, mock_providers
    ):
        """测试OpenAI调用错误"""
        mock_get_all.return_value = [mock_providers[0]]
        mock_decrypt.return_value = "decrypted_key"

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_client.return_value = mock_client

        manager = LLMProviderManager(mock_db)

        request = LLMRequest(messages=[{"role": "user", "content": "Hello"}])

        with pytest.raises(LLMProviderError) as exc_info:
            manager._call_openai("openai-test", request)

        assert "OpenAI API call failed" in str(exc_info.value)
        assert exc_info.value.provider == "openai-test"

    @patch("app.services.ai_service.crud.ai_provider.get_all")
    @patch("app.services.ai_service.decrypt_data")
    def test_call_with_fallback_success(
        self, mock_decrypt, mock_get_all, mock_db, mock_providers
    ):
        """测试回退机制成功"""
        mock_get_all.return_value = mock_providers
        mock_decrypt.side_effect = ["decrypted_openai_key", "decrypted_claude_key"]

        manager = LLMProviderManager(mock_db)

        # 模拟第一个提供商失败，第二个成功
        with patch.object(manager, "call_llm") as mock_call:
            mock_call.side_effect = [
                LLMProviderError("First provider failed", "openai-test"),
                LLMResponse(
                    content="Success from second provider",
                    model="claude-3-haiku",
                    provider="claude-test",
                    usage={},
                    response_time=1.0,
                    cost_estimate=0.001,
                ),
            ]

            request = LLMRequest(messages=[{"role": "user", "content": "Hello"}])
            response = manager.call_with_fallback(request)

            assert response.content == "Success from second provider"
            assert response.provider == "claude-test"
            assert mock_call.call_count == 2

    @patch("app.services.ai_service.crud.ai_provider.get_all")
    @patch("app.services.ai_service.decrypt_data")
    def test_call_with_fallback_all_fail(
        self, mock_decrypt, mock_get_all, mock_db, mock_providers
    ):
        """测试回退机制全部失败"""
        mock_get_all.return_value = mock_providers
        mock_decrypt.side_effect = ["decrypted_openai_key", "decrypted_claude_key"]

        manager = LLMProviderManager(mock_db)

        # 模拟所有提供商都失败
        with patch.object(manager, "call_llm") as mock_call:
            mock_call.side_effect = LLMProviderError("All providers failed", "test")

            request = LLMRequest(messages=[{"role": "user", "content": "Hello"}])

            with pytest.raises(LLMProviderError):
                manager.call_with_fallback(request)

    def test_log_call(self, mock_db):
        """测试调用日志记录"""
        manager = LLMProviderManager(mock_db)

        manager._log_call(
            provider="test-provider",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            response_time=1.5,
            success=True,
        )

        assert len(manager.call_logs) == 1
        log = manager.call_logs[0]
        assert log.provider == "test-provider"
        assert log.model == "test-model"
        assert log.request_tokens == 100
        assert log.response_tokens == 50
        assert log.total_tokens == 150
        assert log.cost_estimate == 0.01
        assert log.response_time == 1.5
        assert log.success is True

    def test_get_usage_stats_empty(self, mock_db):
        """测试空使用统计"""
        manager = LLMProviderManager(mock_db)
        stats = manager.get_usage_stats(24)

        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["total_tokens"] == 0
        assert stats["avg_response_time"] == 0.0

    def test_get_usage_stats_with_data(self, mock_db):
        """测试有数据的使用统计"""
        manager = LLMProviderManager(mock_db)

        # 添加测试日志
        manager.call_logs = [
            LLMCallLog(
                timestamp=datetime.now(),
                provider="openai-test",
                model="gpt-3.5-turbo",
                request_tokens=100,
                response_tokens=50,
                total_tokens=150,
                cost_estimate=0.01,
                response_time=1.0,
                success=True,
            ),
            LLMCallLog(
                timestamp=datetime.now(),
                provider="claude-test",
                model="claude-3-haiku",
                request_tokens=80,
                response_tokens=40,
                total_tokens=120,
                cost_estimate=0.008,
                response_time=1.2,
                success=False,
                error_message="Test error",
            ),
        ]

        stats = manager.get_usage_stats(24)

        assert stats["total_calls"] == 2
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["total_cost"] == 0.018
        assert stats["total_tokens"] == 270
        assert stats["avg_response_time"] == 1.1

        # 检查提供商统计
        assert "openai-test" in stats["providers"]
        assert "claude-test" in stats["providers"]
        assert stats["providers"]["openai-test"]["success_rate"] == 1.0
        assert stats["providers"]["claude-test"]["success_rate"] == 0.0

    @patch("app.services.ai_service.crud.ai_provider.get_all")
    @patch("app.services.ai_service.decrypt_data")
    def test_health_check_all_providers(
        self, mock_decrypt, mock_get_all, mock_db, mock_providers
    ):
        """测试所有提供商健康检查"""
        mock_get_all.return_value = mock_providers
        mock_decrypt.side_effect = ["decrypted_openai_key", "decrypted_claude_key"]

        manager = LLMProviderManager(mock_db)

        # 模拟健康检查调用
        with patch.object(manager, "call_llm") as mock_call:
            mock_call.side_effect = [
                LLMResponse(
                    content="OK",
                    model="gpt-3.5-turbo",
                    provider="openai-test",
                    usage={},
                    response_time=0.5,
                    cost_estimate=0.001,
                ),
                LLMProviderError("Health check failed", "claude-test"),
            ]

            results = manager.health_check_all_providers()

            assert len(results) == 2
            assert results["openai-test"]["status"] == "healthy"
            assert results["openai-test"]["model"] == "gpt-3.5-turbo"
            assert results["claude-test"]["status"] == "error"
            assert "Health check failed" in results["claude-test"]["error"]


class TestAIServiceEnhanced:
    """增强AI服务测试"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def mock_ai_service(self, mock_db):
        with patch("app.services.ai_service.crud.ai_provider.get_active"):
            with patch("app.services.ai_service.LLMProviderManager"):
                service = AIService(mock_db)
                service.llm_manager = Mock()
                return service

    def test_call_llm_unified_success(self, mock_ai_service):
        """测试统一LLM调用成功"""
        mock_response = LLMResponse(
            content="Test response",
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            response_time=1.0,
            cost_estimate=0.001,
        )

        mock_ai_service.llm_manager.call_llm.return_value = mock_response

        request = LLMRequest(messages=[{"role": "user", "content": "Hello"}])
        response = mock_ai_service.call_llm_unified(request, "openai-test")

        assert response.content == "Test response"
        assert response.provider == "openai-test"
        mock_ai_service.llm_manager.call_llm.assert_called_once_with(
            "openai-test", request
        )

    def test_call_llm_unified_fallback(self, mock_ai_service):
        """测试统一LLM调用回退"""
        mock_response = LLMResponse(
            content="Fallback response",
            model="claude-3-haiku",
            provider="claude-test",
            usage={},
            response_time=1.2,
            cost_estimate=0.002,
        )

        mock_ai_service.llm_manager.call_with_fallback.return_value = mock_response

        request = LLMRequest(messages=[{"role": "user", "content": "Hello"}])
        response = mock_ai_service.call_llm_unified(request)

        assert response.content == "Fallback response"
        assert response.provider == "claude-test"
        mock_ai_service.llm_manager.call_with_fallback.assert_called_once_with(request)

    def test_call_llm_unified_error(self, mock_ai_service):
        """测试统一LLM调用错误"""
        mock_ai_service.llm_manager.call_llm.side_effect = LLMProviderError(
            "Test error", "test-provider"
        )

        request = LLMRequest(messages=[{"role": "user", "content": "Hello"}])

        with pytest.raises(ValueError) as exc_info:
            mock_ai_service.call_llm_unified(request, "test-provider")

        assert "LLM service unavailable" in str(exc_info.value)

    def test_understand_placeholder_semantics_success(self, mock_ai_service):
        """测试占位符语义理解成功"""
        mock_response = LLMResponse(
            content=json.dumps(
                {
                    "semantic_meaning": "统计投诉总数",
                    "data_type": "integer",
                    "field_suggestions": ["complaint_count", "total_complaints"],
                    "calculation_needed": True,
                    "aggregation_type": "count",
                    "confidence": 0.9,
                }
            ),
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={},
            response_time=1.0,
            cost_estimate=0.001,
        )

        mock_ai_service.llm_manager.call_with_fallback.return_value = mock_response

        result = mock_ai_service.understand_placeholder_semantics(
            placeholder_type="统计",
            description="总投诉件数",
            context="2024年共受理投诉{{统计:总投诉件数}}件",
            available_fields=["complaint_count", "complaint_date", "region"],
        )

        assert result["semantic_meaning"] == "统计投诉总数"
        assert result["data_type"] == "integer"
        assert result["aggregation_type"] == "count"
        assert result["confidence"] == 0.9

    def test_understand_placeholder_semantics_parse_error(self, mock_ai_service):
        """测试占位符语义理解解析错误"""
        mock_response = LLMResponse(
            content="Invalid JSON response",
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={},
            response_time=1.0,
            cost_estimate=0.001,
        )

        mock_ai_service.llm_manager.call_with_fallback.return_value = mock_response

        result = mock_ai_service.understand_placeholder_semantics(
            placeholder_type="统计", description="总投诉件数", context="测试上下文"
        )

        assert result["confidence"] == 0.0
        assert "无法理解占位符" in result["semantic_meaning"]

    def test_generate_etl_instructions_success(self, mock_ai_service):
        """测试ETL指令生成成功"""
        mock_response = LLMResponse(
            content=json.dumps(
                {
                    "query_type": "aggregate",
                    "source_tables": ["complaints"],
                    "filters": [{"column": "year", "operator": "==", "value": 2024}],
                    "aggregations": [{"function": "count", "column": "id"}],
                    "calculations": [],
                    "output_format": "scalar",
                }
            ),
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={},
            response_time=1.0,
            cost_estimate=0.001,
        )

        mock_ai_service.llm_manager.call_with_fallback.return_value = mock_response

        result = mock_ai_service.generate_etl_instructions(
            placeholder_type="统计",
            description="总投诉件数",
            data_source_schema={
                "tables": ["complaints"],
                "columns": ["id", "date", "type"],
            },
        )

        assert result["query_type"] == "aggregate"
        assert result["source_tables"] == ["complaints"]
        assert len(result["filters"]) == 1
        assert len(result["aggregations"]) == 1

    def test_optimize_report_content_success(self, mock_ai_service):
        """测试报告内容优化成功"""
        mock_response = LLMResponse(
            content="优化后的专业报告内容，语言更加流畅和准确。",
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={},
            response_time=1.5,
            cost_estimate=0.002,
        )

        mock_ai_service.llm_manager.call_with_fallback.return_value = mock_response

        original_content = "原始报告内容，需要优化。"
        context = {"report_type": "complaint_analysis", "region": "昆明市"}

        result = mock_ai_service.optimize_report_content(original_content, context)

        assert result == "优化后的专业报告内容，语言更加流畅和准确。"

    def test_optimize_report_content_error(self, mock_ai_service):
        """测试报告内容优化错误"""
        mock_ai_service.llm_manager.call_with_fallback.side_effect = Exception(
            "Optimization failed"
        )

        original_content = "原始报告内容"
        context = {}

        result = mock_ai_service.optimize_report_content(original_content, context)

        # 应该返回原始内容
        assert result == original_content

    def test_validate_data_consistency_success(self, mock_ai_service):
        """测试数据一致性验证成功"""
        mock_response = LLMResponse(
            content=json.dumps(
                {
                    "is_valid": True,
                    "issues": [],
                    "suggestions": ["数据质量良好"],
                    "confidence": 0.95,
                }
            ),
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={},
            response_time=1.0,
            cost_estimate=0.001,
        )

        mock_ai_service.llm_manager.call_with_fallback.return_value = mock_response

        data = {"total_complaints": 2141, "wechat_complaints": 356}
        schema = {"total_complaints": "integer", "wechat_complaints": "integer"}

        result = mock_ai_service.validate_data_consistency(data, schema)

        assert result["is_valid"] is True
        assert len(result["issues"]) == 0
        assert result["confidence"] == 0.95

    def test_get_llm_usage_stats(self, mock_ai_service):
        """测试获取LLM使用统计"""
        mock_stats = {
            "total_calls": 10,
            "successful_calls": 8,
            "failed_calls": 2,
            "total_cost": 0.05,
            "avg_response_time": 1.2,
        }

        mock_ai_service.llm_manager.get_usage_stats.return_value = mock_stats

        result = mock_ai_service.get_llm_usage_stats(24)

        assert result == mock_stats
        mock_ai_service.llm_manager.get_usage_stats.assert_called_once_with(24)

    def test_health_check_all_llm_providers(self, mock_ai_service):
        """测试所有LLM提供商健康检查"""
        mock_health_results = {
            "openai-test": {"status": "healthy", "response_time": 0.5},
            "claude-test": {"status": "error", "error": "API key invalid"},
        }

        mock_ai_service.llm_manager.health_check_all_providers.return_value = (
            mock_health_results
        )

        result = mock_ai_service.health_check_all_llm_providers()

        assert result == mock_health_results
        mock_ai_service.llm_manager.health_check_all_providers.assert_called_once()

    def test_get_available_llm_providers(self, mock_ai_service):
        """测试获取可用LLM提供商"""
        mock_providers = ["openai-test", "claude-test"]
        mock_ai_service.llm_manager.get_available_providers.return_value = (
            mock_providers
        )

        result = mock_ai_service.get_available_llm_providers()

        assert result == mock_providers
        mock_ai_service.llm_manager.get_available_providers.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
