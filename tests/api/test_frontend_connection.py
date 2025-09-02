#!/usr/bin/env python3
"""
前后端连调测试脚本
测试新的React Agent功能
"""

import requests
import json
import time

# 配置
BACKEND_URL = "http://localhost:8000/api/v1"
FRONTEND_URL = "http://localhost:3000"

def test_backend_apis():
    """测试后端API"""
    print("🔧 测试后端API...")
    
    # 1. 健康检查
    try:
        response = requests.get(f"{BACKEND_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 后端健康检查: {data['data']['status']}")
        else:
            print(f"❌ 后端健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 后端连接失败: {e}")
        return False
    
    # 2. 用户登录
    try:
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
            login_result = response.json()
            if login_result.get('success'):
                token = login_result['data']['access_token']
                print("✅ 用户登录成功")
                
                # 3. 测试React Agent API
                headers = {"Authorization": f"Bearer {token}"}
                
                # 系统健康检查
                health_response = requests.get(
                    f"{BACKEND_URL}/system-insights/context-system/health",
                    headers=headers
                )
                
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    if health_data.get('success'):
                        print(f"✅ React Agent健康状态: {health_data['data']['overall_status']}")
                    else:
                        print("❌ React Agent健康检查返回失败")
                else:
                    print(f"❌ React Agent健康检查请求失败: {health_response.status_code}")
                
                # 优化设置
                settings_response = requests.get(
                    f"{BACKEND_URL}/system-insights/context-system/optimization-settings",
                    headers=headers
                )
                
                if settings_response.status_code == 200:
                    settings_data = settings_response.json()
                    if settings_data.get('success'):
                        modes = settings_data['data'].get('integration_modes', [])
                        print(f"✅ 获取优化设置成功，可用模式数: {len(modes)}")
                    else:
                        print("❌ 优化设置返回失败")
                else:
                    print(f"❌ 优化设置请求失败: {settings_response.status_code}")
                    
                return True
            else:
                print(f"❌ 登录失败: {login_result.get('message')}")
        else:
            print(f"❌ 登录请求失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 登录测试失败: {e}")
    
    return False

def test_frontend_access():
    """测试前端访问"""
    print("\n🌐 测试前端访问...")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            if "AutoReportAI" in response.text:
                print("✅ 前端服务正常")
                return True
            else:
                print("❌ 前端内容异常")
        else:
            print(f"❌ 前端访问失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 前端连接失败: {e}")
    
    return False

def main():
    """主测试函数"""
    print("🚀 AutoReportAI 前后端连调测试")
    print("=" * 50)
    
    # 测试后端
    backend_ok = test_backend_apis()
    
    # 测试前端
    frontend_ok = test_frontend_access()
    
    print("\n📊 测试结果:")
    print(f"后端状态: {'✅ 正常' if backend_ok else '❌ 异常'}")
    print(f"前端状态: {'✅ 正常' if frontend_ok else '❌ 异常'}")
    
    if backend_ok and frontend_ok:
        print("\n🎉 前后端连调测试通过！")
        print("✨ React Agent功能已集成")
        print(f"🌐 前端地址: {FRONTEND_URL}")
        print(f"🔗 后端API: {BACKEND_URL}")
        print(f"📋 API文档: http://localhost:8000/docs")
        print(f"🔍 系统洞察: {FRONTEND_URL}/system-insights")
        return True
    else:
        print("\n❌ 连调测试失败，请检查服务状态")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)