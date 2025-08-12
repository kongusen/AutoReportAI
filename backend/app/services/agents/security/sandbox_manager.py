"""
Agent安全沙盒管理器

提供分层的代码执行沙盒，确保Agent系统的安全性。
支持不同安全级别的代码执行环境。

Features:
- 分层沙盒安全级别
- 资源限制和监控
- 代码审计和日志
- 动态权限管理
- 表达式求值保护
"""

import ast
import re
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Callable
import threading
import resource
import signal
from enum import Enum


class SandboxLevel(Enum):
    """沙盒安全级别"""
    STRICT = "strict"          # 严格模式 - 最高安全性
    MODERATE = "moderate"      # 中等模式 - 平衡安全性和功能性
    PERMISSIVE = "permissive"  # 宽松模式 - 较高功能性


@dataclass
class SandboxConfig:
    """沙盒配置"""
    level: SandboxLevel
    allowed_imports: Set[str]
    allowed_functions: Set[str]
    execution_timeout: int  # 秒
    memory_limit: int  # MB
    max_output_size: int  # bytes
    audit_enabled: bool = True
    log_enabled: bool = True


class SandboxException(Exception):
    """沙盒执行异常"""
    
    def __init__(self, message: str, code: str = None, details: Dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class CodeValidator:
    """代码安全验证器"""
    
    # 危险函数黑名单
    DANGEROUS_FUNCTIONS = {
        '__import__', 'eval', 'exec', 'compile', 'open', 'file',
        'input', 'raw_input', 'reload', 'delattr', 'setattr',
        'getattr', 'hasattr', 'globals', 'locals', 'vars', 'dir',
        'exit', 'quit', 'help', 'copyright', 'credits', 'license',
        'memoryview', 'buffer'
    }
    
    # 危险模块黑名单
    DANGEROUS_MODULES = {
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'requests',
        'ftplib', 'telnetlib', 'poplib', 'imaplib', 'smtplib',
        'pickle', 'cPickle', 'marshal', 'shelve', 'dbm', 'dumbdbm',
        'thread', 'threading', 'multiprocessing', 'ctypes'
    }
    
    # 危险语法模式
    DANGEROUS_PATTERNS = [
        r'__.*__',  # 魔术方法
        r'\..*\(',  # 方法调用链
        r'import\s+\w+',  # import语句
        r'from\s+\w+\s+import',  # from import语句
        r'exec\s*\(',  # exec调用
        r'eval\s*\(',  # eval调用
    ]
    
    def validate_code(self, code: str, config: SandboxConfig) -> bool:
        """验证代码安全性"""
        try:
            # 解析AST
            tree = ast.parse(code)
            
            # AST节点检查
            for node in ast.walk(tree):
                if not self._is_safe_node(node, config):
                    return False
            
            # 字符串模式检查
            if not self._check_string_patterns(code, config):
                return False
            
            return True
            
        except SyntaxError:
            return False
    
    def _is_safe_node(self, node: ast.AST, config: SandboxConfig) -> bool:
        """检查AST节点是否安全"""
        # 检查函数调用
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self.DANGEROUS_FUNCTIONS:
                    return False
                if func_name not in config.allowed_functions and config.level == SandboxLevel.STRICT:
                    return False
        
        # 检查属性访问
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith('_'):
                return False
        
        # 检查导入语句
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if config.level == SandboxLevel.STRICT:
                return False
            # 检查导入的模块是否在允许列表中
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in config.allowed_imports:
                        return False
            elif isinstance(node, ast.ImportFrom):
                if node.module not in config.allowed_imports:
                    return False
        
        return True
    
    def _check_string_patterns(self, code: str, config: SandboxConfig) -> bool:
        """检查代码字符串中的危险模式"""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code) and config.level == SandboxLevel.STRICT:
                return False
        return True


class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.start_time = None
        self.memory_usage = 0
    
    def start_monitoring(self):
        """开始资源监控"""
        self.start_time = time.time()
        
        # 设置内存限制
        if self.config.memory_limit > 0:
            memory_limit = self.config.memory_limit * 1024 * 1024  # 转换为字节
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
    
    def check_timeout(self):
        """检查是否超时"""
        if self.start_time and self.config.execution_timeout > 0:
            elapsed = time.time() - self.start_time
            if elapsed > self.config.execution_timeout:
                raise SandboxException(
                    f"执行超时 ({elapsed:.2f}s > {self.config.execution_timeout}s)",
                    "EXECUTION_TIMEOUT"
                )
    
    def get_memory_usage(self) -> int:
        """获取内存使用量"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss // 1024 // 1024  # MB
        except ImportError:
            return 0


class SandboxExecutor:
    """沙盒执行器"""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.validator = CodeValidator()
        self.monitor = ResourceMonitor(config)
        self.audit_log = []
    
    def execute_expression(self, expression: str, context: Dict[str, Any] = None) -> Any:
        """安全执行表达式"""
        context = context or {}
        
        # 代码验证
        if not self.validator.validate_code(expression, self.config):
            raise SandboxException("表达式包含不安全的代码", "UNSAFE_CODE")
        
        # 开始监控
        self.monitor.start_monitoring()
        
        try:
            # 使用ast.literal_eval进行安全求值（仅支持字面量）
            try:
                result = ast.literal_eval(expression)
                self._log_execution(expression, "literal_eval", True)
                return result
            except (ValueError, SyntaxError):
                pass
            
            # 对于更复杂的表达式，使用受限的eval
            if self.config.level != SandboxLevel.STRICT:
                result = self._safe_eval(expression, context)
                self._log_execution(expression, "safe_eval", True)
                return result
            else:
                raise SandboxException("严格模式下不支持复杂表达式", "EXPRESSION_NOT_SUPPORTED")
                
        except Exception as e:
            self._log_execution(expression, "error", False, str(e))
            raise SandboxException(f"表达式执行失败: {str(e)}", "EXECUTION_ERROR")
        finally:
            self.monitor.check_timeout()
    
    def execute_function(self, func_code: str, func_name: str, args: tuple = (), kwargs: Dict = None) -> Any:
        """安全执行函数"""
        kwargs = kwargs or {}
        
        # 代码验证
        if not self.validator.validate_code(func_code, self.config):
            raise SandboxException("函数代码包含不安全的内容", "UNSAFE_CODE")
        
        # 开始监控
        self.monitor.start_monitoring()
        
        try:
            # 创建受限的执行环境
            safe_globals = self._create_safe_globals()
            safe_locals = {}
            
            # 执行函数定义
            exec(func_code, safe_globals, safe_locals)
            
            # 获取并执行函数
            if func_name not in safe_locals:
                raise SandboxException(f"函数 {func_name} 未定义", "FUNCTION_NOT_FOUND")
            
            func = safe_locals[func_name]
            result = func(*args, **kwargs)
            
            self._log_execution(func_code, "function", True)
            return result
            
        except Exception as e:
            self._log_execution(func_code, "function_error", False, str(e))
            raise SandboxException(f"函数执行失败: {str(e)}", "FUNCTION_EXECUTION_ERROR")
        finally:
            self.monitor.check_timeout()
    
    def _safe_eval(self, expression: str, context: Dict[str, Any]) -> Any:
        """安全的eval执行"""
        safe_globals = self._create_safe_globals()
        safe_locals = dict(context)  # 复制上下文
        
        # 使用受限的globals和locals执行
        return eval(expression, safe_globals, safe_locals)
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """创建安全的全局命名空间"""
        safe_builtins = {}
        
        # 根据配置级别添加允许的内建函数
        if self.config.level == SandboxLevel.PERMISSIVE:
            allowed_builtins = {
                'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes',
                'chr', 'dict', 'divmod', 'enumerate', 'filter', 'float',
                'frozenset', 'hex', 'int', 'len', 'list', 'map', 'max',
                'min', 'oct', 'ord', 'pow', 'range', 'reversed', 'round',
                'set', 'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip'
            }
        elif self.config.level == SandboxLevel.MODERATE:
            allowed_builtins = {
                'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter',
                'float', 'int', 'len', 'list', 'map', 'max', 'min', 'range',
                'round', 'set', 'sorted', 'str', 'sum', 'tuple', 'zip'
            }
        else:  # STRICT
            allowed_builtins = {
                'abs', 'bool', 'dict', 'float', 'int', 'len', 'list',
                'max', 'min', 'round', 'str', 'sum', 'tuple'
            }
        
        # 添加允许的函数
        for name in self.config.allowed_functions:
            if name in allowed_builtins and hasattr(__builtins__, name):
                safe_builtins[name] = getattr(__builtins__, name)
        
        return {
            '__builtins__': safe_builtins,
            '__name__': '__sandbox__',
            '__doc__': None,
        }
    
    def _log_execution(self, code: str, execution_type: str, success: bool, error: str = None):
        """记录执行日志"""
        if not self.config.audit_enabled:
            return
        
        log_entry = {
            'timestamp': time.time(),
            'code': code[:200] + '...' if len(code) > 200 else code,
            'type': execution_type,
            'success': success,
            'error': error,
            'memory_usage': self.monitor.get_memory_usage(),
            'config_level': self.config.level.value
        }
        
        self.audit_log.append(log_entry)
        
        # 保持日志数量在合理范围内
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-500:]
    
    def get_audit_log(self) -> List[Dict]:
        """获取审计日志"""
        return self.audit_log.copy()


class SandboxManager:
    """沙盒管理器 - 统一的沙盒服务入口"""
    
    # 预定义配置
    CONFIGS = {
        SandboxLevel.STRICT: SandboxConfig(
            level=SandboxLevel.STRICT,
            allowed_imports=set(),
            allowed_functions={'len', 'str', 'int', 'float', 'bool', 'abs', 'round'},
            execution_timeout=5,
            memory_limit=10,
            max_output_size=1024
        ),
        
        SandboxLevel.MODERATE: SandboxConfig(
            level=SandboxLevel.MODERATE,
            allowed_imports={'math', 'statistics', 'datetime'},
            allowed_functions={
                'len', 'str', 'int', 'float', 'bool', 'abs', 'round',
                'sum', 'max', 'min', 'sorted', 'list', 'dict', 'set'
            },
            execution_timeout=10,
            memory_limit=50,
            max_output_size=10240
        ),
        
        SandboxLevel.PERMISSIVE: SandboxConfig(
            level=SandboxLevel.PERMISSIVE,
            allowed_imports={'json', 'yaml', 'math', 'statistics', 'datetime', 're'},
            allowed_functions={
                'len', 'str', 'int', 'float', 'bool', 'abs', 'round',
                'sum', 'max', 'min', 'sorted', 'list', 'dict', 'set',
                'enumerate', 'filter', 'map', 'zip', 'range'
            },
            execution_timeout=15,
            memory_limit=100,
            max_output_size=102400
        )
    }
    
    def __init__(self):
        self.executors = {}
        self.global_audit_log = []
    
    def get_executor(self, level: SandboxLevel = SandboxLevel.MODERATE) -> SandboxExecutor:
        """获取沙盒执行器"""
        if level not in self.executors:
            config = self.CONFIGS[level]
            self.executors[level] = SandboxExecutor(config)
        
        return self.executors[level]
    
    def execute_safe(
        self, 
        code: str, 
        level: SandboxLevel = SandboxLevel.MODERATE,
        context: Dict[str, Any] = None
    ) -> Any:
        """安全执行代码"""
        executor = self.get_executor(level)
        
        try:
            # 简单表达式使用表达式执行
            if '\n' not in code.strip() and 'def ' not in code:
                return executor.execute_expression(code, context)
            else:
                # 复杂代码暂时不支持，返回错误
                raise SandboxException("复杂代码执行需要函数模式", "COMPLEX_CODE_NOT_SUPPORTED")
                
        except Exception as e:
            # 记录到全局日志
            self.global_audit_log.append({
                'timestamp': time.time(),
                'level': level.value,
                'code': code[:100] + '...' if len(code) > 100 else code,
                'error': str(e),
                'success': False
            })
            raise
    
    def validate_sql_query(self, query: str) -> bool:
        """验证SQL查询安全性"""
        # SQL注入检测
        dangerous_sql_patterns = [
            r';.*drop\s+table',
            r';.*delete\s+from',
            r';.*update\s+.*set',
            r';.*insert\s+into',
            r';.*create\s+table',
            r';.*alter\s+table',
            r'union\s+select',
            r'--\s*',
            r'/\*.*\*/',
        ]
        
        query_lower = query.lower()
        for pattern in dangerous_sql_patterns:
            if re.search(pattern, query_lower):
                return False
        
        return True
    
    def get_global_audit_log(self) -> List[Dict]:
        """获取全局审计日志"""
        return self.global_audit_log.copy()
    
    def clear_audit_log(self):
        """清空审计日志"""
        self.global_audit_log.clear()
        for executor in self.executors.values():
            executor.audit_log.clear()


# 全局沙盒管理器实例
sandbox_manager = SandboxManager()