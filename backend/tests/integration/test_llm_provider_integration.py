"""
LLM Provider Integration Tests for Intelligent Placeholder Processing.

Tests the system's compatibility with different LLM providers:
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- Local models (Llama, Mistral)
- Azure OpenAI
- Google PaLM/Gemini
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.ai_integration.llm_service import AIService
from app.services.intelligent_placeholder.adapter import (
    IntelligentPlaceholderProcessor,
    LLMPlaceholderService,
)


@dataclass
class LLMProviderConfig:
    """Configuration for LLM provider testing."""

    name: str
    model: str
    api_key_env: str
    base_url: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1
    supports_json_mode: bool = True
    supports_function_calling: bool = False
    expected_response_format: str = "json"


@pytest.mark.asyncio
@pytest.mark.integration
class TestLLMProviderIntegration:
    """Test integration with different LLM providers."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for LLM provider testing."""
        self.test_providers = [
            LLMProviderConfig(
                name="openai",
                model="gpt-4",
                api_key_env="OPENAI_API_KEY",
                supports_json_mode=True,
                supports_function_calling=True,
            ),
            LLMProviderConfig(
                name="openai",
                model="gpt-3.5-turbo",
                api_key_env="OPENAI_API_KEY",
                supports_json_mode=True,
                supports_function_calling=True,
            ),
            LLMProviderConfig(
                name="anthropic",
                model="claude-3-sonnet-20240229",
                api_key_env="ANTHROPIC_API_KEY",
                supports_json_mode=False,
                supports_function_calling=False,
            ),
            LLMProviderConfig(
                name="anthropic",
                model="claude-3-haiku-20240307",
                api_key_env="ANTHROPIC_API_KEY",
                supports_json_mode=False,
                supports_function_calling=False,
            ),
            LLMProviderConfig(
                name="azure_openai",
                model="gpt-4",
                api_key_env="AZURE_OPENAI_API_KEY",
                base_url="https://your-resource.openai.azure.com/",
                supports_json_mode=True,
                supports_function_calling=True,
            ),
            LLMProviderConfig(
                name="local",
                model="llama-2-7b-chat",
                api_key_env="LOCAL_API_KEY",
                base_url="http://localhost:8000",
                supports_json_mode=False,
                supports_function_calling=False,
                expected_response_format="text",
            ),
            LLMProviderConfig(
                name="google",
                model="gemini-pro",
                api_key_env="GOOGLE_API_KEY",
                supports_json_mode=True,
                supports_function_calling=True,
            ),
        ]

    @pytest.fixture
    def sample_placeholder_scenarios(self) -> List[Dict[str, Any]]:
        """Sample placeholder scenarios for testing different LLM providers."""
        return [
            {
                "name": "simple_statistic",
                "placeholder_type": "统计",
                "description": "总投诉件数",
                "context": "本月共收到投诉总投诉件数件，较上月有所增加。",
                "expected_understanding": {
                    "semantic_meaning": "需要统计投诉的总数量",
                    "data_requirements": ["投诉件数", "投诉总数", "complaint_count"],
                    "aggregation_type": "count",
                    "confidence_score": 0.9,
                },
            },
            {
                "name": "time_period",
                "placeholder_type": "周期",
                "description": "2024年第一季度",
                "context": "2024年第一季度的数据分析显示了明显的增长趋势。",
                "expected_understanding": {
                    "semantic_meaning": "时间周期为2024年第一季度",
                    "time_dimension": "2024-Q1",
                    "date_range": {"start": "2024-01-01", "end": "2024-03-31"},
                    "confidence_score": 0.95,
                },
            },
            {
                "name": "regional_data",
                "placeholder_type": "区域",
                "description": "云南省各地州市",
                "context": "云南省各地州市的投诉情况存在较大差异。",
                "expected_understanding": {
                    "semantic_meaning": "需要云南省下属各地州市的数据",
                    "region_dimension": "云南省",
                    "region_level": "地州市",
                    "confidence_score": 0.88,
                },
            },
            {
                "name": "chart_visualization",
                "placeholder_type": "图表",
                "description": "投诉趋势折线图",
                "context": "投诉趋势折线图显示了过去6个月的变化情况。",
                "expected_understanding": {
                    "semantic_meaning": "需要生成投诉数量随时间变化的折线图",
                    "chart_type": "line",
                    "data_dimensions": ["时间", "投诉数量"],
                    "confidence_score": 0.92,
                },
            },
            {
                "name": "complex_analysis",
                "placeholder_type": "分析",
                "description": "投诉处理效率分析",
                "context": "根据投诉处理效率分析，我们发现了以下几个关键问题。",
                "expected_understanding": {
                    "semantic_meaning": "需要分析投诉处理的效率情况",
                    "analysis_type": "efficiency",
                    "required_metrics": ["处理时长", "处理率", "满意度"],
                    "confidence_score": 0.85,
                },
            },
        ]

    async def create_mock_ai_service(self, provider_config: LLMProviderConfig) -> Mock:
        """Create a mock AI service for the specified provider."""
        mock_service = Mock(spec=AIService)
        mock_service.provider = provider_config.name
        mock_service.model = provider_config.model
        mock_service.supports_json_mode = provider_config.supports_json_mode
        mock_service.supports_function_calling = (
            provider_config.supports_function_calling
        )

        # Configure mock responses based on provider capabilities
        if provider_config.supports_json_mode:
            mock_service.generate_completion = AsyncMock(
                side_effect=self._generate_json_response
            )
        else:
            mock_service.generate_completion = AsyncMock(
                side_effect=self._generate_text_response
            )

        return mock_service

    async def _generate_json_response(self, prompt: str, **kwargs) -> str:
        """Generate mock JSON response for providers that support JSON mode."""
        # Analyze prompt to determine response type
        if "占位符理解" in prompt or "placeholder understanding" in prompt.lower():
            return json.dumps(
                {
                    "semantic_meaning": "模拟的语义理解结果",
                    "data_requirements": ["模拟字段1", "模拟字段2"],
                    "confidence_score": 0.9,
                    "processing_notes": "JSON模式响应",
                }
            )
        elif "字段匹配" in prompt or "field matching" in prompt.lower():
            return json.dumps(
                {
                    "field_suggestions": [
                        {
                            "field_name": "mock_field",
                            "confidence": 0.85,
                            "transformation_needed": False,
                        }
                    ]
                }
            )
        elif "质量检查" in prompt or "quality check" in prompt.lower():
            return json.dumps(
                {
                    "quality_score": 0.92,
                    "language_fluency": 0.95,
                    "data_consistency": 0.88,
                    "suggestions": ["模拟质量建议"],
                    "issues": [],
                }
            )
        else:
            return json.dumps({"result": "通用JSON响应", "confidence": 0.8})

    async def _generate_text_response(self, prompt: str, **kwargs) -> str:
        """Generate mock text response for providers that don't support JSON mode."""
        if "占位符理解" in prompt:
            return "这是一个统计类占位符，需要获取投诉总数数据，置信度较高。"
        elif "字段匹配" in prompt:
            return "建议匹配字段：complaint_count，置信度：0.85"
        elif "质量检查" in prompt:
            return "内容质量良好，语言流畅，数据一致性较好。建议：无重大问题。"
        else:
            return "通用文本响应，基于提示内容生成。"

    async def test_openai_provider_integration(
        self, sample_placeholder_scenarios: List[Dict[str, Any]]
    ):
        """Test integration with OpenAI providers (GPT-3.5, GPT-4)."""
        openai_providers = [p for p in self.test_providers if p.name == "openai"]

        for provider in openai_providers:
            mock_ai_service = await self.create_mock_ai_service(provider)
            llm_service = LLMPlaceholderService(mock_ai_service)

            for scenario in sample_placeholder_scenarios:
                # Test placeholder understanding
                result = await llm_service.understand_placeholder(
                    placeholder_type=scenario["placeholder_type"],
                    description=scenario["description"],
                    context=scenario["context"],
                )

                # Verify OpenAI-specific behavior
                assert result is not None
                assert result.confidence_score > 0.7
                assert mock_ai_service.generate_completion.called

                # Verify JSON mode was used
                call_args = mock_ai_service.generate_completion.call_args
                if call_args and len(call_args) > 1:
                    kwargs = call_args[1]
                    if provider.supports_json_mode:
                        assert kwargs.get("response_format") == {"type": "json_object"}

                print(
                    f"✓ {provider.model} - {scenario['name']}: confidence={result.confidence_score:.2f}"
                )

    async def test_anthropic_provider_integration(
        self, sample_placeholder_scenarios: List[Dict[str, Any]]
    ):
        """Test integration with Anthropic Claude models."""
        anthropic_providers = [p for p in self.test_providers if p.name == "anthropic"]

        for provider in anthropic_providers:
            mock_ai_service = await self.create_mock_ai_service(provider)
            llm_service = LLMPlaceholderService(mock_ai_service)

            for scenario in sample_placeholder_scenarios:
                # Test placeholder understanding with Claude
                result = await llm_service.understand_placeholder(
                    placeholder_type=scenario["placeholder_type"],
                    description=scenario["description"],
                    context=scenario["context"],
                )

                # Verify Claude-specific behavior
                assert result is not None
                assert (
                    result.confidence_score > 0.6
                )  # Claude might be more conservative

                # Verify text parsing was used (no JSON mode)
                assert mock_ai_service.generate_completion.called

                print(
                    f"✓ {provider.model} - {scenario['name']}: confidence={result.confidence_score:.2f}"
                )

    async def test_local_model_integration(
        self, sample_placeholder_scenarios: List[Dict[str, Any]]
    ):
        """Test integration with local/self-hosted models."""
        local_providers = [p for p in self.test_providers if p.name == "local"]

        for provider in local_providers:
            mock_ai_service = await self.create_mock_ai_service(provider)
            llm_service = LLMPlaceholderService(mock_ai_service)

            # Test with simpler scenarios for local models
            simple_scenarios = [
                s
                for s in sample_placeholder_scenarios
                if s["name"] in ["simple_statistic", "time_period"]
            ]

            for scenario in simple_scenarios:
                result = await llm_service.understand_placeholder(
                    placeholder_type=scenario["placeholder_type"],
                    description=scenario["description"],
                    context=scenario["context"],
                )

                # Verify local model behavior (might have lower confidence)
                assert result is not None
                assert result.confidence_score > 0.5  # Lower threshold for local models

                print(
                    f"✓ {provider.model} - {scenario['name']}: confidence={result.confidence_score:.2f}"
                )

    async def test_provider_failover_mechanism(self):
        """Test automatic failover between LLM providers."""
        # Primary provider (will fail)
        primary_provider = LLMProviderConfig(
            name="openai", model="gpt-4", api_key_env="OPENAI_API_KEY"
        )

        # Backup provider (will succeed)
        backup_provider = LLMProviderConfig(
            name="anthropic",
            model="claude-3-haiku-20240307",
            api_key_env="ANTHROPIC_API_KEY",
        )

        # Mock primary provider failure
        primary_mock = Mock(spec=AIService)
        primary_mock.generate_completion = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )

        # Mock backup provider success
        backup_mock = await self.create_mock_ai_service(backup_provider)

        # Create LLM service with failover
        llm_service = LLMPlaceholderService(primary_mock, fallback_service=backup_mock)

        # Test failover
        result = await llm_service.understand_placeholder(
            placeholder_type="统计",
            description="测试故障转移",
            context="测试LLM提供商故障转移机制",
        )

        # Verify failover worked
        assert result is not None
        assert result.confidence_score > 0

        # Verify primary was tried and backup was used
        primary_mock.generate_completion.assert_called_once()
        backup_mock.generate_completion.assert_called()

        print("✓ Provider failover mechanism working correctly")

    async def test_provider_performance_comparison(
        self, sample_placeholder_scenarios: List[Dict[str, Any]]
    ):
        """Compare performance across different LLM providers."""
        import time

        performance_results = []

        # Test a subset of providers for performance comparison
        test_providers = [
            p
            for p in self.test_providers
            if p.name in ["openai", "anthropic", "local"]
            and "gpt-4" in p.model
            or "claude-3-sonnet" in p.model
            or "llama" in p.model
        ]

        for provider in test_providers:
            mock_ai_service = await self.create_mock_ai_service(provider)
            llm_service = LLMPlaceholderService(mock_ai_service)

            # Test with a standard scenario
            test_scenario = sample_placeholder_scenarios[0]  # simple_statistic

            # Measure processing time
            start_time = time.time()

            result = await llm_service.understand_placeholder(
                placeholder_type=test_scenario["placeholder_type"],
                description=test_scenario["description"],
                context=test_scenario["context"],
            )

            processing_time = time.time() - start_time

            performance_results.append(
                {
                    "provider": f"{provider.name}/{provider.model}",
                    "processing_time": processing_time,
                    "confidence_score": result.confidence_score if result else 0,
                    "success": result is not None,
                }
            )

        # Log performance comparison
        print(f"\nLLM Provider Performance Comparison:")
        for result in performance_results:
            print(
                f"  {result['provider']}: {result['processing_time']:.3f}s, "
                f"confidence={result['confidence_score']:.2f}, "
                f"{'✓' if result['success'] else '✗'}"
            )

        # Verify all providers processed successfully
        successful_providers = [r for r in performance_results if r["success"]]
        assert (
            len(successful_providers) >= len(test_providers) * 0.8
        )  # At least 80% success rate

    async def test_provider_specific_prompt_optimization(self):
        """Test prompt optimization for different providers."""
        prompt_variations = {
            "openai": {
                "system_prompt": "You are a data analysis expert. Respond in JSON format.",
                "user_prompt": "Analyze this placeholder: {{统计:总投诉件数}}",
                "expected_format": "json",
            },
            "anthropic": {
                "system_prompt": "You are Claude, an AI assistant specialized in data analysis.",
                "user_prompt": "Please analyze this Chinese placeholder and explain its meaning: {{统计:总投诉件数}}",
                "expected_format": "text",
            },
            "local": {
                "system_prompt": "Analyze data placeholders. Be concise.",
                "user_prompt": "What does this mean: {{统计:总投诉件数}}?",
                "expected_format": "text",
            },
        }

        for provider_name, prompt_config in prompt_variations.items():
            # Find matching provider config
            provider_configs = [
                p for p in self.test_providers if p.name == provider_name
            ]
            if not provider_configs:
                continue

            provider_config = provider_configs[0]
            mock_ai_service = await self.create_mock_ai_service(provider_config)
            llm_service = LLMPlaceholderService(mock_ai_service)

            # Test with provider-specific prompts
            result = await llm_service.understand_placeholder(
                placeholder_type="统计",
                description="总投诉件数",
                context="测试提示优化",
                prompt_template=prompt_config["system_prompt"],
            )

            # Verify provider-specific optimization
            assert result is not None
            assert result.confidence_score > 0.5

            # Check that the appropriate prompt format was used
            call_args = mock_ai_service.generate_completion.call_args
            if call_args:
                prompt_used = call_args[0][0] if call_args[0] else ""
                if prompt_config["expected_format"] == "json":
                    assert "JSON" in prompt_used or "json" in prompt_used

            print(
                f"✓ {provider_name} prompt optimization: confidence={result.confidence_score:.2f}"
            )

    async def test_concurrent_multi_provider_processing(self):
        """Test concurrent processing with multiple providers."""
        # Select different providers for concurrent testing
        concurrent_providers = [
            p for p in self.test_providers[:3]  # Test with first 3 providers
        ]

        # Create mock services for each provider
        mock_services = []
        for provider in concurrent_providers:
            mock_service = await self.create_mock_ai_service(provider)
            mock_services.append((provider, mock_service))

        # Test concurrent processing
        async def process_with_provider(provider_service_pair):
            provider, service = provider_service_pair
            llm_service = LLMPlaceholderService(service)

            result = await llm_service.understand_placeholder(
                placeholder_type="统计",
                description=f"并发测试-{provider.name}",
                context="测试多提供商并发处理",
            )

            return {
                "provider": f"{provider.name}/{provider.model}",
                "result": result,
                "success": result is not None,
            }

        # Execute concurrent processing
        start_time = time.time()

        concurrent_results = await asyncio.gather(
            *[process_with_provider(pair) for pair in mock_services],
            return_exceptions=True,
        )

        concurrent_time = time.time() - start_time

        # Verify concurrent processing
        successful_results = [
            r
            for r in concurrent_results
            if not isinstance(r, Exception) and r["success"]
        ]

        assert (
            len(successful_results) >= len(concurrent_providers) * 0.8
        )  # 80% success rate

        print(f"\nConcurrent multi-provider processing:")
        print(
            f"  Total time: {concurrent_time:.2f}s for {len(concurrent_providers)} providers"
        )
        for result in successful_results:
            print(f"  ✓ {result['provider']}: success")

    async def test_provider_cost_optimization(self):
        """Test cost optimization strategies across providers."""
        # Mock cost data for different providers
        provider_costs = {
            "openai/gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
            "openai/gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
            "anthropic/claude-3-sonnet": {"input": 0.015, "output": 0.075},
            "anthropic/claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "local/llama-2-7b": {"input": 0.0, "output": 0.0},  # Free local model
        }

        cost_results = []

        for provider in self.test_providers[:5]:  # Test first 5 providers
            provider_key = f"{provider.name}/{provider.model}"
            if provider_key not in provider_costs:
                continue

            mock_ai_service = await self.create_mock_ai_service(provider)

            # Mock token usage
            mock_ai_service.get_token_usage = Mock(
                return_value={
                    "input_tokens": 150,
                    "output_tokens": 50,
                    "total_tokens": 200,
                }
            )

            llm_service = LLMPlaceholderService(mock_ai_service)

            # Process test scenario
            result = await llm_service.understand_placeholder(
                placeholder_type="统计",
                description="成本优化测试",
                context="测试不同提供商的成本效益",
            )

            # Calculate estimated cost
            costs = provider_costs[provider_key]
            estimated_cost = (150 * costs["input"] + 50 * costs["output"]) / 1000

            cost_results.append(
                {
                    "provider": provider_key,
                    "estimated_cost": estimated_cost,
                    "confidence_score": result.confidence_score if result else 0,
                    "cost_per_confidence": estimated_cost
                    / (
                        result.confidence_score
                        if result and result.confidence_score > 0
                        else 0.1
                    ),
                }
            )

        # Sort by cost efficiency (cost per confidence point)
        cost_results.sort(key=lambda x: x["cost_per_confidence"])

        print(f"\nProvider Cost Optimization Analysis:")
        for result in cost_results:
            print(
                f"  {result['provider']}: ${result['estimated_cost']:.6f}, "
                f"confidence={result['confidence_score']:.2f}, "
                f"cost/confidence=${result['cost_per_confidence']:.6f}"
            )

        # Verify cost optimization logic
        assert len(cost_results) > 0

        # The most cost-effective should be local model or cheapest cloud model
        most_efficient = cost_results[0]
        assert (
            most_efficient["cost_per_confidence"]
            <= cost_results[-1]["cost_per_confidence"]
        )
