#!/usr/bin/env python3
"""
测试更新后的API端点，验证用户友好ID系统是否工作
"""

import asyncio
import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from tools.auth_tools import login
from tools.data_source_tools import create_doris_data_source, find_data_source, get_data_source_preview

async def test_updated_api():
    """测试更新后的API端点"""
    print("🧪 测试更新后的用户友好ID系统")
    print("=" * 50)
    
    # 1. 登录系统
    print("1️⃣ 登录系统...")
    try:
        login_result = await login()
        print(f"✅ 登录成功")
    except Exception as e:
        print(f"❌ 登录失败: {str(e)}")
        return
    
    # 2. 创建一个Doris数据源，指定用户友好的slug和display_name
    print("\n2️⃣ 创建Doris数据源...")
    try:
        create_result = await create_doris_data_source(
            name="测试Doris数据源API",
            host="192.168.61.30",
            port=9030,
            username="root", 
            password="xxxxxxxx",
            database="doris",
            description="测试用户友好ID系统的API端点",
            slug="test-doris-api",
            display_name="测试API数据库"
        )
        result_data = json.loads(create_result)
        if result_data.get("success"):
            print("✅ 创建成功")
            data_source_info = result_data.get("data", {})
            print(f"   数据源ID: {data_source_info.get('id')}")
            print(f"   Slug: {data_source_info.get('slug')}")
            print(f"   Display Name: {data_source_info.get('display_name')}")
        else:
            print(f"❌ 创建失败: {result_data.get('error')}")
            return
    except Exception as e:
        print(f"❌ 创建异常: {str(e)}")
        return
    
    # 3. 测试用不同的ID格式访问数据源
    print("\n3️⃣ 测试不同ID格式的数据预览...")
    
    test_ids = [
        "test-doris-api",      # 使用slug
        "测试Doris数据源API",    # 使用name  
        "测试API数据库"         # 使用display_name
    ]
    
    for test_id in test_ids:
        try:
            print(f"\n🔍 使用ID '{test_id}' 获取数据预览...")
            preview_result = await get_data_source_preview(test_id, limit=5)
            result_data = json.loads(preview_result)
            
            if result_data.get("success"):
                print(f"✅ 成功！使用 '{test_id}' 访问数据源")
            else:
                print(f"❌ 失败: {result_data.get('error')}")
                
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
    
    # 4. 测试查找功能
    print("\n4️⃣ 测试智能查找功能...")
    try:
        find_result = await find_data_source("test-doris")  # 部分匹配
        result_data = json.loads(find_result)
        
        if result_data.get("success"):
            print("✅ 智能查找成功")
            match_type = result_data.get("match_type", "unknown")
            print(f"   匹配类型: {match_type}")
        else:
            print(f"❌ 查找失败: {result_data.get('error')}")
            
    except Exception as e:
        print(f"❌ 查找异常: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_updated_api())