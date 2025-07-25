"""
优化的API层包
提供统一的API路由管理
"""

from fastapi import APIRouter

from .base_router import BaseRouter, APIResponse, PaginatedResponse
from .data_sources import router as data_sources_router
from .reports import router as reports_router

# 导出基础类和响应模型
__all__ = [
    "BaseRouter",
    "APIResponse", 
    "PaginatedResponse",
    "optimized_api_router"
]


def create_optimized_api_router() -> APIRouter:
    """创建优化的API路由器"""
    router = APIRouter(prefix="/v2", tags=["API v2 - 优化版本"])
    
    # 注册各个模块的路由
    router.include_router(data_sources_router, prefix="/api/v2")
    router.include_router(reports_router, prefix="/api/v2")
    
    # 添加健康检查端点
    @router.get("/health", response_model=APIResponse)
    async def health_check():
        """健康检查"""
        return APIResponse(
            message="API服务运行正常",
            data={
                "version": "2.0",
                "status": "healthy",
                "features": [
                    "优化的数据层架构",
                    "统一的服务层管理", 
                    "标准化的API响应",
                    "完整的错误处理",
                    "性能监控和日志"
                ]
            }
        )
    
    # 添加API信息端点
    @router.get("/info", response_model=APIResponse)
    async def api_info():
        """API信息"""
        return APIResponse(
            message="优化API信息",
            data={
                "name": "AutoReportAI Optimized API",
                "version": "2.0.0",
                "description": "优化后的智能报告生成系统API",
                "features": {
                    "data_layer": "统一模型基类，软删除，审计日志",
                    "service_layer": "标准化服务接口，错误处理，权限验证",
                    "api_layer": "RESTful设计，分页响应，批量操作",
                    "performance": "批处理优化，查询优化，异步处理",
                    "integrations": "Doris数据仓库，MCP工具链，AI服务"
                },
                "endpoints": {
                    "data_sources": "/api/v2/data-sources",
                    "reports": "/api/v2/reports", 
                    "templates": "/api/v2/templates",
                    "tasks": "/api/v2/tasks",
                    "users": "/api/v2/users"
                }
            }
        )
    
    return router


# 创建优化的API路由器实例
optimized_api_router = create_optimized_api_router()