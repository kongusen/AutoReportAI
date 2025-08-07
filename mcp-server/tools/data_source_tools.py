"""
Data Source Tools for AutoReportAI MCP Server
数据源管理工具
"""

import json
import os
from typing import Optional
from client import api_client, APIError
from session import session_manager

async def list_data_sources(skip: int = 0, limit: int = 100, 
                          source_type: str = None, is_active: bool = None,
                          search: str = None) -> str:
    """
    获取数据源列表
    
    Args:
        skip: 跳过的记录数
        limit: 返回的记录数 (1-100)
        source_type: 数据源类型筛选 (sql/csv/api/push)
        is_active: 是否激活状态筛选
        search: 搜索关键词
    
    Returns:
        数据源列表的JSON格式
    """
    try:
        # 检查登录状态
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        # 构建查询参数
        params = {"skip": skip, "limit": min(limit, 100)}
        if source_type:
            params["source_type"] = source_type
        if is_active is not None:
            params["is_active"] = is_active
        if search:
            params["search"] = search
        
        result = await api_client.get("data-sources", params=params)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"获取数据源列表失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取数据源列表异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def find_data_source(identifier: str) -> str:
    """
    智能查找数据源，支持多种标识符格式
    
    Args:
        identifier: 数据源标识符 (UUID/slug/name/display_name)
    
    Returns:
        数据源信息的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        # 获取数据源列表
        result = await api_client.get("data-sources", params={"limit": 1000})
        
        if not result.get("success"):
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        # 在本地查找匹配的数据源
        items = result.get("data", {}).get("items", [])
        
        # 尝试多种匹配方式
        matches = []
        
        for item in items:
            # 精确匹配
            if (str(item.get("id")) == identifier or
                item.get("slug") == identifier or
                item.get("name") == identifier or
                item.get("display_name") == identifier):
                matches.append(("exact", item))
            
            # 模糊匹配
            elif (identifier.lower() in item.get("name", "").lower() or
                  identifier.lower() in item.get("display_name", "").lower()):
                matches.append(("fuzzy", item))
        
        if not matches:
            return json.dumps({
                "success": False,
                "error": f"未找到匹配的数据源: {identifier}",
                "suggestion": "请检查数据源名称或使用 mcp_list_data_sources 查看所有数据源"
            }, ensure_ascii=False, indent=2)
        
        # 优先返回精确匹配
        exact_matches = [item for match_type, item in matches if match_type == "exact"]
        if exact_matches:
            return json.dumps({
                "success": True,
                "data": exact_matches[0],
                "match_type": "exact"
            }, ensure_ascii=False, indent=2)
        
        # 返回模糊匹配结果
        fuzzy_matches = [item for match_type, item in matches if match_type == "fuzzy"]
        return json.dumps({
            "success": True,
            "data": fuzzy_matches,
            "match_type": "fuzzy",
            "message": f"找到 {len(fuzzy_matches)} 个模糊匹配结果"
        }, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"查找数据源失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"查找数据源异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def create_sql_data_source(name: str, connection_string: str, 
                               description: str = "", sql_query_type: str = "single_table",
                               base_query: str = None) -> str:
    """
    创建SQL数据库数据源
    
    Args:
        name: 数据源名称
        connection_string: 数据库连接字符串
        description: 描述信息
        sql_query_type: SQL查询类型 (single_table/multi_table/custom_view)
        base_query: 基础查询SQL
    
    Returns:
        创建结果的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        data = {
            "name": name,
            "source_type": "sql",
            "connection_string": connection_string,
            "description": description,
            "sql_query_type": sql_query_type,
            "is_active": True
        }
        
        if base_query:
            data["base_query"] = base_query
        
        result = await api_client.post("data-sources", json=data)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"创建SQL数据源失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"创建SQL数据源异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def create_doris_data_source(
    name: str, 
    host: str, 
    port: int = 9030,
    username: str = "root", 
    password: str = "", 
    database: str = "doris",
    fe_hosts: str = None,
    be_hosts: str = None,
    http_port: int = 8030,
    description: str = "",
    slug: str = None,
    display_name: str = None
) -> str:
    """
    创建Apache Doris数据源
    
    Args:
        name: 数据源名称
        host: Doris主机地址
        port: 查询端口 (默认9030)
        username: 用户名 (默认root)
        password: 密码
        database: 数据库名 (默认doris)
        fe_hosts: FE节点列表 (JSON字符串，如 ["host1", "host2"])
        be_hosts: BE节点列表 (JSON字符串，如 ["host1", "host2"])
        http_port: HTTP端口 (默认8030)
        description: 描述信息
    
    Returns:
        创建结果的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        # 解析主机列表
        fe_host_list = [host]  # 默认使用主机地址
        be_host_list = [host]
        
        if fe_hosts:
            try:
                fe_host_list = json.loads(fe_hosts) if isinstance(fe_hosts, str) else fe_hosts
            except json.JSONDecodeError:
                return json.dumps({
                    "success": False,
                    "error": "fe_hosts必须是有效的JSON数组格式，如 [\"host1\", \"host2\"]"
                }, ensure_ascii=False, indent=2)
        
        if be_hosts:
            try:
                be_host_list = json.loads(be_hosts) if isinstance(be_hosts, str) else be_hosts
            except json.JSONDecodeError:
                return json.dumps({
                    "success": False,
                    "error": "be_hosts必须是有效的JSON数组格式，如 [\"host1\", \"host2\"]"
                }, ensure_ascii=False, indent=2)
        
        # 构建Doris连接数据
        data = {
            "name": name,
            "source_type": "doris",
            "description": description,
            "is_active": True,
            # 用户友好ID
            "slug": slug,
            "display_name": display_name or name,
            # Doris特定配置
            "doris_fe_hosts": fe_host_list,
            "doris_be_hosts": be_host_list,
            "doris_http_port": http_port,
            "doris_query_port": port,
            "doris_database": database,
            "doris_username": username,
            "doris_password": password
        }
        
        result = await api_client.post("data-sources", json=data)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"创建Doris数据源失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"创建Doris数据源异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def create_api_data_source(name: str, api_url: str, api_method: str = "GET",
                               api_headers: str = "{}", api_body: str = None,
                               description: str = "") -> str:
    """
    创建API数据源
    
    Args:
        name: 数据源名称
        api_url: API URL地址
        api_method: HTTP方法 (GET/POST)
        api_headers: 请求头JSON字符串
        api_body: 请求体JSON字符串（POST时使用）
        description: 描述信息
    
    Returns:
        创建结果的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"  
            }, ensure_ascii=False, indent=2)
        
        # 解析JSON字符串
        try:
            headers = json.loads(api_headers) if api_headers else {}
        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": "api_headers必须是有效的JSON格式"
            }, ensure_ascii=False, indent=2)
        
        body = None
        if api_body:
            try:
                body = json.loads(api_body)
            except json.JSONDecodeError:
                return json.dumps({
                    "success": False,
                    "error": "api_body必须是有效的JSON格式"
                }, ensure_ascii=False, indent=2)
        
        data = {
            "name": name,
            "source_type": "api",
            "api_url": api_url,
            "api_method": api_method.upper(),
            "api_headers": headers,
            "description": description,
            "is_active": True
        }
        
        if body:
            data["api_body"] = body
        
        result = await api_client.post("data-sources", json=data)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"创建API数据源失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"创建API数据源异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def upload_csv_data_source(name: str, file_path: str, description: str = "") -> str:
    """
    创建CSV文件数据源并上传文件（使用优化的两步法）
    
    Args:
        name: 数据源名称
        file_path: CSV文件绝对路径
        description: 描述信息
    
    Returns:
        上传结果的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        # 验证文件存在
        if not os.path.exists(file_path):
            return json.dumps({
                "success": False,
                "error": f"文件不存在: {file_path}"
            }, ensure_ascii=False, indent=2)
        
        # 第一步：创建数据源记录
        create_data = {
            "name": name,
            "source_type": "csv",
            "description": description,
            "connection_string": "",  # 临时空值，上传后会更新
            "is_active": True
        }
        
        create_result = await api_client.post("data-sources", json=create_data)
        
        if not create_result.get("success", True):
            return json.dumps(create_result, ensure_ascii=False, indent=2)
        
        # 获取数据源ID
        data_source_id = create_result.get("data", {}).get("id")
        if not data_source_id:
            return json.dumps({
                "success": False,
                "error": "无法获取创建的数据源ID"
            }, ensure_ascii=False, indent=2)
        
        # 第二步：上传文件
        upload_result = await api_client.upload_file(
            f"data-sources/{data_source_id}/upload",
            file_path
        )
        
        return json.dumps(upload_result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"上传CSV数据源失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"上传CSV数据源异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def test_data_source(data_source_id: str) -> str:
    """
    测试数据源连接
    
    Args:
        data_source_id: 数据源ID
    
    Returns:
        测试结果的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        result = await api_client.post(f"data-sources/{data_source_id}/test")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"测试数据源连接失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"测试数据源连接异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def sync_data_source(data_source_id: str) -> str:
    """
    同步数据源数据
    
    Args:
        data_source_id: 数据源ID (支持UUID/slug/name/display_name)
    
    Returns:
        同步结果的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        # URL编码数据源ID以处理特殊字符
        import urllib.parse
        encoded_id = urllib.parse.quote(str(data_source_id), safe='')
        result = await api_client.post(f"data-sources/{encoded_id}/sync")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"同步数据源失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"同步数据源异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def get_data_source_preview(data_source_id: str, limit: int = 10) -> str:
    """
    获取数据源数据预览
    
    Args:
        data_source_id: 数据源ID (支持UUID/slug/name/display_name)
        limit: 预览行数限制
    
    Returns:
        数据预览的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        # URL编码数据源ID以处理特殊字符
        import urllib.parse
        encoded_id = urllib.parse.quote(str(data_source_id), safe='')
        result = await api_client.get(
            f"data-sources/{encoded_id}/wide-table",
            params={"limit": limit}
        )
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"获取数据预览失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取数据预览异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def update_data_source(data_source_id: str, name: str = None, 
                           description: str = None, connection_string: str = None,
                           is_active: bool = None, **kwargs) -> str:
    """
    更新数据源信息
    
    Args:
        data_source_id: 数据源ID
        name: 新的数据源名称
        description: 新的描述信息
        connection_string: 新的连接字符串
        is_active: 是否激活
        **kwargs: 其他更新字段
    
    Returns:
        更新结果的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        # 构建更新数据
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if connection_string is not None:
            update_data["connection_string"] = connection_string
        if is_active is not None:
            update_data["is_active"] = is_active
        
        # 添加其他字段
        update_data.update(kwargs)
        
        if not update_data:
            return json.dumps({
                "success": False,
                "error": "没有提供需要更新的字段"
            }, ensure_ascii=False, indent=2)
        
        result = await api_client.put(f"data-sources/{data_source_id}", json=update_data)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"更新数据源失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"更新数据源异常: {str(e)}"
        }, ensure_ascii=False, indent=2)

async def delete_data_source(data_source_id: str) -> str:
    """
    删除数据源
    
    Args:
        data_source_id: 数据源ID
    
    Returns:
        删除结果的JSON格式
    """
    try:
        session = session_manager.get_current_session()
        if not session:
            return json.dumps({
                "success": False,
                "error": "未登录或会话已过期"
            }, ensure_ascii=False, indent=2)
        
        result = await api_client.delete(f"data-sources/{data_source_id}")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except APIError as e:
        return json.dumps({
            "success": False,
            "error": f"删除数据源失败: {e.message}",
            "status_code": e.status_code
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"删除数据源异常: {str(e)}"
        }, ensure_ascii=False, indent=2)