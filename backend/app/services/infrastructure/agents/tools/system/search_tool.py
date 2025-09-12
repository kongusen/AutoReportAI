"""
Search and Content Discovery Tools
==================================

Comprehensive search tools for finding content, files, and patterns with advanced filtering.
"""

import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
import asyncio
import fnmatch
import mimetypes

from ..core.base import (
    AgentTool, StreamingAgentTool, ToolDefinition, ToolResult, 
    ToolExecutionContext, ToolCategory, ToolPriority, ToolPermission,
    ValidationError, ExecutionError, create_tool_definition
)
from ..core.permissions import SecurityLevel, ResourceType

logger = logging.getLogger(__name__)


# Input schemas
class FileSearchInput(BaseModel):
    """Input schema for file search operations"""
    search_path: str = Field(default=".", description="Path to search in")
    pattern: str = Field(..., description="Search pattern (supports glob patterns)")
    search_type: str = Field(default="filename", description="Search type: filename, content, or both")
    case_sensitive: bool = Field(default=False, description="Case sensitive search")
    include_hidden: bool = Field(default=False, description="Include hidden files and directories")
    recursive: bool = Field(default=True, description="Search recursively in subdirectories")
    max_depth: Optional[int] = Field(default=None, ge=1, le=20, description="Maximum search depth")
    file_types: Optional[List[str]] = Field(None, description="Filter by file extensions (e.g., ['.py', '.txt'])")
    exclude_patterns: Optional[List[str]] = Field(None, description="Patterns to exclude")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    
    @validator('search_type')
    def validate_search_type(cls, v):
        allowed_types = ['filename', 'content', 'both']
        if v not in allowed_types:
            raise ValueError(f"Search type must be one of: {allowed_types}")
        return v
    
    @validator('search_path')
    def validate_search_path(cls, v):
        # Security: prevent path traversal
        if '..' in v or v.startswith('/'):
            if v not in ['.', './']:  # Allow current directory
                raise ValueError("Path traversal or absolute paths not allowed")
        return v


class ContentSearchInput(BaseModel):
    """Input schema for content search within files"""
    search_path: str = Field(default=".", description="Path to search in")
    pattern: str = Field(..., min_length=1, description="Text pattern to search for")
    regex_mode: bool = Field(default=False, description="Treat pattern as regular expression")
    case_sensitive: bool = Field(default=False, description="Case sensitive search")
    whole_words: bool = Field(default=False, description="Match whole words only")
    context_lines: int = Field(default=0, ge=0, le=10, description="Number of context lines around matches")
    file_types: Optional[List[str]] = Field(None, description="Filter by file extensions")
    exclude_patterns: Optional[List[str]] = Field(None, description="File patterns to exclude")
    max_file_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum file size to search (MB)")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    
    @validator('pattern')
    def validate_pattern(cls, v):
        if not v.strip():
            raise ValueError("Search pattern cannot be empty")
        return v


class AdvancedSearchInput(BaseModel):
    """Input schema for advanced search with multiple criteria"""
    search_path: str = Field(default=".", description="Path to search in")
    criteria: Dict[str, Any] = Field(..., description="Search criteria dictionary")
    sort_by: str = Field(default="name", description="Sort results by: name, size, modified, relevance")
    sort_order: str = Field(default="asc", description="Sort order: asc or desc")
    group_by: Optional[str] = Field(None, description="Group results by: type, directory, size")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed_sorts = ['name', 'size', 'modified', 'created', 'relevance', 'type']
        if v not in allowed_sorts:
            raise ValueError(f"Sort by must be one of: {allowed_sorts}")
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v


class SearchTool(StreamingAgentTool):
    """
    Comprehensive search tool for files and content discovery
    """
    
    def __init__(self):
        definition = create_tool_definition(
            name="search_tool",
            description="Search for files and content with advanced filtering and pattern matching",
            category=ToolCategory.SYSTEM,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.READ_ONLY],
            input_schema=FileSearchInput,  # Primary schema
            is_read_only=True,
            supports_streaming=True,
            typical_execution_time_ms=3000,
            examples=[
                {
                    "pattern": "*.py",
                    "search_type": "filename",
                    "search_path": "./src"
                },
                {
                    "pattern": "TODO",
                    "search_type": "content",
                    "file_types": [".py", ".js"]
                }
            ],
            limitations=[
                "Limited to working directory and subdirectories",
                "Large files may be skipped for content search",
                "Binary files are excluded from content search",
                "Search depth is limited for performance"
            ]
        )
        super().__init__(definition)
        
        # Search settings
        self.working_dir = Path.cwd()
        self.max_file_size_bytes = 100 * 1024 * 1024  # 100MB
        self.binary_extensions = {
            '.exe', '.bin', '.dll', '.so', '.dylib', '.zip', '.tar', '.gz',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
            '.mp4', '.avi', '.mov', '.mp3', '.wav', '.pdf', '.doc', '.docx'
        }
        
        # Search statistics
        self.search_stats = {
            'files_scanned': 0,
            'matches_found': 0,
            'errors_encountered': 0
        }
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """Validate search input"""
        search_operation = input_data.get('operation', 'file_search')
        
        try:
            if search_operation == 'file_search':
                validated = FileSearchInput(**input_data)
            elif search_operation == 'content_search':
                validated = ContentSearchInput(**input_data)
            elif search_operation == 'advanced_search':
                validated = AdvancedSearchInput(**input_data)
            else:
                # Default to file search
                validated = FileSearchInput(**{k: v for k, v in input_data.items() if k in FileSearchInput.__fields__})
            
            result = validated.dict()
            result['operation'] = search_operation
            return result
            
        except Exception as e:
            raise ValidationError(f"Invalid input for search tool: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """Check permissions for search operations"""
        # All search operations are read-only
        return ToolPermission.READ_ONLY in context.permissions
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Execute search operations with streaming progress"""
        
        operation = input_data.get('operation', 'file_search')
        
        # Reset search statistics
        self.search_stats = {
            'files_scanned': 0,
            'matches_found': 0,
            'errors_encountered': 0
        }
        
        try:
            if operation == 'file_search':
                async for result in self._handle_file_search(input_data, context):
                    yield result
            elif operation == 'content_search':
                async for result in self._handle_content_search(input_data, context):
                    yield result
            elif operation == 'advanced_search':
                async for result in self._handle_advanced_search(input_data, context):
                    yield result
            else:
                raise ExecutionError(f"Unsupported search operation: {operation}", tool_name=self.name)
                
        except Exception as e:
            raise ExecutionError(f"Search operation failed: {e}", tool_name=self.name)
    
    async def _handle_file_search(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle file name pattern search"""
        
        search_path = input_data['search_path']
        pattern = input_data['pattern']
        search_type = input_data['search_type']
        case_sensitive = input_data['case_sensitive']
        include_hidden = input_data['include_hidden']
        recursive = input_data['recursive']
        max_depth = input_data.get('max_depth')
        file_types = input_data.get('file_types', [])
        exclude_patterns = input_data.get('exclude_patterns', [])
        max_results = input_data['max_results']
        
        # Phase 1: Validate search path
        yield await self.stream_progress({
            'status': 'validating',
            'message': 'Validating search parameters...',
            'progress': 10
        }, context)
        
        search_dir = await self._validate_and_resolve_path(search_path)
        
        # Phase 2: Search execution
        yield await self.stream_progress({
            'status': 'searching',
            'message': f'Searching for pattern: {pattern}',
            'progress': 30
        }, context)
        
        matches = []
        
        try:
            if recursive:
                search_paths = self._walk_directory(
                    search_dir, 
                    include_hidden, 
                    max_depth,
                    exclude_patterns
                )
            else:
                search_paths = [item for item in search_dir.iterdir() if item.is_file()]
            
            processed_count = 0
            total_estimate = len(list(search_paths)) if not recursive else None
            
            async for file_path in self._async_file_iterator(search_paths):
                processed_count += 1
                self.search_stats['files_scanned'] += 1
                
                # Stream progress periodically
                if processed_count % 50 == 0:
                    yield await self.stream_progress({
                        'status': 'searching',
                        'message': f'Processed {processed_count} files...',
                        'progress': 30 + min(50, (processed_count / (total_estimate or max_results)) * 50)
                    }, context)
                
                try:
                    # Check file type filter
                    if file_types and file_path.suffix.lower() not in file_types:
                        continue
                    
                    # Check if file matches pattern
                    match_result = await self._check_file_match(
                        file_path, pattern, search_type, case_sensitive
                    )
                    
                    if match_result['matches']:
                        match_info = {
                            'file_path': str(file_path.relative_to(self.working_dir)),
                            'full_path': str(file_path),
                            'file_name': file_path.name,
                            'file_size': file_path.stat().st_size if file_path.exists() else 0,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat(),
                            'file_type': file_path.suffix.lower(),
                            'match_type': match_result['match_type'],
                            'match_details': match_result.get('details', {})
                        }
                        
                        matches.append(match_info)
                        self.search_stats['matches_found'] += 1
                        
                        # Stop if we reached max results
                        if len(matches) >= max_results:
                            break
                
                except Exception as e:
                    self.search_stats['errors_encountered'] += 1
                    logger.debug(f"Error processing {file_path}: {e}")
                    continue
        
        except Exception as e:
            raise ExecutionError(f"File search failed: {e}", tool_name=self.name)
        
        # Phase 3: Results processing
        yield await self.stream_progress({
            'status': 'processing',
            'message': 'Processing search results...',
            'progress': 80
        }, context)
        
        # Sort results by relevance and name
        matches.sort(key=lambda x: (x['file_name'].lower(), x['file_size']))
        
        result_data = {
            'operation': 'file_search',
            'search_path': str(search_dir.relative_to(self.working_dir)),
            'pattern': pattern,
            'search_type': search_type,
            'matches': matches,
            'total_matches': len(matches),
            'truncated': len(matches) >= max_results,
            'search_stats': self.search_stats,
            'search_parameters': {
                'case_sensitive': case_sensitive,
                'include_hidden': include_hidden,
                'recursive': recursive,
                'file_types': file_types,
                'exclude_patterns': exclude_patterns
            }
        }
        
        yield await self.stream_final_result(result_data, context)
    
    async def _handle_content_search(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle content search within files"""
        
        search_path = input_data['search_path']
        pattern = input_data['pattern']
        regex_mode = input_data['regex_mode']
        case_sensitive = input_data['case_sensitive']
        whole_words = input_data['whole_words']
        context_lines = input_data['context_lines']
        file_types = input_data.get('file_types', [])
        exclude_patterns = input_data.get('exclude_patterns', [])
        max_file_size_mb = input_data['max_file_size_mb']
        max_results = input_data['max_results']
        
        # Phase 1: Prepare search
        yield await self.stream_progress({
            'status': 'preparing',
            'message': 'Preparing content search...',
            'progress': 10
        }, context)
        
        search_dir = await self._validate_and_resolve_path(search_path)
        
        # Compile regex pattern
        try:
            if regex_mode:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(pattern, flags)
            else:
                # Escape special regex characters for literal search
                escaped_pattern = re.escape(pattern)
                if whole_words:
                    escaped_pattern = r'\b' + escaped_pattern + r'\b'
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(escaped_pattern, flags)
        except re.error as e:
            raise ExecutionError(f"Invalid regex pattern: {e}", tool_name=self.name)
        
        # Phase 2: Content search
        yield await self.stream_progress({
            'status': 'searching',
            'message': f'Searching content for: {pattern}',
            'progress': 30
        }, context)
        
        matches = []
        max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
        try:
            search_paths = self._walk_directory(search_dir, False, None, exclude_patterns)
            
            processed_count = 0
            
            async for file_path in self._async_file_iterator(search_paths):
                processed_count += 1
                self.search_stats['files_scanned'] += 1
                
                # Stream progress periodically
                if processed_count % 20 == 0:
                    yield await self.stream_progress({
                        'status': 'searching',
                        'message': f'Searched {processed_count} files, found {len(matches)} matches...',
                        'progress': 30 + min(50, processed_count / 100)
                    }, context)
                
                try:
                    # Skip if not a regular file
                    if not file_path.is_file():
                        continue
                    
                    # Check file type filter
                    if file_types and file_path.suffix.lower() not in file_types:
                        continue
                    
                    # Check file size
                    file_size = file_path.stat().st_size
                    if file_size > max_file_size_bytes:
                        continue
                    
                    # Skip binary files
                    if file_path.suffix.lower() in self.binary_extensions:
                        continue
                    
                    # Search content
                    file_matches = await self._search_file_content(
                        file_path, compiled_pattern, context_lines
                    )
                    
                    if file_matches:
                        match_info = {
                            'file_path': str(file_path.relative_to(self.working_dir)),
                            'file_name': file_path.name,
                            'file_size': file_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat(),
                            'match_count': len(file_matches),
                            'matches': file_matches
                        }
                        
                        matches.append(match_info)
                        self.search_stats['matches_found'] += len(file_matches)
                        
                        # Stop if we reached max results
                        if len(matches) >= max_results:
                            break
                
                except Exception as e:
                    self.search_stats['errors_encountered'] += 1
                    logger.debug(f"Error searching content in {file_path}: {e}")
                    continue
        
        except Exception as e:
            raise ExecutionError(f"Content search failed: {e}", tool_name=self.name)
        
        # Phase 3: Results processing
        yield await self.stream_progress({
            'status': 'processing',
            'message': 'Processing search results...',
            'progress': 80
        }, context)
        
        # Sort by match count and file name
        matches.sort(key=lambda x: (-x['match_count'], x['file_name'].lower()))
        
        result_data = {
            'operation': 'content_search',
            'search_path': str(search_dir.relative_to(self.working_dir)),
            'pattern': pattern,
            'regex_mode': regex_mode,
            'files_with_matches': matches,
            'total_files_with_matches': len(matches),
            'total_individual_matches': sum(match['match_count'] for match in matches),
            'truncated': len(matches) >= max_results,
            'search_stats': self.search_stats,
            'search_parameters': {
                'case_sensitive': case_sensitive,
                'whole_words': whole_words,
                'context_lines': context_lines,
                'file_types': file_types,
                'max_file_size_mb': max_file_size_mb
            }
        }
        
        yield await self.stream_final_result(result_data, context)
    
    async def _handle_advanced_search(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle advanced search with multiple criteria"""
        
        search_path = input_data['search_path']
        criteria = input_data['criteria']
        sort_by = input_data['sort_by']
        sort_order = input_data['sort_order']
        group_by = input_data.get('group_by')
        max_results = input_data['max_results']
        
        # Phase 1: Prepare advanced search
        yield await self.stream_progress({
            'status': 'preparing',
            'message': 'Preparing advanced search...',
            'progress': 10
        }, context)
        
        search_dir = await self._validate_and_resolve_path(search_path)
        
        # Parse and validate criteria
        search_criteria = await self._parse_search_criteria(criteria)
        
        # Phase 2: Advanced search execution
        yield await self.stream_progress({
            'status': 'searching',
            'message': 'Executing advanced search...',
            'progress': 30
        }, context)
        
        matches = []
        
        try:
            search_paths = self._walk_directory(search_dir, False, None, [])
            
            processed_count = 0
            
            async for file_path in self._async_file_iterator(search_paths):
                processed_count += 1
                self.search_stats['files_scanned'] += 1
                
                # Stream progress periodically
                if processed_count % 30 == 0:
                    yield await self.stream_progress({
                        'status': 'searching',
                        'message': f'Evaluated {processed_count} files...',
                        'progress': 30 + min(50, processed_count / 200)
                    }, context)
                
                try:
                    # Evaluate file against all criteria
                    match_result = await self._evaluate_file_criteria(file_path, search_criteria)
                    
                    if match_result['matches']:
                        file_info = await self._get_detailed_file_info(file_path)
                        file_info.update({
                            'match_score': match_result['score'],
                            'matching_criteria': match_result['matching_criteria']
                        })
                        
                        matches.append(file_info)
                        self.search_stats['matches_found'] += 1
                        
                        # Stop if we reached max results
                        if len(matches) >= max_results:
                            break
                
                except Exception as e:
                    self.search_stats['errors_encountered'] += 1
                    logger.debug(f"Error evaluating {file_path}: {e}")
                    continue
        
        except Exception as e:
            raise ExecutionError(f"Advanced search failed: {e}", tool_name=self.name)
        
        # Phase 3: Sort and group results
        yield await self.stream_progress({
            'status': 'processing',
            'message': 'Sorting and grouping results...',
            'progress': 80
        }, context)
        
        # Sort results
        matches = await self._sort_results(matches, sort_by, sort_order)
        
        # Group results if requested
        grouped_results = None
        if group_by:
            grouped_results = await self._group_results(matches, group_by)
        
        result_data = {
            'operation': 'advanced_search',
            'search_path': str(search_dir.relative_to(self.working_dir)),
            'criteria': criteria,
            'matches': matches,
            'grouped_results': grouped_results,
            'total_matches': len(matches),
            'truncated': len(matches) >= max_results,
            'search_stats': self.search_stats,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'group_by': group_by
        }
        
        yield await self.stream_final_result(result_data, context)
    
    async def _validate_and_resolve_path(self, path_str: str) -> Path:
        """Validate and resolve search path"""
        
        path = Path(path_str)
        
        # Ensure it's within working directory
        if path.is_absolute():
            raise ExecutionError("Absolute paths not allowed for search", tool_name=self.name)
        
        # Resolve relative to working directory
        full_path = (self.working_dir / path).resolve()
        
        # Security check
        try:
            full_path.relative_to(self.working_dir)
        except ValueError:
            raise ExecutionError("Path traversal detected in search path", tool_name=self.name)
        
        if not full_path.exists():
            raise ExecutionError(f"Search path does not exist: {path}", tool_name=self.name)
        
        return full_path
    
    def _walk_directory(self, directory: Path, include_hidden: bool, max_depth: Optional[int], exclude_patterns: List[str]) -> AsyncGenerator[Path, None]:
        """Walk directory tree and yield file paths"""
        
        def _should_exclude(path: Path) -> bool:
            """Check if path should be excluded"""
            path_str = str(path)
            
            # Check exclude patterns
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(path.name, pattern):
                    return True
            
            # Check hidden files
            if not include_hidden and path.name.startswith('.'):
                return True
            
            return False
        
        async def _walk_recursive(dir_path: Path, current_depth: int = 0):
            """Recursive directory walking"""
            if max_depth is not None and current_depth > max_depth:
                return
            
            try:
                for item in dir_path.iterdir():
                    if _should_exclude(item):
                        continue
                    
                    if item.is_file():
                        yield item
                    elif item.is_dir():
                        async for sub_item in _walk_recursive(item, current_depth + 1):
                            yield sub_item
                            
            except (PermissionError, OSError) as e:
                logger.debug(f"Cannot access directory {dir_path}: {e}")
        
        return _walk_recursive(directory)
    
    async def _async_file_iterator(self, file_paths):
        """Convert file paths to async iterator"""
        if hasattr(file_paths, '__aiter__'):
            async for path in file_paths:
                yield path
        else:
            for path in file_paths:
                yield path
    
    async def _check_file_match(self, file_path: Path, pattern: str, search_type: str, case_sensitive: bool) -> Dict[str, Any]:
        """Check if file matches the search pattern"""
        
        result = {
            'matches': False,
            'match_type': None,
            'details': {}
        }
        
        filename = file_path.name
        if not case_sensitive:
            filename = filename.lower()
            pattern = pattern.lower()
        
        if search_type in ['filename', 'both']:
            # Check filename pattern
            if fnmatch.fnmatch(filename, pattern) or pattern in filename:
                result['matches'] = True
                result['match_type'] = 'filename'
                result['details']['filename_match'] = True
        
        if search_type in ['content', 'both'] and not result['matches']:
            # Check file content (basic check for text files)
            if file_path.suffix.lower() not in self.binary_extensions:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # Read first chunk to check for pattern
                        chunk = f.read(8192)
                        if not case_sensitive:
                            chunk = chunk.lower()
                        
                        if pattern in chunk:
                            result['matches'] = True
                            result['match_type'] = 'content'
                            result['details']['content_match'] = True
                
                except Exception:
                    # Skip files that can't be read
                    pass
        
        return result
    
    async def _search_file_content(self, file_path: Path, pattern: re.Pattern, context_lines: int) -> List[Dict[str, Any]]:
        """Search for pattern within file content"""
        
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for match in pattern.finditer(line):
                    match_info = {
                        'line_number': line_num,
                        'line_content': line.rstrip('\n\r'),
                        'match_start': match.start(),
                        'match_end': match.end(),
                        'matched_text': match.group()
                    }
                    
                    # Add context lines if requested
                    if context_lines > 0:
                        start_line = max(0, line_num - context_lines - 1)
                        end_line = min(len(lines), line_num + context_lines)
                        
                        context = []
                        for i in range(start_line, end_line):
                            context.append({
                                'line_number': i + 1,
                                'line_content': lines[i].rstrip('\n\r'),
                                'is_match_line': i + 1 == line_num
                            })
                        
                        match_info['context'] = context
                    
                    matches.append(match_info)
        
        except Exception as e:
            logger.debug(f"Error searching content in {file_path}: {e}")
        
        return matches
    
    async def _parse_search_criteria(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate advanced search criteria"""
        
        parsed_criteria = {}
        
        # File size criteria
        if 'size' in criteria:
            size_spec = criteria['size']
            if isinstance(size_spec, dict):
                parsed_criteria['size'] = size_spec
            else:
                # Parse size strings like ">1MB", "<100KB"
                parsed_criteria['size'] = self._parse_size_criterion(size_spec)
        
        # Date criteria
        if 'modified' in criteria:
            parsed_criteria['modified'] = self._parse_date_criterion(criteria['modified'])
        
        if 'created' in criteria:
            parsed_criteria['created'] = self._parse_date_criterion(criteria['created'])
        
        # Name pattern
        if 'name' in criteria:
            parsed_criteria['name'] = criteria['name']
        
        # File type
        if 'type' in criteria:
            parsed_criteria['type'] = criteria['type']
        
        # Content search
        if 'content' in criteria:
            parsed_criteria['content'] = criteria['content']
        
        return parsed_criteria
    
    def _parse_size_criterion(self, size_spec: str) -> Dict[str, Any]:
        """Parse size specification like '>1MB', '<100KB'"""
        
        import re
        
        # Pattern: operator + number + unit
        match = re.match(r'([<>=!]+)(\d+(?:\.\d+)?)([KMGT]?B?)', size_spec.upper())
        
        if not match:
            return {'operator': '>', 'value': 0, 'unit': 'B'}
        
        operator, value, unit = match.groups()
        
        # Convert to bytes
        multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        multiplier = multipliers.get(unit, 1)
        
        return {
            'operator': operator,
            'value': float(value) * multiplier,
            'unit': unit,
            'original': size_spec
        }
    
    def _parse_date_criterion(self, date_spec: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Parse date specification"""
        
        if isinstance(date_spec, dict):
            return date_spec
        
        # Parse relative dates like "7 days ago", "1 week ago"
        # This is a simplified implementation
        return {'type': 'relative', 'spec': date_spec}
    
    async def _evaluate_file_criteria(self, file_path: Path, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate file against search criteria"""
        
        result = {
            'matches': True,
            'score': 0,
            'matching_criteria': []
        }
        
        try:
            file_stat = file_path.stat()
            
            # Check size criteria
            if 'size' in criteria:
                size_criterion = criteria['size']
                file_size = file_stat.st_size
                
                if self._check_size_criterion(file_size, size_criterion):
                    result['score'] += 10
                    result['matching_criteria'].append('size')
                else:
                    result['matches'] = False
            
            # Check name criteria
            if 'name' in criteria:
                name_pattern = criteria['name']
                if fnmatch.fnmatch(file_path.name.lower(), name_pattern.lower()):
                    result['score'] += 20
                    result['matching_criteria'].append('name')
                else:
                    result['matches'] = False
            
            # Check file type
            if 'type' in criteria:
                file_type = criteria['type']
                if file_path.suffix.lower() == file_type.lower():
                    result['score'] += 15
                    result['matching_criteria'].append('type')
                else:
                    result['matches'] = False
            
            # Check modified date
            if 'modified' in criteria:
                modified_criterion = criteria['modified']
                if self._check_date_criterion(file_stat.st_mtime, modified_criterion):
                    result['score'] += 5
                    result['matching_criteria'].append('modified')
                else:
                    result['matches'] = False
        
        except Exception as e:
            logger.debug(f"Error evaluating criteria for {file_path}: {e}")
            result['matches'] = False
        
        return result
    
    def _check_size_criterion(self, file_size: int, size_criterion: Dict[str, Any]) -> bool:
        """Check if file size matches criterion"""
        
        operator = size_criterion['operator']
        threshold = size_criterion['value']
        
        if operator == '>':
            return file_size > threshold
        elif operator == '<':
            return file_size < threshold
        elif operator == '>=':
            return file_size >= threshold
        elif operator == '<=':
            return file_size <= threshold
        elif operator == '=' or operator == '==':
            return abs(file_size - threshold) < threshold * 0.1  # 10% tolerance
        elif operator == '!=' or operator == '!':
            return abs(file_size - threshold) >= threshold * 0.1
        
        return True
    
    def _check_date_criterion(self, file_timestamp: float, date_criterion: Dict[str, Any]) -> bool:
        """Check if file date matches criterion"""
        
        # Simplified date checking
        # In a full implementation, this would handle various date formats and operations
        return True
    
    async def _get_detailed_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get detailed information about a file"""
        
        try:
            stat = file_path.stat()
            
            info = {
                'file_path': str(file_path.relative_to(self.working_dir)),
                'file_name': file_path.name,
                'file_size': stat.st_size,
                'file_type': file_path.suffix.lower(),
                'modified': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
                'is_file': file_path.is_file(),
                'is_directory': file_path.is_dir(),
                'permissions': oct(stat.st_mode)[-3:]
            }
            
            # Add MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            info['mime_type'] = mime_type
            
            return info
        
        except Exception as e:
            logger.debug(f"Error getting file info for {file_path}: {e}")
            return {
                'file_path': str(file_path.relative_to(self.working_dir)),
                'file_name': file_path.name,
                'error': str(e)
            }
    
    async def _sort_results(self, matches: List[Dict[str, Any]], sort_by: str, sort_order: str) -> List[Dict[str, Any]]:
        """Sort search results"""
        
        reverse = sort_order == 'desc'
        
        if sort_by == 'name':
            key_func = lambda x: x.get('file_name', '').lower()
        elif sort_by == 'size':
            key_func = lambda x: x.get('file_size', 0)
        elif sort_by == 'modified':
            key_func = lambda x: x.get('modified', '')
        elif sort_by == 'created':
            key_func = lambda x: x.get('created', '')
        elif sort_by == 'relevance':
            key_func = lambda x: x.get('match_score', 0)
        elif sort_by == 'type':
            key_func = lambda x: x.get('file_type', '')
        else:
            key_func = lambda x: x.get('file_name', '').lower()
        
        return sorted(matches, key=key_func, reverse=reverse)
    
    async def _group_results(self, matches: List[Dict[str, Any]], group_by: str) -> Dict[str, List[Dict[str, Any]]]:
        """Group search results"""
        
        groups = {}
        
        for match in matches:
            if group_by == 'type':
                key = match.get('file_type', 'unknown')
            elif group_by == 'directory':
                key = str(Path(match.get('file_path', '')).parent)
            elif group_by == 'size':
                size = match.get('file_size', 0)
                if size < 1024:
                    key = 'small (<1KB)'
                elif size < 1024**2:
                    key = 'medium (<1MB)'
                elif size < 1024**3:
                    key = 'large (<1GB)'
                else:
                    key = 'very_large (>=1GB)'
            else:
                key = 'all'
            
            if key not in groups:
                groups[key] = []
            groups[key].append(match)
        
        return groups


__all__ = ["SearchTool"]