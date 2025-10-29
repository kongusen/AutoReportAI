"""
三步骤Agent的TT递归使用示例

展示如何基于TT递归自动迭代特性，简化Agent调用
"""

import asyncio
from app.services.infrastructure.agents import (
    execute_sql_generation_tt,
    execute_chart_generation_tt, 
    execute_document_generation_tt,
    execute_tt_recursion
)


async def example_three_stage_agent():
    """
    三步骤Agent使用示例
    
    展示如何利用TT递归的自动迭代特性，简化Agent调用
    """
    
    # 模拟数据
    user_id = "user_123"
    data_source_id = 1
    
    print("🚀 三步骤Agent TT递归示例")
    print("=" * 50)
    
    # 第一阶段：SQL生成（placeholder中调用）
    print("\n📊 第一阶段：SQL生成")
    print("-" * 30)
    
    placeholder = "分析销售数据，生成月度销售报表的SQL查询"
    
    sql_result = await execute_sql_generation_tt(
        placeholder=placeholder,
        data_source_id=data_source_id,
        user_id=user_id,
        context={
            "template_id": "sales_report",
            "business_context": "月度销售分析"
        }
    )
    
    print(f"✅ SQL生成完成: {sql_result[:100]}...")
    
    # 第二阶段：图表生成（task中调用，基于ETL结果）
    print("\n📈 第二阶段：图表生成")
    print("-" * 30)
    
    # 模拟ETL处理后的数据
    etl_data = {
        "sales_data": [
            {"month": "2024-01", "sales": 100000},
            {"month": "2024-02", "sales": 120000},
            {"month": "2024-03", "sales": 110000}
        ],
        "summary": "销售数据已处理完成"
    }
    
    chart_placeholder = "基于销售数据生成月度趋势图表"
    
    chart_result = await execute_chart_generation_tt(
        chart_placeholder=chart_placeholder,
        etl_data=etl_data,
        user_id=user_id,
        context={
            "chart_type": "line_chart",
            "data_format": "monthly_trend"
        }
    )
    
    print(f"✅ 图表生成完成: {chart_result[:100]}...")
    
    # 第三阶段：文档生成（基于图表数据回填模板）
    print("\n📝 第三阶段：文档生成")
    print("-" * 30)
    
    paragraph_context = "根据销售数据分析结果，生成月度销售报告的描述性内容"
    
    placeholder_data = {
        "sql_result": sql_result,
        "chart_result": chart_result,
        "etl_data": etl_data,
        "analysis_insights": "销售呈现上升趋势"
    }
    
    document_result = await execute_document_generation_tt(
        paragraph_context=paragraph_context,
        placeholder_data=placeholder_data,
        user_id=user_id,
        context={
            "document_type": "monthly_report",
            "tone": "professional"
        }
    )
    
    print(f"✅ 文档生成完成: {document_result[:100]}...")
    
    print("\n🎉 三步骤Agent执行完成！")
    print("=" * 50)
    
    return {
        "sql_result": sql_result,
        "chart_result": chart_result,
        "document_result": document_result
    }


async def example_unified_tt_recursion():
    """
    统一TT递归接口使用示例
    
    展示如何使用统一的execute_tt_recursion接口
    """
    
    print("\n🔄 统一TT递归接口示例")
    print("=" * 50)
    
    user_id = "user_456"
    data_source_id = 2
    
    # 使用统一接口执行不同阶段
    stages = [
        ("sql_generation", "分析用户行为数据"),
        ("chart_generation", "生成用户行为趋势图"),
        ("completion", "生成用户行为分析报告")
    ]
    
    results = {}
    
    for stage, question in stages:
        print(f"\n🎯 执行{stage}阶段: {question}")
        print("-" * 40)
        
        response = await execute_tt_recursion(
            question=question,
            data_source_id=data_source_id,
            user_id=user_id,
            stage=stage,
            complexity="medium",
            context={
                "stage": stage,
                "previous_results": results
            }
        )
        
        if response.success:
            print(f"✅ {stage}阶段完成")
            print(f"   迭代次数: {response.iterations}")
            print(f"   执行时间: {response.execution_time:.2f}s")
            print(f"   结果: {response.result[:100]}...")
            results[stage] = response.result
        else:
            print(f"❌ {stage}阶段失败: {response.error}")
    
    return results


async def example_simplified_agent_calls():
    """
    简化Agent调用示例
    
    展示如何消除不必要的中间层，直接使用TT递归
    """
    
    print("\n⚡ 简化Agent调用示例")
    print("=" * 50)
    
    # 传统方式（复杂）
    print("\n❌ 传统方式（复杂）:")
    print("""
    # 需要手动管理Facade、初始化、事件循环等
    container = Container()
    agent_facade = create_stage_aware_facade(container=container, enable_context_retriever=True)
    await agent_facade.initialize(user_id=user_id, task_type="task", task_complexity=complexity)
    
    result = None
    async for event in agent_facade.execute_sql_generation_stage(...):
        if event.event_type == 'execution_completed':
            result = event.data
            break
    """)
    
    # TT递归方式（简化）
    print("\n✅ TT递归方式（简化）:")
    print("""
    # 只需要一行调用，TT递归自动迭代到满意结果
    result = await execute_sql_generation_tt(
        placeholder="分析销售数据",
        data_source_id=1,
        user_id="user_123"
    )
    """)
    
    # 实际演示
    print("\n🚀 实际演示:")
    
    result = await execute_sql_generation_tt(
        placeholder="分析销售数据，生成月度销售报表",
        data_source_id=1,
        user_id="user_123"
    )
    
    print(f"✅ 结果: {result[:100]}...")
    
    print("\n💡 关键优势:")
    print("   - 代码量减少80%")
    print("   - 无需手动管理迭代过程")
    print("   - 自动达到质量阈值")
    print("   - 统一的错误处理")


if __name__ == "__main__":
    async def main():
        # 运行示例
        await example_three_stage_agent()
        await example_unified_tt_recursion()
        await example_simplified_agent_calls()
    
    # 运行示例
    asyncio.run(main())
