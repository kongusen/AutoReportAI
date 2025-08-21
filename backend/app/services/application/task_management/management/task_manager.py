"""
Task Manager

任务管理器，负责：
- 任务生命周期管理
- 任务状态控制
- 任务调度管理
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.time_utils import now
from app.db.session import SessionLocal
from app.services.infrastructure.notification.notification_service import NotificationService
from ..core.progress_manager import update_task_progress

logger = logging.getLogger(__name__)


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.notification_service = NotificationService()
    
    def __del__(self):
        """析构函数，确保数据库连接关闭"""
        if hasattr(self, 'db') and self.db:
            try:
                self.db.close()
            except:
                pass
    
    def create_task(
        self,
        task_data: Dict[str, Any],
        owner_id: str
    ) -> Optional[schemas.Task]:
        """
        创建新任务
        
        Args:
            task_data: 任务数据
            owner_id: 所有者ID
            
        Returns:
            创建的任务
        """
        try:
            # 准备任务数据
            task_create = schemas.TaskCreate(
                name=task_data.get("name", "新任务"),
                description=task_data.get("description", ""),
                template_id=task_data.get("template_id"),
                data_source_id=task_data.get("data_source_id"),
                schedule_config=task_data.get("schedule_config", {}),
                is_active=task_data.get("is_active", True),
                owner_id=owner_id
            )
            
            # 创建任务
            task = crud.task.create(db=self.db, obj_in=task_create)
            
            logger.info(f"任务创建成功 - 任务ID: {task.id}, 名称: {task.name}")
            
            # 发送通知
            self.notification_service.send_task_created_notification(
                task_id=task.id,
                task_name=task.name,
                owner_id=owner_id
            )
            
            return task
            
        except Exception as e:
            logger.error(f"任务创建失败: {e}")
            return None
    
    def update_task(
        self,
        task_id: int,
        task_data: Dict[str, Any]
    ) -> Optional[schemas.Task]:
        """
        更新任务
        
        Args:
            task_id: 任务ID
            task_data: 更新数据
            
        Returns:
            更新后的任务
        """
        try:
            # 获取现有任务
            task = crud.task.get(db=self.db, id=task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return None
            
            # 准备更新数据
            task_update = schemas.TaskUpdate(**task_data)
            
            # 更新任务
            updated_task = crud.task.update(
                db=self.db,
                db_obj=task,
                obj_in=task_update
            )
            
            logger.info(f"任务更新成功 - 任务ID: {task_id}")
            
            return updated_task
            
        except Exception as e:
            logger.error(f"任务更新失败 - 任务ID: {task_id}: {e}")
            return None
    
    def delete_task(self, task_id: int) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否删除成功
        """
        try:
            # 获取任务
            task = crud.task.get(db=self.db, id=task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            # 删除任务
            crud.task.remove(db=self.db, id=task_id)
            
            logger.info(f"任务删除成功 - 任务ID: {task_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"任务删除失败 - 任务ID: {task_id}: {e}")
            return False
    
    def get_task(self, task_id: int) -> Optional[schemas.Task]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息
        """
        try:
            task = crud.task.get(db=self.db, id=task_id)
            return task
            
        except Exception as e:
            logger.error(f"获取任务失败 - 任务ID: {task_id}: {e}")
            return None
    
    def get_user_tasks(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[schemas.Task]:
        """
        获取用户的任务列表
        
        Args:
            user_id: 用户ID
            skip: 跳过数量
            limit: 限制数量
            
        Returns:
            任务列表
        """
        try:
            tasks = crud.task.get_multi_by_owner(
                db=self.db,
                owner_id=user_id,
                skip=skip,
                limit=limit
            )
            return tasks
            
        except Exception as e:
            logger.error(f"获取用户任务列表失败 - 用户ID: {user_id}: {e}")
            return []
    
    def activate_task(self, task_id: int) -> bool:
        """
        激活任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否激活成功
        """
        try:
            task = crud.task.get(db=self.db, id=task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            # 更新任务状态
            crud.task.update(
                db=self.db,
                db_obj=task,
                obj_in=schemas.TaskUpdate(is_active=True)
            )
            
            logger.info(f"任务激活成功 - 任务ID: {task_id}")
            
            # 发送通知
            self.notification_service.send_task_activated_notification(
                task_id=task_id,
                task_name=task.name
            )
            
            return True
            
        except Exception as e:
            logger.error(f"任务激活失败 - 任务ID: {task_id}: {e}")
            return False
    
    def deactivate_task(self, task_id: int) -> bool:
        """
        停用任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否停用成功
        """
        try:
            task = crud.task.get(db=self.db, id=task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            # 更新任务状态
            crud.task.update(
                db=self.db,
                db_obj=task,
                obj_in=schemas.TaskUpdate(is_active=False)
            )
            
            logger.info(f"任务停用成功 - 任务ID: {task_id}")
            
            # 发送通知
            self.notification_service.send_task_deactivated_notification(
                task_id=task_id,
                task_name=task.name
            )
            
            return True
            
        except Exception as e:
            logger.error(f"任务停用失败 - 任务ID: {task_id}: {e}")
            return False
    
    def get_active_tasks(self) -> List[schemas.Task]:
        """
        获取所有活跃任务
        
        Returns:
            活跃任务列表
        """
        try:
            tasks = crud.task.get_active_tasks(db=self.db)
            return tasks
            
        except Exception as e:
            logger.error(f"获取活跃任务失败: {e}")
            return []
    
    def update_task_execution_status(
        self,
        task_id: int,
        status: str,
        execution_time: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新任务执行状态
        
        Args:
            task_id: 任务ID
            status: 状态
            execution_time: 执行时间
            error_message: 错误信息
            
        Returns:
            是否更新成功
        """
        try:
            task = crud.task.get(db=self.db, id=task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            # 准备更新数据
            update_data = {
                "last_execution_status": status,
                "last_execution_at": now()
            }
            
            if execution_time is not None:
                update_data["last_execution_time"] = execution_time
            
            if error_message:
                update_data["last_error_message"] = error_message
            
            # 更新任务
            crud.task.update(
                db=self.db,
                db_obj=task,
                obj_in=schemas.TaskUpdate(**update_data)
            )
            
            logger.info(f"任务执行状态更新成功 - 任务ID: {task_id}, 状态: {status}")
            
            return True
            
        except Exception as e:
            logger.error(f"任务执行状态更新失败 - 任务ID: {task_id}: {e}")
            return False
