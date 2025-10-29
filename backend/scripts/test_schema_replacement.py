#!/usr/bin/env python3
"""
测试 Schema 工具替换的完整流程

验证：
1. Schema Context 初始化
2. 表结构缓存
3. 上下文检索
4. 列验证工具
5. 列自动修复工具
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import logging
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockDataSourceService:
    """模拟数据源服务"""

    def __init__(self):
        # 模拟表结构数据
        self.mock_tables = {
            "orders": {
                "columns": [
                    {"name": "order_id", "type": "bigint", "comment": "订单ID", "key": "PRI"},
                    {"name": "user_id", "type": "bigint", "comment": "用户ID", "key": ""},
                    {"name": "created_at", "type": "datetime", "comment": "创建时间", "key": ""},
                    {"name": "status", "type": "varchar(50)", "comment": "订单状态", "key": ""},
                    {"name": "total_amount", "type": "decimal(10,2)", "comment": "订单总额", "key": ""},
                    {"name": "dt", "type": "date", "comment": "分区日期", "key": ""},
                ]
            },
            "return_orders": {
                "columns": [
                    {"name": "return_id", "type": "bigint", "comment": "退货ID", "key": "PRI"},
                    {"name": "order_id", "type": "bigint", "comment": "原订单ID", "key": ""},
                    {"name": "return_date", "type": "datetime", "comment": "退货日期", "key": ""},
                    {"name": "return_amount", "type": "decimal(10,2)", "comment": "退货金额", "key": ""},
                    {"name": "reason", "type": "varchar(200)", "comment": "退货原因", "key": ""},
                    {"name": "dt", "type": "date", "comment": "分区日期", "key": ""},
                ]
            },
            "order_items": {
                "columns": [
                    {"name": "item_id", "type": "bigint", "comment": "订单明细ID", "key": "PRI"},
                    {"name": "order_id", "type": "bigint", "comment": "订单ID", "key": ""},
                    {"name": "product_id", "type": "bigint", "comment": "商品ID", "key": ""},
                    {"name": "quantity", "type": "int", "comment": "数量", "key": ""},
                    {"name": "price", "type": "decimal(10,2)", "comment": "单价", "key": ""},
                    {"name": "dt", "type": "date", "comment": "分区日期", "key": ""},
                ]
            },
            "users": {
                "columns": [
                    {"name": "user_id", "type": "bigint", "comment": "用户ID", "key": "PRI"},
                    {"name": "username", "type": "varchar(100)", "comment": "用户名", "key": ""},
                    {"name": "email", "type": "varchar(200)", "comment": "邮箱", "key": ""},
                    {"name": "created_at", "type": "datetime", "comment": "注册时间", "key": ""},
                ]
            },
        }

    async def run_query(self, config: Dict[str, Any], sql: str, limit: int = 1000) -> Dict[str, Any]:
        """模拟执行 SQL 查询"""
        sql_upper = sql.upper()

        # 处理 SHOW TABLES
        if "SHOW TABLES" in sql_upper:
            return {
                "success": True,
                "rows": [{"Tables_in_db": table_name} for table_name in self.mock_tables.keys()],
                "columns": ["Tables_in_db"],
            }

        # 处理 SHOW FULL COLUMNS
        if "SHOW FULL COLUMNS" in sql_upper:
            # 提取表名
            for table_name in self.mock_tables.keys():
                if table_name in sql:
                    columns = self.mock_tables[table_name]["columns"]
                    rows = []
                    for col in columns:
                        rows.append({
                            "Field": col["name"],
                            "Type": col["type"],
                            "Null": "YES",
                            "Key": col["key"],
                            "Default": None,
                            "Comment": col["comment"],
                        })
                    return {
                        "success": True,
                        "rows": rows,
                        "columns": ["Field", "Type", "Null", "Key", "Default", "Comment"],
                    }

        # 默认返回成功
        return {
            "success": True,
            "rows": [],
            "columns": [],
        }


class MockContainer:
    """模拟依赖注入容器"""

    def __init__(self):
        self.data_source = MockDataSourceService()


async def test_schema_context_initialization():
    """测试 1: Schema Context 初始化"""
    logger.info("=" * 60)
    logger.info("测试 1: Schema Context 初始化")
    logger.info("=" * 60)

    try:
        from app.services.infrastructure.agents.context_retriever import create_schema_context_retriever

        container = MockContainer()

        # 创建 Schema Context Retriever
        retriever = create_schema_context_retriever(
            data_source_id="test_ds_001",
            container=container,
            top_k=5,
            inject_as="system"
        )

        logger.info("✅ Schema Context Retriever 创建成功")

        # 初始化（加载所有表结构）
        await retriever.retriever.initialize()

        # 验证缓存
        cache_size = len(retriever.retriever.schema_cache)
        logger.info(f"✅ Schema 缓存初始化完成，缓存了 {cache_size} 个表")

        # 验证每个表的缓存内容
        for table_name, table_info in retriever.retriever.schema_cache.items():
            column_count = len(table_info["columns"])
            logger.info(f"   - {table_name}: {column_count} 列")

        assert cache_size == 4, f"期望缓存 4 个表，实际缓存了 {cache_size} 个表"
        logger.info("✅ 测试 1 通过")

        return retriever

    except Exception as e:
        logger.error(f"❌ 测试 1 失败: {e}", exc_info=True)
        raise


async def test_context_retrieval(retriever):
    """测试 2: 上下文检索"""
    logger.info("=" * 60)
    logger.info("测试 2: 上下文检索")
    logger.info("=" * 60)

    try:
        # 测试场景 1: 查询退货相关的表
        query = "分析退货趋势，统计每天的退货订单数量和退货金额"
        documents = await retriever.retriever.retrieve(query, top_k=3)

        logger.info(f"查询: {query}")
        logger.info(f"检索到 {len(documents)} 个相关表:")

        retrieved_tables = set()
        for doc in documents:
            table_name = doc.metadata.get("table_name")
            retrieved_tables.add(table_name)
            logger.info(f"   - {table_name}")
            logger.info(f"     内容预览: {doc.content[:150]}...")

        # 验证：应该包含 return_orders 表
        assert "return_orders" in retrieved_tables, "期望检索到 return_orders 表"
        logger.info("✅ 测试场景 1 通过（退货分析）")

        # 测试场景 2: 查询订单相关的表
        query = "统计最近一周的订单总额和订单数量"
        documents = await retriever.retriever.retrieve(query, top_k=3)

        logger.info(f"查询: {query}")
        logger.info(f"检索到 {len(documents)} 个相关表:")

        retrieved_tables = set()
        for doc in documents:
            table_name = doc.metadata.get("table_name")
            retrieved_tables.add(table_name)
            logger.info(f"   - {table_name}")

        # 验证：应该包含 orders 表
        assert "orders" in retrieved_tables, "期望检索到 orders 表"
        logger.info("✅ 测试场景 2 通过（订单分析）")

        logger.info("✅ 测试 2 通过")

    except Exception as e:
        logger.error(f"❌ 测试 2 失败: {e}", exc_info=True)
        raise


async def test_column_validator():
    """测试 3: 列验证工具"""
    logger.info("=" * 60)
    logger.info("测试 3: 列验证工具")
    logger.info("=" * 60)

    try:
        from app.services.infrastructure.agents.tools.validation_tools import SQLColumnValidatorTool

        container = MockContainer()
        validator = SQLColumnValidatorTool(container=container)

        # 准备 schema_context（模拟已缓存的表结构）
        schema_context = {
            "return_orders": {
                "columns": ["return_id", "order_id", "return_date", "return_amount", "reason", "dt"]
            }
        }

        # 测试场景 1: 正确的 SQL（所有列都存在）
        sql_correct = """
        SELECT return_id, order_id, return_date, return_amount
        FROM return_orders
        WHERE dt BETWEEN {{start_date}} AND {{end_date}}
        """

        result = await validator.run(sql=sql_correct, schema_context=schema_context)
        logger.info(f"测试场景 1: 正确的 SQL")
        logger.info(f"   验证结果: {result.get('valid')}")
        logger.info(f"   消息: {result.get('message')}")

        assert result.get("valid") is True, "期望 SQL 验证通过"
        logger.info("✅ 测试场景 1 通过（正确的 SQL）")

        # 测试场景 2: 错误的列名
        sql_wrong = """
        SELECT return_id, order_id, return_date, return_total_amount
        FROM return_orders
        WHERE dt BETWEEN {{start_date}} AND {{end_date}}
        """

        result = await validator.run(sql=sql_wrong, schema_context=schema_context)
        logger.info(f"测试场景 2: 错误的列名")
        logger.info(f"   验证结果: {result.get('valid')}")
        logger.info(f"   无效列: {result.get('invalid_columns')}")
        logger.info(f"   修复建议: {result.get('suggestions')}")

        assert result.get("valid") is False, "期望 SQL 验证失败"
        assert "return_total_amount" in result.get("invalid_columns", []), "期望检测到无效列"
        logger.info("✅ 测试场景 2 通过（错误的列名）")

        logger.info("✅ 测试 3 通过")

        return result.get("suggestions")

    except Exception as e:
        logger.error(f"❌ 测试 3 失败: {e}", exc_info=True)
        raise


async def test_column_auto_fix(suggestions):
    """测试 4: 列自动修复工具"""
    logger.info("=" * 60)
    logger.info("测试 4: 列自动修复工具")
    logger.info("=" * 60)

    try:
        from app.services.infrastructure.agents.tools.validation_tools import SQLColumnAutoFixTool

        container = MockContainer()
        auto_fix = SQLColumnAutoFixTool(container=container)

        # 测试：修复错误的列名
        sql_wrong = """
        SELECT return_id, order_id, return_date, return_total_amount
        FROM return_orders
        WHERE dt BETWEEN {{start_date}} AND {{end_date}}
        """

        # 使用前面验证工具返回的建议
        result = await auto_fix.run(sql=sql_wrong, suggestions=suggestions)

        logger.info(f"原始 SQL:\n{sql_wrong}")
        logger.info(f"修复后的 SQL:\n{result.get('fixed_sql')}")
        logger.info(f"变更列表: {result.get('changes')}")

        fixed_sql = result.get("fixed_sql")

        # 验证：修复后的 SQL 应该包含正确的列名
        if suggestions and "return_total_amount" in suggestions:
            correct_column = suggestions["return_total_amount"]
            assert correct_column in fixed_sql, f"期望修复后的 SQL 包含 {correct_column}"
            assert "return_total_amount" not in fixed_sql, "期望修复后的 SQL 不包含错误的列名"
            logger.info("✅ 列名已正确修复")

        logger.info("✅ 测试 4 通过")

    except Exception as e:
        logger.error(f"❌ 测试 4 失败: {e}", exc_info=True)
        raise


async def test_tools_removed():
    """测试 5: 验证旧工具已移除"""
    logger.info("=" * 60)
    logger.info("测试 5: 验证旧工具已移除")
    logger.info("=" * 60)

    try:
        from app.services.infrastructure.agents.tools import build_default_tool_factories

        # 获取所有工具
        factories = build_default_tool_factories()

        # 构建工具实例
        container = MockContainer()
        tools = [factory(container) for factory in factories]

        # 获取工具名称列表
        tool_names = []
        for tool in tools:
            # 尝试从不同的属性获取工具名称
            name = getattr(tool, 'name', None) or getattr(tool, '__name__', None)
            if name:
                tool_names.append(name)

        logger.info(f"当前可用的工具 ({len(tool_names)} 个):")
        for name in tool_names:
            logger.info(f"   - {name}")

        # 验证：schema 工具应该已被移除
        schema_tools = [name for name in tool_names if name and "schema." in name]
        assert len(schema_tools) == 0, f"期望没有 schema 工具，但发现: {schema_tools}"
        logger.info("✅ 确认：schema.* 工具已移除")

        # 验证：验证工具应该已添加
        validation_tools = [name for name in tool_names if name and "sql." in name and "validate" in name.lower()]
        assert len(validation_tools) > 0, "期望至少有一个验证工具"
        logger.info("✅ 确认：sql.validate_* 工具已添加")

        logger.info("✅ 测试 5 通过")

    except Exception as e:
        logger.error(f"❌ 测试 5 失败: {e}", exc_info=True)
        raise


async def test_schema_tools_deprecated():
    """测试 6: 验证 schema_tools.py 已标记为 DEPRECATED"""
    logger.info("=" * 60)
    logger.info("测试 6: 验证 schema_tools.py 已标记为 DEPRECATED")
    logger.info("=" * 60)

    try:
        import importlib.util

        schema_tools_path = backend_dir / "app" / "services" / "infrastructure" / "agents" / "tools" / "schema_tools.py"

        # 读取文件内容
        with open(schema_tools_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 验证：文件开头应该包含 DEPRECATED 警告
        assert "DEPRECATED" in content[:500], "期望文件开头包含 DEPRECATED 标记"
        logger.info("✅ 确认：schema_tools.py 已标记为 DEPRECATED")

        # 验证：应该包含替代方案说明
        assert "context_retriever" in content.lower(), "期望文件包含 context_retriever 替代方案说明"
        logger.info("✅ 确认：包含替代方案说明")

        # 验证：应该包含废弃日期
        assert "2025-10-24" in content, "期望文件包含废弃日期"
        logger.info("✅ 确认：包含废弃日期")

        logger.info("✅ 测试 6 通过")

    except Exception as e:
        logger.error(f"❌ 测试 6 失败: {e}", exc_info=True)
        raise


async def main():
    """主测试流程"""
    logger.info("\n")
    logger.info("🚀 开始测试 Schema 工具替换")
    logger.info("\n")

    try:
        # 测试 1: Schema Context 初始化
        retriever = await test_schema_context_initialization()

        # 测试 2: 上下文检索
        await test_context_retrieval(retriever)

        # 测试 3: 列验证工具
        suggestions = await test_column_validator()

        # 测试 4: 列自动修复工具
        await test_column_auto_fix(suggestions)

        # 测试 5: 验证旧工具已移除
        await test_tools_removed()

        # 测试 6: 验证 schema_tools.py 已标记为 DEPRECATED
        await test_schema_tools_deprecated()

        logger.info("\n")
        logger.info("=" * 60)
        logger.info("✅ 所有测试通过！")
        logger.info("=" * 60)
        logger.info("\n")
        logger.info("替换总结：")
        logger.info("  ✅ Schema Context 机制正常工作")
        logger.info("  ✅ 表结构缓存功能正常")
        logger.info("  ✅ 上下文检索准确")
        logger.info("  ✅ 列验证工具正常")
        logger.info("  ✅ 列自动修复工具正常")
        logger.info("  ✅ 旧工具已移除")
        logger.info("  ✅ 文档已更新")
        logger.info("\n")
        logger.info("下一步：")
        logger.info("  1. 在开发环境运行集成测试")
        logger.info("  2. 监控 LLM 调用次数和执行时间")
        logger.info("  3. 验证 SQL 准确率是否提升至 95%+")
        logger.info("  4. 准备生产环境部署")
        logger.info("\n")

    except Exception as e:
        logger.error("\n")
        logger.error("=" * 60)
        logger.error(f"❌ 测试失败: {e}")
        logger.error("=" * 60)
        logger.error("\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
