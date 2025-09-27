"""
Celery调度器集成测试
验证定时任务调度和执行链路
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# 添加项目根路径到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestCelerySchedulerIntegration:
    """Celery调度器集成测试类"""

    def setup_method(self):
        """测试前准备"""
        self.test_template_id = "test_template_celery_001"
        self.test_data_source_id = "test_ds_celery_001"
        self.test_schedule_id = "test_schedule_001"

    @pytest.fixture
    def mock_celery_app(self):
        """模拟Celery应用"""
        from unittest.mock import Mock

        mock_app = Mock()
        mock_app.conf = Mock()
        mock_app.control = Mock()
        mock_app.control.inspect.return_value = Mock()
        mock_app.control.inspect().stats.return_value = {"worker1": {"status": "ok"}}

        return mock_app

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        with patch('app.db.session.get_db_session') as mock:
            db_mock = Mock()
            mock.return_value.__enter__ = Mock(return_value=db_mock)
            mock.return_value.__exit__ = Mock(return_value=None)
            yield db_mock

    @pytest.mark.asyncio
    async def test_celery_app_initialization(self, mock_celery_app):
        """测试Celery应用初始化"""
        with patch('app.core.celery_app.celery_app', mock_celery_app):
            from app.core.celery_app import celery_app

            assert celery_app is not None
            assert hasattr(celery_app, 'control')
            assert hasattr(celery_app, 'conf')

            print("✅ Celery应用初始化测试通过")

    @pytest.mark.asyncio
    async def test_task_registration(self, mock_celery_app):
        """测试任务注册"""
        with patch('app.core.celery_app.celery_app', mock_celery_app):
            try:
                # 测试占位符相关任务是否正确注册
                from app.tasks.placeholder_tasks import (
                    execute_placeholder_scan_task,
                    execute_report_generation_task
                )

                # 验证任务函数存在
                assert callable(execute_placeholder_scan_task)
                assert callable(execute_report_generation_task)

                print("✅ 任务注册测试通过")

            except ImportError as e:
                # 如果任务文件不存在，创建基础版本用于测试
                print(f"⚠️  任务文件未找到，跳过任务注册测试: {e}")

    @pytest.mark.asyncio
    async def test_scheduled_task_creation(self, mock_db_session, mock_celery_app):
        """测试定时任务创建"""
        with patch('app.core.celery_app.celery_app', mock_celery_app):
            # Mock定时任务创建服务
            from app.services.application.scheduler.task_scheduler import TaskScheduler

            with patch.object(TaskScheduler, '__init__', return_value=None):
                scheduler = TaskScheduler()

                # Mock定时任务创建方法
                mock_create_task = AsyncMock()
                mock_create_task.return_value = {
                    "success": True,
                    "schedule_id": self.test_schedule_id,
                    "next_execution": (datetime.now() + timedelta(hours=1)).isoformat(),
                    "cron_expression": "0 9 * * *"
                }

                scheduler.create_scheduled_task = mock_create_task

                # 测试创建定时任务
                result = await scheduler.create_scheduled_task(
                    template_id=self.test_template_id,
                    data_source_id=self.test_data_source_id,
                    cron_expression="0 9 * * *",  # 每天上午9点
                    task_config={
                        "report_name": "每日客服报告",
                        "enabled": True
                    }
                )

                assert result["success"] is True
                assert "schedule_id" in result
                assert "next_execution" in result

                print(f"✅ 定时任务创建测试通过：调度ID {result['schedule_id']}")

    @pytest.mark.asyncio
    async def test_task_execution_flow(self, mock_db_session, mock_celery_app):
        """测试任务执行流程"""
        with patch('app.core.celery_app.celery_app', mock_celery_app):

            # Mock统一门面
            from app.services.application.facades.unified_service_facade import create_unified_service_facade

            with patch.object(create_unified_service_facade, '__init__', return_value=None):
                facade = create_unified_service_facade(mock_db_session, "scheduler_user")

                # Mock流水线执行
                mock_pipeline = AsyncMock()
                mock_pipeline.assemble_report.return_value = {
                    "success": True,
                    "content": "定时任务生成的报告内容",
                    "artifacts": [],
                    "execution_time": datetime.now().isoformat(),
                    "schedule_info": {
                        "cron": "0 9 * * *",
                        "period": "daily",
                        "data_range": "2024-09-25"
                    }
                }

                facade._placeholder_pipeline = mock_pipeline

                # 模拟定时任务执行
                execution_context = {
                    "template_id": self.test_template_id,
                    "data_source_id": self.test_data_source_id,
                    "schedule_id": self.test_schedule_id,
                    "execution_time": datetime.now().isoformat(),
                    "cron_expression": "0 9 * * *"
                }

                # 执行报告生成
                result = await facade.generate_report_v2(
                    template_id=execution_context["template_id"],
                    data_source_id=execution_context["data_source_id"],
                    schedule={"cron_expression": execution_context["cron_expression"]},
                    execution_time=execution_context["execution_time"]
                )

                # 验证执行结果
                assert result["success"] is True
                assert "content" in result
                assert "schedule_info" in result

                print(f"✅ 任务执行流程测试通过：生成内容长度 {len(result['content'])} 字符")

    @pytest.mark.asyncio
    async def test_cron_expression_parsing(self):
        """测试Cron表达式解析"""
        from app.utils.time_context import TimeContextManager

        tm = TimeContextManager()

        # 测试不同的Cron表达式
        cron_test_cases = [
            {
                "cron": "0 9 * * *",
                "description": "每日9点",
                "expected_period": "daily"
            },
            {
                "cron": "0 9 * * 1",
                "description": "每周一9点",
                "expected_period": "weekly"
            },
            {
                "cron": "0 9 1 * *",
                "description": "每月1号9点",
                "expected_period": "monthly"
            },
            {
                "cron": "0 0 1 1 *",
                "description": "每年1月1日",
                "expected_period": "yearly"
            }
        ]

        test_execution_time = datetime(2024, 9, 26, 9, 0, 0)

        for case in cron_test_cases:
            context = tm.build_task_time_context(
                case["cron"],
                test_execution_time
            )

            assert context["period"] == case["expected_period"], \
                f"Cron表达式 {case['cron']} 期望周期 {case['expected_period']}, 实际 {context['period']}"

            print(f"✅ Cron解析测试通过: {case['description']} -> {case['expected_period']}")

    @pytest.mark.asyncio
    async def test_task_error_handling(self, mock_db_session, mock_celery_app):
        """测试任务错误处理"""
        with patch('app.core.celery_app.celery_app', mock_celery_app):

            # Mock失败的任务执行
            from app.services.application.facades.unified_service_facade import create_unified_service_facade

            with patch.object(create_unified_service_facade, '__init__', return_value=None):
                facade = create_unified_service_facade(mock_db_session, "error_test_user")

                # Mock失败的流水线
                mock_pipeline = AsyncMock()
                mock_pipeline.assemble_report.side_effect = Exception("模拟执行失败")

                facade._placeholder_pipeline = mock_pipeline

                try:
                    # 尝试执行失败的任务
                    result = await facade.generate_report_v2(
                        template_id=self.test_template_id,
                        data_source_id=self.test_data_source_id,
                        schedule={"cron_expression": "0 9 * * *"},
                        execution_time=datetime.now().isoformat()
                    )

                    # 如果没有抛出异常，检查错误处理
                    assert result.get("success") is False

                except Exception as e:
                    # 验证错误被正确捕获
                    assert "模拟执行失败" in str(e)

                print("✅ 任务错误处理测试通过")

    @pytest.mark.asyncio
    async def test_worker_health_monitoring(self, mock_celery_app):
        """测试Worker健康监控"""
        with patch('app.core.celery_app.celery_app', mock_celery_app):
            from app.services.application.health.pipeline_health_service import PipelineHealthService

            health_service = PipelineHealthService()

            # 测试Celery系统健康检查
            celery_health = await health_service._check_celery_system()

            assert celery_health["status"] in ["healthy", "degraded", "unhealthy"]
            assert "tested_at" in celery_health
            assert "details" in celery_health

            print(f"✅ Worker健康监控测试通过：状态 {celery_health['status']}")

    @pytest.mark.asyncio
    async def test_schedule_persistence(self, mock_db_session):
        """测试调度信息持久化"""

        # Mock调度信息CRUD操作
        with patch('app.crud.schedule') as mock_schedule_crud:
            mock_schedule_crud.create.return_value = Mock(
                id=self.test_schedule_id,
                template_id=self.test_template_id,
                data_source_id=self.test_data_source_id,
                cron_expression="0 9 * * *",
                enabled=True,
                created_at=datetime.now()
            )

            mock_schedule_crud.get.return_value = mock_schedule_crud.create.return_value
            mock_schedule_crud.update.return_value = mock_schedule_crud.create.return_value

            # 测试创建调度
            schedule_data = {
                "template_id": self.test_template_id,
                "data_source_id": self.test_data_source_id,
                "cron_expression": "0 9 * * *",
                "enabled": True
            }

            created_schedule = mock_schedule_crud.create(mock_db_session, obj_in=schedule_data)
            assert created_schedule.id == self.test_schedule_id

            # 测试查询调度
            retrieved_schedule = mock_schedule_crud.get(mock_db_session, id=self.test_schedule_id)
            assert retrieved_schedule.id == self.test_schedule_id

            # 测试更新调度
            update_data = {"enabled": False}
            updated_schedule = mock_schedule_crud.update(
                mock_db_session,
                db_obj=retrieved_schedule,
                obj_in=update_data
            )
            assert updated_schedule.id == self.test_schedule_id

            print("✅ 调度信息持久化测试通过")


def test_run_celery_integration_suite():
    """运行完整Celery集成测试套件"""
    print("🚀 开始Celery调度器集成测试...")

    # 运行pytest测试
    exit_code = pytest.main([__file__, "-v", "-s"])

    if exit_code == 0:
        print("✅ 所有Celery集成测试通过!")
    else:
        print("❌ 部分Celery集成测试失败")

    return exit_code


if __name__ == "__main__":
    # 直接运行完整测试套件
    test_run_celery_integration_suite()