#!/usr/bin/env python3
"""
优化的Celery Worker健康检查脚本
- 抑制不必要的警告
- 提供详细的检查信息
- 快速响应健康状态
"""

import os
import sys
import subprocess
import time
import logging
from typing import Dict, Any

# 抑制不必要的日志
logging.getLogger('anthropic').setLevel(logging.CRITICAL)
logging.getLogger('google').setLevel(logging.CRITICAL)
logging.getLogger('app.services.storage').setLevel(logging.CRITICAL)
logging.getLogger('app.services.ai_integration').setLevel(logging.CRITICAL)

def check_process_running() -> bool:
    """检查Celery worker进程是否运行"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'celery.*worker'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def check_redis_connection() -> bool:
    """检查Redis连接"""
    try:
        import redis
        redis_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        return True
    except Exception:
        return False

def check_celery_ping() -> Dict[str, Any]:
    """检查Celery worker ping响应"""
    try:
        result = subprocess.run([
            'celery', '-A', 'app.services.task.core.worker.celery_app',
            'inspect', 'ping', '--timeout=3'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 and 'pong' in result.stdout:
            return {"success": True, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr or result.stdout}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Ping timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def check_task_processing() -> Dict[str, Any]:
    """快速测试任务处理能力"""
    try:
        # 设置环境变量以抑制警告
        env = os.environ.copy()
        env['PYTHONPATH'] = '/app'
        
        # 执行快速任务测试
        test_script = '''
import os
import sys
import warnings
warnings.filterwarnings("ignore")

# 抑制各种警告
import logging
logging.getLogger("anthropic").setLevel(logging.CRITICAL)
logging.getLogger("google").setLevel(logging.CRITICAL)
logging.getLogger("app.services.storage").setLevel(logging.CRITICAL)
logging.getLogger("app.services.ai_integration").setLevel(logging.CRITICAL)

try:
    from app.services.task.core.worker.tasks.basic_tasks import test_celery_task
    result = test_celery_task.delay("health_check")
    task_result = result.get(timeout=2)
    print("TASK_SUCCESS")
except Exception as e:
    print(f"TASK_FAILED: {e}")
'''
        
        result = subprocess.run([
            'python3', '-c', test_script
        ], capture_output=True, text=True, timeout=5, env=env)
        
        if 'TASK_SUCCESS' in result.stdout:
            return {"success": True}
        else:
            return {"success": False, "error": result.stdout + result.stderr}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Task test timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    """主健康检查函数"""
    print("🔍 Starting Celery Worker health check...")
    
    # 1. 检查进程
    if not check_process_running():
        print("❌ Celery worker process not found")
        sys.exit(1)
    print("✅ Celery worker process running")
    
    # 2. 检查Redis连接
    if not check_redis_connection():
        print("❌ Redis connection failed")
        sys.exit(1)
    print("✅ Redis connection successful")
    
    # 3. 检查Celery ping
    ping_result = check_celery_ping()
    if not ping_result["success"]:
        print(f"❌ Celery ping failed: {ping_result.get('error', 'Unknown error')}")
        sys.exit(1)
    print("✅ Celery ping successful")
    
    # 4. 测试任务处理（可选，不阻塞）
    task_result = check_task_processing()
    if task_result["success"]:
        print("✅ Task processing test successful")
    else:
        print(f"⚠️  Task processing test failed: {task_result.get('error', 'Unknown')}")
        # 不因为任务测试失败而退出
    
    print("🎉 Celery Worker health check completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())