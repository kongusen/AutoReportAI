"""
图表生成工具集合
提供智能图表生成、推荐、优化等可视化功能
"""

import json
import logging
from typing import List, Dict, Any, Optional

from llama_index.core.tools import FunctionTool

from .base_tool import ToolsCollection, create_standard_tool
from ...data.processing.visualization_service import VisualizationService
from ...application.facades.unified_service_facade import get_unified_facade

logger = logging.getLogger(__name__)


class ChartToolsCollection(ToolsCollection):
    """图表生成工具集合"""
    
    def __init__(self):
        super().__init__(category="chart")
        
        # 初始化可视化服务
        self.visualization_service = None
        self.unified_facade = None
    
    async def _get_visualization_service(self):
        """获取可视化服务实例"""
        if not self.visualization_service:
            self.visualization_service = VisualizationService()
        return self.visualization_service
    
    async def _get_unified_facade(self):
        """获取统一服务门面"""
        if not self.unified_facade:
            self.unified_facade = get_unified_facade()
        return self.unified_facade
    
    def create_tools(self) -> List[FunctionTool]:
        """创建图表工具列表"""
        return [
            self._create_intelligent_charts_tool(),
            self._create_chart_recommendations_tool(),
            self._create_multiple_charts_tool(),
            self._create_optimize_design_tool()
        ]
    
    def _create_intelligent_charts_tool(self) -> FunctionTool:
        """创建智能图表生成工具"""
        
        async def generate_intelligent_charts(
            data_query_or_path: str,
            chart_requirements: str,
            output_format: str = "json"
        ) -> Dict[str, Any]:
            """
            智能图表生成 - 支持多种输出格式
            
            Args:
                data_query_or_path: 数据查询或路径
                chart_requirements: 图表需求描述
                output_format: 输出格式 (json, png, svg, pdf, base64)
                
            Returns:
                图表生成结果
            """
            try:
                service = await self._get_visualization_service()
                
                # 模拟图表生成逻辑
                chart_config = {
                    "type": "bar",
                    "data": [100, 120, 150, 180, 200],
                    "labels": ["Jan", "Feb", "Mar", "Apr", "May"],
                    "title": chart_requirements,
                    "format": output_format
                }
                
                return {
                    "success": True,
                    "chart_config": chart_config,
                    "data_source": data_query_or_path,
                    "requirements": chart_requirements,
                    "output_format": output_format
                }
            except Exception as e:
                logger.error(f"智能图表生成失败: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "chart_config": None
                }
        
        return create_standard_tool(
            generate_intelligent_charts,
            name="generate_intelligent_charts",
            description="根据数据和需求智能生成图表配置",
            category="chart",
            complexity="high"
        )
    
    def _create_chart_recommendations_tool(self) -> FunctionTool:
        """创建图表推荐工具"""
        
        async def recommend_chart_types(
            data_structure: Dict[str, Any],
            analysis_goals: List[str]
        ) -> Dict[str, Any]:
            """
            基于数据结构和分析目标推荐合适的图表类型
            
            Args:
                data_structure: 数据结构信息
                analysis_goals: 分析目标列表
                
            Returns:
                图表类型推荐结果
            """
            try:
                # 模拟图表推荐逻辑
                recommendations = []
                
                # 基于数据类型推荐
                if "numeric" in str(data_structure):
                    recommendations.append({
                        "type": "line",
                        "reason": "适合展示数值变化趋势",
                        "confidence": 0.9
                    })
                    recommendations.append({
                        "type": "bar", 
                        "reason": "适合对比不同类别的数值",
                        "confidence": 0.8
                    })
                
                # 基于分析目标推荐
                for goal in analysis_goals:
                    if "比较" in goal:
                        recommendations.append({
                            "type": "bar",
                            "reason": "适合进行比较分析",
                            "confidence": 0.85
                        })
                    elif "趋势" in goal:
                        recommendations.append({
                            "type": "line",
                            "reason": "适合展示趋势变化",
                            "confidence": 0.9
                        })
                    elif "占比" in goal or "比例" in goal:
                        recommendations.append({
                            "type": "pie",
                            "reason": "适合展示占比关系",
                            "confidence": 0.8
                        })
                
                return {
                    "success": True,
                    "recommendations": recommendations,
                    "data_structure": data_structure,
                    "analysis_goals": analysis_goals
                }
            except Exception as e:
                logger.error(f"图表推荐失败: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "recommendations": []
                }
        
        return create_standard_tool(
            recommend_chart_types,
            name="recommend_chart_types",
            description="基于数据结构和分析目标推荐合适的图表类型",
            category="chart",
            complexity="medium"
        )
    
    def _create_multiple_charts_tool(self) -> FunctionTool:
        """创建多图表生成工具"""
        
        async def generate_multiple_charts(
            dataset: Dict[str, Any],
            chart_specs: List[Dict[str, Any]]
        ) -> Dict[str, Any]:
            """
            基于单一数据集生成多个图表
            
            Args:
                dataset: 数据集
                chart_specs: 图表规格列表
                
            Returns:
                多图表生成结果
            """
            try:
                charts = []
                
                for i, spec in enumerate(chart_specs):
                    chart = {
                        "id": f"chart_{i}",
                        "type": spec.get("type", "bar"),
                        "title": spec.get("title", f"Chart {i+1}"),
                        "data": dataset.get("data", []),
                        "config": spec.get("config", {}),
                        "success": True
                    }
                    charts.append(chart)
                
                return {
                    "success": True,
                    "charts": charts,
                    "total_charts": len(charts),
                    "dataset_used": dataset
                }
            except Exception as e:
                logger.error(f"多图表生成失败: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "charts": []
                }
        
        return create_standard_tool(
            generate_multiple_charts,
            name="generate_multiple_charts",
            description="基于单一数据集生成多个不同类型的图表",
            category="chart",
            complexity="high"
        )
    
    def _create_optimize_design_tool(self) -> FunctionTool:
        """创建图表设计优化工具"""
        
        async def optimize_chart_design(
            chart_config: Dict[str, Any],
            optimization_goals: List[str] = None
        ) -> Dict[str, Any]:
            """
            优化图表设计以提高可读性和美观度
            
            Args:
                chart_config: 原始图表配置
                optimization_goals: 优化目标 (readability, aesthetics, accessibility)
                
            Returns:
                优化后的图表配置
            """
            try:
                optimized_config = chart_config.copy()
                optimizations_applied = []
                
                # 默认优化目标
                if not optimization_goals:
                    optimization_goals = ["readability", "aesthetics"]
                
                # 应用优化
                if "readability" in optimization_goals:
                    optimized_config.setdefault("colors", ["#3498db", "#e74c3c", "#2ecc71"])
                    optimized_config.setdefault("font_size", 12)
                    optimizations_applied.append("improved_readability")
                
                if "aesthetics" in optimization_goals:
                    optimized_config.setdefault("theme", "modern")
                    optimized_config.setdefault("border_radius", 4)
                    optimizations_applied.append("enhanced_aesthetics")
                
                if "accessibility" in optimization_goals:
                    optimized_config.setdefault("contrast_ratio", "high")
                    optimized_config.setdefault("alt_text", "Chart description")
                    optimizations_applied.append("accessibility_improved")
                
                return {
                    "success": True,
                    "original_config": chart_config,
                    "optimized_config": optimized_config,
                    "optimizations_applied": optimizations_applied,
                    "optimization_goals": optimization_goals
                }
            except Exception as e:
                logger.error(f"图表设计优化失败: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "optimized_config": chart_config
                }
        
        return create_standard_tool(
            optimize_chart_design,
            name="optimize_chart_design",
            description="优化图表设计以提高可读性和美观度",
            category="chart",
            complexity="medium"
        )


def create_chart_tools() -> List[FunctionTool]:
    """创建图表工具列表"""
    collection = ChartToolsCollection()
    return collection.create_tools()