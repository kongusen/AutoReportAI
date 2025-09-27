"""
Lightweight JSON helpers and schema-like normalizers for PTAV pipeline.

Goals:
- Parse LLM JSON safely and normalize shapes
- Provide stable plan/step/result structures
- Avoid external dependencies (jsonschema)
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


PTAV_VERSION = "1.0"


def parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    """Try to parse a JSON object from text; returns None if fails."""
    if not text:
        return None
    t = text.strip()
    try:
        if t.startswith("```json"):
            t = t.replace("```json", "").replace("```", "").strip()
        if t.startswith("{") and t.endswith("}"):
            return json.loads(t)
        # Try extract best-effort JSON substring
        start = t.find("{")
        end = t.rfind("}")
        if start >= 0 and end >= 0 and end > start:
            return json.loads(t[start : end + 1])
    except Exception:
        return None
    return None


def normalize_plan(plan: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normalize a plan into a stable shape.

    Required keys:
    - thought: str
    - current_state: str
    - steps: [ { action, tool?, reason, input } ]
    - expected_outcome: str (sql|schema_info|chart|...)
    """
    if not isinstance(plan, dict):
        return None

    normalized: Dict[str, Any] = {
        "version": PTAV_VERSION,
        "thought": str(plan.get("thought", "")).strip(),
        "current_state": str(plan.get("current_state", "")).strip(),
        "expected_outcome": str(plan.get("expected_outcome", "")).strip() or "sql",
        "steps": [],
    }

    steps = plan.get("steps") or []
    if not isinstance(steps, list) or not steps:
        return None

    for s in steps:
        if not isinstance(s, dict):
            continue
        action = (s.get("action") or "tool_call").strip()
        step = {
            "action": action,
            "tool": s.get("tool") if action == "tool_call" else s.get("tool"),
            "reason": s.get("reason", ""),
            "input": s.get("input", {}) if isinstance(s.get("input"), dict) else {},
        }
        normalized["steps"].append(step)

    if not normalized["steps"]:
        return None

    return normalized


def normalize_tool_result(tool_name: str, result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Ensure a tool result dict has stable keys.

    Returns dict with at least:
    - success: bool
    - error: Optional[str]
    - message: Optional[str]
    - action: Optional[str]
    """
    r = result if isinstance(result, dict) else {}
    success = bool(r.get("success")) if "success" in r else ("error" not in r)
    out = {
        "version": PTAV_VERSION,
        "success": success,
        "error": r.get("error"),
        "message": r.get("message"),
        "action": r.get("action"),
    }
    # merge-through remaining keys without overriding normalized keys
    for k, v in r.items():
        if k not in out:
            out[k] = v
    return out


def is_transient_error(err: Optional[str]) -> bool:
    if not err:
        return False
    e = str(err).lower()
    signals = [
        "timeout",
        "timed out",
        "connection",
        "network",
        "rate limit",
        "429",
        "502",
        "503",
        "504",
        "temporary",
        "transient",
        "retry",
    ]
    return any(sig in e for sig in signals)

