from typing import List

import pandas as pd


class StatisticsService:
    """
    A service for performing statistical calculations on datasets.
    """

    def calculate_sum(self, data: List[dict], column_name: str) -> float:
        """
        Calculates the sum of a specific column in a list of dictionaries.

        :param data: A list of dictionaries (e.g., from a database query).
        :param column_name: The name of the column to sum.
        :return: The sum of the column values.
        """
        if not data:
            return 0.0
        df = pd.DataFrame(data)
        if column_name not in df.columns:
            raise ValueError(f"Column '{column_name}' not found in data.")
        return df[column_name].sum()

    def calculate_average(self, data: List[dict], column_name: str) -> float:
        """
        Calculates the average of a specific column in a list of dictionaries.

        :param data: A list of dictionaries.
        :param column_name: The name of the column to average.
        :return: The average of the column values.
        """
        if not data:
            return 0.0
        df = pd.DataFrame(data)
        if column_name not in df.columns:
            raise ValueError(f"Column '{column_name}' not found in data.")
        return df[column_name].mean()

    def calculate_percentage_change(
        self, current_value: float, previous_value: float
    ) -> float:
        """
        Calculates the percentage change between two values.

        :param current_value: The current or new value.
        :param previous_value: The previous or base value.
        :return: The percentage change. Returns 0.0 if previous_value is 0.
        """
        if previous_value == 0:
            return 0.0  # Avoid division by zero
        return ((current_value - previous_value) / previous_value) * 100
    
    def get_basic_stats(self, df: pd.DataFrame) -> dict:
        """
        获取DataFrame的基础统计信息
        
        :param df: pandas DataFrame
        :return: 基础统计信息字典
        """
        if df.empty:
            return {"error": "DataFrame is empty"}
        
        numeric_columns = df.select_dtypes(include=[pd.np.number]).columns.tolist()
        
        stats = {
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "data_types": df.dtypes.astype(str).to_dict(),
            "memory_usage": df.memory_usage(deep=True).sum(),
            "numeric_summary": {}
        }
        
        # 数值列的描述性统计
        if numeric_columns:
            describe_stats = df[numeric_columns].describe()
            stats["numeric_summary"] = describe_stats.to_dict()
        
        return stats


# You can add more statistical functions here as needed, for example:
# - calculate_median
# - calculate_mode
# - calculate_std_dev
# - perform_trend_analysis
# - etc.
