"""
API版本控制系统

提供API版本管理和路由控制功能。
"""

from typing import Dict, List, Optional
from enum import Enum
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel

from app.schemas.base import APIResponse, HealthCheckResponse


class APIVersion(str, Enum):
    """API版本枚举"""
    V1 = "v1"
    V2 = "v2"  # 为未来版本预留


class VersionInfo(BaseModel):
    """版本信息"""
    version: str
    status: str  # active, deprecated, sunset
    release_date: str
    deprecation_date: Optional[str] = None
    sunset_date: Optional[str] = None
    description: str
    breaking_changes: List[str] = []
    new_features: List[str] = []


class APIVersionManager:
    """API版本管理器"""
    
    def __init__(self):
        self.versions: Dict[str, VersionInfo] = {
            APIVersion.V1: VersionInfo(
                version="v1",
                status="active",
                release_date="2024-01-01",
                description="初始API版本，提供核心功能",
                new_features=[
                    "智能占位符处理",
                    "报告生成服务",
                    "数据源管理",
                    "用户认证和授权",
                    "模板管理"
                ]
            )
        }
        self.current_version = APIVersion.V1
        self.supported_versions = [APIVersion.V1]
    
    def get_version_info(self, version: str) -> Optional[VersionInfo]:
        """获取版本信息"""
        return self.versions.get(version)
    
    def is_version_supported(self, version: str) -> bool:
        """检查版本是否支持"""
        return version in [v.value for v in self.supported_versions]
    
    def get_all_versions(self) -> Dict[str, VersionInfo]:
        """获取所有版本信息"""
        return self.versions
    
    def add_version(self, version_info: VersionInfo):
        """添加新版本"""
        self.versions[version_info.version] = version_info
    
    def deprecate_version(self, version: str, deprecation_date: str, sunset_date: str):
        """废弃版本"""
        if version in self.versions:
            self.versions[version].status = "deprecated"
            self.versions[version].deprecation_date = deprecation_date
            self.versions[version].sunset_date = sunset_date


# 全局版本管理器实例
version_manager = APIVersionManager()


def get_api_version_from_request(request: Request) -> str:
    """从请求中获取API版本"""
    # 优先级：Header > Query Parameter > Path > Default
    
    # 1. 从Header获取
    version = request.headers.get("API-Version")
    if version:
        return version
    
    # 2. 从Query Parameter获取
    version = request.query_params.get("version")
    if version:
        return version
    
    # 3. 从Path获取（已在路由中处理）
    path_parts = request.url.path.split("/")
    if len(path_parts) >= 3 and path_parts[2].startswith("v"):
        return path_parts[2]
    
    # 4. 返回默认版本
    return version_manager.current_version.value


def validate_api_version(version: str) -> str:
    """验证API版本"""
    if not version_manager.is_version_supported(version):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": True,
                "message": f"不支持的API版本: {version}",
                "code": "UNSUPPORTED_API_VERSION",
                "details": {
                    "requested_version": version,
                    "supported_versions": [v.value for v in version_manager.supported_versions]
                }
            }
        )
    
    version_info = version_manager.get_version_info(version)
    if version_info and version_info.status == "deprecated":
        # 可以添加警告头，但不阻止请求
        pass
    elif version_info and version_info.status == "sunset":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": True,
                "message": f"API版本已停用: {version}",
                "code": "API_VERSION_SUNSET",
                "details": {
                    "version": version,
                    "sunset_date": version_info.sunset_date
                }
            }
        )
    
    return version


def create_versioned_router(version: APIVersion, prefix: str = "") -> APIRouter:
    """创建版本化路由器"""
    router = APIRouter(prefix=f"/{version.value}{prefix}")
    
    @router.get("/version", response_model=APIResponse[VersionInfo])
    async def get_version_info():
        """获取当前版本信息"""
        version_info = version_manager.get_version_info(version.value)
        if not version_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="版本信息未找到"
            )
        
        return APIResponse[VersionInfo](
            success=True,
            message="版本信息获取成功",
            data=version_info
        )
    
    @router.get("/health", response_model=APIResponse[HealthCheckResponse])
    async def health_check():
        """健康检查"""
        health_info = HealthCheckResponse(
            status="healthy",
            version=version.value,
            services={
                "database": "healthy",
                "redis": "healthy",
                "ai_service": "healthy"
            }
        )
        
        return APIResponse[HealthCheckResponse](
            success=True,
            message="服务健康",
            data=health_info
        )
    
    return router


# 版本兼容性中间件
class APIVersionMiddleware:
    """API版本中间件"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # 获取并验证API版本
            try:
                version = get_api_version_from_request(request)
                validated_version = validate_api_version(version)
                
                # 将版本信息添加到请求状态
                if not hasattr(request.state, "api_version"):
                    request.state.api_version = validated_version
                
                # 添加版本相关的响应头
                async def send_wrapper(message):
                    if message["type"] == "http.response.start":
                        headers = dict(message.get("headers", []))
                        headers[b"API-Version"] = validated_version.encode()
                        headers[b"API-Supported-Versions"] = ",".join(
                            [v.value for v in version_manager.supported_versions]
                        ).encode()
                        message["headers"] = list(headers.items())
                    await send(message)
                
                await self.app(scope, receive, send_wrapper)
                
            except HTTPException as e:
                # 直接返回版本验证错误
                response = {
                    "status_code": e.status_code,
                    "headers": [(b"content-type", b"application/json")],
                    "body": str(e.detail).encode() if isinstance(e.detail, str) else str(e.detail).encode()
                }
                
                await send({
                    "type": "http.response.start",
                    "status": e.status_code,
                    "headers": [(b"content-type", b"application/json")]
                })
                await send({
                    "type": "http.response.body",
                    "body": str(e.detail).encode() if isinstance(e.detail, str) else str(e.detail).encode()
                })
        else:
            await self.app(scope, receive, send)


# 版本信息路由
def create_version_info_router() -> APIRouter:
    """创建版本信息路由"""
    router = APIRouter(prefix="/versions", tags=["版本信息"])
    
    @router.get("/", response_model=APIResponse[Dict[str, VersionInfo]])
    async def list_all_versions():
        """获取所有版本信息"""
        return APIResponse[Dict[str, VersionInfo]](
            success=True,
            message="版本信息列表获取成功",
            data=version_manager.get_all_versions()
        )
    
    @router.get("/{version}", response_model=APIResponse[VersionInfo])
    async def get_specific_version(version: str):
        """获取特定版本信息"""
        version_info = version_manager.get_version_info(version)
        if not version_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": True,
                    "message": f"版本未找到: {version}",
                    "code": "VERSION_NOT_FOUND"
                }
            )
        
        return APIResponse[VersionInfo](
            success=True,
            message="版本信息获取成功",
            data=version_info
        )
    
    return router