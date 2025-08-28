#!/usr/bin/env python3
"""
统一上下文系统集成验证脚本

验证新的统一上下文系统是否正确替换了原有的上下文管理，
确保系统特性的完整性和统一性
"""

import asyncio
import sys
import logging
from typing import Dict, Any
from datetime import datetime

# 设置基本日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """测试新模块的导入"""
    print("🔍 测试模块导入...")
    
    try:
        # 测试核心上下文系统导入
        from app.services.iaop.context import (
            UnifiedContextSystem,
            create_unified_context_system,
            IntelligentContextManager,
            ProgressiveOptimizationEngine,
            LearningEnhancedContextSystem
        )
        print("✅ 核心上下文系统模块导入成功")
        
        # 测试API适配器导入
        from app.services.iaop.integration.unified_api_adapter import (
            UnifiedAPIAdapter,
            get_unified_api_adapter
        )
        print("✅ API适配器模块导入成功")
        
        # 测试统一编排器导入
        from app.services.application.orchestration.unified_context_orchestrator import (
            UnifiedContextOrchestrator,
            get_unified_context_orchestrator
        )
        print("✅ 统一编排器模块导入成功")
        
        # 测试API端点更新
        from app.api.endpoints import system_insights
        print("✅ 系统洞察API端点导入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False

async def test_unified_context_system():
    """测试统一上下文系统的创建和基本功能"""
    print("\n🧪 测试统一上下文系统...")
    
    try:
        from app.services.iaop.context.unified_context_system import create_unified_context_system
        
        # 测试不同集成模式的系统创建
        integration_modes = ['basic', 'enhanced', 'intelligent', 'learning']
        
        for mode in integration_modes:
            print(f"  📊 测试 {mode} 模式...")
            
            system = create_unified_context_system(
                db_session=None,  # 使用None进行基本测试
                integration_mode=mode,
                enable_performance_monitoring=True
            )
            
            # 验证系统组件
            assert system.integration_mode.value == mode, f"集成模式不匹配: {mode}"
            assert system.context_manager is not None, "上下文管理器未初始化"
            
            # 验证组件配置
            if mode in ['enhanced', 'intelligent', 'learning']:
                assert system.optimization_engine is not None, f"{mode} 模式应包含优化引擎"
            
            if mode in ['intelligent', 'learning']:
                assert system.learning_system is not None, f"{mode} 模式应包含学习系统"
            
            print(f"  ✅ {mode} 模式系统创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 统一上下文系统测试失败: {e}")
        return False

async def test_api_adapter():
    """测试API适配器功能"""
    print("\n🔌 测试API适配器...")
    
    try:
        from app.services.iaop.integration.unified_api_adapter import UnifiedAPIAdapter
        
        # 创建适配器
        adapter = UnifiedAPIAdapter(
            db_session=None,
            integration_mode="intelligent"
        )
        
        # 验证适配器属性
        assert adapter.unified_system is not None, "统一系统未初始化"
        assert adapter.integration_mode == "intelligent", "集成模式不正确"
        
        # 测试系统洞察功能
        insights_result = await adapter.get_system_insights()
        
        # 验证响应结构
        assert 'success' in insights_result, "洞察结果应包含success字段"
        assert 'data' in insights_result, "洞察结果应包含data字段"
        
        print("✅ API适配器测试成功")
        return True
        
    except Exception as e:
        print(f"❌ API适配器测试失败: {e}")
        return False

async def test_orchestrator():
    """测试统一编排器功能"""
    print("\n🎭 测试统一编排器...")
    
    try:
        from app.services.application.orchestration.unified_context_orchestrator import UnifiedContextOrchestrator
        
        # 创建编排器
        orchestrator = UnifiedContextOrchestrator(
            db=None,
            user_id="test_user",
            integration_mode="intelligent",
            enable_caching=True
        )
        
        # 验证编排器属性
        assert orchestrator.unified_system is not None, "统一系统未初始化"
        assert orchestrator.api_adapter is not None, "API适配器未初始化"
        assert orchestrator.integration_mode == "intelligent", "集成模式不正确"
        
        # 测试洞察功能
        insights_result = await orchestrator.get_orchestration_insights()
        
        # 验证响应结构
        assert 'success' in insights_result, "洞察结果应包含success字段"
        assert 'data' in insights_result, "洞察结果应包含data字段"
        
        if insights_result['success']:
            data = insights_result['data']
            assert 'orchestrator_stats' in data, "应包含编排器统计信息"
            assert 'configuration' in data, "应包含配置信息"
        
        print("✅ 统一编排器测试成功")
        return True
        
    except Exception as e:
        print(f"❌ 统一编排器测试失败: {e}")
        return False

def test_cached_agent_orchestrator_v2():
    """测试升级后的CachedAgentOrchestrator"""
    print("\n🔄 测试升级后的CachedAgentOrchestrator...")
    
    try:
        from app.services.application.orchestration.cached_agent_orchestrator import CachedAgentOrchestrator
        
        # 创建V2版本的编排器
        orchestrator = CachedAgentOrchestrator(
            db=None,
            user_id="test_user", 
            use_unified_system=True,
            integration_mode="intelligent"
        )
        
        # 验证V2特性
        assert orchestrator.use_unified_system == True, "应使用统一系统"
        assert orchestrator.integration_mode == "intelligent", "集成模式不正确"
        assert hasattr(orchestrator, 'unified_orchestrator'), "应包含统一编排器"
        
        print("✅ CachedAgentOrchestrator V2测试成功")
        return True
        
    except Exception as e:
        print(f"❌ CachedAgentOrchestrator V2测试失败: {e}")
        return False

def test_api_endpoints_updates():
    """测试API端点更新"""
    print("\n🌐 测试API端点更新...")
    
    try:
        # 测试templates.py的更新
        from app.api.endpoints import templates
        
        # 检查analyze_with_agent端点是否有新参数
        import inspect
        sig = inspect.signature(templates.analyze_with_agent)
        params = list(sig.parameters.keys())
        
        assert 'optimization_level' in params, "analyze_with_agent应包含optimization_level参数"
        assert 'target_expectations' in params, "analyze_with_agent应包含target_expectations参数"
        
        # 测试chart_test.py的更新
        from app.api.endpoints import chart_test
        
        sig = inspect.signature(chart_test.test_placeholder_chart)
        params = list(sig.parameters.keys())
        
        assert 'optimization_level' in params, "test_placeholder_chart应包含optimization_level参数"
        assert 'target_expectation' in params, "test_placeholder_chart应包含target_expectation参数"
        
        # 测试system_insights端点
        from app.api.endpoints import system_insights
        assert hasattr(system_insights, 'router'), "system_insights应包含router"
        
        print("✅ API端点更新测试成功")
        return True
        
    except Exception as e:
        print(f"❌ API端点更新测试失败: {e}")
        return False

def test_system_configuration():
    """测试系统配置的完整性"""
    print("\n⚙️ 测试系统配置完整性...")
    
    try:
        from app.services.iaop.context.unified_context_system import SystemIntegrationMode
        from app.services.iaop.context.intelligent_context_manager import ContextIntelligenceLevel
        from app.services.iaop.context.progressive_optimization_engine import OptimizationStrategy
        from app.services.iaop.context.learning_enhanced_context import LearningMode
        
        # 验证枚举类型
        integration_modes = [mode.value for mode in SystemIntegrationMode]
        expected_modes = ['basic', 'enhanced', 'intelligent', 'learning']
        assert all(mode in integration_modes for mode in expected_modes), "系统集成模式不完整"
        
        intelligence_levels = [level.value for level in ContextIntelligenceLevel]
        expected_levels = ['basic', 'enhanced', 'adaptive', 'intelligent']
        assert all(level in intelligence_levels for level in expected_levels), "智能级别不完整"
        
        optimization_strategies = [strategy.value for strategy in OptimizationStrategy]
        expected_strategies = ['conservative', 'balanced', 'aggressive', 'adaptive']
        assert all(strategy in optimization_strategies for strategy in expected_strategies), "优化策略不完整"
        
        learning_modes = [mode.value for mode in LearningMode]
        expected_learning_modes = ['passive', 'active', 'reinforcement']
        assert all(mode in learning_modes for mode in expected_learning_modes), "学习模式不完整"
        
        print("✅ 系统配置完整性测试成功")
        return True
        
    except Exception as e:
        print(f"❌ 系统配置完整性测试失败: {e}")
        return False

async def run_all_tests():
    """运行所有验证测试"""
    print("🚀 开始统一上下文系统集成验证\n")
    print("=" * 60)
    
    tests = [
        ("模块导入测试", test_imports),
        ("统一上下文系统测试", test_unified_context_system),
        ("API适配器测试", test_api_adapter),  
        ("统一编排器测试", test_orchestrator),
        ("CachedAgentOrchestrator V2测试", test_cached_agent_orchestrator_v2),
        ("API端点更新测试", test_api_endpoints_updates),
        ("系统配置完整性测试", test_system_configuration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 执行: {test_name}")
        print("-" * 40)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 执行异常: {e}")
            results.append((test_name, False))
    
    # 生成测试报告
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n📈 总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！统一上下文系统集成成功")
        print("\n💡 系统特性:")
        print("  • 智能上下文管理和推理")
        print("  • 渐进式优化和自适应调整") 
        print("  • 学习驱动的持续改进")
        print("  • 统一的API接口和编排")
        print("  • 完整的性能监控和洞察")
        print("  • 向后兼容的平滑迁移")
        return True
    else:
        print(f"⚠️ {total - passed} 个测试失败，需要修复")
        return False

def main():
    """主函数"""
    print("统一上下文系统集成验证工具")
    print("验证新系统是否成功替换原有上下文管理")
    print(f"执行时间: {datetime.now().isoformat()}\n")
    
    try:
        # 运行异步测试
        success = asyncio.run(run_all_tests())
        
        if success:
            print("\n🎯 验证完成：系统集成成功！")
            print("💡 建议：现在可以启动应用服务器测试实际功能")
            sys.exit(0)
        else:
            print("\n⚠️ 验证完成：发现问题需要修复")
            print("🔧 建议：检查失败的测试项并修复相关问题")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 验证过程异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()