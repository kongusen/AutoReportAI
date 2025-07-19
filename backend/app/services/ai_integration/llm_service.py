import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import openai
import pandas as pd
from sqlalchemy.orm import Session

from app import crud
from app.core.security_utils import decrypt_data
from app.schemas.ai_provider import AIProvider
from ..mcp_client import mcp_client

# Configure logging
logger = logging.getLogger(__name__)

# Try to import additional LLM providers
try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available. Claude support disabled.")

try:
    import google.generativeai as genai
    from google.generativeai import GenerativeModel

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google AI library not available. Gemini support disabled.")


class LLMProviderType(Enum):
    """Supported LLM provider types"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"


@dataclass
class LLMRequest:
    """Standardized LLM request structure"""

    messages: List[Dict[str, str]]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    response_format: Optional[Dict[str, Any]] = None
    stream: bool = False


@dataclass
class LLMResponse:
    """Standardized LLM response structure"""

    content: str
    model: str
    provider: str
    usage: Dict[str, Any]
    response_time: float
    cost_estimate: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMCallLog:
    """LLM call logging structure"""

    timestamp: datetime
    provider: str
    model: str
    request_tokens: int
    response_tokens: int
    total_tokens: int
    cost_estimate: float
    response_time: float
    success: bool
    error_message: Optional[str] = None


class LLMProviderError(Exception):
    """Custom exception for LLM provider errors"""

    def __init__(self, message: str, provider: str, error_code: Optional[str] = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(f"[{provider}] {message}")


class LLMProviderManager:
    """Manages multiple LLM providers with unified interface"""

    # Cost estimates per 1K tokens (approximate)
    COST_ESTIMATES = {
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "gemini-pro": {"input": 0.0005, "output": 0.0015},
        "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
    }

    def __init__(self, db: Session):
        self.db = db
        self.providers = {}
        self.call_logs: List[LLMCallLog] = []
        self.api_keys = {}
        self._load_providers()

    def _load_providers(self):
        """Load all available providers from database"""
        try:
            all_providers = crud.ai_provider.get_all(self.db)
            for provider in all_providers:
                if provider.api_key:
                    try:
                        decrypted_key = decrypt_data(provider.api_key)
                        self.api_keys[provider.provider_name] = decrypted_key
                        self.providers[provider.provider_name] = provider
                        logger.info(f"Loaded provider: {provider.provider_name}")
                    except Exception as e:
                        logger.error(
                            f"Failed to decrypt key for {provider.provider_name}: {e}"
                        )
        except Exception as e:
            logger.error(f"Failed to load providers: {e}")

    def get_available_providers(self) -> List[str]:
        """Get list of available and configured providers"""
        available = []
        for name, provider in self.providers.items():
            if provider.is_active and name in self.api_keys:
                available.append(name)
        return available

    def _create_openai_client(self, provider_name: str) -> openai.OpenAI:
        """Create OpenAI client"""
        provider = self.providers[provider_name]
        api_key = self.api_keys[provider_name]

        return openai.OpenAI(
            api_key=api_key,
            base_url=str(provider.api_base_url) if provider.api_base_url else None,
        )

    def _create_anthropic_client(self, provider_name: str):
        """Create Anthropic client"""
        if not ANTHROPIC_AVAILABLE:
            raise LLMProviderError("Anthropic library not available", provider_name)

        api_key = self.api_keys[provider_name]
        return anthropic.Anthropic(api_key=api_key)

    def _create_google_client(self, provider_name: str):
        """Create Google AI client"""
        if not GOOGLE_AVAILABLE:
            raise LLMProviderError("Google AI library not available", provider_name)

        api_key = self.api_keys[provider_name]
        genai.configure(api_key=api_key)
        return genai

    def _estimate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost based on token usage"""
        if model not in self.COST_ESTIMATES:
            return 0.0

        costs = self.COST_ESTIMATES[model]
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        return input_cost + output_cost

    def _call_openai(self, provider_name: str, request: LLMRequest) -> LLMResponse:
        """Call OpenAI API"""
        start_time = time.time()

        try:
            client = self._create_openai_client(provider_name)
            provider = self.providers[provider_name]
            model = request.model or provider.default_model_name or "gpt-3.5-turbo"

            # Prepare messages
            messages = request.messages.copy()
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})

            # Make API call
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                response_format=request.response_format,
                stream=request.stream,
            )

            response_time = time.time() - start_time

            # Extract response data
            content = response.choices[0].message.content or ""
            usage = response.usage

            # Calculate cost
            cost = self._estimate_cost(
                model,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            )

            # Log the call
            self._log_call(
                provider_name,
                model,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
                cost,
                response_time,
                True,
            )

            return LLMResponse(
                content=content,
                model=model,
                provider=provider_name,
                usage=asdict(usage) if usage else {},
                response_time=response_time,
                cost_estimate=cost,
                metadata={"finish_reason": response.choices[0].finish_reason},
            )

        except Exception as e:
            response_time = time.time() - start_time
            self._log_call(
                provider_name,
                request.model or "unknown",
                0,
                0,
                0,
                response_time,
                False,
                str(e),
            )
            raise LLMProviderError(f"OpenAI API call failed: {str(e)}", provider_name)

    def _call_anthropic(self, provider_name: str, request: LLMRequest) -> LLMResponse:
        """Call Anthropic API"""
        start_time = time.time()

        try:
            client = self._create_anthropic_client(provider_name)
            provider = self.providers[provider_name]
            model = (
                request.model
                or provider.default_model_name
                or "claude-3-haiku-20240307"
            )

            # Prepare messages for Anthropic format
            messages = []
            system_prompt = request.system_prompt

            for msg in request.messages:
                if msg["role"] == "system" and not system_prompt:
                    system_prompt = msg["content"]
                elif msg["role"] in ["user", "assistant"]:
                    messages.append(msg)

            # Make API call
            response = client.messages.create(
                model=model,
                max_tokens=request.max_tokens or 1000,
                temperature=request.temperature,
                system=system_prompt,
                messages=messages,
            )

            response_time = time.time() - start_time

            # Extract response data
            content = response.content[0].text if response.content else ""

            # Calculate cost (approximate)
            input_tokens = (
                response.usage.input_tokens if hasattr(response, "usage") else 0
            )
            output_tokens = (
                response.usage.output_tokens if hasattr(response, "usage") else 0
            )
            cost = self._estimate_cost(model, input_tokens, output_tokens)

            # Log the call
            self._log_call(
                provider_name,
                model,
                input_tokens,
                output_tokens,
                cost,
                response_time,
                True,
            )

            return LLMResponse(
                content=content,
                model=model,
                provider=provider_name,
                usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
                response_time=response_time,
                cost_estimate=cost,
                metadata={
                    "stop_reason": (
                        response.stop_reason
                        if hasattr(response, "stop_reason")
                        else None
                    )
                },
            )

        except Exception as e:
            response_time = time.time() - start_time
            self._log_call(
                provider_name,
                request.model or "unknown",
                0,
                0,
                0,
                response_time,
                False,
                str(e),
            )
            raise LLMProviderError(
                f"Anthropic API call failed: {str(e)}", provider_name
            )

    def _call_google(self, provider_name: str, request: LLMRequest) -> LLMResponse:
        """Call Google AI API"""
        start_time = time.time()

        try:
            genai_client = self._create_google_client(provider_name)
            provider = self.providers[provider_name]
            model_name = request.model or provider.default_model_name or "gemini-pro"

            model = GenerativeModel(model_name)

            # Prepare prompt
            prompt_parts = []
            if request.system_prompt:
                prompt_parts.append(f"System: {request.system_prompt}")

            for msg in request.messages:
                role = "Human" if msg["role"] == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}")

            prompt = "\n\n".join(prompt_parts)

            # Make API call
            response = model.generate_content(
                prompt,
                generation_config=(
                    {
                        "max_output_tokens": request.max_tokens,
                        "temperature": request.temperature,
                    }
                    if request.max_tokens or request.temperature
                    else None
                ),
            )

            response_time = time.time() - start_time

            # Extract response data
            content = response.text if response.text else ""

            # Estimate tokens and cost (Google doesn't provide detailed usage)
            input_tokens = len(prompt.split()) * 1.3  # Rough estimate
            output_tokens = len(content.split()) * 1.3
            cost = self._estimate_cost(
                model_name, int(input_tokens), int(output_tokens)
            )

            # Log the call
            self._log_call(
                provider_name,
                model_name,
                int(input_tokens),
                int(output_tokens),
                cost,
                response_time,
                True,
            )

            return LLMResponse(
                content=content,
                model=model_name,
                provider=provider_name,
                usage={
                    "input_tokens": int(input_tokens),
                    "output_tokens": int(output_tokens),
                },
                response_time=response_time,
                cost_estimate=cost,
                metadata={"finish_reason": "stop"},
            )

        except Exception as e:
            response_time = time.time() - start_time
            self._log_call(
                provider_name,
                request.model or "unknown",
                0,
                0,
                0,
                response_time,
                False,
                str(e),
            )
            raise LLMProviderError(
                f"Google AI API call failed: {str(e)}", provider_name
            )

    def call_llm(self, provider_name: str, request: LLMRequest) -> LLMResponse:
        """Unified LLM calling interface"""
        if provider_name not in self.providers:
            raise LLMProviderError(f"Provider {provider_name} not found", provider_name)

        if provider_name not in self.api_keys:
            raise LLMProviderError(
                f"API key not available for {provider_name}", provider_name
            )

        provider = self.providers[provider_name]
        provider_type = provider.provider_type.value

        try:
            if provider_type == "openai":
                return self._call_openai(provider_name, request)
            elif provider_type == "anthropic":
                return self._call_anthropic(provider_name, request)
            elif provider_type == "google":
                return self._call_google(provider_name, request)
            else:
                raise LLMProviderError(
                    f"Unsupported provider type: {provider_type}", provider_name
                )

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"Unexpected error: {str(e)}", provider_name)

    def call_with_fallback(
        self, request: LLMRequest, provider_priority: List[str] = None
    ) -> LLMResponse:
        """Call LLM with automatic fallback to other providers"""
        if not provider_priority:
            provider_priority = self.get_available_providers()

        last_error = None

        for provider_name in provider_priority:
            try:
                logger.info(f"Attempting LLM call with provider: {provider_name}")
                return self.call_llm(provider_name, request)
            except LLMProviderError as e:
                logger.warning(f"Provider {provider_name} failed: {e.message}")
                last_error = e
                continue

        if last_error:
            raise last_error
        else:
            raise LLMProviderError("No providers available", "none")

    def _log_call(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        response_time: float,
        success: bool,
        error_message: str = None,
    ):
        """Log LLM call for tracking and analysis"""
        log_entry = LLMCallLog(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            request_tokens=input_tokens,
            response_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_estimate=cost,
            response_time=response_time,
            success=success,
            error_message=error_message,
        )

        self.call_logs.append(log_entry)

        # Keep only last 1000 logs in memory
        if len(self.call_logs) > 1000:
            self.call_logs = self.call_logs[-1000:]

        # Log to file/database if needed
        logger.info(
            f"LLM Call: {provider}/{model} - {input_tokens}+{output_tokens} tokens - ${cost:.4f} - {response_time:.2f}s - {'SUCCESS' if success else 'FAILED'}"
        )

    def get_usage_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get usage statistics for the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_logs = [log for log in self.call_logs if log.timestamp >= cutoff_time]

        if not recent_logs:
            return {
                "period_hours": hours,
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "avg_response_time": 0.0,
                "providers": {},
                "models": {},
            }

        # Calculate statistics
        total_calls = len(recent_logs)
        successful_calls = sum(1 for log in recent_logs if log.success)
        failed_calls = total_calls - successful_calls
        total_cost = sum(log.cost_estimate for log in recent_logs)
        total_tokens = sum(log.total_tokens for log in recent_logs)
        avg_response_time = sum(log.response_time for log in recent_logs) / total_calls

        # Provider statistics
        provider_stats = {}
        for log in recent_logs:
            if log.provider not in provider_stats:
                provider_stats[log.provider] = {
                    "calls": 0,
                    "success": 0,
                    "cost": 0.0,
                    "tokens": 0,
                    "avg_time": 0.0,
                }
            stats = provider_stats[log.provider]
            stats["calls"] += 1
            if log.success:
                stats["success"] += 1
            stats["cost"] += log.cost_estimate
            stats["tokens"] += log.total_tokens
            stats["avg_time"] += log.response_time

        # Calculate averages
        for provider, stats in provider_stats.items():
            if stats["calls"] > 0:
                stats["avg_time"] /= stats["calls"]
                stats["success_rate"] = stats["success"] / stats["calls"]

        # Model statistics
        model_stats = {}
        for log in recent_logs:
            if log.model not in model_stats:
                model_stats[log.model] = {"calls": 0, "cost": 0.0, "tokens": 0}
            model_stats[log.model]["calls"] += 1
            model_stats[log.model]["cost"] += log.cost_estimate
            model_stats[log.model]["tokens"] += log.total_tokens

        return {
            "period_hours": hours,
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "total_cost": round(total_cost, 4),
            "total_tokens": total_tokens,
            "avg_response_time": round(avg_response_time, 2),
            "providers": provider_stats,
            "models": model_stats,
        }

    def health_check_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """Health check for all configured providers"""
        results = {}

        for provider_name in self.get_available_providers():
            try:
                test_request = LLMRequest(
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5,
                    temperature=0,
                )

                start_time = time.time()
                response = self.call_llm(provider_name, test_request)
                response_time = time.time() - start_time

                results[provider_name] = {
                    "status": "healthy",
                    "response_time": round(response_time, 2),
                    "model": response.model,
                    "cost_estimate": response.cost_estimate,
                }

            except Exception as e:
                results[provider_name] = {
                    "status": "error",
                    "error": str(e),
                    "response_time": None,
                    "model": None,
                }

        return results


class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = crud.ai_provider.get_active(self.db)
        self.client = None
        self.llm_manager = LLMProviderManager(db)
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the AI client based on the active provider."""
        if not self.provider:
            raise ValueError("No active AI Provider found in the database.")

        decrypted_api_key = None
        if self.provider.api_key:
            try:
                decrypted_api_key = decrypt_data(self.provider.api_key)
            except Exception as e:
                raise ValueError(f"Failed to decrypt API key: {e}")

        if self.provider.provider_type.value == "openai":
            if not decrypted_api_key:
                raise ValueError("Active OpenAI provider has no API key.")
            self.client = openai.OpenAI(
                api_key=decrypted_api_key,
                base_url=(
                    str(self.provider.api_base_url)
                    if self.provider.api_base_url
                    else None
                ),
            )
        else:
            self.client = None  # Or handle other provider types

    def health_check(self) -> Dict[str, Any]:
        """Check the health of the AI service."""
        if not self.provider:
            return {"status": "error", "message": "No active AI provider"}

        if not self.client:
            return {"status": "error", "message": "AI client not initialized"}

        try:
            # Simple test request
            response = self.client.chat.completions.create(
                model=self.provider.default_model_name or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )

            return {
                "status": "healthy",
                "provider": self.provider.provider_name,
                "model": self.provider.default_model_name,
                "response_time": "< 1s",
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": self.provider.provider_name,
                "message": str(e),
            }

    def refresh_provider(self):
        """Refresh the active provider from database."""
        self.provider = crud.ai_provider.get_active(self.db)
        self._initialize_client()

    def get_available_models(self) -> List[str]:
        """Get available models from the current provider."""
        if not self.client:
            return []

        try:
            if self.provider.provider_type.value == "openai":
                models = self.client.models.list()
                return [model.id for model in models.data]
        except Exception:
            # Return default models if API call fails
            return ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]

        return []

    def interpret_description_for_tool(
        self, task_type: str, description: str, df_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Uses AI to interpret a natural language description and generate structured parameters
        for tool execution.
        """
        if not self.client:
            raise ValueError("AI client not initialized")

        # Create a prompt for the AI to interpret the description
        system_prompt = f"""
        You are an AI assistant that converts natural language descriptions into structured parameters for data analysis tools.
        
        Task type: {task_type}
        Description: {description}
        Available columns: {df_columns if df_columns else "Unknown"}
        
        Based on the description, generate a JSON object with the following structure:
        {{
            "filters": [
                {{"column": "column_name", "operator": "==", "value": "some_value"}}
            ],
            "metrics": ["column1", "column2"],
            "dimensions": ["column3", "column4"],
            "chart_type": "bar|line|pie",
            "aggregation": "sum|count|avg|max|min"
        }}
        
        Only include fields that are relevant to the task. Return only the JSON object.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.provider.default_model_name or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": description},
                ],
                max_tokens=500,
                temperature=0.1,
            )

            content = response.choices[0].message.content.strip()

            # Try to parse the JSON response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, return a basic structure
                return {
                    "filters": [],
                    "metrics": df_columns[:2] if df_columns else [],
                    "dimensions": (
                        df_columns[2:4] if df_columns and len(df_columns) > 2 else []
                    ),
                    "chart_type": "bar",
                    "aggregation": "sum",
                }
        except Exception as e:
            raise ValueError(f"Failed to interpret description: {str(e)}")

    def generate_report_content(
        self, data: Dict[str, Any], template_context: str
    ) -> str:
        """
        Generate report content based on data and template context.
        """
        if not self.client:
            raise ValueError("AI client not initialized")

        system_prompt = """
        You are an AI assistant that generates professional report content based on data analysis results.
        Generate clear, concise, and professional text that explains the data insights.
        Focus on key findings, trends, and actionable insights.
        """

        user_prompt = f"""
        Template context: {template_context}
        Data: {json.dumps(data, indent=2)}
        
        Generate professional report content that explains these findings.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.provider.default_model_name or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1000,
                temperature=0.3,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            raise ValueError(f"Failed to generate report content: {str(e)}")

    def generate_chart_from_description(
        self, data: List[Dict[str, Any]], description: str
    ) -> str:
        """
        Generates a chart by calling an external chart generation service via MCP.
        """
        if not self.client:
            raise ValueError("AI client is not initialized.")

        df = pd.DataFrame(data)
        columns = list(df.columns)

        prompt = f"""
        You are an AI assistant that prepares instructions for a charting service.
        Based on the user's request and the available data columns, create a JSON object 
        that specifies how to build the chart.

        User request: "{description}"
        Available columns: {columns}

        Your JSON output must contain:
        - "chart_type": string, one of ['bar', 'line', 'pie']. Choose the best one.
        - "title": string, a concise and descriptive title for the chart.
        - "x_col": string, the column for the x-axis (for 'bar' and 'line' charts).
        - "y_col": string, the column for the y-axis (for 'bar' and 'line' charts).
        - "labels_col": string, the column for pie chart labels (only for 'pie' charts).
        - "values_col": string, the column for pie chart values (only for 'pie' charts).

        Choose the columns for x, y, labels, and values from the available columns list.
        Ensure your response is ONLY the JSON object.

        Example for "show sales by region":
        {{
            "chart_type": "bar",
            "title": "Sales by Region",
            "x_col": "region",
            "y_col": "sales",
            "labels_col": null,
            "values_col": null
        }}
        """

        response = self.client.chat.completions.create(
            model=self.provider.default_model_name,
            messages=[{"role": "system", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError(
                "AI service returned empty content while generating chart spec."
            )

        try:
            chart_spec = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("Failed to decode AI chart spec response as JSON")

        mcp_payload = {"chart_spec": chart_spec, "data": data}

        # The 'self' service will be configured to point to the backend's own URL.
        response_payload = mcp_client.post("self", "/tools/generate-chart", mcp_payload)

        if response_payload and "image_base64" in response_payload:
            return response_payload["image_base64"]
        else:
            raise ValueError(
                "Failed to generate chart via MCP or the response was invalid."
            )

    def generate_text_summary(self, context_data: Dict[str, Any]) -> str:
        """
        Generates a text summary by calling an external text generation service via MCP.
        """
        mcp_payload = {"context_data": context_data}

        # The 'self' service will be configured to point to the backend's own URL.
        response_payload = mcp_client.post(
            "self", "/tools/generate-text-summary", mcp_payload
        )

        if response_payload and "summary" in response_payload:
            return response_payload["summary"]
        else:
            raise ValueError(
                "Failed to generate text summary via MCP or the response was invalid."
            )

    # Enhanced LLM Integration Methods for Intelligent Placeholder Processing

    def call_llm_unified(
        self, request: LLMRequest, provider_name: str = None
    ) -> LLMResponse:
        """
        Unified LLM calling interface using the LLMProviderManager

        Args:
            request: Standardized LLM request
            provider_name: Specific provider to use, or None for fallback

        Returns:
            Standardized LLM response
        """
        try:
            if provider_name:
                return self.llm_manager.call_llm(provider_name, request)
            else:
                return self.llm_manager.call_with_fallback(request)
        except LLMProviderError as e:
            logger.error(f"LLM call failed: {e}")
            raise ValueError(f"LLM service unavailable: {e.message}")

    def understand_placeholder_semantics(
        self,
        placeholder_type: str,
        description: str,
        context: str,
        available_fields: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Use LLM to understand placeholder semantics and suggest field mappings

        Args:
            placeholder_type: Type of placeholder (周期, 区域, 统计, 图表)
            description: Placeholder description
            context: Surrounding context
            available_fields: Available data fields for matching

        Returns:
            Semantic understanding and field mapping suggestions
        """
        system_prompt = f"""
        你是一个智能占位符理解专家，专门分析中文占位符的语义并提供数据字段匹配建议。

        占位符类型说明：
        - 周期: 时间相关的占位符，如年份、日期、时间段
        - 区域: 地理区域相关，如省份、城市、地区
        - 统计: 统计数据相关，如数量、比例、平均值
        - 图表: 图表可视化相关，如折线图、饼图、柱状图

        请分析占位符并返回JSON格式的理解结果，包含：
        1. semantic_meaning: 语义含义解释
        2. data_type: 数据类型 (string, integer, float, date, percentage)
        3. field_suggestions: 推荐的数据字段匹配
        4. calculation_needed: 是否需要计算
        5. aggregation_type: 聚合类型 (sum, count, avg, max, min)
        6. confidence: 理解置信度 (0-1)
        """

        user_prompt = f"""
        占位符类型: {placeholder_type}
        描述: {description}
        上下文: {context}
        可用字段: {available_fields if available_fields else "未提供"}

        请分析这个占位符的语义含义并提供字段匹配建议。
        """

        request = LLMRequest(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            max_tokens=800,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        try:
            response = self.call_llm_unified(request)
            return json.loads(response.content)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"Failed to parse LLM response for placeholder understanding: {e}"
            )
            return {
                "semantic_meaning": f"无法理解占位符: {description}",
                "data_type": "string",
                "field_suggestions": [],
                "calculation_needed": False,
                "aggregation_type": None,
                "confidence": 0.0,
            }

    def generate_etl_instructions(
        self,
        placeholder_type: str,
        description: str,
        data_source_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate ETL instructions for data extraction based on placeholder requirements

        Args:
            placeholder_type: Type of placeholder
            description: Placeholder description
            data_source_schema: Schema of available data source

        Returns:
            ETL instructions for data extraction
        """
        system_prompt = """
        你是一个ETL指令生成专家，根据占位符需求生成数据提取和转换指令。

        请生成JSON格式的ETL指令，包含：
        1. query_type: 查询类型 (select, aggregate, calculate)
        2. source_tables: 需要的源表
        3. filters: 过滤条件
        4. aggregations: 聚合操作
        5. calculations: 计算公式
        6. output_format: 输出格式
        """

        user_prompt = f"""
        占位符类型: {placeholder_type}
        描述: {description}
        数据源结构: {json.dumps(data_source_schema, ensure_ascii=False, indent=2)}

        请生成相应的ETL指令来获取这个占位符所需的数据。
        """

        request = LLMRequest(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        try:
            response = self.call_llm_unified(request)
            return json.loads(response.content)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to generate ETL instructions: {e}")
            return {
                "query_type": "select",
                "source_tables": [],
                "filters": [],
                "aggregations": [],
                "calculations": [],
                "output_format": "raw",
            }

    def optimize_report_content(self, content: str, context: Dict[str, Any]) -> str:
        """
        Use LLM to optimize and improve report content quality

        Args:
            content: Original report content
            context: Additional context for optimization

        Returns:
            Optimized report content
        """
        system_prompt = """
        你是一个专业的报告内容优化专家，专门优化中文商业报告的质量。

        优化要求：
        1. 保持内容的准确性和完整性
        2. 改善语言流畅性和专业性
        3. 确保逻辑结构清晰
        4. 使用恰当的商业术语
        5. 保持数据的准确引用
        """

        user_prompt = f"""
        原始内容:
        {content}

        上下文信息:
        {json.dumps(context, ensure_ascii=False, indent=2)}

        请优化这段报告内容，使其更加专业、流畅和易读。
        """

        request = LLMRequest(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        try:
            response = self.call_llm_unified(request)
            return response.content
        except Exception as e:
            logger.warning(f"Failed to optimize report content: {e}")
            return content  # Return original content if optimization fails

    def validate_data_consistency(
        self, data: Dict[str, Any], expected_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to validate data consistency and identify potential issues

        Args:
            data: Data to validate
            expected_schema: Expected data schema

        Returns:
            Validation results with issues and suggestions
        """
        system_prompt = """
        你是一个数据质量验证专家，专门检查数据的一致性和合理性。

        请检查数据并返回JSON格式的验证结果，包含：
        1. is_valid: 数据是否有效
        2. issues: 发现的问题列表
        3. suggestions: 修复建议
        4. confidence: 验证置信度
        """

        user_prompt = f"""
        待验证数据:
        {json.dumps(data, ensure_ascii=False, indent=2)}

        期望的数据结构:
        {json.dumps(expected_schema, ensure_ascii=False, indent=2)}

        请验证数据的一致性和合理性。
        """

        request = LLMRequest(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        try:
            response = self.call_llm_unified(request)
            return json.loads(response.content)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to validate data consistency: {e}")
            return {
                "is_valid": True,
                "issues": [],
                "suggestions": [],
                "confidence": 0.5,
            }

    def get_llm_usage_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get LLM usage statistics"""
        return self.llm_manager.get_usage_stats(hours)

    def health_check_all_llm_providers(self) -> Dict[str, Dict[str, Any]]:
        """Health check for all LLM providers"""
        return self.llm_manager.health_check_all_providers()

    def get_available_llm_providers(self) -> List[str]:
        """Get list of available LLM providers"""
        return self.llm_manager.get_available_providers()

    def refresh_llm_providers(self):
        """Refresh LLM provider configurations"""
        self.llm_manager._load_providers()
