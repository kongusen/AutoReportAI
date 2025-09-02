"""
Template Management Services - React Agent Architecture

Modern template management powered by React Agent system:
- React Agent-enhanced template processing
- Intelligent placeholder analysis and generation  
- AI-driven template optimization
- Smart template caching with context awareness
- Automated template version control
"""

# Core template services with React Agent integration
from .template_cache_service import TemplateCacheService
from .template_service import TemplateService

# Intelligent Placeholder Service (React Agent-powered)
# Import from: app.services.domain.placeholder import get_intelligent_placeholder_service

__all__ = [
    # Core services
    "TemplateCacheService",
    "TemplateService"
]