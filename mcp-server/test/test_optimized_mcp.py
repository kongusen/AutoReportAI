#!/usr/bin/env python3
"""
AutoReportAI 优化版 MCP Server 测试脚本
验证16个核心工具的完整性和分析流程覆盖
"""
import sys
import os
from pathlib import Path

# 添加MCP服务器路径
sys.path.insert(0, str(Path(__file__).parent))

async def test_optimized_mcp_tools():
    """测试优化版MCP服务器工具"""
    print("🧪 AutoReportAI 优化版 MCP Server 工具测试")
    print("=" * 60)
    
    try:
        # 导入优化版主模块
        from main_optimized import mcp
        
        # 获取所有注册的工具
        try:
            tools_list = await mcp.list_tools()
            tools = {tool.name: tool for tool in tools_list}
            tool_count = len(tools)
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            tools = {}
            tool_count = 0
        
        print(f"📊 注册工具数量: {tool_count}")
        
        # 验证工具数量是否符合要求
        if tool_count <= 18:
            print("✅ 工具数量符合要求 (≤18个)")
        else:
            print(f"❌ 工具数量超标: {tool_count} > 18")
            return False
        
        print("\n🛠️  注册工具列表:")
        
        # 按功能分类统计工具
        tool_categories = {
            "认证管理": [],
            "数据源管理": [],
            "模板管理": [],
            "AI供应商配置": [],
            "任务管理": [],
            "报告查询": [],
            "系统工具": []
        }
        
        # 工具分类映射
        category_mapping = {
            "setup_session": "认证管理",
            "check_session": "认证管理",
            "list_all_data_sources": "数据源管理",
            "create_doris_source": "数据源管理",
            "upload_csv_source": "数据源管理",
            "verify_data_source": "数据源管理",
            "list_all_templates": "模板管理",
            "create_template": "模板管理",
            "upload_template": "模板管理",
            "get_template_info": "模板管理",
            "configure_ai_provider": "AI供应商配置",
            "verify_ai_provider": "AI供应商配置",
            "create_analysis_task": "任务管理",
            "execute_task": "任务管理",
            "check_task_status": "任务管理",
            "get_analysis_result": "报告查询",
            "get_system_status": "系统工具",
            "create_complete_workflow": "系统工具"
        }
        
        # 分类统计
        for tool_name in tools.keys():
            category = category_mapping.get(tool_name, "其他")
            if category in tool_categories:
                tool_categories[category].append(tool_name)
            else:
                tool_categories.setdefault("其他", []).append(tool_name)
        
        # 显示分类结果
        for category, tool_list in tool_categories.items():
            if tool_list:
                print(f"  {category} ({len(tool_list)}个): {', '.join(tool_list)}")
        
        # 验证核心工具是否存在
        print("\n🎯 核心工具验证:")
        required_tools = [
            "setup_session", "create_doris_source", "upload_template",
            "configure_ai_provider", "create_analysis_task", "execute_task",
            "get_analysis_result"
        ]
        
        missing_tools = []
        for tool in required_tools:
            if tool in tools:
                print(f"  ✅ {tool}")
            else:
                print(f"  ❌ {tool} (缺失)")
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"\n❌ 缺失关键工具: {missing_tools}")
            return False
        
        # 验证完整分析流程覆盖
        print("\n🔄 分析流程覆盖验证:")
        workflow_steps = [
            ("1. 认证登录", "setup_session"),
            ("2. 数据源配置", "create_doris_source"),
            ("3. 模板上传", "upload_template"),
            ("4. AI配置", "configure_ai_provider"),
            ("5. 任务创建", "create_analysis_task"),
            ("6. 任务执行", "execute_task"),
            ("7. 结果获取", "get_analysis_result")
        ]
        
        workflow_complete = True
        for step_desc, tool_name in workflow_steps:
            if tool_name in tools:
                print(f"  ✅ {step_desc} ({tool_name})")
            else:
                print(f"  ❌ {step_desc} ({tool_name}) - 缺失")
                workflow_complete = False
        
        if not workflow_complete:
            print("\n❌ 分析流程不完整")
            return False
        
        # 验证文件处理能力
        print("\n📤 文件处理能力验证:")
        file_tools = ["upload_template", "upload_csv_source"]
        file_support = True
        
        for tool in file_tools:
            if tool in tools:
                print(f"  ✅ {tool} - 支持文件上传")
            else:
                print(f"  ❌ {tool} - 不支持文件上传")
                file_support = False
        
        # 验证配置验证能力
        print("\n🔍 配置验证能力:")
        validation_tools = ["verify_data_source", "verify_ai_provider", "check_task_status"]
        validation_support = True
        
        for tool in validation_tools:
            if tool in tools:
                print(f"  ✅ {tool} - 支持配置验证")
            else:
                print(f"  ❌ {tool} - 不支持配置验证")
                validation_support = False
        
        # 总结测试结果
        print("\n" + "="*60)
        print("📊 测试结果总结")
        print("="*60)
        
        results = {
            "工具数量控制": tool_count <= 18,
            "核心工具完整": len(missing_tools) == 0,
            "流程覆盖完整": workflow_complete,
            "文件处理支持": file_support,
            "配置验证支持": validation_support
        }
        
        all_passed = all(results.values())
        
        for test_name, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"  {test_name}: {status}")
        
        if all_passed:
            print(f"\n🎉 所有测试通过！优化版MCP服务器已准备就绪")
            print(f"   - 工具数量: {tool_count}/18")
            print(f"   - 功能完整性: 100%")
            print(f"   - 流程覆盖: 7/7步骤")
            return True
        else:
            failed_tests = [name for name, passed in results.items() if not passed]
            print(f"\n⚠️  部分测试失败: {failed_tests}")
            return False
        
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

async def main():
    """主测试函数"""
    success = await test_optimized_mcp_tools()
    
    if success:
        print(f"\n🚀 AutoReportAI 优化版 MCP Server 测试成功！")
        return 0
    else:
        print(f"\n💥 AutoReportAI 优化版 MCP Server 测试失败！")
        return 1

if __name__ == "__main__":
    import asyncio
    exit(asyncio.run(main()))