"""
Data Analysis Domain Service

数据分析领域服务，包含纯业务逻辑
"""

import logging
import statistics
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import math

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """分析类型"""
    DESCRIPTIVE = "descriptive"
    DIAGNOSTIC = "diagnostic"
    PREDICTIVE = "predictive"
    PRESCRIPTIVE = "prescriptive"


class DataQuality(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class DataProfile:
    """数据概况"""
    total_records: int = 0
    total_columns: int = 0
    numeric_columns: int = 0
    text_columns: int = 0
    date_columns: int = 0
    null_values: int = 0
    duplicate_records: int = 0
    data_types: Dict[str, str] = field(default_factory=dict)
    value_ranges: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @property
    def completeness_ratio(self) -> float:
        """数据完整性比率"""
        if self.total_records == 0:
            return 0.0
        total_cells = self.total_records * self.total_columns
        return 1.0 - (self.null_values / total_cells) if total_cells > 0 else 0.0
    
    @property
    def uniqueness_ratio(self) -> float:
        """数据唯一性比率"""
        if self.total_records == 0:
            return 1.0
        return 1.0 - (self.duplicate_records / self.total_records)


@dataclass
class StatisticalSummary:
    """统计摘要"""
    column_name: str
    data_type: str
    count: int = 0
    null_count: int = 0
    unique_count: int = 0
    
    # 数值型统计
    mean: Optional[float] = None
    median: Optional[float] = None
    mode: Optional[Union[str, float]] = None
    std_dev: Optional[float] = None
    min_value: Optional[Union[str, float, datetime]] = None
    max_value: Optional[Union[str, float, datetime]] = None
    quartiles: Optional[List[float]] = None
    
    # 文本型统计
    avg_length: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    
    # 分布信息
    value_distribution: Dict[str, int] = field(default_factory=dict)
    
    @property
    def completeness(self) -> float:
        """完整性"""
        return 1.0 - (self.null_count / self.count) if self.count > 0 else 0.0
    
    @property
    def uniqueness(self) -> float:
        """唯一性"""
        return self.unique_count / self.count if self.count > 0 else 0.0


@dataclass
class AnomalyDetectionResult:
    """异常检测结果"""
    column_name: str
    anomaly_type: str
    anomaly_count: int
    anomaly_ratio: float
    anomalous_values: List[Any] = field(default_factory=list)
    threshold_used: Optional[float] = None
    detection_method: str = "statistical"
    confidence_level: float = 0.95


class DataAnalysisDomainService:
    """数据分析领域服务"""
    
    def __init__(self):
        self.quality_thresholds = {
            'completeness': {'excellent': 0.98, 'good': 0.95, 'fair': 0.85, 'poor': 0.70},
            'uniqueness': {'excellent': 0.98, 'good': 0.90, 'fair': 0.80, 'poor': 0.60},
            'consistency': {'excellent': 0.98, 'good': 0.95, 'fair': 0.85, 'poor': 0.70}
        }
    
    def profile_dataset(self, data: List[Dict[str, Any]]) -> DataProfile:
        """数据集概况分析"""
        if not data:
            return DataProfile()
        
        profile = DataProfile()
        profile.total_records = len(data)
        
        if profile.total_records == 0:
            return profile
        
        # 获取所有列名
        all_columns = set()
        for record in data:
            all_columns.update(record.keys())
        
        profile.total_columns = len(all_columns)
        
        # 分析每列的数据类型和统计信息
        for column in all_columns:
            values = [record.get(column) for record in data]
            non_null_values = [v for v in values if v is not None]
            
            # 统计空值
            profile.null_values += values.count(None)
            
            if non_null_values:
                # 推断数据类型
                data_type = self._infer_data_type(non_null_values)
                profile.data_types[column] = data_type
                
                # 分类统计
                if data_type in ['integer', 'float']:
                    profile.numeric_columns += 1
                elif data_type == 'string':
                    profile.text_columns += 1
                elif data_type in ['date', 'datetime']:
                    profile.date_columns += 1
                
                # 计算值范围
                profile.value_ranges[column] = self._calculate_value_range(non_null_values, data_type)
        
        # 检测重复记录
        seen_records = set()
        for record in data:
            record_hash = hash(frozenset(record.items()))
            if record_hash in seen_records:
                profile.duplicate_records += 1
            else:
                seen_records.add(record_hash)
        
        return profile
    
    def calculate_column_statistics(self, data: List[Dict[str, Any]], 
                                  column_name: str) -> StatisticalSummary:
        """计算列统计信息"""
        values = [record.get(column_name) for record in data]
        non_null_values = [v for v in values if v is not None]
        
        summary = StatisticalSummary(
            column_name=column_name,
            data_type=self._infer_data_type(non_null_values) if non_null_values else 'unknown',
            count=len(values),
            null_count=values.count(None),
            unique_count=len(set(non_null_values))
        )
        
        if not non_null_values:
            return summary
        
        # 数值型统计
        if summary.data_type in ['integer', 'float']:
            numeric_values = []
            for v in non_null_values:
                try:
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    continue
            
            if numeric_values:
                summary.mean = statistics.mean(numeric_values)
                summary.median = statistics.median(numeric_values)
                summary.std_dev = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0
                summary.min_value = min(numeric_values)
                summary.max_value = max(numeric_values)
                
                # 四分位数
                sorted_values = sorted(numeric_values)
                n = len(sorted_values)
                summary.quartiles = [
                    sorted_values[n//4] if n > 0 else 0,
                    summary.median,
                    sorted_values[3*n//4] if n > 0 else 0
                ]
        
        # 文本型统计
        elif summary.data_type == 'string':
            text_values = [str(v) for v in non_null_values]
            lengths = [len(t) for t in text_values]
            
            summary.avg_length = statistics.mean(lengths) if lengths else 0
            summary.min_length = min(lengths) if lengths else 0
            summary.max_length = max(lengths) if lengths else 0
            summary.min_value = min(text_values) if text_values else ""
            summary.max_value = max(text_values) if text_values else ""
        
        # 计算众数
        try:
            summary.mode = statistics.mode(non_null_values)
        except statistics.StatisticsError:
            # 没有唯一众数
            pass
        
        # 值分布（取前10个最常见的值）
        value_counts = {}
        for value in non_null_values:
            value_counts[str(value)] = value_counts.get(str(value), 0) + 1
        
        # 按频率排序并取前10个
        sorted_values = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
        summary.value_distribution = dict(sorted_values[:10])
        
        return summary
    
    def assess_data_quality(self, profile: DataProfile, 
                          column_stats: List[StatisticalSummary]) -> Dict[str, Any]:
        """评估数据质量"""
        quality_assessment = {
            'overall_quality': DataQuality.GOOD,
            'quality_score': 0.0,
            'completeness_score': 0.0,
            'uniqueness_score': 0.0,
            'consistency_score': 0.0,
            'issues': [],
            'recommendations': []
        }
        
        # 完整性评估
        completeness = profile.completeness_ratio
        quality_assessment['completeness_score'] = completeness
        
        # 唯一性评估
        uniqueness = profile.uniqueness_ratio
        quality_assessment['uniqueness_score'] = uniqueness
        
        # 一致性评估（基于数据类型一致性）
        consistency_score = self._calculate_consistency_score(column_stats)
        quality_assessment['consistency_score'] = consistency_score
        
        # 计算总体质量分数
        overall_score = (completeness * 0.4 + uniqueness * 0.3 + consistency_score * 0.3)
        quality_assessment['quality_score'] = overall_score
        
        # 确定质量等级
        if overall_score >= 0.95:
            quality_assessment['overall_quality'] = DataQuality.EXCELLENT
        elif overall_score >= 0.85:
            quality_assessment['overall_quality'] = DataQuality.GOOD
        elif overall_score >= 0.70:
            quality_assessment['overall_quality'] = DataQuality.FAIR
        elif overall_score >= 0.50:
            quality_assessment['overall_quality'] = DataQuality.POOR
        else:
            quality_assessment['overall_quality'] = DataQuality.CRITICAL
        
        # 生成问题和建议
        self._generate_quality_issues_and_recommendations(quality_assessment, profile, column_stats)
        
        return quality_assessment
    
    def detect_anomalies(self, data: List[Dict[str, Any]], 
                        column_name: str,
                        method: str = 'iqr',
                        sensitivity: float = 1.5) -> AnomalyDetectionResult:
        """异常检测"""
        values = [record.get(column_name) for record in data if record.get(column_name) is not None]
        
        if not values:
            return AnomalyDetectionResult(
                column_name=column_name,
                anomaly_type="no_data",
                anomaly_count=0,
                anomaly_ratio=0.0
            )
        
        # 尝试转换为数值
        numeric_values = []
        for v in values:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                pass
        
        if not numeric_values:
            # 对于非数值数据，使用频率异常检测
            return self._detect_frequency_anomalies(values, column_name)
        
        # 数值异常检测
        if method == 'iqr':
            return self._detect_iqr_anomalies(numeric_values, column_name, sensitivity)
        elif method == 'zscore':
            return self._detect_zscore_anomalies(numeric_values, column_name, sensitivity)
        else:
            raise ValueError(f"Unknown anomaly detection method: {method}")
    
    def generate_insights(self, profile: DataProfile, 
                         column_stats: List[StatisticalSummary]) -> List[Dict[str, Any]]:
        """生成数据洞察"""
        insights = []
        
        # 数据规模洞察
        if profile.total_records > 100000:
            insights.append({
                'type': 'scale',
                'category': 'data_size',
                'message': f'大型数据集 ({profile.total_records:,} 条记录)，适合进行深度分析',
                'priority': 'info'
            })
        elif profile.total_records < 100:
            insights.append({
                'type': 'scale',
                'category': 'data_size', 
                'message': f'小型数据集 ({profile.total_records} 条记录)，统计结果可能不够稳定',
                'priority': 'warning'
            })
        
        # 数据质量洞察
        if profile.completeness_ratio < 0.8:
            insights.append({
                'type': 'quality',
                'category': 'completeness',
                'message': f'数据完整性较低 ({profile.completeness_ratio:.1%})，建议进行数据清理',
                'priority': 'warning'
            })
        
        # 列级别洞察
        for stat in column_stats:
            # 高唯一性列
            if stat.uniqueness > 0.95:
                insights.append({
                    'type': 'uniqueness',
                    'category': 'column_property',
                    'message': f'列 "{stat.column_name}" 具有高唯一性 ({stat.uniqueness:.1%})，可能是标识符',
                    'priority': 'info'
                })
            
            # 数值分布洞察
            if stat.data_type in ['integer', 'float'] and stat.std_dev is not None:
                cv = stat.std_dev / abs(stat.mean) if stat.mean and stat.mean != 0 else 0
                if cv > 1.0:
                    insights.append({
                        'type': 'distribution',
                        'category': 'variability',
                        'message': f'列 "{stat.column_name}" 变异系数较高 ({cv:.2f})，数据分布较为分散',
                        'priority': 'info'
                    })
        
        return insights
    
    def _infer_data_type(self, values: List[Any]) -> str:
        """推断数据类型"""
        if not values:
            return 'unknown'
        
        sample_size = min(100, len(values))
        sample = values[:sample_size]
        
        type_counts = {
            'integer': 0,
            'float': 0,
            'string': 0,
            'boolean': 0,
            'date': 0,
            'datetime': 0
        }
        
        for value in sample:
            if isinstance(value, bool):
                type_counts['boolean'] += 1
            elif isinstance(value, int):
                type_counts['integer'] += 1
            elif isinstance(value, float):
                type_counts['float'] += 1
            elif isinstance(value, datetime):
                if value.time() != value.time().replace(hour=0, minute=0, second=0, microsecond=0):
                    type_counts['datetime'] += 1
                else:
                    type_counts['date'] += 1
            else:
                # 尝试解析数值
                str_value = str(value).strip()
                
                try:
                    int(str_value)
                    type_counts['integer'] += 1
                    continue
                except ValueError:
                    pass
                
                try:
                    float(str_value)
                    type_counts['float'] += 1
                    continue
                except ValueError:
                    pass
                
                # 尝试解析日期
                for date_format in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y']:
                    try:
                        datetime.strptime(str_value, date_format)
                        type_counts['date'] += 1
                        break
                    except ValueError:
                        continue
                else:
                    type_counts['string'] += 1
        
        # 返回最常见的类型
        return max(type_counts, key=type_counts.get)
    
    def _calculate_value_range(self, values: List[Any], data_type: str) -> Dict[str, Any]:
        """计算值范围"""
        if data_type in ['integer', 'float']:
            numeric_values = []
            for v in values:
                try:
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    continue
            
            if numeric_values:
                return {
                    'min': min(numeric_values),
                    'max': max(numeric_values),
                    'range': max(numeric_values) - min(numeric_values)
                }
        
        elif data_type == 'string':
            text_values = [str(v) for v in values]
            lengths = [len(t) for t in text_values]
            
            return {
                'min_length': min(lengths) if lengths else 0,
                'max_length': max(lengths) if lengths else 0,
                'avg_length': statistics.mean(lengths) if lengths else 0
            }
        
        return {'type': data_type, 'sample_values': values[:5]}
    
    def _calculate_consistency_score(self, column_stats: List[StatisticalSummary]) -> float:
        """计算一致性分数"""
        if not column_stats:
            return 1.0
        
        consistency_scores = []
        
        for stat in column_stats:
            # 基于数据类型推断的一致性
            type_consistency = 1.0
            
            # 对于数值列，检查是否有非数值的异常值
            if stat.data_type in ['integer', 'float']:
                # 这里可以添加更复杂的一致性检查
                type_consistency = 1.0
            
            consistency_scores.append(type_consistency)
        
        return statistics.mean(consistency_scores) if consistency_scores else 1.0
    
    def _generate_quality_issues_and_recommendations(self, quality_assessment: Dict[str, Any],
                                                   profile: DataProfile,
                                                   column_stats: List[StatisticalSummary]):
        """生成质量问题和建议"""
        issues = quality_assessment['issues']
        recommendations = quality_assessment['recommendations']
        
        # 完整性问题
        if profile.completeness_ratio < 0.9:
            issues.append({
                'type': 'completeness',
                'severity': 'high' if profile.completeness_ratio < 0.7 else 'medium',
                'message': f'数据完整性较低: {profile.completeness_ratio:.1%}',
                'affected_records': profile.null_values
            })
            
            recommendations.append({
                'type': 'data_cleaning',
                'priority': 'high',
                'action': '考虑填充缺失值或移除不完整的记录',
                'impact': '提高数据分析的可靠性'
            })
        
        # 重复数据问题
        if profile.duplicate_records > 0:
            duplicate_ratio = profile.duplicate_records / profile.total_records
            if duplicate_ratio > 0.05:  # 5%以上的重复率
                issues.append({
                    'type': 'duplicates',
                    'severity': 'medium',
                    'message': f'发现 {profile.duplicate_records} 条重复记录 ({duplicate_ratio:.1%})',
                    'affected_records': profile.duplicate_records
                })
                
                recommendations.append({
                    'type': 'deduplication',
                    'priority': 'medium',
                    'action': '清理重复记录',
                    'impact': '提高数据质量和分析准确性'
                })
    
    def _detect_iqr_anomalies(self, values: List[float], column_name: str, 
                            sensitivity: float) -> AnomalyDetectionResult:
        """使用IQR方法检测异常"""
        if len(values) < 4:
            return AnomalyDetectionResult(
                column_name=column_name,
                anomaly_type="insufficient_data",
                anomaly_count=0,
                anomaly_ratio=0.0
            )
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        q1 = sorted_values[n // 4]
        q3 = sorted_values[3 * n // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - sensitivity * iqr
        upper_bound = q3 + sensitivity * iqr
        
        anomalies = [v for v in values if v < lower_bound or v > upper_bound]
        
        return AnomalyDetectionResult(
            column_name=column_name,
            anomaly_type="statistical_outlier",
            anomaly_count=len(anomalies),
            anomaly_ratio=len(anomalies) / len(values),
            anomalous_values=anomalies[:10],  # 最多返回10个异常值
            threshold_used=sensitivity,
            detection_method="iqr"
        )
    
    def _detect_zscore_anomalies(self, values: List[float], column_name: str,
                               sensitivity: float) -> AnomalyDetectionResult:
        """使用Z分数方法检测异常"""
        if len(values) < 2:
            return AnomalyDetectionResult(
                column_name=column_name,
                anomaly_type="insufficient_data",
                anomaly_count=0,
                anomaly_ratio=0.0
            )
        
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)
        
        if std_val == 0:
            return AnomalyDetectionResult(
                column_name=column_name,
                anomaly_type="no_variance",
                anomaly_count=0,
                anomaly_ratio=0.0
            )
        
        anomalies = []
        for value in values:
            z_score = abs((value - mean_val) / std_val)
            if z_score > sensitivity:
                anomalies.append(value)
        
        return AnomalyDetectionResult(
            column_name=column_name,
            anomaly_type="statistical_outlier",
            anomaly_count=len(anomalies),
            anomaly_ratio=len(anomalies) / len(values),
            anomalous_values=anomalies[:10],
            threshold_used=sensitivity,
            detection_method="zscore"
        )
    
    def _detect_frequency_anomalies(self, values: List[Any], 
                                  column_name: str) -> AnomalyDetectionResult:
        """检测频率异常"""
        if not values:
            return AnomalyDetectionResult(
                column_name=column_name,
                anomaly_type="no_data",
                anomaly_count=0,
                anomaly_ratio=0.0
            )
        
        value_counts = {}
        for value in values:
            str_value = str(value)
            value_counts[str_value] = value_counts.get(str_value, 0) + 1
        
        # 找出只出现一次的值（可能的异常值）
        rare_values = [value for value, count in value_counts.items() if count == 1]
        
        return AnomalyDetectionResult(
            column_name=column_name,
            anomaly_type="rare_values",
            anomaly_count=len(rare_values),
            anomaly_ratio=len(rare_values) / len(values),
            anomalous_values=rare_values[:10],
            detection_method="frequency"
        )