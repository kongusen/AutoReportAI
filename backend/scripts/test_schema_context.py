"""
测试 Schema Context Retriever 功能

验证：
1. SchemaContextRetriever 能够正确初始化并缓存表结构
2. 根据查询检索相关表
3. 格式化并输出上下文信息
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.container import Container
from app.services.infrastructure.agents.context_retriever import (
    create_schema_context_retriever,
    SchemaContextRetriever
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_schema_context_retriever():
    """测试 Schema Context Retriever 功能"""

    logger.info("=" * 80)
    logger.info("开始测试 Schema Context Retriever")
    logger.info("=" * 80)

    try:
        # 1. 创建 container
        container = Container()
        logger.info("✅ Container 创建成功")

        # 2. 指定测试数据源（请替换为实际的数据源ID）
        data_source_id = "YOUR_DATA_SOURCE_ID"  # TODO: 替换为实际的数据源ID

        # 3. 创建 Schema Context Retriever
        logger.info(f"\n📋 Step 1: 创建 Schema Context Retriever (data_source_id={data_source_id})")
        context_retriever = create_schema_context_retriever(
            data_source_id=data_source_id,
            container=container,
            top_k=5,
            inject_as="system"
        )
        logger.info("✅ Schema Context Retriever 创建成功")

        # 4. 初始化并缓存表结构
        logger.info("\n📋 Step 2: 初始化 Schema 缓存")
        await context_retriever.retriever.initialize()

        if context_retriever.retriever.schema_cache:
            logger.info(f"✅ Schema 缓存初始化成功，共 {len(context_retriever.retriever.schema_cache)} 个表")
            logger.info(f"   表列表: {list(context_retriever.retriever.schema_cache.keys())}")
        else:
            logger.warning("⚠️ Schema 缓存为空")
            return

        # 5. 测试查询检索
        logger.info("\n📋 Step 3: 测试上下文检索")

        test_queries = [
            "珠宝玉石类商品的退货单数量占比",
            "查询订单总金额",
            "统计客户购买记录",
        ]

        for query in test_queries:
            logger.info(f"\n--- 查询: {query} ---")
            context = await context_retriever.retrieve_context(query)

            if context:
                logger.info("✅ 检索到相关上下文:")
                logger.info("\n" + context)
            else:
                logger.warning("⚠️ 未检索到相关上下文")

        logger.info("\n" + "=" * 80)
        logger.info("✅ 所有测试完成！")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)


async def test_document_formatting():
    """测试 Document 格式化"""

    logger.info("\n" + "=" * 80)
    logger.info("测试 Document 格式化")
    logger.info("=" * 80)

    # 模拟表结构数据
    table_info = {
        'table_name': 'return_orders',
        'columns': [
            {'name': 'order_id', 'type': 'BIGINT', 'nullable': False, 'comment': '订单ID'},
            {'name': 'product_type', 'type': 'VARCHAR(50)', 'nullable': True, 'comment': '商品类型'},
            {'name': 'return_date', 'type': 'DATE', 'nullable': False, 'comment': '退货日期'},
            {'name': 'amount', 'type': 'DECIMAL(10,2)', 'nullable': True, 'comment': '退货金额'},
        ],
        'table_comment': '退货订单表',
    }

    # 创建一个临时的 SchemaContextRetriever 实例
    container = Container()
    retriever = SchemaContextRetriever(
        data_source_id="test",
        connection_config={},  # 测试用，传递空配置
        container=container
    )

    # 格式化表信息
    formatted = retriever._format_table_info('return_orders', table_info)

    logger.info("📋 格式化后的表结构信息:\n")
    logger.info(formatted)
    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n" + "🔍" * 40)
    print("Schema Context Retriever 测试脚本")
    print("🔍" * 40 + "\n")

    # 测试 Document 格式化
    asyncio.run(test_document_formatting())

    # 测试完整流程（需要配置数据源）
    print("\n⚠️ 注意：完整测试需要配置实际的数据源ID")
    print("请修改 test_schema_context_retriever() 中的 data_source_id")
    print("然后取消下面的注释运行完整测试\n")

    # 取消注释运行完整测试
    # asyncio.run(test_schema_context_retriever())
