"""
Enhanced Analysis Pipeline

Advanced data analysis pipeline using the agent system for comprehensive
statistical analysis, pattern detection, and insight generation.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple
import json

from ..core_types import BaseAgent, AgentConfig, AgentResult, AgentType
from ..specialized.schema_analysis_agent import AnalysisAgent


logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """Types of analysis that can be performed"""
    DESCRIPTIVE = "descriptive"           # Basic statistics
    DIAGNOSTIC = "diagnostic"             # Why something happened
    PREDICTIVE = "predictive"            # What might happen
    PRESCRIPTIVE = "prescriptive"        # What should be done
    EXPLORATORY = "exploratory"          # Pattern discovery
    CONFIRMATORY = "confirmatory"        # Hypothesis testing
    TIME_SERIES = "time_series"          # Temporal analysis
    ANOMALY_DETECTION = "anomaly_detection"  # Outlier identification


class InsightLevel(Enum):
    """Levels of insight detail"""
    BASIC = "basic"                      # Simple statistics
    INTERMEDIATE = "intermediate"         # Correlations, trends
    ADVANCED = "advanced"                # Machine learning insights
    EXPERT = "expert"                    # Deep statistical analysis


@dataclass
class StatisticalSummary:
    """Statistical summary of a dataset"""
    count: int = 0
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    null_count: int = 0
    unique_count: int = 0
    mode: Any = None


@dataclass
class CorrelationAnalysis:
    """Correlation analysis results"""
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    strong_correlations: List[Tuple[str, str, float]] = field(default_factory=list)  # (var1, var2, correlation)
    correlation_insights: List[str] = field(default_factory=list)


@dataclass
class TrendAnalysis:
    """Trend analysis results"""
    trend_direction: str = "stable"      # increasing, decreasing, stable, volatile
    trend_strength: float = 0.0          # 0-1 scale
    seasonality_detected: bool = False
    trend_line_equation: Optional[str] = None
    forecast_points: List[Dict[str, Any]] = field(default_factory=list)
    trend_insights: List[str] = field(default_factory=list)


@dataclass
class AnomalyDetectionResult:
    """Anomaly detection results"""
    anomalies_count: int = 0
    anomaly_threshold: float = 0.0
    anomaly_indices: List[int] = field(default_factory=list)
    anomaly_scores: List[float] = field(default_factory=list)
    anomaly_explanations: List[str] = field(default_factory=list)


@dataclass
class PatternDiscovery:
    """Pattern discovery results"""
    clusters_found: int = 0
    cluster_descriptions: List[str] = field(default_factory=list)
    frequent_patterns: List[Dict[str, Any]] = field(default_factory=list)
    association_rules: List[Dict[str, Any]] = field(default_factory=list)
    pattern_insights: List[str] = field(default_factory=list)


@dataclass
class PredictiveInsights:
    """Predictive analysis results"""
    model_type: str = ""
    model_accuracy: float = 0.0
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    confidence_intervals: List[Tuple[float, float]] = field(default_factory=list)
    predictive_insights: List[str] = field(default_factory=list)


@dataclass
class ComprehensiveAnalysisResult:
    """Comprehensive analysis result containing all analysis types"""
    analysis_id: str
    dataset_info: Dict[str, Any] = field(default_factory=dict)
    statistical_summary: Dict[str, StatisticalSummary] = field(default_factory=dict)
    correlation_analysis: Optional[CorrelationAnalysis] = None
    trend_analysis: Optional[TrendAnalysis] = None
    anomaly_detection: Optional[AnomalyDetectionResult] = None
    pattern_discovery: Optional[PatternDiscovery] = None
    predictive_insights: Optional[PredictiveInsights] = None
    key_insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class EnhancedAnalysisPipeline(BaseAgent):
    """
    Enhanced analysis pipeline for comprehensive data analysis
    """
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="enhanced_analysis_pipeline",
                agent_type=AgentType.ANALYSIS,
                name="Enhanced Analysis Pipeline",
                description="Comprehensive data analysis with statistical insights and ML",
                timeout_seconds=600,  # 10 minutes for complex analysis
                enable_caching=True,
                cache_ttl_seconds=7200  # 2 hours cache
            )
        
        super().__init__(config)
        self.analysis_agent = AnalysisAgent()
    
    async def execute(
        self,
        input_data: Any,
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Execute comprehensive data analysis
        
        Expected input_data format:
        {
            "data": List[Dict] or pd.DataFrame,  # The data to analyze
            "analysis_types": List[str],          # Types of analysis to perform
            "insight_level": str,                # Level of insight detail
            "target_column": str,                # Optional target for predictive analysis
            "time_column": str,                  # Optional time column for time series
            "custom_config": Dict[str, Any]      # Optional custom configuration
        }
        """
        import time
        start_time = time.time()
        
        try:
            # Parse input
            data = input_data.get("data")
            analysis_types = input_data.get("analysis_types", ["descriptive"])
            insight_level = InsightLevel(input_data.get("insight_level", "intermediate"))
            target_column = input_data.get("target_column")
            time_column = input_data.get("time_column")
            custom_config = input_data.get("custom_config", {})
            
            if not data:
                raise ValueError("Data is required for analysis")
            
            analysis_id = f"analysis_{hash(str(input_data))}_{int(start_time)}"
            
            self.logger.info(
                f"Starting enhanced analysis pipeline",
                agent_id=self.agent_id,
                analysis_id=analysis_id,
                analysis_types=analysis_types,
                insight_level=insight_level.value
            )
            
            # Convert data to pandas DataFrame if needed
            df = self._prepare_dataframe(data)
            
            # Initialize comprehensive result
            result = ComprehensiveAnalysisResult(
                analysis_id=analysis_id,
                dataset_info=self._get_dataset_info(df)
            )
            
            # Perform requested analysis types
            for analysis_type in analysis_types:
                try:
                    analysis_enum = AnalysisType(analysis_type)
                    await self._perform_analysis_type(
                        df, analysis_enum, result, insight_level, 
                        target_column, time_column, custom_config
                    )
                except Exception as e:
                    self.logger.error(f"Failed to perform {analysis_type} analysis: {e}")
            
            # Generate key insights and recommendations
            result.key_insights = await self._generate_key_insights(result, df)
            result.recommendations = await self._generate_recommendations(result, df)
            
            result.execution_time = time.time() - start_time
            result.analysis_metadata = {
                "rows_analyzed": len(df),
                "columns_analyzed": len(df.columns),
                "analysis_types_completed": len([t for t in analysis_types]),
                "insight_level": insight_level.value,
                "has_target_column": target_column is not None,
                "has_time_column": time_column is not None
            }
            
            self.logger.info(
                f"Enhanced analysis pipeline completed",
                agent_id=self.agent_id,
                analysis_id=analysis_id,
                execution_time=result.execution_time,
                key_insights_count=len(result.key_insights)
            )
            
            return AgentResult(
                success=True,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=result,
                metadata=result.analysis_metadata
            )
            
        except Exception as e:
            error_msg = f"Enhanced analysis pipeline failed: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
    
    def _prepare_dataframe(self, data: Any) -> pd.DataFrame:
        """Convert input data to pandas DataFrame"""
        if isinstance(data, pd.DataFrame):
            return data
        elif isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            return pd.DataFrame([data])
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
    
    def _get_dataset_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get basic information about the dataset"""
        return {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
            "missing_values": df.isnull().sum().to_dict()
        }
    
    async def _perform_analysis_type(
        self,
        df: pd.DataFrame,
        analysis_type: AnalysisType,
        result: ComprehensiveAnalysisResult,
        insight_level: InsightLevel,
        target_column: Optional[str],
        time_column: Optional[str],
        custom_config: Dict[str, Any]
    ):
        """Perform specific type of analysis"""
        
        if analysis_type == AnalysisType.DESCRIPTIVE:
            result.statistical_summary = self._perform_descriptive_analysis(df)
            
        elif analysis_type == AnalysisType.DIAGNOSTIC:
            if insight_level in [InsightLevel.INTERMEDIATE, InsightLevel.ADVANCED, InsightLevel.EXPERT]:
                result.correlation_analysis = self._perform_correlation_analysis(df)
                
        elif analysis_type == AnalysisType.TIME_SERIES:
            if time_column and time_column in df.columns:
                result.trend_analysis = self._perform_trend_analysis(df, time_column, target_column)
                
        elif analysis_type == AnalysisType.ANOMALY_DETECTION:
            if insight_level in [InsightLevel.ADVANCED, InsightLevel.EXPERT]:
                result.anomaly_detection = self._perform_anomaly_detection(df)
                
        elif analysis_type == AnalysisType.EXPLORATORY:
            if insight_level in [InsightLevel.INTERMEDIATE, InsightLevel.ADVANCED, InsightLevel.EXPERT]:
                result.pattern_discovery = self._perform_pattern_discovery(df)
                
        elif analysis_type == AnalysisType.PREDICTIVE:
            if target_column and insight_level in [InsightLevel.ADVANCED, InsightLevel.EXPERT]:
                result.predictive_insights = await self._perform_predictive_analysis(df, target_column)
    
    def _perform_descriptive_analysis(self, df: pd.DataFrame) -> Dict[str, StatisticalSummary]:
        """Perform descriptive statistical analysis"""
        summaries = {}
        
        for column in df.columns:
            try:
                series = df[column]
                summary = StatisticalSummary()
                
                summary.count = len(series)
                summary.null_count = series.isnull().sum()
                summary.unique_count = series.nunique()
                
                if series.dtype in ['int64', 'float64', 'int32', 'float32']:
                    summary.mean = float(series.mean()) if not series.empty else None
                    summary.median = float(series.median()) if not series.empty else None
                    summary.std = float(series.std()) if not series.empty else None
                    summary.min_value = float(series.min()) if not series.empty else None
                    summary.max_value = float(series.max()) if not series.empty else None
                    summary.q25 = float(series.quantile(0.25)) if not series.empty else None
                    summary.q75 = float(series.quantile(0.75)) if not series.empty else None
                    
                    # Calculate skewness and kurtosis if scipy is available
                    try:
                        from scipy import stats
                        if len(series.dropna()) > 3:
                            summary.skewness = float(stats.skew(series.dropna()))
                            summary.kurtosis = float(stats.kurtosis(series.dropna()))
                    except ImportError:
                        pass
                
                # Mode for all column types
                try:
                    mode_values = series.mode()
                    summary.mode = mode_values.iloc[0] if len(mode_values) > 0 else None
                except:
                    pass
                
                summaries[column] = summary
                
            except Exception as e:
                self.logger.error(f"Failed to analyze column {column}: {e}")
                summaries[column] = StatisticalSummary()
        
        return summaries
    
    def _perform_correlation_analysis(self, df: pd.DataFrame) -> CorrelationAnalysis:
        """Perform correlation analysis"""
        analysis = CorrelationAnalysis()
        
        try:
            # Select only numeric columns
            numeric_df = df.select_dtypes(include=[np.number])
            
            if len(numeric_df.columns) < 2:
                return analysis
            
            # Calculate correlation matrix
            corr_matrix = numeric_df.corr()
            analysis.correlation_matrix = corr_matrix.to_dict()
            
            # Find strong correlations (|r| > 0.7)
            for i, col1 in enumerate(corr_matrix.columns):
                for j, col2 in enumerate(corr_matrix.columns):
                    if i < j:  # Avoid duplicates and self-correlation
                        correlation = corr_matrix.loc[col1, col2]
                        if abs(correlation) > 0.7:
                            analysis.strong_correlations.append((col1, col2, correlation))
            
            # Generate correlation insights
            if analysis.strong_correlations:
                analysis.correlation_insights.append(f"Found {len(analysis.strong_correlations)} strong correlations")
                
                strongest = max(analysis.strong_correlations, key=lambda x: abs(x[2]))
                analysis.correlation_insights.append(
                    f"Strongest correlation: {strongest[0]} and {strongest[1]} (r={strongest[2]:.3f})"
                )
            else:
                analysis.correlation_insights.append("No strong correlations found (|r| > 0.7)")
                
        except Exception as e:
            self.logger.error(f"Correlation analysis failed: {e}")
        
        return analysis
    
    def _perform_trend_analysis(
        self, 
        df: pd.DataFrame, 
        time_column: str, 
        target_column: Optional[str] = None
    ) -> TrendAnalysis:
        """Perform trend analysis on time series data"""
        analysis = TrendAnalysis()
        
        try:
            # Convert time column to datetime
            df_copy = df.copy()
            df_copy[time_column] = pd.to_datetime(df_copy[time_column])
            df_copy = df_copy.sort_values(time_column)
            
            # If no target column specified, use first numeric column
            if not target_column:
                numeric_cols = df_copy.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    target_column = numeric_cols[0]
                else:
                    return analysis
            
            if target_column not in df_copy.columns:
                return analysis
            
            values = df_copy[target_column].dropna()
            time_values = df_copy[time_column]
            
            if len(values) < 3:
                return analysis
            
            # Calculate trend using linear regression
            x = np.arange(len(values))
            slope, intercept = np.polyfit(x, values, 1)
            
            # Determine trend direction and strength
            if slope > 0:
                analysis.trend_direction = "increasing"
            elif slope < 0:
                analysis.trend_direction = "decreasing"
            else:
                analysis.trend_direction = "stable"
            
            # Calculate R-squared for trend strength
            predicted = slope * x + intercept
            ss_res = np.sum((values - predicted) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            analysis.trend_strength = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            analysis.trend_line_equation = f"y = {slope:.6f}x + {intercept:.6f}"
            
            # Simple seasonality detection (very basic)
            if len(values) >= 12:
                # Check for repeating patterns every 12 points (monthly-like)
                autocorr_12 = np.corrcoef(values[:-12], values[12:])[0, 1]
                if not np.isnan(autocorr_12) and autocorr_12 > 0.7:
                    analysis.seasonality_detected = True
            
            # Generate trend insights
            if analysis.trend_strength > 0.7:
                analysis.trend_insights.append(f"Strong {analysis.trend_direction} trend detected (R²={analysis.trend_strength:.3f})")
            elif analysis.trend_strength > 0.3:
                analysis.trend_insights.append(f"Moderate {analysis.trend_direction} trend detected (R²={analysis.trend_strength:.3f})")
            else:
                analysis.trend_insights.append(f"Weak or no clear trend (R²={analysis.trend_strength:.3f})")
            
            if analysis.seasonality_detected:
                analysis.trend_insights.append("Potential seasonal patterns detected")
                
        except Exception as e:
            self.logger.error(f"Trend analysis failed: {e}")
        
        return analysis
    
    def _perform_anomaly_detection(self, df: pd.DataFrame) -> AnomalyDetectionResult:
        """Perform anomaly detection using statistical methods"""
        result = AnomalyDetectionResult()
        
        try:
            # Use IQR method for anomaly detection on numeric columns
            numeric_df = df.select_dtypes(include=[np.number])
            
            if numeric_df.empty:
                return result
            
            all_anomalies = []
            
            for column in numeric_df.columns:
                series = numeric_df[column].dropna()
                if len(series) < 4:
                    continue
                
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # Find anomalies
                anomalies = series[(series < lower_bound) | (series > upper_bound)]
                
                for idx in anomalies.index:
                    anomaly_score = abs(series[idx] - series.median()) / series.std() if series.std() > 0 else 0
                    all_anomalies.append((idx, anomaly_score, column, series[idx]))
            
            # Sort by anomaly score and take top anomalies
            all_anomalies.sort(key=lambda x: x[1], reverse=True)
            
            result.anomalies_count = len(all_anomalies)
            result.anomaly_threshold = 1.5  # IQR multiplier
            
            # Take top 20 anomalies
            top_anomalies = all_anomalies[:20]
            result.anomaly_indices = [x[0] for x in top_anomalies]
            result.anomaly_scores = [x[1] for x in top_anomalies]
            
            # Generate explanations
            for idx, score, column, value in top_anomalies[:5]:  # Top 5 explanations
                result.anomaly_explanations.append(
                    f"Row {idx}: {column}={value} (anomaly score: {score:.2f})"
                )
                
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
        
        return result
    
    def _perform_pattern_discovery(self, df: pd.DataFrame) -> PatternDiscovery:
        """Perform pattern discovery using clustering and association rules"""
        discovery = PatternDiscovery()
        
        try:
            # Simple clustering on numeric data
            numeric_df = df.select_dtypes(include=[np.number])
            
            if len(numeric_df) < 10 or len(numeric_df.columns) < 2:
                return discovery
            
            try:
                from sklearn.cluster import KMeans
                from sklearn.preprocessing import StandardScaler
                
                # Standardize the data
                scaler = StandardScaler()
                scaled_data = scaler.fit_transform(numeric_df.fillna(0))
                
                # Perform clustering (k=3 for simplicity)
                kmeans = KMeans(n_clusters=3, random_state=42)
                clusters = kmeans.fit_predict(scaled_data)
                
                discovery.clusters_found = len(np.unique(clusters))
                
                # Generate cluster descriptions
                for i in range(discovery.clusters_found):
                    cluster_data = numeric_df[clusters == i]
                    cluster_size = len(cluster_data)
                    discovery.cluster_descriptions.append(
                        f"Cluster {i+1}: {cluster_size} samples ({cluster_size/len(df)*100:.1f}%)"
                    )
                
                discovery.pattern_insights.append(f"Identified {discovery.clusters_found} distinct data clusters")
                
            except ImportError:
                discovery.pattern_insights.append("Clustering analysis requires scikit-learn")
                
        except Exception as e:
            self.logger.error(f"Pattern discovery failed: {e}")
        
        return discovery
    
    async def _perform_predictive_analysis(
        self, 
        df: pd.DataFrame, 
        target_column: str
    ) -> PredictiveInsights:
        """Perform predictive analysis using simple ML models"""
        insights = PredictiveInsights()
        
        try:
            if target_column not in df.columns:
                return insights
            
            # Prepare features and target
            feature_columns = [col for col in df.select_dtypes(include=[np.number]).columns if col != target_column]
            
            if len(feature_columns) == 0:
                return insights
            
            X = df[feature_columns].fillna(0)
            y = df[target_column].fillna(0)
            
            if len(X) < 10:
                return insights
            
            try:
                from sklearn.model_selection import train_test_split
                from sklearn.linear_model import LinearRegression
                from sklearn.metrics import r2_score
                
                # Split the data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.3, random_state=42
                )
                
                # Train a simple linear regression model
                model = LinearRegression()
                model.fit(X_train, y_train)
                
                # Make predictions
                y_pred = model.predict(X_test)
                
                # Calculate accuracy (R²)
                insights.model_type = "Linear Regression"
                insights.model_accuracy = r2_score(y_test, y_pred)
                
                # Feature importance (coefficients)
                for feature, coef in zip(feature_columns, model.coef_):
                    insights.feature_importance[feature] = float(coef)
                
                # Generate some predictions for new data
                sample_predictions = model.predict(X.head(5))
                for i, pred in enumerate(sample_predictions):
                    insights.predictions.append({
                        "row_index": i,
                        "predicted_value": float(pred),
                        "actual_value": float(y.iloc[i])
                    })
                
                insights.predictive_insights.append(
                    f"Linear regression model achieved R² = {insights.model_accuracy:.3f}"
                )
                
                # Feature importance insights
                important_features = sorted(
                    insights.feature_importance.items(), 
                    key=lambda x: abs(x[1]), 
                    reverse=True
                )[:3]
                
                if important_features:
                    insights.predictive_insights.append(
                        f"Most important features: {', '.join([f[0] for f in important_features])}"
                    )
                    
            except ImportError:
                insights.predictive_insights.append("Predictive analysis requires scikit-learn")
                
        except Exception as e:
            self.logger.error(f"Predictive analysis failed: {e}")
        
        return insights
    
    async def _generate_key_insights(
        self, 
        result: ComprehensiveAnalysisResult, 
        df: pd.DataFrame
    ) -> List[str]:
        """Generate key insights from all analysis results"""
        insights = []
        
        try:
            # Dataset insights
            insights.append(f"Dataset contains {result.dataset_info['rows']} rows and {result.dataset_info['columns']} columns")
            
            # Missing data insights
            missing_data = result.dataset_info.get('missing_values', {})
            total_missing = sum(missing_data.values())
            if total_missing > 0:
                insights.append(f"Found {total_missing} missing values across {len([k for k, v in missing_data.items() if v > 0])} columns")
            
            # Statistical insights
            if result.statistical_summary:
                numeric_columns = len([col for col, summary in result.statistical_summary.items() 
                                     if summary.mean is not None])
                insights.append(f"Analyzed {numeric_columns} numeric columns with statistical measures")
            
            # Correlation insights
            if result.correlation_analysis and result.correlation_analysis.strong_correlations:
                insights.append(f"Discovered {len(result.correlation_analysis.strong_correlations)} strong variable relationships")
            
            # Trend insights
            if result.trend_analysis and result.trend_analysis.trend_direction != "stable":
                strength_desc = "strong" if result.trend_analysis.trend_strength > 0.7 else "moderate"
                insights.append(f"Detected {strength_desc} {result.trend_analysis.trend_direction} trend in time series")
            
            # Anomaly insights
            if result.anomaly_detection and result.anomaly_detection.anomalies_count > 0:
                anomaly_rate = result.anomaly_detection.anomalies_count / result.dataset_info['rows'] * 100
                insights.append(f"Identified {result.anomaly_detection.anomalies_count} anomalies ({anomaly_rate:.1f}% of data)")
            
            # Pattern insights
            if result.pattern_discovery and result.pattern_discovery.clusters_found > 0:
                insights.append(f"Data naturally groups into {result.pattern_discovery.clusters_found} distinct clusters")
            
            # Predictive insights
            if result.predictive_insights and result.predictive_insights.model_accuracy > 0:
                accuracy_desc = "good" if result.predictive_insights.model_accuracy > 0.7 else "moderate"
                insights.append(f"Predictive model shows {accuracy_desc} performance (R²={result.predictive_insights.model_accuracy:.3f})")
                
        except Exception as e:
            self.logger.error(f"Key insights generation failed: {e}")
        
        return insights
    
    async def _generate_recommendations(
        self, 
        result: ComprehensiveAnalysisResult, 
        df: pd.DataFrame
    ) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        try:
            # Data quality recommendations
            missing_data = result.dataset_info.get('missing_values', {})
            high_missing_cols = [col for col, count in missing_data.items() 
                               if count > len(df) * 0.2]  # >20% missing
            
            if high_missing_cols:
                recommendations.append(f"Consider data imputation strategies for columns with high missing values: {', '.join(high_missing_cols)}")
            
            # Statistical recommendations
            if result.statistical_summary:
                high_variance_cols = []
                for col, summary in result.statistical_summary.items():
                    if summary.std and summary.mean and abs(summary.std / summary.mean) > 2:
                        high_variance_cols.append(col)
                
                if high_variance_cols:
                    recommendations.append(f"Consider normalization/standardization for high-variance columns: {', '.join(high_variance_cols)}")
            
            # Correlation recommendations
            if result.correlation_analysis and result.correlation_analysis.strong_correlations:
                recommendations.append("Strong correlations detected - consider feature selection for machine learning models")
            
            # Anomaly recommendations
            if result.anomaly_detection and result.anomaly_detection.anomalies_count > 0:
                anomaly_rate = result.anomaly_detection.anomalies_count / result.dataset_info['rows']
                if anomaly_rate > 0.05:  # >5% anomalies
                    recommendations.append("High anomaly rate detected - investigate data quality and collection processes")
                else:
                    recommendations.append("Review identified anomalies for potential data insights or quality issues")
            
            # Predictive recommendations
            if result.predictive_insights:
                if result.predictive_insights.model_accuracy < 0.5:
                    recommendations.append("Low predictive accuracy - consider feature engineering or alternative modeling approaches")
                elif result.predictive_insights.feature_importance:
                    top_features = sorted(result.predictive_insights.feature_importance.items(), 
                                        key=lambda x: abs(x[1]), reverse=True)[:3]
                    recommendations.append(f"Focus on key predictive features: {', '.join([f[0] for f in top_features])}")
            
            # General recommendations
            if result.dataset_info['rows'] > 100000:
                recommendations.append("Large dataset detected - consider sampling strategies for exploratory analysis")
            
            if len(result.dataset_info['column_names']) > 50:
                recommendations.append("High-dimensional dataset - consider dimensionality reduction techniques")
                
        except Exception as e:
            self.logger.error(f"Recommendations generation failed: {e}")
        
        return recommendations


# Agent instance for use throughout the system
enhanced_analysis_pipeline = EnhancedAnalysisPipeline()