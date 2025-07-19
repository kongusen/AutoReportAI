"""
图表生成器服务

生成各种类型的图表，支持折线图、柱状图、饼图等。
可以生成图表文件或图表描述文本。
"""

import base64
import json
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 尝试导入图表库，如果不可用则使用模拟实现
try:
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("Agg")  # 使用非交互式后端
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    logger.warning("matplotlib not available, using mock chart generation")

try:
    import seaborn as sns

    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False


@dataclass
class ChartConfig:
    """图表配置"""

    chart_type: str = "bar"  # bar, line, pie, scatter
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    width: int = 800
    height: int = 600
    style: str = "default"  # default, professional, minimal
    color_scheme: str = "default"
    show_legend: bool = True
    show_grid: bool = True


@dataclass
class ChartResult:
    """图表生成结果"""

    chart_type: str
    file_path: Optional[str] = None
    base64_data: Optional[str] = None
    description: str = ""
    metadata: Dict[str, Any] = None
    success: bool = True
    error_message: Optional[str] = None


class ChartGenerator:
    """图表生成器"""

    def __init__(self):
        self.default_config = ChartConfig()

    async def generate_chart(
        self,
        data: List[Dict[str, Any]],
        config: Optional[ChartConfig] = None,
        output_format: str = "description",  # file, base64, description
    ) -> ChartResult:
        """
        生成图表

        Args:
            data: 图表数据
            config: 图表配置
            output_format: 输出格式（file, base64, description）

        Returns:
            图表生成结果
        """
        if config is None:
            config = self.default_config

        try:
            logger.info(f"开始生成图表，类型: {config.chart_type}")

            if not data:
                return ChartResult(
                    chart_type=config.chart_type,
                    description="无数据可显示",
                    success=False,
                    error_message="数据为空",
                )

            # 根据输出格式选择生成方式
            if output_format == "description":
                return await self._generate_chart_description(data, config)
            elif HAS_MATPLOTLIB and output_format in ["file", "base64"]:
                return await self._generate_chart_image(data, config, output_format)
            else:
                # 降级到描述模式
                logger.warning("图表库不可用，降级到描述模式")
                return await self._generate_chart_description(data, config)

        except Exception as e:
            logger.error(f"图表生成失败: {e}")
            return ChartResult(
                chart_type=config.chart_type,
                description=f"图表生成失败: {str(e)}",
                success=False,
                error_message=str(e),
            )

    async def _generate_chart_description(
        self, data: List[Dict[str, Any]], config: ChartConfig
    ) -> ChartResult:
        """生成图表描述"""

        data_points = len(data)

        # 分析数据结构
        if not data:
            description = "空图表"
        else:
            first_item = data[0]

            if config.chart_type == "bar":
                description = self._describe_bar_chart(data, config)
            elif config.chart_type == "line":
                description = self._describe_line_chart(data, config)
            elif config.chart_type == "pie":
                description = self._describe_pie_chart(data, config)
            elif config.chart_type == "scatter":
                description = self._describe_scatter_chart(data, config)
            else:
                description = f"{config.chart_type}图表，包含{data_points}个数据点"

        return ChartResult(
            chart_type=config.chart_type,
            description=description,
            metadata={"data_points": data_points, "chart_config": config.__dict__},
            success=True,
        )

    async def _generate_chart_image(
        self, data: List[Dict[str, Any]], config: ChartConfig, output_format: str
    ) -> ChartResult:
        """生成图表图像"""

        try:
            # 设置图表样式
            if HAS_SEABORN:
                sns.set_style(
                    config.style if config.style != "default" else "whitegrid"
                )

            # 创建图表
            fig, ax = plt.subplots(figsize=(config.width / 100, config.height / 100))

            # 根据图表类型生成
            if config.chart_type == "bar":
                self._create_bar_chart(ax, data, config)
            elif config.chart_type == "line":
                self._create_line_chart(ax, data, config)
            elif config.chart_type == "pie":
                self._create_pie_chart(ax, data, config)
            elif config.chart_type == "scatter":
                self._create_scatter_chart(ax, data, config)

            # 设置标题和标签
            if config.title:
                ax.set_title(config.title, fontsize=14, fontweight="bold")
            if config.x_label:
                ax.set_xlabel(config.x_label)
            if config.y_label:
                ax.set_ylabel(config.y_label)

            # 设置网格
            if config.show_grid and config.chart_type != "pie":
                ax.grid(True, alpha=0.3)

            # 设置图例
            if config.show_legend and config.chart_type != "pie":
                ax.legend()

            plt.tight_layout()

            # 输出处理
            if output_format == "base64":
                # 转换为base64
                buffer = BytesIO()
                plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
                buffer.seek(0)
                base64_data = base64.b64encode(buffer.getvalue()).decode()
                plt.close(fig)

                return ChartResult(
                    chart_type=config.chart_type,
                    base64_data=base64_data,
                    description=f"{config.chart_type}图表已生成",
                    metadata={"format": "base64", "data_points": len(data)},
                    success=True,
                )

            else:  # file
                file_path = f"chart_{config.chart_type}_{hash(str(data))}.png"
                plt.savefig(file_path, dpi=100, bbox_inches="tight")
                plt.close(fig)

                return ChartResult(
                    chart_type=config.chart_type,
                    file_path=file_path,
                    description=f"{config.chart_type}图表已保存到 {file_path}",
                    metadata={"format": "file", "data_points": len(data)},
                    success=True,
                )

        except Exception as e:
            logger.error(f"图表图像生成失败: {e}")
            # 降级到描述模式
            return await self._generate_chart_description(data, config)

    def _describe_bar_chart(self, data: List[Dict], config: ChartConfig) -> str:
        """描述柱状图"""

        if not data:
            return "空柱状图"

        # 尝试提取分类和数值
        categories = []
        values = []

        for item in data:
            if "category" in item and "value" in item:
                categories.append(str(item["category"]))
                values.append(float(item["value"]))
            elif "name" in item and "count" in item:
                categories.append(str(item["name"]))
                values.append(float(item["count"]))

        if not values:
            return f"柱状图，包含{len(data)}个数据点"

        max_value = max(values)
        max_category = categories[values.index(max_value)]
        total_value = sum(values)

        return f"柱状图显示{len(categories)}个类别的数据，总计{total_value:.0f}，其中{max_category}最高({max_value:.0f})"

    def _describe_line_chart(self, data: List[Dict], config: ChartConfig) -> str:
        """描述折线图"""

        if not data:
            return "空折线图"

        data_points = len(data)

        # 尝试提取趋势信息
        values = []
        for item in data:
            if "value" in item:
                values.append(float(item["value"]))
            elif "y" in item:
                values.append(float(item["y"]))

        if len(values) >= 2:
            trend = (
                "上升"
                if values[-1] > values[0]
                else "下降" if values[-1] < values[0] else "平稳"
            )
            return f"折线图显示{data_points}个时间点的数据变化趋势，整体呈{trend}态势"
        else:
            return f"折线图，包含{data_points}个数据点"

    def _describe_pie_chart(self, data: List[Dict], config: ChartConfig) -> str:
        """描述饼图"""

        if not data:
            return "空饼图"

        # 计算比例
        values = []
        labels = []

        for item in data:
            if "value" in item and "label" in item:
                values.append(float(item["value"]))
                labels.append(str(item["label"]))
            elif "count" in item and "category" in item:
                values.append(float(item["count"]))
                labels.append(str(item["category"]))

        if not values:
            return f"饼图，包含{len(data)}个分类"

        total = sum(values)
        max_value = max(values)
        max_label = labels[values.index(max_value)]
        max_percentage = (max_value / total) * 100

        return f"饼图显示{len(labels)}个分类的占比分布，{max_label}占比最大({max_percentage:.1f}%)"

    def _describe_scatter_chart(self, data: List[Dict], config: ChartConfig) -> str:
        """描述散点图"""

        if not data:
            return "空散点图"

        return f"散点图显示{len(data)}个数据点的分布关系"

    def _create_bar_chart(self, ax, data: List[Dict], config: ChartConfig):
        """创建柱状图"""

        categories = []
        values = []

        for item in data:
            if "category" in item and "value" in item:
                categories.append(str(item["category"]))
                values.append(float(item["value"]))
            elif "name" in item and "count" in item:
                categories.append(str(item["name"]))
                values.append(float(item["count"]))

        if categories and values:
            bars = ax.bar(categories, values)

            # 设置颜色
            if config.color_scheme == "professional":
                colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
                for i, bar in enumerate(bars):
                    bar.set_color(colors[i % len(colors)])

    def _create_line_chart(self, ax, data: List[Dict], config: ChartConfig):
        """创建折线图"""

        x_values = []
        y_values = []

        for i, item in enumerate(data):
            if "x" in item and "y" in item:
                x_values.append(item["x"])
                y_values.append(float(item["y"]))
            elif "value" in item:
                x_values.append(i)
                y_values.append(float(item["value"]))

        if x_values and y_values:
            ax.plot(x_values, y_values, marker="o", linewidth=2, markersize=6)

    def _create_pie_chart(self, ax, data: List[Dict], config: ChartConfig):
        """创建饼图"""

        values = []
        labels = []

        for item in data:
            if "value" in item and "label" in item:
                values.append(float(item["value"]))
                labels.append(str(item["label"]))
            elif "count" in item and "category" in item:
                values.append(float(item["count"]))
                labels.append(str(item["category"]))

        if values and labels:
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")

    def _create_scatter_chart(self, ax, data: List[Dict], config: ChartConfig):
        """创建散点图"""

        x_values = []
        y_values = []

        for item in data:
            if "x" in item and "y" in item:
                x_values.append(float(item["x"]))
                y_values.append(float(item["y"]))

        if x_values and y_values:
            ax.scatter(x_values, y_values, alpha=0.6, s=50)


# 创建全局实例
chart_generator = ChartGenerator()
