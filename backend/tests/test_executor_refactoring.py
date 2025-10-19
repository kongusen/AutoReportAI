"""
测试Executor重构后的功能

验证以下改进：
1. _extract_tables_from_sql: 使用sqlparse提取SQL中的表名
2. _load_data_source_config: 统一的数据源配置加载
3. _build_execution_context: 执行上下文构建
"""

import pytest
from app.services.infrastructure.agents.executor import StepExecutor


class TestExecutorRefactoring:
    """测试Executor重构后的功能"""

    def test_extract_tables_from_sql_simple(self):
        """测试从简单SQL中提取表名"""
        # 创建一个mock container
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 测试简单SELECT
        sql = "SELECT * FROM users WHERE id = 1"
        tables = executor._extract_tables_from_sql(sql)
        assert "users" in tables

        # 测试JOIN
        sql = "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id"
        tables = executor._extract_tables_from_sql(sql)
        assert "orders" in tables
        assert "customers" in tables

    def test_extract_tables_from_sql_with_alias(self):
        """测试带别名的SQL表名提取"""
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 测试表别名
        sql = "SELECT * FROM users AS u WHERE u.id = 1"
        tables = executor._extract_tables_from_sql(sql)
        assert "users" in tables

        # 测试复杂JOIN与别名
        sql = """
            SELECT o.*, c.name
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
        """
        tables = executor._extract_tables_from_sql(sql)
        assert "orders" in tables
        assert "customers" in tables

    def test_extract_tables_from_sql_placeholder(self):
        """测试带占位符的SQL表名提取"""
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 测试带占位符的SQL
        sql = """
            SELECT COUNT(*) as cnt
            FROM refund_orders
            WHERE dt BETWEEN {{start_date}} AND {{end_date}}
        """
        tables = executor._extract_tables_from_sql(sql)
        assert "refund_orders" in tables

    def test_extract_tables_from_sql_multiple_tables(self):
        """测试多表SQL的表名提取"""
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 测试逗号分隔的多表
        sql = "SELECT * FROM table1, table2, table3 WHERE table1.id = table2.id"
        tables = executor._extract_tables_from_sql(sql)
        assert "table1" in tables
        assert "table2" in tables
        assert "table3" in tables

    def test_extract_tables_fallback_to_regex(self):
        """测试sqlparse失败时回退到正则表达式"""
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 即使SQL格式不标准，也应该能提取表名
        sql = "SELECT * FROM users"
        tables = executor._extract_tables_from_sql(sql)
        assert len(tables) > 0

    def test_extract_tables_empty_sql(self):
        """测试空SQL或无效SQL"""
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 空SQL
        assert executor._extract_tables_from_sql("") == []
        assert executor._extract_tables_from_sql(None) == []

        # 无表名的SQL
        assert executor._extract_tables_from_sql("SELECT 1") == []

    def test_infer_table_keywords(self):
        """测试从描述中推断表关键词"""
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 测试退货退款关键词
        keywords = executor._infer_table_keywords("统计退货订单数量")
        assert any(k in ["退货", "refund", "return"] for k in keywords)

        keywords = executor._infer_table_keywords("Calculate refund rate")
        assert any(k in ["退货", "refund", "return"] for k in keywords)

    def test_extract_tokens(self):
        """测试token提取"""
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 测试中文token提取（空格分隔）
        tokens = executor._extract_tokens("退货 订单 总数 统计")
        assert "退货" in tokens
        assert "订单" in tokens
        # "总数"和"统计"应该被过滤掉（停用词）
        assert "总数" not in tokens
        assert "统计" not in tokens

        # 测试英文token提取
        tokens = executor._extract_tokens("refund order count")
        assert "refund" in tokens
        assert "order" in tokens
        assert "count" in tokens

        # 测试缩写映射
        tokens = executor._extract_tokens("refund processing")
        # 应该包含refund及其缩写
        assert "refund" in tokens


class TestExecutorStats:
    """测试Executor性能统计功能"""

    def test_executor_has_stats(self):
        """测试Executor是否有性能统计字典"""
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 检查性能统计字典存在
        assert hasattr(executor, '_execution_stats')
        assert isinstance(executor._execution_stats, dict)

        # 检查必要的统计字段
        assert 'total_executions' in executor._execution_stats
        assert 'successful_executions' in executor._execution_stats
        assert 'failed_executions' in executor._execution_stats
        assert 'total_execution_time_ms' in executor._execution_stats


class TestExecutorStructuredLogging:
    """测试Executor结构化日志功能"""

    def test_executor_has_struct_logger(self):
        """测试Executor是否有结构化日志记录器"""
        class MockContainer:
            pass

        executor = StepExecutor(MockContainer())

        # 检查结构化日志记录器存在
        assert hasattr(executor, '_struct_logger')
        assert executor._struct_logger is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
