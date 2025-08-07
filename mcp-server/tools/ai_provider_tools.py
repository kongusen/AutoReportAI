"""
AutoReportAI AI Provider Management Tools
AI供应商管理MCP工具
"""

import json
from typing import Dict, Any, Optional
from client import api_client
from session import session_manager
from utils.helpers import format_response, handle_api_error, validate_uuid

async def list_ai_providers() -> str:
    """
    列出当前用户的所有AI供应商
    
    Returns:
        JSON格式的AI供应商列表
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 调用后端API
        response = await api_client.get("ai-providers/")
        
        if response.get("success", True):
            providers = response.get("data", {}).get("items", [])
            return format_response(True, data={
                "ai_providers": providers,
                "total": len(providers),
                "message": f"获取到 {len(providers)} 个AI供应商"
            })
        else:
            return format_response(False, error=response.get("message", "获取AI供应商列表失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取AI供应商列表")

async def create_ai_provider(
    name: str,
    provider_type: str,
    api_key: str,
    base_url: str = None,
    model_name: str = None,
    description: str = ""
) -> str:
    """
    创建AI供应商配置
    
    Args:
        name: 供应商名称
        provider_type: 供应商类型 (openai, anthropic, azure, etc.)
        api_key: API密钥
        base_url: API基础URL (可选)
        model_name: 模型名称 (可选)
        description: 描述 (可选)
    
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
            return format_response(False, error="供应商名称不能为空")
        
        if not provider_type or not provider_type.strip():
            return format_response(False, error="供应商类型不能为空")
            
        if not api_key or not api_key.strip():
            return format_response(False, error="API密钥不能为空")
        
        # 验证供应商类型
        valid_types = ["openai", "anthropic", "azure", "google", "huggingface", "custom"]
        if provider_type.lower() not in valid_types:
            return format_response(False, error=f"不支持的供应商类型，支持的类型: {', '.join(valid_types)}")
        
        # 准备请求数据
        provider_data = {
            "provider_name": name.strip(),
            "provider_type": provider_type.lower(),
            "api_key": api_key.strip(),
            "description": description.strip() if description else "",
            "config": {}
        }
        
        # 添加可选配置
        if base_url:
            provider_data["config"]["base_url"] = base_url.strip()
        if model_name:
            provider_data["config"]["model_name"] = model_name.strip()
            
        # 根据供应商类型设置默认配置
        if provider_type.lower() == "openai":
            if not base_url:
                provider_data["config"]["base_url"] = "https://api.openai.com/v1"
            if not model_name:
                provider_data["config"]["model_name"] = "gpt-3.5-turbo"
        elif provider_type.lower() == "anthropic":
            if not base_url:
                provider_data["config"]["base_url"] = "https://api.anthropic.com"
            if not model_name:
                provider_data["config"]["model_name"] = "claude-3-sonnet-20240229"
        
        # 调用后端API
        response = await api_client.post("ai-providers/", json=provider_data)
        
        if response.get("success", True):
            provider = response.get("data", {})
            return format_response(True, data=provider, message=f"成功创建AI供应商: {name}")
        else:
            return format_response(False, error=response.get("message", "创建AI供应商失败"))
            
    except Exception as e:
        return handle_api_error(e, "创建AI供应商")

async def test_ai_provider(provider_id: str) -> str:
    """
    测试AI供应商连接
    
    Args:
        provider_id: AI供应商ID
    
    Returns:
        JSON格式的测试结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(provider_id):
            return format_response(False, error="无效的AI供应商ID格式")
        
        # 调用后端API测试连接
        response = await api_client.post(f"ai-providers/{provider_id}/test")
        
        if response.get("success", True):
            test_result = response.get("data", {})
            return format_response(True, data=test_result, message="AI供应商连接测试完成")
        else:
            return format_response(False, error=response.get("message", "AI供应商连接测试失败"))
            
    except Exception as e:
        return handle_api_error(e, "测试AI供应商连接")

async def get_ai_provider(provider_id: str) -> str:
    """
    获取AI供应商详细信息
    
    Args:
        provider_id: AI供应商ID
    
    Returns:
        JSON格式的供应商信息
    """
    try:
        # 检查用户认证  
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(provider_id):
            return format_response(False, error="无效的AI供应商ID格式")
        
        # 调用后端API
        response = await api_client.get(f"ai-providers/{provider_id}")
        
        if response.get("success", True):
            provider = response.get("data", {})
            # 隐藏敏感信息
            if "api_key" in provider:
                provider["api_key"] = "***" + provider["api_key"][-4:] if len(provider["api_key"]) > 4 else "***"
            return format_response(True, data=provider, message="获取AI供应商信息成功")
        else:
            return format_response(False, error=response.get("message", "获取AI供应商信息失败"))
            
    except Exception as e:
        return handle_api_error(e, "获取AI供应商信息")

async def update_ai_provider(
    provider_id: str,
    name: str = None,
    api_key: str = None,
    base_url: str = None,
    model_name: str = None,
    description: str = None,
    is_active: bool = None
) -> str:
    """
    更新AI供应商配置
    
    Args:
        provider_id: AI供应商ID
        name: 新的供应商名称 (可选)
        api_key: 新的API密钥 (可选)
        base_url: 新的API基础URL (可选)
        model_name: 新的模型名称 (可选)
        description: 新的描述 (可选)
        is_active: 是否激活 (可选)
    
    Returns:
        JSON格式的更新结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(provider_id):
            return format_response(False, error="无效的AI供应商ID格式")
        
        # 准备更新数据
        update_data = {}
        config_updates = {}
        
        if name is not None:
            if not name.strip():
                return format_response(False, error="供应商名称不能为空")
            update_data["provider_name"] = name.strip()
        
        if api_key is not None:
            if not api_key.strip():
                return format_response(False, error="API密钥不能为空")
            update_data["api_key"] = api_key.strip()
        
        if description is not None:
            update_data["description"] = description.strip()
            
        if is_active is not None:
            update_data["is_active"] = is_active
        
        if base_url is not None:
            config_updates["base_url"] = base_url.strip()
            
        if model_name is not None:
            config_updates["model_name"] = model_name.strip()
        
        if config_updates:
            update_data["config"] = config_updates
        
        if not update_data:
            return format_response(False, error="没有需要更新的字段")
        
        # 调用后端API
        response = await api_client.put(f"ai-providers/{provider_id}", json=update_data)
        
        if response.get("success", True):
            provider = response.get("data", {})
            return format_response(True, data=provider, message="AI供应商更新成功")
        else:
            return format_response(False, error=response.get("message", "更新AI供应商失败"))
            
    except Exception as e:
        return handle_api_error(e, "更新AI供应商")

async def delete_ai_provider(provider_id: str) -> str:
    """
    删除AI供应商
    
    Args:
        provider_id: AI供应商ID
    
    Returns:
        JSON格式的删除结果
    """
    try:
        # 检查用户认证
        current_session = session_manager.get_current_session()
        if not current_session:
            return format_response(False, error="用户未登录，请先登录")
        
        # 验证UUID格式
        if not validate_uuid(provider_id):
            return format_response(False, error="无效的AI供应商ID格式")
        
        # 调用后端API
        response = await api_client.delete(f"ai-providers/{provider_id}")
        
        if response.get("success", True):
            return format_response(True, message="AI供应商删除成功")
        else:
            return format_response(False, error=response.get("message", "删除AI供应商失败"))
            
    except Exception as e:
        return handle_api_error(e, "删除AI供应商")

# 导出所有工具函数
__all__ = [
    "list_ai_providers",
    "create_ai_provider",
    "test_ai_provider", 
    "get_ai_provider",
    "update_ai_provider",
    "delete_ai_provider"
]