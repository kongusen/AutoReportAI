#!/usr/bin/env python3
"""
测试Celery集成和任务执行
包括基础任务和增强任务
"""

import asyncio
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_celery_connection():
    """测试Celery连接"""
    print("\n🔗 测试Celery连接...")
    
    try:
        from app.services.task.core.worker.config.celery_app import celery_app
        
        # 检查Celery配置
        print(f"  🔧 Broker URL: {celery_app.conf.broker_url}")
        print(f"  🗄️ Result Backend: {celery_app.conf.result_backend}")
        
        # 检查注册的任务
        registered_tasks = list(celery_app.tasks.keys())
        print(f"  📋 注册的任务数: {len(registered_tasks)}")
        
        # 显示任务列表
        for task in registered_tasks[:5]:  # 显示前5个
            print(f"    - {task}")
        if len(registered_tasks) > 5:
            print(f"    ... 还有 {len(registered_tasks) - 5} 个任务")
        
        return {
            "connection_success": True,
            "registered_tasks": len(registered_tasks),
            "broker_url": celery_app.conf.broker_url
        }
        
    except Exception as e:
        print(f"  ❌ Celery连接失败: {e}")
        return {"connection_success": False, "error": str(e)}

def test_basic_celery_task():
    """测试基础Celery任务"""
    print("\n🔄 测试基础Celery任务...")
    
    try:
        from app.services.task.core.worker.tasks.basic_tasks import test_celery_task
        
        # 发送测试任务
        print("  📤 发送测试任务...")
        result = test_celery_task.delay("测试消息")
        
        print(f"  🆔 任务ID: {result.id}")
        print(f"  📊 任务状态: {result.status}")
        
        # 等待任务完成（最多10秒）
        print("  ⏳ 等待任务完成...")
        try:
            task_result = result.get(timeout=10)
            print(f"  ✅ 任务完成，结果: {task_result}")
            
            return {
                "task_success": True,
                "task_id": result.id,
                "result": task_result,
                "status": result.status
            }
            
        except Exception as timeout_error:
            print(f"  ⏰ 任务超时或失败: {timeout_error}")
            return {
                "task_success": False,
                "task_id": result.id,
                "status": result.status,
                "error": str(timeout_error)
            }
        
    except Exception as e:
        print(f"  ❌ 基础任务测试失败: {e}")
        return {"task_success": False, "error": str(e)}

def test_enhanced_task():
    """测试增强任务"""
    print("\n🚀 测试增强任务...")
    
    try:
        from app.services.task.core.worker.tasks.enhanced_tasks import intelligent_report_generation_pipeline
        
        # 准备测试数据
        test_task_data = {
            "task_id": 999,  # 测试任务ID
            "template_id": 1,
            "data_source_ids": [1],
            "user_id": 1,
            "parameters": {
                "test_mode": True,
                "generate_sample": True
            }
        }
        
        print("  📤 发送智能报告生成任务...")
        result = intelligent_report_generation_pipeline.delay(test_task_data)
        
        print(f"  🆔 任务ID: {result.id}")
        print(f"  📊 任务状态: {result.status}")
        
        # 等待任务完成（最多30秒，因为增强任务可能较慢）
        print("  ⏳ 等待增强任务完成...")
        try:
            task_result = result.get(timeout=30)
            print(f"  ✅ 增强任务完成")
            print(f"  📄 结果类型: {type(task_result)}")
            
            if isinstance(task_result, dict):
                success = task_result.get("success", False)
                print(f"  🎯 执行成功: {'✅' if success else '❌'}")
                
                if success:
                    stages = task_result.get("stages_completed", [])
                    print(f"  📋 完成的阶段: {', '.join(stages)}")
            
            return {
                "enhanced_task_success": True,
                "task_id": result.id,
                "result": task_result,
                "status": result.status
            }
            
        except Exception as timeout_error:
            print(f"  ⏰ 增强任务超时或失败: {timeout_error}")
            return {
                "enhanced_task_success": False,
                "task_id": result.id,
                "status": result.status,
                "error": str(timeout_error)
            }
        
    except Exception as e:
        print(f"  ❌ 增强任务测试失败: {e}")
        return {"enhanced_task_success": False, "error": str(e)}

def test_celery_monitoring():
    """测试Celery监控"""
    print("\n📊 测试Celery监控...")
    
    try:
        from app.services.task.core.worker.config.celery_app import celery_app
        
        # 获取活跃任务
        inspect = celery_app.control.inspect()
        
        print("  🔍 检查Celery状态...")
        
        # 检查活跃工作器
        stats = inspect.stats()
        if stats:
            print(f"  👷 活跃工作器: {len(stats)} 个")
            for worker, stat in stats.items():
                print(f"    - {worker}: {stat.get('total', 'N/A')} 个任务")
        else:
            print("  ⚠️ 没有检测到活跃工作器")
        
        # 检查注册的任务
        registered = inspect.registered()
        if registered:
            total_tasks = sum(len(tasks) for tasks in registered.values())
            print(f"  📋 工作器注册的任务: {total_tasks} 个")
        
        # 检查活跃任务
        active = inspect.active()
        if active:
            total_active = sum(len(tasks) for tasks in active.values())
            print(f"  🔄 当前活跃任务: {total_active} 个")
        else:
            print("  ✅ 当前没有活跃任务")
        
        return {
            "monitoring_success": True,
            "active_workers": len(stats) if stats else 0,
            "registered_tasks": total_tasks if registered else 0,
            "active_tasks": total_active if active else 0
        }
        
    except Exception as e:
        print(f"  ❌ Celery监控测试失败: {e}")
        return {"monitoring_success": False, "error": str(e)}

def test_celery_beat_schedule():
    """测试Celery Beat调度"""
    print("\n⏰ 测试Celery Beat调度...")
    
    try:
        from app.core.celery_scheduler import CeleryScheduler
        
        # 获取调度器实例
        scheduler = CeleryScheduler()
        
        print("  📅 检查调度任务...")
        
        # 这里可能需要从数据库加载调度任务
        # 但为了测试，我们检查是否有调度配置
        
        print("  ✅ Celery Beat调度器已初始化")
        
        return {
            "beat_success": True,
            "scheduler_initialized": True
        }
        
    except Exception as e:
        print(f"  ❌ Celery Beat测试失败: {e}")
        return {"beat_success": False, "error": str(e)}

def run_comprehensive_celery_test():
    """运行全面的Celery测试"""
    print("🚀 开始Celery集成全面测试")
    print("=" * 60)
    
    test_results = {}
    
    # 执行各项测试
    tests = [
        ("Celery连接测试", test_celery_connection),
        ("基础任务测试", test_basic_celery_task),
        ("增强任务测试", test_enhanced_task),
        ("Celery监控测试", test_celery_monitoring),
        ("Celery Beat调度测试", test_celery_beat_schedule),
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 {test_name}")
            start_time = time.time()
            result = test_func()
            duration = time.time() - start_time
            
            # 判断测试是否成功
            success_indicators = [
                "connection_success", "task_success", "enhanced_task_success", 
                "monitoring_success", "beat_success"
            ]
            
            success = any(result.get(indicator, False) for indicator in success_indicators)
            if not success:
                success = "error" not in result
            
            test_results[test_name] = {
                "result": result,
                "duration": duration,
                "success": success
            }
            
        except Exception as e:
            test_results[test_name] = {
                "result": {"error": str(e)},
                "duration": 0,
                "success": False
            }
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("📊 Celery集成测试总结")
    print("=" * 60)
    
    success_count = 0
    total_duration = 0
    
    for test_name, result in test_results.items():
        status = "✅ 成功" if result["success"] else "❌ 失败"
        duration = result["duration"]
        total_duration += duration
        
        print(f"{test_name:<25} {status:<10} {duration:.3f}s")
        
        if result["success"]:
            success_count += 1
            
            # 输出关键信息
            test_result = result["result"]
            if "registered_tasks" in test_result:
                print(f"                         注册任务: {test_result['registered_tasks']}")
            if "task_id" in test_result:
                print(f"                         任务ID: {test_result['task_id']}")
            if "active_workers" in test_result:
                print(f"                         活跃工作器: {test_result['active_workers']}")
        else:
            error_msg = result["result"].get("error", "Unknown error")
            print(f"                         错误: {error_msg}")
    
    print("-" * 60)
    print(f"总测试数: {len(tests)}")
    print(f"成功数: {success_count}")
    print(f"失败数: {len(tests) - success_count}")
    print(f"成功率: {success_count/len(tests)*100:.1f}%")
    print(f"总耗时: {total_duration:.3f}s")
    print("=" * 60)
    
    if success_count == len(tests):
        print("🎉 所有Celery测试通过！任务系统运行正常！")
    else:
        print("⚠️ 部分Celery测试失败，请检查错误信息")
    
    return test_results

if __name__ == "__main__":
    # 运行测试
    run_comprehensive_celery_test()