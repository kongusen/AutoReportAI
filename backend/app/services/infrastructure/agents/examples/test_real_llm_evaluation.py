#!/usr/bin/env python3
"""
真实LLM评估功能测试脚本

测试使用真实LLM进行任务复杂度评估和模型选择
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from app.core.container import Container
from app.services.infrastructure.agents.tools.model_selection import (
    assess_task_complexity,
    select_optimal_model,
    assess_and_select_model
)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_llm_complexity_assessment():
    """测试LLM复杂度评估"""
    print("🔍 测试LLM复杂度评估")
    print("=" * 50)
    
    # 创建容器
    container = Container()
    
    # 测试用例
    test_cases = [
        {
            "name": "简单查询",
            "description": "查询用户表中所有用户的姓名和邮箱",
            "expected": "低复杂度"
        },
        {
            "name": "中等复杂度任务",
            "description": "统计过去30天每个产品的销售数量和金额，按产品类别分组，并计算同比增长率",
            "expected": "中等复杂度"
        },
        {
            "name": "复杂分析任务",
            "description": "分析用户行为模式，计算用户生命周期价值，预测流失概率，并生成个性化推荐策略，需要考虑多维度数据关联和机器学习算法",
            "expected": "高复杂度"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['name']}")
        print(f"任务描述: {test_case['description']}")
        print(f"预期复杂度: {test_case['expected']}")
        print("-" * 30)
        
        try:
            result = await assess_task_complexity(
                task_description=test_case['description'],
                context={"test_case": test_case['name']},
                container=container
            )
            
            print(f"✅ LLM评估结果:")
            print(f"   复杂度评分: {result.complexity_score:.2f}")
            print(f"   评估推理: {result.reasoning}")
            print(f"   影响因素: {', '.join(result.factors)}")
            print(f"   置信度: {result.confidence:.2f}")
            
            if result.dimension_scores:
                print(f"   维度评分: {result.dimension_scores}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")


async def test_llm_model_selection():
    """测试LLM模型选择"""
    print("\n🤖 测试LLM模型选择")
    print("=" * 50)
    
    # 创建容器
    container = Container()
    
    # 测试用例
    test_cases = [
        {
            "name": "低复杂度任务",
            "description": "查询用户基本信息",
            "complexity_score": 0.3
        },
        {
            "name": "高复杂度任务",
            "description": "多维度数据分析和机器学习预测",
            "complexity_score": 0.8
        }
    ]
    
    user_id = "test_user_123"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['name']}")
        print(f"任务描述: {test_case['description']}")
        print(f"复杂度评分: {test_case['complexity_score']:.2f}")
        print("-" * 30)
        
        try:
            result = await select_optimal_model(
                task_description=test_case['description'],
                complexity_score=test_case['complexity_score'],
                user_id=user_id,
                task_type="placeholder_analysis",
                container=container
            )
            
            print(f"✅ LLM选择结果:")
            print(f"   选择模型: {result.selected_model}")
            print(f"   模型类型: {result.model_type}")
            print(f"   选择推理: {result.reasoning}")
            print(f"   预期性能: {result.expected_performance}")
            if result.fallback_model:
                print(f"   备用模型: {result.fallback_model}")
            print(f"   置信度: {result.confidence:.2f}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")


async def test_integrated_assessment():
    """测试集成评估和选择"""
    print("\n🔄 测试集成评估和选择")
    print("=" * 50)
    
    # 创建容器
    container = Container()
    
    # 测试用例
    test_cases = [
        {
            "name": "数据分析任务",
            "description": "分析销售数据趋势，计算各产品类别的市场份额和增长率",
            "context": {"data_source": "sales", "time_range": "last_quarter"}
        },
        {
            "name": "复杂预测任务",
            "description": "基于历史数据预测未来6个月的销售趋势，考虑季节性因素和市场变化",
            "context": {"prediction_horizon": "6_months", "ml_required": True}
        }
    ]
    
    user_id = "test_user_456"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['name']}")
        print(f"任务描述: {test_case['description']}")
        print(f"上下文: {test_case['context']}")
        print("-" * 30)
        
        try:
            result = await assess_and_select_model(
                task_description=test_case['description'],
                user_id=user_id,
                context=test_case['context'],
                task_type="data_analysis",
                container=container
            )
            
            print(f"✅ 集成评估结果:")
            print(f"   复杂度评分: {result['complexity_assessment']['complexity_score']:.2f}")
            print(f"   复杂度推理: {result['complexity_assessment']['reasoning']}")
            print(f"   选择模型: {result['model_decision']['selected_model']}")
            print(f"   模型类型: {result['model_decision']['model_type']}")
            print(f"   选择推理: {result['model_decision']['reasoning']}")
            print(f"   最大上下文tokens: {result['max_context_tokens']}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")


async def test_error_handling():
    """测试错误处理"""
    print("\n🛡️ 测试错误处理")
    print("=" * 50)
    
    # 创建容器
    container = Container()
    
    # 测试无效输入
    test_cases = [
        {
            "name": "空任务描述",
            "description": "",
            "expected": "应该回退到规则评估"
        },
        {
            "name": "极长任务描述",
            "description": "这是一个非常长的任务描述..." * 100,
            "expected": "应该能处理长文本"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['name']}")
        print(f"预期行为: {test_case['expected']}")
        print("-" * 30)
        
        try:
            result = await assess_task_complexity(
                task_description=test_case['description'],
                container=container
            )
            
            print(f"✅ 错误处理结果:")
            print(f"   复杂度评分: {result.complexity_score:.2f}")
            print(f"   评估推理: {result.reasoning}")
            print(f"   置信度: {result.confidence:.2f}")
            
        except Exception as e:
            print(f"❌ 错误处理失败: {e}")


async def main():
    """主函数"""
    print("🚀 启动真实LLM评估功能测试")
    print("=" * 60)
    
    try:
        # 测试LLM复杂度评估
        await test_llm_complexity_assessment()
        
        # 测试LLM模型选择
        await test_llm_model_selection()
        
        # 测试集成评估
        await test_integrated_assessment()
        
        # 测试错误处理
        await test_error_handling()
        
        print("\n✅ 所有测试完成！")
        print("\n🎯 关键改进:")
        print("1. 🤖 使用真实LLM进行复杂度评估，替代硬编码规则")
        print("2. 🧠 LLM能够理解任务语义，提供更准确的评估")
        print("3. 🔄 智能模型选择，根据任务特点选择最合适的模型")
        print("4. 🛡️ 完善的错误处理和回退机制")
        print("5. 📊 详细的评估过程和推理说明")
        
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
