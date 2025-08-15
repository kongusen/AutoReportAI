#!/usr/bin/env python3
"""
AutoReportAI Backend 启动脚本
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from typing import Optional

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ Python版本过低，需要Python 3.8+")
        return False
    
    # 检查虚拟环境
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  警告：未检测到虚拟环境，建议在虚拟环境中运行")
    
    # 检查必要的目录
    backend_dir = Path(__file__).parent
    required_dirs = ['app', 'logs', 'uploads', 'reports']
    for dir_name in required_dirs:
        dir_path = backend_dir / dir_name
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"📁 创建目录: {dir_path}")
    
    print("✅ 环境检查完成")
    return True

def load_environment():
    """加载环境配置"""
    print("⚙️  加载环境配置...")
    
    backend_dir = Path(__file__).parent
    env_file = backend_dir / '.env'
    env_example = backend_dir / 'env.example'
    
    # 如果.env文件不存在，从env.example复制
    if not env_file.exists() and env_example.exists():
        print("📋 创建.env文件（从env.example复制）")
        import shutil
        shutil.copy(env_example, env_file)
        print("💡 请根据需要修改.env文件中的配置")
    
    # 设置环境变量
    os.environ.setdefault('ENVIRONMENT', 'development')
    os.environ.setdefault('DEBUG', 'true')
    os.environ.setdefault('LOG_LEVEL', 'INFO')
    
    print("✅ 环境配置加载完成")

def check_dependencies():
    """检查依赖包"""
    print("📦 检查依赖包...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'alembic',
        'redis',
        'celery'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("✅ 依赖包检查完成")
    return True

def start_celery_worker():
    """启动Celery worker"""
    print("🔄 启动Celery worker...")
    
    try:
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent)
        
        # 构建Celery启动命令
        cmd = [
            sys.executable, "-m", "celery", 
            "-A", "app.services.task.core.worker.celery_app",
            "worker",
            "--loglevel=info",
            "--concurrency=2",
            "--without-heartbeat",
            "--without-gossip"
        ]
        
        # 启动Celery worker作为后台进程
        celery_process = subprocess.Popen(
            cmd, 
            cwd=Path(__file__).parent,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待一秒检查是否启动成功
        time.sleep(1)
        
        if celery_process.poll() is None:
            print("✅ Celery worker启动成功")
            return celery_process
        else:
            print("❌ Celery worker启动失败")
            # 输出错误信息
            stdout, stderr = celery_process.communicate()
            if stderr:
                print(f"错误信息: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Celery worker启动异常: {e}")
        return None

def check_redis_connection():
    """检查Redis连接"""
    print("🔍 检查Redis连接...")
    
    try:
        import redis
        from app.core.config import settings
        
        # 尝试连接Redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        print("✅ Redis连接正常")
        return True
        
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        print("💡 请确保Redis服务正在运行")
        return False

def run_database_migrations():
    """运行数据库迁移"""
    print("🗄️  检查数据库迁移...")
    
    try:
        # 检查是否有新的迁移
        result = subprocess.run([
            sys.executable, "-m", "alembic", "current"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✅ 数据库迁移状态正常")
        else:
            print("⚠️  数据库迁移可能需要更新")
            print("💡 如需更新，请运行: alembic upgrade head")
    except Exception as e:
        print(f"⚠️  无法检查数据库迁移: {e}")

def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """启动服务器和Celery worker"""
    print("🚀 启动 AutoReportAI 后端服务...")
    print(f"📂 工作目录: {Path(__file__).parent}")
    print(f"🌐 服务地址: http://{host}:{port}")
    print("📖 API文档: http://localhost:8000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("💡 健康检查: http://localhost:8000/api/v1/health")
    print("🔧 管理界面: http://localhost:8000/api/v1/dashboard")
    print("-" * 60)
    
    # 检查Redis连接
    if not check_redis_connection():
        print("⚠️  Redis连接失败，Celery功能可能无法正常工作")
    
    # 启动Celery worker
    celery_process = start_celery_worker()
    
    # 设置环境变量
    os.environ['PYTHONPATH'] = str(Path(__file__).parent)
    
    # 构建FastAPI启动命令
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app",
        "--host", host,
        "--port", str(port),
        "--log-level", "info"
    ]
    
    if reload:
        cmd.append("--reload")
    
    api_process = None
    
    try:
        # 启动FastAPI服务器
        api_process = subprocess.Popen(cmd, cwd=Path(__file__).parent)
        
        # 等待服务器启动
        time.sleep(2)
        
        if api_process.poll() is None:
            print("✅ FastAPI服务器启动成功！")
            if celery_process:
                print("✅ Celery worker运行中")
            print("🛑 按 Ctrl+C 停止所有服务")
            
            # 等待进程结束
            api_process.wait()
        else:
            print("❌ FastAPI服务器启动失败")
            return False
            
    except KeyboardInterrupt:
        print("\n👋 正在停止所有服务...")
        
        # 停止FastAPI服务器
        if api_process and api_process.poll() is None:
            print("🛑 停止FastAPI服务器...")
            api_process.terminate()
            api_process.wait()
        
        # 停止Celery worker
        if celery_process and celery_process.poll() is None:
            print("🛑 停止Celery worker...")
            celery_process.terminate()
            celery_process.wait()
        
        print("✅ 所有服务已停止")
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        
        # 清理进程
        if api_process and api_process.poll() is None:
            api_process.terminate()
        if celery_process and celery_process.poll() is None:
            celery_process.terminate()
        
        return False
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 AutoReportAI Backend 启动器")
    print("=" * 60)
    
    # 确保在正确的目录
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # 环境检查
    if not check_environment():
        sys.exit(1)
    
    # 加载环境配置
    load_environment()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查数据库迁移
    run_database_migrations()
    
    # 启动服务器（包含Celery worker）
    success = start_server()
    
    if not success:
        print("\n❌ 启动失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()