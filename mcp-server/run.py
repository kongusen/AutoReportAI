#!/usr/bin/env python3
"""
AutoReportAI MCP Server Launcher
MCP服务器启动器，提供更友好的启动体验
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    AutoReportAI MCP Server                   ║
║                                                              ║
║  🤖 基于优化后端API的完整MCP工具服务器                        ║
║  📊 支持数据源、模板、任务、报告的全生命周期管理                ║
║  🔐 多用户会话管理和权限控制                                  ║
║  ⚡ 支持SQL、CSV、API等多种数据源类型                         ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ Python版本过低，需要Python 3.8+")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 检查依赖包
    try:
        import httpx
        import fastmcp
        from mcp.server.fastmcp import FastMCP
        print("✅ 依赖包检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    # 检查配置文件
    try:
        from config import config
        print(f"✅ 后端API地址: {config.BACKEND_BASE_URL}")
    except Exception as e:
        print(f"❌ 配置文件错误: {e}")
        return False
    
    return True

def print_usage_tips():
    """打印使用提示"""
    tips = """
🚀 服务器启动成功！

📖 快速开始:
  1. 使用 mcp_quick_setup() 登录默认管理员账户
  2. 使用 mcp_create_demo_workflow() 创建演示工作流
  3. 使用 mcp_get_system_info() 查看系统状态

🔧 主要工具分类:
  
  👤 认证管理:
    - mcp_login(username, password) - 用户登录
    - mcp_logout() - 用户登出
    - mcp_get_current_user() - 获取当前用户
    - mcp_list_sessions() - 查看所有会话(管理员)
  
  📊 数据源管理:
    - mcp_list_data_sources() - 列出数据源
    - mcp_create_sql_data_source(name, connection_string) - 创建SQL数据源
    - mcp_create_api_data_source(name, api_url) - 创建API数据源
    - mcp_upload_csv_data_source(name, file_path) - 上传CSV文件
    - mcp_test_data_source(id) - 测试数据源连接
  
  📝 模板管理:
    - mcp_list_templates() - 列出模板
    - mcp_create_text_template(name, content) - 创建文本模板
    - mcp_upload_template_file(name, file_path) - 上传模板文件
  
  ⚡ 任务管理:
    - mcp_list_tasks() - 列出任务
    - mcp_create_task(name, template_id, data_source_id) - 创建任务
    - mcp_run_task(task_id) - 运行任务
  
  📈 报告生成:
    - mcp_generate_report(template_id, data_source_id) - 生成报告
    - mcp_list_reports() - 查看报告历史

💡 环境变量配置:
  export BACKEND_BASE_URL="http://localhost:8000/api/v1"
  export DEFAULT_ADMIN_USERNAME="admin"
  export DEFAULT_ADMIN_PASSWORD="admin123"

📞 如需帮助，请查看 README.md 或使用 mcp_get_system_info()
"""
    print(tips)

async def test_backend_connection():
    """测试后端连接"""
    print("🔗 测试后端连接...")
    
    try:
        from client import api_client
        
        # 尝试访问健康检查端点
        result = await api_client.get("../health")
        print("✅ 后端连接正常")
        return True
        
    except Exception as e:
        print(f"⚠️  后端连接失败: {e}")
        print("   请确保后端服务正在运行")
        return False

def main():
    """主启动函数"""
    print_banner()
    
    # 环境检查
    if not check_environment():
        sys.exit(1)
    
    # 后端连接测试
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        backend_ok = loop.run_until_complete(test_backend_connection())
        if not backend_ok:
            print("⚠️  后端连接失败，但服务器仍将启动")
        
    except Exception as e:
        print(f"⚠️  连接测试异常: {e}")
    
    print_usage_tips()
    
    # 启动MCP服务器
    try:
        from mcp_sse_server import main as mcp_main
        mcp_main()
        
    except KeyboardInterrupt:
        print("\n👋 收到中断信号，服务器已关闭")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()