#!/usr/bin/env python3
"""
LLM自主判断任务复杂度和模型选择演示

展示如何让LLM自主判断任务难度并选择合适的模型
"""

import asyncio
import logging
from typing import Dict, Any

from app.services.infrastructure.agents.tools.model_selection import (
    assess_task_complexity,
    select_optimal_model,
    assess_and_select_model
)
from app.core.container import Container

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_llm_self_selection():
    """演示LLM自主判断和模型选择"""
    
    print("🤖 LLM自主判断任务复杂度和模型选择演示")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {
            "name": "简单查询任务",
            "description": "查询用户表中所有用户的姓名和邮箱",
            "expected_complexity": "低"
        },
        {
            "name": "中等复杂度任务", 
            "description": "统计过去30天每个产品的销售数量和金额，按产品类别分组",
            "expected_complexity": "中"
        },
        {
            "name": "复杂分析任务",
            "description": "分析用户行为模式，计算用户生命周期价值，预测流失概率，并生成个性化推荐策略",
            "expected_complexity": "高"
        }
    ]
    
    user_id = "demo_user_123"
    container = Container()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['name']}")
        print(f"任务描述: {test_case['description']}")
        print(f"预期复杂度: {test_case['expected_complexity']}")
        print("-" * 40)
        
        try:
            # 1. 评估任务复杂度
            print("🔍 步骤1: LLM评估任务复杂度...")
            complexity_result = await assess_task_complexity(
                task_description=test_case['description'],
                context={"task_type": "placeholder_analysis"},
                container=container
            )
            
            print(f"   复杂度评分: {complexity_result.complexity_score:.2f}")
            print(f"   评估推理: {complexity_result.reasoning}")
            print(f"   影响因素: {', '.join(complexity_result.factors)}")
            print(f"   置信度: {complexity_result.confidence:.2f}")
            
            # 2. 选择最优模型
            print("\n🤖 步骤2: LLM选择最优模型...")
            model_decision = await select_optimal_model(
                task_description=test_case['description'],
                complexity_score=complexity_result.complexity_score,
                user_id=user_id,
                task_type="placeholder_analysis",
                container=container
            )
            
            print(f"   选择模型: {model_decision.selected_model}")
            print(f"   模型类型: {model_decision.model_type}")
            print(f"   选择推理: {model_decision.reasoning}")
            print(f"   预期性能: {model_decision.expected_performance}")
            if model_decision.fallback_model:
                print(f"   备用模型: {model_decision.fallback_model}")
            
            # 3. 综合分析
            print("\n📊 步骤3: 综合分析结果...")
            full_result = await assess_and_select_model(
                task_description=test_case['description'],
                user_id=user_id,
                context={"task_type": "placeholder_analysis"},
                task_type="placeholder_analysis",
                container=container
            )
            
            print(f"   最大上下文tokens: {full_result['max_context_tokens']}")
            print(f"   自动模型选择: {full_result['user_config']['auto_model_selection']}")
            print(f"   思考模型阈值: {full_result['user_config']['think_model_threshold']}")
            
        except Exception as e:
            print(f"❌ 测试用例 {i} 执行失败: {e}")
        
        print("\n" + "=" * 60)


async def demo_dynamic_model_switching():
    """演示动态模型切换"""
    
    print("\n🔄 动态模型切换演示")
    print("=" * 60)
    
    # 模拟一个复杂的任务流程
    task_flow = [
        {
            "step": 1,
            "description": "分析用户注册数据",
            "context": {"data_source": "user_registration", "time_range": "last_30_days"}
        },
        {
            "step": 2, 
            "description": "计算用户留存率和流失率",
            "context": {"analysis_type": "retention", "cohort_analysis": True}
        },
        {
            "step": 3,
            "description": "预测用户未来6个月的消费行为",
            "context": {"prediction_horizon": "6_months", "ml_model": "required"}
        }
    ]
    
    user_id = "demo_user_456"
    container = Container()
    
    for task in task_flow:
        print(f"\n📋 任务步骤 {task['step']}: {task['description']}")
        print(f"上下文: {task['context']}")
        print("-" * 40)
        
        try:
            result = await assess_and_select_model(
                task_description=task['description'],
                user_id=user_id,
                context=task['context'],
                task_type="data_analysis",
                container=container
            )
            
            print(f"🤖 LLM判断结果:")
            print(f"   复杂度: {result['complexity_assessment']['complexity_score']:.2f}")
            print(f"   选择模型: {result['model_decision']['selected_model']}")
            print(f"   模型类型: {result['model_decision']['model_type']}")
            print(f"   推理过程: {result['model_decision']['reasoning']}")
            
            # 模拟模型切换
            if result['model_decision']['model_type'] == 'think':
                print("   ✅ 使用思考模型处理复杂任务")
            else:
                print("   ✅ 使用默认模型处理常规任务")
                
        except Exception as e:
            print(f"❌ 任务步骤 {task['step']} 执行失败: {e}")


async def demo_user_preference_impact():
    """演示用户偏好对模型选择的影响"""
    
    print("\n👤 用户偏好影响演示")
    print("=" * 60)
    
    # 同一个任务，不同用户偏好
    task_description = "分析销售数据，计算各产品类别的销售趋势和市场份额"
    
    user_preferences = [
        {
            "user_id": "user_prefers_speed",
            "preference": "速度优先",
            "think_threshold": 0.9,  # 更高的阈值，更少使用思考模型
            "auto_selection": True
        },
        {
            "user_id": "user_prefers_quality", 
            "preference": "质量优先",
            "think_threshold": 0.5,  # 更低的阈值，更多使用思考模型
            "auto_selection": True
        },
        {
            "user_id": "user_disabled_auto",
            "preference": "禁用自动选择",
            "think_threshold": 0.7,
            "auto_selection": False
        }
    ]
    
    container = Container()
    
    for user_pref in user_preferences:
        print(f"\n👤 用户: {user_pref['user_id']} ({user_pref['preference']})")
        print(f"思考模型阈值: {user_pref['think_threshold']}")
        print(f"自动选择: {user_pref['auto_selection']}")
        print("-" * 40)
        
        try:
            result = await assess_and_select_model(
                task_description=task_description,
                user_id=user_pref['user_id'],
                context={"user_preference": user_pref['preference']},
                task_type="data_analysis",
                container=container
            )
            
            print(f"🤖 模型选择结果:")
            print(f"   复杂度评分: {result['complexity_assessment']['complexity_score']:.2f}")
            print(f"   选择模型: {result['model_decision']['selected_model']}")
            print(f"   模型类型: {result['model_decision']['model_type']}")
            print(f"   选择推理: {result['model_decision']['reasoning']}")
            
        except Exception as e:
            print(f"❌ 用户 {user_pref['user_id']} 测试失败: {e}")


async def main():
    """主函数"""
    print("🚀 启动LLM自主判断和模型选择演示")
    
    try:
        # 基础功能演示
        await demo_llm_self_selection()
        
        # 动态切换演示
        await demo_dynamic_model_switching()
        
        # 用户偏好影响演示
        await demo_user_preference_impact()
        
        print("\n✅ 所有演示完成！")
        print("\n🎯 关键优势:")
        print("1. 🤖 LLM自主判断任务复杂度，比硬编码规则更准确")
        print("2. 🔄 根据任务需求动态选择思考模型或默认模型")
        print("3. 👤 尊重用户偏好设置，支持个性化配置")
        print("4. 🛡️ 提供回退机制，确保系统稳定性")
        print("5. 📊 详细的推理过程，便于调试和优化")
        
    except Exception as e:
        print(f"❌ 演示执行失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
