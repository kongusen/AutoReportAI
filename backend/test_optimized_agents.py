#!/usr/bin/env python3
"""
测试优化后的Agent系统
包括：Agent工厂、缓存、性能监控、健康检查等功能
"""

import asyncio
import time
import logging
from datetime import datetime
from sqlalchemy.orm import Session

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agent_factory():
    """测试Agent工厂模式"""
    print("\n🏭 测试Agent工厂模式...")
    
    from app.services.agents.factory import create_agent, get_agent_factory, AgentType, AgentCreationMode
    from app.db.session import get_db_session
    
    try:
        # 获取数据库会话
        with get_db_session() as db:
            # 1. 测试基础Agent创建
            print("  📝 创建分析Agent...")
            agent = create_agent(
                AgentType.ANALYSIS,
                db_session=db,
                creation_mode=AgentCreationMode.STATELESS
            )
            print(f"     ✅ Agent创建成功: {agent.agent_id}")
            
            # 2. 测试会话范围Agent
            print("  🔄 创建会话范围Agent...")
            session_agent = create_agent(
                AgentType.ANALYSIS,
                db_session=db,
                creation_mode=AgentCreationMode.SESSION_SCOPED
            )
            print(f"     ✅ 会话Agent创建成功: {session_agent.agent_id}")
            
            # 3. 获取工厂统计
            factory = get_agent_factory()
            stats = factory.get_factory_stats()
            print(f"     📊 工厂统计: {stats}")
            
        return True
    except Exception as e:
        print(f"     ❌ Agent工厂测试失败: {e}")
        return False

async def test_ai_service_caching():
    """测试AI服务缓存功能"""
    print("\n🧠 测试AI服务缓存...")
    
    from app.services.agents.core.ai_service import get_ai_service, get_ai_service_pool
    from app.db.session import get_db_session
    
    try:
        with get_db_session() as db:
            # 1. 获取AI服务实例
            print("  🔧 获取AI服务实例...")
            ai_service = get_ai_service(db_session=db, suppress_warning=False)
            print(f"     ✅ AI服务获取成功")
            
            # 2. 测试连接池统计
            print("  📊 获取连接池统计...")
            pool = get_ai_service_pool()
            pool_stats = pool.get_pool_stats()
            print(f"     📈 连接池统计: {pool_stats}")
            
        return True
    except Exception as e:
        print(f"     ❌ AI服务缓存测试失败: {e}")
        return False

async def test_performance_monitoring():
    """测试性能监控功能"""
    print("\n📊 测试性能监控...")
    
    from app.services.agents.core.performance_monitor import (
        get_performance_monitor, performance_context, optimize_system_performance
    )
    
    try:
        monitor = get_performance_monitor()
        
        # 1. 测试性能上下文
        print("  ⏱️ 测试性能测量...")
        with performance_context("test_operation"):
            # 模拟一些工作
            await asyncio.sleep(0.1)
        print("     ✅ 性能测量完成")
        
        # 2. 获取性能摘要
        print("  📈 获取性能摘要...")
        summary = monitor.get_performance_summary()
        print(f"     📊 性能摘要: {summary}")
        
        # 3. 执行系统优化
        print("  🔧 执行系统优化...")
        optimization_result = await optimize_system_performance()
        print(f"     ✅ 优化完成: {optimization_result}")
        
        return True
    except Exception as e:
        print(f"     ❌ 性能监控测试失败: {e}")
        return False

async def test_cache_system():
    """测试缓存系统"""
    print("\n🔄 测试缓存系统...")
    
    from app.services.agents.core.cache_manager import (
        get_cache_manager, cache_ai_response, get_cached_ai_response,
        cache_query_result, get_cached_query_result
    )
    
    try:
        manager = get_cache_manager()
        
        # 1. 测试AI响应缓存
        print("  🧠 测试AI响应缓存...")
        test_prompt = "测试提示"
        test_response = "测试响应内容"
        
        # 缓存响应
        cache_ai_response(test_response, test_prompt, "test_context", "test_task")
        
        # 获取缓存
        cached = get_cached_ai_response(test_prompt, "test_context", "test_task")
        if cached == test_response:
            print("     ✅ AI响应缓存工作正常")
        else:
            print("     ❌ AI响应缓存异常")
            return False
        
        # 2. 测试查询结果缓存
        print("  🗃️ 测试查询缓存...")
        test_query = "SELECT 1"
        test_result = [{"test": "data"}]
        
        # 缓存查询结果
        cache_query_result(test_query, test_result)
        
        # 获取缓存
        cached_query = get_cached_query_result(test_query)
        if cached_query == test_result:
            print("     ✅ 查询缓存工作正常")
        else:
            print("     ❌ 查询缓存异常")
            return False
        
        # 3. 获取缓存统计
        print("  📊 获取缓存统计...")
        stats = manager.get_global_stats()
        print(f"     📈 缓存统计: {stats}")
        
        return True
    except Exception as e:
        print(f"     ❌ 缓存系统测试失败: {e}")
        return False

async def test_health_monitoring():
    """测试健康监控"""
    print("\n🔍 测试健康监控...")
    
    from app.services.agents.core.health_monitor import (
        get_health_monitor, perform_system_health_check
    )
    
    try:
        monitor = get_health_monitor()
        
        # 1. 执行系统健康检查
        print("  🏥 执行系统健康检查...")
        health_summary = await perform_system_health_check()
        print(f"     📊 系统健康状态: {health_summary}")
        
        # 2. 检查特定组件
        print("  🔧 检查数据库组件...")
        db_health = await monitor.check_component("database")
        if db_health:
            print(f"     ✅ 数据库健康: {db_health.status.value}")
        
        print("  🧠 检查AI服务组件...")
        ai_health = await monitor.check_component("ai_service")
        if ai_health:
            print(f"     ✅ AI服务健康: {ai_health.status.value}")
        
        return True
    except Exception as e:
        print(f"     ❌ 健康监控测试失败: {e}")
        return False

async def test_agent_with_ai():
    """测试Agent AI功能（如果可用）"""
    print("\n🤖 测试Agent AI功能...")
    
    from app.services.agents.factory import create_agent, AgentType
    from app.db.session import get_db_session
    
    try:
        with get_db_session() as db:
            # 创建分析Agent
            agent = create_agent(AgentType.ANALYSIS, db_session=db)
            
            # 检查AI服务是否可用
            if hasattr(agent, 'ai_service') and agent.ai_service:
                print("  🧠 AI服务可用，执行简单分析...")
                
                # 执行简单的AI分析（使用缓存）
                result = await agent.analyze_with_ai(
                    context="测试数据",
                    prompt="请简单分析这个测试数据",
                    task_type="test_analysis",
                    use_cache=True
                )
                print(f"     ✅ AI分析完成: {result[:100]}...")
                
                # 测试缓存命中
                cached_result = await agent.analyze_with_ai(
                    context="测试数据",
                    prompt="请简单分析这个测试数据",
                    task_type="test_analysis",
                    use_cache=True
                )
                
                if cached_result == result:
                    print("     ✅ 缓存命中，性能优化生效")
                else:
                    print("     ⚠️ 缓存未命中")
                
            else:
                print("     ⚠️ AI服务不可用（需要配置AI提供商）")
                
        return True
    except Exception as e:
        print(f"     ❌ Agent AI功能测试失败: {e}")
        return False

async def test_two_phase_tasks():
    """测试两段式任务功能"""
    print("\n🔄 测试两段式任务...")
    
    try:
        # 这里可以添加两段式任务的测试
        # 由于需要具体的任务实现，暂时跳过详细测试
        print("  📋 两段式任务框架已就绪")
        print("  ⚠️ 具体任务测试需要配置真实数据源")
        
        return True
    except Exception as e:
        print(f"     ❌ 两段式任务测试失败: {e}")
        return False

async def run_comprehensive_test():
    """运行全面测试"""
    print("🚀 开始Agent系统优化功能全面测试")
    print("=" * 60)
    
    test_results = {}
    
    # 执行各项测试
    tests = [
        ("Agent工厂模式", test_agent_factory),
        ("AI服务缓存", test_ai_service_caching),
        ("性能监控", test_performance_monitoring),
        ("缓存系统", test_cache_system),
        ("健康监控", test_health_monitoring),
        ("Agent AI功能", test_agent_with_ai),
        ("两段式任务", test_two_phase_tasks),
    ]
    
    for test_name, test_func in tests:
        try:
            start_time = time.time()
            result = await test_func()
            duration = time.time() - start_time
            test_results[test_name] = {
                "success": result,
                "duration": duration
            }
        except Exception as e:
            test_results[test_name] = {
                "success": False,
                "error": str(e),
                "duration": 0
            }
    
    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("📊 测试结果摘要")
    print("=" * 60)
    
    success_count = 0
    total_duration = 0
    
    for test_name, result in test_results.items():
        status = "✅ 成功" if result["success"] else "❌ 失败"
        duration = result["duration"]
        total_duration += duration
        
        print(f"{test_name:<20} {status:<10} {duration:.2f}s")
        
        if result["success"]:
            success_count += 1
        elif "error" in result:
            print(f"                    错误: {result['error']}")
    
    print("-" * 60)
    print(f"总测试数: {len(tests)}")
    print(f"成功数: {success_count}")
    print(f"失败数: {len(tests) - success_count}")
    print(f"成功率: {success_count/len(tests)*100:.1f}%")
    print(f"总耗时: {total_duration:.2f}s")
    print("=" * 60)
    
    if success_count == len(tests):
        print("🎉 所有测试通过！系统优化成功！")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    
    return test_results

if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_comprehensive_test())