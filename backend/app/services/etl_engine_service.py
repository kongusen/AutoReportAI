from typing import Any, Dict, List

import pandas as pd


class ETLTransformationEngine:
    """
    Safely executes a series of ETL transformation steps defined in a structured configuration.
    """

    def __init__(self, transformation_config: Dict[str, Any], df: pd.DataFrame):
        self.operations = transformation_config.get("operations", [])
        self.df = df.copy()  # Work on a copy to avoid side effects

        self.allowed_operations = {
            "filter_rows": self._filter_rows,
            "select_columns": self._select_columns,
            "rename_columns": self._rename_columns,
            "change_column_type": self._change_column_type,
        }

    def _filter_rows(self, params: Dict[str, Any]):
        column = params.get("column")
        operator = params.get("operator")
        value = params.get("value")

        if not all([column, operator, value is not None]):
            raise ValueError("filter_rows requires 'column', 'operator', and 'value'.")

        if column not in self.df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame.")

        supported_operators = {
            "==": self.df[column] == value,
            "!=": self.df[column] != value,
            ">": self.df[column] > value,
            "<": self.df[column] < value,
            ">=": self.df[column] >= value,
            "<=": self.df[column] <= value,
            "in": self.df[column].isin(value),
            "not in": ~self.df[column].isin(value),
            "contains": self.df[column].str.contains(str(value), na=False),
        }

        if operator not in supported_operators:
            raise ValueError(f"Unsupported operator '{operator}'.")

        self.df = self.df[supported_operators[operator]]

    def _select_columns(self, params: Dict[str, Any]):
        columns = params.get("columns")
        if not columns or not isinstance(columns, list):
            raise ValueError("select_columns requires a 'columns' list.")

        missing_cols = [col for col in columns if col not in self.df.columns]
        if missing_cols:
            raise ValueError(f"Columns not found: {', '.join(missing_cols)}")

        self.df = self.df[columns]

    def _rename_columns(self, params: Dict[str, Any]):
        rename_map = params.get("rename_map")
        if not rename_map or not isinstance(rename_map, dict):
            raise ValueError("rename_columns requires a 'rename_map' dictionary.")

        missing_cols = [col for col in rename_map.keys() if col not in self.df.columns]
        if missing_cols:
            raise ValueError(f"Columns to rename not found: {', '.join(missing_cols)}")

        self.df.rename(columns=rename_map, inplace=True)

    def _change_column_type(self, params: Dict[str, Any]):
        column = params.get("column")
        new_type = params.get("new_type")

        if not all([column, new_type]):
            raise ValueError("change_column_type requires 'column' and 'new_type'.")

        if column not in self.df.columns:
            raise ValueError(f"Column '{column}' not found.")

        try:
            self.df[column] = self.df[column].astype(new_type)
        except Exception as e:
            raise ValueError(
                f"Failed to change type of '{column}' to '{new_type}': {e}"
            )

    def run(self) -> pd.DataFrame:
        """
        Executes the entire pipeline of transformations.
        """
        for op in self.operations:
            op_name = op.get("operation")
            op_params = op.get("params", {})

            if op_name not in self.allowed_operations:
                raise ValueError(f"Unknown or disallowed operation: '{op_name}'")

            transform_func = self.allowed_operations[op_name]
            transform_func(op_params)

        return self.df
