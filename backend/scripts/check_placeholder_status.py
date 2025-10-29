"""检查占位符状态"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db.session import SessionLocal
from app.models.template_placeholder import TemplatePlaceholder

db = SessionLocal()

template_id = "3b56b8a8-e3a3-4da1-9319-9891a4f03123"

placeholders = db.query(TemplatePlaceholder).filter(
    TemplatePlaceholder.template_id == template_id
).all()

print(f"\n找到 {len(placeholders)} 个占位符\n")

for i, ph in enumerate(placeholders[:10], 1):
    print(f"{i}. {ph.placeholder_name}")
    print(f"   agent_analyzed: {ph.agent_analyzed}")
    print(f"   sql_validated: {ph.sql_validated}")
    print(f"   has_sql: {bool(ph.generated_sql)}")
    if ph.generated_sql:
        sql_preview = ph.generated_sql[:150].replace('\n', ' ')
        print(f"   SQL: {sql_preview}...")
    print()

db.close()
