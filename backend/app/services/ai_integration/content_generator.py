"""
智能内容生成器

根据占位符类型和处理后的数据，智能生成格式化的内容。
支持统计数值、时间周期、地理区域等多种内容类型的格式化。
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class GeneratedContent:
    """生成的内容"""

    content: str
    content_type: str  # text, number, date, chart, table
    format_applied: str
    metadata: Dict[str, Any]
    confidence: float


@dataclass
class FormatConfig:
    """格式化配置"""

    number_format: str = "default"  # default, currency, percentage, scientific
    date_format: str = "%Y-%m-%d"
    decimal_places: int = 2
    thousand_separator: bool = True
    currency_symbol: str = "¥"
    locale: str = "zh_CN"


class ContentGenerator:
    """智能内容生成器"""

    def __init__(self):
        self.default_format_config = FormatConfig()

    async def generate_content(
        self,
        placeholder_type: str,
        processed_data: Any,
        format_config: Optional[FormatConfig] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedContent:
        """
        生成内容

        Args:
            placeholder_type: 占位符类型（统计、周期、区域、图表）
            processed_data: 处理后的数据
            format_config: 格式化配置
            context: 上下文信息

        Returns:
            生成的内容
        """
        if format_config is None:
            format_config = self.default_format_config

        try:
            logger.info(f"开始生成内容，类型: {placeholder_type}")

            if placeholder_type == "统计":
                return await self._generate_statistic_content(
                    processed_data, format_config, context
                )
            elif placeholder_type == "周期":
                return await self._generate_period_content(
                    processed_data, format_config, context
                )
            elif placeholder_type == "区域":
                return await self._generate_region_content(
                    processed_data, format_config, context
                )
            elif placeholder_type == "图表":
                return await self._generate_chart_content(
                    processed_data, format_config, context
                )
            else:
                # 默认文本内容
                return GeneratedContent(
                    content=str(processed_data) if processed_data is not None else "",
                    content_type="text",
                    format_applied="default",
                    metadata={"placeholder_type": placeholder_type},
                    confidence=0.5,
                )

        except Exception as e:
            logger.error(f"内容生成失败: {e}")
            return GeneratedContent(
                content=str(processed_data) if processed_data is not None else "",
                content_type="text",
                format_applied="error",
                metadata={"error": str(e)},
                confidence=0.1,
            )

    async def _generate_statistic_content(
        self,
        data: Any,
        format_config: FormatConfig,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedContent:
        """生成统计类内容"""

        if data is None:
            return GeneratedContent(
                content="暂无数据",
                content_type="text",
                format_applied="none",
                metadata={"data_type": "null"},
                confidence=0.1,
            )

        # 处理数值数据
        if isinstance(data, (int, float)):
            formatted_content = self._format_number(data, format_config)

            return GeneratedContent(
                content=formatted_content,
                content_type="number",
                format_applied=format_config.number_format,
                metadata={"original_value": data, "data_type": type(data).__name__},
                confidence=0.9,
            )

        # 处理列表数据（可能是聚合结果）
        elif isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict) and "result" in data[0]:
                # 聚合结果
                value = data[0]["result"]
                formatted_content = self._format_number(value, format_config)

                return GeneratedContent(
                    content=formatted_content,
                    content_type="number",
                    format_applied=format_config.number_format,
                    metadata={"original_value": value, "data_source": "aggregation"},
                    confidence=0.8,
                )
            else:
                # 数组数据，计算总数
                count = len(data)
                formatted_content = self._format_number(count, format_config)

                return GeneratedContent(
                    content=formatted_content,
                    content_type="number",
                    format_applied="count",
                    metadata={"original_count": count, "data_source": "array"},
                    confidence=0.7,
                )

        # 处理字典数据
        elif isinstance(data, dict):
            # 查找数值字段
            numeric_fields = []
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    numeric_fields.append((key, value))

            if numeric_fields:
                # 使用第一个数值字段
                key, value = numeric_fields[0]
                formatted_content = self._format_number(value, format_config)

                return GeneratedContent(
                    content=formatted_content,
                    content_type="number",
                    format_applied=format_config.number_format,
                    metadata={
                        "original_value": value,
                        "field_name": key,
                        "data_source": "dict",
                    },
                    confidence=0.8,
                )

        # 默认处理
        return GeneratedContent(
            content=str(data),
            content_type="text",
            format_applied="string",
            metadata={"data_type": type(data).__name__},
            confidence=0.5,
        )

    async def _generate_period_content(
        self,
        data: Any,
        format_config: FormatConfig,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedContent:
        """生成周期类内容"""

        # 处理时间数据
        if isinstance(data, str):
            # 尝试解析时间字符串
            try:
                if re.match(r"\d{4}-\d{2}-\d{2}", data):
                    # 日期格式
                    date_obj = datetime.strptime(data, "%Y-%m-%d")
                    formatted_content = date_obj.strftime(format_config.date_format)

                    return GeneratedContent(
                        content=formatted_content,
                        content_type="date",
                        format_applied=format_config.date_format,
                        metadata={
                            "original_date": data,
                            "parsed_date": date_obj.isoformat(),
                        },
                        confidence=0.9,
                    )
                elif re.match(r"\d{4}-\d{2}", data):
                    # 年月格式
                    date_obj = datetime.strptime(data, "%Y-%m")
                    formatted_content = date_obj.strftime("%Y年%m月")

                    return GeneratedContent(
                        content=formatted_content,
                        content_type="date",
                        format_applied="year_month",
                        metadata={
                            "original_date": data,
                            "parsed_date": date_obj.isoformat(),
                        },
                        confidence=0.9,
                    )
            except ValueError:
                pass

        # 处理相对时间描述
        if context and "relative_period" in context:
            relative_period = context["relative_period"]
            period_mapping = {
                "this_month": "本月",
                "last_month": "上月",
                "this_year": "今年",
                "last_year": "去年",
                "this_quarter": "本季度",
                "last_quarter": "上季度",
            }

            formatted_content = period_mapping.get(relative_period, str(data))

            return GeneratedContent(
                content=formatted_content,
                content_type="period",
                format_applied="relative",
                metadata={"relative_period": relative_period, "original_data": data},
                confidence=0.8,
            )

        # 默认处理
        return GeneratedContent(
            content=str(data),
            content_type="text",
            format_applied="default",
            metadata={"data_type": type(data).__name__},
            confidence=0.5,
        )

    async def _generate_region_content(
        self,
        data: Any,
        format_config: FormatConfig,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedContent:
        """生成区域类内容"""

        if isinstance(data, str):
            # 标准化地理名称
            formatted_content = self._standardize_region_name(data)

            return GeneratedContent(
                content=formatted_content,
                content_type="region",
                format_applied="standardized",
                metadata={
                    "original_name": data,
                    "region_type": self._detect_region_type(formatted_content),
                },
                confidence=0.8,
            )

        elif isinstance(data, dict) and "region_name" in data:
            region_name = data["region_name"]
            formatted_content = self._standardize_region_name(region_name)

            return GeneratedContent(
                content=formatted_content,
                content_type="region",
                format_applied="standardized",
                metadata={
                    "original_name": region_name,
                    "region_type": self._detect_region_type(formatted_content),
                    "additional_data": data,
                },
                confidence=0.8,
            )

        # 默认处理
        return GeneratedContent(
            content=str(data),
            content_type="text",
            format_applied="default",
            metadata={"data_type": type(data).__name__},
            confidence=0.5,
        )

    async def _generate_chart_content(
        self,
        data: Any,
        format_config: FormatConfig,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedContent:
        """生成图表类内容"""

        if isinstance(data, list) and len(data) > 0:
            # 检查是否是图表数据格式
            if all(isinstance(item, dict) for item in data):
                # 生成图表描述
                chart_description = self._generate_chart_description(data)

                return GeneratedContent(
                    content=chart_description,
                    content_type="chart",
                    format_applied="description",
                    metadata={
                        "data_points": len(data),
                        "chart_data": data,
                        "chart_type": "auto_detected",
                    },
                    confidence=0.7,
                )

        # 默认处理
        return GeneratedContent(
            content="[图表数据]",
            content_type="chart",
            format_applied="placeholder",
            metadata={"original_data": data},
            confidence=0.3,
        )

    def _format_number(
        self, value: Union[int, float], format_config: FormatConfig
    ) -> str:
        """格式化数值"""

        if format_config.number_format == "currency":
            # 货币格式
            if format_config.thousand_separator:
                formatted = f"{value:,.{format_config.decimal_places}f}"
            else:
                formatted = f"{value:.{format_config.decimal_places}f}"
            return f"{format_config.currency_symbol}{formatted}"

        elif format_config.number_format == "percentage":
            # 百分比格式
            percentage = value * 100
            return f"{percentage:.{format_config.decimal_places}f}%"

        elif format_config.number_format == "scientific":
            # 科学计数法
            return f"{value:.{format_config.decimal_places}e}"

        else:
            # 默认数值格式
            if isinstance(value, int):
                if format_config.thousand_separator and abs(value) >= 1000:
                    return f"{value:,}"
                else:
                    return str(value)
            else:
                if format_config.thousand_separator:
                    return f"{value:,.{format_config.decimal_places}f}"
                else:
                    return f"{value:.{format_config.decimal_places}f}"

    def _standardize_region_name(self, region_name: str) -> str:
        """标准化地理名称"""

        # 移除多余的空格
        region_name = region_name.strip()

        # 标准化省份名称
        province_mapping = {
            "云南": "云南省",
            "北京": "北京市",
            "上海": "上海市",
            "天津": "天津市",
            "重庆": "重庆市",
        }

        for short_name, full_name in province_mapping.items():
            if region_name == short_name:
                return full_name

        return region_name

    def _detect_region_type(self, region_name: str) -> str:
        """检测区域类型"""

        if region_name.endswith("省"):
            return "province"
        elif region_name.endswith("市"):
            return "city"
        elif region_name.endswith("区") or region_name.endswith("县"):
            return "district"
        else:
            return "unknown"

    def _generate_chart_description(self, chart_data: List[Dict]) -> str:
        """生成图表描述"""

        if not chart_data:
            return "[空图表]"

        data_points = len(chart_data)

        # 检查数据结构
        first_item = chart_data[0]
        if "category" in first_item and "value" in first_item:
            # 分类数据
            categories = [item.get("category", "") for item in chart_data]
            values = [item.get("value", 0) for item in chart_data]

            max_value = max(values) if values else 0
            max_category = categories[values.index(max_value)] if values else ""

            return (
                f"包含{data_points}个数据点的图表，最高值为{max_category}({max_value})"
            )

        elif "x" in first_item and "y" in first_item:
            # 坐标数据
            return f"包含{data_points}个坐标点的图表"

        else:
            # 通用描述
            return f"包含{data_points}个数据点的图表"


# 创建全局实例
content_generator = ContentGenerator()
