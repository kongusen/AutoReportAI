from __future__ import annotations

from loom.interfaces.tool import BaseTool
"""
图表分析工具

分析图表数据特征和模式
提供图表优化建议和洞察
"""


import logging
import math
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class AnalysisFocus(str, Enum):
    """分析重点"""
    PATTERNS = "patterns"           # 模式识别
    TRENDS = "trends"              # 趋势分析
    OUTLIERS = "outliers"          # 异常值检测
    CORRELATIONS = "correlations"  # 相关性分析
    DISTRIBUTION = "distribution"   # 分布分析
    OPTIMIZATION = "optimization"   # 优化建议


class ChartQuality(str, Enum):
    """图表质量"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class AnalysisConfig:
    """分析配置"""
    analysis_focus: List[AnalysisFocus]
    sensitivity: float = 0.5  # 0-1之间，分析敏感度
    include_recommendations: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_focus: AnalysisFocus
    findings: List[str]
    metrics: Dict[str, Any]
    quality_score: float
    recommendations: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ComprehensiveChartAnalysis:
    """综合图表分析"""
    chart_quality: ChartQuality
    overall_score: float
    analysis_results: List[AnalysisResult]
    key_insights: List[str]
    optimization_suggestions: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ChartAnalyzerTool(BaseTool):
    """图表分析工具"""
    
    def __init__(self, container: Any):
        """
        Args:
            container: 服务容器
        """
        super().__init__()

        self.name = "chart_analyzer"

        self.category = ToolCategory.CHART

        self.description = "分析图表数据特征和模式" 
        self.container = container
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class ChartAnalyzerArgs(BaseModel):
            chart_data: Dict[str, Any] = Field(description="图表数据")
            chart_config: Optional[Dict[str, Any]] = Field(default=None, description="图表配置")
            analysis_focus: Optional[List[Literal[
                "patterns", "trends", "outliers", "correlations", "distribution", "optimization"
            ]]] = Field(default=["patterns", "trends", "outliers"], description="分析重点")
            sensitivity: float = Field(default=0.5, description="分析敏感度 (0-1)")
            include_recommendations: bool = Field(default=True, description="是否包含建议")

        self.args_schema = ChartAnalyzerArgs
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "chart_analyzer",
                "description": "分析图表数据特征和模式",
                "parameters": parameters,
            },
        }
    
    async def run(

    
        self,
        chart_data: Dict[str, Any],
        chart_config: Optional[Dict[str, Any]] = None,
        analysis_focus: Optional[List[str]] = None,
        sensitivity: float = 0.5,
        include_recommendations: bool = True,
        **kwargs
    

    
    ) -> Dict[str, Any]:
        """
        执行图表分析
        
        Args:
            chart_data: 图表数据
            chart_config: 图表配置
            analysis_focus: 分析重点
            sensitivity: 分析敏感度
            include_recommendations: 是否包含建议
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        logger.info(f"🔍 [ChartAnalyzerTool] 分析图表")
        logger.info(f"   分析重点: {analysis_focus}")

    
    async def execute(self, **kwargs) -> Dict[str, Any]:

    
        """向后兼容的execute方法"""

    
        return await self.run(**kwargs)
        logger.info(f"   敏感度: {sensitivity}")
        
        try:
            if not chart_data:
                return {
                    "success": False,
                    "error": "图表数据为空",
                    "result": None
                }
            
            # 设置默认分析重点
            if analysis_focus is None:
                analysis_focus = ["patterns", "trends", "outliers"]
            
            # 构建分析配置
            config = AnalysisConfig(
                analysis_focus=[AnalysisFocus(f) for f in analysis_focus],
                sensitivity=sensitivity,
                include_recommendations=include_recommendations
            )
            
            # 执行分析
            analysis_results = []
            for focus in config.analysis_focus:
                result = await self._perform_analysis(chart_data, chart_config, focus, config)
                analysis_results.append(result)
            
            # 计算整体质量分数
            overall_score = self._calculate_overall_score(analysis_results)
            chart_quality = self._determine_chart_quality(overall_score)
            
            # 提取关键洞察
            key_insights = self._extract_key_insights(analysis_results)
            
            # 生成优化建议
            optimization_suggestions = []
            if include_recommendations:
                optimization_suggestions = self._generate_optimization_suggestions(
                    chart_data, chart_config, analysis_results
                )
            
            comprehensive_analysis = ComprehensiveChartAnalysis(
                chart_quality=chart_quality,
                overall_score=overall_score,
                analysis_results=analysis_results,
                key_insights=key_insights,
                optimization_suggestions=optimization_suggestions
            )
            
            return {
                "success": True,
                "result": comprehensive_analysis,
                "metadata": {
                    "analysis_focus": analysis_focus,
                    "sensitivity": sensitivity,
                    "overall_score": overall_score,
                    "chart_quality": chart_quality.value,
                    "insights_count": len(key_insights),
                    "suggestions_count": len(optimization_suggestions)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [ChartAnalyzerTool] 分析失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    async def _perform_analysis(
        self,
        chart_data: Dict[str, Any],
        chart_config: Optional[Dict[str, Any]],
        focus: AnalysisFocus,
        config: AnalysisConfig
    ) -> AnalysisResult:
        """执行特定分析"""
        if focus == AnalysisFocus.PATTERNS:
            return self._analyze_patterns(chart_data, chart_config, config)
        elif focus == AnalysisFocus.TRENDS:
            return self._analyze_trends(chart_data, chart_config, config)
        elif focus == AnalysisFocus.OUTLIERS:
            return self._analyze_outliers(chart_data, chart_config, config)
        elif focus == AnalysisFocus.CORRELATIONS:
            return self._analyze_correlations(chart_data, chart_config, config)
        elif focus == AnalysisFocus.DISTRIBUTION:
            return self._analyze_distribution(chart_data, chart_config, config)
        elif focus == AnalysisFocus.OPTIMIZATION:
            return self._analyze_optimization(chart_data, chart_config, config)
        else:
            return AnalysisResult(
                analysis_focus=focus,
                findings=[],
                metrics={},
                quality_score=0.0,
                recommendations=[]
            )
    
    def _analyze_patterns(self, chart_data: Dict[str, Any], chart_config: Optional[Dict[str, Any]], config: AnalysisConfig) -> AnalysisResult:
        """分析模式"""
        findings = []
        metrics = {}
        recommendations = []
        
        # 分析数据模式
        values = self._extract_values(chart_data)
        
        if values:
            # 检查周期性
            periodicity = self._detect_periodicity(values)
            if periodicity > 0:
                findings.append(f"检测到周期性模式，周期长度: {periodicity}")
                metrics["periodicity"] = periodicity
            
            # 检查单调性
            monotonicity = self._detect_monotonicity(values)
            if monotonicity != "none":
                findings.append(f"检测到{monotonicity}单调模式")
                metrics["monotonicity"] = monotonicity
            
            # 检查波动性
            volatility = self._calculate_volatility(values)
            metrics["volatility"] = volatility
            
            if volatility > config.sensitivity:
                findings.append("数据波动性较大")
                recommendations.append("考虑使用平滑技术减少噪声")
            else:
                findings.append("数据相对稳定")
        
        # 分析分类模式
        categories = chart_data.get("categories", [])
        if categories:
            category_distribution = self._analyze_category_distribution(categories, values)
            metrics["category_distribution"] = category_distribution
            
            if category_distribution.get("dominant_category"):
                findings.append("存在主导分类")
                recommendations.append("考虑突出显示主导分类或分析其他分类")
        
        quality_score = self._calculate_pattern_quality_score(metrics)
        
        return AnalysisResult(
            analysis_focus=AnalysisFocus.PATTERNS,
            findings=findings,
            metrics=metrics,
            quality_score=quality_score,
            recommendations=recommendations
        )
    
    def _analyze_trends(self, chart_data: Dict[str, Any], chart_config: Optional[Dict[str, Any]], config: AnalysisConfig) -> AnalysisResult:
        """分析趋势"""
        findings = []
        metrics = {}
        recommendations = []
        
        values = self._extract_values(chart_data)
        
        if len(values) >= 3:
            # 计算趋势
            trend_info = self._calculate_trend(values)
            metrics["trend"] = trend_info
            
            trend_direction = trend_info.get("direction", "stable")
            trend_strength = trend_info.get("strength", 0)
            
            if trend_direction == "increasing":
                findings.append("数据呈上升趋势")
                if trend_strength > 0.7:
                    findings.append("趋势强度较强")
            elif trend_direction == "decreasing":
                findings.append("数据呈下降趋势")
                if trend_strength > 0.7:
                    findings.append("趋势强度较强")
            else:
                findings.append("数据趋势相对稳定")
            
            # 分析趋势变化点
            change_points = self._detect_change_points(values)
            if change_points:
                findings.append(f"检测到 {len(change_points)} 个趋势变化点")
                metrics["change_points"] = change_points
                recommendations.append("关注趋势变化点，可能包含重要信息")
            
            # 预测趋势
            if len(values) >= 5:
                prediction = self._predict_trend(values)
                metrics["prediction"] = prediction
                
                if prediction.get("confidence", 0) > 0.6:
                    findings.append(f"预测趋势: {prediction.get('direction', 'unknown')}")
        
        quality_score = self._calculate_trend_quality_score(metrics)
        
        return AnalysisResult(
            analysis_focus=AnalysisFocus.TRENDS,
            findings=findings,
            metrics=metrics,
            quality_score=quality_score,
            recommendations=recommendations
        )
    
    def _analyze_outliers(self, chart_data: Dict[str, Any], chart_config: Optional[Dict[str, Any]], config: AnalysisConfig) -> AnalysisResult:
        """分析异常值"""
        findings = []
        metrics = {}
        recommendations = []
        
        values = self._extract_values(chart_data)
        
        if len(values) >= 4:
            # 检测异常值
            outliers = self._detect_outliers(values, config.sensitivity)
            metrics["outliers"] = outliers
            metrics["outlier_count"] = len(outliers)
            metrics["outlier_percentage"] = len(outliers) / len(values) * 100
            
            if outliers:
                findings.append(f"检测到 {len(outliers)} 个异常值")
                
                if len(outliers) / len(values) > 0.1:  # 超过10%
                    findings.append("异常值比例较高")
                    recommendations.append("建议检查数据质量或考虑异常值处理")
                else:
                    findings.append("异常值比例正常")
                    recommendations.append("异常值可能包含重要信息，建议进一步分析")
            else:
                findings.append("未检测到明显异常值")
        
        quality_score = self._calculate_outlier_quality_score(metrics)
        
        return AnalysisResult(
            analysis_focus=AnalysisFocus.OUTLIERS,
            findings=findings,
            metrics=metrics,
            quality_score=quality_score,
            recommendations=recommendations
        )
    
    def _analyze_correlations(self, chart_data: Dict[str, Any], chart_config: Optional[Dict[str, Any]], config: AnalysisConfig) -> AnalysisResult:
        """分析相关性"""
        findings = []
        metrics = {}
        recommendations = []
        
        # 分析多系列数据的相关性
        series = chart_data.get("series", [])
        
        if len(series) >= 2:
            correlations = []
            
            for i in range(len(series)):
                for j in range(i + 1, len(series)):
                    series1_values = series[i].get("data", [])
                    series2_values = series[j].get("data", [])
                    
                    if len(series1_values) == len(series2_values) and len(series1_values) > 1:
                        correlation = self._calculate_correlation(series1_values, series2_values)
                        correlations.append({
                            "series1": series[i].get("name", f"Series {i}"),
                            "series2": series[j].get("name", f"Series {j}"),
                            "correlation": correlation
                        })
            
            metrics["correlations"] = correlations
            
            # 分析强相关性
            strong_correlations = [c for c in correlations if abs(c["correlation"]) > 0.7]
            
            if strong_correlations:
                findings.append(f"发现 {len(strong_correlations)} 对强相关变量")
                for corr in strong_correlations[:3]:  # 只显示前3个
                    findings.append(f"'{corr['series1']}' 和 '{corr['series2']}' 相关系数: {corr['correlation']:.3f}")
                
                recommendations.append("强相关变量可能表示因果关系或共同影响因素")
            else:
                findings.append("未发现强相关关系")
        
        quality_score = self._calculate_correlation_quality_score(metrics)
        
        return AnalysisResult(
            analysis_focus=AnalysisFocus.CORRELATIONS,
            findings=findings,
            metrics=metrics,
            quality_score=quality_score,
            recommendations=recommendations
        )
    
    def _analyze_distribution(self, chart_data: Dict[str, Any], chart_config: Optional[Dict[str, Any]], config: AnalysisConfig) -> AnalysisResult:
        """分析分布"""
        findings = []
        metrics = {}
        recommendations = []
        
        values = self._extract_values(chart_data)
        
        if values:
            # 分析分布特征
            distribution_info = self._analyze_distribution_features(values)
            metrics["distribution"] = distribution_info
            
            # 检查正态性
            if distribution_info.get("is_normal", False):
                findings.append("数据近似正态分布")
            else:
                skewness = distribution_info.get("skewness", 0)
                if abs(skewness) > 1:
                    findings.append(f"数据呈{'右' if skewness > 0 else '左'}偏分布")
                    recommendations.append("偏态分布可能影响统计分析，考虑数据变换")
            
            # 检查峰度
            kurtosis = distribution_info.get("kurtosis", 0)
            if kurtosis > 3:
                findings.append("数据呈尖峰分布")
            elif kurtosis < 3:
                findings.append("数据呈平峰分布")
            
            # 分析集中度
            concentration = self._calculate_concentration(values)
            metrics["concentration"] = concentration
            
            if concentration > 0.8:
                findings.append("数据高度集中")
                recommendations.append("高度集中的数据可能缺乏变异性")
            elif concentration < 0.3:
                findings.append("数据分散度较高")
                recommendations.append("分散的数据可能包含多个子群体")
        
        quality_score = self._calculate_distribution_quality_score(metrics)
        
        return AnalysisResult(
            analysis_focus=AnalysisFocus.DISTRIBUTION,
            findings=findings,
            metrics=metrics,
            quality_score=quality_score,
            recommendations=recommendations
        )
    
    def _analyze_optimization(self, chart_data: Dict[str, Any], chart_config: Optional[Dict[str, Any]], config: AnalysisConfig) -> AnalysisResult:
        """分析优化建议"""
        findings = []
        metrics = {}
        recommendations = []
        
        # 分析图表配置
        if chart_config:
            config_analysis = self._analyze_chart_config(chart_config)
            metrics["config_analysis"] = config_analysis
            
            # 检查标题
            if not chart_config.get("title", {}).get("text"):
                findings.append("缺少图表标题")
                recommendations.append("建议添加描述性标题")
            
            # 检查坐标轴标签
            if not chart_config.get("xAxis", {}).get("title"):
                findings.append("缺少X轴标签")
                recommendations.append("建议添加X轴标签")
            
            if not chart_config.get("yAxis", {}).get("title"):
                findings.append("缺少Y轴标签")
                recommendations.append("建议添加Y轴标签")
        
        # 分析数据质量
        data_quality = self._analyze_data_quality(chart_data)
        metrics["data_quality"] = data_quality
        
        if data_quality.get("missing_data_percentage", 0) > 10:
            findings.append("数据缺失率较高")
            recommendations.append("建议处理缺失数据或说明数据限制")
        
        if data_quality.get("data_points", 0) < 10:
            findings.append("数据点较少")
            recommendations.append("建议增加数据点以提高可信度")
        
        # 分析可视化效果
        visualization_score = self._calculate_visualization_score(chart_data, chart_config)
        metrics["visualization_score"] = visualization_score
        
        if visualization_score < 0.6:
            findings.append("可视化效果有待改善")
            recommendations.append("建议调整图表类型或样式")
        
        quality_score = self._calculate_optimization_quality_score(metrics)
        
        return AnalysisResult(
            analysis_focus=AnalysisFocus.OPTIMIZATION,
            findings=findings,
            metrics=metrics,
            quality_score=quality_score,
            recommendations=recommendations
        )
    
    def _extract_values(self, chart_data: Dict[str, Any]) -> List[float]:
        """提取数值"""
        values = []
        
        # 从series中提取
        series = chart_data.get("series", [])
        for s in series:
            data = s.get("data", [])
            for item in data:
                if isinstance(item, (int, float)):
                    values.append(float(item))
                elif isinstance(item, list) and len(item) >= 2:
                    values.append(float(item[1]))  # 假设是[x, y]格式
        
        # 从values中提取
        if not values:
            values = chart_data.get("values", [])
            values = [float(v) for v in values if isinstance(v, (int, float))]
        
        return values
    
    def _detect_periodicity(self, values: List[float]) -> int:
        """检测周期性"""
        if len(values) < 6:
            return 0
        
        # 简化的周期性检测
        n = len(values)
        max_period = min(n // 2, 20)  # 最大周期长度
        
        best_period = 0
        best_score = 0
        
        for period in range(2, max_period + 1):
            score = 0
            for i in range(period, n):
                if abs(values[i] - values[i - period]) < 0.1:  # 简化的相似性检查
                    score += 1
            
            if score > best_score:
                best_score = score
                best_period = period
        
        return best_period if best_score > len(values) * 0.3 else 0
    
    def _detect_monotonicity(self, values: List[float]) -> str:
        """检测单调性"""
        if len(values) < 2:
            return "none"
        
        increasing_count = 0
        decreasing_count = 0
        
        for i in range(1, len(values)):
            if values[i] > values[i - 1]:
                increasing_count += 1
            elif values[i] < values[i - 1]:
                decreasing_count += 1
        
        total_changes = increasing_count + decreasing_count
        if total_changes == 0:
            return "stable"
        
        increasing_ratio = increasing_count / total_changes
        decreasing_ratio = decreasing_count / total_changes
        
        if increasing_ratio > 0.8:
            return "increasing"
        elif decreasing_ratio > 0.8:
            return "decreasing"
        else:
            return "mixed"
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """计算波动性"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = math.sqrt(variance)
        
        return std / mean if mean != 0 else 0.0
    
    def _analyze_category_distribution(self, categories: List[str], values: List[float]) -> Dict[str, Any]:
        """分析分类分布"""
        if not categories or not values:
            return {}
        
        # 计算每个分类的值
        category_values = {}
        for i, category in enumerate(categories):
            if i < len(values):
                category_values[category] = values[i]
        
        # 找到主导分类
        if category_values:
            max_value = max(category_values.values())
            dominant_category = max(category_values.items(), key=lambda x: x[1])[0]
            
            return {
                "dominant_category": dominant_category,
                "dominant_percentage": max_value / sum(category_values.values()) * 100,
                "category_count": len(categories),
                "distribution_entropy": self._calculate_entropy(list(category_values.values()))
            }
        
        return {}
    
    def _calculate_entropy(self, values: List[float]) -> float:
        """计算熵"""
        if not values:
            return 0.0
        
        total = sum(values)
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for value in values:
            if value > 0:
                p = value / total
                entropy -= p * math.log2(p)
        
        return entropy
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """计算趋势"""
        if len(values) < 2:
            return {"direction": "stable", "strength": 0.0}
        
        n = len(values)
        x_values = list(range(n))
        
        # 计算线性回归
        mean_x = sum(x_values) / n
        mean_y = sum(values) / n
        
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, values))
        denominator = sum((x - mean_x) ** 2 for x in x_values)
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # 计算R²
        y_pred = [mean_y + slope * (x - mean_x) for x in x_values]
        ss_res = sum((y - pred) ** 2 for y, pred in zip(values, y_pred))
        ss_tot = sum((y - mean_y) ** 2 for y in values)
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # 确定趋势方向
        if slope > 0.01:
            direction = "increasing"
        elif slope < -0.01:
            direction = "decreasing"
        else:
            direction = "stable"
        
        return {
            "direction": direction,
            "slope": slope,
            "strength": r_squared,
            "r_squared": r_squared
        }
    
    def _detect_change_points(self, values: List[float]) -> List[int]:
        """检测变化点"""
        if len(values) < 5:
            return []
        
        change_points = []
        
        # 简化的变化点检测
        for i in range(2, len(values) - 2):
            # 计算前后窗口的平均值
            before_avg = sum(values[i-2:i]) / 2
            after_avg = sum(values[i:i+2]) / 2
            
            # 检查是否有显著变化
            if abs(after_avg - before_avg) > 2 * self._calculate_volatility(values[:i]):
                change_points.append(i)
        
        return change_points
    
    def _predict_trend(self, values: List[float]) -> Dict[str, Any]:
        """预测趋势"""
        if len(values) < 5:
            return {"direction": "unknown", "confidence": 0.0}
        
        # 使用最后几个点进行简单预测
        recent_values = values[-5:]
        trend = self._calculate_trend(recent_values)
        
        return {
            "direction": trend["direction"],
            "confidence": min(trend["strength"], 0.9)
        }
    
    def _detect_outliers(self, values: List[float], sensitivity: float) -> List[float]:
        """检测异常值"""
        if len(values) < 4:
            return []
        
        # 使用IQR方法
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        q1 = sorted_values[int(n * 0.25)]
        q3 = sorted_values[int(n * 0.75)]
        iqr = q3 - q1
        
        # 根据敏感度调整阈值
        threshold = 1.5 + (1 - sensitivity) * 1.0
        
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        outliers = [x for x in values if x < lower_bound or x > upper_bound]
        return outliers
    
    def _calculate_correlation(self, values1: List[float], values2: List[float]) -> float:
        """计算相关系数"""
        if len(values1) != len(values2) or len(values1) < 2:
            return 0.0
        
        n = len(values1)
        mean1 = sum(values1) / n
        mean2 = sum(values2) / n
        
        numerator = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2))
        denominator = math.sqrt(sum((x - mean1) ** 2 for x in values1) * sum((y - mean2) ** 2 for y in values2))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _analyze_distribution_features(self, values: List[float]) -> Dict[str, Any]:
        """分析分布特征"""
        if len(values) < 3:
            return {}
        
        n = len(values)
        mean = sum(values) / n
        
        # 计算偏度
        variance = sum((x - mean) ** 2 for x in values) / n
        std = math.sqrt(variance)
        
        if std == 0:
            skewness = 0
            kurtosis = 0
        else:
            skewness = sum(((x - mean) / std) ** 3 for x in values) / n
            kurtosis = sum(((x - mean) / std) ** 4 for x in values) / n
        
        # 简化的正态性检验
        is_normal = abs(skewness) < 0.5 and abs(kurtosis - 3) < 0.5
        
        return {
            "mean": mean,
            "std": std,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "is_normal": is_normal
        }
    
    def _calculate_concentration(self, values: List[float]) -> float:
        """计算集中度"""
        if not values:
            return 0.0
        
        total = sum(values)
        if total == 0:
            return 0.0
        
        # 计算基尼系数
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        cumsum = 0
        gini = 0
        
        for i, value in enumerate(sorted_values):
            cumsum += value
            gini += (2 * (i + 1) - n - 1) * value
        
        gini = gini / (n * total)
        
        return gini
    
    def _analyze_chart_config(self, chart_config: Dict[str, Any]) -> Dict[str, Any]:
        """分析图表配置"""
        return {
            "has_title": bool(chart_config.get("title", {}).get("text")),
            "has_x_axis_label": bool(chart_config.get("xAxis", {}).get("title")),
            "has_y_axis_label": bool(chart_config.get("yAxis", {}).get("title")),
            "has_legend": chart_config.get("legend", {}).get("show", False),
            "has_grid": chart_config.get("grid", {}).get("show", False)
        }
    
    def _analyze_data_quality(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析数据质量"""
        values = self._extract_values(chart_data)
        
        if not values:
            return {"data_points": 0, "missing_data_percentage": 100}
        
        # 计算缺失数据
        missing_count = sum(1 for v in values if v is None or (isinstance(v, float) and math.isnan(v)))
        missing_percentage = missing_count / len(values) * 100
        
        return {
            "data_points": len(values),
            "missing_data_percentage": missing_percentage,
            "unique_values": len(set(values)),
            "data_range": max(values) - min(values) if values else 0
        }
    
    def _calculate_visualization_score(self, chart_data: Dict[str, Any], chart_config: Optional[Dict[str, Any]]) -> float:
        """计算可视化分数"""
        score = 0.0
        
        # 数据质量分数
        data_quality = self._analyze_data_quality(chart_data)
        if data_quality["data_points"] > 10:
            score += 0.3
        if data_quality["missing_data_percentage"] < 5:
            score += 0.2
        
        # 配置分数
        if chart_config:
            config_analysis = self._analyze_chart_config(chart_config)
            if config_analysis["has_title"]:
                score += 0.1
            if config_analysis["has_x_axis_label"]:
                score += 0.1
            if config_analysis["has_y_axis_label"]:
                score += 0.1
            if config_analysis["has_legend"]:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_pattern_quality_score(self, metrics: Dict[str, Any]) -> float:
        """计算模式质量分数"""
        score = 0.5  # 基础分数
        
        if metrics.get("periodicity", 0) > 0:
            score += 0.2
        
        if metrics.get("monotonicity") != "none":
            score += 0.1
        
        volatility = metrics.get("volatility", 0)
        if 0.1 < volatility < 0.5:  # 适中的波动性
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_trend_quality_score(self, metrics: Dict[str, Any]) -> float:
        """计算趋势质量分数"""
        trend = metrics.get("trend", {})
        strength = trend.get("strength", 0)
        
        return min(strength, 1.0)
    
    def _calculate_outlier_quality_score(self, metrics: Dict[str, Any]) -> float:
        """计算异常值质量分数"""
        outlier_percentage = metrics.get("outlier_percentage", 0)
        
        if outlier_percentage < 5:
            return 0.9
        elif outlier_percentage < 15:
            return 0.7
        else:
            return 0.3
    
    def _calculate_correlation_quality_score(self, metrics: Dict[str, Any]) -> float:
        """计算相关性质量分数"""
        correlations = metrics.get("correlations", [])
        
        if not correlations:
            return 0.5
        
        strong_correlations = [c for c in correlations if abs(c["correlation"]) > 0.7]
        
        if len(strong_correlations) > 0:
            return 0.8
        else:
            return 0.6
    
    def _calculate_distribution_quality_score(self, metrics: Dict[str, Any]) -> float:
        """计算分布质量分数"""
        distribution = metrics.get("distribution", {})
        
        if distribution.get("is_normal", False):
            return 0.9
        
        skewness = abs(distribution.get("skewness", 0))
        if skewness < 1:
            return 0.7
        else:
            return 0.4
    
    def _calculate_optimization_quality_score(self, metrics: Dict[str, Any]) -> float:
        """计算优化质量分数"""
        visualization_score = metrics.get("visualization_score", 0)
        data_quality = metrics.get("data_quality", {})
        
        score = visualization_score * 0.6
        
        if data_quality.get("missing_data_percentage", 0) < 5:
            score += 0.2
        
        if data_quality.get("data_points", 0) > 20:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_overall_score(self, analysis_results: List[AnalysisResult]) -> float:
        """计算整体分数"""
        if not analysis_results:
            return 0.0
        
        scores = [result.quality_score for result in analysis_results]
        return sum(scores) / len(scores)
    
    def _determine_chart_quality(self, score: float) -> ChartQuality:
        """确定图表质量"""
        if score >= 0.8:
            return ChartQuality.EXCELLENT
        elif score >= 0.6:
            return ChartQuality.GOOD
        elif score >= 0.4:
            return ChartQuality.FAIR
        else:
            return ChartQuality.POOR
    
    def _extract_key_insights(self, analysis_results: List[AnalysisResult]) -> List[str]:
        """提取关键洞察"""
        insights = []
        
        for result in analysis_results:
            # 选择最重要的发现
            if result.findings:
                insights.extend(result.findings[:2])  # 每个分析最多2个洞察
        
        return insights[:5]  # 最多5个关键洞察
    
    def _generate_optimization_suggestions(self, chart_data: Dict[str, Any], chart_config: Optional[Dict[str, Any]], analysis_results: List[AnalysisResult]) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        for result in analysis_results:
            suggestions.extend(result.recommendations)
        
        # 去重并限制数量
        unique_suggestions = list(set(suggestions))
        return unique_suggestions[:8]  # 最多8个建议


def create_chart_analyzer_tool(container: Any) -> ChartAnalyzerTool:
    """
    创建图表分析工具

    Args:
        container: 服务容器

    Returns:
        ChartAnalyzerTool 实例
    """
    return ChartAnalyzerTool(container)


# 导出
__all__ = [
    "ChartAnalyzerTool",
    "AnalysisFocus",
    "ChartQuality",
    "AnalysisConfig",
    "AnalysisResult",
    "ComprehensiveChartAnalysis",
    "create_chart_analyzer_tool",
]