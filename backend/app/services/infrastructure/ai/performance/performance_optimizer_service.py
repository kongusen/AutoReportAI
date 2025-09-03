"""
性能优化器服务

负责分析系统性能瓶颈并提供优化建议
"""

import logging
import time
import statistics
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class BottleneckType(Enum):
    """瓶颈类型"""
    DATABASE_QUERY = "database_query"       # 数据库查询瓶颈
    MEMORY_USAGE = "memory_usage"           # 内存使用瓶颈
    CPU_USAGE = "cpu_usage"                 # CPU使用瓶颈
    NETWORK_IO = "network_io"               # 网络IO瓶颈
    DISK_IO = "disk_io"                     # 磁盘IO瓶颈
    API_RESPONSE = "api_response"           # API响应瓶颈
    CACHE_MISS = "cache_miss"               # 缓存失效瓶颈
    CONNECTION_POOL = "connection_pool"     # 连接池瓶颈
    LOCK_CONTENTION = "lock_contention"     # 锁竞争瓶颈
    GARBAGE_COLLECTION = "garbage_collection" # 垃圾回收瓶颈


class OptimizationLevel(Enum):
    """优化级别"""
    LOW = "low"                 # 低级优化
    MEDIUM = "medium"           # 中级优化  
    HIGH = "high"               # 高级优化
    CRITICAL = "critical"       # 关键优化


class Priority(Enum):
    """优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class PerformanceBottleneck:
    """性能瓶颈"""
    type: BottleneckType
    description: str
    impact_score: float  # 0.0-1.0
    confidence: float    # 0.0-1.0
    affected_components: List[str]
    metrics: Dict[str, float]
    detected_at: datetime
    priority: Priority


@dataclass
class OptimizationRecommendation:
    """优化建议"""
    title: str
    description: str
    optimization_level: OptimizationLevel
    expected_improvement: float  # 0.0-1.0
    implementation_effort: str   # easy, medium, hard
    cost_estimate: str          # low, medium, high
    dependencies: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    metrics_to_track: List[str] = field(default_factory=list)


@dataclass
class PerformanceAnalysisResult:
    """性能分析结果"""
    overall_score: float
    bottlenecks: List[PerformanceBottleneck]
    recommendations: List[OptimizationRecommendation]
    quick_wins: List[str]
    long_term_improvements: List[str]
    analysis_summary: str
    metadata: Dict[str, Any]


class PerformanceOptimizerService:
    """性能优化器服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 性能基准和阈值
        self.performance_thresholds = {
            "response_time": {
                "excellent": 0.1,  # 100ms
                "good": 0.5,       # 500ms
                "acceptable": 2.0,  # 2s
                "poor": 5.0        # 5s
            },
            "cpu_usage": {
                "normal": 60.0,    # 60%
                "high": 80.0,      # 80%
                "critical": 95.0   # 95%
            },
            "memory_usage": {
                "normal": 70.0,    # 70%
                "high": 85.0,      # 85%
                "critical": 95.0   # 95%
            },
            "error_rate": {
                "acceptable": 0.01,  # 1%
                "concerning": 0.05,  # 5%
                "critical": 0.1      # 10%
            }
        }
        
        # 优化模式库
        self.optimization_patterns = {
            "database": [
                "查询优化", "索引优化", "连接池调优", "分区策略", "缓存策略"
            ],
            "application": [
                "代码优化", "算法改进", "并发控制", "资源池化", "异步处理"
            ],
            "infrastructure": [
                "硬件升级", "网络优化", "负载均衡", "分布式架构", "缓存集群"
            ]
        }

    async def optimize_performance(
        self, 
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析和优化系统性能
        
        Args:
            performance_data: 性能数据
            
        Returns:
            优化分析结果字典
        """
        try:
            self.logger.info("开始性能分析和优化")
            
            # 解析性能数据
            parsed_data = self._parse_performance_data(performance_data)
            
            # 检测性能瓶颈
            bottlenecks = await self._detect_bottlenecks(parsed_data)
            
            # 生成优化建议
            recommendations = await self._generate_optimization_recommendations(
                bottlenecks, parsed_data
            )
            
            # 识别快速改进机会
            quick_wins = self._identify_quick_wins(bottlenecks, recommendations)
            
            # 制定长期改进计划
            long_term_improvements = self._plan_long_term_improvements(
                bottlenecks, recommendations
            )
            
            # 计算优化后预期性能
            optimized_metrics = self._calculate_optimized_metrics(
                parsed_data, recommendations
            )
            
            # 计算整体性能评分
            overall_score = self._calculate_performance_score(parsed_data, bottlenecks)
            
            # 生成分析摘要
            analysis_summary = self._generate_analysis_summary(
                bottlenecks, recommendations, overall_score, optimized_metrics
            )
            
            result = {
                "overall_score": overall_score,
                "current_performance": {
                    "response_time": parsed_data.get("avg_response_time", 0),
                    "cpu_usage": parsed_data.get("cpu_usage", 0),
                    "memory_usage": parsed_data.get("memory_usage", 0),
                    "error_rate": parsed_data.get("error_rate", 0),
                    "throughput": parsed_data.get("throughput", 0)
                },
                "optimized_performance": optimized_metrics,
                "improvement_potential": self._calculate_improvement_potential(
                    parsed_data, optimized_metrics
                ),
                "bottlenecks": [self._bottleneck_to_dict(b) for b in bottlenecks],
                "optimization_recommendations": [
                    self._recommendation_to_dict(r) for r in recommendations
                ],
                "quick_wins": quick_wins,
                "long_term_improvements": long_term_improvements,
                "analysis_summary": analysis_summary,
                "optimization_applied": True,
                "metadata": {
                    "analysis_timestamp": datetime.now().isoformat(),
                    "bottlenecks_detected": len(bottlenecks),
                    "recommendations_generated": len(recommendations),
                    "optimization_categories": list(self.optimization_patterns.keys()),
                    "analysis_depth": "comprehensive"
                }
            }
            
            self.logger.info(
                f"性能优化分析完成: 瓶颈={len(bottlenecks)}, 建议={len(recommendations)}, "
                f"评分={overall_score:.2f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"性能优化分析失败: {e}")
            raise ValueError(f"性能优化分析失败: {str(e)}")

    def _parse_performance_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析性能数据"""
        parsed = {
            "avg_response_time": float(data.get("response_time", data.get("avg_response_time", 1.0))),
            "max_response_time": float(data.get("max_response_time", 2.0)),
            "min_response_time": float(data.get("min_response_time", 0.5)),
            "cpu_usage": float(data.get("cpu_usage", 50.0)),
            "memory_usage": float(data.get("memory_usage", 60.0)),
            "error_rate": float(data.get("error_rate", 0.02)),
            "throughput": float(data.get("throughput", 100.0)),
            "connection_pool_usage": float(data.get("connection_pool_usage", 0.4)),
            "cache_hit_rate": float(data.get("cache_hit_rate", 0.8)),
            "disk_usage": float(data.get("disk_usage", 70.0)),
            "network_latency": float(data.get("network_latency", 50.0)),
            "current_score": float(data.get("current_score", 0.7)),
            "bottlenecks": data.get("bottlenecks", [])
        }
        
        return parsed

    async def _detect_bottlenecks(self, data: Dict[str, Any]) -> List[PerformanceBottleneck]:
        """检测性能瓶颈"""
        bottlenecks = []
        
        # 检测数据库查询瓶颈
        if data["avg_response_time"] > self.performance_thresholds["response_time"]["poor"]:
            bottlenecks.append(PerformanceBottleneck(
                type=BottleneckType.DATABASE_QUERY,
                description=f"数据库查询响应时间过长: {data['avg_response_time']:.2f}s",
                impact_score=0.8,
                confidence=0.9,
                affected_components=["database", "api_endpoints"],
                metrics={"response_time": data["avg_response_time"]},
                detected_at=datetime.now(),
                priority=Priority.HIGH
            ))
        
        # 检测内存使用瓶颈
        if data["memory_usage"] > self.performance_thresholds["memory_usage"]["high"]:
            bottlenecks.append(PerformanceBottleneck(
                type=BottleneckType.MEMORY_USAGE,
                description=f"内存使用率过高: {data['memory_usage']:.1f}%",
                impact_score=0.7,
                confidence=0.8,
                affected_components=["application_server", "cache"],
                metrics={"memory_usage": data["memory_usage"]},
                detected_at=datetime.now(),
                priority=Priority.MEDIUM if data["memory_usage"] < 90 else Priority.HIGH
            ))
        
        # 检测CPU使用瓶颈
        if data["cpu_usage"] > self.performance_thresholds["cpu_usage"]["high"]:
            bottlenecks.append(PerformanceBottleneck(
                type=BottleneckType.CPU_USAGE,
                description=f"CPU使用率过高: {data['cpu_usage']:.1f}%",
                impact_score=0.75,
                confidence=0.85,
                affected_components=["application_server", "background_jobs"],
                metrics={"cpu_usage": data["cpu_usage"]},
                detected_at=datetime.now(),
                priority=Priority.HIGH
            ))
        
        # 检测API响应瓶颈
        if data["error_rate"] > self.performance_thresholds["error_rate"]["concerning"]:
            bottlenecks.append(PerformanceBottleneck(
                type=BottleneckType.API_RESPONSE,
                description=f"API错误率过高: {data['error_rate']:.1%}",
                impact_score=0.6,
                confidence=0.9,
                affected_components=["api_gateway", "business_logic"],
                metrics={"error_rate": data["error_rate"]},
                detected_at=datetime.now(),
                priority=Priority.HIGH
            ))
        
        # 检测缓存失效瓶颈
        if data["cache_hit_rate"] < 0.7:
            bottlenecks.append(PerformanceBottleneck(
                type=BottleneckType.CACHE_MISS,
                description=f"缓存命中率低: {data['cache_hit_rate']:.1%}",
                impact_score=0.5,
                confidence=0.7,
                affected_components=["cache_layer", "database"],
                metrics={"cache_hit_rate": data["cache_hit_rate"]},
                detected_at=datetime.now(),
                priority=Priority.MEDIUM
            ))
        
        # 检测连接池瓶颈
        if data["connection_pool_usage"] > 0.8:
            bottlenecks.append(PerformanceBottleneck(
                type=BottleneckType.CONNECTION_POOL,
                description=f"连接池使用率过高: {data['connection_pool_usage']:.1%}",
                impact_score=0.65,
                confidence=0.8,
                affected_components=["database_layer", "api_endpoints"],
                metrics={"connection_pool_usage": data["connection_pool_usage"]},
                detected_at=datetime.now(),
                priority=Priority.MEDIUM
            ))
        
        # 处理用户提供的瓶颈信息
        user_bottlenecks = data.get("bottlenecks", [])
        for bottleneck_name in user_bottlenecks:
            if bottleneck_name in [bt.value for bt in BottleneckType]:
                bottleneck_type = BottleneckType(bottleneck_name)
                bottlenecks.append(PerformanceBottleneck(
                    type=bottleneck_type,
                    description=f"用户指定的瓶颈: {bottleneck_name}",
                    impact_score=0.6,
                    confidence=0.7,
                    affected_components=["system"],
                    metrics={bottleneck_name: 1.0},
                    detected_at=datetime.now(),
                    priority=Priority.MEDIUM
                ))
        
        # 按影响分数排序
        bottlenecks.sort(key=lambda x: x.impact_score, reverse=True)
        
        return bottlenecks

    async def _generate_optimization_recommendations(
        self,
        bottlenecks: List[PerformanceBottleneck],
        data: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """生成优化建议"""
        recommendations = []
        
        for bottleneck in bottlenecks:
            recs = self._get_bottleneck_recommendations(bottleneck, data)
            recommendations.extend(recs)
        
        # 去重和优先级排序
        unique_recommendations = self._deduplicate_recommendations(recommendations)
        
        # 按期望改进排序
        unique_recommendations.sort(key=lambda x: x.expected_improvement, reverse=True)
        
        return unique_recommendations[:10]  # 限制建议数量

    def _get_bottleneck_recommendations(
        self, 
        bottleneck: PerformanceBottleneck, 
        data: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """根据瓶颈类型生成具体建议"""
        
        recommendations = []
        
        if bottleneck.type == BottleneckType.DATABASE_QUERY:
            recommendations.extend([
                OptimizationRecommendation(
                    title="数据库查询优化",
                    description="优化慢查询，添加必要索引，重写复杂查询",
                    optimization_level=OptimizationLevel.HIGH,
                    expected_improvement=0.4,
                    implementation_effort="medium",
                    cost_estimate="low",
                    steps=[
                        "分析慢查询日志",
                        "识别缺失索引", 
                        "优化查询语句",
                        "实施查询缓存"
                    ],
                    metrics_to_track=["query_response_time", "index_usage"],
                    risks=["索引过多可能影响写入性能"]
                ),
                OptimizationRecommendation(
                    title="数据库连接优化",
                    description="调整连接池配置，实施连接复用",
                    optimization_level=OptimizationLevel.MEDIUM,
                    expected_improvement=0.2,
                    implementation_effort="easy",
                    cost_estimate="low",
                    steps=[
                        "调整连接池大小",
                        "设置合理的超时时间",
                        "启用连接验证"
                    ],
                    metrics_to_track=["connection_pool_usage", "connection_wait_time"]
                )
            ])
        
        elif bottleneck.type == BottleneckType.MEMORY_USAGE:
            recommendations.append(OptimizationRecommendation(
                title="内存使用优化",
                description="优化内存分配，实施对象池化，调整GC参数",
                optimization_level=OptimizationLevel.HIGH,
                expected_improvement=0.3,
                implementation_effort="medium",
                cost_estimate="low",
                steps=[
                    "分析内存泄漏",
                    "优化大对象处理", 
                    "调整堆内存大小",
                    "实施对象池化"
                ],
                metrics_to_track=["heap_usage", "gc_frequency", "memory_allocation_rate"],
                risks=["GC调优可能引入延迟"]
            ))
        
        elif bottleneck.type == BottleneckType.CPU_USAGE:
            recommendations.extend([
                OptimizationRecommendation(
                    title="CPU使用优化", 
                    description="优化算法复杂度，实施并行处理，减少CPU密集操作",
                    optimization_level=OptimizationLevel.HIGH,
                    expected_improvement=0.35,
                    implementation_effort="hard",
                    cost_estimate="medium",
                    steps=[
                        "分析CPU热点",
                        "优化算法实现",
                        "实施异步处理",
                        "考虑水平扩展"
                    ],
                    metrics_to_track=["cpu_utilization", "thread_pool_usage"],
                    risks=["并行处理可能增加复杂度"]
                )
            ])
        
        elif bottleneck.type == BottleneckType.API_RESPONSE:
            recommendations.extend([
                OptimizationRecommendation(
                    title="API响应优化",
                    description="实施响应缓存，优化序列化，减少网络往返",
                    optimization_level=OptimizationLevel.MEDIUM,
                    expected_improvement=0.25,
                    implementation_effort="medium",
                    cost_estimate="low",
                    steps=[
                        "实施API缓存",
                        "优化响应体大小",
                        "启用压缩",
                        "实施CDN"
                    ],
                    metrics_to_track=["api_response_time", "cache_hit_rate"],
                    risks=["缓存可能导致数据一致性问题"]
                )
            ])
        
        elif bottleneck.type == BottleneckType.CACHE_MISS:
            recommendations.append(OptimizationRecommendation(
                title="缓存策略优化",
                description="优化缓存键设计，调整缓存过期策略，实施预热机制",
                optimization_level=OptimizationLevel.MEDIUM,
                expected_improvement=0.3,
                implementation_effort="medium", 
                cost_estimate="low",
                steps=[
                    "分析缓存使用模式",
                    "优化缓存键设计",
                    "调整TTL策略",
                    "实施缓存预热"
                ],
                metrics_to_track=["cache_hit_rate", "cache_eviction_rate"]
            ))
        
        elif bottleneck.type == BottleneckType.CONNECTION_POOL:
            recommendations.append(OptimizationRecommendation(
                title="连接池优化",
                description="调整连接池参数，实施连接监控，优化连接生命周期",
                optimization_level=OptimizationLevel.MEDIUM,
                expected_improvement=0.2,
                implementation_effort="easy",
                cost_estimate="low",
                steps=[
                    "增加最大连接数",
                    "调整连接超时时间",
                    "启用连接验证",
                    "实施连接监控"
                ],
                metrics_to_track=["connection_pool_usage", "connection_wait_time"]
            ))
        
        return recommendations

    def _identify_quick_wins(
        self, 
        bottlenecks: List[PerformanceBottleneck], 
        recommendations: List[OptimizationRecommendation]
    ) -> List[str]:
        """识别快速改进机会"""
        quick_wins = []
        
        # 寻找简单实施且效果明显的优化
        easy_recommendations = [
            r for r in recommendations 
            if r.implementation_effort == "easy" and r.expected_improvement > 0.1
        ]
        
        for rec in easy_recommendations:
            quick_wins.append(f"{rec.title}: {rec.description}")
        
        # 基于瓶颈类型的快速修复
        for bottleneck in bottlenecks:
            if bottleneck.type == BottleneckType.CONNECTION_POOL:
                quick_wins.append("立即增加数据库连接池大小")
            elif bottleneck.type == BottleneckType.CACHE_MISS:
                quick_wins.append("启用基础查询结果缓存")
            elif bottleneck.impact_score > 0.7 and bottleneck.confidence > 0.8:
                quick_wins.append(f"紧急处理{bottleneck.description}")
        
        return list(set(quick_wins))  # 去重

    def _plan_long_term_improvements(
        self, 
        bottlenecks: List[PerformanceBottleneck], 
        recommendations: List[OptimizationRecommendation]
    ) -> List[str]:
        """制定长期改进计划"""
        long_term_plans = []
        
        # 寻找复杂但影响大的优化
        complex_recommendations = [
            r for r in recommendations 
            if r.implementation_effort in ["medium", "hard"] and r.expected_improvement > 0.2
        ]
        
        for rec in complex_recommendations:
            long_term_plans.append(f"{rec.title}: 预期改善{rec.expected_improvement:.0%}")
        
        # 基于瓶颈模式的长期规划
        critical_bottlenecks = [b for b in bottlenecks if b.priority == Priority.CRITICAL]
        if critical_bottlenecks:
            long_term_plans.append("制定全面的性能重构计划")
        
        # 基础设施改进
        if any(b.type in [BottleneckType.CPU_USAGE, BottleneckType.MEMORY_USAGE] for b in bottlenecks):
            long_term_plans.append("考虑硬件升级或水平扩展")
        
        # 架构优化
        if len(bottlenecks) > 3:
            long_term_plans.append("评估微服务架构拆分的可行性")
        
        return long_term_plans

    def _calculate_optimized_metrics(
        self, 
        current_data: Dict[str, Any], 
        recommendations: List[OptimizationRecommendation]
    ) -> Dict[str, Any]:
        """计算优化后的预期性能指标"""
        optimized = current_data.copy()
        
        total_improvement = sum(rec.expected_improvement for rec in recommendations)
        improvement_factor = min(total_improvement, 0.8)  # 最大改进限制在80%
        
        # 应用改进到各项指标
        optimized["avg_response_time"] = current_data["avg_response_time"] * (1 - improvement_factor * 0.4)
        optimized["cpu_usage"] = current_data["cpu_usage"] * (1 - improvement_factor * 0.3)
        optimized["memory_usage"] = current_data["memory_usage"] * (1 - improvement_factor * 0.3)
        optimized["error_rate"] = current_data["error_rate"] * (1 - improvement_factor * 0.5)
        optimized["throughput"] = current_data["throughput"] * (1 + improvement_factor * 0.3)
        optimized["cache_hit_rate"] = min(current_data["cache_hit_rate"] * (1 + improvement_factor * 0.2), 0.99)
        
        return optimized

    def _calculate_improvement_potential(
        self, 
        current: Dict[str, Any], 
        optimized: Dict[str, Any]
    ) -> Dict[str, float]:
        """计算改进潜力"""
        improvements = {}
        
        # 计算各项指标的改进幅度
        if current["avg_response_time"] > 0:
            improvements["response_time"] = (
                current["avg_response_time"] - optimized["avg_response_time"]
            ) / current["avg_response_time"]
        
        improvements["cpu_usage"] = (current["cpu_usage"] - optimized["cpu_usage"]) / 100.0
        improvements["memory_usage"] = (current["memory_usage"] - optimized["memory_usage"]) / 100.0
        improvements["error_rate"] = (current["error_rate"] - optimized["error_rate"]) / (current["error_rate"] or 0.01)
        improvements["throughput"] = (optimized["throughput"] - current["throughput"]) / current["throughput"]
        improvements["cache_hit_rate"] = optimized["cache_hit_rate"] - current["cache_hit_rate"]
        
        # 计算总体改进潜力
        improvements["overall"] = statistics.mean([
            abs(v) for v in improvements.values() if isinstance(v, (int, float))
        ])
        
        return {k: round(v, 3) for k, v in improvements.items()}

    def _calculate_performance_score(
        self, 
        data: Dict[str, Any], 
        bottlenecks: List[PerformanceBottleneck]
    ) -> float:
        """计算性能评分"""
        
        # 基础评分
        base_score = 1.0
        
        # 响应时间评分
        response_time = data["avg_response_time"]
        if response_time > 5.0:
            base_score *= 0.4
        elif response_time > 2.0:
            base_score *= 0.6
        elif response_time > 0.5:
            base_score *= 0.8
        
        # 资源使用评分
        cpu_penalty = max(0, (data["cpu_usage"] - 70) / 30 * 0.2)
        memory_penalty = max(0, (data["memory_usage"] - 70) / 30 * 0.2)
        base_score -= (cpu_penalty + memory_penalty)
        
        # 错误率影响
        error_penalty = min(data["error_rate"] * 5, 0.3)
        base_score -= error_penalty
        
        # 瓶颈影响
        bottleneck_penalty = sum(b.impact_score * 0.1 for b in bottlenecks)
        base_score -= min(bottleneck_penalty, 0.4)
        
        # 缓存命中率加成
        cache_bonus = (data["cache_hit_rate"] - 0.7) * 0.2 if data["cache_hit_rate"] > 0.7 else 0
        base_score += cache_bonus
        
        return round(max(min(base_score, 1.0), 0.0), 2)

    def _generate_analysis_summary(
        self, 
        bottlenecks: List[PerformanceBottleneck],
        recommendations: List[OptimizationRecommendation], 
        overall_score: float,
        optimized_metrics: Dict[str, Any]
    ) -> str:
        """生成分析摘要"""
        
        summary_parts = [
            f"系统性能评分为 {overall_score:.1%}。"
        ]
        
        if bottlenecks:
            critical_bottlenecks = [b for b in bottlenecks if b.priority == Priority.CRITICAL]
            high_bottlenecks = [b for b in bottlenecks if b.priority == Priority.HIGH]
            
            if critical_bottlenecks:
                summary_parts.append(f"检测到 {len(critical_bottlenecks)} 个关键性能瓶颈。")
            elif high_bottlenecks:
                summary_parts.append(f"检测到 {len(high_bottlenecks)} 个高优先级性能瓶颈。")
            else:
                summary_parts.append(f"检测到 {len(bottlenecks)} 个性能优化机会。")
        
        if recommendations:
            high_impact_recs = [r for r in recommendations if r.expected_improvement > 0.2]
            if high_impact_recs:
                summary_parts.append(f"提供了 {len(high_impact_recs)} 个高影响优化建议。")
            else:
                summary_parts.append(f"生成了 {len(recommendations)} 个优化建议。")
        
        # 预期改进描述
        current_response = optimized_metrics.get("avg_response_time", 0)
        if current_response > 0:
            summary_parts.append(f"实施优化后，预期响应时间可改善至 {current_response:.2f}秒。")
        
        return " ".join(summary_parts)

    def _deduplicate_recommendations(
        self, 
        recommendations: List[OptimizationRecommendation]
    ) -> List[OptimizationRecommendation]:
        """去重优化建议"""
        seen_titles = set()
        unique_recs = []
        
        for rec in recommendations:
            if rec.title not in seen_titles:
                unique_recs.append(rec)
                seen_titles.add(rec.title)
        
        return unique_recs

    def _bottleneck_to_dict(self, bottleneck: PerformanceBottleneck) -> Dict[str, Any]:
        """将瓶颈对象转换为字典"""
        return {
            "type": bottleneck.type.value,
            "description": bottleneck.description,
            "impact_score": bottleneck.impact_score,
            "confidence": bottleneck.confidence,
            "affected_components": bottleneck.affected_components,
            "metrics": bottleneck.metrics,
            "detected_at": bottleneck.detected_at.isoformat(),
            "priority": bottleneck.priority.name
        }

    def _recommendation_to_dict(self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """将建议对象转换为字典"""
        return {
            "title": recommendation.title,
            "description": recommendation.description,
            "optimization_level": recommendation.optimization_level.value,
            "expected_improvement": recommendation.expected_improvement,
            "implementation_effort": recommendation.implementation_effort,
            "cost_estimate": recommendation.cost_estimate,
            "dependencies": recommendation.dependencies,
            "steps": recommendation.steps,
            "risks": recommendation.risks,
            "metrics_to_track": recommendation.metrics_to_track
        }

    def get_performance_thresholds(self) -> Dict[str, Dict[str, float]]:
        """获取性能阈值配置"""
        return self.performance_thresholds.copy()

    def update_performance_thresholds(self, new_thresholds: Dict[str, Dict[str, float]]) -> None:
        """更新性能阈值"""
        for metric, thresholds in new_thresholds.items():
            if metric in self.performance_thresholds:
                self.performance_thresholds[metric].update(thresholds)
            else:
                self.performance_thresholds[metric] = thresholds
        
        self.logger.info(f"性能阈值已更新: {list(new_thresholds.keys())}")


# 全局实例
performance_optimizer_service = PerformanceOptimizerService()