"""
Task Notification Interface

任务通知接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class TaskNotificationInterface(ABC):
    """任务通知接口"""
    
    @abstractmethod
    async def send_task_created(self, task_id: str, task_name: str, owner_id: str):
        """发送任务创建通知"""
        pass
    
    @abstractmethod
    async def send_task_updated(self, task_id: str, task_name: str, owner_id: str):
        """发送任务更新通知"""
        pass
    
    @abstractmethod
    async def send_task_deleted(self, task_id: str, task_name: str, owner_id: str):
        """发送任务删除通知"""
        pass
    
    @abstractmethod
    async def send_task_activated(self, task_id: str, task_name: str, owner_id: str):
        """发送任务激活通知"""
        pass
    
    @abstractmethod
    async def send_task_deactivated(self, task_id: str, task_name: str, owner_id: str):
        """发送任务停用通知"""
        pass
    
    @abstractmethod
    async def send_execution_started(self, task_id: str, execution_id: str, owner_id: str):
        """发送执行开始通知"""
        pass
    
    @abstractmethod
    async def send_execution_completed(self, task_id: str, execution_id: str,
                                     result_data: Dict[str, Any], owner_id: str):
        """发送执行完成通知"""
        pass
    
    @abstractmethod
    async def send_execution_failed(self, task_id: str, execution_id: str,
                                  error_message: str, owner_id: str):
        """发送执行失败通知"""
        pass
    
    @abstractmethod
    async def send_execution_cancelled(self, task_id: str, execution_id: str, owner_id: str):
        """发送执行取消通知"""
        pass
    
    @abstractmethod
    async def send_progress_update(self, task_id: str, execution_id: str,
                                 progress_data: Dict[str, Any], owner_id: str):
        """发送进度更新通知"""
        pass