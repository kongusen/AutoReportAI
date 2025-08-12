#!/usr/bin/env python3
"""
测试 Doris show_proc API 来获取系统信息
"""

import asyncio
import aiohttp
import json

async def test_show_proc():
    """测试 show_proc API 的各种路径"""
    
    host = "192.168.61.30"
    http_port = 8030
    username = "root"
    password = "yjg@123456"
    
    auth = aiohttp.BasicAuth(username, password)
    
    # 从之前的响应中看到的可用路径
    proc_paths = [
        "/",
        "/dbs", 
        "/backends",
        "/frontends",
        "/current_queries",
        "/jobs",
        "/statistic",
        "/monitor",
        "/cluster_health",
        "/transactions"
    ]
    
    print("=" * 80)
    print(f"测试 Doris show_proc API - {host}:{http_port}")
    print("=" * 80)
    
    async with aiohttp.ClientSession() as session:
        for path in proc_paths:
            try:
                print(f"\n🔍 测试路径: {path}")
                
                params = {"path": path}
                url = f"http://{host}:{http_port}/api/show_proc"
                
                async with session.get(url, params=params, auth=auth, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get("code") == 0:
                            data = result.get("data", [])
                            print(f"✅ 成功 - 返回 {len(data)} 条记录")
                            
                            # 显示前几条数据
                            for i, item in enumerate(data[:5]):
                                if isinstance(item, list):
                                    print(f"   [{i}]: {item}")
                                else:
                                    print(f"   [{i}]: {item}")
                            
                            if len(data) > 5:
                                print(f"   ... 还有 {len(data) - 5} 条记录")
                                
                        else:
                            print(f"❌ API 错误: {result.get('msg', 'Unknown error')}")
                    else:
                        print(f"❌ HTTP 错误: {response.status}")
                        
            except Exception as e:
                print(f"❌ 异常: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_show_proc())