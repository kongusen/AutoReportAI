#!/usr/bin/env python3
"""
AutoReportAI MCP Server - Unified SSE Version
基于FastAPI的SSE服务器实现，整合了MCP工具功能
支持远程部署，基于HTTP/SSE协议
"""

import asyncio
import sys
import json
import os
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from config import config
from session import session_manager
from client import api_client

# 导入所有工具模块
from tools.auth_tools import (
    login, logout, get_current_user, switch_user, list_sessions,
    refresh_session, get_session_status
)

from tools.data_source_tools import (
    list_data_sources, create_sql_data_source, create_api_data_source, create_doris_data_source,
    upload_csv_data_source, test_data_source, sync_data_source,
    get_data_source_preview, update_data_source, delete_data_source, find_data_source
)

from tools.template_tools import (
    list_templates, create_text_template, upload_template_file,
    get_template, update_template, delete_template, duplicate_template, preview_template
)

from tools.task_tools import (
    list_tasks, create_task, get_task, update_task, run_task,
    enable_task, disable_task, delete_task, get_task_logs, get_task_status
)

from tools.report_tools import (
    generate_report, list_reports, get_report, download_report,
    regenerate_report, delete_report, get_report_content, batch_generate_reports
)

from tools.ai_provider_tools import (
    create_ai_provider, list_ai_providers, get_ai_provider, 
    update_ai_provider, delete_ai_provider, test_ai_provider
)

# 创建FastAPI应用
app = FastAPI(
    title="AutoReportAI MCP Server",
    description="AutoReportAI MCP Server with SSE support",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建MCP服务器实例
mcp = FastMCP(
    "AutoReportAI", 
    description="AutoReportAI完整功能MCP服务器 (SSE模式)"
)

# 工具注册表
TOOLS = {}

# ===== 认证工具 =====
@mcp.tool()
async def mcp_login(username: str = None, password: str = None) -> str:
    """用户登录AutoReportAI系统"""
    result = await login(username, password)
    # 注册工具到工具注册表
    TOOLS["mcp_login"] = login
    return result

@mcp.tool()
async def mcp_logout(session_id: str = None) -> str:
    """用户登出系统"""
    result = await logout(session_id)
    TOOLS["mcp_logout"] = logout
    return result

@mcp.tool()
async def mcp_get_current_user(session_id: str = None) -> str:
    """获取当前登录用户信息"""
    result = await get_current_user(session_id)
    TOOLS["mcp_get_current_user"] = get_current_user
    return result

@mcp.tool()
async def mcp_switch_user(session_id: str) -> str:
    """切换到指定用户会话（管理员功能）"""
    result = await switch_user(session_id)
    TOOLS["mcp_switch_user"] = switch_user
    return result

@mcp.tool()
async def mcp_list_sessions() -> str:
    """列出所有活跃用户会话（管理员功能）"""
    result = await list_sessions()
    TOOLS["mcp_list_sessions"] = list_sessions
    return result

@mcp.tool()
async def mcp_refresh_session(session_id: str = None) -> str:
    """刷新用户会话"""
    result = await refresh_session(session_id)
    TOOLS["mcp_refresh_session"] = refresh_session
    return result

@mcp.tool()
async def mcp_get_session_status() -> str:
    """获取会话管理器状态"""
    result = await get_session_status()
    TOOLS["mcp_get_session_status"] = get_session_status
    return result

# ===== 数据源工具 =====
@mcp.tool()
async def mcp_list_data_sources(skip: int = 0, limit: int = 100, 
                              source_type: str = None, is_active: bool = None,
                              search: str = None) -> str:
    """获取数据源列表"""
    result = await list_data_sources(skip, limit, source_type, is_active, search)
    TOOLS["mcp_list_data_sources"] = list_data_sources
    return result

@mcp.tool()
async def mcp_create_sql_data_source(name: str, connection_string: str, 
                                   description: str = "", sql_query_type: str = "single_table",
                                   base_query: str = None) -> str:
    """创建SQL数据库数据源"""
    result = await create_sql_data_source(name, connection_string, description, sql_query_type, base_query)
    TOOLS["mcp_create_sql_data_source"] = create_sql_data_source
    return result

@mcp.tool()
async def mcp_create_api_data_source(name: str, api_url: str, api_method: str = "GET",
                                   api_headers: str = "{}", api_body: str = None,
                                   description: str = "") -> str:
    """创建API数据源"""
    result = await create_api_data_source(name, api_url, api_method, api_headers, api_body, description)
    TOOLS["mcp_create_api_data_source"] = create_api_data_source
    return result

@mcp.tool()
async def mcp_create_doris_data_source(
    name: str, 
    host: str, 
    port: int = 9030,
    username: str = "root", 
    password: str = "", 
    database: str = "doris",
    fe_hosts: str = None,
    be_hosts: str = None,
    http_port: int = 8030,
    description: str = ""
) -> str:
    """创建Apache Doris数据源"""
    result = await create_doris_data_source(name, host, port, username, password, database, fe_hosts, be_hosts, http_port, description)
    TOOLS["mcp_create_doris_data_source"] = create_doris_data_source
    return result

@mcp.tool()
async def mcp_upload_csv_data_source(name: str, file_path: str, description: str = "") -> str:
    """创建CSV文件数据源并上传文件"""
    result = await upload_csv_data_source(name, file_path, description)
    TOOLS["mcp_upload_csv_data_source"] = upload_csv_data_source
    return result

@mcp.tool()
async def mcp_test_data_source(data_source_id: str) -> str:
    """测试数据源连接"""
    result = await test_data_source(data_source_id)
    TOOLS["mcp_test_data_source"] = test_data_source
    return result

@mcp.tool()
async def mcp_sync_data_source(data_source_id: str) -> str:
    """同步数据源数据"""
    result = await sync_data_source(data_source_id)
    TOOLS["mcp_sync_data_source"] = sync_data_source
    return result

@mcp.tool()
async def mcp_get_data_source_preview(data_source_id: str, limit: int = 10) -> str:
    """获取数据源数据预览"""
    result = await get_data_source_preview(data_source_id, limit)
    TOOLS["mcp_get_data_source_preview"] = get_data_source_preview
    return result

@mcp.tool()
async def mcp_update_data_source(data_source_id: str, name: str = None, 
                               description: str = None, connection_string: str = None,
                               is_active: bool = None) -> str:
    """更新数据源信息"""
    result = await update_data_source(data_source_id, name, description, connection_string, is_active)
    TOOLS["mcp_update_data_source"] = update_data_source
    return result

@mcp.tool()
async def mcp_delete_data_source(data_source_id: str) -> str:
    """删除数据源"""
    result = await delete_data_source(data_source_id)
    TOOLS["mcp_delete_data_source"] = delete_data_source
    return result

@mcp.tool()
async def mcp_find_data_source(identifier: str) -> str:
    """智能查找数据源，支持多种标识符格式 (UUID/slug/name/display_name)"""
    result = await find_data_source(identifier)
    TOOLS["mcp_find_data_source"] = find_data_source
    return result

# ===== 模板管理工具 =====
@mcp.tool()
async def mcp_list_templates() -> str:
    """列出当前用户的所有模板"""
    result = await list_templates()
    TOOLS["mcp_list_templates"] = list_templates
    return result

@mcp.tool()
async def mcp_create_text_template(name: str, content: str, description: str = "") -> str:
    """创建文本模板"""
    result = await create_text_template(name, content, description)
    TOOLS["mcp_create_text_template"] = create_text_template
    return result

@mcp.tool()
async def mcp_upload_template_file(name: str, file_path: str, description: str = "") -> str:
    """上传模板文件"""
    result = await upload_template_file(name, file_path, description)
    TOOLS["mcp_upload_template_file"] = upload_template_file
    return result

@mcp.tool()
async def mcp_get_template(template_id: str) -> str:
    """获取指定模板的详细信息"""
    result = await get_template(template_id)
    TOOLS["mcp_get_template"] = get_template
    return result

@mcp.tool()
async def mcp_update_template(template_id: str, name: str = None, content: str = None, description: str = None) -> str:
    """更新模板信息"""
    result = await update_template(template_id, name, content, description)
    TOOLS["mcp_update_template"] = update_template
    return result

@mcp.tool()
async def mcp_delete_template(template_id: str) -> str:
    """删除模板"""
    result = await delete_template(template_id)
    TOOLS["mcp_delete_template"] = delete_template
    return result

@mcp.tool()
async def mcp_duplicate_template(template_id: str, new_name: str) -> str:
    """复制模板"""
    result = await duplicate_template(template_id, new_name)
    TOOLS["mcp_duplicate_template"] = duplicate_template
    return result

@mcp.tool()
async def mcp_preview_template(template_id: str, sample_data: str = "{}") -> str:
    """预览模板效果"""
    result = await preview_template(template_id, sample_data)
    TOOLS["mcp_preview_template"] = preview_template
    return result

# ===== 任务管理工具 =====
@mcp.tool()
async def mcp_list_tasks() -> str:
    """列出当前用户的所有任务"""
    result = await list_tasks()
    TOOLS["mcp_list_tasks"] = list_tasks
    return result

@mcp.tool()
async def mcp_create_task(name: str, template_id: str, data_source_id: str, 
                         schedule: str = "manual", description: str = "",
                         recipients: str = "", ai_provider_id: str = None) -> str:
    """创建新任务"""
    result = await create_task(name, template_id, data_source_id, schedule, description, recipients, ai_provider_id)
    TOOLS["mcp_create_task"] = create_task
    return result

@mcp.tool()
async def mcp_get_task(task_id: str) -> str:
    """获取指定任务的详细信息"""
    result = await get_task(task_id)
    TOOLS["mcp_get_task"] = get_task
    return result

@mcp.tool()
async def mcp_update_task(task_id: str, name: str = None, schedule: str = None,
                         description: str = None, recipients: str = None,
                         ai_provider_id: str = None) -> str:
    """更新任务信息"""
    result = await update_task(task_id, name, schedule, description, recipients, ai_provider_id)
    TOOLS["mcp_update_task"] = update_task
    return result

@mcp.tool()
async def mcp_run_task(task_id: str) -> str:
    """手动运行任务"""
    result = await run_task(task_id)
    TOOLS["mcp_run_task"] = run_task
    return result

@mcp.tool()
async def mcp_enable_task(task_id: str) -> str:
    """启用任务（允许定时执行）"""
    result = await enable_task(task_id)
    TOOLS["mcp_enable_task"] = enable_task
    return result

@mcp.tool()
async def mcp_disable_task(task_id: str) -> str:
    """禁用任务（停止定时执行）"""
    result = await disable_task(task_id)
    TOOLS["mcp_disable_task"] = disable_task
    return result

@mcp.tool()
async def mcp_delete_task(task_id: str) -> str:
    """删除任务"""
    result = await delete_task(task_id)
    TOOLS["mcp_delete_task"] = delete_task
    return result

@mcp.tool()
async def mcp_get_task_logs(task_id: str, limit: int = 50) -> str:
    """获取任务执行日志"""
    result = await get_task_logs(task_id, limit)
    TOOLS["mcp_get_task_logs"] = get_task_logs
    return result

@mcp.tool()
async def mcp_get_task_status(task_id: str) -> str:
    """获取任务当前状态"""
    result = await get_task_status(task_id)
    TOOLS["mcp_get_task_status"] = get_task_status
    return result

# ===== 报告生成工具 =====
@mcp.tool()
async def mcp_generate_report(template_id: str, data_source_id: str, 
                             ai_provider_id: str = None, output_format: str = "html",
                             name: str = None, description: str = "") -> str:
    """生成报告"""
    result = await generate_report(template_id, data_source_id, ai_provider_id, output_format, name, description)
    TOOLS["mcp_generate_report"] = generate_report
    return result

@mcp.tool()
async def mcp_list_reports(limit: int = 50, offset: int = 0, status: str = None) -> str:
    """列出报告历史"""
    result = await list_reports(limit, offset, status)
    TOOLS["mcp_list_reports"] = list_reports
    return result

@mcp.tool()
async def mcp_get_report(report_id: str) -> str:
    """获取指定报告的详细信息"""
    result = await get_report(report_id)
    TOOLS["mcp_get_report"] = get_report
    return result

@mcp.tool()
async def mcp_download_report(report_id: str, save_path: str = None) -> str:
    """下载报告文件"""
    result = await download_report(report_id, save_path)
    TOOLS["mcp_download_report"] = download_report
    return result

@mcp.tool()
async def mcp_regenerate_report(report_id: str, ai_provider_id: str = None) -> str:
    """重新生成报告"""
    result = await regenerate_report(report_id, ai_provider_id)
    TOOLS["mcp_regenerate_report"] = regenerate_report
    return result

@mcp.tool()
async def mcp_delete_report(report_id: str) -> str:
    """删除报告"""
    result = await delete_report(report_id)
    TOOLS["mcp_delete_report"] = delete_report
    return result

@mcp.tool()
async def mcp_get_report_content(report_id: str) -> str:
    """获取报告内容"""
    result = await get_report_content(report_id)
    TOOLS["mcp_get_report_content"] = get_report_content
    return result

@mcp.tool()
async def mcp_batch_generate_reports(template_id: str, data_source_ids: str,
                                   ai_provider_id: str = None, output_format: str = "html") -> str:
    """批量生成报告"""
    result = await batch_generate_reports(template_id, data_source_ids, ai_provider_id, output_format)
    TOOLS["mcp_batch_generate_reports"] = batch_generate_reports
    return result

# ===== AI供应商工具 =====
@mcp.tool()
async def mcp_create_ai_provider(
    name: str,
    provider_type: str,
    api_key: str,
    base_url: str = None,
    model_name: str = None,
    description: str = ""
) -> str:
    """创建AI供应商配置"""
    result = await create_ai_provider(name, provider_type, api_key, base_url, model_name, description)
    TOOLS["mcp_create_ai_provider"] = create_ai_provider
    return result

@mcp.tool()
async def mcp_list_ai_providers() -> str:
    """列出所有AI供应商"""
    result = await list_ai_providers()
    TOOLS["mcp_list_ai_providers"] = list_ai_providers
    return result

@mcp.tool()
async def mcp_get_ai_provider(provider_id: str) -> str:
    """获取AI供应商详情"""
    result = await get_ai_provider(provider_id)
    TOOLS["mcp_get_ai_provider"] = get_ai_provider
    return result

@mcp.tool()
async def mcp_update_ai_provider(provider_id: str, name: str = None, api_key: str = None,
                               base_url: str = None, model_name: str = None,
                               description: str = None) -> str:
    """更新AI供应商配置"""
    result = await update_ai_provider(provider_id, name, api_key, base_url, model_name, description)
    TOOLS["mcp_update_ai_provider"] = update_ai_provider
    return result

@mcp.tool()
async def mcp_delete_ai_provider(provider_id: str) -> str:
    """删除AI供应商"""
    result = await delete_ai_provider(provider_id)
    TOOLS["mcp_delete_ai_provider"] = delete_ai_provider
    return result

@mcp.tool()
async def mcp_test_ai_provider(provider_id: str) -> str:
    """测试AI供应商连接"""
    result = await test_ai_provider(provider_id)
    TOOLS["mcp_test_ai_provider"] = test_ai_provider
    return result

# ===== 系统信息工具 =====
@mcp.tool()
async def mcp_get_system_info() -> str:
    """获取MCP服务器系统信息"""
    try:
        return json.dumps({
            "success": True,
            "data": {
                "server_name": "AutoReportAI MCP Server (Unified SSE Mode)",
                "version": "1.0.0",
                "mode": "SSE/HTTP",
                "host": config.MCP_SERVER_HOST,
                "port": config.MCP_SERVER_PORT,
                "config": config.to_dict(),
                "session_stats": {
                    "active_sessions": session_manager.get_session_count(),
                    "max_sessions": config.MAX_SESSIONS,
                    "current_session": session_manager._current_session_id
                },
                "backend_status": {
                    "base_url": config.BACKEND_BASE_URL,
                    "timeout": config.BACKEND_TIMEOUT
                }
            }
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取系统信息失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

# ===== 快速设置工具 =====
@mcp.tool()
async def mcp_quick_setup() -> str:
    """快速设置：登录默认管理员账户"""
    result = await login()
    TOOLS["mcp_quick_setup"] = login
    return result

@mcp.tool()
async def mcp_create_demo_workflow(workflow_name: str = "演示工作流") -> str:
    """创建演示工作流：数据源 -> 模板 -> 任务"""
    import json
    
    try:
        # 先登录
        login_result = await login()
        login_data = json.loads(login_result)
        
        if not login_data.get("success"):
            return login_result
        
        results = {"steps": []}
        
        # 创建演示数据源（API类型）
        ds_result = await create_api_data_source(
            name=f"{workflow_name}_数据源",
            api_url="https://jsonplaceholder.typicode.com/posts",
            description="演示用的API数据源"
        )
        results["steps"].append({"step": "create_data_source", "result": json.loads(ds_result)})
        
        return json.dumps({
            "success": True,
            "message": f"演示工作流 '{workflow_name}' 创建进行中",
            "data": results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"创建演示工作流失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

# ===== FastAPI路由 =====
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "AutoReportAI MCP Server",
        "version": "1.0.0",
        "mode": "SSE/HTTP",
        "endpoints": {
            "health": "/health",
            "tools": "/tools",
            "call_tool": "/tools/{tool_name}",
            "sse": "/sse"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 测试后端连接
        backend_status = "unknown"
        try:
            test_result = await api_client.get("../health")
            backend_status = "healthy" if test_result else "degraded"
        except:
            backend_status = "degraded"
        
        return {
            "status": "healthy",
            "server": "AutoReportAI MCP Server (Unified SSE)",
            "version": "1.0.0",
            "backend_status": backend_status,
            "backend_url": config.BACKEND_BASE_URL,
            "session_count": session_manager.get_session_count(),
            "available_tools": len(TOOLS)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/tools")
async def list_available_tools():
    """获取可用工具列表"""
    tools_info = []
    for tool_name in TOOLS.keys():
        # 获取函数的文档字符串
        func = TOOLS[tool_name]
        doc = func.__doc__ or "无描述"
        tools_info.append({
            "name": tool_name,
            "description": doc.strip()
        })
    
    return {
        "tools": tools_info,
        "total": len(tools_info)
    }

@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, payload: Dict[str, Any] = None):
    """调用指定工具"""
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        # 获取工具函数
        tool_func = TOOLS[tool_name]
        
        # 解析参数
        args = {}
        if payload and "arguments" in payload:
            args = payload["arguments"]
        
        # 调用工具
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**args)
        else:
            result = tool_func(**args)
        
        return {
            "success": True,
            "tool": tool_name,
            "result": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "tool": tool_name,
            "error": str(e),
            "type": type(e).__name__
        }

# 快捷工具端点
@app.post("/quick_setup")
async def quick_setup():
    """快速设置：登录默认管理员"""
    return await call_tool("mcp_login", {"arguments": {}})

@app.post("/system_info")
async def system_info():
    """获取系统信息"""
    try:
        info = {
            "server_name": "AutoReportAI MCP Server (Unified SSE)",
            "version": "1.0.0", 
            "mode": "SSE/HTTP",
            "host": config.MCP_SERVER_HOST,
            "port": config.MCP_SERVER_PORT,
            "backend_url": config.BACKEND_BASE_URL,
            "session_stats": {
                "active_sessions": session_manager.get_session_count(),
                "max_sessions": config.MAX_SESSIONS,
            },
            "available_tools": len(TOOLS)
        }
        
        return {
            "success": True,
            "data": info
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/sse")
async def sse_endpoint():
    """SSE端点，用于服务器发送事件"""
    async def event_stream():
        """SSE事件流生成器"""
        # 发送连接确认
        yield f"data: {json.dumps({'type': 'connection', 'message': 'SSE连接已建立'})}\n\n"
        
        # 定期发送系统状态
        while True:
            try:
                # 获取系统状态
                status = {
                    "type": "status",
                    "timestamp": json.dumps({"timestamp": asyncio.get_event_loop().time()}),
                    "active_sessions": session_manager.get_session_count(),
                    "backend_healthy": True  # 简化版本
                }
                
                yield f"data: {json.dumps(status, ensure_ascii=False)}\n\n"
                await asyncio.sleep(30)  # 每30秒发送一次状态更新
                
            except Exception as e:
                error_data = {
                    "type": "error", 
                    "message": f"SSE stream error: {str(e)}"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                break
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# 启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    print("🚀 AutoReportAI MCP Server (Unified SSE) 启动中...")
    print(f"📡 后端API: {config.BACKEND_BASE_URL}")
    
    # 启动会话管理
    await session_manager.start_cleanup_task()
    print("🧹 会话清理任务已启动")
    
    # 测试后端连接
    try:
        test_result = await api_client.get("../health")
        print("✅ 后端连接测试成功")
    except Exception as e:
        print(f"⚠️  后端连接测试失败: {e}")
    
    print("🎉 MCP服务器启动完成！")
    print("\n📖 可用工具:")
    print("  认证: mcp_login, mcp_logout, mcp_get_current_user")
    print("  数据源: mcp_list_data_sources, mcp_create_sql_data_source, mcp_upload_csv_data_source")
    print("  快速开始: mcp_quick_setup, mcp_create_demo_workflow")
    print("  系统: mcp_get_system_info, mcp_get_session_status")

@app.on_event("shutdown") 
async def shutdown_event():
    """关闭时清理"""
    print("🛑 正在关闭 MCP服务器...")
    await session_manager.stop_cleanup_task()
    await api_client.close()
    print("👋 MCP服务器已关闭")

def main():
    """启动服务器"""
    host = config.MCP_SERVER_HOST
    port = config.MCP_SERVER_PORT
    
    print(f"🌐 启动地址: http://{host}:{port}")
    print(f"🔗 健康检查: http://{host}:{port}/health")
    print(f"📋 工具列表: http://{host}:{port}/tools")
    print(f"📡 SSE端点: http://{host}:{port}/sse")
    
    # 同时运行FastAPI和MCP服务器
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()