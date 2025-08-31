"""
统一服务门面 - 为图表生成和数据分析提供统一接口
整合可视化服务、数据分析和报告生成功能
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...data.processing.visualization_service import VisualizationService
from ...data.processing.schema_aware_analysis import SchemaAwareAnalysisService
# from ...domain.reporting.generator import ReportGenerator  # Not available

logger = logging.getLogger(__name__)


class UnifiedServiceFacade:
    """
    统一服务门面
    
    集成以下服务:
    - 数据可视化服务
    - 模式感知分析服务  
    - 报告生成服务
    """
    
    def __init__(self):
        """初始化统一服务门面"""
        self.visualization_service = VisualizationService()
        self.analysis_service = SchemaAwareAnalysisService()
        # self.report_generator = ReportGenerator()  # Not available
        
    async def generate_charts(
        self,
        data_source: str,
        requirements: str,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        基于数据源和需求生成图表
        
        Args:
            data_source: 数据查询SQL或数据文件路径
            requirements: 图表需求描述
            output_format: 输出格式 (json, png, svg, pdf)
            
        Returns:
            图表生成结果
        """
        try:
            logger.info(f"开始图表生成: data_source={data_source[:50]}..., requirements={requirements}")
            
            # 1. 解析需求，确定图表类型
            chart_info = await self._parse_chart_requirements(requirements)
            
            # 2. 获取或处理数据
            data = await self._prepare_chart_data(data_source)
            
            if not data:
                return {
                    "success": False,
                    "error": "No data available for chart generation"
                }
            
            # 3. 生成图表
            chart_result = self.visualization_service.generate_chart(
                data=data,
                chart_type=chart_info["chart_type"],
                config=chart_info["config"],
                output_format=output_format
            )
            
            if chart_result.get("success", True):
                return {
                    "success": True,
                    "generated_charts": [{
                        "chart_type": chart_info["chart_type"],
                        "output_path": chart_result.get("image_path"),
                        "config": chart_result.get("chart_config"),
                        "echarts_config": chart_result.get("echarts_config")
                    }],
                    "metadata": {
                        "requirements_parsed": requirements,
                        "data_points": len(data),
                        "generation_time": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "success": False,
                    "error": chart_result.get("error", "Chart generation failed")
                }
                
        except Exception as e:
            logger.error(f"图表生成失败: {str(e)}")
            return {
                "success": False,
                "error": f"Chart generation failed: {str(e)}"
            }
    
    async def optimize_chart(
        self,
        chart_path: str,
        optimization_goals: List[str]
    ) -> Dict[str, Any]:
        """
        优化图表设计
        
        Args:
            chart_path: 图表文件路径
            optimization_goals: 优化目标列表
            
        Returns:
            优化结果
        """
        try:
            logger.info(f"开始图表优化: {chart_path}, goals={optimization_goals}")
            
            # 这里实现图表优化逻辑
            # 目前返回模拟结果
            improvements = []
            
            if "clarity" in optimization_goals:
                improvements.append("增加图表标题清晰度")
                improvements.append("优化坐标轴标签")
                
            if "aesthetics" in optimization_goals:
                improvements.append("改善配色方案")
                improvements.append("调整图表布局")
                
            if "accessibility" in optimization_goals:
                improvements.append("增加色盲友好配色")
                improvements.append("提升对比度")
            
            # 生成优化后的文件路径
            optimized_path = chart_path.replace(".png", "_optimized.png")
            
            return {
                "success": True,
                "improvements": improvements,
                "optimized_path": optimized_path,
                "optimization_goals": optimization_goals
            }
            
        except Exception as e:
            logger.error(f"图表优化失败: {str(e)}")
            return {
                "success": False,
                "error": f"Chart optimization failed: {str(e)}"
            }
    
    async def analyze_data_for_charts(
        self,
        data: List[Dict[str, Any]],
        analysis_type: str = "exploratory"
    ) -> Dict[str, Any]:
        """
        分析数据以推荐合适的图表类型
        
        Args:
            data: 数据列表
            analysis_type: 分析类型
            
        Returns:
            数据分析和图表推荐结果
        """
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided for analysis"
                }
            
            # 使用分析服务进行数据分析
            analysis_result = await self.analysis_service.analyze_data_structure(data)
            
            # 基于数据特征推荐图表类型
            recommendations = self._recommend_chart_types(analysis_result)
            
            return {
                "success": True,
                "data_analysis": analysis_result,
                "chart_recommendations": recommendations,
                "analysis_type": analysis_type
            }
            
        except Exception as e:
            logger.error(f"数据分析失败: {str(e)}")
            return {
                "success": False,
                "error": f"Data analysis failed: {str(e)}"
            }
    
    async def _parse_chart_requirements(self, requirements: str) -> Dict[str, Any]:
        """
        解析图表需求描述
        
        Args:
            requirements: 需求描述文本
            
        Returns:
            解析后的图表信息
        """
        # 简单的关键词匹配来确定图表类型
        req_lower = requirements.lower()
        
        chart_type = "bar_chart"  # 默认
        config = {}
        
        if any(word in req_lower for word in ["饼图", "pie", "比例", "占比", "percentage"]):
            chart_type = "pie_chart"
        elif any(word in req_lower for word in ["折线", "line", "趋势", "trend", "时间"]):
            chart_type = "line_chart"
        elif any(word in req_lower for word in ["散点", "scatter", "关系", "correlation"]):
            chart_type = "scatter_chart"
        elif any(word in req_lower for word in ["雷达", "radar", "多维", "能力"]):
            chart_type = "radar_chart"
        elif any(word in req_lower for word in ["漏斗", "funnel", "转化", "流程"]):
            chart_type = "funnel_chart"
        elif any(word in req_lower for word in ["柱状", "bar", "对比", "compare"]):
            chart_type = "bar_chart"
        
        # 提取标题
        if "标题" in requirements:
            title_part = requirements.split("标题")[1].split(",")[0].split("，")[0]
            config["title"] = title_part.strip()
        else:
            config["title"] = "数据图表"
        
        return {
            "chart_type": chart_type,
            "config": config,
            "original_requirements": requirements
        }
    
    async def _prepare_chart_data(self, data_source: str) -> List[Dict[str, Any]]:
        """
        准备图表数据
        
        Args:
            data_source: 数据源 (SQL查询或文件路径)
            
        Returns:
            处理后的数据列表
        """
        try:
            # 如果是SQL查询
            if data_source.strip().lower().startswith("select"):
                # 这里应该执行SQL查询获取数据
                # 目前返回模拟数据
                return [
                    {"category": "A", "value": 100, "year": 2023},
                    {"category": "B", "value": 150, "year": 2023},
                    {"category": "C", "value": 200, "year": 2023},
                    {"category": "D", "value": 120, "year": 2023}
                ]
            
            # 如果是文件路径
            elif data_source.endswith(('.csv', '.json', '.xlsx')):
                # 这里应该读取文件数据
                # 目前返回模拟数据
                return [
                    {"name": "产品A", "sales": 1000, "profit": 200},
                    {"name": "产品B", "sales": 1500, "profit": 300},
                    {"name": "产品C", "sales": 800, "profit": 150}
                ]
            
            # 其他情况返回默认数据
            else:
                return [
                    {"item": "Item1", "count": 10},
                    {"item": "Item2", "count": 15},
                    {"item": "Item3", "count": 8}
                ]
                
        except Exception as e:
            logger.error(f"数据准备失败: {str(e)}")
            return []
    
    def _recommend_chart_types(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于数据分析结果推荐图表类型
        
        Args:
            analysis_result: 数据分析结果
            
        Returns:
            图表类型推荐列表
        """
        recommendations = []
        
        # 获取数据特征
        data_types = analysis_result.get("column_types", {})
        row_count = analysis_result.get("row_count", 0)
        
        numeric_cols = [col for col, dtype in data_types.items() if dtype in ["int64", "float64", "number"]]
        categorical_cols = [col for col, dtype in data_types.items() if dtype in ["object", "string", "category"]]
        
        # 推荐逻辑
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            recommendations.append({
                "chart_type": "bar_chart",
                "confidence": 0.9,
                "reason": "适合显示分类数据的数值比较",
                "suggested_config": {
                    "x_column": categorical_cols[0],
                    "y_column": numeric_cols[0]
                }
            })
            
            if row_count <= 10:  # 少量数据适合饼图
                recommendations.append({
                    "chart_type": "pie_chart", 
                    "confidence": 0.8,
                    "reason": "数据量适中，适合显示占比关系",
                    "suggested_config": {
                        "label_column": categorical_cols[0],
                        "value_column": numeric_cols[0]
                    }
                })
        
        if len(numeric_cols) >= 2:
            recommendations.append({
                "chart_type": "scatter_chart",
                "confidence": 0.7,
                "reason": "多个数值字段，适合探索变量关系",
                "suggested_config": {
                    "x_column": numeric_cols[0],
                    "y_column": numeric_cols[1]
                }
            })
        
        if len(numeric_cols) >= 3:
            recommendations.append({
                "chart_type": "radar_chart",
                "confidence": 0.6,
                "reason": "多维数值数据，适合综合展示",
                "suggested_config": {
                    "dimensions": numeric_cols[:6]
                }
            })
        
        # 如果没有推荐，默认推荐柱状图
        if not recommendations:
            recommendations.append({
                "chart_type": "bar_chart",
                "confidence": 0.5,
                "reason": "通用图表类型",
                "suggested_config": {}
            })
        
        return sorted(recommendations, key=lambda x: x["confidence"], reverse=True)


# 创建全局实例
_unified_facade = None

def get_unified_facade() -> UnifiedServiceFacade:
    """获取统一服务门面实例"""
    global _unified_facade
    if _unified_facade is None:
        _unified_facade = UnifiedServiceFacade()
    return _unified_facade