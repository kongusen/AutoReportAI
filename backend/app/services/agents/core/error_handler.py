"""
统一的错误处理器
提供标准化的错误处理和恢复机制
"""

import logging
import traceback
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(Enum):
    """错误类型"""
    AI_SERVICE_ERROR = "ai_service_error"
    PARSING_ERROR = "parsing_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorInfo:
    """错误信息"""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    recoverable: bool = True


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_callbacks: Dict[ErrorType, Callable] = {}
        self.recovery_strategies: Dict[ErrorType, Callable] = {}
    
    def register_error_callback(
        self, 
        error_type: ErrorType, 
        callback: Callable[[ErrorInfo], None]
    ):
        """注册错误回调"""
        self.error_callbacks[error_type] = callback
    
    def register_recovery_strategy(
        self, 
        error_type: ErrorType, 
        strategy: Callable[[ErrorInfo], Any]
    ):
        """注册恢复策略"""
        self.recovery_strategies[error_type] = strategy
    
    def handle_error(
        self, 
        exception: Exception, 
        context: str = "",
        **kwargs
    ) -> ErrorInfo:
        """处理错误"""
        error_info = self._create_error_info(exception, context, **kwargs)
        
        # 记录错误
        self._log_error(error_info)
        
        # 执行错误回调
        if error_info.error_type in self.error_callbacks:
            try:
                self.error_callbacks[error_info.error_type](error_info)
            except Exception as e:
                self.logger.error(f"错误回调执行失败: {e}")
        
        return error_info
    
    def try_recovery(self, error_info: ErrorInfo) -> Optional[Any]:
        """尝试恢复"""
        if not error_info.recoverable:
            return None
        
        if error_info.error_type in self.recovery_strategies:
            try:
                return self.recovery_strategies[error_info.error_type](error_info)
            except Exception as e:
                self.logger.error(f"恢复策略执行失败: {e}")
        
        return None
    
    def _create_error_info(
        self, 
        exception: Exception, 
        context: str = "",
        **kwargs
    ) -> ErrorInfo:
        """创建错误信息"""
        error_type = self._classify_error(exception)
        severity = self._assess_severity(exception, error_type)
        
        return ErrorInfo(
            error_type=error_type,
            severity=severity,
            message=str(exception),
            details={
                "context": context,
                "exception_type": type(exception).__name__,
                "traceback": traceback.format_exc(),
                **kwargs
            },
            recoverable=self._is_recoverable(error_type, severity)
        )
    
    def _classify_error(self, exception: Exception) -> ErrorType:
        """分类错误"""
        exception_name = type(exception).__name__.lower()
        
        if "ai" in exception_name or "service" in exception_name:
            return ErrorType.AI_SERVICE_ERROR
        elif "json" in exception_name or "parse" in exception_name:
            return ErrorType.PARSING_ERROR
        elif "validation" in exception_name or "validate" in exception_name:
            return ErrorType.VALIDATION_ERROR
        elif "network" in exception_name or "connection" in exception_name:
            return ErrorType.NETWORK_ERROR
        elif "timeout" in exception_name:
            return ErrorType.TIMEOUT_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _assess_severity(self, exception: Exception, error_type: ErrorType) -> ErrorSeverity:
        """评估错误严重程度"""
        if error_type == ErrorType.CRITICAL:
            return ErrorSeverity.CRITICAL
        elif error_type in [ErrorType.AI_SERVICE_ERROR, ErrorType.NETWORK_ERROR]:
            return ErrorSeverity.HIGH
        elif error_type in [ErrorType.PARSING_ERROR, ErrorType.VALIDATION_ERROR]:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _is_recoverable(self, error_type: ErrorType, severity: ErrorSeverity) -> bool:
        """判断是否可恢复"""
        if severity == ErrorSeverity.CRITICAL:
            return False
        
        # 某些错误类型总是可恢复的
        if error_type in [ErrorType.PARSING_ERROR, ErrorType.VALIDATION_ERROR]:
            return True
        
        # 某些错误类型可能可恢复
        if error_type in [ErrorType.AI_SERVICE_ERROR, ErrorType.NETWORK_ERROR, ErrorType.TIMEOUT_ERROR]:
            return True
        
        return False
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误"""
        log_message = f"[{error_info.error_type.value}] {error_info.message}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra=error_info.details)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, extra=error_info.details)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra=error_info.details)
        else:
            self.logger.info(log_message, extra=error_info.details)


class AgentErrorHandler(ErrorHandler):
    """Agent专用错误处理器"""
    
    def __init__(self):
        super().__init__()
        self._setup_default_strategies()
    
    def _setup_default_strategies(self):
        """设置默认恢复策略"""
        
        # AI服务错误恢复策略
        self.register_recovery_strategy(
            ErrorType.AI_SERVICE_ERROR,
            self._recover_ai_service_error
        )
        
        # 解析错误恢复策略
        self.register_recovery_strategy(
            ErrorType.PARSING_ERROR,
            self._recover_parsing_error
        )
        
        # 验证错误恢复策略
        self.register_recovery_strategy(
            ErrorType.VALIDATION_ERROR,
            self._recover_validation_error
        )
    
    def _recover_ai_service_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """恢复AI服务错误"""
        return {
            "success": False,
            "error": error_info.message,
            "fallback_result": self._get_fallback_result(error_info)
        }
    
    def _recover_parsing_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """恢复解析错误"""
        return {
            "success": False,
            "error": error_info.message,
            "raw_response": error_info.details.get("raw_response", ""),
            "fallback_result": self._get_fallback_result(error_info)
        }
    
    def _recover_validation_error(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """恢复验证错误"""
        return {
            "success": False,
            "error": error_info.message,
            "validation_details": error_info.details,
            "fallback_result": self._get_fallback_result(error_info)
        }
    
    def _get_fallback_result(self, error_info: ErrorInfo) -> Dict[str, Any]:
        """获取备用结果"""
        if error_info.error_type == ErrorType.AI_SERVICE_ERROR:
            return {
                "insights": ["AI服务暂时不可用，请稍后重试"],
                "recommendations": ["检查AI服务配置", "检查网络连接"]
            }
        elif error_info.error_type == ErrorType.PARSING_ERROR:
            return {
                "insights": ["响应解析失败，请检查数据格式"],
                "recommendations": ["检查AI响应格式", "使用备用解析方法"]
            }
        else:
            return {
                "insights": ["处理过程中发生错误"],
                "recommendations": ["检查输入数据", "联系技术支持"]
            }


# 全局错误处理器实例
_error_handler = None


def get_error_handler() -> AgentErrorHandler:
    """获取错误处理器实例（单例模式）"""
    global _error_handler
    if _error_handler is None:
        _error_handler = AgentErrorHandler()
    return _error_handler
