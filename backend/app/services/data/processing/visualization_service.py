from typing import Any, Dict, List, Optional, Union
import json
import logging
from enum import Enum
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """支持的图表类型枚举"""
    BAR = "bar_chart"
    PIE = "pie_chart" 
    LINE = "line_chart"
    SCATTER = "scatter_chart"
    RADAR = "radar_chart"
    FUNNEL = "funnel_chart"


class OutputFormat(Enum):
    """支持的输出格式"""
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"
    JSON = "json"
    BASE64 = "base64"


class VisualizationService:
    """
    完善的数据可视化服务
    支持6种图表类型和多种输出格式
    """

    def __init__(self):
        """初始化可视化服务"""
        self.supported_chart_types = {
            ChartType.BAR: self._generate_bar_chart,
            ChartType.PIE: self._generate_pie_chart,
            ChartType.LINE: self._generate_line_chart,
            ChartType.SCATTER: self._generate_scatter_chart,
            ChartType.RADAR: self._generate_radar_chart,
            ChartType.FUNNEL: self._generate_funnel_chart,
        }

    def generate_chart(
        self,
        data: List[Dict[str, Any]],
        chart_type: str,
        config: Dict[str, Any],
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        生成图表的统一入口方法
        
        Args:
            data: 数据列表
            chart_type: 图表类型 (bar_chart, pie_chart, line_chart, scatter_chart, radar_chart, funnel_chart)
            config: 图表配置
            output_format: 输出格式 (json, png, svg, pdf, base64)
            
        Returns:
            图表生成结果
        """
        try:
            if not data:
                return {"success": False, "error": "No data provided for chart generation"}

            df = pd.DataFrame(data)
            
            # 验证图表类型
            try:
                chart_type_enum = ChartType(chart_type)
            except ValueError:
                return {
                    "success": False, 
                    "error": f"Unsupported chart type: {chart_type}. Supported types: {[ct.value for ct in ChartType]}"
                }

            # 生成图表配置
            generator = self.supported_chart_types[chart_type_enum]
            chart_config = generator(df, config)
            
            if not chart_config.get("success", True):
                return chart_config

            # 根据输出格式处理结果
            if output_format == "json":
                return {
                    "success": True,
                    "chart_type": chart_type,
                    "chart_config": chart_config,
                    "echarts_config": chart_config.get("echarts_config"),
                    "metadata": {
                        "data_points": len(data),
                        "generated_at": pd.Timestamp.now().isoformat()
                    }
                }
            elif output_format in ["png", "svg", "pdf", "base64"]:
                # 生成图像
                image_result = self.create_chart_image(df, chart_type, config, output_format)
                return {
                    "success": image_result.get("success", True),
                    "chart_type": chart_type,
                    "chart_config": chart_config,
                    "image_data": image_result.get("image_data"),
                    "image_path": image_result.get("image_path"),
                    "metadata": {
                        "data_points": len(data),
                        "output_format": output_format,
                        "generated_at": pd.Timestamp.now().isoformat()
                    },
                    "error": image_result.get("error")
                }
            else:
                return {"success": False, "error": f"Unsupported output format: {output_format}"}
                
        except Exception as e:
            logger.error(f"Chart generation failed: {str(e)}")
            return {"success": False, "error": f"Chart generation failed: {str(e)}"}

    def generate_bar_chart(
        self, data: List[Dict[str, Any]], x_column: str, y_column: str, title: str
    ) -> Dict[str, Any]:
        """
        生成柱状图 (保持向后兼容)
        """
        config = {
            "title": title,
            "x_column": x_column,
            "y_column": y_column
        }
        return self.generate_chart(data, ChartType.BAR.value, config)

    def _generate_bar_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """生成柱状图配置"""
        try:
            x_column = config.get("x_column")
            y_column = config.get("y_column") 
            title = config.get("title", "Bar Chart")
            
            if not x_column or not y_column:
                return {"success": False, "error": "Missing x_column or y_column in config"}
                
            if x_column not in df.columns or y_column not in df.columns:
                return {"success": False, "error": f"Columns '{x_column}' or '{y_column}' not found in data"}
            
            # ECharts配置
            echarts_config = {
                "title": {"text": title},
                "tooltip": {},
                "xAxis": {
                    "type": "category",
                    "data": df[x_column].tolist()
                },
                "yAxis": {"type": "value"},
                "series": [{
                    "name": title,
                    "type": "bar",
                    "data": df[y_column].tolist()
                }]
            }
            
            return {
                "success": True,
                "type": "bar",
                "title": title,
                "labels": df[x_column].tolist(),
                "datasets": [{
                    "label": title,
                    "data": df[y_column].tolist(),
                }],
                "echarts_config": echarts_config
            }
        except Exception as e:
            return {"success": False, "error": f"Bar chart generation failed: {str(e)}"}

    def _generate_pie_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """生成饼图配置"""
        try:
            label_column = config.get("label_column") or config.get("x_column")
            value_column = config.get("value_column") or config.get("y_column")
            title = config.get("title", "Pie Chart")
            
            if not label_column or not value_column:
                return {"success": False, "error": "Missing label_column or value_column in config"}
                
            if label_column not in df.columns or value_column not in df.columns:
                return {"success": False, "error": f"Columns '{label_column}' or '{value_column}' not found in data"}
            
            # 准备饼图数据
            pie_data = []
            for _, row in df.iterrows():
                pie_data.append({
                    "name": str(row[label_column]),
                    "value": float(row[value_column])
                })
            
            # ECharts配置
            echarts_config = {
                "title": {"text": title},
                "tooltip": {
                    "trigger": "item",
                    "formatter": "{a} <br/>{b} : {c} ({d}%)"
                },
                "series": [{
                    "name": title,
                    "type": "pie",
                    "radius": "50%",
                    "data": pie_data
                }]
            }
            
            return {
                "success": True,
                "type": "pie",
                "title": title,
                "labels": df[label_column].tolist(),
                "data": df[value_column].tolist(),
                "echarts_config": echarts_config
            }
        except Exception as e:
            return {"success": False, "error": f"Pie chart generation failed: {str(e)}"}

    def _generate_line_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """生成折线图配置"""
        try:
            x_column = config.get("x_column")
            y_column = config.get("y_column")
            title = config.get("title", "Line Chart")
            
            if not x_column or not y_column:
                return {"success": False, "error": "Missing x_column or y_column in config"}
                
            if x_column not in df.columns or y_column not in df.columns:
                return {"success": False, "error": f"Columns '{x_column}' or '{y_column}' not found in data"}
            
            # ECharts配置
            echarts_config = {
                "title": {"text": title},
                "tooltip": {"trigger": "axis"},
                "xAxis": {
                    "type": "category",
                    "data": df[x_column].tolist()
                },
                "yAxis": {"type": "value"},
                "series": [{
                    "name": title,
                    "type": "line",
                    "data": df[y_column].tolist()
                }]
            }
            
            return {
                "success": True,
                "type": "line",
                "title": title,
                "labels": df[x_column].tolist(),
                "datasets": [{
                    "label": title,
                    "data": df[y_column].tolist(),
                }],
                "echarts_config": echarts_config
            }
        except Exception as e:
            return {"success": False, "error": f"Line chart generation failed: {str(e)}"}

    def _generate_scatter_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """生成散点图配置"""
        try:
            x_column = config.get("x_column")
            y_column = config.get("y_column")
            title = config.get("title", "Scatter Chart")
            
            if not x_column or not y_column:
                return {"success": False, "error": "Missing x_column or y_column in config"}
                
            if x_column not in df.columns or y_column not in df.columns:
                return {"success": False, "error": f"Columns '{x_column}' or '{y_column}' not found in data"}
            
            # 准备散点图数据
            scatter_data = []
            for _, row in df.iterrows():
                scatter_data.append([float(row[x_column]), float(row[y_column])])
            
            # ECharts配置
            echarts_config = {
                "title": {"text": title},
                "tooltip": {"trigger": "item"},
                "xAxis": {
                    "type": "value",
                    "name": x_column
                },
                "yAxis": {
                    "type": "value", 
                    "name": y_column
                },
                "series": [{
                    "name": title,
                    "type": "scatter",
                    "data": scatter_data
                }]
            }
            
            return {
                "success": True,
                "type": "scatter",
                "title": title,
                "data": scatter_data,
                "echarts_config": echarts_config
            }
        except Exception as e:
            return {"success": False, "error": f"Scatter chart generation failed: {str(e)}"}

    def _generate_radar_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """生成雷达图配置"""
        try:
            dimensions = config.get("dimensions", [])
            name_column = config.get("name_column")
            title = config.get("title", "Radar Chart")
            
            if not dimensions:
                # 自动检测数值列作为维度
                numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
                if len(numeric_columns) < 3:
                    return {"success": False, "error": "Radar chart requires at least 3 numeric dimensions"}
                dimensions = numeric_columns[:6]  # 最多取6个维度
            
            # 验证维度列存在
            missing_dims = [dim for dim in dimensions if dim not in df.columns]
            if missing_dims:
                return {"success": False, "error": f"Dimensions not found in data: {missing_dims}"}
            
            # 准备雷达图指标配置
            indicators = []
            for dim in dimensions:
                max_val = float(df[dim].max())
                indicators.append({
                    "name": dim,
                    "max": max_val * 1.1  # 稍微放大范围
                })
            
            # 准备数据
            radar_data = []
            for _, row in df.iterrows():
                data_point = {
                    "name": str(row[name_column]) if name_column and name_column in df.columns else f"Item {_+1}",
                    "value": [float(row[dim]) for dim in dimensions]
                }
                radar_data.append(data_point)
            
            # ECharts配置
            echarts_config = {
                "title": {"text": title},
                "tooltip": {},
                "radar": {
                    "indicator": indicators
                },
                "series": [{
                    "name": title,
                    "type": "radar",
                    "data": radar_data
                }]
            }
            
            return {
                "success": True,
                "type": "radar",
                "title": title,
                "dimensions": dimensions,
                "data": radar_data,
                "echarts_config": echarts_config
            }
        except Exception as e:
            return {"success": False, "error": f"Radar chart generation failed: {str(e)}"}

    def _generate_funnel_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """生成漏斗图配置"""
        try:
            stage_column = config.get("stage_column") or config.get("x_column")
            value_column = config.get("value_column") or config.get("y_column") 
            title = config.get("title", "Funnel Chart")
            
            if not stage_column or not value_column:
                return {"success": False, "error": "Missing stage_column or value_column in config"}
                
            if stage_column not in df.columns or value_column not in df.columns:
                return {"success": False, "error": f"Columns '{stage_column}' or '{value_column}' not found in data"}
            
            # 按值降序排列 (漏斗图特征)
            df_sorted = df.sort_values(value_column, ascending=False)
            
            # 准备漏斗图数据
            funnel_data = []
            for _, row in df_sorted.iterrows():
                funnel_data.append({
                    "name": str(row[stage_column]),
                    "value": float(row[value_column])
                })
            
            # ECharts配置
            echarts_config = {
                "title": {"text": title},
                "tooltip": {
                    "trigger": "item",
                    "formatter": "{a} <br/>{b} : {c}"
                },
                "series": [{
                    "name": title,
                    "type": "funnel",
                    "left": "10%",
                    "top": 60,
                    "bottom": 60,
                    "width": "80%",
                    "data": funnel_data
                }]
            }
            
            return {
                "success": True,
                "type": "funnel",
                "title": title,
                "stages": df_sorted[stage_column].tolist(),
                "values": df_sorted[value_column].tolist(),
                "data": funnel_data,
                "echarts_config": echarts_config
            }
        except Exception as e:
            return {"success": False, "error": f"Funnel chart generation failed: {str(e)}"}

    def create_chart_image(
        self,
        df: pd.DataFrame,
        chart_type: str,
        config: Dict[str, Any],
        output_format: str = "png"
    ) -> Dict[str, Any]:
        """
        创建图表图像
        
        Args:
            df: 数据DataFrame
            chart_type: 图表类型
            config: 图表配置
            output_format: 输出格式 (png, svg, pdf, base64)
            
        Returns:
            图像生成结果
        """
        import base64
        import io
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.patches import Wedge

        try:
            # 设置中文字体支持
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            title = config.get("title", "Chart")
            
            if chart_type == "bar_chart":
                x_column = config.get("x_column")
                y_column = config.get("y_column")
                ax.bar(df[x_column], df[y_column])
                ax.set_xlabel(x_column)
                ax.set_ylabel(y_column)
                plt.xticks(rotation=45, ha="right")
                
            elif chart_type == "pie_chart":
                label_column = config.get("label_column") or config.get("x_column")
                value_column = config.get("value_column") or config.get("y_column")
                ax.pie(df[value_column], labels=df[label_column], autopct='%1.1f%%')
                
            elif chart_type == "line_chart":
                x_column = config.get("x_column")
                y_column = config.get("y_column")
                ax.plot(df[x_column], df[y_column], marker='o')
                ax.set_xlabel(x_column)
                ax.set_ylabel(y_column)
                plt.xticks(rotation=45, ha="right")
                
            elif chart_type == "scatter_chart":
                x_column = config.get("x_column")
                y_column = config.get("y_column")
                ax.scatter(df[x_column], df[y_column])
                ax.set_xlabel(x_column)
                ax.set_ylabel(y_column)
                
            elif chart_type == "radar_chart":
                dimensions = config.get("dimensions", [])
                if not dimensions:
                    dimensions = df.select_dtypes(include=['number']).columns.tolist()[:6]
                
                # 简化的雷达图实现
                angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
                angles += angles[:1]  # 闭合
                
                ax.set_theta_offset(np.pi / 2)
                ax.set_theta_direction(-1)
                ax.set_thetagrids(np.degrees(angles[:-1]), dimensions)
                
                for idx, row in df.iterrows():
                    values = [float(row[dim]) for dim in dimensions]
                    values += values[:1]  # 闭合
                    ax.plot(angles, values, 'o-', label=f'Item {idx+1}')
                    ax.fill(angles, values, alpha=0.25)
                
                ax.legend()
                
            elif chart_type == "funnel_chart":
                stage_column = config.get("stage_column") or config.get("x_column")
                value_column = config.get("value_column") or config.get("y_column")
                
                # 简化的漏斗图实现 (使用水平条形图)
                df_sorted = df.sort_values(value_column, ascending=True)  # matplotlib中从下往上
                y_pos = np.arange(len(df_sorted))
                ax.barh(y_pos, df_sorted[value_column])
                ax.set_yticks(y_pos)
                ax.set_yticklabels(df_sorted[stage_column])
                ax.set_xlabel(value_column)
                
            else:
                # 默认柱状图
                x_column = config.get("x_column")
                y_column = config.get("y_column")
                if x_column and y_column:
                    ax.bar(df[x_column], df[y_column])
                    ax.set_xlabel(x_column)
                    ax.set_ylabel(y_column)

            ax.set_title(title)
            plt.tight_layout()

            # 保存图像
            if output_format == "base64":
                buffer = io.BytesIO()
                plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
                plt.close(fig)
                
                return {
                    "success": True,
                    "image_data": image_base64,
                    "format": "base64"
                }
            else:
                # 保存到文件
                output_path = f"/tmp/chart_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"
                plt.savefig(output_path, format=output_format, dpi=300, bbox_inches="tight")
                plt.close(fig)
                
                return {
                    "success": True,
                    "image_path": output_path,
                    "format": output_format
                }

        except Exception as e:
            plt.close(fig)
            return {
                "success": False,
                "error": f"Chart image generation failed: {str(e)}"
            }
