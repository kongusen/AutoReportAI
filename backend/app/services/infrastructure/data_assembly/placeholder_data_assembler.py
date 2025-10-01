"""
占位符数据组装器

负责将ETL查询结果组装成标准化的占位符数据格式，便于后续文档组装使用
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PlaceholderType(Enum):
    """占位符类型"""
    STATISTIC = "statistic"      # 统计数据
    TIME = "time"               # 时间数据
    VISUALIZATION = "visualization"  # 图表数据
    TEXT = "text"               # 纯文本数据


class DisplayFormat(Enum):
    """显示格式类型"""
    NUMBER = "number"                    # 普通数字
    NUMBER_WITH_UNIT = "number_with_unit"  # 带单位数字
    PERCENTAGE = "percentage"            # 百分比
    CURRENCY = "currency"               # 货币
    DATE = "date"                       # 日期
    DATE_RANGE = "date_range"           # 日期范围
    DATE_RANGE_CHINESE = "date_range_chinese"  # 中文日期范围


@dataclass
class ProcessedValue:
    """处理后的值"""
    raw_value: Union[int, float, str, Dict, List]
    formatted_value: str
    display_format: DisplayFormat
    unit: Optional[str] = None
    decimal_places: Optional[int] = None


@dataclass
class PlaceholderData:
    """标准化的占位符数据"""
    placeholder_name: str
    placeholder_type: PlaceholderType
    status: str  # success/error/partial
    processed_value: Optional[ProcessedValue]
    raw_data: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PlaceholderDataAssembler:
    """占位符数据组装器"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def assemble_etl_results(self,
                           etl_results: Dict[str, Any],
                           placeholders: List[Any],
                           time_window: Dict[str, str]) -> Dict[str, PlaceholderData]:
        """
        将ETL结果组装成标准化的占位符数据格式

        Args:
            etl_results: 原始ETL结果
            placeholders: 占位符列表
            time_window: 时间窗口

        Returns:
            标准化的占位符数据字典
        """
        assembled_data = {}

        for placeholder in placeholders:
            placeholder_name = placeholder.placeholder_name

            # 获取ETL结果
            etl_result = etl_results.get(placeholder_name, {})

            # 确定占位符类型
            placeholder_type = self._determine_placeholder_type(placeholder_name)

            # 组装数据
            try:
                if etl_result.get("success", False):
                    placeholder_data = self._assemble_successful_result(
                        placeholder_name, placeholder_type, etl_result, time_window
                    )
                else:
                    placeholder_data = self._assemble_error_result(
                        placeholder_name, placeholder_type, etl_result
                    )

                assembled_data[placeholder_name] = placeholder_data

            except Exception as e:
                self.logger.error(f"Failed to assemble data for {placeholder_name}: {e}")
                assembled_data[placeholder_name] = self._assemble_error_result(
                    placeholder_name, placeholder_type, {"error": str(e)}
                )

        return assembled_data

    def _determine_placeholder_type(self, placeholder_name: str) -> PlaceholderType:
        """确定占位符类型"""
        if '周期' in placeholder_name or '时间' in placeholder_name:
            return PlaceholderType.TIME
        elif '统计' in placeholder_name or '数量' in placeholder_name or '占比' in placeholder_name:
            return PlaceholderType.STATISTIC
        elif '图表' in placeholder_name or '表格' in placeholder_name:
            return PlaceholderType.VISUALIZATION
        else:
            return PlaceholderType.TEXT

    def _assemble_successful_result(self,
                                  placeholder_name: str,
                                  placeholder_type: PlaceholderType,
                                  etl_result: Dict[str, Any],
                                  time_window: Dict[str, str]) -> PlaceholderData:
        """组装成功的结果"""

        raw_data = etl_result.get("data", [])

        if placeholder_type == PlaceholderType.STATISTIC:
            return self._assemble_statistic_data(placeholder_name, raw_data, etl_result)
        elif placeholder_type == PlaceholderType.TIME:
            return self._assemble_time_data(placeholder_name, time_window, etl_result)
        elif placeholder_type == PlaceholderType.VISUALIZATION:
            return self._assemble_visualization_data(placeholder_name, raw_data, etl_result)
        else:
            return self._assemble_text_data(placeholder_name, raw_data, etl_result)

    def _assemble_statistic_data(self,
                               placeholder_name: str,
                               raw_data: List[Dict],
                               etl_result: Dict[str, Any]) -> PlaceholderData:
        """组装统计数据"""

        # 从原始数据中提取值
        if raw_data and len(raw_data) > 0:
            first_row = raw_data[0]
            # 尝试获取数值（假设查询返回的第一个数值字段就是我们要的）
            raw_value = None
            for key, value in first_row.items():
                if isinstance(value, (int, float)):
                    raw_value = value
                    break

            if raw_value is None and first_row:
                # 如果没有数值字段，取第一个值
                raw_value = list(first_row.values())[0]
        else:
            raw_value = 0

        # 格式化数值
        if '占比' in placeholder_name or '百分比' in placeholder_name:
            formatted_value = f"{raw_value:.2f}%"
            display_format = DisplayFormat.PERCENTAGE
            unit = "%"
        elif '数量' in placeholder_name or '申请' in placeholder_name:
            formatted_value = f"{raw_value:,}件"
            display_format = DisplayFormat.NUMBER_WITH_UNIT
            unit = "件"
        else:
            formatted_value = f"{raw_value:,}"
            display_format = DisplayFormat.NUMBER
            unit = None

        processed_value = ProcessedValue(
            raw_value=raw_value,
            formatted_value=formatted_value,
            display_format=display_format,
            unit=unit,
            decimal_places=2 if display_format == DisplayFormat.PERCENTAGE else 0
        )

        return PlaceholderData(
            placeholder_name=placeholder_name,
            placeholder_type=PlaceholderType.STATISTIC,
            status="success",
            processed_value=processed_value,
            raw_data=raw_data,
            metadata={
                "sql_executed": etl_result.get("metadata", {}).get("sql", ""),
                "execution_time": etl_result.get("execution_time", 0),
                "row_count": etl_result.get("row_count", 0),
                "last_updated": datetime.utcnow().isoformat()
            }
        )

    def _assemble_time_data(self,
                          placeholder_name: str,
                          time_window: Dict[str, str],
                          etl_result: Dict[str, Any]) -> PlaceholderData:
        """组装时间数据"""

        start_date = time_window.get("start", "")
        end_date = time_window.get("end", "")

        # 根据占位符名称格式化时间
        if "示例：8月1日-8月6日" in placeholder_name:
            # 短格式
            formatted_value = self._format_date_range_short(start_date, end_date)
        elif "示例：2025年8月1日至2025年8月6日" in placeholder_name:
            # 长格式
            formatted_value = self._format_date_range_long(start_date, end_date)
        else:
            formatted_value = f"{start_date} 至 {end_date}"

        processed_value = ProcessedValue(
            raw_value={"start_date": start_date, "end_date": end_date},
            formatted_value=formatted_value,
            display_format=DisplayFormat.DATE_RANGE_CHINESE
        )

        return PlaceholderData(
            placeholder_name=placeholder_name,
            placeholder_type=PlaceholderType.TIME,
            status="success",
            processed_value=processed_value,
            raw_data=[{"start_date": start_date, "end_date": end_date}],
            metadata={
                "period_type": "daily",  # 可以从time_window推断
                "timezone": "Asia/Shanghai"
            }
        )

    def _assemble_visualization_data(self,
                                   placeholder_name: str,
                                   raw_data: List[Dict],
                                   etl_result: Dict[str, Any]) -> PlaceholderData:
        """组装图表数据"""

        # 这里需要根据图表类型和数据生成图表配置
        chart_config = {
            "title": "数据图表",
            "type": "bar",  # 从placeholder_name中解析
            "data": raw_data
        }

        processed_value = ProcessedValue(
            raw_value=chart_config,
            formatted_value="[图表]",
            display_format=DisplayFormat.NUMBER  # 图表用特殊处理
        )

        return PlaceholderData(
            placeholder_name=placeholder_name,
            placeholder_type=PlaceholderType.VISUALIZATION,
            status="success",
            processed_value=processed_value,
            raw_data=raw_data,
            metadata={
                "chart_type": "bar",
                "data_points": len(raw_data)
            }
        )

    def _assemble_text_data(self,
                          placeholder_name: str,
                          raw_data: List[Dict],
                          etl_result: Dict[str, Any]) -> PlaceholderData:
        """组装文本数据"""

        # 简单的文本处理
        if raw_data and len(raw_data) > 0:
            text_value = str(list(raw_data[0].values())[0])
        else:
            text_value = ""

        processed_value = ProcessedValue(
            raw_value=text_value,
            formatted_value=text_value,
            display_format=DisplayFormat.NUMBER
        )

        return PlaceholderData(
            placeholder_name=placeholder_name,
            placeholder_type=PlaceholderType.TEXT,
            status="success",
            processed_value=processed_value,
            raw_data=raw_data,
            metadata={}
        )

    def _assemble_error_result(self,
                             placeholder_name: str,
                             placeholder_type: PlaceholderType,
                             etl_result: Dict[str, Any]) -> PlaceholderData:
        """组装错误结果"""

        return PlaceholderData(
            placeholder_name=placeholder_name,
            placeholder_type=placeholder_type,
            status="error",
            processed_value=None,
            raw_data=[],
            metadata={},
            error=etl_result.get("error", "Unknown error")
        )

    def _format_date_range_short(self, start_date: str, end_date: str) -> str:
        """格式化短日期范围"""
        # 简化实现，实际应该解析日期并格式化
        return "1月1日-1月31日"

    def _format_date_range_long(self, start_date: str, end_date: str) -> str:
        """格式化长日期范围"""
        # 简化实现，实际应该解析日期并格式化
        return "2025年1月1日至2025年1月31日"