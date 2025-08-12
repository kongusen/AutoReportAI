#!/usr/bin/env python3
"""
最终测试 - 找到正确的 Doris SQL 执行方法
"""
import requests
import json
from requests.auth import HTTPBasicAuth
import urllib.parse

# Doris 连接配置
DORIS_FE_HOST = "192.168.61.30"
DORIS_HTTP_PORT = 8030
DORIS_USERNAME = "root"
DORIS_PASSWORD = "yjg@123456"

def test_final_sql_methods():
    print("最终测试 Doris SQL 执行方法...")
    
    # 测试 1: 使用 show_proc 执行 SQL（因为这个我们知道能工作）
    print("\n1. 通过 show_proc 执行 SQL:")
    try:
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/show_proc"
        params = {'path': '/current_queries'}
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        
        response = requests.get(url, params=params, auth=auth, timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"当前查询: {result}")
        
    except Exception as e:
        print(f"异常: {e}")
    
    # 测试 2: 查询表数据
    print("\n2. 查询具体表的数据 (通过 show_proc):")
    try:
        # 查看表结构
        url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/show_proc"
        params = {'path': '/dbs/10116/10126'}  # yjg/ods_travel 表
        auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
        
        response = requests.get(url, params=params, auth=auth, timeout=10)
        print(f"ods_travel 表详情: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"表信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        print(f"异常: {e}")
    
    # 测试 3: 尝试通过 MySQL 客户端模拟（使用 HTTP）
    print("\n3. 尝试 MySQL 兼容查询:")
    try:
        # 有些 Doris 支持简单的 HTTP SQL 查询
        base_urls = [
            f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/query",
            f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/sql",
            f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/execute"
        ]
        
        for base_url in base_urls:
            try:
                auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
                params = {
                    'q': 'SELECT 1',
                    'query': 'SELECT 1',
                    'sql': 'SELECT 1'
                }
                
                response = requests.get(base_url, params=params, auth=auth, timeout=5)
                print(f"{base_url}: {response.status_code}")
                if response.status_code == 200:
                    print(f"  内容: {response.text[:200]}...")
                    
            except Exception as e:
                print(f"  异常: {str(e)[:100]}...")
    
    except Exception as e:
        print(f"MySQL 兼容测试异常: {e}")
    
    # 测试 4: 查看系统配置，寻找正确的查询端点
    print("\n4. 查看系统配置:")
    try:
        config_paths = [
            '/frontends',
            '/backends', 
            '/cluster_health'
        ]
        
        for path in config_paths:
            try:
                url = f"http://{DORIS_FE_HOST}:{DORIS_HTTP_PORT}/api/show_proc"
                params = {'path': path}
                auth = HTTPBasicAuth(DORIS_USERNAME, DORIS_PASSWORD)
                
                response = requests.get(url, params=params, auth=auth, timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    print(f"{path}: {result.get('msg', 'N/A')}")
                    if 'data' in result and result['data']:
                        print(f"  数据: {result['data'][0] if result['data'] else 'Empty'}")
                        
            except Exception as e:
                print(f"  {path} 异常: {e}")
                
    except Exception as e:
        print(f"系统配置查询异常: {e}")

if __name__ == "__main__":
    test_final_sql_methods()