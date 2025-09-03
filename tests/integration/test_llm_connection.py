#!/usr/bin/env python3
"""
测试LLM连接和React Agent集成
"""

import requests
import json
import time
import asyncio
import sys
import os

# 添加后端路径
sys.path.append('/Users/shan/work/me/AutoReportAI/backend')

BACKEND_URL = "http://localhost:8000/api/v1"

def get_auth_token():
    """获取认证token"""
    login_data = {
        "username": "testuser",
        "password": "testpassword123"
    }
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            return result['data']['access_token']
    return None

def test_direct_llm_connection():
    """测试直接连接LLM服务"""
    print("\n🔌 测试直接LLM连接...")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/llm-monitor/test-connection",
            headers={"Content-Type": "application/json"},
            json={
                "model_name": "gpt-3.5-turbo",
                "api_key": "test-key",
                "base_url": "https://api.openai.com/v1"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ LLM直连成功: {content.strip()}")
            assert True, "LLM连接应该成功"
        else:
            print(f"❌ LLM连接失败: {response.status_code}")
            print(f"错误内容: {response.text[:200]}")
            assert False, f"LLM连接失败: {response.status_code}"
    except Exception as e:
        print(f"❌ LLM连接异常: {e}")
        assert False, f"LLM连接异常: {e}"

def test_react_agent_llm_integration():
    """测试React Agent与LLM的集成"""
    print("\n🤖 测试React Agent与LLM集成...")
    
    token = get_auth_token()
    if not token:
        print("❌ 无法获取认证token")
        assert False, "无法获取认证token"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 设置环境变量后测试
    os.environ['DATABASE_URL'] = "postgresql://postgres:postgres123@localhost:5432/autoreport"
    os.environ['REDIS_URL'] = "redis://localhost:6379/0"
    
    try:
        # 测试React Agent系统
        sys.path.append('/Users/shan/work/me/AutoReportAI/backend')
        
        from app.services.infrastructure.ai.agents import create_react_agent
        from app.db.session import SessionLocal
        
        # 创建React Agent
        agent = create_react_agent("21a164aa-2978-4f7f-8c9e-e5da6d2a9026")  # testuser的ID
        
        # 初始化agent
        asyncio.run(agent.initialize())
        
        # 测试简单对话
        response = asyncio.run(agent.chat("请用中文回答：你是什么AI助手？请简短回答。"))
        
        print(f"✅ React Agent响应: {response}")
        assert True, "React Agent测试应该成功"
        
    except Exception as e:
        print(f"❌ React Agent测试失败: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"React Agent测试失败: {e}"

def test_template_analysis_with_ai():
    """测试模板分析功能"""
    print("\n📝 测试模板分析功能...")
    
    token = get_auth_token()
    if not token:
        print("❌ 无法获取认证token")
        assert False, "无法获取认证token"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 首先创建一个数据源
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        data_source_data = {
            "name": f"测试数据源_{unique_suffix}",
            "source_type": "sql",
            "connection_string": "postgresql://test:test@localhost/test",
            "is_active": True,
            "description": "用于测试模板分析的数据源"
        }
        
        ds_response = requests.post(
            f"{BACKEND_URL}/data-sources/",
            headers=headers,
            json=data_source_data
        )
        
        if ds_response.status_code in [200, 201]:
            ds_result = ds_response.json()
            # Handle both wrapped and direct response formats
            if ds_result.get('success'):
                data_source_id = ds_result['data']['id']
                print(f"✅ 创建数据源成功: {data_source_id}")
            elif 'id' in ds_result:
                # Direct response format
                data_source_id = ds_result['id']
                print(f"✅ 创建数据源成功: {data_source_id}")
            else:
                print(f"❌ 创建数据源失败: {ds_result.get('message', '未知响应格式')}")
                assert False, "创建数据源失败"
        else:
            print(f"❌ 创建数据源请求失败: {ds_response.status_code}")
            assert False, f"创建数据源请求失败: {ds_response.status_code}"
        
        # 创建一个测试模板
        template_data = {
            "name": f"AI分析测试模板_{unique_suffix}",
            "description": "用于测试React Agent分析功能的模板",
            "content": "销售报告：{{sales_data}} 业绩分析：{{performance_metrics}}",
            "template_type": "report",
            "is_active": True
        }
        
        template_response = requests.post(
            f"{BACKEND_URL}/templates/",
            headers=headers,
            json=template_data
        )
        
        if template_response.status_code in [200, 201]:
            template_result = template_response.json()
            # Handle both wrapped and direct response formats  
            if template_result.get('success'):
                template_id = template_result['data']['id']
                print(f"✅ 创建模板成功: {template_id}")
            elif 'id' in template_result:
                # Direct response format
                template_id = template_result['id']
                print(f"✅ 创建模板成功: {template_id}")
            else:
                print(f"❌ 创建模板失败: {template_result.get('message', '未知响应格式')}")
                assert False, "创建模板失败"
                
            # 测试模板分析
            analyze_url = f"{BACKEND_URL}/templates/{template_id}/analyze"
            analyze_params = {
                "data_source_id": data_source_id,
                "force_reanalyze": True,
                "optimization_level": "enhanced"
            }
            
            analyze_response = requests.post(
                analyze_url,
                headers=headers,
                params=analyze_params
            )
            
            if analyze_response.status_code in [200, 201]:
                analyze_result = analyze_response.json()
                if analyze_result.get('success'):
                    print(f"✅ 模板分析成功: {analyze_result.get('message')}")
                    print(f"分析结果摘要: {str(analyze_result.get('data', {}))[:200]}...")
                    assert True, "模板分析应该成功"
                else:
                    print(f"❌ 模板分析失败: {analyze_result.get('message')}")
                    assert False, "模板分析失败"
            else:
                print(f"❌ 模板分析请求失败: {analyze_response.status_code}")
                print(f"错误: {analyze_response.text[:200]}")
                assert False, f"模板分析请求失败: {analyze_response.status_code}"
        else:
            print(f"❌ 创建模板请求失败: {template_response.status_code}")
            assert False, f"创建模板请求失败: {template_response.status_code}"
            
    except Exception as e:
        print(f"❌ 模板分析测试异常: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"模板分析测试异常: {e}"

def main():
    """主测试函数"""
    print("🚀 LLM连接和React Agent集成测试")
    print("=" * 50)
    
    results = {}
    
    # 1. 直接LLM连接测试
    results['direct_llm'] = test_direct_llm_connection()
    
    # 2. React Agent LLM集成测试
    results['react_agent'] = test_react_agent_llm_integration()
    
    # 3. 模板分析功能测试
    results['template_analysis'] = test_template_analysis_with_ai()
    
    # 结果汇总
    print("\n📊 测试结果汇总:")
    print(f"直接LLM连接: {'✅ 成功' if results['direct_llm'] else '❌ 失败'}")
    print(f"React Agent集成: {'✅ 成功' if results['react_agent'] else '❌ 失败'}")
    print(f"模板分析功能: {'✅ 成功' if results['template_analysis'] else '❌ 失败'}")
    
    success_count = sum(results.values())
    total_tests = len(results)
    
    print(f"\n🎯 测试通过率: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
    
    if success_count == total_tests:
        print("🎉 所有LLM和AI功能测试通过!")
        print("✨ React Agent已成功集成大模型")
        print("🌐 可以通过前端界面使用AI功能")
    else:
        print("⚠️  部分功能需要进一步调试")
    
    return success_count == total_tests

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)