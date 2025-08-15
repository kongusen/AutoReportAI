"""
Specialized Agents Module

This module contains domain-specific agents that inherit from BaseAnalysisAgent
and provide specialized functionality for different types of analysis and processing.
"""

from .schema_analysis_agent import SchemaAnalysisAgent
from .data_query_agent import DataQueryAgent
from .content_generation_agent import ContentGenerationAgent
from .visualization_agent import VisualizationAgent

# 创建 DataAnalysisAgent 作为通用数据分析 Agent
class DataAnalysisAgent(SchemaAnalysisAgent):
    """
    数据分析 Agent - 专注于统计分析和数据处理
    
    继承自 SchemaAnalysisAgent，提供通用的数据分析功能
    """
    
    async def perform_descriptive_analysis(self, data, context=None):
        """执行描述性统计分析"""
        prompt = self._build_descriptive_analysis_prompt(data, context)
        return await self.analyze_with_ai(context, prompt, "descriptive_analysis")
    
    async def perform_trend_analysis(self, data, context=None):
        """执行趋势分析"""
        prompt = self._build_trend_analysis_prompt(data, context)
        return await self.analyze_with_ai(context, prompt, "trend_analysis")
    
    async def perform_correlation_analysis(self, data, context=None):
        """执行相关性分析"""
        prompt = self._build_correlation_analysis_prompt(data, context)
        return await self.analyze_with_ai(context, prompt, "correlation_analysis")
    
    def _build_descriptive_analysis_prompt(self, data, context):
        """构建描述性分析提示"""
        return f"""
        请对以下数据进行描述性统计分析：
        
        数据：{data}
        上下文：{context or '无'}
        
        请提供：
        1. 基本统计信息（均值、中位数、标准差等）
        2. 数据分布特征
        3. 异常值检测
        4. 数据质量评估
        """
    
    def _build_trend_analysis_prompt(self, data, context):
        """构建趋势分析提示"""
        return f"""
        请对以下数据进行趋势分析：
        
        数据：{data}
        上下文：{context or '无'}
        
        请提供：
        1. 时间序列趋势识别
        2. 周期性模式分析
        3. 趋势预测建议
        4. 关键转折点识别
        """
    
    def _build_correlation_analysis_prompt(self, data, context):
        """构建相关性分析提示"""
        return f"""
        请对以下数据进行相关性分析：
        
        数据：{data}
        上下文：{context or '无'}
        
        请提供：
        1. 变量间相关性矩阵
        2. 强相关性变量识别
        3. 因果关系分析建议
        4. 多变量关系可视化建议
        """

__all__ = [
    "SchemaAnalysisAgent",
    "DataAnalysisAgent", 
    "DataQueryAgent",
    "ContentGenerationAgent",
    "VisualizationAgent"
]
