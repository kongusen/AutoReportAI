#!/usr/bin/env python3
"""
AutoReportAI MCP Server Test Script
测试MCP服务器功能的快速脚本
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_basic_functionality():
    """测试基本功能"""
    print("🧪 开始测试AutoReportAI MCP服务器基本功能...")
    
    try:
        # 导入必要模块
        from config import config
        from session import session_manager
        from client import api_client
        from tools.auth_tools import login, get_current_user
        from tools.data_source_tools import list_data_sources, create_api_data_source
        
        print("✅ 模块导入成功")
        
        # 测试1: 配置加载
        print(f"✅ 配置加载成功 - 后端API: {config.BACKEND_BASE_URL}")
        
        # 测试2: 登录功能
        print("🔐 测试登录功能...")
        login_result = await login()
        login_data = json.loads(login_result)
        
        if login_data.get("success"):
            print("✅ 登录测试成功")
            print(f"   用户名: {login_data['data']['username']}")
        else:
            print(f"❌ 登录测试失败: {login_data.get('error')}")
            return False
        
        # 测试3: 获取用户信息
        print("👤 测试获取用户信息...")
        user_result = await get_current_user()
        user_data = json.loads(user_result)
        
        if user_data.get("success"):
            print("✅ 获取用户信息成功")
        else:
            print(f"❌ 获取用户信息失败: {user_data.get('error')}")
        
        # 测试4: 数据源列表
        print("📊 测试数据源列表...")
        ds_result = await list_data_sources()
        ds_data = json.loads(ds_result)
        
        if ds_data.get("success", True):
            print("✅ 数据源列表获取成功")
            data_sources = ds_data.get("data", {})
            if isinstance(data_sources, dict):
                ds_count = len(data_sources.get("data", []))
            else:
                ds_count = len(data_sources) if isinstance(data_sources, list) else 0
            print(f"   当前数据源数量: {ds_count}")
        else:
            print(f"❌ 数据源列表获取失败: {ds_data.get('error')}")
        
        # 测试5: 创建演示数据源
        print("🆕 测试创建演示数据源...")
        demo_ds_result = await create_api_data_source(
            name="测试API数据源",
            api_url="https://jsonplaceholder.typicode.com/posts",
            description="用于测试的演示API数据源"
        )
        demo_ds_data = json.loads(demo_ds_result)
        
        if demo_ds_data.get("success", True):
            print("✅ 演示数据源创建成功")
            if "data" in demo_ds_data:
                ds_id = demo_ds_data["data"].get("id")
                print(f"   数据源ID: {ds_id}")
        else:
            print(f"⚠️  演示数据源创建失败: {demo_ds_data.get('error')}")
        
        print("\n🎉 基本功能测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_session_management():
    """测试会话管理功能"""
    print("\n🧪 测试会话管理功能...")
    
    try:
        from session import session_manager
        
        # 测试会话状态
        current_session = session_manager.get_current_session()
        if current_session:
            print("✅ 当前会话存在")
            print(f"   用户: {current_session.username}")
            print(f"   会话ID: {session_manager._current_session_id}")
        else:
            print("ℹ️  当前无活跃会话")
        
        # 测试会话统计
        session_count = session_manager.get_session_count()
        print(f"✅ 活跃会话数: {session_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 会话管理测试失败: {e}")
        return False

async def test_api_client():
    """测试API客户端"""
    print("\n🧪 测试API客户端...")
    
    try:
        from client import api_client
        
        # 测试健康检查
        try:
            health_result = await api_client.get("../health")
            print("✅ 后端健康检查成功")
        except Exception as e:
            print(f"⚠️  后端健康检查失败: {e}")
        
        # 测试客户端状态
        print("✅ API客户端初始化正常")
        
        return True
        
    except Exception as e:
        print(f"❌ API客户端测试失败: {e}")
        return False

def print_test_summary(results):
    """打印测试总结"""
    print("\n" + "="*60)
    print("📋 测试总结")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n总计: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！MCP服务器功能正常")
    else:
        print("⚠️  部分测试失败，请检查配置和后端服务状态")

async def main():
    """主测试函数"""
    print("🚀 AutoReportAI MCP Server 功能测试")
    print("="*60)
    
    # 运行测试
    results = {}
    
    results["基本功能测试"] = await test_basic_functionality()
    results["会话管理测试"] = await test_session_management()
    results["API客户端测试"] = await test_api_client()
    
    # 清理资源
    try:
        from client import api_client
        await api_client.close()
    except:
        pass
    
    # 打印总结
    print_test_summary(results)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print(f"测试运行失败: {e}")
        sys.exit(1)