"""
Test data package initialization.

This package contains all test data organized by category:
- fixtures/: Python fixtures and data factories
- csv_data/: CSV test data files
- json_data/: JSON configuration and test data
- sample_files/: Template and other sample files
- mock_data/: Mock data for external services
"""

import os
from pathlib import Path

# Base paths for test data
TEST_DATA_DIR = Path(__file__).parent
CSV_DATA_DIR = TEST_DATA_DIR / "csv_data"
JSON_DATA_DIR = TEST_DATA_DIR / "json_data"
SAMPLE_FILES_DIR = TEST_DATA_DIR / "sample_files"
FIXTURES_DIR = TEST_DATA_DIR / "fixtures"
MOCK_DATA_DIR = TEST_DATA_DIR / "mock_data"

# Common file paths
SAMPLE_CSV = CSV_DATA_DIR / "sample_data.csv"
COMPLAINT_RAW_DATA = CSV_DATA_DIR / "complaint_raw_data.csv"
COMPLAINT_WIDE_TABLE = CSV_DATA_DIR / "complaint_wide_table.csv"
BASIC_TEMPLATE = SAMPLE_FILES_DIR / "basic_template.txt"


# Utility functions
def get_test_file_path(filename: str, category: str = "csv_data") -> str:
    """Get the full path to a test file."""
    category_dir = TEST_DATA_DIR / category
    return str(category_dir / filename)


def get_relative_test_path(filename: str, category: str = "csv_data") -> str:
    """Get the relative path from backend root to a test file."""
    return f"tests/test_data/{category}/{filename}"
