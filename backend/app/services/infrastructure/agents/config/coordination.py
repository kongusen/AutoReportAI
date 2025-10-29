"""
协调配置

定义 Agent 系统的协调和优化配置
支持智能协调、性能优化和监控
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

from ..types import CoordinationConfig, ExecutionStage, TaskComplexity

logger = logging.getLogger(__name__)


@dataclass
class RecursionControl:
    """递归控制配置"""
    # 递归深度控制
    max_recursion_depth: int = 5
    recursion_timeout: int = 300  # 秒
    
    # 复杂度阈值
    complexity_threshold: float = 0.8
    complexity_decay_factor: float = 0.9
    
    # 递归策略
    enable_early_termination: bool = True
    enable_complexity_adaptation: bool = True
    
    # 递归监控
    enable_recursion_logging: bool = True
    recursion_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextManagement:
    """上下文管理配置"""
    # 缓存配置
    context_cache_size: int = 100
    context_refresh_interval: int = 300  # 秒
    context_compression_enabled: bool = True
    
    # 上下文策略
    enable_context_pruning: bool = True
    context_pruning_threshold: float = 0.7
    enable_context_prioritization: bool = True
    
    # 上下文注入
    enable_dynamic_injection: bool = True
    injection_strategy: str = "adaptive"  # adaptive, aggressive, conservative
    injection_frequency: int = 3  # 每N次迭代注入一次


@dataclass
class TokenBudget:
    """Token 预算管理"""
    # 预算限制
    max_tokens_per_iteration: int = 4000
    max_total_tokens: int = 16000
    token_reserve_ratio: float = 0.1  # 保留10%作为缓冲
    
    # 预算策略
    enable_token_monitoring: bool = True
    enable_token_optimization: bool = True
    token_optimization_threshold: float = 0.8
    
    # 预算分配
    system_tokens_ratio: float = 0.3  # 系统消息占30%
    conversation_tokens_ratio: float = 0.6  # 对话历史占60%
    tool_tokens_ratio: float = 0.1  # 工具结果占10%


@dataclass
class PerformanceOptimization:
    """性能优化配置"""
    # 并行执行
    enable_parallel_execution: bool = True
    max_concurrent_tools: int = 3
    parallel_execution_timeout: int = 30  # 秒
    
    # 缓存优化
    enable_tool_result_caching: bool = True
    tool_cache_size: int = 50
    tool_cache_ttl: int = 600  # 秒
    
    # 预取优化
    enable_context_prefetching: bool = True
    prefetch_strategy: str = "predictive"  # predictive, aggressive, conservative
    
    # 批处理优化
    enable_batch_processing: bool = True
    batch_size: int = 5
    batch_timeout: int = 10  # 秒


@dataclass
class MonitoringAndDebugging:
    """监控和调试配置"""
    # 日志配置
    enable_detailed_logging: bool = True
    log_level: str = "INFO"
    log_format: str = "detailed"  # detailed, compact, json
    
    # 指标收集
    enable_metrics_collection: bool = True
    metrics_retention_days: int = 7
    metrics_export_interval: int = 300  # 秒
    
    # 性能监控
    enable_performance_monitoring: bool = True
    performance_sampling_rate: float = 0.1  # 10%采样率
    performance_threshold_ms: int = 5000  # 5秒阈值
    
    # 调试功能
    enable_debug_mode: bool = False
    debug_tool_calls: bool = False
    debug_context_injection: bool = False


@dataclass
class AdvancedCoordinationConfig(CoordinationConfig):
    """高级协调配置"""
    # 递归控制
    recursion: RecursionControl = field(default_factory=RecursionControl)
    
    # 上下文管理
    context: ContextManagement = field(default_factory=ContextManagement)
    
    # Token 预算
    token_budget: TokenBudget = field(default_factory=TokenBudget)
    
    # 性能优化
    performance: PerformanceOptimization = field(default_factory=PerformanceOptimization)
    
    # 监控调试
    monitoring: MonitoringAndDebugging = field(default_factory=MonitoringAndDebugging)
    
    # 自定义回调
    custom_callbacks: List[Callable] = field(default_factory=list)


class CoordinationManager:
    """协调管理器"""
    
    def __init__(self, config: AdvancedCoordinationConfig):
        """
        Args:
            config: 协调配置
        """
        self.config = config
        self._metrics: Dict[str, Any] = {}
        self._callbacks: List[Callable] = []
        
        # 初始化监控
        if config.monitoring.enable_metrics_collection:
            self._init_metrics()
        
        # 初始化日志
        if config.monitoring.enable_detailed_logging:
            self._setup_logging()
    
    def _init_metrics(self):
        """初始化指标收集"""
        self._metrics = {
            "execution_count": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "tool_call_count": 0,
            "context_injection_count": 0,
            "recursion_depth_stats": {},
            "token_usage_stats": {},
            "error_count": 0,
            "success_rate": 0.0,
        }
        logger.info("📊 [CoordinationManager] 指标收集已启用")
    
    def _setup_logging(self):
        """设置日志"""
        # 配置日志格式
        if self.config.monitoring.log_format == "detailed":
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        elif self.config.monitoring.log_format == "compact":
            log_format = "%(levelname)s: %(message)s"
        else:  # json
            log_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
        
        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, self.config.monitoring.log_level))
        logger.info(f"📝 [CoordinationManager] 日志配置已启用: {self.config.monitoring.log_format}")
    
    def should_continue_recursion(
        self, 
        current_depth: int, 
        complexity_score: float,
        execution_time: float
    ) -> bool:
        """判断是否应该继续递归"""
        # 检查递归深度
        if current_depth >= self.config.recursion.max_recursion_depth:
            logger.warning(f"⚠️ 达到最大递归深度: {current_depth}")
            return False
        
        # 检查复杂度阈值
        if complexity_score > self.config.recursion.complexity_threshold:
            logger.warning(f"⚠️ 复杂度超过阈值: {complexity_score}")
            return False
        
        # 检查执行时间
        if execution_time > self.config.recursion.recursion_timeout:
            logger.warning(f"⚠️ 执行时间超过限制: {execution_time}s")
            return False
        
        return True
    
    def calculate_token_budget(self, iteration: int, total_iterations: int) -> Dict[str, int]:
        """计算 Token 预算分配"""
        budget = self.config.token_budget
        
        # 基础预算
        total_budget = budget.max_total_tokens
        reserve_tokens = int(total_budget * budget.token_reserve_ratio)
        available_tokens = total_budget - reserve_tokens
        
        # 根据迭代进度调整预算
        progress_ratio = iteration / total_iterations
        if progress_ratio > 0.8:  # 接近结束，减少预算
            available_tokens = int(available_tokens * 0.7)
        
        # 分配预算
        allocation = {
            "system": int(available_tokens * budget.system_tokens_ratio),
            "conversation": int(available_tokens * budget.conversation_tokens_ratio),
            "tools": int(available_tokens * budget.tool_tokens_ratio),
            "reserve": reserve_tokens,
            "total": total_budget
        }
        
        logger.debug(f"💰 Token 预算分配: {allocation}")
        return allocation
    
    def should_inject_context(self, iteration: int, stage: ExecutionStage) -> bool:
        """判断是否应该注入上下文"""
        context_config = self.config.context
        
        if not context_config.enable_dynamic_injection:
            return False
        
        # 检查注入频率
        if iteration % context_config.injection_frequency != 0:
            return False
        
        # 根据阶段调整注入策略
        if context_config.injection_strategy == "aggressive":
            return True
        elif context_config.injection_strategy == "conservative":
            return stage in [ExecutionStage.SCHEMA_DISCOVERY, ExecutionStage.SQL_GENERATION]
        else:  # adaptive
            return stage in [ExecutionStage.SCHEMA_DISCOVERY, ExecutionStage.SQL_GENERATION, ExecutionStage.SQL_VALIDATION]
    
    def optimize_performance(self, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """性能优化建议"""
        optimizations = {}
        
        perf_config = self.config.performance
        
        # 检查执行时间
        avg_time = current_metrics.get("average_execution_time", 0)
        if avg_time > self.config.monitoring.performance_threshold_ms:
            optimizations["enable_parallel_execution"] = True
            optimizations["reduce_tool_timeout"] = True
        
        # 检查工具调用频率
        tool_call_count = current_metrics.get("tool_call_count", 0)
        if tool_call_count > 20:
            optimizations["enable_tool_caching"] = True
            optimizations["batch_tool_calls"] = True
        
        # 检查上下文使用
        context_injection_count = current_metrics.get("context_injection_count", 0)
        if context_injection_count > 10:
            optimizations["optimize_context_injection"] = True
            optimizations["reduce_context_frequency"] = True
        
        return optimizations
    
    def record_metrics(self, metrics: Dict[str, Any]):
        """记录指标"""
        if not self.config.monitoring.enable_metrics_collection:
            return
        
        # 更新基础指标
        self._metrics["execution_count"] += 1
        self._metrics["total_execution_time"] += metrics.get("execution_time", 0)
        self._metrics["tool_call_count"] += metrics.get("tool_calls", 0)
        self._metrics["context_injection_count"] += metrics.get("context_injections", 0)
        
        # 计算平均值
        if self._metrics["execution_count"] > 0:
            self._metrics["average_execution_time"] = (
                self._metrics["total_execution_time"] / self._metrics["execution_count"]
            )
        
        # 记录递归深度统计
        depth = metrics.get("recursion_depth", 0)
        if depth not in self._metrics["recursion_depth_stats"]:
            self._metrics["recursion_depth_stats"][depth] = 0
        self._metrics["recursion_depth_stats"][depth] += 1
        
        # 记录 Token 使用统计
        token_usage = metrics.get("token_usage", {})
        for token_type, usage in token_usage.items():
            if token_type not in self._metrics["token_usage_stats"]:
                self._metrics["token_usage_stats"][token_type] = []
            self._metrics["token_usage_stats"][token_type].append(usage)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        if not self.config.monitoring.enable_metrics_collection:
            return {}
        
        summary = {
            "execution_count": self._metrics.get("execution_count", 0),
            "average_execution_time": self._metrics.get("average_execution_time", 0),
            "total_tool_calls": self._metrics.get("tool_call_count", 0),
            "total_context_injections": self._metrics.get("context_injection_count", 0),
            "recursion_depth_distribution": self._metrics.get("recursion_depth_stats", {}),
            "token_usage_average": {},
        }
        
        # 计算 Token 使用平均值
        for token_type, usage_list in self._metrics.get("token_usage_stats", {}).items():
            if usage_list:
                summary["token_usage_average"][token_type] = sum(usage_list) / len(usage_list)
        
        return summary
    
    def add_callback(self, callback: Callable):
        """添加回调函数"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """通知回调函数"""
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.warning(f"⚠️ 协调回调执行失败: {e}")


def create_default_coordination_config() -> AdvancedCoordinationConfig:
    """创建默认协调配置"""
    return AdvancedCoordinationConfig()


def create_high_performance_config() -> AdvancedCoordinationConfig:
    """创建高性能配置"""
    config = AdvancedCoordinationConfig()
    
    # 优化性能设置
    config.performance.enable_parallel_execution = True
    config.performance.max_concurrent_tools = 5
    config.performance.enable_tool_result_caching = True
    config.performance.enable_batch_processing = True
    
    # 优化 Token 预算
    config.token_budget.max_tokens_per_iteration = 6000
    config.token_budget.max_total_tokens = 20000
    
    # 优化上下文管理
    config.context.context_cache_size = 200
    config.context.enable_context_compression = True
    
    return config


def create_debug_config() -> AdvancedCoordinationConfig:
    """创建调试配置"""
    config = AdvancedCoordinationConfig()
    
    # 启用调试功能
    config.monitoring.enable_debug_mode = True
    config.monitoring.debug_tool_calls = True
    config.monitoring.debug_context_injection = True
    config.monitoring.enable_detailed_logging = True
    config.monitoring.log_level = "DEBUG"
    
    # 减少限制以便调试
    config.recursion.max_recursion_depth = 10
    config.recursion.recursion_timeout = 600
    
    return config


# 导出
__all__ = [
    "AdvancedCoordinationConfig",
    "CoordinationManager",
    "create_default_coordination_config",
    "create_high_performance_config", 
    "create_debug_config",
]