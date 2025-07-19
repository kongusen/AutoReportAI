"""
Pytest configuration for service module unit tests

This file provides common fixtures and configuration for testing
the new service modules.
"""

import pytest
from unittest.mock import Mock, MagicMock
import pandas as pd
from datetime import datetime
import tempfile
import os

# Test data fixtures
@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing"""
    return pd.DataFrame({
        'region': ['云南省', '北京市', '上海市', '广东省', '浙江省'],
        'sales': [1000000, 2000000, 1800000, 2500000, 1500000],
        'complaints': [45, 23, 67, 89, 34],
        'completion_rate': [0.85, 0.92, 0.78, 0.88, 0.91],
        'date': pd.date_range('2024-01-01', periods=5, freq='M')
    })

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.all.return_value = []
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    mock_session.close.return_value = None
    return mock_session

@pytest.fixture
def mock_data_source():
    """Mock data source object"""
    mock_source = Mock()
    mock_source.id = 1
    mock_source.name = "Test Data Source"
    mock_source.source_type = "csv"
    mock_source.file_path = "/path/to/test.csv"
    mock_source.connection_string = None
    mock_source.api_url = None
    mock_source.api_method = "GET"
    mock_source.api_headers = {}
    mock_source.api_body = None
    mock_source.db_query = "SELECT * FROM test_table"
    return mock_source

@pytest.fixture
def mock_template():
    """Mock template object"""
    mock_template = Mock()
    mock_template.id = 1
    mock_template.name = "Test Template"
    mock_template.file_path = "/path/to/template.docx"
    mock_template.content = "Template with {{统计:总数}} placeholder"
    return mock_template

@pytest.fixture
def mock_task():
    """Mock task object"""
    mock_task = Mock()
    mock_task.id = 1
    mock_task.name = "Test Task"
    mock_task.description = "Test task description"
    mock_task.status = "pending"
    mock_task.created_at = datetime.now()
    return mock_task

@pytest.fixture
def sample_placeholder_text():
    """Sample text with placeholders for testing"""
    return """
    本月{{周期:2024年3月}}，{{区域:云南省}}共处理投诉{{统计:总投诉件数}}件，
    其中已完成{{统计:已完成件数}}件，完成率达到{{统计:完成率}}%。
    
    各地区投诉分布如下图所示：
    {{图表:地区投诉分布图}}
    
    与上月相比，投诉总数{{统计:环比变化}}。
    """

@pytest.fixture
def sample_chart_data():
    """Sample chart data for testing"""
    return [
        {"category": "昆明市", "value": 156, "percentage": 35.2},
        {"category": "大理州", "value": 89, "percentage": 20.1},
        {"category": "丽江市", "value": 67, "percentage": 15.1},
        {"category": "西双版纳", "value": 45, "percentage": 10.2},
        {"category": "其他地区", "value": 86, "percentage": 19.4}
    ]

@pytest.fixture
def temp_file():
    """Temporary file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test file content")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass

@pytest.fixture
def temp_csv_file(sample_dataframe):
    """Temporary CSV file with sample data"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        sample_dataframe.to_csv(f.name, index=False)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass

@pytest.fixture
def mock_ai_provider():
    """Mock AI provider object"""
    mock_provider = Mock()
    mock_provider.id = 1
    mock_provider.provider_name = "openai"
    mock_provider.provider_type.value = "openai"
    mock_provider.api_key = "encrypted_test_key"
    mock_provider.api_base_url = None
    mock_provider.default_model_name = "gpt-3.5-turbo"
    mock_provider.is_active = True
    mock_provider.max_tokens = 4000
    mock_provider.temperature = 0.7
    return mock_provider

@pytest.fixture
def mock_llm_response():
    """Mock LLM response"""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test AI response"
    mock_response.choices[0].finish_reason = "stop"
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 25
    mock_response.usage.total_tokens = 75
    return mock_response

@pytest.fixture
def sample_report_content():
    """Sample report content for quality testing"""
    return """
    云南省旅游投诉处理月度报告
    
    一、基本情况
    本月共接收旅游投诉443件，较上月增长12.5%。其中，购物投诉156件，
    占比35.2%；住宿投诉89件，占比20.1%；交通投诉67件，占比15.1%。
    
    二、处理情况
    已处理投诉376件，处理率达84.9%。平均处理时长3.2天，
    较上月缩短0.5天。游客满意度评价为4.2分（满分5分）。
    
    三、主要问题
    1. 购物环节投诉仍然较多，主要集中在价格虚高、强制消费等问题
    2. 部分景区服务质量有待提升
    3. 交通服务投诉呈上升趋势
    
    四、改进措施
    1. 加强购物场所监管，建立价格公示制度
    2. 提升景区服务标准，完善投诉处理机制
    3. 优化交通服务质量，加强司机培训
    """

# Mock service fixtures
@pytest.fixture
def mock_template_parser():
    """Mock template parser service"""
    mock_parser = Mock()
    mock_parser.parse.return_value = {
        "placeholders": [
            {"name": "total_count", "type": "scalar", "description": "总数"},
            {"name": "region_chart", "type": "chart", "description": "地区分布图"}
        ],
        "structure": {
            "sections": ["header", "body", "footer"],
            "tables": 2,
            "images": 1
        }
    }
    return mock_parser

@pytest.fixture
def mock_tool_dispatcher():
    """Mock tool dispatcher service"""
    mock_dispatcher = Mock()
    mock_dispatcher.dispatch.return_value = "Mock result"
    return mock_dispatcher

@pytest.fixture
def mock_word_generator():
    """Mock Word document generator"""
    mock_generator = Mock()
    mock_generator.generate_report_from_content.return_value = "/path/to/output.docx"
    return mock_generator

@pytest.fixture
def mock_statistics_service():
    """Mock statistics service"""
    mock_service = Mock()
    mock_service.get_basic_stats.return_value = {
        "count": 1000,
        "mean": 156.7,
        "std": 45.2,
        "min": 23,
        "max": 445,
        "median": 134.5
    }
    return mock_service

@pytest.fixture
def mock_visualization_service():
    """Mock visualization service"""
    mock_service = Mock()
    mock_service.generate_bar_chart.return_value = {
        "type": "bar",
        "title": "Test Chart",
        "data": [{"x": "A", "y": 100}, {"x": "B", "y": 200}],
        "config": {"width": 800, "height": 600}
    }
    return mock_service

# Test environment setup
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables and configurations"""
    # Set test environment variables
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    
    # Mock external dependencies that might not be available in test environment
    import sys
    from unittest.mock import MagicMock
    
    # Mock optional dependencies
    mock_modules = [
        'sentence_transformers',
        'fuzzywuzzy', 
        'redis',
        'matplotlib',
        'seaborn',
        'anthropic',
        'google.generativeai'
    ]
    
    for module_name in mock_modules:
        if module_name not in sys.modules:
            sys.modules[module_name] = MagicMock()

# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()

# Async testing fixtures
@pytest.fixture
def event_loop():
    """Event loop for async testing"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Error simulation fixtures
@pytest.fixture
def mock_error_scenarios():
    """Mock various error scenarios for testing"""
    return {
        "database_error": Exception("Database connection failed"),
        "file_not_found": FileNotFoundError("File not found"),
        "api_error": Exception("API request failed"),
        "timeout_error": TimeoutError("Operation timed out"),
        "permission_error": PermissionError("Permission denied"),
        "value_error": ValueError("Invalid value provided"),
        "json_decode_error": ValueError("Invalid JSON format")
    }