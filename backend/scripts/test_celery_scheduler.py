#!/usr/bin/env python3
"""
测试 Celery Beat 调度系统
"""
import sys
import os
import time
from datetime import datetime, timedelta

# 添加项目路径到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.worker import celery_app
from app.core.celery_scheduler import get_scheduler_manager
from app.db.session import get_db_session
from app.models.task import Task
from sqlalchemy import text

def test_scheduler():
    """测试调度系统"""
    print("🔧 开始测试 Celery Beat 调度系统...")
    
    # 1. 检查 Celery 应用状态
    print(f"📱 Celery 应用名称: {celery_app.main}")
    print(f"🔗 Broker URL: {celery_app.conf.broker_url}")
    print(f"💾 Result Backend: {celery_app.conf.result_backend}")
    
    # 2. 获取调度管理器
    scheduler = get_scheduler_manager(celery_app)
    
    # 3. 检查数据库中的任务
    print("\n📊 数据库中的任务:")
    with get_db_session() as db:
        tasks = db.query(Task).filter(Task.is_active == True).all()
        for task in tasks:
            print(f"  - ID: {task.id}, 名称: {task.name}, 调度: {task.schedule}")
    
    # 4. 检查 Celery Beat 配置
    print(f"\n⏰ Celery Beat 调度配置:")
    beat_schedule = celery_app.conf.beat_schedule
    print(f"  - 调度任务数量: {len(beat_schedule)}")
    for task_name, config in beat_schedule.items():
        print(f"  - {task_name}: {config}")
    
    # 5. 加载调度任务
    print("\n🔄 重新加载调度任务...")
    loaded_count = scheduler.load_scheduled_tasks_from_database()
    print(f"✅ 成功加载 {loaded_count} 个任务")
    
    # 6. 再次检查 Beat 配置
    print(f"\n⏰ 重新加载后的 Celery Beat 调度配置:")
    beat_schedule = celery_app.conf.beat_schedule
    print(f"  - 调度任务数量: {len(beat_schedule)}")
    for task_name, config in beat_schedule.items():
        print(f"  - {task_name}: {config}")
    
    # 7. 获取所有调度任务状态
    print("\n📈 调度任务状态:")
    tasks_info = scheduler.get_all_scheduled_tasks()
    for task_info in tasks_info:
        print(f"  - 任务 {task_info['task_id']}: {task_info['name']}")
        print(f"    调度: {task_info['schedule']}")
        print(f"    在 Beat 中: {task_info['in_celery_beat']}")
        print(f"    激活状态: {task_info['is_active']}")
        if 'last_status' in task_info:
            print(f"    最近状态: {task_info['last_status']}")
    
    # 8. 测试立即执行
    if tasks:
        test_task = tasks[0]
        print(f"\n🚀 测试立即执行任务 {test_task.id}...")
        result = scheduler.execute_task_immediately(test_task.id, "system")
        print(f"执行结果: {result}")
        
        # 等待几秒钟检查状态
        print("⏳ 等待 3 秒检查任务状态...")
        time.sleep(3)
        
        status = scheduler.get_task_status(test_task.id)
        print(f"任务状态: {status}")
    
    # 9. 创建一个每分钟执行的测试任务
    print(f"\n🔧 创建一个每分钟执行的测试调度...")
    next_minute = datetime.now() + timedelta(minutes=1)
    test_cron = f"{next_minute.minute} {next_minute.hour} * * *"
    print(f"测试 cron 表达式: {test_cron}")
    
    # 更新第一个任务的调度为每分钟执行（仅用于测试）
    if tasks:
        test_task = tasks[0]
        success = scheduler.add_or_update_task(test_task.id, "* * * * *")  # 每分钟执行
        print(f"更新任务调度结果: {success}")
        
        # 查看更新后的配置
        print(f"\n⏰ 更新后的 Celery Beat 调度配置:")
        beat_schedule = celery_app.conf.beat_schedule
        for task_name, config in beat_schedule.items():
            print(f"  - {task_name}: {config}")

def test_worker_connection():
    """测试 Worker 连接"""
    print("\n🔌 测试 Worker 连接...")
    try:
        inspect = celery_app.control.inspect()
        
        # 检查活跃的 workers
        active_workers = inspect.active()
        print(f"活跃的 Workers: {active_workers}")
        
        # 检查注册的任务
        registered_tasks = inspect.registered()
        print(f"注册的任务: {registered_tasks}")
        
        # 检查统计信息
        stats = inspect.stats()
        print(f"Worker 统计: {stats}")
        
    except Exception as e:
        print(f"❌ Worker 连接测试失败: {e}")

if __name__ == "__main__":
    test_scheduler()
    test_worker_connection()
    print("\n✅ 测试完成！")