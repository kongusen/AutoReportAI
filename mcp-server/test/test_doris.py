#!/usr/bin/env python3
"""
测试Doris数据源创建和连接
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from tools.auth_tools import login
from tools.data_source_tools import create_doris_data_source, test_data_source, list_data_sources
import json

async def test_doris_workflow():
    """测试完整的Doris工作流"""
    print("🧪 测试 AutoReportAI Doris 数据源功能")
    print("=" * 50)
    
    try:
        # 1. 登录
        print("1️⃣ 登录系统...")
        login_result = await login()
        login_data = json.loads(login_result)
        
        if not login_data.get("success"):
            print(f"❌ 登录失败: {login_data.get('error')}")
            return False
        
        print("✅ 登录成功")
        
        # 2. 创建Doris数据源
        print("\n2️⃣ 创建Doris数据源...")
        doris_result = await create_doris_data_source(
            name="测试Doris数据源",
            host="192.168.61.30",
            port=9030,
            username="root",
            password="yjg@123456",
            database="doris",
            description="用于测试的Doris数据源连接"
        )
        
        doris_data = json.loads(doris_result)
        print(f"创建结果: {doris_data}")
        
        if not doris_data.get("success"):
            print(f"❌ 创建Doris数据源失败: {doris_data.get('error')}")
            return False
        
        print("✅ Doris数据源创建成功")
        data_source_id = doris_data["data"]["id"]
        
        # 3. 测试连接
        print("\n3️⃣ 测试Doris连接...")
        test_result = await test_data_source(data_source_id)
        test_data = json.loads(test_result)
        print(f"连接测试结果: {test_data}")
        
        if test_data.get("success"):
            print("✅ Doris连接测试成功")
        else:
            print(f"⚠️  Doris连接测试失败: {test_data.get('error')}")
        
        # 4. 列出数据源
        print("\n4️⃣ 查看数据源列表...")
        list_result = await list_data_sources(limit=5)
        list_data = json.loads(list_result)
        
        if list_data.get("success"):
            items = list_data["data"]["items"]
            print(f"📊 数据源总数: {len(items)}")
            for item in items:
                print(f"   - {item['name']} ({item['source_type']})")
        
        print("\n🎉 Doris工作流测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_doris_connection_info():
    """打印Doris连接信息说明"""
    print("\n📋 Doris 连接配置说明:")
    print("=" * 30)
    print("主机: 192.168.61.30")
    print("查询端口: 9030")
    print("HTTP端口: 8030 (默认)")
    print("用户名: root")
    print("密码: yjg@123456")
    print("数据库: doris")
    print()
    print("📡 Doris连接字符串格式:")
    print("doris://root:yjg@123456@192.168.61.30:9030/doris")
    print()
    print("🔧 MCP工具调用示例:")
    print("mcp_create_doris_data_source(")
    print("    name='我的Doris数据源',")
    print("    host='192.168.61.30',")
    print("    port=9030,")
    print("    username='root',")
    print("    password='yjg@123456',")
    print("    database='doris'")
    print(")")

if __name__ == "__main__":
    print_doris_connection_info()
    
    print("\n🧪 开始运行测试...")
    success = asyncio.run(test_doris_workflow())
    if not success:
        sys.exit(1)