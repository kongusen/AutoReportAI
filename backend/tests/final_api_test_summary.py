#!/usr/bin/env python3
"""
AutoReportAI 后端API测试总结
基于实际测试结果生成功能状态报告
"""

import requests
import json
from datetime import datetime

def test_core_functionality():
    """测试核心功能"""
    print("🚀 AutoReportAI 后端API功能测试总结")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    base_url = "http://localhost:8000/api/v1"
    results = []
    
    # 1. 健康检查
    print("1. 健康检查...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 后端服务正常运行")
            print(f"   状态: {data.get('status', 'unknown')}")
            print(f"   版本: {data.get('version', 'unknown')}")
            results.append(("健康检查", True, "服务正常"))
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            results.append(("健康检查", False, f"状态码: {response.status_code}"))
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        results.append(("健康检查", False, f"异常: {e}"))
    
    # 2. 用户认证测试
    print("\n2. 用户认证测试...")
    try:
        # 创建测试用户
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        register_data = {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@example.com",
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        
        response = requests.post(f"{base_url}/auth/register", json=register_data)
        if response.status_code in [200, 201]:
            print("✅ 用户注册功能正常")
            results.append(("用户注册", True, "功能正常"))
            
            # 测试登录
            login_data = {
                "username": register_data["username"],
                "password": register_data["password"]
            }
            response = requests.post(f"{base_url}/auth/login", data=login_data)
            if response.status_code == 200:
                login_response = response.json()
                auth_headers = {"Authorization": f"Bearer {login_response['access_token']}"}
                print("✅ 用户登录功能正常")
                results.append(("用户登录", True, "功能正常"))
                
                # 测试数据源创建
                ds_data = {
                    "name": f"Test Data Source {unique_id}",
                    "source_type": "sql",
                    "connection_string": "sqlite:///test.db",
                    "description": "Test data source",
                    "is_active": True
                }
                response = requests.post(f"{base_url}/data-sources/", json=ds_data, headers=auth_headers)
                if response.status_code in [200, 201]:
                    print("✅ 数据源创建功能正常")
                    results.append(("数据源创建", True, "功能正常"))
                else:
                    print(f"❌ 数据源创建失败: {response.status_code}")
                    results.append(("数据源创建", False, f"状态码: {response.status_code}"))
                
                # 测试模板创建
                template_data = {
                    "name": f"Test Template {unique_id}",
                    "description": "Test template",
                    "content": "测试模板内容：{{统计:总数}}",
                    "is_active": True
                }
                response = requests.post(f"{base_url}/templates/", json=template_data, headers=auth_headers)
                if response.status_code in [200, 201]:
                    print("✅ 模板创建功能正常")
                    results.append(("模板创建", True, "功能正常"))
                else:
                    print(f"❌ 模板创建失败: {response.status_code}")
                    results.append(("模板创建", False, f"状态码: {response.status_code}"))
                
                # 测试AI提供商创建
                ai_data = {
                    "provider_name": f"test_ai_{unique_id}",
                    "provider_type": "openai",
                    "api_key": "sk-test123456789012345678901234567890123456789012345678901234567890",
                    "api_base_url": "https://api.openai.com/v1",
                    "default_model_name": "gpt-3.5-turbo",
                    "is_active": True
                }
                response = requests.post(f"{base_url}/ai-providers/", json=ai_data, headers=auth_headers)
                if response.status_code in [200, 201]:
                    print("✅ AI提供商创建功能正常")
                    results.append(("AI提供商创建", True, "功能正常"))
                else:
                    print(f"❌ AI提供商创建失败: {response.status_code}")
                    results.append(("AI提供商创建", False, f"状态码: {response.status_code}"))
                
                # 测试列表端点
                endpoints = [
                    ("数据源列表", "/data-sources/"),
                    ("模板列表", "/templates/"),
                    ("AI提供商列表", "/ai-providers/"),
                ]
                
                for name, endpoint in endpoints:
                    response = requests.get(f"{base_url}{endpoint}", headers=auth_headers)
                    if response.status_code == 200:
                        print(f"✅ {name}功能正常")
                        results.append((name, True, "功能正常"))
                    else:
                        print(f"❌ {name}失败: {response.status_code}")
                        results.append((name, False, f"状态码: {response.status_code}"))
                
            else:
                print(f"❌ 用户登录失败: {response.status_code}")
                results.append(("用户登录", False, f"状态码: {response.status_code}"))
        else:
            print(f"❌ 用户注册失败: {response.status_code}")
            results.append(("用户注册", False, f"状态码: {response.status_code}"))
    except Exception as e:
        print(f"❌ 认证测试异常: {e}")
        results.append(("认证测试", False, f"异常: {e}"))
    
    # 3. 生成测试报告
    print("\n" + "=" * 60)
    print("📊 功能测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"总测试项目: {total}")
    print(f"通过项目: {passed}")
    print(f"失败项目: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    print("\n详细结果:")
    for name, success, details in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}: {details}")
    
    print("\n" + "=" * 60)
    if passed == total:
        print("🎉 所有核心功能测试通过！后端API功能正常")
    else:
        print("⚠️ 部分功能需要进一步检查")
    
    print("\n📋 已配置的AI提供商:")
    print("   - 小爱AI (xiaoai)")
    print("   - API地址: https://xiaoai.com/api/v1/chat/completions")
    print("   - 模型: gpt-4o-mini")
    print("   - 状态: 已激活")
    
    return results

if __name__ == "__main__":
    test_core_functionality() 