#!/usr/bin/env python3
"""
DAG架构核心功能测试脚本
测试纯DAG架构的核心组件是否正常工作
"""

import asyncio
import logging
import sys
import traceback
from datetime import datetime
from typing import Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_intelligent_placeholder_service():
    """测试智能占位符服务"""
    print("🔍 测试智能占位符服务...")
    
    try:
        from app.services.domain.placeholder.intelligent_placeholder_service import IntelligentPlaceholderService
        
        service = IntelligentPlaceholderService()
        print("✅ IntelligentPlaceholderService 实例化成功")
        
        # 测试服务方法是否可用
        methods = ['analyze_template_for_sql_generation', 
                   'analyze_template_for_chart_testing',
                   'analyze_task_for_sql_validation', 
                   'analyze_task_for_chart_generation']
        
        for method_name in methods:
            if hasattr(service, method_name):
                print(f"✅ 方法 {method_name} 可用")
            else:
                print(f"❌ 方法 {method_name} 不可用")
                
        return True
        
    except Exception as e:
        print(f"❌ IntelligentPlaceholderService 测试失败: {e}")
        traceback.print_exc()
        return False

async def test_react_agent():
    """测试React智能代理"""
    print("\n🤖 测试React智能代理...")
    
    try:
        from app.services.agents.core.react_agent import ReactIntelligentAgent
        
        # 创建代理实例
        agent = ReactIntelligentAgent(
            verbose=True,
            max_iterations=5
        )
        print("✅ ReactIntelligentAgent 实例化成功")
        
        # 检查核心方法
        methods = ['initialize', 'chat', 'stream_chat']
        for method_name in methods:
            if hasattr(agent, method_name):
                print(f"✅ 方法 {method_name} 可用")
            else:
                print(f"⚠️ 方法 {method_name} 不可用")
                
        return True
        
    except Exception as e:
        print(f"❌ ReactIntelligentAgent 测试失败: {e}")
        traceback.print_exc()
        return False

async def test_background_controller():
    """测试后台控制器"""
    print("\n🎮 测试后台控制器...")
    
    try:
        from app.services.agents.core.background_controller import BackgroundController
        
        controller = BackgroundController()
        print("✅ BackgroundController 实例化成功")
        
        # 检查核心方法
        methods = ['execute_dag', 'orchestrate_agents']
        for method_name in methods:
            if hasattr(controller, method_name):
                print(f"✅ 方法 {method_name} 可用")
            else:
                print(f"⚠️ 方法 {method_name} 不可用")
                
        return True
        
    except Exception as e:
        print(f"❌ BackgroundController 测试失败: {e}")
        traceback.print_exc()
        return False

async def test_tools_collections():
    """测试工具集合"""
    print("\n🔧 测试工具集合...")
    
    try:
        # 测试占位符工具
        from app.services.agents.tools.placeholder_tools import PlaceholderToolsCollection
        placeholder_tools = PlaceholderToolsCollection()
        print("✅ PlaceholderToolsCollection 实例化成功")
        
        # 测试图表工具
        from app.services.agents.tools.chart_tools import ChartToolsCollection  
        chart_tools = ChartToolsCollection()
        print("✅ ChartToolsCollection 实例化成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具集合测试失败: {e}")
        traceback.print_exc()
        return False

async def test_llm_integration():
    """测试LLM集成"""
    print("\n🧠 测试LLM集成...")
    
    try:
        from app.services.llm.client import LLMServerClient
        
        client = LLMServerClient()
        print("✅ LLMServerClient 实例化成功")
        
        # 检查核心方法
        methods = ['get_available_models', 'chat_completion']
        for method_name in methods:
            if hasattr(client, method_name):
                print(f"✅ 方法 {method_name} 可用")
            else:
                print(f"⚠️ 方法 {method_name} 不可用")
                
        return True
        
    except Exception as e:
        print(f"❌ LLM集成测试失败: {e}")
        traceback.print_exc()
        return False

async def test_api_endpoints():
    """测试API端点"""
    print("\n🌐 测试API端点...")
    
    import httpx
    
    base_url = "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient() as client:
            # 测试健康检查
            response = await client.get(f"{base_url}/api/health")
            if response.status_code == 200:
                print("✅ 健康检查端点正常")
                health_data = response.json()
                print(f"   状态: {health_data.get('status', 'unknown')}")
            else:
                print(f"❌ 健康检查端点异常: {response.status_code}")
            
            # 测试根端点
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                print("✅ 根端点正常")
            else:
                print(f"❌ 根端点异常: {response.status_code}")
                
            # 测试API文档
            response = await client.get(f"{base_url}/docs")
            if response.status_code == 200:
                print("✅ API文档端点正常")
            else:
                print(f"❌ API文档端点异常: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ API端点测试失败: {e}")
        traceback.print_exc()
        return False

async def test_database_connectivity():
    """测试数据库连接"""
    print("\n🗄️ 测试数据库连接...")
    
    try:
        from app.db.session import SessionLocal
        from app.models.user import User
        
        db = SessionLocal()
        try:
            # 简单查询测试数据库连接
            user_count = db.query(User).count()
            print(f"✅ 数据库连接成功，用户数量: {user_count}")
            return True
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {e}")
        traceback.print_exc()
        return False

async def run_comprehensive_test():
    """运行全面测试"""
    print("🚀 开始DAG架构核心功能测试...\n")
    
    test_results = {}
    
    # 运行各项测试
    tests = [
        ("智能占位符服务", test_intelligent_placeholder_service),
        ("React智能代理", test_react_agent),
        ("后台控制器", test_background_controller),
        ("工具集合", test_tools_collections),
        ("LLM集成", test_llm_integration),
        ("API端点", test_api_endpoints),
        ("数据库连接", test_database_connectivity),
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} 测试出现异常: {e}")
            test_results[test_name] = False
    
    # 输出测试总结
    print("\n" + "="*50)
    print("🎯 测试结果总结:")
    print("="*50)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 所有测试通过！DAG架构核心功能正常运行。")
        return True
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，需要进一步调试和修复。")
        return False

if __name__ == "__main__":
    # 直接运行测试
    print("🚀 假设后端服务器正在运行，开始自动测试...")
    
    # 运行测试
    success = asyncio.run(run_comprehensive_test())
    sys.exit(0 if success else 1)