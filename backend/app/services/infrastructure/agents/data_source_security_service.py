"""
数据源安全服务
实现用户数据源访问权限验证和SQL安全策略
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import logging
import re
from urllib.parse import urlparse

from app.crud.crud_data_source import crud_data_source
from app.crud.crud_user import crud_user
from app.db.session import SessionLocal
from app.models.data_source import DataSource


class DataSourceSecurityService:
    """数据源安全服务"""

    def __init__(self):
        """初始化安全服务"""
        self.logger = logging.getLogger(self.__class__.__name__)

        # SQL安全策略配置
        self.sql_security_config = {
            "policy_row_limit": True,           # 默认开启行数限制
            "default_row_limit": 10000,         # 默认行数限制
            "max_row_limit": 100000,            # 最大行数限制
            "enable_time_filter_suggestion": True,  # 启用时间过滤建议
            "dangerous_keywords": [             # 危险关键词
                "DROP", "DELETE", "TRUNCATE", "UPDATE",
                "INSERT", "ALTER", "CREATE", "GRANT", "REVOKE"
            ],
            "admin_only_keywords": [            # 管理员专用关键词
                "SHOW DATABASES", "SHOW TABLES", "DESCRIBE", "EXPLAIN"
            ]
        }

    def validate_data_source_access(
        self,
        user_id: str,
        data_source_id: str
    ) -> Dict[str, Any]:
        """
        验证用户对数据源的访问权限

        Args:
            user_id: 用户ID
            data_source_id: 数据源ID

        Returns:
            权限验证结果
        """
        db: Optional[Session] = None
        try:
            db = SessionLocal()

            # 获取数据源
            data_source = crud_data_source.get(db, id=data_source_id)
            if not data_source:
                return {
                    "allowed": False,
                    "reason": "数据源不存在",
                    "error_code": "DATASOURCE_NOT_FOUND"
                }

            # 检查数据源是否激活
            if not data_source.is_active:
                return {
                    "allowed": False,
                    "reason": "数据源未激活",
                    "error_code": "DATASOURCE_INACTIVE"
                }

            # 获取用户信息
            user = crud_user.get(db, id=user_id)
            if not user:
                return {
                    "allowed": False,
                    "reason": "用户不存在",
                    "error_code": "USER_NOT_FOUND"
                }

            # 检查用户是否激活
            if not user.is_active:
                return {
                    "allowed": False,
                    "reason": "用户账户未激活",
                    "error_code": "USER_INACTIVE"
                }

            # 权限检查：用户只能访问自己的数据源
            if str(data_source.user_id) != str(user_id):
                # 超级用户可以访问所有数据源
                if not user.is_superuser:
                    return {
                        "allowed": False,
                        "reason": "无权访问该数据源",
                        "error_code": "ACCESS_DENIED",
                        "data_source_owner": str(data_source.user_id)
                    }

            # 验证连接配置
            connection_check = self._validate_connection_config(data_source)
            if not connection_check["valid"]:
                return {
                    "allowed": False,
                    "reason": f"数据源配置无效: {connection_check['reason']}",
                    "error_code": "INVALID_CONFIGURATION"
                }

            return {
                "allowed": True,
                "data_source": {
                    "id": str(data_source.id),
                    "name": data_source.name,
                    "type": data_source.source_type.value,
                    "database": self._get_database_name(data_source),
                    "connection_info": self._get_safe_connection_info(data_source)
                },
                "user_permissions": {
                    "is_owner": str(data_source.user_id) == str(user_id),
                    "is_superuser": user.is_superuser,
                    "can_execute_sql": True,
                    "can_modify": str(data_source.user_id) == str(user_id) or user.is_superuser
                }
            }

        except Exception as e:
            self.logger.error(f"数据源权限验证失败: {e}")
            return {
                "allowed": False,
                "reason": "权限验证失败",
                "error_code": "VALIDATION_ERROR",
                "error": str(e)
            }
        finally:
            if db is not None:
                db.close()

    def apply_sql_security_policy(
        self,
        sql: str,
        user_id: str,
        data_source_id: Optional[str] = None,
        is_superuser: bool = False
    ) -> Dict[str, Any]:
        """
        应用SQL安全策略

        Args:
            sql: SQL语句
            user_id: 用户ID
            data_source_id: 数据源ID
            is_superuser: 是否为超级用户

        Returns:
            安全策略检查结果
        """
        try:
            sql_upper = sql.upper().strip()
            issues = []
            warnings = []
            modifications = []

            # 1. 危险关键词检查
            for keyword in self.sql_security_config["dangerous_keywords"]:
                if keyword in sql_upper:
                    issues.append(f"包含危险关键词: {keyword}")

            # 2. 管理员专用关键词检查
            if not is_superuser:
                for keyword in self.sql_security_config["admin_only_keywords"]:
                    if keyword in sql_upper:
                        issues.append(f"非管理员用户不能使用: {keyword}")

            # 3. 行数限制策略
            if self.sql_security_config["policy_row_limit"]:
                limit_check = self._check_and_apply_row_limit(sql, sql_upper)
                if limit_check["needs_limit"]:
                    if limit_check["current_limit"] > self.sql_security_config["max_row_limit"]:
                        issues.append(f"LIMIT值过大，最大允许: {self.sql_security_config['max_row_limit']}")
                    elif limit_check["suggested_sql"]:
                        modifications.append("已添加默认行数限制")
                        sql = limit_check["suggested_sql"]
                        warnings.append(f"已自动添加LIMIT {self.sql_security_config['default_row_limit']}")

            # 4. 时间过滤建议
            if self.sql_security_config["enable_time_filter_suggestion"]:
                time_filter_check = self._suggest_time_filter(sql, sql_upper)
                if time_filter_check["should_add_time_filter"]:
                    warnings.append(time_filter_check["suggestion"])

            # 5. 基本SQL结构验证
            if not sql_upper.startswith("SELECT"):
                issues.append("只允许SELECT查询")

            if "FROM" not in sql_upper:
                issues.append("查询必须包含FROM子句")

            return {
                "allowed": len(issues) == 0,
                "modified_sql": sql,
                "issues": issues,
                "warnings": warnings,
                "modifications": modifications,
                "policy_applied": True
            }

        except Exception as e:
            self.logger.error(f"SQL安全策略检查失败: {e}")
            return {
                "allowed": False,
                "issues": [f"安全策略检查失败: {str(e)}"],
                "policy_applied": False
            }

    def _validate_connection_config(self, data_source: DataSource) -> Dict[str, Any]:
        """验证数据源连接配置"""
        try:
            if data_source.source_type.value == "doris":
                # 验证Doris配置
                if not data_source.doris_fe_hosts:
                    return {"valid": False, "reason": "缺少Doris FE主机配置"}

                if not data_source.doris_database:
                    return {"valid": False, "reason": "缺少数据库名称"}

                if not data_source.doris_username:
                    return {"valid": False, "reason": "缺少用户名"}

                if not data_source.doris_password:
                    return {"valid": False, "reason": "缺少密码"}

            elif data_source.source_type.value == "sql":
                # 验证SQL连接字符串
                if not data_source.connection_string:
                    return {"valid": False, "reason": "缺少连接字符串"}

                # 基本URL格式验证
                try:
                    parsed = urlparse(data_source.connection_string)
                    if not parsed.scheme or not parsed.hostname:
                        return {"valid": False, "reason": "连接字符串格式无效"}
                except Exception:
                    return {"valid": False, "reason": "连接字符串解析失败"}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "reason": f"配置验证失败: {str(e)}"}

    def _get_database_name(self, data_source: DataSource) -> str:
        """获取数据库名称"""
        if data_source.source_type.value == "doris":
            return data_source.doris_database or ""
        elif data_source.connection_string:
            try:
                parsed = urlparse(data_source.connection_string)
                return parsed.path.lstrip('/') if parsed.path else ""
            except Exception:
                return ""
        return ""

    def _get_safe_connection_info(self, data_source: DataSource) -> Dict[str, Any]:
        """获取安全的连接信息（不包含密码）"""
        if data_source.source_type.value == "doris":
            return {
                "type": "doris",
                "hosts": data_source.doris_fe_hosts,
                "http_port": data_source.doris_http_port,
                "query_port": data_source.doris_query_port,
                "database": data_source.doris_database,
                "username": data_source.doris_username
            }
        elif data_source.connection_string:
            try:
                parsed = urlparse(data_source.connection_string)
                return {
                    "type": "sql",
                    "scheme": parsed.scheme,
                    "hostname": parsed.hostname,
                    "port": parsed.port,
                    "database": parsed.path.lstrip('/') if parsed.path else "",
                    "username": parsed.username
                }
            except Exception:
                return {"type": "sql", "connection": "配置解析失败"}

        return {"type": data_source.source_type.value}

    def _check_and_apply_row_limit(self, sql: str, sql_upper: str) -> Dict[str, Any]:
        """检查并应用行数限制"""
        # 检查是否已有LIMIT
        limit_pattern = r'LIMIT\s+(\d+)(?:\s+OFFSET\s+\d+)?'
        limit_match = re.search(limit_pattern, sql_upper)

        if limit_match:
            current_limit = int(limit_match.group(1))
            return {
                "needs_limit": False,
                "has_limit": True,
                "current_limit": current_limit
            }

        # 如果没有LIMIT，建议添加
        suggested_sql = sql.rstrip(';') + f' LIMIT {self.sql_security_config["default_row_limit"]}'

        return {
            "needs_limit": True,
            "has_limit": False,
            "suggested_sql": suggested_sql,
            "current_limit": 0
        }

    def _suggest_time_filter(self, sql: str, sql_upper: str) -> Dict[str, Any]:
        """建议时间过滤"""
        # 检查是否已有时间过滤
        time_patterns = [
            r'WHERE.*\b(DATE|TIME|TIMESTAMP|CREATED_AT|UPDATED_AT)\b',
            r'WHERE.*\b\d{4}-\d{2}-\d{2}\b',
            r'WHERE.*\bBETWEEN\b.*\bAND\b'
        ]

        has_time_filter = any(re.search(pattern, sql_upper) for pattern in time_patterns)

        if not has_time_filter:
            # 检查是否有大表查询的迹象
            if re.search(r'\bJOIN\b', sql_upper) or 'COUNT(*)' in sql_upper:
                return {
                    "should_add_time_filter": True,
                    "suggestion": "建议添加时间范围过滤以提高查询性能"
                }

        return {"should_add_time_filter": False}


# 创建全局实例
data_source_security_service = DataSourceSecurityService()