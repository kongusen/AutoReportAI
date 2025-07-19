"""
Unit tests for ai_integration service module
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import json
import base64
from io import BytesIO

from app.services.ai_integration import (
    AIService,
    LLMProviderManager,
    LLMRequest,
    LLMResponse,
    ContentGenerator,
    GeneratedContent,
    FormatConfig,
    ChartGenerator,
    ChartConfig,
    ChartResult,
    EnhancedAIService,
    AIRequest,
    AIResponse,
    AIModelType,
    AIServiceMetrics
)


class TestLLMProviderManager:
    """Test LLMProviderManager class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        self.manager = LLMProviderManager(self.mock_db)

    @patch('app.services.ai_integration.llm_service.crud')
    def test_load_providers(self, mock_crud):
        """Test loading providers from database"""
        # Setup mock providers
        mock_provider = Mock()
        mock_provider.provider_name = "openai"
        mock_provider.api_key = "encrypted_key"
        mock_provider.is_active = True
        
        mock_crud.ai_provider.get_all.return_value = [mock_provider]
        
        with patch('app.services.ai_integration.llm_service.decrypt_data', return_value="decrypted_key"):
            self.manager._load_providers()
        
        assert "openai" in self.manager.providers
        assert "openai" in self.manager.api_keys

    def test_get_available_providers(self):
        """Test getting available providers"""
        # Setup mock providers
        mock_provider = Mock()
        mock_provider.is_active = True
        self.manager.providers = {"openai": mock_provider}
        self.manager.api_keys = {"openai": "test_key"}
        
        available = self.manager.get_available_providers()
        
        assert "openai" in available

    def test_estimate_cost(self):
        """Test cost estimation"""
        cost = self.manager._estimate_cost("gpt-3.5-turbo", 1000, 500)
        
        assert cost > 0
        assert isinstance(cost, float)

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation for unknown model"""
        cost = self.manager._estimate_cost("unknown-model", 1000, 500)
        
        assert cost == 0.0

    @patch('app.services.ai_integration.llm_service.openai.OpenAI')
    def test_call_openai_success(self, mock_openai_class):
        """Test successful OpenAI API call"""
        # Setup mocks
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Setup provider
        mock_provider = Mock()
        mock_provider.default_model_name = "gpt-3.5-turbo"
        self.manager.providers = {"openai": mock_provider}
        self.manager.api_keys = {"openai": "test_key"}
        
        # Create request
        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=100,
            temperature=0.7
        )
        
        # Call API
        response = self.manager._call_openai("openai", request)
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.provider == "openai"
        assert response.model == "gpt-3.5-turbo"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 5

    def test_call_llm_provider_not_found(self):
        """Test calling LLM with non-existent provider"""
        request = LLMRequest(messages=[{"role": "user", "content": "Hello"}])
        
        with pytest.raises(Exception):  # Should raise LLMProviderError
            self.manager.call_llm("nonexistent", request)

    def test_call_with_fallback_success(self):
        """Test calling LLM with fallback"""
        # Mock successful call
        mock_response = LLMResponse(
            content="Test response",
            model="gpt-3.5-turbo",
            provider="openai",
            usage={},
            response_time=1.0
        )
        
        with patch.object(self.manager, 'call_llm', return_value=mock_response):
            with patch.object(self.manager, 'get_available_providers', return_value=["openai"]):
                request = LLMRequest(messages=[{"role": "user", "content": "Hello"}])
                response = self.manager.call_with_fallback(request)
        
        assert response.content == "Test response"

    def test_get_usage_stats_empty(self):
        """Test getting usage stats with no logs"""
        stats = self.manager.get_usage_stats(hours=24)
        
        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 0
        assert stats["total_cost"] == 0.0

    def test_health_check_all_providers(self):
        """Test health check for all providers"""
        # Mock successful health check
        mock_response = LLMResponse(
            content="Hello",
            model="gpt-3.5-turbo",
            provider="openai",
            usage={},
            response_time=0.5,
            cost_estimate=0.001
        )
        
        with patch.object(self.manager, 'get_available_providers', return_value=["openai"]):
            with patch.object(self.manager, 'call_llm', return_value=mock_response):
                results = self.manager.health_check_all_providers()
        
        assert "openai" in results
        assert results["openai"]["status"] == "healthy"
        assert results["openai"]["response_time"] == 0.5


class TestAIService:
    """Test AIService class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        
        # Mock provider
        self.mock_provider = Mock()
        self.mock_provider.provider_type.value = "openai"
        self.mock_provider.provider_name = "openai"
        self.mock_provider.default_model_name = "gpt-3.5-turbo"
        self.mock_provider.api_key = "encrypted_key"
        
        with patch('app.services.ai_integration.llm_service.crud') as mock_crud:
            mock_crud.ai_provider.get_active.return_value = self.mock_provider
            with patch('app.services.ai_integration.llm_service.decrypt_data', return_value="test_key"):
                with patch('app.services.ai_integration.llm_service.openai.OpenAI'):
                    self.service = AIService(self.mock_db)

    def test_initialization_success(self):
        """Test successful AI service initialization"""
        assert self.service.provider is not None
        assert self.service.client is not None

    @patch('app.services.ai_integration.llm_service.crud')
    def test_initialization_no_provider(self, mock_crud):
        """Test initialization with no active provider"""
        mock_crud.ai_provider.get_active.return_value = None
        
        with pytest.raises(ValueError, match="No active AI Provider found"):
            AIService(self.mock_db)

    def test_health_check_success(self):
        """Test successful health check"""
        # Mock successful API call
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello"
        
        self.service.client.chat.completions.create.return_value = mock_response
        
        result = self.service.health_check()
        
        assert result["status"] == "healthy"
        assert result["provider"] == "openai"

    def test_health_check_failure(self):
        """Test health check failure"""
        self.service.client.chat.completions.create.side_effect = Exception("API Error")
        
        result = self.service.health_check()
        
        assert result["status"] == "error"
        assert "API Error" in result["message"]

    def test_interpret_description_for_tool(self):
        """Test interpreting description for tool"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "filters": [{"column": "region", "operator": "==", "value": "云南"}],
            "metrics": ["sales"],
            "chart_type": "bar"
        })
        
        self.service.client.chat.completions.create.return_value = mock_response
        
        result = self.service.interpret_description_for_tool(
            task_type="chart",
            description="显示各地区销售额",
            df_columns=["region", "sales", "date"]
        )
        
        assert "filters" in result
        assert "metrics" in result
        assert "chart_type" in result
        assert result["chart_type"] == "bar"

    def test_interpret_description_invalid_json(self):
        """Test interpreting description with invalid JSON response"""
        # Mock API response with invalid JSON
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        
        self.service.client.chat.completions.create.return_value = mock_response
        
        result = self.service.interpret_description_for_tool(
            task_type="chart",
            description="显示数据",
            df_columns=["col1", "col2"]
        )
        
        # Should return basic structure when JSON parsing fails
        assert "filters" in result
        assert "metrics" in result
        assert "chart_type" in result

    def test_generate_report_content(self):
        """Test generating report content"""
        # Mock API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated report content based on the data analysis."
        
        self.service.client.chat.completions.create.return_value = mock_response
        
        data = {"total_sales": 1000, "regions": ["A", "B", "C"]}
        template_context = "Monthly sales report"
        
        result = self.service.generate_report_content(data, template_context)
        
        assert result == "Generated report content based on the data analysis."


class TestContentGenerator:
    """Test ContentGenerator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.generator = ContentGenerator()

    @pytest.mark.asyncio
    async def test_generate_content_statistic_number(self):
        """Test generating statistic content with number"""
        result = await self.generator.generate_content(
            placeholder_type="统计",
            processed_data=1234.56,
            format_config=FormatConfig(decimal_places=2)
        )
        
        assert isinstance(result, GeneratedContent)
        assert result.content_type == "number"
        assert "1,234.56" in result.content
        assert result.confidence > 0.8

    @pytest.mark.asyncio
    async def test_generate_content_statistic_currency(self):
        """Test generating statistic content with currency format"""
        format_config = FormatConfig(
            number_format="currency",
            currency_symbol="¥",
            decimal_places=2
        )
        
        result = await self.generator.generate_content(
            placeholder_type="统计",
            processed_data=1000.0,
            format_config=format_config
        )
        
        assert result.content_type == "number"
        assert "¥" in result.content
        assert "1,000.00" in result.content

    @pytest.mark.asyncio
    async def test_generate_content_statistic_percentage(self):
        """Test generating statistic content with percentage format"""
        format_config = FormatConfig(number_format="percentage")
        
        result = await self.generator.generate_content(
            placeholder_type="统计",
            processed_data=0.85,
            format_config=format_config
        )
        
        assert result.content_type == "number"
        assert "85.00%" in result.content

    @pytest.mark.asyncio
    async def test_generate_content_period_date(self):
        """Test generating period content with date"""
        result = await self.generator.generate_content(
            placeholder_type="周期",
            processed_data="2024-03-15"
        )
        
        assert result.content_type == "date"
        assert "2024" in result.content

    @pytest.mark.asyncio
    async def test_generate_content_period_relative(self):
        """Test generating period content with relative time"""
        context = {"relative_period": "this_month"}
        
        result = await self.generator.generate_content(
            placeholder_type="周期",
            processed_data="2024-03",
            context=context
        )
        
        assert result.content_type == "period"
        assert result.content == "本月"

    @pytest.mark.asyncio
    async def test_generate_content_region(self):
        """Test generating region content"""
        result = await self.generator.generate_content(
            placeholder_type="区域",
            processed_data="云南"
        )
        
        assert result.content_type == "region"
        assert result.content == "云南省"

    @pytest.mark.asyncio
    async def test_generate_content_chart(self):
        """Test generating chart content"""
        chart_data = [
            {"category": "A", "value": 100},
            {"category": "B", "value": 200},
            {"category": "C", "value": 150}
        ]
        
        result = await self.generator.generate_content(
            placeholder_type="图表",
            processed_data=chart_data
        )
        
        assert result.content_type == "chart"
        assert "3个数据点" in result.content
        assert "B(200)" in result.content

    @pytest.mark.asyncio
    async def test_generate_content_null_data(self):
        """Test generating content with null data"""
        result = await self.generator.generate_content(
            placeholder_type="统计",
            processed_data=None
        )
        
        assert result.content == "暂无数据"
        assert result.confidence < 0.5

    def test_format_number_default(self):
        """Test default number formatting"""
        config = FormatConfig()
        
        # Integer
        result = self.generator._format_number(1234, config)
        assert result == "1,234"
        
        # Float
        result = self.generator._format_number(1234.567, config)
        assert result == "1,234.57"

    def test_format_number_no_separator(self):
        """Test number formatting without thousand separator"""
        config = FormatConfig(thousand_separator=False)
        
        result = self.generator._format_number(1234.567, config)
        assert result == "1234.57"

    def test_standardize_region_name(self):
        """Test region name standardization"""
        assert self.generator._standardize_region_name("云南") == "云南省"
        assert self.generator._standardize_region_name("北京") == "北京市"
        assert self.generator._standardize_region_name("昆明市") == "昆明市"

    def test_detect_region_type(self):
        """Test region type detection"""
        assert self.generator._detect_region_type("云南省") == "province"
        assert self.generator._detect_region_type("昆明市") == "city"
        assert self.generator._detect_region_type("五华区") == "district"
        assert self.generator._detect_region_type("未知地区") == "unknown"


class TestChartGenerator:
    """Test ChartGenerator class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.generator = ChartGenerator()

    @pytest.mark.asyncio
    async def test_generate_chart_description_mode(self):
        """Test generating chart in description mode"""
        data = [
            {"category": "A", "value": 100},
            {"category": "B", "value": 200},
            {"category": "C", "value": 150}
        ]
        config = ChartConfig(chart_type="bar", title="Test Chart")
        
        result = await self.generator.generate_chart(
            data=data,
            config=config,
            output_format="description"
        )
        
        assert isinstance(result, ChartResult)
        assert result.success is True
        assert result.chart_type == "bar"
        assert "3个类别" in result.description
        assert "B" in result.description  # Highest value category

    @pytest.mark.asyncio
    async def test_generate_chart_empty_data(self):
        """Test generating chart with empty data"""
        result = await self.generator.generate_chart(
            data=[],
            config=ChartConfig(chart_type="bar"),
            output_format="description"
        )
        
        assert result.success is False
        assert "无数据可显示" in result.description

    @pytest.mark.asyncio
    async def test_generate_chart_base64_mode(self):
        """Test generating chart in base64 mode"""
        data = [
            {"category": "A", "value": 100},
            {"category": "B", "value": 200}
        ]
        config = ChartConfig(chart_type="bar", title="Test Chart")
        
        # This will fall back to description mode if matplotlib is not available
        result = await self.generator.generate_chart(
            data=data,
            config=config,
            output_format="base64"
        )
        
        assert isinstance(result, ChartResult)
        assert result.success is True

    def test_describe_bar_chart(self):
        """Test bar chart description"""
        data = [
            {"category": "A", "value": 100},
            {"category": "B", "value": 200},
            {"category": "C", "value": 150}
        ]
        config = ChartConfig(chart_type="bar")
        
        description = self.generator._describe_bar_chart(data, config)
        
        assert "3个类别" in description
        assert "450" in description  # Total
        assert "B" in description and "200" in description  # Max value

    def test_describe_line_chart(self):
        """Test line chart description"""
        data = [
            {"value": 100},
            {"value": 150},
            {"value": 200}
        ]
        config = ChartConfig(chart_type="line")
        
        description = self.generator._describe_line_chart(data, config)
        
        assert "3个时间点" in description
        assert "上升" in description  # Trend

    def test_describe_pie_chart(self):
        """Test pie chart description"""
        data = [
            {"label": "A", "value": 100},
            {"label": "B", "value": 200},
            {"label": "C", "value": 100}
        ]
        config = ChartConfig(chart_type="pie")
        
        description = self.generator._describe_pie_chart(data, config)
        
        assert "3个分类" in description
        assert "B" in description  # Largest category
        assert "50.0%" in description  # B's percentage

    def test_describe_scatter_chart(self):
        """Test scatter chart description"""
        data = [{"x": 1, "y": 2}, {"x": 2, "y": 4}, {"x": 3, "y": 6}]
        config = ChartConfig(chart_type="scatter")
        
        description = self.generator._describe_scatter_chart(data, config)
        
        assert "3个数据点" in description
        assert "分布关系" in description


class TestDataClasses:
    """Test data classes and configurations"""

    def test_llm_request_dataclass(self):
        """Test LLMRequest dataclass"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-3.5-turbo",
            max_tokens=100,
            temperature=0.7
        )
        
        assert request.messages[0]["content"] == "Hello"
        assert request.model == "gpt-3.5-turbo"
        assert request.max_tokens == 100
        assert request.temperature == 0.7

    def test_llm_response_dataclass(self):
        """Test LLMResponse dataclass"""
        response = LLMResponse(
            content="Test response",
            model="gpt-3.5-turbo",
            provider="openai",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            response_time=1.5,
            cost_estimate=0.001
        )
        
        assert response.content == "Test response"
        assert response.model == "gpt-3.5-turbo"
        assert response.provider == "openai"
        assert response.response_time == 1.5

    def test_format_config_dataclass(self):
        """Test FormatConfig dataclass"""
        config = FormatConfig(
            number_format="currency",
            decimal_places=3,
            currency_symbol="$"
        )
        
        assert config.number_format == "currency"
        assert config.decimal_places == 3
        assert config.currency_symbol == "$"

    def test_chart_config_dataclass(self):
        """Test ChartConfig dataclass"""
        config = ChartConfig(
            chart_type="line",
            title="Test Chart",
            width=1000,
            height=800
        )
        
        assert config.chart_type == "line"
        assert config.title == "Test Chart"
        assert config.width == 1000
        assert config.height == 800

    def test_generated_content_dataclass(self):
        """Test GeneratedContent dataclass"""
        content = GeneratedContent(
            content="Test content",
            content_type="text",
            format_applied="default",
            metadata={"test": "data"},
            confidence=0.9
        )
        
        assert content.content == "Test content"
        assert content.content_type == "text"
        assert content.confidence == 0.9
        assert content.metadata["test"] == "data"


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_content_generator_error_handling(self):
        """Test content generator error handling"""
        generator = ContentGenerator()
        
        # Test with invalid data that might cause an exception
        with patch.object(generator, '_format_number', side_effect=Exception("Format error")):
            result = await generator.generate_content(
                placeholder_type="统计",
                processed_data=1234
            )
        
        assert result.format_applied == "error"
        assert "Format error" in result.metadata["error"]

    @pytest.mark.asyncio
    async def test_chart_generator_error_handling(self):
        """Test chart generator error handling"""
        generator = ChartGenerator()
        
        # Test with data that might cause an exception
        with patch.object(generator, '_describe_bar_chart', side_effect=Exception("Chart error")):
            result = await generator.generate_chart(
                data=[{"category": "A", "value": 100}],
                config=ChartConfig(chart_type="bar"),
                output_format="description"
            )
        
        assert result.success is False
        assert "Chart error" in result.error_message


class TestModuleIntegration:
    """Test module integration and exports"""

    def test_module_exports(self):
        """Test that all expected classes are exported"""
        from app.services.ai_integration import (
            AIService,
            LLMProviderManager,
            LLMRequest,
            LLMResponse,
            ContentGenerator,
            GeneratedContent,
            FormatConfig,
            ChartGenerator,
            ChartConfig,
            ChartResult
        )
        
        # Verify classes can be imported and instantiated
        assert AIService is not None
        assert LLMProviderManager is not None
        assert LLMRequest is not None
        assert LLMResponse is not None
        assert ContentGenerator is not None
        assert GeneratedContent is not None
        assert FormatConfig is not None
        assert ChartGenerator is not None
        assert ChartConfig is not None
        assert ChartResult is not None

    def test_module_version(self):
        """Test module version"""
        import app.services.ai_integration as module
        assert hasattr(module, '__version__')
        assert module.__version__ == "1.0.0"


class TestIntegrationScenarios:
    """Test integration scenarios"""

    @pytest.mark.asyncio
    async def test_end_to_end_content_generation(self):
        """Test end-to-end content generation workflow"""
        # Setup
        generator = ContentGenerator()
        
        # Test different content types
        test_cases = [
            ("统计", 1234.56, "number"),
            ("周期", "2024-03-15", "date"),
            ("区域", "云南", "region"),
            ("图表", [{"category": "A", "value": 100}], "chart")
        ]
        
        for placeholder_type, data, expected_type in test_cases:
            result = await generator.generate_content(
                placeholder_type=placeholder_type,
                processed_data=data
            )
            
            assert isinstance(result, GeneratedContent)
            assert result.content_type == expected_type
            assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_chart_generation_workflow(self):
        """Test complete chart generation workflow"""
        # Setup
        generator = ChartGenerator()
        
        # Test data
        data = [
            {"category": "产品A", "value": 1000},
            {"category": "产品B", "value": 1500},
            {"category": "产品C", "value": 800}
        ]
        
        config = ChartConfig(
            chart_type="bar",
            title="产品销售对比",
            x_label="产品",
            y_label="销售额"
        )
        
        # Generate chart
        result = await generator.generate_chart(
            data=data,
            config=config,
            output_format="description"
        )
        
        # Verify result
        assert result.success is True
        assert result.chart_type == "bar"
        assert "产品B" in result.description  # Highest value
        assert "3个类别" in result.description