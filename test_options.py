#!/usr/bin/env python3
"""
测试OPTIONS预检请求处理
"""

import requests
import sys
import os

# 添加后端路径到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_options_request():
    """测试OPTIONS预检请求"""
    url = "http://192.168.61.30:8000/api/v1/auth/login"
    
    print("🧪 测试OPTIONS预检请求处理...")
    print(f"📡 目标URL: {url}")
    
    try:
        # 发送OPTIONS请求
        response = requests.options(url, timeout=5)
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"📋 响应头:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower():
                print(f"  {key}: {value}")
        
        if response.status_code == 200:
            print("🎉 OPTIONS请求处理成功！")
            return True
        else:
            print(f"❌ OPTIONS请求失败，状态码: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保后端服务正在运行")
        return False
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("测试CORS OPTIONS预检请求处理")
    print("=" * 50)
    
    result = test_options_request()
    
    print("=" * 50)
    if result:
        print("✅ 测试通过：OPTIONS预检请求能正常处理")
        print("🌍 跨域问题已解决")
    else:
        print("❌ 测试失败：需要启动后端服务进行实际测试")
        print("💡 建议：运行 uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("=" * 50)