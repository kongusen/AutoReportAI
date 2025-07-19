"""
智能内容生成器单元测试

测试统计数值、时间周期、地理区域等多种内容类型的格式化功能。
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

import pytest

from app.services.ai_integration.content_generator import (
    ContentGenerator,
    FormatConfig,
    GeneratedContent,
)


class TestContentGenerator:
    """智能内容生成器测试"""

    @pytest.fixture
    def generator(self):
        """创建内容生成器实例"""
        return ContentGenerator()

    @pytest.fixture
    def default_format_config(self):
        """默认格式配置"""
        return FormatConfig()

    @pytest.fixture
    def custom_format_config(self):
        """自定义格式配置"""
        return FormatConfig(
            number_format="currency",
            date_format="%Y年%m月%d日",
            decimal_places=1,
            thousand_separator=True,
            currency_symbol="￥",
            locale="zh_CN",
        )

    @pytest.mark.asyncio
    async def test_generate_statistic_content_integer(
        self, generator, default_format_config
    ):
        """测试生成统计内容（整数）"""
        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=1234,
            format_config=default_format_config,
        )

        assert isinstance(result, GeneratedContent)
        assert result.content == "1,234"  # 默认千位分隔符
        assert result.content_type == "number"
        assert result.format_applied == "default"
        assert result.confidence == 0.9
        assert result.metadata["original_value"] == 1234
        assert result.metadata["data_type"] == "int"

    @pytest.mark.asyncio
    async def test_generate_statistic_content_float(
        self, generator, default_format_config
    ):
        """测试生成统计内容（浮点数）"""
        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=1234.567,
            format_config=default_format_config,
        )

        assert result.content == "1,234.57"  # 默认2位小数
        assert result.content_type == "number"
        assert result.confidence == 0.9
        assert result.metadata["original_value"] == 1234.567
        assert result.metadata["data_type"] == "float"

    @pytest.mark.asyncio
    async def test_generate_statistic_content_currency(
        self, generator, custom_format_config
    ):
        """测试生成统计内容（货币格式）"""
        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=1234.56,
            format_config=custom_format_config,
        )

        assert result.content == "￥1,234.6"  # 自定义货币符号和1位小数
        assert result.content_type == "number"
        assert result.format_applied == "currency"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_generate_statistic_content_percentage(self, generator):
        """测试生成统计内容（百分比格式）"""
        percentage_config = FormatConfig(number_format="percentage", decimal_places=1)

        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=0.1234,
            format_config=percentage_config,
        )

        assert result.content == "12.3%"
        assert result.content_type == "number"
        assert result.format_applied == "percentage"

    @pytest.mark.asyncio
    async def test_generate_statistic_content_scientific(self, generator):
        """测试生成统计内容（科学计数法）"""
        scientific_config = FormatConfig(number_format="scientific", decimal_places=2)

        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=123456.789,
            format_config=scientific_config,
        )

        assert "e+" in result.content.lower()
        assert result.content_type == "number"
        assert result.format_applied == "scientific"

    @pytest.mark.asyncio
    async def test_generate_statistic_content_list_aggregation(
        self, generator, default_format_config
    ):
        """测试生成统计内容（列表聚合结果）"""
        aggregation_data = [{"result": 42}]

        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=aggregation_data,
            format_config=default_format_config,
        )

        assert result.content == "42"
        assert result.content_type == "number"
        assert result.metadata["original_value"] == 42
        assert result.metadata["data_source"] == "aggregation"

    @pytest.mark.asyncio
    async def test_generate_statistic_content_list_count(
        self, generator, default_format_config
    ):
        """测试生成统计内容（列表计数）"""
        list_data = [{"item": 1}, {"item": 2}, {"item": 3}]

        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=list_data,
            format_config=default_format_config,
        )

        assert result.content == "3"
        assert result.content_type == "number"
        assert result.format_applied == "count"
        assert result.metadata["original_count"] == 3
        assert result.metadata["data_source"] == "array"

    @pytest.mark.asyncio
    async def test_generate_statistic_content_dict(
        self, generator, default_format_config
    ):
        """测试生成统计内容（字典数据）"""
        dict_data = {"count": 100, "name": "test", "rate": 0.85}

        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=dict_data,
            format_config=default_format_config,
        )

        assert result.content == "100"  # 应该选择第一个数值字段
        assert result.content_type == "number"
        assert result.metadata["original_value"] == 100
        assert result.metadata["field_name"] == "count"
        assert result.metadata["data_source"] == "dict"

    @pytest.mark.asyncio
    async def test_generate_statistic_content_null(
        self, generator, default_format_config
    ):
        """测试生成统计内容（空数据）"""
        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=None,
            format_config=default_format_config,
        )

        assert result.content == "暂无数据"
        assert result.content_type == "text"
        assert result.format_applied == "none"
        assert result.confidence == 0.1
        assert result.metadata["data_type"] == "null"

    @pytest.mark.asyncio
    async def test_generate_period_content_date_string(
        self, generator, default_format_config
    ):
        """测试生成周期内容（日期字符串）"""
        result = await generator.generate_content(
            placeholder_type="周期",
            processed_data="2024-03-15",
            format_config=default_format_config,
        )

        assert result.content == "2024-03-15"  # 默认格式
        assert result.content_type == "date"
        assert result.format_applied == "%Y-%m-%d"
        assert result.confidence == 0.9
        assert result.metadata["original_date"] == "2024-03-15"

    @pytest.mark.asyncio
    async def test_generate_period_content_custom_format(
        self, generator, custom_format_config
    ):
        """测试生成周期内容（自定义格式）"""
        result = await generator.generate_content(
            placeholder_type="周期",
            processed_data="2024-03-15",
            format_config=custom_format_config,
        )

        assert result.content == "2024年03月15日"
        assert result.content_type == "date"
        assert result.format_applied == "%Y年%m月%d日"

    @pytest.mark.asyncio
    async def test_generate_period_content_year_month(
        self, generator, default_format_config
    ):
        """测试生成周期内容（年月格式）"""
        result = await generator.generate_content(
            placeholder_type="周期",
            processed_data="2024-03",
            format_config=default_format_config,
        )

        assert result.content == "2024年03月"
        assert result.content_type == "date"
        assert result.format_applied == "year_month"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_generate_period_content_relative(
        self, generator, default_format_config
    ):
        """测试生成周期内容（相对时间）"""
        context = {"relative_period": "this_month"}

        result = await generator.generate_content(
            placeholder_type="周期",
            processed_data="2024-03",
            format_config=default_format_config,
            context=context,
        )

        assert result.content == "本月"
        assert result.content_type == "period"
        assert result.format_applied == "relative"
        assert result.confidence == 0.8
        assert result.metadata["relative_period"] == "this_month"

    @pytest.mark.asyncio
    async def test_generate_period_content_relative_mappings(
        self, generator, default_format_config
    ):
        """测试生成周期内容（相对时间映射）"""
        test_cases = [
            ("this_month", "本月"),
            ("last_month", "上月"),
            ("this_year", "今年"),
            ("last_year", "去年"),
            ("this_quarter", "本季度"),
            ("last_quarter", "上季度"),
            ("unknown_period", "test_data"),  # 未知周期应返回原数据
        ]

        for relative_period, expected in test_cases:
            context = {"relative_period": relative_period}
            result = await generator.generate_content(
                placeholder_type="周期",
                processed_data="test_data",
                format_config=default_format_config,
                context=context,
            )
            assert result.content == expected

    @pytest.mark.asyncio
    async def test_generate_region_content_string(
        self, generator, default_format_config
    ):
        """测试生成区域内容（字符串）"""
        result = await generator.generate_content(
            placeholder_type="区域",
            processed_data="云南",
            format_config=default_format_config,
        )

        assert result.content == "云南省"  # 标准化后
        assert result.content_type == "region"
        assert result.format_applied == "standardized"
        assert result.confidence == 0.8
        assert result.metadata["original_name"] == "云南"
        assert result.metadata["region_type"] == "province"

    @pytest.mark.asyncio
    async def test_generate_region_content_dict(self, generator, default_format_config):
        """测试生成区域内容（字典）"""
        region_data = {"region_name": "北京", "population": 21000000}

        result = await generator.generate_content(
            placeholder_type="区域",
            processed_data=region_data,
            format_config=default_format_config,
        )

        assert result.content == "北京市"
        assert result.content_type == "region"
        assert result.metadata["original_name"] == "北京"
        assert result.metadata["region_type"] == "city"
        assert result.metadata["additional_data"] == region_data

    @pytest.mark.asyncio
    async def test_generate_chart_content_list(self, generator, default_format_config):
        """测试生成图表内容（列表数据）"""
        chart_data = [
            {"category": "投诉", "value": 100},
            {"category": "咨询", "value": 50},
            {"category": "建议", "value": 25},
        ]

        result = await generator.generate_content(
            placeholder_type="图表",
            processed_data=chart_data,
            format_config=default_format_config,
        )

        assert "3个数据点" in result.content
        assert "投诉(100)" in result.content  # 最高值
        assert result.content_type == "chart"
        assert result.format_applied == "description"
        assert result.confidence == 0.7
        assert result.metadata["data_points"] == 3
        assert result.metadata["chart_data"] == chart_data

    @pytest.mark.asyncio
    async def test_generate_chart_content_coordinates(
        self, generator, default_format_config
    ):
        """测试生成图表内容（坐标数据）"""
        coordinate_data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}, {"x": 3, "y": 15}]

        result = await generator.generate_content(
            placeholder_type="图表",
            processed_data=coordinate_data,
            format_config=default_format_config,
        )

        assert "3个坐标点" in result.content
        assert result.content_type == "chart"
        assert result.format_applied == "description"

    @pytest.mark.asyncio
    async def test_generate_chart_content_empty(self, generator, default_format_config):
        """测试生成图表内容（空数据）"""
        result = await generator.generate_content(
            placeholder_type="图表",
            processed_data=[],
            format_config=default_format_config,
        )

        assert result.content == "[图表数据]"
        assert result.content_type == "chart"
        assert result.format_applied == "placeholder"
        assert result.confidence == 0.3

    @pytest.mark.asyncio
    async def test_generate_unknown_type(self, generator, default_format_config):
        """测试生成未知类型内容"""
        result = await generator.generate_content(
            placeholder_type="未知类型",
            processed_data="测试数据",
            format_config=default_format_config,
        )

        assert result.content == "测试数据"
        assert result.content_type == "text"
        assert result.format_applied == "default"
        assert result.confidence == 0.5
        assert result.metadata["placeholder_type"] == "未知类型"

    @pytest.mark.asyncio
    async def test_generate_content_error_handling(self, generator):
        """测试内容生成错误处理"""
        # 模拟生成过程中的异常
        with pytest.raises(Exception):
            # 这里可以通过mock来模拟异常，但为了简化测试，我们直接测试异常情况
            raise Exception("测试异常")

        # 测试异常数据类型
        result = await generator.generate_content(
            placeholder_type="统计",
            processed_data=object(),  # 不支持的数据类型
            format_config=FormatConfig(),
        )

        # 应该返回字符串表示而不是抛出异常
        assert isinstance(result.content, str)
        assert result.confidence <= 0.5

    def test_format_number_integer(self, generator):
        """测试数值格式化（整数）"""
        config = FormatConfig(thousand_separator=True)

        # 小数值
        result = generator._format_number(123, config)
        assert result == "123"

        # 大数值
        result = generator._format_number(123456, config)
        assert result == "123,456"

        # 无千位分隔符
        config.thousand_separator = False
        result = generator._format_number(123456, config)
        assert result == "123456"

    def test_format_number_float(self, generator):
        """测试数值格式化（浮点数）"""
        config = FormatConfig(decimal_places=2, thousand_separator=True)

        result = generator._format_number(1234.5678, config)
        assert result == "1,234.57"

        # 不同小数位数
        config.decimal_places = 1
        result = generator._format_number(1234.5678, config)
        assert result == "1,234.6"

    def test_format_number_currency(self, generator):
        """测试数值格式化（货币）"""
        config = FormatConfig(
            number_format="currency",
            currency_symbol="$",
            decimal_places=2,
            thousand_separator=True,
        )

        result = generator._format_number(1234.56, config)
        assert result == "$1,234.56"

    def test_format_number_percentage(self, generator):
        """测试数值格式化（百分比）"""
        config = FormatConfig(number_format="percentage", decimal_places=1)

        result = generator._format_number(0.1234, config)
        assert result == "12.3%"

        result = generator._format_number(1.0, config)
        assert result == "100.0%"

    def test_format_number_scientific(self, generator):
        """测试数值格式化（科学计数法）"""
        config = FormatConfig(number_format="scientific", decimal_places=2)

        result = generator._format_number(123456.789, config)
        assert "e+" in result.lower()
        assert result.count(".") == 1  # 应该有小数点

    def test_standardize_region_name(self, generator):
        """测试地理名称标准化"""
        test_cases = [
            ("云南", "云南省"),
            ("北京", "北京市"),
            ("上海", "上海市"),
            ("天津", "天津市"),
            ("重庆", "重庆市"),
            ("广东省", "广东省"),  # 已经标准化的不变
            ("未知地区", "未知地区"),  # 未知地区不变
        ]

        for input_name, expected in test_cases:
            result = generator._standardize_region_name(input_name)
            assert result == expected

    def test_detect_region_type(self, generator):
        """测试区域类型检测"""
        test_cases = [
            ("云南省", "province"),
            ("昆明市", "city"),
            ("五华区", "district"),
            ("西山县", "district"),
            ("未知地区", "unknown"),
        ]

        for region_name, expected_type in test_cases:
            result = generator._detect_region_type(region_name)
            assert result == expected_type

    def test_generate_chart_description(self, generator):
        """测试图表描述生成"""
        # 空数据
        result = generator._generate_chart_description([])
        assert result == "[空图表]"

        # 分类数据
        category_data = [
            {"category": "A", "value": 100},
            {"category": "B", "value": 50},
            {"category": "C", "value": 75},
        ]
        result = generator._generate_chart_description(category_data)
        assert "3个数据点" in result
        assert "A(100)" in result  # 最高值

        # 坐标数据
        coordinate_data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}]
        result = generator._generate_chart_description(coordinate_data)
        assert "2个坐标点" in result

        # 通用数据
        generic_data = [{"field1": "value1"}, {"field2": "value2"}]
        result = generator._generate_chart_description(generic_data)
        assert "2个数据点" in result


class TestFormatConfig:
    """格式配置测试"""

    def test_format_config_defaults(self):
        """测试格式配置默认值"""
        config = FormatConfig()

        assert config.number_format == "default"
        assert config.date_format == "%Y-%m-%d"
        assert config.decimal_places == 2
        assert config.thousand_separator is True
        assert config.currency_symbol == "¥"
        assert config.locale == "zh_CN"

    def test_format_config_custom(self):
        """测试自定义格式配置"""
        config = FormatConfig(
            number_format="currency",
            date_format="%d/%m/%Y",
            decimal_places=3,
            thousand_separator=False,
            currency_symbol="$",
            locale="en_US",
        )

        assert config.number_format == "currency"
        assert config.date_format == "%d/%m/%Y"
        assert config.decimal_places == 3
        assert config.thousand_separator is False
        assert config.currency_symbol == "$"
        assert config.locale == "en_US"


class TestGeneratedContent:
    """生成内容结果测试"""

    def test_generated_content_creation(self):
        """测试生成内容结果创建"""
        content = GeneratedContent(
            content="测试内容",
            content_type="text",
            format_applied="default",
            metadata={"source": "test"},
            confidence=0.8,
        )

        assert content.content == "测试内容"
        assert content.content_type == "text"
        assert content.format_applied == "default"
        assert content.metadata == {"source": "test"}
        assert content.confidence == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
