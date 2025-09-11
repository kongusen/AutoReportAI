"""
AI核心模块 - 基于Claude Code架构理念的重构版本

主要组件：
1. 统一控制器 (UnifiedController) - 替换复杂的编排系统
2. 安全检查器 (SecurityChecker) - 多层安全验证
3. API消息系统 - 双重消息表示
4. 心理学导向提示工程 - 优化的LLM交互
"""
from typing import Optional

# 核心组件导入
from .messages import AgentMessage, MessageType, ProgressData, ErrorData
from .tools import ToolChain, ToolContext, ToolResult, ToolResultType, BaseTool
from .context import ContextManager, TaskContext, TemplateContext, DataSourceContext, ExecutionContext
from .tasks import AgentTask, TaskType

# 重构后的新组件
from .api_messages import APIMessage, MessageConverter, StreamingJSONParser
from .security import SecurityChecker, SecurityLevel, SecurityCheckResult, get_security_checker
from .enhanced_prompts import SimplifiedPromptManager, get_simplified_prompt_manager
from .unified_controller import UnifiedController, get_unified_controller, tt
from .compatibility import CompatibilityLayer, get_compatibility_layer, execute_task_unified

# 向后兼容的旧组件
from .controller import AgentController
from .unified_orchestrator import UnifiedOrchestrator
from .prompts import PromptManager, prompt_manager

# 导出所有关键组件
__all__ = [
    # 消息系统
    "AgentMessage", "MessageType", "ProgressData", "ErrorData",
    "APIMessage", "MessageConverter", "StreamingJSONParser",
    
    # 工具系统
    "ToolChain", "ToolContext", "ToolResult", "ToolResultType", "BaseTool",
    
    # 上下文和任务
    "ContextManager", "TaskContext", "TemplateContext", "DataSourceContext", "ExecutionContext",
    "AgentTask", "TaskType",
    
    # 新的统一架构
    "UnifiedController", "get_unified_controller", "tt",
    "SecurityChecker", "SecurityLevel", "SecurityCheckResult", "get_security_checker",
    "SimplifiedPromptManager", "get_simplified_prompt_manager",
    
    # 兼容性层
    "CompatibilityLayer", "get_compatibility_layer", "execute_task_unified",
    
    # 向后兼容（逐步弃用）
    "AgentController", "UnifiedOrchestrator", "PromptManager", "prompt_manager"
]


# 便捷的系统入口类
class AutoReportAI:
    """
    统一的AI系统入口 - 基于Claude Code四层架构
    
    这是整个AI系统的主入口点，提供：
    1. 统一的任务处理接口
    2. 自动安全检查
    3. 智能工具选择
    4. 流式结果处理
    """
    
    def __init__(self, enable_security: bool = True, enable_compatibility: bool = True):
        self.controller = get_unified_controller()
        self.security_checker = get_security_checker() if enable_security else None
        self.compatibility_layer = get_compatibility_layer() if enable_compatibility else None
        
        # 系统配置
        self.enable_security = enable_security
        self.enable_compatibility = enable_compatibility
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0
    
    async def process_task(
        self, 
        task_description: str, 
        context: ToolContext
    ):
        """
        统一任务处理入口
        
        Args:
            task_description: 任务描述
            context: 执行上下文
            
        Yields:
            AgentMessage: 执行过程中的消息
        """
        self.total_requests += 1
        
        try:
            async for result in tt(task_description, context):
                yield result
            
            self.successful_requests += 1
            
        except Exception as e:
            yield AgentMessage.create_error(
                error_type="system_error",
                error_message=f"系统处理失败: {str(e)}",
                user_id=context.user_id,
                task_id=context.task_id
            )
    
    async def process_legacy_task(self, task: AgentTask):
        """
        处理旧格式任务（兼容性接口）
        
        Args:
            task: 旧格式任务对象
            
        Yields:
            AgentMessage: 执行结果
        """
        if not self.compatibility_layer:
            raise RuntimeError("兼容性层未启用")
        
        async for result in self.compatibility_layer.execute_task_compatible(task):
            yield result
    
    def get_system_statistics(self):
        """获取系统统计信息"""
        stats = {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "controller_stats": self.controller.get_statistics() if hasattr(self.controller, 'get_statistics') else {},
            "security_enabled": self.enable_security,
            "compatibility_enabled": self.enable_compatibility
        }
        
        if self.security_checker:
            stats["security_stats"] = self.security_checker.get_security_statistics()
        
        if self.compatibility_layer:
            stats["migration_stats"] = self.compatibility_layer.get_migration_statistics()
        
        return stats


# 全局AI系统实例
_auto_report_ai: Optional[AutoReportAI] = None


def get_auto_report_ai() -> AutoReportAI:
    """获取全局AI系统实例"""
    global _auto_report_ai
    if _auto_report_ai is None:
        _auto_report_ai = AutoReportAI()
    return _auto_report_ai


# 添加AutoReportAI到导出列表
__all__.extend(["AutoReportAI", "get_auto_report_ai"])