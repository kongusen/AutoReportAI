"""
AutoReportAI Template Management Tools
模板管理MCP工具

提供模板的创建、上传、列出、更新、删除等完整生命周期管理功能
"""

import json
import os
from typing import Dict, Any, Optional
from client import api_client
from session import session_manager
from utils.helpers import format_response, handle_api_error, validate_uuid

async def list_templates() -> str:
    """
    列出当前用户的所有模板
    
    Returns:
        JSON格式的模板列表
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 调用后端API
        response = await api_client.get("templates/")
        
        if response.get("success", True):
            templates = response.get("data", [])
            return format_response(True, data={
                "templates": templates,
                "total": len(templates) if isinstance(templates, list) else 0,
                "message": f"获取到 {len(templates) if isinstance(templates, list) else 0} 个模板"
            })
        else:
            return format_response(False, error=response.get("message", "获取模板列表失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取模板列表")

async def create_text_template(name: str, content: str, description: str = "") -> str:
    """
    创建文本模板
    
    Args:
        name: 模板名称
        content: 模板内容 (支持变量占位符，如 {{variable_name}})
        description: 模板描述 (可选)
    
    Returns:
        JSON格式的创建结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证参数
        if not name or not name.strip():
            return format_response(False, error="模板名称不能为空")
        
        if not content or not content.strip():
            return format_response(False, error="模板内容不能为空")
        
        # 准备请求数据
        template_data = {
            "name": name.strip(),
            "content": content,
            "description": description.strip() if description else "",
            "template_type": "text"
        }
        
        # 调用后端API
        response = await api_client.post("templates/", json=template_data)
        
        if response.get("success", True):
            template = response.get("data", {})
            return format_response(True, data=template, message=f"成功创建文本模板: {name}")
        else:
            return format_response(False, error=response.get("message", "创建模板失败"))
            
    except Exception as e:
        return handle_api_error(e, "创建文本模板")

async def upload_template_file(name: str, file_path: str, description: str = "") -> str:
    """
    上传模板文件
    
    Args:
        name: 模板名称
        file_path: 本地文件路径
        description: 模板描述 (可选)
    
    Returns:
        JSON格式的上传结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证参数
        if not name or not name.strip():
            return format_response(False, error="模板名称不能为空")
        
        if not file_path or not os.path.exists(file_path):
            return format_response(False, error=f"文件不存在: {file_path}")
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            return format_response(False, error=f"文件大小超过限制 ({max_size//1024//1024}MB)")
        
        # 检查文件类型
        allowed_extensions = ['.docx', '.doc', '.html', '.htm', '.pdf', '.txt']
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in allowed_extensions:
            return format_response(False, error=f"不支持的文件类型: {file_ext}")
        
        # 步骤1: 创建模板记录
        template_data = {
            "name": name.strip(),
            "description": description.strip() if description else "",
            "template_type": "file",
            "file_name": os.path.basename(file_path)
        }
        
        create_response = await api_client.post("templates/", json=template_data)
        
        if not create_response.get("success", True):
            return format_response(False, error=create_response.get("message", "创建模板记录失败"))
        
        template_id = create_response.get("data", {}).get("id")
        if not template_id:
            return format_response(False, error="创建模板记录成功但未返回模板ID")
        
        # 步骤2: 上传文件
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                upload_response = await api_client.put(f"templates/{template_id}/upload", files=files)
            
            if upload_response.get("success", True):
                return format_response(True, data=upload_response.get("data", {}), 
                                     message=f"成功上传模板文件: {name}")
            else:
                # 上传失败，尝试删除已创建的模板记录
                try:
                    await api_client.delete(f"templates/{template_id}")
                except:
                    pass
                return format_response(False, error=upload_response.get("message", "上传文件失败"))
                
        except Exception as upload_error:
            # 上传失败，尝试删除已创建的模板记录
            try:
                await api_client.delete(f"templates/{template_id}")
            except:
                pass
            raise upload_error
            
    except Exception as e:
        return handle_api_error(e, "上传模板文件")

async def get_template(template_id: str) -> str:
    """
    获取指定模板的详细信息
    
    Args:
        template_id: 模板ID
    
    Returns:
        JSON格式的模板信息
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(template_id):
            return format_response(False, error="无效的模板ID格式")
        
        # 调用后端API
        response = await api_client.get(f"templates/{template_id}")
        
        if response.get("success", True):
            template = response.get("data", {})
            return format_response(True, data=template, message="获取模板信息成功")
        else:
            return format_response(False, error=response.get("message", "获取模板信息失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取模板信息")

async def update_template(template_id: str, name: str = None, content: str = None, description: str = None) -> str:
    """
    更新模板信息
    
    Args:
        template_id: 模板ID
        name: 新的模板名称 (可选)
        content: 新的模板内容 (可选，仅文本模板)
        description: 新的模板描述 (可选)
    
    Returns:
        JSON格式的更新结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(template_id):
            return format_response(False, error="无效的模板ID格式")
        
        # 准备更新数据
        update_data = {}
        if name is not None:
            if not name.strip():
                return format_response(False, error="模板名称不能为空")
            update_data["name"] = name.strip()
        
        if content is not None:
            if not content.strip():
                return format_response(False, error="模板内容不能为空")
            update_data["content"] = content
        
        if description is not None:
            update_data["description"] = description.strip()
        
        if not update_data:
            return format_response(False, error="没有需要更新的字段")
        
        # 调用后端API
        response = await api_client.put(f"templates/{template_id}", json=update_data)
        
        if response.get("success", True):
            template = response.get("data", {})
            return format_response(True, data=template, message="模板更新成功")
        else:
            return format_response(False, error=response.get("message", "更新模板失败"))
            
    except Exception as e:
        return handle_api_error(e, "更新模板")

async def delete_template(template_id: str) -> str:
    """
    删除模板
    
    Args:
        template_id: 模板ID
    
    Returns:
        JSON格式的删除结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(template_id):
            return format_response(False, error="无效的模板ID格式")
        
        # 调用后端API
        response = await api_client.delete(f"templates/{template_id}")
        
        if response.get("success", True):
            return format_response(True, message="模板删除成功")
        else:
            return format_response(False, error=response.get("message", "删除模板失败"))
            
    except Exception as e:
        return handle_api_error(e, "删除模板")

async def duplicate_template(template_id: str, new_name: str) -> str:
    """
    复制模板
    
    Args:
        template_id: 源模板ID
        new_name: 新模板名称
    
    Returns:
        JSON格式的复制结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证参数
        if not validate_uuid(template_id):
            return format_response(False, error="无效的模板ID格式")
        
        if not new_name or not new_name.strip():
            return format_response(False, error="新模板名称不能为空")
        
        # 调用后端API
        response = await api_client.post(f"templates/{template_id}/duplicate", json={"name": new_name.strip()})
        
        if response.get("success", True):
            new_template = response.get("data", {})
            return format_response(True, data=new_template, message=f"成功复制模板: {new_name}")
        else:
            return format_response(False, error=response.get("message", "复制模板失败"))
            
    except Exception as e:
        return handle_api_error(e, "复制模板")

async def preview_template(template_id: str, sample_data: str = "{}") -> str:
    """
    预览模板效果 (使用示例数据渲染模板)
    
    Args:
        template_id: 模板ID
        sample_data: 示例数据 (JSON格式字符串)
    
    Returns:
        JSON格式的预览结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(template_id):
            return format_response(False, error="无效的模板ID格式")
        
        # 验证示例数据格式
        try:
            sample_data_dict = json.loads(sample_data)
        except json.JSONDecodeError:
            return format_response(False, error="示例数据必须是有效的JSON格式")
        
        # 调用后端API
        response = await api_client.post(f"templates/{template_id}/preview", json={"data": sample_data_dict})
        
        if response.get("success", True):
            preview_result = response.get("data", {})
            return format_response(True, data=preview_result, message="模板预览生成成功")
        else:
            return format_response(False, error=response.get("message", "模板预览失败"))
            
    except Exception as e:
        return handle_api_error(e, "预览模板")

# 导出所有工具函数
__all__ = [
    "list_templates",
    "create_text_template", 
    "upload_template_file",
    "get_template",
    "update_template",
    "delete_template",
    "duplicate_template",
    "preview_template"
]