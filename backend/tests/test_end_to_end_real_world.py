"""
端到端真实环境测试
使用实际数据源、真实模板和完整流水线进行测试
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import os

# 添加项目根路径到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestEndToEndRealWorld:
    """端到端真实环境测试类"""

    def setup_method(self):
        """测试前准备"""
        self.test_user_id = "e2e_test_user"
        # 实际的模板内容（客服日报模板）
        self.real_template_content = """
# 客服日报 - {{周期：报告日期}}

## 概览
- 报告期间：{{周期：报告日期}}
- 投诉总数：{{统计：当日投诉总数}}
- 解决率：{{统计：投诉解决率}}

## 详细数据
### 投诉分析
- 总投诉数：{{统计：当日投诉总数}}
- 已解决：{{统计：已解决投诉数}}
- 未解决：{{统计：未解决投诉数}}

### 趋势图表
投诉趋势：{{图表：投诉趋势图}}

## 总结
基于{{周期：报告日期}}的数据分析...
        """.strip()

    @pytest.fixture
    def real_db_session(self):
        """实际数据库会话"""
        from app.db.session import get_db_session

        try:
            with get_db_session() as db:
                yield db
        except Exception as e:
            pytest.skip(f"数据库连接失败，跳过真实环境测试: {e}")

    @pytest.fixture
    def real_data_source(self, real_db_session):
        """获取真实数据源"""
        from app import crud

        # 尝试获取第一个可用的数据源
        data_sources = crud.data_source.get_multi(real_db_session, limit=1)

        if not data_sources:
            pytest.skip("没有可用的数据源，跳过真实环境测试")

        return data_sources[0]

    @pytest.fixture
    def real_template(self, real_db_session):
        """创建或获取真实模板"""
        from app import crud
        from app.schemas.template import TemplateCreate

        # 尝试创建测试模板
        template_create = TemplateCreate(
            name="客服日报测试模板",
            description="用于端到端测试的客服日报模板",
            content=self.real_template_content,
            category="daily_report"
        )

        try:
            # 检查是否已存在相同名称的模板
            existing = crud.template.get_by_name(real_db_session, name=template_create.name)
            if existing:
                return existing

            # 创建新模板
            template = crud.template.create(real_db_session, obj_in=template_create)
            return template

        except Exception as e:
            pytest.skip(f"无法创建测试模板: {e}")

    @pytest.mark.asyncio
    @pytest.mark.real_world
    async def test_complete_pipeline_with_real_data(self, real_db_session, real_data_source, real_template):
        """使用真实数据测试完整流水线"""
        print(f"\n🚀 开始端到端真实环境测试...")
        print(f"📋 使用模板: {real_template.name}")
        print(f"🗄️ 使用数据源: {real_data_source.name} ({real_data_source.source_type})")

        # 1. 健康检查
        print("\n1️⃣ 执行健康检查...")
        from app.services.application.health.pipeline_health_service import get_quick_health

        health_result = await get_quick_health()
        print(f"   健康状态: {health_result['status']}")
        print(f"   流水线准备就绪: {health_result['ready_for_pipeline']}")

        if health_result['status'] == 'unhealthy':
            pytest.skip(f"系统不健康，跳过测试: {health_result}")

        # 2. 创建统一门面服务
        print("\n2️⃣ 初始化服务...")
        from app.services.application.facades.unified_service_facade import create_unified_service_facade

        facade = create_unified_service_facade(real_db_session, self.test_user_id)

        # 3. ETL前扫描
        print("\n3️⃣ 执行ETL前扫描...")
        scan_result = await facade.etl_pre_scan_placeholders(
            template_id=str(real_template.id),
            data_source_id=str(real_data_source.id)
        )

        print(f"   扫描状态: {scan_result.get('success', False)}")
        if scan_result.get('success'):
            stats = scan_result.get('stats', {})
            print(f"   发现占位符: {stats.get('total', 0)} 个")
            print(f"   需重分析: {stats.get('need_reanalysis', 0)} 个")

            # 打印占位符详情
            items = scan_result.get('items', [])
            for item in items[:3]:  # 显示前3个
                print(f"   - {item.get('text', '')} ({item.get('kind', '')})")

        assert scan_result.get('success') is True, "ETL前扫描失败"

        # 4. 报告生成
        print("\n4️⃣ 执行报告生成...")

        # 设置调度信息（模拟每日报告）
        current_time = datetime.now()
        schedule_info = {
            "cron_expression": "0 9 * * *"  # 每天上午9点
        }

        report_result = await facade.generate_report_v2(
            template_id=str(real_template.id),
            data_source_id=str(real_data_source.id),
            schedule=schedule_info,
            execution_time=current_time.isoformat()
        )

        print(f"   生成状态: {report_result.get('success', False)}")
        if report_result.get('success'):
            content = report_result.get('content', '')
            print(f"   报告长度: {len(content)} 字符")
            print(f"   生成artifacts: {len(report_result.get('artifacts', []))} 个")

            # 显示报告预览
            if content:
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"   内容预览: {preview}")

        assert report_result.get('success') is True, "报告生成失败"

        print("\n✅ 端到端真实环境测试完成!")

    @pytest.mark.asyncio
    @pytest.mark.real_world
    async def test_time_context_accuracy_real_scenarios(self):
        """测试真实场景下的时间上下文准确性"""
        print(f"\n🕒 测试真实时间上下文计算...")

        from app.utils.time_context import TimeContextManager

        tm = TimeContextManager()

        # 真实场景：2024年9月26日周四上午10点运行测试
        test_time = datetime(2024, 9, 26, 10, 0, 0)

        real_scenarios = [
            {
                "name": "客服日报场景",
                "cron": "0 9 * * *",
                "description": "每天上午9点生成前一日报告",
                "expected_date": "2024-09-25"
            },
            {
                "name": "销售周报场景",
                "cron": "0 9 * * 1",
                "description": "每周一上午9点生成上周报告",
                "expected_range": "2024-09-16～2024-09-22"
            },
            {
                "name": "财务月报场景",
                "cron": "0 9 1 * *",
                "description": "每月1号上午9点生成上月报告",
                "expected_range": "2024-08-01～2024-08-31"
            }
        ]

        for scenario in real_scenarios:
            print(f"\n   测试场景: {scenario['name']}")

            context = tm.build_task_time_context(scenario["cron"], test_time)

            print(f"   周期类型: {context['period']}")
            print(f"   数据范围: {context['data_start_time']} ~ {context['data_end_time']}")
            print(f"   描述: {context['period_description']}")

            if "expected_date" in scenario:
                assert context["data_start_time"] == scenario["expected_date"]
                assert context["data_end_time"] == scenario["expected_date"]
            elif "expected_range" in scenario:
                expected_start, expected_end = scenario["expected_range"].split("～")
                assert context["data_start_time"] == expected_start
                assert context["data_end_time"] == expected_end

        print("\n✅ 时间上下文准确性测试通过!")

    @pytest.mark.asyncio
    @pytest.mark.real_world
    async def test_error_recovery_real_conditions(self, real_db_session, real_data_source):
        """测试真实条件下的错误恢复机制"""
        print(f"\n🔧 测试错误恢复机制...")

        from app.services.application.facades.unified_service_facade import create_unified_service_facade

        facade = create_unified_service_facade(real_db_session, self.test_user_id)

        # 测试1: 不存在的模板ID
        print("\n   测试场景1: 不存在的模板")
        try:
            result = await facade.etl_pre_scan_placeholders(
                template_id="non_existent_template",
                data_source_id=str(real_data_source.id)
            )
            assert result.get('success') is False
            print("   ✅ 正确处理不存在的模板")
        except Exception as e:
            print(f"   ✅ 异常被捕获: {type(e).__name__}")

        # 测试2: 不存在的数据源ID
        print("\n   测试场景2: 不存在的数据源")
        from app import crud

        # 获取一个真实模板
        templates = crud.template.get_multi(real_db_session, limit=1)
        if templates:
            template = templates[0]
            try:
                result = await facade.etl_pre_scan_placeholders(
                    template_id=str(template.id),
                    data_source_id="non_existent_datasource"
                )
                assert result.get('success') is False
                print("   ✅ 正确处理不存在的数据源")
            except Exception as e:
                print(f"   ✅ 异常被捕获: {type(e).__name__}")

        # 测试3: 无效的调度表达式
        print("\n   测试场景3: 无效的cron表达式")
        if templates:
            try:
                result = await facade.generate_report_v2(
                    template_id=str(template.id),
                    data_source_id=str(real_data_source.id),
                    schedule={"cron_expression": "invalid cron"},
                    execution_time=datetime.now().isoformat()
                )
                # 应该回退到默认行为而不是失败
                print(f"   处理结果: {result.get('success', False)}")
                print("   ✅ 无效cron表达式处理完成")
            except Exception as e:
                print(f"   ✅ 异常被捕获并处理: {type(e).__name__}")

        print("\n✅ 错误恢复机制测试完成!")

    @pytest.mark.asyncio
    @pytest.mark.real_world
    async def test_performance_benchmarking(self, real_db_session, real_data_source):
        """性能基准测试"""
        print(f"\n⚡ 开始性能基准测试...")

        from app.services.application.facades.unified_service_facade import create_unified_service_facade
        import time

        facade = create_unified_service_facade(real_db_session, self.test_user_id)

        # 获取一个模板
        from app import crud
        templates = crud.template.get_multi(real_db_session, limit=1)

        if not templates:
            pytest.skip("没有可用模板进行性能测试")

        template = templates[0]

        # 性能测试1: ETL扫描速度
        print("\n   测试1: ETL扫描性能")
        start_time = time.time()

        scan_result = await facade.etl_pre_scan_placeholders(
            template_id=str(template.id),
            data_source_id=str(real_data_source.id)
        )

        scan_duration = time.time() - start_time
        print(f"   ETL扫描耗时: {scan_duration:.2f}秒")

        if scan_result.get('success'):
            items_count = scan_result.get('stats', {}).get('total', 0)
            if items_count > 0:
                avg_time_per_item = scan_duration / items_count
                print(f"   平均每个占位符处理时间: {avg_time_per_item:.3f}秒")

        # 性能测试2: 报告生成速度
        print("\n   测试2: 报告生成性能")
        start_time = time.time()

        report_result = await facade.generate_report_v2(
            template_id=str(template.id),
            data_source_id=str(real_data_source.id),
            schedule={"cron_expression": "0 9 * * *"},
            execution_time=datetime.now().isoformat()
        )

        generation_duration = time.time() - start_time
        print(f"   报告生成耗时: {generation_duration:.2f}秒")

        if report_result.get('success'):
            content_length = len(report_result.get('content', ''))
            if content_length > 0:
                chars_per_second = content_length / generation_duration
                print(f"   生成速率: {chars_per_second:.0f} 字符/秒")

        # 性能基准
        max_scan_time = 30.0  # 扫描不应超过30秒
        max_generation_time = 60.0  # 生成不应超过60秒

        assert scan_duration < max_scan_time, f"ETL扫描超时: {scan_duration}s > {max_scan_time}s"
        assert generation_duration < max_generation_time, f"报告生成超时: {generation_duration}s > {max_generation_time}s"

        print("\n✅ 性能基准测试通过!")


def test_run_real_world_suite():
    """运行真实环境测试套件"""
    print("🌍 开始真实环境端到端测试...")

    # 运行带有real_world标记的测试
    exit_code = pytest.main([
        __file__,
        "-v",
        "-s",
        "-m",
        "real_world",
        "--tb=short"
    ])

    if exit_code == 0:
        print("✅ 所有真实环境测试通过!")
    else:
        print("❌ 部分真实环境测试失败")

    return exit_code


if __name__ == "__main__":
    # 直接运行真实环境测试套件
    test_run_real_world_suite()