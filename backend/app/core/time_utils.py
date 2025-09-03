"""
统一时间处理工具
确保整个应用使用一致的时区配置
"""
import pytz
from datetime import datetime
from typing import Optional

from .config import settings


# 应用时区设置 - 从配置文件读取
APP_TIMEZONE = pytz.timezone(settings.APP_TIMEZONE)


def now() -> datetime:
    """获取当前应用时区时间"""
    return datetime.now(APP_TIMEZONE)


def utc_now() -> datetime:
    """获取当前UTC时间"""
    return datetime.utcnow().replace(tzinfo=pytz.UTC)


def to_app_timezone(dt: datetime) -> datetime:
    """将datetime转换为应用时区"""
    if dt.tzinfo is None:
        # 假设无时区信息的时间为UTC
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(APP_TIMEZONE)


def to_utc(dt: datetime) -> datetime:
    """将datetime转换为UTC"""
    if dt.tzinfo is None:
        # 假设无时区信息的时间为应用时区
        dt = APP_TIMEZONE.localize(dt)
    return dt.astimezone(pytz.UTC)


def format_iso(dt: Optional[datetime] = None) -> str:
    """格式化为ISO字符串（应用时区）"""
    if dt is None:
        dt = now()
    return dt.isoformat()


def format_utc_iso(dt: Optional[datetime] = None) -> str:
    """格式化为UTC ISO字符串"""
    if dt is None:
        dt = utc_now()
    return dt.isoformat()


def parse_iso(iso_string: str) -> datetime:
    """解析ISO字符串为datetime对象"""
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return to_app_timezone(dt)


def timestamp() -> float:
    """获取当前时间戳"""
    return now().timestamp()


def from_timestamp(ts: float, tz: Optional[pytz.BaseTzInfo] = None) -> datetime:
    """从时间戳创建datetime对象"""
    if tz is None:
        tz = APP_TIMEZONE
    return datetime.fromtimestamp(ts, tz)