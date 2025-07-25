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
from app.initial_data import init_db
from app.websocket.router import router as websocket_router

# Setup logging as soon as the application starts
setup_logging()

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

    # CORS 配置
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

# Enhanced FastAPI app configuration with comprehensive documentation
# app = FastAPI(
#     title=settings.PROJECT_NAME,
#     description="""
#     ## AutoReportAI - 智能报告生成系统

#     AutoReportAI是一个基于人工智能的智能报告生成系统，提供以下核心功能：

#     ### �� 核心功能
#     - **智能占位符处理**: 自动识别和处理模板中的占位符
#     - **数据源集成**: 支持多种数据源的连接和数据提取
#     - **AI驱动的内容生成**: 使用大语言模型生成高质量报告内容
#     - **模板管理**: 灵活的报告模板创建和管理
#     - **自动化报告生成**: 端到端的自动化报告生成流程

#     ### �� 智能占位符系统
#     支持多种类型的智能占位符：
#     - **统计类**: `{{统计:投诉总数}}` - 自动计算统计数据
#     - **区域类**: `{{区域:主要投诉地区}}` - 地理位置相关分析
#     - **周期类**: `{{周期:本月}}` - 时间周期相关数据
#     - **图表类**: `{{图表:投诉趋势图}}` - 自动生成数据可视化

#     ### 🔧 技术特性
#     - RESTful API设计
#     - 异步处理支持
#     - 实时WebSocket通信
#     - 缓存优化
#     - 错误处理和日志记录
#     - API版本控制
#     - 请求限流保护

#     ### 📚 API使用指南
#     1. **认证**: 所有API请求需要有效的JWT令牌
#     2. **版本控制**: 当前API版本为v1，通过URL路径指定
#     3. **错误处理**: 统一的错误响应格式
#     4. **分页**: 列表接口支持skip和limit参数
#     5. **过滤**: 支持多种过滤条件

#     ### 🔐 安全性
#     - JWT令牌认证
#     - 请求速率限制
#     - 输入验证和清理
#     - SQL注入防护
#     - CORS配置

#     ### 📈 性能优化
#     - Redis缓存
#     - 数据库查询优化
#     - 异步处理
#     - 响应压缩

#     ---
    
#     **版本**: v1.0.0  
#     **文档更新**: 自动生成  
#     **支持**: 查看各个端点的详细文档和示例
#     """,
#     version="1.0.0",
#     terms_of_service="https://autoreportai.com/terms",
#     contact={
#         "name": "AutoReportAI开发团队",
#         "url": "https://autoreportai.com/contact",
#         "email": "support@autoreportai.com",
#     },
#     license_info={
#         "name": "MIT License",
#         "url": "https://opensource.org/licenses/MIT",
#     },
#     openapi_tags=[
#         {
#             "name": "认证",
#             "description": "用户认证和授权相关接口",
#             "externalDocs": {
#                 "description": "认证文档",
#                 "url": "https://autoreportai.com/docs/auth",
#             },
#         },
#         {
#             "name": "用户管理",
#             "description": "用户账户管理接口",
#         },
#         {
#             "name": "模板管理",
#             "description": "报告模板的创建、编辑、删除和查询接口",
#             "externalDocs": {
#                 "description": "模板使用指南",
#                 "url": "https://autoreportai.com/docs/templates",
#             },
#         },
#         {
#             "name": "智能占位符",
#             "description": "智能占位符分析、字段匹配和处理接口",
#             "externalDocs": {
#                 "description": "占位符系统文档",
#                 "url": "https://autoreportai.com/docs/placeholders",
#             },
#         },
#         {
#             "name": "数据源管理",
#             "description": "数据源连接和管理接口",
#         },
#         {
#             "name": "增强数据源",
#             "description": "增强数据源功能和ETL处理接口",
#         },
#         {
#             "name": "报告生成",
#             "description": "智能报告生成和管理接口",
#             "externalDocs": {
#                 "description": "报告生成指南",
#                 "url": "https://autoreportai.com/docs/reports",
#             },
#         },
#         {
#             "name": "AI提供商",
#             "description": "AI服务提供商配置和管理接口",
#         },
#         {
#             "name": "任务管理",
#             "description": "后台任务管理和监控接口",
#         },
#         {
#             "name": "ETL作业",
#             "description": "数据提取、转换和加载作业管理接口",
#         },
#         {
#             "name": "数据分析",
#             "description": "数据分析和统计接口",
#         },
#         {
#             "name": "历史记录",
#             "description": "操作历史和审计日志接口",
#         },
#         {
#             "name": "用户配置",
#             "description": "用户个人配置和偏好设置接口",
#         },
#         {
#             "name": "邮件设置",
#             "description": "邮件通知配置接口",
#         },
#         {
#             "name": "学习功能",
#             "description": "机器学习和模型训练接口",
#         },
#         {
#             "name": "模板分析",
#             "description": "模板内容分析和优化建议接口",
#         },
#         {
#             "name": "MCP分析",
#             "description": "MCP (Model Context Protocol) 分析工具接口",
#         },
#         {
#             "name": "系统监控",
#             "description": "系统健康检查和监控接口",
#         },
#     ],
#     openapi_url=f"{settings.API_V1_STR}/openapi.json",
#     docs_url=f"{settings.API_V1_STR}/docs",
#     redoc_url=f"{settings.API_V1_STR}/redoc",
# )

# Setup exception handlers
# setup_exception_handlers(app)

# Add API versioning middleware
# app.add_middleware(APIVersionMiddleware)

# Add request logging middleware (before CORS)
# app.add_middleware(RequestLoggingMiddleware)

# CORS 配置
# origins = [
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


@app.on_event("startup")
async def startup():
    # setup_logging() # Can be called again if needed, it's idempotent
    init_db()
    redis_connection = redis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    await FastAPILimiter.init(redis_connection)


# All API routes are handled by the api_router
app.include_router(api_router)

# WebSocket routes
app.include_router(websocket_router)


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
