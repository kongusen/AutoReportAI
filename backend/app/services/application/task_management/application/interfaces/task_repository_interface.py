"""
Task Repository Interface

任务仓储接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ...domain.entities.task_entity import TaskEntity


class TaskRepositoryInterface(ABC):
    """任务仓储接口"""
    
    @abstractmethod
    async def generate_task_id(self) -> str:
        """生成任务ID"""
        pass
    
    @abstractmethod
    async def save(self, task: TaskEntity) -> TaskEntity:
        """保存任务"""
        pass
    
    @abstractmethod
    async def get_by_id(self, task_id: str) -> Optional[TaskEntity]:
        """根据ID获取任务"""
        pass
    
    @abstractmethod
    async def get_by_user(self, user_id: str, 
                         filters: Dict[str, Any] = None,
                         pagination: Dict[str, Any] = None) -> List[TaskEntity]:
        """获取用户的任务列表"""
        pass
    
    @abstractmethod
    async def get_active_tasks(self) -> List[TaskEntity]:
        """获取所有活跃任务"""
        pass
    
    @abstractmethod
    async def get_scheduled_tasks(self) -> List[TaskEntity]:
        """获取所有需要调度的任务"""
        pass
    
    @abstractmethod
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[TaskEntity]:
        """根据条件查找任务"""
        pass
    
    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        pass
    
    @abstractmethod
    async def get_task_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取任务统计信息"""
        pass