"""
Workflow Engine

统一的工作流引擎，支持复杂业务流程的编排和执行
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """工作流状态"""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class StepType(Enum):
    """步骤类型"""
    ACTION = "action"           # 执行动作
    CONDITION = "condition"     # 条件判断
    PARALLEL = "parallel"      # 并行执行
    LOOP = "loop"              # 循环执行
    HUMAN = "human"            # 人工干预
    DELAY = "delay"            # 延迟等待


@dataclass
class WorkflowContext:
    """工作流上下文"""
    workflow_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def set_variable(self, key: str, value: Any):
        """设置变量"""
        self.variables[key] = value
        
    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(key, default)
    
    def merge_outputs(self, step_outputs: Dict[str, Any]):
        """合并步骤输出"""
        self.outputs.update(step_outputs)


@dataclass
class StepDefinition:
    """步骤定义"""
    step_id: str
    step_type: StepType
    name: str
    description: str = ""
    
    # 执行配置
    handler: Optional[str] = None  # 处理器名称
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 依赖关系
    depends_on: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    
    # 重试配置
    max_retries: int = 0
    retry_delay: float = 1.0
    
    # 超时配置
    timeout_seconds: Optional[float] = None
    
    # 并行/循环配置
    parallel_steps: List['StepDefinition'] = field(default_factory=list)
    loop_condition: Optional[str] = None
    loop_max_iterations: int = 100
    
    # 输出映射
    output_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class StepExecution:
    """步骤执行记录"""
    step_id: str
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    
    @property
    def duration(self) -> Optional[float]:
        """执行时长（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    workflow_id: str
    name: str
    description: str = ""
    version: str = "1.0"
    
    # 步骤定义
    steps: List[StepDefinition] = field(default_factory=list)
    
    # 全局配置
    timeout_seconds: Optional[float] = None
    max_parallel_steps: int = 10
    
    # 事件处理
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    on_timeout: Optional[str] = None
    
    def get_step(self, step_id: str) -> Optional[StepDefinition]:
        """获取步骤定义"""
        return next((step for step in self.steps if step.step_id == step_id), None)
    
    def validate(self) -> Dict[str, Any]:
        """验证工作流定义"""
        validation = {'valid': True, 'errors': [], 'warnings': []}
        
        # 检查步骤ID唯一性
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            validation['valid'] = False
            validation['errors'].append("Duplicate step IDs found")
        
        # 检查依赖关系
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    validation['valid'] = False
                    validation['errors'].append(f"Step {step.step_id} depends on non-existent step {dep}")
        
        # 检查循环依赖
        if self._has_circular_dependencies():
            validation['valid'] = False
            validation['errors'].append("Circular dependencies detected")
        
        return validation
    
    def _has_circular_dependencies(self) -> bool:
        """检查是否有循环依赖"""
        # 简化的循环依赖检测
        visited = set()
        rec_stack = set()
        
        def has_cycle(step_id: str) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = self.get_step(step_id)
            if step:
                for dep in step.depends_on:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        for step in self.steps:
            if step.step_id not in visited:
                if has_cycle(step.step_id):
                    return True
        
        return False


class WorkflowExecution:
    """工作流执行器"""
    
    def __init__(self, workflow_def: WorkflowDefinition, context: WorkflowContext):
        self.workflow_def = workflow_def
        self.context = context
        
        self.status = WorkflowStatus.CREATED
        self.step_executions: Dict[str, StepExecution] = {}
        
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        self.error_message: Optional[str] = None
        self.completed_steps: Set[str] = set()
        self.failed_steps: Set[str] = set()
        
        # 初始化步骤执行记录
        for step in workflow_def.steps:
            self.step_executions[step.step_id] = StepExecution(step_id=step.step_id)
    
    @property
    def duration(self) -> Optional[float]:
        """执行时长"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def get_step_execution(self, step_id: str) -> Optional[StepExecution]:
        """获取步骤执行记录"""
        return self.step_executions.get(step_id)
    
    def get_executable_steps(self) -> List[str]:
        """获取可执行的步骤"""
        executable = []
        
        for step in self.workflow_def.steps:
            if self._can_execute_step(step):
                executable.append(step.step_id)
        
        return executable
    
    def _can_execute_step(self, step: StepDefinition) -> bool:
        """检查步骤是否可以执行"""
        step_exec = self.step_executions[step.step_id]
        
        # 已完成或失败的步骤不能再执行
        if step_exec.status in [StepStatus.COMPLETED, StepStatus.FAILED]:
            return False
        
        # 正在运行的步骤不能重复执行
        if step_exec.status == StepStatus.RUNNING:
            return False
        
        # 检查依赖是否完成
        for dep_id in step.depends_on:
            dep_exec = self.step_executions.get(dep_id)
            if not dep_exec or dep_exec.status != StepStatus.COMPLETED:
                return False
        
        # 检查条件
        for condition in step.conditions:
            if not self._evaluate_condition(condition):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: str) -> bool:
        """评估条件表达式"""
        try:
            # 简化的条件评估
            # 在实际实现中，这里应该有更安全的表达式评估
            local_vars = {
                'context': self.context.variables,
                'inputs': self.context.inputs,
                'outputs': self.context.outputs
            }
            return eval(condition, {"__builtins__": {}}, local_vars)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition}, error: {e}")
            return False
    
    def mark_step_completed(self, step_id: str, outputs: Dict[str, Any] = None):
        """标记步骤完成"""
        if step_id in self.step_executions:
            step_exec = self.step_executions[step_id]
            step_exec.status = StepStatus.COMPLETED
            step_exec.end_time = datetime.now()
            step_exec.outputs = outputs or {}
            
            self.completed_steps.add(step_id)
            
            # 合并输出到上下文
            step_def = self.workflow_def.get_step(step_id)
            if step_def and step_def.output_mapping:
                mapped_outputs = {}
                for output_key, context_key in step_def.output_mapping.items():
                    if output_key in step_exec.outputs:
                        mapped_outputs[context_key] = step_exec.outputs[output_key]
                self.context.merge_outputs(mapped_outputs)
            else:
                self.context.merge_outputs(step_exec.outputs)
    
    def mark_step_failed(self, step_id: str, error_message: str):
        """标记步骤失败"""
        if step_id in self.step_executions:
            step_exec = self.step_executions[step_id]
            step_exec.status = StepStatus.FAILED
            step_exec.end_time = datetime.now()
            step_exec.error_message = error_message
            
            self.failed_steps.add(step_id)
    
    def is_completed(self) -> bool:
        """检查工作流是否完成"""
        return len(self.completed_steps) == len(self.workflow_def.steps)
    
    def has_failed(self) -> bool:
        """检查工作流是否失败"""
        return len(self.failed_steps) > 0


class StepHandler:
    """步骤处理器基类"""
    
    async def execute(self, step_def: StepDefinition, context: WorkflowContext, 
                     inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行步骤 - 基于React Agent的默认实现"""
        try:
            from app.services.infrastructure.ai.service_orchestrator import get_service_orchestrator
            
            user_id = context.get_context_value("user_id") or "system"
            orchestrator = get_service_orchestrator()
            
            # 构建执行提示
            prompt = f"""
            执行工作流步骤:
            - 步骤名称: {step_def.name}
            - 步骤类型: {step_def.step_type}
            - 输入数据: {inputs}
            - 上下文: {context.get_all_context()}
            
            请执行此步骤并返回结果。
            """
            
            result = await agent.chat(prompt)
            
            return {
                "success": True,
                "result": result,
                "step_name": step_def.name,
                "handler": "ServiceOrchestratorHandler"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step_name": step_def.name,
                "handler": "ServiceOrchestratorHandler"
            }


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.step_handlers: Dict[str, StepHandler] = {}
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.event_listeners: Dict[str, List[Callable]] = {}
    
    def register_step_handler(self, handler_name: str, handler: StepHandler):
        """注册步骤处理器"""
        self.step_handlers[handler_name] = handler
        logger.info(f"Registered step handler: {handler_name}")
    
    def register_event_listener(self, event_name: str, listener: Callable):
        """注册事件监听器"""
        if event_name not in self.event_listeners:
            self.event_listeners[event_name] = []
        self.event_listeners[event_name].append(listener)
    
    async def execute_workflow(self, workflow_def: WorkflowDefinition, 
                             inputs: Dict[str, Any] = None) -> WorkflowExecution:
        """执行工作流"""
        # 验证工作流定义
        validation = workflow_def.validate()
        if not validation['valid']:
            raise ValueError(f"Invalid workflow definition: {validation['errors']}")
        
        # 创建执行上下文
        context = WorkflowContext(
            workflow_id=workflow_def.workflow_id,
            inputs=inputs or {}
        )
        
        # 创建执行器
        execution = WorkflowExecution(workflow_def, context)
        execution.status = WorkflowStatus.RUNNING
        execution.start_time = datetime.now()
        
        self.active_workflows[workflow_def.workflow_id] = execution
        
        try:
            await self._execute_workflow_steps(execution)
            
            # 检查最终状态
            if execution.is_completed():
                execution.status = WorkflowStatus.COMPLETED
                await self._emit_event('workflow_completed', execution)
            elif execution.has_failed():
                execution.status = WorkflowStatus.FAILED
                await self._emit_event('workflow_failed', execution)
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Workflow execution failed: {e}")
            await self._emit_event('workflow_error', execution)
        
        finally:
            execution.end_time = datetime.now()
            
            # 清理活跃工作流
            if workflow_def.workflow_id in self.active_workflows:
                del self.active_workflows[workflow_def.workflow_id]
        
        return execution
    
    async def _execute_workflow_steps(self, execution: WorkflowExecution):
        """执行工作流步骤"""
        max_iterations = 1000  # 防止无限循环
        iteration = 0
        
        while not execution.is_completed() and not execution.has_failed() and iteration < max_iterations:
            executable_steps = execution.get_executable_steps()
            
            if not executable_steps:
                # 没有可执行的步骤，检查是否有未完成的步骤
                pending_steps = [
                    step_id for step_id, step_exec in execution.step_executions.items()
                    if step_exec.status == StepStatus.PENDING
                ]
                
                if pending_steps:
                    # 有待执行的步骤但当前不可执行，可能是条件不满足或依赖未完成
                    logger.warning(f"Workflow deadlock detected. Pending steps: {pending_steps}")
                    break
                else:
                    # 所有步骤都已处理
                    break
            
            # 并行执行可执行的步骤
            tasks = []
            for step_id in executable_steps[:execution.workflow_def.max_parallel_steps]:
                task = asyncio.create_task(self._execute_step(execution, step_id))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            iteration += 1
        
        if iteration >= max_iterations:
            raise RuntimeError("Workflow execution exceeded maximum iterations")
    
    async def _execute_step(self, execution: WorkflowExecution, step_id: str):
        """执行单个步骤"""
        step_def = execution.workflow_def.get_step(step_id)
        step_exec = execution.get_step_execution(step_id)
        
        if not step_def or not step_exec:
            return
        
        step_exec.status = StepStatus.RUNNING
        step_exec.start_time = datetime.now()
        
        try:
            # 准备输入参数
            inputs = step_def.parameters.copy()
            inputs.update(execution.context.variables)
            step_exec.inputs = inputs
            
            # 执行步骤
            outputs = await self._execute_step_with_retry(step_def, execution.context, inputs)
            
            # 标记完成
            execution.mark_step_completed(step_id, outputs)
            
            logger.info(f"Step {step_id} completed successfully")
            
        except Exception as e:
            execution.mark_step_failed(step_id, str(e))
            logger.error(f"Step {step_id} failed: {e}")
    
    async def _execute_step_with_retry(self, step_def: StepDefinition, 
                                     context: WorkflowContext, 
                                     inputs: Dict[str, Any]) -> Dict[str, Any]:
        """带重试的步骤执行"""
        last_exception = None
        
        for attempt in range(step_def.max_retries + 1):
            try:
                # 根据步骤类型执行
                if step_def.step_type == StepType.ACTION:
                    return await self._execute_action_step(step_def, context, inputs)
                elif step_def.step_type == StepType.CONDITION:
                    return await self._execute_condition_step(step_def, context, inputs)
                elif step_def.step_type == StepType.DELAY:
                    return await self._execute_delay_step(step_def, context, inputs)
                elif step_def.step_type == StepType.PARALLEL:
                    return await self._execute_parallel_step(step_def, context, inputs)
                elif step_def.step_type == StepType.LOOP:
                    return await self._execute_loop_step(step_def, context, inputs)
                else:
                    # 使用React Agent处理未知步骤类型
                    return await self._execute_with_react_agent(step_def, context, inputs)
                
            except Exception as e:
                last_exception = e
                
                if attempt < step_def.max_retries:
                    logger.warning(f"Step {step_def.step_id} failed (attempt {attempt + 1}), retrying: {e}")
                    await asyncio.sleep(step_def.retry_delay)
                else:
                    logger.error(f"Step {step_def.step_id} failed after {step_def.max_retries + 1} attempts: {e}")
        
        raise last_exception or RuntimeError("Step execution failed")
    
    async def _execute_action_step(self, step_def: StepDefinition, 
                                 context: WorkflowContext, 
                                 inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行动作步骤"""
        if not step_def.handler:
            raise ValueError(f"Action step {step_def.step_id} has no handler specified")
        
        handler = self.step_handlers.get(step_def.handler)
        if not handler:
            raise ValueError(f"Handler {step_def.handler} not found")
        
        return await handler.execute(step_def, context, inputs)
    
    async def _execute_condition_step(self, step_def: StepDefinition,
                                    context: WorkflowContext,
                                    inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行条件步骤"""
        condition = step_def.parameters.get('condition')
        if not condition:
            raise ValueError(f"Condition step {step_def.step_id} has no condition specified")
        
        result = self._evaluate_condition_in_context(condition, context)
        
        return {'condition_result': result}
    
    async def _execute_delay_step(self, step_def: StepDefinition,
                                context: WorkflowContext,
                                inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行延迟步骤"""
        delay_seconds = step_def.parameters.get('delay_seconds', 1.0)
        await asyncio.sleep(delay_seconds)
        
        return {'delayed_seconds': delay_seconds}
    
    async def _execute_parallel_step(self, step_def: StepDefinition,
                                   context: WorkflowContext,
                                   inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行并行步骤"""
        parallel_tasks = step_def.parameters.get('parallel_tasks', [])
        
        # 并行执行任务
        tasks = []
        for task in parallel_tasks:
            task_coro = self._execute_task_from_config(task, context, inputs)
            tasks.append(task_coro)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append({"task_index": i, "error": str(result)})
            else:
                successful_results.append({"task_index": i, "result": result})
        
        return {
            "parallel_results": successful_results,
            "errors": errors,
            "total_tasks": len(parallel_tasks),
            "successful_tasks": len(successful_results)
        }
    
    async def _execute_loop_step(self, step_def: StepDefinition,
                               context: WorkflowContext,
                               inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行循环步骤"""
        loop_config = step_def.parameters.get('loop_config', {})
        items = loop_config.get('items', [])
        max_iterations = loop_config.get('max_iterations', len(items))
        
        results = []
        
        for i, item in enumerate(items[:max_iterations]):
            try:
                # 设置循环变量
                loop_context = context.copy()
                loop_context.set_variable('loop_item', item)
                loop_context.set_variable('loop_index', i)
                
                # 执行循环体
                loop_task = loop_config.get('task')
                result = await self._execute_task_from_config(loop_task, loop_context, inputs)
                
                results.append({
                    "iteration": i,
                    "item": item,
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "iteration": i,
                    "item": item,
                    "error": str(e)
                })
        
        return {
            "loop_results": results,
            "total_iterations": len(results),
            "successful_iterations": len([r for r in results if "error" not in r])
        }
    
    async def _execute_with_react_agent(self, step_def: StepDefinition,
                                      context: WorkflowContext,
                                      inputs: Dict[str, Any]) -> Dict[str, Any]:
        """使用React Agent执行未知步骤类型"""
        try:
            from app.services.infrastructure.ai.service_orchestrator import get_service_orchestrator
            
            user_id = context.get_context_value("user_id") or "system"
            orchestrator = get_service_orchestrator()
            
            workflow_content = f"""
            自定义工作流步骤执行
            
            步骤ID: {step_def.step_id}
            步骤名称: {step_def.name}
            步骤类型: {step_def.step_type}
            参数: {step_def.parameters}
            输入: {inputs}
            
            请根据步骤配置执行相应的操作并返回结果。
            """
            
            result = await orchestrator.analyze_template_simple(
                user_id=str(user_id),
                template_id="custom_workflow_step",
                template_content=workflow_content,
                data_source_info={
                    "type": "custom_workflow_step",
                    "step_definition": step_def.model_dump(),
                    "workflow_context": context.get_all_context()
                }
            )
            
            return {
                "success": True,
                "result": str(result),
                "execution_method": "service_orchestrator",
                "step_type": step_def.step_type
            }
            
        except Exception as e:
            logger.error(f"ServiceOrchestrator step execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_method": "service_orchestrator",
                "step_type": step_def.step_type
            }
    
    async def _execute_task_from_config(self, task_config: Dict[str, Any],
                                      context: WorkflowContext,
                                      inputs: Dict[str, Any]) -> Any:
        """从配置执行任务"""
        task_type = task_config.get('type', 'unknown')
        
        if task_type == 'react_agent' or task_type == 'service_orchestrator':
            # 使用新的Claude Code架构
            from app.services.infrastructure.ai.service_orchestrator import get_service_orchestrator
            user_id = context.get_context_value("user_id") or "system"
            orchestrator = get_service_orchestrator()
            
            prompt = task_config.get('prompt', '')
            result = await orchestrator.analyze_template_simple(
                user_id=str(user_id),
                template_id="workflow_task",
                template_content=prompt,
                data_source_info={
                    "type": "workflow_task",
                    "task_config": task_config,
                    "inputs": inputs
                }
            )
            return str(result)
        
        else:
            # 其他任务类型的默认处理
            return {"task_type": task_type, "config": task_config, "inputs": inputs}
    
    def _evaluate_condition_in_context(self, condition: str, context: WorkflowContext) -> bool:
        """在上下文中评估条件"""
        try:
            local_vars = {
                'variables': context.variables,
                'inputs': context.inputs,
                'outputs': context.outputs
            }
            return eval(condition, {"__builtins__": {}}, local_vars)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {condition}, error: {e}")
            return False
    
    async def _emit_event(self, event_name: str, data: Any):
        """发送事件"""
        listeners = self.event_listeners.get(event_name, [])
        for listener in listeners:
            try:
                await listener(data)
            except Exception as e:
                logger.error(f"Event listener failed for {event_name}: {e}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        execution = self.active_workflows.get(workflow_id)
        if not execution:
            return None
        
        return {
            'workflow_id': workflow_id,
            'status': execution.status.value,
            'start_time': execution.start_time.isoformat() if execution.start_time else None,
            'duration': execution.duration,
            'completed_steps': len(execution.completed_steps),
            'failed_steps': len(execution.failed_steps),
            'total_steps': len(execution.workflow_def.steps),
            'error_message': execution.error_message
        }
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流"""
        execution = self.active_workflows.get(workflow_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.CANCELLED
            execution.end_time = datetime.now()
            return True
        return False