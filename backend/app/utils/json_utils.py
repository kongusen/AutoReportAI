"""
JSON 序列化工具类
统一处理各种类型的 JSON 序列化问题
"""

import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


def convert_for_json(obj: Any) -> Any:
    """
    递归转换对象为 JSON 可序列化的类型

    支持的转换:
    - Decimal -> float
    - datetime/date -> ISO格式字符串
    - UUID -> 字符串
    - dict/list -> 递归转换
    - 其他类型 -> 保持原样

    Args:
        obj: 需要转换的对象

    Returns:
        JSON 可序列化的对象
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: convert_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_for_json(item) for item in obj)
    return obj


def convert_decimals(obj: Any) -> Any:
    """
    递归转换 Decimal 为 float，确保 JSON 可序列化
    
    这是 convert_for_json 的简化版本，仅处理 Decimal 类型
    保留此函数以保持向后兼容
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    return obj


logger.info("✅ JSON 序列化工具类已加载")
