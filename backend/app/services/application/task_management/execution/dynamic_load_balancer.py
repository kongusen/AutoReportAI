"""
Dynamic Load Balancer

动态负载均衡器 - 智能任务分发和工作负载管理
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import random

logger = logging.getLogger(__name__)


class WorkerType(Enum):
    """工作器类型"""
    AGENT_ANALYSIS = "agent_analysis"
    SQL_EXECUTION = "sql_execution" 
    REPORT_GENERATION = "report_generation"
    ETL_PROCESSING = "etl_processing"


class TaskType(Enum):
    """任务类型"""
    PLACEHOLDER_ANALYSIS = "placeholder_analysis"
    SQL_QUERY = "sql_query"
    DATA_EXTRACTION = "data_extraction"
    REPORT_COMPILE = "report_compile"
    CACHE_UPDATE = "cache_update"


@dataclass
class WorkerInfo:
    """工作器信息"""
    worker_id: str
    worker_type: WorkerType
    current_load: int
    max_capacity: int
    avg_execution_time: float
    success_rate: float
    last_heartbeat: datetime
    is_active: bool = True


@dataclass
class TaskAllocation:
    """任务分配信息"""
    task_id: str
    subtask_id: str
    worker_id: str
    worker_type: WorkerType
    priority: int
    estimated_duration: int
    allocated_at: datetime


@dataclass
class LoadBalancingResult:
    """负载均衡结果"""
    allocations: List[TaskAllocation]
    total_estimated_time: int
    load_balance_score: float
    rejected_tasks: List[str]


class WorkerPool:
    """工作器池"""
    
    def __init__(self, pool_type: WorkerType, initial_size: int = 4):
        self.pool_type = pool_type
        self.workers: Dict[str, WorkerInfo] = {}
        self.task_queue: List[Dict[str, Any]] = []
        self.max_queue_size = 100
        
        # 初始化工作器
        for i in range(initial_size):
            worker_id = f"{pool_type.value}_{i:03d}"
            self.workers[worker_id] = WorkerInfo(
                worker_id=worker_id,
                worker_type=pool_type,
                current_load=0,
                max_capacity=self._get_default_capacity(pool_type),
                avg_execution_time=self._get_default_exec_time(pool_type),
                success_rate=0.95,
                last_heartbeat=datetime.now(),
                is_active=True
            )
    
    def _get_default_capacity(self, worker_type: WorkerType) -> int:
        """获取默认容量"""
        capacity_map = {
            WorkerType.AGENT_ANALYSIS: 2,  # Agent分析比较消耗资源
            WorkerType.SQL_EXECUTION: 5,   # SQL执行可以并发更多
            WorkerType.REPORT_GENERATION: 1, # 报告生成通常单线程
            WorkerType.ETL_PROCESSING: 3   # ETL处理中等并发
        }
        return capacity_map.get(worker_type, 3)
    
    def _get_default_exec_time(self, worker_type: WorkerType) -> float:
        """获取默认执行时间（秒）"""
        time_map = {
            WorkerType.AGENT_ANALYSIS: 15.0,
            WorkerType.SQL_EXECUTION: 3.0,
            WorkerType.REPORT_GENERATION: 30.0,
            WorkerType.ETL_PROCESSING: 8.0
        }
        return time_map.get(worker_type, 10.0)
    
    def get_available_workers(self) -> List[WorkerInfo]:
        """获取可用工作器"""
        return [
            worker for worker in self.workers.values()
            if worker.is_active and worker.current_load < worker.max_capacity
        ]
    
    def allocate_task(self, task_info: Dict[str, Any]) -> Optional[WorkerInfo]:
        """分配任务到最优工作器"""
        available_workers = self.get_available_workers()
        
        if not available_workers:
            return None
        
        # 选择负载最低且性能最好的工作器
        best_worker = min(
            available_workers,
            key=lambda w: (
                w.current_load / w.max_capacity,  # 负载率
                -w.success_rate,  # 成功率（负值用于升序）
                w.avg_execution_time  # 平均执行时间
            )
        )
        
        # 更新工作器负载
        best_worker.current_load += 1
        return best_worker
    
    def release_task(self, worker_id: str, execution_time: float, success: bool):
        """释放任务，更新工作器统计"""
        if worker_id in self.workers:
            worker = self.workers[worker_id]
            worker.current_load = max(0, worker.current_load - 1)
            
            # 更新性能统计
            alpha = 0.1  # 平滑因子
            worker.avg_execution_time = (
                (1 - alpha) * worker.avg_execution_time + 
                alpha * execution_time
            )
            
            if success:
                worker.success_rate = (
                    (1 - alpha) * worker.success_rate + alpha * 1.0
                )
            else:
                worker.success_rate = (
                    (1 - alpha) * worker.success_rate + alpha * 0.0
                )
            
            worker.last_heartbeat = datetime.now()


class DynamicLoadBalancer:
    """动态负载均衡器"""
    
    def __init__(self):
        # 初始化工作器池
        self.worker_pools = {
            WorkerType.AGENT_ANALYSIS: WorkerPool(WorkerType.AGENT_ANALYSIS, 4),
            WorkerType.SQL_EXECUTION: WorkerPool(WorkerType.SQL_EXECUTION, 6),
            WorkerType.REPORT_GENERATION: WorkerPool(WorkerType.REPORT_GENERATION, 2),
            WorkerType.ETL_PROCESSING: WorkerPool(WorkerType.ETL_PROCESSING, 4)
        }
        
        # 任务分发历史
        self.allocation_history: List[TaskAllocation] = []
        self.performance_metrics = {}
        
        # 自适应参数
        self.load_threshold = 0.8
        self.auto_scaling_enabled = True
    
    async def distribute_task(
        self, 
        main_task_id: int, 
        subtasks: List[Dict[str, Any]]
    ) -> LoadBalancingResult:
        """智能任务分发"""
        
        logger.info(f"开始分发任务 {main_task_id}，包含 {len(subtasks)} 个子任务")
        
        try:
            allocations = []
            rejected_tasks = []
            
            # 按优先级排序子任务
            sorted_subtasks = sorted(
                subtasks, 
                key=lambda t: t.get('priority', 5), 
                reverse=True
            )
            
            for subtask in sorted_subtasks:
                allocation = await self._allocate_subtask(main_task_id, subtask)
                
                if allocation:
                    allocations.append(allocation)
                else:
                    rejected_tasks.append(subtask['subtask_id'])
                    logger.warning(f"子任务 {subtask['subtask_id']} 分配失败，所有工作器都忙")
            
            # 计算总体估算时间和负载均衡分数
            total_estimated_time = self._calculate_total_time(allocations)
            balance_score = self._calculate_balance_score(allocations)
            
            result = LoadBalancingResult(
                allocations=allocations,
                total_estimated_time=total_estimated_time,
                load_balance_score=balance_score,
                rejected_tasks=rejected_tasks
            )
            
            # 记录分配结果
            self.allocation_history.extend(allocations)
            await self._update_performance_metrics(result)
            
            logger.info(f"任务分发完成 - 成功分配: {len(allocations)}, "
                       f"拒绝: {len(rejected_tasks)}, 负载均衡分数: {balance_score:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"任务分发失败: {e}")
            return LoadBalancingResult(
                allocations=[],
                total_estimated_time=0,
                load_balance_score=0.0,
                rejected_tasks=[st['subtask_id'] for st in subtasks]
            )
    
    async def _allocate_subtask(
        self, 
        main_task_id: int, 
        subtask: Dict[str, Any]
    ) -> Optional[TaskAllocation]:
        """分配单个子任务"""
        
        task_type = TaskType(subtask.get('type', 'sql_query'))
        
        # 根据任务类型选择工作器池
        worker_type = self._map_task_to_worker_type(task_type)
        pool = self.worker_pools[worker_type]
        
        # 尝试分配工作器
        worker = pool.allocate_task(subtask)
        
        if not worker:
            # 尝试自动扩容
            if self.auto_scaling_enabled:
                await self._try_auto_scaling(worker_type)
                worker = pool.allocate_task(subtask)
        
        if not worker:
            return None
        
        # 创建分配记录
        allocation = TaskAllocation(
            task_id=str(main_task_id),
            subtask_id=subtask['subtask_id'],
            worker_id=worker.worker_id,
            worker_type=worker.worker_type,
            priority=subtask.get('priority', 5),
            estimated_duration=subtask.get('estimated_duration', int(worker.avg_execution_time)),
            allocated_at=datetime.now()
        )
        
        return allocation
    
    def _map_task_to_worker_type(self, task_type: TaskType) -> WorkerType:
        """映射任务类型到工作器类型"""
        mapping = {
            TaskType.PLACEHOLDER_ANALYSIS: WorkerType.AGENT_ANALYSIS,
            TaskType.SQL_QUERY: WorkerType.SQL_EXECUTION,
            TaskType.DATA_EXTRACTION: WorkerType.ETL_PROCESSING,
            TaskType.REPORT_COMPILE: WorkerType.REPORT_GENERATION,
            TaskType.CACHE_UPDATE: WorkerType.SQL_EXECUTION
        }
        return mapping.get(task_type, WorkerType.SQL_EXECUTION)
    
    async def _try_auto_scaling(self, worker_type: WorkerType):
        """尝试自动扩容"""
        pool = self.worker_pools[worker_type]
        
        # 检查当前负载
        total_capacity = sum(w.max_capacity for w in pool.workers.values() if w.is_active)
        current_load = sum(w.current_load for w in pool.workers.values() if w.is_active)
        
        load_ratio = current_load / max(1, total_capacity)
        
        if load_ratio > self.load_threshold and len(pool.workers) < 20:
            # 添加新工作器
            worker_id = f"{worker_type.value}_{len(pool.workers):03d}"
            new_worker = WorkerInfo(
                worker_id=worker_id,
                worker_type=worker_type,
                current_load=0,
                max_capacity=pool._get_default_capacity(worker_type),
                avg_execution_time=pool._get_default_exec_time(worker_type),
                success_rate=0.95,
                last_heartbeat=datetime.now(),
                is_active=True
            )
            pool.workers[worker_id] = new_worker
            
            logger.info(f"自动扩容：为 {worker_type.value} 池添加工作器 {worker_id}")
    
    def _calculate_total_time(self, allocations: List[TaskAllocation]) -> int:
        """计算总体估算时间（并行执行的最长时间）"""
        if not allocations:
            return 0
        
        # 按工作器分组，计算每个工作器的总时间
        worker_times = {}
        for allocation in allocations:
            worker_id = allocation.worker_id
            worker_times[worker_id] = worker_times.get(worker_id, 0) + allocation.estimated_duration
        
        # 返回最长的工作器执行时间（并行执行）
        return max(worker_times.values()) if worker_times else 0
    
    def _calculate_balance_score(self, allocations: List[TaskAllocation]) -> float:
        """计算负载均衡分数（0-1，越高越好）"""
        if not allocations:
            return 1.0
        
        # 计算每个工作器的负载
        worker_loads = {}
        for allocation in allocations:
            worker_id = allocation.worker_id
            worker_loads[worker_id] = worker_loads.get(worker_id, 0) + 1
        
        if len(worker_loads) <= 1:
            return 1.0 if len(worker_loads) == 1 else 0.0
        
        # 计算负载方差，方差越小，均衡性越好
        loads = list(worker_loads.values())
        avg_load = sum(loads) / len(loads)
        variance = sum((load - avg_load) ** 2 for load in loads) / len(loads)
        
        # 将方差转换为0-1分数（方差越小，分数越高）
        max_possible_variance = (len(allocations)) ** 2 / 4  # 最大可能方差的近似
        balance_score = max(0, 1 - variance / max(1, max_possible_variance))
        
        return min(1.0, balance_score)
    
    async def _update_performance_metrics(self, result: LoadBalancingResult):
        """更新性能指标"""
        current_time = datetime.now()
        
        self.performance_metrics[current_time] = {
            "total_allocations": len(result.allocations),
            "rejected_tasks": len(result.rejected_tasks),
            "balance_score": result.load_balance_score,
            "estimated_time": result.total_estimated_time
        }
        
        # 保留最近24小时的指标
        cutoff_time = current_time - timedelta(hours=24)
        self.performance_metrics = {
            time: metrics for time, metrics in self.performance_metrics.items()
            if time > cutoff_time
        }
    
    async def complete_task(
        self, 
        allocation: TaskAllocation, 
        execution_time: float, 
        success: bool
    ):
        """完成任务，更新工作器状态"""
        
        pool = self.worker_pools[allocation.worker_type]
        pool.release_task(allocation.worker_id, execution_time, success)
        
        logger.debug(f"任务完成 - Worker: {allocation.worker_id}, "
                    f"执行时间: {execution_time:.2f}s, 成功: {success}")
    
    async def get_load_statistics(self) -> Dict[str, Any]:
        """获取负载统计信息"""
        
        stats = {
            "worker_pools": {},
            "total_allocations": len(self.allocation_history),
            "performance_metrics": {}
        }
        
        # 工作器池统计
        for worker_type, pool in self.worker_pools.items():
            active_workers = [w for w in pool.workers.values() if w.is_active]
            total_capacity = sum(w.max_capacity for w in active_workers)
            current_load = sum(w.current_load for w in active_workers)
            
            stats["worker_pools"][worker_type.value] = {
                "active_workers": len(active_workers),
                "total_capacity": total_capacity,
                "current_load": current_load,
                "load_ratio": current_load / max(1, total_capacity),
                "avg_success_rate": sum(w.success_rate for w in active_workers) / max(1, len(active_workers))
            }
        
        # 性能指标统计
        if self.performance_metrics:
            recent_metrics = list(self.performance_metrics.values())[-10:]  # 最近10次
            stats["performance_metrics"] = {
                "avg_balance_score": sum(m["balance_score"] for m in recent_metrics) / len(recent_metrics),
                "avg_rejection_rate": sum(m["rejected_tasks"] for m in recent_metrics) / sum(m["total_allocations"] + m["rejected_tasks"] for m in recent_metrics),
                "recent_allocations": len(recent_metrics)
            }
        
        return stats
    
    async def rebalance_workers(self):
        """重新平衡工作器"""
        
        logger.info("开始重新平衡工作器")
        
        for worker_type, pool in self.worker_pools.items():
            # 清理不活跃的工作器
            inactive_workers = [
                worker_id for worker_id, worker in pool.workers.items()
                if not worker.is_active or 
                (datetime.now() - worker.last_heartbeat).seconds > 300
            ]
            
            for worker_id in inactive_workers:
                del pool.workers[worker_id]
                logger.info(f"移除不活跃工作器: {worker_id}")
            
            # 检查是否需要调整池大小
            active_count = len([w for w in pool.workers.values() if w.is_active])
            if active_count < 2:  # 最少保持2个工作器
                await self._try_auto_scaling(worker_type)
        
        logger.info("工作器重新平衡完成")