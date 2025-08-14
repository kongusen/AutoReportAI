import redis.asyncio as redis
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi_limiter import FastAPILimiter

from app.api.router import api_router
from app.api.versioning import APIVersionMiddleware
from app.core.config import settings
from app.core.logging_config import setup_logging, RequestLoggingMiddleware
from app.core.exception_handlers import setup_exception_handlers
from app.websocket.router import router as websocket_router

# Setup logging as soon as the application starts
setup_logging()

def print_startup_config():
    """启动时打印简化的配置信息"""
    print("🚀 AutoReportAI 启动成功")
    print("-" * 50)
    
    # 获取前端地址
    cors_origins = getattr(settings, "CORS_ORIGINS", "http://localhost:3000").split(",")
    frontend_url = cors_origins[0].strip() if cors_origins else "http://localhost:3000"
    
    # 打印前后端地址
    print(f"📱 前端地址: {frontend_url}")
    print(f"🔗 后端API: {settings.API_BASE_URL}{settings.API_V1_STR}")
    print(f"🌐 WebSocket: ws://localhost:{getattr(settings, 'WS_PORT', 8000)}/ws")
    print(f"📋 API文档: {settings.API_BASE_URL}/docs")
    print(f"🔧 运行环境: {settings.ENVIRONMENT}")
    print("-" * 50)

def print_all_settings_values():
    """打印Settings的所有配置项（敏感信息脱敏）"""
    try:
        print("=" * 80)
        print("🧩 Settings 全量配置值（启动时）")
        print("=" * 80)
        
        # 收集并排序，保证输出稳定
        keys = [k for k in dir(settings) if not k.startswith('_') and not callable(getattr(settings, k, None))]
        for key in sorted(keys):
            try:
                value = getattr(settings, key)
                # 脱敏处理
                lower_key = key.lower()
                if any(s in lower_key for s in ["password", "secret", "key", "token"]):
                    if isinstance(value, str) and len(value) > 8:
                        display_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
                    else:
                        display_value = "*" * len(str(value)) if value else "None"
                else:
                    display_value = value
                print(f"{key:<30} = {display_value}")
            except Exception as inner_e:
                print(f"{key:<30} = Error: {inner_e}")
        print("=" * 80)
        print("✅ Settings 全量配置打印完成")
        print("=" * 80)
    except Exception as e:
        print(f"⚠️ 打印Settings失败: {e}")

def create_application() -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(
        title="AutoReportAI API",
        description="""
        ## AutoReportAI 智能报告生成系统API

        这是一个基于AI的智能报告生成系统，提供以下核心功能：

        ### 🔐 认证与授权
        * 用户注册、登录、密码重置
        * JWT token认证
        * 角色权限管理
        
        ### 📊 数据源管理
        * 多种数据源连接（数据库、API、文件）
        * 数据源配置与验证
        * 数据预处理和清洗
        
        ### 🤖 AI服务集成
        * 多AI提供商支持（OpenAI、Claude、本地模型）
        * 智能数据分析
        * 自动图表生成
        
        ### 📝 报告生成
        * 模板化报告生成
        * 智能占位符匹配
        * 多格式输出支持
        
        ### 🔄 ETL任务管理
        * 数据提取、转换、加载
        * 任务调度与监控
        * 数据质量检查
        
        ## 🚀 快速开始
        
        1. 获取API访问令牌
        2. 配置数据源
        3. 创建报告模板
        4. 生成报告
        
        ## 📋 API版本
        
        当前版本：v1.0.0
        
        ## 🔗 相关链接
        
        * [GitHub仓库](https://github.com/your-org/AutoReportAI)
        * [用户指南](https://docs.autoreportai.com)
        * [API最佳实践](https://docs.autoreportai.com/api/best-practices)
    """,
        version="1.0.0",
        contact={
            "name": "AutoReportAI Team",
            "email": "support@autoreportai.com",
            "url": "https://autoreportai.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        servers=[
            {
                "url": "https://api.autoreportai.com",
                "description": "生产环境"
            },
            {
                "url": "https://staging-api.autoreportai.com", 
                "description": "测试环境"
            },
            {
                "url": "http://localhost:8000",
                "description": "本地开发环境"
            }
        ],
        openapi_tags=[
            {
                "name": "认证",
                "description": "用户认证与授权相关操作"
            },
            {
                "name": "用户管理",
                "description": "用户信息管理"
            },
            {
                "name": "数据源",
                "description": "数据源连接与管理"
            },
            {
                "name": "AI服务",
                "description": "AI提供商与AI服务管理"
            },
            {
                "name": "模板",
                "description": "报告模板管理"
            },
            {
                "name": "任务",
                "description": "任务创建与管理"
            },
            {
                "name": "ETL",
                "description": "数据提取、转换、加载"
            },
            {
                "name": "报告",
                "description": "报告生成与历史记录"
            },
            {
                "name": "系统",
                "description": "系统状态与健康检查"
            }
        ]
    )

    # Setup exception handlers
    setup_exception_handlers(app)

    # Add API versioning middleware
    app.add_middleware(APIVersionMiddleware)

    # Add request logging middleware (before CORS)
    app.add_middleware(RequestLoggingMiddleware)

    # CORS 配置 - 从环境变量动态配置
    origins = []
    if hasattr(settings, "CORS_ORIGINS") and settings.CORS_ORIGINS:
        origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
    
    # 默认前端地址（如果环境变量未配置）
    if not origins:
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=getattr(settings, "CORS_ORIGIN_REGEX", None),
        allow_credentials=getattr(settings, "CORS_ALLOW_CREDENTIALS", True),
        allow_methods=getattr(settings, "CORS_ALLOW_METHODS", ["*"]),
        allow_headers=getattr(settings, "CORS_ALLOW_HEADERS", ["*"]),
    )

    # 自定义OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            servers=app.servers,
            tags=app.openapi_tags
        )
        
        # 添加安全定义
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "请在请求头中添加 'Authorization: Bearer <token>'"
            }
        }
        
        # 添加全局安全要求
        openapi_schema["security"] = [{"BearerAuth": []}]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app


# 创建应用实例
app = create_application()



@app.on_event("startup")
async def startup():

    redis_connection = redis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    await FastAPILimiter.init(redis_connection)
    

    # 启动时打印关键配置
    print_startup_config()
    # 如需查看详细配置，可取消下行注释
    # print_all_settings_values()


@app.on_event("shutdown")
async def shutdown():

    pass


# All API routes are handled by the api_router
app.include_router(api_router, prefix="/api")

# WebSocket routes
app.include_router(websocket_router)


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
