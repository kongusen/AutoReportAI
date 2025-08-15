"""
Task Progress Manager

任务进度管理器，负责：
- 任务进度更新
- 状态同步
- 错误处理
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import redis.asyncio as redis
from app.core.config import settings
from app.core.time_utils import format_iso
from app.services.notification.notification_service import NotificationService

logger = logging.getLogger(__name__)


class TaskProgressManager:
    """任务进度管理器"""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True
        )
    
    async def update_task_progress(
        self,
        task_id: int,
        status: str,
        progress: int,
        current_step: Optional[str] = None,
        step_details: Optional[Dict[str, Any]] = None
    ):
        """更新任务进度"""
        status_data = {
            "status": status,
            "progress": progress,
            "updated_at": format_iso()
        }
        
        if current_step:
            status_data["current_step"] = current_step
        
        if step_details:
            status_data.update(step_details)
        
        # 更新Redis
        await self.redis_client.hset(
            f"report_task:{task_id}:status", 
            mapping=status_data
        )
        
        # 发送WebSocket通知
        notification_service = NotificationService()
        await notification_service.send_task_progress_update(task_id, status_data)
    
    def update_task_progress_sync(
        self,
        task_id: int,
        status: str,
        progress: int,
        current_step: Optional[str] = None,
        step_details: Optional[Dict[str, Any]] = None
    ):
        """同步更新任务进度（在Celery任务中使用）"""
        # 在新的事件循环中运行异步方法
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                self.update_task_progress(
                    task_id, status, progress, current_step, step_details
                )
            )
        except Exception as e:
            logger.error(f"同步更新任务进度失败: {e}")
        finally:
            try:
                loop.close()
            except:
                pass


class EnhancedTaskProgressManager:
    """增强的任务进度管理器 - 改进错误处理"""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True
        )
    
    async def update_task_progress_safe(
        self,
        task_id: int,
        status: str,
        progress: int,
        current_step: Optional[str] = None,
        step_details: Optional[Dict[str, Any]] = None,
        error_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """安全的任务进度更新，包含错误处理和重试机制"""
        max_retries = 3
        
        status_data = {
            "status": status,
            "progress": progress,
            "updated_at": datetime.utcnow().isoformat(),
            "task_id": task_id
        }
        
        if current_step:
            status_data["current_step"] = current_step
        
        if step_details:
            status_data.update(step_details)
            
        if error_info:
            status_data.update(error_info)
            status_data["has_error"] = True
        
        for attempt in range(max_retries):
            try:
                # 更新Redis
                await self.redis_client.hset(
                    f"report_task:{task_id}:status", 
                    mapping=status_data
                )
                
                # 发送WebSocket通知
                try:
                    notification_service = NotificationService()
                    await notification_service.send_task_progress_update(task_id, status_data)
                except Exception as notify_error:
                    logger.warning(f"WebSocket通知发送失败: {notify_error}")
                
                logger.debug(f"任务进度更新成功 - 任务ID: {task_id}, 状态: {status}, 进度: {progress}%")
                return True
                
            except Exception as e:
                logger.warning(f"更新任务进度失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"任务进度更新彻底失败 - 任务ID: {task_id}: {e}")
                    return False
                await asyncio.sleep(1 * (attempt + 1))  # 递增等待时间
        
        return False


def sync_update_task_progress(task_id: int, status: str, progress: int, message: str, 
                            error_info: Optional[Dict[str, Any]] = None) -> bool:
    """同步版本的安全进度更新"""
    try:
        import redis
        redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        
        status_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow().isoformat(),
            "task_id": task_id
        }
        
        if error_info:
            status_data.update(error_info)
            status_data["has_error"] = True
        
        redis_client.hset(f"report_task:{task_id}:status", mapping=status_data)
        redis_client.close()
        logger.debug(f"任务进度同步更新成功 - 任务ID: {task_id}, 状态: {status}")
        return True
        
    except Exception as e:
        logger.error(f"同步更新任务进度失败 - 任务ID: {task_id}: {e}")
        return False


def update_task_progress_dict(task_id: int, status_data: dict):
    """同步更新任务进度的辅助函数（字典版本）- 改进错误处理"""
    max_retries = 3
    for attempt in range(max_retries):
        redis_client = None
        try:
            import redis
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            
            # 添加时间戳确保数据新鲜度
            if "updated_at" not in status_data:
                status_data["updated_at"] = format_iso()
            
            # 测试Redis连接
            redis_client.ping()
            
            # 设置状态数据
            result = redis_client.hset(f"report_task:{task_id}:status", mapping=status_data)
            logger.debug(f"任务进度更新成功 - 任务ID: {task_id}, 状态: {status_data.get('status', 'unknown')}, Redis返回: {result}")
            
            # 设置过期时间（1小时）
            redis_client.expire(f"report_task:{task_id}:status", 3600)
            
            return True
            
        except redis.ConnectionError as conn_error:
            logger.warning(f"Redis连接失败 (尝试 {attempt + 1}/{max_retries}): {conn_error}")
        except redis.TimeoutError as timeout_error:
            logger.warning(f"Redis超时 (尝试 {attempt + 1}/{max_retries}): {timeout_error}")
        except Exception as e:
            logger.warning(f"更新任务进度失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            
        finally:
            # 确保Redis连接关闭
            if redis_client:
                try:
                    redis_client.close()
                except:
                    pass
        
        # 最后一次尝试失败
        if attempt == max_retries - 1:
            logger.error(f"任务进度更新彻底失败 - 任务ID: {task_id}")
            # 尝试发送错误通知
            try:
                send_error_notification(task_id, f"状态更新失败: Redis连接问题")
            except Exception as notify_error:
                logger.error(f"发送错误通知也失败: {notify_error}")
            return False
            
        # 等待后重试
        time.sleep(1 * (attempt + 1))
    
    return False


def send_error_notification(task_id: int, error_message: str, user_id: Optional[str] = None):
    """发送错误通知"""
    try:
        notification_service = NotificationService()
        # 这里可以添加更多的通知机制，如邮件、短信等
        logger.info(f"错误通知已记录 - 任务ID: {task_id}: {error_message}")
        
        # 如果有用户ID，可以发送个人通知
        if user_id:
            # 这里可以添加用户特定的通知逻辑
            pass
            
    except Exception as e:
        logger.error(f"发送错误通知失败: {e}")


def update_task_progress(task_id: int, status: str, progress: int, message: str):
    """同步更新任务进度的辅助函数 - 改进错误处理"""
    status_data = {
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": format_iso()
    }
    return update_task_progress_dict(task_id, status_data)


def safe_update_progress_with_fallback(task_id: int, status: str, progress: int, message: str, fallback_status: dict = None):
    """安全的进度更新，失败时使用备用状态"""
    success = update_task_progress(task_id, status, progress, message)
    if not success and fallback_status:
        logger.warning(f"使用备用状态更新任务 {task_id}")
        update_task_progress_dict(task_id, fallback_status)
    return success
