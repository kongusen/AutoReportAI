#!/usr/bin/env python3
"""
Run an end-to-end PTOF (Plan-Tool-Observe-Finalize) flow using real Container services.

Usage:
  PYTHONPATH=backend backend/venv/bin/python backend/selftests/run_ptof.py \
    --user-id <USER_ID> --template-id <TPL_ID> --data-source-id <DS_ID> \
    --placeholder "占位符名称" --outcome sql|chart|report

Notes:
  - Requires DB configured (for templates/data sources) and LLM wired in Container.
  - Prints key intermediate JSON to help debug (plan steps, tool context keys, observations).
"""

import argparse
import asyncio
import json
from datetime import datetime

from app.services.application import AgentInputBridge


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--user-id", required=True)
    p.add_argument("--template-id", required=True)
    p.add_argument("--data-source-id", required=True)
    p.add_argument("--placeholder", required=True)
    p.add_argument("--outcome", default="sql", choices=["sql", "chart", "report"])
    p.add_argument("--cron", default="0 0 * * 1", help="cron expression")
    p.add_argument("--tz", default="Asia/Shanghai", help="timezone")
    p.add_argument("--offset", type=int, default=1, help="data period offset")
    return p.parse_args()


async def main():
    args = parse_args()

    bridge = AgentInputBridge()
    task_def = {
        "task_id": f"ptof_{args.placeholder}_{datetime.now().timestamp()}",
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

    print("=== Building AgentInput ===")
    build = await bridge.build_for_placeholder(
        user_id=args.user_id,
        template_id=args.template_id,
        data_source_id=args.data_source_id,
        placeholder_name=args.placeholder,
        task_definition=task_def,
        output_kind=args.outcome,
    )
    print("build.success:", build.get("success"))
    if build.get("errors"):
        print("errors:", build.get("errors"))
    if build.get("warnings"):
        print("warnings:", build.get("warnings"))
    print("dynamic_user_prompt:\n", build.get("dynamic_user_prompt"))

    print("\n=== Executing PTOF ===")
    exec_res = await bridge.execute_for_placeholder(
        user_id=args.user_id,
        template_id=args.template_id,
        data_source_id=args.data_source_id,
        placeholder_name=args.placeholder,
        task_definition=task_def,
        output_kind=args.outcome,
    )
    print("exec.success:", exec_res.get("success"))
    if exec_res.get("metadata"):
        print("metadata:", json.dumps(exec_res["metadata"], ensure_ascii=False)[:400])
    if not exec_res.get("success"):
        print("error:", exec_res.get("error"))


if __name__ == "__main__":
    asyncio.run(main())

