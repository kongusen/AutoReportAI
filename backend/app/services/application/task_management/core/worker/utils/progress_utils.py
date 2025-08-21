"""
Progress Management Utilities

进度管理工具函数，包括：
- 任务进度更新
- 错误通知
- 状态同步
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import redis
from app.core.config import settings
from app.core.time_utils import format_iso

logger = logging.getLogger(__name__)


def update_task_progress(task_id: int, status: str, progress: int, message: str):
    """同步更新任务进度的辅助函数 - 改进错误处理"""
    status_data = {
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": format_iso()
    }
    return update_task_progress_dict(task_id, status_data)


def send_error_notification(task_id: int, error_message: str):
    """发送错误通知的辅助函数"""
    try:
        from app.services.infrastructure.notification.notification_service import NotificationService
        notification_service = NotificationService()
        # 这里可以添加异步通知逻辑
        logger.info(f"错误通知已发送 - 任务ID: {task_id}: {error_message}")
    except Exception as e:
        logger.error(f"发送错误通知失败: {e}")


def safe_update_progress_with_fallback(task_id: int, status: str, progress: int, message: str, fallback_status: dict = None):
    """安全的进度更新，失败时使用备用状态"""
    success = update_task_progress(task_id, status, progress, message)
    if not success and fallback_status:
        logger.warning(f"使用备用状态更新任务 {task_id}")
        update_task_progress_dict(task_id, fallback_status)
    return success


def update_task_progress_dict(task_id: int, status_data: dict):
    """同步更新任务进度的辅助函数（字典版本）- 改进错误处理"""
    max_retries = 3
    for attempt in range(max_retries):
        redis_client = None
        try:
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
