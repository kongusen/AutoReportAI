"""
Tool Permission and Security System
===================================

Comprehensive permission management and security framework for agent tools,
inspired by Claude Code's permission patterns and security architecture.
"""

import logging
import hashlib
import time
from typing import Dict, Any, List, Optional, Set, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
import asyncio

from .base import ToolPermission, ToolExecutionContext, PermissionError

logger = logging.getLogger(__name__)


class PermissionBehavior(Enum):
    """Permission check behaviors"""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"        # Require user confirmation
    CONDITIONAL = "conditional"  # Allow with conditions
    AUDIT = "audit"    # Allow but log for audit


class SecurityLevel(Enum):
    """Security levels for operations"""
    PUBLIC = 1
    INTERNAL = 2
    RESTRICTED = 3
    CONFIDENTIAL = 4
    SECRET = 5


class ResourceType(Enum):
    """Types of resources that can be accessed"""
    FILE = "file"
    DIRECTORY = "directory"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM_COMMAND = "system_command"
    ENVIRONMENT = "environment"
    MEMORY = "memory"
    PROCESS = "process"


@dataclass
class SecurityContext:
    """Security context for permission decisions"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: str = "unknown"
    
    # Resource context
    requested_resource: Optional[str] = None
    resource_type: Optional[ResourceType] = None
    operation: str = "unknown"
    
    # Security metadata
    security_level: SecurityLevel = SecurityLevel.INTERNAL
    audit_required: bool = False
    elevated_permissions: bool = False
    
    # Request context
    request_origin: str = "internal"
    request_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    request_hash: Optional[str] = None
    
    # Previous permissions
    granted_permissions: Set[str] = field(default_factory=set)
    denied_permissions: Set[str] = field(default_factory=set)
    
    def generate_request_hash(self) -> str:
        """Generate a hash for this permission request"""
        content = f"{self.user_id}:{self.agent_id}:{self.requested_resource}:{self.operation}:{self.request_time.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def has_permission(self, permission: str) -> bool:
        """Check if permission was previously granted"""
        return permission in self.granted_permissions
    
    def is_denied(self, permission: str) -> bool:
        """Check if permission was previously denied"""
        return permission in self.denied_permissions


@dataclass
class PermissionRule:
    """A permission rule definition"""
    pattern: str  # Pattern to match (regex or glob)
    behavior: PermissionBehavior
    conditions: List[str] = field(default_factory=list)
    message: Optional[str] = None
    priority: int = 100  # Lower number = higher priority
    expires_at: Optional[datetime] = None
    
    # Metadata
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""
    
    def matches(self, resource: str, operation: str = None) -> bool:
        """Check if this rule matches the given resource/operation"""
        try:
            # Simple glob-style matching for now
            pattern = self.pattern.replace('*', '.*').replace('?', '.')
            
            # Build full match string
            match_string = resource
            if operation:
                match_string = f"{operation}:{resource}"
            
            return bool(re.match(pattern, match_string, re.IGNORECASE))
        except Exception as e:
            logger.warning(f"Permission rule pattern matching failed: {e}")
            return False
    
    def is_expired(self) -> bool:
        """Check if this rule has expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def evaluate_conditions(self, context: SecurityContext) -> bool:
        """Evaluate any conditions for this rule"""
        if not self.conditions:
            return True
        
        for condition in self.conditions:
            if not self._evaluate_single_condition(condition, context):
                return False
        
        return True
    
    def _evaluate_single_condition(self, condition: str, context: SecurityContext) -> bool:
        """Evaluate a single condition"""
        try:
            # Simple condition evaluation
            if condition.startswith("security_level <="):
                required_level = int(condition.split("<=")[1].strip())
                return context.security_level.value <= required_level
            
            elif condition.startswith("time_range"):
                # Format: time_range(09:00-17:00)
                time_range = condition.split("(")[1].split(")")[0]
                start_time, end_time = time_range.split("-")
                current_time = datetime.now().time()
                start = datetime.strptime(start_time, "%H:%M").time()
                end = datetime.strptime(end_time, "%H:%M").time()
                
                if start <= end:
                    return start <= current_time <= end
                else:  # Overnight range
                    return current_time >= start or current_time <= end
            
            elif condition.startswith("user_role"):
                # Would need user role lookup in real implementation
                return True  # Placeholder
            
            else:
                logger.warning(f"Unknown condition: {condition}")
                return True
                
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return False


@dataclass
class PermissionResult:
    """Result of a permission check"""
    behavior: PermissionBehavior
    granted: bool = False
    message: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    rule_matched: Optional[PermissionRule] = None
    
    # Suggestions for user
    suggestions: List[str] = field(default_factory=list)
    alternative_actions: List[str] = field(default_factory=list)
    
    # Audit information
    audit_log: bool = False
    audit_level: SecurityLevel = SecurityLevel.INTERNAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'behavior': self.behavior.value,
            'granted': self.granted,
            'message': self.message,
            'conditions': self.conditions,
            'suggestions': self.suggestions,
            'alternative_actions': self.alternative_actions,
            'audit_log': self.audit_log,
            'audit_level': self.audit_level.value
        }


class PermissionManager:
    """
    Central permission management system
    
    Handles permission rules, security contexts, and access control decisions
    with support for dynamic rules, caching, and audit logging.
    """
    
    def __init__(self):
        self.rules: List[PermissionRule] = []
        self.default_behavior = PermissionBehavior.DENY
        
        # Permission cache
        self._permission_cache: Dict[str, PermissionResult] = {}
        self._cache_ttl_seconds = 300  # 5 minutes
        self._cache_times: Dict[str, float] = {}
        
        # Audit logging
        self._audit_logger = logging.getLogger("tool_permissions.audit")
        self._audit_required_levels = {SecurityLevel.CONFIDENTIAL, SecurityLevel.SECRET}
        
        # Rate limiting
        self._rate_limits: Dict[str, List[float]] = {}
        self._rate_limit_window = 60  # 1 minute
        self._rate_limit_max_requests = 100
        
        # Built-in security rules
        self._initialize_default_rules()
        
        logger.info("PermissionManager initialized")
    
    def _initialize_default_rules(self):
        """Initialize default security rules"""
        
        # File system protection
        self.add_rule(PermissionRule(
            pattern="read:/etc/passwd",
            behavior=PermissionBehavior.DENY,
            message="Access to system password file is forbidden",
            priority=1,
            description="Protect system password file"
        ))
        
        self.add_rule(PermissionRule(
            pattern="read:/etc/shadow",
            behavior=PermissionBehavior.DENY,
            message="Access to shadow password file is forbidden",
            priority=1,
            description="Protect shadow password file"
        ))
        
        self.add_rule(PermissionRule(
            pattern="write:/system/*",
            behavior=PermissionBehavior.ASK,
            message="Writing to system directories requires confirmation",
            priority=10,
            conditions=["security_level <= 3"],
            description="Protect system directories"
        ))
        
        # Network access
        self.add_rule(PermissionRule(
            pattern="network:*",
            behavior=PermissionBehavior.CONDITIONAL,
            conditions=["security_level <= 4"],
            message="Network access requires appropriate security level",
            priority=20,
            description="Control network access"
        ))
        
        # Database access
        self.add_rule(PermissionRule(
            pattern="database:production",
            behavior=PermissionBehavior.ASK,
            message="Production database access requires confirmation",
            priority=5,
            description="Protect production data"
        ))
        
        # Default file access in working directory
        self.add_rule(PermissionRule(
            pattern="*",
            behavior=PermissionBehavior.ALLOW,
            priority=1000,  # Lowest priority (catch-all)
            description="Default allow for working directory"
        ))
    
    def add_rule(self, rule: PermissionRule):
        """Add a permission rule"""
        self.rules.append(rule)
        # Sort by priority (lower number = higher priority)
        self.rules.sort(key=lambda r: r.priority)
        logger.debug(f"Added permission rule: {rule.pattern} -> {rule.behavior.value}")
    
    def remove_rule(self, pattern: str) -> bool:
        """Remove a permission rule by pattern"""
        initial_count = len(self.rules)
        self.rules = [r for r in self.rules if r.pattern != pattern]
        removed_count = initial_count - len(self.rules)
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} permission rule(s) with pattern: {pattern}")
            return True
        return False
    
    def check_permission(self,
                        resource: str,
                        operation: str,
                        context: SecurityContext) -> PermissionResult:
        """
        Check permission for a resource and operation
        
        Args:
            resource: Resource being accessed (e.g., file path, database name)
            operation: Operation being performed (e.g., read, write, execute)
            context: Security context for the request
            
        Returns:
            PermissionResult indicating whether access is granted
        """
        # Generate cache key
        cache_key = self._generate_cache_key(resource, operation, context)
        
        # Check cache first
        cached_result = self._get_cached_permission(cache_key)
        if cached_result:
            return cached_result
        
        # Check rate limiting
        if not self._check_rate_limit(context):
            return PermissionResult(
                behavior=PermissionBehavior.DENY,
                granted=False,
                message="Rate limit exceeded",
                audit_log=True,
                audit_level=SecurityLevel.RESTRICTED
            )
        
        # Evaluate rules
        result = self._evaluate_permission_rules(resource, operation, context)
        
        # Cache the result
        self._cache_permission(cache_key, result)
        
        # Audit logging
        if result.audit_log or context.security_level in self._audit_required_levels:
            self._log_audit_event(resource, operation, context, result)
        
        return result
    
    def _evaluate_permission_rules(self,
                                 resource: str,
                                 operation: str,
                                 context: SecurityContext) -> PermissionResult:
        """Evaluate permission rules for a request"""
        
        # Clean up expired rules
        self.rules = [r for r in self.rules if not r.is_expired()]
        
        # Check each rule in priority order
        for rule in self.rules:
            if rule.matches(resource, operation):
                # Evaluate conditions
                if not rule.evaluate_conditions(context):
                    continue
                
                # Rule matched and conditions satisfied
                result = PermissionResult(
                    behavior=rule.behavior,
                    rule_matched=rule,
                    message=rule.message
                )
                
                # Set granted status based on behavior
                if rule.behavior == PermissionBehavior.ALLOW:
                    result.granted = True
                elif rule.behavior == PermissionBehavior.DENY:
                    result.granted = False
                elif rule.behavior == PermissionBehavior.ASK:
                    result.granted = False  # Requires user confirmation
                    result.suggestions = [f"Consider granting permission for: {resource}"]
                elif rule.behavior == PermissionBehavior.CONDITIONAL:
                    result.granted = True
                    result.conditions = rule.conditions
                elif rule.behavior == PermissionBehavior.AUDIT:
                    result.granted = True
                    result.audit_log = True
                    result.audit_level = context.security_level
                
                # Add security suggestions
                result.suggestions.extend(self._generate_security_suggestions(resource, operation, context))
                
                return result
        
        # No rule matched, use default behavior
        return PermissionResult(
            behavior=self.default_behavior,
            granted=(self.default_behavior == PermissionBehavior.ALLOW),
            message=f"No specific rule found, using default: {self.default_behavior.value}"
        )
    
    def _generate_security_suggestions(self,
                                     resource: str,
                                     operation: str,
                                     context: SecurityContext) -> List[str]:
        """Generate security suggestions for the user"""
        suggestions = []
        
        # Path-based suggestions
        if "/" in resource:
            path = Path(resource)
            
            # Suggest safer alternatives
            if str(path).startswith("/system") or str(path).startswith("/etc"):
                suggestions.append("Consider using a safer location in your working directory")
            
            # Suggest read-only access
            if operation == "write" and not context.elevated_permissions:
                suggestions.append("Consider using read-only access if possible")
        
        # Database suggestions
        if "database" in resource.lower():
            if "production" in resource.lower():
                suggestions.append("Consider using a development or staging database")
        
        # Network suggestions
        if context.resource_type == ResourceType.NETWORK:
            suggestions.append("Ensure network endpoints are trusted and secure")
        
        return suggestions
    
    def _generate_cache_key(self, resource: str, operation: str, context: SecurityContext) -> str:
        """Generate cache key for permission result"""
        key_parts = [
            resource,
            operation,
            context.agent_id,
            context.security_level.value,
            str(context.elevated_permissions)
        ]
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_permission(self, cache_key: str) -> Optional[PermissionResult]:
        """Get cached permission result if still valid"""
        if cache_key not in self._permission_cache:
            return None
        
        # Check if cache entry has expired
        cache_time = self._cache_times.get(cache_key, 0)
        if time.time() - cache_time > self._cache_ttl_seconds:
            del self._permission_cache[cache_key]
            del self._cache_times[cache_key]
            return None
        
        return self._permission_cache[cache_key]
    
    def _cache_permission(self, cache_key: str, result: PermissionResult):
        """Cache a permission result"""
        self._permission_cache[cache_key] = result
        self._cache_times[cache_key] = time.time()
        
        # Clean up old cache entries
        current_time = time.time()
        expired_keys = [
            key for key, cache_time in self._cache_times.items()
            if current_time - cache_time > self._cache_ttl_seconds
        ]
        
        for key in expired_keys:
            self._permission_cache.pop(key, None)
            self._cache_times.pop(key, None)
    
    def _check_rate_limit(self, context: SecurityContext) -> bool:
        """Check if request is within rate limits"""
        key = f"{context.user_id}:{context.agent_id}"
        current_time = time.time()
        
        # Get request times for this key
        if key not in self._rate_limits:
            self._rate_limits[key] = []
        
        request_times = self._rate_limits[key]
        
        # Remove old requests outside the window
        cutoff_time = current_time - self._rate_limit_window
        request_times[:] = [t for t in request_times if t > cutoff_time]
        
        # Check if we're at the limit
        if len(request_times) >= self._rate_limit_max_requests:
            return False
        
        # Add current request
        request_times.append(current_time)
        return True
    
    def _log_audit_event(self,
                        resource: str,
                        operation: str,
                        context: SecurityContext,
                        result: PermissionResult):
        """Log an audit event"""
        audit_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': context.user_id,
            'agent_id': context.agent_id,
            'resource': resource,
            'operation': operation,
            'granted': result.granted,
            'behavior': result.behavior.value,
            'security_level': context.security_level.value,
            'request_hash': context.generate_request_hash()
        }
        
        self._audit_logger.info(f"PERMISSION_CHECK: {audit_data}")
    
    def grant_temporary_permission(self,
                                 resource: str,
                                 operation: str,
                                 context: SecurityContext,
                                 duration_minutes: int = 60):
        """Grant temporary permission for a specific resource/operation"""
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        
        temp_rule = PermissionRule(
            pattern=f"{operation}:{resource}",
            behavior=PermissionBehavior.ALLOW,
            expires_at=expires_at,
            message=f"Temporary permission granted until {expires_at.isoformat()}",
            priority=1,  # High priority
            created_by=f"temp_grant_{context.agent_id}",
            description=f"Temporary access for {context.agent_id}"
        )
        
        self.add_rule(temp_rule)
        
        # Clear cache for this permission
        cache_key = self._generate_cache_key(resource, operation, context)
        self._permission_cache.pop(cache_key, None)
        self._cache_times.pop(cache_key, None)
        
        logger.info(f"Granted temporary permission: {operation}:{resource} until {expires_at}")
    
    def revoke_permission(self, resource: str, operation: str):
        """Revoke permission by adding a deny rule"""
        
        deny_rule = PermissionRule(
            pattern=f"{operation}:{resource}",
            behavior=PermissionBehavior.DENY,
            message=f"Permission explicitly revoked for {operation}:{resource}",
            priority=1,  # High priority
            created_by="manual_revoke",
            description=f"Manually revoked access to {resource}"
        )
        
        self.add_rule(deny_rule)
        logger.info(f"Revoked permission: {operation}:{resource}")
    
    def get_permission_summary(self, context: SecurityContext) -> Dict[str, Any]:
        """Get a summary of permissions for a context"""
        return {
            'security_level': context.security_level.value,
            'granted_permissions': list(context.granted_permissions),
            'denied_permissions': list(context.denied_permissions),
            'elevated_permissions': context.elevated_permissions,
            'active_rules': len(self.rules),
            'cache_size': len(self._permission_cache),
            'audit_required': context.security_level in self._audit_required_levels
        }


# Convenience functions

def create_permission_manager() -> PermissionManager:
    """Create a permission manager with default settings"""
    return PermissionManager()


def create_security_context(user_id: str = None,
                          agent_id: str = "system",
                          security_level: SecurityLevel = SecurityLevel.INTERNAL) -> SecurityContext:
    """Create a security context with default values"""
    return SecurityContext(
        user_id=user_id,
        agent_id=agent_id,
        security_level=security_level
    )


# Global permission manager instance
_global_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get the global permission manager instance"""
    global _global_permission_manager
    
    if _global_permission_manager is None:
        _global_permission_manager = PermissionManager()
    
    return _global_permission_manager


__all__ = [
    "PermissionBehavior", "SecurityLevel", "ResourceType",
    "SecurityContext", "PermissionRule", "PermissionResult",
    "PermissionManager", "create_permission_manager",
    "create_security_context", "get_permission_manager"
]