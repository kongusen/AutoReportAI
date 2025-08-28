"""
数据分析Agent - 对查询数据进行统计分析、趋势分析和洞察发现

功能特性：
- 基础统计分析（求和、平均、最大最小值等）
- 时间序列分析（趋势、同比环比）
- 异常值检测
- 数据分布分析
- 关联性分析
- 业务洞察生成
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics

from ..base import BaseAgent
from ...context.execution_context import EnhancedExecutionContext, ContextScope

logger = logging.getLogger(__name__)


@dataclass
class AnalysisInsight:
    """分析洞察"""
    type: str  # 洞察类型：trend, anomaly, comparison, pattern
    title: str  # 洞察标题
    description: str  # 详细描述
    importance: float  # 重要性评分 0-1
    confidence: float  # 置信度 0-1
    data_points: List[Any] = None  # 相关数据点
    
    def to_dict(self):
        return {
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "importance": self.importance,
            "confidence": self.confidence,
            "data_points": self.data_points or []
        }


class DataAnalysisAgent(BaseAgent):
    """数据分析Agent"""
    
    def __init__(self):
        super().__init__("data_analysis", ["statistical_analysis", "trend_analysis", "anomaly_detection"])
        self.require_context("query_result", "parsed_request")
        
        # 分析配置
        self.analysis_config = {
            'trend_threshold': 0.05,  # 趋势变化阈值
            'anomaly_threshold': 2.0,  # 异常值检测阈值（标准差倍数）
            'significance_level': 0.05,  # 显著性水平
            'min_data_points': 3  # 最少数据点要求
        }

    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行数据分析"""
        try:
            # 获取查询结果和解析请求
            query_result = context.get_context("query_result")
            parsed_request = context.get_context("parsed_request")
            
            if not query_result:
                return {
                    "success": False,
                    "error": "缺少查询结果数据",
                    "data": {}
                }
            
            # 处理多个查询结果
            if isinstance(query_result, dict) and 'query_results' in query_result:
                return await self._analyze_multiple_results(query_result, parsed_request, context)
            else:
                return await self._analyze_single_result(query_result, parsed_request, context)
                
        except Exception as e:
            logger.error(f"数据分析Agent执行失败: {e}")
            return {
                "success": False,
                "error": f"数据分析失败: {str(e)}",
                "data": {}
            }

    async def _analyze_multiple_results(self, query_results: Dict[str, Any], 
                                      parsed_requests: Dict[str, Any],
                                      context: EnhancedExecutionContext) -> Dict[str, Any]:
        """分析多个查询结果"""
        analysis_results = []
        
        for query_result in query_results.get('query_results', []):
            if not query_result.get('success', False):
                continue
            
            try:
                # 获取对应的解析请求
                placeholder_index = query_result.get('placeholder_index', 0)
                parsed_request = None
                
                if isinstance(parsed_requests, dict) and 'placeholders' in parsed_requests:
                    placeholders = parsed_requests['placeholders']
                    if 0 <= placeholder_index < len(placeholders):
                        parsed_request = placeholders[placeholder_index]
                
                if not parsed_request:
                    continue
                
                # 分析单个结果
                analysis = await self._perform_single_analysis(
                    query_result, parsed_request, context
                )
                
                analysis['placeholder_index'] = placeholder_index
                analysis['original_text'] = query_result.get('original_text', '')
                analysis_results.append(analysis)
                
                # 存储到上下文
                context.set_context(f"analysis_result_{placeholder_index}", analysis, ContextScope.REQUEST)
                
            except Exception as e:
                logger.error(f"分析第{placeholder_index}个结果失败: {e}")
                analysis_results.append({
                    'placeholder_index': placeholder_index,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            "success": True,
            "data": {
                "analysis_results": analysis_results,
                "summary": self._generate_multi_analysis_summary(analysis_results)
            }
        }

    async def _analyze_single_result(self, query_result: Dict[str, Any], 
                                   parsed_request: Dict[str, Any],
                                   context: EnhancedExecutionContext) -> Dict[str, Any]:
        """分析单个查询结果"""
        analysis = await self._perform_single_analysis(query_result, parsed_request, context)
        context.set_context("analysis_result", analysis, ContextScope.REQUEST)
        
        return {
            "success": True,
            "data": analysis
        }

    async def _perform_single_analysis(self, query_result: Dict[str, Any],
                                     parsed_request: Dict[str, Any],
                                     context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行单个结果的分析"""
        logger.info(f"分析数据: {parsed_request.get('task_type')} - {parsed_request.get('metric')}")
        
        raw_data = query_result.get('raw_data', [])
        task_type = parsed_request.get('task_type', 'statistics')
        
        if not raw_data:
            return {
                "success": False,
                "error": "查询结果为空",
                "data": {}
            }
        
        # 转换为DataFrame进行分析
        df = pd.DataFrame(raw_data)
        
        # 执行分析
        analysis_result = {
            "success": True,
            "task_type": task_type,
            "data_summary": self._generate_data_summary(df),
            "statistics": await self._calculate_basic_statistics(df, task_type),
            "insights": await self._generate_insights(df, task_type, parsed_request),
            "trends": await self._analyze_trends(df, task_type),
            "anomalies": await self._detect_anomalies(df),
            "recommendations": await self._generate_recommendations(df, task_type, parsed_request)
        }
        
        return analysis_result

    def _generate_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """生成数据概要"""
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "has_missing_values": df.isnull().sum().sum() > 0,
            "missing_value_count": df.isnull().sum().to_dict(),
            "data_types": df.dtypes.to_dict()
        }

    async def _calculate_basic_statistics(self, df: pd.DataFrame, task_type: str) -> Dict[str, Any]:
        """计算基础统计指标"""
        stats = {}
        
        # 数值列统计
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            values = df[column].dropna()
            if len(values) > 0:
                stats[column] = {
                    "count": len(values),
                    "sum": float(values.sum()),
                    "mean": float(values.mean()),
                    "median": float(values.median()),
                    "std": float(values.std()) if len(values) > 1 else 0.0,
                    "min": float(values.min()),
                    "max": float(values.max()),
                    "q25": float(values.quantile(0.25)),
                    "q75": float(values.quantile(0.75))
                }
        
        # 分类列统计
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns
        
        for column in categorical_columns:
            value_counts = df[column].value_counts()
            stats[f"{column}_distribution"] = {
                "unique_count": len(value_counts),
                "most_frequent": value_counts.index[0] if len(value_counts) > 0 else None,
                "most_frequent_count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                "distribution": value_counts.head(10).to_dict()
            }
        
        # 任务特定统计
        if task_type == 'line_chart':
            stats.update(await self._calculate_time_series_stats(df))
        elif task_type in ['bar_chart', 'pie_chart']:
            stats.update(await self._calculate_categorical_stats(df))
        
        return stats

    async def _calculate_time_series_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算时间序列统计"""
        time_stats = {}
        
        # 寻找时间列和数值列
        time_columns = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower() or 'period' in col.lower()]
        value_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if time_columns and value_columns:
            time_col = time_columns[0]
            value_col = value_columns[0]
            
            # 按时间排序
            df_sorted = df.sort_values(time_col)
            values = df_sorted[value_col].values
            
            if len(values) > 1:
                # 计算增长率
                growth_rates = []
                for i in range(1, len(values)):
                    if values[i-1] != 0:
                        growth_rate = (values[i] - values[i-1]) / values[i-1]
                        growth_rates.append(growth_rate)
                
                if growth_rates:
                    time_stats["trend_analysis"] = {
                        "average_growth_rate": float(np.mean(growth_rates)),
                        "growth_rate_std": float(np.std(growth_rates)),
                        "positive_periods": sum(1 for rate in growth_rates if rate > 0),
                        "negative_periods": sum(1 for rate in growth_rates if rate < 0),
                        "max_growth_rate": float(max(growth_rates)),
                        "min_growth_rate": float(min(growth_rates))
                    }
                
                # 趋势方向
                if len(values) >= 3:
                    # 简单线性趋势
                    x = np.arange(len(values))
                    slope, _ = np.polyfit(x, values, 1)
                    
                    trend_direction = "increasing" if slope > self.analysis_config['trend_threshold'] else \
                                    "decreasing" if slope < -self.analysis_config['trend_threshold'] else \
                                    "stable"
                    
                    time_stats["trend_direction"] = trend_direction
                    time_stats["trend_strength"] = abs(float(slope))
        
        return time_stats

    async def _calculate_categorical_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算分类数据统计"""
        categorical_stats = {}
        
        # 寻找分类列和数值列
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if categorical_columns and numeric_columns:
            cat_col = categorical_columns[0]
            num_col = numeric_columns[0]
            
            # 按类别分组统计
            grouped = df.groupby(cat_col)[num_col].agg(['sum', 'mean', 'count'])
            
            categorical_stats["category_analysis"] = {
                "top_category": grouped['sum'].idxmax(),
                "top_category_value": float(grouped['sum'].max()),
                "bottom_category": grouped['sum'].idxmin(),
                "bottom_category_value": float(grouped['sum'].min()),
                "category_count": len(grouped),
                "value_distribution": grouped['sum'].to_dict(),
                "concentration_ratio": float(grouped['sum'].max() / grouped['sum'].sum())  # 最大类别占比
            }
        
        return categorical_stats

    async def _generate_insights(self, df: pd.DataFrame, task_type: str, 
                               parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成数据洞察"""
        insights = []
        
        try:
            # 基于任务类型生成不同洞察
            if task_type == 'line_chart':
                insights.extend(await self._generate_trend_insights(df, parsed_request))
            elif task_type in ['bar_chart', 'pie_chart']:
                insights.extend(await self._generate_categorical_insights(df, parsed_request))
            elif task_type == 'statistics':
                insights.extend(await self._generate_statistical_insights(df, parsed_request))
            
            # 通用洞察
            insights.extend(await self._generate_general_insights(df, parsed_request))
            
            # 按重要性排序
            insights.sort(key=lambda x: x.get('importance', 0), reverse=True)
            
        except Exception as e:
            logger.error(f"生成洞察失败: {e}")
            insights.append(AnalysisInsight(
                type="error",
                title="洞察生成失败",
                description=f"无法生成数据洞察: {str(e)}",
                importance=0.1,
                confidence=0.5
            ).to_dict())
        
        return insights[:10]  # 最多返回10个洞察

    async def _generate_trend_insights(self, df: pd.DataFrame, 
                                     parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成趋势洞察"""
        insights = []
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_columns:
            return insights
        
        value_col = numeric_columns[0]
        values = df[value_col].values
        
        if len(values) >= 3:
            # 趋势分析
            x = np.arange(len(values))
            slope, _ = np.polyfit(x, values, 1)
            
            if slope > self.analysis_config['trend_threshold']:
                trend_type = "上升"
                importance = min(abs(slope) / np.mean(values), 1.0)
            elif slope < -self.analysis_config['trend_threshold']:
                trend_type = "下降"
                importance = min(abs(slope) / np.mean(values), 1.0)
            else:
                trend_type = "平稳"
                importance = 0.3
            
            insights.append(AnalysisInsight(
                type="trend",
                title=f"数据呈{trend_type}趋势",
                description=f"通过分析{len(values)}个数据点，发现{parsed_request.get('metric', '指标')}整体呈{trend_type}趋势",
                importance=importance,
                confidence=0.8
            ).to_dict())
            
            # 最值洞察
            max_idx = np.argmax(values)
            min_idx = np.argmin(values)
            
            insights.append(AnalysisInsight(
                type="extremes",
                title="峰值和谷值分析",
                description=f"最高值出现在第{max_idx+1}个时间点({values[max_idx]})，最低值出现在第{min_idx+1}个时间点({values[min_idx]})",
                importance=0.7,
                confidence=0.9,
                data_points=[{"max_index": int(max_idx), "max_value": float(values[max_idx])},
                            {"min_index": int(min_idx), "min_value": float(values[min_idx])}]
            ).to_dict())
        
        return insights

    async def _generate_categorical_insights(self, df: pd.DataFrame, 
                                           parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成分类洞察"""
        insights = []
        
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not categorical_columns or not numeric_columns:
            return insights
        
        cat_col = categorical_columns[0]
        num_col = numeric_columns[0]
        
        # 分类占比分析
        grouped = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False)
        total = grouped.sum()
        
        if len(grouped) > 0:
            top_category = grouped.index[0]
            top_value = grouped.iloc[0]
            top_ratio = top_value / total
            
            insights.append(AnalysisInsight(
                type="dominance",
                title=f"{top_category}占据主导地位",
                description=f"{top_category}的{parsed_request.get('metric', '数值')}为{top_value:.2f}，占总体的{top_ratio:.1%}",
                importance=top_ratio,
                confidence=0.9,
                data_points=[{"category": top_category, "value": float(top_value), "ratio": float(top_ratio)}]
            ).to_dict())
            
            # 长尾分析
            if len(grouped) > 3:
                top3_ratio = grouped.head(3).sum() / total
                insights.append(AnalysisInsight(
                    type="concentration",
                    title="数据集中度分析",
                    description=f"前3个类别占总体的{top3_ratio:.1%}，{'集中度较高' if top3_ratio > 0.7 else '分布相对均匀'}",
                    importance=0.6,
                    confidence=0.8
                ).to_dict())
        
        return insights

    async def _generate_statistical_insights(self, df: pd.DataFrame, 
                                           parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成统计洞察"""
        insights = []
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for column in numeric_columns:
            values = df[column].dropna()
            if len(values) > 0:
                mean_val = values.mean()
                std_val = values.std()
                
                # 变异系数分析
                cv = std_val / mean_val if mean_val != 0 else 0
                if cv > 0.3:
                    insights.append(AnalysisInsight(
                        type="variability",
                        title=f"{column}数据波动较大",
                        description=f"{column}的变异系数为{cv:.2f}，数据波动相对较大，需要关注稳定性",
                        importance=min(cv, 1.0),
                        confidence=0.7
                    ).to_dict())
                
                # 分布特征
                if len(values) > 10:
                    q25, q75 = values.quantile([0.25, 0.75])
                    iqr = q75 - q25
                    
                    if iqr > 0:
                        insights.append(AnalysisInsight(
                            type="distribution", 
                            title=f"{column}分布特征",
                            description=f"{column}的四分位距为{iqr:.2f}，中位数为{values.median():.2f}",
                            importance=0.5,
                            confidence=0.8,
                            data_points=[{"q25": float(q25), "q75": float(q75), "median": float(values.median())}]
                        ).to_dict())
        
        return insights

    async def _generate_general_insights(self, df: pd.DataFrame, 
                                       parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成通用洞察"""
        insights = []
        
        # 数据完整性洞察
        missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        if missing_ratio > 0.1:
            insights.append(AnalysisInsight(
                type="data_quality",
                title="数据完整性提醒",
                description=f"数据集中有{missing_ratio:.1%}的缺失值，可能影响分析结果的准确性",
                importance=missing_ratio,
                confidence=0.9
            ).to_dict())
        
        # 样本大小洞察
        sample_size = len(df)
        if sample_size < 10:
            insights.append(AnalysisInsight(
                type="sample_size",
                title="样本量较小",
                description=f"当前样本量为{sample_size}，建议增加样本量以提高分析可靠性",
                importance=0.6,
                confidence=0.8
            ).to_dict())
        
        return insights

    async def _analyze_trends(self, df: pd.DataFrame, task_type: str) -> Dict[str, Any]:
        """趋势分析"""
        trends = {"detected": False}
        
        if task_type != 'line_chart':
            return trends
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_columns:
            return trends
        
        value_col = numeric_columns[0]
        values = df[value_col].values
        
        if len(values) >= 3:
            # 线性趋势
            x = np.arange(len(values))
            slope, intercept = np.polyfit(x, values, 1)
            r_squared = np.corrcoef(x, values)[0, 1] ** 2
            
            trends.update({
                "detected": True,
                "linear_trend": {
                    "slope": float(slope),
                    "intercept": float(intercept),
                    "r_squared": float(r_squared),
                    "direction": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
                }
            })
            
            # 季节性检测（简单版）
            if len(values) >= 12:
                # 简单的周期性检测
                try:
                    from scipy import stats
                    # 使用自相关检测周期性（简化版）
                    autocorr = [np.corrcoef(values[:-i], values[i:])[0, 1] for i in range(1, min(len(values)//2, 12))]
                    max_autocorr_idx = np.argmax(autocorr) + 1
                    
                    if autocorr[max_autocorr_idx-1] > 0.5:
                        trends["seasonality"] = {
                            "detected": True,
                            "period": int(max_autocorr_idx),
                            "strength": float(autocorr[max_autocorr_idx-1])
                        }
                except:
                    pass
        
        return trends

    async def _detect_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """异常值检测"""
        anomalies = {"detected": False, "anomalies": []}
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for column in numeric_columns:
            values = df[column].dropna()
            if len(values) < 5:  # 数据点太少，跳过异常检测
                continue
            
            # 使用IQR方法检测异常值
            q25, q75 = values.quantile([0.25, 0.75])
            iqr = q75 - q25
            
            if iqr > 0:
                lower_bound = q25 - 1.5 * iqr
                upper_bound = q75 + 1.5 * iqr
                
                outliers = values[(values < lower_bound) | (values > upper_bound)]
                
                if len(outliers) > 0:
                    anomalies["detected"] = True
                    anomalies["anomalies"].append({
                        "column": column,
                        "outlier_count": len(outliers),
                        "outlier_ratio": len(outliers) / len(values),
                        "outlier_values": outliers.tolist()[:10],  # 最多显示10个异常值
                        "bounds": {"lower": float(lower_bound), "upper": float(upper_bound)}
                    })
        
        return anomalies

    async def _generate_recommendations(self, df: pd.DataFrame, task_type: str,
                                      parsed_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成建议"""
        recommendations = []
        
        # 基于任务类型的建议
        if task_type == 'line_chart':
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_columns:
                values = df[numeric_columns[0]].values
                if len(values) >= 3:
                    x = np.arange(len(values))
                    slope, _ = np.polyfit(x, values, 1)
                    
                    if slope > 0:
                        recommendations.append({
                            "type": "action",
                            "title": "趋势向好，建议持续关注",
                            "description": "当前数据呈上升趋势，建议保持现有策略并持续监控",
                            "priority": "medium"
                        })
                    elif slope < 0:
                        recommendations.append({
                            "type": "alert",
                            "title": "下降趋势需要关注",
                            "description": "数据呈下降趋势，建议分析原因并采取改进措施",
                            "priority": "high"
                        })
        
        elif task_type in ['bar_chart', 'pie_chart']:
            # 分类数据建议
            categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if categorical_columns and numeric_columns:
                cat_col = categorical_columns[0]
                num_col = numeric_columns[0]
                
                grouped = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False)
                total = grouped.sum()
                
                if len(grouped) > 0:
                    top_ratio = grouped.iloc[0] / total
                    
                    if top_ratio > 0.7:
                        recommendations.append({
                            "type": "balance",
                            "title": "建议关注数据分布均衡性",
                            "description": f"最大类别占比过高({top_ratio:.1%})，建议关注其他类别的发展",
                            "priority": "medium"
                        })
        
        # 数据质量建议
        missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        if missing_ratio > 0.1:
            recommendations.append({
                "type": "data_quality",
                "title": "改善数据完整性",
                "description": f"数据缺失率为{missing_ratio:.1%}，建议完善数据收集流程",
                "priority": "high"
            })
        
        # 样本量建议
        if len(df) < 30:
            recommendations.append({
                "type": "data_collection",
                "title": "增加样本量",
                "description": "当前样本量较少，建议收集更多数据以提高分析可靠性",
                "priority": "medium"
            })
        
        return recommendations

    def _generate_multi_analysis_summary(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成多分析结果摘要"""
        successful_analyses = [r for r in analysis_results if r.get('success', False)]
        
        return {
            "total_analyses": len(analysis_results),
            "successful_analyses": len(successful_analyses),
            "success_rate": len(successful_analyses) / len(analysis_results) if analysis_results else 0,
            "task_type_distribution": self._count_task_types(successful_analyses),
            "total_insights": sum(len(r.get('insights', [])) for r in successful_analyses),
            "total_recommendations": sum(len(r.get('recommendations', [])) for r in successful_analyses)
        }

    def _count_task_types(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计任务类型分布"""
        task_type_counts = {}
        for result in analysis_results:
            task_type = result.get('task_type', 'unknown')
            task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1
        return task_type_counts