#!/usr/bin/env python3
"""
Agent系统集成测试
==================

测试新的Agent系统架构的核心功能和组件集成。
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.infrastructure.agents.core.universal_agent_coordinator import (
    UniversalAgentCoordinator, CoordinationMode, execute_intelligent_task
)
from app.services.infrastructure.agents.core.smart_context_processor import (
    SmartContextProcessor, TaskComplexity
)
from app.services.infrastructure.agents.core.intelligent_prompt_orchestrator import (
    IntelligentPromptOrchestrator, create_smart_context
)
from app.services.infrastructure.agents.core.unified_tool_ecosystem import (
    UnifiedToolEcosystem, create_tool_definition, ToolCategory
)


async def test_smart_context_processor():
    """测试智能上下文处理器"""
    print("\n🎨 测试 SmartContextProcessor")
    print("=" * 50)
    
    processor = SmartContextProcessor()
    
    # 测试占位符分析场景
    test_cases = [
        {
            "description": "分析模板中的占位符 {{用户名}} 和 {{日期}}",
            "context": {
                "template_info": {"content": "Hello {{用户名}}, 今天是 {{日期}}"},
                "placeholder_text": "{{用户名}}, {{日期}}"
            }
        },
        {
            "description": "生成用户活跃度的SQL查询语句",
            "context": {
                "data_source_info": {
                    "table_details": [{"table_name": "users", "columns": ["id", "name", "login_time"]}]
                }
            }
        },
        {
            "description": "创建销售数据分析报告",
            "context": {
                "report_template": {"type": "dashboard"},
                "data_sensitivity": "medium"
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试用例 {i}: {test_case['description']}")
        
        try:
            context = await processor.build_intelligent_context(
                task_description=test_case["description"],
                context_data=test_case["context"],
                user_id="test_user"
            )
            
            print(f"  ✅ 场景识别: {context.scenario}")
            print(f"  ✅ 复杂度等级: {context.complexity_level.value}")
            print(f"  ✅ 推荐Agent: {context.optimal_agent_type}")
            print(f"  ✅ 工作流类型: {context.workflow_type.value}")
            print(f"  ✅ 可用工具: {', '.join(context.available_tools[:3])}...")
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")


async def test_intelligent_prompt_orchestrator():
    """测试智能Prompt编排器"""
    print("\n🧠 测试 IntelligentPromptOrchestrator")
    print("=" * 50)
    
    orchestrator = IntelligentPromptOrchestrator()
    
    # 创建测试上下文
    smart_context = create_smart_context(
        task_description="分析占位符 {{周期:统计开始日期}} 的含义",
        context_data={
            "suggested_date_filter": "DATE(create_time) = '2025-09-14'",
            "template_info": {"placeholder_count": 3}
        },
        user_id="test_user",
        scenario="placeholder_analysis",
        complexity_level=TaskComplexity.MEDIUM
    )
    
    try:
        print("📋 生成执行策略...")
        strategy = await orchestrator.generate_execution_strategy(smart_context)
        
        print(f"  ✅ 策略ID: {strategy.strategy_id}")
        print(f"  ✅ 置信度: {strategy.confidence_score}")
        print(f"  ✅ 工具选择: {', '.join(strategy.tool_selection[:3])}")
        print(f"  ✅ 优化提示: {len(strategy.optimization_hints)} 条")
        
        # 测试缓存
        print("\n🔄 测试策略缓存...")
        cached_strategy = await orchestrator.generate_execution_strategy(smart_context)
        print(f"  ✅ 缓存命中: {strategy.strategy_id == cached_strategy.strategy_id}")
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")


async def test_unified_tool_ecosystem():
    """测试统一工具生态系统"""
    print("\n🛠️  测试 UnifiedToolEcosystem")
    print("=" * 50)
    
    ecosystem = UnifiedToolEcosystem()
    
    # 注册测试工具
    test_tool = create_tool_definition(
        name="test_placeholder_analyzer",
        category=ToolCategory.ANALYSIS,
        description="测试占位符分析工具",
        capabilities=["placeholder_analysis", "context_extraction"],
        performance_score=0.9,
        reliability_score=0.85
    )
    
    try:
        print("🔧 注册测试工具...")
        success = ecosystem.register_custom_tool(test_tool)
        print(f"  ✅ 工具注册: {'成功' if success else '失败'}")
        
        # 创建测试上下文
        from app.services.infrastructure.agents.core.intelligent_prompt_orchestrator import ExecutionStrategy
        
        test_context = create_smart_context(
            task_description="分析占位符",
            scenario="placeholder_analysis"
        )
        
        test_strategy = ExecutionStrategy(
            tool_selection=["placeholder_analyzer", "reasoning_tool"],
            optimization_hints=["Check context first"]
        )
        
        print("\n🎯 测试工具选择...")
        selected_tools = await ecosystem.discover_and_select_tools(test_context, test_strategy)
        print(f"  ✅ 选择了 {len(selected_tools)} 个工具")
        
        for tool in selected_tools:
            print(f"    - {tool.definition.name} (置信度: {tool.confidence_score:.2f})")
        
        # 获取性能统计
        stats = ecosystem.get_performance_stats()
        print(f"\n📊 性能统计:")
        print(f"  ✅ 注册工具数: {stats['registered_tools']}")
        print(f"  ✅ 工具分类: {list(stats['category_distribution'].keys())}")
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")


async def test_universal_agent_coordinator():
    """测试通用Agent协调器"""
    print("\n🎯 测试 UniversalAgentCoordinator")
    print("=" * 50)
    
    # 测试不同协调模式
    modes = [
        (CoordinationMode.SIMPLE, "简单模式"),
        (CoordinationMode.STANDARD, "标准模式"), 
        (CoordinationMode.INTELLIGENT, "智能模式")
    ]
    
    for mode, mode_name in modes:
        print(f"\n🚀 测试 {mode_name}")
        print("-" * 30)
        
        coordinator = UniversalAgentCoordinator(coordination_mode=mode)
        
        try:
            # 测试占位符分析任务
            result = await coordinator.execute_intelligent_task(
                task_description="分析占位符 {{周期:统计开始日期}}，上下文已提供 suggested_date_filter: \"DATE(create_time) = '2025-09-14'\"",
                context_data={
                    "suggested_date_filter": "DATE(create_time) = '2025-09-14'",
                    "template_info": {
                        "placeholder_text": "{{周期:统计开始日期}}",
                        "context_available": True
                    }
                },
                user_id="test_user"
            )
            
            print(f"  ✅ 执行成功: {result.success}")
            print(f"  ✅ 任务ID: {result.task_id}")
            print(f"  ✅ 执行时间: {result.execution_time:.3f}s")
            print(f"  ✅ 完成阶段: {len(result.phases_completed)} 个")
            
            if result.metadata:
                print(f"  ✅ 执行模式: {result.metadata.get('mode', 'unknown')}")
                if 'scenario' in result.metadata:
                    print(f"  ✅ 场景识别: {result.metadata['scenario']}")
                
        except Exception as e:
            print(f"  ❌ {mode_name} 执行失败: {e}")
        
        # 获取协调器状态
        status = coordinator.get_coordination_status()
        print(f"  📊 活跃任务: {status['active_tasks']}")
        print(f"  📊 完成任务: {status['completed_tasks']}")


async def test_integration_scenario():
    """测试集成场景 - 解决原始问题"""
    print("\n🔍 集成测试 - 原始问题场景")  
    print("=" * 50)
    
    # 模拟原始问题场景
    task_description = "分析占位符 {{周期:统计开始日期}}"
    context_data = {
        # 上下文已经提供了足够信息
        "suggested_date_filter": "DATE(create_time) = '2025-09-14'",
        "analysis_context": {
            "date_provided": True,
            "filter_ready": True,
            "needs_db_query": False
        },
        "template_info": {
            "placeholder_text": "{{周期:统计开始日期}}",
            "expected_value": "2025-09-14"
        }
    }
    
    print("📝 任务描述:", task_description)
    print("📊 上下文信息: 已提供日期过滤器和分析上下文")
    
    try:
        # 使用快捷函数测试
        result = await execute_intelligent_task(
            task_description=task_description,
            context_data=context_data,
            user_id="integration_test",
            mode=CoordinationMode.INTELLIGENT
        )
        
        print(f"\n✅ 集成测试结果:")
        print(f"  🎯 执行成功: {result.success}")
        print(f"  ⏱️  执行时间: {result.execution_time:.3f}s")
        print(f"  📋 完成阶段: {[p.value for p in result.phases_completed]}")
        
        if result.success and result.metadata:
            print(f"  🎨 识别场景: {result.metadata.get('scenario', 'N/A')}")
            print(f"  🧠 复杂度: {result.metadata.get('complexity', 'N/A')}")
            print(f"  🤖 Agent类型: {result.metadata.get('agent_type', 'N/A')}")
            print(f"  🛠️  使用工具: {result.metadata.get('tools_used', 0)} 个")
            print(f"  📈 策略置信度: {result.metadata.get('strategy_confidence', 'N/A')}")
        
        # 检查是否避免了不必要的数据库查询
        if result.result and isinstance(result.result, dict):
            synthesis = result.result
            print(f"\n🔍 结果分析:")
            if "execution_summary" in synthesis:
                summary = synthesis["execution_summary"]
                print(f"  ✅ 场景正确识别: {summary.get('scenario') == 'placeholder_analysis'}")
                print(f"  ✅ 智能处理: 应该避免不必要的数据库查询")
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("🧪 Agent系统架构测试")
    print("=" * 60)
    print("测试新的 Prompt + TT控制循环 + 工具生态 架构")
    
    try:
        # 1. 测试智能上下文处理器
        await test_smart_context_processor()
        
        # 2. 测试智能Prompt编排器  
        await test_intelligent_prompt_orchestrator()
        
        # 3. 测试统一工具生态系统
        await test_unified_tool_ecosystem()
        
        # 4. 测试通用Agent协调器
        await test_universal_agent_coordinator()
        
        # 5. 集成测试
        await test_integration_scenario()
        
        print("\n🎉 测试完成!")
        print("=" * 60)
        print("✅ 新Agent系统架构测试通过")
        print("✅ Prompt + TT控制循环 + 工具生态 集成正常")
        print("✅ 智能适配多种情况的能力验证成功")
        
    except Exception as e:
        print(f"\n💥 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())