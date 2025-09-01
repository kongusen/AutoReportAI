"""
Infrastructure层AI工具监控器

负责监控工具的性能、使用情况和健康状态

核心职责：
- 监控工具执行性能和统计
- 检测工具异常和故障
- 提供工具使用分析和报告
- 为上层Agent提供监控服务

技术职责：
- 纯技术实现，不包含业务逻辑
- 可被Application/Domain层的Agent使用
- 提供稳定的监控和统计服务
"""

import logging
import time
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ToolHealthStatus(Enum):
    """工具健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ToolExecutionMetric:
    """工具执行指标"""
    tool_name: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    input_size: int = 0
    output_size: int = 0
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    user_id: str = "system"
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolHealthCheck:
    """工具健康检查结果"""
    tool_name: str
    status: ToolHealthStatus
    last_check: datetime
    response_time: Optional[float] = None
    success_rate: float = 0.0
    error_count: int = 0
    warning_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """告警"""
    alert_id: str
    tool_name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolsMonitor:
    """
    Infrastructure层AI工具监控器
    
    核心职责：
    1. 监控工具执行性能和统计
    2. 检测工具异常和生成告警
    3. 提供工具健康检查和分析
    4. 管理监控数据和历史记录
    
    技术定位：
    - Infrastructure层技术基础设施
    - 为上层Agent提供监控能力
    - 不包含具体业务逻辑
    """
    
    def __init__(
        self,
        max_metrics_history: int = 10000,
        max_alerts_history: int = 1000,
        health_check_interval: int = 300,  # 5分钟
        alert_thresholds: Optional[Dict[str, Any]] = None
    ):
        self.max_metrics_history = max_metrics_history
        self.max_alerts_history = max_alerts_history
        self.health_check_interval = health_check_interval
        
        # 监控数据存储
        self.execution_metrics: deque = deque(maxlen=max_metrics_history)
        self.tool_metrics: Dict[str, List[ToolExecutionMetric]] = defaultdict(list)
        self.health_checks: Dict[str, ToolHealthCheck] = {}
        self.alerts: deque = deque(maxlen=max_alerts_history)
        
        # 统计数据
        self.tool_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "min_execution_time": float('inf'),
            "max_execution_time": 0.0,
            "last_execution": None,
            "error_rate": 0.0,
            "success_rate": 0.0
        })
        
        # 告警阈值
        self.alert_thresholds = alert_thresholds or {
            "max_execution_time": 30.0,  # 30秒
            "max_error_rate": 0.1,       # 10%
            "min_success_rate": 0.9,     # 90%
            "max_consecutive_failures": 3
        }
        
        # 监控状态
        self.monitoring_started = datetime.utcnow()
        self.last_health_check = None
        
        logger.info("AI工具监控器初始化完成")
    
    def start_execution(self, tool_name: str, user_id: str = "system", **context) -> str:
        """
        开始工具执行监控
        
        Args:
            tool_name: 工具名称
            user_id: 用户ID
            **context: 额外上下文
            
        Returns:
            执行ID
        """
        execution_id = f"{tool_name}_{int(time.time() * 1000)}_{hash(user_id) % 10000}"
        
        metric = ToolExecutionMetric(
            tool_name=tool_name,
            execution_id=execution_id,
            start_time=datetime.utcnow(),
            user_id=user_id,
            context=context
        )
        
        self.execution_metrics.append(metric)
        self.tool_metrics[tool_name].append(metric)
        
        # 限制单个工具的历史记录数量
        if len(self.tool_metrics[tool_name]) > 1000:
            self.tool_metrics[tool_name] = self.tool_metrics[tool_name][-1000:]
        
        logger.debug(f"开始监控工具执行: {tool_name} ({execution_id})")
        return execution_id
    
    def end_execution(
        self,
        execution_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        input_size: int = 0,
        output_size: int = 0,
        **metadata
    ):
        """
        结束工具执行监控
        
        Args:
            execution_id: 执行ID
            success: 是否成功
            error_message: 错误消息
            input_size: 输入大小
            output_size: 输出大小
            **metadata: 额外元数据
        """
        # 查找对应的执行指标
        metric = None
        for m in reversed(self.execution_metrics):
            if m.execution_id == execution_id:
                metric = m
                break
        
        if not metric:
            logger.warning(f"未找到执行指标: {execution_id}")
            return
        
        # 更新执行指标
        metric.end_time = datetime.utcnow()
        metric.execution_time = (metric.end_time - metric.start_time).total_seconds()
        metric.success = success
        metric.error_message = error_message
        metric.input_size = input_size
        metric.output_size = output_size
        metric.memory_usage = metadata.get('memory_usage')
        metric.cpu_usage = metadata.get('cpu_usage')
        
        # 更新统计数据
        self._update_tool_stats(metric)
        
        # 检查告警条件
        self._check_alerts(metric)
        
        logger.debug(f"结束监控工具执行: {metric.tool_name} ({execution_id}), 用时: {metric.execution_time:.2f}s")
    
    def _update_tool_stats(self, metric: ToolExecutionMetric):
        """更新工具统计数据"""
        tool_name = metric.tool_name
        stats = self.tool_stats[tool_name]
        
        stats["total_executions"] += 1
        stats["last_execution"] = metric.end_time
        
        if metric.success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
        
        if metric.execution_time is not None:
            stats["total_execution_time"] += metric.execution_time
            stats["average_execution_time"] = (
                stats["total_execution_time"] / stats["total_executions"]
            )
            stats["min_execution_time"] = min(
                stats["min_execution_time"], metric.execution_time
            )
            stats["max_execution_time"] = max(
                stats["max_execution_time"], metric.execution_time
            )
        
        # 计算成功率和错误率
        if stats["total_executions"] > 0:
            stats["success_rate"] = (
                stats["successful_executions"] / stats["total_executions"]
            )
            stats["error_rate"] = (
                stats["failed_executions"] / stats["total_executions"]
            )
    
    def _check_alerts(self, metric: ToolExecutionMetric):
        """检查告警条件"""
        tool_name = metric.tool_name
        stats = self.tool_stats[tool_name]
        
        alerts_to_create = []
        
        # 检查执行时间告警
        if (metric.execution_time and 
            metric.execution_time > self.alert_thresholds["max_execution_time"]):
            alerts_to_create.append({
                "level": AlertLevel.WARNING,
                "message": f"工具 {tool_name} 执行时间过长: {metric.execution_time:.2f}s",
                "metadata": {"execution_time": metric.execution_time}
            })
        
        # 检查错误率告警
        if (stats["total_executions"] >= 10 and 
            stats["error_rate"] > self.alert_thresholds["max_error_rate"]):
            alerts_to_create.append({
                "level": AlertLevel.ERROR,
                "message": f"工具 {tool_name} 错误率过高: {stats['error_rate']:.2%}",
                "metadata": {"error_rate": stats["error_rate"]}
            })
        
        # 检查成功率告警
        if (stats["total_executions"] >= 10 and 
            stats["success_rate"] < self.alert_thresholds["min_success_rate"]):
            alerts_to_create.append({
                "level": AlertLevel.ERROR,
                "message": f"工具 {tool_name} 成功率过低: {stats['success_rate']:.2%}",
                "metadata": {"success_rate": stats["success_rate"]}
            })
        
        # 检查连续失败告警
        recent_failures = 0
        for m in reversed(list(self.tool_metrics[tool_name])[-10:]):
            if not m.success:
                recent_failures += 1
            else:
                break
        
        if recent_failures >= self.alert_thresholds["max_consecutive_failures"]:
            alerts_to_create.append({
                "level": AlertLevel.CRITICAL,
                "message": f"工具 {tool_name} 连续失败 {recent_failures} 次",
                "metadata": {"consecutive_failures": recent_failures}
            })
        
        # 创建告警
        for alert_data in alerts_to_create:
            self._create_alert(tool_name, **alert_data)
    
    def _create_alert(
        self,
        tool_name: str,
        level: AlertLevel,
        message: str,
        metadata: Dict[str, Any] = None
    ):
        """创建告警"""
        alert_id = f"alert_{tool_name}_{int(time.time() * 1000)}"
        
        alert = Alert(
            alert_id=alert_id,
            tool_name=tool_name,
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        
        logger.log(
            logging.ERROR if level in [AlertLevel.ERROR, AlertLevel.CRITICAL] else logging.WARNING,
            f"工具告警: {message}"
        )
    
    def perform_health_check(self, tool_name: str, health_check_func: Optional[Callable] = None) -> ToolHealthCheck:
        """
        执行工具健康检查
        
        Args:
            tool_name: 工具名称
            health_check_func: 自定义健康检查函数
            
        Returns:
            健康检查结果
        """
        start_time = time.time()
        
        try:
            if health_check_func:
                # 执行自定义健康检查
                result = health_check_func()
                status = ToolHealthStatus.HEALTHY if result else ToolHealthStatus.ERROR
                details = {"custom_check": result}
            else:
                # 基于统计数据的健康检查
                stats = self.tool_stats.get(tool_name, {})
                
                if not stats or stats["total_executions"] == 0:
                    status = ToolHealthStatus.UNKNOWN
                    details = {"reason": "no_execution_data"}
                elif stats["error_rate"] > 0.5:
                    status = ToolHealthStatus.ERROR
                    details = {"reason": "high_error_rate", "error_rate": stats["error_rate"]}
                elif stats["error_rate"] > 0.2:
                    status = ToolHealthStatus.WARNING
                    details = {"reason": "elevated_error_rate", "error_rate": stats["error_rate"]}
                else:
                    status = ToolHealthStatus.HEALTHY
                    details = {"reason": "normal_operation"}
            
            response_time = time.time() - start_time
            
            health_check = ToolHealthCheck(
                tool_name=tool_name,
                status=status,
                last_check=datetime.utcnow(),
                response_time=response_time,
                success_rate=self.tool_stats[tool_name].get("success_rate", 0.0),
                error_count=self.tool_stats[tool_name].get("failed_executions", 0),
                details=details
            )
            
            self.health_checks[tool_name] = health_check
            
            logger.debug(f"工具健康检查完成: {tool_name} - {status.value}")
            return health_check
            
        except Exception as e:
            logger.error(f"工具健康检查失败: {tool_name}, 错误: {e}")
            
            health_check = ToolHealthCheck(
                tool_name=tool_name,
                status=ToolHealthStatus.ERROR,
                last_check=datetime.utcnow(),
                response_time=time.time() - start_time,
                details={"error": str(e)}
            )
            
            self.health_checks[tool_name] = health_check
            return health_check
    
    def perform_all_health_checks(self) -> Dict[str, ToolHealthCheck]:
        """执行所有工具的健康检查"""
        results = {}
        
        for tool_name in self.tool_stats.keys():
            results[tool_name] = self.perform_health_check(tool_name)
        
        self.last_health_check = datetime.utcnow()
        
        logger.info(f"完成所有工具健康检查，检查了 {len(results)} 个工具")
        return results
    
    def get_tool_statistics(self, tool_name: str) -> Dict[str, Any]:
        """获取工具统计信息"""
        stats = self.tool_stats.get(tool_name, {})
        health_check = self.health_checks.get(tool_name)
        
        # 获取最近的执行指标
        recent_metrics = []
        for metric in reversed(list(self.tool_metrics.get(tool_name, [])[-10:])):
            recent_metrics.append({
                "execution_id": metric.execution_id,
                "start_time": metric.start_time.isoformat(),
                "execution_time": metric.execution_time,
                "success": metric.success,
                "error_message": metric.error_message,
                "user_id": metric.user_id
            })
        
        # 获取最近的告警
        recent_alerts = []
        for alert in reversed(list(self.alerts)):
            if alert.tool_name == tool_name:
                recent_alerts.append({
                    "alert_id": alert.alert_id,
                    "level": alert.level.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "resolved": alert.resolved
                })
                if len(recent_alerts) >= 5:
                    break
        
        return {
            "tool_name": tool_name,
            "statistics": stats,
            "health_status": health_check.status.value if health_check else "unknown",
            "last_health_check": health_check.last_check.isoformat() if health_check else None,
            "recent_executions": recent_metrics,
            "recent_alerts": recent_alerts
        }
    
    def get_overall_statistics(self) -> Dict[str, Any]:
        """获取总体统计信息"""
        uptime = (datetime.utcnow() - self.monitoring_started).total_seconds()
        
        total_executions = sum(stats["total_executions"] for stats in self.tool_stats.values())
        total_successful = sum(stats["successful_executions"] for stats in self.tool_stats.values())
        total_failed = sum(stats["failed_executions"] for stats in self.tool_stats.values())
        
        # 健康状态统计
        health_status_counts = defaultdict(int)
        for health_check in self.health_checks.values():
            health_status_counts[health_check.status.value] += 1
        
        # 告警统计
        alert_level_counts = defaultdict(int)
        active_alerts = 0
        for alert in self.alerts:
            alert_level_counts[alert.level.value] += 1
            if not alert.resolved:
                active_alerts += 1
        
        return {
            "monitoring_uptime": uptime,
            "total_tools_monitored": len(self.tool_stats),
            "total_executions": total_executions,
            "successful_executions": total_successful,
            "failed_executions": total_failed,
            "overall_success_rate": total_successful / max(total_executions, 1),
            "overall_error_rate": total_failed / max(total_executions, 1),
            "health_status_counts": dict(health_status_counts),
            "alert_level_counts": dict(alert_level_counts),
            "active_alerts": active_alerts,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "metrics_history_size": len(self.execution_metrics),
            "alerts_history_size": len(self.alerts)
        }
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃的告警"""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                logger.info(f"告警已解决: {alert_id}")
                return True
        
        return False
    
    def clear_old_data(self, days: int = 7):
        """清理旧数据"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # 清理旧的执行指标
        original_metrics_count = len(self.execution_metrics)
        self.execution_metrics = deque(
            [m for m in self.execution_metrics if m.start_time > cutoff_time],
            maxlen=self.max_metrics_history
        )
        
        # 清理工具指标
        for tool_name, metrics in self.tool_metrics.items():
            self.tool_metrics[tool_name] = [
                m for m in metrics if m.start_time > cutoff_time
            ]
        
        # 清理旧的告警
        original_alerts_count = len(self.alerts)
        self.alerts = deque(
            [a for a in self.alerts if a.timestamp > cutoff_time],
            maxlen=self.max_alerts_history
        )
        
        cleaned_metrics = original_metrics_count - len(self.execution_metrics)
        cleaned_alerts = original_alerts_count - len(self.alerts)
        
        logger.info(f"清理完成 - 指标: {cleaned_metrics}, 告警: {cleaned_alerts}")
    
    def export_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """导出监控指标"""
        if tool_name:
            # 导出特定工具的指标
            metrics = [
                {
                    "execution_id": m.execution_id,
                    "start_time": m.start_time.isoformat(),
                    "end_time": m.end_time.isoformat() if m.end_time else None,
                    "execution_time": m.execution_time,
                    "success": m.success,
                    "error_message": m.error_message,
                    "input_size": m.input_size,
                    "output_size": m.output_size,
                    "user_id": m.user_id,
                    "context": m.context
                }
                for m in self.tool_metrics.get(tool_name, [])
            ]
            
            return {
                "tool_name": tool_name,
                "metrics": metrics,
                "statistics": self.get_tool_statistics(tool_name)
            }
        else:
            # 导出所有指标
            all_metrics = [
                {
                    "tool_name": m.tool_name,
                    "execution_id": m.execution_id,
                    "start_time": m.start_time.isoformat(),
                    "end_time": m.end_time.isoformat() if m.end_time else None,
                    "execution_time": m.execution_time,
                    "success": m.success,
                    "error_message": m.error_message,
                    "input_size": m.input_size,
                    "output_size": m.output_size,
                    "user_id": m.user_id,
                    "context": m.context
                }
                for m in self.execution_metrics
            ]
            
            return {
                "metrics": all_metrics,
                "statistics": self.get_overall_statistics()
            }