import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter

from app.api.router import api_router
from app.api.versioning import APIVersionMiddleware, create_version_info_router
from app.core.config import settings
from app.core.logging_config import setup_logging, RequestLoggingMiddleware
from app.core.exception_handlers import setup_exception_handlers
from app.websocket.router import router as websocket_router

# 修复 bcrypt 兼容性问题
def fix_bcrypt_compatibility():
    """修复 bcrypt 兼容性问题"""
    try:
        import bcrypt
        if not hasattr(bcrypt, '__about__'):
            class About:
                __version__ = getattr(bcrypt, '__version__', '4.0.0')
            bcrypt.__about__ = About()
            print("✅ bcrypt compatibility fixed")
    except Exception as e:
        print(f"⚠️ bcrypt compatibility fix failed: {e}")

# 修复 bcrypt 兼容性
fix_bcrypt_compatibility()

# Setup logging as soon as the application starts
setup_logging()

def create_application() -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(
        title="AutoReportAI API",
        description="AutoReportAI 智能报告生成系统API",
        version="0.4.0",
        contact={
            "name": "wanghaishan",
            "email": "448486810@qq.com",
        },
        license_info={
            "name": "Apache License 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0"
        }
    )

    # Setup exception handlers
    setup_exception_handlers(app)

    # 🌍 CORS 配置 - 完全开放（开发环境）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],              # 允许所有来源
        allow_credentials=False,          # 不允许携带凭证
        allow_methods=["*"],              # 允许所有HTTP方法
        allow_headers=["*"],              # 允许所有请求头
        expose_headers=["*"]              # 暴露所有响应头
    )
    
    # Add other middleware
    app.add_middleware(APIVersionMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    print("🌍 CORS已配置：允许所有来源和方法")

    return app


# 创建应用实例
app = create_application()


def print_startup_config():
    """启动时打印简化的配置信息 - 支持局域网访问"""
    import os
    
    print("🚀 AutoReportAI 启动成功")
    print("-" * 50)
    
    # 获取服务器IP配置
    server_ip = os.getenv('SERVER_IP', 'localhost')
    server_port = getattr(settings, 'PORT', 8000)
    ws_port = getattr(settings, 'WS_PORT', 8000)
    frontend_port = os.getenv('FRONTEND_PORT', '3000')
    
    # 检测环境
    is_docker = os.path.exists("/.dockerenv") or os.getenv('DOCKER_ENV') == 'true'
    environment_type = getattr(settings, 'ENVIRONMENT_TYPE', 'unknown')
    
    # 优先显示局域网访问地址
    if server_ip != 'localhost' and server_ip != '127.0.0.1':
        # 局域网访问模式
        frontend_url = f"http://{server_ip}:{frontend_port}"
        backend_url = f"http://{server_ip}:{server_port}"
        websocket_url = f"ws://{server_ip}:{ws_port}/ws"
        docs_url = f"http://{server_ip}:{server_port}/docs"
        
        print(f"🌐 局域网访问模式 (IP: {server_ip})")
        print(f"📱 前端地址: {frontend_url}")
        print(f"🔗 后端API: {backend_url}{settings.API_V1_STR}")
        print(f"🌐 WebSocket: {websocket_url}")
        print(f"📋 API文档: {docs_url}")
        
        # 同时显示本地访问地址
        print(f"💻 本地访问: http://localhost:{frontend_port}")
    else:
        # 本地访问模式
        frontend_url = f"http://localhost:{frontend_port}"
        
        print(f"💻 本地访问模式")
        print(f"📱 前端地址: {frontend_url}")
        print(f"🔗 后端API: {settings.API_BASE_URL}{settings.API_V1_STR}")
        print(f"🌐 WebSocket: ws://localhost:{ws_port}/ws")
        print(f"📋 API文档: {settings.API_BASE_URL}/docs")
    
    # 环境信息
    print(f"🔧 运行环境: {settings.ENVIRONMENT}")
    if is_docker:
        print(f"🐳 容器环境: {environment_type}")
    
    print("🌍 CORS状态: 已完全开放，无跨域限制")
    print("-" * 50)


@app.on_event("startup")
async def startup():
    try:
        redis_connection = redis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
        await FastAPILimiter.init(redis_connection)
        print("📡 Redis连接和速率限制器初始化成功")
    except Exception as e:
        print(f"⚠️ Redis连接失败，跳过速率限制器初始化: {e}")
        # 不阻止应用启动
    
    # 初始化统一缓存管理器
    try:
        from app.services.infrastructure.cache.unified_cache_system import initialize_cache_manager
        from app.db.session import get_db
        
        # 获取数据库会话
        db_gen = get_db()
        db = next(db_gen)
        
        # 初始化缓存管理器
        redis_client = None
        try:
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        except:
            pass
            
        cache_manager = initialize_cache_manager(
            enable_memory=True,
            enable_redis=redis_client is not None,
            enable_database=True,
            redis_client=redis_client,
            db_session=db
        )
        
        print("🗄️ 统一缓存系统初始化成功")
        
    except Exception as e:
        print(f"⚠️ 缓存系统初始化失败: {e}")
        # 缓存系统初始化失败不应该阻止应用启动

    # 启动LLM监控服务
    try:
        from app.services.infrastructure.llm.monitor_integration import start_llm_monitoring
        from app.db.session import get_db
        
        await start_llm_monitoring(get_db)
        print("🤖 LLM监控服务启动成功")
        
    except Exception as e:
        print(f"⚠️ LLM监控服务启动失败: {e}")

    # 启动时打印关键配置
    print_startup_config()


@app.on_event("shutdown")
async def shutdown():
    """应用关闭处理"""
    shutdown_tasks = [
        ("LLM监控服务", "app.services.infrastructure.llm.monitor_integration", "stop_llm_monitoring"),
        ("WebSocket管理器", "app.websocket.manager", "websocket_manager")
    ]
    
    for service_name, module_path, service_attr in shutdown_tasks:
        try:
            if service_attr == "websocket_manager":
                from app.websocket.manager import websocket_manager
                await websocket_manager.shutdown()
            else:
                module = __import__(module_path, fromlist=[service_attr])
                stop_func = getattr(module, service_attr)
                await stop_func()
            print(f"✅ {service_name}已停止")
        except Exception as e:
            print(f"⚠️ 停止{service_name}失败: {e}")
    
    print("👋 应用已安全关闭")


# API路由
app.include_router(api_router, prefix="/api")
app.include_router(create_version_info_router(), prefix="/api", tags=["版本信息"])
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])


@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "status": "running",
        "cors": "disabled - no restrictions"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "cors": "open"}