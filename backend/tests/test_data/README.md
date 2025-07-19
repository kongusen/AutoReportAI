# Test Data Organization

This directory contains all test data organized by category for easy maintenance and reuse across different test types.

## Directory Structure

```
test_data/
├── __init__.py              # Package initialization with utility functions
├── README.md               # This file
├── fixtures/               # Python fixtures and data factories
│   ├── base_fixtures.py    # Common test data factories
│   └── template_fixtures.py # Template-specific test data
├── csv_data/               # CSV test data files
│   ├── sample_data.csv     # Basic sample data for general testing
│   ├── complaint_raw_data.csv # Complaint data for integration tests
│   └── complaint_wide_table.csv # Aggregated complaint data
├── json_data/              # JSON configuration and test data
│   ├── complaint_api_test_data.json # API test configuration
│   ├── complaint_data_source_config.json # Data source configuration
│   └── complaint_aggregated_data.json # Aggregated test data
├── sample_files/           # Template and other sample files
│   └── basic_template.txt  # Basic template for testing
└── mock_data/              # Mock data for external services
    └── __init__.py
```

## Usage

### Using Fixtures

```python
from tests.test_data.fixtures.base_fixtures import TestDataFactory

# Create test data
user = TestDataFactory.create_user("testuser", "test@example.com")
data_source = TestDataFactory.create_data_source("Test Source", "csv")
```

### Using File Paths

```python
from tests.test_data import get_test_file_path, get_relative_test_path

# Get absolute path
csv_path = get_test_file_path("sample_data.csv")

# Get relative path (for database storage)
relative_path = get_relative_test_path("sample_data.csv")
```

### Using Template Data

```python
from tests.test_data.fixtures.template_fixtures import get_simple_template

template_data = get_simple_template()
```

## Guidelines

1. **Centralized Data**: All test data should be stored in this directory structure
2. **Reusable Fixtures**: Use the fixture factories instead of hardcoding test data
3. **Proper Paths**: Always use the utility functions to get file paths
4. **Clean Data**: Keep test data minimal and focused on the specific test scenario
5. **Documentation**: Document any complex test data scenarios

## File Naming Conventions

- CSV files: `{purpose}_data.csv` (e.g., `sample_data.csv`, `user_data.csv`)
- JSON files: `{purpose}_{type}.json` (e.g., `api_config.json`, `test_data.json`)
- Template files: `{purpose}_template.{ext}` (e.g., `basic_template.txt`)
- Fixture files: `{category}_fixtures.py` (e.g., `user_fixtures.py`)

## Adding New Test Data

1. Choose the appropriate category directory
2. Follow the naming conventions
3. Update the `__init__.py` file if adding new common paths
4. Create corresponding fixtures if the data will be reused
5. Update this README if adding new categories