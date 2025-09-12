"""
数据分析工具
============

用于数据分析、模式分析和统计操作的工具。
"""

import logging
import json
import statistics
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.orm import Session

from ..core.base import (
    AgentTool, StreamingAgentTool, ToolDefinition, ToolResult, 
    ToolExecutionContext, ToolCategory, ToolPriority, ToolPermission,
    ValidationError, ExecutionError, create_tool_definition
)

logger = logging.getLogger(__name__)


# 输入模式
class DataAnalysisInput(BaseModel):
    """数据分析的输入模式"""
    data_source: str = Field(..., description="数据源（文件路径、查询结果或数据集标识符）")
    analysis_type: str = Field(..., description="要执行的分析类型")
    columns: Optional[List[str]] = Field(None, description="要分析的具体列")
    filters: Optional[Dict[str, Any]] = Field(None, description="要应用的数据过滤器")
    statistical_measures: List[str] = Field(default=["mean", "median", "std"], description="要计算的统计指标")
    group_by: Optional[List[str]] = Field(None, description="用于分组的列")
    output_format: str = Field(default="summary", description="输出格式（summary, detailed, json）")
    
    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        allowed_types = [
            "descriptive", "correlation", "distribution", "outlier_detection",
            "time_series", "comparison", "profiling", "quality_check"
        ]
        if v not in allowed_types:
            raise ValueError(f"分析类型必须是以下之一: {allowed_types}")
        return v
    
    @validator('output_format')
    def validate_output_format(cls, v):
        allowed_formats = ["summary", "detailed", "json", "csv", "html"]
        if v not in allowed_formats:
            raise ValueError(f"输出格式必须是以下之一: {allowed_formats}")
        return v


class SchemaAnalysisInput(BaseModel):
    """数据库模式分析的输入模式"""
    database_connection: str = Field(..., description="数据库连接字符串")
    schema_name: Optional[str] = Field(None, description="要分析的具体模式")
    table_names: Optional[List[str]] = Field(None, description="要分析的具体表")
    analysis_depth: str = Field(default="standard", description="分析深度（basic, standard, detailed）")
    include_relationships: bool = Field(default=True, description="包含外键关系")
    include_statistics: bool = Field(default=True, description="包含表统计信息")
    
    @validator('analysis_depth')
    def validate_analysis_depth(cls, v):
        allowed_depths = ["basic", "standard", "detailed"]
        if v not in allowed_depths:
            raise ValueError(f"分析深度必须是以下之一: {allowed_depths}")
        return v


class DataAnalysisTool(StreamingAgentTool):
    """
    具有统计操作和洞察的高级数据分析工具
    """
    
    def __init__(self):
        definition = create_tool_definition(
            name="data_analyzer",
            description="执行具有统计指标和洞察的综合数据分析",
            category=ToolCategory.ANALYSIS,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.READ_ONLY],
            input_schema=DataAnalysisInput,
            is_read_only=True,
            supports_streaming=True,
            typical_execution_time_ms=5000,
            examples=[
                {
                    "data_source": "sales_data.csv",
                    "analysis_type": "descriptive",
                    "columns": ["revenue", "quantity"],
                    "statistical_measures": ["mean", "median", "std", "min", "max"]
                },
                {
                    "data_source": "customer_data",
                    "analysis_type": "outlier_detection",
                    "columns": ["age", "income"],
                    "output_format": "detailed"
                }
            ],
            limitations=[
                "大型数据集可能占用大量内存",
                "复杂的统计操作可能需要时间",
                "需要正确格式化的输入数据"
            ]
        )
        super().__init__(definition)
        
        # 统计分析方法
        self.statistical_methods = {
            'mean': lambda data: np.mean(data),
            'median': lambda data: np.median(data),
            'mode': lambda data: statistics.mode(data) if len(set(data)) < len(data) else None,
            'std': lambda data: np.std(data),
            'var': lambda data: np.var(data),
            'min': lambda data: np.min(data),
            'max': lambda data: np.max(data),
            'q25': lambda data: np.percentile(data, 25),
            'q75': lambda data: np.percentile(data, 75),
            'skewness': lambda data: self._calculate_skewness(data),
            'kurtosis': lambda data: self._calculate_kurtosis(data)
        }
        
        # 分析类型及其方法
        self.analysis_methods = {
            'descriptive': self._descriptive_analysis,
            'correlation': self._correlation_analysis,
            'distribution': self._distribution_analysis,
            'outlier_detection': self._outlier_detection,
            'time_series': self._time_series_analysis,
            'comparison': self._comparison_analysis,
            'profiling': self._data_profiling,
            'quality_check': self._data_quality_check
        }
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """验证数据分析输入"""
        try:
            validated = DataAnalysisInput(**input_data)
            return validated.dict()
        except Exception as e:
            raise ValidationError(f"数据分析器输入无效: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """检查数据分析权限"""
        # 数据分析是只读操作
        return ToolPermission.READ_ONLY in context.permissions
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """执行数据分析并流式传输进度"""
        
        data_source = input_data['data_source']
        analysis_type = input_data['analysis_type']
        columns = input_data.get('columns')
        filters = input_data.get('filters', {})
        statistical_measures = input_data['statistical_measures']
        group_by = input_data.get('group_by')
        output_format = input_data['output_format']
        
        # 阶段1：加载和准备数据
        yield await self.stream_progress({
            'status': 'loading_data',
            'message': '正在加载和准备数据...',
            'progress': 20
        }, context)
        
        data_df = await self._load_data(data_source, context)
        
        # 阶段2：应用过滤器
        if filters:
            yield await self.stream_progress({
                'status': 'filtering',
                'message': '正在应用数据过滤器...',
                'progress': 30
            }, context)
            
            data_df = await self._apply_filters(data_df, filters)
        
        # 阶段3：选择列
        if columns:
            available_columns = data_df.columns.tolist()
            valid_columns = [col for col in columns if col in available_columns]
            if not valid_columns:
                raise ExecutionError(f"在数据中未找到指定的列: {columns}", tool_name=self.name)
            data_df = data_df[valid_columns]
        
        # 阶段4：执行分析
        yield await self.stream_progress({
            'status': 'analyzing',
            'message': f'正在执行 {analysis_type} 分析...',
            'progress': 50
        }, context)
        
        analysis_method = self.analysis_methods.get(analysis_type)
        if not analysis_method:
            raise ExecutionError(f"不支持的分析类型: {analysis_type}", tool_name=self.name)
        
        analysis_results = await analysis_method(
            data_df, statistical_measures, group_by, context
        )
        
        # 阶段5：生成洞察
        yield await self.stream_progress({
            'status': 'generating_insights',
            'message': '正在生成洞察和建议...',
            'progress': 80
        }, context)
        
        insights = await self._generate_insights(analysis_results, analysis_type, data_df)
        
        # 阶段6：格式化输出
        yield await self.stream_progress({
            'status': 'formatting',
            'message': '正在格式化分析结果...',
            'progress': 90
        }, context)
        
        formatted_results = await self._format_analysis_output(
            analysis_results, insights, output_format, analysis_type
        )
        
        # Final result
        result_data = {
            'analysis_type': analysis_type,
            'data_summary': {
                'total_rows': len(data_df),
                'total_columns': len(data_df.columns),
                'columns_analyzed': list(data_df.columns),
                'memory_usage_mb': data_df.memory_usage(deep=True).sum() / 1024 / 1024
            },
            'analysis_results': analysis_results,
            'insights': insights,
            'formatted_output': formatted_results,
            'metadata': {
                'statistical_measures_used': statistical_measures,
                'filters_applied': bool(filters),
                'grouped_analysis': bool(group_by),
                'output_format': output_format
            }
        }
        
        yield await self.stream_final_result(result_data, context)
    
    async def _load_data(self, data_source: str, context: ToolExecutionContext) -> pd.DataFrame:
        """从各种数据源加载数据"""
        
        try:
            # 检测数据源类型
            if data_source.endswith('.csv'):
                return pd.read_csv(data_source)
            elif data_source.endswith('.json'):
                return pd.read_json(data_source)
            elif data_source.endswith('.xlsx') or data_source.endswith('.xls'):
                return pd.read_excel(data_source)
            elif data_source.endswith('.parquet'):
                return pd.read_parquet(data_source)
            elif isinstance(data_source, str) and data_source.startswith(('postgresql://', 'mysql://', 'sqlite://')):
                # 数据库连接
                engine = create_engine(data_source)
                # 假设 data_source 在连接字符串后包含表名
                # 这是简化版本 - 在生产环境中，您需要正确解析连接
                return pd.read_sql("SELECT * FROM your_table LIMIT 10000", engine)
            else:
                # 尝试解释为 JSON 数据
                try:
                    import io
                    data = json.loads(data_source)
                    return pd.DataFrame(data)
                except:
                    raise ExecutionError(f"不支持的数据源格式: {data_source}", tool_name=self.name)
                    
        except Exception as e:
            raise ExecutionError(f"从 {data_source} 加载数据失败: {e}", tool_name=self.name)
    
    async def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """对数据框应用过滤器"""
        
        filtered_df = df.copy()
        
        for column, filter_condition in filters.items():
            if column not in df.columns:
                continue
            
            if isinstance(filter_condition, dict):
                # 复杂过滤条件
                for operator, value in filter_condition.items():
                    if operator == 'gt':
                        filtered_df = filtered_df[filtered_df[column] > value]
                    elif operator == 'lt':
                        filtered_df = filtered_df[filtered_df[column] < value]
                    elif operator == 'gte':
                        filtered_df = filtered_df[filtered_df[column] >= value]
                    elif operator == 'lte':
                        filtered_df = filtered_df[filtered_df[column] <= value]
                    elif operator == 'eq':
                        filtered_df = filtered_df[filtered_df[column] == value]
                    elif operator == 'ne':
                        filtered_df = filtered_df[filtered_df[column] != value]
                    elif operator == 'in':
                        filtered_df = filtered_df[filtered_df[column].isin(value)]
                    elif operator == 'not_in':
                        filtered_df = filtered_df[~filtered_df[column].isin(value)]
            else:
                # 简单等值过滤
                filtered_df = filtered_df[filtered_df[column] == filter_condition]
        
        return filtered_df
    
    async def _descriptive_analysis(self, df: pd.DataFrame, statistical_measures: List[str], 
                                  group_by: Optional[List[str]], context: ToolExecutionContext) -> Dict[str, Any]:
        """执行描述性统计分析"""
        
        results = {}
        
        # 选择数值列进行分析
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if group_by:
            # 分组分析
            for group_col in group_by:
                if group_col in df.columns:
                    grouped = df.groupby(group_col)
                    group_results = {}
                    
                    for name, group in grouped:
                        group_stats = {}
                        for col in numeric_columns:
                            if col in group.columns:
                                col_stats = self._calculate_statistics(group[col], statistical_measures)
                                group_stats[col] = col_stats
                        group_results[str(name)] = group_stats
                    
                    results[f'grouped_by_{group_col}'] = group_results
        else:
            # 整体分析
            overall_stats = {}
            for col in numeric_columns:
                col_stats = self._calculate_statistics(df[col], statistical_measures)
                overall_stats[col] = col_stats
            
            results['overall'] = overall_stats
        
        # 添加分类列摘要
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        if categorical_columns:
            categorical_stats = {}
            for col in categorical_columns:
                categorical_stats[col] = {
                    'unique_count': df[col].nunique(),
                    'most_frequent': df[col].mode().iloc[0] if not df[col].mode().empty else None,
                    'frequency_distribution': df[col].value_counts().head(10).to_dict()
                }
            results['categorical_summary'] = categorical_stats
        
        return results
    
    async def _correlation_analysis(self, df: pd.DataFrame, statistical_measures: List[str], 
                                  group_by: Optional[List[str]], context: ToolExecutionContext) -> Dict[str, Any]:
        """执行相关性分析"""
        
        numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            return {'error': '未找到用于相关性分析的数值列'}
        
        # 计算相关性矩阵
        correlation_matrix = numeric_df.corr()
        
        # 查找强相关性
        strong_correlations = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:  # 强相关性阈值
                    strong_correlations.append({
                        'column1': correlation_matrix.columns[i],
                        'column2': correlation_matrix.columns[j],
                        'correlation': corr_value,
                        'strength': 'strong' if abs(corr_value) > 0.8 else 'moderate'
                    })
        
        return {
            'correlation_matrix': correlation_matrix.to_dict(),
            'strong_correlations': strong_correlations,
            'summary': {
                'columns_analyzed': list(numeric_df.columns),
                'total_pairs': len(strong_correlations),
                'highest_correlation': max([abs(c['correlation']) for c in strong_correlations]) if strong_correlations else 0
            }
        }
    
    async def _distribution_analysis(self, df: pd.DataFrame, statistical_measures: List[str], 
                                   group_by: Optional[List[str]], context: ToolExecutionContext) -> Dict[str, Any]:
        """Analyze data distributions"""
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        results = {}
        
        for col in numeric_columns:
            data = df[col].dropna()
            
            # Basic distribution stats
            dist_stats = {
                'mean': float(np.mean(data)),
                'median': float(np.median(data)),
                'std': float(np.std(data)),
                'skewness': float(self._calculate_skewness(data)),
                'kurtosis': float(self._calculate_kurtosis(data)),
                'min': float(np.min(data)),
                'max': float(np.max(data)),
                'range': float(np.max(data) - np.min(data))
            }
            
            # Distribution shape analysis
            dist_shape = self._analyze_distribution_shape(data)
            
            # Histogram data (for visualization)
            hist, bin_edges = np.histogram(data, bins=20)
            
            results[col] = {
                'statistics': dist_stats,
                'shape_analysis': dist_shape,
                'histogram': {
                    'counts': hist.tolist(),
                    'bin_edges': bin_edges.tolist()
                }
            }
        
        return results
    
    async def _outlier_detection(self, df: pd.DataFrame, statistical_measures: List[str], 
                               group_by: Optional[List[str]], context: ToolExecutionContext) -> Dict[str, Any]:
        """Detect outliers in the data"""
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        results = {}
        
        for col in numeric_columns:
            data = df[col].dropna()
            
            # IQR method
            Q1 = np.percentile(data, 25)
            Q3 = np.percentile(data, 75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            iqr_outliers = data[(data < lower_bound) | (data > upper_bound)]
            
            # Z-score method
            z_scores = np.abs((data - np.mean(data)) / np.std(data))
            z_outliers = data[z_scores > 3]
            
            # Modified Z-score method
            median_data = np.median(data)
            mad = np.median(np.abs(data - median_data))
            modified_z_scores = 0.6745 * (data - median_data) / mad
            modified_z_outliers = data[np.abs(modified_z_scores) > 3.5]
            
            results[col] = {
                'iqr_method': {
                    'outlier_count': len(iqr_outliers),
                    'outlier_percentage': (len(iqr_outliers) / len(data)) * 100,
                    'bounds': {'lower': lower_bound, 'upper': upper_bound},
                    'outliers': iqr_outliers.tolist()[:10]  # Limit to first 10
                },
                'z_score_method': {
                    'outlier_count': len(z_outliers),
                    'outlier_percentage': (len(z_outliers) / len(data)) * 100,
                    'outliers': z_outliers.tolist()[:10]
                },
                'modified_z_score_method': {
                    'outlier_count': len(modified_z_outliers),
                    'outlier_percentage': (len(modified_z_outliers) / len(data)) * 100,
                    'outliers': modified_z_outliers.tolist()[:10]
                }
            }
        
        return results
    
    async def _time_series_analysis(self, df: pd.DataFrame, statistical_measures: List[str], 
                                  group_by: Optional[List[str]], context: ToolExecutionContext) -> Dict[str, Any]:
        """Perform time series analysis"""
        
        # Try to identify datetime columns
        datetime_columns = []
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                datetime_columns.append(col)
            elif df[col].dtype == 'object':
                # Try to parse as datetime
                try:
                    pd.to_datetime(df[col].head(10))
                    datetime_columns.append(col)
                except:
                    pass
        
        if not datetime_columns:
            return {'error': 'No datetime columns found for time series analysis'}
        
        results = {}
        
        for date_col in datetime_columns:
            # Convert to datetime if needed
            if df[date_col].dtype != 'datetime64[ns]':
                df[date_col] = pd.to_datetime(df[date_col])
            
            # Sort by date
            df_sorted = df.sort_values(date_col)
            
            # Basic time series statistics
            time_stats = {
                'date_range': {
                    'start': df_sorted[date_col].min().isoformat(),
                    'end': df_sorted[date_col].max().isoformat(),
                    'duration_days': (df_sorted[date_col].max() - df_sorted[date_col].min()).days
                },
                'frequency_analysis': self._analyze_time_frequency(df_sorted[date_col]),
                'gaps': self._find_time_gaps(df_sorted[date_col])
            }
            
            results[date_col] = time_stats
        
        return results
    
    async def _comparison_analysis(self, df: pd.DataFrame, statistical_measures: List[str], 
                                 group_by: Optional[List[str]], context: ToolExecutionContext) -> Dict[str, Any]:
        """Perform comparison analysis between groups"""
        
        if not group_by:
            return {'error': 'group_by parameter required for comparison analysis'}
        
        results = {}
        
        for group_col in group_by:
            if group_col not in df.columns:
                continue
            
            # Get unique groups
            groups = df[group_col].unique()
            
            if len(groups) < 2:
                continue
            
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            comparison_results = {}
            
            for num_col in numeric_columns:
                group_stats = {}
                
                for group in groups:
                    group_data = df[df[group_col] == group][num_col].dropna()
                    if len(group_data) > 0:
                        group_stats[str(group)] = self._calculate_statistics(group_data, statistical_measures)
                
                # Calculate differences between groups
                if len(group_stats) >= 2:
                    group_names = list(group_stats.keys())
                    comparisons = []
                    
                    for i in range(len(group_names)):
                        for j in range(i+1, len(group_names)):
                            group1, group2 = group_names[i], group_names[j]
                            
                            mean_diff = group_stats[group1]['mean'] - group_stats[group2]['mean']
                            
                            comparisons.append({
                                'group1': group1,
                                'group2': group2,
                                'mean_difference': mean_diff,
                                'percentage_difference': (mean_diff / group_stats[group2]['mean']) * 100 if group_stats[group2]['mean'] != 0 else None
                            })
                    
                    comparison_results[num_col] = {
                        'group_statistics': group_stats,
                        'comparisons': comparisons
                    }
            
            results[group_col] = comparison_results
        
        return results
    
    async def _data_profiling(self, df: pd.DataFrame, statistical_measures: List[str], 
                            group_by: Optional[List[str]], context: ToolExecutionContext) -> Dict[str, Any]:
        """Perform comprehensive data profiling"""
        
        profile = {
            'dataset_overview': {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
                'duplicate_rows': df.duplicated().sum()
            },
            'column_profiles': {}
        }
        
        for col in df.columns:
            col_profile = {
                'data_type': str(df[col].dtype),
                'non_null_count': df[col].count(),
                'null_count': df[col].isnull().sum(),
                'null_percentage': (df[col].isnull().sum() / len(df)) * 100,
                'unique_count': df[col].nunique(),
                'unique_percentage': (df[col].nunique() / len(df)) * 100
            }
            
            if df[col].dtype in ['int64', 'float64']:
                # Numeric column profiling
                col_data = df[col].dropna()
                if len(col_data) > 0:
                    col_profile.update({
                        'statistics': self._calculate_statistics(col_data, statistical_measures),
                        'zeros_count': (col_data == 0).sum(),
                        'negative_count': (col_data < 0).sum(),
                        'positive_count': (col_data > 0).sum()
                    })
            else:
                # Categorical/text column profiling
                col_profile.update({
                    'most_frequent': df[col].mode().iloc[0] if not df[col].mode().empty else None,
                    'least_frequent': df[col].value_counts().idxmin() if df[col].count() > 0 else None,
                    'average_length': df[col].astype(str).str.len().mean() if df[col].count() > 0 else 0
                })
            
            profile['column_profiles'][col] = col_profile
        
        return profile
    
    async def _data_quality_check(self, df: pd.DataFrame, statistical_measures: List[str], 
                                group_by: Optional[List[str]], context: ToolExecutionContext) -> Dict[str, Any]:
        """Perform data quality checks"""
        
        quality_issues = []
        quality_score = 100
        
        # Check for missing data
        missing_data = df.isnull().sum()
        for col, missing_count in missing_data.items():
            if missing_count > 0:
                missing_pct = (missing_count / len(df)) * 100
                if missing_pct > 50:
                    quality_issues.append({
                        'type': 'high_missing_data',
                        'column': col,
                        'severity': 'high',
                        'description': f'{missing_pct:.1f}% missing data in column {col}'
                    })
                    quality_score -= 20
                elif missing_pct > 10:
                    quality_issues.append({
                        'type': 'moderate_missing_data', 
                        'column': col,
                        'severity': 'medium',
                        'description': f'{missing_pct:.1f}% missing data in column {col}'
                    })
                    quality_score -= 5
        
        # Check for duplicates
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            duplicate_pct = (duplicate_count / len(df)) * 100
            quality_issues.append({
                'type': 'duplicate_rows',
                'severity': 'medium' if duplicate_pct > 10 else 'low',
                'description': f'{duplicate_count} duplicate rows ({duplicate_pct:.1f}%)'
            })
            quality_score -= min(duplicate_pct, 15)
        
        # Check for outliers in numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            data = df[col].dropna()
            if len(data) > 0:
                Q1 = np.percentile(data, 25)
                Q3 = np.percentile(data, 75)
                IQR = Q3 - Q1
                outliers = data[(data < Q1 - 1.5 * IQR) | (data > Q3 + 1.5 * IQR)]
                
                if len(outliers) > 0:
                    outlier_pct = (len(outliers) / len(data)) * 100
                    if outlier_pct > 10:
                        quality_issues.append({
                            'type': 'high_outliers',
                            'column': col,
                            'severity': 'medium',
                            'description': f'{outlier_pct:.1f}% outliers in column {col}'
                        })
                        quality_score -= 5
        
        # Check for inconsistent data types
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if numeric data is stored as string
                try:
                    numeric_values = pd.to_numeric(df[col], errors='coerce')
                    if not numeric_values.isnull().all() and numeric_values.count() > len(df) * 0.8:
                        quality_issues.append({
                            'type': 'inconsistent_data_type',
                            'column': col,
                            'severity': 'low',
                            'description': f'Column {col} contains numeric data stored as text'
                        })
                        quality_score -= 3
                except:
                    pass
        
        return {
            'quality_score': max(0, quality_score),
            'quality_issues': quality_issues,
            'recommendations': self._generate_quality_recommendations(quality_issues),
            'summary': {
                'total_issues': len(quality_issues),
                'high_severity_issues': len([i for i in quality_issues if i['severity'] == 'high']),
                'medium_severity_issues': len([i for i in quality_issues if i['severity'] == 'medium']),
                'low_severity_issues': len([i for i in quality_issues if i['severity'] == 'low'])
            }
        }
    
    def _calculate_statistics(self, data: pd.Series, measures: List[str]) -> Dict[str, float]:
        """Calculate statistical measures for a data series"""
        stats = {}
        
        for measure in measures:
            if measure in self.statistical_methods:
                try:
                    value = self.statistical_methods[measure](data)
                    stats[measure] = float(value) if value is not None else None
                except Exception as e:
                    logger.warning(f"Failed to calculate {measure}: {e}")
                    stats[measure] = None
        
        return stats
    
    def _calculate_skewness(self, data):
        """Calculate skewness"""
        try:
            from scipy import stats
            return stats.skew(data)
        except ImportError:
            # Manual calculation
            mean = np.mean(data)
            std = np.std(data)
            n = len(data)
            skewness = (n / ((n-1) * (n-2))) * np.sum(((data - mean) / std) ** 3)
            return skewness
    
    def _calculate_kurtosis(self, data):
        """Calculate kurtosis"""
        try:
            from scipy import stats
            return stats.kurtosis(data)
        except ImportError:
            # Manual calculation
            mean = np.mean(data)
            std = np.std(data)
            n = len(data)
            kurtosis = (n * (n+1) / ((n-1) * (n-2) * (n-3))) * np.sum(((data - mean) / std) ** 4) - 3 * (n-1)**2 / ((n-2) * (n-3))
            return kurtosis
    
    def _analyze_distribution_shape(self, data) -> Dict[str, Any]:
        """Analyze the shape of the distribution"""
        skewness = self._calculate_skewness(data)
        kurtosis = self._calculate_kurtosis(data)
        
        shape_analysis = {
            'skewness': float(skewness),
            'kurtosis': float(kurtosis),
            'distribution_type': 'normal'  # Default
        }
        
        # Determine distribution characteristics
        if abs(skewness) < 0.5:
            shape_analysis['skew_description'] = 'approximately symmetric'
        elif skewness > 0.5:
            shape_analysis['skew_description'] = 'right-skewed (positive skew)'
        else:
            shape_analysis['skew_description'] = 'left-skewed (negative skew)'
        
        if abs(kurtosis) < 0.5:
            shape_analysis['kurtosis_description'] = 'mesokurtic (normal-like tails)'
        elif kurtosis > 0.5:
            shape_analysis['kurtosis_description'] = 'leptokurtic (heavy tails)'
        else:
            shape_analysis['kurtosis_description'] = 'platykurtic (light tails)'
        
        return shape_analysis
    
    def _analyze_time_frequency(self, date_series: pd.Series) -> Dict[str, Any]:
        """Analyze time frequency patterns"""
        # Calculate differences between consecutive dates
        date_diffs = date_series.diff().dropna()
        
        if len(date_diffs) == 0:
            return {'frequency': 'unknown', 'regularity': 'unknown'}
        
        # Most common time difference
        most_common_diff = date_diffs.mode().iloc[0] if not date_diffs.mode().empty else date_diffs.iloc[0]
        
        # Determine frequency
        days = most_common_diff.days
        if days == 1:
            frequency = 'daily'
        elif days == 7:
            frequency = 'weekly'  
        elif 28 <= days <= 31:
            frequency = 'monthly'
        elif 365 <= days <= 366:
            frequency = 'yearly'
        else:
            frequency = f'{days}_days'
        
        # Check regularity
        std_dev = date_diffs.dt.days.std()
        if std_dev < 1:
            regularity = 'very_regular'
        elif std_dev < 7:
            regularity = 'regular'
        else:
            regularity = 'irregular'
        
        return {
            'frequency': frequency,
            'regularity': regularity,
            'most_common_interval_days': days,
            'interval_std_dev': std_dev
        }
    
    def _find_time_gaps(self, date_series: pd.Series) -> List[Dict[str, Any]]:
        """Find gaps in time series data"""
        date_diffs = date_series.diff().dropna()
        
        if len(date_diffs) == 0:
            return []
        
        # Expected interval (most common difference)
        expected_interval = date_diffs.mode().iloc[0] if not date_diffs.mode().empty else date_diffs.iloc[0]
        
        # Find gaps that are significantly larger than expected
        threshold = expected_interval * 2  # Gap is 2x the expected interval
        
        gaps = []
        for i, diff in enumerate(date_diffs):
            if diff > threshold:
                gaps.append({
                    'start_date': date_series.iloc[i].isoformat(),
                    'end_date': date_series.iloc[i+1].isoformat(),
                    'gap_duration_days': diff.days,
                    'expected_duration_days': expected_interval.days
                })
        
        return gaps
    
    def _generate_quality_recommendations(self, quality_issues: List[Dict]) -> List[str]:
        """Generate recommendations based on quality issues"""
        recommendations = []
        
        for issue in quality_issues:
            if issue['type'] == 'high_missing_data':
                recommendations.append(f"Consider imputation strategies for column {issue['column']} or remove if not essential")
            elif issue['type'] == 'duplicate_rows':
                recommendations.append("Remove duplicate rows to improve data quality")
            elif issue['type'] == 'high_outliers':
                recommendations.append(f"Investigate outliers in column {issue['column']} - may indicate data entry errors")
            elif issue['type'] == 'inconsistent_data_type':
                recommendations.append(f"Convert column {issue['column']} to appropriate numeric type")
        
        if not recommendations:
            recommendations.append("Data quality is good - no major issues detected")
        
        return recommendations
    
    async def _generate_insights(self, analysis_results: Dict[str, Any], 
                               analysis_type: str, df: pd.DataFrame) -> List[str]:
        """Generate insights based on analysis results"""
        insights = []
        
        if analysis_type == 'descriptive':
            # Insights from descriptive analysis
            if 'overall' in analysis_results:
                for col, stats in analysis_results['overall'].items():
                    if stats.get('std', 0) > stats.get('mean', 0):
                        insights.append(f"Column '{col}' shows high variability (std > mean)")
                    
                    if stats.get('min', 0) < 0 and stats.get('max', 0) > 0:
                        insights.append(f"Column '{col}' contains both positive and negative values")
        
        elif analysis_type == 'correlation':
            strong_correlations = analysis_results.get('strong_correlations', [])
            if strong_correlations:
                insights.append(f"Found {len(strong_correlations)} strong correlations in the data")
                for corr in strong_correlations[:3]:  # Top 3
                    insights.append(f"Strong correlation between {corr['column1']} and {corr['column2']} ({corr['correlation']:.2f})")
        
        elif analysis_type == 'outlier_detection':
            for col, outlier_data in analysis_results.items():
                iqr_outliers = outlier_data['iqr_method']['outlier_count']
                if iqr_outliers > 0:
                    insights.append(f"Column '{col}' has {iqr_outliers} outliers ({outlier_data['iqr_method']['outlier_percentage']:.1f}%)")
        
        elif analysis_type == 'quality_check':
            quality_score = analysis_results.get('quality_score', 100)
            if quality_score < 70:
                insights.append(f"Data quality score is {quality_score}/100 - significant improvements needed")
            elif quality_score < 90:
                insights.append(f"Data quality score is {quality_score}/100 - some improvements recommended")
            else:
                insights.append(f"Excellent data quality score: {quality_score}/100")
        
        return insights
    
    async def _format_analysis_output(self, analysis_results: Dict[str, Any], 
                                    insights: List[str], output_format: str, 
                                    analysis_type: str) -> Union[str, Dict[str, Any]]:
        """Format analysis output according to specified format"""
        
        if output_format == 'json':
            return {
                'analysis_type': analysis_type,
                'results': analysis_results,
                'insights': insights
            }
        
        elif output_format == 'summary':
            summary_lines = [f"# {analysis_type.replace('_', ' ').title()} Analysis Summary"]
            summary_lines.append("")
            
            # Add key insights
            if insights:
                summary_lines.append("## Key Insights:")
                for insight in insights:
                    summary_lines.append(f"- {insight}")
                summary_lines.append("")
            
            # Add main results
            summary_lines.append("## Results:")
            if isinstance(analysis_results, dict):
                for key, value in analysis_results.items():
                    summary_lines.append(f"### {key.replace('_', ' ').title()}")
                    if isinstance(value, dict) and len(value) <= 5:
                        for subkey, subvalue in value.items():
                            summary_lines.append(f"- {subkey}: {subvalue}")
                    else:
                        summary_lines.append(f"- {len(value) if hasattr(value, '__len__') else 'N/A'} items")
                    summary_lines.append("")
            
            return "\n".join(summary_lines)
        
        elif output_format == 'detailed':
            return {
                'analysis_type': analysis_type,
                'detailed_results': analysis_results,
                'insights': insights,
                'formatted_summary': await self._format_analysis_output(
                    analysis_results, insights, 'summary', analysis_type
                )
            }
        
        else:
            # Default to dictionary format
            return analysis_results


class SchemaAnalysisTool(StreamingAgentTool):
    """
    Database schema analysis tool
    """
    
    def __init__(self):
        definition = create_tool_definition(
            name="schema_analyzer", 
            description="Analyze database schema structure, relationships, and statistics",
            category=ToolCategory.DATA,
            priority=ToolPriority.NORMAL,
            permissions=[ToolPermission.READ_ONLY],
            input_schema=SchemaAnalysisInput,
            is_read_only=True,
            supports_streaming=True,
            typical_execution_time_ms=3000,
            examples=[
                {
                    "database_connection": "postgresql://localhost/mydb",
                    "analysis_depth": "detailed",
                    "include_relationships": True,
                    "include_statistics": True
                }
            ]
        )
        super().__init__(definition)
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """Validate schema analysis input"""
        try:
            validated = SchemaAnalysisInput(**input_data)
            return validated.dict()
        except Exception as e:
            raise ValidationError(f"Invalid input for schema analyzer: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """Check permissions for schema analysis"""
        return ToolPermission.READ_ONLY in context.permissions
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Execute schema analysis"""
        
        connection_string = input_data['database_connection']
        schema_name = input_data.get('schema_name')
        table_names = input_data.get('table_names')
        analysis_depth = input_data['analysis_depth']
        include_relationships = input_data['include_relationships']
        include_statistics = input_data['include_statistics']
        
        # Phase 1: Connect to database
        yield await self.stream_progress({
            'status': 'connecting',
            'message': 'Connecting to database...',
            'progress': 10
        }, context)
        
        try:
            engine = create_engine(connection_string)
            inspector = inspect(engine)
            
            # Phase 2: Get schema information
            yield await self.stream_progress({
                'status': 'discovering',
                'message': 'Discovering schema structure...',
                'progress': 30
            }, context)
            
            schema_info = await self._analyze_schema_structure(
                inspector, schema_name, table_names
            )
            
            # Phase 3: Analyze relationships
            if include_relationships:
                yield await self.stream_progress({
                    'status': 'analyzing_relationships',
                    'message': 'Analyzing table relationships...',
                    'progress': 50
                }, context)
                
                relationships = await self._analyze_relationships(inspector, schema_info['tables'])
                schema_info['relationships'] = relationships
            
            # Phase 4: Gather statistics
            if include_statistics:
                yield await self.stream_progress({
                    'status': 'gathering_statistics',
                    'message': 'Gathering table statistics...',
                    'progress': 70
                }, context)
                
                statistics = await self._gather_table_statistics(
                    engine, schema_info['tables']
                )
                schema_info['statistics'] = statistics
            
            # Phase 5: Generate recommendations
            yield await self.stream_progress({
                'status': 'generating_recommendations',
                'message': 'Generating optimization recommendations...',
                'progress': 90
            }, context)
            
            recommendations = await self._generate_schema_recommendations(schema_info)
            
            # Final result
            result_data = {
                'schema_analysis': schema_info,
                'recommendations': recommendations,
                'analysis_metadata': {
                    'analysis_depth': analysis_depth,
                    'relationships_analyzed': include_relationships,
                    'statistics_included': include_statistics,
                    'total_tables': len(schema_info.get('tables', {})),
                    'total_columns': sum(len(table.get('columns', [])) for table in schema_info.get('tables', {}).values())
                }
            }
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"Schema analysis failed: {e}", tool_name=self.name)
    
    async def _analyze_schema_structure(self, inspector, schema_name: Optional[str], 
                                      table_names: Optional[List[str]]) -> Dict[str, Any]:
        """Analyze database schema structure"""
        
        schema_info = {
            'database_type': inspector.dialect.name,
            'schemas': [],
            'tables': {}
        }
        
        # Get available schemas
        try:
            schemas = inspector.get_schema_names()
            schema_info['schemas'] = schemas
        except:
            schema_info['schemas'] = ['public']  # Default for databases without schema support
        
        # Determine which schema to analyze
        target_schema = schema_name or (schemas[0] if schemas else None)
        
        # Get tables
        if table_names:
            tables_to_analyze = table_names
        else:
            tables_to_analyze = inspector.get_table_names(schema=target_schema)
        
        # Analyze each table
        for table_name in tables_to_analyze:
            table_info = {
                'columns': [],
                'indexes': [],
                'constraints': [],
                'foreign_keys': []
            }
            
            # Get column information
            try:
                columns = inspector.get_columns(table_name, schema=target_schema)
                for col in columns:
                    table_info['columns'].append({
                        'name': col['name'],
                        'type': str(col['type']),
                        'nullable': col['nullable'],
                        'default': col.get('default'),
                        'primary_key': col.get('primary_key', False)
                    })
            except Exception as e:
                logger.warning(f"Failed to get columns for table {table_name}: {e}")
            
            # Get indexes
            try:
                indexes = inspector.get_indexes(table_name, schema=target_schema)
                table_info['indexes'] = indexes
            except Exception as e:
                logger.warning(f"Failed to get indexes for table {table_name}: {e}")
            
            # Get foreign keys
            try:
                foreign_keys = inspector.get_foreign_keys(table_name, schema=target_schema)
                table_info['foreign_keys'] = foreign_keys
            except Exception as e:
                logger.warning(f"Failed to get foreign keys for table {table_name}: {e}")
            
            schema_info['tables'][table_name] = table_info
        
        return schema_info
    
    async def _analyze_relationships(self, inspector, tables: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze relationships between tables"""
        
        relationships = {
            'foreign_key_relationships': [],
            'relationship_graph': {},
            'orphaned_tables': [],
            'hub_tables': []
        }
        
        # Build relationship graph
        for table_name, table_info in tables.items():
            relationships['relationship_graph'][table_name] = {
                'references': [],  # Tables this table references
                'referenced_by': []  # Tables that reference this table
            }
        
        # Analyze foreign key relationships
        for table_name, table_info in tables.items():
            for fk in table_info.get('foreign_keys', []):
                ref_table = fk.get('referred_table')
                if ref_table and ref_table in tables:
                    # Record the relationship
                    relationships['foreign_key_relationships'].append({
                        'from_table': table_name,
                        'to_table': ref_table,
                        'foreign_key_columns': fk.get('constrained_columns', []),
                        'referenced_columns': fk.get('referred_columns', [])
                    })
                    
                    # Update relationship graph
                    relationships['relationship_graph'][table_name]['references'].append(ref_table)
                    relationships['relationship_graph'][ref_table]['referenced_by'].append(table_name)
        
        # Identify orphaned tables (no relationships)
        for table_name, rels in relationships['relationship_graph'].items():
            if not rels['references'] and not rels['referenced_by']:
                relationships['orphaned_tables'].append(table_name)
        
        # Identify hub tables (heavily referenced)
        reference_counts = {}
        for table_name, rels in relationships['relationship_graph'].items():
            reference_counts[table_name] = len(rels['referenced_by'])
        
        # Tables with many references are likely hub tables
        avg_references = sum(reference_counts.values()) / len(reference_counts) if reference_counts else 0
        for table_name, ref_count in reference_counts.items():
            if ref_count > avg_references * 2:  # Significantly above average
                relationships['hub_tables'].append({
                    'table': table_name,
                    'reference_count': ref_count
                })
        
        return relationships
    
    async def _gather_table_statistics(self, engine, tables: Dict[str, Any]) -> Dict[str, Any]:
        """Gather table statistics"""
        
        statistics = {}
        
        with engine.connect() as conn:
            for table_name in tables.keys():
                try:
                    # Get row count
                    result = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = result.scalar()
                    
                    # Get table size (database-specific)
                    table_size = await self._get_table_size(conn, table_name)
                    
                    statistics[table_name] = {
                        'row_count': row_count,
                        'estimated_size_bytes': table_size,
                        'columns_count': len(tables[table_name].get('columns', [])),
                        'indexes_count': len(tables[table_name].get('indexes', [])),
                        'foreign_keys_count': len(tables[table_name].get('foreign_keys', []))
                    }
                    
                except Exception as e:
                    logger.warning(f"Failed to get statistics for table {table_name}: {e}")
                    statistics[table_name] = {
                        'row_count': 'unknown',
                        'estimated_size_bytes': 'unknown',
                        'error': str(e)
                    }
        
        return statistics
    
    async def _get_table_size(self, conn, table_name: str) -> Union[int, str]:
        """Get table size (database-specific implementation)"""
        
        try:
            # PostgreSQL
            result = conn.execute(f"""
                SELECT pg_total_relation_size('{table_name}')
            """)
            return result.scalar()
        except:
            try:
                # MySQL
                result = conn.execute(f"""
                    SELECT (data_length + index_length) 
                    FROM information_schema.TABLES 
                    WHERE table_name = '{table_name}'
                """)
                return result.scalar()
            except:
                return 'unknown'
    
    async def _generate_schema_recommendations(self, schema_info: Dict[str, Any]) -> List[str]:
        """Generate schema optimization recommendations"""
        
        recommendations = []
        
        tables = schema_info.get('tables', {})
        relationships = schema_info.get('relationships', {})
        statistics = schema_info.get('statistics', {})
        
        # Check for tables without primary keys
        for table_name, table_info in tables.items():
            has_primary_key = any(col.get('primary_key', False) for col in table_info.get('columns', []))
            if not has_primary_key:
                recommendations.append(f"Table '{table_name}' lacks a primary key - consider adding one for better performance")
        
        # Check for tables without indexes
        for table_name, table_info in tables.items():
            if not table_info.get('indexes') and statistics.get(table_name, {}).get('row_count', 0) > 1000:
                recommendations.append(f"Table '{table_name}' has no indexes but contains many rows - consider adding indexes")
        
        # Check for orphaned tables
        if relationships and relationships.get('orphaned_tables'):
            recommendations.append(f"Orphaned tables detected: {', '.join(relationships['orphaned_tables'])} - verify if these are needed")
        
        # Check for very large tables
        for table_name, stats in statistics.items():
            row_count = stats.get('row_count', 0)
            if isinstance(row_count, int) and row_count > 1000000:
                recommendations.append(f"Table '{table_name}' is very large ({row_count:,} rows) - consider partitioning")
        
        # Check for tables with many columns
        for table_name, table_info in tables.items():
            column_count = len(table_info.get('columns', []))
            if column_count > 50:
                recommendations.append(f"Table '{table_name}' has many columns ({column_count}) - consider normalization")
        
        if not recommendations:
            recommendations.append("Schema structure looks good - no major issues detected")
        
        return recommendations


__all__ = ["DataAnalysisTool", "SchemaAnalysisTool"]