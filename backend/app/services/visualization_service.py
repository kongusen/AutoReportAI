from typing import Any, Dict, List

import pandas as pd


class VisualizationService:
    """
    A service for generating data visualizations.
    """

    def generate_bar_chart(
        self, data: List[Dict[str, Any]], x_column: str, y_column: str, title: str
    ) -> Dict[str, Any]:
        """
        Generates the data structure for a bar chart.

        In a real implementation, this could use libraries like Matplotlib or Plotly
        to generate an image or a JSON object for a frontend library like Chart.js or ECharts.

        :param data: The dataset for the chart.
        :param x_column: The column for the X-axis.
        :param y_column: The column for the Y-axis.
        :param title: The title of the chart.
        :return: A dictionary representing the chart data.
        """
        if not data:
            return {"error": "No data provided for chart generation."}

        df = pd.DataFrame(data)
        if x_column not in df.columns or y_column not in df.columns:
            raise ValueError(
                f"One or more columns ('{x_column}', '{y_column}') not found in data."
            )

        # For now, return a structured dictionary that a frontend could use.
        # This simulates generating data for a library like Chart.js
        return {
            "type": "bar",
            "title": title,
            "labels": df[x_column].tolist(),
            "datasets": [
                {
                    "label": title,
                    "data": df[y_column].tolist(),
                }
            ],
        }

    def create_chart_image(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x_column: str,
        y_column: str,
        title: str,
    ) -> str:
        """
        创建图表图像并返回base64编码的字符串

        :param df: 数据DataFrame
        :param chart_type: 图表类型
        :param x_column: X轴列名
        :param y_column: Y轴列名
        :param title: 图表标题
        :return: base64编码的图像字符串
        """
        import base64
        import io

        import matplotlib.pyplot as plt

        try:
            # 创建图表
            fig, ax = plt.subplots(figsize=(10, 6))

            if chart_type == "bar":
                ax.bar(df[x_column], df[y_column])
            elif chart_type == "line":
                ax.plot(df[x_column], df[y_column])
            elif chart_type == "scatter":
                ax.scatter(df[x_column], df[y_column])
            else:
                # 默认使用柱状图
                ax.bar(df[x_column], df[y_column])

            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column)
            ax.set_title(title)

            # 旋转x轴标签以防重叠
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()

            # 将图表转换为base64字符串
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
            buffer.seek(0)

            # 编码为base64
            image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

            plt.close(fig)  # 释放内存

            return image_base64

        except Exception as e:
            # 如果图表生成失败，返回错误信息
            return f"Chart generation failed: {str(e)}"
