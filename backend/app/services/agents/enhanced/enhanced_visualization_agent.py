"""
增强版可视化Agent

在原有VisualizationAgent基础上增加以下功能：
- 智能图表类型推荐
- 自适应颜色和布局
- 交互功能构建
- 数据叙事能力
- 实时可视化支持

Features:
- AI驱动的图表推荐
- 响应式设计系统
- 高级交互功能
- 数据故事生成
- 多维度可视化
"""

import asyncio
import json
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from ..base import BaseAgent, AgentConfig, AgentResult, AgentType, AgentError
from ..visualization_agent import VisualizationAgent, ChartRequest, ChartResult
from ..security import sandbox_manager, SandboxLevel
from ..tools import tool_registry


@dataclass
class SmartChartRequest:
    """智能图表请求"""
    data: Union[List[Dict[str, Any]], Dict[str, Any]]
    purpose: str = "explore"                    # 目的: explore, present, analyze, compare
    audience: str = "general"                   # 受众: general, technical, executive
    context: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    interactive: bool = False
    responsive: bool = True
    accessibility: bool = True


@dataclass
class ChartRecommendation:
    """图表推荐"""
    chart_type: str
    confidence: float
    reasoning: str
    config: Dict[str, Any]
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ColorPalette:
    """颜色调色板"""
    name: str
    colors: List[str]
    type: str  # "sequential", "diverging", "categorical"
    accessibility_rating: float
    suitable_for: List[str]


@dataclass
class LayoutConfig:
    """布局配置"""
    width: int
    height: int
    margins: Dict[str, int]
    spacing: Dict[str, int]
    responsive_breakpoints: Dict[str, Dict[str, int]]
    grid_system: Dict[str, Any]


class ChartRecommender:
    """图表推荐引擎"""
    
    def __init__(self):
        # 图表类型映射
        self.chart_mappings = {
            "comparison": ["bar", "column", "radar"],
            "relationship": ["scatter", "bubble", "heatmap"],
            "distribution": ["histogram", "box", "violin"],
            "composition": ["pie", "donut", "stacked_bar"],
            "trend": ["line", "area", "candlestick"],
            "geographical": ["map", "choropleth", "bubble_map"],
            "hierarchical": ["treemap", "sunburst", "sankey"]
        }
        
        # 数据特征检测规则
        self.feature_rules = {
            "temporal": lambda df: self._has_time_columns(df),
            "categorical": lambda df: self._count_categorical_columns(df),
            "numerical": lambda df: self._count_numerical_columns(df),
            "geographical": lambda df: self._has_geo_columns(df),
            "hierarchical": lambda df: self._has_hierarchical_structure(df)
        }
    
    async def recommend_chart(
        self, 
        data: pd.DataFrame, 
        request: SmartChartRequest
    ) -> ChartRecommendation:
        """推荐最佳图表类型"""
        try:
            # 分析数据特征
            data_features = await self._analyze_data_features(data)
            
            # 基于目的和数据特征评分
            chart_scores = await self._calculate_chart_scores(data_features, request)
            
            # 选择最佳图表类型
            best_chart = max(chart_scores.items(), key=lambda x: x[1])
            chart_type, confidence = best_chart
            
            # 生成推荐理由
            reasoning = await self._generate_reasoning(chart_type, data_features, request)
            
            # 生成图表配置
            config = await self._generate_chart_config(chart_type, data_features, request)
            
            # 生成替代方案
            alternatives = await self._generate_alternatives(chart_scores, chart_type)
            
            return ChartRecommendation(
                chart_type=chart_type,
                confidence=confidence,
                reasoning=reasoning,
                config=config,
                alternatives=alternatives
            )
            
        except Exception as e:
            # 返回默认推荐
            return ChartRecommendation(
                chart_type="bar",
                confidence=0.5,
                reasoning=f"使用默认推荐，原因：{str(e)}",
                config={"title": "数据可视化"},
                alternatives=[]
            )
    
    async def _analyze_data_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数据特征"""
        features = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "numerical_columns": self._count_numerical_columns(df),
            "categorical_columns": self._count_categorical_columns(df),
            "temporal_columns": self._count_temporal_columns(df),
            "has_nulls": df.isnull().any().any(),
            "data_sparsity": df.isnull().sum().sum() / (len(df) * len(df.columns)),
            "unique_values_ratio": df.nunique() / len(df),
            "data_types": df.dtypes.to_dict()
        }
        
        # 检测特殊模式
        features["is_time_series"] = self._has_time_columns(df)
        features["is_geographical"] = self._has_geo_columns(df)
        features["is_hierarchical"] = self._has_hierarchical_structure(df)
        
        return features
    
    def _count_numerical_columns(self, df: pd.DataFrame) -> int:
        """计算数值列数量"""
        return len(df.select_dtypes(include=[np.number]).columns)
    
    def _count_categorical_columns(self, df: pd.DataFrame) -> int:
        """计算分类列数量"""
        return len(df.select_dtypes(include=['object', 'category']).columns)
    
    def _count_temporal_columns(self, df: pd.DataFrame) -> int:
        """计算时间列数量"""
        time_columns = 0
        for col in df.columns:
            if df[col].dtype in ['datetime64[ns]', '<M8[ns]']:
                time_columns += 1
            elif isinstance(df[col].dtype, pd.core.dtypes.dtypes.DatetimeTZDtype):
                time_columns += 1
            else:
                # 尝试解析为日期
                sample_values = df[col].dropna().head(5)
                if len(sample_values) > 0:
                    try:
                        pd.to_datetime(sample_values)
                        time_columns += 1
                    except:
                        pass
        return time_columns
    
    def _has_time_columns(self, df: pd.DataFrame) -> bool:
        """检测是否有时间列"""
        return self._count_temporal_columns(df) > 0
    
    def _has_geo_columns(self, df: pd.DataFrame) -> bool:
        """检测是否有地理列"""
        geo_keywords = ['lat', 'lng', 'longitude', 'latitude', 'city', 'country', 'region', '城市', '地区', '省份']
        for col in df.columns:
            if any(keyword.lower() in col.lower() for keyword in geo_keywords):
                return True
        return False
    
    def _has_hierarchical_structure(self, df: pd.DataFrame) -> bool:
        """检测是否有层次结构"""
        hierarchy_keywords = ['parent', 'child', 'level', 'category', 'subcategory', '父', '子', '层级']
        for col in df.columns:
            if any(keyword.lower() in col.lower() for keyword in hierarchy_keywords):
                return True
        return False
    
    async def _calculate_chart_scores(
        self,
        features: Dict[str, Any],
        request: SmartChartRequest
    ) -> Dict[str, float]:
        """计算各种图表类型的得分"""
        scores = {}
        
        # 基础图表类型评分
        chart_types = ["bar", "line", "scatter", "pie", "heatmap", "histogram", "box"]
        
        for chart_type in chart_types:
            score = await self._score_chart_type(chart_type, features, request)
            scores[chart_type] = score
        
        return scores
    
    async def _score_chart_type(
        self,
        chart_type: str,
        features: Dict[str, Any],
        request: SmartChartRequest
    ) -> float:
        """为特定图表类型评分"""
        base_score = 0.5
        
        # 基于数据特征的评分
        if chart_type == "bar":
            if features["categorical_columns"] >= 1 and features["numerical_columns"] >= 1:
                base_score += 0.3
            if features["row_count"] <= 20:  # 适合较少的类别
                base_score += 0.1
        
        elif chart_type == "line":
            if features["is_time_series"]:
                base_score += 0.4
            if features["numerical_columns"] >= 1:
                base_score += 0.2
        
        elif chart_type == "scatter":
            if features["numerical_columns"] >= 2:
                base_score += 0.3
            if request.purpose == "analyze":
                base_score += 0.1
        
        elif chart_type == "pie":
            if features["categorical_columns"] >= 1 and features["row_count"] <= 10:
                base_score += 0.3
            if request.purpose == "present":
                base_score += 0.1
        
        elif chart_type == "histogram":
            if features["numerical_columns"] >= 1 and request.purpose in ["explore", "analyze"]:
                base_score += 0.3
        
        elif chart_type == "heatmap":
            if features["numerical_columns"] >= 2 and features["categorical_columns"] >= 2:
                base_score += 0.3
        
        elif chart_type == "box":
            if features["numerical_columns"] >= 1 and features["categorical_columns"] >= 1:
                base_score += 0.2
            if request.purpose == "analyze":
                base_score += 0.1
        
        # 基于目的的调整
        purpose_adjustments = {
            "explore": {"histogram": 0.1, "scatter": 0.1, "box": 0.1},
            "present": {"pie": 0.1, "bar": 0.1, "line": 0.1},
            "analyze": {"scatter": 0.1, "heatmap": 0.1, "box": 0.1},
            "compare": {"bar": 0.1, "radar": 0.1}
        }
        
        if request.purpose in purpose_adjustments:
            adjustment = purpose_adjustments[request.purpose].get(chart_type, 0)
            base_score += adjustment
        
        return min(1.0, max(0.0, base_score))
    
    async def _generate_reasoning(
        self,
        chart_type: str,
        features: Dict[str, Any],
        request: SmartChartRequest
    ) -> str:
        """生成推荐理由"""
        reasons = []
        
        if chart_type == "bar":
            if features["categorical_columns"] >= 1:
                reasons.append("数据包含分类变量，适合使用柱状图进行比较")
            if features["row_count"] <= 20:
                reasons.append("数据类别数量适中，柱状图可以清晰展示")
        
        elif chart_type == "line":
            if features["is_time_series"]:
                reasons.append("检测到时间序列数据，折线图最适合展示趋势")
            if features["numerical_columns"] >= 1:
                reasons.append("数值数据的变化趋势适合用折线图展示")
        
        elif chart_type == "scatter":
            if features["numerical_columns"] >= 2:
                reasons.append("多个数值变量间的关系适合用散点图分析")
            if request.purpose == "analyze":
                reasons.append("分析目的下，散点图有助于发现数据模式")
        
        elif chart_type == "pie":
            if features["row_count"] <= 10:
                reasons.append("类别数量较少，饼图可以直观显示占比")
        
        if not reasons:
            reasons.append(f"基于数据特征和使用场景，{chart_type}图是合适的选择")
        
        return "；".join(reasons)
    
    async def _generate_chart_config(
        self,
        chart_type: str,
        features: Dict[str, Any],
        request: SmartChartRequest
    ) -> Dict[str, Any]:
        """生成图表配置"""
        config = {
            "chart_type": chart_type,
            "responsive": request.responsive,
            "interactive": request.interactive
        }
        
        # 基于数据特征设置默认配置
        if features["row_count"] > 100:
            config["enable_zoom"] = True
            config["enable_pan"] = True
        
        if features["categorical_columns"] > 10:
            config["rotate_labels"] = True
        
        if request.audience == "executive":
            config["simplified"] = True
            config["highlight_key_metrics"] = True
        
        return config
    
    async def _generate_alternatives(
        self,
        chart_scores: Dict[str, float],
        selected_chart: str
    ) -> List[Dict[str, Any]]:
        """生成替代方案"""
        # 排除已选择的图表，按分数排序
        alternatives_scores = {k: v for k, v in chart_scores.items() if k != selected_chart}
        sorted_alternatives = sorted(alternatives_scores.items(), key=lambda x: x[1], reverse=True)
        
        alternatives = []
        for chart_type, score in sorted_alternatives[:3]:  # 返回前3个替代方案
            alternatives.append({
                "chart_type": chart_type,
                "confidence": score,
                "reason": f"替代方案，置信度：{score:.2f}"
            })
        
        return alternatives


class ColorHarmonyEngine:
    """颜色和谐引擎"""
    
    def __init__(self):
        # 预定义调色板
        self.palettes = {
            "professional": ColorPalette(
                name="专业",
                colors=["#2E86AB", "#A23B72", "#F18F01", "#C73E1D"],
                type="categorical",
                accessibility_rating=0.9,
                suitable_for=["business", "presentation"]
            ),
            "modern": ColorPalette(
                name="现代",
                colors=["#667eea", "#764ba2", "#f093fb", "#f5576c"],
                type="categorical", 
                accessibility_rating=0.8,
                suitable_for=["digital", "creative"]
            ),
            "accessible": ColorPalette(
                name="无障碍",
                colors=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
                type="categorical",
                accessibility_rating=1.0,
                suitable_for=["accessibility", "public"]
            ),
            "sequential": ColorPalette(
                name="序列",
                colors=["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"],
                type="sequential",
                accessibility_rating=0.9,
                suitable_for=["heatmap", "choropleth"]
            )
        }
    
    async def select_palette(
        self,
        chart_type: str,
        data_characteristics: Dict[str, Any],
        user_preferences: Dict[str, Any] = None
    ) -> ColorPalette:
        """选择最佳调色板"""
        # 默认偏好
        preferences = user_preferences or {}
        
        # 基于图表类型选择
        if chart_type in ["heatmap", "choropleth"]:
            return self.palettes["sequential"]
        elif preferences.get("accessibility", False):
            return self.palettes["accessible"]
        elif preferences.get("style") == "modern":
            return self.palettes["modern"]
        else:
            return self.palettes["professional"]
    
    async def generate_custom_palette(
        self,
        base_color: str,
        color_count: int,
        palette_type: str = "categorical"
    ) -> ColorPalette:
        """生成自定义调色板"""
        try:
            # 简化的调色板生成逻辑
            # 实际应用中可以使用更复杂的颜色理论算法
            import colorsys
            
            # 解析基础颜色（假设为hex格式）
            base_rgb = self._hex_to_rgb(base_color)
            base_hsv = colorsys.rgb_to_hsv(*[c/255.0 for c in base_rgb])
            
            colors = []
            for i in range(color_count):
                if palette_type == "sequential":
                    # 序列调色板：调整明度
                    lightness = 0.2 + (0.7 * i / (color_count - 1))
                    new_hsv = (base_hsv[0], base_hsv[1], lightness)
                else:
                    # 分类调色板：调整色相
                    hue_shift = (360 / color_count * i) % 360
                    new_hue = (base_hsv[0] + hue_shift / 360) % 1.0
                    new_hsv = (new_hue, base_hsv[1], base_hsv[2])
                
                new_rgb = colorsys.hsv_to_rgb(*new_hsv)
                hex_color = self._rgb_to_hex([int(c * 255) for c in new_rgb])
                colors.append(hex_color)
            
            return ColorPalette(
                name="custom",
                colors=colors,
                type=palette_type,
                accessibility_rating=0.7,  # 需要进一步计算
                suitable_for=["custom"]
            )
            
        except Exception:
            # 如果生成失败，返回默认调色板
            return self.palettes["professional"]
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """将hex颜色转换为RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _rgb_to_hex(self, rgb: List[int]) -> str:
        """将RGB颜色转换为hex"""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


class LayoutOptimizer:
    """布局优化器"""
    
    def __init__(self):
        # 黄金比例和常用比例
        self.aspect_ratios = {
            "golden": 1.618,
            "square": 1.0,
            "wide": 16/9,
            "standard": 4/3
        }
    
    async def optimize_layout(
        self,
        chart_type: str,
        data_size: Dict[str, int],
        container_constraints: Dict[str, int] = None
    ) -> LayoutConfig:
        """优化布局配置"""
        constraints = container_constraints or {"width": 800, "height": 600}
        
        # 基于图表类型选择最佳比例
        optimal_ratio = await self._get_optimal_ratio(chart_type, data_size)
        
        # 计算尺寸
        width, height = await self._calculate_dimensions(optimal_ratio, constraints)
        
        # 计算边距
        margins = await self._calculate_margins(chart_type, width, height)
        
        # 响应式断点
        breakpoints = await self._generate_breakpoints(width, height)
        
        return LayoutConfig(
            width=width,
            height=height,
            margins=margins,
            spacing={"padding": 20, "gap": 10},
            responsive_breakpoints=breakpoints,
            grid_system={"columns": 12, "gutter": 20}
        )
    
    async def _get_optimal_ratio(self, chart_type: str, data_size: Dict[str, int]) -> float:
        """获取最佳宽高比"""
        if chart_type in ["bar", "column"]:
            # 柱状图：如果类别很多，使用更宽的比例
            if data_size.get("categories", 0) > 10:
                return self.aspect_ratios["wide"]
            else:
                return self.aspect_ratios["golden"]
        elif chart_type in ["line", "area"]:
            # 线图：通常使用宽屏比例以展示趋势
            return self.aspect_ratios["wide"]
        elif chart_type in ["pie", "donut"]:
            # 饼图：使用方形比例
            return self.aspect_ratios["square"]
        elif chart_type == "scatter":
            # 散点图：黄金比例
            return self.aspect_ratios["golden"]
        else:
            return self.aspect_ratios["standard"]
    
    async def _calculate_dimensions(
        self,
        target_ratio: float,
        constraints: Dict[str, int]
    ) -> Tuple[int, int]:
        """计算最佳尺寸"""
        max_width = constraints.get("width", 800)
        max_height = constraints.get("height", 600)
        
        # 基于约束计算尺寸
        if max_width / max_height > target_ratio:
            # 宽度过大，以高度为准
            height = max_height
            width = int(height * target_ratio)
        else:
            # 高度过大，以宽度为准
            width = max_width
            height = int(width / target_ratio)
        
        return width, height
    
    async def _calculate_margins(
        self,
        chart_type: str,
        width: int,
        height: int
    ) -> Dict[str, int]:
        """计算边距"""
        # 基于尺寸的相对边距
        base_margin = min(width, height) * 0.05
        
        margins = {
            "top": int(base_margin),
            "right": int(base_margin),
            "bottom": int(base_margin * 1.5),  # 底部留更多空间给标签
            "left": int(base_margin * 1.2)     # 左侧留空间给Y轴标签
        }
        
        # 基于图表类型调整
        if chart_type in ["pie", "donut"]:
            # 饼图需要较少边距
            for key in margins:
                margins[key] = int(margins[key] * 0.5)
        elif chart_type == "heatmap":
            # 热力图需要更多空间给标签
            margins["left"] *= 2
            margins["bottom"] *= 2
        
        return margins
    
    async def _generate_breakpoints(
        self,
        base_width: int,
        base_height: int
    ) -> Dict[str, Dict[str, int]]:
        """生成响应式断点"""
        return {
            "mobile": {
                "width": min(base_width, 350),
                "height": min(base_height, 250)
            },
            "tablet": {
                "width": min(base_width, 600),
                "height": min(base_height, 400)
            },
            "desktop": {
                "width": base_width,
                "height": base_height
            }
        }


class StorytellingEngine:
    """数据叙事引擎"""
    
    def __init__(self):
        self.story_templates = {
            "trend": "数据显示{direction}趋势，从{start_value}变化到{end_value}，{period}内{change_description}",
            "comparison": "在{categories}中，{winner}表现最佳，达到{max_value}，比最低的{loser}高出{difference}",
            "distribution": "数据分布{distribution_type}，平均值为{mean}，{outlier_description}",
            "anomaly": "检测到{anomaly_count}个异常点，其中{notable_anomaly}最为显著"
        }
    
    async def generate_story(
        self,
        chart_data: Dict[str, Any],
        chart_type: str,
        analysis_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成数据故事"""
        try:
            story = {
                "title": await self._generate_title(chart_data, chart_type),
                "summary": await self._generate_summary(chart_data, chart_type),
                "insights": await self._extract_insights(chart_data, analysis_results),
                "recommendations": await self._generate_recommendations(chart_data, analysis_results)
            }
            
            return story
            
        except Exception as e:
            return {
                "title": "数据可视化",
                "summary": "展示数据的基本情况",
                "insights": ["数据已成功可视化"],
                "recommendations": ["建议进一步分析数据模式"]
            }
    
    async def _generate_title(self, chart_data: Dict, chart_type: str) -> str:
        """生成标题"""
        if chart_type == "line":
            return "趋势分析图表"
        elif chart_type == "bar":
            return "对比分析图表"
        elif chart_type == "pie":
            return "占比分布图表"
        elif chart_type == "scatter":
            return "相关性分析图表"
        else:
            return f"{chart_type.title()} 数据图表"
    
    async def _generate_summary(self, chart_data: Dict, chart_type: str) -> str:
        """生成摘要"""
        data_count = len(chart_data.get("data", []))
        return f"此图表展示了包含 {data_count} 个数据点的{chart_type}可视化结果"
    
    async def _extract_insights(
        self,
        chart_data: Dict,
        analysis_results: Dict = None
    ) -> List[str]:
        """提取洞察"""
        insights = []
        
        data = chart_data.get("data", [])
        if not data:
            return ["暂无数据洞察"]
        
        # 基本统计洞察
        if isinstance(data, list) and len(data) > 0:
            insights.append(f"数据集包含 {len(data)} 个观测值")
            
            # 如果有数值数据，提供基本统计
            numeric_fields = []
            if isinstance(data[0], dict):
                for key, value in data[0].items():
                    if isinstance(value, (int, float)):
                        numeric_fields.append(key)
            
            if numeric_fields:
                for field in numeric_fields[:2]:  # 只分析前两个数值字段
                    values = [item.get(field, 0) for item in data if isinstance(item.get(field), (int, float))]
                    if values:
                        avg_val = sum(values) / len(values)
                        max_val = max(values)
                        min_val = min(values)
                        insights.append(f"{field}的平均值为 {avg_val:.2f}，范围从 {min_val} 到 {max_val}")
        
        return insights
    
    async def _generate_recommendations(
        self,
        chart_data: Dict,
        analysis_results: Dict = None
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        data_count = len(chart_data.get("data", []))
        
        if data_count < 10:
            recommendations.append("数据量较少，建议收集更多数据以获得更可靠的分析结果")
        elif data_count > 1000:
            recommendations.append("数据量较大，可以考虑进行数据聚合或抽样以提高可视化效果")
        
        if analysis_results and "anomaly" in analysis_results:
            recommendations.append("检测到异常值，建议进一步调查这些数据点")
        
        recommendations.append("建议结合业务背景解读可视化结果")
        
        return recommendations


class EnhancedVisualizationAgent(VisualizationAgent):
    """增强版可视化Agent"""
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="enhanced_visualization_agent",
                agent_type=AgentType.VISUALIZATION,
                name="Enhanced Visualization Agent",
                description="增强版可视化Agent，支持智能推荐和自适应设计",
                timeout_seconds=90,
                enable_caching=True,
                cache_ttl_seconds=2400  # 40分钟缓存
            )
        
        super().__init__(config)
        
        # 初始化增强组件
        self.chart_recommender = ChartRecommender()
        self.color_engine = ColorHarmonyEngine()
        self.layout_optimizer = LayoutOptimizer()
        self.storytelling_engine = StorytellingEngine()
    
    async def create_smart_chart(self, request: SmartChartRequest) -> AgentResult:
        """创建智能图表"""
        try:
            self.logger.info(
                "创建智能图表",
                agent_id=self.agent_id,
                purpose=request.purpose,
                audience=request.audience
            )
            
            # 准备数据
            df = await self._prepare_dataframe(request.data)
            
            # 获取图表推荐
            recommendation = await self.chart_recommender.recommend_chart(df, request)
            
            # 选择颜色调色板
            color_palette = await self.color_engine.select_palette(
                recommendation.chart_type,
                {"data_size": len(df)},
                request.preferences
            )
            
            # 优化布局
            layout_config = await self.layout_optimizer.optimize_layout(
                recommendation.chart_type,
                {"rows": len(df), "columns": len(df.columns)},
                request.constraints
            )
            
            # 构建标准图表请求
            chart_request = await self._build_chart_request(
                request, recommendation, color_palette, layout_config
            )
            
            # 生成图表
            chart_result = await super().execute(chart_request)
            
            if chart_result.success:
                # 生成数据故事
                story = await self.storytelling_engine.generate_story(
                    {"data": request.data},
                    recommendation.chart_type
                )
                
                # 增强结果
                enhanced_result = await self._enhance_chart_result(
                    chart_result.data, recommendation, story, layout_config
                )
                
                chart_result.data = enhanced_result
                chart_result.metadata.update({
                    "smart_features": True,
                    "recommendation": {
                        "chart_type": recommendation.chart_type,
                        "confidence": recommendation.confidence,
                        "reasoning": recommendation.reasoning
                    },
                    "story": story,
                    "layout_optimized": True
                })
            
            return chart_result
            
        except Exception as e:
            error_msg = f"智能图表创建失败: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _prepare_dataframe(self, data: Union[List[Dict], Dict]) -> pd.DataFrame:
        """准备DataFrame"""
        if isinstance(data, dict):
            df = pd.DataFrame([data])
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            raise AgentError("不支持的数据格式", self.agent_id, "INVALID_DATA_FORMAT")
        
        return df
    
    async def _build_chart_request(
        self,
        smart_request: SmartChartRequest,
        recommendation: ChartRecommendation,
        color_palette: ColorPalette,
        layout_config: LayoutConfig
    ) -> ChartRequest:
        """构建标准图表请求"""
        # 自动检测字段
        df = await self._prepare_dataframe(smart_request.data)
        
        # 选择X和Y字段
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        x_field = categorical_cols[0] if categorical_cols else (numerical_cols[0] if numerical_cols else "")
        y_field = numerical_cols[0] if numerical_cols else (categorical_cols[1] if len(categorical_cols) > 1 else "")
        
        return ChartRequest(
            data=smart_request.data,
            chart_type=recommendation.chart_type,
            title=f"{recommendation.chart_type.title()} 图表",
            x_field=x_field,
            y_field=y_field,
            width=layout_config.width,
            height=layout_config.height,
            theme="smart",
            interactive=smart_request.interactive,
            custom_config={
                "colors": color_palette.colors,
                "layout": layout_config.__dict__,
                "recommendation": recommendation.config
            }
        )
    
    async def _enhance_chart_result(
        self,
        chart_result: ChartResult,
        recommendation: ChartRecommendation,
        story: Dict[str, Any],
        layout_config: LayoutConfig
    ) -> ChartResult:
        """增强图表结果"""
        # 更新描述
        enhanced_description = f"{story['summary']}。{recommendation.reasoning}"
        chart_result.description = enhanced_description
        
        # 添加智能功能的元数据
        if not chart_result.metadata:
            chart_result.metadata = {}
        
        chart_result.metadata.update({
            "recommendation": {
                "confidence": recommendation.confidence,
                "alternatives": recommendation.alternatives
            },
            "story": story,
            "layout": {
                "optimized": True,
                "responsive": True,
                "accessibility": True
            }
        })
        
        return chart_result
    
    async def generate_dashboard(
        self,
        requests: List[SmartChartRequest],
        layout: str = "auto"
    ) -> AgentResult:
        """生成仪表板"""
        try:
            self.logger.info(
                "生成智能仪表板",
                agent_id=self.agent_id,
                chart_count=len(requests)
            )
            
            # 并行生成所有图表
            chart_tasks = [self.create_smart_chart(req) for req in requests]
            chart_results = await asyncio.gather(*chart_tasks, return_exceptions=True)
            
            # 处理结果
            successful_charts = []
            failed_charts = []
            
            for i, result in enumerate(chart_results):
                if isinstance(result, AgentResult) and result.success:
                    successful_charts.append({
                        "index": i,
                        "chart": result.data,
                        "metadata": result.metadata
                    })
                else:
                    failed_charts.append({
                        "index": i,
                        "error": str(result) if not isinstance(result, AgentResult) else result.error_message
                    })
            
            # 生成仪表板布局
            dashboard_layout = await self._generate_dashboard_layout(successful_charts, layout)
            
            # 生成仪表板摘要
            dashboard_story = await self._generate_dashboard_story(successful_charts)
            
            dashboard_result = {
                "charts": successful_charts,
                "layout": dashboard_layout,
                "story": dashboard_story,
                "summary": {
                    "total_charts": len(requests),
                    "successful_charts": len(successful_charts),
                    "failed_charts": len(failed_charts)
                }
            }
            
            return AgentResult(
                success=len(successful_charts) > 0,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=dashboard_result,
                metadata={
                    "dashboard": True,
                    "chart_count": len(successful_charts),
                    "failures": failed_charts
                }
            )
            
        except Exception as e:
            error_msg = f"仪表板生成失败: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _generate_dashboard_layout(
        self,
        charts: List[Dict],
        layout: str
    ) -> Dict[str, Any]:
        """生成仪表板布局"""
        chart_count = len(charts)
        
        if layout == "auto":
            # 自动布局算法
            if chart_count == 1:
                grid_layout = {"rows": 1, "cols": 1}
            elif chart_count == 2:
                grid_layout = {"rows": 1, "cols": 2}
            elif chart_count <= 4:
                grid_layout = {"rows": 2, "cols": 2}
            elif chart_count <= 6:
                grid_layout = {"rows": 2, "cols": 3}
            else:
                rows = math.ceil(math.sqrt(chart_count))
                cols = math.ceil(chart_count / rows)
                grid_layout = {"rows": rows, "cols": cols}
        else:
            # 使用指定布局
            grid_layout = {"rows": 2, "cols": 2}  # 默认2x2
        
        return {
            "type": "grid",
            "grid": grid_layout,
            "spacing": 20,
            "responsive": True,
            "charts": [{"id": i, "position": {"row": i // grid_layout["cols"], "col": i % grid_layout["cols"]}} for i in range(chart_count)]
        }
    
    async def _generate_dashboard_story(self, charts: List[Dict]) -> Dict[str, Any]:
        """生成仪表板故事"""
        return {
            "title": "数据分析仪表板",
            "summary": f"包含 {len(charts)} 个可视化图表的综合分析仪表板",
            "insights": [
                f"仪表板展示了 {len(charts)} 个不同维度的数据分析",
                "所有图表采用智能推荐的最佳可视化类型",
                "布局经过自适应优化，确保最佳的视觉体验"
            ]
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        health = await super().health_check()
        
        # 添加智能功能的健康检查
        health.update({
            "chart_recommender": "healthy",
            "color_engine": {
                "healthy": True,
                "palettes_available": len(self.color_engine.palettes)
            },
            "layout_optimizer": "healthy",
            "storytelling_engine": "healthy",
            "smart_features": {
                "recommendation": True,
                "color_harmony": True,
                "layout_optimization": True,
                "data_storytelling": True
            }
        })
        
        return health