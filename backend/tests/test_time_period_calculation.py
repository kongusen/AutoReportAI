"""
时间周期计算测试
验证基于cron表达式和执行时间的周期计算准确性
"""

import pytest
from datetime import datetime
import sys
import os

# 添加项目根路径到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.utils.time_context import TimeContextManager


class TestTimePeriodCalculation:
    """时间周期计算测试类"""

    def setup_method(self):
        """测试前准备"""
        self.tm = TimeContextManager()

    def test_daily_period_calculation(self):
        """测试每日周期计算"""
        # 测试场景：2024年9月26日周四上午9点执行日报
        execution_time = datetime(2024, 9, 26, 9, 0, 0)
        cron_expression = "0 9 * * *"  # 每天9点

        context = self.tm.build_task_time_context(cron_expression, execution_time)

        assert context["period"] == "daily"
        assert context["data_start_time"] == "2024-09-25"  # 昨日
        assert context["data_end_time"] == "2024-09-25"    # 昨日
        assert "每日周期：2024-09-25" in context["period_description"]

    def test_weekly_period_calculation(self):
        """测试每周周期计算（自然周）"""
        # 测试场景：2024年9月26日周四执行周报
        execution_time = datetime(2024, 9, 26, 9, 0, 0)
        cron_expression = "0 9 * * 1"  # 每周一9点

        context = self.tm.build_task_time_context(cron_expression, execution_time)

        assert context["period"] == "weekly"
        # 上周：2024年9月16日(周一) ~ 2024年9月22日(周日)
        assert context["data_start_time"] == "2024-09-16"
        assert context["data_end_time"] == "2024-09-22"
        assert "每周周期：2024-09-16～2024-09-22" in context["period_description"]

    def test_monthly_period_calculation(self):
        """测试每月周期计算"""
        # 测试场景：2024年9月26日执行月报
        execution_time = datetime(2024, 9, 26, 9, 0, 0)
        cron_expression = "0 9 1 * *"  # 每月1号9点

        context = self.tm.build_task_time_context(cron_expression, execution_time)

        assert context["period"] == "monthly"
        # 上月：2024年8月1日 ~ 2024年8月31日
        assert context["data_start_time"] == "2024-08-01"
        assert context["data_end_time"] == "2024-08-31"
        assert "每月周期：2024-08-01～2024-08-31" in context["period_description"]

    def test_yearly_period_calculation(self):
        """测试每年周期计算"""
        # 测试场景：2024年9月26日执行年报
        execution_time = datetime(2024, 9, 26, 9, 0, 0)
        cron_expression = "0 0 1 1 *"  # 每年1月1号

        context = self.tm.build_task_time_context(cron_expression, execution_time)

        assert context["period"] == "yearly"
        # 去年：2023年1月1日 ~ 2023年12月31日
        assert context["data_start_time"] == "2023-01-01"
        assert context["data_end_time"] == "2023-12-31"
        assert "每年周期：2023-01-01～2023-12-31" in context["period_description"]

    def test_edge_cases(self):
        """测试边界情况"""

        # 测试1月份的月报（跨年）
        execution_time = datetime(2024, 1, 15, 9, 0, 0)
        cron_expression = "0 9 1 * *"

        context = self.tm.build_task_time_context(cron_expression, execution_time)
        assert context["period"] == "monthly"
        assert context["data_start_time"] == "2023-12-01"  # 上年12月
        assert context["data_end_time"] == "2023-12-31"

        # 测试周一执行的周报
        execution_time = datetime(2024, 9, 23, 9, 0, 0)  # 2024年9月23日周一
        cron_expression = "0 9 * * 1"

        context = self.tm.build_task_time_context(cron_expression, execution_time)
        assert context["period"] == "weekly"
        # 上周：9月16日(周一) ~ 9月22日(周日)
        assert context["data_start_time"] == "2024-09-16"
        assert context["data_end_time"] == "2024-09-22"

    def test_invalid_cron_fallback(self):
        """测试无效cron表达式的回退"""
        execution_time = datetime(2024, 9, 26, 9, 0, 0)
        invalid_cron = "invalid cron"

        context = self.tm.build_task_time_context(invalid_cron, execution_time)

        # 应该回退到daily
        assert context["period"] == "daily"
        assert context["data_start_time"] == "2024-09-25"

    def test_no_execution_time(self):
        """测试未提供执行时间的情况"""
        cron_expression = "0 9 * * *"

        # 不提供执行时间，应该使用当前时间
        context = self.tm.build_task_time_context(cron_expression, None)

        assert context["period"] == "daily"
        assert "data_start_time" in context
        assert "data_end_time" in context

    def test_period_handler_integration(self):
        """测试与PeriodHandler的集成"""
        from app.services.domain.placeholder.core.handlers.period_handler import PeriodHandler

        handler = PeriodHandler()

        # 测试日报场景
        time_ctx = {
            "cron_expression": "0 9 * * *",
            "execution_time": datetime(2024, 9, 26, 9, 0, 0).isoformat(),
            "schedule": {
                "cron_expression": "0 9 * * *"
            }
        }

        import asyncio
        result = asyncio.run(handler.compute("报告周期", time_ctx))

        assert result["value"] == "2024-09-25"  # 昨日
        assert result["meta"]["period"] == "daily"

        # 测试周报场景
        time_ctx = {
            "cron_expression": "0 9 * * 1",
            "execution_time": datetime(2024, 9, 26, 9, 0, 0).isoformat(),
            "schedule": {
                "cron_expression": "0 9 * * 1"
            }
        }

        result = asyncio.run(handler.compute("报告周期", time_ctx))

        assert result["value"] == "2024-09-16～2024-09-22"  # 上周
        assert result["meta"]["period"] == "weekly"


def test_real_world_scenarios():
    """真实世界场景测试"""
    tm = TimeContextManager()

    # 场景1: 每日客服报告，周四上午9点执行
    execution_time = datetime(2024, 9, 26, 9, 0, 0)
    context = tm.build_task_time_context("0 9 * * *", execution_time)

    print(f"日报场景: {context['period_description']}")
    assert context["data_start_time"] == "2024-09-25"

    # 场景2: 每周销售报告，周一上午9点执行
    execution_time = datetime(2024, 9, 23, 9, 0, 0)  # 周一
    context = tm.build_task_time_context("0 9 * * 1", execution_time)

    print(f"周报场景: {context['period_description']}")
    assert context["data_start_time"] == "2024-09-16"
    assert context["data_end_time"] == "2024-09-22"

    # 场景3: 每月财务报告，每月1号上午9点执行
    execution_time = datetime(2024, 10, 1, 9, 0, 0)  # 10月1日
    context = tm.build_task_time_context("0 9 1 * *", execution_time)

    print(f"月报场景: {context['period_description']}")
    assert context["data_start_time"] == "2024-09-01"
    assert context["data_end_time"] == "2024-09-30"


if __name__ == "__main__":
    # 直接运行测试
    print("开始时间周期计算测试...")

    test_real_world_scenarios()

    # 运行pytest测试
    pytest.main([__file__, "-v"])

    print("时间周期计算测试完成!")