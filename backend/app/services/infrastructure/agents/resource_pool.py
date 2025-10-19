"""
ResourcePool - 精简记忆模式的资源池

设计理念：
- ContextMemory：轻量级状态标记，用于步骤间传递（减少token消耗）
- ResourcePool：完整资源存储，按需提取详细信息

适用场景：
- 大型数据库（10+张表）
- 多轮复杂对话
- Token成本敏感的场景
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import copy
import logging


@dataclass
class ContextMemory:
    """轻量级上下文记忆 - 只传递状态标记，不传递完整数据

    Token消耗：约200-500字符（vs 传统模式的5000+字符）
    """
    # 状态标记（布尔值）
    has_sql: bool = False
    schema_available: bool = False
    database_validated: bool = False
    sql_executed_successfully: bool = False

    # 表名列表（不含字段详情）
    available_tables: List[str] = field(default_factory=list)

    # 简要标识
    sql_length: int = 0
    sql_fix_attempts: int = 0
    last_error_summary: str = ""

    # 时间范围（精简）
    time_range: Optional[Dict[str, str]] = None
    recommended_time_column: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextMemory":
        """从字典创建"""
        return cls(
            has_sql=data.get("has_sql", False),
            schema_available=data.get("schema_available", False),
            database_validated=data.get("database_validated", False),
            sql_executed_successfully=data.get("sql_executed_successfully", False),
            available_tables=data.get("available_tables", []),
            sql_length=data.get("sql_length", 0),
            sql_fix_attempts=data.get("sql_fix_attempts", 0),
            last_error_summary=data.get("last_error_summary", ""),
            time_range=data.get("time_range"),
            recommended_time_column=data.get("recommended_time_column")
        )


class ResourcePool:
    """资源池 - 存储完整的上下文数据，按需提取

    核心优势：
    1. 减少token消耗：只传递ContextMemory状态标记
    2. 避免context膨胀：完整数据存储在ResourcePool，不累积到execution_context
    3. 按需提取：不同步骤提取所需的最小数据集
    """

    def __init__(self):
        self._storage: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)

    def update(self, updates: Dict[str, Any]) -> None:
        """增量更新资源池

        关键特性：
        - column_details：合并而不是覆盖
        - sql_history：追加而不是覆盖
        - validation_history：追加而不是覆盖

        Args:
            updates: 要更新的字段
        """
        for key, value in updates.items():
            if value is None:
                continue

            # 特殊处理：column_details合并
            if key == "column_details" and isinstance(value, dict):
                existing = self._storage.get("column_details", {})
                if isinstance(existing, dict):
                    # 合并新旧column_details
                    existing.update(value)
                    self._storage["column_details"] = existing
                    self._logger.debug(
                        f"🗄️ [ResourcePool] 合并column_details: "
                        f"{len(value)}张新表 -> 总计{len(existing)}张表"
                    )
                else:
                    self._storage["column_details"] = value
                continue

            # 特殊处理：历史记录追加
            if key in ["sql_history", "validation_history"] and isinstance(value, list):
                existing = self._storage.get(key, [])
                if isinstance(existing, list):
                    existing.extend(value)
                    self._storage[key] = existing
                else:
                    self._storage[key] = value
                continue

            # 普通字段：直接覆盖
            self._storage[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取资源（返回深拷贝，避免外部修改）

        Args:
            key: 资源键
            default: 默认值

        Returns:
            资源值的深拷贝
        """
        value = self._storage.get(key, default)
        # 返回深拷贝，避免外部修改ResourcePool
        if isinstance(value, (dict, list)):
            return copy.deepcopy(value)
        return value

    def build_context_memory(self) -> ContextMemory:
        """从ResourcePool构建轻量级ContextMemory

        这是ResourcePool的核心功能：将完整数据压缩为状态标记

        Returns:
            ContextMemory实例
        """
        column_details = self._storage.get("column_details", {})
        current_sql = self._storage.get("current_sql", "")

        return ContextMemory(
            has_sql=bool(current_sql),
            schema_available=bool(column_details),
            database_validated=self._storage.get("database_validated", False),
            sql_executed_successfully=self._storage.get("sql_executed_successfully", False),
            available_tables=list(column_details.keys()) if isinstance(column_details, dict) else [],
            sql_length=len(current_sql) if current_sql else 0,
            sql_fix_attempts=self._storage.get("sql_fix_attempts", 0),
            last_error_summary=self._storage.get("last_error_summary", ""),
            time_range=self._storage.get("time_range"),
            recommended_time_column=self._storage.get("recommended_time_column")
        )

    def extract_for_step(self, step_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """为特定步骤提取所需的最小上下文

        不同步骤需要不同的数据：
        - plan: 只需要ContextMemory
        - sql_generation: 需要column_details + template_context
        - sql_validation: 需要current_sql + column_details
        - sql_refinement: 需要SQL + 错误 + schema

        Args:
            step_type: 步骤类型
            context: 当前context（可能需要合并）

        Returns:
            合并后的context
        """
        extracted = dict(context)  # 复制现有context

        if step_type == "sql_generation":
            # SQL生成需要完整的column_details和template_context
            if self._storage.get("column_details"):
                extracted["column_details"] = self.get("column_details")
            if self._storage.get("template_context"):
                extracted["template_context"] = self.get("template_context")
            if self._storage.get("recommended_time_column"):
                extracted["recommended_time_column"] = self.get("recommended_time_column")

        elif step_type == "sql_validation":
            # SQL验证需要SQL和schema
            if self._storage.get("current_sql"):
                extracted["current_sql"] = self.get("current_sql")
            if self._storage.get("column_details"):
                extracted["column_details"] = self.get("column_details")

        elif step_type == "sql_refinement":
            # SQL修复需要SQL、错误、schema
            if self._storage.get("current_sql"):
                extracted["current_sql"] = self.get("current_sql")
            if self._storage.get("column_details"):
                extracted["column_details"] = self.get("column_details")
            if self._storage.get("last_sql_issues"):
                extracted["last_sql_issues"] = self.get("last_sql_issues")
            if self._storage.get("last_error_summary"):
                extracted["last_error_summary"] = self.get("last_error_summary")

        elif step_type == "schema_query":
            # Schema查询可能需要已有的schema信息作为参考
            if self._storage.get("schema_summary"):
                extracted["schema_summary"] = self.get("schema_summary")

        return extracted

    def get_all(self) -> Dict[str, Any]:
        """获取所有资源（用于调试）

        Returns:
            所有资源的深拷贝
        """
        return copy.deepcopy(self._storage)

    def clear(self) -> None:
        """清空资源池"""
        self._storage.clear()
        self._logger.info("🗄️ [ResourcePool] 资源池已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取资源池统计信息

        Returns:
            统计信息字典
        """
        column_details = self._storage.get("column_details", {})
        return {
            "total_tables": len(column_details) if isinstance(column_details, dict) else 0,
            "has_sql": bool(self._storage.get("current_sql")),
            "sql_length": len(self._storage.get("current_sql", "")),
            "sql_fix_attempts": self._storage.get("sql_fix_attempts", 0),
            "storage_keys": list(self._storage.keys())
        }
