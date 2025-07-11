import pandas as pd
from typing import Dict, Callable

class ComputationService:
    def __init__(self):
        self._functions: Dict[str, Callable] = {}
        self._register_default_functions()

    def register(self, name: str, func: Callable):
        self._functions[name] = func

    def execute(self, name: str, context_dfs: Dict[str, pd.DataFrame]) -> any:
        if name not in self._functions:
            raise ValueError(f"Computation function '{name}' not registered.")
        return self._functions[name](context_dfs)

    def _register_default_functions(self):
        self.register("sum_column", self._sum_column)
        self.register("add_price_per_unit", self._add_price_per_unit)

    # --- Example Computation Functions using Pandas ---

    def _sum_column(self, context: Dict[str, pd.DataFrame]) -> float:
        """
        Calculates the sum of the 'sales' column from the 'sales_by_region' DataFrame.
        """
        df = context.get("sales_by_region")
        if df is None or 'sales' not in df.columns:
            return 0
        return df['sales'].sum()

    def _add_price_per_unit(self, context: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Adds a calculated column 'price_per_unit' to the 'sales_by_region' DataFrame.
        Returns the modified DataFrame.
        """
        df = context.get("sales_by_region")
        if df is None or not all(col in df.columns for col in ['sales', 'units_sold']):
            return pd.DataFrame() # Return empty if required columns are missing
        
        # Avoid division by zero
        df['price_per_unit'] = df.apply(
            lambda row: row['sales'] / row['units_sold'] if row['units_sold'] != 0 else 0,
            axis=1
        )
        return df

computation_service = ComputationService() 