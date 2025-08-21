"""
Service Orchestrator

统一的服务编排层，协调所有services层的服务
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

# Import domain services
from ...domain.placeholder.services.placeholder_domain_service import PlaceholderDomainService
from ...domain.template.services.template_domain_service import TemplateDomainService
from ...domain.analysis.services.data_analysis_domain_service import DataAnalysisDomainService
from ...domain.reporting.services.report_generation_domain_service import ReportGenerationDomainService

# Import AI services
from ...ai.core.context_manager import ContextManager, AgentContext
from ...ai.core.prompt_engine import PromptEngine
from ...ai.core.agent_registry import AgentRegistry

# Import task services
from ..task_management.core.scheduler import TaskScheduler as RefactoredTaskManager
from ..task_management.execution.two_phase_pipeline import ExecutionMode

# Import workflow engine
from .workflow_engine import WorkflowEngine, WorkflowDefinition, StepDefinition, StepType

logger = logging.getLogger(__name__)


class OrchestrationMode(Enum):
    """编排模式"""
    SIMPLE = "simple"           # 简单模式，单一服务调用
    PIPELINE = "pipeline"       # 流水线模式，顺序调用多个服务
    PARALLEL = "parallel"       # 并行模式，并行调用多个服务
    WORKFLOW = "workflow"       # 工作流模式，使用工作流引擎
    AI_DRIVEN = "ai_driven"     # AI驱动模式，由AI决定服务调用顺序


@dataclass
class ServiceContext:
    """服务上下文"""
    request_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 执行上下文
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    # 服务调用记录
    service_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    # AI上下文
    ai_context: Optional[AgentContext] = None
    
    def add_service_call(self, service_name: str, method_name: str, 
                        inputs: Dict[str, Any], outputs: Dict[str, Any],
                        duration: float, success: bool):
        """添加服务调用记录"""
        self.service_calls.append({
            "service_name": service_name,
            "method_name": method_name,
            "inputs": inputs,
            "outputs": outputs,
            "duration": duration,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @property
    def total_duration(self) -> Optional[float]:
        """总执行时长"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class ServiceOrchestrator:
    """服务编排器"""
    
    def __init__(self):
        # 初始化核心服务
        self.context_manager = ContextManager()
        self.prompt_engine = PromptEngine()
        self.agent_registry = AgentRegistry()
        self.workflow_engine = WorkflowEngine()
        
        # 初始化领域服务
        self.placeholder_service = PlaceholderDomainService()
        self.template_service = TemplateDomainService()
        self.analysis_service = DataAnalysisDomainService()
        self.reporting_service = ReportGenerationDomainService()
        
        # 任务管理器（延迟初始化）
        self._task_manager: Optional[RefactoredTaskManager] = None
        
        # 服务注册表
        self.services = {
            "placeholder": self.placeholder_service,
            "template": self.template_service,
            "analysis": self.analysis_service,
            "reporting": self.reporting_service,
            "context": self.context_manager,
            "prompt": self.prompt_engine,
            "agent_registry": self.agent_registry,
            "workflow": self.workflow_engine
        }
        
        # 编排策略
        self.orchestration_strategies = {
            OrchestrationMode.SIMPLE: self._execute_simple,
            OrchestrationMode.PIPELINE: self._execute_pipeline,
            OrchestrationMode.PARALLEL: self._execute_parallel,
            OrchestrationMode.WORKFLOW: self._execute_workflow,
            OrchestrationMode.AI_DRIVEN: self._execute_ai_driven
        }
        
        logger.info("Service Orchestrator initialized")
    
    async def get_task_manager(self) -> RefactoredTaskManager:
        """获取任务管理器（延迟初始化）"""
        if self._task_manager is None:
            # Adjusted to new task management scheduler
            self._task_manager = RefactoredTaskManager()
        return self._task_manager
    
    async def execute(self, request: Dict[str, Any], 
                     mode: OrchestrationMode = OrchestrationMode.SIMPLE) -> Dict[str, Any]:
        """
        执行服务编排
        
        Args:
            request: 请求数据
            mode: 编排模式
            
        Returns:
            编排结果
        """
        try:
            # 创建服务上下文
            context = ServiceContext(
                request_id=request.get("request_id", f"req_{datetime.utcnow().timestamp()}"),
                user_id=request.get("user_id"),
                session_id=request.get("session_id"),
                metadata=request.get("metadata", {})
            )
            
            # 创建AI上下文（如果需要）
            if mode == OrchestrationMode.AI_DRIVEN or request.get("use_ai_context"):
                context.ai_context = await self.context_manager.create_context(
                    context_id=context.request_id,
                    user_id=context.user_id,
                    metadata=context.metadata
                )
            
            logger.info(f"Starting orchestration: {context.request_id}, mode: {mode.value}")
            
            # 执行编排策略
            strategy = self.orchestration_strategies[mode]
            result = await strategy(request, context)
            
            # 完成上下文
            context.end_time = datetime.utcnow()
            
            # 构建响应
            response = {
                "success": True,
                "request_id": context.request_id,
                "mode": mode.value,
                "data": result,
                "execution_summary": {
                    "total_duration": context.total_duration,
                    "service_calls": len(context.service_calls),
                    "start_time": context.start_time.isoformat(),
                    "end_time": context.end_time.isoformat()
                },
                "service_calls": context.service_calls
            }
            
            logger.info(f"Orchestration completed: {context.request_id}")
            return response
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "request_id": request.get("request_id", "unknown")
            }
    
    async def _execute_simple(self, request: Dict[str, Any], 
                            context: ServiceContext) -> Dict[str, Any]:
        """简单模式执行"""
        service_name = request.get("service")
        method_name = request.get("method")
        parameters = request.get("parameters", {})
        
        if not service_name or not method_name:
            raise ValueError("Service and method must be specified for simple mode")
        
        return await self._call_service(service_name, method_name, parameters, context)
    
    async def _execute_pipeline(self, request: Dict[str, Any], 
                              context: ServiceContext) -> Dict[str, Any]:
        """流水线模式执行"""
        pipeline = request.get("pipeline", [])
        if not pipeline:
            raise ValueError("Pipeline must be specified for pipeline mode")
        
        results = []
        previous_result = None
        
        for i, step in enumerate(pipeline):
            step_name = step.get("name", f"step_{i}")
            service_name = step.get("service")
            method_name = step.get("method")
            parameters = step.get("parameters", {})
            
            # 将前一步的结果作为输入（如果配置了）
            if step.get("use_previous_result") and previous_result:
                parameters.update(previous_result)
            
            logger.info(f"Executing pipeline step {step_name}")
            step_result = await self._call_service(service_name, method_name, parameters, context)
            
            results.append({
                "step": step_name,
                "result": step_result
            })
            
            previous_result = step_result
        
        return {
            "pipeline_results": results,
            "final_result": previous_result
        }
    
    async def _execute_parallel(self, request: Dict[str, Any], 
                              context: ServiceContext) -> Dict[str, Any]:
        """并行模式执行"""
        tasks = request.get("tasks", [])
        if not tasks:
            raise ValueError("Tasks must be specified for parallel mode")
        
        # 创建并行任务
        async_tasks = []
        for task in tasks:
            task_name = task.get("name", f"task_{len(async_tasks)}")
            service_name = task.get("service")
            method_name = task.get("method")
            parameters = task.get("parameters", {})
            
            async_task = self._call_service_with_name(
                task_name, service_name, method_name, parameters, context
            )
            async_tasks.append(async_task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        # 处理结果
        task_results = []
        for i, result in enumerate(results):
            task_name = tasks[i].get("name", f"task_{i}")
            if isinstance(result, Exception):
                task_results.append({
                    "task": task_name,
                    "success": False,
                    "error": str(result)
                })
            else:
                task_results.append({
                    "task": task_name,
                    "success": True,
                    "result": result
                })
        
        return {"parallel_results": task_results}
    
    async def _execute_workflow(self, request: Dict[str, Any], 
                              context: ServiceContext) -> Dict[str, Any]:
        """工作流模式执行"""
        workflow_def = request.get("workflow")
        workflow_inputs = request.get("inputs", {})
        
        if not workflow_def:
            raise ValueError("Workflow definition must be specified for workflow mode")
        
        # 如果是字典，转换为WorkflowDefinition
        if isinstance(workflow_def, dict):
            workflow_def = self._dict_to_workflow_definition(workflow_def)
        
        # 执行工作流
        execution = await self.workflow_engine.execute_workflow(workflow_def, workflow_inputs)
        
        return {
            "workflow_id": execution.workflow_def.workflow_id,
            "status": execution.status.value,
            "outputs": execution.context.outputs,
            "duration": execution.duration,
            "completed_steps": len(execution.completed_steps),
            "failed_steps": len(execution.failed_steps)
        }
    
    async def _execute_ai_driven(self, request: Dict[str, Any], 
                               context: ServiceContext) -> Dict[str, Any]:
        """AI驱动模式执行"""
        if not context.ai_context:
            raise ValueError("AI context required for AI-driven mode")
        
        goal = request.get("goal")
        available_services = request.get("services", list(self.services.keys()))
        constraints = request.get("constraints", {})
        
        if not goal:
            raise ValueError("Goal must be specified for AI-driven mode")
        
        # 使用AI规划服务调用序列
        plan = await self._plan_service_calls(goal, available_services, constraints, context)
        
        # 执行计划
        results = []
        for step in plan["steps"]:
            step_result = await self._call_service(
                step["service"],
                step["method"],
                step["parameters"],
                context
            )
            results.append({
                "step": step["name"],
                "result": step_result
            })
        
        return {
            "plan": plan,
            "results": results
        }
    
    async def _call_service(self, service_name: str, method_name: str,
                          parameters: Dict[str, Any], context: ServiceContext) -> Any:
        """调用服务方法"""
        start_time = datetime.utcnow()
        
        try:
            service = self.services.get(service_name)
            if not service:
                raise ValueError(f"Service '{service_name}' not found")
            
            method = getattr(service, method_name, None)
            if not method:
                raise ValueError(f"Method '{method_name}' not found in service '{service_name}'")
            
            # 调用方法
            if asyncio.iscoroutinefunction(method):
                result = await method(**parameters)
            else:
                result = method(**parameters)
            
            # 记录成功调用
            duration = (datetime.utcnow() - start_time).total_seconds()
            context.add_service_call(
                service_name=service_name,
                method_name=method_name,
                inputs=parameters,
                outputs=result,
                duration=duration,
                success=True
            )
            
            return result
            
        except Exception as e:
            # 记录失败调用
            duration = (datetime.utcnow() - start_time).total_seconds()
            context.add_service_call(
                service_name=service_name,
                method_name=method_name,
                inputs=parameters,
                outputs={"error": str(e)},
                duration=duration,
                success=False
            )
            raise
    
    async def _call_service_with_name(self, task_name: str, service_name: str,
                                    method_name: str, parameters: Dict[str, Any],
                                    context: ServiceContext) -> Dict[str, Any]:
        """带任务名的服务调用（用于并行执行）"""
        try:
            result = await self._call_service(service_name, method_name, parameters, context)
            return {"task": task_name, "result": result}
        except Exception as e:
            return {"task": task_name, "error": str(e)}
    
    async def _plan_service_calls(self, goal: str, available_services: List[str],
                                constraints: Dict[str, Any], context: ServiceContext) -> Dict[str, Any]:
        """使用AI规划服务调用序列"""
        # 构建规划提示
        prompt_data = {
            "goal": goal,
            "available_services": available_services,
            "constraints": constraints,
            "service_descriptions": self._get_service_descriptions(available_services)
        }
        
        planning_prompt = await self.prompt_engine.generate_prompt(
            template_name="service_planning",
            context_data=prompt_data,
            context=context.ai_context
        )
        
        # 这里应该调用LLM生成计划
        # 简化实现，返回默认计划
        return {
            "goal": goal,
            "strategy": "sequential",
            "steps": [
                {
                    "name": "analyze_goal",
                    "service": "analysis",
                    "method": "analyze_requirements",
                    "parameters": {"goal": goal, "constraints": constraints}
                }
            ]
        }
    
    def _get_service_descriptions(self, service_names: List[str]) -> Dict[str, str]:
        """获取服务描述"""
        descriptions = {
            "placeholder": "占位符解析和语义分析服务",
            "template": "模板管理和验证服务",
            "analysis": "数据分析和质量评估服务",
            "reporting": "报告生成和内容管理服务",
            "context": "AI上下文管理服务",
            "prompt": "提示词工程服务",
            "agent_registry": "Agent注册和发现服务",
            "workflow": "工作流编排服务"
        }
        
        return {name: descriptions.get(name, "未知服务") for name in service_names}
    
    def _dict_to_workflow_definition(self, workflow_dict: Dict[str, Any]) -> WorkflowDefinition:
        """将字典转换为工作流定义"""
        steps = []
        for step_dict in workflow_dict.get("steps", []):
            step = StepDefinition(
                step_id=step_dict["step_id"],
                step_type=StepType(step_dict["step_type"]),
                name=step_dict["name"],
                description=step_dict.get("description", ""),
                handler=step_dict.get("handler"),
                parameters=step_dict.get("parameters", {}),
                depends_on=step_dict.get("depends_on", []),
                max_retries=step_dict.get("max_retries", 0),
                timeout_seconds=step_dict.get("timeout_seconds")
            )
            steps.append(step)
        
        return WorkflowDefinition(
            workflow_id=workflow_dict["workflow_id"],
            name=workflow_dict["name"],
            description=workflow_dict.get("description", ""),
            steps=steps,
            timeout_seconds=workflow_dict.get("timeout_seconds"),
            max_parallel_steps=workflow_dict.get("max_parallel_steps", 10)
        )
    
    def register_service(self, name: str, service: Any):
        """注册新服务"""
        self.services[name] = service
        logger.info(f"Service registered: {name}")
    
    def get_service_registry(self) -> Dict[str, Any]:
        """获取服务注册表"""
        return {
            name: {
                "type": type(service).__name__,
                "methods": [method for method in dir(service) if not method.startswith("_")]
            }
            for name, service in self.services.items()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "orchestrator": "healthy",
            "services": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for name, service in self.services.items():
            try:
                # 尝试调用健康检查方法
                if hasattr(service, "health_check"):
                    if asyncio.iscoroutinefunction(service.health_check):
                        status = await service.health_check()
                    else:
                        status = service.health_check()
                    health_status["services"][name] = status
                else:
                    health_status["services"][name] = "no_health_check"
            except Exception as e:
                health_status["services"][name] = {"status": "error", "error": str(e)}
        
        return health_status