from __future__ import annotations

from loom.interfaces.tool import BaseTool
"""
时间窗口工具

处理时间窗口相关的数据操作
支持滑动窗口、固定窗口和会话窗口
"""


import logging
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class WindowType(str, Enum):
    """窗口类型"""
    TUMBLING = "tumbling"       # 滚动窗口
    SLIDING = "sliding"         # 滑动窗口
    SESSION = "session"         # 会话窗口
    CUSTOM = "custom"          # 自定义窗口


class TimeUnit(str, Enum):
    """时间单位"""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass
class WindowConfig:
    """窗口配置"""
    window_type: WindowType
    size: int
    time_unit: TimeUnit
    slide_size: Optional[int] = None
    session_timeout: Optional[int] = None
    time_column: str = "timestamp"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WindowResult:
    """窗口结果"""
    windows: List[Dict[str, Any]]
    window_count: int
    total_records: int
    config: WindowConfig
    statistics: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TimeWindowTool(BaseTool):
    """时间窗口工具"""
    
    def __init__(self, container: Any):
        """
        Args:
            container: 服务容器
        """
        super().__init__()

        self.name = "time_window"

        self.category = ToolCategory.TIME

        self.description = "处理时间窗口相关的数据操作" 
        self.container = container
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class TimeWindowArgs(BaseModel):
            data: List[Dict[str, Any]] = Field(description="要处理的数据")
            window_type: Literal["tumbling", "sliding", "session", "custom"] = Field(
                default="tumbling", description="窗口类型"
            )
            size: int = Field(default=1, description="窗口大小")
            time_unit: Literal["second", "minute", "hour", "day", "week", "month", "year"] = Field(
                default="hour", description="时间单位"
            )
            slide_size: Optional[int] = Field(default=None, description="滑动大小（用于滑动窗口）")
            session_timeout: Optional[int] = Field(default=None, description="会话超时时间（秒）")
            time_column: str = Field(default="timestamp", description="时间列名")
            aggregation: Optional[Dict[str, str]] = Field(default=None, description="聚合配置")

        self.args_schema = TimeWindowArgs
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "time_window",
                "description": "处理时间窗口相关的数据操作",
                "parameters": parameters,
            },
        }
    
    async def run(
        self,
        data: List[Dict[str, Any]],
        window_type: str = "tumbling",
        size: int = 1,
        time_unit: str = "hour",
        slide_size: Optional[int] = None,
        session_timeout: Optional[int] = None,
        time_column: str = "timestamp",
        aggregation: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行时间窗口操作
        
        Args:
            data: 要处理的数据
            window_type: 窗口类型
            size: 窗口大小
            time_unit: 时间单位
            slide_size: 滑动大小
            session_timeout: 会话超时时间
            time_column: 时间列名
            aggregation: 聚合配置
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        logger.info(f"⏰ [TimeWindowTool] 处理时间窗口")
        logger.info(f"   窗口类型: {window_type}")
        logger.info(f"   窗口大小: {size} {time_unit}")
        logger.info(f"   数据行数: {len(data)}")
        
        try:
            if not data:
                return {
                    "success": False,
                    "error": "数据为空",
                    "result": None
                }
            
            # 构建窗口配置
            config = WindowConfig(
                window_type=WindowType(window_type),
                size=size,
                time_unit=TimeUnit(time_unit),
                slide_size=slide_size,
                session_timeout=session_timeout,
                time_column=time_column
            )
            
            # 验证时间列
            if time_column not in data[0]:
                return {
                    "success": False,
                    "error": f"时间列 '{time_column}' 不存在",
                    "result": None
                }
            
            # 执行窗口操作
            result = await self._process_windows(data, config, aggregation)
            
            return {
                "success": True,
                "result": result,
                "window": {
                    "start": result.windows[0]["start_time"] if result.windows else None,
                    "end": result.windows[-1]["end_time"] if result.windows else None,
                    "window_count": result.window_count
                },
                "metadata": {
                    "window_type": window_type,
                    "size": size,
                    "time_unit": time_unit,
                    "window_count": result.window_count,
                    "total_records": result.total_records
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [TimeWindowTool] 处理失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """向后兼容的execute方法"""
        return await self.run(**kwargs)
    
    async def _process_windows(
        self,
        data: List[Dict[str, Any]],
        config: WindowConfig,
        aggregation: Optional[Dict[str, str]]
    ) -> WindowResult:
        """处理窗口"""
        # 按时间排序数据
        sorted_data = self._sort_by_time(data, config.time_column)
        
        # 根据窗口类型处理
        if config.window_type == WindowType.TUMBLING:
            windows = self._create_tumbling_windows(sorted_data, config)
        elif config.window_type == WindowType.SLIDING:
            windows = self._create_sliding_windows(sorted_data, config)
        elif config.window_type == WindowType.SESSION:
            windows = self._create_session_windows(sorted_data, config)
        else:
            windows = self._create_custom_windows(sorted_data, config)
        
        # 应用聚合
        if aggregation:
            windows = self._apply_aggregation(windows, aggregation)
        
        # 计算统计信息
        statistics = self._calculate_window_statistics(windows)
        
        return WindowResult(
            windows=windows,
            window_count=len(windows),
            total_records=len(data),
            config=config,
            statistics=statistics
        )
    
    def _sort_by_time(self, data: List[Dict[str, Any]], time_column: str) -> List[Dict[str, Any]]:
        """按时间排序数据"""
        def get_timestamp(row):
            timestamp = row.get(time_column)
            if isinstance(timestamp, str):
                try:
                    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    return datetime.min
            elif isinstance(timestamp, datetime):
                return timestamp
            else:
                return datetime.min
        
        return sorted(data, key=get_timestamp)
    
    def _create_tumbling_windows(self, data: List[Dict[str, Any]], config: WindowConfig) -> List[Dict[str, Any]]:
        """创建滚动窗口"""
        windows = []
        
        if not data:
            return windows
        
        # 获取时间范围
        start_time = self._get_timestamp(data[0], config.time_column)
        end_time = self._get_timestamp(data[-1], config.time_column)
        
        # 计算窗口大小（秒）
        window_size_seconds = self._convert_to_seconds(config.size, config.time_unit)
        
        # 创建窗口
        current_window_start = start_time
        window_id = 0
        
        while current_window_start < end_time:
            current_window_end = current_window_start + timedelta(seconds=window_size_seconds)
            
            # 获取窗口内的数据
            window_data = []
            for row in data:
                timestamp = self._get_timestamp(row, config.time_column)
                if current_window_start <= timestamp < current_window_end:
                    window_data.append(row)
            
            if window_data:
                window = {
                    "window_id": window_id,
                    "start_time": current_window_start.isoformat(),
                    "end_time": current_window_end.isoformat(),
                    "data": window_data,
                    "record_count": len(window_data)
                }
                windows.append(window)
                window_id += 1
            
            current_window_start = current_window_end
        
        return windows
    
    def _create_sliding_windows(self, data: List[Dict[str, Any]], config: WindowConfig) -> List[Dict[str, Any]]:
        """创建滑动窗口"""
        windows = []
        
        if not data:
            return windows
        
        # 计算窗口大小和滑动大小（秒）
        window_size_seconds = self._convert_to_seconds(config.size, config.time_unit)
        slide_size_seconds = self._convert_to_seconds(config.slide_size or config.size, config.time_unit)
        
        # 获取时间范围
        start_time = self._get_timestamp(data[0], config.time_column)
        end_time = self._get_timestamp(data[-1], config.time_column)
        
        # 创建滑动窗口
        current_window_start = start_time
        window_id = 0
        
        while current_window_start < end_time:
            current_window_end = current_window_start + timedelta(seconds=window_size_seconds)
            
            # 获取窗口内的数据
            window_data = []
            for row in data:
                timestamp = self._get_timestamp(row, config.time_column)
                if current_window_start <= timestamp < current_window_end:
                    window_data.append(row)
            
            if window_data:
                window = {
                    "window_id": window_id,
                    "start_time": current_window_start.isoformat(),
                    "end_time": current_window_end.isoformat(),
                    "data": window_data,
                    "record_count": len(window_data)
                }
                windows.append(window)
                window_id += 1
            
            current_window_start += timedelta(seconds=slide_size_seconds)
        
        return windows
    
    def _create_session_windows(self, data: List[Dict[str, Any]], config: WindowConfig) -> List[Dict[str, Any]]:
        """创建会话窗口"""
        windows = []
        
        if not data:
            return windows
        
        session_timeout_seconds = config.session_timeout or 1800  # 默认30分钟
        
        current_session = []
        last_timestamp = None
        session_id = 0
        
        for row in data:
            timestamp = self._get_timestamp(row, config.time_column)
            
            if last_timestamp is None:
                # 第一个记录
                current_session.append(row)
                last_timestamp = timestamp
            else:
                # 检查是否超时
                time_diff = (timestamp - last_timestamp).total_seconds()
                
                if time_diff > session_timeout_seconds:
                    # 会话超时，创建新会话
                    if current_session:
                        window = {
                            "window_id": session_id,
                            "start_time": self._get_timestamp(current_session[0], config.time_column).isoformat(),
                            "end_time": last_timestamp.isoformat(),
                            "data": current_session,
                            "record_count": len(current_session),
                            "session_duration": (last_timestamp - self._get_timestamp(current_session[0], config.time_column)).total_seconds()
                        }
                        windows.append(window)
                        session_id += 1
                    
                    current_session = [row]
                else:
                    # 继续当前会话
                    current_session.append(row)
                
                last_timestamp = timestamp
        
        # 处理最后一个会话
        if current_session:
            window = {
                "window_id": session_id,
                "start_time": self._get_timestamp(current_session[0], config.time_column).isoformat(),
                "end_time": last_timestamp.isoformat(),
                "data": current_session,
                "record_count": len(current_session),
                "session_duration": (last_timestamp - self._get_timestamp(current_session[0], config.time_column)).total_seconds()
            }
            windows.append(window)
        
        return windows
    
    def _create_custom_windows(self, data: List[Dict[str, Any]], config: WindowConfig) -> List[Dict[str, Any]]:
        """创建自定义窗口"""
        # 简化实现，使用滚动窗口
        return self._create_tumbling_windows(data, config)
    
    def _apply_aggregation(self, windows: List[Dict[str, Any]], aggregation: Dict[str, str]) -> List[Dict[str, Any]]:
        """应用聚合"""
        aggregated_windows = []
        
        for window in windows:
            window_data = window.get("data", [])
            
            if not window_data:
                aggregated_windows.append(window)
                continue
            
            # 计算聚合值
            aggregated_data = {}
            
            for column, agg_func in aggregation.items():
                values = []
                for row in window_data:
                    if column in row and row[column] is not None:
                        try:
                            values.append(float(row[column]))
                        except (ValueError, TypeError):
                            continue
                
                if values:
                    if agg_func.lower() == "sum":
                        aggregated_data[f"{column}_sum"] = sum(values)
                    elif agg_func.lower() == "avg":
                        aggregated_data[f"{column}_avg"] = sum(values) / len(values)
                    elif agg_func.lower() == "min":
                        aggregated_data[f"{column}_min"] = min(values)
                    elif agg_func.lower() == "max":
                        aggregated_data[f"{column}_max"] = max(values)
                    elif agg_func.lower() == "count":
                        aggregated_data[f"{column}_count"] = len(values)
            
            # 创建聚合后的窗口
            aggregated_window = {
                "window_id": window["window_id"],
                "start_time": window["start_time"],
                "end_time": window["end_time"],
                "record_count": window["record_count"],
                "aggregated_data": aggregated_data
            }
            
            aggregated_windows.append(aggregated_window)
        
        return aggregated_windows
    
    def _calculate_window_statistics(self, windows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算窗口统计信息"""
        if not windows:
            return {}
        
        record_counts = [window.get("record_count", 0) for window in windows]
        
        statistics = {
            "total_windows": len(windows),
            "avg_records_per_window": sum(record_counts) / len(record_counts) if record_counts else 0,
            "min_records_per_window": min(record_counts) if record_counts else 0,
            "max_records_per_window": max(record_counts) if record_counts else 0,
            "empty_windows": len([count for count in record_counts if count == 0])
        }
        
        return statistics
    
    def _get_timestamp(self, row: Dict[str, Any], time_column: str) -> datetime:
        """获取时间戳"""
        timestamp = row.get(time_column)
        
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return datetime.min
        elif isinstance(timestamp, datetime):
            return timestamp
        else:
            return datetime.min
    
    def _convert_to_seconds(self, size: int, time_unit: TimeUnit) -> int:
        """转换为秒"""
        if time_unit == TimeUnit.SECOND:
            return size
        elif time_unit == TimeUnit.MINUTE:
            return size * 60
        elif time_unit == TimeUnit.HOUR:
            return size * 3600
        elif time_unit == TimeUnit.DAY:
            return size * 86400
        elif time_unit == TimeUnit.WEEK:
            return size * 604800
        elif time_unit == TimeUnit.MONTH:
            return size * 2592000  # 30天
        elif time_unit == TimeUnit.YEAR:
            return size * 31536000  # 365天
        else:
            return size


def create_time_window_tool(container: Any) -> TimeWindowTool:
    """
    创建时间窗口工具
    
    Args:
        container: 服务容器
        
    Returns:
        TimeWindowTool 实例
    """
    return TimeWindowTool(container)


# 导出
__all__ = [
    "TimeWindowTool",
    "WindowType",
    "TimeUnit",
    "WindowConfig",
    "WindowResult",
    "create_time_window_tool",
]
