"""
LLM监控WebSocket集成服务
将LLM健康状态变化通过WebSocket推送给前端
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.core.api_specification import NotificationMessage, WebSocketMessage, WebSocketMessageType
from app.websocket.manager import websocket_manager
from app.services.infrastructure.ai.llm.health_service import get_model_health_service
from app.services.infrastructure.ai.llm.rate_limiter import get_llm_rate_limiter
from app.services.infrastructure.ai.service_pool import get_ai_service_pool

logger = logging.getLogger(__name__)


class LLMMonitorWebSocketService:
    """LLM监控WebSocket服务"""
    
    def __init__(self):
        self.monitoring_active = False
        self.monitor_interval = 300  # 5分钟
        self.monitor_task: Optional[asyncio.Task] = None
        self.last_health_states: Dict[str, bool] = {}
        
    async def start_monitoring(self, db_session_factory):
        """开始LLM监控"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(db_session_factory)
        )
        
        logger.info("LLM监控WebSocket服务已启动")
    
    async def stop_monitoring(self):
        """停止LLM监控"""
        self.monitoring_active = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("LLM监控WebSocket服务已停止")
    
    async def _monitoring_loop(self, db_session_factory):
        """监控循环"""
        while self.monitoring_active:
            try:
                # 获取数据库会话
                db = next(db_session_factory())
                
                # 执行监控检查
                await self._perform_monitoring_check(db)
                
                # 等待下一次检查
                await asyncio.sleep(self.monitor_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"LLM监控循环错误: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟再重试
    
    async def _perform_monitoring_check(self, db: Session):
        """执行监控检查"""
        try:
            # 获取健康检查服务
            health_service = get_model_health_service()
            
            # 检查所有服务器健康状态
            health_results = await health_service.test_all_servers_health(db, "系统监控检查")
            
            # 检查状态变化并发送通知
            for result in health_results:
                await self._check_health_change(result)
            
            # 发送系统状态更新
            await self._broadcast_system_status()
            
        except Exception as e:
            logger.error(f"监控检查执行失败: {e}")
    
    async def _check_health_change(self, health_result):
        """检查健康状态变化"""
        server_key = f"server_{health_result.server_id}"
        previous_healthy = self.last_health_states.get(server_key)
        current_healthy = health_result.is_healthy
        
        # 记录当前状态
        self.last_health_states[server_key] = current_healthy
        
        # 如果状态发生变化，发送通知
        if previous_healthy is not None and previous_healthy != current_healthy:
            await self._send_health_change_notification(health_result, previous_healthy)
    
    async def _send_health_change_notification(self, health_result, was_healthy: bool):
        """发送健康状态变化通知"""
        try:
            if health_result.is_healthy and not was_healthy:
                # 服务器恢复健康
                notification = NotificationMessage(
                    title="LLM服务器恢复",
                    message=f"服务器 {health_result.server_name} 已恢复健康状态",
                    notification_type="success",
                    category="llm_monitor",
                    data={
                        "server_id": health_result.server_id,
                        "server_name": health_result.server_name,
                        "health_rate": health_result.health_rate,
                        "response_time": health_result.response_time
                    }
                )
            elif not health_result.is_healthy and was_healthy:
                # 服务器变为不健康
                notification = NotificationMessage(
                    title="LLM服务器异常",
                    message=f"服务器 {health_result.server_name} 检测到异常",
                    notification_type="error",
                    category="llm_monitor",
                    data={
                        "server_id": health_result.server_id,
                        "server_name": health_result.server_name,
                        "error_message": health_result.error_message,
                        "health_rate": health_result.health_rate
                    }
                )
            else:
                return  # 无需通知
            
            # 广播通知给所有订阅了LLM监控的用户
            await websocket_manager.broadcast_to_channel("llm_monitor", notification)
            
            # 也发送给系统警报频道
            await websocket_manager.broadcast_to_channel("system:alerts", notification)
            
        except Exception as e:
            logger.error(f"发送健康状态变化通知失败: {e}")
    
    async def _broadcast_system_status(self):
        """广播系统状态更新"""
        try:
            # 获取速率限制器状态（安全方式）
            try:
                rate_limiter = get_llm_rate_limiter()
                limiter_stats = rate_limiter.get_statistics()
                
                # 安全获取嵌套字典值
                current_status = limiter_stats.get("current_status", {})
                metrics = limiter_stats.get("metrics", {})
                
                rate_limiter_data = {
                    "active_requests": current_status.get("active_requests", 0),
                    "success_rate": metrics.get("success_rate", 0.0),
                    "requests_per_minute": metrics.get("requests_per_minute", 0.0)
                }
            except Exception as e:
                logger.warning(f"获取速率限制器统计失败: {e}")
                rate_limiter_data = {
                    "active_requests": 0,
                    "success_rate": 0.0,
                    "requests_per_minute": 0.0
                }
            
            # 获取服务池状态（安全方式）
            try:
                service_pool = get_ai_service_pool()
                pool_stats = service_pool.get_pool_stats()
                
                service_pool_data = {
                    "healthy_instances": pool_stats.get("healthy_instances", 0),
                    "total_instances": pool_stats.get("total_instances", 0),
                    "pool_usage": pool_stats.get("pool_usage", 0.0)
                }
            except Exception as e:
                logger.warning(f"获取服务池统计失败: {e}")
                service_pool_data = {
                    "healthy_instances": 0,
                    "total_instances": 0,
                    "pool_usage": 0.0
                }
            
            # 构建状态消息
            status_message = WebSocketMessage(
                type=WebSocketMessageType.SYSTEM_STATUS,
                data={
                    "component": "llm_monitor",
                    "timestamp": datetime.utcnow().isoformat(),
                    "rate_limiter": rate_limiter_data,
                    "service_pool": service_pool_data
                }
            )
            
            # 发送给订阅了系统更新的用户
            sent_count = await websocket_manager.broadcast_to_channel("system:updates", status_message)
            
            if sent_count == 0:
                logger.debug("系统状态广播: 没有订阅者")
            else:
                logger.debug(f"系统状态广播成功，发送给 {sent_count} 个订阅者")
            
        except Exception as e:
            logger.error(f"广播系统状态失败: {e}", exc_info=True)
    
    async def send_rate_limit_warning(self, user_id: str, details: Dict[str, Any]):
        """发送速率限制警告"""
        try:
            warning = NotificationMessage(
                title="LLM请求速率限制",
                message="您的LLM请求频率过高，请稍后再试",
                notification_type="warning",
                category="rate_limit",
                data=details,
                user_id=user_id
            )
            
            # 发送给特定用户
            await websocket_manager.send_to_user(user_id, warning)
            
        except Exception as e:
            logger.error(f"发送速率限制警告失败: {e}")
    
    async def send_service_usage_update(self, user_id: str, usage_data: Dict[str, Any]):
        """发送服务使用情况更新"""
        try:
            update_message = WebSocketMessage(
                type=WebSocketMessageType.TASK_UPDATE,
                data={
                    "component": "llm_usage",
                    "user_id": user_id,
                    "usage_data": usage_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # 发送给用户私有频道
            await websocket_manager.send_to_user(user_id, update_message)
            
        except Exception as e:
            logger.error(f"发送服务使用更新失败: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return {
            "monitoring_active": self.monitoring_active,
            "monitor_interval": self.monitor_interval,
            "monitored_servers": len(self.last_health_states),
            "task_running": self.monitor_task is not None and not self.monitor_task.done(),
            "last_check": max(
                self.last_health_states.keys(), 
                default="never",
                key=lambda k: self.last_health_states.get(k, datetime.min)
            ) if self.last_health_states else "never"
        }


# 全局监控服务实例
_global_monitor_service: Optional[LLMMonitorWebSocketService] = None


def get_llm_monitor_service() -> LLMMonitorWebSocketService:
    """获取全局LLM监控服务"""
    global _global_monitor_service
    
    if _global_monitor_service is None:
        _global_monitor_service = LLMMonitorWebSocketService()
    
    return _global_monitor_service


async def start_llm_monitoring(db_session_factory):
    """启动LLM监控"""
    service = get_llm_monitor_service()
    await service.start_monitoring(db_session_factory)


async def stop_llm_monitoring():
    """停止LLM监控"""
    service = get_llm_monitor_service()
    await service.stop_monitoring()