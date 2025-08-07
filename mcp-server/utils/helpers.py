"""
Helper functions for AutoReportAI MCP Server
辅助工具函数
"""

import json
import os
import re
import uuid
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union

def format_response(success: bool = True, data: Any = None, message: str = "", 
                   error: str = "", **kwargs) -> str:
    """
    格式化标准响应
    
    Args:
        success: 是否成功
        data: 响应数据
        message: 成功消息
        error: 错误消息
        **kwargs: 其他字段
    
    Returns:
        JSON格式的响应字符串
    """
    response = {
        "success": success,
        **kwargs
    }
    
    if data is not None:
        response["data"] = data
    
    if message:
        response["message"] = message
    
    if error:
        response["error"] = error
    
    return json.dumps(response, ensure_ascii=False, indent=2)

def format_error(error_message: str, status_code: int = None, **kwargs) -> str:
    """
    格式化错误响应
    
    Args:
        error_message: 错误消息
        status_code: HTTP状态码
        **kwargs: 其他字段
    
    Returns:
        JSON格式的错误响应
    """
    response = {
        "success": False,
        "error": error_message,
        **kwargs
    }
    
    if status_code:
        response["status_code"] = status_code
    
    return json.dumps(response, ensure_ascii=False, indent=2)

def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """
    安全的JSON解析
    
    Args:
        json_string: JSON字符串
        default: 解析失败时的默认值
    
    Returns:
        解析结果或默认值
    """
    if not json_string:
        return default
    
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default

def format_datetime(dt: datetime = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化日期时间
    
    Args:
        dt: 日期时间对象，为空时使用当前时间
        format_str: 格式字符串
    
    Returns:
        格式化的日期时间字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_str)

def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        清理后的文件名
    """
    if not filename:
        return "unnamed"
    
    # 移除路径分隔符和其他不安全字符
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # 移除控制字符
    cleaned = re.sub(r'[\x00-\x1f\x7f]', '', cleaned)
    
    # 限制长度
    if len(cleaned) > 255:
        name, ext = os.path.splitext(cleaned)
        cleaned = name[:255-len(ext)] + ext
    
    return cleaned or "unnamed"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
    
    Returns:
        截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def extract_error_message(error_data: Union[str, Dict, Exception]) -> str:
    """
    从各种错误源提取错误消息
    
    Args:
        error_data: 错误数据
    
    Returns:
        错误消息字符串
    """
    if isinstance(error_data, str):
        return error_data
    
    if isinstance(error_data, Exception):
        return str(error_data)
    
    if isinstance(error_data, dict):
        # 尝试从常见字段提取错误消息
        for field in ["detail", "message", "error", "msg"]:
            if field in error_data:
                return str(error_data[field])
        return str(error_data)
    
    return str(error_data)

def build_query_params(**kwargs) -> Dict[str, Any]:
    """
    构建查询参数，过滤空值
    
    Args:
        **kwargs: 参数键值对
    
    Returns:
        过滤后的参数字典
    """
    return {k: v for k, v in kwargs.items() if v is not None}

def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个配置字典
    
    Args:
        *configs: 配置字典列表
    
    Returns:
        合并后的配置字典
    """
    result = {}
    for config in configs:
        if isinstance(config, dict):
            result.update(config)
    return result

def parse_cron_expression(cron_expr: str) -> Dict[str, str]:
    """
    解析Cron表达式
    
    Args:
        cron_expr: Cron表达式字符串
    
    Returns:
        解析结果字典
    """
    if not cron_expr:
        return {"valid": False, "error": "空的Cron表达式"}
    
    parts = cron_expr.strip().split()
    
    if len(parts) != 5:
        return {"valid": False, "error": "Cron表达式必须包含5个字段"}
    
    field_names = ["分钟", "小时", "日期", "月份", "星期"]
    field_ranges = [
        (0, 59),   # 分钟
        (0, 23),   # 小时
        (1, 31),   # 日期
        (1, 12),   # 月份
        (0, 7)     # 星期 (0和7都表示星期日)
    ]
    
    parsed = {
        "valid": True,
        "fields": {},
        "description": []
    }
    
    for i, (part, name, (min_val, max_val)) in enumerate(zip(parts, field_names, field_ranges)):
        parsed["fields"][name] = part
        
        if part == "*":
            parsed["description"].append(f"每{name}")
        elif "/" in part:
            base, interval = part.split("/", 1)
            if base == "*":
                parsed["description"].append(f"每{interval}{name}")
            else:
                parsed["description"].append(f"从{base}开始每{interval}{name}")
        elif "-" in part:
            start, end = part.split("-", 1)
            parsed["description"].append(f"{name}{start}到{end}")
        elif "," in part:
            values = part.split(",")
            parsed["description"].append(f"{name}在{','.join(values)}")
        else:
            parsed["description"].append(f"{name}为{part}")
    
    parsed["description"] = "，".join(parsed["description"])
    
    return parsed

def validate_uuid(uuid_string: str) -> bool:
    """
    验证UUID格式
    
    Args:
        uuid_string: UUID字符串
    
    Returns:
        是否为有效的UUID格式
    """
    if not isinstance(uuid_string, str):
        return False
    
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False

def handle_api_error(error: Exception, operation: str = "操作") -> str:
    """
    处理API错误并格式化响应
    
    Args:
        error: 异常对象
        operation: 操作描述
    
    Returns:
        格式化的错误响应
    """
    error_message = extract_error_message(error)
    
    # 记录详细错误信息（可选）
    try:
        error_details = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": error_message,
            "traceback": traceback.format_exc()
        }
        # 这里可以添加日志记录逻辑
        print(f"[ERROR] {operation}失败: {error_message}")
    except:
        pass
    
    return format_response(
        success=False,
        error=f"{operation}失败: {error_message}"
    )