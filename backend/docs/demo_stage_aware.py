#!/usr/bin/env python3
"""
Stage-Aware Agent 演示脚本

展示基于TT递归的三阶段Agent架构的能力
"""

import asyncio
import logging
import sys
from typing import Dict, Any

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.append('/Users/shan/work/AutoReportAI/backend')

from app.services.infrastructure.agents import (
    StageAwareFacade,
    create_stage_aware_facade,
    ExecutionStage,
    TaskComplexity,
    AgentEvent
)


class MockContainer:
    """模拟服务容器"""
    
    def __init__(self):
        self.user_data_source_service = MockUserDataSourceService()
        self.llm_service = MockLLMService()


class MockUserDataSourceService:
    """模拟用户数据源服务"""
    
    async def get_user_data_source(self, user_id: str, data_source_id: str):
        return MockDataSource()


class MockDataSource:
    """模拟数据源"""
    
    def __init__(self):
        self.connection_config = {
            "host": "localhost",
            "port": 5432,
            "database": "demo_db",
            "username": "demo_user",
            "password": "demo_pass"
        }


class MockLLMService:
    """模拟LLM服务"""
    
    async def generate_response(self, prompt: str, **kwargs):
        return f"Mock response for: {prompt[:50]}..."


async def demo_sql_generation_stage():
    """演示SQL生成阶段"""
    logger.info("🎯 演示SQL生成阶段")
    
    # 创建Stage-Aware Facade
    container = MockContainer()
    facade = create_stage_aware_facade(container)
    
    # 模拟占位符
    placeholder = "统计各部门的销售额，按部门分组，显示部门名称、销售额和员工数量"
    
    logger.info(f"📝 占位符: {placeholder}")
    
    try:
        # 执行SQL生成阶段
        async for event in facade.execute_sql_generation_stage(
            placeholder=placeholder,
            data_source_id=1,
            user_id="demo_user",
            task_context={
                "business_domain": "销售管理",
                "data_scope": "全公司"
            }
        ):
            logger.info(f"📊 事件: {event.event_type}")
            if event.event_type == 'execution_completed':
                response = event.data.get('response')
                if response:
                    logger.info(f"✅ SQL生成完成")
                    logger.info(f"   质量评分: {response.quality_score:.2f}")
                    logger.info(f"   迭代次数: {response.iterations_used}")
                    logger.info(f"   执行时间: {response.execution_time_ms}ms")
                    logger.info(f"   结果: {response.result[:200]}...")
    
    except Exception as e:
        logger.error(f"❌ SQL生成阶段失败: {e}")


async def demo_chart_generation_stage():
    """演示图表生成阶段"""
    logger.info("🎯 演示图表生成阶段")
    
    # 创建Stage-Aware Facade
    container = MockContainer()
    facade = create_stage_aware_facade(container)
    
    # 模拟ETL数据
    etl_data = {
        "columns": ["department", "sales_amount", "employee_count"],
        "data": [
            {"department": "销售部", "sales_amount": 1500000, "employee_count": 25},
            {"department": "技术部", "sales_amount": 800000, "employee_count": 30},
            {"department": "市场部", "sales_amount": 600000, "employee_count": 15}
        ],
        "summary": {
            "total_sales": 2900000,
            "total_employees": 70,
            "avg_sales_per_employee": 41428
        }
    }
    
    chart_placeholder = "生成部门销售额对比图表"
    
    logger.info(f"📊 ETL数据: {len(etl_data['data'])} 条记录")
    logger.info(f"📝 图表需求: {chart_placeholder}")
    
    try:
        # 执行图表生成阶段
        async for event in facade.execute_chart_generation_stage(
            etl_data=etl_data,
            chart_placeholder=chart_placeholder,
            user_id="demo_user",
            data_source_id=1
        ):
            logger.info(f"📊 事件: {event.event_type}")
            if event.event_type == 'execution_completed':
                response = event.data.get('response')
                if response:
                    logger.info(f"✅ 图表生成完成")
                    logger.info(f"   质量评分: {response.quality_score:.2f}")
                    logger.info(f"   迭代次数: {response.iterations_used}")
                    logger.info(f"   结果: {response.result[:200]}...")
    
    except Exception as e:
        logger.error(f"❌ 图表生成阶段失败: {e}")


async def demo_document_generation_stage():
    """演示文档生成阶段"""
    logger.info("🎯 演示文档生成阶段")
    
    # 创建Stage-Aware Facade
    container = MockContainer()
    facade = create_stage_aware_facade(container)
    
    # 模拟段落上下文和占位符数据
    paragraph_context = "根据销售数据分析，各部门的业绩表现如下："
    placeholder_data = {
        "sales_data": {
            "销售部": {"sales": 1500000, "employees": 25, "avg_per_employee": 60000},
            "技术部": {"sales": 800000, "employees": 30, "avg_per_employee": 26667},
            "市场部": {"sales": 600000, "employees": 15, "avg_per_employee": 40000}
        },
        "insights": [
            "销售部业绩最佳，人均销售额最高",
            "技术部员工数量最多，但人均销售额较低",
            "市场部规模较小，但效率较高"
        ]
    }
    
    logger.info(f"📝 段落上下文: {paragraph_context}")
    logger.info(f"📊 占位符数据: {len(placeholder_data['sales_data'])} 个部门")
    
    try:
        # 执行文档生成阶段
        async for event in facade.execute_document_generation_stage(
            paragraph_context=paragraph_context,
            placeholder_data=placeholder_data,
            user_id="demo_user",
            data_source_id=1
        ):
            logger.info(f"📊 事件: {event.event_type}")
            if event.event_type == 'execution_completed':
                response = event.data.get('response')
                if response:
                    logger.info(f"✅ 文档生成完成")
                    logger.info(f"   质量评分: {response.quality_score:.2f}")
                    logger.info(f"   迭代次数: {response.iterations_used}")
                    logger.info(f"   结果: {response.result[:200]}...")
    
    except Exception as e:
        logger.error(f"❌ 文档生成阶段失败: {e}")


async def demo_full_pipeline():
    """演示完整的三阶段Pipeline"""
    logger.info("🚀 演示完整的三阶段Pipeline")
    
    # 创建Stage-Aware Facade
    container = MockContainer()
    facade = create_stage_aware_facade(container)
    
    # 模拟完整的业务场景
    placeholder = "分析公司各部门的销售业绩，生成可视化图表，并撰写分析报告"
    
    logger.info(f"📝 完整任务: {placeholder}")
    
    try:
        # 执行完整Pipeline
        stage_results = {}
        async for event in facade.execute_full_pipeline(
            placeholder=placeholder,
            data_source_id=1,
            user_id="demo_user",
            need_chart=True,
            chart_placeholder="生成部门业绩对比图表",
            paragraph_context="根据销售数据分析，各部门的业绩表现如下："
        ):
            logger.info(f"📊 Pipeline事件: {event.event_type}")
            
            # 收集各阶段结果
            if event.event_type == 'execution_completed':
                stage = event.data.get('current_stage', 'unknown')
                stage_results[stage] = event.data.get('response')
                logger.info(f"✅ 阶段 {stage} 完成")
        
        # 总结Pipeline结果
        logger.info("🎉 完整Pipeline执行完成")
        logger.info(f"   完成阶段: {list(stage_results.keys())}")
        for stage, result in stage_results.items():
            if result:
                logger.info(f"   {stage}: 质量={result.quality_score:.2f}, 迭代={result.iterations_used}")
    
    except Exception as e:
        logger.error(f"❌ 完整Pipeline失败: {e}")


async def demo_stage_configuration():
    """演示阶段配置功能"""
    logger.info("⚙️ 演示阶段配置功能")
    
    # 创建Stage-Aware Facade
    container = MockContainer()
    facade = create_stage_aware_facade(container)
    
    # 检查各阶段配置
    stages = [
        ExecutionStage.SQL_GENERATION,
        ExecutionStage.CHART_GENERATION,
        ExecutionStage.DOCUMENT_GENERATION
    ]
    
    for stage in stages:
        is_configured = facade.is_stage_configured(stage)
        stage_config = facade.get_stage_config(stage)
        
        logger.info(f"📋 阶段 {stage.value}:")
        logger.info(f"   已配置: {is_configured}")
        if stage_config:
            logger.info(f"   质量阈值: {stage_config.quality_threshold}")
            logger.info(f"   最大迭代: {stage_config.max_iterations}")
            logger.info(f"   启用工具: {len(stage_config.enabled_tools)} 个")
            logger.info(f"   阶段目标: {stage_config.stage_goal}")


async def main():
    """主演示函数"""
    logger.info("🎯 Stage-Aware Agent 演示开始")
    logger.info("=" * 60)
    
    try:
        # 1. 演示阶段配置
        await demo_stage_configuration()
        logger.info("=" * 60)
        
        # 2. 演示SQL生成阶段
        await demo_sql_generation_stage()
        logger.info("=" * 60)
        
        # 3. 演示图表生成阶段
        await demo_chart_generation_stage()
        logger.info("=" * 60)
        
        # 4. 演示文档生成阶段
        await demo_document_generation_stage()
        logger.info("=" * 60)
        
        # 5. 演示完整Pipeline
        await demo_full_pipeline()
        logger.info("=" * 60)
        
        logger.info("🎉 Stage-Aware Agent 演示完成")
        
    except Exception as e:
        logger.error(f"❌ 演示过程中发生错误: {e}", exc_info=True)


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
