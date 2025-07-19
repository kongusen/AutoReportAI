import json
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import decode_access_token
from app.websocket.manager import NotificationMessage, manager

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


async def get_current_user_from_token(token: str, db: Session):
    """从WebSocket token中获取当前用户"""
    try:
        payload = decode_access_token(token)
        if payload is None:
            return None

        username = payload.get("sub")
        if username is None:
            return None

        from app import crud

        user = crud.user.get_by_username(db, username=username)
        return user
    except Exception as e:
        logger.error(f"Error decoding WebSocket token: {e}")
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(deps.get_db)):
    """WebSocket连接端点"""
    user_id = None

    try:
        await websocket.accept()

        # 等待认证消息
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)

        if auth_data.get("type") != "auth":
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Authentication required"})
            )
            await websocket.close()
            return

        token = auth_data.get("token")
        if not token:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Token required"})
            )
            await websocket.close()
            return

        # 验证用户
        user = await get_current_user_from_token(token, db)
        if not user:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Invalid token"})
            )
            await websocket.close()
            return

        user_id = str(user.id)

        # 建立连接
        await manager.connect(websocket, user_id)

        # 保持连接活跃
        while True:
            try:
                # 接收客户端消息（心跳包等）
                message = await websocket.receive_text()
                data = json.loads(message)

                # 处理心跳包
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in manager.connection_user_map:
            manager.disconnect(websocket)


@router.post("/notifications/send")
async def send_notification(
    notification_data: dict, current_user=Depends(deps.get_current_active_user)
):
    """发送通知API（用于测试）"""
    try:
        notification = NotificationMessage(
            type=notification_data.get("type", "info"),
            title=notification_data.get("title", "Test Notification"),
            message=notification_data.get("message", "This is a test notification"),
            data=notification_data.get("data"),
            user_id=str(current_user.id),
        )

        if notification_data.get("broadcast", False):
            await manager.broadcast_message(notification)
        else:
            await manager.send_personal_message(notification, str(current_user.id))

        return {"message": "Notification sent successfully"}
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification")


@router.get("/notifications/status")
async def get_notification_status(current_user=Depends(deps.get_current_active_user)):
    """获取通知系统状态"""
    return {
        "connected_users": manager.get_connected_users(),
        "is_connected": manager.is_user_connected(str(current_user.id)),
        "total_connections": sum(
            len(connections) for connections in manager.active_connections.values()
        ),
    }
