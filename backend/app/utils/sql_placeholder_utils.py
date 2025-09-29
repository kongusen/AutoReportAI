"""
SQL占位符替换工具类
统一处理所有SQL中的时间占位符替换，摒弃复杂的SQL表达式替换逻辑
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SqlPlaceholderReplacer:
    """
    SQL占位符替换工具类

    统一处理SQL中的占位符替换，特别是时间相关的占位符。
    使用简单直接的字符串替换方式，与占位符验证逻辑保持一致。
    """

    # 支持的时间占位符
    TIME_PLACEHOLDERS = {
        'start_date': 'data_start_time',      # {{start_date}} -> time_context['data_start_time']
        'end_date': 'data_end_time',          # {{end_date}} -> time_context['data_end_time']
        'execution_date': 'execution_time',   # {{execution_date}} -> time_context['execution_time']
        'current_date': 'execution_time',     # {{current_date}} -> time_context['execution_time']
    }

    @classmethod
    def replace_time_placeholders(cls, sql: str, time_context: Dict[str, Any]) -> str:
        """
        替换SQL中的时间占位符

        Args:
            sql: 包含占位符的SQL，如: "WHERE dt BETWEEN {{start_date}} AND {{end_date}}"
            time_context: 时间上下文字典，包含实际的时间值

        Returns:
            替换后的SQL，如: "WHERE dt BETWEEN '2025-09-27' AND '2025-09-27'"
        """
        if not sql or not time_context:
            logger.warning("SQL或时间上下文为空，跳过占位符替换")
            return sql

        original_sql = sql
        replacements = []

        # 替换时间占位符
        for placeholder, context_key in cls.TIME_PLACEHOLDERS.items():
            placeholder_pattern = f"{{{{{placeholder}}}}}"

            if placeholder_pattern in sql:
                # 获取时间值，支持多种格式的键名
                time_value = cls._get_time_value(time_context, context_key, placeholder)

                if time_value:
                    # 确保时间值是日期格式 (YYYY-MM-DD)
                    formatted_time = cls._format_time_value(time_value)
                    sql = sql.replace(placeholder_pattern, f"'{formatted_time}'")
                    replacements.append(f"{{{{placeholder}}}} -> '{formatted_time}'")
                else:
                    logger.warning(f"时间上下文中缺少 {context_key} 或 {placeholder}，跳过占位符 {placeholder_pattern}")

        # 记录替换结果
        if replacements:
            logger.info(f"SQL占位符替换完成: {', '.join(replacements)}")
            logger.debug(f"原始SQL: {original_sql}")
            logger.debug(f"替换后SQL: {sql}")

        return sql

    @classmethod
    def _get_time_value(cls, time_context: Dict[str, Any], primary_key: str, fallback_key: str) -> Optional[str]:
        """
        从时间上下文中获取时间值，支持多种键名格式
        """
        # 尝试主键名
        value = time_context.get(primary_key)
        if value:
            return str(value)

        # 尝试备用键名
        value = time_context.get(fallback_key)
        if value:
            return str(value)

        # 尝试其他可能的键名变体
        fallback_keys = [
            f"period_{primary_key}",
            f"{primary_key}_date",
            primary_key.replace('_time', '_date'),
            primary_key.replace('data_', 'period_')
        ]

        for key in fallback_keys:
            value = time_context.get(key)
            if value:
                return str(value)

        return None

    @classmethod
    def _format_time_value(cls, time_value: str) -> str:
        """
        格式化时间值为标准的日期格式 (YYYY-MM-DD)
        """
        if not time_value:
            return time_value

        # 如果已经是日期格式，直接返回
        if re.match(r'^\d{4}-\d{2}-\d{2}$', time_value):
            return time_value

        # 如果是datetime格式，提取日期部分
        if 'T' in time_value:
            return time_value.split('T')[0]

        # 如果包含时间部分，提取日期部分
        if ' ' in time_value:
            return time_value.split(' ')[0]

        return time_value

    @classmethod
    def extract_placeholders(cls, sql: str) -> List[str]:
        """
        提取SQL中的所有占位符

        Args:
            sql: SQL字符串

        Returns:
            占位符列表，如: ['start_date', 'end_date']
        """
        if not sql:
            return []

        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, sql)
        return list(set(matches))  # 去重

    @classmethod
    def validate_placeholders(cls, sql: str, time_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证占位符是否都有对应的上下文值

        Args:
            sql: SQL字符串
            time_context: 时间上下文

        Returns:
            验证结果字典，包含缺失的占位符和警告信息
        """
        placeholders = cls.extract_placeholders(sql)
        missing_placeholders = []
        available_placeholders = []
        warnings = []

        for placeholder in placeholders:
            if placeholder in cls.TIME_PLACEHOLDERS:
                context_key = cls.TIME_PLACEHOLDERS[placeholder]
                time_value = cls._get_time_value(time_context, context_key, placeholder)

                if time_value:
                    available_placeholders.append(placeholder)
                else:
                    missing_placeholders.append(placeholder)
                    warnings.append(f"时间占位符 {{{{placeholder}}}} 缺少对应的时间上下文值")
            else:
                warnings.append(f"未识别的占位符 {{{{placeholder}}}}，可能需要扩展支持")

        return {
            "valid": len(missing_placeholders) == 0,
            "total_placeholders": len(placeholders),
            "available_placeholders": available_placeholders,
            "missing_placeholders": missing_placeholders,
            "warnings": warnings,
            "placeholder_details": {
                ph: cls._get_time_value(
                    time_context,
                    cls.TIME_PLACEHOLDERS.get(ph, ph),
                    ph
                ) for ph in placeholders
            }
        }

    @classmethod
    def preview_replacement(cls, sql: str, time_context: Dict[str, Any]) -> Dict[str, str]:
        """
        预览占位符替换结果，用于调试

        Returns:
            包含原始SQL和替换后SQL的字典
        """
        replaced_sql = cls.replace_time_placeholders(sql, time_context)
        placeholders = cls.extract_placeholders(sql)

        replacements = {}
        for placeholder in placeholders:
            if placeholder in cls.TIME_PLACEHOLDERS:
                context_key = cls.TIME_PLACEHOLDERS[placeholder]
                time_value = cls._get_time_value(time_context, context_key, placeholder)
                if time_value:
                    formatted_time = cls._format_time_value(time_value)
                    replacements[f"{{{{{placeholder}}}}}"] = f"'{formatted_time}'"

        return {
            "original_sql": sql,
            "replaced_sql": replaced_sql,
            "replacements": replacements,
            "placeholder_count": len(placeholders)
        }


def replace_sql_placeholders(sql: str, time_context: Dict[str, Any]) -> str:
    """
    便捷函数：替换SQL中的占位符

    这是SqlPlaceholderReplacer.replace_time_placeholders的快捷方式
    """
    return SqlPlaceholderReplacer.replace_time_placeholders(sql, time_context)


# 向后兼容的别名
replace_time_placeholders = replace_sql_placeholders

logger.info("✅ SQL占位符替换工具类已加载")