import asyncio

from app.services.infrastructure.agents.context_retriever import create_schema_context_retriever
from app.core.container import container


async def main():
    # 构造一个包含系统指令/递归标记的长 query
    noisy = (
        "# 系统指令\n你是一个Doris SQL生成专家...\n"
        "## 关键要求\n...\n"
        "继续处理任务：# 任务描述\n统计退货申请的总数，时间范围使用占位符\n"
    )

    retriever = create_schema_context_retriever(
        data_source_id="dummy",
        connection_config={"type": "doris"},
        container=container,
    )

    # 直接调用内部净化函数以方便断言
    cleaned = retriever._sanitize_query(noisy)  # type: ignore
    assert "系统指令" not in cleaned
    assert "继续处理任务" not in cleaned
    assert "统计" in cleaned
    print("Sanitized query:", cleaned[:120], "...")


if __name__ == "__main__":
    asyncio.run(main())


