#!/usr/bin/env python3
"""
测试用户友好ID系统的功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from tools.auth_tools import login
from tools.data_source_tools import find_data_source, list_data_sources, create_doris_data_source

async def test_id_system():
    """测试ID系统功能"""
    print("🧪 测试用户友好ID系统")
    print("=" * 50)
    
    # 1. 登录系统
    print("1️⃣ 登录系统...")
    try:
        login_result = await login()
        print(f"✅ 登录成功")
    except Exception as e:
        print(f"❌ 登录失败: {str(e)}")
        return
    
    # 2. 列出现有数据源
    print("\n2️⃣ 获取现有数据源列表...")
    try:
        sources_result = await list_data_sources(limit=10)
        print("✅ 获取数据源列表成功")
        print(sources_result)
    except Exception as e:
        print(f"❌ 获取数据源列表失败: {str(e)}")
    
    # 3. 创建测试Doris数据源（带有用户友好ID）
    print("\n3️⃣ 创建测试Doris数据源...")
    try:
        create_result = await create_doris_data_source(
            name="测试Doris数据源",
            host="192.168.61.30",
            port=9030,
            username="root", 
            password="xxxxxxxx",
            database="doris",
            description="用于测试用户友好ID系统的Doris数据源",
            slug="test-doris-db",
            display_name="我的测试Doris数据库"
        )
        print("✅ 创建Doris数据源成功")
        print(create_result)
    except Exception as e:
        print(f"❌ 创建Doris数据源失败: {str(e)}")
    
    # 4. 测试不同ID格式的查找功能
    print("\n4️⃣ 测试ID解析功能...")
    
    test_identifiers = [
        "test-doris-db",  # slug
        "测试Doris数据源",  # name
        "我的测试Doris数据库",  # display_name
        "doris"  # 模糊匹配
    ]
    
    for identifier in test_identifiers:
        try:
            print(f"\n🔍 查找数据源: '{identifier}'")
            find_result = await find_data_source(identifier)
            print(f"✅ 查找成功")
            print(find_result)
        except Exception as e:
            print(f"❌ 查找失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_id_system())