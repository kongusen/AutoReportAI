#!/usr/bin/env python3
"""
Find user=admin, locate yjg data source and template, then run PTOF.

Usage:
  PYTHONPATH=backend backend/venv/bin/python backend/selftests/find_yjg_and_run_ptof.py \
    --placeholder "占位符名称" --outcome sql|chart|report

Notes:
  - Searches users by username='admin' (falls back to email LIKE '%admin%').
  - Selects first template/data source whose name or display_name contains 'yjg' (case-insensitive).
"""

import argparse
import asyncio
import sys
from datetime import datetime

from app.db.session import get_db_session
from app.models.user import User
from app.models.data_source import DataSource
from app.models.template import Template
from app.services.application import AgentInputBridge


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--placeholder", required=True)
    p.add_argument("--outcome", default="sql", choices=["sql", "chart", "report"])
    p.add_argument("--cron", default="0 0 * * 1")
    p.add_argument("--tz", default="Asia/Shanghai")
    p.add_argument("--offset", type=int, default=1)
    return p.parse_args()


def find_admin_user():
    with get_db_session() as db:
        user = db.query(User).filter(User.username == 'admin').first()
        if not user:
            user = db.query(User).filter(User.email.ilike('%admin%')).first()
        if not user:
            raise SystemExit("Admin user not found (username='admin' or email LIKE '%admin%')")
        return user


def find_yjg_resources(user_id):
    with get_db_session() as db:
        # template: search name/description/original_filename
        tpl = db.query(Template).filter(
            Template.user_id == user_id,
            (
                Template.name.ilike('%yjg%') |
                Template.description.ilike('%yjg%') |
                Template.original_filename.ilike('%yjg%')
            )
        ).first()

        # datasource: search name/display_name/slug
        ds = db.query(DataSource).filter(
            DataSource.user_id == user_id,
            (
                DataSource.name.ilike('%yjg%') |
                DataSource.display_name.ilike('%yjg%') |
                DataSource.slug.ilike('%yjg%')
            )
        ).first()

        if not tpl or not ds:
            # Fallback: print top items for manual selection
            print("No 'yjg' resources found. Listing first 20 templates and data sources for admin:")
            tpls = db.query(Template).filter(Template.user_id == user_id).limit(20).all()
            print("\nTemplates (id, name):")
            for t in tpls:
                print("-", t.id, t.name)

            dss = db.query(DataSource).filter(DataSource.user_id == user_id).limit(20).all()
            print("\nDataSources (id, name, display_name, slug):")
            for d in dss:
                print("-", d.id, d.name, d.display_name, d.slug)

        if not tpl:
            raise SystemExit("No template containing 'yjg' found for admin user")
        if not ds:
            raise SystemExit("No data source containing 'yjg' found for admin user")
        return tpl, ds


async def run():
    args = parse_args()
    admin = find_admin_user()
    tpl, ds = find_yjg_resources(admin.id)
    print("User:", admin.id, admin.username or admin.email)
    print("Template:", tpl.id, tpl.name)
    print("DataSource:", ds.id, ds.name)

    bridge = AgentInputBridge()
    task_def = {
        "task_id": f"ptof_yjg_{args.placeholder}_{datetime.now().timestamp()}",
        "task_type": "custom_period",
        "placeholder_index": 0,
        "execution_context": {"placeholder_name": args.placeholder},
        "user_task_config": {
            "cron_expression": args.cron,
            "timezone": args.tz,
            "data_period_offset": args.offset,
            "current_execution_time": datetime.now().isoformat(),
        },
    }

    print("\n=== Build AgentInput ===")
    build = await bridge.build_for_placeholder(
        user_id=str(admin.id),
        template_id=str(tpl.id),
        data_source_id=str(ds.id),
        placeholder_name=args.placeholder,
        task_definition=task_def,
        output_kind=args.outcome,
    )
    print("build.success:", build.get("success"))
    if build.get("errors"):
        print("errors:", build.get("errors"))
    if build.get("warnings"):
        print("warnings:", build.get("warnings"))
    print("dynamic_user_prompt:\n", (build.get("dynamic_user_prompt") or "")[:800])

    print("\n=== Execute PTOF ===")
    exec_res = await bridge.execute_for_placeholder(
        user_id=str(admin.id),
        template_id=str(tpl.id),
        data_source_id=str(ds.id),
        placeholder_name=args.placeholder,
        task_definition=task_def,
        output_kind=args.outcome,
    )
    print("exec.success:", exec_res.get("success"))
    if not exec_res.get("success"):
        print("error:", exec_res.get("error"))


if __name__ == "__main__":
    asyncio.run(run())
