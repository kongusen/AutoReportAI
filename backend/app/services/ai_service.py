import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from typing import List, Dict, Any

class AIService:
    def __init__(self):
        # Set Chinese font for matplotlib
        # This font needs to be installed in the Docker container
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

    def generate_chart_from_description(self, data: List[Dict[str, Any]], description: str) -> str:
        """
        Generates a chart image based on data and a natural language description.
        Returns the image as a base64 encoded string.
        """
        if not data:
            raise ValueError("Input data cannot be empty.")

        df = pd.DataFrame(data)
        
        # Determine chart type from description
        if "柱状图" in description:
            self._create_bar_chart(df, description)
        elif "饼图" in description:
            self._create_pie_chart(df, description)
        elif "折线图" in description:
            self._create_line_chart(df, description)
        else:
            # Default to a bar chart if type is not specified
            self._create_bar_chart(df, description)
            
        # Save plot to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        
        # Encode buffer to base64
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        
        return image_base64

    def generate_text_summary(self, context_data: Dict[str, Any]) -> str:
        """
        Generates a narrative text summary based on the provided data context.
        
        This is a mock implementation using a simple rule-based template.
        It can be replaced with a call to a real Large Language Model (LLM).
        """
        project_name = context_data.get("project_name", "该项目")
        total_sales = context_data.get("total_sales_from_regions", 0)
        
        # Example of finding the region with the highest sales
        regional_sales = context_data.get("sales_by_region", [])
        top_region = ""
        max_sales = 0
        if isinstance(regional_sales, list) and regional_sales:
            top_performer = max(regional_sales, key=lambda x: x.get('sales', 0))
            top_region = top_performer.get("region", "")
            max_sales = top_performer.get("sales", 0)

        summary = (
            f"根据数据显示，{project_name}本月表现优异。总销售额达到 {total_sales:,.2f}元。"
            f"其中，{top_region}地区表现最为突出，销售额为 {max_sales:,.2f}元，是主要的增长动力。"
            "建议持续关注该地区的市场动态，并考虑将成功经验推广至其他区域。"
        )
        return summary

    def _create_bar_chart(self, df: pd.DataFrame, title: str):
        if len(df.columns) < 2:
            raise ValueError("Bar chart requires at least two columns (labels and values).")
        x_col, y_col = df.columns[0], df.columns[1]
        df.plot(kind='bar', x=x_col, y=y_col, legend=False)
        plt.title(title)
        plt.ylabel(y_col)
        plt.xticks(rotation=45)
    
    def _create_pie_chart(self, df: pd.DataFrame, title: str):
        if len(df.columns) < 2:
            raise ValueError("Pie chart requires at least two columns (labels and values).")
        labels_col, values_col = df.columns[0], df.columns[1]
        plt.pie(df[values_col], labels=df[labels_col], autopct='%1.1f%%', startangle=90)
        plt.title(title)
        plt.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.

    def _create_line_chart(self, df: pd.DataFrame, title: str):
        if len(df.columns) < 2:
            raise ValueError("Line chart requires at least two columns (x and y values).")
        x_col, y_col = df.columns[0], df.columns[1]
        df.plot(kind='line', x=x_col, y=y_col, marker='o', legend=False)
        plt.title(title)
        plt.ylabel(y_col)
        plt.grid(True)
        plt.xticks(rotation=45)

ai_service = AIService()
