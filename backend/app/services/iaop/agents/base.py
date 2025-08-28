from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from ..context.execution_context import EnhancedExecutionContext, ContextScope


class AgentType(Enum):
    """Agent类型枚举"""
    PLACEHOLDER_PARSER = "placeholder_parser"
    DATA_QUERY = "data_query"
    DATA_ANALYSIS = "data_analysis"
    CHART_GENERATOR = "chart_generator"
    INSIGHT_NARRATOR = "insight_narrator"
    SQL_GENERATOR = "sql_generator"
    QUALITY_ASSESSOR = "quality_assessor"
    SEMANTIC_ANALYZER = "semantic_analyzer"


@dataclass
class AgentCapabilities:
    """Agent能力定义"""
    supported_input_types: List[str]
    supported_output_types: List[str]
    required_context: List[str]
    optional_context: List[str]
    processing_modes: List[str]
    max_parallel_tasks: int = 1
    timeout_seconds: int = 60
    supports_streaming: bool = False
    supports_caching: bool = True


class ExecutionContext:
    """执行上下文 - 简化版本以保持兼容性"""
    
    def __init__(self, session_id: str, user_id: str, task_id: str = None):
        self.session_id = session_id
        self.user_id = user_id
        self.task_id = task_id or session_id
        self.context_data: Dict[str, Any] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return self.context_data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置上下文数据"""
        self.context_data[key] = value
    
    def add_execution_record(self, agent_name: str, action: str, result: Dict[str, Any], duration: float = 0):
        """添加执行记录"""
        record = {
            "agent_name": agent_name,
            "action": action,
            "result": result,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.execution_history.append(record)


class BaseAgent(ABC):
    """增强的基础Agent类 - 整合上下文管理功能"""
    
    def __init__(self, name: str, capabilities: List[str] | None = None):
        self.name = name
        self.capabilities = capabilities or []
        self._context_requirements: List[str] = []

    def require_context(self, *context_keys: str):
        """声明所需的上下文键"""
        self._context_requirements.extend(context_keys)

    async def validate_preconditions(self, context: EnhancedExecutionContext) -> bool:
        """验证前置条件 - 检查上下文要求"""
        missing_context = [
            key for key in self._context_requirements 
            if context.get_context(key) is None
        ]
        if missing_context:
            print(f"Warning: {self.name} missing required context: {missing_context}")
            return False
        return True

    async def execute_with_tracking(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """带跟踪的执行方法"""
        # 检查前置条件
        if not await self.validate_preconditions(context):
            raise ValueError(f"Preconditions not met for agent: {self.name}")
        
        # 记录执行开始
        start_time = datetime.utcnow()
        
        try:
            # 执行具体操作
            result = await self.execute(context)
            
            # 记录执行结果
            duration = (datetime.utcnow() - start_time).total_seconds()
            context.add_execution_record(
                agent_name=self.name,
                action="execute",
                result=result,
                duration=duration
            )
            
            return result
            
        except Exception as e:
            # 记录执行错误
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_result = {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
            context.add_execution_record(
                agent_name=self.name,
                action="execute",
                result=error_result,
                duration=duration
            )
            # 添加错误堆栈
            context.error_stack.append({
                'agent': self.name,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
            raise
    
    def update_context(self, context: EnhancedExecutionContext, key: str, value: Any, 
                      scope: ContextScope = ContextScope.TASK):
        """更新上下文"""
        context.set_context(key, value, scope, {'updated_by': self.name})

    @abstractmethod
    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行具体操作 - 子类需要实现"""
        raise NotImplementedError


