"""
时间推断服务

基于任务执行时间和cron表达式推断数据处理的基准时间
支持测试验证时的固定时间设置
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple, List
import re
try:
    from croniter import croniter
except ImportError:
    # 如果没有安装croniter，提供基本功能
    croniter = None

logger = logging.getLogger(__name__)


class TimeInferenceService:
    """时间推断服务"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def infer_base_date_from_cron(
        self,
        cron_expression: str,
        task_execution_time: Optional[datetime] = None,
        timezone_offset: int = 8
    ) -> Dict[str, Any]:
        """
        基于cron表达式和任务执行时间推断基准日期

        Args:
            cron_expression: cron表达式
            task_execution_time: 任务执行时间（None时使用当前时间）
            timezone_offset: 时区偏移小时数

        Returns:
            推断结果
        """
        try:
            if task_execution_time is None:
                task_execution_time = datetime.now()

            # 确保时间是timezone-aware
            if task_execution_time.tzinfo is None:
                task_execution_time = task_execution_time.replace(
                    tzinfo=timezone(timedelta(hours=timezone_offset))
                )

            # 解析cron表达式
            cron_info = self._parse_cron_expression(cron_expression)

            # 推断数据基准日期
            base_date_logic = self._infer_data_period_logic(cron_info, task_execution_time)

            # 计算具体的基准日期
            base_date = self._calculate_base_date(base_date_logic, task_execution_time)

            result = {
                "base_date": base_date.strftime('%Y-%m-%d'),
                "base_date_obj": base_date,
                "task_execution_time": task_execution_time,
                "cron_info": cron_info,
                "data_period_logic": base_date_logic,
                "inference_confidence": self._calculate_confidence(cron_info),
                "explanation": self._generate_explanation(cron_info, base_date_logic, base_date)
            }

            self.logger.info(f"✅ 时间推断完成: {result['base_date']} (置信度: {result['inference_confidence']})")
            return result

        except Exception as e:
            self.logger.error(f"❌ 时间推断失败: {e}")
            raise

    def get_test_validation_date(
        self,
        fixed_date: Optional[str] = None,
        days_offset: int = -1
    ) -> Dict[str, Any]:
        """
        获取测试验证时使用的固定日期

        Args:
            fixed_date: 指定的固定日期 YYYY-MM-DD，None时使用当前时间+偏移
            days_offset: 相对当前时间的天数偏移（负数表示过去）

        Returns:
            测试验证时间信息
        """
        try:
            if fixed_date:
                base_date = datetime.strptime(fixed_date, '%Y-%m-%d')
                source = "指定日期"
            else:
                base_date = datetime.now() + timedelta(days=days_offset)
                source = f"当前时间{days_offset:+d}天"

            result = {
                "base_date": base_date.strftime('%Y-%m-%d'),
                "base_date_obj": base_date,
                "source": source,
                "is_test_mode": True,
                "data_period": "daily",  # 测试时固定为日周期
                "explanation": f"测试验证模式: 使用{source}作为数据基准日期，便于核查数据正确性"
            }

            self.logger.info(f"📅 测试验证日期: {result['base_date']} ({source})")
            return result

        except Exception as e:
            self.logger.error(f"❌ 获取测试验证日期失败: {e}")
            raise

    def _parse_cron_expression(self, cron_expression: str) -> Dict[str, Any]:
        """解析cron表达式"""
        try:
            # 标准cron格式：分 时 日 月 周
            parts = cron_expression.strip().split()

            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression format: {cron_expression}")

            minute, hour, day, month, weekday = parts

            # 解析各个字段
            parsed = {
                "minute": self._parse_cron_field(minute, "minute"),
                "hour": self._parse_cron_field(hour, "hour"),
                "day": self._parse_cron_field(day, "day"),
                "month": self._parse_cron_field(month, "month"),
                "weekday": self._parse_cron_field(weekday, "weekday"),
                "raw_expression": cron_expression
            }

            # 推断执行频率
            parsed["frequency"] = self._infer_frequency(parsed)

            return parsed

        except Exception as e:
            self.logger.error(f"❌ 解析cron表达式失败: {e}")
            raise

    def _parse_cron_field(self, field: str, field_type: str) -> Dict[str, Any]:
        """解析cron字段"""
        result = {
            "raw": field,
            "type": field_type,
            "is_wildcard": field == "*",
            "is_fixed": field.isdigit(),
            "values": [],
            "range": None,
            "step": None
        }

        if field == "*":
            result["pattern"] = "any"
        elif field.isdigit():
            result["pattern"] = "fixed"
            result["values"] = [int(field)]
        elif "/" in field:
            result["pattern"] = "step"
            base, step = field.split("/")
            result["step"] = int(step)
            if base == "*":
                result["base"] = "any"
            else:
                result["base"] = int(base)
        elif "-" in field:
            result["pattern"] = "range"
            start, end = field.split("-")
            result["range"] = (int(start), int(end))
        elif "," in field:
            result["pattern"] = "list"
            result["values"] = [int(x) for x in field.split(",")]
        else:
            result["pattern"] = "unknown"

        return result

    def _infer_frequency(self, parsed_cron: Dict[str, Any]) -> str:
        """推断执行频率"""
        minute = parsed_cron["minute"]
        hour = parsed_cron["hour"]
        day = parsed_cron["day"]
        month = parsed_cron["month"]
        weekday = parsed_cron["weekday"]

        # 每分钟
        if all(field["is_wildcard"] for field in [hour, day, month, weekday]):
            return "minutely"

        # 每小时
        elif all(field["is_wildcard"] for field in [day, month, weekday]) and minute["is_fixed"]:
            return "hourly"

        # 每天
        elif all(field["is_wildcard"] for field in [day, month, weekday]) and hour["is_fixed"] and minute["is_fixed"]:
            return "daily"

        # 每周
        elif day["is_wildcard"] and month["is_wildcard"] and weekday["is_fixed"] and hour["is_fixed"]:
            return "weekly"

        # 每月
        elif day["is_fixed"] and month["is_wildcard"] and weekday["is_wildcard"] and hour["is_fixed"]:
            return "monthly"

        # 每年
        elif day["is_fixed"] and month["is_fixed"] and weekday["is_wildcard"] and hour["is_fixed"]:
            return "yearly"

        else:
            return "custom"

    def _infer_data_period_logic(self, cron_info: Dict[str, Any], execution_time: datetime) -> Dict[str, Any]:
        """推断数据周期逻辑"""
        frequency = cron_info["frequency"]

        if frequency == "daily":
            # 每日任务通常处理前一天的数据
            return {
                "period_type": "daily",
                "data_lag_days": -1,
                "explanation": "每日任务，处理前一天数据"
            }
        elif frequency == "weekly":
            # 每周任务处理上一周的数据
            return {
                "period_type": "weekly",
                "data_lag_days": -7,
                "explanation": "每周任务，处理上周数据"
            }
        elif frequency == "monthly":
            # 每月任务处理上个月的数据
            return {
                "period_type": "monthly",
                "data_lag_days": -30,  # 简化处理
                "explanation": "每月任务，处理上月数据"
            }
        elif frequency == "hourly":
            # 每小时任务处理当前小时或前一小时数据
            return {
                "period_type": "hourly",
                "data_lag_days": 0,
                "explanation": "每小时任务，处理当前时段数据"
            }
        else:
            # 默认处理前一天数据
            return {
                "period_type": "daily",
                "data_lag_days": -1,
                "explanation": "自定义频率，默认处理前一天数据"
            }

    def _calculate_base_date(self, base_date_logic: Dict[str, Any], execution_time: datetime) -> datetime:
        """计算基准日期"""
        lag_days = base_date_logic["data_lag_days"]

        if base_date_logic["period_type"] == "weekly":
            # 周任务：找到上周的同一天
            return execution_time + timedelta(days=lag_days)
        elif base_date_logic["period_type"] == "monthly":
            # 月任务：找到上个月的同一天（简化处理）
            return execution_time + timedelta(days=lag_days)
        else:
            # 日任务和其他：简单的日期偏移
            return execution_time + timedelta(days=lag_days)

    def _calculate_confidence(self, cron_info: Dict[str, Any]) -> float:
        """计算推断置信度"""
        frequency = cron_info["frequency"]

        confidence_map = {
            "daily": 0.95,    # 日任务模式很明确
            "weekly": 0.90,   # 周任务较明确
            "monthly": 0.85,  # 月任务相对明确
            "hourly": 0.80,   # 小时任务可能需要实时数据
            "custom": 0.60    # 自定义频率不确定性较高
        }

        return confidence_map.get(frequency, 0.50)

    def _generate_explanation(
        self,
        cron_info: Dict[str, Any],
        base_date_logic: Dict[str, Any],
        base_date: datetime
    ) -> str:
        """生成推断解释"""
        frequency = cron_info["frequency"]
        cron_expr = cron_info["raw_expression"]
        period_explanation = base_date_logic["explanation"]

        return (
            f"根据cron表达式 '{cron_expr}' 推断为{frequency}任务，"
            f"{period_explanation}，计算出数据基准日期为 {base_date.strftime('%Y-%m-%d')}"
        )

    def get_next_execution_times(
        self,
        cron_expression: str,
        count: int = 5,
        base_time: Optional[datetime] = None
    ) -> List[datetime]:
        """
        获取下次执行时间列表

        Args:
            cron_expression: cron表达式
            count: 返回的执行时间数量
            base_time: 基准时间

        Returns:
            执行时间列表
        """
        try:
            if base_time is None:
                base_time = datetime.now()

            cron = croniter(cron_expression, base_time)
            execution_times = []

            for _ in range(count):
                next_time = cron.get_next(datetime)
                execution_times.append(next_time)

            return execution_times

        except Exception as e:
            self.logger.error(f"❌ 获取执行时间失败: {e}")
            raise

    def simulate_task_execution(
        self,
        cron_expression: str,
        simulation_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        模拟任务执行，用于验证时间推断逻辑

        Args:
            cron_expression: cron表达式
            simulation_days: 模拟天数

        Returns:
            模拟执行结果列表
        """
        try:
            base_time = datetime.now()
            end_time = base_time + timedelta(days=simulation_days)

            cron = croniter(cron_expression, base_time)
            simulations = []

            while True:
                next_execution = cron.get_next(datetime)
                if next_execution > end_time:
                    break

                # 为每次执行推断基准日期
                inference_result = self.infer_base_date_from_cron(
                    cron_expression,
                    next_execution
                )

                simulations.append({
                    "execution_time": next_execution,
                    "base_date": inference_result["base_date"],
                    "explanation": inference_result["explanation"]
                })

            self.logger.info(f"✅ 模拟了 {len(simulations)} 次任务执行")
            return simulations

        except Exception as e:
            self.logger.error(f"❌ 模拟任务执行失败: {e}")
            raise


# 全局服务实例
time_inference_service = TimeInferenceService()