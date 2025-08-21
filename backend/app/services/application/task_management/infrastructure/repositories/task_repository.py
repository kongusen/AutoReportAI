"""
Task Repository Implementation

任务仓储实现
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from app import crud, schemas
from app.db.session import SessionLocal
from ...application.interfaces.task_repository_interface import TaskRepositoryInterface
from ...domain.entities.task_entity import TaskEntity, TaskStatus, TaskPriority, ExecutionMode, ScheduleConfig

logger = logging.getLogger(__name__)


class TaskRepository(TaskRepositoryInterface):
    """任务仓储实现"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        self._should_close_db = db_session is None
    
    def __del__(self):
        """析构函数，确保数据库连接关闭"""
        if self._should_close_db and hasattr(self, 'db') and self.db:
            try:
                self.db.close()
            except:
                pass
    
    async def generate_task_id(self) -> str:
        """生成任务ID"""
        return str(uuid.uuid4())
    
    async def save(self, task: TaskEntity) -> TaskEntity:
        """保存任务"""
        try:
            # 检查任务是否已存在
            existing_task = crud.task.get(self.db, id=task.id)
            
            if existing_task:
                # 更新现有任务
                task_update = self._entity_to_update_schema(task)
                updated_task = crud.task.update(
                    db=self.db,
                    db_obj=existing_task,
                    obj_in=task_update
                )
                return self._db_model_to_entity(updated_task)
            else:
                # 创建新任务
                task_create = self._entity_to_create_schema(task)
                created_task = crud.task.create(
                    db=self.db,
                    obj_in=task_create
                )
                return self._db_model_to_entity(created_task)
                
        except Exception as e:
            logger.error(f"Failed to save task {task.id}: {e}")
            self.db.rollback()
            raise
    
    async def get_by_id(self, task_id: str) -> Optional[TaskEntity]:
        """根据ID获取任务"""
        try:
            task = crud.task.get(self.db, id=task_id)
            return self._db_model_to_entity(task) if task else None
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    async def get_by_user(self, user_id: str, 
                         filters: Dict[str, Any] = None,
                         pagination: Dict[str, Any] = None) -> List[TaskEntity]:
        """获取用户的任务列表"""
        try:
            skip = pagination.get("skip", 0) if pagination else 0
            limit = pagination.get("limit", 100) if pagination else 100
            
            tasks = crud.task.get_multi_by_owner(
                db=self.db,
                owner_id=user_id,
                skip=skip,
                limit=limit
            )
            
            entities = [self._db_model_to_entity(task) for task in tasks]
            
            # 应用额外过滤器
            if filters:
                entities = self._apply_filters(entities, filters)
            
            return entities
            
        except Exception as e:
            logger.error(f"Failed to get tasks for user {user_id}: {e}")
            return []
    
    async def get_active_tasks(self) -> List[TaskEntity]:
        """获取所有活跃任务"""
        try:
            tasks = crud.task.get_active_tasks(self.db)
            return [self._db_model_to_entity(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return []
    
    async def get_scheduled_tasks(self) -> List[TaskEntity]:
        """获取所有需要调度的任务"""
        try:
            # 查询有调度配置且活跃的任务
            tasks = self.db.query(crud.task.model).filter(
                crud.task.model.is_active == True,
                crud.task.model.schedule.isnot(None)
            ).all()
            
            return [self._db_model_to_entity(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"Failed to get scheduled tasks: {e}")
            return []
    
    async def find_by_criteria(self, criteria: Dict[str, Any]) -> List[TaskEntity]:
        """根据条件查找任务"""
        try:
            query = self.db.query(crud.task.model)
            
            # 应用查询条件
            if "task_type" in criteria:
                query = query.filter(crud.task.model.task_type == criteria["task_type"])
            
            if "status" in criteria:
                query = query.filter(crud.task.model.status == criteria["status"])
            
            if "is_active" in criteria:
                query = query.filter(crud.task.model.is_active == criteria["is_active"])
            
            if "owner_id" in criteria:
                query = query.filter(crud.task.model.owner_id == criteria["owner_id"])
            
            if "template_id" in criteria:
                query = query.filter(crud.task.model.template_id == criteria["template_id"])
            
            if "data_source_id" in criteria:
                query = query.filter(crud.task.model.data_source_id == criteria["data_source_id"])
            
            tasks = query.all()
            return [self._db_model_to_entity(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"Failed to find tasks by criteria {criteria}: {e}")
            return []
    
    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        try:
            result = crud.task.remove(self.db, id=task_id)
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False
    
    async def get_task_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取任务统计信息"""
        try:
            query = self.db.query(crud.task.model)
            
            if user_id:
                query = query.filter(crud.task.model.owner_id == user_id)
            
            tasks = query.all()
            
            stats = {
                "total_tasks": len(tasks),
                "active_tasks": len([t for t in tasks if t.is_active]),
                "scheduled_tasks": len([t for t in tasks if t.schedule]),
                "completed_tasks": len([t for t in tasks if t.last_execution_status == "completed"]),
                "failed_tasks": len([t for t in tasks if t.last_execution_status == "failed"]),
                "tasks_by_type": {},
                "tasks_by_status": {}
            }
            
            # 按类型统计
            for task in tasks:
                task_type = task.task_type or "unknown"
                stats["tasks_by_type"][task_type] = stats["tasks_by_type"].get(task_type, 0) + 1
            
            # 按状态统计
            for task in tasks:
                status = task.last_execution_status or "never_run"
                stats["tasks_by_status"][status] = stats["tasks_by_status"].get(status, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get task statistics: {e}")
            return {}
    
    def _db_model_to_entity(self, db_task) -> Optional[TaskEntity]:
        """将数据库模型转换为实体"""
        if not db_task:
            return None
        
        try:
            # 创建任务实体
            entity = TaskEntity(
                task_id=str(db_task.id),
                name=db_task.name or "Unnamed Task",
                task_type=db_task.task_type or "report_generation"
            )
            
            # 设置基本属性
            entity.description = db_task.description or ""
            entity.owner_id = str(db_task.owner_id) if db_task.owner_id else None
            entity.template_id = str(db_task.template_id) if db_task.template_id else None
            entity.data_source_id = str(db_task.data_source_id) if db_task.data_source_id else None
            
            # 设置状态
            entity.is_active = db_task.is_active or False
            entity.created_at = db_task.created_at or datetime.utcnow()
            entity.updated_at = db_task.updated_at or datetime.utcnow()
            
            # 设置调度配置
            if db_task.schedule:
                schedule_config = ScheduleConfig(
                    cron_expression=db_task.schedule,
                    enabled=True
                )
                entity.schedule_config = schedule_config
            
            # 设置配置和参数
            if hasattr(db_task, 'schedule_config') and db_task.schedule_config:
                entity.configuration = db_task.schedule_config
            
            # 设置执行统计（从数据库字段获取）
            entity.total_executions = getattr(db_task, 'total_executions', 0)
            entity.successful_executions = getattr(db_task, 'successful_executions', 0)
            entity.failed_executions = getattr(db_task, 'failed_executions', 0)
            
            if db_task.last_execution_at:
                entity.last_successful_execution_at = db_task.last_execution_at
            
            # 设置当前状态
            if db_task.last_execution_status:
                if db_task.last_execution_status == "completed":
                    entity.status = TaskStatus.COMPLETED
                elif db_task.last_execution_status == "failed":
                    entity.status = TaskStatus.FAILED
                elif db_task.last_execution_status == "running":
                    entity.status = TaskStatus.RUNNING
                else:
                    entity.status = TaskStatus.CREATED
            
            return entity
            
        except Exception as e:
            logger.error(f"Failed to convert DB model to entity: {e}")
            return None
    
    def _entity_to_create_schema(self, entity: TaskEntity) -> schemas.TaskCreate:
        """将实体转换为创建Schema"""
        return schemas.TaskCreate(
            name=entity.name,
            description=entity.description,
            task_type=entity.task_type,
            template_id=entity.template_id,
            data_source_id=entity.data_source_id,
            schedule_config=entity.configuration,
            schedule=entity.schedule_config.cron_expression if entity.schedule_config else None,
            is_active=entity.is_active,
            owner_id=entity.owner_id
        )
    
    def _entity_to_update_schema(self, entity: TaskEntity) -> schemas.TaskUpdate:
        """将实体转换为更新Schema"""
        update_data = {
            "name": entity.name,
            "description": entity.description,
            "schedule_config": entity.configuration,
            "schedule": entity.schedule_config.cron_expression if entity.schedule_config else None,
            "is_active": entity.is_active,
            "updated_at": entity.updated_at
        }
        
        # 添加执行状态更新
        if entity.status:
            if entity.status == TaskStatus.COMPLETED:
                update_data["last_execution_status"] = "completed"
            elif entity.status == TaskStatus.FAILED:
                update_data["last_execution_status"] = "failed"
            elif entity.status == TaskStatus.RUNNING:
                update_data["last_execution_status"] = "running"
        
        # 添加执行统计
        update_data["total_executions"] = entity.total_executions
        update_data["successful_executions"] = entity.successful_executions
        update_data["failed_executions"] = entity.failed_executions
        
        if entity.last_successful_execution_at:
            update_data["last_execution_at"] = entity.last_successful_execution_at
        
        return schemas.TaskUpdate(**update_data)
    
    def _apply_filters(self, entities: List[TaskEntity], filters: Dict[str, Any]) -> List[TaskEntity]:
        """应用额外过滤器"""
        filtered = entities
        
        if "status" in filters:
            status_filter = filters["status"]
            filtered = [e for e in filtered if e.status.value == status_filter]
        
        if "is_active" in filters:
            active_filter = filters["is_active"]
            filtered = [e for e in filtered if e.is_active == active_filter]
        
        if "task_type" in filters:
            type_filter = filters["task_type"]
            filtered = [e for e in filtered if e.task_type == type_filter]
        
        if "has_schedule" in filters:
            schedule_filter = filters["has_schedule"]
            if schedule_filter:
                filtered = [e for e in filtered if e.schedule_config is not None]
            else:
                filtered = [e for e in filtered if e.schedule_config is None]
        
        return filtered