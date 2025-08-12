#!/usr/bin/env python3
"""
测试 Doris 数据库连接
"""
import requests
import json
from requests.auth import HTTPBasicAuth

# Doris 连接配置
DORIS_FE_HOST = "192.168.61.30"
DORIS_QUERY_PORT = 9030
DORIS_HTTP_PORT = 8030
DORIS_USERNAME = "root"
DORIS_PASSWORD = "yjg@123456"

def test_doris_connection():
    print("开始测试 Doris 连接...")
    
    # 测试 1: 通过 HTTP API 查询
    print("\n1. 测试 HTTP API 连接 (端口 8030):")
    try:
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/query/default"
        headers = {
            'Content-Type': 'application/json'
        }
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        data = {
            "sql": "SELECT 1 as test_column"
        }
        
        response = requests.post(url, 
                               headers=headers, 
                               auth=auth, 
                               json=data, 
                               timeout=10)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("✅ HTTP API 连接成功!")
        else:
            print(f"❌ HTTP API 连接失败: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ HTTP API 连接异常: {e}")
    
    # 测试 2: 检查 FE 状态
    print("\n2. 测试 FE 状态查询:")
    try:
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/show_proc?path=/"
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        
        response = requests.get(url, auth=auth, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}...")
        
        if response.status_code == 200:
            print("✅ FE 状态查询成功!")
        else:
            print(f"❌ FE 状态查询失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ FE 状态查询异常: {e}")
    
    # 测试 3: 尝试其他 API 端点
    print("\n3. 测试其他 API 端点:")
    endpoints = [
        f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/rest/v1/query",
        f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/query",
        f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/_query",
    ]
    
    for endpoint in endpoints:
        try:
            auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
            headers = {'Content-Type': 'application/json'}
            data = {"sql": "SELECT 1"}
            
            response = requests.post(endpoint, 
                                   headers=headers, 
                                   auth=auth, 
                                   json=data, 
                                   timeout=5)
            
            print(f"端点: {endpoint}")
            print(f"  状态码: {response.status_code}")
            if response.status_code != 404:
                print(f"  响应: {response.text[:200]}...")
            
        except Exception as e:
            print(f"  异常: {e}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    test_doris_connection()