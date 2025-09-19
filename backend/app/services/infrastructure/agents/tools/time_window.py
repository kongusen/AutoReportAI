"""
时间窗口注入工具（SQL） - 骨架版

根据任务上下文或参数，将时间窗口/粒度/数据域注入到 SQL 中
注：为安全与简化，采用字符串注入策略；后续可替换为 SQL AST
"""

from typing import Dict, Any, Optional
import re
from datetime import datetime, timedelta, date

from ..core.tools.registry import BaseTool
from ..types import ToolSafetyLevel


def _date_range_from_preset(preset: str) -> Optional[Dict[str, str]]:
    today = date.today()
    if preset == "last_7d":
        start = today - timedelta(days=7)
        end = today
    elif preset == "last_30d":
        start = today - timedelta(days=30)
        end = today
    elif preset == "this_month":
        start = today.replace(day=1)
        end = today
    else:
        return None
    return {"start": f"{start} 00:00:00", "end": f"{end} 23:59:59"}


def _inject_where(sql: str, clause: str) -> str:
    """将 WHERE/AND 子句插入到合适位置（在 ORDER/GROUP/LIMIT 等之前）"""
    s = (sql or "").strip().rstrip(";\n ")
    lower = s.lower()

    # 确定插入位置：在 ORDER BY/GROUP BY/LIMIT/OFFSET/FETCH 等子句之前（忽略大小写与前导空白）
    tokens = ["order by", "group by", "limit", "offset", "fetch"]
    cut_pos = len(s)
    for token in tokens:
        idx = lower.find(token)
        if idx != -1:
            cut_pos = min(cut_pos, idx)

    head = s[:cut_pos]
    tail = s[cut_pos:]

    head_lower = head.lower()
    has_where = re.search(r"\bwhere\b", head_lower) is not None
    if has_where:
        head = head + f" AND {clause}"
    else:
        head = head + f" WHERE {clause}"
    # 确保与后续子句之间有空格
    if tail and not tail[:1].isspace():
        return head + " " + tail
    return head + tail


class TimeWindowAdjustTool(BaseTool):
    """时间窗口与数据域注入工具"""

    def __init__(self):
        super().__init__(
            name="time_window",
            description="将时间窗口/粒度/数据域条件注入 SQL 查询"
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        sql = (input_data.get("sql_query") or "").strip()
        time_column = input_data.get("time_column", "created_at")
        window = input_data.get("window", {})  # {start,end} or {preset}
        granularity = input_data.get("granularity")  # day/week/month
        data_scope = input_data.get("data_scope")  # 业务侧附加域

        if not sql:
            return {"success": False, "error": "Empty sql_query"}

        # 解析窗口
        start, end = window.get("start"), window.get("end")
        if not (start and end) and window.get("preset"):
            rng = _date_range_from_preset(window.get("preset"))
            if rng:
                start, end = rng["start"], rng["end"]

        hints = {"applied": []}
        if start and end:
            clause = f"{time_column} BETWEEN '{start}' AND '{end}'"
            sql = _inject_where(sql, clause)
            hints["applied"].append({"time_window": {"start": start, "end": end}})
        else:
            hints.setdefault("warnings", []).append("no_time_window_applied")

        # data_scope 可选注入（简单等值/IN 列表）
        if isinstance(data_scope, dict):
            for k, v in data_scope.items():
                if isinstance(v, list):
                    values = ", ".join([f"'{str(x)}'" for x in v])
                    clause = f"{k} IN ({values})"
                else:
                    clause = f"{k} = '{str(v)}'"
                sql = _inject_where(sql, clause)
            hints["applied"].append({"data_scope": list(data_scope.keys())})

        # 粒度信息仅作为提示返回，实际聚合由上游 SQL/下游 transform 决定
        if granularity:
            hints["granularity"] = granularity

        return {
            "success": True,
            "sql_query_adjusted": sql,
            "hints": hints,
            "timestamp": datetime.now().isoformat(),
        }

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql_query": {"type": "string"},
                "time_column": {"type": "string"},
                "window": {"type": "object"},
                "granularity": {"type": "string"},
                "data_scope": {"type": "object"},
            },
            "required": ["sql_query"],
        }

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql_query_adjusted": {"type": "string"},
                "hints": {"type": "object"},
                "success": {"type": "boolean"},
                "error": {"type": "string"},
            },
            "required": ["success"],
        }

    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.SAFE

    def get_capabilities(self):
        return ["sql_time_window", "scope_injection"]
