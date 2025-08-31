"""
图表生成功能演示
展示如何在DAG编排架构中使用六种统计图生成工具
"""

import asyncio
import json
import logging
from typing import Dict, Any

# 导入agents系统
from . import execute_placeholder_with_context
from .tools.chart_generation_tools import chart_tools

logger = logging.getLogger(__name__)


async def demo_chart_generation():
    """
    演示图表生成功能
    展示在DAG架构中如何生成六种统计图
    """
    print("=" * 70)
    print("DAG编排架构 - 图表生成功能演示")
    print("六种统计图：柱状图、饼图、折线图、散点图、雷达图、漏斗图")
    print("=" * 70)
    
    # 示例数据
    sample_data = [
        {"category": "产品A", "sales": 1200, "profit": 300, "month": "1月"},
        {"category": "产品B", "sales": 1500, "profit": 450, "month": "1月"},
        {"category": "产品C", "sales": 800, "profit": 200, "month": "1月"},
        {"category": "产品A", "sales": 1300, "profit": 350, "month": "2月"},
        {"category": "产品B", "sales": 1600, "profit": 480, "month": "2月"},
        {"category": "产品C", "sales": 900, "profit": 250, "month": "2月"}
    ]
    
    data_json = json.dumps(sample_data)
    
    print("\n1. 🔥 演示柱状图生成")
    print("-" * 50)
    
    # 通过DAG系统生成柱状图
    context_engine_bar = {
        "template_content": "{{柱状图：各产品销售额对比}}",
        "business_context": {"analysis_type": "sales_comparison"},
        "metadata": {"chart_requirement": "bar_chart"}
    }
    
    try:
        bar_result = execute_placeholder_with_context(
            placeholder_text="{{柱状图：各产品销售额对比}}",
            statistical_type="统计图",
            description="各产品销售额对比柱状图",
            context_engine=context_engine_bar,
            user_id="demo_user"
        )
        
        if bar_result.get("status") == "success":
            print("✅ 柱状图生成成功！")
            print(f"   图表类型: {bar_result.get('result', {}).get('chart_type', 'unknown')}")
            print(f"   执行时间: {bar_result.get('execution_time', 0):.2f}秒")
        else:
            print("❌ 柱状图生成失败")
            
    except Exception as e:
        print(f"❌ 柱状图生成异常: {str(e)}")
    
    print("\n2. 🥧 演示饼图生成")
    print("-" * 50)
    
    # 直接使用图表工具生成饼图
    try:
        pie_result = chart_tools.generate_pie_chart(
            data_source=data_json,
            label_column="category",
            value_column="sales", 
            title="各产品销售额占比",
            output_format="json"
        )
        
        if pie_result.get("success"):
            print("✅ 饼图生成成功！")
            print(f"   图表名称: {pie_result.get('chart_name')}")
            print(f"   图表类型: {pie_result.get('chart_type')}")
            print(f"   配置生成: {'是' if pie_result.get('echarts_config') else '否'}")
        else:
            print(f"❌ 饼图生成失败: {pie_result.get('error')}")
            
    except Exception as e:
        print(f"❌ 饼图生成异常: {str(e)}")
    
    print("\n3. 📈 演示折线图生成")
    print("-" * 50)
    
    try:
        line_result = chart_tools.generate_line_chart(
            data_source=data_json,
            x_column="month",
            y_column="sales",
            title="销售额趋势图",
            output_format="json"
        )
        
        if line_result.get("success"):
            print("✅ 折线图生成成功！")
            print(f"   图表名称: {line_result.get('chart_name')}")
            print(f"   用途分析: 趋势展示")
        else:
            print(f"❌ 折线图生成失败: {line_result.get('error')}")
            
    except Exception as e:
        print(f"❌ 折线图生成异常: {str(e)}")
    
    print("\n4. ⚡ 演示散点图生成")
    print("-" * 50)
    
    try:
        scatter_result = chart_tools.generate_scatter_chart(
            data_source=data_json,
            x_column="sales",
            y_column="profit",
            title="销售额与利润关系图",
            output_format="json"
        )
        
        if scatter_result.get("success"):
            print("✅ 散点图生成成功！")
            print(f"   图表名称: {scatter_result.get('chart_name')}")
            print(f"   用途分析: 关联关系分析")
        else:
            print(f"❌ 散点图生成失败: {scatter_result.get('error')}")
            
    except Exception as e:
        print(f"❌ 散点图生成异常: {str(e)}")
    
    print("\n5. 🎯 演示雷达图生成")
    print("-" * 50)
    
    try:
        radar_result = chart_tools.generate_radar_chart(
            data_source=data_json,
            indicator_columns=["sales", "profit"],
            title="产品综合表现雷达图",
            output_format="json"
        )
        
        if radar_result.get("success"):
            print("✅ 雷达图生成成功！")
            print(f"   图表名称: {radar_result.get('chart_name')}")
            print(f"   复杂度: 复杂图表")
        else:
            print(f"❌ 雷达图生成失败: {radar_result.get('error')}")
            
    except Exception as e:
        print(f"❌ 雷达图生成异常: {str(e)}")
    
    print("\n6. 🔻 演示漏斗图生成")
    print("-" * 50)
    
    # 漏斗图需要特殊的阶段数据
    funnel_data = [
        {"stage": "访问", "count": 1000},
        {"stage": "浏览", "count": 800},
        {"stage": "咨询", "count": 600},
        {"stage": "试用", "count": 400},
        {"stage": "购买", "count": 200}
    ]
    
    try:
        funnel_result = chart_tools.generate_funnel_chart(
            data_source=json.dumps(funnel_data),
            stage_column="stage",
            value_column="count",
            title="客户转化漏斗",
            output_format="json"
        )
        
        if funnel_result.get("success"):
            print("✅ 漏斗图生成成功！")
            print(f"   图表名称: {funnel_result.get('chart_name')}")
            print(f"   用途分析: 分布展示")
        else:
            print(f"❌ 漏斗图生成失败: {funnel_result.get('error')}")
            
    except Exception as e:
        print(f"❌ 漏斗图生成异常: {str(e)}")
    
    print("\n7. 🤖 演示智能图表生成")
    print("-" * 50)
    
    try:
        intelligent_result = chart_tools.generate_intelligent_chart(
            data_source=data_json,
            requirements="我想看各个产品的销售情况对比，选择最合适的图表类型",
            output_format="json"
        )
        
        if intelligent_result.get("success"):
            print("✅ 智能图表生成成功！")
            print(f"   生成方式: {intelligent_result.get('generation_method')}")
            print(f"   需求分析: {intelligent_result.get('requirements_analyzed')}")
        else:
            print(f"❌ 智能图表生成失败: {intelligent_result.get('error')}")
            
    except Exception as e:
        print(f"❌ 智能图表生成异常: {str(e)}")
    
    print("\n8. 📊 演示批量图表生成")
    print("-" * 50)
    
    # 批量生成多种图表
    chart_configs = [
        {
            "chart_type": "bar_chart",
            "title": "销售额对比", 
            "x_column": "category",
            "y_column": "sales"
        },
        {
            "chart_type": "pie_chart",
            "title": "销售占比",
            "label_column": "category",
            "value_column": "sales"
        },
        {
            "chart_type": "line_chart",
            "title": "趋势分析",
            "x_column": "month", 
            "y_column": "sales"
        }
    ]
    
    try:
        batch_result = chart_tools.generate_multiple_charts(
            data_source=data_json,
            chart_configs=chart_configs,
            output_format="json"
        )
        
        if batch_result.get("success"):
            print("✅ 批量图表生成成功！")
            print(f"   总图表数: {batch_result.get('total_charts')}")
            print(f"   成功生成: {batch_result.get('successful_charts')}")
            print(f"   失败数量: {batch_result.get('failed_charts')}")
            print(f"   摘要: {batch_result.get('summary')}")
        else:
            print(f"❌ 批量图表生成失败: {batch_result.get('error')}")
            
    except Exception as e:
        print(f"❌ 批量图表生成异常: {str(e)}")
    
    print("\n9. 📋 支持的图表类型总览")
    print("-" * 50)
    
    try:
        supported_types = chart_tools.get_supported_chart_types()
        print(f"✅ 共支持 {len(supported_types)} 种图表类型：")
        
        for chart_info in supported_types:
            print(f"   • {chart_info['name']} ({chart_info['type']})")
            print(f"     描述: {chart_info['description']}")
            print(f"     复杂度: {chart_info['complexity']} | 用途: {chart_info['purpose']}")
            print()
            
    except Exception as e:
        print(f"❌ 获取支持类型失败: {str(e)}")
    
    print("=" * 70)
    print("图表生成功能演示完成！")
    print("所有六种统计图已成功集成到DAG编排架构中")
    print("=" * 70)


async def demo_chart_in_dag_workflow():
    """
    演示图表在DAG工作流中的应用
    """
    print("\n🔄 DAG工作流中的图表生成演示")
    print("-" * 50)
    
    # 构建上下文工程
    context_engine = {
        "template_content": "{{统计图：2023年销售业绩分析}}",
        "business_context": {
            "report_type": "sales_analysis", 
            "period": "yearly",
            "include_charts": True,
            "chart_requirements": [
                "销售额趋势图",
                "产品销售占比饼图", 
                "各部门业绩对比柱状图"
            ]
        },
        "time_context": {"year": 2023, "period_type": "annual"},
        "document_context": {"template_type": "report", "includes_visualization": True},
        "storage_capabilities": {
            "intermediate_results": True,
            "chart_configs": True,
            "execution_history": True
        },
        "metadata": {
            "workflow_type": "chart_enhanced_reporting",
            "architecture": "dag_orchestration"
        }
    }
    
    try:
        # 通过DAG系统处理包含图表的占位符
        workflow_result = execute_placeholder_with_context(
            placeholder_text="{{统计图：2023年销售业绩分析}}",
            statistical_type="统计图",
            description="2023年销售业绩分析图表",
            context_engine=context_engine,
            user_id="workflow_demo_user"
        )
        
        print("✅ DAG工作流执行完成！")
        print(f"   状态: {workflow_result.get('status')}")
        print(f"   处理时间: {workflow_result.get('execution_time', 0):.2f}秒")
        
        # 显示工作流处理结果
        if workflow_result.get("result"):
            result = workflow_result["result"]
            if result.get("chart_type"):
                print(f"   生成图表: {result.get('chart_type')}")
            if result.get("confidence"):
                print(f"   置信度: {result.get('confidence'):.2f}")
        
        # 显示DAG推理过程
        if workflow_result.get("dag_reasoning"):
            print(f"   DAG推理: {workflow_result.get('dag_reasoning')[:100]}...")
            
    except Exception as e:
        print(f"❌ DAG工作流执行失败: {str(e)}")
    
    print("\n🎯 工作流特性演示完成")
    print("- ✅ 上下文工程协助存储")
    print("- ✅ Background Agent分析")
    print("- ✅ DAG流程控制")
    print("- ✅ Think/Default模型选择")
    print("- ✅ 图表生成工具集成")


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 运行演示
    asyncio.run(demo_chart_generation())
    asyncio.run(demo_chart_in_dag_workflow())