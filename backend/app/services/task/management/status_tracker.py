"""
Status Tracker

状态跟踪器，负责：
- 任务状态监控
- 执行历史记录
- 性能统计
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.config import settings
from app.core.time_utils import now
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class StatusTracker:
    """状态跟踪器"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    
    def __del__(self):
        """析构函数，确保连接关闭"""
        if hasattr(self, 'db') and self.db:
            try:
                self.db.close()
            except:
                pass
        
        if hasattr(self, 'redis_client') and self.redis_client:
            try:
                self.redis_client.close()
            except:
                pass
    
    def track_task_start(self, task_id: int, user_id: str) -> bool:
        """
        跟踪任务开始
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            是否跟踪成功
        """
        try:
            start_time = now()
            
            # 更新Redis状态
            status_data = {
                "status": "started",
                "start_time": start_time.isoformat(),
                "user_id": user_id,
                "progress": 0
            }
            
            self.redis_client.hset(
                f"report_task:{task_id}:status",
                mapping=status_data
            )
            
            # 设置过期时间（1小时）
            self.redis_client.expire(f"report_task:{task_id}:status", 3600)
            
            logger.info(f"任务开始跟踪 - 任务ID: {task_id}, 用户ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"任务开始跟踪失败 - 任务ID: {task_id}: {e}")
            return False
    
    def track_task_progress(
        self,
        task_id: int,
        progress: int,
        current_step: str,
        step_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        跟踪任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度百分比
            current_step: 当前步骤
            step_details: 步骤详情
            
        Returns:
            是否跟踪成功
        """
        try:
            update_time = now()
            
            # 更新Redis状态
            status_data = {
                "status": "processing",
                "progress": progress,
                "current_step": current_step,
                "last_update": update_time.isoformat()
            }
            
            if step_details:
                status_data.update(step_details)
            
            self.redis_client.hset(
                f"report_task:{task_id}:status",
                mapping=status_data
            )
            
            logger.debug(f"任务进度跟踪 - 任务ID: {task_id}, 进度: {progress}%, 步骤: {current_step}")
            return True
            
        except Exception as e:
            logger.error(f"任务进度跟踪失败 - 任务ID: {task_id}: {e}")
            return False
    
    def track_task_completion(
        self,
        task_id: int,
        result: Dict[str, Any],
        execution_time: float
    ) -> bool:
        """
        跟踪任务完成
        
        Args:
            task_id: 任务ID
            result: 执行结果
            execution_time: 执行时间
            
        Returns:
            是否跟踪成功
        """
        try:
            completion_time = now()
            
            # 更新Redis状态
            status_data = {
                "status": "completed",
                "progress": 100,
                "completion_time": completion_time.isoformat(),
                "execution_time": execution_time,
                "result": str(result)
            }
            
            self.redis_client.hset(
                f"report_task:{task_id}:status",
                mapping=status_data
            )
            
            # 保存到数据库
            self._save_execution_history(task_id, "completed", execution_time, result)
            
            logger.info(f"任务完成跟踪 - 任务ID: {task_id}, 执行时间: {execution_time}s")
            return True
            
        except Exception as e:
            logger.error(f"任务完成跟踪失败 - 任务ID: {task_id}: {e}")
            return False
    
    def track_task_failure(
        self,
        task_id: int,
        error: str,
        execution_time: Optional[float] = None
    ) -> bool:
        """
        跟踪任务失败
        
        Args:
            task_id: 任务ID
            error: 错误信息
            execution_time: 执行时间
            
        Returns:
            是否跟踪成功
        """
        try:
            failure_time = now()
            
            # 更新Redis状态
            status_data = {
                "status": "failed",
                "progress": 0,
                "failure_time": failure_time.isoformat(),
                "error": error
            }
            
            if execution_time is not None:
                status_data["execution_time"] = execution_time
            
            self.redis_client.hset(
                f"report_task:{task_id}:status",
                mapping=status_data
            )
            
            # 保存到数据库
            self._save_execution_history(task_id, "failed", execution_time or 0, {"error": error})
            
            logger.error(f"任务失败跟踪 - 任务ID: {task_id}, 错误: {error}")
            return True
            
        except Exception as e:
            logger.error(f"任务失败跟踪失败 - 任务ID: {task_id}: {e}")
            return False
    
    def get_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        try:
            status_data = self.redis_client.hgetall(f"report_task:{task_id}:status")
            
            if not status_data:
                return None
            
            # 转换数据类型
            if "progress" in status_data:
                status_data["progress"] = int(status_data["progress"])
            
            if "execution_time" in status_data:
                status_data["execution_time"] = float(status_data["execution_time"])
            
            return status_data
            
        except Exception as e:
            logger.error(f"获取任务状态失败 - 任务ID: {task_id}: {e}")
            return None
    
    def get_user_task_statuses(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的所有任务状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            任务状态列表
        """
        try:
            # 获取用户的任务列表
            tasks = crud.task.get_multi_by_owner(db=self.db, owner_id=user_id)
            
            statuses = []
            for task in tasks:
                status = self.get_task_status(task.id)
                if status:
                    status["task_id"] = task.id
                    status["task_name"] = task.name
                    statuses.append(status)
            
            return statuses
            
        except Exception as e:
            logger.error(f"获取用户任务状态失败 - 用户ID: {user_id}: {e}")
            return []
    
    def get_task_execution_history(
        self,
        task_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取任务执行历史
        
        Args:
            task_id: 任务ID
            limit: 限制数量
            
        Returns:
            执行历史列表
        """
        try:
            # 从数据库获取执行历史
            history = crud.report_history.get_multi_by_task(
                db=self.db,
                task_id=task_id,
                limit=limit
            )
            
            return [
                {
                    "id": record.id,
                    "status": record.status,
                    "generated_at": record.generated_at.isoformat() if record.generated_at else None,
                    "execution_time": getattr(record, 'execution_time', None),
                    "file_path": record.file_path
                }
                for record in history
            ]
            
        except Exception as e:
            logger.error(f"获取任务执行历史失败 - 任务ID: {task_id}: {e}")
            return []
    
    def get_performance_stats(
        self,
        user_id: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取性能统计
        
        Args:
            user_id: 用户ID（可选）
            days: 统计天数
            
        Returns:
            性能统计信息
        """
        try:
            start_date = now() - timedelta(days=days)
            
            # 获取执行历史
            if user_id:
                # 获取用户的任务
                tasks = crud.task.get_multi_by_owner(db=self.db, owner_id=user_id)
                task_ids = [task.id for task in tasks]
                
                if not task_ids:
                    return self._empty_stats()
                
                history = crud.report_history.get_multi_by_tasks_and_date(
                    db=self.db,
                    task_ids=task_ids,
                    start_date=start_date
                )
            else:
                # 获取所有执行历史
                history = crud.report_history.get_multi_by_date(
                    db=self.db,
                    start_date=start_date
                )
            
            # 计算统计信息
            total_tasks = len(history)
            completed_tasks = len([h for h in history if h.status == "completed"])
            failed_tasks = len([h for h in history if h.status == "failed"])
            
            # 计算平均执行时间
            execution_times = [
                getattr(h, 'execution_time', 0) 
                for h in history 
                if hasattr(h, 'execution_time') and getattr(h, 'execution_time', 0) > 0
            ]
            
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                "avg_execution_time": avg_execution_time,
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"获取性能统计失败: {e}")
            return self._empty_stats()
    
    def _save_execution_history(
        self,
        task_id: int,
        status: str,
        execution_time: float,
        result: Dict[str, Any]
    ):
        """保存执行历史到数据库"""
        try:
            # 这里可以扩展为保存更详细的执行历史
            # 目前主要依赖report_history表
            pass
            
        except Exception as e:
            logger.error(f"保存执行历史失败 - 任务ID: {task_id}: {e}")
    
    def _empty_stats(self) -> Dict[str, Any]:
        """返回空的统计信息"""
        return {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "success_rate": 0,
            "avg_execution_time": 0,
            "period_days": 0
        }
