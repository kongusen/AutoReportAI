#!/usr/bin/env python3
"""
AI Integration Test Script
用于测试AI提供商集成功能
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.ai_provider import AIProvider
from app.services.ai_integration.ai_service_enhanced import EnhancedAIService
from app.core.security_utils import decrypt_data

def test_ai_provider_connection(provider_name: str):
    """测试AI提供商连接"""
    print(f"🧪 测试 {provider_name} 连接...")
    
    db = SessionLocal()
    try:
        # 获取提供商
        provider = db.query(AIProvider).filter(
            AIProvider.provider_name == provider_name
        ).first()
        
        if not provider:
            print(f"❌ 找不到提供商: {provider_name}")
            return False
        
        # 检查API密钥
        if provider.api_key:
            try:
                decrypted_key = decrypt_data(provider.api_key)
                print(f"✅ API密钥解密成功")
            except Exception as e:
                print(f"❌ API密钥解密失败: {e}")
                return False
        else:
            print(f"⚠️  提供商没有API密钥")
        
        # 创建AI服务实例
        try:
            ai_service = EnhancedAIService(db)
            print(f"✅ AI服务初始化成功")
        except Exception as e:
            print(f"❌ AI服务初始化失败: {e}")
            return False
        
        # 测试健康检查
        try:
            health = asyncio.run(ai_service.health_check())
            print(f"✅ 健康检查通过: {health.get('status', 'unknown')}")
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return False
        
        # 测试简单对话
        try:
            from app.services.ai_integration.ai_service_enhanced import AIRequest
            
            request = AIRequest(
                model=provider.default_model_name or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello, this is a test message."}],
                max_tokens=50,
                temperature=0.7
            )
            
            response = asyncio.run(ai_service.chat_completion(request))
            print(f"✅ 对话测试成功")
            print(f"   响应: {response.content[:100]}...")
            print(f"   模型: {response.model}")
            print(f"   响应时间: {response.response_time:.2f}s")
            
        except Exception as e:
            print(f"❌ 对话测试失败: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False
    finally:
        db.close()

def test_ai_features():
    """测试AI功能"""
    print("🧪 测试AI功能...")
    
    db = SessionLocal()
    try:
        ai_service = EnhancedAIService(db)
        
        # 测试自然语言查询解释
        print("📝 测试自然语言查询解释...")
        try:
            result = asyncio.run(ai_service.interpret_natural_language_query(
                query="显示销售额最高的前10个产品",
                context={"table": "sales_data"},
                available_columns=["product_name", "sales_amount", "date"]
            ))
            print(f"✅ 查询解释成功: {result.get('sql_query', 'N/A')}")
        except Exception as e:
            print(f"❌ 查询解释失败: {e}")
        
        # 测试洞察生成
        print("💡 测试洞察生成...")
        try:
            data_summary = {
                "total_records": 1000,
                "columns": ["sales", "profit", "region"],
                "summary_stats": {
                    "sales": {"mean": 5000, "max": 15000},
                    "profit": {"mean": 1000, "max": 3000}
                }
            }
            
            insights = asyncio.run(ai_service.generate_insights(
                data_summary=data_summary,
                context="销售数据分析"
            ))
            print(f"✅ 洞察生成成功: {insights[:100]}...")
        except Exception as e:
            print(f"❌ 洞察生成失败: {e}")
        
        # 测试图表配置生成
        print("📊 测试图表配置生成...")
        try:
            sample_data = [
                {"region": "North", "sales": 5000},
                {"region": "South", "sales": 6000},
                {"region": "East", "sales": 4000},
                {"region": "West", "sales": 7000}
            ]
            
            chart_config = asyncio.run(ai_service.generate_chart_config(
                data=sample_data,
                description="按地区显示销售额分布"
            ))
            print(f"✅ 图表配置生成成功: {chart_config.get('type', 'N/A')}")
        except Exception as e:
            print(f"❌ 图表配置生成失败: {e}")
        
    except Exception as e:
        print(f"❌ AI功能测试失败: {e}")
    finally:
        db.close()

def test_ai_metrics():
    """测试AI指标"""
    print("📊 测试AI指标...")
    
    db = SessionLocal()
    try:
        ai_service = EnhancedAIService(db)
        metrics = ai_service.get_service_metrics()
        
        print("📈 AI服务指标:")
        print(f"   总请求数: {metrics.get('total_requests', 0)}")
        print(f"   成功请求数: {metrics.get('successful_requests', 0)}")
        print(f"   错误数: {metrics.get('error_count', 0)}")
        print(f"   错误率: {metrics.get('error_rate', 0):.2%}")
        print(f"   总token数: {metrics.get('total_tokens', 0)}")
        print(f"   总成本: ${metrics.get('total_cost', 0):.4f}")
        print(f"   平均响应时间: {metrics.get('average_response_time', 0):.2f}s")
        
        model_usage = metrics.get('model_usage', {})
        if model_usage:
            print("   模型使用情况:")
            for model, stats in model_usage.items():
                print(f"     {model}: {stats.get('requests', 0)} 请求, {stats.get('tokens', 0)} tokens")
        
    except Exception as e:
        print(f"❌ AI指标测试失败: {e}")
    finally:
        db.close()

def list_available_providers():
    """列出可用的AI提供商"""
    print("📋 可用的AI提供商:")
    
    db = SessionLocal()
    try:
        providers = db.query(AIProvider).all()
        
        if not providers:
            print("   没有找到AI提供商")
            return []
        
        provider_names = []
        for provider in providers:
            status = "🟢 激活" if provider.is_active else "🔴 未激活"
            print(f"   {provider.provider_name} ({provider.provider_type.value}) - {status}")
            provider_names.append(provider.provider_name)
        
        return provider_names
        
    except Exception as e:
        print(f"❌ 获取提供商列表失败: {e}")
        return []
    finally:
        db.close()

def main():
    """主函数"""
    print("🤖 AutoReportAI AI集成测试")
    print("=" * 50)
    
    # 列出可用提供商
    providers = list_available_providers()
    
    if not providers:
        print("❌ 没有可用的AI提供商，请先运行初始化脚本")
        return
    
    print("\n" + "=" * 50)
    
    # 测试每个提供商
    for provider_name in providers:
        print(f"\n🔧 测试提供商: {provider_name}")
        print("-" * 30)
        
        success = test_ai_provider_connection(provider_name)
        
        if success:
            print(f"✅ {provider_name} 测试通过")
        else:
            print(f"❌ {provider_name} 测试失败")
        
        print()
    
    # 测试AI功能
    print("🔧 测试AI功能")
    print("-" * 30)
    test_ai_features()
    
    # 测试AI指标
    print("\n🔧 测试AI指标")
    print("-" * 30)
    test_ai_metrics()
    
    print("\n🎉 AI集成测试完成!")

if __name__ == "__main__":
    main() 