import re

import pandas as pd

# A simple regex to strip out characters that are often used in injection attacks.
# This is not foolproof and should be adapted based on expected data formats.
# For truly robust HTML/JS sanitization, a library like 'bleach' is recommended.
POTENTIALLY_MALICIOUS_CHARS = re.compile(r'[<>"\'\(\);&]')


class DataSanitizationService:
    def __init__(self, max_rows: int = 100000, max_cols: int = 100):
        self.max_rows = max_rows
        self.max_cols = max_cols

    def sanitize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Performs basic sanitization on a pandas DataFrame.
        - Limits the number of rows and columns to prevent resource exhaustion.
        - Strips potentially malicious characters from string columns.
        """
        if df.shape[0] > self.max_rows:
            df = df.head(self.max_rows)

        if df.shape[1] > self.max_cols:
            df = df.iloc[:, : self.max_cols]

        # Sanitize object columns (typically strings)
        for col in df.select_dtypes(include=["object"]).columns:
            # Ensure data is string type before applying string operations
            df[col] = (
                df[col]
                .astype(str)
                .apply(lambda x: POTENTIALLY_MALICIOUS_CHARS.sub("", x))
            )

        return df


# Create a default instance for easy import
data_sanitizer = DataSanitizationService()
