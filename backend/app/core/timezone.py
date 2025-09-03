"""
时区处理工具
统一处理应用中的时区相关操作，默认使用上海时区
"""

from datetime import datetime, timezone
from typing import Optional
import pytz
from app.core.config import settings

# 设置应用默认时区
SHANGHAI_TZ = pytz.timezone(settings.TIMEZONE)


def get_current_time() -> datetime:
    """获取当前上海时区时间"""
    return datetime.now(SHANGHAI_TZ)


def get_current_utc_time() -> datetime:
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)


def to_shanghai_time(dt: datetime) -> datetime:
    """将datetime转换为上海时区时间"""
    if dt.tzinfo is None:
        # 如果没有时区信息，假设是UTC时间
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(SHANGHAI_TZ)


def to_utc_time(dt: datetime) -> datetime:
    """将datetime转换为UTC时间"""
    if dt.tzinfo is None:
        # 如果没有时区信息，假设是上海时区时间
        dt = SHANGHAI_TZ.localize(dt)
    return dt.astimezone(timezone.utc)


def format_time(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间为字符串，使用上海时区"""
    if dt is None:
        dt = get_current_time()
    else:
        dt = to_shanghai_time(dt)
    return dt.strftime(format_str)


def parse_time(time_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """解析时间字符串为datetime对象，假设为上海时区"""
    dt = datetime.strptime(time_str, format_str)
    return SHANGHAI_TZ.localize(dt)