from __future__ import annotations

from loom.interfaces.tool import BaseTool
"""
图表生成工具

基于数据生成各种类型的图表
支持柱状图、折线图、饼图、散点图等
"""


import logging
import json
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class ChartType(str, Enum):
    """图表类型"""
    BAR = "bar"                 # 柱状图
    LINE = "line"               # 折线图
    PIE = "pie"                 # 饼图
    SCATTER = "scatter"         # 散点图
    AREA = "area"               # 面积图
    HISTOGRAM = "histogram"     # 直方图
    BOX = "box"                 # 箱线图
    HEATMAP = "heatmap"         # 热力图
    RADAR = "radar"             # 雷达图
    GAUGE = "gauge"             # 仪表盘


class ChartTheme(str, Enum):
    """图表主题"""
    LIGHT = "light"
    DARK = "dark"
    COLORFUL = "colorful"
    MINIMAL = "minimal"


@dataclass
class ChartConfig:
    """图表配置"""
    chart_type: ChartType
    title: str
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    color_column: Optional[str] = None
    size_column: Optional[str] = None
    theme: ChartTheme = ChartTheme.LIGHT
    width: int = 800
    height: int = 600
    show_legend: bool = True
    show_grid: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ChartResult:
    """图表结果"""
    chart_config: ChartConfig
    chart_data: Dict[str, Any]
    chart_options: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ChartGeneratorTool(BaseTool):
    """图表生成工具"""
    
    def __init__(self, container: Any):
        """
        Args:
            container: 服务容器
        """
        super().__init__()

        self.name = "chart_generator"

        self.category = ToolCategory.CHART

        self.description = "基于数据生成各种类型的图表" 
        self.container = container
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class ChartGeneratorArgs(BaseModel):
            data: List[Dict[str, Any]] = Field(description="要可视化的数据")
            chart_type: Literal["bar", "line", "pie", "scatter", "area", "histogram", "box", "heatmap", "radar", "gauge"] = Field(
                default="bar", description="图表类型"
            )
            title: Optional[str] = Field(default=None, description="图表标题")
            x_axis: Optional[str] = Field(default=None, description="X轴列名")
            y_axis: Optional[str] = Field(default=None, description="Y轴列名")
            color_column: Optional[str] = Field(default=None, description="颜色分组列名")
            size_column: Optional[str] = Field(default=None, description="大小映射列名")
            theme: Literal["light", "dark", "colorful", "minimal"] = Field(
                default="light", description="图表主题"
            )
            width: int = Field(default=800, description="图表宽度")
            height: int = Field(default=600, description="图表高度")
            show_legend: bool = Field(default=True, description="是否显示图例")
            show_grid: bool = Field(default=True, description="是否显示网格")
            auto_detect_axes: bool = Field(default=True, description="是否自动检测坐标轴")

        self.args_schema = ChartGeneratorArgs
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "chart_generator",
                "description": "基于数据生成各种类型的图表",
                "parameters": parameters,
            },
        }
    
    async def run(

    
        self,
        data: List[Dict[str, Any]],
        chart_type: str = "bar",
        title: Optional[str] = None,
        x_axis: Optional[str] = None,
        y_axis: Optional[str] = None,
        color_column: Optional[str] = None,
        size_column: Optional[str] = None,
        theme: str = "light",
        width: int = 800,
        height: int = 600,
        show_legend: bool = True,
        show_grid: bool = True,
        auto_detect_axes: bool = True,
        **kwargs
    

    
    ) -> Dict[str, Any]:
        """
        执行图表生成

    Args:
            data: 要可视化的数据
            chart_type: 图表类型
            title: 图表标题
            x_axis: X轴列名
            y_axis: Y轴列名
            color_column: 颜色分组列名
            size_column: 大小映射列名
            theme: 图表主题
            width: 图表宽度
            height: 图表高度
            show_legend: 是否显示图例
            show_grid: 是否显示网格
            auto_detect_axes: 是否自动检测坐标轴

    Returns:
            Dict[str, Any]: 生成结果
        """
        logger.info(f"📊 [ChartGeneratorTool] 生成图表")
        logger.info(f"   图表类型: {chart_type}")

    
    async def execute(self, **kwargs) -> Dict[str, Any]:

    
        """向后兼容的execute方法"""

    
        return await self.run(**kwargs)
        logger.info(f"   数据行数: {len(data)}")
        
        try:
            if not data:
                return {
                    "success": False,
                    "error": "数据为空",
                    "result": None
                }
            
            # 自动检测坐标轴
            if auto_detect_axes and (not x_axis or not y_axis):
                detected_axes = self._detect_axes(data, chart_type)
                x_axis = x_axis or detected_axes.get("x_axis")
                y_axis = y_axis or detected_axes.get("y_axis")
            
            # 构建图表配置
            config = ChartConfig(
                chart_type=ChartType(chart_type),
                title=title or f"{chart_type.title()} Chart",
                x_axis=x_axis,
                y_axis=y_axis,
                color_column=color_column,
                size_column=size_column,
                theme=ChartTheme(theme),
                width=width,
                height=height,
                show_legend=show_legend,
                show_grid=show_grid
            )
            
            # 生成图表
            result = await self._generate_chart(data, config)
            
            return {
                "success": True,
                "result": result,
                "metadata": {
                    "chart_type": chart_type,
                    "data_rows": len(data),
                    "data_columns": len(data[0]) if data else 0,
                    "title": config.title,
                    "theme": theme
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [ChartGeneratorTool] 生成失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    def _detect_axes(self, data: List[Dict[str, Any]], chart_type: str) -> Dict[str, Optional[str]]:
        """自动检测坐标轴"""
        if not data:
            return {"x_axis": None, "y_axis": None}
        
        columns = list(data[0].keys())
        
        # 分析列类型
        numeric_columns = []
        categorical_columns = []
        datetime_columns = []
        
        for column in columns:
            values = [row.get(column) for row in data[:100]]  # 采样分析
            column_type = self._analyze_column_type(values)
            
            if column_type == "numeric":
                numeric_columns.append(column)
            elif column_type == "categorical":
                categorical_columns.append(column)
            elif column_type == "datetime":
                datetime_columns.append(column)
        
        # 根据图表类型推荐坐标轴
        x_axis = None
        y_axis = None
        
        if chart_type in ["bar", "line", "area"]:
            # 对于柱状图、折线图、面积图
            if categorical_columns:
                x_axis = categorical_columns[0]
            elif datetime_columns:
                x_axis = datetime_columns[0]
            
            if numeric_columns:
                y_axis = numeric_columns[0]
        
        elif chart_type == "pie":
            # 饼图通常使用分类列作为标签，数值列作为值
            if categorical_columns:
                x_axis = categorical_columns[0]
            if numeric_columns:
                y_axis = numeric_columns[0]
        
        elif chart_type == "scatter":
            # 散点图需要两个数值列
            if len(numeric_columns) >= 2:
                x_axis = numeric_columns[0]
                y_axis = numeric_columns[1]
        
        elif chart_type == "histogram":
            # 直方图使用数值列
            if numeric_columns:
                x_axis = numeric_columns[0]
        
        return {"x_axis": x_axis, "y_axis": y_axis}
    
    def _analyze_column_type(self, values: List[Any]) -> str:
        """分析列类型"""
        if not values:
            return "unknown"
        
        # 检查数值型
        numeric_count = 0
        for value in values:
            if value is None:
                continue
            try:
                float(str(value))
                numeric_count += 1
            except (ValueError, TypeError):
                break
        
        if numeric_count == len([v for v in values if v is not None]):
            return "numeric"
        
        # 检查日期时间型
        datetime_count = 0
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and len(str(value)) > 8:
                if any(char in str(value) for char in ['-', '/', ':']):
                    datetime_count += 1
        
        if datetime_count > len([v for v in values if v is not None]) * 0.8:
            return "datetime"
        
        # 默认为分类型
        return "categorical"
    
    async def _generate_chart(self, data: List[Dict[str, Any]], config: ChartConfig) -> ChartResult:
        """生成图表"""
        # 处理数据
        chart_data = self._process_chart_data(data, config)
        
        # 生成图表选项
        chart_options = self._generate_chart_options(config)
        
        # 生成洞察和建议
        insights = self._generate_insights(data, config, chart_data)
        recommendations = self._generate_recommendations(data, config, chart_data)
        
        return ChartResult(
            chart_config=config,
            chart_data=chart_data,
            chart_options=chart_options,
            insights=insights,
            recommendations=recommendations
        )
    
    def _process_chart_data(self, data: List[Dict[str, Any]], config: ChartConfig) -> Dict[str, Any]:
        """处理图表数据"""
        chart_data = {
            "series": [],
            "categories": [],
            "values": []
        }
        
        if config.chart_type == ChartType.BAR:
            chart_data = self._process_bar_chart_data(data, config)
        elif config.chart_type == ChartType.LINE:
            chart_data = self._process_line_chart_data(data, config)
        elif config.chart_type == ChartType.PIE:
            chart_data = self._process_pie_chart_data(data, config)
        elif config.chart_type == ChartType.SCATTER:
            chart_data = self._process_scatter_chart_data(data, config)
        elif config.chart_type == ChartType.AREA:
            chart_data = self._process_area_chart_data(data, config)
        elif config.chart_type == ChartType.HISTOGRAM:
            chart_data = self._process_histogram_data(data, config)
        else:
            chart_data = self._process_generic_chart_data(data, config)
        
        return chart_data
    
    def _process_bar_chart_data(self, data: List[Dict[str, Any]], config: ChartConfig) -> Dict[str, Any]:
        """处理柱状图数据"""
        if not config.x_axis or not config.y_axis:
            return {"series": [], "categories": [], "values": []}
        
        # 聚合数据
        aggregated_data = {}
        for row in data:
            x_value = str(row.get(config.x_axis, ""))
            y_value = row.get(config.y_axis, 0)
            
            try:
                y_value = float(y_value)
            except (ValueError, TypeError):
                y_value = 0
            
            if x_value in aggregated_data:
                aggregated_data[x_value] += y_value
            else:
                aggregated_data[x_value] = y_value
        
        # 转换为图表格式
        categories = list(aggregated_data.keys())
        values = list(aggregated_data.values())
        
        return {
            "series": [{"name": config.y_axis, "data": values}],
            "categories": categories,
            "values": values
        }
    
    def _process_line_chart_data(self, data: List[Dict[str, Any]], config: ChartConfig) -> Dict[str, Any]:
        """处理折线图数据"""
        if not config.x_axis or not config.y_axis:
            return {"series": [], "categories": [], "values": []}
        
        # 按X轴排序
        sorted_data = sorted(data, key=lambda x: str(x.get(config.x_axis, "")))
        
        categories = []
        values = []
        
        for row in sorted_data:
            x_value = str(row.get(config.x_axis, ""))
            y_value = row.get(config.y_axis, 0)
            
            try:
                y_value = float(y_value)
            except (ValueError, TypeError):
                y_value = 0
            
            categories.append(x_value)
            values.append(y_value)
        
        return {
            "series": [{"name": config.y_axis, "data": values}],
            "categories": categories,
            "values": values
        }
    
    def _process_pie_chart_data(self, data: List[Dict[str, Any]], config: ChartConfig) -> Dict[str, Any]:
        """处理饼图数据"""
        if not config.x_axis or not config.y_axis:
            return {"series": [], "categories": [], "values": []}
        
        # 聚合数据
        aggregated_data = {}
        for row in data:
            label = str(row.get(config.x_axis, ""))
            value = row.get(config.y_axis, 0)
            
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = 0
            
            if label in aggregated_data:
                aggregated_data[label] += value
            else:
                aggregated_data[label] = value
        
        # 转换为饼图格式
        series_data = []
        for label, value in aggregated_data.items():
            series_data.append({"name": label, "value": value})
        
        return {
            "series": series_data,
            "categories": list(aggregated_data.keys()),
            "values": list(aggregated_data.values())
        }
    
    def _process_scatter_chart_data(self, data: List[Dict[str, Any]], config: ChartConfig) -> Dict[str, Any]:
        """处理散点图数据"""
        if not config.x_axis or not config.y_axis:
            return {"series": [], "categories": [], "values": []}
        
        scatter_data = []
        for row in data:
            x_value = row.get(config.x_axis, 0)
            y_value = row.get(config.y_axis, 0)
            
            try:
                x_value = float(x_value)
                y_value = float(y_value)
                scatter_data.append([x_value, y_value])
            except (ValueError, TypeError):
                continue
        
        return {
            "series": [{"name": "Scatter", "data": scatter_data}],
            "categories": [],
            "values": scatter_data
        }
    
    def _process_area_chart_data(self, data: List[Dict[str, Any]], config: ChartConfig) -> Dict[str, Any]:
        """处理面积图数据"""
        # 面积图与折线图类似
        return self._process_line_chart_data(data, config)
    
    def _process_histogram_data(self, data: List[Dict[str, Any]], config: ChartConfig) -> Dict[str, Any]:
        """处理直方图数据"""
        if not config.x_axis:
            return {"series": [], "categories": [], "values": []}
        
        # 提取数值
        values = []
        for row in data:
            value = row.get(config.x_axis, 0)
            try:
                values.append(float(value))
            except (ValueError, TypeError):
                continue
        
        if not values:
            return {"series": [], "categories": [], "values": []}
        
        # 创建直方图区间
        min_val = min(values)
        max_val = max(values)
        bin_count = min(10, len(values) // 5)  # 动态确定区间数
        
        if bin_count < 2:
            bin_count = 2
        
        bin_width = (max_val - min_val) / bin_count
        
        bins = []
        bin_counts = []
        
        for i in range(bin_count):
            bin_start = min_val + i * bin_width
            bin_end = min_val + (i + 1) * bin_width
            bin_label = f"{bin_start:.1f}-{bin_end:.1f}"
            
            count = len([v for v in values if bin_start <= v < bin_end])
            if i == bin_count - 1:  # 最后一个区间包含最大值
                count = len([v for v in values if bin_start <= v <= bin_end])
            
            bins.append(bin_label)
            bin_counts.append(count)
        
        return {
            "series": [{"name": "Frequency", "data": bin_counts}],
            "categories": bins,
            "values": bin_counts
        }
    
    def _process_generic_chart_data(self, data: List[Dict[str, Any]], config: ChartConfig) -> Dict[str, Any]:
        """处理通用图表数据"""
        return {
            "series": [],
            "categories": [],
            "values": []
        }
    
    def _generate_chart_options(self, config: ChartConfig) -> Dict[str, Any]:
        """生成图表选项"""
        options = {
            "title": {
                "text": config.title,
                "show": True
            },
            "theme": config.theme.value,
            "width": config.width,
            "height": config.height,
            "legend": {
                "show": config.show_legend
            },
            "grid": {
                "show": config.show_grid
            },
            "xAxis": {
                "show": True,
                "title": config.x_axis or "X Axis"
            },
            "yAxis": {
                "show": True,
                "title": config.y_axis or "Y Axis"
            }
        }
        
        # 根据图表类型添加特定选项
        if config.chart_type == ChartType.PIE:
            options["pie"] = {
                "radius": "50%",
                "label": {
                    "show": True,
                    "formatter": "{b}: {c}"
                }
            }
        elif config.chart_type == ChartType.SCATTER:
            options["scatter"] = {
                "symbolSize": 6
            }
        
        return options
    
    def _generate_insights(self, data: List[Dict[str, Any]], config: ChartConfig, chart_data: Dict[str, Any]) -> List[str]:
        """生成洞察"""
        insights = []
        
        if not chart_data.get("values"):
            return insights
        
        values = chart_data["values"]
        
        # 数据量洞察
        insights.append(f"图表包含 {len(data)} 条数据记录")
        
        # 数值洞察
        if isinstance(values[0], (int, float)):
            max_val = max(values)
            min_val = min(values)
            avg_val = sum(values) / len(values)
            
            insights.append(f"数值范围: {min_val:.2f} - {max_val:.2f}")
            insights.append(f"平均值: {avg_val:.2f}")
            
            if max_val > avg_val * 2:
                insights.append("数据中存在较大的极值")
        
        # 分类洞察
        if chart_data.get("categories"):
            categories = chart_data["categories"]
            insights.append(f"包含 {len(categories)} 个分类")
            
            if len(categories) > 10:
                insights.append("分类数量较多，建议考虑合并或筛选")
        
        return insights
    
    def _generate_recommendations(self, data: List[Dict[str, Any]], config: ChartConfig, chart_data: Dict[str, Any]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 图表类型建议
        if config.chart_type == ChartType.BAR and len(chart_data.get("categories", [])) > 20:
            recommendations.append("柱状图分类过多，建议使用折线图或筛选数据")
        
        if config.chart_type == ChartType.PIE and len(chart_data.get("categories", [])) > 8:
            recommendations.append("饼图分类过多，建议合并小分类或使用其他图表类型")
        
        # 数据质量建议
        if len(data) < 10:
            recommendations.append("数据量较少，建议增加更多数据点")
        
        # 坐标轴建议
        if not config.x_axis or not config.y_axis:
            recommendations.append("建议明确指定X轴和Y轴列")
        
        # 主题建议
        if config.theme == ChartTheme.DARK:
            recommendations.append("深色主题适合展示场景，浅色主题更适合打印")
        
        return recommendations


def create_chart_generator_tool(container: Any) -> ChartGeneratorTool:
    """
    创建图表生成工具
    
    Args:
        container: 服务容器
        
    Returns:
        ChartGeneratorTool 实例
    """
    return ChartGeneratorTool(container)


# 导出
__all__ = [
    "ChartGeneratorTool",
    "ChartType",
    "ChartTheme",
    "ChartConfig",
    "ChartResult",
    "create_chart_generator_tool",
]