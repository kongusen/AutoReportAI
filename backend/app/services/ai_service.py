import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

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
        if not self.provider:
            raise ValueError("No active AI Provider found in the database.")

        decrypted_api_key = None
        if self.provider.api_key:
            try:
                decrypted_api_key = decrypt_data(self.provider.api_key)
            except Exception as e:
                # Handle potential decryption errors, e.g., if the key is invalid
                # or was encrypted with a different encryption key.
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

    def interpret_description_for_tool(
        self,
        task_type: str,
        description: str,
        df_columns: list[str],
    ) -> dict:
        """
        Interprets a natural language description to generate structured parameters for data filtering.
        This remains the first step to get the data.
        """
        if not self.client:
            raise ValueError("AI client is not initialized.")

        system_prompt = f"""
        You are a data analysis assistant. Your task is to interpret a user's natural language
        description and convert it into a structured JSON object of parameters for data processing.
        The user wants to perform a task of type '{task_type}'.
        The available data columns are: {df_columns}.

        You must identify the following from the user's description:
        1.  **date_range**: A list of two strings representing the start and end date. Analyze terms like "last month", "this week", "today" relative to the current date, {datetime.now().strftime('%Y-%m-%d')}. If no date is mentioned, return an empty list.
        2.  **filters**: A dictionary of key-value pairs for filtering the data. The keys must be valid column names from the provided list. If no filters are mentioned, return an empty dictionary.
        3.  **metrics**: A list of column names the user is interested in for analysis (e.g., for plotting on the y-axis or for summarization). This should be a non-empty list.
        4.  **dimensions**: (Optional) A list of column names to use for grouping or as the x-axis in a chart.
        5.  **chart_type**: (Only for 'chart' task type) The suggested type of chart. Can be 'bar', 'line', 'pie', etc. If the task type is not 'chart', omit this field.

        The user's request is: "{description}"

        Your response MUST be a valid JSON object only, with no other text or explanations.
        Example for a chart request "last week's sales for product 'X'":
        {{
            "date_range": ["{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}", "{datetime.now().strftime('%Y-%m-%d')}"],
            "filters": {{"product_name": "X"}},
            "metrics": ["sales"],
            "dimensions": ["date"],
            "chart_type": "line"
        }}
        """

        response = self.client.chat.completions.create(
            model=self.provider.default_model_name,
            messages=[
                {"role": "system", "content": system_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("AI service returned empty content")

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("Failed to decode AI service response as JSON")

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
