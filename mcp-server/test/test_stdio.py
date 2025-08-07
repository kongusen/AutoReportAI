#!/usr/bin/env python3
"""
测试stdio配置是否正确
"""

import subprocess
import sys
import os
from pathlib import Path

def test_stdio_config():
    """测试stdio配置"""
    print("🧪 测试AutoReportAI MCP stdio配置...")
    
    # 配置路径
    python_path = "/Users/shan/work/uploads/AutoReportAI/mcp-server/venv/bin/python"
    script_path = "/Users/shan/work/uploads/AutoReportAI/mcp-server/main.py"
    cwd = "/Users/shan/work/uploads/AutoReportAI/mcp-server"
    
    # 环境变量
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": "/Users/shan/work/uploads/AutoReportAI/mcp-server",
        "BACKEND_BASE_URL": "http://localhost:8000/api/v1",
        "DEFAULT_ADMIN_USERNAME": "admin",
        "DEFAULT_ADMIN_PASSWORD": "password"
    })
    
    # 检查文件存在性
    print("1️⃣ 检查文件存在性...")
    if not Path(python_path).exists():
        print(f"❌ Python路径不存在: {python_path}")
        return False
    
    if not Path(script_path).exists():
        print(f"❌ 脚本路径不存在: {script_path}")
        return False
        
    print("✅ 文件路径检查通过")
    
    # 检查权限
    print("2️⃣ 检查执行权限...")
    if not os.access(python_path, os.X_OK):
        print(f"❌ Python没有执行权限: {python_path}")
        return False
        
    if not os.access(script_path, os.R_OK):
        print(f"❌ 脚本没有读取权限: {script_path}")
        return False
        
    print("✅ 权限检查通过")
    
    # 测试命令执行
    print("3️⃣ 测试命令执行...")
    try:
        # 测试Python版本
        result = subprocess.run([python_path, "--version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Python版本: {result.stdout.strip()}")
        else:
            print(f"❌ Python版本检查失败: {result.stderr}")
            return False
            
        # 测试脚本语法
        result = subprocess.run([python_path, "-m", "py_compile", script_path],
                              capture_output=True, text=True, timeout=10,
                              cwd=cwd, env=env)
        if result.returncode == 0:
            print("✅ 脚本语法检查通过")
        else:
            print(f"❌ 脚本语法错误: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 命令执行异常: {e}")
        return False
    
    print("🎉 stdio配置测试通过！")
    return True

def print_final_config():
    """打印最终配置"""
    print("\n📋 最终stdio配置:")
    config = {
        "mcpServers": {
            "autoreport": {
                "command": "/Users/shan/work/uploads/AutoReportAI/mcp-server/venv/bin/python",
                "args": ["/Users/shan/work/uploads/AutoReportAI/mcp-server/main.py"],
                "cwd": "/Users/shan/work/uploads/AutoReportAI/mcp-server",
                "env": {
                    "PYTHONPATH": "/Users/shan/work/uploads/AutoReportAI/mcp-server",
                    "BACKEND_BASE_URL": "http://localhost:8000/api/v1",
                    "DEFAULT_ADMIN_USERNAME": "admin",
                    "DEFAULT_ADMIN_PASSWORD": "password"
                }
            }
        }
    }
    
    import json
    print(json.dumps(config, indent=2))
    
    print("\n📝 使用说明:")
    print("1. 确保后端服务运行在 http://localhost:8000")
    print("2. 将上述配置添加到你的MCP客户端配置文件中")
    print("3. 重启你的MCP客户端")
    print("4. 测试工具调用")

if __name__ == "__main__":
    success = test_stdio_config()
    if success:
        print_final_config()
    else:
        print("\n❌ 配置测试失败，请检查错误信息")
        sys.exit(1)