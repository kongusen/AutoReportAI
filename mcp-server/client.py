"""
AutoReportAI API Client
与后端API交互的客户端类
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
import httpx
from config import config
from session import session_manager, UserSession

class APIError(Exception):
    """API错误异常"""
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(message)

class AutoReportAIClient:
    """AutoReportAI后端API客户端"""
    
    def __init__(self):
        self.base_url = config.BACKEND_BASE_URL
        self.timeout = config.BACKEND_TIMEOUT
        self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端实例"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client
    
    async def close(self):
        """关闭客户端连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_headers(self, session: UserSession = None) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        
        if session is None:
            session = session_manager.get_current_session()
        
        if session and session.access_token:
            headers["Authorization"] = f"Bearer {session.access_token}"
        
        return headers
    
    async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """处理API响应"""
        try:
            data = response.json()
        except Exception:
            data = {"error": response.text}
        
        if response.status_code >= 400:
            error_message = data.get("detail", data.get("message", f"HTTP {response.status_code}"))
            raise APIError(
                message=error_message,
                status_code=response.status_code,
                response_data=data
            )
        
        return data
    
    async def _request(self, method: str, endpoint: str, session: UserSession = None, 
                      **kwargs) -> Dict[str, Any]:
        """发送HTTP请求"""
        client = await self._get_client()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers(session)
        
        # 合并自定义headers
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            return await self._handle_response(response)
        
        except httpx.TimeoutException:
            raise APIError("请求超时")
        except httpx.ConnectError:
            raise APIError("无法连接到服务器")
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"请求失败: {str(e)}")
    
    async def get(self, endpoint: str, session: UserSession = None, **kwargs) -> Dict[str, Any]:
        """GET请求"""
        return await self._request("GET", endpoint, session, **kwargs)
    
    async def post(self, endpoint: str, session: UserSession = None, **kwargs) -> Dict[str, Any]:
        """POST请求"""
        return await self._request("POST", endpoint, session, **kwargs)
    
    async def put(self, endpoint: str, session: UserSession = None, **kwargs) -> Dict[str, Any]:
        """PUT请求"""
        return await self._request("PUT", endpoint, session, **kwargs)
    
    async def delete(self, endpoint: str, session: UserSession = None, **kwargs) -> Dict[str, Any]:
        """DELETE请求"""
        return await self._request("DELETE", endpoint, session, **kwargs)
    
    async def patch(self, endpoint: str, session: UserSession = None, **kwargs) -> Dict[str, Any]:
        """PATCH请求"""
        return await self._request("PATCH", endpoint, session, **kwargs)
    
    # 认证相关方法
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        data = {
            "username": username,
            "password": password,
            "grant_type": "password"
        }
        
        try:
            response = await self._request(
                "POST", 
                "auth/login",
                session=None,  # 登录时不需要session
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # 创建会话
            if response.get("access_token"):
                user_data = {
                    "id": response.get("user_id"),
                    "username": username,
                    "email": response.get("email"),
                    "full_name": response.get("full_name"),
                    "permissions": response.get("permissions", [])
                }
                
                session_id = session_manager.create_session(
                    user_data, 
                    response["access_token"]
                )
                
                response["session_id"] = session_id
            
            return response
            
        except APIError:
            raise
    
    async def logout(self, session_id: str = None) -> Dict[str, Any]:
        """用户登出"""
        session = session_manager.get_session(session_id)
        
        try:
            # 调用后端登出接口
            if session:
                await self._request("POST", "auth/logout", session)
        except Exception:
            # 即使后端登出失败，也要清理本地会话
            pass
        finally:
            # 清理本地会话
            session_manager.remove_session(session_id)
        
        return {"success": True, "message": "登出成功"}
    
    async def get_current_user(self, session_id: str = None) -> Dict[str, Any]:
        """获取当前用户信息"""
        session = session_manager.get_session(session_id)
        if not session:
            raise APIError("未登录或会话已过期")
        
        try:
            return await self._request("GET", "auth/me", session)
        except APIError as e:
            if e.status_code == 401:
                # Token已过期，清理会话
                session_manager.remove_session(session_id)
            raise
    
    # 文件上传辅助方法
    async def upload_file(self, endpoint: str, file_path: str, 
                         session: UserSession = None, **kwargs) -> Dict[str, Any]:
        """上传文件"""
        if not os.path.exists(file_path):
            raise APIError("文件不存在")
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > config.MAX_FILE_SIZE:
            raise APIError(f"文件大小超出限制 ({config.MAX_FILE_SIZE / 1024 / 1024:.1f}MB)")
        
        # 检查文件扩展名
        if not config.validate_file_extension(file_path):
            raise APIError(f"不支持的文件类型，允许的扩展名: {config.ALLOWED_FILE_EXTENSIONS}")
        
        if session is None:
            session = session_manager.get_current_session()
        
        if not session:
            raise APIError("未登录或会话已过期")
        
        client = await self._get_client()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # 准备文件和headers
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            headers = {"Authorization": f"Bearer {session.access_token}"}
            
            # 添加额外的headers
            if "headers" in kwargs:
                headers.update(kwargs.pop("headers"))
            
            try:
                response = await client.put(url, files=files, headers=headers, **kwargs)
                return await self._handle_response(response)
            except httpx.TimeoutException:
                raise APIError("文件上传超时")
            except Exception as e:
                raise APIError(f"文件上传失败: {str(e)}")

# 全局客户端实例
api_client = AutoReportAIClient()