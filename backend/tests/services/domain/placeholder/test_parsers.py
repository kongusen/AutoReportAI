"""
占位符解析器单元测试
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.domain.placeholder.parsers import (
    PlaceholderParser,
    ParameterizedParser, 
    CompositeParser,
    ConditionalParser,
    SyntaxValidator,
    ParserFactory
)
from app.services.domain.placeholder.models import (
    PlaceholderSpec,
    StatisticalType,
    SyntaxType
)

class TestPlaceholderParser:
    """基础占位符解析器测试"""
    
    def setup_method(self):
        self.parser = PlaceholderParser()
    
    def test_parse_basic_placeholder(self):
        """测试基础占位符解析"""
        content = "销售额为 {{sales_total}} 元"
        
        placeholders = self.parser.parse(content)
        
        assert len(placeholders) == 1
        assert placeholders[0].content == "sales_total"
        assert placeholders[0].statistical_type == StatisticalType.STATISTICAL
        assert placeholders[0].syntax_type == SyntaxType.BASIC
    
    def test_parse_multiple_placeholders(self):
        """测试多个占位符解析"""
        content = "销售额 {{sales_total}} 比去年同期 {{last_year_sales}} 增长了 {{growth_rate}}"
        
        placeholders = self.parser.parse(content)
        
        assert len(placeholders) == 3
        expected_contents = ["sales_total", "last_year_sales", "growth_rate"]
        actual_contents = [p.content for p in placeholders]
        assert actual_contents == expected_contents
    
    def test_parse_no_placeholders(self):
        """测试无占位符内容"""
        content = "这是一段没有占位符的文本"
        
        placeholders = self.parser.parse(content)
        
        assert len(placeholders) == 0
    
    def test_parse_nested_brackets(self):
        """测试嵌套括号"""
        content = "数据：{{outer_{{inner}}_value}}"
        
        placeholders = self.parser.parse(content)
        
        # 应该正确处理嵌套
        assert len(placeholders) == 1
        assert "outer_" in placeholders[0].content or "inner" in placeholders[0].content

class TestParameterizedParser:
    """参数化占位符解析器测试"""
    
    def setup_method(self):
        self.parser = ParameterizedParser()
    
    def test_parse_parameterized_placeholder(self):
        """测试参数化占位符解析"""
        content = "销售额：{{sales(region='北京', year=2023)}}"
        
        placeholders = self.parser.parse(content)
        
        assert len(placeholders) == 1
        placeholder = placeholders[0]
        assert placeholder.syntax_type == SyntaxType.PARAMETERIZED
        assert "sales" in placeholder.content
        assert placeholder.parameters is not None
        assert "region" in str(placeholder.parameters)
    
    def test_parse_multiple_parameters(self):
        """测试多参数占位符"""
        content = "{{revenue(region='上海', product='手机', period='Q1')}}"
        
        placeholders = self.parser.parse(content)
        
        assert len(placeholders) == 1
        placeholder = placeholders[0]
        # 检查参数解析
        params_str = str(placeholder.parameters)
        assert "'上海'" in params_str
        assert "'手机'" in params_str
        assert "'Q1'" in params_str

class TestCompositeParser:
    """复合占位符解析器测试"""
    
    def setup_method(self):
        self.parser = CompositeParser()
    
    def test_parse_composite_placeholder(self):
        """测试复合占位符解析"""
        content = "总销售额：{{sum(sales_q1, sales_q2, sales_q3, sales_q4)}}"
        
        placeholders = self.parser.parse(content)
        
        assert len(placeholders) == 1
        placeholder = placeholders[0]
        assert placeholder.syntax_type == SyntaxType.COMPOSITE
        assert "sum" in placeholder.content
    
    def test_parse_complex_composite(self):
        """测试复杂复合占位符"""
        content = "增长率：{{(current_sales - previous_sales) / previous_sales * 100}}"
        
        placeholders = self.parser.parse(content)
        
        assert len(placeholders) == 1
        placeholder = placeholders[0]
        assert placeholder.syntax_type == SyntaxType.COMPOSITE

class TestConditionalParser:
    """条件占位符解析器测试"""
    
    def setup_method(self):
        self.parser = ConditionalParser()
    
    def test_parse_conditional_placeholder(self):
        """测试条件占位符解析"""
        content = "状态：{{if sales > target then '超额完成' else '未达标'}}"
        
        placeholders = self.parser.parse(content)
        
        assert len(placeholders) == 1
        placeholder = placeholders[0]
        assert placeholder.syntax_type == SyntaxType.CONDITIONAL
        assert "if" in placeholder.content
        assert "then" in placeholder.content
        assert "else" in placeholder.content

class TestSyntaxValidator:
    """语法验证器测试"""
    
    def setup_method(self):
        self.validator = SyntaxValidator()
    
    def test_validate_basic_syntax(self):
        """测试基础语法验证"""
        placeholder = PlaceholderSpec(
            content="sales_total",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=0,
            end_position=15
        )
        
        is_valid, errors = self.validator.validate(placeholder)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_invalid_syntax(self):
        """测试无效语法"""
        placeholder = PlaceholderSpec(
            content="",  # 空内容
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=0,
            end_position=5
        )
        
        is_valid, errors = self.validator.validate(placeholder)
        
        assert not is_valid
        assert len(errors) > 0
        assert "内容不能为空" in str(errors)
    
    def test_validate_parameterized_syntax(self):
        """测试参数化语法验证"""
        placeholder = PlaceholderSpec(
            content="sales(region='北京')",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.PARAMETERIZED,
            start_position=0,
            end_position=20,
            parameters={"region": "北京"}
        )
        
        is_valid, errors = self.validator.validate(placeholder)
        
        assert is_valid
        assert len(errors) == 0

class TestParserFactory:
    """解析器工厂测试"""
    
    def setup_method(self):
        self.factory = ParserFactory()
    
    def test_create_basic_parser(self):
        """测试创建基础解析器"""
        parser = self.factory.create_parser(SyntaxType.BASIC)
        
        assert isinstance(parser, PlaceholderParser)
    
    def test_create_parameterized_parser(self):
        """测试创建参数化解析器"""
        parser = self.factory.create_parser(SyntaxType.PARAMETERIZED)
        
        assert isinstance(parser, ParameterizedParser)
    
    def test_create_composite_parser(self):
        """测试创建复合解析器"""
        parser = self.factory.create_parser(SyntaxType.COMPOSITE)
        
        assert isinstance(parser, CompositeParser)
    
    def test_create_conditional_parser(self):
        """测试创建条件解析器"""
        parser = self.factory.create_parser(SyntaxType.CONDITIONAL)
        
        assert isinstance(parser, ConditionalParser)
    
    def test_auto_detect_parser_type(self):
        """测试自动检测解析器类型"""
        test_cases = [
            ("{{sales_total}}", SyntaxType.BASIC),
            ("{{sales(region='北京')}}", SyntaxType.PARAMETERIZED),
            ("{{sum(q1, q2, q3)}}", SyntaxType.COMPOSITE),
            ("{{if x > y then 'high' else 'low'}}", SyntaxType.CONDITIONAL)
        ]
        
        for content, expected_type in test_cases:
            detected_type = self.factory.detect_syntax_type(content)
            assert detected_type == expected_type
    
    def test_parse_with_auto_detection(self):
        """测试自动检测解析"""
        content = "销售额：{{sales(region='北京')}} 状态：{{if sales > 100 then '优秀' else '良好'}}"
        
        placeholders = self.factory.parse_with_auto_detection(content)
        
        assert len(placeholders) == 2
        assert placeholders[0].syntax_type == SyntaxType.PARAMETERIZED
        assert placeholders[1].syntax_type == SyntaxType.CONDITIONAL

class TestIntegrationScenarios:
    """集成场景测试"""
    
    def test_complex_document_parsing(self):
        """测试复杂文档解析"""
        content = """
        销售报告
        
        本月销售额：{{current_month_sales}} 元
        去年同期：{{last_year_sales(month=current_month)}} 元
        增长率：{{(current_month_sales - last_year_same_month) / last_year_same_month * 100}}%
        
        评估结果：{{if growth_rate > 10 then '表现优异' else if growth_rate > 0 then '稳步增长' else '需要改进'}}
        
        地区分析：
        - 北京：{{region_sales(region='北京')}}
        - 上海：{{region_sales(region='上海')}}
        - 深圳：{{region_sales(region='深圳')}}
        
        总结：{{summary(sales_data, growth_data, region_data)}}
        """
        
        factory = ParserFactory()
        placeholders = factory.parse_with_auto_detection(content)
        
        # 验证解析出的占位符数量和类型
        assert len(placeholders) >= 7  # 至少应该有7个占位符
        
        syntax_types = [p.syntax_type for p in placeholders]
        assert SyntaxType.BASIC in syntax_types
        assert SyntaxType.PARAMETERIZED in syntax_types
        assert SyntaxType.COMPOSITE in syntax_types
        assert SyntaxType.CONDITIONAL in syntax_types
    
    def test_error_handling(self):
        """测试错误处理"""
        factory = ParserFactory()
        
        # 测试格式错误的占位符
        malformed_content = "销售额：{{sales(region='北京'}} 元"  # 缺少右括号
        
        placeholders = factory.parse_with_auto_detection(malformed_content)
        
        # 应该能够处理错误并返回部分结果或空结果
        assert isinstance(placeholders, list)
    
    def test_performance_with_large_content(self):
        """测试大内容解析性能"""
        # 生成大量占位符内容
        large_content = "\n".join([
            f"第{i}项数据：{{item_{i}}} 参数化：{{data(id={i})}} 条件：{{if value_{i} > 100 then 'high' else 'low'}}"
            for i in range(100)
        ])
        
        factory = ParserFactory()
        start_time = datetime.now()
        
        placeholders = factory.parse_with_auto_detection(large_content)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # 验证性能
        assert len(placeholders) == 300  # 100 * 3 = 300个占位符
        assert processing_time < 5.0  # 应该在5秒内完成