"""
Task Execution Interface

任务执行接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from ...domain.entities.task_entity import TaskEntity, TaskExecution


class TaskExecutionInterface(ABC):
    """任务执行接口"""
    
    @abstractmethod
    async def execute(self, task: TaskEntity, execution: TaskExecution,
                     context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task: 任务实体
            execution: 执行记录
            context: 执行上下文
            
        Returns:
            执行结果 {"success": bool, "data": Any, "error": str}
        """
        pass
    
    @abstractmethod
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        取消执行
        
        Args:
            execution_id: 执行ID
            
        Returns:
            是否成功取消
        """
        pass
    
    @abstractmethod
    async def get_execution_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            执行状态信息
        """
        pass
    
    @abstractmethod
    async def get_execution_progress(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行进度
        
        Args:
            execution_id: 执行ID
            
        Returns:
            进度信息
        """
        pass
    
    @abstractmethod
    async def get_execution_logs(self, execution_id: str) -> List[Dict[str, Any]]:
        """
        获取执行日志
        
        Args:
            execution_id: 执行ID
            
        Returns:
            日志列表
        """
        pass