#!/usr/bin/env python3
"""
测试 Doris 数据源连接器功能
192.168.61.30:9030 root/yjg@123456
"""

import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.connectors.doris_connector import DorisConnector, DorisConfig

async def test_doris_connection():
    """测试 Doris 连接功能"""
    print("=" * 60)
    print("测试 Doris 数据源连接器")
    print("=" * 60)
    
    # 创建 Doris 配置
    config = DorisConfig(
        fe_hosts=['192.168.61.30'],
        be_hosts=['192.168.61.30'],  # 通常与 FE 主机相同
        http_port=8030,
        query_port=9030,
        username='root',
        password='yjg@123456',
        database='information_schema'  # 使用默认的信息模式数据库
    )
    
    print(f"连接参数:")
    print(f"  主机: {config.fe_hosts}")
    print(f"  查询端口: {config.query_port}")
    print(f"  HTTP端口: {config.http_port}")
    print(f"  用户: {config.username}")
    print(f"  数据库: {config.database}")
    print()
    
    try:
        # 创建连接器实例并使用异步上下文管理器
        async with DorisConnector(config) as connector:
            print("✅ DorisConnector 实例创建成功")
            
            # 测试连接
            print("\n🔗 测试连接...")
            connection_result = await connector.test_connection()
            if connection_result['success']:
                print("✅ 连接测试成功!")
                print(f"   响应: {connection_result.get('message', 'N/A')}")
            else:
                print("❌ 连接测试失败!")
                print(f"   错误: {connection_result.get('error', 'Unknown error')}")
                return False
                
            # 测试查询数据库列表
            print("\n📋 查询数据库列表...")
            try:
                databases_query = "SHOW DATABASES"
                result = await connector.execute_query(databases_query)
                
                # DorisQueryResult 对象格式
                if hasattr(result, 'data'):
                    print("✅ 数据库查询成功!")
                    data = result.data
                    if hasattr(data, 'values'):  # pandas DataFrame
                        databases = [row[0] for row in data.values]
                    else:  # 列表格式
                        databases = [row[0] if isinstance(row, (list, tuple)) else row for row in data]
                    print(f"   发现 {len(databases)} 个数据库:")
                    for db in databases[:10]:  # 显示前10个
                        print(f"     - {db}")
                    if len(databases) > 10:
                        print(f"     ... 还有 {len(databases) - 10} 个数据库")
                else:
                    print("❌ 数据库查询失败!")
                    print(f"   错误: 查询结果格式异常")
                    
            except Exception as e:
                print(f"❌ 查询数据库时出错: {e}")
                import traceback
                traceback.print_exc()
                
            # 测试查询表信息
            print("\n📊 查询系统表信息...")
            try:
                tables_query = "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', '__internal_schema') LIMIT 10"
                result = await connector.execute_query(tables_query)
                
                if hasattr(result, 'data'):
                    print("✅ 表查询成功!")
                    data = result.data
                    if hasattr(data, 'values'):  # pandas DataFrame
                        tables = data.values
                    else:  # 列表格式
                        tables = data
                    print(f"   发现 {len(tables)} 个用户表:")
                    for row in tables:
                        schema, table = row[0], row[1]
                        print(f"     - {schema}.{table}")
                else:
                    print("❌ 表查询失败!")
                    print(f"   错误: 查询结果格式异常")
                    
            except Exception as e:
                print(f"❌ 查询表时出错: {e}")
                import traceback
                traceback.print_exc()
                
            # 测试基本统计查询
            print("\n📈 测试基本统计查询...")
            try:
                stats_query = "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', '__internal_schema')"
                result = await connector.execute_query(stats_query)
                
                if hasattr(result, 'data'):
                    print("✅ 统计查询成功!")
                    data = result.data
                    if hasattr(data, 'values'):  # pandas DataFrame
                        count = data.values[0][0] if len(data.values) > 0 else 0
                    else:  # 列表格式
                        count = data[0][0] if len(data) > 0 else 0
                    print(f"   用户表总数: {count}")
                else:
                    print("❌ 统计查询失败!")
                    print(f"   错误: 查询结果格式异常")
                    
            except Exception as e:
                print(f"❌ 统计查询时出错: {e}")
                import traceback
                traceback.print_exc()
                
            return True
        
    except Exception as e:
        print(f"❌ 连接器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

if __name__ == "__main__":
    success = asyncio.run(test_doris_connection())
    sys.exit(0 if success else 1)