"""
Enhanced comprehensive unit tests for ai_integration service module
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import json
import base64
import time
from io import BytesIO

from app.services.ai_integration.llm_service import (
    LLMProviderManager,
    LLMRequest,
    LLMResponse,
    LLMCallLog,
    LLMProviderError,
    LLMProviderType,
    AIService,
)

# Try to import other AI integration components
try:
    from app.services.ai_integration import (
        ContentGenerator,
        GeneratedContent,
        FormatConfig,
        ChartGenerator,
        ChartConfig,
        ChartResult,
    )
    HAS_EXTENDED_AI_COMPONENTS = True
except ImportError:
    HAS_EXTENDED_AI_COMPONENTS = False


class TestLLMProviderManagerEnhanced:
    """Enhanced tests for LLMProviderManager class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        self.manager = LLMProviderManager(self.mock_db)

    @patch('app.services.ai_integration.llm_service.crud')
    @patch('app.services.ai_integration.llm_service.decrypt_data')
    def test_load_providers_comprehensive(self, mock_decrypt, mock_crud):
        """Test comprehensive provider loading scenarios"""
        # Setup multiple mock providers
        mock_providers = [
            Mock(
                provider_name="openai",
                provider_type=Mock(value="openai"),
                api_key="encrypted_openai_key",
                is_active=True,
                default_model_name="gpt-3.5-turbo",
                api_base_url=None
            ),
            Mock(
                provider_name="anthropic",
                provider_type=Mock(value="anthropic"),
                api_key="encrypted_anthropic_key",
                is_active=True,
                default_model_name="claude-3-haiku-20240307",
                api_base_url=None
            ),
            Mock(
                provider_name="google",
                provider_type=Mock(value="google"),
                api_key="encrypted_google_key",
                is_active=False,  # Inactive provider
                default_model_name="gemini-pro",
                api_base_url=None
            ),
        ]
        
        mock_crud.ai_provider.get_all.return_value = mock_providers
        mock_decrypt.side_effect = lambda x: f"decrypted_{x}" if x else None
        
        self.manager._load_providers()
        
        # Verify providers loaded correctly
        assert "openai" in self.manager.providers
        assert "anthropic" in self.manager.providers
        assert "google" in self.manager.providers
        
        # Verify API keys
        assert "openai" in self.manager.api_keys
        assert "anthropic" in self.manager.api_keys
        assert "google" in self.manager.api_keys

    def test_get_available_providers_filtering(self):
        """Test provider availability filtering"""
        # Setup mock providers with different states
        mock_active_provider = Mock(is_active=True)
        mock_inactive_provider = Mock(is_active=False)
        
        self.manager.providers = {
            "active_with_key": mock_active_provider,
            "inactive_with_key": mock_inactive_provider,
            "active_no_key": mock_active_provider
        }
        self.manager.api_keys = {
            "active_with_key": "test_key",
            "inactive_with_key": "test_key"
            # "active_no_key" intentionally missing
        }
        
        available = self.manager.get_available_providers()
        
        # Only active providers with API keys should be available
        assert "active_with_key" in available
        assert "inactive_with_key" not in available
        assert "active_no_key" not in available

    def test_cost_estimation_comprehensive(self):
        """Test comprehensive cost estimation"""
        test_cases = [
            # OpenAI models
            ("gpt-3.5-turbo", 1000, 500, 0.0015 + 0.001),
            ("gpt-4", 1000, 500, 0.03 + 0.03),
            ("gpt-4-turbo", 1000, 500, 0.01 + 0.015),
            ("gpt-4o", 1000, 500, 0.005 + 0.0075),
            
            # Anthropic models
            ("claude-3-haiku", 1000, 500, 0.00025 + 0.000625),
            ("claude-3-sonnet", 1000, 500, 0.003 + 0.0075),
            ("claude-3-opus", 1000, 500, 0.015 + 0.0375),
            
            # Google models
            ("gemini-pro", 1000, 500, 0.0005 + 0.00075),
            ("gemini-1.5-pro", 1000, 500, 0.0035 + 0.00525),
            
            # Unknown model
            ("unknown-model", 1000, 500, 0.0)
        ]
        
        for model, input_tokens, output_tokens, expected_cost in test_cases:
            cost = self.manager._estimate_cost(model, input_tokens, output_tokens)
            assert abs(cost - expected_cost) < 0.0001, f"Cost mismatch for {model}"

    @patch('app.services.ai_integration.llm_service.openai.OpenAI')
    def test_call_openai_comprehensive(self, mock_openai_class):
        """Test comprehensive OpenAI API calling"""
        # Setup mock client and response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        
        mock_choice = Mock()
        mock_choice.message.content = "Test response content"
        mock_choice.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Setup provider
        mock_provider = Mock()
        mock_provider.default_model_name = "gpt-4"
        mock_provider.api_base_url = None
        
        self.manager.providers = {"openai": mock_provider}
        self.manager.api_keys = {"openai": "test_key"}
        
        # Test request
        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4",
            max_tokens=100,
            temperature=0.7,
            system_prompt="You are a helpful assistant"
        )
        
        response = self.manager._call_openai("openai", request)
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test response content"
        assert response.provider == "openai"
        assert response.model == "gpt-4"
        assert response.usage["prompt_tokens"] == 100
        assert response.usage["completion_tokens"] == 50
        assert response.cost_estimate > 0

    def test_usage_stats_comprehensive(self):
        """Test comprehensive usage statistics"""
        # Create mock call logs
        now = datetime.now()
        test_logs = [
            LLMCallLog(
                timestamp=now - timedelta(hours=1),
                provider="openai",
                model="gpt-3.5-turbo",
                request_tokens=100,
                response_tokens=50,
                total_tokens=150,
                cost_estimate=0.001,
                response_time=1.5,
                success=True
            ),
            LLMCallLog(
                timestamp=now - timedelta(hours=2),
                provider="anthropic",
                model="claude-3-haiku",
                request_tokens=200,
                response_tokens=100,
                total_tokens=300,
                cost_estimate=0.002,
                response_time=2.0,
                success=True
            ),
            LLMCallLog(
                timestamp=now - timedelta(days=2),  # Outside 24h window
                provider="openai",
                model="gpt-3.5-turbo",
                request_tokens=100,
                response_tokens=50,
                total_tokens=150,
                cost_estimate=0.001,
                response_time=1.0,
                success=True
            )
        ]
        
        self.manager.call_logs = test_logs
        
        stats = self.manager.get_usage_stats(hours=24)
        
        # Verify statistics (should only include first 2 logs within 24h)
        assert stats["total_calls"] == 2
        assert stats["successful_calls"] == 2
        assert stats["failed_calls"] == 0
        assert stats["total_cost"] == 0.003  # 0.001 + 0.002
        assert stats["total_tokens"] == 450  # 150 + 300


class TestAIServiceEnhanced:
    """Enhanced tests for AIService class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()

    @patch('app.services.ai_integration.llm_service.crud')
    @patch('app.services.ai_integration.llm_service.decrypt_data')
    @patch('app.services.ai_integration.llm_service.openai.OpenAI')
    def test_initialization_comprehensive(self, mock_openai, mock_decrypt, mock_crud):
        """Test comprehensive AI service initialization"""
        # Test successful initialization
        mock_provider = Mock()
        mock_provider.provider_type.value = "openai"
        mock_provider.api_key = "encrypted_key"
        mock_provider.api_base_url = None
        mock_provider.default_model_name = "gpt-3.5-turbo"
        
        mock_crud.ai_provider.get_active.return_value = mock_provider
        mock_decrypt.return_value = "decrypted_key"
        
        service = AIService(self.mock_db)
        
        assert service.provider is not None
        assert service.client is not None
        mock_openai.assert_called_once_with(api_key="decrypted_key", base_url=None)

    def test_health_check_comprehensive(self):
        """Test comprehensive health check scenarios"""
        # Setup service with mock provider and client
        service = AIService.__new__(AIService)  # Create without calling __init__
        service.db = self.mock_db
        service.provider = Mock()
        service.provider.provider_name = "test_provider"
        service.provider.default_model_name = "gpt-3.5-turbo"
        service.client = Mock()
        service.llm_manager = Mock()
        
        # Test successful health check
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello"
        service.client.chat.completions.create.return_value = mock_response
        
        result = service.health_check()
        
        assert result["status"] == "healthy"
        assert result["provider"] == "test_provider"
        assert result["model"] == "gpt-3.5-turbo"

    def test_interpret_description_comprehensive(self):
        """Test comprehensive description interpretation"""
        service = AIService.__new__(AIService)
        service.client = Mock()
        service.provider = Mock()
        service.provider.default_model_name = "gpt-3.5-turbo"
        
        # Test successful JSON response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "filters": [{"column": "region", "operator": "==", "value": "云南"}],
            "metrics": ["sales", "count"],
            "dimensions": ["region", "date"],
            "chart_type": "bar",
            "aggregation": "sum"
        })
        
        service.client.chat.completions.create.return_value = mock_response
        
        result = service.interpret_description_for_tool(
            task_type="chart",
            description="显示各地区销售额分布",
            df_columns=["region", "sales", "date", "count"]
        )
        
        assert "filters" in result
        assert "metrics" in result
        assert "chart_type" in result
        assert result["chart_type"] == "bar"
        assert len(result["filters"]) == 1
        assert result["filters"][0]["column"] == "region"


class TestDataClassesEnhanced:
    """Enhanced tests for data classes and configurations"""

    def test_llm_request_dataclass_comprehensive(self):
        """Test comprehensive LLMRequest dataclass functionality"""
        # Test basic request
        basic_request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert basic_request.messages[0]["content"] == "Hello"
        assert basic_request.model is None
        assert basic_request.temperature is None
        
        # Test full request
        full_request = LLMRequest(
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ],
            model="gpt-4",
            max_tokens=1000,
            temperature=0.7,
            system_prompt="Custom system prompt",
            response_format={"type": "json_object"},
            stream=True
        )
        
        assert len(full_request.messages) == 2
        assert full_request.model == "gpt-4"
        assert full_request.max_tokens == 1000
        assert full_request.temperature == 0.7
        assert full_request.system_prompt == "Custom system prompt"
        assert full_request.response_format["type"] == "json_object"
        assert full_request.stream is True

    def test_llm_response_dataclass_comprehensive(self):
        """Test comprehensive LLMResponse dataclass functionality"""
        response = LLMResponse(
            content="Test response content",
            model="gpt-4",
            provider="openai",
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            },
            response_time=2.5,
            cost_estimate=0.005,
            metadata={
                "finish_reason": "stop",
                "system_fingerprint": "fp_123"
            }
        )
        
        assert response.content == "Test response content"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 150
        assert response.response_time == 2.5
        assert response.cost_estimate == 0.005
        assert response.metadata["finish_reason"] == "stop"


class TestErrorHandlingEnhanced:
    """Enhanced error handling tests"""

    def test_llm_provider_error_comprehensive(self):
        """Test comprehensive LLM provider error handling"""
        # Test basic error
        error = LLMProviderError("Test error", "openai")
        assert str(error) == "[openai] Test error"
        assert error.provider == "openai"
        assert error.message == "Test error"
        assert error.error_code is None
        
        # Test error with code
        error_with_code = LLMProviderError(
            "Rate limit exceeded", 
            "anthropic", 
            error_code="RATE_LIMIT"
        )
        assert error_with_code.error_code == "RATE_LIMIT"

    def test_provider_manager_error_scenarios(self):
        """Test provider manager error scenarios"""
        manager = LLMProviderManager(Mock())
        
        # Test calling non-existent provider
        request = LLMRequest(messages=[{"role": "user", "content": "Test"}])
        
        with pytest.raises(LLMProviderError, match="Provider nonexistent not found"):
            manager.call_llm("nonexistent", request)


class TestPerformanceAndConcurrency:
    """Performance and concurrency tests"""

    def test_llm_call_logging_performance(self):
        """Test LLM call logging performance"""
        manager = LLMProviderManager(Mock())
        
        # Add many log entries
        start_time = time.time()
        for i in range(2000):  # More than the 1000 limit
            manager._log_call(
                provider="test",
                model="test-model",
                input_tokens=100,
                output_tokens=50,
                cost=0.001,
                response_time=1.0,
                success=True
            )
        end_time = time.time()
        
        # Should complete quickly
        assert end_time - start_time < 1.0
        
        # Should maintain only last 1000 logs
        assert len(manager.call_logs) == 1000

    @pytest.mark.asyncio
    async def test_concurrent_ai_requests(self):
        """Test concurrent AI request handling"""
        import asyncio
        
        async def mock_ai_call(request_id):
            # Simulate AI call
            await asyncio.sleep(0.1)
            return f"Response {request_id}"
        
        # Run multiple concurrent requests
        tasks = [mock_ai_call(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(f"Response {i}" == results[i] for i in range(10))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])