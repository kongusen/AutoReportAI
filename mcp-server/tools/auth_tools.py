"""
Authentication Tools for AutoReportAI MCP Server
用户认证和会话管理工具
"""

import json
from typing import Optional
from client import api_client, APIError
from session import session_manager
from config import config

async def login(username: str = None, password: str = None) -> str:
    """
    用户登录AutoReportAI系统
    
    Args:
        username: 用户名，为空时使用默认管理员账户
        password: 密码，为空时使用默认管理员密码
    
    Returns:
        登录结果和会话信息的JSON格式
    """
    try:
        # 使用默认值或提供的凭据
        username = username or config.DEFAULT_ADMIN_USERNAME
        password = password or config.DEFAULT_ADMIN_PASSWORD
        
        result = await api_client.login(username, password)
        
        return json.dumps({
            "success": True,
            "message": "登录成功",
            "data": {
                "session_id": result.get("session_id"),
                "username": username,
                "email": result.get("email"),
                "full_name": result.get("full_name"),
                "permissions": result.get("permissions", [])
            }
        }, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"登录失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"登录异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def logout(session_id: str = None) -> str:
    """
    用户登出系统
    
    Args:
        session_id: 会话ID，为空时登出当前会话
    
    Returns:
        登出结果的JSON格式
    """
    try:
        result = await api_client.logout(session_id)
        
        return json.dumps({
            "success": True,
            "message": "登出成功"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"登出失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def get_current_user(session_id: str = None) -> str:
    """
    获取当前登录用户信息
    
    Args:
        session_id: 会话ID，为空时获取当前会话用户
    
    Returns:
        用户信息的JSON格式
    """
    try:
        # 先从本地会话获取基本信息
        session = session_manager.get_session(session_id)
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        # 从后端获取最新用户信息
        try:
            backend_user = await api_client.get_current_user(session_id)
            user_info = backend_user.get("data", {})
        except APIError:
            # 后端获取失败时使用会话信息
            user_info = {
                "id": session.user_id,
                "username": session.username,
                "email": session.email,
                "full_name": session.full_name,
                "permissions": session.permissions
            }
        
        return json.dumps({
            "success": True,
            "data": {
                "session_info": session.to_dict(),
                "user_info": user_info
            }
        }, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"获取用户信息失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取用户信息异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def switch_user(session_id: str) -> str:
    """
    切换到指定用户会话（管理员功能）
    
    Args:
        session_id: 目标会话ID
    
    Returns:
        切换结果的JSON格式
    """
    try:
        # 检查当前用户是否为管理员
        current_session = session_manager.get_current_session()
        if not current_session or not session_manager.is_admin():
            return json.dumps({
                "success": False,
                "error": "需要管理员权限"
            }, ensure_ascii=False, indent=2)
        
        # 切换会话
        if session_manager.switch_session(session_id):
            target_session = session_manager.get_session(session_id)
            return json.dumps({
                "success": True,
                "message": f"已切换到用户: {target_session.username}",
                "data": target_session.to_dict()
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": "目标会话不存在或已过期"
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"切换用户失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def list_sessions() -> str:
    """
    列出所有活跃用户会话（管理员功能）
    
    Returns:
        会话列表的JSON格式
    """
    try:
        # 检查管理员权限
        if not session_manager.is_admin():
            return json.dumps({
                "success": False,
                "error": "需要管理员权限"
            }, ensure_ascii=False, indent=2)
        
        sessions = session_manager.list_sessions()
        
        return json.dumps({
            "success": True,
            "data": {
                "sessions": sessions,
                "total": len(sessions),
                "current_session": session_manager._current_session_id
            }
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取会话列表失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def refresh_session(session_id: str = None) -> str:
    """
    刷新用户会话
    
    Args:
        session_id: 会话ID，为空时刷新当前会话
    
    Returns:
        刷新结果的JSON格式
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            return json.dumps({
                "success": False,
                "error": "会话不存在或已过期"
            }, ensure_ascii=False, indent=2)
        
        # 尝试从后端获取最新用户信息来验证token
        try:
            await api_client.get_current_user(session_id)
            session.update_activity()
            
            return json.dumps({
                "success": True,
                "message": "会话刷新成功",
                "data": session.to_dict()
            }, ensure_ascii=False, indent=2)
            
        except APIError as e:
            if e.status_code == 401:
                # Token已过期，删除会话
                session_manager.remove_session(session_id)
                return json.dumps({
                    "success": False,
                    "error": "会话已过期，请重新登录"
                }, ensure_ascii=False, indent=2)
            else:
                raise
                
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"会话刷新失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"会话刷新异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def get_session_status() -> str:
    """
    获取会话管理器状态
    
    Returns:
        状态信息的JSON格式
    """
    try:
        current_session = session_manager.get_current_session()
        
        return json.dumps({
            "success": True,
            "data": {
                "total_sessions": session_manager.get_session_count(),
                "max_sessions": config.MAX_SESSIONS,
                "session_timeout": config.SESSION_TIMEOUT,
                "current_session": current_session.to_dict() if current_session else None,
                "has_admin_session": session_manager.is_admin()
            }
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取状态失败: {str(e)}"
        }, ensure_ascii=False, indent=2)