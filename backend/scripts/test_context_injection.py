"""
简化测试：直接检查 ContextRetriever 输出的内容
"""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.container import Container
from app.db.session import get_db_session
from app.models.data_source import DataSource
from app.services.infrastructure.agents.context_retriever import create_schema_context_retriever


async def test_context_injection():
    """测试 ContextRetriever 输出的格式化内容"""

    print("=" * 80)
    print("🧪 测试：检查 ContextRetriever 注入的内容")
    print("=" * 80)

    # 1. 获取数据源配置
    data_source_id = "908c9e22-2773-4175-955c-bc0231336698"
    print(f"\n📊 获取数据源配置 (ID: {data_source_id})")

    with get_db_session() as db:
        data_source = db.query(DataSource).filter(
            DataSource.id == data_source_id
        ).first()

        if not data_source:
            print(f"❌ 未找到数据源")
            return

        connection_config = data_source.connection_config

    # 2. 创建 ContextRetriever
    print(f"\n📚 创建 ContextRetriever")
    container = Container()

    context_retriever = create_schema_context_retriever(
        data_source_id=data_source_id,
        connection_config=connection_config,
        container=container,
        top_k=5,
        inject_as="system",
        enable_stage_aware=True
    )

    # 3. 获取底层 schema retriever
    schema_retriever = context_retriever.retriever
    if hasattr(schema_retriever, 'schema_retriever'):
        schema_retriever = schema_retriever.schema_retriever

    # 确保初始化
    if not schema_retriever._initialized:
        await schema_retriever.initialize()

    print(f"✅ Schema 缓存初始化，共 {len(schema_retriever.schema_cache)} 个表")

    # 4. 模拟检索（像 Loom 框架那样调用底层 retriever）
    print(f"\n🔍 步骤：模拟 Loom 框架检索上下文")
    query = "统计：独立客户数量"

    # Loom 的 ContextRetriever 内部会调用底层 retriever 的 retrieve 方法
    inner_retriever = context_retriever.retriever
    documents = await inner_retriever.retrieve(query, top_k=5)

    print(f"\n📄 检索结果:")
    print(f"   - 返回文档数: {len(documents)}")

    for i, doc in enumerate(documents, 1):
        print(f"\n   文档 #{i}:")
        print(f"   - metadata: {doc.metadata}")
        print(f"   - score: {doc.score}")
        print(f"   - content (前500字符):")
        print(f"     {doc.content[:500]}")

    # 5. 格式化文档（像 Loom 框架在注入前那样）
    print(f"\n📝 步骤：格式化文档（即将注入到 System Message 的内容）")
    # 调用底层 retriever 的 format_documents（我们自定义的 ContextRetriever 有这个方法）
    formatted_context = inner_retriever.format_documents(documents)

    print("\n" + "=" * 80)
    print("📤 最终注入到 System Message 的内容")
    print("=" * 80)
    print(formatted_context)
    print("=" * 80)

    # 6. 分析
    print(f"\n📊 分析:")
    print(f"   - 格式化内容长度: {len(formatted_context)} 字符")
    print(f"   - 包含 'online_retail': {'✅ 是' if 'online_retail' in formatted_context else '❌ 否'}")
    print(f"   - 包含列信息: {'✅ 是' if 'InvoiceNo' in formatted_context or 'StockCode' in formatted_context else '❌ 否'}")

    if 'online_retail' in formatted_context:
        print(f"\n🎉 成功！ContextRetriever 正确注入了表结构信息！")
        print(f"   LLM 将能看到 online_retail 表的完整结构")
    else:
        print(f"\n⚠️ 问题：ContextRetriever 没有包含表结构信息")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_context_injection())
