"""
测试图表生成工具

验证 Agent 图表工具的完整功能，包括：
1. 图表生成工具基础功能
2. 数据分析和推荐功能
3. 与 ETL 数据的集成
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.infrastructure.agents.tools.chart_tools import (
    ChartGenerationTool,
    ChartDataAnalyzerTool
)


async def test_chart_generation_basic():
    """测试基础图表生成功能"""
    print("\n" + "="*60)
    print("测试 1: 基础图表生成")
    print("="*60)

    chart_tool = ChartGenerationTool()

    # 测试柱状图
    test_data = {
        "chart_type": "bar",
        "data": [
            {"month": "1月", "sales": 1200},
            {"month": "2月", "sales": 1500},
            {"month": "3月", "sales": 1800},
            {"month": "4月", "sales": 1600},
            {"month": "5月", "sales": 2000},
            {"month": "6月", "sales": 2200},
        ],
        "title": "月度销售额",
        "x_column": "month",
        "y_column": "sales",
        "user_id": "test_user"
    }

    result = await chart_tool.execute(test_data)

    if result["success"]:
        print(f"✅ 柱状图生成成功")
        print(f"   图表路径: {result['chart_path']}")
        print(f"   生成时间: {result['generation_time_ms']}ms")
        print(f"   数据点数: {result['metadata']['data_points']}")

        # 验证文件存在
        if os.path.exists(result['chart_path']):
            file_size = os.path.getsize(result['chart_path'])
            print(f"   文件大小: {file_size} bytes")
        else:
            print(f"❌ 文件不存在: {result['chart_path']}")
    else:
        print(f"❌ 图表生成失败: {result.get('error')}")

    return result


async def test_different_chart_types():
    """测试不同类型的图表"""
    print("\n" + "="*60)
    print("测试 2: 不同图表类型")
    print("="*60)

    chart_tool = ChartGenerationTool()

    test_cases = [
        {
            "name": "折线图",
            "data": {
                "chart_type": "line",
                "data": [
                    {"date": "Q1", "revenue": 500},
                    {"date": "Q2", "revenue": 650},
                    {"date": "Q3", "revenue": 720},
                    {"date": "Q4", "revenue": 890},
                ],
                "title": "季度营收趋势",
                "x_column": "date",
                "y_column": "revenue",
                "user_id": "test_user"
            }
        },
        {
            "name": "饼图",
            "data": {
                "chart_type": "pie",
                "data": [
                    {"product": "产品A", "share": 35},
                    {"product": "产品B", "share": 28},
                    {"product": "产品C", "share": 22},
                    {"product": "产品D", "share": 15},
                ],
                "title": "产品销售占比",
                "x_column": "product",
                "y_column": "share",
                "user_id": "test_user"
            }
        },
        {
            "name": "散点图",
            "data": {
                "chart_type": "scatter",
                "data": [
                    {"price": 100, "quantity": 50},
                    {"price": 150, "quantity": 45},
                    {"price": 200, "quantity": 38},
                    {"price": 250, "quantity": 30},
                    {"price": 300, "quantity": 25},
                ],
                "title": "价格-销量关系",
                "x_column": "price",
                "y_column": "quantity",
                "user_id": "test_user"
            }
        }
    ]

    results = []
    for test_case in test_cases:
        print(f"\n测试 {test_case['name']}...")
        result = await chart_tool.execute(test_case['data'])

        if result["success"]:
            print(f"   ✅ {test_case['name']}生成成功")
            print(f"   路径: {result['chart_path']}")
        else:
            print(f"   ❌ {test_case['name']}生成失败: {result.get('error')}")

        results.append(result)

    return results


async def test_data_analyzer():
    """测试数据分析和图表推荐"""
    print("\n" + "="*60)
    print("测试 3: 数据分析和图表推荐")
    print("="*60)

    analyzer_tool = ChartDataAnalyzerTool()

    test_cases = [
        {
            "name": "时间序列数据",
            "data": {
                "data": [
                    {"month": "1月", "sales": 1200},
                    {"month": "2月", "sales": 1500},
                    {"month": "3月", "sales": 1800},
                ],
                "intent": "显示月度销售趋势"
            },
            "expected": "line"
        },
        {
            "name": "占比数据",
            "data": {
                "data": [
                    {"category": "A", "value": 30},
                    {"category": "B", "value": 25},
                    {"category": "C", "value": 45},
                ],
                "intent": "展示各类别占比"
            },
            "expected": "pie"
        },
        {
            "name": "对比数据",
            "data": {
                "data": [
                    {"region": "华东", "sales": 500},
                    {"region": "华北", "sales": 450},
                    {"region": "华南", "sales": 380},
                ],
                "intent": "对比各区域销售额"
            },
            "expected": "bar"
        }
    ]

    for test_case in test_cases:
        print(f"\n测试 {test_case['name']}...")
        result = await analyzer_tool.execute(test_case['data'])

        if result["success"]:
            recommended = result['recommended_chart_type']
            expected = test_case['expected']

            print(f"   推荐图表类型: {recommended}")
            print(f"   X轴: {result.get('x_column')}")
            print(f"   Y轴: {result.get('y_column')}")
            print(f"   推荐理由: {result.get('reasoning')}")

            if recommended == expected:
                print(f"   ✅ 推荐正确（期望: {expected}）")
            else:
                print(f"   ⚠️  推荐不符预期（期望: {expected}，实际: {recommended}）")
        else:
            print(f"   ❌ 分析失败: {result.get('error')}")


async def test_etl_data_integration():
    """测试与 ETL 数据的集成"""
    print("\n" + "="*60)
    print("测试 4: 模拟 ETL 数据集成")
    print("="*60)

    # 模拟 ETL 返回的数据格式
    simulated_etl_result = {
        "success": True,
        "data": [
            {"product_name": "产品A", "total_sales": 1250000, "order_count": 523},
            {"product_name": "产品B", "total_sales": 980000, "order_count": 412},
            {"product_name": "产品C", "total_sales": 760000, "order_count": 335},
            {"product_name": "产品D", "total_sales": 540000, "order_count": 221},
        ],
        "columns": ["product_name", "total_sales", "order_count"],
        "row_count": 4
    }

    print("模拟 ETL 数据:")
    print(f"   行数: {simulated_etl_result['row_count']}")
    print(f"   列: {simulated_etl_result['columns']}")

    # Step 1: 分析数据
    analyzer_tool = ChartDataAnalyzerTool()
    analysis_result = await analyzer_tool.execute({
        "data": simulated_etl_result['data'],
        "intent": "展示各产品销售额对比",
        "columns": simulated_etl_result['columns']
    })

    if analysis_result["success"]:
        print(f"\n数据分析结果:")
        print(f"   推荐图表: {analysis_result['recommended_chart_type']}")
        print(f"   X轴: {analysis_result.get('x_column')}")
        print(f"   Y轴: {analysis_result.get('y_column')}")

    # Step 2: 基于分析结果生成图表
    chart_tool = ChartGenerationTool()
    chart_result = await chart_tool.execute({
        "chart_type": analysis_result['recommended_chart_type'],
        "data": simulated_etl_result['data'],
        "title": "产品销售额对比",
        "x_column": analysis_result.get('x_column'),
        "y_column": analysis_result.get('y_column'),
        "user_id": "test_user"
    })

    if chart_result["success"]:
        print(f"\n✅ ETL数据图表生成成功")
        print(f"   图表路径: {chart_result['chart_path']}")
        print(f"   生成时间: {chart_result['generation_time_ms']}ms")
    else:
        print(f"\n❌ 图表生成失败: {chart_result.get('error')}")

    return chart_result


async def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("测试 5: 错误处理")
    print("="*60)

    chart_tool = ChartGenerationTool()

    error_cases = [
        {
            "name": "空数据",
            "data": {
                "chart_type": "bar",
                "data": [],
                "title": "测试"
            }
        },
        {
            "name": "不支持的图表类型",
            "data": {
                "chart_type": "unknown_type",
                "data": [{"x": 1, "y": 2}],
                "title": "测试"
            }
        },
        {
            "name": "缺少data参数",
            "data": {
                "chart_type": "bar",
                "title": "测试"
            }
        }
    ]

    for test_case in error_cases:
        print(f"\n测试 {test_case['name']}...")
        result = await chart_tool.execute(test_case['data'])

        if not result["success"]:
            print(f"   ✅ 正确捕获错误: {result.get('error')}")
        else:
            print(f"   ❌ 应该失败但成功了")


async def main():
    """运行所有测试"""
    print("🚀 开始测试图表生成工具")
    print("="*60)

    try:
        # 测试 1: 基础图表生成
        await test_chart_generation_basic()

        # 测试 2: 不同图表类型
        await test_different_chart_types()

        # 测试 3: 数据分析
        await test_data_analyzer()

        # 测试 4: ETL 集成
        await test_etl_data_integration()

        # 测试 5: 错误处理
        await test_error_handling()

        print("\n" + "="*60)
        print("✅ 所有测试完成")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
