#!/usr/bin/env python3
"""
Loom Agent 系统演示脚本

展示基于 Loom 0.0.3 的新 Agent 架构的使用方法
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.core.container import Container
from app.services.infrastructure.agents import (
    create_agent_system,
    create_high_performance_system,
    create_lightweight_system,
    quick_analyze,
    quick_generate_sql,
    ExecutionStage,
    TaskComplexity,
    AgentConfig
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_basic_usage():
    """演示基础使用方法"""
    logger.info("🚀 开始基础使用演示")
    
    # 创建容器
    container = Container()
    
    # 创建 Agent 系统
    agent_system = create_agent_system(container)
    
    # 示例占位符
    placeholder = """
    分析最近30天的用户注册趋势
    需要按天统计注册用户数量
    并计算环比增长率
    """
    
    try:
        # 分析占位符
        logger.info("📝 分析占位符...")
        response = await agent_system.analyze_placeholder_sync(
            placeholder=placeholder,
            data_source_id=1,  # 假设的数据源ID
            user_id="demo_user"
        )
        
        logger.info("✅ 分析完成")
        logger.info(f"   成功: {response.success}")
        logger.info(f"   执行时间: {response.execution_time_ms}ms")
        logger.info(f"   迭代次数: {response.iterations_used}")
        logger.info(f"   质量评分: {response.quality_score:.2f}")
        logger.info(f"   结果预览: {str(response.result)[:200]}...")
        
    except Exception as e:
        logger.error(f"❌ 分析失败: {e}")


async def demo_sql_generation():
    """演示 SQL 生成功能"""
    logger.info("🔧 开始 SQL 生成演示")
    
    # 创建容器
    container = Container()
    
    # 创建 Agent 系统
    agent_system = create_agent_system(container)
    
    # 业务需求
    business_requirement = """
    查询2024年每个月的销售总额
    按月份排序显示
    只包含状态为'已完成'的订单
    """
    
    try:
        # 生成 SQL
        logger.info("📝 生成 SQL 查询...")
        sql = await agent_system.generate_sql(
            business_requirement=business_requirement,
            data_source_id=1,
            user_id="demo_user"
        )
        
        logger.info("✅ SQL 生成完成")
        logger.info(f"生成的 SQL:\n{sql}")
        
    except Exception as e:
        logger.error(f"❌ SQL 生成失败: {e}")


async def demo_data_analysis():
    """演示数据分析功能"""
    logger.info("📊 开始数据分析演示")
    
    # 创建容器
    container = Container()
    
    # 创建 Agent 系统
    agent_system = create_agent_system(container)
    
    # SQL 查询
    sql_query = """
    SELECT 
        DATE_FORMAT(created_at, '%Y-%m') as month,
        COUNT(*) as user_count
    FROM users 
    WHERE created_at >= '2024-01-01'
    GROUP BY DATE_FORMAT(created_at, '%Y-%m')
    ORDER BY month
    """
    
    try:
        # 分析数据
        logger.info("📝 分析数据...")
        analysis_result = await agent_system.analyze_data(
            sql_query=sql_query,
            data_source_id=1,
            user_id="demo_user",
            analysis_type="trend"
        )
        
        logger.info("✅ 数据分析完成")
        logger.info(f"分析结果: {analysis_result}")
        
    except Exception as e:
        logger.error(f"❌ 数据分析失败: {e}")


async def demo_chart_generation():
    """演示图表生成功能"""
    logger.info("📈 开始图表生成演示")
    
    # 创建容器
    container = Container()
    
    # 创建 Agent 系统
    agent_system = create_agent_system(container)
    
    # 数据摘要
    data_summary = """
    用户注册趋势数据：
    - 2024-01: 1200 用户
    - 2024-02: 1350 用户
    - 2024-03: 1180 用户
    - 2024-04: 1420 用户
    - 2024-05: 1580 用户
    """
    
    # 图表需求
    chart_requirements = """
    需要生成一个折线图显示用户注册趋势
    要求：
    - X轴显示月份
    - Y轴显示用户数量
    - 使用蓝色线条
    - 添加数据标签
    """
    
    try:
        # 生成图表配置
        logger.info("📝 生成图表配置...")
        chart_config = await agent_system.generate_chart(
            data_summary=data_summary,
            chart_requirements=chart_requirements,
            data_source_id=1,
            user_id="demo_user"
        )
        
        logger.info("✅ 图表配置生成完成")
        logger.info(f"图表配置: {chart_config}")
        
    except Exception as e:
        logger.error(f"❌ 图表生成失败: {e}")


async def demo_schema_discovery():
    """演示 Schema 发现功能"""
    logger.info("🔍 开始 Schema 发现演示")
    
    # 创建容器
    container = Container()
    
    # 创建 Agent 系统
    agent_system = create_agent_system(container)
    
    try:
        # 获取 Schema 信息
        logger.info("📝 获取 Schema 信息...")
        schema_info = await agent_system.get_schema_info(
            data_source_id=1,
            user_id="demo_user"
        )
        
        logger.info("✅ Schema 信息获取完成")
        logger.info(f"数据源ID: {schema_info.get('data_source_id')}")
        logger.info(f"表数量: {schema_info.get('total_tables', 0)}")
        
        if schema_info.get('tables'):
            logger.info("发现的表:")
            for table in schema_info['tables'][:5]:  # 只显示前5个表
                logger.info(f"  - {table.get('name', 'Unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Schema 发现失败: {e}")


async def demo_streaming_analysis():
    """演示流式分析功能"""
    logger.info("🌊 开始流式分析演示")
    
    # 创建容器
    container = Container()
    
    # 创建 Agent 系统
    agent_system = create_agent_system(container)
    
    # 复杂占位符
    placeholder = """
    分析用户行为数据：
    1. 计算每日活跃用户数
    2. 分析用户留存率
    3. 识别用户流失模式
    4. 提供改进建议
    """
    
    try:
        # 流式分析
        logger.info("📝 开始流式分析...")
        
        async for event in agent_system.analyze_placeholder(
            placeholder=placeholder,
            data_source_id=1,
            user_id="demo_user",
            complexity=TaskComplexity.COMPLEX
        ):
            logger.info(f"📡 事件: {event.event_type} - {event.stage.value}")
            
            if event.event_type == "execution_completed":
                response = event.data.get("response")
                if response:
                    logger.info(f"✅ 分析完成: {response.success}")
                    logger.info(f"   执行时间: {response.execution_time_ms}ms")
                    logger.info(f"   质量评分: {response.quality_score:.2f}")
                break
            elif event.event_type == "execution_failed":
                error = event.data.get("error", "Unknown error")
                logger.error(f"❌ 分析失败: {error}")
                break
        
    except Exception as e:
        logger.error(f"❌ 流式分析失败: {e}")


async def demo_quick_functions():
    """演示便捷函数"""
    logger.info("⚡ 开始便捷函数演示")
    
    # 创建容器
    container = Container()
    
    # 示例占位符
    placeholder = "查询最近7天的订单统计"
    
    try:
        # 使用便捷函数快速分析
        logger.info("📝 使用便捷函数快速分析...")
        response = await quick_analyze(
            placeholder=placeholder,
            data_source_id=1,
            user_id="demo_user",
            container=container
        )
        
        logger.info("✅ 快速分析完成")
        logger.info(f"   成功: {response.success}")
        logger.info(f"   结果: {str(response.result)[:100]}...")
        
        # 使用便捷函数快速生成 SQL
        logger.info("📝 使用便捷函数快速生成 SQL...")
        sql = await quick_generate_sql(
            business_requirement="查询用户总数",
            data_source_id=1,
            user_id="demo_user",
            container=container
        )
        
        logger.info("✅ 快速 SQL 生成完成")
        logger.info(f"生成的 SQL: {sql}")
        
    except Exception as e:
        logger.error(f"❌ 便捷函数演示失败: {e}")


async def demo_different_configs():
    """演示不同配置的使用"""
    logger.info("⚙️ 开始不同配置演示")
    
    # 创建容器
    container = Container()
    
    # 高性能配置
    logger.info("📝 创建高性能系统...")
    high_perf_system = create_high_performance_system(container)
    metrics = high_perf_system.get_metrics()
    logger.info(f"高性能系统指标: {metrics}")
    
    # 轻量级配置
    logger.info("📝 创建轻量级系统...")
    lightweight_system = create_lightweight_system(container)
    config = lightweight_system.get_config()
    logger.info(f"轻量级系统配置: max_iterations={config.max_iterations}")
    
    # 调试配置
    logger.info("📝 创建调试系统...")
    debug_system = create_debug_system(container)
    debug_config = debug_system.get_config()
    logger.info(f"调试系统配置: max_iterations={debug_config.max_iterations}")


async def main():
    """主函数"""
    logger.info("🎯 Loom Agent 系统演示开始")
    logger.info("=" * 60)
    
    try:
        # 基础使用演示
        await demo_basic_usage()
        logger.info("=" * 60)
        
        # SQL 生成演示
        await demo_sql_generation()
        logger.info("=" * 60)
        
        # 数据分析演示
        await demo_data_analysis()
        logger.info("=" * 60)
        
        # 图表生成演示
        await demo_chart_generation()
        logger.info("=" * 60)
        
        # Schema 发现演示
        await demo_schema_discovery()
        logger.info("=" * 60)
        
        # 流式分析演示
        await demo_streaming_analysis()
        logger.info("=" * 60)
        
        # 便捷函数演示
        await demo_quick_functions()
        logger.info("=" * 60)
        
        # 不同配置演示
        await demo_different_configs()
        logger.info("=" * 60)
        
        logger.info("🎉 所有演示完成！")
        
    except Exception as e:
        logger.error(f"❌ 演示过程中发生错误: {e}", exc_info=True)


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
