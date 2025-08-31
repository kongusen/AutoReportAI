"""
Template Management Services

Provides comprehensive template management capabilities including:
- Template CRUD operations
- Placeholder configuration and management  
- Template parsing and analysis
- Cache-aware template processing
- Template version control
- Agent-enhanced intelligent processing
"""

# Core template services
from .template_cache_service import TemplateCacheService

# Agent-enhanced template service (NEW - integrates with placeholder agents system)
from .agent_enhanced_template_service import (
    AgentEnhancedTemplateService,
    get_agent_enhanced_template_service,
    analyze_template_with_agents,
    execute_template_with_agents
)

# PlaceholderConfigService 已迁移到 app.services.domain.placeholder
# 使用: from app.services.domain.placeholder import get_intelligent_placeholder_service

__all__ = [
    # Core services
    "TemplateCacheService",
    
    # Agent-enhanced services
    "AgentEnhancedTemplateService",
    "get_agent_enhanced_template_service",
    "analyze_template_with_agents", 
    "execute_template_with_agents"
]