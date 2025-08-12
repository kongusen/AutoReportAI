#!/usr/bin/env python3
"""
基于 Doris 官方文档的正确 API 使用方式测试
"""
import requests
import json
from requests.auth import HTTPBasicAuth

# Doris 连接配置
DORIS_FE_HOST = "192.168.61.30"
DORIS_HTTP_PORT = 8030
DORIS_USERNAME = "root"
DORIS_PASSWORD = "yjg@123456"

def test_documented_api():
    print("基于官方文档测试 Doris API...")
    
    # 方法 1: Stream Load 风格的查询（标准 Doris 查询方式）
    print("\n1. 测试 Stream Load 风格查询:")
    try:
        # 使用 Doris 标准的查询格式
        # 格式: PUT /api/{db}/_query
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/yjg/_query"
        
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        headers = {
            'Content-Type': 'text/plain',
            'sql': 'SELECT count(*) FROM ods_travel LIMIT 1'
        }
        
        # 使用 PUT 方法，这是 Doris 的标准方式
        response = requests.put(url, headers=headers, auth=auth, timeout=10)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容: {response.text}")
        
    except Exception as e:
        print(f"异常: {e}")
    
    # 方法 2: 通过 Header 传递 SQL 的 GET 方式
    print("\n2. 测试通过 Header 传递 SQL:")
    try:
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/yjg/_query"
        
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        headers = {
            'sql': 'SELECT 1 as test_column'
        }
        
        response = requests.get(url, headers=headers, auth=auth, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text[:300]}...")
        
    except Exception as e:
        print(f"异常: {e}")
    
    # 方法 3: 尝试正确的 JSON API 格式
    print("\n3. 测试 JSON API (如果支持的话):")
    try:
        # 有些版本支持这种格式
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/yjg"
        
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        headers = {
            'Content-Type': 'application/json',
            'sql': 'SELECT 1 as test'
        }
        
        data = {
            'sql': 'SELECT count(*) FROM ods_travel LIMIT 1'
        }
        
        response = requests.post(url, json=data, headers=headers, auth=auth, timeout=10)
        print(f"POST JSON 状态码: {response.status_code}")
        if response.status_code != 405:
            print(f"响应内容: {response.text}")
        
    except Exception as e:
        print(f"异常: {e}")
    
    # 方法 4: 使用 MySQL 协议测试（如果可能的话）
    print("\n4. 测试简单表访问:")
    try:
        # 尝试使用管理 API 获取数据样本
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/show_proc"
        params = {'path': '/dbs/10116/10126/partitions'}  # ods_travel 表的分区
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        
        response = requests.get(url, params=params, auth=auth, timeout=10)
        print(f"表分区查询: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"分区信息: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
        
    except Exception as e:
        print(f"异常: {e}")

if __name__ == "__main__":
    test_documented_api()