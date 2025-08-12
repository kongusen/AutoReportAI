"""
Analysis Agent

Performs statistical analysis and data processing operations.
Handles complex analytical tasks that were previously done in the
intelligent_placeholder system's statistical components.

Features:
- Descriptive statistics calculation
- Trend analysis and forecasting
- Comparative analysis
- Aggregation and grouping operations
- Custom analytical functions
"""

import json
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

from .base import BaseAgent, AgentConfig, AgentResult, AgentType, AgentError


@dataclass
class AnalysisRequest:
    """Analysis request parameters"""
    data: Union[List[Dict[str, Any]], Dict[str, Any]]
    analysis_type: str  # "descriptive", "trend", "comparative", "aggregation"
    parameters: Dict[str, Any] = None
    groupby_fields: List[str] = None
    metric_fields: List[str] = None
    time_field: str = None
    filters: Dict[str, Any] = None
    
    def __post_init__(self):
        """Handle any additional parameters passed to the constructor"""
        pass


@dataclass
class AnalysisResult:
    """Analysis result"""
    analysis_type: str
    results: Dict[str, Any]
    summary: str
    metadata: Dict[str, Any] = None
    charts_data: List[Dict[str, Any]] = None


class AnalysisAgent(BaseAgent):
    """
    Agent for performing statistical analysis and data processing
    """
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="analysis_agent",
                agent_type=AgentType.ANALYSIS,
                name="Analysis Agent",
                description="Performs statistical analysis and data processing",
                timeout_seconds=60,
                enable_caching=True,
                cache_ttl_seconds=900  # 15-minute cache for analysis results
            )
        
        super().__init__(config)
        self.analysis_functions = self._register_analysis_functions()
    
    def _register_analysis_functions(self) -> Dict[str, callable]:
        """Register available analysis functions"""
        return {
            "descriptive": self._descriptive_analysis,
            "trend": self._trend_analysis,
            "comparative": self._comparative_analysis,
            "aggregation": self._aggregation_analysis,
            "correlation": self._correlation_analysis,
            "distribution": self._distribution_analysis
        }
    
    async def execute(
        self,
        input_data: Union[AnalysisRequest, Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Execute analysis operation
        
        Args:
            input_data: AnalysisRequest or dict with analysis parameters
            context: Additional context information
            
        Returns:
            AgentResult with analysis results
        """
        try:
            # Parse input data
            if isinstance(input_data, dict):
                # Filter out unsupported parameters
                supported_params = {
                    'data', 'analysis_type', 'parameters', 'groupby_fields', 
                    'metric_fields', 'time_field', 'filters'
                }
                filtered_data = {k: v for k, v in input_data.items() if k in supported_params}
                analysis_request = AnalysisRequest(**filtered_data)
            else:
                analysis_request = input_data
            
            self.logger.info(
                "Executing analysis",
                agent_id=self.agent_id,
                analysis_type=analysis_request.analysis_type,
                data_size=len(str(analysis_request.data))
            )
            
            # Validate and prepare data
            prepared_data = self._prepare_data(analysis_request.data)
            
            # Apply filters if specified
            if analysis_request.filters:
                prepared_data = self._apply_filters(prepared_data, analysis_request.filters)
            
            # Execute analysis
            if analysis_request.analysis_type not in self.analysis_functions:
                raise AgentError(
                    f"Unsupported analysis type: {analysis_request.analysis_type}",
                    self.agent_id,
                    "UNSUPPORTED_ANALYSIS_TYPE"
                )
            
            analysis_function = self.analysis_functions[analysis_request.analysis_type]
            analysis_result = await analysis_function(prepared_data, analysis_request)
            
            return AgentResult(
                success=True,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=analysis_result,
                metadata={
                    "analysis_type": analysis_request.analysis_type,
                    "data_points": len(prepared_data) if isinstance(prepared_data, list) else 1,
                    "processing_time": analysis_result.metadata.get("processing_time", 0)
                }
            )
            
        except Exception as e:
            error_msg = f"Analysis execution failed: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    def _prepare_data(self, data: Union[List[Dict], Dict]) -> List[Dict[str, Any]]:
        """Prepare and validate data for analysis"""
        if isinstance(data, dict):
            # Convert single dict to list
            return [data]
        elif isinstance(data, list):
            # Ensure all items are dictionaries
            return [item for item in data if isinstance(item, dict)]
        else:
            raise AgentError(
                f"Unsupported data type: {type(data)}",
                self.agent_id,
                "INVALID_DATA_TYPE"
            )
    
    def _apply_filters(
        self, 
        data: List[Dict[str, Any]], 
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filters to data"""
        filtered_data = []
        
        for item in data:
            include_item = True
            
            for field, filter_value in filters.items():
                if field not in item:
                    include_item = False
                    break
                
                item_value = item[field]
                
                # Handle different filter types
                if isinstance(filter_value, dict):
                    # Range or comparison filters
                    if "min" in filter_value and item_value < filter_value["min"]:
                        include_item = False
                        break
                    if "max" in filter_value and item_value > filter_value["max"]:
                        include_item = False
                        break
                    if "eq" in filter_value and item_value != filter_value["eq"]:
                        include_item = False
                        break
                elif isinstance(filter_value, list):
                    # Value list filter
                    if item_value not in filter_value:
                        include_item = False
                        break
                else:
                    # Direct value comparison
                    if item_value != filter_value:
                        include_item = False
                        break
            
            if include_item:
                filtered_data.append(item)
        
        return filtered_data
    
    async def _descriptive_analysis(
        self, 
        data: List[Dict[str, Any]], 
        request: AnalysisRequest
    ) -> AnalysisResult:
        """Perform descriptive statistical analysis"""
        import time
        start_time = time.time()
        
        results = {}
        numeric_fields = []
        categorical_fields = []
        
        # Identify field types and calculate statistics
        if data:
            sample_item = data[0]
            
            for field in sample_item.keys():
                values = [item.get(field) for item in data if item.get(field) is not None]
                
                # Check if field is numeric
                numeric_values = []
                for value in values:
                    try:
                        numeric_values.append(float(value))
                    except (ValueError, TypeError):
                        break
                
                if len(numeric_values) == len(values) and numeric_values:
                    # Numeric field
                    numeric_fields.append(field)
                    results[field] = {
                        "type": "numeric",
                        "count": len(numeric_values),
                        "mean": statistics.mean(numeric_values),
                        "median": statistics.median(numeric_values),
                        "mode": statistics.mode(numeric_values) if len(set(numeric_values)) < len(numeric_values) else None,
                        "std_dev": statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0,
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "sum": sum(numeric_values),
                        "variance": statistics.variance(numeric_values) if len(numeric_values) > 1 else 0
                    }
                else:
                    # Categorical field
                    categorical_fields.append(field)
                    value_counts = {}
                    for value in values:
                        value_str = str(value)
                        value_counts[value_str] = value_counts.get(value_str, 0) + 1
                    
                    results[field] = {
                        "type": "categorical",
                        "count": len(values),
                        "unique_values": len(value_counts),
                        "value_counts": value_counts,
                        "most_frequent": max(value_counts.items(), key=lambda x: x[1]) if value_counts else None
                    }
        
        # Generate summary
        summary = f"描述性分析完成：分析了 {len(data)} 条记录，包含 {len(numeric_fields)} 个数值字段和 {len(categorical_fields)} 个分类字段。"
        
        processing_time = time.time() - start_time
        
        return AnalysisResult(
            analysis_type="descriptive",
            results=results,
            summary=summary,
            metadata={
                "processing_time": processing_time,
                "numeric_fields": numeric_fields,
                "categorical_fields": categorical_fields,
                "total_records": len(data)
            }
        )
    
    async def _trend_analysis(
        self,
        data: List[Dict[str, Any]],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """Perform trend analysis"""
        import time
        start_time = time.time()
        
        time_field = request.time_field or self._detect_time_field(data)
        metric_fields = request.metric_fields or self._detect_numeric_fields(data)
        
        if not time_field:
            raise AgentError(
                "No time field specified or detected for trend analysis",
                self.agent_id,
                "MISSING_TIME_FIELD"
            )
        
        results = {}
        
        # Sort data by time field
        try:
            sorted_data = sorted(data, key=lambda x: self._parse_time_value(x.get(time_field)))
        except Exception as e:
            raise AgentError(
                f"Failed to sort data by time field: {str(e)}",
                self.agent_id,
                "TIME_SORT_ERROR"
            )
        
        for metric_field in metric_fields:
            # Extract time series data
            time_series = []
            values = []
            
            for item in sorted_data:
                if metric_field in item and item[metric_field] is not None:
                    try:
                        time_value = self._parse_time_value(item[time_field])
                        numeric_value = float(item[metric_field])
                        time_series.append(time_value)
                        values.append(numeric_value)
                    except (ValueError, TypeError):
                        continue
            
            if len(values) < 2:
                continue
            
            # Calculate trend metrics
            trend_analysis = self._calculate_trend_metrics(values)
            
            results[metric_field] = {
                "data_points": len(values),
                "start_value": values[0],
                "end_value": values[-1],
                "total_change": values[-1] - values[0],
                "percent_change": ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0,
                "trend_direction": trend_analysis["direction"],
                "trend_strength": trend_analysis["strength"],
                "average_change_per_period": trend_analysis["average_change"],
                "volatility": trend_analysis["volatility"],
                "time_series_data": list(zip(time_series, values))
            }
        
        # Generate summary
        summary = f"趋势分析完成：分析了 {len(metric_fields)} 个指标的时间趋势，时间跨度包含 {len(data)} 个数据点。"
        
        processing_time = time.time() - start_time
        
        return AnalysisResult(
            analysis_type="trend",
            results=results,
            summary=summary,
            metadata={
                "processing_time": processing_time,
                "time_field": time_field,
                "metric_fields": metric_fields
            },
            charts_data=[{
                "type": "line",
                "title": f"{field} 趋势图",
                "data": results[field]["time_series_data"]
            } for field in results.keys()]
        )
    
    async def _comparative_analysis(
        self,
        data: List[Dict[str, Any]],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """Perform comparative analysis"""
        import time
        start_time = time.time()
        
        groupby_fields = request.groupby_fields or []
        metric_fields = request.metric_fields or self._detect_numeric_fields(data)
        
        if not groupby_fields:
            raise AgentError(
                "No groupby fields specified for comparative analysis",
                self.agent_id,
                "MISSING_GROUPBY_FIELDS"
            )
        
        results = {}
        
        # Group data
        groups = self._group_data(data, groupby_fields)
        
        for metric_field in metric_fields:
            metric_results = {}
            group_values = {}
            
            # Calculate statistics for each group
            for group_key, group_data in groups.items():
                values = []
                for item in group_data:
                    if metric_field in item and item[metric_field] is not None:
                        try:
                            values.append(float(item[metric_field]))
                        except (ValueError, TypeError):
                            continue
                
                if values:
                    group_values[group_key] = values
                    metric_results[group_key] = {
                        "count": len(values),
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                        "min": min(values),
                        "max": max(values),
                        "sum": sum(values)
                    }
            
            # Perform comparisons
            if len(metric_results) >= 2:
                # Find best and worst performing groups
                means = {k: v["mean"] for k, v in metric_results.items()}
                best_group = max(means, key=means.get)
                worst_group = min(means, key=means.get)
                
                metric_results["comparison_summary"] = {
                    "best_performing_group": best_group,
                    "worst_performing_group": worst_group,
                    "performance_gap": means[best_group] - means[worst_group],
                    "relative_difference": ((means[best_group] - means[worst_group]) / means[worst_group] * 100) if means[worst_group] != 0 else 0
                }
            
            results[metric_field] = metric_results
        
        # Generate summary
        total_groups = len(groups)
        summary = f"比较分析完成：对 {total_groups} 个组别进行了 {len(metric_fields)} 个指标的比较分析。"
        
        processing_time = time.time() - start_time
        
        return AnalysisResult(
            analysis_type="comparative",
            results=results,
            summary=summary,
            metadata={
                "processing_time": processing_time,
                "groupby_fields": groupby_fields,
                "metric_fields": metric_fields,
                "total_groups": total_groups
            },
            charts_data=[{
                "type": "bar",
                "title": f"{field} 组别比较",
                "data": [(k, v["mean"]) for k, v in results[field].items() if isinstance(v, dict) and "mean" in v]
            } for field in metric_fields if field in results]
        )
    
    async def _aggregation_analysis(
        self,
        data: List[Dict[str, Any]],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """Perform aggregation analysis"""
        import time
        start_time = time.time()
        
        groupby_fields = request.groupby_fields or []
        metric_fields = request.metric_fields or self._detect_numeric_fields(data)
        parameters = request.parameters or {}
        
        results = {}
        
        if groupby_fields:
            # Group and aggregate
            groups = self._group_data(data, groupby_fields)
            
            for group_key, group_data in groups.items():
                group_results = {"record_count": len(group_data)}
                
                for metric_field in metric_fields:
                    values = []
                    for item in group_data:
                        if metric_field in item and item[metric_field] is not None:
                            try:
                                values.append(float(item[metric_field]))
                            except (ValueError, TypeError):
                                continue
                    
                    if values:
                        group_results[metric_field] = {
                            "sum": sum(values),
                            "avg": statistics.mean(values),
                            "count": len(values),
                            "min": min(values),
                            "max": max(values)
                        }
                
                results[group_key] = group_results
        else:
            # Overall aggregation
            overall_results = {"total_records": len(data)}
            
            for metric_field in metric_fields:
                values = []
                for item in data:
                    if metric_field in item and item[metric_field] is not None:
                        try:
                            values.append(float(item[metric_field]))
                        except (ValueError, TypeError):
                            continue
                
                if values:
                    overall_results[metric_field] = {
                        "sum": sum(values),
                        "avg": statistics.mean(values),
                        "count": len(values),
                        "min": min(values),
                        "max": max(values)
                    }
            
            results["overall"] = overall_results
        
        # Generate summary
        if groupby_fields:
            summary = f"聚合分析完成：按 {', '.join(groupby_fields)} 分组，对 {len(metric_fields)} 个指标进行了聚合计算。"
        else:
            summary = f"聚合分析完成：对 {len(metric_fields)} 个指标进行了整体聚合计算。"
        
        processing_time = time.time() - start_time
        
        return AnalysisResult(
            analysis_type="aggregation",
            results=results,
            summary=summary,
            metadata={
                "processing_time": processing_time,
                "groupby_fields": groupby_fields,
                "metric_fields": metric_fields
            }
        )
    
    async def _correlation_analysis(
        self,
        data: List[Dict[str, Any]],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """Perform correlation analysis"""
        import time
        start_time = time.time()
        
        metric_fields = request.metric_fields or self._detect_numeric_fields(data)
        
        if len(metric_fields) < 2:
            raise AgentError(
                "At least two numeric fields required for correlation analysis",
                self.agent_id,
                "INSUFFICIENT_FIELDS"
            )
        
        results = {}
        
        # Extract numeric data
        field_values = {}
        for field in metric_fields:
            values = []
            for item in data:
                if field in item and item[field] is not None:
                    try:
                        values.append(float(item[field]))
                    except (ValueError, TypeError):
                        continue
            field_values[field] = values
        
        # Calculate correlations
        correlations = {}
        for i, field1 in enumerate(metric_fields):
            for field2 in metric_fields[i+1:]:
                if len(field_values[field1]) == len(field_values[field2]) and len(field_values[field1]) > 1:
                    correlation = self._calculate_correlation(
                        field_values[field1], 
                        field_values[field2]
                    )
                    correlations[f"{field1}_vs_{field2}"] = correlation
        
        results["correlations"] = correlations
        results["field_statistics"] = {
            field: {
                "count": len(values),
                "mean": statistics.mean(values) if values else 0,
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0
            }
            for field, values in field_values.items()
        }
        
        # Generate summary
        strong_correlations = [k for k, v in correlations.items() if abs(v) > 0.7]
        summary = f"相关性分析完成：分析了 {len(correlations)} 对字段的相关性，发现 {len(strong_correlations)} 对强相关关系。"
        
        processing_time = time.time() - start_time
        
        return AnalysisResult(
            analysis_type="correlation",
            results=results,
            summary=summary,
            metadata={
                "processing_time": processing_time,
                "metric_fields": metric_fields,
                "strong_correlations": strong_correlations
            }
        )
    
    async def _distribution_analysis(
        self,
        data: List[Dict[str, Any]],
        request: AnalysisRequest
    ) -> AnalysisResult:
        """Perform distribution analysis"""
        import time
        start_time = time.time()
        
        metric_fields = request.metric_fields or self._detect_numeric_fields(data)
        
        results = {}
        
        for field in metric_fields:
            values = []
            for item in data:
                if field in item and item[field] is not None:
                    try:
                        values.append(float(item[field]))
                    except (ValueError, TypeError):
                        continue
            
            if values:
                # Calculate distribution metrics
                sorted_values = sorted(values)
                n = len(values)
                
                # Quartiles
                q1_idx = n // 4
                q2_idx = n // 2
                q3_idx = 3 * n // 4
                
                distribution_metrics = {
                    "count": n,
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std_dev": statistics.stdev(values) if n > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                    "q1": sorted_values[q1_idx] if q1_idx < n else sorted_values[0],
                    "q3": sorted_values[q3_idx] if q3_idx < n else sorted_values[-1],
                    "range": max(values) - min(values),
                    "skewness": self._calculate_skewness(values),
                    "kurtosis": self._calculate_kurtosis(values)
                }
                
                # Create histogram data
                histogram = self._create_histogram(values, bins=10)
                distribution_metrics["histogram"] = histogram
                
                results[field] = distribution_metrics
        
        # Generate summary
        summary = f"分布分析完成：分析了 {len(results)} 个数值字段的分布特征。"
        
        processing_time = time.time() - start_time
        
        return AnalysisResult(
            analysis_type="distribution",
            results=results,
            summary=summary,
            metadata={
                "processing_time": processing_time,
                "metric_fields": metric_fields
            },
            charts_data=[{
                "type": "histogram",
                "title": f"{field} 分布图",
                "data": results[field]["histogram"]
            } for field in results.keys()]
        )
    
    def _detect_numeric_fields(self, data: List[Dict[str, Any]]) -> List[str]:
        """Detect numeric fields in data"""
        if not data:
            return []
        
        numeric_fields = []
        sample_item = data[0]
        
        for field in sample_item.keys():
            # Check if field is numeric by sampling values
            numeric_count = 0
            total_count = 0
            
            for item in data[:min(10, len(data))]:  # Sample first 10 items
                if field in item and item[field] is not None:
                    try:
                        float(item[field])
                        numeric_count += 1
                    except (ValueError, TypeError):
                        pass
                    total_count += 1
            
            # Consider field numeric if > 80% of values are numeric
            if total_count > 0 and numeric_count / total_count > 0.8:
                numeric_fields.append(field)
        
        return numeric_fields
    
    def _detect_time_field(self, data: List[Dict[str, Any]]) -> Optional[str]:
        """Detect time/date field in data"""
        if not data:
            return None
        
        sample_item = data[0]
        time_keywords = ["time", "date", "created", "updated", "timestamp", "日期", "时间"]
        
        # Check for fields with time-related names
        for field in sample_item.keys():
            field_lower = field.lower()
            if any(keyword in field_lower for keyword in time_keywords):
                return field
        
        # Check for fields with time-like values
        for field in sample_item.keys():
            sample_values = [item.get(field) for item in data[:5] if item.get(field)]
            if all(self._is_time_like(value) for value in sample_values):
                return field
        
        return None
    
    def _parse_time_value(self, value) -> datetime:
        """Parse time value to datetime object"""
        if isinstance(value, datetime):
            return value
        elif isinstance(value, str):
            # Try common date formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y-%m-%dT%H:%M:%S"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            
            # If no format works, try parsing as timestamp
            try:
                return datetime.fromtimestamp(float(value))
            except:
                raise ValueError(f"Cannot parse time value: {value}")
        else:
            raise ValueError(f"Unsupported time value type: {type(value)}")
    
    def _is_time_like(self, value) -> bool:
        """Check if value looks like a time/date"""
        try:
            self._parse_time_value(value)
            return True
        except:
            return False
    
    def _group_data(
        self, 
        data: List[Dict[str, Any]], 
        groupby_fields: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group data by specified fields"""
        groups = {}
        
        for item in data:
            # Create group key
            key_parts = []
            for field in groupby_fields:
                if field in item:
                    key_parts.append(str(item[field]))
                else:
                    key_parts.append("null")
            
            group_key = "|".join(key_parts)
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)
        
        return groups
    
    def _calculate_trend_metrics(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend analysis metrics"""
        if len(values) < 2:
            return {"direction": "insufficient_data", "strength": 0, "average_change": 0, "volatility": 0}
        
        # Calculate period-to-period changes
        changes = []
        for i in range(1, len(values)):
            change = values[i] - values[i-1]
            changes.append(change)
        
        average_change = statistics.mean(changes)
        volatility = statistics.stdev(changes) if len(changes) > 1 else 0
        
        # Determine trend direction and strength
        positive_changes = sum(1 for c in changes if c > 0)
        negative_changes = sum(1 for c in changes if c < 0)
        
        if positive_changes > negative_changes:
            direction = "increasing"
            strength = positive_changes / len(changes)
        elif negative_changes > positive_changes:
            direction = "decreasing"
            strength = negative_changes / len(changes)
        else:
            direction = "stable"
            strength = 0.5
        
        return {
            "direction": direction,
            "strength": strength,
            "average_change": average_change,
            "volatility": volatility
        }
    
    def _calculate_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0
        
        n = len(x_values)
        
        # Calculate means
        mean_x = sum(x_values) / n
        mean_y = sum(y_values) / n
        
        # Calculate correlation
        numerator = sum((x_values[i] - mean_x) * (y_values[i] - mean_y) for i in range(n))
        
        sum_sq_x = sum((x_values[i] - mean_x) ** 2 for i in range(n))
        sum_sq_y = sum((y_values[i] - mean_y) ** 2 for i in range(n))
        
        denominator = (sum_sq_x * sum_sq_y) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _calculate_skewness(self, values: List[float]) -> float:
        """Calculate skewness of distribution"""
        if len(values) < 3:
            return 0.0
        
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values)
        
        if std_dev == 0:
            return 0.0
        
        n = len(values)
        skewness = sum(((x - mean) / std_dev) ** 3 for x in values) / n
        
        return skewness
    
    def _calculate_kurtosis(self, values: List[float]) -> float:
        """Calculate kurtosis of distribution"""
        if len(values) < 4:
            return 0.0
        
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values)
        
        if std_dev == 0:
            return 0.0
        
        n = len(values)
        kurtosis = sum(((x - mean) / std_dev) ** 4 for x in values) / n - 3  # Excess kurtosis
        
        return kurtosis
    
    def _create_histogram(self, values: List[float], bins: int = 10) -> List[Dict[str, Any]]:
        """Create histogram data"""
        if not values:
            return []
        
        min_val = min(values)
        max_val = max(values)
        
        if min_val == max_val:
            return [{"bin_start": min_val, "bin_end": max_val, "count": len(values)}]
        
        bin_width = (max_val - min_val) / bins
        histogram = []
        
        for i in range(bins):
            bin_start = min_val + i * bin_width
            bin_end = bin_start + bin_width
            
            if i == bins - 1:  # Last bin includes max value
                count = sum(1 for v in values if bin_start <= v <= bin_end)
            else:
                count = sum(1 for v in values if bin_start <= v < bin_end)
            
            histogram.append({
                "bin_start": bin_start,
                "bin_end": bin_end,
                "count": count
            })
        
        return histogram
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for analysis agent"""
        health = await super().health_check()
        
        # Test basic analysis functionality
        try:
            test_data = [{"value": 1}, {"value": 2}, {"value": 3}]
            test_result = await self._descriptive_analysis(test_data, AnalysisRequest(
                data=test_data,
                analysis_type="descriptive"
            ))
            health["analysis_functions"] = "healthy"
        except Exception as e:
            health["analysis_functions"] = f"error: {str(e)}"
            health["healthy"] = False
        
        health["available_analysis_types"] = list(self.analysis_functions.keys())
        return health