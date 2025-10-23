from app.services.infrastructure.agents.prompts import build_system_instructions


def test_build_system_instructions_includes_tools():
    tools = [
        {"name": "sql.validate", "desc": "验证SQL"},
        {"name": "sql.execute", "desc": "执行SQL"},
    ]

    instructions = build_system_instructions("task_execution", tools)

    assert "任务执行" in instructions
    assert "sql.validate" in instructions
    assert "sql.execute" in instructions


def test_build_system_instructions_defaults_to_template():
    instructions = build_system_instructions("", [])
    assert "模板规划" in instructions
