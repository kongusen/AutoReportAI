"""
SQL生成协调器测试

测试SQL-First架构的核心组件
"""

import pytest
from typing import Dict, Any

from app.services.infrastructure.agents.sql_generation import (
    SQLGenerationCoordinator,
    SQLGenerationConfig,
)
from app.core.container import Container


class TestSQLGenerationCoordinator:
    """SQL生成协调器测试套件"""

    @pytest.fixture
    def container(self):
        """获取容器实例"""
        return Container()

    @pytest.fixture
    def coordinator(self, container):
        """创建协调器实例"""
        return SQLGenerationCoordinator(
            container=container,
            llm_client=container.llm_service,
            db_connector=container.data_source,
            config=SQLGenerationConfig(
                max_generation_attempts=3,
                max_fix_attempts=2,
                enable_dry_run_validation=True,
            ),
        )

    @pytest.fixture
    def base_context(self) -> Dict[str, Any]:
        """基础context快照"""
        return {
            "time_window": {"start_date": "2024-01-01", "end_date": "2024-01-31"},
            "column_details": {
                "ods_sales": {
                    "sale_date": {"type": "DATE", "comment": "销售日期"},
                    "amount": {"type": "DECIMAL", "comment": "销售金额"},
                    "product_id": {"type": "VARCHAR", "comment": "产品ID"},
                    "region": {"type": "VARCHAR", "comment": "销售区域"},
                },
                "ods_products": {
                    "product_id": {"type": "VARCHAR", "comment": "产品ID"},
                    "product_name": {"type": "VARCHAR", "comment": "产品名称"},
                    "category": {"type": "VARCHAR", "comment": "产品类别"},
                },
            },
            "data_source": {
                "id": "test_ds_001",
                "source_type": "doris",
                "host": "localhost",
                "port": 9030,
                "database": "test_db",
            },
            "user_id": "test_user",
        }

    @pytest.mark.asyncio
    async def test_simple_query_success(self, coordinator, base_context):
        """测试简单查询成功场景"""
        result = await coordinator.generate(
            query="统计1月份的销售总额",
            context_snapshot=base_context,
        )

        # 验证结果
        assert result.success, f"生成失败: {result.error}"
        assert result.sql, "SQL不应为空"
        assert "SELECT" in result.sql.upper()
        assert "{{start_date}}" in result.sql, "应使用时间占位符"
        assert "{{end_date}}" in result.sql, "应使用时间占位符"
        assert "ods_sales" in result.sql, "应使用正确的表名"

        # 验证元数据
        assert result.metadata.get("attempt") <= 3
        assert result.metadata.get("confidence", 0) > 0.5

        print(f"\n✅ 成功生成SQL:\n{result.sql}")
        print(f"📊 元数据: {result.metadata}")

    @pytest.mark.asyncio
    async def test_complex_query_with_join(self, coordinator, base_context):
        """测试复杂查询（带JOIN）"""
        result = await coordinator.generate(
            query="统计每个产品类别的销售金额总和",
            context_snapshot=base_context,
        )

        assert result.success
        assert "JOIN" in result.sql.upper() or "ods_products" in result.sql
        print(f"\n✅ 复杂查询SQL:\n{result.sql}")

    @pytest.mark.asyncio
    async def test_missing_time_dependency(self, coordinator, base_context):
        """测试缺少时间依赖"""
        # 移除时间窗口
        context = {**base_context}
        del context["time_window"]

        result = await coordinator.generate(
            query="统计销售额",
            context_snapshot=context,
        )

        # 应该失败并提示缺少时间信息
        assert not result.success
        assert result.needs_user_input
        assert "时间" in result.error
        print(f"\n⚠️ 预期失败: {result.error}")
        print(f"💡 建议: {result.suggestions}")

    @pytest.mark.asyncio
    async def test_missing_schema_dependency(self, coordinator, base_context):
        """测试缺少Schema依赖"""
        # 移除schema
        context = {**base_context}
        del context["column_details"]

        result = await coordinator.generate(
            query="统计销售额",
            context_snapshot=context,
        )

        # 应该失败并提示缺少Schema
        assert not result.success
        assert "Schema" in result.error
        print(f"\n⚠️ 预期失败: {result.error}")

    @pytest.mark.asyncio
    async def test_invalid_table_name_fix(self, coordinator, base_context):
        """测试表名错误自动修复"""
        # 这个测试假设LLM可能生成错误的表名
        # Coordinator应该能通过Schema验证发现并尝试修复
        result = await coordinator.generate(
            query="统计sales表的数据",  # 故意使用不存在的表名
            context_snapshot=base_context,
        )

        # 即使用户说了错误的表名，也应该生成正确的SQL
        if result.success:
            assert "ods_sales" in result.sql
            print(f"\n✅ 自动修正表名:\n{result.sql}")
        else:
            # 或者明确报错
            assert "表名" in result.error or "table" in result.error.lower()
            print(f"\n⚠️ 检测到表名错误: {result.error}")

    @pytest.mark.asyncio
    async def test_multiple_attempts(self, coordinator, base_context):
        """测试多次尝试机制"""
        result = await coordinator.generate(
            query="用非常模糊的方式统计一些数据",  # 故意模糊
            context_snapshot=base_context,
        )

        # 无论成功失败，都应该有尝试记录
        if result.success:
            attempts = result.metadata.get("attempt", 1)
            print(f"\n✅ {attempts}次尝试后成功")
        else:
            debug_info = result.debug_info or []
            print(f"\n❌ {len(debug_info)}次尝试后失败")
            print(f"失败原因: {result.metadata.get('failure_reasons')}")
            print(f"建议: {result.metadata.get('suggestions')}")

    @pytest.mark.asyncio
    async def test_error_summary(self, coordinator):
        """测试错误摘要功能"""
        # 创建一个必然失败的场景
        result = await coordinator.generate(
            query="无意义的查询",
            context_snapshot={},  # 完全空的context
        )

        assert not result.success
        assert result.error
        assert result.metadata.get("suggestions")

        print(f"\n❌ 错误信息: {result.error}")
        print(f"💡 建议:")
        for suggestion in result.metadata.get("suggestions", []):
            print(f"  - {suggestion}")


class TestSQLGenerationConfig:
    """测试配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = SQLGenerationConfig()

        assert config.max_generation_attempts == 3
        assert config.max_fix_attempts == 2
        assert config.enable_dry_run_validation is True
        assert config.feature_flag_key == "enable_sql_generation_coordinator"

    def test_custom_config(self):
        """测试自定义配置"""
        config = SQLGenerationConfig(
            max_generation_attempts=5,
            max_fix_attempts=3,
            enable_dry_run_validation=False,
        )

        assert config.max_generation_attempts == 5
        assert config.max_fix_attempts == 3
        assert config.enable_dry_run_validation is False


# ===== 性能测试 =====


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_performance_benchmark():
    """性能基准测试"""
    import time

    container = Container()
    coordinator = SQLGenerationCoordinator(
        container=container,
        llm_client=container.llm_service,
        db_connector=container.data_source,
        config=SQLGenerationConfig(),
    )

    context = {
        "time_window": {"start_date": "2024-01-01", "end_date": "2024-01-31"},
        "column_details": {
            "ods_sales": {
                "sale_date": {"type": "DATE"},
                "amount": {"type": "DECIMAL"},
            }
        },
        "data_source": {"id": "test", "source_type": "doris"},
    }

    queries = [
        "统计销售总额",
        "统计每日销售趋势",
        "查询销售额TOP10的日期",
    ]

    total_time = 0
    success_count = 0

    for query in queries:
        start = time.time()
        result = await coordinator.generate(query, context)
        elapsed = time.time() - start

        total_time += elapsed
        if result.success:
            success_count += 1

        print(f"\n查询: {query}")
        print(f"耗时: {elapsed:.2f}s")
        print(f"结果: {'✅ 成功' if result.success else '❌ 失败'}")

    avg_time = total_time / len(queries)
    success_rate = success_count / len(queries) * 100

    print(f"\n📊 性能统计:")
    print(f"  总耗时: {total_time:.2f}s")
    print(f"  平均耗时: {avg_time:.2f}s")
    print(f"  成功率: {success_rate:.1f}%")

    # 性能断言（可根据实际情况调整）
    assert avg_time < 15, f"平均耗时过长: {avg_time:.2f}s"
    assert success_rate >= 60, f"成功率过低: {success_rate:.1f}%"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s", "--tb=short"])
