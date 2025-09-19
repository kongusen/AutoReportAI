"""
图表构建工具（ECharts） - 骨架版

根据数据与映射生成 ECharts 配置，支持 bar/line/pie 基础图表
"""

from typing import Dict, Any, List
from datetime import datetime

from ..core.tools.registry import BaseTool
from ..types import ToolSafetyLevel


class ChartBuilderTool(BaseTool):
    """根据数据和映射生成 ECharts 配置"""

    def __init__(self):
        super().__init__(
            name="chart_builder",
            description="从 columns+rows 数据生成 ECharts 图表配置"
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        chart_type = (input_data.get("chart_type") or "bar").lower()
        data = input_data.get("data", {})
        mapping = input_data.get("mapping", {})
        options = input_data.get("options", {})

        columns: List[str] = data.get("columns", [])
        rows: List[List[Any]] = data.get("rows", [])

        # 简单容错
        if not columns or not rows:
            return {
                "success": False,
                "error": "Empty data for chart",
                "echarts_option": {},
                "timestamp": datetime.now().isoformat()
            }

        # 字段映射
        x_field = mapping.get("x")
        y_field = mapping.get("y")
        series_field = mapping.get("series")

        if chart_type in ("bar", "line"):
            if not x_field or not y_field:
                return {"success": False, "error": "x/y mapping required", "echarts_option": {}}
            x_idx = columns.index(x_field) if x_field in columns else None
            y_idx = columns.index(y_field) if y_field in columns else None
            if x_idx is None or y_idx is None:
                return {"success": False, "error": "x/y field not found", "echarts_option": {}}

            if series_field and series_field in columns:
                s_idx = columns.index(series_field)
                # 按 series 分组
                series_map: Dict[Any, List] = {}
                x_axis_vals: List[Any] = []
                for r in rows:
                    x_val = r[x_idx]
                    if x_val not in x_axis_vals:
                        x_axis_vals.append(x_val)
                    key = r[s_idx]
                    series_map.setdefault(key, []).append((x_val, r[y_idx]))
                # 对齐数据
                def build_series(name, points):
                    x_to_y = {x: y for x, y in points}
                    data_vals = [x_to_y.get(x) for x in x_axis_vals]
                    return {"name": name, "type": chart_type, "data": data_vals}
                series = [build_series(name, pts) for name, pts in series_map.items()]
                option = {
                    "title": {"text": options.get("title", "")},
                    "tooltip": {"trigger": "axis"},
                    "legend": {"data": list(series_map.keys())},
                    "xAxis": {"type": "category", "data": x_axis_vals},
                    "yAxis": {"type": "value"},
                    "series": series,
                }
            else:
                # 单序列
                x_axis_vals = [r[x_idx] for r in rows]
                y_vals = [r[y_idx] for r in rows]
                option = {
                    "title": {"text": options.get("title", "")},
                    "tooltip": {"trigger": "axis"},
                    "xAxis": {"type": "category", "data": x_axis_vals},
                    "yAxis": {"type": "value"},
                    "series": [{"type": chart_type, "data": y_vals}],
                }

        elif chart_type == "pie":
            if not x_field or not y_field:
                return {"success": False, "error": "x/y mapping required", "echarts_option": {}}
            x_idx = columns.index(x_field) if x_field in columns else None
            y_idx = columns.index(y_field) if y_field in columns else None
            if x_idx is None or y_idx is None:
                return {"success": False, "error": "x/y field not found", "echarts_option": {}}

            pie_data = [{"name": r[x_idx], "value": r[y_idx]} for r in rows]
            option = {
                "title": {"text": options.get("title", ""), "left": "center"},
                "tooltip": {"trigger": "item"},
                "legend": {"orient": "vertical", "left": "left"},
                "series": [{
                    "name": options.get("seriesName", ""),
                    "type": "pie",
                    "radius": "50%",
                    "data": pie_data,
                    "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0, 0, 0, 0.5)"}}
                }]
            }
        else:
            return {"success": False, "error": f"Unsupported chart_type: {chart_type}", "echarts_option": {}}

        return {
            "success": True,
            "echarts_option": option,
            "brief": {"type": chart_type, "columns": columns, "rows": len(rows)},
            "timestamp": datetime.now().isoformat(),
        }

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chart_type": {"type": "string", "enum": ["bar", "line", "pie"]},
                "data": {"type": "object"},
                "mapping": {"type": "object"},
                "options": {"type": "object"}
            },
            "required": ["chart_type", "data", "mapping"],
        }

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "echarts_option": {"type": "object"},
                "success": {"type": "boolean"},
                "error": {"type": "string"},
            },
            "required": ["echarts_option", "success"],
        }

    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.SAFE

    def get_capabilities(self) -> List[str]:
        return ["chart_building", "echarts_config"]

