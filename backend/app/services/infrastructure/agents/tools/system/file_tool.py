"""
File System Tools
=================

Safe file system operations with permission checks and security validations.
"""

import logging
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
import aiofiles
import asyncio
from hashlib import sha256

from ..core.base import (
    AgentTool, StreamingAgentTool, ToolDefinition, ToolResult, 
    ToolExecutionContext, ToolCategory, ToolPriority, ToolPermission,
    ValidationError, ExecutionError, create_tool_definition
)
from ..core.permissions import SecurityLevel, ResourceType

logger = logging.getLogger(__name__)


# Input schemas
class FileReadInput(BaseModel):
    """Input schema for file reading operations"""
    file_path: str = Field(..., description="Path to the file to read")
    encoding: str = Field(default="utf-8", description="File encoding")
    max_size_mb: Optional[int] = Field(default=10, ge=1, le=100, description="Maximum file size to read (MB)")
    binary_mode: bool = Field(default=False, description="Read file in binary mode")
    
    @validator('file_path')
    def validate_file_path(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("File path cannot be empty")
        
        # Security: prevent path traversal
        if '..' in v or v.startswith('/'):
            raise ValueError("Path traversal or absolute paths not allowed")
        
        return v.strip()


class FileWriteInput(BaseModel):
    """Input schema for file writing operations"""
    file_path: str = Field(..., description="Path to the file to write")
    content: Union[str, bytes] = Field(..., description="Content to write to file")
    encoding: str = Field(default="utf-8", description="File encoding")
    create_dirs: bool = Field(default=True, description="Create parent directories if they don't exist")
    backup_existing: bool = Field(default=True, description="Backup existing file before overwriting")
    binary_mode: bool = Field(default=False, description="Write file in binary mode")
    
    @validator('file_path')
    def validate_file_path(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("File path cannot be empty")
        
        # Security: prevent path traversal
        if '..' in v or v.startswith('/'):
            raise ValueError("Path traversal or absolute paths not allowed")
        
        return v.strip()


class DirectoryOperationInput(BaseModel):
    """Input schema for directory operations"""
    directory_path: str = Field(..., description="Path to the directory")
    operation: str = Field(..., description="Operation to perform (list, create, delete, copy, move)")
    target_path: Optional[str] = Field(None, description="Target path for copy/move operations")
    recursive: bool = Field(default=False, description="Apply operation recursively")
    include_hidden: bool = Field(default=False, description="Include hidden files/directories")
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_ops = ['list', 'create', 'delete', 'copy', 'move']
        if v not in allowed_ops:
            raise ValueError(f"Operation must be one of: {allowed_ops}")
        return v
    
    @validator('directory_path')
    def validate_directory_path(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Directory path cannot be empty")
        
        # Security: prevent path traversal
        if '..' in v or v.startswith('/'):
            raise ValueError("Path traversal or absolute paths not allowed")
        
        return v.strip()


class FileOperationTool(StreamingAgentTool):
    """
    Safe file system operations with comprehensive security checks
    """
    
    def __init__(self):
        definition = create_tool_definition(
            name="file_operation",
            description="Perform safe file system operations with security checks",
            category=ToolCategory.SYSTEM,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.READ_ONLY, ToolPermission.WRITE_LIMITED],
            input_schema=FileReadInput,  # Primary schema, others handled in validation
            is_read_only=False,
            supports_streaming=True,
            typical_execution_time_ms=1000,
            examples=[
                {
                    "file_path": "data/report.txt",
                    "operation": "read"
                },
                {
                    "file_path": "output/results.json",
                    "content": '{"key": "value"}',
                    "operation": "write"
                }
            ],
            limitations=[
                "Limited to working directory and subdirectories",
                "File size limits apply",
                "Binary files have special handling",
                "Backup files are created automatically"
            ]
        )
        super().__init__(definition)
        
        # Working directory restriction
        self.working_dir = Path.cwd()
        self.max_file_size_bytes = 100 * 1024 * 1024  # 100MB
        self.backup_dir = self.working_dir / ".file_backups"
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True)
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """Validate file operation input"""
        operation = input_data.get('operation', 'read')
        
        try:
            if operation in ['read', 'info', 'exists']:
                validated = FileReadInput(**input_data)
            elif operation in ['write', 'append']:
                validated = FileWriteInput(**input_data)
            elif operation in ['list', 'create_dir', 'delete_dir', 'copy_dir', 'move_dir']:
                validated = DirectoryOperationInput(**input_data)
            else:
                # Generic validation for other operations
                if 'file_path' not in input_data:
                    raise ValueError("file_path is required")
                validated = FileReadInput(**{k: v for k, v in input_data.items() if k in FileReadInput.__fields__})
            
            result = validated.dict()
            result['operation'] = operation
            return result
            
        except Exception as e:
            raise ValidationError(f"Invalid input for file operation: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """Check permissions for file operations"""
        operation = input_data.get('operation', 'read')
        file_path = input_data.get('file_path', '')
        
        # Read operations
        if operation in ['read', 'info', 'exists', 'list']:
            return ToolPermission.READ_ONLY in context.permissions
        
        # Write operations
        if operation in ['write', 'append', 'delete', 'copy', 'move', 'create_dir', 'delete_dir']:
            return ToolPermission.WRITE_LIMITED in context.permissions
        
        return False
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Execute file system operations with streaming progress"""
        
        operation = input_data['operation']
        file_path = input_data.get('file_path', '')
        
        # Validate path security
        safe_path = await self._validate_and_resolve_path(file_path)
        
        # Phase 1: Security validation
        yield await self.stream_progress({
            'status': 'validating',
            'message': f'Validating {operation} operation on {file_path}...',
            'progress': 10
        }, context)
        
        security_check = await self._security_check(safe_path, operation, context)
        if not security_check['allowed']:
            raise ExecutionError(f"Security check failed: {security_check['reason']}", tool_name=self.name)
        
        # Route to specific operation
        try:
            if operation == 'read':
                async for result in self._handle_file_read(safe_path, input_data, context):
                    yield result
            elif operation == 'write':
                async for result in self._handle_file_write(safe_path, input_data, context):
                    yield result
            elif operation == 'append':
                async for result in self._handle_file_append(safe_path, input_data, context):
                    yield result
            elif operation == 'delete':
                async for result in self._handle_file_delete(safe_path, input_data, context):
                    yield result
            elif operation == 'copy':
                async for result in self._handle_file_copy(safe_path, input_data, context):
                    yield result
            elif operation == 'move':
                async for result in self._handle_file_move(safe_path, input_data, context):
                    yield result
            elif operation == 'info':
                async for result in self._handle_file_info(safe_path, input_data, context):
                    yield result
            elif operation == 'exists':
                async for result in self._handle_file_exists(safe_path, input_data, context):
                    yield result
            elif operation in ['list', 'create_dir', 'delete_dir']:
                async for result in self._handle_directory_operation(safe_path, input_data, context):
                    yield result
            else:
                raise ExecutionError(f"Unsupported operation: {operation}", tool_name=self.name)
                
        except Exception as e:
            raise ExecutionError(f"File operation failed: {e}", tool_name=self.name)
    
    async def _validate_and_resolve_path(self, file_path: str) -> Path:
        """Validate and resolve file path to ensure security"""
        
        # Convert to Path and resolve
        path = Path(file_path)
        
        # Ensure it's relative and within working directory
        if path.is_absolute():
            raise ExecutionError("Absolute paths not allowed", tool_name=self.name)
        
        # Resolve relative to working directory
        full_path = (self.working_dir / path).resolve()
        
        # Security: ensure resolved path is still within working directory
        try:
            full_path.relative_to(self.working_dir)
        except ValueError:
            raise ExecutionError("Path traversal detected - access denied", tool_name=self.name)
        
        return full_path
    
    async def _security_check(self, path: Path, operation: str, context: ToolExecutionContext) -> Dict[str, Any]:
        """Perform security checks on file operations"""
        
        # Check for sensitive files
        sensitive_patterns = [
            r'\.env$', r'\.key$', r'\.pem$', r'\.p12$', r'password', 
            r'secret', r'token', r'config\.py$', r'settings\.py$'
        ]
        
        path_str = str(path).lower()
        
        for pattern in sensitive_patterns:
            import re
            if re.search(pattern, path_str):
                return {
                    'allowed': False,
                    'reason': f"Access to potentially sensitive file blocked: {path.name}"
                }
        
        # Check file size for read operations
        if operation in ['read', 'copy'] and path.exists() and path.is_file():
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_file_size_bytes / (1024 * 1024):
                return {
                    'allowed': False,
                    'reason': f"File too large: {size_mb:.1f}MB (limit: {self.max_file_size_bytes / (1024 * 1024)}MB)"
                }
        
        # Check write permissions
        if operation in ['write', 'append', 'delete', 'move'] and not context.permissions:
            return {
                'allowed': False,
                'reason': "Insufficient permissions for write operation"
            }
        
        return {'allowed': True, 'reason': 'Security check passed'}
    
    async def _handle_file_read(self, path: Path, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle file read operations"""
        
        if not path.exists():
            raise ExecutionError(f"File not found: {path}", tool_name=self.name)
        
        if not path.is_file():
            raise ExecutionError(f"Path is not a file: {path}", tool_name=self.name)
        
        # Phase 2: Reading file
        yield await self.stream_progress({
            'status': 'reading',
            'message': f'Reading file {path.name}...',
            'progress': 30
        }, context)
        
        binary_mode = input_data.get('binary_mode', False)
        encoding = input_data.get('encoding', 'utf-8')
        
        try:
            if binary_mode:
                # Read binary file
                with open(path, 'rb') as f:
                    content = f.read()
                
                result_data = {
                    'operation': 'read',
                    'file_path': str(path.relative_to(self.working_dir)),
                    'content': content.hex(),  # Hex representation for binary
                    'binary_mode': True,
                    'size_bytes': len(content),
                    'file_info': await self._get_file_info(path)
                }
            else:
                # Read text file
                async with aiofiles.open(path, 'r', encoding=encoding) as f:
                    content = await f.read()
                
                result_data = {
                    'operation': 'read',
                    'file_path': str(path.relative_to(self.working_dir)),
                    'content': content,
                    'binary_mode': False,
                    'encoding': encoding,
                    'size_bytes': len(content.encode(encoding)),
                    'line_count': len(content.splitlines()),
                    'file_info': await self._get_file_info(path)
                }
            
            yield await self.stream_final_result(result_data, context)
            
        except UnicodeDecodeError as e:
            raise ExecutionError(f"File encoding error: {e}. Try binary_mode=true", tool_name=self.name)
        except Exception as e:
            raise ExecutionError(f"Failed to read file: {e}", tool_name=self.name)
    
    async def _handle_file_write(self, path: Path, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle file write operations"""
        
        content = input_data['content']
        binary_mode = input_data.get('binary_mode', False)
        encoding = input_data.get('encoding', 'utf-8')
        create_dirs = input_data.get('create_dirs', True)
        backup_existing = input_data.get('backup_existing', True)
        
        # Phase 2: Preparing write
        yield await self.stream_progress({
            'status': 'preparing',
            'message': f'Preparing to write {path.name}...',
            'progress': 30
        }, context)
        
        # Create parent directories if needed
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup existing file
        backup_path = None
        if backup_existing and path.exists():
            backup_path = await self._create_backup(path)
        
        # Phase 3: Writing file
        yield await self.stream_progress({
            'status': 'writing',
            'message': f'Writing content to {path.name}...',
            'progress': 60
        }, context)
        
        try:
            if binary_mode:
                # Handle binary content
                if isinstance(content, str):
                    # Assume hex-encoded binary data
                    content = bytes.fromhex(content)
                
                with open(path, 'wb') as f:
                    f.write(content)
                
                size_bytes = len(content)
            else:
                # Handle text content
                async with aiofiles.open(path, 'w', encoding=encoding) as f:
                    await f.write(content)
                
                size_bytes = len(content.encode(encoding))
            
            # Phase 4: Verification
            yield await self.stream_progress({
                'status': 'verifying',
                'message': 'Verifying written content...',
                'progress': 80
            }, context)
            
            # Verify file was written correctly
            if not path.exists():
                raise ExecutionError("File write verification failed", tool_name=self.name)
            
            result_data = {
                'operation': 'write',
                'file_path': str(path.relative_to(self.working_dir)),
                'size_bytes': size_bytes,
                'binary_mode': binary_mode,
                'backup_created': backup_path is not None,
                'backup_path': str(backup_path.relative_to(self.working_dir)) if backup_path else None,
                'file_info': await self._get_file_info(path)
            }
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            # Restore backup if write failed
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, path)
                    logger.info(f"Restored backup after write failure: {backup_path}")
                except Exception as restore_err:
                    logger.error(f"Failed to restore backup: {restore_err}")
            
            raise ExecutionError(f"Failed to write file: {e}", tool_name=self.name)
    
    async def _handle_file_append(self, path: Path, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle file append operations"""
        
        content = input_data['content']
        encoding = input_data.get('encoding', 'utf-8')
        
        # Phase 2: Appending to file
        yield await self.stream_progress({
            'status': 'appending',
            'message': f'Appending to {path.name}...',
            'progress': 50
        }, context)
        
        try:
            # Get original size
            original_size = path.stat().st_size if path.exists() else 0
            
            async with aiofiles.open(path, 'a', encoding=encoding) as f:
                await f.write(content)
            
            new_size = path.stat().st_size
            appended_bytes = new_size - original_size
            
            result_data = {
                'operation': 'append',
                'file_path': str(path.relative_to(self.working_dir)),
                'original_size_bytes': original_size,
                'appended_bytes': appended_bytes,
                'new_size_bytes': new_size,
                'file_info': await self._get_file_info(path)
            }
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"Failed to append to file: {e}", tool_name=self.name)
    
    async def _handle_file_delete(self, path: Path, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle file delete operations"""
        
        if not path.exists():
            raise ExecutionError(f"File not found: {path}", tool_name=self.name)
        
        # Phase 2: Creating backup before delete
        yield await self.stream_progress({
            'status': 'backing_up',
            'message': f'Creating backup before deletion...',
            'progress': 30
        }, context)
        
        backup_path = await self._create_backup(path)
        
        # Phase 3: Deleting file
        yield await self.stream_progress({
            'status': 'deleting',
            'message': f'Deleting {path.name}...',
            'progress': 60
        }, context)
        
        try:
            file_info = await self._get_file_info(path)
            path.unlink()  # Delete the file
            
            result_data = {
                'operation': 'delete',
                'file_path': str(path.relative_to(self.working_dir)),
                'deleted': True,
                'backup_path': str(backup_path.relative_to(self.working_dir)),
                'deleted_file_info': file_info
            }
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"Failed to delete file: {e}", tool_name=self.name)
    
    async def _handle_file_copy(self, source_path: Path, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle file copy operations"""
        
        target_path_str = input_data.get('target_path')
        if not target_path_str:
            raise ExecutionError("target_path required for copy operation", tool_name=self.name)
        
        target_path = await self._validate_and_resolve_path(target_path_str)
        
        if not source_path.exists():
            raise ExecutionError(f"Source file not found: {source_path}", tool_name=self.name)
        
        # Phase 2: Copying file
        yield await self.stream_progress({
            'status': 'copying',
            'message': f'Copying {source_path.name} to {target_path.name}...',
            'progress': 50
        }, context)
        
        try:
            # Create target directory if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file with metadata
            shutil.copy2(source_path, target_path)
            
            result_data = {
                'operation': 'copy',
                'source_path': str(source_path.relative_to(self.working_dir)),
                'target_path': str(target_path.relative_to(self.working_dir)),
                'copied': True,
                'source_info': await self._get_file_info(source_path),
                'target_info': await self._get_file_info(target_path)
            }
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"Failed to copy file: {e}", tool_name=self.name)
    
    async def _handle_file_move(self, source_path: Path, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle file move operations"""
        
        target_path_str = input_data.get('target_path')
        if not target_path_str:
            raise ExecutionError("target_path required for move operation", tool_name=self.name)
        
        target_path = await self._validate_and_resolve_path(target_path_str)
        
        if not source_path.exists():
            raise ExecutionError(f"Source file not found: {source_path}", tool_name=self.name)
        
        # Phase 2: Moving file
        yield await self.stream_progress({
            'status': 'moving',
            'message': f'Moving {source_path.name} to {target_path.name}...',
            'progress': 50
        }, context)
        
        try:
            source_info = await self._get_file_info(source_path)
            
            # Create target directory if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(source_path, target_path)
            
            result_data = {
                'operation': 'move',
                'source_path': str(source_path.relative_to(self.working_dir)),
                'target_path': str(target_path.relative_to(self.working_dir)),
                'moved': True,
                'original_info': source_info,
                'target_info': await self._get_file_info(target_path)
            }
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"Failed to move file: {e}", tool_name=self.name)
    
    async def _handle_file_info(self, path: Path, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle file info operations"""
        
        if not path.exists():
            raise ExecutionError(f"File not found: {path}", tool_name=self.name)
        
        # Phase 2: Gathering file info
        yield await self.stream_progress({
            'status': 'analyzing',
            'message': f'Analyzing {path.name}...',
            'progress': 50
        }, context)
        
        try:
            file_info = await self._get_file_info(path)
            
            result_data = {
                'operation': 'info',
                'file_path': str(path.relative_to(self.working_dir)),
                'exists': True,
                'file_info': file_info
            }
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"Failed to get file info: {e}", tool_name=self.name)
    
    async def _handle_file_exists(self, path: Path, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle file exists check"""
        
        result_data = {
            'operation': 'exists',
            'file_path': str(path.relative_to(self.working_dir)),
            'exists': path.exists(),
            'is_file': path.is_file() if path.exists() else False,
            'is_directory': path.is_dir() if path.exists() else False
        }
        
        yield await self.stream_final_result(result_data, context)
    
    async def _handle_directory_operation(self, path: Path, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle directory operations"""
        
        operation = input_data['operation']
        
        if operation == 'list':
            # List directory contents
            if not path.exists():
                raise ExecutionError(f"Directory not found: {path}", tool_name=self.name)
            
            if not path.is_dir():
                raise ExecutionError(f"Path is not a directory: {path}", tool_name=self.name)
            
            yield await self.stream_progress({
                'status': 'listing',
                'message': f'Listing contents of {path.name}...',
                'progress': 50
            }, context)
            
            try:
                include_hidden = input_data.get('include_hidden', False)
                recursive = input_data.get('recursive', False)
                
                contents = []
                
                if recursive:
                    for item in path.rglob('*'):
                        if not include_hidden and item.name.startswith('.'):
                            continue
                        
                        contents.append({
                            'path': str(item.relative_to(self.working_dir)),
                            'name': item.name,
                            'is_file': item.is_file(),
                            'is_directory': item.is_dir(),
                            'size_bytes': item.stat().st_size if item.is_file() else 0,
                            'modified': datetime.fromtimestamp(item.stat().st_mtime, timezone.utc).isoformat()
                        })
                else:
                    for item in path.iterdir():
                        if not include_hidden and item.name.startswith('.'):
                            continue
                        
                        contents.append({
                            'path': str(item.relative_to(self.working_dir)),
                            'name': item.name,
                            'is_file': item.is_file(),
                            'is_directory': item.is_dir(),
                            'size_bytes': item.stat().st_size if item.is_file() else 0,
                            'modified': datetime.fromtimestamp(item.stat().st_mtime, timezone.utc).isoformat()
                        })
                
                result_data = {
                    'operation': 'list',
                    'directory_path': str(path.relative_to(self.working_dir)),
                    'contents': contents,
                    'total_items': len(contents),
                    'recursive': recursive,
                    'include_hidden': include_hidden
                }
                
                yield await self.stream_final_result(result_data, context)
                
            except Exception as e:
                raise ExecutionError(f"Failed to list directory: {e}", tool_name=self.name)
        
        elif operation == 'create_dir':
            # Create directory
            yield await self.stream_progress({
                'status': 'creating',
                'message': f'Creating directory {path.name}...',
                'progress': 50
            }, context)
            
            try:
                path.mkdir(parents=True, exist_ok=True)
                
                result_data = {
                    'operation': 'create_dir',
                    'directory_path': str(path.relative_to(self.working_dir)),
                    'created': True,
                    'directory_info': await self._get_file_info(path)
                }
                
                yield await self.stream_final_result(result_data, context)
                
            except Exception as e:
                raise ExecutionError(f"Failed to create directory: {e}", tool_name=self.name)
        
        else:
            raise ExecutionError(f"Unsupported directory operation: {operation}", tool_name=self.name)
    
    async def _get_file_info(self, path: Path) -> Dict[str, Any]:
        """Get comprehensive file information"""
        
        if not path.exists():
            return {'exists': False}
        
        stat = path.stat()
        
        info = {
            'exists': True,
            'name': path.name,
            'size_bytes': stat.st_size,
            'is_file': path.is_file(),
            'is_directory': path.is_dir(),
            'is_symlink': path.is_symlink(),
            'created': datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
            'permissions': oct(stat.st_mode)[-3:],
            'owner_readable': os.access(path, os.R_OK),
            'owner_writable': os.access(path, os.W_OK),
            'owner_executable': os.access(path, os.X_OK)
        }
        
        # File type detection
        if path.is_file():
            info['extension'] = path.suffix.lower()
            
            # MIME type detection (simplified)
            if info['extension'] in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml']:
                info['file_type'] = 'text'
            elif info['extension'] in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']:
                info['file_type'] = 'image'
            elif info['extension'] in ['.mp4', '.avi', '.mov', '.wmv', '.flv']:
                info['file_type'] = 'video'
            elif info['extension'] in ['.mp3', '.wav', '.flac', '.aac']:
                info['file_type'] = 'audio'
            elif info['extension'] in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']:
                info['file_type'] = 'document'
            else:
                info['file_type'] = 'binary'
            
            # Calculate file hash for integrity checking
            if stat.st_size < 1024 * 1024:  # Only for files < 1MB
                try:
                    with open(path, 'rb') as f:
                        content = f.read()
                        info['sha256'] = sha256(content).hexdigest()
                except Exception:
                    info['sha256'] = None
        
        return info
    
    async def _create_backup(self, path: Path) -> Path:
        """Create a backup of the file"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.name}.backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise ExecutionError(f"Failed to create backup: {e}", tool_name=self.name)


__all__ = ["FileOperationTool"]