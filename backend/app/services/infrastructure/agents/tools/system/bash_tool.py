"""
Bash Command Execution Tools
============================

Safe bash command execution with comprehensive security checks and output streaming.
"""

import logging
import asyncio
import subprocess
import shutil
import time
import signal
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
import psutil

from ..core.base import (
    AgentTool, StreamingAgentTool, ToolDefinition, ToolResult, 
    ToolExecutionContext, ToolCategory, ToolPriority, ToolPermission,
    ValidationError, ExecutionError, create_tool_definition
)
from ..core.permissions import SecurityLevel, ResourceType

logger = logging.getLogger(__name__)


# Input schemas
class BashExecutorInput(BaseModel):
    """Input schema for bash command execution"""
    command: str = Field(..., min_length=1, max_length=2000, description="Command to execute")
    working_directory: Optional[str] = Field(None, description="Working directory for command execution")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Command timeout in seconds")
    capture_output: bool = Field(default=True, description="Capture stdout and stderr")
    environment_vars: Optional[Dict[str, str]] = Field(None, description="Additional environment variables")
    shell: str = Field(default="/bin/bash", description="Shell to use for execution")
    safe_mode: bool = Field(default=True, description="Enable additional safety checks")
    dry_run: bool = Field(default=False, description="Only validate without executing")
    
    @validator('command')
    def validate_command(cls, v):
        if not v.strip():
            raise ValueError("Command cannot be empty")
        
        # Security: check for dangerous commands
        dangerous_patterns = [
            'rm -rf /', 'format ', 'del /f /s /q', 'mkfs', 'dd if=', 
            ':(){ :|:& };:', 'sudo rm', 'chmod 777', 'chown root',
            '> /dev/sda', 'wget http', 'curl http', 'nc -l', 'netcat -l'
        ]
        
        command_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                raise ValueError(f"Potentially dangerous command pattern detected: {pattern}")
        
        return v.strip()
    
    @validator('shell')
    def validate_shell(cls, v):
        allowed_shells = ['/bin/bash', '/bin/sh', '/bin/zsh', '/usr/bin/fish']
        if v not in allowed_shells:
            raise ValueError(f"Shell must be one of: {allowed_shells}")
        return v


class SystemInfoInput(BaseModel):
    """Input schema for system information queries"""
    info_type: str = Field(..., description="Type of system info to retrieve")
    include_details: bool = Field(default=False, description="Include detailed information")
    
    @validator('info_type')
    def validate_info_type(cls, v):
        allowed_types = [
            'system', 'cpu', 'memory', 'disk', 'network', 
            'processes', 'environment', 'python', 'packages'
        ]
        if v not in allowed_types:
            raise ValueError(f"Info type must be one of: {allowed_types}")
        return v


class BashExecutorTool(StreamingAgentTool):
    """
    Secure bash command execution with comprehensive safety checks
    """
    
    def __init__(self):
        definition = create_tool_definition(
            name="bash_executor",
            description="Execute bash commands with safety checks and output streaming",
            category=ToolCategory.SYSTEM,
            priority=ToolPriority.HIGH,
            permissions=[ToolPermission.WRITE_LIMITED, ToolPermission.SYSTEM_ACCESS],
            input_schema=BashExecutorInput,
            is_read_only=False,
            supports_streaming=True,
            typical_execution_time_ms=5000,
            examples=[
                {
                    "command": "ls -la",
                    "working_directory": "/tmp",
                    "timeout_seconds": 10
                },
                {
                    "command": "python --version",
                    "safe_mode": True,
                    "dry_run": False
                }
            ],
            limitations=[
                "Commands are executed with current user permissions",
                "Dangerous commands are blocked",
                "Output is limited to prevent memory issues",
                "Long-running commands may be terminated"
            ]
        )
        super().__init__(definition)
        
        # Security settings
        self.working_dir = Path.cwd()
        self.max_output_size = 1024 * 1024  # 1MB
        self.blocked_commands = {
            'rm', 'rmdir', 'del', 'format', 'mkfs', 'dd',
            'sudo', 'su', 'chmod 777', 'chown root', 'passwd'
        }
        
        # Command whitelist for safe mode
        self.safe_commands = {
            'ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'grep', 'find',
            'ps', 'top', 'whoami', 'date', 'uptime', 'df', 'du', 'free',
            'python', 'python3', 'pip', 'node', 'npm', 'git', 'which',
            'env', 'export', 'history', 'wc', 'sort', 'uniq', 'cut',
            'awk', 'sed', 'tr', 'tee', 'less', 'more'
        }
    
    async def validate_input(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> Dict[str, Any]:
        """Validate bash execution input"""
        operation = input_data.get('operation', 'bash')
        
        try:
            if operation == 'bash':
                validated = BashExecutorInput(**input_data)
            elif operation == 'system_info':
                validated = SystemInfoInput(**input_data)
            else:
                # Default to bash validation
                validated = BashExecutorInput(**{k: v for k, v in input_data.items() if k in BashExecutorInput.__fields__})
            
            result = validated.dict()
            result['operation'] = operation
            return result
            
        except Exception as e:
            raise ValidationError(f"Invalid input for bash executor: {e}", tool_name=self.name)
    
    async def check_permissions(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> bool:
        """Check permissions for bash operations"""
        operation = input_data.get('operation', 'bash')
        
        # System info operations
        if operation == 'system_info':
            return ToolPermission.READ_ONLY in context.permissions
        
        # Bash execution operations
        if operation == 'bash':
            command = input_data.get('command', '').lower().strip()
            
            # Read-only commands
            read_only_commands = ['ls', 'pwd', 'cat', 'head', 'tail', 'grep', 'find', 'ps', 'top', 'df', 'free']
            if any(command.startswith(cmd) for cmd in read_only_commands):
                return ToolPermission.READ_ONLY in context.permissions
            
            # Write operations
            return ToolPermission.WRITE_LIMITED in context.permissions
        
        return False
    
    async def execute(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Execute bash operations with streaming progress"""
        
        operation = input_data.get('operation', 'bash')
        
        if operation == 'bash':
            async for result in self._handle_bash_execution(input_data, context):
                yield result
        elif operation == 'system_info':
            async for result in self._handle_system_info(input_data, context):
                yield result
        else:
            raise ExecutionError(f"Unsupported operation: {operation}", tool_name=self.name)
    
    async def _handle_bash_execution(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle bash command execution"""
        
        command = input_data['command']
        working_directory = input_data.get('working_directory')
        timeout_seconds = input_data['timeout_seconds']
        capture_output = input_data['capture_output']
        environment_vars = input_data.get('environment_vars', {})
        shell = input_data['shell']
        safe_mode = input_data['safe_mode']
        dry_run = input_data['dry_run']
        
        # Phase 1: Security validation
        yield await self.stream_progress({
            'status': 'validating',
            'message': 'Validating command security...',
            'progress': 10
        }, context)
        
        security_check = await self._security_check_command(command, safe_mode)
        if not security_check['allowed']:
            raise ExecutionError(f"Security check failed: {security_check['reason']}", tool_name=self.name)
        
        # Phase 2: Environment setup
        yield await self.stream_progress({
            'status': 'preparing',
            'message': 'Preparing execution environment...',
            'progress': 20
        }, context)
        
        # Set working directory
        if working_directory:
            work_dir = await self._validate_and_resolve_path(working_directory)
        else:
            work_dir = self.working_dir
        
        # Prepare environment
        env = os.environ.copy()
        env.update(environment_vars)
        
        if dry_run:
            # Dry run - just validate and return
            result_data = {
                'operation': 'bash',
                'command': command,
                'dry_run': True,
                'working_directory': str(work_dir),
                'security_check': security_check,
                'estimated_safety': 'Safe' if security_check['safe_command'] else 'Potentially unsafe',
                'environment_vars': environment_vars
            }
            yield await self.stream_final_result(result_data, context)
            return
        
        # Phase 3: Command execution
        yield await self.stream_progress({
            'status': 'executing',
            'message': f'Executing: {command[:50]}...',
            'progress': 40
        }, context)
        
        try:
            start_time = time.time()
            
            # Execute command
            if capture_output:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=work_dir,
                    env=env,
                    executable=shell
                )
                
                # Stream output as it comes
                stdout_chunks = []
                stderr_chunks = []
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=timeout_seconds
                    )
                    
                    if stdout:
                        stdout_chunks.append(stdout.decode('utf-8', errors='replace'))
                    if stderr:
                        stderr_chunks.append(stderr.decode('utf-8', errors='replace'))
                
                except asyncio.TimeoutError:
                    # Kill the process if it times out
                    try:
                        process.kill()
                        await process.wait()
                    except:
                        pass
                    
                    raise ExecutionError(f"Command timed out after {timeout_seconds} seconds", tool_name=self.name)
                
                execution_time = (time.time() - start_time) * 1000
                return_code = process.returncode
                
                stdout_text = ''.join(stdout_chunks)
                stderr_text = ''.join(stderr_chunks)
                
                # Limit output size
                if len(stdout_text) > self.max_output_size:
                    stdout_text = stdout_text[:self.max_output_size] + "\n[Output truncated...]"
                if len(stderr_text) > self.max_output_size:
                    stderr_text = stderr_text[:self.max_output_size] + "\n[Error output truncated...]"
                
            else:
                # Execute without capturing output
                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=work_dir,
                    env=env,
                    executable=shell
                )
                
                try:
                    return_code = await asyncio.wait_for(
                        process.wait(), 
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    try:
                        process.kill()
                        await process.wait()
                    except:
                        pass
                    
                    raise ExecutionError(f"Command timed out after {timeout_seconds} seconds", tool_name=self.name)
                
                execution_time = (time.time() - start_time) * 1000
                stdout_text = "[Output not captured]"
                stderr_text = "[Error output not captured]"
            
            # Phase 4: Results processing
            yield await self.stream_progress({
                'status': 'processing',
                'message': 'Processing command results...',
                'progress': 80
            }, context)
            
            result_data = {
                'operation': 'bash',
                'command': command,
                'working_directory': str(work_dir),
                'return_code': return_code,
                'success': return_code == 0,
                'execution_time_ms': execution_time,
                'stdout': stdout_text,
                'stderr': stderr_text,
                'output_size': len(stdout_text) + len(stderr_text),
                'environment_vars': environment_vars,
                'security_check': security_check
            }
            
            # Add system resource usage if available
            try:
                process_info = psutil.Process().as_dict(attrs=['memory_info', 'cpu_percent'])
                result_data['resource_usage'] = process_info
            except Exception:
                pass
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"Command execution failed: {e}", tool_name=self.name)
    
    async def _handle_system_info(self, input_data: Dict[str, Any], context: ToolExecutionContext) -> AsyncGenerator[ToolResult, None]:
        """Handle system information queries"""
        
        info_type = input_data['info_type']
        include_details = input_data['include_details']
        
        # Phase 1: Gathering system info
        yield await self.stream_progress({
            'status': 'gathering',
            'message': f'Gathering {info_type} information...',
            'progress': 50
        }, context)
        
        try:
            if info_type == 'system':
                info_data = await self._get_system_info(include_details)
            elif info_type == 'cpu':
                info_data = await self._get_cpu_info(include_details)
            elif info_type == 'memory':
                info_data = await self._get_memory_info(include_details)
            elif info_type == 'disk':
                info_data = await self._get_disk_info(include_details)
            elif info_type == 'network':
                info_data = await self._get_network_info(include_details)
            elif info_type == 'processes':
                info_data = await self._get_process_info(include_details)
            elif info_type == 'environment':
                info_data = await self._get_environment_info(include_details)
            elif info_type == 'python':
                info_data = await self._get_python_info(include_details)
            elif info_type == 'packages':
                info_data = await self._get_package_info(include_details)
            else:
                raise ExecutionError(f"Unsupported info type: {info_type}", tool_name=self.name)
            
            result_data = {
                'operation': 'system_info',
                'info_type': info_type,
                'include_details': include_details,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': info_data
            }
            
            yield await self.stream_final_result(result_data, context)
            
        except Exception as e:
            raise ExecutionError(f"Failed to gather system info: {e}", tool_name=self.name)
    
    async def _security_check_command(self, command: str, safe_mode: bool) -> Dict[str, Any]:
        """Perform security checks on bash commands"""
        
        command_lower = command.lower().strip()
        first_word = command_lower.split()[0] if command_lower else ""
        
        # Check blocked commands
        for blocked_cmd in self.blocked_commands:
            if blocked_cmd in command_lower:
                return {
                    'allowed': False,
                    'reason': f"Blocked command detected: {blocked_cmd}",
                    'safe_command': False
                }
        
        # Safe mode check
        if safe_mode:
            if first_word not in self.safe_commands:
                return {
                    'allowed': False,
                    'reason': f"Command not in safe list: {first_word}",
                    'safe_command': False,
                    'suggestion': f"Consider using one of: {', '.join(list(self.safe_commands)[:10])}"
                }
        
        # Check for file system modifications
        dangerous_patterns = [
            '>', '>>', 'rm ', 'del ', 'mv ', 'cp ', 'chmod ', 'chown ',
            'mkdir ', 'rmdir ', 'touch ', 'ln ', 'unlink '
        ]
        
        has_modifications = any(pattern in command_lower for pattern in dangerous_patterns)
        
        # Check for network operations
        network_patterns = ['curl ', 'wget ', 'nc ', 'netcat ', 'ssh ', 'scp ', 'rsync ']
        has_network = any(pattern in command_lower for pattern in network_patterns)
        
        # Check for privilege escalation
        privilege_patterns = ['sudo ', 'su ', 'doas ']
        has_privilege = any(pattern in command_lower for pattern in privilege_patterns)
        
        return {
            'allowed': True,
            'reason': 'Command passed security checks',
            'safe_command': first_word in self.safe_commands,
            'has_modifications': has_modifications,
            'has_network': has_network,
            'has_privilege': has_privilege,
            'risk_level': 'high' if has_privilege else 'medium' if (has_modifications or has_network) else 'low'
        }
    
    async def _validate_and_resolve_path(self, path_str: str) -> Path:
        """Validate and resolve working directory path"""
        
        path = Path(path_str)
        
        # Ensure it's within allowed directories
        if path.is_absolute():
            # Allow absolute paths but check they're safe
            try:
                # Must be within current working directory tree or common safe directories
                safe_roots = [self.working_dir, Path('/tmp'), Path('/var/tmp')]
                
                is_safe = False
                for safe_root in safe_roots:
                    try:
                        path.relative_to(safe_root)
                        is_safe = True
                        break
                    except ValueError:
                        continue
                
                if not is_safe:
                    raise ExecutionError("Path not in allowed directories", tool_name=self.name)
                
            except Exception:
                raise ExecutionError("Invalid working directory path", tool_name=self.name)
        else:
            # Resolve relative to working directory
            path = (self.working_dir / path).resolve()
        
        # Ensure directory exists
        if not path.exists():
            raise ExecutionError(f"Working directory does not exist: {path}", tool_name=self.name)
        
        if not path.is_dir():
            raise ExecutionError(f"Path is not a directory: {path}", tool_name=self.name)
        
        return path
    
    async def _get_system_info(self, include_details: bool) -> Dict[str, Any]:
        """Get system information"""
        import platform
        
        info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.architecture()[0],
            'machine': platform.machine(),
            'processor': platform.processor(),
            'hostname': platform.node(),
            'python_version': platform.python_version()
        }
        
        if include_details:
            try:
                info.update({
                    'platform_details': platform.platform(),
                    'system_alias': platform.system_alias(platform.system(), platform.release(), platform.version()),
                    'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
                })
            except Exception:
                pass
        
        return info
    
    async def _get_cpu_info(self, include_details: bool) -> Dict[str, Any]:
        """Get CPU information"""
        
        info = {
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
        
        if include_details:
            try:
                info.update({
                    'cpu_times': psutil.cpu_times()._asdict(),
                    'cpu_stats': psutil.cpu_stats()._asdict(),
                    'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                })
            except Exception:
                pass
        
        return info
    
    async def _get_memory_info(self, include_details: bool) -> Dict[str, Any]:
        """Get memory information"""
        
        virtual_mem = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()
        
        info = {
            'total_memory': virtual_mem.total,
            'available_memory': virtual_mem.available,
            'used_memory': virtual_mem.used,
            'memory_percent': virtual_mem.percent,
            'swap_total': swap_mem.total,
            'swap_used': swap_mem.used,
            'swap_percent': swap_mem.percent
        }
        
        if include_details:
            info.update({
                'virtual_memory': virtual_mem._asdict(),
                'swap_memory': swap_mem._asdict()
            })
        
        return info
    
    async def _get_disk_info(self, include_details: bool) -> Dict[str, Any]:
        """Get disk information"""
        
        disk_usage = psutil.disk_usage('/')
        
        info = {
            'total_disk': disk_usage.total,
            'used_disk': disk_usage.used,
            'free_disk': disk_usage.free,
            'disk_percent': (disk_usage.used / disk_usage.total) * 100
        }
        
        if include_details:
            try:
                partitions = []
                for partition in psutil.disk_partitions():
                    try:
                        partition_usage = psutil.disk_usage(partition.mountpoint)
                        partitions.append({
                            'device': partition.device,
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total': partition_usage.total,
                            'used': partition_usage.used,
                            'free': partition_usage.free,
                            'percent': (partition_usage.used / partition_usage.total) * 100
                        })
                    except Exception:
                        pass
                
                info['partitions'] = partitions
                info['disk_io'] = psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else None
            except Exception:
                pass
        
        return info
    
    async def _get_network_info(self, include_details: bool) -> Dict[str, Any]:
        """Get network information"""
        
        info = {
            'network_interfaces': list(psutil.net_if_addrs().keys())
        }
        
        if include_details:
            try:
                net_io = psutil.net_io_counters()
                if net_io:
                    info['network_io'] = net_io._asdict()
                
                info['network_connections'] = len(psutil.net_connections())
                info['network_stats'] = psutil.net_if_stats()
            except Exception:
                pass
        
        return info
    
    async def _get_process_info(self, include_details: bool) -> Dict[str, Any]:
        """Get process information"""
        
        current_process = psutil.Process()
        
        info = {
            'current_pid': current_process.pid,
            'current_ppid': current_process.ppid(),
            'current_name': current_process.name(),
            'current_status': current_process.status(),
            'total_processes': len(psutil.pids())
        }
        
        if include_details:
            try:
                info.update({
                    'current_cmdline': current_process.cmdline(),
                    'current_cwd': current_process.cwd(),
                    'current_memory': current_process.memory_info()._asdict(),
                    'current_cpu_percent': current_process.cpu_percent(),
                    'current_create_time': datetime.fromtimestamp(current_process.create_time()).isoformat()
                })
                
                # Top 10 processes by memory
                top_processes = []
                for proc in sorted(psutil.process_iter(['pid', 'name', 'memory_percent']), 
                                 key=lambda p: p.info['memory_percent'] or 0, reverse=True)[:10]:
                    try:
                        top_processes.append(proc.info)
                    except Exception:
                        pass
                
                info['top_memory_processes'] = top_processes
            except Exception:
                pass
        
        return info
    
    async def _get_environment_info(self, include_details: bool) -> Dict[str, Any]:
        """Get environment information"""
        
        important_vars = ['PATH', 'HOME', 'USER', 'SHELL', 'PWD', 'LANG']
        
        info = {
            'working_directory': str(self.working_dir),
            'user': os.environ.get('USER', 'unknown'),
            'home': os.environ.get('HOME', 'unknown'),
            'shell': os.environ.get('SHELL', 'unknown')
        }
        
        if include_details:
            env_vars = {}
            for var in important_vars:
                env_vars[var] = os.environ.get(var)
            
            info['environment_variables'] = env_vars
            info['total_env_vars'] = len(os.environ)
        
        return info
    
    async def _get_python_info(self, include_details: bool) -> Dict[str, Any]:
        """Get Python information"""
        import sys
        
        info = {
            'python_version': sys.version,
            'python_executable': sys.executable,
            'python_path': sys.path[:5]  # First 5 paths
        }
        
        if include_details:
            try:
                info.update({
                    'python_implementation': sys.implementation.name,
                    'python_version_info': {
                        'major': sys.version_info.major,
                        'minor': sys.version_info.minor,
                        'micro': sys.version_info.micro
                    },
                    'python_platform': sys.platform,
                    'python_modules_count': len(sys.modules)
                })
            except Exception:
                pass
        
        return info
    
    async def _get_package_info(self, include_details: bool) -> Dict[str, Any]:
        """Get installed package information"""
        
        info = {
            'pip_available': shutil.which('pip') is not None,
            'conda_available': shutil.which('conda') is not None,
            'npm_available': shutil.which('npm') is not None
        }
        
        if include_details:
            # This would require executing pip list, which we handle separately
            # for security reasons in safe mode
            info['note'] = "Use 'pip list' command for detailed package information"
        
        return info


__all__ = ["BashExecutorTool"]