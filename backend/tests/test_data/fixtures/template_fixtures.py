"""
Template-specific test fixtures and data.

Provides template-related test data for various testing scenarios.
"""

from typing import Any, Dict, List


def get_simple_template() -> Dict[str, str]:
    """Simple template for basic testing."""
    return {
        "name": "Simple Template",
        "content": "Hello {{name}}! Today is {{date}}.",
        "description": "A simple template for testing basic placeholder replacement",
    }


def get_report_template() -> Dict[str, str]:
    """Report template with multiple placeholders."""
    return {
        "name": "Monthly Report",
        "content": """Monthly Report for {{month}} {{year}}

Summary:
- Total Sales: {{total_sales}}
- Top Product: {{top_product}}
- Growth Rate: {{growth_rate}}%

{{chart:sales_chart}}

Analysis: {{analysis}}""",
        "description": "Monthly report template with charts and analysis",
    }


def get_complex_template() -> Dict[str, str]:
    """Complex template with nested placeholders and conditions."""
    return {
        "name": "Complex Analysis Template",
        "content": """{{region}} Analysis Report - {{period}}

{{if:has_data}}
Data Summary:
{{loop:data_items}}
- {{item.name}}: {{item.value}} ({{item.change}}%)
{{/loop}}

{{chart:trend_analysis "Trend Analysis Chart"}}

{{if:performance_good}}
✅ Performance is above target
{{else}}
⚠️ Performance needs improvement
{{/if}}
{{else}}
No data available for this period.
{{/if}}

Generated on: {{current_date}}""",
        "description": "Complex template with conditions and loops",
    }


def get_template_with_intelligent_placeholders() -> Dict[str, Any]:
    """Template with intelligent placeholder support."""
    return {
        "name": "Intelligent Placeholder Template",
        "content": """{{周期:报告年份}}年{{区域:地区名称}}数据分析报告

统计数据：
- 总数量：{{统计:总数量}}
- 平均值：{{统计:平均值}}
- 最大值：{{统计:最大值}}

{{图表:趋势图表}}

分析结论：{{分析:总结}}""",
        "supports_intelligent_placeholders": True,
        "placeholder_types": ["周期", "区域", "统计", "图表", "分析"],
        "description": "Template with Chinese intelligent placeholders",
    }


def get_template_test_cases() -> List[Dict[str, Any]]:
    """Various template test cases for comprehensive testing."""
    return [
        {"name": "Empty Template", "content": "", "expected_placeholders": []},
        {
            "name": "No Placeholders",
            "content": "This is a plain text template without any placeholders.",
            "expected_placeholders": [],
        },
        {
            "name": "Single Placeholder",
            "content": "Hello {{name}}!",
            "expected_placeholders": ["name"],
        },
        {
            "name": "Multiple Placeholders",
            "content": "{{greeting}} {{name}}, today is {{date}}.",
            "expected_placeholders": ["greeting", "name", "date"],
        },
        {
            "name": "Duplicate Placeholders",
            "content": "{{name}} and {{name}} are both {{name}}.",
            "expected_placeholders": ["name"],
        },
        {
            "name": "Nested Braces",
            "content": "{{outer {{inner}} placeholder}}",
            "expected_placeholders": ["outer {{inner}} placeholder"],
        },
        {
            "name": "Chart Placeholder",
            "content": "Sales data: {{chart:sales_chart}}",
            "expected_placeholders": ["chart:sales_chart"],
        },
    ]


def get_placeholder_replacement_data() -> Dict[str, Any]:
    """Sample data for placeholder replacement testing."""
    return {
        "name": "John Doe",
        "date": "2024-01-15",
        "greeting": "Hello",
        "month": "January",
        "year": "2024",
        "total_sales": "150,000",
        "top_product": "Product A",
        "growth_rate": "12.5",
        "region": "North America",
        "period": "Q1 2024",
        "current_date": "2024-01-15 10:30:00",
    }
