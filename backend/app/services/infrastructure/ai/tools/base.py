"""
新工具系统基础架构
===============================================

重新设计的工具基类，完全集成优化提示词系统
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator
from enum import Enum

from ..core.prompts import prompt_manager, PromptComplexity
from ..llm import ask_agent_for_user

logger = logging.getLogger(__name__)


class ToolResultType(Enum):
    """工具结果类型"""
    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ToolContext:
    """工具执行上下文 - v2优化版"""
    user_id: str
    task_id: str
    session_id: str
    
    # 数据源信息
    data_source_id: Optional[str] = None
    data_source_info: Optional[Dict[str, Any]] = None
    
    # 模板信息
    template_id: Optional[str] = None
    template_content: Optional[str] = None
    
    # 占位符信息
    placeholders: List[Dict[str, Any]] = field(default_factory=list)
    
    # 执行配置
    complexity: PromptComplexity = PromptComplexity.MEDIUM
    max_iterations: int = 5
    enable_learning: bool = True
    
    # 执行历史和学习
    iteration_history: List[Dict[str, Any]] = field(default_factory=list)
    learned_insights: List[str] = field(default_factory=list)
    error_history: List[str] = field(default_factory=list)
    
    # 额外上下文
    context_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """工具执行结果 - v2增强版"""
    type: ToolResultType
    data: Any
    
    # 迭代信息
    iteration: Optional[int] = None
    step_name: Optional[str] = None
    
    # 质量评估
    confidence: Optional[float] = None
    validation_passed: bool = True
    
    # 错误信息
    error_details: Optional[Dict[str, Any]] = None
    
    # 学习信息
    insights: List[str] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BaseTool(ABC):
    """新一代工具基类 - 与优化提示词系统深度集成"""
    
    def __init__(self, tool_name: str, tool_category: str = "general"):
        self.tool_name = tool_name
        self.tool_category = tool_category
        self.prompt_manager = prompt_manager
        self.logger = logging.getLogger(f"{__name__}.{tool_name}")
        
        # 工具特定配置
        self.default_complexity = PromptComplexity.MEDIUM
        self.supports_iteration = True
        self.requires_validation = True
    
    @abstractmethod
    async def execute(
        self, 
        context: ToolContext,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """
        执行工具逻辑
        
        Args:
            context: 工具执行上下文
            **kwargs: 额外参数
            
        Yields:
            ToolResult: 执行结果流
        """
        pass
    
    async def validate_input(self, context: ToolContext, **kwargs) -> bool:
        """验证输入参数"""
        try:
            # 基础验证
            if not context.user_id:
                self.logger.error("缺少用户ID")
                return False
            
            # 子类可以覆盖此方法进行特定验证
            return await self._validate_specific_input(context, **kwargs)
            
        except Exception as e:
            self.logger.error(f"输入验证异常: {e}")
            return False
    
    async def _validate_specific_input(self, context: ToolContext, **kwargs) -> bool:
        """子类特定的输入验证"""
        return True
    
    def create_progress_result(
        self, 
        message: str, 
        step_name: str = None,
        iteration: int = None,
        confidence: float = None
    ) -> ToolResult:
        """创建进度结果"""
        return ToolResult(
            type=ToolResultType.PROGRESS,
            data=message,
            step_name=step_name,
            iteration=iteration,
            confidence=confidence
        )
    
    def create_success_result(
        self, 
        data: Any,
        confidence: float = None,
        insights: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> ToolResult:
        """创建成功结果"""
        return ToolResult(
            type=ToolResultType.RESULT,
            data=data,
            confidence=confidence,
            insights=insights or [],
            metadata=metadata or {},
            validation_passed=True
        )
    
    def create_error_result(
        self, 
        error_message: str,
        error_type: str = "execution_error",
        error_details: Dict[str, Any] = None
    ) -> ToolResult:
        """创建错误结果"""
        return ToolResult(
            type=ToolResultType.ERROR,
            data=error_message,
            error_details={
                "error_type": error_type,
                "error_message": error_message,
                **(error_details or {})
            },
            validation_passed=False
        )
    
    def create_warning_result(
        self, 
        warning_message: str,
        data: Any = None
    ) -> ToolResult:
        """创建警告结果"""
        return ToolResult(
            type=ToolResultType.WARNING,
            data=data or warning_message,
            metadata={"warning": warning_message}
        )
    
    async def ask_llm(
        self,
        prompt: str,
        context: ToolContext,
        agent_type: str = "general",
        task_type: str = None,
        complexity: str = None
    ) -> str:
        """调用LLM - 统一接口"""
        try:
            response = await ask_agent_for_user(
                user_id=context.user_id,
                question=prompt,
                agent_type=agent_type,
                context=f"工具: {self.tool_name}",
                task_type=task_type or self.tool_category,
                complexity=complexity or context.complexity.value
            )
            return response
            
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise
    
    def get_prompt(
        self,
        prompt_category: str,
        prompt_type: str,
        context: ToolContext,
        **prompt_kwargs
    ) -> str:
        """获取优化提示词"""
        try:
            # 准备提示词上下文
            prompt_context = {
                **prompt_kwargs,
                'complexity': context.complexity,
                'iteration_history': context.iteration_history,
                'learned_insights': context.learned_insights,
                'error_history': context.error_history
            }
            
            # 获取提示词
            prompt = self.prompt_manager.get_prompt(
                category=prompt_category,
                prompt_type=prompt_type,
                context=prompt_context
            )
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"获取提示词失败: {e}")
            raise
    
    def add_to_history(
        self,
        context: ToolContext,
        step_name: str,
        result: Dict[str, Any],
        success: bool = True
    ):
        """添加执行历史"""
        history_entry = {
            "tool": self.tool_name,
            "step": step_name,
            "result": result,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        context.iteration_history.append(history_entry)
    
    def add_insight(self, context: ToolContext, insight: str):
        """添加学习洞察"""
        if insight not in context.learned_insights:
            context.learned_insights.append(insight)
    
    def add_error(self, context: ToolContext, error: str):
        """添加错误历史"""
        context.error_history.append(error)
    
    def get_complexity_level(self, context: ToolContext) -> PromptComplexity:
        """动态评估复杂度级别"""
        # 基于错误历史和迭代次数动态调整复杂度
        error_count = len(context.error_history)
        iteration_count = len(context.iteration_history)
        
        if error_count >= 3 or iteration_count >= 3:
            return PromptComplexity.CRITICAL
        elif error_count >= 1 or iteration_count >= 1:
            return PromptComplexity.HIGH
        elif len(context.placeholders) > 5:
            return PromptComplexity.HIGH
        else:
            return context.complexity


class IterativeTool(BaseTool):
    """支持迭代执行的工具基类"""
    
    def __init__(self, tool_name: str, tool_category: str = "iterative"):
        super().__init__(tool_name, tool_category)
        self.max_iterations = 5
        self.supports_iteration = True
    
    async def execute_with_iteration(
        self,
        context: ToolContext,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """支持迭代的执行方法"""
        
        yield self.create_progress_result(f"开始迭代执行: {self.tool_name}")
        
        max_iterations = context.max_iterations or self.max_iterations
        
        for iteration in range(max_iterations):
            try:
                yield self.create_progress_result(
                    f"第 {iteration + 1}/{max_iterations} 轮迭代",
                    step_name="iteration",
                    iteration=iteration
                )
                
                # 执行单次迭代
                success = False
                async for result in self._execute_iteration(context, iteration, **kwargs):
                    yield result
                    if result.type == ToolResultType.RESULT:
                        success = True
                        
                        # 检查是否满足完成条件
                        if await self._should_stop_iteration(context, result, iteration):
                            yield self.create_success_result(
                                result.data,
                                confidence=result.confidence,
                                insights=result.insights + [f"在第{iteration + 1}轮完成"],
                                metadata={"iterations_used": iteration + 1}
                            )
                            return
                
                if not success:
                    self.add_error(context, f"第{iteration + 1}轮迭代失败")
                    
            except Exception as e:
                error_msg = f"第{iteration + 1}轮迭代异常: {str(e)}"
                self.logger.error(error_msg)
                self.add_error(context, error_msg)
                yield self.create_error_result(error_msg)
        
        # 达到最大迭代次数
        yield self.create_warning_result(
            f"达到最大迭代次数 ({max_iterations})，任务可能未完全完成",
            data={"iterations_used": max_iterations, "status": "partial"}
        )
    
    @abstractmethod
    async def _execute_iteration(
        self,
        context: ToolContext,
        iteration: int,
        **kwargs
    ) -> AsyncGenerator[ToolResult, None]:
        """执行单次迭代"""
        pass
    
    async def _should_stop_iteration(
        self,
        context: ToolContext,
        result: ToolResult,
        iteration: int
    ) -> bool:
        """判断是否应该停止迭代"""
        # 默认实现：高置信度或验证通过则停止
        return (
            result.confidence and result.confidence > 0.8
        ) or result.validation_passed