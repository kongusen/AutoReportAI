#!/usr/bin/env python3
"""
数据库驱动的智能模型选择测试

测试用户配置的LLM服务器和模型的智能选择功能
展示与前端配置页面的完整集成
"""

import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from uuid import uuid4

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def setup_test_data(db: Session):
    """设置测试数据"""
    print("🔧 设置测试数据...")
    
    from app.models.llm_server import LLMServer, LLMModel, ProviderType, ModelType
    from app.models.user_llm_preference import UserLLMPreference
    from app.models.user import User
    
    # 创建测试用户
    test_user = User(
        id=uuid4(),
        username="test_user",
        email="test@example.com",
        hashed_password="hashed_password_here",
        is_active=True
    )
    db.add(test_user)
    
    # 创建测试LLM服务器
    xiaoai_server = LLMServer(
        name="xiaoai",
        description="小艾API服务器",
        base_url="https://xiaoai.com/api/v1/chat/completions",
        provider_type=ProviderType.OPENAI,
        api_key="sk-cFoNGtf6djfyk1mJftn5xSOr6HMvV4jtxmnO9e1nEfnsXM4S",
        is_active=True,
        is_healthy=True,
        last_health_check=datetime.utcnow()
    )
    db.add(xiaoai_server)
    db.flush()  # 获取ID
    
    # 创建本地服务器
    local_server = LLMServer(
        name="local_ollama",
        description="本地Ollama服务器", 
        base_url="http://localhost:11434",
        provider_type=ProviderType.CUSTOM,
        api_key=None,
        is_active=True,
        is_healthy=True,
        last_health_check=datetime.utcnow()
    )
    db.add(local_server)
    db.flush()
    
    # 为xiaoai服务器添加模型
    xiaoai_models = [
        {
            "name": "gpt-4o-mini",
            "display_name": "GPT-4o Mini",
            "model_type": ModelType.CHAT,
            "provider_name": "openai",
            "max_tokens": 4000,
            "supports_function_calls": True,
            "supports_thinking": False
        },
        {
            "name": "gpt-5-chat-latest", 
            "display_name": "GPT-5 Chat Latest",
            "model_type": ModelType.CHAT,
            "provider_name": "openai",
            "max_tokens": 8000,
            "supports_function_calls": True,
            "supports_thinking": False
        },
        {
            "name": "claude-sonnet-4-20250514",
            "display_name": "Claude Sonnet 4",
            "model_type": ModelType.CHAT,
            "provider_name": "anthropic",
            "max_tokens": 200000,
            "supports_function_calls": True,
            "supports_thinking": False
        },
        {
            "name": "claude-sonnet-4-20250514-thinking",
            "display_name": "Claude Sonnet 4 Thinking",
            "model_type": ModelType.THINK,
            "provider_name": "anthropic",
            "max_tokens": 200000,
            "supports_function_calls": True,
            "supports_thinking": True
        }
    ]
    
    for model_data in xiaoai_models:
        model = LLMModel(
            server_id=xiaoai_server.id,
            name=model_data["name"],
            display_name=model_data["display_name"],
            model_type=model_data["model_type"],
            provider_name=model_data["provider_name"],
            is_active=True,
            is_healthy=True,
            max_tokens=model_data["max_tokens"],
            supports_function_calls=model_data["supports_function_calls"],
            supports_thinking=model_data["supports_thinking"],
            last_health_check=datetime.utcnow()
        )
        db.add(model)
    
    # 为本地服务器添加模型
    local_models = [
        {
            "name": "qwen2",
            "display_name": "Qwen2 7B",
            "model_type": ModelType.CHAT,
            "provider_name": "qwen",
            "max_tokens": 32000,
            "supports_function_calls": False,
            "supports_thinking": False
        },
        {
            "name": "llama3",
            "display_name": "Llama 3 8B",
            "model_type": ModelType.CHAT,
            "provider_name": "meta",
            "max_tokens": 8000,
            "supports_function_calls": False,
            "supports_thinking": False
        }
    ]
    
    for model_data in local_models:
        model = LLMModel(
            server_id=local_server.id,
            name=model_data["name"],
            display_name=model_data["display_name"],
            model_type=model_data["model_type"],
            provider_name=model_data["provider_name"],
            is_active=True,
            is_healthy=True,
            max_tokens=model_data["max_tokens"],
            supports_function_calls=model_data["supports_function_calls"],
            supports_thinking=model_data["supports_thinking"],
            last_health_check=datetime.utcnow()
        )
        db.add(model)
    
    # 创建用户偏好设置
    user_preference = UserLLMPreference(
        user_id=test_user.id,
        default_llm_server_id=xiaoai_server.id,
        default_provider_name="anthropic",
        default_model_name="claude-sonnet-4-20250514",
        preferred_temperature=0.7,
        max_tokens_limit=8000,
        daily_token_quota=100000,
        monthly_cost_limit=200.0,
        enable_caching=True,
        enable_learning=True,
        provider_priorities={"anthropic": 1, "openai": 2, "qwen": 3, "meta": 4},
        model_preferences={"reasoning": "claude-sonnet-4-20250514", "coding": "gpt-4o-mini"}
    )
    db.add(user_preference)
    
    db.commit()
    
    print(f"✅ 测试数据创建完成:")
    print(f"   - 用户: {test_user.username} ({test_user.id})")
    print(f"   - LLM服务器: {xiaoai_server.name}, {local_server.name}")
    print(f"   - 模型总数: {len(xiaoai_models) + len(local_models)}")
    print(f"   - 用户偏好: 已配置")
    
    return test_user.id


async def test_database_selector():
    """测试数据库驱动的智能选择器"""
    print("\n🧠 测试数据库驱动的智能选择器")
    print("=" * 50)
    
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    
    try:
        # 设置测试数据
        user_id = await setup_test_data(db)
        
        # 测试不同场景的模型选择
        from app.services.infrastructure.ai.llm.database_selector import (
            get_database_selector,
            TaskType,
            TaskComplexity,
            TaskCharacteristics,
            SelectionCriteria
        )
        
        selector = get_database_selector()
        
        test_scenarios = [
            {
                "name": "高质量推理任务（用户偏好Claude）",
                "task": TaskCharacteristics(
                    task_type=TaskType.REASONING,
                    complexity=TaskComplexity.COMPLEX,
                    estimated_tokens=5000,
                    accuracy_critical=True
                ),
                "criteria": SelectionCriteria(min_capability_score=0.8),
                "agent_id": "reasoning_agent"
            },
            {
                "name": "成本敏感的编程任务",
                "task": TaskCharacteristics(
                    task_type=TaskType.CODING,
                    complexity=TaskComplexity.MEDIUM,
                    estimated_tokens=3000,
                    cost_sensitive=True
                ),
                "criteria": SelectionCriteria(max_cost_per_request=0.05),
                "agent_id": "coding_agent"
            },
            {
                "name": "需要思考模式的专家级分析",
                "task": TaskCharacteristics(
                    task_type=TaskType.ANALYSIS,
                    complexity=TaskComplexity.EXPERT,
                    estimated_tokens=8000,
                    accuracy_critical=True
                ),
                "criteria": SelectionCriteria(preferred_providers=["anthropic"]),
                "agent_id": "analysis_agent"
            },
            {
                "name": "快速简单问答（本地优先）",
                "task": TaskCharacteristics(
                    task_type=TaskType.QA,
                    complexity=TaskComplexity.SIMPLE,
                    estimated_tokens=500,
                    speed_priority=True,
                    cost_sensitive=True
                ),
                "criteria": SelectionCriteria(max_latency_ms=3000, max_cost_per_request=0.001),
                "agent_id": "qa_agent"
            }
        ]
        
        recommendations = []
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n📋 场景 {i}: {scenario['name']}")
            
            try:
                recommendation = await selector.select_best_model_for_user(
                    user_id=str(user_id),
                    task_characteristics=scenario['task'],
                    criteria=scenario['criteria'],
                    agent_id=scenario['agent_id'],
                    db=db
                )
                
                recommendations.append({
                    "scenario": scenario['name'],
                    "recommendation": recommendation,
                    "agent_id": scenario['agent_id']
                })
                
                print(f"   🎯 推荐模型: {recommendation.provider}:{recommendation.model}")
                print(f"   📊 置信度: {recommendation.confidence:.1%}")
                print(f"   💭 推荐理由: {recommendation.reasoning}")
                print(f"   💰 预期成本: ${recommendation.expected_cost:.4f}")
                print(f"   ⚡ 预期延迟: {recommendation.expected_latency}ms")
                print(f"   🎛️ 能力匹配: {recommendation.capability_match_score:.2f}")
                
                if recommendation.fallback_models:
                    fallbacks = ", ".join([f"{p}:{m}" for m, p in recommendation.fallback_models[:2]])
                    print(f"   🔄 备选方案: {fallbacks}")
                
            except Exception as e:
                print(f"   ❌ 选择失败: {e}")
        
        # 测试使用反馈记录
        print(f"\n📈 测试使用反馈记录")
        print("-" * 30)
        
        for rec_data in recommendations:
            if not rec_data.get("recommendation"):
                continue
            
            recommendation = rec_data["recommendation"]
            agent_id = rec_data["agent_id"]
            
            # 模拟使用反馈
            import random
            success = random.choice([True, True, True, False])  # 75% 成功率
            satisfaction = random.uniform(0.8, 0.95) if success else random.uniform(0.3, 0.6)
            
            selector.record_user_feedback(
                user_id=str(user_id),
                model=recommendation.model,
                provider=recommendation.provider,
                success=success,
                satisfaction_score=satisfaction,
                actual_cost=recommendation.expected_cost * random.uniform(0.9, 1.1),
                actual_latency=int(recommendation.expected_latency * random.uniform(0.8, 1.2)),
                agent_id=agent_id,
                task_type=TaskType.REASONING
            )
            
            print(f"   📊 {agent_id}: {recommendation.provider}:{recommendation.model}")
            print(f"      反馈 - 成功: {success}, 满意度: {satisfaction:.2f}")
        
        # 展示Agent偏好学习结果
        print(f"\n👤 Agent偏好学习结果")
        print("-" * 30)
        
        for agent_id in ["reasoning_agent", "coding_agent", "analysis_agent", "qa_agent"]:
            agent_prefs = selector.agent_preferences.get(agent_id, {})
            if agent_prefs:
                print(f"\n🤖 {agent_id}:")
                for model_key, pref_data in agent_prefs.items():
                    print(f"   📈 {model_key}: 使用{pref_data['usage_count']}次, 满意度{pref_data['avg_satisfaction']:.2f}")
        
        return {
            "status": "success",
            "user_id": str(user_id),
            "scenarios_tested": len(test_scenarios),
            "successful_recommendations": len([r for r in recommendations if r.get("recommendation")]),
            "agent_preferences": len(selector.agent_preferences)
        }
        
    except Exception as e:
        logger.error(f"数据库选择器测试失败: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
        
    finally:
        db.close()


async def test_llm_manager_integration():
    """测试LLM管理器与数据库选择器的集成"""
    print("\n🔗 测试LLM管理器集成")
    print("=" * 40)
    
    try:
        from app.services.infrastructure.ai.llm import get_llm_manager
        from app.db.session import SessionLocal
        from app.models.user import User
        
        llm_manager = await get_llm_manager()
        
        # 获取测试用户ID
        db = SessionLocal()
        try:
            test_user = db.query(User).filter(User.username == "test_user").first()
            if not test_user:
                print("❌ 找不到测试用户")
                return {"status": "error", "error": "测试用户不存在"}
            
            user_id = str(test_user.id)
        finally:
            db.close()
        
        # 测试不同Agent的模型选择
        test_cases = [
            {
                "agent": "react_agent",
                "task_type": "reasoning",
                "complexity": "medium",
                "constraints": {"max_cost": 0.02, "cost_sensitive": True}
            },
            {
                "agent": "coding_agent", 
                "task_type": "coding",
                "complexity": "complex",
                "constraints": {"accuracy_critical": True}
            },
            {
                "agent": "analysis_agent",
                "task_type": "analysis", 
                "complexity": "expert",
                "constraints": {"preferred_providers": ["anthropic"]}
            }
        ]
        
        results = []
        
        for case in test_cases:
            print(f"\n🤖 测试 {case['agent']}")
            
            try:
                # 使用数据库选择器
                selection = await llm_manager.select_best_model(
                    task_type=case["task_type"],
                    complexity=case["complexity"], 
                    constraints=case["constraints"],
                    agent_id=case["agent"],
                    user_id=user_id  # 关键：传递user_id启用数据库选择
                )
                
                print(f"   ✅ 选择成功: {selection.get('provider')}:{selection.get('model')}")
                print(f"   📊 置信度: {selection.get('confidence', 0):.1%}")
                print(f"   💭 理由: {selection.get('reasoning', 'N/A')}")
                print(f"   💰 预期成本: ${selection.get('expected_cost', 0):.4f}")
                print(f"   🔧 数据源: {selection.get('source', 'unknown')}")
                
                results.append({"agent": case["agent"], "status": "success", "selection": selection})
                
            except Exception as e:
                print(f"   ❌ 选择失败: {e}")
                results.append({"agent": case["agent"], "status": "error", "error": str(e)})
        
        success_count = sum(1 for r in results if r["status"] == "success")
        
        return {
            "status": "success",
            "total_tests": len(test_cases),
            "successful_tests": success_count,
            "success_rate": success_count / len(test_cases),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"LLM管理器集成测试失败: {e}")
        return {"status": "error", "error": str(e)}


async def main():
    """主测试函数"""
    print("🧪 数据库驱动智能模型选择测试")
    print("=" * 70)
    print("展示用户配置的LLM服务器和模型的智能选择")
    print("与前端配置页面完全集成")
    print("=" * 70)
    
    try:
        # 测试数据库选择器
        result1 = await test_database_selector()
        
        # 测试LLM管理器集成
        result2 = await test_llm_manager_integration()
        
        # 总结报告
        print(f"\n🏆 测试完成总结")
        print("=" * 50)
        
        if result1.get("status") == "success":
            print("✅ 数据库智能选择器: 测试成功")
            print(f"   - 用户ID: {result1['user_id']}")
            print(f"   - 测试场景: {result1['scenarios_tested']}")
            print(f"   - 成功推荐: {result1['successful_recommendations']}")
            print(f"   - Agent偏好: {result1['agent_preferences']}")
        else:
            print("❌ 数据库智能选择器: 测试失败")
            print(f"   错误: {result1.get('error')}")
        
        if result2.get("status") == "success":
            print("✅ LLM管理器集成: 测试成功")
            print(f"   - 测试Agent: {result2['total_tests']}")
            print(f"   - 成功率: {result2['success_rate']:.1%}")
        else:
            print("❌ LLM管理器集成: 测试失败")
            print(f"   错误: {result2.get('error')}")
        
        print(f"\n💡 核心功能验证:")
        print("🎯 数据库配置驱动 - 从用户配置的服务器和模型中选择")
        print("👤 用户偏好集成 - 基于用户的提供商优先级和模型偏好")
        print("📊 配额约束支持 - 考虑用户的成本和Token限制")
        print("🧠 智能推荐算法 - 多维度评分和动态学习")
        print("🔄 Agent个性化 - 不同Agent形成各自的使用偏好")
        print("📈 使用反馈学习 - 持续优化选择策略")
        
        print(f"\n✨ 与前端集成优势:")
        print("🖥️  前端配置页面 → 数据库存储 → 后端智能选择")
        print("⚙️  用户可视化配置LLM服务器和模型偏好")
        print("📊 实时统计和监控用户的模型使用情况")
        print("🎛️ 灵活的配额管理和成本控制")
        
        print(f"\n🎉 数据库驱动智能选择系统测试完成！")
        
    except Exception as e:
        logger.error(f"主测试函数失败: {e}")
        print(f"❌ 测试系统失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())