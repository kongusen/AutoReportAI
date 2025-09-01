"""
增强的WebSocket路由
支持更丰富的实时通信功能
"""

import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import decode_access_token
from app.websocket.enhanced_manager import enhanced_manager
from app.core.api_specification import (
    WebSocketMessage, WebSocketMessageType, NotificationMessage,
    APIResponse, create_success_response, create_error_response
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def authenticate_websocket_user(token: str, db: Session):
    """WebSocket用户认证"""
    try:
        payload = decode_access_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        from app.crud.crud_user import crud_user
        user = crud_user.get(db, id=user_id)
        return user
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


@router.websocket("/ws")
async def enhanced_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    client_type: Optional[str] = Query("web"),
    client_version: Optional[str] = Query(None),
    db: Session = Depends(deps.get_db)
):
    """增强的WebSocket连接端点"""
    session_id = None
    
    try:
        await websocket.accept()
        logger.info(f"WebSocket connection accepted from {websocket.client}")
        
        # 认证处理
        auth_token = token
        if not auth_token:
            # 等待认证消息
            auth_message = await websocket.receive_text()
            try:
                auth_data = json.loads(auth_message)
                if auth_data.get("type") == "auth":
                    auth_token = auth_data.get("token")
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Authentication required"
                    }))
                    await websocket.close()
                    return
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": "Invalid authentication message format"
                }))
                await websocket.close()
                return
        
        # 验证用户
        user = await authenticate_websocket_user(auth_token, db)
        if not user:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Authentication failed"
            }))
            await websocket.close()
            return
        
        # 建立连接
        client_info = {
            "client_type": client_type,
            "client_version": client_version,
            "client_host": websocket.client.host if websocket.client else None,
            "client_port": websocket.client.port if websocket.client else None,
        }
        
        session_id = await enhanced_manager.connect(
            websocket=websocket,
            user_id=str(user.id),
            client_info=client_info
        )
        
        # 认证会话
        await enhanced_manager.authenticate(session_id, {
            "user_id": str(user.id),
            "subscriptions": [
                f"user:{user.id}",  # 用户私有频道
                "system:alerts",    # 系统警报
                "system:updates"    # 系统更新
            ]
        })
        
        logger.info(f"WebSocket authenticated: user={user.id}, session={session_id}")
        
        # 消息循环
        while True:
            try:
                message_data = await websocket.receive_text()
                await enhanced_manager.handle_message(session_id, message_data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: session={session_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket message loop: {e}")
                # 发送错误消息给客户端
                try:
                    error_msg = WebSocketMessage(
                        type=WebSocketMessageType.ERROR,
                        message="Internal server error",
                        data={"error": str(e)}
                    )
                    await enhanced_manager.send_to_session(session_id, error_msg)
                except:
                    break
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        if session_id:
            await enhanced_manager.disconnect(session_id, "connection_closed")


# ============================================================================
# WebSocket管理API端点
# ============================================================================

@router.get("/status")
async def get_websocket_status(
    current_user = Depends(deps.get_current_active_user)
):
    """获取WebSocket系统状态"""
    try:
        stats = enhanced_manager.get_system_stats()
        user_connections = enhanced_manager.get_user_connections(str(current_user.id))
        
        return create_success_response(
            data={
                "system_stats": stats,
                "user_connections": user_connections,
                "is_user_connected": len(user_connections) > 0
            },
            message="WebSocket status retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        return create_error_response(
            error="WEBSOCKET_STATUS_ERROR",
            message="Failed to get WebSocket status"
        )


@router.post("/send-notification")
async def send_notification_api(
    notification_data: Dict[str, Any],
    target_user_id: Optional[str] = None,
    broadcast: bool = False,
    channel: Optional[str] = None,
    current_user = Depends(deps.get_current_active_user)
):
    """发送通知API"""
    try:
        # 创建通知消息
        notification = NotificationMessage(
            title=notification_data.get("title", "Notification"),
            message=notification_data.get("message", ""),
            notification_type=notification_data.get("type", "info"),
            category=notification_data.get("category"),
            action_url=notification_data.get("action_url"),
            data=notification_data.get("data", {}),
            user_id=target_user_id or str(current_user.id)
        )
        
        sent_count = 0
        
        if broadcast:
            # 广播给所有用户
            sent_count = await enhanced_manager.broadcast_to_all(notification)
        elif channel:
            # 发送到指定频道
            sent_count = await enhanced_manager.broadcast_to_channel(channel, notification)
        elif target_user_id:
            # 发送给指定用户
            sent_count = await enhanced_manager.send_to_user(target_user_id, notification)
        else:
            # 发送给当前用户
            sent_count = await enhanced_manager.send_to_user(str(current_user.id), notification)
        
        return create_success_response(
            data={
                "sent_count": sent_count,
                "notification_id": notification.id
            },
            message=f"Notification sent to {sent_count} connections"
        )
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return create_error_response(
            error="NOTIFICATION_SEND_ERROR",
            message="Failed to send notification"
        )


@router.post("/subscribe")
async def subscribe_to_channel(
    channel: str,
    session_id: Optional[str] = None,
    current_user = Depends(deps.get_current_active_user)
):
    """订阅频道"""
    try:
        user_id = str(current_user.id)
        
        if session_id:
            # 指定会话订阅
            success = await enhanced_manager.subscribe(session_id, channel)
            if not success:
                return create_error_response(
                    error="SESSION_NOT_FOUND",
                    message="Session not found"
                )
        else:
            # 用户所有会话订阅
            user_sessions = enhanced_manager.user_sessions.get(user_id, set())
            success_count = 0
            for sid in user_sessions:
                if await enhanced_manager.subscribe(sid, channel):
                    success_count += 1
            
            if success_count == 0:
                return create_error_response(
                    error="NO_ACTIVE_SESSIONS",
                    message="No active sessions found"
                )
        
        return create_success_response(
            data={"channel": channel},
            message="Successfully subscribed to channel"
        )
        
    except Exception as e:
        logger.error(f"Error subscribing to channel: {e}")
        return create_error_response(
            error="SUBSCRIPTION_ERROR",
            message="Failed to subscribe to channel"
        )


@router.post("/unsubscribe")
async def unsubscribe_from_channel(
    channel: str,
    session_id: Optional[str] = None,
    current_user = Depends(deps.get_current_active_user)
):
    """取消订阅频道"""
    try:
        user_id = str(current_user.id)
        
        if session_id:
            # 指定会话取消订阅
            success = await enhanced_manager.unsubscribe(session_id, channel)
            if not success:
                return create_error_response(
                    error="SESSION_NOT_FOUND", 
                    message="Session not found"
                )
        else:
            # 用户所有会话取消订阅
            user_sessions = enhanced_manager.user_sessions.get(user_id, set())
            for sid in user_sessions:
                await enhanced_manager.unsubscribe(sid, channel)
        
        return create_success_response(
            data={"channel": channel},
            message="Successfully unsubscribed from channel"
        )
        
    except Exception as e:
        logger.error(f"Error unsubscribing from channel: {e}")
        return create_error_response(
            error="UNSUBSCRIPTION_ERROR",
            message="Failed to unsubscribe from channel"
        )


@router.get("/connections")
async def get_user_connections(
    current_user = Depends(deps.get_current_active_user)
):
    """获取用户连接信息"""
    try:
        connections = enhanced_manager.get_user_connections(str(current_user.id))
        
        return create_success_response(
            data={
                "connections": connections,
                "total_connections": len(connections)
            },
            message="User connections retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting user connections: {e}")
        return create_error_response(
            error="CONNECTIONS_ERROR",
            message="Failed to get user connections"
        )


@router.delete("/connections/{session_id}")
async def disconnect_session(
    session_id: str,
    current_user = Depends(deps.get_current_active_user)
):
    """断开指定会话"""
    try:
        # 验证会话属于当前用户
        conn_info = enhanced_manager.get_connection_info(session_id)
        if not conn_info or conn_info["user_id"] != str(current_user.id):
            return create_error_response(
                error="SESSION_NOT_FOUND",
                message="Session not found or access denied"
            )
        
        # 强制断开连接
        await enhanced_manager._force_disconnect(session_id, "user_requested")
        
        return create_success_response(
            data={"session_id": session_id},
            message="Session disconnected successfully"
        )
        
    except Exception as e:
        logger.error(f"Error disconnecting session: {e}")
        return create_error_response(
            error="DISCONNECT_ERROR", 
            message="Failed to disconnect session"
        )


# ============================================================================
# 系统管理API（需要管理员权限）
# ============================================================================

@router.get("/admin/system-stats")
async def get_system_stats(
    current_user = Depends(deps.get_current_active_superuser)
):
    """获取系统统计信息（管理员）"""
    try:
        stats = enhanced_manager.get_system_stats()
        
        # 获取详细连接信息
        all_connections = []
        for session_id, conn in enhanced_manager.connections.items():
            all_connections.append(conn.to_dict())
        
        return create_success_response(
            data={
                "system_stats": stats,
                "all_connections": all_connections,
                "channels": {
                    channel: len(sessions)
                    for channel, sessions in enhanced_manager.channels.items()
                }
            },
            message="System statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return create_error_response(
            error="SYSTEM_STATS_ERROR",
            message="Failed to get system statistics"
        )


@router.post("/admin/broadcast")
async def broadcast_admin_message(
    message_data: Dict[str, Any],
    current_user = Depends(deps.get_current_active_superuser)
):
    """管理员广播消息"""
    try:
        notification = NotificationMessage(
            title=message_data.get("title", "System Notification"),
            message=message_data.get("message", ""),
            notification_type=message_data.get("type", "info"),
            category="admin_broadcast",
            data={
                "sender": str(current_user.id),
                "sender_name": current_user.full_name or current_user.username,
                **message_data.get("data", {})
            }
        )
        
        sent_count = await enhanced_manager.broadcast_to_all(notification)
        
        return create_success_response(
            data={
                "sent_count": sent_count,
                "notification_id": notification.id
            },
            message=f"Admin message broadcasted to {sent_count} connections"
        )
        
    except Exception as e:
        logger.error(f"Error broadcasting admin message: {e}")
        return create_error_response(
            error="BROADCAST_ERROR",
            message="Failed to broadcast message"
        )


# ============================================================================
# 消息处理器注册
# ============================================================================

async def handle_client_ping(session_id: str, message: WebSocketMessage):
    """处理客户端ping"""
    logger.debug(f"Received ping from session {session_id}")

async def handle_subscription_request(session_id: str, message: WebSocketMessage):
    """处理订阅请求"""
    channel = message.data.get("channel")
    if channel:
        await enhanced_manager.subscribe(session_id, channel)
        logger.debug(f"Session {session_id} subscribed to {channel}")

# 注册消息处理器
enhanced_manager.register_message_handler(WebSocketMessageType.PING, handle_client_ping)
enhanced_manager.register_global_handler(handle_subscription_request)