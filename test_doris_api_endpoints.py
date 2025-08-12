#!/usr/bin/env python3
"""
测试 Doris API 端点的可用性
"""

import asyncio
import aiohttp
import json

async def test_doris_api_endpoints():
    """测试各种 Doris API 端点"""
    
    host = "192.168.61.30"
    http_port = 8030
    username = "root"
    password = "yjg@123456"
    
    auth = aiohttp.BasicAuth(username, password)
    
    # 测试的端点列表
    endpoints = [
        # 管理API
        {"method": "GET", "path": "/api/show_proc", "params": {"path": "/"}},
        {"method": "GET", "path": "/api/bootstrap"},
        {"method": "GET", "path": "/api/backends"},
        {"method": "GET", "path": "/api/frontends"},
        {"method": "GET", "path": "/api/cluster_info"},
        
        # 查询API尝试
        {"method": "GET", "path": "/api/sql", "params": {"sql": "SHOW DATABASES"}},
        {"method": "POST", "path": "/api/sql", "data": {"sql": "SHOW DATABASES"}},
        {"method": "GET", "path": "/api/query_data", "params": {"sql": "SHOW DATABASES"}},
        {"method": "POST", "path": "/api/query_data", "data": {"sql": "SHOW DATABASES"}},
        {"method": "GET", "path": "/api/database", "params": {"sql": "SHOW DATABASES"}},
        {"method": "POST", "path": "/api/database", "data": {"sql": "SHOW DATABASES"}},
        {"method": "GET", "path": "/api/execute", "params": {"sql": "SHOW DATABASES"}},
        {"method": "POST", "path": "/api/execute", "data": {"sql": "SHOW DATABASES"}},
    ]
    
    print("=" * 80)
    print(f"测试 Doris API 端点 - {host}:{http_port}")
    print("=" * 80)
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            url = f"http://{host}:{http_port}{endpoint['path']}"
            method = endpoint['method']
            params = endpoint.get('params')
            data = endpoint.get('data')
            
            try:
                print(f"\n🔍 测试: {method} {endpoint['path']}")
                
                if method == "GET":
                    async with session.get(url, params=params, auth=auth, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        status = response.status
                        content_type = response.headers.get('content-type', '')
                        
                        if status == 200:
                            if 'json' in content_type:
                                try:
                                    result = await response.json()
                                    print(f"✅ 成功 - Status: {status}, Content-Type: {content_type}")
                                    if isinstance(result, dict) and len(str(result)) < 500:
                                        print(f"   响应: {result}")
                                    else:
                                        print(f"   响应长度: {len(str(result))} 字符")
                                except json.JSONDecodeError:
                                    text = await response.text()
                                    print(f"✅ 成功 - Status: {status}, Content-Type: {content_type}")
                                    print(f"   响应长度: {len(text)} 字符 (非JSON)")
                            else:
                                text = await response.text()
                                print(f"✅ 成功 - Status: {status}, Content-Type: {content_type}")
                                print(f"   响应长度: {len(text)} 字符")
                        else:
                            print(f"❌ 失败 - Status: {status}")
                            
                elif method == "POST":
                    headers = {"Content-Type": "application/json"} if data else {}
                    json_data = data if data else None
                    
                    async with session.post(url, json=json_data, auth=auth, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        status = response.status
                        content_type = response.headers.get('content-type', '')
                        
                        if status == 200:
                            if 'json' in content_type:
                                try:
                                    result = await response.json()
                                    print(f"✅ 成功 - Status: {status}, Content-Type: {content_type}")
                                    if isinstance(result, dict) and len(str(result)) < 500:
                                        print(f"   响应: {result}")
                                    else:
                                        print(f"   响应长度: {len(str(result))} 字符")
                                except json.JSONDecodeError:
                                    text = await response.text()
                                    print(f"✅ 成功 - Status: {status}, Content-Type: {content_type}")
                                    print(f"   响应长度: {len(text)} 字符 (非JSON)")
                            else:
                                text = await response.text()
                                print(f"✅ 成功 - Status: {status}, Content-Type: {content_type}")
                                print(f"   响应长度: {len(text)} 字符")
                        else:
                            error_text = await response.text()
                            print(f"❌ 失败 - Status: {status}")
                            if len(error_text) < 200:
                                print(f"   错误: {error_text}")
                            
            except asyncio.TimeoutError:
                print(f"⏰ 超时")
            except Exception as e:
                print(f"❌ 异常: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_doris_api_endpoints())