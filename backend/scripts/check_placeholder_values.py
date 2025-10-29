"""检查placeholder_values表"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db.session import SessionLocal
from app.models.template_placeholder import TemplatePlaceholder, PlaceholderValue

db = SessionLocal()

template_id = "3b56b8a8-e3a3-4da1-9319-9891a4f03123"

placeholders = db.query(TemplatePlaceholder).filter(
    TemplatePlaceholder.template_id == template_id
).all()

print(f"\n📋 模板占位符状态检查（共 {len(placeholders)} 个）\n")

for i, ph in enumerate(placeholders[:5], 1):
    print(f"{i}. {ph.placeholder_name}")
    print(f"   TemplatePlaceholder表:")
    print(f"     - generated_sql: {bool(ph.generated_sql)}")
    print(f"     - agent_analyzed: {ph.agent_analyzed}")
    print(f"     - sql_validated: {ph.sql_validated}")

    # 查询对应的PlaceholderValue
    values = db.query(PlaceholderValue).filter(
        PlaceholderValue.placeholder_id == ph.id
    ).order_by(PlaceholderValue.created_at.desc()).limit(3).all()

    print(f"   PlaceholderValue表: {len(values)} 条记录")
    for j, val in enumerate(values, 1):
        if val.execution_sql:
            sql_preview = val.execution_sql[:150].replace('\n', ' ')
            print(f"     [{j}] SQL: {sql_preview}...")
            print(f"         success: {val.success}")
            print(f"         created_at: {val.created_at}")
    print()

db.close()
