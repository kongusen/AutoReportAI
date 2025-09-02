#!/usr/bin/env python3
"""
测试React Agent的图表生成功能
验证Agent是否能调用工具生成真实图表
"""

import asyncio
import json
import sys
import os
import time

# 添加backend目录到Python路径
sys.path.append('/Users/shan/work/me/AutoReportAI/backend')

async def test_chart_generation_tool():
    """测试图表生成工具"""
    print("🛠️ 测试图表生成工具...")
    
    try:
        from app.services.infrastructure.ai.tools.chart_generator_tool import generate_chart, generate_sample_data
        
        # 测试柱状图生成
        print("\n📊 测试柱状图生成...")
        sample_data = generate_sample_data()
        bar_config = sample_data["bar_chart_sample"]
        
        result = generate_chart(json.dumps(bar_config))
        result_data = json.loads(result)
        
        if result_data.get("success"):
            print(f"✅ 柱状图生成成功: {result_data['filename']}")
            print(f"   文件路径: {result_data['filepath']}")
            print(f"   数据点数: {result_data['data_points']}")
        else:
            print(f"❌ 柱状图生成失败: {result_data.get('error')}")
        
        # 测试折线图生成
        print("\n📈 测试折线图生成...")
        line_config = sample_data["line_chart_sample"]
        
        result = generate_chart(json.dumps(line_config))
        result_data = json.loads(result)
        
        if result_data.get("success"):
            print(f"✅ 折线图生成成功: {result_data['filename']}")
            print(f"   系列数量: {result_data['series_count']}")
        else:
            print(f"❌ 折线图生成失败: {result_data.get('error')}")
        
        # 测试饼图生成
        print("\n🥧 测试饼图生成...")
        pie_config = sample_data["pie_chart_sample"]
        
        result = generate_chart(json.dumps(pie_config))
        result_data = json.loads(result)
        
        if result_data.get("success"):
            print(f"✅ 饼图生成成功: {result_data['filename']}")
            print(f"   类别数量: {result_data['categories']}")
        else:
            print(f"❌ 饼图生成失败: {result_data.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 图表工具测试失败: {e}")
        return False

async def test_react_agent_with_charts():
    """测试React Agent的图表生成能力"""
    print("\n🤖 测试React Agent图表生成...")
    
    try:
        from app.services.infrastructure.ai.agents import create_react_agent
        
        # 创建用户专属React Agent
        user_id = "test_user_charts"
        agent = create_react_agent(user_id)
        
        print(f"初始化Agent (用户: {user_id})...")
        await agent.initialize()
        
        # 测试图表生成对话
        test_messages = [
            "请帮我分析一下销售业绩，并生成相关图表",
            "生成一个显示业务增长趋势的折线图",
            "创建一个市场份额分布的饼图",
            "我需要看一下产品销售的可视化数据"
        ]
        
        results = []
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n💬 测试对话 {i}: {message}")
            
            start_time = time.time()
            response = await agent.chat(message, context={
                "task_type": "chart_generation_test",
                "test_id": f"test_{i}"
            })
            response_time = time.time() - start_time
            
            print(f"⏱️  响应时间: {response_time:.2f}秒")
            
            # 检查响应
            if hasattr(response, 'charts') and response.charts:
                print(f"📊 生成图表数量: {len(response.charts)}")
                for j, chart in enumerate(response.charts, 1):
                    print(f"   图表{j}: {chart.get('title', 'N/A')} - {chart.get('filename', 'N/A')}")
                results.append({"message": message, "charts": len(response.charts), "success": True})
            else:
                print("⚠️  未检测到图表生成")
                results.append({"message": message, "charts": 0, "success": False})
            
            print(f"📝 Agent响应:\n{response}")
            print("-" * 60)
        
        # 统计结果
        total_tests = len(results)
        successful_chart_generations = sum(1 for r in results if r['success'] and r['charts'] > 0)
        total_charts = sum(r['charts'] for r in results)
        
        print(f"\n📊 测试结果统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   成功生成图表的对话: {successful_chart_generations}")
        print(f"   总生成图表数: {total_charts}")
        print(f"   成功率: {successful_chart_generations/total_tests*100:.1f}%")
        
        return successful_chart_generations > 0
        
    except Exception as e:
        print(f"❌ React Agent测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integrated_report_with_charts():
    """测试集成的报告生成（带图表）"""
    print("\n📄 测试集成报告生成（带图表）...")
    
    try:
        from app.services.infrastructure.ai.agents import create_react_agent
        
        user_id = "test_user_report"
        agent = create_react_agent(user_id)
        await agent.initialize()
        
        # 请求生成完整的业务报告
        report_request = """
        请生成一份完整的业务分析报告，要求包含：
        1. 销售业绩的柱状图分析
        2. 增长趋势的折线图
        3. 市场份额的饼图分析
        4. 基于图表的业务洞察和建议
        
        请确保报告包含实际的图表文件。
        """
        
        print("🤖 请求生成完整业务报告...")
        start_time = time.time()
        
        response = await agent.chat(report_request, context={
            "task_type": "comprehensive_report",
            "include_charts": True,
            "optimization_level": "enhanced"
        })
        
        generation_time = time.time() - start_time
        print(f"⏱️  报告生成时间: {generation_time:.2f}秒")
        
        # 分析响应
        if hasattr(response, 'charts') and response.charts:
            print(f"✅ 报告生成成功，包含 {len(response.charts)} 个图表:")
            for i, chart in enumerate(response.charts, 1):
                print(f"   📊 图表{i}: {chart.get('title')} ({chart.get('chart_type')})")
                print(f"      文件: {chart.get('filename')}")
        else:
            print("⚠️  报告生成但未包含图表")
        
        print(f"\n📝 完整报告内容:")
        print("=" * 80)
        print(response)
        print("=" * 80)
        
        # 保存报告到文件
        timestamp = int(time.time())
        report_filename = f"agent_generated_report_with_charts_{timestamp}.md"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(str(response))
        
        print(f"💾 报告已保存到: {report_filename}")
        
        return hasattr(response, 'charts') and len(response.charts) > 0
        
    except Exception as e:
        print(f"❌ 集成报告测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🚀 React Agent图表生成功能测试")
    print("=" * 80)
    
    # 测试结果
    results = {}
    
    # 1. 测试图表生成工具
    print("\n🔧 第1步: 测试图表生成工具")
    results['chart_tool'] = await test_chart_generation_tool()
    
    # 2. 测试React Agent图表能力
    print("\n🤖 第2步: 测试React Agent图表生成")
    results['agent_charts'] = await test_react_agent_with_charts()
    
    # 3. 测试集成报告生成
    print("\n📊 第3步: 测试集成报告生成")
    results['integrated_report'] = await test_integrated_report_with_charts()
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("🎯 测试结果汇总")
    print("=" * 80)
    
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
    
    success_rate = success_count / total_count * 100
    print(f"\n🎯 总体通过率: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_count == total_count:
        print("🎉 所有测试通过！Agent图表生成功能完全可用")
        print("✨ React Agent现在可以生成专业的图表文件")
        print("📊 支持柱状图、折线图、饼图、面积图等多种图表类型")
    elif success_count >= total_count * 0.5:
        print("⚠️  部分测试通过，功能基本可用但需要优化")
    else:
        print("❌ 多个测试失败，需要检查系统配置")
    
    # 显示生成的图表文件位置
    charts_dir = "/Users/shan/work/me/AutoReportAI/storage/reports"
    if os.path.exists(charts_dir):
        chart_files = [f for f in os.listdir(charts_dir) if f.endswith('.png')]
        if chart_files:
            print(f"\n📂 生成的图表文件 ({len(chart_files)} 个):")
            for file in chart_files[-5:]:  # 显示最新的5个文件
                print(f"   📊 {file}")
            if len(chart_files) > 5:
                print(f"   ... 还有 {len(chart_files) - 5} 个文件")
            print(f"📁 完整路径: {charts_dir}")
    
    return success_count == total_count

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)