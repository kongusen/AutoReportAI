"""
AI服务集成单元测试

测试LLM服务集成、多提供商支持、错误处理和成本跟踪功能。
"""

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.ai_integration.llm_service import (
    AIService,
    LLMProviderType,
    LLMProviderManager,
    LLMRequest,
    LLMResponse,
)


class TestAIService:
    """AI服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def ai_service(self, mock_db):
        """创建AI服务实例"""
        return AIService(mock_db)

    @pytest.fixture
    def sample_llm_request(self):
        """示例LLM请求"""
        return LLMRequest(
            messages=[
                {"role": "user", "content": "分析这个占位符：{{统计:总投诉件数}}"}
            ],
            system_prompt="你是一个专业的占位符分析专家",
            max_tokens=500,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

    @pytest.fixture
    def sample_llm_response_content(self):
        """示例LLM响应内容"""
        return {
            "semantic_meaning": "统计投诉总数量",
            "data_type": "integer",
            "field_suggestions": ["complaint_count", "total_complaints"],
            "calculation_needed": True,
            "aggregation_type": "count",
            "confidence": 0.95,
        }

    def test_ai_service_initialization(self, ai_service, mock_db):
        """测试AI服务初始化"""
        assert ai_service.db == mock_db
        assert hasattr(ai_service, "usage_stats")
        assert hasattr(ai_service, "cost_tracker")
        assert hasattr(ai_service, "error_handler")

    @patch("app.services.ai_service.openai.ChatCompletion.create")
    def test_call_openai_success(
        self,
        mock_openai_create,
        ai_service,
        sample_llm_request,
        sample_llm_response_content,
    ):
        """测试OpenAI调用成功"""
        # 模拟OpenAI响应
        mock_openai_create.return_value = {
            "choices": [
                {"message": {"content": json.dumps(sample_llm_response_content)}}
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
            "model": "gpt-3.5-turbo",
        }

        # 调用服务
        response = ai_service.call_llm_unified(sample_llm_request, provider="openai")

        # 验证响应
        assert isinstance(response, LLMResponse)
        assert response.provider == "openai"
        assert response.model == "gpt-3.5-turbo"
        assert json.loads(response.content) == sample_llm_response_content
        assert response.usage["total_tokens"] == 150
        assert response.cost_estimate > 0
        assert response.response_time > 0

        # 验证OpenAI被正确调用
        mock_openai_create.assert_called_once()
        call_args = mock_openai_create.call_args[1]
        assert call_args["model"] == "gpt-3.5-turbo"
        assert call_args["max_tokens"] == 500
        assert call_args["temperature"] == 0.1

    @patch("app.services.ai_service.anthropic.Anthropic")
    def test_call_claude_success(
        self,
        mock_anthropic_class,
        ai_service,
        sample_llm_request,
        sample_llm_response_content,
    ):
        """测试Claude调用成功"""
        # 模拟Anthropic客户端
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = json.dumps(sample_llm_response_content)
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.model = "claude-3-sonnet-20240229"

        mock_client.messages.create.return_value = mock_response

        # 调用服务
        response = ai_service.call_llm_unified(sample_llm_request, provider="claude")

        # 验证响应
        assert isinstance(response, LLMResponse)
        assert response.provider == "claude"
        assert response.model == "claude-3-sonnet-20240229"
        assert json.loads(response.content) == sample_llm_response_content
        assert response.usage["input_tokens"] == 100
        assert response.usage["output_tokens"] == 50

    def test_call_llm_invalid_provider(self, ai_service, sample_llm_request):
        """测试无效提供商处理"""
        with pytest.raises(ValueError) as exc_info:
            ai_service.call_llm_unified(sample_llm_request, provider="invalid_provider")

        assert "不支持的LLM提供商" in str(exc_info.value)

    @patch("app.services.ai_service.openai.ChatCompletion.create")
    def test_call_llm_openai_error(
        self, mock_openai_create, ai_service, sample_llm_request
    ):
        """测试OpenAI调用错误处理"""
        # 模拟OpenAI异常
        mock_openai_create.side_effect = Exception("OpenAI API错误")

        with pytest.raises(Exception) as exc_info:
            ai_service.call_llm_unified(sample_llm_request, provider="openai")

        assert "OpenAI API错误" in str(exc_info.value)

    @patch("app.services.ai_service.openai.ChatCompletion.create")
    def test_call_llm_with_retry(
        self, mock_openai_create, ai_service, sample_llm_request
    ):
        """测试LLM调用重试机制"""
        # 第一次调用失败，第二次成功
        mock_openai_create.side_effect = [
            Exception("临时错误"),
            {
                "choices": [{"message": {"content": '{"result": "success"}'}}],
                "usage": {"total_tokens": 100},
                "model": "gpt-3.5-turbo",
            },
        ]

        # 启用重试
        response = ai_service.call_llm_unified(
            sample_llm_request, provider="openai", max_retries=2
        )

        # 验证最终成功
        assert response.content == '{"result": "success"}'
        assert mock_openai_create.call_count == 2

    def test_calculate_cost_openai(self, ai_service):
        """测试OpenAI成本计算"""
        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost = ai_service._calculate_cost("openai", "gpt-3.5-turbo", usage)

        # 验证成本计算合理
        assert cost > 0
        assert isinstance(cost, float)

    def test_calculate_cost_claude(self, ai_service):
        """测试Claude成本计算"""
        usage = {"input_tokens": 1000, "output_tokens": 500}
        cost = ai_service._calculate_cost("claude", "claude-3-sonnet-20240229", usage)

        # 验证成本计算合理
        assert cost > 0
        assert isinstance(cost, float)

    def test_calculate_cost_unknown_model(self, ai_service):
        """测试未知模型成本计算"""
        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost = ai_service._calculate_cost("openai", "unknown-model", usage)

        # 未知模型应该返回0或默认值
        assert cost >= 0

    def test_track_usage_stats(self, ai_service):
        """测试使用统计跟踪"""
        # 模拟多次调用
        for i in range(5):
            ai_service._track_usage_stats(
                provider="openai",
                model="gpt-3.5-turbo",
                usage={"total_tokens": 100 + i * 10},
                cost=0.001 + i * 0.0001,
                response_time=1.0 + i * 0.1,
            )

        # 获取统计信息
        stats = ai_service.get_llm_usage_stats(hours=24)

        # 验证统计
        assert stats["total_calls"] == 5
        assert stats["total_tokens"] == 600  # 100+110+120+130+140
        assert stats["total_cost"] > 0
        assert stats["avg_response_time"] > 0
        assert "openai" in stats["provider_distribution"]
        assert stats["provider_distribution"]["openai"] == 5

    def test_get_usage_stats_time_filter(self, ai_service):
        """测试使用统计时间过滤"""
        # 添加一些统计数据
        ai_service._track_usage_stats(
            "openai", "gpt-3.5-turbo", {"total_tokens": 100}, 0.001, 1.0
        )

        # 测试不同时间范围
        stats_24h = ai_service.get_llm_usage_stats(hours=24)
        stats_1h = ai_service.get_llm_usage_stats(hours=1)

        # 24小时范围应该包含数据
        assert stats_24h["total_calls"] >= 1

        # 验证统计结构
        assert "total_calls" in stats_24h
        assert "total_tokens" in stats_24h
        assert "total_cost" in stats_24h
        assert "avg_response_time" in stats_24h
        assert "provider_distribution" in stats_24h
        assert "model_distribution" in stats_24h

    def test_get_cost_breakdown(self, ai_service):
        """测试成本分解"""
        # 添加不同提供商的使用数据
        ai_service._track_usage_stats(
            "openai", "gpt-3.5-turbo", {"total_tokens": 1000}, 0.002, 1.0
        )
        ai_service._track_usage_stats(
            "claude", "claude-3-sonnet-20240229", {"total_tokens": 500}, 0.003, 1.2
        )

        breakdown = ai_service.get_cost_breakdown(hours=24)

        # 验证成本分解结构
        assert "total_cost" in breakdown
        assert "by_provider" in breakdown
        assert "by_model" in breakdown
        assert "cost_trend" in breakdown

        # 验证提供商分解
        assert len(breakdown["by_provider"]) >= 1

        # 验证模型分解
        assert len(breakdown["by_model"]) >= 1

    def test_error_handling_and_logging(self, ai_service, sample_llm_request):
        """测试错误处理和日志记录"""
        with patch(
            "app.services.ai_service.openai.ChatCompletion.create"
        ) as mock_create:
            # 模拟API错误
            mock_create.side_effect = Exception("API限流错误")

            # 记录错误前的统计
            initial_stats = ai_service.get_llm_usage_stats(hours=1)
            initial_calls = initial_stats.get("total_calls", 0)

            # 调用应该抛出异常
            with pytest.raises(Exception):
                ai_service.call_llm_unified(sample_llm_request, provider="openai")

            # 验证错误被记录（如果有错误跟踪机制）
            # 这里可以检查日志或错误统计

    def test_concurrent_calls(self, ai_service, sample_llm_request):
        """测试并发调用处理"""
        import threading
        import time

        results = []
        errors = []

        def make_call():
            try:
                with patch(
                    "app.services.ai_service.openai.ChatCompletion.create"
                ) as mock_create:
                    mock_create.return_value = {
                        "choices": [{"message": {"content": '{"result": "success"}'}}],
                        "usage": {"total_tokens": 100},
                        "model": "gpt-3.5-turbo",
                    }

                    response = ai_service.call_llm_unified(
                        sample_llm_request, provider="openai"
                    )
                    results.append(response)
            except Exception as e:
                errors.append(e)

        # 创建多个线程并发调用
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_call)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0  # 不应该有错误
        assert len(results) == 5  # 应该有5个成功响应

    def test_request_validation(self, ai_service):
        """测试请求验证"""
        # 测试空消息
        invalid_request = LLMRequest(messages=[], system_prompt="测试", max_tokens=100)

        with pytest.raises(ValueError) as exc_info:
            ai_service.call_llm_unified(invalid_request)

        assert (
            "消息不能为空" in str(exc_info.value)
            or "messages" in str(exc_info.value).lower()
        )

        # 测试无效的max_tokens
        invalid_request = LLMRequest(
            messages=[{"role": "user", "content": "test"}], max_tokens=-1
        )

        with pytest.raises(ValueError) as exc_info:
            ai_service.call_llm_unified(invalid_request)

        assert "max_tokens" in str(exc_info.value).lower()

    def test_response_parsing(self, ai_service, sample_llm_request):
        """测试响应解析"""
        with patch(
            "app.services.ai_service.openai.ChatCompletion.create"
        ) as mock_create:
            # 测试正常JSON响应
            mock_create.return_value = {
                "choices": [{"message": {"content": '{"valid": "json"}'}}],
                "usage": {"total_tokens": 100},
                "model": "gpt-3.5-turbo",
            }

            response = ai_service.call_llm_unified(
                sample_llm_request, provider="openai"
            )
            assert response.content == '{"valid": "json"}'

            # 测试无效JSON响应（应该仍然返回原始内容）
            mock_create.return_value = {
                "choices": [{"message": {"content": "invalid json content"}}],
                "usage": {"total_tokens": 100},
                "model": "gpt-3.5-turbo",
            }

            response = ai_service.call_llm_unified(
                sample_llm_request, provider="openai"
            )
            assert response.content == "invalid json content"

    def test_model_selection(self, ai_service, sample_llm_request):
        """测试模型选择"""
        with patch(
            "app.services.ai_service.openai.ChatCompletion.create"
        ) as mock_create:
            mock_create.return_value = {
                "choices": [{"message": {"content": "test"}}],
                "usage": {"total_tokens": 100},
                "model": "gpt-4",
            }

            # 测试指定模型
            response = ai_service.call_llm_unified(
                sample_llm_request, provider="openai", model="gpt-4"
            )

            assert response.model == "gpt-4"

            # 验证调用参数
            call_args = mock_create.call_args[1]
            assert call_args["model"] == "gpt-4"


class TestLLMRequest:
    """LLM请求数据类测试"""

    def test_llm_request_creation(self):
        """测试LLM请求创建"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="system",
            max_tokens=500,
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        assert len(request.messages) == 1
        assert request.messages[0]["content"] == "test"
        assert request.system_prompt == "system"
        assert request.max_tokens == 500
        assert request.temperature == 0.7
        assert request.response_format == {"type": "json_object"}

    def test_llm_request_defaults(self):
        """测试LLM请求默认值"""
        request = LLMRequest(messages=[{"role": "user", "content": "test"}])

        assert request.system_prompt is None
        assert request.max_tokens == 1000
        assert request.temperature == 0.1
        assert request.response_format is None


class TestLLMResponse:
    """LLM响应数据类测试"""

    def test_llm_response_creation(self):
        """测试LLM响应创建"""
        response = LLMResponse(
            content="test response",
            model="gpt-3.5-turbo",
            provider="openai",
            usage={"total_tokens": 100},
            response_time=1.5,
            cost_estimate=0.002,
        )

        assert response.content == "test response"
        assert response.model == "gpt-3.5-turbo"
        assert response.provider == "openai"
        assert response.usage == {"total_tokens": 100}
        assert response.response_time == 1.5
        assert response.cost_estimate == 0.002


class TestLLMProviderType:
    """LLM提供商类型枚举测试"""

    def test_llm_provider_type_values(self):
        """测试LLM提供商类型枚举值"""
        assert LLMProviderType.OPENAI.value == "openai"
        assert LLMProviderType.CLAUDE.value == "claude"
        assert LLMProviderType.LOCAL.value == "local"

    def test_llm_provider_type_from_string(self):
        """测试从字符串创建LLM提供商类型"""
        assert LLMProviderType("openai") == LLMProviderType.OPENAI
        assert LLMProviderType("claude") == LLMProviderType.CLAUDE
        assert LLMProviderType("local") == LLMProviderType.LOCAL





if __name__ == "__main__":
    pytest.main([__file__, "-v"])
