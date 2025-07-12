import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import openai
import pandas as pd
from sqlalchemy.orm import Session

from app import crud
from app.core.security_utils import decrypt_data
from app.schemas.ai_provider import AIProvider
from app.services.mcp_client import mcp_client


class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = crud.ai_provider.get_active(self.db)
        self.client = None
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
                max_tokens=5
            )
            
            return {
                "status": "healthy",
                "provider": self.provider.provider_name,
                "model": self.provider.default_model_name,
                "response_time": "< 1s"
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": self.provider.provider_name,
                "message": str(e)
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
                    {"role": "user", "content": description}
                ],
                max_tokens=500,
                temperature=0.1
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
                    "dimensions": df_columns[2:4] if df_columns and len(df_columns) > 2 else [],
                    "chart_type": "bar",
                    "aggregation": "sum"
                }
        except Exception as e:
            raise ValueError(f"Failed to interpret description: {str(e)}")

    def generate_report_content(self, data: Dict[str, Any], template_context: str) -> str:
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
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
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
