from __future__ import annotations

from loom.interfaces.tool import BaseTool
"""
数据分析工具

分析数据特征、统计信息和模式
支持描述性统计、相关性分析和异常检测
"""


import logging
import math
import statistics
from typing import Any, Dict, List, Optional, Union, Tuple, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """分析类型"""
    DESCRIPTIVE = "descriptive"     # 描述性统计
    CORRELATION = "correlation"     # 相关性分析
    DISTRIBUTION = "distribution"    # 分布分析
    OUTLIER = "outlier"            # 异常值检测
    TREND = "trend"               # 趋势分析
    PATTERN = "pattern"            # 模式识别


class StatisticalMeasure(str, Enum):
    """统计量"""
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    STD = "std"
    VARIANCE = "variance"
    MIN = "min"
    MAX = "max"
    QUARTILE_25 = "q25"
    QUARTILE_75 = "q75"
    SKEWNESS = "skewness"
    KURTOSIS = "kurtosis"


@dataclass
class AnalysisConfig:
    """分析配置"""
    analysis_types: List[AnalysisType]
    confidence_level: float = 0.95
    outlier_method: str = "iqr"  # iqr, zscore, modified_zscore
    correlation_method: str = "pearson"  # pearson, spearman, kendall
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_type: AnalysisType
    results: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ComprehensiveAnalysisReport:
    """综合分析报告"""
    data_summary: Dict[str, Any]
    descriptive_stats: Dict[str, Any]
    correlation_matrix: Dict[str, Any]
    outlier_analysis: Dict[str, Any]
    distribution_analysis: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DataAnalyzerTool(BaseTool):
    """数据分析工具"""
    
    def __init__(self, container: Any):
        """
        Args:
            container: 服务容器
        """
        super().__init__()

        self.name = "data_analyzer"

        self.category = ToolCategory.DATA

        self.description = "分析数据特征、统计信息和模式" 
        self.container = container
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class DataAnalyzerArgs(BaseModel):
            data: List[Dict[str, Any]] = Field(description="要分析的数据")
            analysis_types: Optional[List[Literal[
                "descriptive", "correlation", "distribution", "outlier", "trend", "pattern"
            ]]] = Field(default=["descriptive", "correlation", "outlier"], description="要执行的分析类型")
            target_columns: Optional[List[str]] = Field(default=None, description="目标分析列")
            confidence_level: float = Field(default=0.95, description="置信水平")
            outlier_method: Literal["iqr", "zscore", "modified_zscore"] = Field(default="iqr", description="异常值检测方法")
            correlation_method: Literal["pearson", "spearman", "kendall"] = Field(default="pearson", description="相关性分析方法")
            generate_insights: bool = Field(default=True, description="是否生成洞察")

        self.args_schema = DataAnalyzerArgs
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "data_analyzer",
                "description": "分析数据特征、统计信息和模式",
                "parameters": parameters,
            },
        }
    
    async def run(

    
        self,
        data: List[Dict[str, Any]],
        analysis_types: Optional[List[str]] = None,
        target_columns: Optional[List[str]] = None,
        confidence_level: float = 0.95,
        outlier_method: str = "iqr",
        correlation_method: str = "pearson",
        generate_insights: bool = True,
        **kwargs
    

    
    ) -> Dict[str, Any]:
        """
        执行数据分析

    Args:
            data: 要分析的数据
            analysis_types: 要执行的分析类型
            target_columns: 目标分析列
            confidence_level: 置信水平
            outlier_method: 异常值检测方法
            correlation_method: 相关性分析方法
            generate_insights: 是否生成洞察

    Returns:
            Dict[str, Any]: 分析结果
        """
        logger.info(f"📈 [DataAnalyzerTool] 开始分析")
        logger.info(f"   数据行数: {len(data)}")

    
    async def execute(self, **kwargs) -> Dict[str, Any]:

    
        """向后兼容的execute方法"""

    
        return await self.run(**kwargs)
        logger.info(f"   分析类型: {analysis_types}")
        
        try:
            if not data:
                return {
                    "success": False,
                    "error": "数据为空",
                    "result": None
                }
            
            # 设置默认分析类型
            if analysis_types is None:
                analysis_types = ["descriptive", "correlation", "outlier"]
            
            # 构建分析配置
            config = AnalysisConfig(
                analysis_types=[AnalysisType(t) for t in analysis_types],
                confidence_level=confidence_level,
                outlier_method=outlier_method,
                correlation_method=correlation_method
            )
            
            # 确定目标列
            if target_columns is None:
                target_columns = list(data[0].keys()) if data else []
            
            # 执行分析
            results = {}
            insights = []
            recommendations = []
            
            for analysis_type in config.analysis_types:
                result = await self._perform_analysis(data, analysis_type, target_columns, config)
                results[analysis_type.value] = result.results
                insights.extend(result.insights)
                recommendations.extend(result.recommendations)
            
            # 生成综合报告
            report = ComprehensiveAnalysisReport(
                data_summary=self._generate_data_summary(data),
                descriptive_stats=results.get("descriptive", {}),
                correlation_matrix=results.get("correlation", {}),
                outlier_analysis=results.get("outlier", {}),
                distribution_analysis=results.get("distribution", {}),
                insights=insights,
                recommendations=recommendations
            )
            
            return {
                "success": True,
                "result": report,
                "metadata": {
                    "analysis_types": analysis_types,
                    "target_columns": target_columns,
                    "data_rows": len(data),
                    "data_columns": len(target_columns),
                    "insights_count": len(insights),
                    "recommendations_count": len(recommendations)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [DataAnalyzerTool] 分析失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    async def _perform_analysis(
        self,
        data: List[Dict[str, Any]],
        analysis_type: AnalysisType,
        target_columns: List[str],
        config: AnalysisConfig
    ) -> AnalysisResult:
        """执行特定类型的分析"""
        if analysis_type == AnalysisType.DESCRIPTIVE:
            return self._descriptive_analysis(data, target_columns)
        elif analysis_type == AnalysisType.CORRELATION:
            return self._correlation_analysis(data, target_columns, config)
        elif analysis_type == AnalysisType.DISTRIBUTION:
            return self._distribution_analysis(data, target_columns)
        elif analysis_type == AnalysisType.OUTLIER:
            return self._outlier_analysis(data, target_columns, config)
        elif analysis_type == AnalysisType.TREND:
            return self._trend_analysis(data, target_columns)
        elif analysis_type == AnalysisType.PATTERN:
            return self._pattern_analysis(data, target_columns)
        else:
            return AnalysisResult(
                analysis_type=analysis_type,
                results={},
                insights=[],
                recommendations=[]
            )
    
    def _descriptive_analysis(self, data: List[Dict[str, Any]], target_columns: List[str]) -> AnalysisResult:
        """描述性统计分析"""
        results = {}
        insights = []
        recommendations = []
        
        for column in target_columns:
            values = self._extract_column_values(data, column)
            numeric_values = self._convert_to_numeric(values)
            
            if numeric_values:
                stats = self._calculate_numeric_statistics(numeric_values)
                results[column] = stats
                
                # 生成洞察
                if stats.get("std", 0) > stats.get("mean", 0) * 0.5:
                    insights.append(f"列 '{column}' 的数据变异性较大")
                
                if stats.get("skewness", 0) > 1:
                    insights.append(f"列 '{column}' 呈正偏态分布")
                elif stats.get("skewness", 0) < -1:
                    insights.append(f"列 '{column}' 呈负偏态分布")
                
                # 生成建议
                if stats.get("null_percentage", 0) > 20:
                    recommendations.append(f"列 '{column}' 缺失值较多，建议检查数据质量")
                
                if stats.get("unique_percentage", 0) > 90:
                    recommendations.append(f"列 '{column}' 唯一值比例很高，可能是标识符")
            else:
                # 分类数据统计
                stats = self._calculate_categorical_statistics(values)
                results[column] = stats
                
                if stats.get("unique_count", 0) < 10:
                    insights.append(f"列 '{column}' 是分类变量，有 {stats['unique_count']} 个类别")
                
                if stats.get("most_common_percentage", 0) > 80:
                    recommendations.append(f"列 '{column}' 存在主导类别，可能影响分析结果")
        
        return AnalysisResult(
            analysis_type=AnalysisType.DESCRIPTIVE,
            results=results,
            insights=insights,
            recommendations=recommendations
        )
    
    def _correlation_analysis(self, data: List[Dict[str, Any]], target_columns: List[str], config: AnalysisConfig) -> AnalysisResult:
        """相关性分析"""
        results = {}
        insights = []
        recommendations = []
        
        # 提取数值列
        numeric_columns = []
        for column in target_columns:
            values = self._extract_column_values(data, column)
            numeric_values = self._convert_to_numeric(values)
            if numeric_values and len(numeric_values) > 1:
                numeric_columns.append(column)
        
        if len(numeric_columns) < 2:
            insights.append("数值列不足，无法进行相关性分析")
            return AnalysisResult(
                analysis_type=AnalysisType.CORRELATION,
                results={},
                insights=insights,
                recommendations=recommendations
            )
        
        # 计算相关性矩阵
        correlation_matrix = {}
        for col1 in numeric_columns:
            correlation_matrix[col1] = {}
            values1 = self._convert_to_numeric(self._extract_column_values(data, col1))
            
            for col2 in numeric_columns:
                values2 = self._convert_to_numeric(self._extract_column_values(data, col2))
                
                if len(values1) == len(values2):
                    correlation = self._calculate_correlation(values1, values2, config.correlation_method)
                    correlation_matrix[col1][col2] = correlation
        
        results["correlation_matrix"] = correlation_matrix
        results["numeric_columns"] = numeric_columns
        
        # 分析强相关性
        strong_correlations = []
        for col1 in numeric_columns:
            for col2 in numeric_columns:
                if col1 != col2:
                    corr = correlation_matrix.get(col1, {}).get(col2, 0)
                    if abs(corr) > 0.7:
                        strong_correlations.append((col1, col2, corr))
        
        if strong_correlations:
            insights.append(f"发现 {len(strong_correlations)} 对强相关变量")
            for col1, col2, corr in strong_correlations[:3]:  # 只显示前3个
                insights.append(f"'{col1}' 和 '{col2}' 的相关系数为 {corr:.3f}")
        
        # 生成建议
        if strong_correlations:
            recommendations.append("存在强相关变量，考虑进行降维分析")
        
        return AnalysisResult(
            analysis_type=AnalysisType.CORRELATION,
            results=results,
            insights=insights,
            recommendations=recommendations
        )
    
    def _distribution_analysis(self, data: List[Dict[str, Any]], target_columns: List[str]) -> AnalysisResult:
        """分布分析"""
        results = {}
        insights = []
        recommendations = []
        
        for column in target_columns:
            values = self._extract_column_values(data, column)
            numeric_values = self._convert_to_numeric(values)
            
            if numeric_values:
                distribution_info = self._analyze_distribution(numeric_values)
                results[column] = distribution_info
                
                # 分析分布特征
                if distribution_info.get("is_normal", False):
                    insights.append(f"列 '{column}' 近似正态分布")
                elif distribution_info.get("skewness", 0) > 1:
                    insights.append(f"列 '{column}' 呈右偏分布")
                elif distribution_info.get("skewness", 0) < -1:
                    insights.append(f"列 '{column}' 呈左偏分布")
                
                if distribution_info.get("kurtosis", 0) > 3:
                    insights.append(f"列 '{column}' 呈尖峰分布")
                elif distribution_info.get("kurtosis", 0) < 3:
                    insights.append(f"列 '{column}' 呈平峰分布")
        
        return AnalysisResult(
            analysis_type=AnalysisType.DISTRIBUTION,
            results=results,
            insights=insights,
            recommendations=recommendations
        )
    
    def _outlier_analysis(self, data: List[Dict[str, Any]], target_columns: List[str], config: AnalysisConfig) -> AnalysisResult:
        """异常值分析"""
        results = {}
        insights = []
        recommendations = []
        
        for column in target_columns:
            values = self._extract_column_values(data, column)
            numeric_values = self._convert_to_numeric(values)
            
            if numeric_values and len(numeric_values) > 4:
                outliers = self._detect_outliers(numeric_values, config.outlier_method)
                outlier_info = {
                    "outlier_count": len(outliers),
                    "outlier_percentage": len(outliers) / len(numeric_values) * 100,
                    "outlier_values": outliers[:10],  # 只显示前10个
                    "method": config.outlier_method
                }
                results[column] = outlier_info
                
                if len(outliers) > 0:
                    insights.append(f"列 '{column}' 发现 {len(outliers)} 个异常值")
                    
                    if outlier_info["outlier_percentage"] > 5:
                        recommendations.append(f"列 '{column}' 异常值比例较高，建议检查数据质量")
        
        return AnalysisResult(
            analysis_type=AnalysisType.OUTLIER,
            results=results,
            insights=insights,
            recommendations=recommendations
        )
    
    def _trend_analysis(self, data: List[Dict[str, Any]], target_columns: List[str]) -> AnalysisResult:
        """趋势分析"""
        results = {}
        insights = []
        recommendations = []
        
        # 简化实现，假设数据按时间顺序排列
        for column in target_columns:
            values = self._extract_column_values(data, column)
            numeric_values = self._convert_to_numeric(values)
            
            if numeric_values and len(numeric_values) > 2:
                trend_info = self._analyze_trend(numeric_values)
                results[column] = trend_info
                
                if trend_info.get("trend", "stable") == "increasing":
                    insights.append(f"列 '{column}' 呈上升趋势")
                elif trend_info.get("trend", "stable") == "decreasing":
                    insights.append(f"列 '{column}' 呈下降趋势")
        
        return AnalysisResult(
            analysis_type=AnalysisType.TREND,
            results=results,
            insights=insights,
            recommendations=recommendations
        )
    
    def _pattern_analysis(self, data: List[Dict[str, Any]], target_columns: List[str]) -> AnalysisResult:
        """模式识别"""
        results = {}
        insights = []
        recommendations = []
        
        # 简化实现
        for column in target_columns:
            values = self._extract_column_values(data, column)
            
            # 检查重复模式
            value_counts = {}
            for value in values:
                value_str = str(value)
                value_counts[value_str] = value_counts.get(value_str, 0) + 1
            
            patterns = {
                "most_common": max(value_counts.items(), key=lambda x: x[1]) if value_counts else None,
                "unique_values": len(value_counts),
                "duplicate_percentage": (len(values) - len(value_counts)) / len(values) * 100 if values else 0
            }
            
            results[column] = patterns
            
            if patterns["duplicate_percentage"] > 50:
                insights.append(f"列 '{column}' 存在大量重复值")
        
        return AnalysisResult(
            analysis_type=AnalysisType.PATTERN,
            results=results,
            insights=insights,
            recommendations=recommendations
        )
    
    def _extract_column_values(self, data: List[Dict[str, Any]], column: str) -> List[Any]:
        """提取列值"""
        values = []
        for row in data:
            if column in row:
                values.append(row[column])
        return values
    
    def _convert_to_numeric(self, values: List[Any]) -> List[float]:
        """转换为数值"""
        numeric_values = []
        for value in values:
            if value is None:
                continue
            try:
                numeric_values.append(float(str(value)))
            except (ValueError, TypeError):
                continue
        return numeric_values
    
    def _calculate_numeric_statistics(self, values: List[float]) -> Dict[str, Any]:
        """计算数值统计量"""
        if not values:
            return {}
        
        stats = {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0,
            "variance": statistics.variance(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "null_count": 0,
            "null_percentage": 0,
            "unique_count": len(set(values)),
            "unique_percentage": len(set(values)) / len(values) * 100
        }
        
        # 计算分位数
        sorted_values = sorted(values)
        n = len(sorted_values)
        stats["q25"] = sorted_values[int(n * 0.25)] if n > 0 else 0
        stats["q75"] = sorted_values[int(n * 0.75)] if n > 0 else 0
        
        # 计算偏度和峰度
        if len(values) > 2:
            stats["skewness"] = self._calculate_skewness(values)
            stats["kurtosis"] = self._calculate_kurtosis(values)
        
        return stats
    
    def _calculate_categorical_statistics(self, values: List[Any]) -> Dict[str, Any]:
        """计算分类统计量"""
        if not values:
            return {}
        
        value_counts = {}
        null_count = 0
        
        for value in values:
            if value is None:
                null_count += 1
            else:
                value_str = str(value)
                value_counts[value_str] = value_counts.get(value_str, 0) + 1
        
        total_count = len(values)
        unique_count = len(value_counts)
        
        stats = {
            "count": total_count,
            "null_count": null_count,
            "null_percentage": null_count / total_count * 100,
            "unique_count": unique_count,
            "unique_percentage": unique_count / total_count * 100,
            "value_counts": value_counts,
            "most_common": max(value_counts.items(), key=lambda x: x[1]) if value_counts else None,
            "most_common_percentage": max(value_counts.values()) / total_count * 100 if value_counts else 0
        }
        
        return stats
    
    def _calculate_correlation(self, values1: List[float], values2: List[float], method: str) -> float:
        """计算相关性"""
        if len(values1) != len(values2) or len(values1) < 2:
            return 0.0
        
        if method == "pearson":
            return self._pearson_correlation(values1, values2)
        elif method == "spearman":
            return self._spearman_correlation(values1, values2)
        else:
            return self._pearson_correlation(values1, values2)
    
    def _pearson_correlation(self, values1: List[float], values2: List[float]) -> float:
        """皮尔逊相关系数"""
        n = len(values1)
        if n < 2:
            return 0.0
        
        mean1 = statistics.mean(values1)
        mean2 = statistics.mean(values2)
        
        numerator = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2))
        denominator = math.sqrt(sum((x - mean1) ** 2 for x in values1) * sum((y - mean2) ** 2 for y in values2))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _spearman_correlation(self, values1: List[float], values2: List[float]) -> float:
        """斯皮尔曼相关系数"""
        # 简化实现，使用皮尔逊相关系数
        return self._pearson_correlation(values1, values2)
    
    def _analyze_distribution(self, values: List[float]) -> Dict[str, Any]:
        """分析分布"""
        if not values:
            return {}
        
        stats = self._calculate_numeric_statistics(values)
        
        # 简化的正态性检验
        skewness = abs(stats.get("skewness", 0))
        kurtosis = abs(stats.get("kurtosis", 0))
        
        is_normal = skewness < 0.5 and abs(kurtosis - 3) < 0.5
        
        return {
            "is_normal": is_normal,
            "skewness": stats.get("skewness", 0),
            "kurtosis": stats.get("kurtosis", 0),
            "distribution_type": "normal" if is_normal else "non-normal"
        }
    
    def _detect_outliers(self, values: List[float], method: str) -> List[float]:
        """检测异常值"""
        if len(values) < 4:
            return []
        
        if method == "iqr":
            return self._iqr_outliers(values)
        elif method == "zscore":
            return self._zscore_outliers(values)
        else:
            return self._iqr_outliers(values)
    
    def _iqr_outliers(self, values: List[float]) -> List[float]:
        """IQR方法检测异常值"""
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        q1 = sorted_values[int(n * 0.25)]
        q3 = sorted_values[int(n * 0.75)]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [x for x in values if x < lower_bound or x > upper_bound]
        return outliers
    
    def _zscore_outliers(self, values: List[float]) -> List[float]:
        """Z-score方法检测异常值"""
        if len(values) < 2:
            return []
        
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        
        if std == 0:
            return []
        
        outliers = [x for x in values if abs((x - mean) / std) > 2]
        return outliers
    
    def _analyze_trend(self, values: List[float]) -> Dict[str, Any]:
        """分析趋势"""
        if len(values) < 2:
            return {"trend": "insufficient_data"}
        
        # 简单的线性趋势分析
        n = len(values)
        x_values = list(range(n))
        
        # 计算斜率
        mean_x = statistics.mean(x_values)
        mean_y = statistics.mean(values)
        
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, values))
        denominator = sum((x - mean_x) ** 2 for x in x_values)
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # 判断趋势
        if slope > 0.01:
            trend = "increasing"
        elif slope < -0.01:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "slope": slope,
            "strength": abs(slope)
        }
    
    def _calculate_skewness(self, values: List[float]) -> float:
        """计算偏度"""
        if len(values) < 3:
            return 0.0
        
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        
        if std == 0:
            return 0.0
        
        n = len(values)
        skewness = (n / ((n - 1) * (n - 2))) * sum(((x - mean) / std) ** 3 for x in values)
        return skewness
    
    def _calculate_kurtosis(self, values: List[float]) -> float:
        """计算峰度"""
        if len(values) < 4:
            return 0.0
        
        mean = statistics.mean(values)
        std = statistics.stdev(values)
        
        if std == 0:
            return 0.0
        
        n = len(values)
        kurtosis = (n * (n + 1) / ((n - 1) * (n - 2) * (n - 3))) * sum(((x - mean) / std) ** 4 for x in values) - (3 * (n - 1) ** 2 / ((n - 2) * (n - 3)))
        return kurtosis
    
    def _generate_data_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成数据摘要"""
        if not data:
            return {}
        
        return {
            "total_rows": len(data),
            "total_columns": len(data[0]) if data else 0,
            "columns": list(data[0].keys()) if data else [],
            "memory_usage_estimate": len(str(data))  # 粗略估计
        }


def create_data_analyzer_tool(container: Any) -> DataAnalyzerTool:
    """
    创建数据分析工具
    
    Args:
        container: 服务容器
        
    Returns:
        DataAnalyzerTool 实例
    """
    return DataAnalyzerTool(container)


# 导出
__all__ = [
    "DataAnalyzerTool",
    "AnalysisType",
    "StatisticalMeasure",
    "AnalysisConfig",
    "AnalysisResult",
    "ComprehensiveAnalysisReport",
    "create_data_analyzer_tool",
]