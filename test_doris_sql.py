#!/usr/bin/env python3
"""
测试实际的 Doris SQL 查询 API
"""
import requests
import json
from requests.auth import HTTPBasicAuth

# Doris 连接配置
DORIS_FE_HOST = "192.168.61.30"
DORIS_HTTP_PORT = 8030
DORIS_USERNAME = "root"
DORIS_PASSWORD = "yjg@123456"

def test_doris_sql_execution():
    print("测试 Doris SQL 执行...")
    
    # 从之前的结果看到有数据库: yjg
    # 让我们尝试使用正确的 SQL 执行端点
    
    print("\n1. 使用 _sql 端点:")
    try:
        # 尝试使用 _sql 端点，这是很多数据库的标准端点
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/yjg/_sql"
        
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # 使用表单数据格式
        data = {
            'sql': 'SELECT 1 as test_column'
        }
        
        response = requests.post(url, data=data, auth=auth, headers=headers, timeout=10)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容: {response.text}")
        
    except Exception as e:
        print(f"异常: {e}")
    
    print("\n2. 使用 query 端点 POST:")
    try:
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/yjg/query"
        
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'sql': 'SELECT 1 as test_column'
        }
        
        response = requests.post(url, data=data, auth=auth, headers=headers, timeout=10)
        
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}...")
        
    except Exception as e:
        print(f"异常: {e}")
    
    print("\n3. 测试其他数据库的查询端点:")
    databases = ["information_schema", "yjg", "__internal_schema"]
    
    for db in databases:
        try:
            url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/{db}/_sql"
            auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
            
            data = {'sql': 'SELECT 1 as test'}
            
            response = requests.post(url, data=data, auth=auth, timeout=5)
            print(f"数据库 {db}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"  JSON 响应: {result}")
                except:
                    print(f"  文本响应: {response.text[:200]}...")
            
        except Exception as e:
            print(f"  异常: {e}")
    
    print("\n4. 检查表列表:")
    try:
        # 查询 yjg 数据库中的表
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/show_proc"
        params = {'path': '/dbs/10116'}  # yjg 数据库的 ID 是 10116
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        
        response = requests.get(url, params=params, auth=auth, timeout=10)
        print(f"yjg 数据库详情: {response.status_code}")
        if response.status_code == 200:
            print(f"内容: {response.text}")
            
    except Exception as e:
        print(f"异常: {e}")

if __name__ == "__main__":
    test_doris_sql_execution()