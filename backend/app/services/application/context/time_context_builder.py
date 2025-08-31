"""
时间上下文构建器
将各种时间相关的业务需求转换为标准的TimeContext对象
"""
import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, Tuple, Union, List
from dataclasses import dataclass
from enum import Enum
import calendar
import pytz

from app.services.domain.placeholder.models import TimeContext

logger = logging.getLogger(__name__)

class ReportingPeriod(Enum):
    """报告周期枚举"""
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class TimeGranularity(Enum):
    """时间粒度枚举"""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"

@dataclass
class TimePreferences:
    """时间偏好设置"""
    default_timezone: str = "Asia/Shanghai"
    fiscal_year_start_month: int = 1  # 财年开始月份
    week_start_day: int = 0  # 周开始日 (0=Monday, 6=Sunday)
    business_hours_start: int = 9  # 营业时间开始
    business_hours_end: int = 18  # 营业时间结束
    working_days: List[int] = None  # 工作日 [0-6]
    holiday_calendar: str = "china"  # 节假日日历

    def __post_init__(self):
        if self.working_days is None:
            self.working_days = [0, 1, 2, 3, 4]  # 默认周一到周五

class TimeContextBuilder:
    """时间上下文构建器"""
    
    def __init__(self, preferences: Optional[TimePreferences] = None):
        self.preferences = preferences or TimePreferences()
        self._timezone_cache = {}
        
    def build_from_request(self, 
                          time_range_str: Optional[str] = None,
                          reporting_period: Optional[str] = None,
                          timezone: Optional[str] = None,
                          fiscal_year: Optional[int] = None,
                          custom_params: Optional[Dict[str, Any]] = None) -> TimeContext:
        """
        从请求参数构建时间上下文
        
        Args:
            time_range_str: 时间范围字符串，如 "2024-01", "2024-Q1", "last_3_months"
            reporting_period: 报告周期
            timezone: 时区
            fiscal_year: 财年
            custom_params: 自定义参数
        """
        try:
            # 解析时间范围
            time_range = self._parse_time_range(time_range_str)
            
            # 确定报告周期
            period = self._determine_reporting_period(reporting_period, time_range_str)
            
            # 确定时区
            tz = self._get_timezone(timezone)
            
            # 计算财年
            fiscal_year_start = self._calculate_fiscal_year_start(fiscal_year, time_range)
            
            # 构建时间上下文
            return TimeContext(
                reporting_period=period,
                time_range=time_range,
                timezone=tz,
                fiscal_year_start=fiscal_year_start,
                granularity=self._infer_granularity(time_range_str, period),
                metadata=self._build_metadata(time_range_str, custom_params)
            )
            
        except Exception as e:
            logger.error(f"时间上下文构建失败: {e}")
            return self._create_default_context()
    
    def build_current_month(self, timezone: Optional[str] = None) -> TimeContext:
        """构建当前月份的时间上下文"""
        tz = self._get_timezone(timezone)
        now = datetime.now(tz)
        
        # 当前月份的开始和结束
        month_start = datetime(now.year, now.month, 1, tzinfo=tz)
        if now.month == 12:
            month_end = datetime(now.year + 1, 1, 1, tzinfo=tz) - timedelta(days=1)
        else:
            month_end = datetime(now.year, now.month + 1, 1, tzinfo=tz) - timedelta(days=1)
        
        return TimeContext(
            reporting_period="monthly",
            time_range=(month_start, month_end),
            timezone=tz.zone,
            fiscal_year_start=self._calculate_fiscal_year_start(None, (month_start, month_end)),
            granularity="month",
            metadata={
                'is_current': True,
                'month_name': calendar.month_name[now.month],
                'days_in_month': calendar.monthrange(now.year, now.month)[1]
            }
        )
    
    def build_current_quarter(self, timezone: Optional[str] = None) -> TimeContext:
        """构建当前季度的时间上下文"""
        tz = self._get_timezone(timezone)
        now = datetime.now(tz)
        
        # 计算当前季度
        quarter = (now.month - 1) // 3 + 1
        quarter_start = datetime(now.year, (quarter - 1) * 3 + 1, 1, tzinfo=tz)
        
        if quarter == 4:
            quarter_end = datetime(now.year + 1, 1, 1, tzinfo=tz) - timedelta(days=1)
        else:
            quarter_end = datetime(now.year, quarter * 3 + 1, 1, tzinfo=tz) - timedelta(days=1)
        
        return TimeContext(
            reporting_period="quarterly",
            time_range=(quarter_start, quarter_end),
            timezone=tz.zone,
            fiscal_year_start=self._calculate_fiscal_year_start(None, (quarter_start, quarter_end)),
            granularity="quarter",
            metadata={
                'is_current': True,
                'quarter': quarter,
                'quarter_name': f"{now.year}Q{quarter}"
            }
        )
    
    def build_current_year(self, fiscal: bool = False, timezone: Optional[str] = None) -> TimeContext:
        """构建当前年度的时间上下文"""
        tz = self._get_timezone(timezone)
        now = datetime.now(tz)
        
        if fiscal:
            # 财年
            fiscal_start_month = self.preferences.fiscal_year_start_month
            if now.month >= fiscal_start_month:
                fiscal_year = now.year
            else:
                fiscal_year = now.year - 1
            
            year_start = datetime(fiscal_year, fiscal_start_month, 1, tzinfo=tz)
            year_end = datetime(fiscal_year + 1, fiscal_start_month, 1, tzinfo=tz) - timedelta(days=1)
            
            period = "fiscal_yearly"
            metadata = {
                'is_current': True,
                'is_fiscal': True,
                'fiscal_year': fiscal_year,
                'fiscal_year_name': f"FY{fiscal_year}"
            }
        else:
            # 自然年
            year_start = datetime(now.year, 1, 1, tzinfo=tz)
            year_end = datetime(now.year + 1, 1, 1, tzinfo=tz) - timedelta(days=1)
            
            period = "yearly"
            metadata = {
                'is_current': True,
                'is_fiscal': False,
                'calendar_year': now.year
            }
        
        return TimeContext(
            reporting_period=period,
            time_range=(year_start, year_end),
            timezone=tz.zone,
            fiscal_year_start=year_start,
            granularity="year",
            metadata=metadata
        )
    
    def build_relative_period(self, 
                             period_type: str, 
                             offset: int = 0,
                             timezone: Optional[str] = None) -> TimeContext:
        """
        构建相对时间周期的上下文
        
        Args:
            period_type: 周期类型 ("month", "quarter", "year", "week")
            offset: 偏移量 (0=当前, -1=上一个, 1=下一个)
            timezone: 时区
        """
        tz = self._get_timezone(timezone)
        now = datetime.now(tz)
        
        if period_type == "month":
            # 计算目标月份
            target_month = now.month + offset
            target_year = now.year
            
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            while target_month > 12:
                target_month -= 12
                target_year += 1
            
            start = datetime(target_year, target_month, 1, tzinfo=tz)
            if target_month == 12:
                end = datetime(target_year + 1, 1, 1, tzinfo=tz) - timedelta(days=1)
            else:
                end = datetime(target_year, target_month + 1, 1, tzinfo=tz) - timedelta(days=1)
            
            period = "monthly"
            granularity = "month"
            
        elif period_type == "quarter":
            # 计算目标季度
            current_quarter = (now.month - 1) // 3 + 1
            target_quarter = current_quarter + offset
            target_year = now.year
            
            while target_quarter <= 0:
                target_quarter += 4
                target_year -= 1
            while target_quarter > 4:
                target_quarter -= 4
                target_year += 1
            
            start = datetime(target_year, (target_quarter - 1) * 3 + 1, 1, tzinfo=tz)
            if target_quarter == 4:
                end = datetime(target_year + 1, 1, 1, tzinfo=tz) - timedelta(days=1)
            else:
                end = datetime(target_year, target_quarter * 3 + 1, 1, tzinfo=tz) - timedelta(days=1)
            
            period = "quarterly"
            granularity = "quarter"
            
        elif period_type == "year":
            target_year = now.year + offset
            start = datetime(target_year, 1, 1, tzinfo=tz)
            end = datetime(target_year + 1, 1, 1, tzinfo=tz) - timedelta(days=1)
            
            period = "yearly"
            granularity = "year"
            
        elif period_type == "week":
            # 计算周的开始和结束
            days_since_week_start = (now.weekday() - self.preferences.week_start_day) % 7
            week_start = now - timedelta(days=days_since_week_start)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 应用偏移
            target_week_start = week_start + timedelta(weeks=offset)
            target_week_end = target_week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            start = target_week_start
            end = target_week_end
            
            period = "weekly"
            granularity = "week"
            
        else:
            raise ValueError(f"不支持的周期类型: {period_type}")
        
        return TimeContext(
            reporting_period=period,
            time_range=(start, end),
            timezone=tz.zone,
            fiscal_year_start=self._calculate_fiscal_year_start(None, (start, end)),
            granularity=granularity,
            metadata={
                'is_relative': True,
                'period_type': period_type,
                'offset': offset,
                'is_current': offset == 0
            }
        )
    
    def build_custom_range(self, 
                          start_date: Union[datetime, date, str],
                          end_date: Union[datetime, date, str],
                          timezone: Optional[str] = None,
                          reporting_period: Optional[str] = None) -> TimeContext:
        """构建自定义时间范围的上下文"""
        tz = self._get_timezone(timezone)
        
        # 转换开始和结束时间
        start = self._normalize_datetime(start_date, tz, is_start=True)
        end = self._normalize_datetime(end_date, tz, is_start=False)
        
        # 推断报告周期
        if not reporting_period:
            reporting_period = self._infer_reporting_period(start, end)
        
        # 推断粒度
        granularity = self._infer_granularity_from_range(start, end)
        
        return TimeContext(
            reporting_period=reporting_period,
            time_range=(start, end),
            timezone=tz.zone,
            fiscal_year_start=self._calculate_fiscal_year_start(None, (start, end)),
            granularity=granularity,
            metadata={
                'is_custom': True,
                'duration_days': (end - start).days,
                'start_date': start.strftime('%Y-%m-%d'),
                'end_date': end.strftime('%Y-%m-%d')
            }
        )
    
    def _parse_time_range(self, time_range_str: Optional[str]) -> Optional[Tuple[datetime, datetime]]:
        """解析时间范围字符串"""
        if not time_range_str:
            return None
        
        try:
            tz = self._get_timezone()
            
            # 标准格式解析
            if time_range_str == "current_month":
                return self._get_current_month_range(tz)
            elif time_range_str == "last_month":
                return self._get_last_month_range(tz)
            elif time_range_str == "current_quarter":
                return self._get_current_quarter_range(tz)
            elif time_range_str == "last_quarter":
                return self._get_last_quarter_range(tz)
            elif time_range_str == "current_year":
                return self._get_current_year_range(tz)
            elif time_range_str == "last_year":
                return self._get_last_year_range(tz)
            
            # 相对时间解析
            elif time_range_str.startswith("last_"):
                return self._parse_relative_time(time_range_str, tz)
            elif time_range_str.startswith("recent_"):
                return self._parse_recent_time(time_range_str, tz)
            
            # 具体日期格式解析
            elif "-" in time_range_str:
                return self._parse_date_format(time_range_str, tz)
            
            return None
            
        except Exception as e:
            logger.error(f"时间范围解析失败: {time_range_str}, 错误: {e}")
            return None
    
    def _get_current_month_range(self, tz: pytz.timezone) -> Tuple[datetime, datetime]:
        """获取当前月份范围"""
        now = datetime.now(tz)
        start = datetime(now.year, now.month, 1, tzinfo=tz)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1, tzinfo=tz) - timedelta(days=1)
        else:
            end = datetime(now.year, now.month + 1, 1, tzinfo=tz) - timedelta(days=1)
        return start, end
    
    def _get_last_month_range(self, tz: pytz.timezone) -> Tuple[datetime, datetime]:
        """获取上个月范围"""
        now = datetime.now(tz)
        if now.month == 1:
            start = datetime(now.year - 1, 12, 1, tzinfo=tz)
            end = datetime(now.year, 1, 1, tzinfo=tz) - timedelta(days=1)
        else:
            start = datetime(now.year, now.month - 1, 1, tzinfo=tz)
            end = datetime(now.year, now.month, 1, tzinfo=tz) - timedelta(days=1)
        return start, end
    
    def _determine_reporting_period(self, period_str: Optional[str], time_range_str: Optional[str]) -> str:
        """确定报告周期"""
        if period_str:
            return period_str
        
        if time_range_str:
            if "month" in time_range_str:
                return "monthly"
            elif "quarter" in time_range_str or "Q" in time_range_str:
                return "quarterly"
            elif "year" in time_range_str:
                return "yearly"
            elif "week" in time_range_str:
                return "weekly"
            elif "day" in time_range_str:
                return "daily"
        
        return "custom"
    
    def _get_timezone(self, timezone: Optional[str] = None) -> pytz.timezone:
        """获取时区对象"""
        tz_name = timezone or self.preferences.default_timezone
        
        if tz_name not in self._timezone_cache:
            try:
                self._timezone_cache[tz_name] = pytz.timezone(tz_name)
            except pytz.UnknownTimeZoneError:
                logger.warning(f"未知时区: {tz_name}, 使用默认时区")
                self._timezone_cache[tz_name] = pytz.timezone(self.preferences.default_timezone)
        
        return self._timezone_cache[tz_name]
    
    def _calculate_fiscal_year_start(self, 
                                   fiscal_year: Optional[int], 
                                   time_range: Optional[Tuple[datetime, datetime]]) -> datetime:
        """计算财年开始时间"""
        if fiscal_year:
            tz = self._get_timezone()
            return datetime(fiscal_year, self.preferences.fiscal_year_start_month, 1, tzinfo=tz)
        
        if time_range:
            start_date = time_range[0]
            year = start_date.year
            if start_date.month < self.preferences.fiscal_year_start_month:
                year -= 1
            
            return datetime(year, self.preferences.fiscal_year_start_month, 1, tzinfo=start_date.tzinfo)
        
        # 默认使用当前财年
        tz = self._get_timezone()
        now = datetime.now(tz)
        year = now.year
        if now.month < self.preferences.fiscal_year_start_month:
            year -= 1
        
        return datetime(year, self.preferences.fiscal_year_start_month, 1, tzinfo=tz)
    
    def _infer_granularity(self, time_range_str: Optional[str], period: str) -> str:
        """推断时间粒度"""
        if time_range_str:
            if "hour" in time_range_str or "实时" in time_range_str:
                return "hour"
            elif "day" in time_range_str or "日" in time_range_str:
                return "day"
            elif "week" in time_range_str or "周" in time_range_str:
                return "week"
            elif "month" in time_range_str or "月" in time_range_str:
                return "month"
            elif "quarter" in time_range_str or "季" in time_range_str:
                return "quarter"
            elif "year" in time_range_str or "年" in time_range_str:
                return "year"
        
        # 根据报告周期推断
        period_to_granularity = {
            "real_time": "minute",
            "hourly": "hour",
            "daily": "day",
            "weekly": "week",
            "monthly": "month",
            "quarterly": "quarter",
            "yearly": "year"
        }
        
        return period_to_granularity.get(period, "day")
    
    def _build_metadata(self, time_range_str: Optional[str], custom_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """构建元数据"""
        metadata = {
            'builder_version': '1.0',
            'created_at': datetime.now().isoformat(),
            'preferences': {
                'timezone': self.preferences.default_timezone,
                'fiscal_year_start': self.preferences.fiscal_year_start_month,
                'week_start_day': self.preferences.week_start_day
            }
        }
        
        if time_range_str:
            metadata['original_time_range_str'] = time_range_str
        
        if custom_params:
            metadata['custom_params'] = custom_params
        
        return metadata
    
    def _create_default_context(self) -> TimeContext:
        """创建默认的时间上下文"""
        return self.build_current_month()
    
    def _normalize_datetime(self, 
                           dt: Union[datetime, date, str], 
                           tz: pytz.timezone, 
                           is_start: bool = True) -> datetime:
        """规范化日期时间对象"""
        if isinstance(dt, str):
            # 解析字符串日期
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        elif isinstance(dt, date) and not isinstance(dt, datetime):
            # date转datetime
            if is_start:
                dt = datetime.combine(dt, datetime.min.time())
            else:
                dt = datetime.combine(dt, datetime.max.time())
        
        # 确保有时区信息
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        elif dt.tzinfo != tz:
            dt = dt.astimezone(tz)
        
        return dt
    
    def _infer_reporting_period(self, start: datetime, end: datetime) -> str:
        """根据时间范围推断报告周期"""
        duration = end - start
        
        if duration.days <= 1:
            return "daily"
        elif duration.days <= 7:
            return "weekly"
        elif duration.days <= 31:
            return "monthly"
        elif duration.days <= 93:
            return "quarterly"
        elif duration.days <= 366:
            return "yearly"
        else:
            return "custom"
    
    def _infer_granularity_from_range(self, start: datetime, end: datetime) -> str:
        """根据时间范围推断粒度"""
        duration = end - start
        
        if duration.total_seconds() <= 3600:  # 1小时内
            return "minute"
        elif duration.days <= 1:
            return "hour"
        elif duration.days <= 31:
            return "day"
        elif duration.days <= 93:
            return "week"
        elif duration.days <= 366:
            return "month"
        else:
            return "year"