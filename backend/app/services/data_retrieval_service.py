from typing import Any, Dict

import httpx
import pandas as pd

from app import models


class DataRetrievalService:
    async def fetch_data(self, source: models.DataSource) -> pd.DataFrame:
        """
        Fetches data from the given data source and returns it as a pandas DataFrame.
        """
        if source.source_type == "sql":
            return self._fetch_from_sql(source)
        elif source.source_type == "csv":
            return self._fetch_from_csv(source)
        elif source.source_type == "api":
            return await self._fetch_from_api(source)
        else:
            raise ValueError(f"Unsupported data source type: {source.source_type}")

    def _fetch_from_sql(self, source: models.DataSource) -> pd.DataFrame:
        """Mock function to simulate fetching data from SQL."""
        print(f"Executing SQL: {source.db_query}")
        if "region" in source.db_query.lower():
            data = [
                {"region": "昆明", "sales": 520000, "units_sold": 120},
                {"region": "大理", "sales": 410000, "units_sold": 95},
                {"region": "丽江", "sales": 630000, "units_sold": 150},
                {"region": "西双版纳", "sales": 350000, "units_sold": 80},
                {"region": "香格里拉", "sales": 280000, "units_sold": 65},
            ]
            return pd.DataFrame(data)
        elif "total_sales" in source.db_query.lower():
            return pd.DataFrame([{"total": 2190000}])
        return pd.DataFrame()

    def _fetch_from_csv(self, source: models.DataSource) -> pd.DataFrame:
        """Fetches data from a CSV file."""
        try:
            # In a real scenario, ensure the file_path is secure and not traversing directories
            return pd.read_csv(source.file_path)
        except FileNotFoundError:
            print(f"CSV file not found at path: {source.file_path}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return pd.DataFrame()

    async def _fetch_from_api(self, source: models.DataSource) -> pd.DataFrame:
        """Fetches data from an external API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=source.api_method,
                    url=source.api_url,
                    headers=source.api_headers,
                    json=source.api_body,
                    timeout=20.0,
                )
                response.raise_for_status()
                # Assuming the API returns a list of JSON objects
                return pd.DataFrame(response.json())
        except httpx.RequestError as e:
            print(f"API request failed: {e}")
            return pd.DataFrame()


data_retrieval_service = DataRetrievalService()
