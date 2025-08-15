"""
Task状态管理器
负责Task状态跟踪、状态转换和进度管理
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.task import Task, TaskExecution, TaskStatus, AgentWorkflowType
from app.crud.crud_task import crud_task
from app.crud.crud_task_execution import crud_task_execution

logger = logging.getLogger(__name__)


class TaskStatusTransition:
    """任务状态转换规则"""
    
    VALID_TRANSITIONS = {
        TaskStatus.PENDING: [TaskStatus.PROCESSING, TaskStatus.CANCELLED],
        TaskStatus.PROCESSING: [
            TaskStatus.AGENT_ORCHESTRATING, 
            TaskStatus.GENERATING, 
            TaskStatus.COMPLETED, 
            TaskStatus.FAILED, 
            TaskStatus.CANCELLED
        ],
        TaskStatus.AGENT_ORCHESTRATING: [
            TaskStatus.GENERATING, 
            TaskStatus.COMPLETED, 
            TaskStatus.FAILED, 
            TaskStatus.CANCELLED
        ],
        TaskStatus.GENERATING: [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
        TaskStatus.COMPLETED: [TaskStatus.PENDING],  # 可以重新执行
        TaskStatus.FAILED: [TaskStatus.PENDING, TaskStatus.PROCESSING],  # 可以重试
        TaskStatus.CANCELLED: [TaskStatus.PENDING]  # 可以重新执行
    }
    
    @classmethod
    def is_valid_transition(cls, from_status: TaskStatus, to_status: TaskStatus) -> bool:
        """检查状态转换是否有效"""
        return to_status in cls.VALID_TRANSITIONS.get(from_status, [])
    
    @classmethod
    def get_valid_next_statuses(cls, current_status: TaskStatus) -> List[TaskStatus]:
        """获取当前状态的有效下一步状态"""
        return cls.VALID_TRANSITIONS.get(current_status, [])


class TaskStatusManager:
    """任务状态管理器"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        
    async def initialize(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("TaskStatusManager Redis连接初始化成功")
        except Exception as e:
            logger.error(f"TaskStatusManager Redis连接初始化失败: {e}")
            self.redis_client = None
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def update_task_status(
        self,
        db: Session,
        task_id: int,
        new_status: TaskStatus,
        progress_percentage: Optional[int] = None,
        current_step: Optional[str] = None,
        error_details: Optional[str] = None,
        execution_id: Optional[int] = None
    ) -> bool:
        """更新任务状态"""
        try:
            # 获取当前任务
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            # 验证状态转换
            if task.status and not TaskStatusTransition.is_valid_transition(task.status, new_status):
                logger.warning(f"无效的状态转换: {task.status} -> {new_status}")
                return False
            
            # 更新数据库中的任务状态
            task.status = new_status
            db.commit()
            
            # 更新执行记录
            if execution_id:
                crud_task_execution.update_execution_status(
                    db,
                    execution_id=execution_id,
                    status=new_status,
                    progress_percentage=progress_percentage,
                    current_step=current_step,
                    error_details=error_details
                )
            
            # 更新Redis缓存
            await self._update_redis_status(
                task_id=task_id,
                status=new_status,
                progress_percentage=progress_percentage,
                current_step=current_step,
                error_details=error_details
            )
            
            logger.info(f"任务状态更新成功: task_id={task_id}, status={new_status.value}")
            return True
            
        except Exception as e:
            logger.error(f"更新任务状态失败: task_id={task_id}, error={e}")
            return False
    
    async def _update_redis_status(
        self,
        task_id: int,
        status: TaskStatus,
        progress_percentage: Optional[int] = None,
        current_step: Optional[str] = None,
        error_details: Optional[str] = None
    ):
        """更新Redis中的状态信息"""
        if not self.redis_client:
            return
        
        try:
            status_key = f"report_task:{task_id}:status"
            status_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            if progress_percentage is not None:
                status_data["progress"] = progress_percentage
            
            if current_step:
                status_data["current_step"] = current_step
            
            if error_details:
                status_data["error"] = error_details
            
            await self.redis_client.hset(status_key, mapping=status_data)
            await self.redis_client.expire(status_key, 86400)  # 24小时过期
            
        except Exception as e:
            logger.error(f"更新Redis状态失败: {e}")
    
    async def get_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if not self.redis_client:
            return None
        
        try:
            status_key = f"report_task:{task_id}:status"
            status_data = await self.redis_client.hgetall(status_key)
            
            if status_data:
                return {
                    "task_id": task_id,
                    "status": status_data.get("status", "unknown"),
                    "progress": int(status_data.get("progress", 0)),
                    "current_step": status_data.get("current_step"),
                    "error": status_data.get("error"),
                    "updated_at": status_data.get("updated_at")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None
    
    async def set_task_progress(
        self,
        task_id: int,
        progress_percentage: int,
        current_step: Optional[str] = None,
        step_details: Optional[Dict[str, Any]] = None
    ):
        """设置任务进度"""
        if not self.redis_client:
            return
        
        try:
            progress_key = f"report_task:{task_id}:progress"
            progress_data = {
                "progress": progress_percentage,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if current_step:
                progress_data["current_step"] = current_step
            
            if step_details:
                progress_data["step_details"] = str(step_details)
            
            await self.redis_client.hset(progress_key, mapping=progress_data)
            await self.redis_client.expire(progress_key, 3600)  # 1小时过期
            
            # 同时更新状态中的进度
            status_key = f"report_task:{task_id}:status"
            await self.redis_client.hset(status_key, "progress", progress_percentage)
            
        except Exception as e:
            logger.error(f"设置任务进度失败: {e}")
    
    async def get_running_tasks(self) -> List[Dict[str, Any]]:
        """获取所有运行中的任务"""
        if not self.redis_client:
            return []
        
        try:
            running_statuses = [
                TaskStatus.PROCESSING.value,
                TaskStatus.AGENT_ORCHESTRATING.value,
                TaskStatus.GENERATING.value
            ]
            
            running_tasks = []
            pattern = "report_task:*:status"
            
            async for key in self.redis_client.scan_iter(match=pattern):
                status_data = await self.redis_client.hgetall(key)
                if status_data.get("status") in running_statuses:
                    # 提取task_id
                    task_id = int(key.split(":")[1])
                    running_tasks.append({
                        "task_id": task_id,
                        "status": status_data.get("status"),
                        "progress": int(status_data.get("progress", 0)),
                        "current_step": status_data.get("current_step"),
                        "updated_at": status_data.get("updated_at")
                    })
            
            return running_tasks
            
        except Exception as e:
            logger.error(f"获取运行中任务失败: {e}")
            return []
    
    async def cleanup_completed_tasks(self, older_than_hours: int = 24):
        """清理已完成任务的状态缓存"""
        if not self.redis_client:
            return
        
        try:
            completed_statuses = [
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value
            ]
            
            cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
            cleaned_count = 0
            
            pattern = "report_task:*:status"
            async for key in self.redis_client.scan_iter(match=pattern):
                status_data = await self.redis_client.hgetall(key)
                
                if status_data.get("status") in completed_statuses:
                    updated_at_str = status_data.get("updated_at")
                    if updated_at_str:
                        try:
                            updated_at = datetime.fromisoformat(updated_at_str)
                            if updated_at < cutoff_time:
                                await self.redis_client.delete(key)
                                
                                # 同时删除进度缓存
                                task_id = key.split(":")[1]
                                progress_key = f"report_task:{task_id}:progress"
                                await self.redis_client.delete(progress_key)
                                
                                cleaned_count += 1
                        except ValueError:
                            # 无效的时间格式，删除
                            await self.redis_client.delete(key)
                            cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"清理了 {cleaned_count} 个已完成任务的缓存")
                
        except Exception as e:
            logger.error(f"清理已完成任务缓存失败: {e}")
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        if not self.redis_client:
            return {}
        
        try:
            stats = {
                "total_tasks": 0,
                "status_distribution": {},
                "average_progress": 0
            }
            
            total_progress = 0
            pattern = "report_task:*:status"
            
            async for key in self.redis_client.scan_iter(match=pattern):
                status_data = await self.redis_client.hgetall(key)
                stats["total_tasks"] += 1
                
                status = status_data.get("status", "unknown")
                stats["status_distribution"][status] = stats["status_distribution"].get(status, 0) + 1
                
                progress = int(status_data.get("progress", 0))
                total_progress += progress
            
            if stats["total_tasks"] > 0:
                stats["average_progress"] = total_progress / stats["total_tasks"]
            
            return stats
            
        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}


# 创建全局任务状态管理器实例
task_status_manager = TaskStatusManager()


async def initialize_task_status_manager():
    """初始化任务状态管理器"""
    await task_status_manager.initialize()


async def cleanup_task_status_manager():
    """清理任务状态管理器"""
    await task_status_manager.close()