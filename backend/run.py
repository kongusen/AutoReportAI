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
    """启动服务器"""
    print("🚀 启动 AutoReportAI 后端服务...")
    print(f"📂 工作目录: {Path(__file__).parent}")
    print(f"🌐 服务地址: http://{host}:{port}")
    print("📖 API文档: http://localhost:8000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("💡 健康检查: http://localhost:8000/api/v1/health")
    print("🔧 管理界面: http://localhost:8000/api/v1/dashboard")
    print("-" * 60)
    
    # 设置环境变量
    os.environ['PYTHONPATH'] = str(Path(__file__).parent)
    
    # 构建启动命令
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app",
        "--host", host,
        "--port", str(port),
        "--log-level", "info"
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        # 启动服务器
        process = subprocess.Popen(cmd, cwd=Path(__file__).parent)
        
        # 等待服务器启动
        time.sleep(2)
        
        if process.poll() is None:
            print("✅ 服务器启动成功！")
            print("🛑 按 Ctrl+C 停止服务器")
            
            # 等待进程结束
            process.wait()
        else:
            print("❌ 服务器启动失败")
            return False
            
    except KeyboardInterrupt:
        print("\n👋 正在停止服务器...")
        if 'process' in locals():
            process.terminate()
            process.wait()
        print("✅ 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
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
    
    # 启动服务器
    success = start_server()
    
    if not success:
        print("\n❌ 启动失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()