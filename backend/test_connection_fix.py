#!/usr/bin/env python3
"""
测试数据源连接修复
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

from app.db.session import SessionLocal
from app.models.data_source import DataSource
from app.services.connectors.connector_factory import create_connector


async def test_data_source_connection():
    """测试数据源连接"""
    db = SessionLocal()
    try:
        # 获取"公司数据"数据源
        data_source = db.query(DataSource).filter(DataSource.display_name == '政采').first()
        
        if not data_source:
            print("未找到'政采'数据源")
            return False
        
        print(f"测试数据源: {data_source.name} (ID: {data_source.id})")
        print(f"类型: {data_source.source_type}")
        print(f"FE主机: {data_source.doris_fe_hosts}")
        print(f"用户名: {data_source.doris_username}")
        
        # 创建连接器
        connector = create_connector(data_source)
        
        # 测试连接
        async with connector:
            print("正在测试连接...")
            result = await connector.test_connection()
            
            if result.get("success"):
                print("✅ 连接测试成功!")
                print(f"消息: {result.get('message')}")
                print(f"FE主机: {result.get('fe_host')}")
                return True
            else:
                print("❌ 连接测试失败!")
                print(f"错误: {result.get('error')}")
                print(f"消息: {result.get('message')}")
                return False
                
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(test_data_source_connection())
    sys.exit(0 if success else 1)