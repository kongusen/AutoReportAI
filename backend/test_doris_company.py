#!/usr/bin/env python3
"""
测试公司Doris数据源连接
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.data.connectors.doris_connector import DorisConnector, DorisConfig

async def test_company_doris():
    """测试公司Doris数据源"""
    
    # 使用公司数据源配置
    config = DorisConfig(
        source_type="doris",
        name="公司测试连接",
        mysql_host="192.168.61.30",
        mysql_port=9030,
        mysql_database="yjg",
        mysql_username="root",
        mysql_password="yjg@123456",
        fe_hosts=["192.168.61.30"],
        http_port=8030,
        query_port=9030,
        database="yjg",
        username="root",
        password="yjg@123456",
        timeout=10,
        use_mysql_protocol=True
    )
    
    connector = DorisConnector(config)
    
    try:
        print("🔄 正在连接到公司Doris...")
        await connector.connect()
        
        print("✅ 连接成功！")
        
        # 测试简单查询
        print("\n🔄 测试简单查询...")
        test_queries = [
            "SELECT 1 as test_value",
            "SHOW DATABASES",
            "SHOW TABLES"
        ]
        
        for sql in test_queries:
            try:
                print(f"\n执行SQL: {sql}")
                result = await connector.execute_query(sql)
                
                if hasattr(result, 'data') and not result.data.empty:
                    print(f"✅ 查询成功，返回 {len(result.data)} 行数据")
                    print(result.data.head())
                else:
                    print("⚠️ 查询返回空结果")
                    
            except Exception as e:
                print(f"❌ 查询失败: {e}")
        
        print("\n🔄 测试获取表列表...")
        tables = await connector.get_all_tables()
        print(f"✅ 获取到 {len(tables)} 个表")
        if tables:
            print(f"前几个表: {tables[:5]}")
            
            # 测试第一个表的结构
            if tables:
                first_table = tables[0]
                print(f"\n🔄 测试表 {first_table} 的结构...")
                try:
                    schema = await connector.get_table_schema(first_table)
                    print(f"✅ 表结构获取成功: {schema.get('total_columns', 0)} 个字段")
                    for col in schema.get('columns', [])[:3]:
                        print(f"  - {col.get('name')}: {col.get('type')}")
                except Exception as e:
                    print(f"❌ 获取表结构失败: {e}")
        
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await connector.disconnect()
        print("🔄 连接已关闭")

if __name__ == "__main__":
    asyncio.run(test_company_doris())