"""
占位符测试配置文件
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.services.domain.placeholder.models import (
    DocumentContext,
    BusinessContext,
    TimeContext,
    PlaceholderSpec,
    StatisticalType,
    SyntaxType
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = Mock()
    session.query.return_value = Mock()
    session.add.return_value = None
    session.commit.return_value = None
    session.rollback.return_value = None
    return session


@pytest.fixture
def sample_document_context():
    """样本文档上下文"""
    return DocumentContext(
        document_id="test_doc_001",
        title="测试文档",
        content="这是一个测试文档内容，包含占位符 {{test_placeholder}}",
        metadata={
            "department": "测试部",
            "type": "测试报告",
            "created_by": "test_user",
            "created_at": "2023-12-01"
        }
    )


@pytest.fixture
def sample_business_context():
    """样本业务上下文"""
    return BusinessContext(
        domain="测试分析",
        rules=[
            "数据必须准确",
            "计算必须可验证",
            "格式必须统一"
        ],
        constraints={
            "currency": "CNY",
            "unit": "万元",
            "precision": 2,
            "data_source": "测试数据库"
        }
    )


@pytest.fixture
def sample_time_context():
    """样本时间上下文"""
    return TimeContext(
        reference_time=datetime(2023, 12, 31),
        time_range="monthly",
        fiscal_year=2023,
        period="Q4"
    )


@pytest.fixture
def sample_placeholder_specs():
    """样本占位符规格"""
    return [
        PlaceholderSpec(
            content="total_sales",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=0,
            end_position=11
        ),
        PlaceholderSpec(
            content="growth_rate",
            statistical_type=StatisticalType.TREND,
            syntax_type=SyntaxType.BASIC,
            start_position=20,
            end_position=31
        ),
        PlaceholderSpec(
            content="region_sales(region='北京')",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.PARAMETERIZED,
            start_position=40,
            end_position=67,
            parameters={"region": "北京"}
        ),
        PlaceholderSpec(
            content="sum(q1_sales, q2_sales, q3_sales)",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.COMPOSITE,
            start_position=80,
            end_position=113
        ),
        PlaceholderSpec(
            content="if sales > target then '达标' else '未达标'",
            statistical_type=StatisticalType.COMPARISON,
            syntax_type=SyntaxType.CONDITIONAL,
            start_position=120,
            end_position=160
        )
    ]


@pytest.fixture
def mock_agents_integration():
    """模拟智能代理集成服务"""
    mock_service = AsyncMock()
    
    # 默认的分析结果
    mock_service.analyze_placeholders.return_value = {
        "success": True,
        "placeholders": [
            {
                "content": "test_placeholder",
                "statistical_type": "STATISTICAL",
                "syntax_type": "BASIC",
                "generated_sql": "SELECT SUM(amount) FROM test_table",
                "confidence_score": 0.9,
                "execution_result": {
                    "value": "1000",
                    "unit": "元",
                    "status": "success"
                }
            }
        ],
        "processing_time": 0.5,
        "total_confidence": 0.9
    }
    
    # 批量分析结果
    mock_service.batch_analyze_placeholders.return_value = {
        "success": True,
        "results": [
            {
                "placeholder_id": "ph_001",
                "analysis_result": {
                    "generated_sql": "SELECT COUNT(*) FROM table1",
                    "confidence_score": 0.85
                }
            }
        ]
    }
    
    # SQL验证结果
    mock_service.validate_sql.return_value = {
        "valid": True,
        "issues": [],
        "performance_score": 0.8
    }
    
    # 上下文分析结果
    mock_service.analyze_context.return_value = {
        "document_relevance": 0.9,
        "business_relevance": 0.8,
        "temporal_relevance": 0.7
    }
    
    return mock_service


@pytest.fixture
def performance_test_data():
    """性能测试数据"""
    return {
        "small_dataset": {
            "size": 10,
            "expected_time": 1.0,
            "content": "小数据集测试 " + " ".join([f"{{metric_{i}}}" for i in range(10)])
        },
        "medium_dataset": {
            "size": 100,
            "expected_time": 5.0,
            "content": "中等数据集测试 " + " ".join([f"{{metric_{i}}}" for i in range(100)])
        },
        "large_dataset": {
            "size": 1000,
            "expected_time": 30.0,
            "content": "大数据集测试 " + " ".join([f"{{metric_{i}}}" for i in range(1000)])
        }
    }


@pytest.fixture
def test_scenarios():
    """测试场景数据"""
    return {
        "simple_report": {
            "name": "简单报告",
            "content": "销售额：{{sales}} 元，客户数：{{customers}} 个",
            "expected_placeholders": 2
        },
        "complex_analysis": {
            "name": "复杂分析",
            "content": """
            收入：{{total_revenue}} 万元
            成本：{{total_costs}} 万元
            利润：{{total_revenue - total_costs}} 万元
            利润率：{{(total_revenue - total_costs) / total_revenue * 100}} %
            """,
            "expected_placeholders": 4
        },
        "multi_syntax": {
            "name": "多语法类型",
            "content": """
            基础：{{basic_value}}
            参数：{{param_value(region='test')}}
            复合：{{sum(a, b, c)}}
            条件：{{if x > y then 'high' else 'low'}}
            """,
            "expected_placeholders": 4
        }
    }


@pytest.fixture(autouse=True)
def setup_test_logging():
    """设置测试日志"""
    import logging
    
    # 设置测试期间的日志级别
    logging.getLogger("app.services.domain.placeholder").setLevel(logging.WARNING)
    yield
    # 测试完成后恢复日志级别
    logging.getLogger("app.services.domain.placeholder").setLevel(logging.INFO)