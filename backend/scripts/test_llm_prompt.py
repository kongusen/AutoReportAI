"""
测试脚本：检查 LLM 实际收到的 Prompt

目标：验证 ContextRetriever 是否正确将表结构注入到 LLM 的 prompt 中
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.container import Container
from app.db.session import get_db_session
from app.models.data_source import DataSource
from app.services.infrastructure.agents import AgentService
from app.services.infrastructure.agents.context_retriever import (
    SchemaContextRetriever,
    create_schema_context_retriever
)
from app.services.infrastructure.agents.types import AgentInput

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_llm_prompt():
    """测试 LLM 收到的完整 Prompt"""

    print("=" * 80)
    print("🧪 测试开始：检查 LLM 收到的 Prompt")
    print("=" * 80)

    # 1. 获取数据源配置
    data_source_id = "908c9e22-2773-4175-955c-bc0231336698"
    print(f"\n📊 步骤1：获取数据源配置 (ID: {data_source_id})")

    connection_config = {}
    with get_db_session() as db:
        data_source = db.query(DataSource).filter(
            DataSource.id == data_source_id
        ).first()

        if not data_source:
            print(f"❌ 未找到数据源 {data_source_id}")
            return

        connection_config = data_source.connection_config
        print(f"✅ 获取连接配置成功:")
        print(f"   - database: {connection_config.get('database')}")
        print(f"   - fe_hosts: {connection_config.get('fe_hosts')}")
        print(f"   - username: {connection_config.get('username')}")

    # 2. 创建 ContextRetriever 并初始化
    print(f"\n📚 步骤2：创建并初始化 ContextRetriever")
    container = Container()

    context_retriever = create_schema_context_retriever(
        data_source_id=data_source_id,
        connection_config=connection_config,
        container=container,
        top_k=5,
        inject_as="system",
        enable_stage_aware=True
    )

    # 获取底层的 schema retriever 来检查缓存（处理多层包装）
    schema_retriever = context_retriever

    # 逐层解包
    print(f"   解包 ContextRetriever 层次:")
    level = 0
    while hasattr(schema_retriever, 'retriever'):
        level += 1
        retriever_type = type(schema_retriever).__name__
        print(f"   - 第{level}层: {retriever_type}")
        schema_retriever = schema_retriever.retriever

        # 检查是否是 StageAwareContextRetriever
        if hasattr(schema_retriever, 'schema_retriever'):
            print(f"   - 检测到 StageAwareContextRetriever，深入到 schema_retriever")
            schema_retriever = schema_retriever.schema_retriever
            break

    print(f"   - 底层类型: {type(schema_retriever).__name__}")

    # 确保已初始化
    if hasattr(schema_retriever, '_initialized') and not schema_retriever._initialized:
        print(f"   ⚠️ Schema 缓存未初始化，正在初始化...")
        await schema_retriever.initialize()

    if hasattr(schema_retriever, 'schema_cache'):
        cache = schema_retriever.schema_cache
        print(f"✅ Schema 缓存已初始化，共 {len(cache)} 个表")
        for table_name, table_info in cache.items():
            columns = table_info.get('columns', [])
            print(f"   📋 表 '{table_name}': {len(columns)} 列")
            for col in columns[:3]:  # 显示前3列
                print(f"      - {col.get('name')} ({col.get('type')}): {col.get('comment', '')}")
            if len(columns) > 3:
                print(f"      ... 还有 {len(columns) - 3} 列")
    else:
        print(f"⚠️ 未找到 schema_cache 属性")

    # 3. 创建 AgentService
    print(f"\n🤖 步骤3：创建 AgentService")
    agent_service = AgentService(
        container=container,
        context_retriever=context_retriever
    )
    print(f"✅ AgentService 创建成功")
    print(f"   - ContextRetriever 已配置: {agent_service._facade._context_retriever is not None}")

    # 4. 构建测试用的 AgentInput
    print(f"\n📝 步骤4：构建 AgentInput")
    from app.services.infrastructure.agents.types import (
        PlaceholderSpec,
        SchemaInfo,
        TaskContext,
        AgentConstraints
    )

    agent_input = AgentInput(
        user_prompt="统计：独立客户数量",
        placeholder=PlaceholderSpec(
            id="test_placeholder",
            description="统计：独立客户数量",
            type="stat"
        ),
        schema=SchemaInfo(
            tables=list(schema_retriever.schema_cache.keys()) if hasattr(schema_retriever, 'schema_cache') else [],
            columns={}
        ),
        context=TaskContext(
            timezone="Asia/Shanghai",
            window={
                "start_date": "2025-10-25",
                "end_date": "2025-10-25"
            }
        ),
        constraints=AgentConstraints(
            sql_only=True,
            output_kind="sql",
            max_attempts=3
        ),
        template_id="test_template",
        data_source={
            "id": data_source_id
        },
        user_id="test_user"
    )
    print(f"✅ AgentInput 创建成功")

    # 5. 拦截 LLM 调用，记录发送的消息
    print(f"\n🔍 步骤5：拦截并记录 LLM 收到的消息")
    print("=" * 80)

    # 暂时 patch LLM adapter 来记录消息
    from app.services.infrastructure.agents.runtime import ContainerLLMAdapter
    original_generate = ContainerLLMAdapter.generate

    captured_messages = []

    async def patched_generate(self, messages, **kwargs):
        """拦截 generate 调用，记录消息"""
        captured_messages.append({
            'messages': messages,
            'kwargs': kwargs
        })

        print("\n📨 捕获到发送给 LLM 的消息:")
        print(f"   消息数量: {len(messages)}")

        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')

            print(f"\n   消息 #{i+1} [role={role}]:")
            print(f"   内容长度: {len(content)} 字符")

            if role == 'system':
                print(f"\n   {'='*70}")
                print(f"   SYSTEM MESSAGE (完整内容):")
                print(f"   {'='*70}")
                print(content)
                print(f"   {'='*70}")

                # 检查是否包含表结构信息
                if 'online_retail' in content:
                    print(f"\n   ✅ 检测到表结构信息：包含 'online_retail' 表")
                else:
                    print(f"\n   ❌ 未检测到表结构信息：缺少 'online_retail' 表")

                if '数据表结构' in content or 'Schema' in content or '可用表' in content:
                    print(f"   ✅ 包含表结构章节标题")
                else:
                    print(f"   ⚠️ 未找到表结构章节标题")

            elif role == 'user':
                print(f"\n   USER MESSAGE (前500字符):")
                print(f"   {'-'*70}")
                print(f"   {content[:500]}")
                if len(content) > 500:
                    print(f"   ... (还有 {len(content) - 500} 字符)")
                print(f"   {'-'*70}")

        print(f"\n   kwargs: {kwargs}")
        print("=" * 80)

        # 不实际调用 LLM，返回模拟响应（generate 方法返回字符串）
        return '{"sql": "SELECT COUNT(DISTINCT CustomerID) FROM online_retail", "reasoning": "测试响应"}'

    # 应用 patch
    ContainerLLMAdapter.generate = patched_generate

    try:
        # 6. 执行 Agent
        print(f"\n▶️ 步骤6：执行 Agent")
        result = await agent_service.execute(agent_input)

        print(f"\n✅ Agent 执行完成")
        print(f"   - 成功: {result.success}")
        print(f"   - 结果类型: {type(result.result)}")

    finally:
        # 恢复原始方法
        ContainerLLMAdapter.generate = original_generate

    # 7. 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"✅ 测试完成！")
    print(f"   - 捕获到 {len(captured_messages)} 次 LLM 调用")

    if captured_messages:
        first_call = captured_messages[0]
        messages = first_call['messages']
        system_msg = next((m for m in messages if m.get('role') == 'system'), None)

        if system_msg:
            content = system_msg.get('content', '')
            has_table_info = 'online_retail' in content

            print(f"\n   System Message 分析:")
            print(f"   - 长度: {len(content)} 字符")
            print(f"   - 包含表结构: {'✅ 是' if has_table_info else '❌ 否'}")

            if has_table_info:
                print(f"\n   🎉 成功！ContextRetriever 正确注入了表结构信息！")
            else:
                print(f"\n   ⚠️ 问题：ContextRetriever 没有注入表结构信息")
        else:
            print(f"\n   ⚠️ 未找到 system message")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_llm_prompt())
