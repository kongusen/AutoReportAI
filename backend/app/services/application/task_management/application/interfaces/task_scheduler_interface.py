"""
Task Scheduler Interface

任务调度器接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...domain.entities.task_entity import ScheduleConfig


class TaskSchedulerInterface(ABC):
    """任务调度器接口"""
    
    @abstractmethod
    async def schedule_task(self, task_id: str, schedule_config: ScheduleConfig):
        """
        调度任务
        
        Args:
            task_id: 任务ID
            schedule_config: 调度配置
        """
        pass
    
    @abstractmethod
    async def unschedule_task(self, task_id: str) -> bool:
        """
        取消任务调度
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        pass
    
    @abstractmethod
    async def reschedule_task(self, task_id: str, schedule_config: ScheduleConfig):
        """
        重新调度任务
        
        Args:
            task_id: 任务ID
            schedule_config: 新的调度配置
        """
        pass
    
    @abstractmethod
    async def get_next_run_time(self, task_id: str) -> Optional[datetime]:
        """
        获取下次运行时间
        
        Args:
            task_id: 任务ID
            
        Returns:
            下次运行时间
        """
        pass
    
    @abstractmethod
    async def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有已调度的任务信息
        
        Returns:
            调度任务列表
        """
        pass
    
    @abstractmethod
    async def is_task_scheduled(self, task_id: str) -> bool:
        """
        检查任务是否已调度
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否已调度
        """
        pass
    
    @abstractmethod
    async def pause_scheduler(self):
        """暂停调度器"""
        pass
    
    @abstractmethod
    async def resume_scheduler(self):
        """恢复调度器"""
        pass
    
    @abstractmethod
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        pass