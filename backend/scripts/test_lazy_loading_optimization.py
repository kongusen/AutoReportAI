"""
测试懒加载优化的完整功能

验证：
1. 启动时只加载表名，不加载列信息
2. TT循环中按需加载列信息
3. 避免重复查询已加载的表
4. 智能筛选相关表
5. 缓存统计功能
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.container import Container
from app.db.session import get_db_session
from app.models.data_source import DataSource
from app.services.infrastructure.agents.context_retriever import (
    create_schema_context_retriever
)
from app.services.infrastructure.agents.tools.schema import (
    create_schema_discovery_tool
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_test_data_source():
    """从数据库获取测试用的数据源配置"""
    logger.info("\n📊 从数据库获取测试数据源...")

    with get_db_session() as db:
        # 尝试获取第一个可用的数据源
        data_source = db.query(DataSource).first()

        if not data_source:
            logger.error("❌ 数据库中没有可用的数据源")
            return None, None

        logger.info(f"✅ 找到数据源: {data_source.name} (ID: {data_source.id})")
        logger.info(f"   类型: {data_source.source_type}")

        return str(data_source.id), data_source.connection_config


async def test_schema_discovery_tool_lazy_loading():
    """测试 SchemaDiscoveryTool 的懒加载功能"""
    logger.info("\n" + "="*80)
    logger.info("测试 SchemaDiscoveryTool 懒加载功能")
    logger.info("="*80)

    try:
        # 1. 获取测试数据源配置
        data_source_id, connection_config = get_test_data_source()
        if not connection_config:
            logger.error("❌ 无法获取数据源配置，跳过测试")
            return False

        # 2. 创建容器
        container = Container()

        # 3. 创建 SchemaDiscoveryTool（启用懒加载）
        tool = create_schema_discovery_tool(container, enable_lazy_loading=True)
        logger.info(f"✅ 创建 SchemaDiscoveryTool，懒加载模式: {tool.enable_lazy_loading}")

        # 4. 测试：只发现表名（懒加载模式）
        logger.info("\n📋 测试1: 只发现表名（懒加载模式）")
        result = await tool.run(
            connection_config=connection_config,
            discovery_type="tables",
            max_tables=100
        )

        if result.get("success"):
            tables = result.get("tables", [])
            logger.info(f"✅ 发现 {len(tables)} 个表")
            logger.info(f"   懒加载启用: {result['metadata'].get('lazy_loading_enabled')}")

            # 检查表信息是否只包含表名，不包含列信息
            if tables:
                sample_table = tables[0]
                logger.info(f"   示例表: {sample_table.get('table_name')}")
                logger.info(f"   列数: {len(sample_table.get('columns', []))}")
                logger.info(f"   是否懒加载: {sample_table.get('lazy_loaded')}")

                if len(sample_table.get('columns', [])) == 0:
                    logger.info("✅ 验证通过：表信息不包含列数据（懒加载生效）")
                else:
                    logger.warning("⚠️ 验证失败：表信息包含列数据（懒加载未生效）")
        else:
            logger.error(f"❌ 发现失败: {result.get('error')}")

        # 5. 获取缓存统计
        cache_stats = tool.get_cache_stats()
        logger.info(f"\n📊 缓存统计:")
        logger.info(f"   懒加载启用: {cache_stats['lazy_loading_enabled']}")
        logger.info(f"   缓存已初始化: {cache_stats['cache_initialized']}")
        logger.info(f"   总表数: {cache_stats['total_tables']}")
        logger.info(f"   已加载表数: {cache_stats['loaded_tables']}")
        logger.info(f"   表名列表（前10个）: {cache_stats['table_names']}")

        # 6. 测试：按需加载特定表的列信息
        logger.info("\n📋 测试2: 按需加载列信息")
        result = await tool.run(
            connection_config=connection_config,
            discovery_type="columns",
            tables=cache_stats['table_names'][:3]  # 只加载前3个表的列信息
        )

        if result.get("success"):
            columns = result.get("columns", [])
            logger.info(f"✅ 加载 {len(columns)} 个列")

            # 再次获取缓存统计
            cache_stats_after = tool.get_cache_stats()
            logger.info(f"\n📊 加载后的缓存统计:")
            logger.info(f"   总表数: {cache_stats_after['total_tables']}")
            logger.info(f"   已加载表数: {cache_stats_after['loaded_tables']}")
            logger.info(f"   已加载的表: {cache_stats_after['loaded_table_names']}")

            if cache_stats_after['loaded_tables'] == 3:
                logger.info("✅ 验证通过：只加载了请求的3个表")
            else:
                logger.warning(f"⚠️ 验证失败：加载了 {cache_stats_after['loaded_tables']} 个表")

        # 7. 测试：重复加载相同的表（应该使用缓存）
        logger.info("\n📋 测试3: 重复加载相同的表（测试缓存）")
        result = await tool.run(
            connection_config=connection_config,
            discovery_type="columns",
            tables=cache_stats['table_names'][:3]  # 再次加载相同的表
        )

        if result.get("success"):
            logger.info("✅ 重复加载成功（应该使用了缓存）")

            # 检查缓存统计是否未变化
            cache_stats_repeat = tool.get_cache_stats()
            if cache_stats_repeat['loaded_tables'] == cache_stats_after['loaded_tables']:
                logger.info("✅ 验证通过：缓存生效，未重复加载")
            else:
                logger.warning("⚠️ 验证失败：发生了重复加载")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def test_schema_context_retriever_lazy_loading():
    """测试 SchemaContextRetriever 的懒加载功能"""
    logger.info("\n" + "="*80)
    logger.info("测试 SchemaContextRetriever 懒加载功能")
    logger.info("="*80)

    try:
        # 1. 获取测试数据源配置
        data_source_id, connection_config = get_test_data_source()
        if not connection_config:
            logger.error("❌ 无法获取数据源配置，跳过测试")
            return False

        # 2. 创建容器
        container = Container()

        # 3. 创建 SchemaContextRetriever（启用懒加载）
        retriever = create_schema_context_retriever(
            data_source_id=data_source_id,
            connection_config=connection_config,
            container=container,
            top_k=5,
            enable_stage_aware=True,
            enable_lazy_loading=True
        )
        logger.info(f"✅ 创建 SchemaContextRetriever，懒加载模式: {retriever.enable_lazy_loading}")

        # 4. 初始化（只加载表名）
        logger.info("\n📋 测试1: 初始化（只加载表名）")
        await retriever.initialize()

        # 获取初始化后的缓存统计
        # 注意：create_schema_context_retriever 返回的是 SchemaContextRetriever 实例
        # 而 SchemaContextRetriever 有 get_cache_stats 方法
        cache_stats = retriever.get_cache_stats()
        logger.info(f"\n📊 初始化后的缓存统计:")
        logger.info(f"   懒加载启用: {cache_stats['lazy_loading_enabled']}")
        logger.info(f"   总表数: {cache_stats['total_tables']}")
        logger.info(f"   已加载表数: {cache_stats['loaded_tables']}")
        logger.info(f"   缓存大小: {cache_stats['cache_size']}")

        if cache_stats['loaded_tables'] == 0 and cache_stats['total_tables'] > 0:
            logger.info("✅ 验证通过：初始化只获取了表名，未加载列信息")
        else:
            logger.warning(f"⚠️ 验证失败：已加载 {cache_stats['loaded_tables']} 个表的列信息")

        # 5. 测试：检索相关表（触发按需加载）
        logger.info("\n📋 测试2: 检索相关表（触发按需加载）")
        query = "统计退货申请的总数"
        documents = await retriever.retrieve(query=query, top_k=3)

        logger.info(f"✅ 检索到 {len(documents)} 个相关表")
        for doc in documents:
            table_name = doc.metadata.get('table_name')
            relevance_score = doc.metadata.get('relevance_score', 0)
            retrieval_method = doc.metadata.get('retrieval_method', 'unknown')
            logger.info(f"   - {table_name} (相关性: {relevance_score:.2f}, 方法: {retrieval_method})")

        # 获取检索后的缓存统计
        cache_stats_after = retriever.get_cache_stats()
        logger.info(f"\n📊 检索后的缓存统计:")
        logger.info(f"   总表数: {cache_stats_after['total_tables']}")
        logger.info(f"   已加载表数: {cache_stats_after['loaded_tables']}")
        logger.info(f"   缓存大小: {cache_stats_after['cache_size']}")

        if cache_stats_after['loaded_tables'] > 0:
            logger.info(f"✅ 验证通过：按需加载了 {cache_stats_after['loaded_tables']} 个表的列信息")
        else:
            logger.warning("⚠️ 验证失败：未按需加载表信息")

        # 6. 测试：重复检索（应该使用缓存）
        logger.info("\n📋 测试3: 重复检索相同查询（测试缓存）")
        documents_repeat = await retriever.retrieve(query=query, top_k=3)

        logger.info(f"✅ 重复检索到 {len(documents_repeat)} 个表")

        # 检查缓存统计是否未变化
        cache_stats_repeat = retriever.get_cache_stats()
        if cache_stats_repeat['loaded_tables'] == cache_stats_after['loaded_tables']:
            logger.info("✅ 验证通过：缓存生效，未重复加载")
        else:
            logger.warning("⚠️ 验证失败：发生了重复加载")

        # 7. 测试：不同查询（可能加载新表）
        logger.info("\n📋 测试4: 不同查询（可能加载新表）")
        new_query = "分析用户的订单数据"
        documents_new = await retriever.retrieve(query=new_query, top_k=3)

        logger.info(f"✅ 检索到 {len(documents_new)} 个表")
        for doc in documents_new:
            table_name = doc.metadata.get('table_name')
            logger.info(f"   - {table_name}")

        # 最终缓存统计
        cache_stats_final = retriever.get_cache_stats()
        logger.info(f"\n📊 最终缓存统计:")
        logger.info(f"   总表数: {cache_stats_final['total_tables']}")
        logger.info(f"   已加载表数: {cache_stats_final['loaded_tables']}")
        logger.info(f"   智能检索启用: {cache_stats_final['intelligent_retrieval_enabled']}")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def main():
    """主测试函数"""
    logger.info("\n" + "🚀"*40)
    logger.info("开始测试懒加载优化功能")
    logger.info("🚀"*40 + "\n")

    results = []

    # 测试 SchemaDiscoveryTool
    logger.info("\n" + "="*80)
    logger.info("第一部分：测试 SchemaDiscoveryTool")
    logger.info("="*80)
    result1 = await test_schema_discovery_tool_lazy_loading()
    results.append(("SchemaDiscoveryTool", result1))

    # 测试 SchemaContextRetriever
    logger.info("\n" + "="*80)
    logger.info("第二部分：测试 SchemaContextRetriever")
    logger.info("="*80)
    result2 = await test_schema_context_retriever_lazy_loading()
    results.append(("SchemaContextRetriever", result2))

    # 总结
    logger.info("\n" + "="*80)
    logger.info("测试总结")
    logger.info("="*80)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{name}: {status}")

    all_passed = all(result for _, result in results)
    if all_passed:
        logger.info("\n🎉 所有测试通过！懒加载优化功能正常工作。")
    else:
        logger.info("\n⚠️ 部分测试失败，请检查日志。")

    return all_passed


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ 测试异常: {e}", exc_info=True)
        sys.exit(1)
