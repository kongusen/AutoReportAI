#!/usr/bin/env python3
"""
测试Doris连接器的修复效果
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.data.connectors.doris_connector import DorisConnector, DorisConfig

async def test_doris_connection():
    """测试Doris连接器"""
    
    # 测试配置 - 使用个人数据源配置
    config = DorisConfig(
        source_type="doris",
        name="测试连接",
        mysql_host="192.168.31.160",
        mysql_port=9030,
        mysql_database="retail_db", 
        mysql_username="root",
        mysql_password="",
        fe_hosts=["192.168.31.160"],
        http_port=8030,
        query_port=9030,
        database="retail_db",
        username="root", 
        password="",
        timeout=10,
        use_mysql_protocol=True
    )
    
    connector = DorisConnector(config)
    
    try:
        print("🔄 正在连接到Doris...")
        await connector.connect()
        
        print("✅ 连接成功！")
        
        # 测试简单查询
        print("\n🔄 测试简单查询...")
        test_queries = [
            "SHOW DATABASES",
            "SHOW TABLES", 
            "SELECT 1 as test_value",
            "SELECT COUNT(*) as count FROM information_schema.tables"
        ]
        
        for sql in test_queries:
            try:
                print(f"\n执行SQL: {sql}")
                result = await connector.execute_query(sql)
                
                if hasattr(result, 'data') and not result.data.empty:
                    print(f"✅ 查询成功，返回 {len(result.data)} 行数据")
                    if len(result.data) <= 5:  # 只显示前几行
                        print(result.data.to_string())
                else:
                    print("⚠️ 查询返回空结果")
                    
            except Exception as e:
                print(f"❌ 查询失败: {e}")
        
        print("\n🔄 测试获取表列表...")
        tables = await connector.get_all_tables()
        print(f"✅ 获取到 {len(tables)} 个表: {tables[:5]}...")  # 只显示前5个
        
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await connector.disconnect()
        print("🔄 连接已关闭")

if __name__ == "__main__":
    asyncio.run(test_doris_connection())