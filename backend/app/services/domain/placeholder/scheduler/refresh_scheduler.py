"""
刷新调度器

管理占位符数据的定时刷新和更新
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import croniter
from collections import defaultdict

logger = logging.getLogger(__name__)

class RefreshStrategy(Enum):
    """刷新策略"""
    FIXED_INTERVAL = "fixed_interval"  # 固定间隔
    CRON_EXPRESSION = "cron_expression"  # Cron表达式
    DATA_DRIVEN = "data_driven"  # 数据驱动
    ADAPTIVE = "adaptive"  # 自适应

class RefreshStatus(Enum):
    """刷新状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class RefreshJob:
    """刷新任务"""
    job_id: str
    placeholder_id: str
    strategy: RefreshStrategy
    configuration: Dict[str, Any]
    next_run_time: datetime
    last_run_time: Optional[datetime]
    status: RefreshStatus
    enabled: bool
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    execution_stats: Dict[str, Any] = None

class RefreshScheduler:
    """刷新调度器"""
    
    def __init__(self, 
                 check_interval: int = 60,  # 检查间隔（秒）
                 max_concurrent_jobs: int = 10):
        """
        初始化刷新调度器
        
        Args:
            check_interval: 检查间隔
            max_concurrent_jobs: 最大并发任务数
        """
        self.check_interval = check_interval
        self.max_concurrent_jobs = max_concurrent_jobs
        
        # 任务管理
        self._jobs: Dict[str, RefreshJob] = {}
        self._running_jobs: Set[str] = set()
        
        # 处理器映射
        self._refresh_handlers: Dict[str, Callable] = {}
        
        # 统计信息
        self._stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'cancelled_jobs': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0
        }
        
        self._lock = asyncio.Lock()
        self._running = False
        self._scheduler_task = None
        
        logger.info("刷新调度器初始化完成")
    
    async def start(self):
        """启动调度器"""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("刷新调度器已启动")
    
    async def stop(self):
        """停止调度器"""
        if not self._running:
            return
        
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # 等待所有运行中的任务完成
        while self._running_jobs:
            await asyncio.sleep(1)
        
        logger.info("刷新调度器已停止")
    
    async def register_refresh_handler(self, 
                                     handler_name: str, 
                                     handler_func: Callable) -> bool:
        """注册刷新处理器"""
        try:
            self._refresh_handlers[handler_name] = handler_func
            logger.info(f"注册刷新处理器: {handler_name}")
            return True
        except Exception as e:
            logger.error(f"注册刷新处理器失败: {e}")
            return False
    
    async def create_refresh_job(self,
                               placeholder_id: str,
                               strategy: RefreshStrategy,
                               configuration: Dict[str, Any],
                               enabled: bool = True) -> str:
        """创建刷新任务"""
        async with self._lock:
            try:
                job_id = f"refresh_{placeholder_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # 计算下次运行时间
                next_run_time = await self._calculate_next_run_time(strategy, configuration)
                
                job = RefreshJob(
                    job_id=job_id,
                    placeholder_id=placeholder_id,
                    strategy=strategy,
                    configuration=configuration,
                    next_run_time=next_run_time,
                    last_run_time=None,
                    status=RefreshStatus.PENDING,
                    enabled=enabled,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    execution_stats={}
                )
                
                self._jobs[job_id] = job
                self._stats['total_jobs'] += 1
                
                logger.info(f"创建刷新任务: {job_id} for {placeholder_id}")
                return job_id
                
            except Exception as e:
                logger.error(f"创建刷新任务失败: {e}")
                raise
    
    async def update_refresh_job(self,
                               job_id: str,
                               configuration: Optional[Dict[str, Any]] = None,
                               enabled: Optional[bool] = None) -> bool:
        """更新刷新任务"""
        async with self._lock:
            try:
                if job_id not in self._jobs:
                    return False
                
                job = self._jobs[job_id]
                
                if configuration is not None:
                    job.configuration = configuration
                    # 重新计算下次运行时间
                    job.next_run_time = await self._calculate_next_run_time(
                        job.strategy, job.configuration
                    )
                
                if enabled is not None:
                    job.enabled = enabled
                
                job.updated_at = datetime.now()
                
                logger.info(f"更新刷新任务: {job_id}")
                return True
                
            except Exception as e:
                logger.error(f"更新刷新任务失败: {e}")
                return False
    
    async def delete_refresh_job(self, job_id: str) -> bool:
        """删除刷新任务"""
        async with self._lock:
            try:
                if job_id not in self._jobs:
                    return False
                
                # 如果任务正在运行，先取消
                if job_id in self._running_jobs:
                    await self._cancel_job(job_id)
                
                del self._jobs[job_id]
                logger.info(f"删除刷新任务: {job_id}")
                return True
                
            except Exception as e:
                logger.error(f"删除刷新任务失败: {e}")
                return False
    
    async def trigger_immediate_refresh(self, job_id: str) -> bool:
        """触发立即刷新"""
        async with self._lock:
            try:
                if job_id not in self._jobs:
                    return False
                
                job = self._jobs[job_id]
                if not job.enabled:
                    return False
                
                # 设置为立即执行
                job.next_run_time = datetime.now()
                job.updated_at = datetime.now()
                
                logger.info(f"触发立即刷新: {job_id}")
                return True
                
            except Exception as e:
                logger.error(f"触发立即刷新失败: {e}")
                return False
    
    async def _scheduler_loop(self):
        """调度器主循环"""
        while self._running:
            try:
                await self._check_and_execute_jobs()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"调度器循环出错: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_and_execute_jobs(self):
        """检查并执行任务"""
        current_time = datetime.now()
        jobs_to_execute = []
        
        async with self._lock:
            # 检查需要执行的任务
            for job in self._jobs.values():
                if (job.enabled and 
                    job.status in [RefreshStatus.PENDING, RefreshStatus.FAILED] and
                    job.next_run_time <= current_time and
                    job.job_id not in self._running_jobs and
                    len(self._running_jobs) < self.max_concurrent_jobs):
                    
                    jobs_to_execute.append(job)
            
            # 标记任务为运行中
            for job in jobs_to_execute:
                job.status = RefreshStatus.RUNNING
                self._running_jobs.add(job.job_id)
        
        # 异步执行任务
        for job in jobs_to_execute:
            asyncio.create_task(self._execute_refresh_job(job))
    
    async def _execute_refresh_job(self, job: RefreshJob):
        """执行刷新任务"""
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行刷新任务: {job.job_id}")
            
            # 调用刷新处理器
            success = await self._call_refresh_handlers(job)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            async with self._lock:
                if success:
                    job.status = RefreshStatus.COMPLETED
                    job.retry_count = 0
                    job.error_message = None
                    self._stats['completed_jobs'] += 1
                else:
                    await self._handle_job_failure(job)
                
                # 更新执行统计
                job.last_run_time = start_time
                job.updated_at = datetime.now()
                job.execution_stats = {
                    'last_execution_time': execution_time,
                    'last_execution_status': job.status.value,
                    'total_executions': job.execution_stats.get('total_executions', 0) + 1
                }
                
                # 计算下次运行时间
                if job.status == RefreshStatus.COMPLETED:
                    job.next_run_time = await self._calculate_next_run_time(
                        job.strategy, job.configuration, job.last_run_time
                    )
                
                # 更新全局统计
                self._stats['total_execution_time'] += execution_time
                executed_jobs = self._stats['completed_jobs'] + self._stats['failed_jobs']
                if executed_jobs > 0:
                    self._stats['avg_execution_time'] = self._stats['total_execution_time'] / executed_jobs
                
                # 从运行中任务集合移除
                self._running_jobs.discard(job.job_id)
            
            logger.info(f"刷新任务执行完成: {job.job_id} - {job.status.value}")
            
        except Exception as e:
            logger.error(f"执行刷新任务失败: {job.job_id} - {e}")
            
            async with self._lock:
                job.error_message = str(e)
                await self._handle_job_failure(job)
                self._running_jobs.discard(job.job_id)
    
    async def _call_refresh_handlers(self, job: RefreshJob) -> bool:
        """调用刷新处理器"""
        try:
            # 默认刷新处理器
            if 'default' in self._refresh_handlers:
                handler = self._refresh_handlers['default']
                
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(job)
                else:
                    result = handler(job)
                
                return bool(result)
            
            # 占位符特定处理器
            placeholder_handler = f"placeholder_{job.placeholder_id}"
            if placeholder_handler in self._refresh_handlers:
                handler = self._refresh_handlers[placeholder_handler]
                
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(job)
                else:
                    result = handler(job)
                
                return bool(result)
            
            logger.warning(f"没有找到适合的刷新处理器: {job.job_id}")
            return False
            
        except Exception as e:
            logger.error(f"调用刷新处理器失败: {e}")
            return False
    
    async def _handle_job_failure(self, job: RefreshJob):
        """处理任务失败"""
        job.retry_count += 1
        
        if job.retry_count <= job.max_retries:
            # 重试
            job.status = RefreshStatus.PENDING
            # 延迟重试时间
            retry_delay = min(300, 60 * (2 ** (job.retry_count - 1)))  # 指数退避，最大5分钟
            job.next_run_time = datetime.now() + timedelta(seconds=retry_delay)
            
            logger.info(f"刷新任务将重试: {job.job_id} (第{job.retry_count}次)")
        else:
            # 达到最大重试次数
            job.status = RefreshStatus.FAILED
            self._stats['failed_jobs'] += 1
            
            logger.error(f"刷新任务失败: {job.job_id} - 达到最大重试次数")
    
    async def _cancel_job(self, job_id: str):
        """取消任务"""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = RefreshStatus.CANCELLED
            job.updated_at = datetime.now()
            self._stats['cancelled_jobs'] += 1
            
            if job_id in self._running_jobs:
                self._running_jobs.discard(job_id)
    
    async def _calculate_next_run_time(self, 
                                     strategy: RefreshStrategy, 
                                     configuration: Dict[str, Any],
                                     last_run_time: Optional[datetime] = None) -> datetime:
        """计算下次运行时间"""
        current_time = last_run_time or datetime.now()
        
        try:
            if strategy == RefreshStrategy.FIXED_INTERVAL:
                interval_seconds = configuration.get('interval_seconds', 3600)
                return current_time + timedelta(seconds=interval_seconds)
            
            elif strategy == RefreshStrategy.CRON_EXPRESSION:
                cron_expr = configuration.get('cron_expression', '0 * * * *')
                cron = croniter.croniter(cron_expr, current_time)
                return cron.get_next(datetime)
            
            elif strategy == RefreshStrategy.DATA_DRIVEN:
                # 基于数据变化频率确定下次刷新时间
                change_frequency = configuration.get('change_frequency', 'medium')
                
                if change_frequency == 'high':
                    interval = 300  # 5分钟
                elif change_frequency == 'medium':
                    interval = 1800  # 30分钟
                else:  # low
                    interval = 7200  # 2小时
                
                return current_time + timedelta(seconds=interval)
            
            elif strategy == RefreshStrategy.ADAPTIVE:
                # 自适应策略，基于历史执行情况调整
                base_interval = configuration.get('base_interval_seconds', 3600)
                
                # 这里可以基于历史性能数据进行调整
                # 简化实现，使用基础间隔
                return current_time + timedelta(seconds=base_interval)
            
            else:
                # 默认1小时间隔
                return current_time + timedelta(hours=1)
                
        except Exception as e:
            logger.error(f"计算下次运行时间失败: {e}")
            # 默认1小时后
            return current_time + timedelta(hours=1)
    
    async def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        async with self._lock:
            if job_id not in self._jobs:
                return None
            
            job = self._jobs[job_id]
            return {
                'job_id': job.job_id,
                'placeholder_id': job.placeholder_id,
                'strategy': job.strategy.value,
                'configuration': job.configuration,
                'next_run_time': job.next_run_time.isoformat(),
                'last_run_time': job.last_run_time.isoformat() if job.last_run_time else None,
                'status': job.status.value,
                'enabled': job.enabled,
                'created_at': job.created_at.isoformat(),
                'updated_at': job.updated_at.isoformat(),
                'retry_count': job.retry_count,
                'max_retries': job.max_retries,
                'error_message': job.error_message,
                'execution_stats': job.execution_stats or {},
                'is_running': job.job_id in self._running_jobs
            }
    
    async def get_jobs_by_placeholder(self, placeholder_id: str) -> List[Dict[str, Any]]:
        """获取特定占位符的所有任务"""
        async with self._lock:
            jobs = []
            for job in self._jobs.values():
                if job.placeholder_id == placeholder_id:
                    job_info = await self.get_job_info(job.job_id)
                    if job_info:
                        jobs.append(job_info)
            
            return sorted(jobs, key=lambda j: j['created_at'])
    
    async def get_all_jobs(self, 
                          status: Optional[RefreshStatus] = None,
                          enabled_only: bool = False) -> List[Dict[str, Any]]:
        """获取所有任务"""
        async with self._lock:
            jobs = []
            
            for job in self._jobs.values():
                if status and job.status != status:
                    continue
                
                if enabled_only and not job.enabled:
                    continue
                
                job_info = await self.get_job_info(job.job_id)
                if job_info:
                    jobs.append(job_info)
            
            return sorted(jobs, key=lambda j: j['next_run_time'])
    
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """获取调度器统计"""
        async with self._lock:
            # 按状态统计任务
            status_counts = defaultdict(int)
            for job in self._jobs.values():
                status_counts[job.status.value] += 1
            
            # 按策略统计任务
            strategy_counts = defaultdict(int)
            for job in self._jobs.values():
                strategy_counts[job.strategy.value] += 1
            
            return {
                'total_jobs': len(self._jobs),
                'running_jobs': len(self._running_jobs),
                'enabled_jobs': len([j for j in self._jobs.values() if j.enabled]),
                'status_distribution': dict(status_counts),
                'strategy_distribution': dict(strategy_counts),
                'execution_stats': self._stats.copy(),
                'registered_handlers': len(self._refresh_handlers),
                'is_running': self._running
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = await self.get_scheduler_stats()
            
            health_status = "healthy"
            issues = []
            
            # 检查调度器运行状态
            if not self._running:
                issues.append("调度器未运行")
                health_status = "error"
            
            # 检查失败任务比例
            total_executed = stats['execution_stats']['completed_jobs'] + stats['execution_stats']['failed_jobs']
            if total_executed > 0:
                failure_rate = stats['execution_stats']['failed_jobs'] / total_executed
                if failure_rate > 0.2:  # 失败率超过20%
                    issues.append(f"任务失败率过高: {failure_rate:.2%}")
                    health_status = "warning"
            
            # 检查运行中任务数量
            if stats['running_jobs'] >= self.max_concurrent_jobs:
                issues.append("并发任务数达到上限")
                health_status = "warning"
            
            # 检查处理器注册情况
            if stats['registered_handlers'] == 0:
                issues.append("没有注册的刷新处理器")
                health_status = "warning"
            
            return {
                'status': health_status,
                'issues': issues,
                'stats': stats
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'issues': [f"健康检查失败: {str(e)}"],
                'stats': {}
            }
    
    async def shutdown(self):
        """关闭刷新调度器"""
        await self.stop()
        logger.info("刷新调度器已关闭")

# 全局刷新调度器实例
_refresh_scheduler: Optional[RefreshScheduler] = None

def get_refresh_scheduler() -> RefreshScheduler:
    """获取全局刷新调度器实例"""
    global _refresh_scheduler
    if _refresh_scheduler is None:
        _refresh_scheduler = RefreshScheduler()
    return _refresh_scheduler

def initialize_refresh_scheduler(**kwargs) -> RefreshScheduler:
    """初始化全局刷新调度器"""
    global _refresh_scheduler
    _refresh_scheduler = RefreshScheduler(**kwargs)
    return _refresh_scheduler