"""
Error Formatting Pipeline
========================

Advanced error formatting system for agent failures and communication issues.
Inspired by Claude Code's error formatting pipeline with agent-specific enhancements.
"""

import logging
import traceback
import re
import json
import uuid
from typing import Any, Dict, List, Optional, Union, Type, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import sys

from .message_types import AgentMessage, MessageType

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification"""
    COMMUNICATION = "communication"        # Message passing errors
    PARSING = "parsing"                   # Data parsing errors
    VALIDATION = "validation"             # Input validation errors
    TIMEOUT = "timeout"                   # Timeout and ANR errors
    RESOURCE = "resource"                 # Resource allocation errors
    AUTHENTICATION = "authentication"     # Auth and permissions
    BUSINESS_LOGIC = "business_logic"     # Application logic errors
    SYSTEM = "system"                     # System-level errors
    UNKNOWN = "unknown"                   # Unclassified errors


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = 1      # Info/warning level
    MEDIUM = 2   # Recoverable errors
    HIGH = 3     # Serious errors affecting functionality  
    CRITICAL = 4 # System-breaking errors
    FATAL = 5    # Unrecoverable failures


@dataclass
class ErrorContext:
    """Contextual information for error formatting"""
    agent_id: str
    task_id: Optional[str] = None
    message_id: Optional[str] = None
    
    # Error location
    file_name: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    
    # Runtime context
    local_variables: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    
    # Agent state
    agent_state: Dict[str, Any] = field(default_factory=dict)
    previous_errors: List[str] = field(default_factory=list)
    
    # Environment
    system_info: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentError:
    """Structured representation of an agent error"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    
    # Core error information
    title: str = ""
    description: str = ""
    original_exception: Optional[Exception] = None
    
    # Context and debugging
    context: Optional[ErrorContext] = None
    root_cause: Optional[str] = None
    
    # Recovery information
    is_recoverable: bool = True
    recovery_suggestions: List[str] = field(default_factory=list)
    recovery_actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Impact assessment
    affected_agents: List[str] = field(default_factory=list)
    user_impact: str = ""
    business_impact: str = ""
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_error_hash(self) -> str:
        """Generate unique hash for error deduplication"""
        hash_input = f"{self.category.value}:{self.title}:{self.root_cause}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'error_id': self.error_id,
            'category': self.category.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'original_exception': str(self.original_exception) if self.original_exception else None,
            'context': self.context.__dict__ if self.context else None,
            'root_cause': self.root_cause,
            'is_recoverable': self.is_recoverable,
            'recovery_suggestions': self.recovery_suggestions,
            'recovery_actions': self.recovery_actions,
            'affected_agents': self.affected_agents,
            'user_impact': self.user_impact,
            'business_impact': self.business_impact,
            'tags': self.tags,
            'custom_metadata': self.custom_metadata,
            'created_at': self.created_at.isoformat(),
            'error_hash': self.get_error_hash()
        }


class ErrorFormatter:
    """
    Advanced error formatting system for agents
    
    Features:
    1. Automatic error classification and categorization
    2. Context-aware error descriptions
    3. Recovery suggestion generation
    4. Impact assessment
    5. Multiple output formats (human, structured, logs)
    """
    
    def __init__(self):
        # Error classification patterns
        self.classification_patterns = {
            ErrorCategory.COMMUNICATION: [
                r"connection.*refused",
                r"network.*unreachable", 
                r"timeout.*connecting",
                r"message.*delivery.*failed",
                r"serialization.*error",
                r"deserialization.*error"
            ],
            ErrorCategory.PARSING: [
                r"json.*decode.*error",
                r"xml.*parse.*error",
                r"invalid.*format",
                r"malformed.*data",
                r"unexpected.*token"
            ],
            ErrorCategory.VALIDATION: [
                r"validation.*failed",
                r"invalid.*input",
                r"missing.*required.*field",
                r"constraint.*violation",
                r"schema.*validation.*error"
            ],
            ErrorCategory.TIMEOUT: [
                r"timeout.*exceeded",
                r"operation.*timed.*out",
                r"anr.*detected",
                r"hung.*operation",
                r"deadlock.*detected"
            ],
            ErrorCategory.RESOURCE: [
                r"out.*of.*memory",
                r"disk.*space.*full",
                r"resource.*exhausted",
                r"thread.*pool.*full",
                r"connection.*pool.*exhausted"
            ],
            ErrorCategory.AUTHENTICATION: [
                r"authentication.*failed",
                r"unauthorized.*access",
                r"permission.*denied",
                r"access.*forbidden",
                r"invalid.*credentials"
            ]
        }
        
        # Recovery suggestion templates
        self.recovery_templates = {
            ErrorCategory.COMMUNICATION: [
                "Check network connectivity",
                "Verify service endpoints are accessible",
                "Implement retry with exponential backoff",
                "Check firewall and proxy settings"
            ],
            ErrorCategory.PARSING: [
                "Validate input data format",
                "Check data encoding",
                "Implement more robust parsing with error handling",
                "Log raw input data for debugging"
            ],
            ErrorCategory.VALIDATION: [
                "Review input validation rules", 
                "Check required field mappings",
                "Validate data types and formats",
                "Implement fallback values for optional fields"
            ],
            ErrorCategory.TIMEOUT: [
                "Increase timeout values",
                "Optimize slow operations",
                "Implement async processing",
                "Check for blocking operations"
            ],
            ErrorCategory.RESOURCE: [
                "Increase resource limits",
                "Implement resource monitoring",
                "Optimize memory usage",
                "Clean up unused resources"
            ],
            ErrorCategory.AUTHENTICATION: [
                "Check credentials configuration",
                "Verify authentication tokens",
                "Review permission settings",
                "Implement credential refresh"
            ]
        }
        
        # Custom formatters for different contexts
        self.formatters: Dict[str, Callable[[AgentError], str]] = {
            'human': self._format_human_readable,
            'technical': self._format_technical,
            'structured': self._format_structured_log,
            'agent_message': self._format_agent_message,
            'user_friendly': self._format_user_friendly
        }
        
        # Error statistics
        self.error_counts: Dict[ErrorCategory, int] = {cat: 0 for cat in ErrorCategory}
        self.total_errors_processed = 0
        
        logger.info("ErrorFormatter initialized")
    
    def format_error(self, 
                    exception: Exception,
                    context: ErrorContext = None,
                    format_type: str = 'human') -> AgentError:
        """
        Format an exception into a structured AgentError
        
        Args:
            exception: The original exception
            context: Additional context information
            format_type: Output format type
            
        Returns:
            AgentError: Structured error representation
        """
        
        self.total_errors_processed += 1
        
        # Create base error
        agent_error = AgentError(
            original_exception=exception,
            context=context or ErrorContext(agent_id="unknown"),
            title=self._extract_error_title(exception),
            description=self._extract_error_description(exception)
        )
        
        # Classify error
        agent_error.category = self._classify_error(exception, context)
        agent_error.severity = self._assess_severity(exception, context)
        
        # Update statistics
        self.error_counts[agent_error.category] += 1
        
        # Extract root cause
        agent_error.root_cause = self._analyze_root_cause(exception, context)
        
        # Generate recovery suggestions
        agent_error.recovery_suggestions = self._generate_recovery_suggestions(agent_error)
        
        # Assess impact
        agent_error.user_impact = self._assess_user_impact(agent_error)
        agent_error.business_impact = self._assess_business_impact(agent_error)
        
        # Add tags
        agent_error.tags = self._generate_tags(agent_error)
        
        logger.debug(f"Formatted error: {agent_error.category.value} - {agent_error.title}")
        
        return agent_error
    
    def format_to_string(self, agent_error: AgentError, format_type: str = 'human') -> str:
        """Format AgentError to string using specified formatter"""
        
        formatter = self.formatters.get(format_type, self._format_human_readable)
        return formatter(agent_error)
    
    def format_to_agent_message(self, agent_error: AgentError, to_agent: str = "system") -> AgentMessage:
        """Convert AgentError to AgentMessage for transmission"""
        
        return AgentMessage(
            message_type=MessageType.TASK_ERROR,
            from_agent=agent_error.context.agent_id if agent_error.context else "error_formatter",
            to_agent=to_agent,
            payload={
                'error': agent_error.to_dict(),
                'formatted_message': self.format_to_string(agent_error, 'agent_message')
            },
            error_info={
                'error_id': agent_error.error_id,
                'category': agent_error.category.value,
                'severity': agent_error.severity.value,
                'recoverable': agent_error.is_recoverable
            },
            recovery_suggestions=agent_error.recovery_suggestions,
            confidence=0.9 if agent_error.category != ErrorCategory.UNKNOWN else 0.5
        )
    
    def _extract_error_title(self, exception: Exception) -> str:
        """Extract concise error title"""
        exc_type = type(exception).__name__
        exc_msg = str(exception)
        
        # Clean up common patterns
        if exc_msg:
            # Truncate very long messages
            if len(exc_msg) > 100:
                exc_msg = exc_msg[:97] + "..."
            return f"{exc_type}: {exc_msg}"
        else:
            return exc_type
    
    def _extract_error_description(self, exception: Exception) -> str:
        """Extract detailed error description"""
        description_parts = []
        
        # Exception message
        if str(exception):
            description_parts.append(f"Error: {str(exception)}")
        
        # Exception type
        description_parts.append(f"Exception Type: {type(exception).__name__}")
        
        # Module information
        if hasattr(exception, '__module__'):
            description_parts.append(f"Module: {exception.__module__}")
        
        # Stack trace (truncated)
        try:
            tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
            if tb:
                # Get the last few frames
                relevant_frames = tb[-3:] if len(tb) > 3 else tb
                description_parts.append("Stack Trace (recent):")
                description_parts.extend(relevant_frames)
        except Exception:
            pass
        
        return "\n".join(description_parts)
    
    def _classify_error(self, exception: Exception, context: ErrorContext = None) -> ErrorCategory:
        """Classify error into category"""
        
        error_text = str(exception).lower()
        exc_type = type(exception).__name__.lower()
        combined_text = f"{exc_type} {error_text}"
        
        # Check classification patterns
        for category, patterns in self.classification_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    return category
        
        # Check exception type patterns
        if 'timeout' in exc_type or 'anr' in exc_type:
            return ErrorCategory.TIMEOUT
        elif 'parse' in exc_type or 'json' in exc_type or 'xml' in exc_type:
            return ErrorCategory.PARSING
        elif 'validation' in exc_type or 'value' in exc_type:
            return ErrorCategory.VALIDATION
        elif 'connection' in exc_type or 'network' in exc_type:
            return ErrorCategory.COMMUNICATION
        elif 'memory' in exc_type or 'resource' in exc_type:
            return ErrorCategory.RESOURCE
        elif 'auth' in exc_type or 'permission' in exc_type:
            return ErrorCategory.AUTHENTICATION
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, exception: Exception, context: ErrorContext = None) -> ErrorSeverity:
        """Assess error severity"""
        
        exc_type = type(exception).__name__.lower()
        error_msg = str(exception).lower()
        
        # Critical patterns
        if any(pattern in exc_type or pattern in error_msg for pattern in [
            'fatal', 'critical', 'system', 'kernel', 'segmentation', 'abort'
        ]):
            return ErrorSeverity.FATAL
        
        # High severity patterns
        if any(pattern in exc_type or pattern in error_msg for pattern in [
            'memory', 'disk', 'resource', 'deadlock', 'corruption'
        ]):
            return ErrorSeverity.CRITICAL
        
        # Medium severity patterns
        if any(pattern in exc_type or pattern in error_msg for pattern in [
            'timeout', 'connection', 'network', 'parse', 'validation'
        ]):
            return ErrorSeverity.HIGH
        
        # Check context for severity clues
        if context and context.previous_errors:
            # Repeated errors are more severe
            if len(context.previous_errors) > 3:
                return ErrorSeverity.HIGH
        
        return ErrorSeverity.MEDIUM
    
    def _analyze_root_cause(self, exception: Exception, context: ErrorContext = None) -> Optional[str]:
        """Analyze and determine root cause"""
        
        # Common root cause patterns
        error_text = str(exception).lower()
        
        root_causes = {
            r'connection.*refused': "Target service is not running or unreachable",
            r'timeout.*exceeded': "Operation took longer than expected - performance issue or blocking",
            r'out.*of.*memory': "Memory exhaustion - possible memory leak or insufficient resources",
            r'json.*decode.*error': "Invalid or malformed JSON data",
            r'validation.*failed': "Input data doesn't meet required criteria",
            r'permission.*denied': "Insufficient privileges to perform operation",
            r'file.*not.*found': "Required file or resource is missing",
            r'authentication.*failed': "Invalid credentials or expired token"
        }
        
        for pattern, cause in root_causes.items():
            if re.search(pattern, error_text, re.IGNORECASE):
                return cause
        
        # Check for chained exceptions
        if hasattr(exception, '__cause__') and exception.__cause__:
            return f"Caused by: {str(exception.__cause__)}"
        
        return None
    
    def _generate_recovery_suggestions(self, agent_error: AgentError) -> List[str]:
        """Generate recovery suggestions based on error category"""
        
        suggestions = []
        
        # Get template suggestions for category
        template_suggestions = self.recovery_templates.get(agent_error.category, [])
        suggestions.extend(template_suggestions)
        
        # Add specific suggestions based on error content
        if agent_error.original_exception:
            error_text = str(agent_error.original_exception).lower()
            
            if 'connection' in error_text:
                suggestions.append("Check if target service is running and accessible")
                suggestions.append("Verify network connectivity and firewall rules")
            
            if 'timeout' in error_text:
                suggestions.append("Consider increasing timeout values")
                suggestions.append("Optimize the operation to complete faster")
            
            if 'memory' in error_text:
                suggestions.append("Monitor and optimize memory usage")
                suggestions.append("Implement memory cleanup routines")
            
            if 'json' in error_text or 'parse' in error_text:
                suggestions.append("Validate input data format before parsing")
                suggestions.append("Add error handling for malformed data")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:5]  # Limit to top 5 suggestions
    
    def _assess_user_impact(self, agent_error: AgentError) -> str:
        """Assess impact on user experience"""
        
        severity_impact = {
            ErrorSeverity.LOW: "Minimal - user may not notice",
            ErrorSeverity.MEDIUM: "Moderate - some features may be affected",
            ErrorSeverity.HIGH: "Significant - core functionality impacted", 
            ErrorSeverity.CRITICAL: "Severe - system unusable",
            ErrorSeverity.FATAL: "Complete - system failure"
        }
        
        base_impact = severity_impact.get(agent_error.severity, "Unknown impact")
        
        # Add category-specific details
        if agent_error.category == ErrorCategory.COMMUNICATION:
            return f"{base_impact} - Communication with services disrupted"
        elif agent_error.category == ErrorCategory.TIMEOUT:
            return f"{base_impact} - Operations taking too long or failing"
        elif agent_error.category == ErrorCategory.AUTHENTICATION:
            return f"{base_impact} - User access may be blocked"
        
        return base_impact
    
    def _assess_business_impact(self, agent_error: AgentError) -> str:
        """Assess business impact"""
        
        if agent_error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            return "High - Service disruption affecting operations"
        elif agent_error.severity == ErrorSeverity.HIGH:
            return "Medium - Reduced functionality affecting productivity"
        elif agent_error.severity == ErrorSeverity.MEDIUM:
            return "Low - Minor degradation in service quality"
        else:
            return "Minimal - Negligible business impact"
    
    def _generate_tags(self, agent_error: AgentError) -> List[str]:
        """Generate tags for categorization and search"""
        
        tags = [
            agent_error.category.value,
            agent_error.severity.name.lower()
        ]
        
        if agent_error.original_exception:
            tags.append(type(agent_error.original_exception).__name__.lower())
        
        if agent_error.context and agent_error.context.agent_id:
            tags.append(f"agent:{agent_error.context.agent_id}")
        
        if agent_error.is_recoverable:
            tags.append("recoverable")
        else:
            tags.append("non-recoverable")
        
        return tags
    
    # Formatters
    
    def _format_human_readable(self, agent_error: AgentError) -> str:
        """Format for human readability"""
        
        lines = [
            f"🚨 Agent Error [{agent_error.severity.name}]",
            f"Category: {agent_error.category.value.title()}",
            f"Title: {agent_error.title}",
            "",
            "Description:",
            agent_error.description,
        ]
        
        if agent_error.root_cause:
            lines.extend(["", f"Root Cause: {agent_error.root_cause}"])
        
        if agent_error.recovery_suggestions:
            lines.extend(["", "Recovery Suggestions:"])
            for i, suggestion in enumerate(agent_error.recovery_suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
        
        lines.extend([
            "",
            f"Error ID: {agent_error.error_id}",
            f"Timestamp: {agent_error.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ])
        
        return "\n".join(lines)
    
    def _format_technical(self, agent_error: AgentError) -> str:
        """Format for technical debugging"""
        
        sections = []
        
        # Header
        sections.append(f"=== AGENT ERROR REPORT ===")
        sections.append(f"ID: {agent_error.error_id}")
        sections.append(f"Hash: {agent_error.get_error_hash()}")
        sections.append(f"Timestamp: {agent_error.created_at.isoformat()}")
        sections.append("")
        
        # Classification
        sections.append("CLASSIFICATION:")
        sections.append(f"  Category: {agent_error.category.value}")
        sections.append(f"  Severity: {agent_error.severity.name}")
        sections.append(f"  Recoverable: {agent_error.is_recoverable}")
        sections.append("")
        
        # Error details
        sections.append("ERROR DETAILS:")
        sections.append(f"  Title: {agent_error.title}")
        sections.append(f"  Description: {agent_error.description}")
        if agent_error.root_cause:
            sections.append(f"  Root Cause: {agent_error.root_cause}")
        sections.append("")
        
        # Context
        if agent_error.context:
            sections.append("CONTEXT:")
            sections.append(f"  Agent: {agent_error.context.agent_id}")
            sections.append(f"  Task: {agent_error.context.task_id}")
            if agent_error.context.file_name:
                sections.append(f"  Location: {agent_error.context.file_name}:{agent_error.context.line_number}")
            sections.append("")
        
        # Stack trace
        if agent_error.context and agent_error.context.stack_trace:
            sections.append("STACK TRACE:")
            sections.append(agent_error.context.stack_trace)
            sections.append("")
        
        return "\n".join(sections)
    
    def _format_structured_log(self, agent_error: AgentError) -> str:
        """Format as structured JSON log"""
        return json.dumps(agent_error.to_dict(), indent=2)
    
    def _format_agent_message(self, agent_error: AgentError) -> str:
        """Format for agent-to-agent communication"""
        
        message = f"Error in {agent_error.context.agent_id if agent_error.context else 'unknown'}: {agent_error.title}"
        
        if agent_error.is_recoverable and agent_error.recovery_suggestions:
            message += f" | Suggested actions: {', '.join(agent_error.recovery_suggestions[:2])}"
        
        return message
    
    def _format_user_friendly(self, agent_error: AgentError) -> str:
        """Format for end-user display"""
        
        if agent_error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            return "A critical system error has occurred. Please contact support."
        elif agent_error.severity == ErrorSeverity.HIGH:
            return "A service error has occurred. Some features may be temporarily unavailable."
        elif agent_error.category == ErrorCategory.TIMEOUT:
            return "The operation is taking longer than expected. Please try again."
        elif agent_error.category == ErrorCategory.VALIDATION:
            return "The provided information appears to be invalid. Please check your input."
        else:
            return "A temporary error has occurred. Please try again shortly."
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error processing statistics"""
        
        return {
            'total_errors_processed': self.total_errors_processed,
            'error_counts_by_category': {cat.value: count for cat, count in self.error_counts.items()},
            'most_common_category': max(self.error_counts, key=self.error_counts.get).value if self.error_counts else None,
            'available_formatters': list(self.formatters.keys())
        }


# Convenience functions

def format_exception(exception: Exception, agent_id: str = "unknown", format_type: str = 'human') -> str:
    """Quick format an exception to string"""
    formatter = ErrorFormatter()
    context = ErrorContext(agent_id=agent_id)
    agent_error = formatter.format_error(exception, context, format_type)
    return formatter.format_to_string(agent_error, format_type)

def create_error_message(exception: Exception, agent_id: str, to_agent: str = "system") -> AgentMessage:
    """Create an AgentMessage from an exception"""
    formatter = ErrorFormatter()
    context = ErrorContext(agent_id=agent_id)
    agent_error = formatter.format_error(exception, context)
    return formatter.format_to_agent_message(agent_error, to_agent)

def extract_stack_context() -> ErrorContext:
    """Extract context from current stack frame"""
    frame = sys._getframe(1)  # Get caller's frame
    
    return ErrorContext(
        agent_id="current",
        file_name=frame.f_code.co_filename,
        line_number=frame.f_lineno,
        function_name=frame.f_code.co_name,
        local_variables={k: str(v) for k, v in frame.f_locals.items()},
        stack_trace=traceback.format_stack()[-5:]  # Last 5 frames
    )


__all__ = [
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorContext", 
    "AgentError",
    "ErrorFormatter",
    "format_exception",
    "create_error_message",
    "extract_stack_context",
]