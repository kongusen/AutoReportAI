"""
增强的工具基础架构 v3.0
===============================================

基于现有BaseTool架构的全面优化：
- 更强大的错误处理和恢复机制
- 智能流式处理和进度管理
- 工具间依赖管理和协调能力
- 动态配置和自适应执行
- 企业级安全和监控集成
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator, Union, Callable, Set
from enum import Enum
import json

from .prompts import prompt_manager, PromptComplexity
from ..llm import ask_agent_for_user

logger = logging.getLogger(__name__)


class ToolResultType(Enum):
    """工具结果类型 - 扩展版"""
    PROGRESS = "progress"           # 进度更新
    RESULT = "result"               # 最终结果
    ERROR = "error"                 # 错误信息
    WARNING = "warning"             # 警告信息
    INFO = "info"                   # 信息提示
    VALIDATION = "validation"       # 验证结果
    DEPENDENCY = "dependency"       # 依赖状态
    RECOVERY = "recovery"           # 错误恢复
    OPTIMIZATION = "optimization"   # 优化建议


class ToolPriority(Enum):
    """工具优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ToolStatus(Enum):
    """工具状态"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolDependency:
    """工具依赖定义"""
    tool_name: str
    required: bool = True
    condition: Optional[Callable] = None
    timeout: Optional[int] = None


@dataclass
class ToolMetrics:
    """工具执行指标"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_duration: Optional[float] = None
    memory_usage: Optional[float] = None
    success_rate: float = 0.0
    error_count: int = 0
    retry_count: int = 0
    complexity_level: Optional[PromptComplexity] = None


@dataclass
class EnhancedToolContext:
    """增强的工具执行上下文"""
    # 基础信息
    user_id: str
    task_id: str
    session_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
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
    max_retries: int = 3
    timeout: Optional[int] = 300
    enable_learning: bool = True
    enable_optimization: bool = True
    
    # 质量控制
    confidence_threshold: float = 0.8
    validation_required: bool = True
    enable_recovery: bool = True
    
    # 执行历史和学习
    iteration_history: List[Dict[str, Any]] = field(default_factory=list)
    learned_insights: List[str] = field(default_factory=list)
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    optimization_hints: List[str] = field(default_factory=list)
    
    # 工具协调
    parent_tools: List[str] = field(default_factory=list)
    child_tools: List[str] = field(default_factory=list)
    tool_chain_id: Optional[str] = None
    
    # 额外上下文
    context_data: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    
    def add_insight(self, insight: str):
        """添加学到的经验"""
        if insight not in self.learned_insights:
            self.learned_insights.append(insight)
    
    def add_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """记录错误"""
        error_record = {
            "type": error_type,
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        self.error_history.append(error_record)
    
    def get_recent_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最近的错误"""
        return self.error_history[-limit:] if self.error_history else []


@dataclass
class EnhancedToolResult:
    """增强的工具执行结果"""
    type: ToolResultType
    data: Any
    tool_name: str
    
    # 执行信息
    iteration: Optional[int] = None
    step_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # 质量评估
    confidence: Optional[float] = None
    validation_passed: bool = True
    quality_score: Optional[float] = None
    
    # 错误和恢复信息
    error_details: Optional[Dict[str, Any]] = None
    recovery_suggestions: List[str] = field(default_factory=list)
    retry_count: int = 0
    
    # 学习和优化
    insights: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    performance_hints: List[str] = field(default_factory=list)
    
    # 依赖信息
    dependencies_met: List[str] = field(default_factory=list)
    dependencies_missing: List[str] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Optional[ToolMetrics] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type.value,
            "data": self.data,
            "tool_name": self.tool_name,
            "iteration": self.iteration,
            "step_name": self.step_name,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "validation_passed": self.validation_passed,
            "quality_score": self.quality_score,
            "error_details": self.error_details,
            "recovery_suggestions": self.recovery_suggestions,
            "retry_count": self.retry_count,
            "insights": self.insights,
            "optimization_suggestions": self.optimization_suggestions,
            "performance_hints": self.performance_hints,
            "dependencies_met": self.dependencies_met,
            "dependencies_missing": self.dependencies_missing,
            "metadata": self.metadata,
            "metrics": self.metrics.__dict__ if self.metrics else None
        }


class EnhancedBaseTool(ABC):
    """增强的基础工具类 - v3.0"""
    
    def __init__(
        self,
        tool_name: str,
        tool_category: str = "general",
        priority: ToolPriority = ToolPriority.NORMAL,
        dependencies: List[ToolDependency] = None,
        max_retries: int = 3,
        timeout: Optional[int] = 300
    ):
        self.tool_name = tool_name
        self.tool_category = tool_category
        self.priority = priority
        self.dependencies = dependencies or []
        self.max_retries = max_retries
        self.timeout = timeout
        
        # 状态管理
        self.status = ToolStatus.IDLE
        self.metrics = ToolMetrics()
        
        # 配置管理
        self.config = {}
        self.prompt_templates = {}
        
        # 日志记录
        self.logger = logging.getLogger(f"{__name__}.{tool_name}")
        
        # 初始化
        self._initialize()
    
    def _initialize(self):
        """工具初始化"""
        self.status = ToolStatus.INITIALIZING
        try:
            self._load_configuration()
            self._load_prompt_templates()
            self.status = ToolStatus.IDLE
            self.logger.info(f"工具 {self.tool_name} 初始化完成")
        except Exception as e:
            self.status = ToolStatus.FAILED
            self.logger.error(f"工具 {self.tool_name} 初始化失败: {e}")
            raise
    
    def _load_configuration(self):
        """加载工具配置"""
        # 从prompt_manager获取工具相关配置
        try:
            self.config = prompt_manager.get_tool_config(self.tool_name)
        except Exception:
            self.config = {}  # 使用默认配置
    
    def _load_prompt_templates(self):
        """加载提示词模板"""
        try:
            self.prompt_templates = prompt_manager.get_tool_prompts(self.tool_name)
        except Exception:
            self.prompt_templates = {}  # 使用默认模板
    
    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: EnhancedToolContext
    ) -> AsyncGenerator[EnhancedToolResult, None]:
        """
        执行工具逻辑 - 抽象方法
        
        Args:
            input_data: 输入数据
            context: 增强的执行上下文
            
        Yields:
            EnhancedToolResult: 可能是进度更新或最终结果
        """
        pass
    
    async def execute_with_retry(
        self,
        input_data: Dict[str, Any],
        context: EnhancedToolContext
    ) -> AsyncGenerator[EnhancedToolResult, None]:
        """带重试机制的执行"""
        retry_count = 0
        last_error = None
        
        while retry_count <= self.max_retries:
            try:
                self.status = ToolStatus.RUNNING
                self.metrics.start_time = datetime.utcnow()
                
                # 检查依赖
                deps_check = await self._check_dependencies(context)
                if not deps_check["all_met"]:
                    yield self.create_dependency_result(deps_check)
                    return
                
                # 执行主逻辑
                async for result in self.execute(input_data, context):
                    result.retry_count = retry_count
                    yield result
                    
                    # 如果是最终结果且成功，更新指标并返回
                    if result.type == ToolResultType.RESULT and result.validation_passed:
                        self._update_success_metrics()
                        return
                
                # 如果到这里说明没有返回最终结果，尝试重试
                retry_count += 1
                if retry_count <= self.max_retries:
                    yield self.create_recovery_result(f"第 {retry_count} 次重试")
                    await asyncio.sleep(2 ** retry_count)  # 指数退避
                
            except Exception as e:
                last_error = e
                self.logger.error(f"工具执行失败 (重试 {retry_count}/{self.max_retries}): {e}")
                
                # 记录错误
                context.add_error("execution_error", str(e), {"retry_count": retry_count})
                
                # 如果还有重试机会，继续
                retry_count += 1
                if retry_count <= self.max_retries:
                    yield self.create_error_result(str(e), recoverable=True)
                    await asyncio.sleep(2 ** retry_count)
                else:
                    # 最后一次重试失败
                    self._update_error_metrics()
                    yield self.create_error_result(str(last_error), recoverable=False)
                    return
        
        # 如果所有重试都失败
        self._update_error_metrics()
        yield self.create_error_result(
            f"工具执行失败，已重试 {self.max_retries} 次",
            recoverable=False
        )
    
    async def _check_dependencies(self, context: EnhancedToolContext) -> Dict[str, Any]:
        """检查工具依赖"""
        deps_status = {
            "all_met": True,
            "met": [],
            "missing": [],
            "details": {}
        }
        
        for dep in self.dependencies:
            try:
                # 检查依赖条件
                if dep.condition:
                    is_met = await dep.condition(context)
                else:
                    is_met = True  # 默认认为满足
                
                if is_met:
                    deps_status["met"].append(dep.tool_name)
                else:
                    deps_status["missing"].append(dep.tool_name)
                    if dep.required:
                        deps_status["all_met"] = False
                
                deps_status["details"][dep.tool_name] = {
                    "required": dep.required,
                    "met": is_met,
                    "timeout": dep.timeout
                }
                
            except Exception as e:
                self.logger.error(f"检查依赖 {dep.tool_name} 失败: {e}")
                deps_status["missing"].append(dep.tool_name)
                if dep.required:
                    deps_status["all_met"] = False
        
        return deps_status
    
    def _update_success_metrics(self):
        """更新成功指标"""
        self.status = ToolStatus.COMPLETED
        self.metrics.end_time = datetime.utcnow()
        if self.metrics.start_time:
            self.metrics.execution_duration = (
                self.metrics.end_time - self.metrics.start_time
            ).total_seconds()
        self.metrics.success_rate = min(1.0, self.metrics.success_rate + 0.1)
    
    def _update_error_metrics(self):
        """更新错误指标"""
        self.status = ToolStatus.FAILED
        self.metrics.end_time = datetime.utcnow()
        self.metrics.error_count += 1
        self.metrics.success_rate = max(0.0, self.metrics.success_rate - 0.1)
    
    async def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证输入数据 - 增强版"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        try:
            # 基础验证
            if not isinstance(input_data, dict):
                validation_result["valid"] = False
                validation_result["errors"].append("输入数据必须是字典格式")
                return validation_result
            
            # 调用子类的具体验证逻辑
            specific_validation = await self._validate_specific_input(input_data)
            
            # 合并验证结果
            validation_result["valid"] = validation_result["valid"] and specific_validation.get("valid", True)
            validation_result["errors"].extend(specific_validation.get("errors", []))
            validation_result["warnings"].extend(specific_validation.get("warnings", []))
            validation_result["suggestions"].extend(specific_validation.get("suggestions", []))
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"验证过程出错: {str(e)}")
        
        return validation_result
    
    async def _validate_specific_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """子类可以重写的具体验证逻辑"""
        return {"valid": True, "errors": [], "warnings": [], "suggestions": []}
    
    def create_progress_result(
        self,
        message: str,
        step: Optional[str] = None,
        percentage: Optional[float] = None,
        insights: List[str] = None
    ) -> EnhancedToolResult:
        """创建进度结果"""
        return EnhancedToolResult(
            type=ToolResultType.PROGRESS,
            data=message,
            tool_name=self.tool_name,
            step_name=step,
            insights=insights or [],
            metadata={
                "percentage": percentage,
                "status": self.status.value
            }
        )
    
    def create_success_result(
        self,
        data: Any,
        confidence: Optional[float] = None,
        insights: List[str] = None,
        optimization_suggestions: List[str] = None
    ) -> EnhancedToolResult:
        """创建成功结果"""
        return EnhancedToolResult(
            type=ToolResultType.RESULT,
            data=data,
            tool_name=self.tool_name,
            confidence=confidence,
            validation_passed=True,
            insights=insights or [],
            optimization_suggestions=optimization_suggestions or [],
            metrics=self.metrics
        )
    
    def create_error_result(
        self,
        error_message: str,
        error_type: str = "execution_error",
        recoverable: bool = True,
        recovery_suggestions: List[str] = None
    ) -> EnhancedToolResult:
        """创建错误结果"""
        return EnhancedToolResult(
            type=ToolResultType.ERROR,
            data=error_message,
            tool_name=self.tool_name,
            validation_passed=False,
            error_details={
                "type": error_type,
                "message": error_message,
                "recoverable": recoverable
            },
            recovery_suggestions=recovery_suggestions or [],
            metrics=self.metrics
        )
    
    def create_dependency_result(self, deps_check: Dict[str, Any]) -> EnhancedToolResult:
        """创建依赖检查结果"""
        return EnhancedToolResult(
            type=ToolResultType.DEPENDENCY,
            data="依赖检查结果",
            tool_name=self.tool_name,
            dependencies_met=deps_check["met"],
            dependencies_missing=deps_check["missing"],
            validation_passed=deps_check["all_met"],
            metadata=deps_check["details"]
        )
    
    def create_recovery_result(self, message: str) -> EnhancedToolResult:
        """创建恢复结果"""
        return EnhancedToolResult(
            type=ToolResultType.RECOVERY,
            data=message,
            tool_name=self.tool_name,
            metadata={"status": self.status.value}
        )
    
    def get_optimized_prompt(
        self,
        prompt_type: str,
        context: EnhancedToolContext,
        **kwargs
    ) -> str:
        """获取优化的提示词"""
        try:
            return prompt_manager.get_prompt(
                category=self.tool_category,
                prompt_type=prompt_type,
                context={
                    "tool_name": self.tool_name,
                    "complexity": context.complexity,
                    "learned_insights": context.learned_insights,
                    "error_history": context.get_recent_errors(),
                    **kwargs
                },
                complexity=context.complexity
            )
        except Exception as e:
            self.logger.error(f"获取提示词失败: {e}")
            return self._get_fallback_prompt(prompt_type, **kwargs)
    
    def _get_fallback_prompt(self, prompt_type: str, **kwargs) -> str:
        """获取回退提示词"""
        return f"请执行 {self.tool_name} 的 {prompt_type} 任务。输入参数: {kwargs}"
    
    async def learn_from_execution(
        self,
        result: EnhancedToolResult,
        context: EnhancedToolContext
    ):
        """从执行结果中学习"""
        if not context.enable_learning:
            return
        
        try:
            # 基于结果质量生成学习洞察
            if result.confidence and result.confidence > 0.8:
                context.add_insight(f"高质量结果策略：{result.step_name}")
            
            # 基于错误生成学习洞察
            if result.type == ToolResultType.ERROR and result.recovery_suggestions:
                for suggestion in result.recovery_suggestions:
                    context.add_insight(f"错误恢复策略：{suggestion}")
            
            # 记录性能洞察
            if result.metrics and result.metrics.execution_duration:
                if result.metrics.execution_duration < 10:  # 快速执行
                    context.add_insight("快速执行路径已验证")
                elif result.metrics.execution_duration > 60:  # 慢速执行
                    context.add_insight("需要优化执行效率")
            
        except Exception as e:
            self.logger.error(f"学习过程出错: {e}")


class IterativeEnhancedTool(EnhancedBaseTool):
    """支持迭代执行的增强工具"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_iterations = 5
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: EnhancedToolContext
    ) -> AsyncGenerator[EnhancedToolResult, None]:
        """迭代执行框架"""
        
        iteration = 0
        current_data = input_data.copy()
        accumulated_insights = []
        
        while iteration < min(self.max_iterations, context.max_iterations):
            iteration += 1
            
            yield self.create_progress_result(
                f"开始第 {iteration} 次迭代",
                step=f"iteration_{iteration}",
                percentage=(iteration - 1) / self.max_iterations * 100
            )
            
            try:
                # 执行单次迭代
                async for result in self.execute_single_iteration(
                    current_data, context, iteration
                ):
                    result.iteration = iteration
                    
                    # 收集洞察
                    if result.insights:
                        accumulated_insights.extend(result.insights)
                    
                    yield result
                    
                    # 检查是否应该停止迭代
                    if result.type == ToolResultType.RESULT:
                        if await self.should_stop_iteration(result, context):
                            # 添加所有累积的洞察
                            result.insights = list(set(accumulated_insights))
                            return
                        else:
                            # 准备下一次迭代的数据
                            current_data = await self.prepare_next_iteration(
                                result, current_data, context
                            )
                
            except Exception as e:
                yield self.create_error_result(
                    f"第 {iteration} 次迭代失败: {str(e)}",
                    recoverable=iteration < self.max_iterations
                )
                
                if iteration >= self.max_iterations:
                    return
        
        # 如果达到最大迭代次数
        yield self.create_error_result(
            f"达到最大迭代次数 {self.max_iterations}，未获得满意结果",
            recoverable=False
        )
    
    @abstractmethod
    async def execute_single_iteration(
        self,
        input_data: Dict[str, Any],
        context: EnhancedToolContext,
        iteration: int
    ) -> AsyncGenerator[EnhancedToolResult, None]:
        """执行单次迭代 - 子类必须实现"""
        pass
    
    async def should_stop_iteration(
        self,
        result: EnhancedToolResult,
        context: EnhancedToolContext
    ) -> bool:
        """判断是否应该停止迭代"""
        # 默认停止条件
        return (
            result.confidence and result.confidence >= context.confidence_threshold
        ) or result.validation_passed
    
    async def prepare_next_iteration(
        self,
        result: EnhancedToolResult,
        current_data: Dict[str, Any],
        context: EnhancedToolContext
    ) -> Dict[str, Any]:
        """准备下一次迭代的数据"""
        # 默认保持原数据，子类可以重写
        return current_data


# 工具装饰器
def tool_monitor(func):
    """工具监控装饰器"""
    async def wrapper(self, *args, **kwargs):
        start_time = datetime.utcnow()
        try:
            result = await func(self, *args, **kwargs)
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(f"工具 {self.tool_name} 执行成功，耗时 {duration:.2f}s")
            return result
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(f"工具 {self.tool_name} 执行失败，耗时 {duration:.2f}s: {e}")
            raise
    return wrapper


def tool_cache(ttl: int = 300):
    """工具结果缓存装饰器"""
    cache = {}
    
    def decorator(func):
        async def wrapper(self, input_data, context, *args, **kwargs):
            # 生成缓存键
            cache_key = f"{self.tool_name}_{hash(str(input_data))}"
            
            # 检查缓存
            if cache_key in cache:
                cached_result, cached_time = cache[cache_key]
                if datetime.utcnow() - cached_time < timedelta(seconds=ttl):
                    self.logger.info(f"使用缓存结果: {cache_key}")
                    yield cached_result
                    return
            
            # 执行并缓存结果
            async for result in func(self, input_data, context, *args, **kwargs):
                if result.type == ToolResultType.RESULT:
                    cache[cache_key] = (result, datetime.utcnow())
                yield result
        
        return wrapper
    return decorator