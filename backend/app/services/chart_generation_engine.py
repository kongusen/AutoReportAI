"""
图表生成引擎模块

提供图表生成和可视化功能，支持各种图表类型的创建和渲染。
"""

from typing import Any, Dict, List, Optional
import pandas as pd
from .visualization_service import VisualizationService


class ChartGenerationEngine:
    """图表生成引擎"""
    
    def __init__(self):
        self.visualization_service = VisualizationService()
    
    async def generate_chart(
        self, 
        data: List[Dict[str, Any]], 
        chart_type: str, 
        x_column: str, 
        y_column: str, 
        title: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成图表
        
        Args:
            data: 图表数据
            chart_type: 图表类型
            x_column: X轴列名
            y_column: Y轴列名
            title: 图表标题
            output_dir: 输出目录
            
        Returns:
            图表结果
        """
        if not data:
            return {"error": "No data provided for chart generation"}
        
        try:
            df = pd.DataFrame(data)
            
            if chart_type == "bar":
                chart_data = self.visualization_service.generate_bar_chart(
                    data, x_column, y_column, title
                )
            else:
                # 默认使用柱状图
                chart_data = self.visualization_service.generate_bar_chart(
                    data, x_column, y_column, title
                )
            
            # 生成图表图像
            image_base64 = self.visualization_service.create_chart_image(
                df, chart_type, x_column, y_column, title
            )
            
            result = {
                "chart_type": chart_type,
                "title": title,
                "chart_data": chart_data,
                "image_base64": image_base64,
                "success": True
            }
            
            return result
            
        except Exception as e:
            return {
                "error": f"Chart generation failed: {str(e)}",
                "success": False
            }
    
    async def create_chart_from_description(
        self, 
        data: List[Dict[str, Any]], 
        description: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据描述创建图表
        
        Args:
            data: 数据
            description: 图表描述
            output_dir: 输出目录
            
        Returns:
            图表结果
        """
        if not data:
            return {"error": "No data provided"}
        
        df = pd.DataFrame(data)
        
        # 简单的描述解析逻辑
        description_lower = description.lower()
        
        # 确定图表类型
        if "柱状图" in description or "条形图" in description:
            chart_type = "bar"
        elif "折线图" in description or "线图" in description:
            chart_type = "line"
        elif "散点图" in description:
            chart_type = "scatter"
        else:
            chart_type = "bar"  # 默认柱状图
        
        # 尝试确定列名
        columns = df.columns.tolist()
        if len(columns) >= 2:
            x_column = columns[0]
            y_column = columns[1]
        else:
            return {"error": "Insufficient columns for chart generation"}
        
        return await self.generate_chart(
            data, chart_type, x_column, y_column, description, output_dir
        )


# 创建全局实例
chart_engine = ChartGenerationEngine() 