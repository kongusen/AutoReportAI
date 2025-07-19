"""Data sanitization service for cleaning and validating data."""

import re
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class DataSanitizer:
    """Service for sanitizing and validating data before processing."""
    
    def __init__(self):
        self.patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^\+?1?\d{9,15}$',
            'url': r'^https?://[^\s/$.?#].[^\s]*$',
            'sql_injection': r"(union|select|insert|update|delete|drop|create|alter|exec|execute|;|'|\"|--|/\*|\*/)",
            'xss': r"(<script|<iframe|<object|<embed|<link|<meta|javascript:|data:|vbscript:|onload=|onerror=)",
        }
    
    def sanitize_string(self, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            return str(value)
        
        # Remove SQL injection attempts
        value = re.sub(self.patterns['sql_injection'], '', value, flags=re.IGNORECASE)
        
        # Remove XSS attempts
        value = re.sub(self.patterns['xss'], '', value, flags=re.IGNORECASE)
        
        # Trim whitespace
        value = value.strip()
        
        # Limit length if specified
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    def sanitize_email(self, email: str) -> Optional[str]:
        """Sanitize and validate email address."""
        if not email:
            return None
        
        email = self.sanitize_string(email).lower()
        
        if re.match(self.patterns['email'], email):
            return email
        
        return None
    
    def sanitize_phone(self, phone: str) -> Optional[str]:
        """Sanitize and validate phone number."""
        if not phone:
            return None
        
        phone = re.sub(r'[^\d+]', '', str(phone))
        
        if re.match(self.patterns['phone'], phone):
            return phone
        
        return None
    
    def sanitize_url(self, url: str) -> Optional[str]:
        """Sanitize and validate URL."""
        if not url:
            return None
        
        url = self.sanitize_string(url)
        
        if re.match(self.patterns['url'], url):
            return url
        
        return None
    
    def sanitize_dict(self, data: Dict[str, Any], schema: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Sanitize dictionary data."""
        sanitized = {}
        
        for key, value in data.items():
            if schema and key in schema:
                field_type = schema[key]
                if field_type == 'email':
                    sanitized[key] = self.sanitize_email(str(value))
                elif field_type == 'phone':
                    sanitized[key] = self.sanitize_phone(str(value))
                elif field_type == 'url':
                    sanitized[key] = self.sanitize_url(str(value))
                elif field_type == 'string':
                    sanitized[key] = self.sanitize_string(str(value))
                else:
                    sanitized[key] = value
            else:
                if isinstance(value, str):
                    sanitized[key] = self.sanitize_string(value)
                else:
                    sanitized[key] = value
        
        return sanitized
    
    def sanitize_list(self, items: List[Any], item_type: str = 'string') -> List[Any]:
        """Sanitize list of items."""
        sanitized = []
        
        for item in items:
            if item_type == 'email':
                clean_item = self.sanitize_email(str(item))
            elif item_type == 'phone':
                clean_item = self.sanitize_phone(str(item))
            elif item_type == 'url':
                clean_item = self.sanitize_url(str(item))
            elif item_type == 'string':
                clean_item = self.sanitize_string(str(item))
            else:
                clean_item = item
            
            if clean_item is not None:
                sanitized.append(clean_item)
        
        return sanitized
    
    def validate_data(self, data: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Validate data against rules."""
        errors = {}
        
        for field, rule in rules.items():
            value = data.get(field)
            
            field_errors = []
            
            # Required check
            if rule.get('required') and (value is None or value == ''):
                field_errors.append(f"{field} is required")
            
            # Type check
            if value is not None and 'type' in rule:
                expected_type = rule['type']
                if expected_type == 'email' and not self.sanitize_email(str(value)):
                    field_errors.append(f"{field} must be a valid email")
                elif expected_type == 'phone' and not self.sanitize_phone(str(value)):
                    field_errors.append(f"{field} must be a valid phone number")
                elif expected_type == 'url' and not self.sanitize_url(str(value)):
                    field_errors.append(f"{field} must be a valid URL")
            
            # Length check
            if value is not None and 'max_length' in rule:
                max_length = rule['max_length']
                if len(str(value)) > max_length:
                    field_errors.append(f"{field} must be {max_length} characters or less")
            
            # Range check for numbers
            if value is not None and isinstance(value, (int, float)):
                if 'min' in rule and value < rule['min']:
                    field_errors.append(f"{field} must be at least {rule['min']}")
                if 'max' in rule and value > rule['max']:
                    field_errors.append(f"{field} must be at most {rule['max']}")
            
            if field_errors:
                errors[field] = field_errors
        
        return errors
    
    def sanitize_sql_query(self, query: str) -> str:
        """Sanitize SQL query to prevent injection."""
        if not query:
            return ""
        
        # Remove dangerous keywords
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'UNION', 'SCRIPT'
        ]
        
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise ValueError(f"Dangerous SQL keyword detected: {keyword}")
        
        # Remove comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        
        return query.strip()
    
    def sanitize_html(self, html: str) -> str:
        """Sanitize HTML content."""
        if not html:
            return ""
        
        # Remove script tags and content
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove event handlers
        html = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
        
        # Remove dangerous tags
        dangerous_tags = ['iframe', 'object', 'embed', 'form', 'input', 'meta', 'link']
        for tag in dangerous_tags:
            html = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.IGNORECASE | re.DOTALL)
            html = re.sub(rf'<{tag}[^>]*/?>', '', html, flags=re.IGNORECASE)
        
        return html
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe file operations."""
        if not filename:
            return ""
        
        # Remove path traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Remove special characters
        filename = re.sub(r'[^\w\-_\.]', '', filename)
        
        # Limit length
        if len(filename) > 255:
            filename = filename[:255]
        
        return filename


# Global instance
data_sanitizer = DataSanitizer()
