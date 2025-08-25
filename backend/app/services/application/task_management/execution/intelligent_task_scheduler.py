"""
Intelligent Task Scheduler

智能任务调度器 - 基于任务复杂度和系统负载进行智能调度
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List
import psutil
import time

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """任务复杂度级别"""
    LOW = "low"           # 简单任务，少于5个占位符
    MEDIUM = "medium"     # 中等任务，5-20个占位符
    HIGH = "high"         # 复杂任务，20-50个占位符
    VERY_HIGH = "very_high"  # 极复杂任务，超过50个占位符


class ExecutionPriority(Enum):
    """执行优先级"""
    URGENT = "urgent"      # 紧急任务，立即执行
    HIGH = "high"         # 高优先级，优先调度
    NORMAL = "normal"     # 正常优先级
    LOW = "low"           # 低优先级，空闲时执行


@dataclass
class SystemLoad:
    """系统负载信息"""
    cpu_usage: float
    memory_usage: float
    disk_io_usage: float
    network_io_usage: float
    active_tasks: int
    timestamp: datetime


@dataclass
class TaskComplexityAnalysis:
    """任务复杂度分析结果"""
    complexity_level: TaskComplexity
    placeholder_count: int
    estimated_execution_time: int  # 秒
    requires_agent_analysis: bool
    data_volume_estimate: str
    parallel_opportunities: int


@dataclass
class ExecutionStrategy:
    """执行策略"""
    execution_mode: str
    parallel_degree: int
    cache_strategy: str
    priority_level: ExecutionPriority
    estimated_duration: int
    max_retries: int = 3
    timeout: int = 3600


@dataclass
class TaskExecutionPlan:
    """任务执行计划"""
    task_id: int
    strategy: ExecutionStrategy
    scheduled_time: datetime
    resource_allocation: Dict[str, Any]
    dependencies: List[int]


class IntelligentTaskScheduler:
    """智能任务调度器"""
    
    def __init__(self):
        self.system_load_cache = None
        self.cache_ttl = 30  # 系统负载缓存30秒
        self.last_load_update = None
        
        # 调度历史统计
        self.scheduling_history = {}
        self.performance_stats = {}
    
    async def schedule_task(
        self, 
        task_id: int, 
        user_id: str, 
        task_context: Dict[str, Any]
    ) -> TaskExecutionPlan:
        """智能任务调度"""
        logger.info(f"开始智能调度任务 {task_id}")
        
        try:
            # 1. 分析任务复杂度
            complexity_analysis = await self._analyze_task_complexity(task_id, task_context)
            
            # 2. 评估系统负载
            system_load = await self._get_system_load()
            
            # 3. 选择最优执行策略
            strategy = await self._select_execution_strategy(
                complexity_analysis, 
                system_load,
                user_id
            )
            
            # 4. 计算调度时间
            scheduled_time = await self._calculate_schedule_time(
                complexity_analysis,
                system_load,
                strategy.priority_level
            )
            
            # 5. 分配资源
            resource_allocation = await self._allocate_resources(
                complexity_analysis,
                strategy
            )
            
            execution_plan = TaskExecutionPlan(
                task_id=task_id,
                strategy=strategy,
                scheduled_time=scheduled_time,
                resource_allocation=resource_allocation,
                dependencies=[]
            )
            
            # 6. 记录调度决策
            await self._record_scheduling_decision(task_id, execution_plan)
            
            logger.info(f"任务 {task_id} 调度完成，复杂度: {complexity_analysis.complexity_level.value}, "
                       f"策略: {strategy.execution_mode}, 并发度: {strategy.parallel_degree}")
            
            return execution_plan
            
        except Exception as e:
            logger.error(f"任务调度失败 - 任务ID: {task_id}: {e}")
            # 返回默认调度计划
            return await self._create_fallback_plan(task_id)
    
    async def _analyze_task_complexity(
        self, 
        task_id: int, 
        task_context: Dict[str, Any]
    ) -> TaskComplexityAnalysis:
        """分析任务复杂度"""
        
        # 从任务上下文中提取信息
        template_placeholders = task_context.get('placeholders', [])
        template_content = task_context.get('template_content', '')
        data_source_info = task_context.get('data_source', {})
        
        placeholder_count = len(template_placeholders)
        
        # 评估是否需要Agent分析
        requires_agent_analysis = any(
            placeholder.get('agent_analyzed') is False or 
            placeholder.get('generated_sql') is None
            for placeholder in template_placeholders
        )
        
        # 估算数据量
        estimated_rows = 0
        for placeholder in template_placeholders:
            if placeholder.get('data_volume_hint'):
                estimated_rows += placeholder.get('data_volume_hint', 1000)
            else:
                estimated_rows += 1000  # 默认估算
        
        data_volume_estimate = self._categorize_data_volume(estimated_rows)
        
        # 确定复杂度级别
        if placeholder_count <= 5 and not requires_agent_analysis:
            complexity_level = TaskComplexity.LOW
            estimated_time = 30 + placeholder_count * 5
            parallel_opportunities = 1
        elif placeholder_count <= 20:
            complexity_level = TaskComplexity.MEDIUM
            estimated_time = 60 + placeholder_count * 8
            parallel_opportunities = min(3, placeholder_count // 3)
        elif placeholder_count <= 50:
            complexity_level = TaskComplexity.HIGH
            estimated_time = 180 + placeholder_count * 12
            parallel_opportunities = min(5, placeholder_count // 5)
        else:
            complexity_level = TaskComplexity.VERY_HIGH
            estimated_time = 360 + placeholder_count * 15
            parallel_opportunities = min(8, placeholder_count // 8)
        
        # 如果需要Agent分析，增加估算时间
        if requires_agent_analysis:
            estimated_time += placeholder_count * 10
        
        return TaskComplexityAnalysis(
            complexity_level=complexity_level,
            placeholder_count=placeholder_count,
            estimated_execution_time=estimated_time,
            requires_agent_analysis=requires_agent_analysis,
            data_volume_estimate=data_volume_estimate,
            parallel_opportunities=parallel_opportunities
        )
    
    async def _get_system_load(self) -> SystemLoad:
        """获取系统负载信息"""
        
        # 检查缓存
        current_time = datetime.now()
        if (self.system_load_cache and self.last_load_update and 
            (current_time - self.last_load_update).seconds < self.cache_ttl):
            return self.system_load_cache
        
        # 收集系统指标
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()
        
        # 估算当前活跃任务数（通过进程计算）
        active_tasks = len([p for p in psutil.process_iter(['name']) 
                           if 'python' in p.info['name'].lower() or 'celery' in p.info['name'].lower()])
        
        system_load = SystemLoad(
            cpu_usage=cpu_usage,
            memory_usage=memory_info.percent,
            disk_io_usage=0,  # 简化计算
            network_io_usage=0,  # 简化计算
            active_tasks=active_tasks,
            timestamp=current_time
        )
        
        # 更新缓存
        self.system_load_cache = system_load
        self.last_load_update = current_time
        
        return system_load
    
    async def _select_execution_strategy(
        self,
        complexity_analysis: TaskComplexityAnalysis,
        system_load: SystemLoad,
        user_id: str
    ) -> ExecutionStrategy:
        """选择执行策略"""
        
        # 基础策略选择
        if complexity_analysis.complexity_level == TaskComplexity.LOW:
            base_parallel_degree = 1
            base_mode = "SMART_EXECUTION"
            cache_strategy = "BALANCED"
            priority = ExecutionPriority.NORMAL
            
        elif complexity_analysis.complexity_level == TaskComplexity.MEDIUM:
            base_parallel_degree = 2
            base_mode = "SMART_EXECUTION" 
            cache_strategy = "AGGRESSIVE"
            priority = ExecutionPriority.NORMAL
            
        elif complexity_analysis.complexity_level == TaskComplexity.HIGH:
            base_parallel_degree = 3
            base_mode = "FULL_PIPELINE"
            cache_strategy = "AGGRESSIVE"
            priority = ExecutionPriority.HIGH
            
        else:  # VERY_HIGH
            base_parallel_degree = 5
            base_mode = "FULL_PIPELINE"
            cache_strategy = "AGGRESSIVE"
            priority = ExecutionPriority.HIGH
        
        # 根据系统负载调整策略
        adjusted_parallel_degree = base_parallel_degree
        adjusted_mode = base_mode
        
        if system_load.cpu_usage > 80:
            # CPU压力大，降低并发度
            adjusted_parallel_degree = max(1, base_parallel_degree - 2)
            cache_strategy = "CACHE_FIRST"
            
        elif system_load.memory_usage > 85:
            # 内存压力大，使用缓存优先策略
            adjusted_mode = "CACHED_EXECUTION"
            cache_strategy = "CACHE_FIRST"
            
        elif system_load.cpu_usage < 30 and system_load.memory_usage < 50:
            # 系统负载低，可以增加并发度
            adjusted_parallel_degree = min(8, base_parallel_degree + 2)
        
        # 根据Agent分析需求调整
        if complexity_analysis.requires_agent_analysis and system_load.cpu_usage > 70:
            # Agent分析需要CPU资源，系统负载高时降级
            cache_strategy = "CACHE_FIRST"
            adjusted_parallel_degree = max(1, adjusted_parallel_degree - 1)
        
        return ExecutionStrategy(
            execution_mode=adjusted_mode,
            parallel_degree=adjusted_parallel_degree,
            cache_strategy=cache_strategy,
            priority_level=priority,
            estimated_duration=complexity_analysis.estimated_execution_time,
            max_retries=3,
            timeout=max(900, complexity_analysis.estimated_execution_time * 2)
        )
    
    async def _calculate_schedule_time(
        self,
        complexity_analysis: TaskComplexityAnalysis,
        system_load: SystemLoad,
        priority: ExecutionPriority
    ) -> datetime:
        """计算调度时间"""
        
        base_time = datetime.now()
        
        if priority == ExecutionPriority.URGENT:
            return base_time
        
        # 根据系统负载和优先级计算延迟
        delay_seconds = 0
        
        if system_load.cpu_usage > 90 or system_load.memory_usage > 90:
            # 系统高负载，延迟执行
            if priority == ExecutionPriority.LOW:
                delay_seconds = 300  # 5分钟
            elif priority == ExecutionPriority.NORMAL:
                delay_seconds = 60   # 1分钟
            # HIGH优先级立即执行
        
        elif system_load.active_tasks > 10:
            # 活跃任务太多，轻微延迟
            if priority == ExecutionPriority.LOW:
                delay_seconds = 120  # 2分钟
            elif priority == ExecutionPriority.NORMAL:
                delay_seconds = 30   # 30秒
        
        return base_time + timedelta(seconds=delay_seconds)
    
    async def _allocate_resources(
        self,
        complexity_analysis: TaskComplexityAnalysis,
        strategy: ExecutionStrategy
    ) -> Dict[str, Any]:
        """分配资源"""
        
        return {
            "cpu_cores": strategy.parallel_degree,
            "memory_limit": f"{min(2048, 512 * strategy.parallel_degree)}MB",
            "disk_space": "1GB",
            "network_bandwidth": "100Mbps",
            "cache_size": f"{min(1024, 256 * strategy.parallel_degree)}MB",
            "agent_workers": min(2, strategy.parallel_degree),
            "sql_workers": strategy.parallel_degree,
            "report_workers": 1
        }
    
    async def _record_scheduling_decision(
        self,
        task_id: int,
        execution_plan: TaskExecutionPlan
    ):
        """记录调度决策"""
        
        self.scheduling_history[task_id] = {
            "scheduled_at": datetime.now(),
            "complexity": execution_plan.strategy.execution_mode,
            "parallel_degree": execution_plan.strategy.parallel_degree,
            "estimated_duration": execution_plan.strategy.estimated_duration,
            "priority": execution_plan.strategy.priority_level.value
        }
    
    async def _create_fallback_plan(self, task_id: int) -> TaskExecutionPlan:
        """创建降级执行计划"""
        
        fallback_strategy = ExecutionStrategy(
            execution_mode="SMART_EXECUTION",
            parallel_degree=1,
            cache_strategy="BALANCED",
            priority_level=ExecutionPriority.NORMAL,
            estimated_duration=300,
            max_retries=2,
            timeout=1800
        )
        
        return TaskExecutionPlan(
            task_id=task_id,
            strategy=fallback_strategy,
            scheduled_time=datetime.now(),
            resource_allocation={"mode": "fallback"},
            dependencies=[]
        )
    
    def _categorize_data_volume(self, estimated_rows: int) -> str:
        """数据量分类"""
        if estimated_rows < 1000:
            return "small"
        elif estimated_rows < 100000:
            return "medium"
        elif estimated_rows < 1000000:
            return "large"
        else:
            return "very_large"
    
    async def get_scheduling_stats(self) -> Dict[str, Any]:
        """获取调度统计信息"""
        
        total_scheduled = len(self.scheduling_history)
        if total_scheduled == 0:
            return {"total_tasks": 0, "message": "No tasks scheduled yet"}
        
        # 计算平均执行时间等统计信息
        avg_parallel_degree = sum(
            task["parallel_degree"] for task in self.scheduling_history.values()
        ) / total_scheduled
        
        complexity_distribution = {}
        for task in self.scheduling_history.values():
            complexity = task["complexity"]
            complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1
        
        return {
            "total_tasks": total_scheduled,
            "average_parallel_degree": round(avg_parallel_degree, 2),
            "complexity_distribution": complexity_distribution,
            "last_updated": datetime.now().isoformat()
        }