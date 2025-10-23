"""
数据源安全服务
实现用户数据源访问权限验证和SQL安全策略
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.crud.crud_data_source import crud_data_source
from app.crud.crud_user import crud_user
from app.db.session import SessionLocal
from app.models.data_source import DataSource


class DataSourceSecurityService:
    """数据源安全服务"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sql_security_config = {
            "policy_row_limit": True,
            "default_row_limit": 10000,
            "max_row_limit": 100000,
            "enable_time_filter_suggestion": True,
            "dangerous_keywords": [
                "DROP",
                "DELETE",
                "TRUNCATE",
                "UPDATE",
                "INSERT",
                "ALTER",
                "CREATE",
                "GRANT",
                "REVOKE",
            ],
            "admin_only_keywords": [
                "SHOW DATABASES",
                "SHOW TABLES",
                "DESCRIBE",
                "EXPLAIN",
            ],
        }

    def validate_data_source_access(self, user_id: str, data_source_id: str) -> Dict[str, Any]:
        db: Optional[Session] = None
        try:
            db = SessionLocal()
            data_source = crud_data_source.get(db, id=data_source_id)
            if not data_source:
                return {
                    "allowed": False,
                    "reason": "数据源不存在",
                    "error_code": "DATASOURCE_NOT_FOUND",
                }

            if not data_source.is_active:
                return {
                    "allowed": False,
                    "reason": "数据源未激活",
                    "error_code": "DATASOURCE_INACTIVE",
                }

            user = crud_user.get(db, id=user_id)
            if not user:
                return {
                    "allowed": False,
                    "reason": "用户不存在",
                    "error_code": "USER_NOT_FOUND",
                }

            if not user.is_active:
                return {
                    "allowed": False,
                    "reason": "用户账户未激活",
                    "error_code": "USER_INACTIVE",
                }

            if str(data_source.user_id) != str(user_id):
                if not user.is_superuser:
                    return {
                        "allowed": False,
                        "reason": "无权访问该数据源",
                        "error_code": "ACCESS_DENIED",
                        "data_source_owner": str(data_source.user_id),
                    }

            connection_check = self._validate_connection_config(data_source)
            if not connection_check["valid"]:
                return {
                    "allowed": False,
                    "reason": f"数据源配置无效: {connection_check['reason']}",
                    "error_code": "INVALID_CONFIGURATION",
                }

            return {
                "allowed": True,
                "data_source": {
                    "id": str(data_source.id),
                    "name": data_source.name,
                    "type": data_source.source_type.value,
                    "database": self._get_database_name(data_source),
                    "connection_info": self._get_safe_connection_info(data_source),
                },
                "user_permissions": {
                    "is_owner": str(data_source.user_id) == str(user_id),
                    "is_superuser": user.is_superuser,
                    "can_execute_sql": True,
                    "can_modify": str(data_source.user_id) == str(user_id) or user.is_superuser,
                },
            }

        except Exception as exc:  # pragma: no cover - defensive
            self.logger.error("数据源权限验证失败: %s", exc)
            return {
                "allowed": False,
                "reason": "权限验证失败",
                "error_code": "VALIDATION_ERROR",
                "error": str(exc),
            }
        finally:
            if db is not None:
                db.close()

    def apply_sql_security_policy(
        self,
        sql: str,
        user_id: str,
        data_source_id: Optional[str] = None,
        is_superuser: bool = False,
    ) -> Dict[str, Any]:
        try:
            sql_upper = sql.upper().strip()
            issues: List[str] = []
            warnings: List[str] = []
            modifications: List[str] = []

            for keyword in self.sql_security_config["dangerous_keywords"]:
                if keyword in sql_upper:
                    issues.append(f"包含危险关键词: {keyword}")

            if not is_superuser:
                for keyword in self.sql_security_config["admin_only_keywords"]:
                    if keyword in sql_upper:
                        issues.append(f"非管理员用户不能使用: {keyword}")

            if self.sql_security_config["policy_row_limit"]:
                limit_check = self._check_and_apply_row_limit(sql, sql_upper)
                if limit_check["needs_limit"]:
                    if limit_check["current_limit"] > self.sql_security_config["max_row_limit"]:
                        issues.append(
                            f"LIMIT值过大，最大允许: {self.sql_security_config['max_row_limit']}"
                        )
                    elif limit_check["suggested_sql"]:
                        modifications.append("已添加默认行数限制")
                        sql = limit_check["suggested_sql"]
                        warnings.append(
                            f"已自动添加LIMIT {self.sql_security_config['default_row_limit']}"
                        )

            if self.sql_security_config["enable_time_filter_suggestion"]:
                time_filter_check = self._suggest_time_filter(sql, sql_upper)
                if time_filter_check["should_add_time_filter"]:
                    warnings.append(time_filter_check["suggestion"])

            if not sql_upper.startswith("SELECT"):
                issues.append("只允许SELECT查询")
            if "FROM" not in sql_upper:
                issues.append("查询必须包含FROM子句")

            return {
                "success": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "modifications": modifications,
                "sql": sql,
            }
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.error("SQL安全策略检查失败: %s", exc)
            return {
                "success": False,
                "issues": [f"SQL安全策略检查失败: {str(exc)}"],
                "warnings": [],
                "modifications": [],
                "sql": sql,
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_connection_config(self, data_source: DataSource) -> Dict[str, Any]:
        if not data_source.connection_uri:
            return {"valid": False, "reason": "缺少连接URI"}

        parsed = urlparse(data_source.connection_uri)
        if not parsed.scheme or not parsed.netloc:
            return {"valid": False, "reason": "连接URI格式无效"}

        return {"valid": True}

    def _get_database_name(self, data_source: DataSource) -> str:
        parsed = urlparse(data_source.connection_uri)
        if parsed.path:
            return parsed.path.lstrip("/") or "default"
        return "default"

    def _get_safe_connection_info(self, data_source: DataSource) -> Dict[str, Any]:
        parsed = urlparse(data_source.connection_uri)
        return {
            "host": parsed.hostname or "",
            "port": parsed.port or "",
            "username": parsed.username or "",
            "database": self._get_database_name(data_source),
        }

    def _check_and_apply_row_limit(self, sql: str, sql_upper: str) -> Dict[str, Any]:
        limit_match = re.search(r"LIMIT\s+(\d+)", sql_upper)
        if limit_match:
            return {
                "needs_limit": False,
                "current_limit": int(limit_match.group(1)),
                "suggested_sql": None,
            }

        suggested_sql = f"{sql.rstrip(';')} LIMIT {self.sql_security_config['default_row_limit']}"
        return {
            "needs_limit": True,
            "current_limit": 0,
            "suggested_sql": suggested_sql,
        }

    def _suggest_time_filter(self, sql: str, sql_upper: str) -> Dict[str, Any]:
        if "WHERE" not in sql_upper:
            return {
                "should_add_time_filter": True,
                "suggestion": "建议添加时间过滤条件以限制结果集范围",
            }
        return {"should_add_time_filter": False, "suggestion": ""}


data_source_security_service = DataSourceSecurityService()


__all__ = ["DataSourceSecurityService", "data_source_security_service"]
