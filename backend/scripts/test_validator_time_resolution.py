import asyncio

from app.services.infrastructure.agents.tools.sql.validator import create_sql_validator_tool
from app.core.container import container


async def main():
    tool = create_sql_validator_tool(container)

    sql = "SELECT COUNT(*) FROM ods_refund WHERE dt >= '{{start_date}}' AND dt <= '{{end_date}}'"
    context = {
        "time_window": {"start": "2025-01-01", "end": "2025-01-31"}
    }

    result = await tool.execute(
        sql=sql,
        connection_config={"type": "doris"},
        validation_level="basic",
        check_syntax=True,
        check_semantics=False,
        check_performance=False,
        context=context,
    )

    meta = result.get("metadata", {})
    resolved_sql = meta.get("resolved_sql", "")
    assert "{{start_date}}" not in resolved_sql and "{{end_date}}" not in resolved_sql
    print("Resolved SQL:", resolved_sql)


if __name__ == "__main__":
    asyncio.run(main())


