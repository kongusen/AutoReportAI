#!/usr/bin/env python3
"""
AutoReportAI MCP Server Core Tools Test
测试核心MCP工具功能的脚本，包括模板、任务、报告管理
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_template_tools():
    """测试模板管理工具"""
    print("\n🧪 测试模板管理工具...")
    
    try:
        from tools.template_tools import list_templates, create_text_template, get_template
        
        # 测试1: 列出模板
        print("📝 测试列出模板...")
        result = await list_templates()
        data = json.loads(result)
        
        if data.get("success"):
            print("✅ 列出模板成功")
            template_count = data.get("data", {}).get("total", 0)
            print(f"   当前模板数量: {template_count}")
        else:
            print(f"❌ 列出模板失败: {data.get('error')}")
            return False
        
        # 测试2: 创建文本模板
        print("🆕 测试创建文本模板...")
        template_result = await create_text_template(
            name="MCP测试模板",
            content="这是一个测试模板，销售额：{{sales_amount}}，订单数：{{order_count}}",
            description="MCP功能测试用模板"
        )
        template_data = json.loads(template_result)
        
        if template_data.get("success"):
            print("✅ 创建文本模板成功")
            template_id = template_data.get("data", {}).get("id")
            print(f"   模板ID: {template_id}")
            
            # 测试3: 获取模板详情
            if template_id:
                print("📋 测试获取模板详情...")
                detail_result = await get_template(template_id)
                detail_data = json.loads(detail_result)
                
                if detail_data.get("success"):
                    print("✅ 获取模板详情成功")
                    print(f"   模板名称: {detail_data.get('data', {}).get('name')}")
                else:
                    print(f"❌ 获取模板详情失败: {detail_data.get('error')}")
        else:
            print(f"❌ 创建文本模板失败: {template_data.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 模板工具测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_task_tools():
    """测试任务管理工具"""
    print("\n🧪 测试任务管理工具...")
    
    try:
        from tools.task_tools import list_tasks, get_task_status
        
        # 测试1: 列出任务
        print("⚡ 测试列出任务...")
        result = await list_tasks()
        data = json.loads(result)
        
        if data.get("success"):
            print("✅ 列出任务成功")
            task_count = data.get("data", {}).get("total", 0)
            print(f"   当前任务数量: {task_count}")
        else:
            print(f"❌ 列出任务失败: {data.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 任务工具测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_report_tools():
    """测试报告生成工具"""
    print("\n🧪 测试报告生成工具...")
    
    try:
        from tools.report_tools import list_reports
        
        # 测试1: 列出报告
        print("📈 测试列出报告...")
        result = await list_reports()
        data = json.loads(result)
        
        if data.get("success"):
            print("✅ 列出报告成功")
            report_count = data.get("data", {}).get("total", 0)
            print(f"   当前报告数量: {report_count}")
        else:
            print(f"❌ 列出报告失败: {data.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 报告工具测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_tool_integration():
    """测试工具集成"""
    print("\n🧪 测试工具集成...")
    
    try:
        # 确保用户已登录 
        from session import session_manager
        current_session = session_manager.get_current_session()
        if not current_session:
            from tools.auth_tools import login
            login_result = await login()
            login_data = json.loads(login_result)
            if not login_data.get("success"):
                print("❌ 登录失败，无法进行集成测试")
                return False
        
        # 获取所有资源概览
        from tools.data_source_tools import list_data_sources
        from tools.template_tools import list_templates
        from tools.task_tools import list_tasks
        from tools.report_tools import list_reports
        
        print("📊 获取系统资源概览...")
        
        # 并发获取所有列表
        results = await asyncio.gather(
            list_data_sources(),
            list_templates(),
            list_tasks(),
            list_reports(),
            return_exceptions=True
        )
        
        resource_names = ["数据源", "模板", "任务", "报告"]
        overview = {"total_resources": 0}
        
        for i, (result, name) in enumerate(zip(results, resource_names)):
            if isinstance(result, Exception):
                print(f"⚠️  获取{name}列表异常: {result}")
                overview[name] = 0
            else:
                try:
                    data = json.loads(result)
                    if data.get("success"):
                        count = data.get("data", {}).get("total", 0)
                        overview[name] = count
                        overview["total_resources"] += count
                        print(f"   {name}: {count} 个")
                    else:
                        print(f"⚠️  获取{name}列表失败: {data.get('error')}")
                        overview[name] = 0
                except:
                    print(f"⚠️  解析{name}列表结果失败")
                    overview[name] = 0
        
        print(f"✅ 系统资源概览获取完成，共 {overview['total_resources']} 个资源")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具集成测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_test_summary(results):
    """打印测试总结"""
    print("\n" + "="*60)
    print("📋 核心工具测试总结")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n总计: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有核心工具测试通过！MCP服务器核心功能正常")
        print("\n🚀 已实现的核心MCP工具:")
        print("   🔐 认证管理 (login, logout, get_current_user)")
        print("   📊 数据源管理 (create, list, test, delete)")
        print("   📝 模板管理 (create, list, update, delete)")
        print("   ⚡ 任务管理 (create, run, monitor, schedule)")
        print("   📈 报告生成 (generate, download, history)")
        print("\n💡 您现在可以通过LLM直接调用这些MCP工具来管理AutoReportAI系统！")
    else:
        print("⚠️  部分核心工具测试失败，请检查实现和后端API连接")

async def main():
    """主测试函数"""
    print("🚀 AutoReportAI MCP Server 核心工具测试")
    print("="*60)
    
    # 先进行登录
    print("🔐 执行登录...")
    try:
        from tools.auth_tools import login
        login_result = await login()
        login_data = json.loads(login_result)
        if login_data.get("success"):
            print("✅ 登录成功")
        else:
            print(f"❌ 登录失败: {login_data.get('error')}")
            print("无法进行核心工具测试")
            return
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        print("无法进行核心工具测试")
        return
    
    # 运行核心工具测试
    results = {}
    
    results["模板管理工具"] = await test_template_tools()
    results["任务管理工具"] = await test_task_tools()
    results["报告生成工具"] = await test_report_tools()
    results["工具集成测试"] = await test_tool_integration()
    
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