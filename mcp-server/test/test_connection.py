#!/usr/bin/env python3
"""
测试MCP服务器与后端的连接
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from client import api_client
from tools.auth_tools import login

async def test_connection():
    """测试连接和登录"""
    print("🔍 测试 MCP 服务器与后端连接...")
    
    try:
        # 测试后端健康检查
        print("1. 测试后端健康检查...")
        health_result = await api_client.get("../health")
        print(f"   健康检查结果: {health_result}")
        
        # 测试登录功能
        print("2. 测试默认管理员登录...")
        login_result = await login()
        print(f"   登录结果: {login_result}")
        
        print("✅ 连接和功能测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await api_client.close()

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)