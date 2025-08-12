#!/usr/bin/env python3
"""
测试当前的 Doris 连接器实现
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, '/Users/shan/work/uploads/AutoReportAI/backend')

# 模拟加密解密功能
def mock_decrypt_data(data):
    return data  # 对于测试，直接返回原始数据

# 替换加密解密模块
sys.modules['app.core.security_utils'] = type(sys)('mock_security_utils')
sys.modules['app.core.security_utils'].decrypt_data = mock_decrypt_data

from app.services.connectors.doris_connector import DorisConnector, DorisConfig
from unittest.mock import Mock

async def test_current_connector():
    print("测试当前的 Doris 连接器...")
    
    # 创建模拟的数据源对象
    class MockDataSource:
        doris_fe_hosts = ["192.168.61.30"]
        doris_be_hosts = ["192.168.61.30"]
        doris_http_port = 8030
        doris_query_port = 9030
        doris_database = "yjg"
        doris_username = "root"
        doris_password = "yjg@123456"  # 未加密的密码用于测试
    
    mock_data_source = MockDataSource()
    
    # 创建连接器
    connector = DorisConnector.from_data_source(mock_data_source)
    
    try:
        # 测试连接
        async with connector:
            print("\n1. 测试连接...")
            result = await connector.test_connection()
            print(f"连接测试结果: {result}")
            
            if result.get("success"):
                print("\n2. 测试查询...")
                try:
                    query_result = await connector.execute_query("SELECT 1 as test_connection")
                    print(f"查询结果:")
                    print(f"  数据: {query_result.data}")
                    print(f"  执行时间: {query_result.execution_time}s")
                    print(f"  FE主机: {query_result.fe_host}")
                    
                except Exception as query_error:
                    print(f"查询失败: {query_error}")
                
                print("\n3. 测试表结构查询...")
                try:
                    tables_result = await connector.execute_query("SHOW TABLES")
                    print(f"表列表:")
                    print(f"  数据: {tables_result.data}")
                    
                except Exception as tables_error:
                    print(f"表查询失败: {tables_error}")
            else:
                print("连接测试失败，跳过查询测试")
                
    except Exception as e:
        print(f"测试异常: {e}")

if __name__ == "__main__":
    asyncio.run(test_current_connector())