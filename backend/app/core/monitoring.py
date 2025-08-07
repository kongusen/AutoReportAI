"""
系统监控模块

基于设计文档实现的完整监控和错误处理系统
包括性能指标收集、错误追踪、任务监控和告警机制
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.notification.notification_service import NotificationService

logger = logging.getLogger(__name__)


class TaskMetrics:
    """任务指标收集器"""

    def __init__(self):
        self.metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_processing_time": 0.0,
            "placeholder_analysis_time": {},
            "data_query_time": {},
            "report_generation_time": 0.0
        }
        self.processing_times = []
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

    async def record_task_completion(
        self,
        task_id: int,
        duration: float,
        status: str,
        step_times: Optional[Dict[str, float]] = None
    ):
        """记录任务完成情况"""
        try:
            # 更新本地指标
            self.metrics["total_tasks"] += 1
            
            if status == "completed":
                self.metrics["completed_tasks"] += 1
                self.processing_times.append(duration)
                
                # 更新平均处理时间
                if self.processing_times:
                    self.metrics["avg_processing_time"] = sum(self.processing_times) / len(self.processing_times)
                
                # 记录各步骤时间
                if step_times:
                    for step, step_time in step_times.items():
                        if step not in self.metrics:
                            self.metrics[step] = []
                        self.metrics[step].append(step_time)
                        
            elif status == "failed":
                self.metrics["failed_tasks"] += 1

            # 同步到Redis
            await self._sync_metrics_to_redis(task_id, status, duration, step_times)
            
        except Exception as e:
            logger.error(f"记录任务指标失败: {str(e)}")

    async def _sync_metrics_to_redis(
        self,
        task_id: int,
        status: str,
        duration: float,
        step_times: Optional[Dict[str, float]]
    ):
        """同步指标到Redis"""
        try:
            # 更新计数器
            await self.redis_client.incr("task_metrics:total_tasks")
            
            if status == "completed":
                await self.redis_client.incr("task_metrics:completed_tasks")
                
                # 更新平均处理时间
                await self.redis_client.lpush(
                    "task_metrics:processing_times",
                    str(duration)
                )
                # 只保留最新100条记录用于计算平均值
                await self.redis_client.ltrim("task_metrics:processing_times", 0, 99)
                
            elif status == "failed":
                await self.redis_client.incr("task_metrics:failed_tasks")
            
            # 记录详细任务信息
            task_record = {
                "task_id": task_id,
                "status": status,
                "duration": duration,
                "step_times": step_times or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.lpush(
                "task_metrics:detailed_history",
                json.dumps(task_record)
            )
            
            # 保持最新1000条详细记录
            await self.redis_client.ltrim("task_metrics:detailed_history", 0, 999)
            
            # 设置过期时间（24小时）
            expire_time = 86400
            await self.redis_client.expire("task_metrics:total_tasks", expire_time)
            await self.redis_client.expire("task_metrics:completed_tasks", expire_time)
            await self.redis_client.expire("task_metrics:failed_tasks", expire_time)
            
        except Exception as e:
            logger.error(f"同步指标到Redis失败: {str(e)}")

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        try:
            # 从Redis获取最新数据
            total_tasks = await self.redis_client.get("task_metrics:total_tasks") or "0"
            completed_tasks = await self.redis_client.get("task_metrics:completed_tasks") or "0"
            failed_tasks = await self.redis_client.get("task_metrics:failed_tasks") or "0"
            
            total_count = int(total_tasks)
            completed_count = int(completed_tasks)
            failed_count = int(failed_tasks)
            
            # 计算平均处理时间
            processing_times = await self.redis_client.lrange("task_metrics:processing_times", 0, -1)
            avg_time = 0.0
            if processing_times:
                times = [float(t) for t in processing_times]
                avg_time = sum(times) / len(times)
            
            # 计算失败率
            failure_rate = failed_count / total_count if total_count > 0 else 0
            success_rate = completed_count / total_count if total_count > 0 else 0
            
            return {
                "total_requests": total_count,
                "successful_requests": completed_count,
                "failed_requests": failed_count,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "average_processing_time": avg_time,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取指标摘要失败: {str(e)}")
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate": 0,
                "failure_rate": 0,
                "average_processing_time": 0,
                "error": str(e)
            }


class TaskErrorHandler:
    """任务错误处理器"""

    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        self.notification_service = NotificationService()

    async def handle_task_error(
        self,
        task_id: int,
        error: Exception,
        task_type: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """处理任务错误"""
        try:
            error_info = {
                "task_id": task_id,
                "task_type": task_type,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
                "timestamp": datetime.utcnow().isoformat()
            }

            # 记录错误日志
            logger.error(f"任务执行失败: {error_info}")

            # 存储到Redis错误历史
            await self.redis_client.lpush(
                "task_errors:history",
                json.dumps(error_info)
            )
            
            # 保持最新500条错误记录
            await self.redis_client.ltrim("task_errors:history", 0, 499)

            # 更新错误统计
            await self.redis_client.incr(f"task_errors:count:{task_type}")
            await self.redis_client.incr("task_errors:total_count")

            # 发送错误通知
            await self.notification_service.record_task_metrics(
                task_id=task_id,
                status="failed",
                error=str(error)
            )

            # 根据错误类型决定是否需要立即告警
            if self._is_critical_error(error, task_type):
                await self.notification_service.send_system_alert(
                    level="error",
                    title=f"严重任务错误: {task_type}",
                    message=f"任务 {task_id} 发生严重错误: {str(error)}"
                )

        except Exception as e:
            logger.error(f"处理任务错误失败: {str(e)}")

    def _is_critical_error(self, error: Exception, task_type: str) -> bool:
        """判断是否为严重错误"""
        critical_errors = [
            "DatabaseError",
            "ConnectionError", 
            "AuthenticationError",
            "MemoryError",
            "TimeoutError"
        ]
        
        error_type = type(error).__name__
        return error_type in critical_errors

    async def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        try:
            # 获取总错误数
            total_errors = await self.redis_client.get("task_errors:total_count") or "0"
            
            # 获取各类型错误数
            error_types = {}
            keys = await self.redis_client.keys("task_errors:count:*")
            
            for key in keys:
                task_type = key.split(":")[-1]
                count = await self.redis_client.get(key) or "0"
                error_types[task_type] = int(count)
            
            # 获取最近的错误记录
            recent_errors = await self.redis_client.lrange("task_errors:history", 0, 9)
            parsed_errors = []
            
            for error_json in recent_errors:
                try:
                    parsed_errors.append(json.loads(error_json))
                except json.JSONDecodeError:
                    continue
            
            return {
                "total_errors": int(total_errors),
                "error_types": error_types,
                "recent_errors": parsed_errors,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取错误统计失败: {str(e)}")
            return {
                "total_errors": 0,
                "error_types": {},
                "recent_errors": [],
                "error": str(e)
            }


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.notification_service = NotificationService()
        self.task_metrics = TaskMetrics()
        self.error_handler = TaskErrorHandler()

    async def check_system_health(self):
        """检查系统健康状态"""
        try:
            # 检查任务失败率
            await self._check_task_failure_rate()
            
            # 检查平均处理时间
            await self._check_processing_time()
            
            # 检查错误频率
            await self._check_error_frequency()
            
            # 检查资源使用情况
            await self._check_resource_usage()
            
        except Exception as e:
            logger.error(f"系统健康检查失败: {str(e)}")

    async def _check_task_failure_rate(self):
        """检查任务失败率"""
        try:
            metrics = await self.task_metrics.get_metrics_summary()
            failure_rate = metrics.get("failure_rate", 0)
            
            if failure_rate > 0.1:  # 失败率超过10%
                await self.notification_service.send_system_alert(
                    level="warning",
                    title="任务失败率过高",
                    message=f"当前任务失败率为 {failure_rate:.2%}，超过告警阈值10%"
                )
            elif failure_rate > 0.2:  # 失败率超过20%
                await self.notification_service.send_system_alert(
                    level="error",
                    title="任务失败率严重过高",
                    message=f"当前任务失败率为 {failure_rate:.2%}，系统可能存在严重问题"
                )
                
        except Exception as e:
            logger.error(f"检查任务失败率失败: {str(e)}")

    async def _check_processing_time(self):
        """检查平均处理时间"""
        try:
            metrics = await self.task_metrics.get_metrics_summary()
            avg_time = metrics.get("average_processing_time", 0)
            
            # 如果平均处理时间超过10分钟，发出警告
            if avg_time > 600:  # 10分钟
                await self.notification_service.send_system_alert(
                    level="warning",
                    title="任务处理时间过长",
                    message=f"当前平均处理时间为 {avg_time:.2f}秒，可能影响用户体验"
                )
                
        except Exception as e:
            logger.error(f"检查处理时间失败: {str(e)}")

    async def _check_error_frequency(self):
        """检查错误频率"""
        try:
            error_stats = await self.error_handler.get_error_statistics()
            recent_errors = error_stats.get("recent_errors", [])
            
            # 检查最近1小时内的错误数量
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_error_count = 0
            
            for error in recent_errors:
                try:
                    error_time = datetime.fromisoformat(error.get("timestamp", ""))
                    if error_time > one_hour_ago:
                        recent_error_count += 1
                except (ValueError, TypeError):
                    continue
            
            # 如果1小时内错误超过50次，发出告警
            if recent_error_count > 50:
                await self.notification_service.send_system_alert(
                    level="warning",
                    title="错误频率过高",
                    message=f"最近1小时内发生了 {recent_error_count} 次错误"
                )
                
        except Exception as e:
            logger.error(f"检查错误频率失败: {str(e)}")

    async def _check_resource_usage(self):
        """检查资源使用情况"""
        try:
            import psutil
            
            # 检查CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                await self.notification_service.send_system_alert(
                    level="warning",
                    title="CPU使用率过高",
                    message=f"当前CPU使用率为 {cpu_percent:.1f}%"
                )
            
            # 检查内存使用率
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                await self.notification_service.send_system_alert(
                    level="warning",
                    title="内存使用率过高",
                    message=f"当前内存使用率为 {memory.percent:.1f}%"
                )
            
            # 检查磁盘使用率
            disk = psutil.disk_usage('/')
            if disk.percent > 85:
                await self.notification_service.send_system_alert(
                    level="warning",
                    title="磁盘空间不足",
                    message=f"当前磁盘使用率为 {disk.percent:.1f}%"
                )
                
        except ImportError:
            logger.warning("psutil未安装，跳过资源使用情况检查")
        except Exception as e:
            logger.error(f"检查资源使用情况失败: {str(e)}")


class MonitoringService:
    """监控服务主类"""

    def __init__(self):
        self.task_metrics = TaskMetrics()
        self.error_handler = TaskErrorHandler()
        self.alert_manager = AlertManager()
        self.is_monitoring = False

    async def start_monitoring(self):
        """启动监控服务"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        logger.info("启动系统监控服务")
        
        # 启动定期健康检查
        asyncio.create_task(self._periodic_health_check())

    async def stop_monitoring(self):
        """停止监控服务"""
        self.is_monitoring = False
        logger.info("停止系统监控服务")

    async def _periodic_health_check(self):
        """定期健康检查"""
        while self.is_monitoring:
            try:
                await self.alert_manager.check_system_health()
                # 每5分钟检查一次
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"定期健康检查失败: {str(e)}")
                await asyncio.sleep(60)  # 出错时等待1分钟后重试

    async def record_task_event(
        self,
        task_id: int,
        event_type: str,
        status: str,
        duration: Optional[float] = None,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """记录任务事件"""
        try:
            if status in ["completed", "failed"]:
                await self.task_metrics.record_task_completion(
                    task_id=task_id,
                    duration=duration or 0,
                    status=status
                )
            
            if error:
                await self.error_handler.handle_task_error(
                    task_id=task_id,
                    error=error,
                    task_type=event_type,
                    context=context
                )
                
        except Exception as e:
            logger.error(f"记录任务事件失败: {str(e)}")

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态摘要"""
        try:
            metrics_summary = await self.task_metrics.get_metrics_summary()
            error_stats = await self.error_handler.get_error_statistics()
            
            return {
                "metrics": metrics_summary,
                "errors": error_stats,
                "monitoring_status": "active" if self.is_monitoring else "inactive",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {str(e)}")
            return {
                "metrics": {},
                "errors": {},
                "monitoring_status": "error",
                "error": str(e)
            }


# 全局监控服务实例
monitoring_service = MonitoringService()