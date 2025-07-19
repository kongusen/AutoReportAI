import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import openai
import pandas as pd
from cachetools import TTLCache
from sqlalchemy.orm import Session

from app import crud
from app.core.security_utils import decrypt_data
from app.schemas.ai_provider import AIProvider
from ..mcp_client import mcp_client

logger = logging.getLogger(__name__)


class AIModelType(str, Enum):
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE = "image"


@dataclass
class AIRequest:
    """AI请求数据结构"""

    model: str
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None


@dataclass
class AIResponse:
    """AI响应数据结构"""

    content: str
    model: str
    usage: Dict[str, int]
    response_time: float
    timestamp: datetime


class AIServiceMetrics:
    """AI服务指标收集器"""

    def __init__(self):
        self.request_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.response_times = []
        self.error_count = 0
        self.model_usage = {}

    def record_request(
        self,
        model: str,
        tokens: int,
        cost: float,
        response_time: float,
        success: bool = True,
    ):
        """记录请求指标"""
        self.request_count += 1

        if success:
            self.total_tokens += tokens
            self.total_cost += cost
            self.response_times.append(response_time)

            if model not in self.model_usage:
                self.model_usage[model] = {"requests": 0, "tokens": 0, "cost": 0.0}

            self.model_usage[model]["requests"] += 1
            self.model_usage[model]["tokens"] += tokens
            self.model_usage[model]["cost"] += cost
        else:
            self.error_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标摘要"""
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times
            else 0
        )

        return {
            "total_requests": self.request_count,
            "successful_requests": self.request_count - self.error_count,
            "error_count": self.error_count,
            "error_rate": (
                self.error_count / self.request_count if self.request_count > 0 else 0
            ),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "average_response_time": avg_response_time,
            "model_usage": self.model_usage,
        }


class EnhancedAIService:
    """增强版AI服务"""

    def __init__(self, db: Session):
        self.db = db
        self.provider = crud.ai_provider.get_active(self.db)
        self.client = None
        self.metrics = AIServiceMetrics()

        # 响应缓存 (TTL: 1小时)
        self.response_cache = TTLCache(maxsize=1000, ttl=3600)

        # 模型价格表 (每1K tokens的价格，美元)
        self.model_pricing = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4o": {"input": 0.005, "output": 0.015},
        }

        self._initialize_client()

    def _initialize_client(self):
        """初始化AI客户端"""
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

            self.client = openai.AsyncOpenAI(
                api_key=decrypted_api_key,
                base_url=(
                    str(self.provider.api_base_url)
                    if self.provider.api_base_url
                    else None
                ),
            )
        else:
            self.client = None

    def _generate_cache_key(self, request: AIRequest) -> str:
        """生成缓存键"""
        request_str = json.dumps(
            {
                "model": request.model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            },
            sort_keys=True,
        )

        return hashlib.md5(request_str.encode()).hexdigest()

    def _calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """计算请求成本"""
        if model not in self.model_pricing:
            return 0.0

        pricing = self.model_pricing[model]
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    async def chat_completion(
        self, request: AIRequest, use_cache: bool = True
    ) -> AIResponse:
        """聊天完成请求"""
        if not self.client:
            raise ValueError("AI client not initialized")

        # 检查缓存
        cache_key = self._generate_cache_key(request)
        if use_cache and cache_key in self.response_cache:
            logger.info(f"Cache hit for request: {cache_key[:8]}...")
            return self.response_cache[cache_key]

        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=request.messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
            )

            response_time = time.time() - start_time

            # 提取响应内容
            content = response.choices[0].message.content or ""
            usage = response.usage.model_dump() if response.usage else {}

            # 计算成本
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = self._calculate_cost(request.model, input_tokens, output_tokens)

            # 创建响应对象
            ai_response = AIResponse(
                content=content,
                model=request.model,
                usage=usage,
                response_time=response_time,
                timestamp=datetime.now(),
            )

            # 记录指标
            total_tokens = input_tokens + output_tokens
            self.metrics.record_request(
                request.model, total_tokens, cost, response_time, True
            )

            # 缓存响应
            if use_cache:
                self.response_cache[cache_key] = ai_response

            logger.info(
                f"AI request completed: {request.model}, tokens: {total_tokens}, cost: ${cost:.4f}"
            )

            return ai_response

        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.record_request(request.model, 0, 0, response_time, False)

            logger.error(f"AI request failed: {e}")
            raise ValueError(f"AI request failed: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self.provider:
            return {"status": "error", "message": "No active AI provider"}

        if not self.client:
            return {"status": "error", "message": "AI client not initialized"}

        try:
            # 简单测试请求
            request = AIRequest(
                model=self.provider.default_model_name or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )

            response = await self.chat_completion(request, use_cache=False)

            return {
                "status": "healthy",
                "provider": self.provider.provider_name,
                "model": self.provider.default_model_name,
                "response_time": f"{response.response_time:.2f}s",
                "metrics": self.metrics.get_metrics(),
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": self.provider.provider_name,
                "message": str(e),
            }

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        if not self.client:
            return []

        try:
            if self.provider.provider_type.value == "openai":
                models = await self.client.models.list()

                model_list = []
                for model in models.data:
                    model_info = {
                        "id": model.id,
                        "created": model.created,
                        "owned_by": model.owned_by,
                        "pricing": self.model_pricing.get(
                            model.id, {"input": 0, "output": 0}
                        ),
                    }
                    model_list.append(model_info)

                return model_list
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            # 返回默认模型列表
            return [
                {
                    "id": "gpt-3.5-turbo",
                    "owned_by": "openai",
                    "pricing": self.model_pricing.get(
                        "gpt-3.5-turbo", {"input": 0, "output": 0}
                    ),
                },
                {
                    "id": "gpt-4",
                    "owned_by": "openai",
                    "pricing": self.model_pricing.get(
                        "gpt-4", {"input": 0, "output": 0}
                    ),
                },
            ]

        return []

    async def interpret_natural_language_query(
        self,
        query: str,
        context: Dict[str, Any],
        available_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """解释自然语言查询"""

        system_prompt = f"""
        You are an AI assistant that converts natural language queries into structured data analysis parameters.
        
        Context: {json.dumps(context, indent=2)}
        Available columns: {available_columns or "Unknown"}
        
        Convert the user's query into a JSON object with the following structure:
        {{
            "intent": "analysis_type (e.g., 'trend', 'comparison', 'summary', 'correlation')",
            "filters": [
                {{"column": "column_name", "operator": "==|!=|>|<|>=|<=|contains", "value": "filter_value"}}
            ],
            "metrics": ["column1", "column2"],
            "dimensions": ["column3", "column4"],
            "time_column": "date_column_name",
            "aggregation": "sum|count|avg|max|min|median",
            "chart_type": "bar|line|pie|scatter|heatmap",
            "sort_by": "column_name",
            "sort_order": "asc|desc",
            "limit": 100
        }}
        
        Only include fields that are relevant to the query. Return only the JSON object.
        """

        request = AIRequest(
            model=self.provider.default_model_name or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            max_tokens=800,
            temperature=0.1,
        )

        try:
            response = await self.chat_completion(request)

            # 尝试解析JSON响应
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回基本结构
                return {
                    "intent": "summary",
                    "filters": [],
                    "metrics": available_columns[:2] if available_columns else [],
                    "dimensions": (
                        available_columns[2:4]
                        if available_columns and len(available_columns) > 2
                        else []
                    ),
                    "chart_type": "bar",
                    "aggregation": "sum",
                }
        except Exception as e:
            raise ValueError(f"Failed to interpret query: {str(e)}")

    async def generate_insights(
        self, data_summary: Dict[str, Any], context: str = ""
    ) -> str:
        """生成数据洞察"""

        system_prompt = """
        You are a data analyst AI that generates professional insights from data analysis results.
        Provide clear, actionable insights that highlight key findings, trends, and recommendations.
        Focus on business value and practical implications.
        """

        user_prompt = f"""
        Context: {context}
        
        Data Summary:
        {json.dumps(data_summary, indent=2)}
        
        Generate professional insights that explain:
        1. Key findings and trends
        2. Notable patterns or anomalies
        3. Business implications
        4. Actionable recommendations
        
        Keep the response concise but comprehensive.
        """

        request = AIRequest(
            model=self.provider.default_model_name or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1000,
            temperature=0.3,
        )

        try:
            response = await self.chat_completion(request)
            return response.content
        except Exception as e:
            raise ValueError(f"Failed to generate insights: {str(e)}")

    async def generate_chart_config(
        self,
        data: List[Dict[str, Any]],
        description: str,
        chart_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成图表配置"""

        df = pd.DataFrame(data)
        columns = list(df.columns)

        system_prompt = f"""
        You are an AI assistant that creates chart configurations based on data and user requirements.
        
        Available columns: {columns}
        Data sample: {data[:3] if data else []}
        
        Generate a JSON configuration for creating a chart with the following structure:
        {{
            "chart_type": "bar|line|pie|scatter|area",
            "title": "Chart title",
            "x_axis": {{"column": "column_name", "label": "X-axis label"}},
            "y_axis": {{"column": "column_name", "label": "Y-axis label"}},
            "color_by": "column_name (optional)",
            "aggregation": "sum|count|avg|max|min (if needed)",
            "sort_by": "column_name (optional)",
            "sort_order": "asc|desc",
            "limit": 20
        }}
        
        Choose appropriate columns and chart type based on the data and description.
        Return only the JSON object.
        """

        user_prompt = f"Create a chart configuration for: {description}"
        if chart_type:
            user_prompt += f" Use chart type: {chart_type}"

        request = AIRequest(
            model=self.provider.default_model_name or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
            temperature=0.1,
        )

        try:
            response = await self.chat_completion(request)
            return json.loads(response.content)
        except (json.JSONDecodeError, Exception) as e:
            # 返回默认配置
            return {
                "chart_type": chart_type or "bar",
                "title": "Data Visualization",
                "x_axis": {"column": columns[0] if columns else "x", "label": "X-axis"},
                "y_axis": {
                    "column": columns[1] if len(columns) > 1 else "y",
                    "label": "Y-axis",
                },
                "limit": 20,
            }

    async def batch_process(self, requests: List[AIRequest]) -> List[AIResponse]:
        """批量处理AI请求"""
        tasks = [self.chat_completion(request) for request in requests]

        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            results = []
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    logger.error(f"Batch request {i} failed: {response}")
                    # 创建错误响应
                    error_response = AIResponse(
                        content=f"Error: {str(response)}",
                        model=requests[i].model,
                        usage={},
                        response_time=0,
                        timestamp=datetime.now(),
                    )
                    results.append(error_response)
                else:
                    results.append(response)

            return results

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            raise ValueError(f"Batch processing failed: {str(e)}")

    def get_service_metrics(self) -> Dict[str, Any]:
        """获取服务指标"""
        return self.metrics.get_metrics()

    def clear_cache(self):
        """清空缓存"""
        self.response_cache.clear()
        logger.info("AI service cache cleared")

    def refresh_provider(self):
        """刷新AI提供商配置"""
        self.provider = crud.ai_provider.get_active(self.db)
        self._initialize_client()
        logger.info("AI provider configuration refreshed")
