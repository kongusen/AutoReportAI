#!/usr/bin/env python3
"""
离线触发占位符重新解析以验证 CRUD 接口对 dict 的兼容性
"""

import sys
from app.db.session import get_db_session
from app.crud.crud_template import crud_template
from app.services.domain.placeholder.hybrid_placeholder_manager import create_hybrid_placeholder_manager


def main(template_id: str):
    with get_db_session() as db:
        tpl = crud_template.get(db, id=template_id)
        if not tpl:
            print(f"Template not found: {template_id}")
            sys.exit(1)
        manager = create_hybrid_placeholder_manager(db)
        result = manager.parse_and_store_placeholders(
            template_id=template_id,
            template_content=tpl.content or "",
            force_reparse=True,
        )
        print({
            "success": result.get("success"),
            "action": result.get("action"),
            "total_parsed": result.get("total_parsed"),
            "newly_stored": result.get("newly_stored"),
            "total_stored": result.get("total_stored"),
            "error": result.get("error"),
        })


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: reparse_test.py <template_id>")
        sys.exit(2)
    main(sys.argv[1])


