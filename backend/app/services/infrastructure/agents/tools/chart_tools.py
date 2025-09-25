"""
图表相关工具

提供图表配置生成和图表渲染功能
"""

import logging
from typing import Dict, Any, List

from .base import Tool


class ChartSpecTool(Tool):
    """图表配置生成工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "chart.spec"
        self.description = "基于数据生成图表配置"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成图表配置"""
        try:
            # 从执行结果中获取数据
            execution_result = input_data.get("execution_result", {})
            rows = execution_result.get("rows", [])
            columns = execution_result.get("columns", [])
            placeholder_desc = input_data.get("placeholder_description", "")

            if not rows or not columns:
                return {"success": False, "error": "没有可用的数据生成图表"}

            # 分析数据结构
            chart_type = self._determine_chart_type(rows, columns, placeholder_desc)
            chart_spec = self._generate_chart_spec(rows, columns, chart_type, placeholder_desc)

            return {
                "success": True,
                "chart_spec": chart_spec,
                "chart_type": chart_type,
                "data_rows": len(rows),
                "data_columns": len(columns)
            }

        except Exception as e:
            self._logger.error(f"图表配置生成失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _determine_chart_type(self, rows: List[List], columns: List[str], description: str) -> str:
        """确定图表类型"""
        description_lower = description.lower()

        # 根据描述关键词判断
        if any(word in description_lower for word in ["饼图", "pie", "占比", "比例"]):
            return "pie"
        elif any(word in description_lower for word in ["线图", "line", "趋势", "变化"]):
            return "line"
        elif any(word in description_lower for word in ["柱状图", "bar", "柱图", "对比"]):
            return "bar"
        elif any(word in description_lower for word in ["散点图", "scatter", "分布"]):
            return "scatter"

        # 根据数据结构判断
        if len(columns) == 2:
            # 两列数据，默认柱状图
            return "bar"
        elif len(columns) > 2:
            # 多列数据，使用线图
            return "line"
        else:
            # 默认柱状图
            return "bar"

    def _generate_chart_spec(self, rows: List[List], columns: List[str], chart_type: str, title: str) -> Dict[str, Any]:
        """生成图表配置"""
        if len(columns) < 2:
            # 数据不足，生成简单配置
            return {
                "type": "bar",
                "title": title or "数据图表",
                "data": [],
                "error": "数据列数不足"
            }

        # 转换数据格式
        chart_data = []
        x_field = columns[0]
        y_field = columns[1]

        for row in rows:
            if len(row) >= 2:
                chart_data.append({
                    x_field: row[0],
                    y_field: row[1]
                })

        # 生成图表配置
        chart_spec = {
            "type": chart_type,
            "title": title or "数据图表",
            "theme": "enterprise-light",
            "style": {
                "palette": ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"],
                "fontFamily": "Inter, -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial",
                "axis": {
                    "labelColor": "#374151",
                    "gridColor": "#e5e7eb"
                },
                "legend": {
                    "position": "top-right"
                }
            },
            "xField": x_field,
            "yField": y_field,
            "data": chart_data
        }

        # 特殊配置
        if chart_type == "pie":
            chart_spec.update({
                "angleField": y_field,
                "colorField": x_field
            })
        elif chart_type == "line":
            chart_spec.update({
                "smooth": True,
                "point": {
                    "size": 4,
                    "shape": "circle"
                }
            })

        return chart_spec


class WordChartGeneratorTool(Tool):
    """Word文档图表生成工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "word_chart_generator"
        self.description = "将ETL数据生成可插入Word的图表图片"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成Word图表图片"""
        try:
            chart_spec = input_data.get("chart_spec", {})
            if not chart_spec:
                return {"success": False, "error": "缺少图表配置"}

            # 生成图表图片
            chart_result = await self._generate_chart_image(chart_spec, input_data)

            return {
                "success": True,
                "chart_image_path": chart_result["image_path"],
                "chart_image_base64": chart_result.get("image_base64", ""),
                "chart_title": chart_spec.get("title", "数据图表"),
                "chart_type": chart_spec.get("type", "bar")
            }

        except Exception as e:
            self._logger.error(f"图表图片生成失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _generate_chart_image(self, chart_spec: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """生成图表图片"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            import os
            import base64
            import io
            from datetime import datetime

            # 设置中文字体支持
            matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial']
            matplotlib.rcParams['axes.unicode_minus'] = False

            # 创建图表
            fig, ax = plt.subplots(figsize=(10, 6))

            chart_type = chart_spec.get("type", "bar")
            data = chart_spec.get("data", [])
            title = chart_spec.get("title", "数据图表")

            if not data:
                ax.text(0.5, 0.5, "暂无数据", transform=ax.transAxes, ha="center", va="center")
            else:
                x_field = chart_spec.get("xField", "x")
                y_field = chart_spec.get("yField", "y")

                x_values = [item.get(x_field, "") for item in data]
                y_values = [float(item.get(y_field, 0)) for item in data]

                if chart_type == "bar":
                    bars = ax.bar(x_values, y_values, color="#2563eb", alpha=0.8)
                    ax.set_xlabel(x_field)
                    ax.set_ylabel(y_field)
                elif chart_type == "line":
                    ax.plot(x_values, y_values, marker="o", linewidth=2, markersize=6, color="#10b981")
                    ax.set_xlabel(x_field)
                    ax.set_ylabel(y_field)
                elif chart_type == "pie":
                    ax.pie(y_values, labels=x_values, autopct="%1.1f%%", startangle=90)
                    ax.axis("equal")

            ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
            plt.tight_layout()

            # 保存图片
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            placeholder_id = context.get("placeholder", {}).get("id", "chart")
            filename = f"chart_{placeholder_id}_{timestamp}.png"

            # 确保charts目录存在
            charts_dir = "./charts"
            os.makedirs(charts_dir, exist_ok=True)
            image_path = os.path.join(charts_dir, filename)

            # 保存到文件
            plt.savefig(image_path, dpi=300, bbox_inches="tight", facecolor="white")

            # 生成base64编码
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight", facecolor="white")
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            buffer.close()

            plt.close()

            return {
                "image_path": image_path,
                "image_base64": image_base64
            }

        except Exception as e:
            self._logger.error(f"图表图片生成异常: {str(e)}")
            # 返回一个占位符图片路径
            return {
                "image_path": "./charts/placeholder_chart.png",
                "image_base64": ""
            }