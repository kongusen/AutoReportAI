"""
Tool Registry System
===================

Manages registration, discovery, and access to agent tools,
inspired by Claude Code's tool management architecture.
"""

import logging
import importlib
import inspect
from typing import Dict, List, Optional, Type, Set, Callable, Any
from pathlib import Path
from collections import defaultdict
import asyncio
from datetime import datetime, timezone

from .base import AgentTool, ToolDefinition, ToolCategory, ToolPermission, ToolError

logger = logging.getLogger(__name__)


class ToolRegistryError(ToolError):
    """Tool registry specific errors"""
    pass


class ToolRegistry:
    """
    Central registry for all agent tools
    
    Provides tool discovery, registration, filtering, and access patterns
    similar to Claude Code's tool management system.
    """
    
    def __init__(self):
        self._tools: Dict[str, AgentTool] = {}
        self._definitions: Dict[str, ToolDefinition] = {}
        self._categories: Dict[ToolCategory, Set[str]] = defaultdict(set)
        self._permissions: Dict[ToolPermission, Set[str]] = defaultdict(set)
        self._aliases: Dict[str, str] = {}
        
        # Tool lifecycle hooks
        self._registration_hooks: List[Callable[[AgentTool], None]] = []
        self._execution_hooks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Metrics
        self._registration_count = 0
        self._execution_count = 0
        self._last_discovery_time: Optional[datetime] = None
        
        logger.info("ToolRegistry initialized")
    
    def register_tool(self, tool: AgentTool, aliases: List[str] = None) -> bool:
        """
        Register a tool with the registry
        
        Args:
            tool: Tool instance to register
            aliases: Alternative names for the tool
            
        Returns:
            True if registration successful
            
        Raises:
            ToolRegistryError: If registration fails
        """
        try:
            tool_name = tool.name
            
            # Check for conflicts
            if tool_name in self._tools:
                raise ToolRegistryError(
                    f"Tool '{tool_name}' is already registered",
                    tool_name=tool_name,
                    error_code="DUPLICATE_REGISTRATION"
                )
            
            # Validate tool
            self._validate_tool(tool)
            
            # Register tool
            self._tools[tool_name] = tool
            self._definitions[tool_name] = tool.definition
            
            # Update category index
            self._categories[tool.category].add(tool_name)
            
            # Update permission index
            for permission in tool.permissions:
                self._permissions[permission].add(tool_name)
            
            # Register aliases
            if aliases:
                for alias in aliases:
                    if alias in self._aliases:
                        logger.warning(f"Alias '{alias}' already exists, overriding")
                    self._aliases[alias] = tool_name
            
            # Execute registration hooks
            for hook in self._registration_hooks:
                try:
                    hook(tool)
                except Exception as e:
                    logger.warning(f"Registration hook failed: {e}")
            
            self._registration_count += 1
            logger.info(f"Tool '{tool_name}' registered successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tool '{tool.name}': {e}")
            raise ToolRegistryError(
                f"Registration failed: {e}",
                tool_name=tool.name,
                error_code="REGISTRATION_FAILED"
            )
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool from the registry
        
        Args:
            tool_name: Name of tool to unregister
            
        Returns:
            True if unregistration successful
        """
        try:
            if tool_name not in self._tools:
                logger.warning(f"Tool '{tool_name}' not found for unregistration")
                return False
            
            tool = self._tools[tool_name]
            
            # Remove from main registry
            del self._tools[tool_name]
            del self._definitions[tool_name]
            
            # Remove from category index
            self._categories[tool.category].discard(tool_name)
            
            # Remove from permission index
            for permission in tool.permissions:
                self._permissions[permission].discard(tool_name)
            
            # Remove aliases
            aliases_to_remove = [alias for alias, name in self._aliases.items() if name == tool_name]
            for alias in aliases_to_remove:
                del self._aliases[alias]
            
            logger.info(f"Tool '{tool_name}' unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister tool '{tool_name}': {e}")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[AgentTool]:
        """
        Get a tool by name or alias
        
        Args:
            tool_name: Tool name or alias
            
        Returns:
            Tool instance or None if not found
        """
        # Check direct name
        if tool_name in self._tools:
            return self._tools[tool_name]
        
        # Check aliases
        if tool_name in self._aliases:
            actual_name = self._aliases[tool_name]
            return self._tools.get(actual_name)
        
        return None
    
    def get_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Get a tool definition by name or alias
        
        Args:
            tool_name: Tool name or alias
            
        Returns:
            Tool definition or None if not found
        """
        # Check direct name
        if tool_name in self._definitions:
            return self._definitions[tool_name]
        
        # Check aliases
        if tool_name in self._aliases:
            actual_name = self._aliases[tool_name]
            return self._definitions.get(actual_name)
        
        return None
    
    def list_tools(self, 
                   category: Optional[ToolCategory] = None,
                   permissions: Optional[List[ToolPermission]] = None,
                   read_only: Optional[bool] = None,
                   supports_streaming: Optional[bool] = None) -> List[str]:
        """
        List tools with optional filtering
        
        Args:
            category: Filter by category
            permissions: Filter by required permissions
            read_only: Filter by read-only status
            supports_streaming: Filter by streaming support
            
        Returns:
            List of tool names matching criteria
        """
        tools = list(self._tools.keys())
        
        # Filter by category
        if category is not None:
            tools = [name for name in tools if name in self._categories[category]]
        
        # Filter by permissions
        if permissions is not None:
            permission_sets = [self._permissions[perm] for perm in permissions]
            if permission_sets:
                # Tools that have ALL specified permissions
                intersection = set.intersection(*permission_sets) if permission_sets else set()
                tools = [name for name in tools if name in intersection]
        
        # Filter by read-only status
        if read_only is not None:
            tools = [name for name in tools 
                    if self._definitions[name].is_read_only == read_only]
        
        # Filter by streaming support
        if supports_streaming is not None:
            tools = [name for name in tools 
                    if self._definitions[name].supports_streaming == supports_streaming]
        
        return sorted(tools)
    
    def get_tools_by_category(self) -> Dict[ToolCategory, List[str]]:
        """
        Get tools organized by category
        
        Returns:
            Dictionary mapping categories to tool names
        """
        result = {}
        for category, tool_names in self._categories.items():
            result[category] = sorted(list(tool_names))
        return result
    
    def get_tools_by_permission(self) -> Dict[ToolPermission, List[str]]:
        """
        Get tools organized by required permissions
        
        Returns:
            Dictionary mapping permissions to tool names
        """
        result = {}
        for permission, tool_names in self._permissions.items():
            result[permission] = sorted(list(tool_names))
        return result
    
    def search_tools(self, query: str) -> List[str]:
        """
        Search tools by name, description, or category
        
        Args:
            query: Search query string
            
        Returns:
            List of matching tool names
        """
        query_lower = query.lower()
        matches = []
        
        for tool_name, definition in self._definitions.items():
            # Search in name
            if query_lower in tool_name.lower():
                matches.append((tool_name, 3))  # High priority for name match
                continue
            
            # Search in description
            if query_lower in definition.description.lower():
                matches.append((tool_name, 2))  # Medium priority for description
                continue
            
            # Search in category
            if query_lower in definition.category.value.lower():
                matches.append((tool_name, 1))  # Low priority for category
        
        # Sort by priority (higher first) then by name
        matches.sort(key=lambda x: (-x[1], x[0]))
        
        return [match[0] for match in matches]
    
    def get_tool_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Get tool dependency and relationship graph
        
        Returns:
            Graph representation of tool relationships
        """
        graph = {}
        
        for tool_name, definition in self._definitions.items():
            graph[tool_name] = {
                'category': definition.category.value,
                'permissions': [p.value for p in definition.permissions],
                'related_tools': definition.see_also,
                'is_read_only': definition.is_read_only,
                'supports_streaming': definition.supports_streaming,
                'execution_time_hint': definition.typical_execution_time_ms
            }
        
        return graph
    
    def add_registration_hook(self, hook: Callable[[AgentTool], None]):
        """
        Add a hook that's called when tools are registered
        
        Args:
            hook: Function to call with registered tool
        """
        self._registration_hooks.append(hook)
    
    def add_execution_hook(self, hook: Callable[[str, Dict[str, Any]], None]):
        """
        Add a hook that's called when tools are executed
        
        Args:
            hook: Function to call with tool name and execution info
        """
        self._execution_hooks.append(hook)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics
        
        Returns:
            Dictionary with registry statistics
        """
        return {
            'total_tools': len(self._tools),
            'categories': {cat.value: len(tools) for cat, tools in self._categories.items()},
            'permissions': {perm.value: len(tools) for perm, tools in self._permissions.items()},
            'aliases': len(self._aliases),
            'registration_count': self._registration_count,
            'execution_count': self._execution_count,
            'last_discovery': self._last_discovery_time.isoformat() if self._last_discovery_time else None
        }
    
    def _validate_tool(self, tool: AgentTool):
        """
        Validate a tool before registration
        
        Args:
            tool: Tool to validate
            
        Raises:
            ToolRegistryError: If validation fails
        """
        # Check required methods
        required_methods = ['validate_input', 'check_permissions', 'execute']
        for method_name in required_methods:
            if not hasattr(tool, method_name):
                raise ToolRegistryError(
                    f"Tool missing required method: {method_name}",
                    tool_name=tool.name,
                    error_code="MISSING_METHOD"
                )
        
        # Check if execute method is async generator
        execute_method = getattr(tool, 'execute')
        if not inspect.ismethod(execute_method) and not inspect.isfunction(execute_method):
            raise ToolRegistryError(
                "Tool execute method must be callable",
                tool_name=tool.name,
                error_code="INVALID_EXECUTE_METHOD"
            )
        
        # Validate definition
        if not isinstance(tool.definition, ToolDefinition):
            raise ToolRegistryError(
                "Tool must have valid ToolDefinition",
                tool_name=tool.name,
                error_code="INVALID_DEFINITION"
            )


# Discovery functions

def discover_tools_in_module(module_path: str) -> List[Type[AgentTool]]:
    """
    Discover tool classes in a Python module
    
    Args:
        module_path: Python module path (e.g., 'package.module')
        
    Returns:
        List of discovered tool classes
    """
    try:
        module = importlib.import_module(module_path)
        tool_classes = []
        
        for name in dir(module):
            obj = getattr(module, name)
            
            # Check if it's a tool class (not the base class itself)
            if (inspect.isclass(obj) and 
                issubclass(obj, AgentTool) and 
                obj is not AgentTool):
                tool_classes.append(obj)
        
        logger.info(f"Discovered {len(tool_classes)} tools in {module_path}")
        return tool_classes
        
    except Exception as e:
        logger.error(f"Failed to discover tools in {module_path}: {e}")
        return []


def discover_tools_in_directory(directory_path: Path) -> List[Type[AgentTool]]:
    """
    Discover tool classes in a directory tree
    
    Args:
        directory_path: Path to directory to search
        
    Returns:
        List of discovered tool classes
    """
    tool_classes = []
    
    for py_file in directory_path.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        
        try:
            # Convert file path to module path
            relative_path = py_file.relative_to(directory_path.parent)
            module_path = str(relative_path.with_suffix("")).replace("/", ".")
            
            discovered = discover_tools_in_module(module_path)
            tool_classes.extend(discovered)
            
        except Exception as e:
            logger.warning(f"Failed to discover tools in {py_file}: {e}")
    
    return tool_classes


def auto_register_tools(registry: ToolRegistry, search_paths: List[str] = None) -> int:
    """
    Automatically discover and register tools
    
    Args:
        registry: Tool registry to register tools in
        search_paths: List of module paths to search
        
    Returns:
        Number of tools registered
    """
    if search_paths is None:
        search_paths = [
            "app.services.infrastructure.agents.tools.data",
            "app.services.infrastructure.agents.tools.system", 
            "app.services.infrastructure.agents.tools.ai"
        ]
    
    registered_count = 0
    
    for module_path in search_paths:
        try:
            tool_classes = discover_tools_in_module(module_path)
            
            for tool_class in tool_classes:
                try:
                    # Instantiate and register the tool
                    tool_instance = tool_class()
                    registry.register_tool(tool_instance)
                    registered_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to register tool {tool_class.__name__}: {e}")
        
        except Exception as e:
            logger.warning(f"Failed to process module {module_path}: {e}")
    
    registry._last_discovery_time = datetime.now(timezone.utc)
    logger.info(f"Auto-registered {registered_count} tools")
    
    return registered_count


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    
    if _global_registry is None:
        _global_registry = ToolRegistry()
        
        # Auto-discover and register tools
        try:
            auto_register_tools(_global_registry)
        except Exception as e:
            logger.warning(f"Auto-registration failed: {e}")
    
    return _global_registry


def register_tool(tool: AgentTool, aliases: List[str] = None) -> bool:
    """
    Register a tool with the global registry
    
    Args:
        tool: Tool to register
        aliases: Optional aliases
        
    Returns:
        True if registration successful
    """
    return get_tool_registry().register_tool(tool, aliases)


def get_available_tools(category: Optional[ToolCategory] = None) -> List[str]:
    """
    Get list of available tools
    
    Args:
        category: Optional category filter
        
    Returns:
        List of available tool names
    """
    return get_tool_registry().list_tools(category=category)


def discover_tools() -> int:
    """
    Trigger tool discovery and registration
    
    Returns:
        Number of newly discovered tools
    """
    registry = get_tool_registry()
    initial_count = len(registry._tools)
    
    auto_register_tools(registry)
    
    return len(registry._tools) - initial_count


__all__ = [
    "ToolRegistry", "ToolRegistryError",
    "discover_tools_in_module", "discover_tools_in_directory",
    "auto_register_tools", "get_tool_registry",
    "register_tool", "get_available_tools", "discover_tools"
]