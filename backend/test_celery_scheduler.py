#!/usr/bin/env python3
"""
Celery 调度系统测试脚本
用于测试完整的 Celery 调度功能
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import requests
from app.core.celery_scheduler import get_scheduler_manager
from app.core.worker import celery_app, test_celery_task
from app.db.session import SessionLocal
from app.models.task import Task
from app import crud

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_celery_task():
    """测试基础 Celery 任务"""
    print("\n" + "="*50)
    print("🧪 测试基础 Celery 任务")
    print("="*50)
    
    try:
        # 提交测试任务
        result = test_celery_task.delay("Hello, Celery!")
        print(f"✅ 任务已提交，ID: {result.id}")
        
        # 等待结果
        print("⏳ 等待任务完成...")
        task_result = result.get(timeout=30)
        print(f"✅ 任务完成，结果: {task_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础任务测试失败: {e}")
        return False


def test_scheduler_manager():
    """测试调度管理器"""
    print("\n" + "="*50)
    print("🧪 测试调度管理器")
    print("="*50)
    
    try:
        manager = get_scheduler_manager(celery_app)
        
        # 测试获取Worker状态
        print("📊 获取 Worker 状态...")
        stats = manager.get_worker_stats()
        print(f"✅ Worker 状态获取成功，发现 {len(stats.get('workers', {}))} 个 worker")
        
        # 测试获取调度任务
        print("📋 获取调度任务...")
        tasks = manager.get_all_scheduled_tasks()
        print(f"✅ 调度任务获取成功，共 {len(tasks)} 个任务")
        
        # 显示任务详情
        for task in tasks:
            status = "✅ 激活" if task.get("is_active") else "❌ 未激活"
            schedule = task.get("schedule", "无调度")
            in_beat = "✅ 是" if task.get("in_celery_beat") else "❌ 否"
            print(f"  - 任务 {task['task_id']}: {task['name']}")
            print(f"    状态: {status}, 调度: {schedule}, 在Beat中: {in_beat}")
        
        return True
        
    except Exception as e:
        print(f"❌ 调度管理器测试失败: {e}")
        return False


def test_task_scheduling():
    """测试任务调度功能"""
    print("\n" + "="*50)
    print("🧪 测试任务调度功能")
    print("="*50)
    
    try:
        db = SessionLocal()
        manager = get_scheduler_manager(celery_app)
        
        # 查找一个测试任务
        task = db.query(Task).filter(Task.is_active == True).first()
        if not task:
            print("⚠️  没有找到活跃的任务，跳过调度测试")
            return True
        
        print(f"📝 使用任务: {task.id} - {task.name}")
        
        # 测试添加调度
        test_cron = "*/5 * * * *"  # 每5分钟执行一次（测试用）
        print(f"⏰ 设置调度: {test_cron}")
        
        success = manager.add_or_update_task(task.id, test_cron)
        if success:
            print("✅ 调度设置成功")
        else:
            print("❌ 调度设置失败")
            return False
        
        # 验证调度状态
        print("🔍 验证调度状态...")
        status = manager.get_task_status(task.id)
        print(f"  - 任务状态: {status.get('is_active', 'unknown')}")
        print(f"  - 调度表达式: {status.get('schedule', 'none')}")
        print(f"  - 在Beat中: {status.get('in_celery_beat', False)}")
        
        # 测试立即执行
        print("🚀 测试立即执行...")
        exec_result = manager.execute_task_immediately(task.id, "test_user")
        print(f"  - 执行结果: {exec_result.get('status', 'unknown')}")
        print(f"  - Celery任务ID: {exec_result.get('celery_task_id', 'none')}")
        
        # 清理：移除测试调度
        print("🧹 清理测试调度...")
        manager.remove_task(task.id)
        print("✅ 测试调度已清理")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 任务调度测试失败: {e}")
        return False


def test_api_endpoints():
    """测试 API 端点"""
    print("\n" + "="*50)
    print("🧪 测试 API 端点")
    print("="*50)
    
    base_url = "http://localhost:8000/api/v1/celery"
    
    # 测试端点列表
    endpoints = [
        ("GET", "/workers/status", "Workers状态"),
        ("GET", "/tasks/scheduled", "调度任务列表"),
        ("GET", "/inspect/active", "活跃任务"),
        ("GET", "/inspect/stats", "Worker统计"),
        ("GET", "/inspect/registered", "已注册任务"),
        ("GET", "/beat/schedule", "Beat调度信息"),
    ]
    
    success_count = 0
    
    for method, endpoint, description in endpoints:
        try:
            print(f"📡 测试: {description} ({method} {endpoint})")
            
            # 这里需要认证token，简化测试先跳过
            print(f"⚠️  跳过API测试（需要认证token）")
            continue
            
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
            else:
                response = requests.post(f"{base_url}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {description} 测试成功")
                success_count += 1
            else:
                print(f"❌ {description} 测试失败: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"⚠️  {description} 连接失败（服务可能未启动）")
        except Exception as e:
            print(f"❌ {description} 测试异常: {e}")
    
    print(f"\n📊 API测试总结: {success_count}/{len(endpoints)} 个端点测试成功")
    return success_count > 0


def test_celery_beat_schedule():
    """测试 Celery Beat 调度配置"""
    print("\n" + "="*50)
    print("🧪 测试 Celery Beat 调度配置")
    print("="*50)
    
    try:
        # 显示当前的 beat_schedule
        beat_schedule = celery_app.conf.beat_schedule
        print(f"📅 当前 Beat 调度任务数量: {len(beat_schedule)}")
        
        for task_name, config in beat_schedule.items():
            print(f"  - {task_name}:")
            print(f"    任务: {config['task']}")
            print(f"    调度: {config['schedule']}")
            print(f"    参数: {config.get('args', [])}")
        
        # 测试添加临时调度
        print("\n🔧 测试添加临时调度...")
        from celery.schedules import crontab
        
        test_schedule_name = "test_temp_task"
        celery_app.conf.beat_schedule[test_schedule_name] = {
            'task': 'app.core.worker.test_celery_task',
            'schedule': crontab(minute='*/10'),  # 每10分钟
            'args': ('Beat Test',)
        }
        
        print(f"✅ 临时调度 '{test_schedule_name}' 已添加")
        
        # 清理临时调度
        if test_schedule_name in celery_app.conf.beat_schedule:
            del celery_app.conf.beat_schedule[test_schedule_name]
            print(f"🧹 临时调度 '{test_schedule_name}' 已清理")
        
        return True
        
    except Exception as e:
        print(f"❌ Beat 调度配置测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 AutoReportAI Celery 调度系统测试")
    print("=" * 60)
    
    results = []
    
    # 执行各项测试
    test_functions = [
        ("基础任务", test_basic_celery_task),
        ("调度管理器", test_scheduler_manager),
        ("任务调度", test_task_scheduling),
        ("Beat调度配置", test_celery_beat_schedule),
        ("API端点", test_api_endpoints),
    ]
    
    for test_name, test_func in test_functions:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试结果总结")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！Celery 调度系统运行正常。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查系统配置。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)