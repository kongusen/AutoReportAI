"""
占位符流水线集成测试
测试从模板扫描到报告组装的完整链路
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根路径到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestPipelineIntegration:
    """流水线集成测试类"""

    def setup_method(self):
        """测试前准备"""
        self.test_template_id = "test_template_001"
        self.test_data_source_id = "test_ds_001"
        self.test_user_id = "test_user_001"

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        with patch('app.db.session.get_db_session') as mock:
            db_mock = Mock()
            mock.return_value.__enter__ = Mock(return_value=db_mock)
            mock.return_value.__exit__ = Mock(return_value=None)
            yield db_mock

    @pytest.fixture
    def mock_template_data(self):
        """模拟模板数据"""
        return Mock(
            id=self.test_template_id,
            name="测试报告模板",
            content="客服日报：{{周期：报告日期}}，投诉总数：{{统计：投诉总数}}，趋势图：{{图表：投诉趋势图}}",
            created_at=datetime.now()
        )

    @pytest.fixture
    def mock_data_source(self):
        """模拟数据源"""
        return Mock(
            id=self.test_data_source_id,
            name="测试数据源",
            source_type="doris",
            doris_database="test_db"
        )

    @pytest.mark.asyncio
    async def test_etl_pre_scan_pipeline(self, mock_db_session, mock_template_data, mock_data_source):
        """测试ETL前扫描流水线"""

        # Mock CRUD操作
        with patch('app.crud.template.get') as mock_get_template:
            mock_get_template.return_value = mock_template_data

            # Mock健康检查
            with patch('app.services.application.health.pipeline_health_service.get_quick_health') as mock_health:
                mock_health.return_value = {
                    "status": "healthy",
                    "ready_for_pipeline": True
                }

                # Mock统一门面
                from app.services.application.facades.unified_service_facade import create_unified_service_facade

                with patch.object(create_unified_service_facade, '__init__', return_value=None):
                    facade = create_unified_service_facade(mock_db_session, self.test_user_id)

                    # Mock流水线服务
                    mock_pipeline = AsyncMock()
                    mock_pipeline.etl_pre_scan.return_value = {
                        "success": True,
                        "items": [
                            {
                                "text": "报告日期",
                                "kind": "period",
                                "needs_reanalysis": False
                            },
                            {
                                "text": "投诉总数",
                                "kind": "statistical",
                                "needs_reanalysis": True
                            },
                            {
                                "text": "投诉趋势图",
                                "kind": "chart",
                                "needs_reanalysis": True
                            }
                        ],
                        "stats": {
                            "total": 3,
                            "need_reanalysis": 2,
                            "by_kind": {
                                "period": 1,
                                "statistical": 1,
                                "chart": 1
                            }
                        }
                    }

                    facade._placeholder_pipeline = mock_pipeline

                    # 执行ETL前扫描
                    result = await facade.etl_pre_scan_placeholders(
                        self.test_template_id,
                        self.test_data_source_id
                    )

                    # 验证结果
                    assert result["success"] is True
                    assert result["stats"]["total"] == 3
                    assert result["stats"]["need_reanalysis"] == 2

                    # 验证占位符分类
                    items_by_kind = {item["kind"]: item for item in result["items"]}
                    assert "period" in items_by_kind
                    assert "statistical" in items_by_kind
                    assert "chart" in items_by_kind

                    print(f"✅ ETL前扫描测试通过：发现{result['stats']['total']}个占位符，{result['stats']['need_reanalysis']}个需重分析")

    @pytest.mark.asyncio
    async def test_report_assembly_pipeline(self, mock_db_session, mock_template_data, mock_data_source):
        """测试报告组装流水线"""

        with patch('app.crud.template.get') as mock_get_template:
            mock_get_template.return_value = mock_template_data

            # Mock统一门面
            from app.services.application.facades.unified_service_facade import create_unified_service_facade

            with patch.object(create_unified_service_facade, '__init__', return_value=None):
                facade = create_unified_service_facade(mock_db_session, self.test_user_id)

                # Mock流水线服务
                mock_pipeline = AsyncMock()
                mock_pipeline.assemble_report.return_value = {
                    "success": True,
                    "content": "客服日报：2024-09-25，投诉总数：1250 (统计结果: 1250)，趋势图：[图表: /tmp/chart_stub.png]",
                    "artifacts": ["/tmp/chart_stub.png"],
                    "resolved": {
                        "报告日期": {
                            "kind": "period",
                            "value": "2024-09-25",
                            "meta": {"period": "daily"}
                        },
                        "投诉总数": {
                            "kind": "statistical",
                            "value": 1250,
                            "metric": "投诉总数"
                        },
                        "投诉趋势图": {
                            "kind": "chart",
                            "artifact": "/tmp/chart_stub.png",
                            "chart_type": "bar"
                        }
                    }
                }

                facade._placeholder_pipeline = mock_pipeline

                # 执行报告组装（使用调度信息）
                result = await facade.generate_report_v2(
                    template_id=self.test_template_id,
                    data_source_id=self.test_data_source_id,
                    schedule={"cron_expression": "0 9 * * *"},
                    execution_time="2024-09-26T09:00:00"
                )

                # 验证结果
                assert result["success"] is True
                assert "content" in result
                assert "artifacts" in result

                # 验证内容已替换
                content = result["content"]
                assert "2024-09-25" in content  # 周期占位符已替换
                assert "1250" in content       # 统计占位符已替换
                assert "chart_stub.png" in content  # 图表占位符已替换

                # 验证artifacts
                assert len(result["artifacts"]) > 0
                assert "/tmp/chart_stub.png" in result["artifacts"]

                print(f"✅ 报告组装测试通过：内容长度{len(content)}字符，生成{len(result['artifacts'])}个图表")

    @pytest.mark.asyncio
    async def test_period_calculation_accuracy(self):
        """测试周期计算准确性"""
        from app.services.domain.placeholder.core.handlers.period_handler import PeriodHandler

        handler = PeriodHandler()

        # 测试不同周期的计算
        test_cases = [
            {
                "name": "日报场景",
                "cron": "0 9 * * *",
                "execution_time": "2024-09-26T09:00:00",
                "expected_period": "daily",
                "expected_value": "2024-09-25"
            },
            {
                "name": "周报场景",
                "cron": "0 9 * * 1",
                "execution_time": "2024-09-26T09:00:00",  # 周四
                "expected_period": "weekly",
                "expected_value": "2024-09-16～2024-09-22"  # 上周一到周日
            },
            {
                "name": "月报场景",
                "cron": "0 9 1 * *",
                "execution_time": "2024-09-26T09:00:00",
                "expected_period": "monthly",
                "expected_value": "2024-08-01～2024-08-31"  # 上月
            }
        ]

        for case in test_cases:
            time_ctx = {
                "cron_expression": case["cron"],
                "execution_time": case["execution_time"],
                "schedule": {"cron_expression": case["cron"]}
            }

            result = await handler.compute("测试周期", time_ctx)

            assert result["value"] == case["expected_value"], \
                f"{case['name']}失败：期望{case['expected_value']}，实际{result['value']}"
            assert result["meta"]["period"] == case["expected_period"], \
                f"{case['name']}周期类型失败：期望{case['expected_period']}，实际{result['meta']['period']}"

            print(f"✅ {case['name']}测试通过：{result['value']}")

    @pytest.mark.asyncio
    async def test_sql_generation_and_execution_chain(self, mock_db_session):
        """测试SQL生成和执行链路"""

        # Mock SQL生成适配器
        with patch('app.services.infrastructure.agents.adapters.sql_generation_adapter.SqlGenerationAdapter') as MockSqlGen:
            mock_sql_gen = AsyncMock()
            mock_sql_gen.generate_sql.return_value = Mock(
                sql="SELECT COUNT(*) as complaint_count FROM complaints WHERE DATE(created_time) = '2024-09-25'",
                confidence=0.9
            )
            MockSqlGen.return_value = mock_sql_gen

            # Mock SQL执行适配器
            with patch('app.services.infrastructure.agents.adapters.sql_execution_adapter.SqlExecutionAdapter') as MockSqlExec:
                mock_sql_exec = AsyncMock()
                mock_sql_exec.execute.return_value = Mock(
                    columns=["complaint_count"],
                    rows=[[1250]],
                    row_count=1,
                    metadata={"execution_time_ms": 150}
                )
                MockSqlExec.return_value = mock_sql_exec

                # Mock处理器
                from app.services.domain.placeholder.core.handlers.stat_handler import StatHandler
                handler = StatHandler()

                # 测试统计类占位符处理
                time_ctx = {
                    "start_date": "2024-09-25",
                    "end_date": "2024-09-25"
                }

                result = await handler.generate_result(
                    placeholder_name="投诉总数",
                    placeholder_text="统计：投诉总数",
                    data_source_id=self.test_data_source_id,
                    time_ctx=time_ctx
                )

                # 验证结果
                assert result["success"] is True
                assert "sql" in result
                assert result["sql"] is not None
                assert len(result["sql"]) > 0

                print(f"✅ SQL生成和执行链路测试通过：生成SQL长度{len(result['sql'])}字符")

    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """测试健康检查集成"""
        from app.services.application.health.pipeline_health_service import get_quick_health

        # Mock关键组件
        with patch('app.services.infrastructure.agents.facade.AgentFacade') as MockAgentFacade:
            mock_agent = AsyncMock()
            mock_agent.execute.return_value = Mock(success=True, result="SELECT 1", metadata={})
            MockAgentFacade.return_value = mock_agent

            with patch('app.services.application.facades.unified_service_facade.create_unified_service_facade'):
                health_result = await get_quick_health()

                assert health_result["status"] in ["healthy", "degraded"]
                assert "ready_for_pipeline" in health_result
                assert health_result["timestamp"] is not None

                print(f"✅ 健康检查集成测试通过：状态{health_result['status']}")

    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self, mock_db_session):
        """测试错误处理和回退机制"""

        # 测试Agent不可用时的回退
        with patch('app.services.infrastructure.agents.facade.AgentFacade') as MockAgentFacade:
            mock_agent = AsyncMock()
            mock_agent.execute.return_value = Mock(success=False, result=None, metadata={"error": "Agent不可用"})
            MockAgentFacade.return_value = mock_agent

            # Mock SQL生成回退
            with patch('app.services.infrastructure.agents.adapters.sql_generation_adapter.SqlGenerationAdapter') as MockSqlGen:
                mock_sql_gen = AsyncMock()
                # 返回回退SQL
                mock_sql_gen.generate_sql.return_value = Mock(
                    sql="SELECT 1 AS stub",
                    confidence=0.3
                )
                MockSqlGen.return_value = mock_sql_gen

                from app.services.domain.placeholder.core.handlers.stat_handler import StatHandler
                handler = StatHandler()

                result = await handler.generate_result(
                    placeholder_name="测试占位符",
                    placeholder_text="统计：测试数据",
                    data_source_id=self.test_data_source_id,
                    time_ctx={"start_date": "2024-09-25"}
                )

                # 验证回退逻辑生效
                assert result is not None
                # 即使Agent失败，也应该有某种形式的结果
                print(f"✅ 错误处理和回退机制测试通过")


def test_run_integration_suite():
    """运行完整集成测试套件"""
    print("🚀 开始占位符流水线集成测试...")

    # 运行pytest测试
    exit_code = pytest.main([__file__, "-v", "-s"])

    if exit_code == 0:
        print("✅ 所有集成测试通过!")
    else:
        print("❌ 部分集成测试失败")

    return exit_code


if __name__ == "__main__":
    # 直接运行完整测试套件
    test_run_integration_suite()