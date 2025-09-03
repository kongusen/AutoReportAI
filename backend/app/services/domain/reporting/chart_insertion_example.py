"""
图表插入功能使用示例
展示如何在Word文档中插入生成的图表
"""

import asyncio
from typing import Dict, Any, List
from app.services.domain.reporting.word_generator_service import WordGeneratorService
from app.services.domain.reporting.chart_integration_service import ChartIntegrationService


async def example_chart_insertion():
    """
    完整的图表生成和插入示例
    """
    
    # 1. 模拟模板内容（包含图表占位符）
    template_content = """
# 销售业绩分析报告

## 报告概述
本报告展示了{{报告年份}}年的销售业绩分析。

## 关键指标
- 总销售额: {{total_sales}}万元
- 同比增长: {{growth_rate}}%
- 活跃客户数: {{active_customers}}个

## 数据可视化

### 月度销售趋势
{{chart:line:销售趋势分析}}

以上图表显示了各月销售额的变化趋势。

### 产品销售占比
{{chart:pie:产品销售占比}}

### 区域销售对比
{{chart:bar:区域销售对比}}

## 分析结论
根据以上数据分析...
"""
    
    # 2. 模拟占位符数据
    placeholder_values = {
        "报告年份": "2024",
        "total_sales": "1250",
        "growth_rate": "15.3",
        "active_customers": "2850"
    }
    
    # 3. 模拟图表生成结果
    chart_results = [
        {
            "success": True,
            "chart_type": "line_chart",
            "filepath": "/Users/shan/work/me/AutoReportAI/storage/reports/line_chart_12345678.png",
            "filename": "line_chart_12345678.png",
            "title": "销售趋势分析",
            "series_count": 2,
            "chinese_support": True
        },
        {
            "success": True,
            "chart_type": "pie_chart", 
            "filepath": "/Users/shan/work/me/AutoReportAI/storage/reports/pie_chart_87654321.png",
            "filename": "pie_chart_87654321.png",
            "title": "产品销售占比",
            "categories": 5,
            "chinese_support": True
        },
        {
            "success": True,
            "chart_type": "bar_chart",
            "filepath": "/Users/shan/work/me/AutoReportAI/storage/reports/bar_chart_11223344.png", 
            "filename": "bar_chart_11223344.png",
            "title": "区域销售对比",
            "data_points": 6,
            "chinese_support": True
        }
    ]
    
    # 4. 使用完善的WordGeneratorService
    word_service = WordGeneratorService()
    
    try:
        # 生成包含图表的报告
        report_path = word_service.generate_report_from_template(
            template_content=template_content,
            placeholder_values=placeholder_values,
            title="2024年销售业绩分析报告",
            chart_results=chart_results
        )
        
        print(f"✅ 报告生成成功: {report_path}")
        print("📊 图表插入完成:")
        for chart in chart_results:
            print(f"   - {chart['title']} ({chart['chart_type']})")
            
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")


def example_chart_placeholder_patterns():
    """
    展示支持的图表占位符格式
    """
    patterns = {
        "基础格式": [
            "{{chart:bar}}",      # 柱状图
            "{{chart:line}}",     # 折线图
            "{{chart:pie}}",      # 饼图
        ],
        "带标题格式": [
            "{{chart:bar:销售业绩}}",        # 指定标题的柱状图
            "{{chart:line:趋势分析}}",       # 指定标题的折线图
            "{{chart:pie:产品占比}}",        # 指定标题的饼图
        ],
        "模板示例": [
            "## 销售分析\n{{chart:bar:月度销售额}}\n\n分析结论...",
            "趋势图如下：\n{{chart:line}}\n以上是关键趋势。",
            "各产品占比情况：{{chart:pie:产品分布}}，可以看出..."
        ]
    }
    
    print("📋 支持的图表占位符格式:")
    for category, examples in patterns.items():
        print(f"\n{category}:")
        for example in examples:
            print(f"   {example}")


def example_chart_size_control():
    """
    展示图表尺寸控制功能
    """
    size_settings = {
        "默认尺寸": {
            "宽度": "6.0英寸",
            "高度": "4.0英寸"
        },
        "最大尺寸限制": {
            "最大宽度": "6.5英寸", 
            "最大高度": "5.0英寸"
        },
        "自动调整": [
            "保持图片原始宽高比",
            "根据内容自动调整到合适尺寸",
            "超出最大限制时自动缩放"
        ]
    }
    
    print("📏 图表尺寸控制:")
    for category, info in size_settings.items():
        print(f"\n{category}:")
        if isinstance(info, dict):
            for key, value in info.items():
                print(f"   {key}: {value}")
        else:
            for item in info:
                print(f"   • {item}")


async def example_error_handling():
    """
    展示错误处理机制
    """
    print("🛠️ 错误处理机制:")
    
    error_scenarios = [
        {
            "场景": "图表文件不存在",
            "处理": "显示红色错误提示文本 '[图表文件不存在: 图表名称]'"
        },
        {
            "场景": "图表类型不匹配", 
            "处理": "使用第一个可用图表作为备选"
        },
        {
            "场景": "占位符格式错误",
            "处理": "显示 '[图表未找到: 类型名]' 提示"
        },
        {
            "场景": "图片插入失败",
            "处理": "显示错误信息，不中断文档生成"
        },
        {
            "场景": "全部图表生成失败",
            "处理": "降级到纯文本报告，保证基本功能"
        }
    ]
    
    for scenario in error_scenarios:
        print(f"   • {scenario['场景']}: {scenario['处理']}")


async def main():
    """主函数：运行所有示例"""
    print("🚀 AutoReportAI 图表插入功能演示")
    print("=" * 50)
    
    # 1. 基础图表插入示例
    print("\n1. 基础图表插入示例:")
    await example_chart_insertion()
    
    # 2. 占位符格式说明
    print("\n2. 占位符格式说明:")
    example_chart_placeholder_patterns()
    
    # 3. 尺寸控制说明
    print("\n3. 图表尺寸控制:")
    example_chart_size_control()
    
    # 4. 错误处理机制
    print("\n4. 错误处理机制:")
    await example_error_handling()
    
    print("\n" + "=" * 50)
    print("✨ 演示完成！图表插入功能已完善。")


if __name__ == "__main__":
    asyncio.run(main())