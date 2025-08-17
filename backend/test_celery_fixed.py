#!/usr/bin/env python3
"""
修复版Celery测试 - 测试完整的任务流程
"""

import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_celery_comprehensive():
    """全面测试Celery系统"""
    print("🚀 Celery系统全面测试")
    print("=" * 60)
    
    results = {}
    
    # 1. 测试Celery连接
    print("\n1️⃣ 测试Celery连接和任务注册")
    try:
        from app.services.task.core.worker.config.celery_app import celery_app
        
        registered_tasks = list(celery_app.tasks.keys())
        print(f"  ✅ Celery连接成功")
        print(f"  📋 注册任务数: {len(registered_tasks)}")
        print(f"  🔧 Broker: {celery_app.conf.broker_url}")
        
        results["connection"] = {"success": True, "tasks": len(registered_tasks)}
        
    except Exception as e:
        print(f"  ❌ Celery连接失败: {e}")
        results["connection"] = {"success": False, "error": str(e)}
    
    # 2. 测试基础任务
    print("\n2️⃣ 测试基础任务执行")
    try:
        from app.services.task.core.worker.tasks.basic_tasks import test_celery_task
        
        print("  📤 发送测试任务...")
        result = test_celery_task.delay("Hello Celery!")
        
        print(f"  🆔 任务ID: {result.id}")
        
        # 等待结果
        task_result = result.get(timeout=10)
        print(f"  ✅ 任务执行成功: {task_result}")
        
        results["basic_task"] = {"success": True, "result": task_result}
        
    except Exception as e:
        print(f"  ❌ 基础任务失败: {e}")
        results["basic_task"] = {"success": False, "error": str(e)}
    
    # 3. 测试数据查询任务
    print("\n3️⃣ 测试数据查询任务")
    try:
        from app.services.task.core.worker.tasks.basic_tasks import data_query
        
        query_params = {
            "data_source_id": 1,
            "query": "SELECT 1 as test_column",
            "parameters": {}
        }
        
        print("  📤 发送数据查询任务...")
        result = data_query.delay(query_params)
        
        print(f"  🆔 查询任务ID: {result.id}")
        
        # 等待结果
        query_result = result.get(timeout=15)
        print(f"  ✅ 查询任务完成")
        if isinstance(query_result, dict):
            success = query_result.get("success", False)
            print(f"  🎯 查询成功: {'✅' if success else '❌'}")
        
        results["data_query"] = {"success": True, "result": query_result}
        
    except Exception as e:
        print(f"  ❌ 数据查询任务失败: {e}")
        results["data_query"] = {"success": False, "error": str(e)}
    
    # 4. 测试模板解析任务
    print("\n4️⃣ 测试模板解析任务")
    try:
        from app.services.task.core.worker.tasks.basic_tasks import template_parsing
        
        template_params = {
            "template_id": 1,
            "context": {"test_var": "测试值"},
            "user_id": 1
        }
        
        print("  📤 发送模板解析任务...")
        result = template_parsing.delay(template_params)
        
        print(f"  🆔 模板任务ID: {result.id}")
        
        # 等待结果
        template_result = result.get(timeout=15)
        print(f"  ✅ 模板解析完成")
        
        results["template_parsing"] = {"success": True, "result": template_result}
        
    except Exception as e:
        print(f"  ❌ 模板解析任务失败: {e}")
        results["template_parsing"] = {"success": False, "error": str(e)}
    
    # 5. 测试Celery监控
    print("\n5️⃣ 测试Celery工作器监控")
    try:
        from app.services.task.core.worker.config.celery_app import celery_app
        
        inspect = celery_app.control.inspect()
        
        # 检查工作器状态
        stats = inspect.stats()
        if stats:
            print(f"  👷 检测到 {len(stats)} 个活跃工作器")
            for worker_name in stats.keys():
                print(f"    - {worker_name}")
        
        # 检查注册任务
        registered = inspect.registered()
        if registered:
            total_registered = sum(len(tasks) for tasks in registered.values())
            print(f"  📋 工作器注册任务总数: {total_registered}")
        
        # 检查活跃任务
        active = inspect.active()
        if active:
            total_active = sum(len(tasks) for tasks in active.values())
            print(f"  🔄 当前活跃任务: {total_active}")
        else:
            print(f"  ✅ 当前无活跃任务")
        
        results["monitoring"] = {
            "success": True, 
            "workers": len(stats) if stats else 0,
            "active_tasks": total_active if active else 0
        }
        
    except Exception as e:
        print(f"  ❌ 监控测试失败: {e}")
        results["monitoring"] = {"success": False, "error": str(e)}
    
    # 6. 检查Docker服务状态
    print("\n6️⃣ 检查Docker服务状态")
    try:
        import subprocess
        
        docker_result = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\\t{{.Status}}"],
            capture_output=True, text=True, timeout=10
        )
        
        if docker_result.returncode == 0:
            lines = docker_result.stdout.strip().split('\n')
            services = {}
            
            for line in lines[1:]:  # 跳过表头
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        status = parts[1].strip()
                        
                        if 'celery' in name.lower():
                            services[name] = status
                            health = "healthy" if "healthy" in status else "starting" if "starting" in status else "unhealthy"
                            print(f"  🐳 {name}: {health}")
            
            results["docker_services"] = {"success": True, "services": services}
        else:
            print(f"  ⚠️ 无法检查Docker状态")
            results["docker_services"] = {"success": False, "error": "Docker检查失败"}
    
    except Exception as e:
        print(f"  ❌ Docker状态检查失败: {e}")
        results["docker_services"] = {"success": False, "error": str(e)}
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 Celery系统测试总结")
    print("=" * 60)
    
    success_count = 0
    total_tests = len(results)
    
    for test_name, result in results.items():
        status = "✅ 成功" if result["success"] else "❌ 失败"
        print(f"{test_name:<20} {status}")
        
        if result["success"]:
            success_count += 1
        else:
            print(f"                     错误: {result.get('error', 'Unknown')}")
    
    print("-" * 60)
    print(f"总测试项: {total_tests}")
    print(f"成功数: {success_count}")
    print(f"成功率: {success_count/total_tests*100:.1f}%")
    print("=" * 60)
    
    if success_count >= total_tests * 0.8:  # 80%以上成功率
        print("🎉 Celery系统运行良好！")
    else:
        print("⚠️ Celery系统需要进一步检查")
    
    return results

if __name__ == "__main__":
    test_celery_comprehensive()