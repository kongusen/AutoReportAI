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
        logger.info(f"正在验证WebSocket token: {token[:20]}...")
        payload = decode_access_token(token)
        logger.info(f"Token解码结果: {payload}")
        
        if payload is None:
            logger.warning("Token解码失败: payload为None")
            return None

        user_id = payload.get("sub")
        logger.info(f"从token中提取的用户ID: {user_id}")
        
        if user_id is None:
            logger.warning("Token中没有找到sub字段")
            return None

        from app.crud.crud_user import crud_user

        user = crud_user.get(db, id=user_id)
        if user:
            logger.info(f"找到用户: {user.id}")
        else:
            logger.warning(f"未找到用户ID为 {user_id} 的用户")
        return user
    except Exception as e:
        logger.error(f"WebSocket token验证异常: {e}")
        import traceback
        traceback.print_exc()
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None, db: Session = Depends(deps.get_db)):
    """WebSocket连接端点"""
    user_id = None

    try:
        logger.info(f"WebSocket连接请求，查询参数token: {token[:20] if token else 'None'}...")
        
        # 首先尝试从查询参数获取token
        query_token = token
        
        await websocket.accept()
        logger.info("WebSocket连接已接受")
        
        # 如果没有查询参数token，等待认证消息
        if not query_token:
            logger.info("没有查询参数token，等待认证消息...")
            auth_message = await websocket.receive_text()
            logger.info(f"收到认证消息: {auth_message}")
            auth_data = json.loads(auth_message)

            if auth_data.get("type") != "auth":
                logger.warning(f"收到非认证消息: {auth_data.get('type')}")
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Authentication required"})
                )
                await websocket.close()
                return

            query_token = auth_data.get("token")
            logger.info(f"从认证消息中提取token: {query_token[:20] if query_token else 'None'}...")

        if not query_token:
            logger.warning("没有提供token")
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Token required"})
            )
            await websocket.close()
            return

        # 验证用户
        logger.info("开始验证用户token...")
        user = await get_current_user_from_token(query_token, db)
        if not user:
            logger.warning("用户token验证失败")
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Invalid token"})
            )
            await websocket.close()
            return

        user_id = str(user.id)
        logger.info(f"WebSocket用户认证成功: {user_id}")

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
