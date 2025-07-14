from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from enum import Enum

class AnalyticsOperationType(str, Enum):
    """统计分析操作类型"""
    PERIOD_COMPARISON = "period_comparison"  # 环比
    YEAR_OVER_YEAR = "year_over_year"  # 同比
    SUMMARY_STATISTICS = "summary_statistics"  # 汇总统计
    GROWTH_RATE = "growth_rate"  # 增长率
    PROPORTION = "proportion"  # 比例分析
    TREND_ANALYSIS = "trend_analysis"  # 趋势分析
    MOVING_AVERAGE = "moving_average"  # 移动平均
    PERCENTILE = "percentile"  # 百分位数

@dataclass
class AnalyticsContext:
    """分析上下文"""
    data: pd.DataFrame
    date_column: str
    value_columns: List[str]
    group_columns: Optional[List[str]] = None
    period_type: str = "daily"  # daily, weekly, monthly, yearly
    baseline_period: Optional[str] = None

class MCPAnalyticsEngine:
    """基于MCP的统计分析引擎"""
    
    def __init__(self):
        self.operations = {
            AnalyticsOperationType.PERIOD_COMPARISON: self._calculate_period_comparison,
            AnalyticsOperationType.YEAR_OVER_YEAR: self._calculate_yoy_comparison,
            AnalyticsOperationType.SUMMARY_STATISTICS: self._calculate_summary_stats,
            AnalyticsOperationType.GROWTH_RATE: self._calculate_growth_rate,
            AnalyticsOperationType.PROPORTION: self._calculate_proportion,
            AnalyticsOperationType.TREND_ANALYSIS: self._calculate_trend,
            AnalyticsOperationType.MOVING_AVERAGE: self._calculate_moving_average,
            AnalyticsOperationType.PERCENTILE: self._calculate_percentile,
        }
    
    async def execute_analytics(self, 
                              operation: AnalyticsOperationType,
                              context: AnalyticsContext,
                              parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行统计分析操作"""
        
        if operation not in self.operations:
            raise ValueError(f"不支持的操作类型: {operation}")
        
        try:
            result = await self.operations[operation](context, parameters or {})
            return {
                "operation": operation,
                "status": "success",
                "result": result,
                "metadata": {
                    "data_shape": context.data.shape,
                    "columns_analyzed": context.value_columns,
                    "period_type": context.period_type
                }
            }
        except Exception as e:
            return {
                "operation": operation,
                "status": "error",
                "error": str(e),
                "metadata": {
                    "data_shape": context.data.shape,
                    "columns_analyzed": context.value_columns
                }
            }
    
    async def _calculate_period_comparison(self, 
                                         context: AnalyticsContext, 
                                         parameters: Dict[str, Any]) -> Dict[str, Any]:
        """计算环比分析"""
        df = context.data.copy()
        date_col = context.date_column
        value_cols = context.value_columns
        
        # 确保日期列为datetime类型
        df[date_col] = pd.to_datetime(df[date_col])
        
        # 按日期排序
        df = df.sort_values(date_col)
        
        # 设置日期为索引
        df.set_index(date_col, inplace=True)
        
        results = {}
        
        for col in value_cols:
            # 计算环比变化
            current_values = df[col]
            previous_values = df[col].shift(1)
            
            # 环比变化量
            period_change = current_values - previous_values
            
            # 环比变化率
            period_change_rate = (period_change / previous_values.replace(0, np.nan)) * 100
            
            results[col] = {
                "current_values": current_values.dropna().tolist(),
                "previous_values": previous_values.dropna().tolist(),
                "period_change": period_change.dropna().tolist(),
                "period_change_rate": period_change_rate.dropna().tolist(),
                "summary": {
                    "avg_change": period_change.mean(),
                    "avg_change_rate": period_change_rate.mean(),
                    "positive_periods": (period_change > 0).sum(),
                    "negative_periods": (period_change < 0).sum()
                }
            }
        
        return results
    
    async def _calculate_yoy_comparison(self, 
                                      context: AnalyticsContext, 
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """计算同比分析"""
        df = context.data.copy()
        date_col = context.date_column
        value_cols = context.value_columns
        
        # 确保日期列为datetime类型
        df[date_col] = pd.to_datetime(df[date_col])
        
        # 添加年份和月份列
        df['year'] = df[date_col].dt.year
        df['month'] = df[date_col].dt.month
        
        results = {}
        
        for col in value_cols:
            # 按年月分组
            monthly_data = df.groupby(['year', 'month'])[col].sum().reset_index()
            
            # 计算同比变化
            yoy_changes = []
            yoy_rates = []
            
            for _, row in monthly_data.iterrows():
                current_year = row['year']
                current_month = row['month']
                current_value = row[col]
                
                # 查找去年同期数据
                last_year_data = monthly_data[
                    (monthly_data['year'] == current_year - 1) & 
                    (monthly_data['month'] == current_month)
                ]
                
                if not last_year_data.empty:
                    last_year_value = last_year_data.iloc[0][col]
                    yoy_change = current_value - last_year_value
                    yoy_rate = (yoy_change / last_year_value) * 100 if last_year_value != 0 else 0
                    
                    yoy_changes.append({
                        'year': current_year,
                        'month': current_month,
                        'change': yoy_change,
                        'rate': yoy_rate,
                        'current': current_value,
                        'previous': last_year_value
                    })
            
            results[col] = {
                "yoy_changes": yoy_changes,
                "summary": {
                    "avg_yoy_change": np.mean([x['change'] for x in yoy_changes]) if yoy_changes else 0,
                    "avg_yoy_rate": np.mean([x['rate'] for x in yoy_changes]) if yoy_changes else 0,
                    "positive_periods": len([x for x in yoy_changes if x['change'] > 0]),
                    "negative_periods": len([x for x in yoy_changes if x['change'] < 0])
                }
            }
        
        return results
    
    async def _calculate_summary_stats(self, 
                                     context: AnalyticsContext, 
                                     parameters: Dict[str, Any]) -> Dict[str, Any]:
        """计算汇总统计"""
        df = context.data.copy()
        value_cols = context.value_columns
        group_cols = context.group_columns
        
        results = {}
        
        if group_cols:
            # 按分组计算统计
            grouped = df.groupby(group_cols)
            
            for col in value_cols:
                stats = grouped[col].agg([
                    'count', 'sum', 'mean', 'std', 'min', 'max', 'median'
                ]).reset_index()
                
                results[col] = {
                    "grouped_stats": stats.to_dict('records'),
                    "overall_stats": {
                        'total_count': df[col].count(),
                        'total_sum': df[col].sum(),
                        'mean': df[col].mean(),
                        'std': df[col].std(),
                        'min': df[col].min(),
                        'max': df[col].max(),
                        'median': df[col].median()
                    }
                }
        else:
            # 整体统计
            for col in value_cols:
                results[col] = {
                    'count': df[col].count(),
                    'sum': df[col].sum(),
                    'mean': df[col].mean(),
                    'std': df[col].std(),
                    'min': df[col].min(),
                    'max': df[col].max(),
                    'median': df[col].median(),
                    'q1': df[col].quantile(0.25),
                    'q3': df[col].quantile(0.75)
                }
        
        return results
    
    async def _calculate_growth_rate(self, 
                                   context: AnalyticsContext, 
                                   parameters: Dict[str, Any]) -> Dict[str, Any]:
        """计算增长率"""
        df = context.data.copy()
        date_col = context.date_column
        value_cols = context.value_columns
        
        # 确保日期列为datetime类型
        df[date_col] = pd.to_datetime(df[date_col])
        
        # 设置日期为索引
        df.set_index(date_col, inplace=True)
        
        # 根据period_type进行重采样
        period_type = context.period_type
        if period_type == "daily":
            freq = "D"
        elif period_type == "weekly":
            freq = "W"
        elif period_type == "monthly":
            freq = "M"
        elif period_type == "yearly":
            freq = "Y"
        else:
            freq = "D"
        
        results = {}
        
        for col in value_cols:
            # 重采样数据
            resampled = df[col].resample(freq).sum()
            
            # 计算增长率
            growth_rates = resampled.pct_change() * 100
            
            # 计算累计增长率
            cumulative_growth = ((resampled / resampled.iloc[0] - 1) * 100)
            
            results[col] = {
                "period_growth_rates": growth_rates.dropna().tolist(),
                "cumulative_growth": cumulative_growth.dropna().tolist(),
                "resampled_values": resampled.dropna().tolist(),
                "summary": {
                    "avg_growth_rate": growth_rates.mean(),
                    "total_growth": cumulative_growth.iloc[-1] if len(cumulative_growth) > 0 else 0,
                    "positive_periods": (growth_rates > 0).sum(),
                    "negative_periods": (growth_rates < 0).sum()
                }
            }
        
        return results
    
    async def _calculate_proportion(self, 
                                  context: AnalyticsContext, 
                                  parameters: Dict[str, Any]) -> Dict[str, Any]:
        """计算比例分析"""
        df = context.data.copy()
        value_cols = context.value_columns
        group_cols = context.group_columns
        
        results = {}
        
        if group_cols:
            # 按分组计算比例
            for col in value_cols:
                grouped = df.groupby(group_cols)[col].sum()
                total = grouped.sum()
                proportions = (grouped / total * 100)
                
                results[col] = {
                    "group_values": grouped.to_dict(),
                    "proportions": proportions.to_dict(),
                    "total": total,
                    "top_groups": proportions.nlargest(5).to_dict()
                }
        else:
            # 整体比例
            for col in value_cols:
                total = df[col].sum()
                proportions = (df[col] / total * 100)
                
                results[col] = {
                    "individual_values": df[col].tolist(),
                    "proportions": proportions.tolist(),
                    "total": total
                }
        
        return results
    
    async def _calculate_trend(self, 
                             context: AnalyticsContext, 
                             parameters: Dict[str, Any]) -> Dict[str, Any]:
        """计算趋势分析"""
        df = context.data.copy()
        date_col = context.date_column
        value_cols = context.value_columns
        
        # 确保日期列为datetime类型
        df[date_col] = pd.to_datetime(df[date_col])
        
        # 设置日期为索引
        df.set_index(date_col, inplace=True)
        
        results = {}
        
        for col in value_cols:
            # 简单线性趋势
            x = np.arange(len(df[col]))
            y = df[col].values
            
            # 计算线性回归
            coeffs = np.polyfit(x, y, 1)
            slope = coeffs[0]
            intercept = coeffs[1]
            
            # 预测值
            trend_line = slope * x + intercept
            
            # 计算R²
            y_mean = np.mean(y)
            ss_tot = np.sum((y - y_mean) ** 2)
            ss_res = np.sum((y - trend_line) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            results[col] = {
                "slope": slope,
                "intercept": intercept,
                "r_squared": r_squared,
                "trend_direction": "increasing" if slope > 0 else "decreasing",
                "trend_strength": abs(r_squared),
                "trend_line": trend_line.tolist(),
                "actual_values": y.tolist()
            }
        
        return results
    
    async def _calculate_moving_average(self, 
                                      context: AnalyticsContext, 
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """计算移动平均"""
        df = context.data.copy()
        date_col = context.date_column
        value_cols = context.value_columns
        
        # 确保日期列为datetime类型
        df[date_col] = pd.to_datetime(df[date_col])
        
        # 设置日期为索引
        df.set_index(date_col, inplace=True)
        
        # 获取窗口大小参数
        window = parameters.get("window", 7)
        
        results = {}
        
        for col in value_cols:
            # 计算移动平均
            moving_avg = df[col].rolling(window=window).mean()
            
            # 计算移动标准差
            moving_std = df[col].rolling(window=window).std()
            
            results[col] = {
                "moving_average": moving_avg.dropna().tolist(),
                "moving_std": moving_std.dropna().tolist(),
                "window": window,
                "original_values": df[col].tolist(),
                "upper_band": (moving_avg + 2 * moving_std).dropna().tolist(),
                "lower_band": (moving_avg - 2 * moving_std).dropna().tolist()
            }
        
        return results
    
    async def _calculate_percentile(self, 
                                  context: AnalyticsContext, 
                                  parameters: Dict[str, Any]) -> Dict[str, Any]:
        """计算百分位数"""
        df = context.data.copy()
        value_cols = context.value_columns
        
        # 获取百分位参数
        percentiles = parameters.get("percentiles", [25, 50, 75, 90, 95])
        
        results = {}
        
        for col in value_cols:
            # 计算百分位数
            percentile_values = {}
            for p in percentiles:
                percentile_values[f"p{p}"] = df[col].quantile(p / 100)
            
            # 计算四分位距
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            
            results[col] = {
                "percentiles": percentile_values,
                "quartiles": {
                    "q1": q1,
                    "q2": df[col].quantile(0.5),
                    "q3": q3,
                    "iqr": iqr
                },
                "outliers": {
                    "lower_bound": q1 - 1.5 * iqr,
                    "upper_bound": q3 + 1.5 * iqr,
                    "count": ((df[col] < (q1 - 1.5 * iqr)) | (df[col] > (q3 + 1.5 * iqr))).sum()
                }
            }
        
        return results

class MCPAnalyticsAPI:
    """MCP统计分析API接口"""
    
    def __init__(self):
        self.engine = MCPAnalyticsEngine()
    
    async def analyze_data(self, 
                         data: Dict[str, List],
                         operation: str,
                         date_column: str = None,
                         value_columns: List[str] = None,
                         group_columns: List[str] = None,
                         parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析数据API接口"""
        
        # 转换数据为DataFrame
        df = pd.DataFrame(data)
        
        # 创建分析上下文
        context = AnalyticsContext(
            data=df,
            date_column=date_column or "date",
            value_columns=value_columns or ["value"],
            group_columns=group_columns,
            period_type=parameters.get("period_type", "daily") if parameters else "daily"
        )
        
        # 执行分析
        operation_type = AnalyticsOperationType(operation)
        result = await self.engine.execute_analytics(
            operation=operation_type,
            context=context,
            parameters=parameters
        )
        
        return result
    
    async def batch_analyze(self, 
                          data: Dict[str, List],
                          operations: List[str],
                          date_column: str = None,
                          value_columns: List[str] = None,
                          group_columns: List[str] = None,
                          parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """批量分析多个操作"""
        
        results = {}
        
        for operation in operations:
            try:
                result = await self.analyze_data(
                    data=data,
                    operation=operation,
                    date_column=date_column,
                    value_columns=value_columns,
                    group_columns=group_columns,
                    parameters=parameters
                )
                results[operation] = result
            except Exception as e:
                results[operation] = {
                    "operation": operation,
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "batch_results": results,
            "total_operations": len(operations),
            "successful_operations": len([r for r in results.values() if r.get("status") == "success"])
        }
