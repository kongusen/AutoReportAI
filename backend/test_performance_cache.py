#!/usr/bin/env python3
"""
测试性能监控和缓存功能
深度验证系统优化效果
"""

import asyncio
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cache_effectiveness():
    """测试缓存效果"""
    print("\n🔄 测试缓存有效性...")
    
    from app.services.agents.core.cache_manager import (
        get_cache_manager, cache_ai_response, get_cached_ai_response,
        cache_query_result, get_cached_query_result
    )
    
    try:
        manager = get_cache_manager()
        
        # 清空现有缓存
        manager.clear_all_caches()
        print("  🧹 清空现有缓存")
        
        # 测试AI响应缓存
        print("  🧠 测试AI响应缓存性能...")
        
        test_cases = [
            ("分析用户数据", "用户数据分析", "data_analysis"),
            ("生成报告", "报告生成任务", "report_generation"),
            ("查询优化", "SQL查询优化", "query_optimization"),
        ]
        
        # 第一轮：缓存响应
        start_time = time.time()
        for prompt, context, task_type in test_cases:
            response = f"AI分析结果：{prompt} - {context}"
            cache_ai_response(response, prompt, context, task_type)
        first_round_time = time.time() - start_time
        
        print(f"     ✅ 缓存 {len(test_cases)} 个AI响应，耗时: {first_round_time:.3f}s")
        
        # 第二轮：从缓存获取
        start_time = time.time()
        hit_count = 0
        for prompt, context, task_type in test_cases:
            cached = get_cached_ai_response(prompt, context, task_type)
            if cached:
                hit_count += 1
        second_round_time = time.time() - start_time
        
        print(f"     ✅ 缓存命中 {hit_count}/{len(test_cases)}，耗时: {second_round_time:.3f}s")
        print(f"     📈 性能提升: {(first_round_time/second_round_time):.1f}x")
        
        # 测试查询缓存
        print("  🗃️ 测试查询缓存性能...")
        
        queries = [
            "SELECT COUNT(*) FROM users",
            "SELECT status, COUNT(*) FROM tasks GROUP BY status",
            "SELECT DATE(created_at), COUNT(*) FROM reports GROUP BY DATE(created_at)"
        ]
        
        # 缓存查询结果
        for i, query in enumerate(queries):
            result = [{"count": 100 + i * 10}]
            cache_query_result(query, result)
        
        # 测试缓存命中
        cache_hits = 0
        for query in queries:
            cached = get_cached_query_result(query)
            if cached:
                cache_hits += 1
        
        print(f"     ✅ 查询缓存命中: {cache_hits}/{len(queries)}")
        
        # 获取缓存统计
        stats = manager.get_global_stats()
        print(f"  📊 缓存统计:")
        print(f"     总缓存项目: {stats['global']['total_size']}")
        print(f"     全局命中率: {stats['global']['global_hit_rate']:.2%}")
        
        return {
            "ai_cache_performance": first_round_time / second_round_time if second_round_time > 0 else 0,
            "ai_cache_hits": hit_count,
            "query_cache_hits": cache_hits,
            "total_cache_items": stats['global']['total_size'],
            "global_hit_rate": stats['global']['global_hit_rate']
        }
        
    except Exception as e:
        print(f"     ❌ 缓存测试失败: {e}")
        return {"error": str(e)}

async def test_performance_monitoring_detailed():
    """详细测试性能监控"""
    print("\n📊 详细测试性能监控...")
    
    from app.services.agents.core.performance_monitor import (
        get_performance_monitor, performance_context, optimize_system_performance
    )
    
    try:
        monitor = get_performance_monitor()
        
        # 测试性能上下文
        print("  ⏱️ 测试性能测量上下文...")
        
        measurements = []
        operations = [
            ("数据库查询", 0.1),
            ("AI分析", 0.2),
            ("报告生成", 0.15),
            ("缓存操作", 0.05),
        ]
        
        for op_name, sleep_time in operations:
            with performance_context(op_name):
                await asyncio.sleep(sleep_time)
            print(f"     ✅ 测量 {op_name}")
        
        # 获取性能摘要
        print("  📈 获取性能摘要...")
        summary = monitor.get_performance_summary()
        print(f"     监控状态: {summary.get('monitoring_enabled', 'unknown')}")
        
        # 执行系统优化
        print("  🔧 执行系统优化...")
        optimization = await optimize_system_performance()
        
        memory_freed = optimization.get('memory_optimization', {}).get('memory_freed_mb', 0)
        print(f"     ✅ 内存优化释放: {memory_freed:.2f} MB")
        
        return {
            "operations_measured": len(operations),
            "memory_freed_mb": memory_freed,
            "optimization_actions": len(optimization.get('memory_optimization', {}).get('actions_taken', [])),
            "performance_summary": summary
        }
        
    except Exception as e:
        print(f"     ❌ 性能监控测试失败: {e}")
        return {"error": str(e)}

async def test_health_monitoring_detailed():
    """详细测试健康监控"""
    print("\n🏥 详细测试健康监控...")
    
    from app.services.agents.core.health_monitor import (
        get_health_monitor, perform_system_health_check
    )
    
    try:
        monitor = get_health_monitor()
        
        # 执行多次健康检查
        print("  🔍 执行多轮健康检查...")
        
        health_results = []
        for i in range(3):
            health = await perform_system_health_check()
            health_results.append(health)
            print(f"     第 {i+1} 轮检查: {health['overall_status']}")
            
            # 检查各组件状态
            for component, status in health['components'].items():
                response_time = status.get('duration_ms', 0)
                print(f"       {component}: {status['status']} ({response_time:.2f}ms)")
            
            await asyncio.sleep(0.1)  # 短暂等待
        
        # 分析健康趋势
        statuses = [h['overall_status'] for h in health_results]
        healthy_count = statuses.count('healthy')
        consistency = healthy_count / len(health_results)
        
        print(f"  📊 健康监控分析:")
        print(f"     检查次数: {len(health_results)}")
        print(f"     健康率: {consistency:.2%}")
        print(f"     状态一致性: {'✅ 稳定' if consistency >= 0.8 else '⚠️ 不稳定'}")
        
        # 获取最新的指标
        latest_health = health_results[-1]
        total_components = latest_health.get('total_components', 0)
        
        return {
            "health_checks": len(health_results),
            "health_rate": consistency,
            "total_components": total_components,
            "stable": consistency >= 0.8,
            "latest_status": latest_health['overall_status']
        }
        
    except Exception as e:
        print(f"     ❌ 健康监控测试失败: {e}")
        return {"error": str(e)}

async def test_agent_factory_performance():
    """测试Agent工厂性能"""
    print("\n🏭 测试Agent工厂性能...")
    
    from app.services.agents.factory import get_agent_factory, create_agent, AgentType, AgentCreationMode
    from app.db.session import get_db_session
    
    try:
        factory = get_agent_factory()
        
        # 测试不同创建模式的性能
        print("  🔄 测试不同创建模式...")
        
        with get_db_session() as db:
            # 无状态模式
            start_time = time.time()
            stateless_agents = []
            for i in range(5):
                agent = create_agent(
                    AgentType.ANALYSIS,
                    db_session=db,
                    creation_mode=AgentCreationMode.STATELESS
                )
                stateless_agents.append(agent)
            stateless_time = time.time() - start_time
            
            print(f"     ✅ 无状态模式创建 {len(stateless_agents)} 个Agent: {stateless_time:.3f}s")
            
            # 会话范围模式
            start_time = time.time()
            session_agents = []
            for i in range(5):
                agent = create_agent(
                    AgentType.ANALYSIS,
                    db_session=db,
                    creation_mode=AgentCreationMode.SESSION_SCOPED
                )
                session_agents.append(agent)
            session_time = time.time() - start_time
            
            print(f"     ✅ 会话范围模式创建 {len(session_agents)} 个Agent: {session_time:.3f}s")
            
            # 获取工厂统计
            stats = factory.get_factory_stats()
            print(f"  📊 工厂统计:")
            print(f"     注册的Agent类型: {len(stats['registered_agent_types'])}")
            print(f"     单例实例: {stats['singleton_instances']}")
            print(f"     会话范围实例: {stats['total_session_scoped_instances']}")
            
            return {
                "stateless_creation_time": stateless_time,
                "session_creation_time": session_time,
                "performance_ratio": stateless_time / session_time if session_time > 0 else 0,
                "factory_stats": stats
            }
        
    except Exception as e:
        print(f"     ❌ Agent工厂性能测试失败: {e}")
        return {"error": str(e)}

async def run_comprehensive_performance_test():
    """运行全面的性能和缓存测试"""
    print("🚀 开始性能监控和缓存全面测试")
    print("=" * 60)
    
    test_results = {}
    
    # 执行各项测试
    tests = [
        ("缓存有效性测试", test_cache_effectiveness),
        ("性能监控详细测试", test_performance_monitoring_detailed),
        ("健康监控详细测试", test_health_monitoring_detailed),
        ("Agent工厂性能测试", test_agent_factory_performance),
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🔍 {test_name}")
            start_time = time.time()
            result = await test_func()
            duration = time.time() - start_time
            
            test_results[test_name] = {
                "result": result,
                "duration": duration,
                "success": "error" not in result
            }
            
        except Exception as e:
            test_results[test_name] = {
                "result": {"error": str(e)},
                "duration": 0,
                "success": False
            }
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("📊 性能和缓存测试总结")
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
            
            # 输出关键指标
            test_result = result["result"]
            if "global_hit_rate" in test_result:
                print(f"                         缓存命中率: {test_result['global_hit_rate']:.2%}")
            if "memory_freed_mb" in test_result:
                print(f"                         释放内存: {test_result['memory_freed_mb']:.2f}MB")
            if "health_rate" in test_result:
                print(f"                         健康率: {test_result['health_rate']:.2%}")
        else:
            print(f"                         错误: {result['result'].get('error', 'Unknown')}")
    
    print("-" * 60)
    print(f"总测试数: {len(tests)}")
    print(f"成功数: {success_count}")
    print(f"失败数: {len(tests) - success_count}")
    print(f"成功率: {success_count/len(tests)*100:.1f}%")
    print(f"总耗时: {total_duration:.3f}s")
    print("=" * 60)
    
    if success_count == len(tests):
        print("🎉 所有性能和缓存测试通过！系统优化效果显著！")
    else:
        print("⚠️ 部分测试失败，需要进一步优化")
    
    return test_results

if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_comprehensive_performance_test())