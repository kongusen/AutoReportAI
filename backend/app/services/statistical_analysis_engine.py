"""
统计分析引擎模块

提供统计分析和数据处理功能，支持各种统计计算和数据分析操作。
"""

from typing import Any, Dict, List, Optional
import pandas as pd
from .statistics_service import StatisticsService


class StatisticalAnalysisEngine:
    """统计分析引擎"""
    
    def __init__(self):
        self.statistics_service = StatisticsService()
    
    async def analyze_data(self, data: List[Dict[str, Any]], analysis_type: str, **kwargs) -> Dict[str, Any]:
        """
        分析数据
        
        Args:
            data: 要分析的数据
            analysis_type: 分析类型
            **kwargs: 其他参数
            
        Returns:
            分析结果
        """
        if not data:
            return {"error": "No data provided for analysis"}
        
        df = pd.DataFrame(data)
        
        if analysis_type == "basic_stats":
            return self.statistics_service.get_basic_stats(df)
        elif analysis_type == "sum":
            column = kwargs.get("column")
            if not column:
                return {"error": "Column name required for sum analysis"}
            return {"sum": self.statistics_service.calculate_sum(data, column)}
        elif analysis_type == "average":
            column = kwargs.get("column")
            if not column:
                return {"error": "Column name required for average analysis"}
            return {"average": self.statistics_service.calculate_average(data, column)}
        else:
            return {"error": f"Unsupported analysis type: {analysis_type}"}
    
    async def calculate_statistic(self, data: List[Dict[str, Any]], description: str) -> Dict[str, Any]:
        """
        根据描述计算统计值
        
        Args:
            data: 数据
            description: 统计描述
            
        Returns:
            统计结果
        """
        if not data:
            return {"error": "No data provided"}
        
        # 简单的描述解析逻辑
        description_lower = description.lower()
        
        if "总数" in description or "总" in description:
            # 尝试找到数值列
            df = pd.DataFrame(data)
            numeric_columns = df.select_dtypes(include=[pd.np.number]).columns.tolist()
            if numeric_columns:
                return {"total": self.statistics_service.calculate_sum(data, numeric_columns[0])}
        
        if "平均" in description or "均值" in description:
            df = pd.DataFrame(data)
            numeric_columns = df.select_dtypes(include=[pd.np.number]).columns.tolist()
            if numeric_columns:
                return {"average": self.statistics_service.calculate_average(data, numeric_columns[0])}
        
        # 默认返回基础统计
        df = pd.DataFrame(data)
        return self.statistics_service.get_basic_stats(df)


# 创建全局实例
statistical_engine = StatisticalAnalysisEngine() 