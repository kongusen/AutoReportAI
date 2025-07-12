import json
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from fastapi import Request

logger = structlog.get_logger(__name__)


class SecurityLogger:
    """
    Centralized security event logging service.
    Provides structured logging for security-critical events.
    """

    @staticmethod
    def log_authentication_attempt(
        username: str,
        success: bool,
        ip_address: str,
        user_agent: str,
        failure_reason: Optional[str] = None,
    ):
        """Log authentication attempts with context."""
        event_data = {
            "event_type": "authentication",
            "username": username,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if not success and failure_reason:
            event_data["failure_reason"] = failure_reason

        if success:
            logger.info("authentication.success", **event_data)
        else:
            logger.warning("authentication.failure", **event_data)

    @staticmethod
    def log_authorization_failure(
        user_id: str,
        resource: str,
        action: str,
        ip_address: str,
        reason: str = "insufficient_permissions",
    ):
        """Log authorization failures."""
        logger.warning(
            "authorization.failure",
            event_type="authorization",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=ip_address,
            reason=reason,
            timestamp=datetime.utcnow().isoformat(),
        )

    @staticmethod
    def log_sensitive_data_access(
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log access to sensitive data like API keys, user data, etc."""
        event_data = {
            "event_type": "sensitive_data_access",
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if details:
            event_data["details"] = details

        logger.info("data.sensitive_access", **event_data)

    @staticmethod
    def log_configuration_change(
        user_id: str,
        config_type: str,
        config_id: str,
        changes: Dict[str, Any],
        ip_address: str,
    ):
        """Log configuration changes like AI provider updates, data source changes."""
        logger.info(
            "configuration.change",
            event_type="configuration_change",
            user_id=user_id,
            config_type=config_type,
            config_id=config_id,
            changes=changes,
            ip_address=ip_address,
            timestamp=datetime.utcnow().isoformat(),
        )

    @staticmethod
    def log_rate_limit_exceeded(
        ip_address: str, endpoint: str, user_id: Optional[str] = None
    ):
        """Log rate limiting events."""
        event_data = {
            "event_type": "rate_limit_exceeded",
            "ip_address": ip_address,
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if user_id:
            event_data["user_id"] = user_id

        logger.warning("security.rate_limit_exceeded", **event_data)

    @staticmethod
    def log_suspicious_activity(
        activity_type: str,
        details: Dict[str, Any],
        ip_address: str,
        user_id: Optional[str] = None,
        severity: str = "medium",
    ):
        """Log suspicious activities that might indicate security threats."""
        event_data = {
            "event_type": "suspicious_activity",
            "activity_type": activity_type,
            "details": details,
            "ip_address": ip_address,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if user_id:
            event_data["user_id"] = user_id

        if severity == "high":
            logger.error("security.suspicious_activity", **event_data)
        else:
            logger.warning("security.suspicious_activity", **event_data)

    @staticmethod
    def log_data_export(
        user_id: str,
        export_type: str,
        record_count: int,
        ip_address: str,
        file_path: Optional[str] = None,
    ):
        """Log data export operations."""
        event_data = {
            "event_type": "data_export",
            "user_id": user_id,
            "export_type": export_type,
            "record_count": record_count,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if file_path:
            event_data["file_path"] = file_path

        logger.info("data.export", **event_data)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request, considering proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent from request."""
    return request.headers.get("User-Agent", "unknown")


# Create a global instance
security_logger = SecurityLogger()
