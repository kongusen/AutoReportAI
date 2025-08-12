"""
增强版分析Agent

在原有AnalysisAgent基础上增加以下功能：
- 机器学习预测模型
- 异常检测算法
- 因果关系分析
- 模式挖掘
- 智能洞察生成

Features:
- 预测分析和趋势预测
- 多维异常检测
- 时间序列分析
- 聚类和分类
- 自动特征工程
"""

import asyncio
import numpy as np
import pandas as pd
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings('ignore')

from ..base import BaseAgent, AgentConfig, AgentResult, AgentType, AgentError
from ..analysis_agent import AnalysisAgent, AnalysisRequest, AnalysisResult
from ..security import sandbox_manager, SandboxLevel
from ..tools import tool_registry


@dataclass
class MLAnalysisRequest:
    """机器学习分析请求"""
    data: Union[List[Dict[str, Any]], Dict[str, Any]]
    analysis_type: str  # "prediction", "anomaly", "clustering", "classification", "pattern"
    target_variable: Optional[str] = None       # 目标变量
    feature_columns: List[str] = None           # 特征列
    time_column: Optional[str] = None           # 时间列
    prediction_horizon: int = 7                 # 预测时间跨度（天）
    model_params: Dict[str, Any] = field(default_factory=dict)
    quality_threshold: float = 0.7              # 质量阈值
    enable_feature_engineering: bool = True     # 启用特征工程
    cross_validation: bool = True               # 启用交叉验证


@dataclass
class MLModelInfo:
    """机器学习模型信息"""
    model_id: str
    model_type: str
    algorithm: str
    features: List[str]
    performance_metrics: Dict[str, float]
    created_at: datetime
    last_trained: datetime
    training_data_size: int
    model_object: Any = None  # 实际模型对象


@dataclass
class PredictionResult:
    """预测结果"""
    predictions: List[Any]
    confidence_scores: List[float]
    feature_importance: Dict[str, float]
    model_performance: Dict[str, float]
    forecast_dates: List[str] = None
    prediction_intervals: Dict[str, List] = None


@dataclass
class AnomalyDetectionResult:
    """异常检测结果"""
    anomalies: List[Dict[str, Any]]
    anomaly_scores: List[float]
    normal_pattern: Dict[str, Any]
    detection_method: str
    threshold: float
    summary: str


@dataclass
class ClusteringResult:
    """聚类结果"""
    cluster_labels: List[int]
    cluster_centers: List[List[float]]
    cluster_summary: Dict[int, Dict[str, Any]]
    silhouette_score: float
    optimal_clusters: int
    algorithm: str


class MLPredictor:
    """机器学习预测器"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        
    async def train_prediction_model(
        self,
        data: pd.DataFrame,
        target_column: str,
        feature_columns: List[str] = None,
        model_type: str = "regression"
    ) -> MLModelInfo:
        """训练预测模型"""
        try:
            if feature_columns is None:
                feature_columns = [col for col in data.columns if col != target_column]
            
            # 准备数据
            X = data[feature_columns].fillna(data[feature_columns].mean())
            y = data[target_column].fillna(data[target_column].mean())
            
            # 特征缩放
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 选择模型
            if model_type == "regression":
                from sklearn.ensemble import RandomForestRegressor
                model = RandomForestRegressor(n_estimators=100, random_state=42)
                metric_name = "r2_score"
            else:
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                metric_name = "accuracy"
            
            # 训练模型
            model.fit(X_scaled, y)
            
            # 计算性能指标
            if model_type == "regression":
                from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
                y_pred = model.predict(X_scaled)
                performance = {
                    "r2_score": r2_score(y, y_pred),
                    "mae": mean_absolute_error(y, y_pred),
                    "rmse": np.sqrt(mean_squared_error(y, y_pred))
                }
            else:
                from sklearn.metrics import accuracy_score, precision_score, recall_score
                y_pred = model.predict(X_scaled)
                performance = {
                    "accuracy": accuracy_score(y, y_pred),
                    "precision": precision_score(y, y_pred, average='weighted'),
                    "recall": recall_score(y, y_pred, average='weighted')
                }
            
            # 创建模型信息
            model_id = f"{model_type}_{int(time.time())}"
            model_info = MLModelInfo(
                model_id=model_id,
                model_type=model_type,
                algorithm="RandomForest",
                features=feature_columns,
                performance_metrics=performance,
                created_at=datetime.now(),
                last_trained=datetime.now(),
                training_data_size=len(data),
                model_object=model
            )
            
            # 存储模型和缩放器
            self.models[model_id] = model_info
            self.scalers[model_id] = scaler
            
            return model_info
            
        except Exception as e:
            raise AgentError(f"模型训练失败: {str(e)}", "ml_predictor", "TRAINING_ERROR")
    
    async def make_predictions(
        self,
        model_id: str,
        data: pd.DataFrame,
        prediction_horizon: int = 1
    ) -> PredictionResult:
        """进行预测"""
        try:
            if model_id not in self.models:
                raise AgentError("模型不存在", "ml_predictor", "MODEL_NOT_FOUND")
            
            model_info = self.models[model_id]
            model = model_info.model_object
            scaler = self.scalers[model_id]
            
            # 准备预测数据
            X_pred = data[model_info.features].fillna(data[model_info.features].mean())
            X_pred_scaled = scaler.transform(X_pred)
            
            # 进行预测
            predictions = model.predict(X_pred_scaled)
            
            # 计算置信度（对于回归任务，使用预测方差作为置信度指标）
            if hasattr(model, 'predict_proba'):
                confidence_scores = model.predict_proba(X_pred_scaled).max(axis=1).tolist()
            else:
                # 对于回归模型，使用简化的置信度计算
                if hasattr(model, 'estimators_'):
                    tree_predictions = np.array([tree.predict(X_pred_scaled) for tree in model.estimators_])
                    prediction_std = np.std(tree_predictions, axis=0)
                    confidence_scores = (1 / (1 + prediction_std)).tolist()
                else:
                    confidence_scores = [0.8] * len(predictions)  # 默认置信度
            
            # 特征重要性
            if hasattr(model, 'feature_importances_'):
                feature_importance = dict(zip(model_info.features, model.feature_importances_))
            else:
                feature_importance = {}
            
            return PredictionResult(
                predictions=predictions.tolist(),
                confidence_scores=confidence_scores,
                feature_importance=feature_importance,
                model_performance=model_info.performance_metrics,
                forecast_dates=None,  # 如果是时间序列，需要添加日期
                prediction_intervals=None
            )
            
        except Exception as e:
            raise AgentError(f"预测失败: {str(e)}", "ml_predictor", "PREDICTION_ERROR")


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self):
        self.detectors = {}
    
    async def detect_anomalies(
        self,
        data: pd.DataFrame,
        method: str = "isolation_forest",
        contamination: float = 0.1
    ) -> AnomalyDetectionResult:
        """检测异常"""
        try:
            # 选择数值列
            numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_columns:
                raise AgentError("没有找到数值列进行异常检测", "anomaly_detector", "NO_NUMERIC_DATA")
            
            X = data[numeric_columns].fillna(data[numeric_columns].mean())
            
            # 选择异常检测算法
            if method == "isolation_forest":
                detector = IsolationForest(contamination=contamination, random_state=42)
            elif method == "dbscan":
                from sklearn.cluster import DBSCAN
                detector = DBSCAN(eps=0.5, min_samples=5)
            else:
                detector = IsolationForest(contamination=contamination, random_state=42)
            
            # 检测异常
            if method == "dbscan":
                cluster_labels = detector.fit_predict(X)
                anomaly_labels = (cluster_labels == -1).astype(int)
                anomaly_scores = [-1 if label == -1 else 1 for label in cluster_labels]
            else:
                anomaly_labels = detector.fit_predict(X)
                anomaly_scores = detector.decision_function(X)
                # 转换为0/1标签（-1表示异常，1表示正常）
                anomaly_labels = (anomaly_labels == -1).astype(int)
            
            # 提取异常点
            anomalies = []
            for i, is_anomaly in enumerate(anomaly_labels):
                if is_anomaly:
                    anomaly_record = data.iloc[i].to_dict()
                    anomaly_record['anomaly_score'] = float(anomaly_scores[i])
                    anomaly_record['index'] = i
                    anomalies.append(anomaly_record)
            
            # 计算正常模式
            normal_data = X[anomaly_labels == 0]
            normal_pattern = {
                col: {
                    "mean": float(normal_data[col].mean()),
                    "std": float(normal_data[col].std()),
                    "min": float(normal_data[col].min()),
                    "max": float(normal_data[col].max())
                }
                for col in numeric_columns
            }
            
            # 计算阈值
            threshold = np.percentile(anomaly_scores, (1 - contamination) * 100)
            
            # 生成摘要
            summary = f"在 {len(data)} 条记录中检测到 {len(anomalies)} 个异常点（{len(anomalies)/len(data)*100:.1f}%）"
            
            return AnomalyDetectionResult(
                anomalies=anomalies,
                anomaly_scores=anomaly_scores.tolist(),
                normal_pattern=normal_pattern,
                detection_method=method,
                threshold=float(threshold),
                summary=summary
            )
            
        except Exception as e:
            raise AgentError(f"异常检测失败: {str(e)}", "anomaly_detector", "DETECTION_ERROR")


class PatternMiner:
    """模式挖掘器"""
    
    def __init__(self):
        pass
    
    async def perform_clustering(
        self,
        data: pd.DataFrame,
        method: str = "kmeans",
        n_clusters: int = None
    ) -> ClusteringResult:
        """执行聚类分析"""
        try:
            # 选择数值列
            numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_columns:
                raise AgentError("没有找到数值列进行聚类", "pattern_miner", "NO_NUMERIC_DATA")
            
            X = data[numeric_columns].fillna(data[numeric_columns].mean())
            
            # 数据标准化
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 确定最优聚类数
            if n_clusters is None:
                n_clusters = await self._find_optimal_clusters(X_scaled, method)
            
            # 执行聚类
            if method == "kmeans":
                clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            elif method == "dbscan":
                clusterer = DBSCAN(eps=0.5, min_samples=5)
            else:
                clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            
            cluster_labels = clusterer.fit_predict(X_scaled)
            
            # 计算轮廓系数
            if len(set(cluster_labels)) > 1:
                sil_score = silhouette_score(X_scaled, cluster_labels)
            else:
                sil_score = 0.0
            
            # 获取聚类中心
            if hasattr(clusterer, 'cluster_centers_'):
                cluster_centers = scaler.inverse_transform(clusterer.cluster_centers_).tolist()
            else:
                # 对于DBSCAN，计算每个簇的中心
                unique_labels = set(cluster_labels)
                cluster_centers = []
                for label in unique_labels:
                    if label != -1:  # 忽略噪声点
                        cluster_points = X_scaled[cluster_labels == label]
                        center = cluster_points.mean(axis=0)
                        cluster_centers.append(scaler.inverse_transform([center])[0].tolist())
            
            # 生成簇摘要
            cluster_summary = {}
            for label in set(cluster_labels):
                if label != -1:  # 忽略噪声点
                    cluster_data = data[cluster_labels == label]
                    cluster_summary[int(label)] = {
                        "size": len(cluster_data),
                        "percentage": len(cluster_data) / len(data) * 100,
                        "characteristics": {
                            col: {
                                "mean": float(cluster_data[col].mean()),
                                "std": float(cluster_data[col].std())
                            }
                            for col in numeric_columns
                        }
                    }
            
            return ClusteringResult(
                cluster_labels=cluster_labels.tolist(),
                cluster_centers=cluster_centers,
                cluster_summary=cluster_summary,
                silhouette_score=sil_score,
                optimal_clusters=n_clusters,
                algorithm=method
            )
            
        except Exception as e:
            raise AgentError(f"聚类分析失败: {str(e)}", "pattern_miner", "CLUSTERING_ERROR")
    
    async def _find_optimal_clusters(self, X: np.ndarray, method: str, max_clusters: int = 10) -> int:
        """寻找最优聚类数"""
        if method != "kmeans":
            return 3  # 对于非K-means算法，返回默认值
        
        try:
            max_clusters = min(max_clusters, len(X) // 2)
            if max_clusters < 2:
                return 2
            
            silhouette_scores = []
            K_range = range(2, max_clusters + 1)
            
            for k in K_range:
                kmeans = KMeans(n_clusters=k, random_state=42)
                labels = kmeans.fit_predict(X)
                score = silhouette_score(X, labels)
                silhouette_scores.append(score)
            
            # 选择轮廓系数最高的聚类数
            optimal_k = K_range[np.argmax(silhouette_scores)]
            return optimal_k
            
        except Exception:
            return 3  # 默认聚类数


class InsightGenerator:
    """洞察生成器"""
    
    def __init__(self):
        pass
    
    async def generate_insights(
        self,
        analysis_results: Dict[str, Any],
        data: pd.DataFrame
    ) -> List[str]:
        """生成数据洞察"""
        insights = []
        
        try:
            # 基于预测结果的洞察
            if "prediction" in analysis_results:
                pred_result = analysis_results["prediction"]
                if isinstance(pred_result, PredictionResult):
                    insights.extend(await self._generate_prediction_insights(pred_result, data))
            
            # 基于异常检测的洞察
            if "anomaly" in analysis_results:
                anomaly_result = analysis_results["anomaly"]
                if isinstance(anomaly_result, AnomalyDetectionResult):
                    insights.extend(await self._generate_anomaly_insights(anomaly_result))
            
            # 基于聚类的洞察
            if "clustering" in analysis_results:
                cluster_result = analysis_results["clustering"]
                if isinstance(cluster_result, ClusteringResult):
                    insights.extend(await self._generate_clustering_insights(cluster_result))
            
            # 基于统计分析的洞察
            if "statistics" in analysis_results:
                stats_result = analysis_results["statistics"]
                insights.extend(await self._generate_statistical_insights(stats_result, data))
            
        except Exception as e:
            insights.append(f"洞察生成过程中出现错误: {str(e)}")
        
        return insights
    
    async def _generate_prediction_insights(
        self,
        pred_result: PredictionResult,
        data: pd.DataFrame
    ) -> List[str]:
        """生成预测相关洞察"""
        insights = []
        
        # 模型性能洞察
        performance = pred_result.model_performance
        if "r2_score" in performance:
            r2 = performance["r2_score"]
            if r2 > 0.8:
                insights.append(f"预测模型表现优秀，R²得分达到 {r2:.3f}，预测结果可信度高")
            elif r2 > 0.6:
                insights.append(f"预测模型表现良好，R²得分为 {r2:.3f}，预测结果基本可信")
            else:
                insights.append(f"预测模型表现一般，R²得分仅为 {r2:.3f}，预测结果需谨慎使用")
        
        # 特征重要性洞察
        if pred_result.feature_importance:
            top_feature = max(pred_result.feature_importance, key=pred_result.feature_importance.get)
            importance = pred_result.feature_importance[top_feature]
            insights.append(f"'{top_feature}' 是最重要的预测因子，重要性为 {importance:.3f}")
        
        # 预测值分布洞察
        predictions = pred_result.predictions
        if predictions:
            pred_mean = np.mean(predictions)
            pred_std = np.std(predictions)
            insights.append(f"预测值平均为 {pred_mean:.2f}，标准差为 {pred_std:.2f}")
            
            # 预测趋势
            if len(predictions) > 1:
                trend = np.polyfit(range(len(predictions)), predictions, 1)[0]
                if trend > 0:
                    insights.append(f"预测显示上升趋势，平均增长率为 {trend:.3f}")
                elif trend < 0:
                    insights.append(f"预测显示下降趋势，平均下降率为 {abs(trend):.3f}")
                else:
                    insights.append("预测显示相对稳定的趋势")
        
        return insights
    
    async def _generate_anomaly_insights(self, anomaly_result: AnomalyDetectionResult) -> List[str]:
        """生成异常检测洞察"""
        insights = []
        
        # 异常比例洞察
        total_anomalies = len(anomaly_result.anomalies)
        if total_anomalies > 0:
            insights.append(anomaly_result.summary)
            
            # 异常严重程度
            scores = [abs(anomaly['anomaly_score']) for anomaly in anomaly_result.anomalies]
            if scores:
                max_score = max(scores)
                avg_score = np.mean(scores)
                insights.append(f"异常严重程度：最高 {max_score:.3f}，平均 {avg_score:.3f}")
                
                # 识别最严重的异常
                most_severe = max(anomaly_result.anomalies, key=lambda x: abs(x['anomaly_score']))
                insights.append(f"最严重异常出现在索引 {most_severe['index']}，异常分数为 {most_severe['anomaly_score']:.3f}")
        else:
            insights.append("未检测到异常数据，数据质量良好")
        
        return insights
    
    async def _generate_clustering_insights(self, cluster_result: ClusteringResult) -> List[str]:
        """生成聚类洞察"""
        insights = []
        
        # 聚类质量洞察
        sil_score = cluster_result.silhouette_score
        if sil_score > 0.5:
            insights.append(f"聚类效果优秀，轮廓系数为 {sil_score:.3f}，数据分组清晰")
        elif sil_score > 0.3:
            insights.append(f"聚类效果良好，轮廓系数为 {sil_score:.3f}，存在一定的数据分组")
        else:
            insights.append(f"聚类效果一般，轮廓系数为 {sil_score:.3f}，数据分组不够明显")
        
        # 簇分布洞察
        cluster_summary = cluster_result.cluster_summary
        if cluster_summary:
            largest_cluster = max(cluster_summary.items(), key=lambda x: x[1]['size'])
            smallest_cluster = min(cluster_summary.items(), key=lambda x: x[1]['size'])
            
            insights.append(f"数据被分为 {len(cluster_summary)} 个主要群组")
            insights.append(f"最大群组包含 {largest_cluster[1]['percentage']:.1f}% 的数据")
            insights.append(f"最小群组包含 {smallest_cluster[1]['percentage']:.1f}% 的数据")
        
        return insights
    
    async def _generate_statistical_insights(
        self,
        stats_result: Dict[str, Any],
        data: pd.DataFrame
    ) -> List[str]:
        """生成统计洞察"""
        insights = []
        
        # 基础统计洞察
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col in stats_result:
                col_stats = stats_result[col]
                mean_val = col_stats.get('mean', 0)
                std_val = col_stats.get('std_dev', 0)
                
                # 变异系数
                if mean_val != 0:
                    cv = std_val / abs(mean_val)
                    if cv > 1:
                        insights.append(f"'{col}' 数据波动较大，变异系数为 {cv:.2f}")
                    elif cv < 0.1:
                        insights.append(f"'{col}' 数据相对稳定，变异系数为 {cv:.2f}")
        
        return insights


class EnhancedAnalysisAgent(AnalysisAgent):
    """增强版分析Agent"""
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="enhanced_analysis_agent",
                agent_type=AgentType.ANALYSIS,
                name="Enhanced Analysis Agent",
                description="增强版分析Agent，支持机器学习和高级分析",
                timeout_seconds=180,  # 更长的超时时间
                enable_caching=True,
                cache_ttl_seconds=3600  # 1小时缓存
            )
        
        super().__init__(config)
        
        # 初始化机器学习组件
        self.ml_predictor = MLPredictor()
        self.anomaly_detector = AnomalyDetector()
        self.pattern_miner = PatternMiner()
        self.insight_generator = InsightGenerator()
    
    async def execute_ml_analysis(self, request: MLAnalysisRequest) -> AgentResult:
        """执行机器学习分析"""
        try:
            self.logger.info(
                "执行机器学习分析",
                agent_id=self.agent_id,
                analysis_type=request.analysis_type,
                data_size=len(str(request.data))
            )
            
            # 准备数据
            df = await self._prepare_dataframe(request.data)
            
            # 执行不同类型的分析
            results = {}
            
            if request.analysis_type == "prediction":
                results["prediction"] = await self._perform_prediction_analysis(df, request)
            elif request.analysis_type == "anomaly":
                results["anomaly"] = await self._perform_anomaly_detection(df, request)
            elif request.analysis_type == "clustering":
                results["clustering"] = await self._perform_clustering_analysis(df, request)
            elif request.analysis_type == "pattern":
                results["pattern"] = await self._perform_pattern_analysis(df, request)
            elif request.analysis_type == "comprehensive":
                # 综合分析
                results["prediction"] = await self._perform_prediction_analysis(df, request)
                results["anomaly"] = await self._perform_anomaly_detection(df, request)
                results["clustering"] = await self._perform_clustering_analysis(df, request)
            
            # 生成洞察
            insights = await self.insight_generator.generate_insights(results, df)
            
            # 创建增强的分析结果
            analysis_result = AnalysisResult(
                analysis_type=f"ml_{request.analysis_type}",
                results=results,
                summary=f"完成 {request.analysis_type} 分析，数据量：{len(df)} 条记录",
                metadata={
                    "ml_analysis": True,
                    "insights": insights,
                    "data_shape": df.shape,
                    "analysis_timestamp": datetime.now().isoformat()
                }
            )
            
            return AgentResult(
                success=True,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=analysis_result,
                metadata={
                    "ml_enhanced": True,
                    "analysis_type": request.analysis_type,
                    "insights_count": len(insights)
                }
            )
            
        except Exception as e:
            error_msg = f"机器学习分析失败: {str(e)}"
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
            # 如果是单个字典，转换为单行DataFrame
            df = pd.DataFrame([data])
        elif isinstance(data, list):
            # 如果是字典列表，直接转换
            df = pd.DataFrame(data)
        else:
            raise AgentError("不支持的数据格式", self.agent_id, "INVALID_DATA_FORMAT")
        
        return df
    
    async def _perform_prediction_analysis(
        self,
        df: pd.DataFrame,
        request: MLAnalysisRequest
    ) -> PredictionResult:
        """执行预测分析"""
        if not request.target_variable:
            # 自动选择目标变量
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_columns:
                raise AgentError("没有找到数值列进行预测", self.agent_id, "NO_NUMERIC_TARGET")
            request.target_variable = numeric_columns[-1]  # 使用最后一个数值列作为目标
        
        if request.target_variable not in df.columns:
            raise AgentError(f"目标变量 '{request.target_variable}' 不存在", self.agent_id, "TARGET_NOT_FOUND")
        
        # 训练模型
        model_info = await self.ml_predictor.train_prediction_model(
            df,
            request.target_variable,
            request.feature_columns
        )
        
        # 进行预测
        prediction_result = await self.ml_predictor.make_predictions(
            model_info.model_id,
            df,
            request.prediction_horizon
        )
        
        return prediction_result
    
    async def _perform_anomaly_detection(
        self,
        df: pd.DataFrame,
        request: MLAnalysisRequest
    ) -> AnomalyDetectionResult:
        """执行异常检测"""
        contamination = request.model_params.get("contamination", 0.1)
        method = request.model_params.get("method", "isolation_forest")
        
        return await self.anomaly_detector.detect_anomalies(df, method, contamination)
    
    async def _perform_clustering_analysis(
        self,
        df: pd.DataFrame,
        request: MLAnalysisRequest
    ) -> ClusteringResult:
        """执行聚类分析"""
        method = request.model_params.get("method", "kmeans")
        n_clusters = request.model_params.get("n_clusters", None)
        
        return await self.pattern_miner.perform_clustering(df, method, n_clusters)
    
    async def _perform_pattern_analysis(
        self,
        df: pd.DataFrame,
        request: MLAnalysisRequest
    ) -> Dict[str, Any]:
        """执行模式分析"""
        patterns = {}
        
        # 相关性分析
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) > 1:
            correlation_matrix = numeric_df.corr()
            patterns["correlations"] = correlation_matrix.to_dict()
        
        # 主成分分析
        if len(numeric_df.columns) > 2 and len(df) > 3:
            try:
                pca = PCA(n_components=min(3, len(numeric_df.columns)))
                pca_result = pca.fit_transform(StandardScaler().fit_transform(numeric_df.fillna(0)))
                patterns["pca"] = {
                    "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
                    "n_components": pca.n_components_
                }
            except Exception as e:
                self.logger.warning(f"PCA分析失败: {str(e)}")
        
        return patterns
    
    async def health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        health = await super().health_check()
        
        # 添加机器学习组件的健康检查
        health.update({
            "ml_predictor": {
                "healthy": True,
                "models_count": len(self.ml_predictor.models)
            },
            "anomaly_detector": "healthy",
            "pattern_miner": "healthy",
            "insight_generator": "healthy",
            "ml_libraries": {
                "sklearn": "available",
                "pandas": "available",
                "numpy": "available"
            }
        })
        
        return health