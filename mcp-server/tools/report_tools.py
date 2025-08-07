"""
AutoReportAI Report Generation Tools
报告生成MCP工具

提供报告的生成、查看、下载、删除等完整生命周期管理功能
支持多种输出格式和批量处理
"""

import json
import os
from typing import Dict, Any, Optional
from client import api_client
from session import session_manager
from utils.helpers import format_response, handle_api_error, validate_uuid

async def generate_report(
    template_id: str,
    data_source_id: str,
    ai_provider_id: str = None,
    output_format: str = "html",
    name: str = None,
    description: str = ""
) -> str:
    """
    生成报告
    
    Args:
        template_id: 模板ID
        data_source_id: 数据源ID
        ai_provider_id: AI提供商ID (可选，使用默认配置)
        output_format: 输出格式 (html, pdf, docx, 默认html)
        name: 报告名称 (可选，自动生成)
        description: 报告描述 (可选)
    
    Returns:
        JSON格式的生成结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证必需参数
        if not validate_uuid(template_id):
            return format_response(False, error="无效的模板ID格式")
        
        if not validate_uuid(data_source_id):
            return format_response(False, error="无效的数据源ID格式")
        
        if ai_provider_id and not validate_uuid(ai_provider_id):
            return format_response(False, error="无效的AI提供商ID格式")
        
        # 验证输出格式
        valid_formats = ["html", "pdf", "docx", "txt"]
        if output_format not in valid_formats:
            return format_response(False, error=f"不支持的输出格式，支持的格式: {', '.join(valid_formats)}")
        
        # 准备请求数据
        report_data = {
            "template_id": template_id,
            "data_source_id": data_source_id,
            "output_format": output_format.lower(),
            "description": description.strip() if description else ""
        }
        
        if ai_provider_id:
            report_data["ai_provider_id"] = ai_provider_id
        
        if name and name.strip():
            report_data["name"] = name.strip()
        
        # 调用后端API
        response = await api_client.post("reports/generate", json=report_data)
        
        if response.get("success", True):
            report = response.get("data", {})
            return format_response(True, data=report, message="报告生成成功")
        else:
            return format_response(False, error=response.get("message", "生成报告失败"))
            
    except Exception as e:
        return handle_api_error(e, "生成报告")

async def list_reports(limit: int = 50, offset: int = 0, status: str = None) -> str:
    """
    列出报告历史
    
    Args:
        limit: 返回的报告数量限制 (默认50)
        offset: 偏移量 (默认0)
        status: 状态筛选 (pending, generating, completed, failed, 默认全部)
    
    Returns:
        JSON格式的报告列表
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证参数
        if limit <= 0 or limit > 1000:
            limit = 50
        
        if offset < 0:
            offset = 0
        
        # 准备查询参数
        params = {"limit": limit, "offset": offset}
        if status and status in ["pending", "generating", "completed", "failed"]:
            params["status"] = status
        
        # 调用后端API
        response = await api_client.get("reports/", params=params)
        
        if response.get("success", True):
            data = response.get("data", {})
            reports = data.get("reports", []) if isinstance(data, dict) else data
            total = data.get("total", len(reports)) if isinstance(data, dict) else len(reports)
            
            return format_response(True, data={
                "reports": reports,
                "total": total,
                "limit": limit,
                "offset": offset,
                "message": f"获取到 {len(reports)} 个报告 (共 {total} 个)"
            })
        else:
            return format_response(False, error=response.get("message", "获取报告列表失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取报告列表")

async def get_report(report_id: str) -> str:
    """
    获取指定报告的详细信息
    
    Args:
        report_id: 报告ID
    
    Returns:
        JSON格式的报告信息
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(report_id):
            return format_response(False, error="无效的报告ID格式")
        
        # 调用后端API
        response = await api_client.get(f"reports/{report_id}")
        
        if response.get("success", True):
            report = response.get("data", {})
            return format_response(True, data=report, message="获取报告信息成功")
        else:
            return format_response(False, error=response.get("message", "获取报告信息失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取报告信息")

async def download_report(report_id: str, save_path: str = None) -> str:
    """
    下载报告文件
    
    Args:
        report_id: 报告ID
        save_path: 保存路径 (可选，默认当前目录)
    
    Returns:
        JSON格式的下载结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(report_id):
            return format_response(False, error="无效的报告ID格式")
        
        # 获取报告信息
        report_response = await api_client.get(f"reports/{report_id}")
        if not report_response.get("success", True):
            return format_response(False, error="获取报告信息失败")
        
        report_info = report_response.get("data", {})
        if report_info.get("status") != "completed":
            return format_response(False, error=f"报告状态为 {report_info.get('status', 'unknown')}，无法下载")
        
        # 确定保存文件名和路径
        filename = report_info.get("filename", f"report_{report_id}.html")
        if save_path:
            if os.path.isdir(save_path):
                file_path = os.path.join(save_path, filename)
            else:
                file_path = save_path
        else:
            file_path = filename
        
        # 下载文件
        download_response = await api_client.get(f"reports/{report_id}/download", stream=True)
        
        if isinstance(download_response, bytes):
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(download_response)
            
            return format_response(True, data={
                "file_path": os.path.abspath(file_path),
                "filename": filename,
                "size": len(download_response)
            }, message=f"报告下载成功: {file_path}")
        else:
            return format_response(False, error="下载报告失败")
            
    except Exception as e:
        return handle_api_error(e, "下载报告")

async def regenerate_report(report_id: str, ai_provider_id: str = None) -> str:
    """
    重新生成报告
    
    Args:
        report_id: 报告ID
        ai_provider_id: 新的AI提供商ID (可选)
    
    Returns:
        JSON格式的重新生成结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(report_id):
            return format_response(False, error="无效的报告ID格式")
        
        if ai_provider_id and not validate_uuid(ai_provider_id):
            return format_response(False, error="无效的AI提供商ID格式")
        
        # 准备请求数据
        regenerate_data = {}
        if ai_provider_id:
            regenerate_data["ai_provider_id"] = ai_provider_id
        
        # 调用后端API
        response = await api_client.post(f"reports/{report_id}/regenerate", json=regenerate_data)
        
        if response.get("success", True):
            report = response.get("data", {})
            return format_response(True, data=report, message="报告重新生成成功")
        else:
            return format_response(False, error=response.get("message", "重新生成报告失败"))
            
    except Exception as e:
        return handle_api_error(e, "重新生成报告")

async def delete_report(report_id: str) -> str:
    """
    删除报告
    
    Args:
        report_id: 报告ID
    
    Returns:
        JSON格式的删除结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(report_id):
            return format_response(False, error="无效的报告ID格式")
        
        # 调用后端API
        response = await api_client.delete(f"reports/{report_id}")
        
        if response.get("success", True):
            return format_response(True, message="报告删除成功")
        else:
            return format_response(False, error=response.get("message", "删除报告失败"))
            
    except Exception as e:
        return handle_api_error(e, "删除报告")

async def get_report_content(report_id: str) -> str:
    """
    获取报告内容 (适用于文本格式报告)
    
    Args:
        report_id: 报告ID
    
    Returns:
        JSON格式的报告内容
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(report_id):
            return format_response(False, error="无效的报告ID格式")
        
        # 调用后端API
        response = await api_client.get(f"reports/{report_id}/content")
        
        if response.get("success", True):
            content = response.get("data", {})
            return format_response(True, data=content, message="获取报告内容成功")
        else:
            return format_response(False, error=response.get("message", "获取报告内容失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取报告内容")

async def batch_generate_reports(
    template_id: str,
    data_source_ids: str,
    ai_provider_id: str = None,
    output_format: str = "html"
) -> str:
    """
    批量生成报告
    
    Args:
        template_id: 模板ID
        data_source_ids: 数据源ID列表，逗号分隔
        ai_provider_id: AI提供商ID (可选)
        output_format: 输出格式 (html, pdf, docx, 默认html)
    
    Returns:
        JSON格式的批量生成结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证模板ID
        if not validate_uuid(template_id):
            return format_response(False, error="无效的模板ID格式")
        
        # 解析数据源ID列表
        ds_id_list = []
        for ds_id in data_source_ids.split(","):
            ds_id = ds_id.strip()
            if not validate_uuid(ds_id):
                return format_response(False, error=f"无效的数据源ID格式: {ds_id}")
            ds_id_list.append(ds_id)
        
        if not ds_id_list:
            return format_response(False, error="至少需要提供一个数据源ID")
        
        if ai_provider_id and not validate_uuid(ai_provider_id):
            return format_response(False, error="无效的AI提供商ID格式")
        
        # 验证输出格式
        valid_formats = ["html", "pdf", "docx", "txt"]
        if output_format not in valid_formats:
            return format_response(False, error=f"不支持的输出格式，支持的格式: {', '.join(valid_formats)}")
        
        # 准备请求数据
        batch_data = {
            "template_id": template_id,
            "data_source_ids": ds_id_list,
            "output_format": output_format.lower()
        }
        
        if ai_provider_id:
            batch_data["ai_provider_id"] = ai_provider_id
        
        # 调用后端API
        response = await api_client.post("reports/batch-generate", json=batch_data)
        
        if response.get("success", True):
            result = response.get("data", {})
            return format_response(True, data=result, message=f"成功启动批量生成任务，处理 {len(ds_id_list)} 个数据源")
        else:
            return format_response(False, error=response.get("message", "批量生成报告失败"))
            
    except Exception as e:
        return handle_api_error(e, "批量生成报告")

# 导出所有工具函数
__all__ = [
    "generate_report",
    "list_reports",
    "get_report",
    "download_report",
    "regenerate_report",
    "delete_report",
    "get_report_content",
    "batch_generate_reports"
]