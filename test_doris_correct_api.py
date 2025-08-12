#!/usr/bin/env python3
"""
测试正确的 Doris API 使用方式
"""
import requests
import json
from requests.auth import HTTPBasicAuth

# Doris 连接配置
DORIS_FE_HOST = "192.168.61.30"
DORIS_HTTP_PORT = 8030
DORIS_USERNAME = "root"
DORIS_PASSWORD = "yjg@123456"
DORIS_DATABASE = "default"

def test_correct_doris_api():
    print("测试正确的 Doris API...")
    
    # 方法1: 使用 Stream Load URL 格式但用于查询
    print("\n1. 测试通过 HTTP 参数传递 SQL:")
    try:
        # Doris 支持通过 HTTP 参数传递 SQL
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/{DORIS_DATABASE}/_query"
        
        params = {
            'sql': 'SELECT 1 as test_column'
        }
        
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        
        response = requests.get(url, params=params, auth=auth, timeout=10)
        
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("✅ HTTP 参数查询成功!")
        else:
            print(f"❌ HTTP 参数查询失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ HTTP 参数查询异常: {e}")
    
    # 方法2: 使用正确的查询端点
    print("\n2. 测试查询端点:")
    endpoints_to_try = [
        f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/query",
        f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/{DORIS_DATABASE}/query",
        f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/v1/query",
    ]
    
    for endpoint in endpoints_to_try:
        try:
            auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
            params = {'sql': 'SELECT 1 as test'}
            
            # 尝试 GET 方法
            response = requests.get(endpoint, params=params, auth=auth, timeout=5)
            print(f"GET {endpoint}: {response.status_code}")
            if response.status_code == 200:
                print(f"  响应: {response.text[:200]}...")
                
        except Exception as e:
            print(f"  异常: {e}")
    
    # 方法3: 尝试使用 MySQL 协议（如果 Doris 支持的话）
    print("\n3. 测试 MySQL 协议兼容性:")
    try:
        # 某些 Doris 版本支持 MySQL 协议端口
        mysql_endpoints = [
            f"http://{DORIS_FE_HOST}:9030/",
            f"http://{DORIS_FE_HOST}:9030/query",
        ]
        
        for endpoint in mysql_endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                print(f"{endpoint}: {response.status_code}")
                if response.status_code == 200:
                    print(f"  内容: {response.text[:100]}...")
            except Exception as e:
                print(f"  {endpoint} 异常: {e}")
                
    except Exception as e:
        print(f"MySQL 协议测试异常: {e}")
    
    # 方法4: 检查可用的 API 端点
    print("\n4. 发现可用的 API 端点:")
    try:
        # 基于之前成功的 show_proc API，尝试其他管理端点
        base_url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api"
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        
        # 尝试发现 API
        discovery_endpoints = [
            f"{base_url}/",
            f"{base_url}/help",
            f"{base_url}/version", 
            f"{base_url}/show_proc?path=/dbs",
        ]
        
        for endpoint in discovery_endpoints:
            try:
                response = requests.get(endpoint, auth=auth, timeout=5)
                print(f"{endpoint}: {response.status_code}")
                if response.status_code == 200:
                    content = response.text
                    if len(content) < 500:
                        print(f"  内容: {content}")
                    else:
                        print(f"  内容长度: {len(content)} 字符")
                        
            except Exception as e:
                print(f"  异常: {e}")
                
    except Exception as e:
        print(f"API 发现异常: {e}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    test_correct_doris_api()