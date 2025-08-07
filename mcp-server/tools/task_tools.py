"""
AutoReportAI Task Management Tools
任务管理MCP工具

提供任务的创建、运行、监控、更新、删除等完整生命周期管理功能
支持定时任务和手动任务两种模式
"""

import json
from typing import Dict, Any, Optional
from client import api_client
from session import session_manager
from utils.helpers import format_response, handle_api_error, validate_uuid

async def list_tasks() -> str:
    """
    列出当前用户的所有任务
    
    Returns:
        JSON格式的任务列表
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 调用后端API
        response = await api_client.get("tasks/")
        
        if response.get("success", True):
            tasks = response.get("data", [])
            return format_response(True, data={
                "tasks": tasks,
                "total": len(tasks) if isinstance(tasks, list) else 0,
                "message": f"获取到 {len(tasks) if isinstance(tasks, list) else 0} 个任务"
            })
        else:
            return format_response(False, error=response.get("message", "获取任务列表失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取任务列表")

async def create_task(
    name: str,
    template_id: str,
    data_source_id: str,
    schedule: str = "manual",
    description: str = "",
    recipients: str = "",
    ai_provider_id: str = None
) -> str:
    """
    创建新任务
    
    Args:
        name: 任务名称
        template_id: 模板ID
        data_source_id: 数据源ID
        schedule: 调度配置 (manual=手动执行, 或cron表达式如 "0 9 * * *")
        description: 任务描述 (可选)
        recipients: 接收者邮箱列表，逗号分隔 (可选)
        ai_provider_id: AI提供商ID (可选)
    
    Returns:
        JSON格式的创建结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证必需参数
        if not name or not name.strip():
            return format_response(False, error="任务名称不能为空")
        
        if not validate_uuid(template_id):
            return format_response(False, error="无效的模板ID格式")
        
        if not validate_uuid(data_source_id):
            return format_response(False, error="无效的数据源ID格式")
        
        if ai_provider_id and not validate_uuid(ai_provider_id):
            return format_response(False, error="无效的AI提供商ID格式")
        
        # 验证调度配置
        if not schedule or not schedule.strip():
            schedule = "manual"
        
        # 处理接收者列表
        recipient_list = []
        if recipients and recipients.strip():
            recipient_list = [email.strip() for email in recipients.split(",") if email.strip()]
        
        # 准备请求数据
        task_data = {
            "name": name.strip(),
            "template_id": template_id,
            "data_source_id": data_source_id,
            "schedule": schedule.strip(),
            "description": description.strip() if description else "",
            "recipients": recipient_list,
            "ai_provider_id": ai_provider_id,
            "is_active": True
        }
        
        # 调用后端API
        response = await api_client.post("tasks/", json=task_data)
        
        if response.get("success", True):
            task = response.get("data", {})
            return format_response(True, data=task, message=f"成功创建任务: {name}")
        else:
            return format_response(False, error=response.get("message", "创建任务失败"))
            
    except Exception as e:
        return handle_api_error(e, "创建任务")

async def get_task(task_id: str) -> str:
    """
    获取指定任务的详细信息
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON格式的任务信息
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(task_id):
            return format_response(False, error="无效的任务ID格式")
        
        # 调用后端API
        response = await api_client.get(f"tasks/{task_id}")
        
        if response.get("success", True):
            task = response.get("data", {})
            return format_response(True, data=task, message="获取任务信息成功")
        else:
            return format_response(False, error=response.get("message", "获取任务信息失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取任务信息")

async def update_task(
    task_id: str,
    name: str = None,
    schedule: str = None,
    description: str = None,
    recipients: str = None,
    ai_provider_id: str = None
) -> str:
    """
    更新任务信息
    
    Args:
        task_id: 任务ID
        name: 新的任务名称 (可选)
        schedule: 新的调度配置 (可选)
        description: 新的任务描述 (可选)
        recipients: 新的接收者邮箱列表 (可选)
        ai_provider_id: 新的AI提供商ID (可选)
    
    Returns:
        JSON格式的更新结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(task_id):
            return format_response(False, error="无效的任务ID格式")
        
        # 准备更新数据
        update_data = {}
        
        if name is not None:
            if not name.strip():
                return format_response(False, error="任务名称不能为空")
            update_data["name"] = name.strip()
        
        if schedule is not None:
            update_data["schedule"] = schedule.strip() if schedule.strip() else "manual"
        
        if description is not None:
            update_data["description"] = description.strip()
        
        if recipients is not None:
            recipient_list = []
            if recipients and recipients.strip():
                recipient_list = [email.strip() for email in recipients.split(",") if email.strip()]
            update_data["recipients"] = recipient_list
            
        if ai_provider_id is not None:
            if ai_provider_id and not validate_uuid(ai_provider_id):
                return format_response(False, error="无效的AI提供商ID格式")
            update_data["ai_provider_id"] = ai_provider_id
        
        if not update_data:
            return format_response(False, error="没有需要更新的字段")
        
        # 调用后端API
        response = await api_client.put(f"tasks/{task_id}", json=update_data)
        
        if response.get("success", True):
            task = response.get("data", {})
            return format_response(True, data=task, message="任务更新成功")
        else:
            return format_response(False, error=response.get("message", "更新任务失败"))
            
    except Exception as e:
        return handle_api_error(e, "更新任务")

async def run_task(task_id: str) -> str:
    """
    手动运行任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON格式的运行结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(task_id):
            return format_response(False, error="无效的任务ID格式")
        
        # 调用后端API
        response = await api_client.post(f"tasks/{task_id}/run")
        
        if response.get("success", True):
            result = response.get("data", {})
            return format_response(True, data=result, message="任务运行成功")
        else:
            return format_response(False, error=response.get("message", "运行任务失败"))
            
    except Exception as e:
        return handle_api_error(e, "运行任务")

async def enable_task(task_id: str) -> str:
    """
    启用任务 (允许定时执行)
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON格式的操作结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(task_id):
            return format_response(False, error="无效的任务ID格式")
        
        # 调用后端API
        response = await api_client.post(f"tasks/{task_id}/enable")
        
        if response.get("success", True):
            return format_response(True, message="任务已启用")
        else:
            return format_response(False, error=response.get("message", "启用任务失败"))
            
    except Exception as e:
        return handle_api_error(e, "启用任务")

async def disable_task(task_id: str) -> str:
    """
    禁用任务 (停止定时执行)
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON格式的操作结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(task_id):
            return format_response(False, error="无效的任务ID格式")
        
        # 调用后端API
        response = await api_client.post(f"tasks/{task_id}/disable")
        
        if response.get("success", True):
            return format_response(True, message="任务已禁用")
        else:
            return format_response(False, error=response.get("message", "禁用任务失败"))
            
    except Exception as e:
        return handle_api_error(e, "禁用任务")

async def delete_task(task_id: str) -> str:
    """
    删除任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON格式的删除结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(task_id):
            return format_response(False, error="无效的任务ID格式")
        
        # 调用后端API
        response = await api_client.delete(f"tasks/{task_id}")
        
        if response.get("success", True):
            return format_response(True, message="任务删除成功")
        else:
            return format_response(False, error=response.get("message", "删除任务失败"))
            
    except Exception as e:
        return handle_api_error(e, "删除任务")

async def get_task_logs(task_id: str, limit: int = 50) -> str:
    """
    获取任务执行日志
    
    Args:
        task_id: 任务ID
        limit: 返回的日志条数限制 (默认50条)
    
    Returns:
        JSON格式的日志列表
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(task_id):
            return format_response(False, error="无效的任务ID格式")
        
        # 验证limit参数
        if limit <= 0 or limit > 1000:
            limit = 50
        
        # 调用后端API
        response = await api_client.get(f"tasks/{task_id}/logs", params={"limit": limit})
        
        if response.get("success", True):
            logs = response.get("data", [])
            return format_response(True, data={
                "logs": logs,
                "total": len(logs) if isinstance(logs, list) else 0,
                "message": f"获取到 {len(logs) if isinstance(logs, list) else 0} 条执行日志"
            })
        else:
            return format_response(False, error=response.get("message", "获取任务日志失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取任务日志")

async def get_task_status(task_id: str) -> str:
    """
    获取任务当前状态和最近执行情况
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON格式的任务状态
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(task_id):
            return format_response(False, error="无效的任务ID格式")
        
        # 调用后端API
        response = await api_client.get(f"tasks/{task_id}/status")
        
        if response.get("success", True):
            status = response.get("data", {})
            return format_response(True, data=status, message="获取任务状态成功")
        else:
            return format_response(False, error=response.get("message", "获取任务状态失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取任务状态")

# 导出所有工具函数
__all__ = [
    "list_tasks",
    "create_task",
    "get_task", 
    "update_task",
    "run_task",
    "enable_task",
    "disable_task",
    "delete_task",
    "get_task_logs",
    "get_task_status"
]