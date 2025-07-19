from fastapi import APIRouter, Depends

from app.api import deps
from app.api.versioning import create_versioned_router, create_version_info_router, APIVersion
from app.api.endpoints import (
    ai_providers,
    analysis,
    data_sources,
    email_settings,
    enhanced_data_sources,
    etl_jobs,
    history,
    intelligent_placeholders,
    learning,
    login,
    mcp_analytics,
    report_generation,
    tasks,
    template_analysis,
    templates,
    user_profile,
    users,
)

# 创建主API路由器
api_router = APIRouter()

# 添加版本信息路由（不带版本前缀）
api_router.include_router(create_version_info_router())

# V1 API端点 - 直接添加到主路由器，不使用额外的版本前缀
api_router.include_router(login.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(
    ai_providers.router, prefix="/ai-providers", tags=["AI提供商"]
)
api_router.include_router(
    data_sources.router, prefix="/data-sources", tags=["数据源管理"]
)
api_router.include_router(
    enhanced_data_sources.router,
    prefix="/enhanced-data-sources",
    tags=["增强数据源"],
)
api_router.include_router(
    mcp_analytics.router, prefix="/mcp-analytics", tags=["MCP分析"]
)
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(etl_jobs.router, prefix="/etl-jobs", tags=["ETL作业"])
api_router.include_router(
    report_generation.router, prefix="/reports", tags=["报告生成"]
)
api_router.include_router(
    template_analysis.router, prefix="/template-analysis", tags=["模板分析"]
)
api_router.include_router(history.router, prefix="/history", tags=["历史记录"])
api_router.include_router(
    user_profile.router, prefix="/user-profile", tags=["用户配置"]
)
api_router.include_router(templates.router, prefix="/templates", tags=["模板管理"])
api_router.include_router(
    email_settings.router, prefix="/email-settings", tags=["邮件设置"]
)
api_router.include_router(learning.router, prefix="/learning", tags=["学习功能"])
api_router.include_router(
    intelligent_placeholders.router,
    prefix="/intelligent-placeholders",
    tags=["智能占位符"],
)
api_router.include_router(analysis.router, prefix="/analysis", tags=["数据分析"])

# 添加版本和健康检查端点
@api_router.get("/version")
async def get_api_version():
    """获取API版本信息"""
    from app.api.versioning import version_manager
    return {
        "version": "v1",
        "status": "active",
        "supported_versions": ["v1"],
        "current_version": version_manager.current_version.value
    }

@api_router.get("/health")
async def health_check():
    """基础API健康检查"""
    from datetime import datetime
    return {
        "status": "healthy",
        "version": "v1",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "API is operational"
    }

@api_router.get("/health/detailed")
async def detailed_health_check(
    health_status: dict = Depends(deps.get_all_services_health)
):
    """详细的服务健康检查"""
    return health_status

@api_router.get("/health/services")
async def services_health_check(
    db: deps.Session = Depends(deps.get_db)
):
    """服务模块健康检查"""
    from datetime import datetime
    
    services_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Test each service module
    service_tests = [
        ("intelligent_placeholder", deps.get_placeholder_processor),
        ("report_generation", lambda: deps.get_report_generation_service(db)),
        ("data_processing", lambda: deps.get_data_retrieval_service()),
        ("ai_integration", lambda: deps.get_enhanced_ai_service(db)),
        ("notification", lambda: deps.get_email_service(db)),
    ]
    
    overall_healthy = True
    
    for service_name, service_getter in service_tests:
        try:
            if service_name == "intelligent_placeholder":
                service_instance = service_getter()
            else:
                service_instance = service_getter()
            
            services_status["services"][service_name] = {
                "status": "healthy",
                "message": f"{service_name} service is available"
            }
        except Exception as e:
            services_status["services"][service_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
    
    services_status["overall_status"] = "healthy" if overall_healthy else "degraded"
    return services_status

@api_router.get("/health/database")
async def database_health_check(db: deps.Session = Depends(deps.get_db)):
    """数据库连接健康检查"""
    from datetime import datetime
    from sqlalchemy import text
    
    try:
        # Test basic connection
        db.execute(text("SELECT 1"))
        
        # Test table access (basic query)
        from app.models.user import User
        user_count = db.query(User).count()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "connection": "successful",
                "basic_query": "successful",
                "user_count": user_count
            },
            "message": "Database is operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Database connection failed"
        }
