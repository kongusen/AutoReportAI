"""
数据变换工具（骨架版）

提供常用的数据整形能力：filter/sort/topk/groupby+agg
输入支持 columns+rows 或 records 两种形式；输出统一为 columns+rows
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ..core.tools.registry import BaseTool
from ..types import ToolSafetyLevel


def _to_tabular(input_data: Dict[str, Any]) -> Tuple[List[str], List[List[Any]]]:
    """将输入统一为 (columns, rows[[]]) 形式，支持 records(list[dict]) 或 columns+rows"""
    if "records" in input_data and isinstance(input_data["records"], list):
        records = input_data["records"]
        if not records:
            return [], []
        # 统一列顺序
        columns = list(records[0].keys())
        rows = [[rec.get(col) for col in columns] for rec in records]
        return columns, rows
    # 默认 columns+rows
    columns = input_data.get("columns", [])
    rows = input_data.get("rows", [])
    return columns, rows


def _from_tabular(columns: List[str], rows: List[List[Any]]) -> Dict[str, Any]:
    return {"columns": columns, "rows": rows, "row_count": len(rows)}


class DataTransformTool(BaseTool):
    """数据变换工具（filter/sort/topk/groupby+agg）"""

    def __init__(self):
        super().__init__(
            name="data_transform",
            description="对表格数据执行过滤、排序、TopK、分组聚合等操作"
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        columns, rows = _to_tabular(input_data)
        ops: List[Dict[str, Any]] = input_data.get("operations", [])
        meta: Dict[str, Any] = {"applied_ops": []}

        # 建列名->索引映射
        col_idx = {c: i for i, c in enumerate(columns)}

        try:
            table_rows = rows
            for op in ops:
                op_type = op.get("type")
                if op_type == "filter":
                    # 支持 eq/gt/lt/in 文本和数值基本过滤
                    field = op.get("field")
                    mode = op.get("mode", "eq")
                    value = op.get("value")
                    idx = col_idx.get(field)
                    if idx is None:
                        continue
                    if mode == "eq":
                        table_rows = [r for r in table_rows if r[idx] == value]
                    elif mode == "gt":
                        table_rows = [r for r in table_rows if (r[idx] is not None and r[idx] > value)]
                    elif mode == "lt":
                        table_rows = [r for r in table_rows if (r[idx] is not None and r[idx] < value)]
                    elif mode == "in":
                        allowed = set(value or [])
                        table_rows = [r for r in table_rows if r[idx] in allowed]
                    meta["applied_ops"].append({"filter": op})

                elif op_type == "sort":
                    field = op.get("field")
                    descending = bool(op.get("desc", True))
                    idx = col_idx.get(field)
                    if idx is None:
                        continue
                    table_rows = sorted(table_rows, key=lambda r: (r[idx] is None, r[idx]), reverse=descending)
                    meta["applied_ops"].append({"sort": op})

                elif op_type == "topk":
                    field = op.get("field")
                    k = int(op.get("k", 10))
                    descending = bool(op.get("desc", True))
                    idx = col_idx.get(field)
                    if idx is None:
                        continue
                    table_rows = sorted(table_rows, key=lambda r: (r[idx] is None, r[idx]), reverse=descending)[:k]
                    meta["applied_ops"].append({"topk": op})

                elif op_type in ("groupby", "agg"):
                    group_by = op.get("group_by", [])
                    aggs = op.get("aggregations", [])  # [{field, op}]
                    # 构建 group key
                    gb_idx = [col_idx[g] for g in group_by if g in col_idx]
                    groups: Dict[Tuple[Any, ...], List[List[Any]]] = {}
                    for r in table_rows:
                        key = tuple(r[i] for i in gb_idx)
                        groups.setdefault(key, []).append(r)
                    # 输出列
                    out_cols = list(group_by)
                    for agg in aggs:
                        out_cols.append(f"{agg.get('op','sum')}_{agg.get('field','value')}")
                    out_rows: List[List[Any]] = []
                    for key, items in groups.items():
                        row = list(key)
                        for agg in aggs:
                            f = agg.get("field")
                            op_name = (agg.get("op") or "sum").lower()
                            fidx = col_idx.get(f)
                            series = [it[fidx] for it in items if fidx is not None]
                            val = None
                            if op_name == "sum":
                                val = sum(x for x in series if isinstance(x, (int, float)))
                            elif op_name in ("avg", "mean"):
                                nums = [x for x in series if isinstance(x, (int, float))]
                                val = (sum(nums) / len(nums)) if nums else None
                            elif op_name == "count":
                                val = len(series)
                            elif op_name == "max":
                                val = max(series) if series else None
                            elif op_name == "min":
                                val = min(series) if series else None
                            else:
                                val = None
                            row.append(val)
                        out_rows.append(row)
                    # 应用新表
                    columns = out_cols
                    table_rows = out_rows
                    col_idx = {c: i for i, c in enumerate(columns)}
                    meta["applied_ops"].append({"groupby": op})

                else:
                    # 占位：yoy/mom/pivot 等后续扩展
                    meta.setdefault("warnings", []).append({"op": op_type, "status": "not_implemented"})

            result = _from_tabular(columns, table_rows)
            result["meta"] = meta
            result["success"] = True
            result["timestamp"] = datetime.now().isoformat()
            return result
        except Exception as e:
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "meta": meta,
            }

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}},
                "rows": {"type": "array", "items": {"type": "array"}},
                "records": {"type": "array", "items": {"type": "object"}},
                "operations": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["operations"],
        }

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}},
                "rows": {"type": "array", "items": {"type": "array"}},
                "row_count": {"type": "integer"},
                "meta": {"type": "object"},
                "success": {"type": "boolean"},
                "error": {"type": "string"},
            },
            "required": ["columns", "rows", "success"],
        }

    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.SAFE

    def get_capabilities(self) -> List[str]:
        return ["data_transform", "aggregation", "filtering", "sorting"]

