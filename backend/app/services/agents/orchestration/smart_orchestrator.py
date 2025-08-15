"""
智能Agent编排器

自动分析用户需求，智能选择和编排多个Agent协作完成复杂任务。

Features:
- 意图识别和任务分解
- Agent选择和调度
- 工作流自动构建
- 并行和串行执行优化
- 错误恢复和重试机制
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta

from ..core_types import BaseAgent, AgentConfig, AgentResult, AgentType, AgentError
from ..enhanced.enhanced_data_query_agent import EnhancedDataQueryAgent, SemanticQueryRequest
from ..enhanced.enhanced_content_generation_agent import EnhancedContentGenerationAgent, ContextualContentRequest
from ..enhanced.enhanced_analysis_agent import EnhancedAnalysisAgent, MLAnalysisRequest
from ..enhanced.enhanced_visualization_agent import EnhancedVisualizationAgent, SmartChartRequest
from ..security import sandbox_manager, SandboxLevel
from ..tools import tool_registry


class TaskType(Enum):
    """任务类型"""
    QUERY = "query"                      # 数据查询
    ANALYSIS = "analysis"                # 数据分析
    VISUALIZATION = "visualization"      # 数据可视化
    CONTENT_GENERATION = "content"       # 内容生成
    REPORT_GENERATION = "report"         # 报告生成
    DATA_PIPELINE = "pipeline"           # 数据管道
    DASHBOARD = "dashboard"              # 仪表板创建


class ExecutionMode(Enum):
    """执行模式"""
    SEQUENTIAL = "sequential"            # 串行执行
    PARALLEL = "parallel"               # 并行执行
    PIPELINE = "pipeline"               # 流水线执行
    CONDITIONAL = "conditional"          # 条件执行


@dataclass
class TaskRequest:
    """任务请求"""
    task_id: str
    task_type: TaskType
    description: str
    input_data: Any
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID
    priority: int = 1                    # 优先级 1-10
    timeout: int = 300                   # 超时时间（秒）
    retry_count: int = 3                 # 重试次数
    agent_hints: List[str] = field(default_factory=list)   # Agent提示


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str
    agent_type: AgentType
    agent_config: Dict[str, Any]
    input_mapping: Dict[str, str]        # 输入映射
    output_mapping: Dict[str, str]       # 输出映射
    condition: Optional[str] = None      # 执行条件
    parallel_group: Optional[str] = None # 并行组ID


@dataclass
class Workflow:
    """工作流定义"""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    execution_mode: ExecutionMode
    error_handling: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """执行结果"""
    task_id: str
    success: bool
    result: Any = None
    error_message: str = ""
    execution_time: float = 0.0
    agent_used: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentAnalyzer:
    """意图分析器"""
    
    def __init__(self):
        # 意图识别模式
        self.intent_patterns = {
            TaskType.QUERY: [
                r'查询|获取|检索|查找|搜索',
                r'数据|记录|信息',
                r'多少|统计|计算',
                r'列出|显示|展示'
            ],
            TaskType.ANALYSIS: [
                r'分析|统计|计算|预测',
                r'趋势|模式|规律|相关性',
                r'聚类|分类|异常',
                r'平均|总和|最大|最小'
            ],
            TaskType.VISUALIZATION: [
                r'图表|可视化|绘制|画图',
                r'柱状图|折线图|饼图|散点图',
                r'展示|呈现|显示',
                r'仪表板|Dashboard'
            ],
            TaskType.CONTENT_GENERATION: [
                r'生成|创建|撰写|编写',
                r'报告|总结|说明|描述',
                r'文档|文章|内容',
                r'摘要|概述|解释'
            ],
            TaskType.REPORT_GENERATION: [
                r'报告|报表|汇报',
                r'总结|概述|摘要',
                r'完整|综合|全面',
                r'生成.*报告|创建.*报表'
            ]
        }
        
        # 复合任务识别
        self.compound_patterns = {
            TaskType.DATA_PIPELINE: [
                r'(查询|获取).*?(分析|统计)',
                r'(数据处理|ETL|数据流)',
                r'从.*到.*的完整流程'
            ],
            TaskType.DASHBOARD: [
                r'仪表板|Dashboard|面板',
                r'多个图表|综合展示',
                r'监控|实时'
            ]
        }
    
    async def analyze_intent(self, description: str) -> List[TaskRequest]:
        """分析用户意图并分解任务"""
        import re
        
        description_lower = description.lower()
        detected_intents = []
        
        # 检测复合任务
        for task_type, patterns in self.compound_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description_lower):
                    return await self._decompose_compound_task(description, task_type)
        
        # 检测单一任务
        for task_type, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, description_lower))
                score += matches
            
            if score > 0:
                detected_intents.append((task_type, score))
        
        # 按得分排序，选择最高分的意图
        if detected_intents:
            detected_intents.sort(key=lambda x: x[1], reverse=True)
            primary_intent = detected_intents[0][0]
            
            return [TaskRequest(
                task_id=f"task_{int(time.time())}",
                task_type=primary_intent,
                description=description,
                input_data={"description": description}
            )]
        
        # 默认返回查询任务
        return [TaskRequest(
            task_id=f"task_{int(time.time())}",
            task_type=TaskType.QUERY,
            description=description,
            input_data={"description": description}
        )]
    
    async def _decompose_compound_task(self, description: str, task_type: TaskType) -> List[TaskRequest]:
        """分解复合任务"""
        base_id = int(time.time())
        tasks = []
        
        if task_type == TaskType.DATA_PIPELINE:
            # 数据管道：查询 -> 分析 -> 可视化 -> 报告
            tasks = [
                TaskRequest(
                    task_id=f"query_{base_id}",
                    task_type=TaskType.QUERY,
                    description=f"从描述中提取数据查询需求：{description}",
                    input_data={"description": description},
                    priority=3
                ),
                TaskRequest(
                    task_id=f"analysis_{base_id}",
                    task_type=TaskType.ANALYSIS,
                    description=f"分析查询得到的数据",
                    input_data={},
                    dependencies=[f"query_{base_id}"],
                    priority=2
                ),
                TaskRequest(
                    task_id=f"visualization_{base_id}",
                    task_type=TaskType.VISUALIZATION,
                    description=f"可视化分析结果",
                    input_data={},
                    dependencies=[f"analysis_{base_id}"],
                    priority=2
                ),
                TaskRequest(
                    task_id=f"report_{base_id}",
                    task_type=TaskType.CONTENT_GENERATION,
                    description=f"生成综合报告",
                    input_data={},
                    dependencies=[f"analysis_{base_id}", f"visualization_{base_id}"],
                    priority=1
                )
            ]
        
        elif task_type == TaskType.DASHBOARD:
            # 仪表板：查询 -> 多个分析和可视化（并行）-> 汇总
            tasks = [
                TaskRequest(
                    task_id=f"query_{base_id}",
                    task_type=TaskType.QUERY,
                    description=f"获取仪表板所需数据：{description}",
                    input_data={"description": description},
                    priority=3
                ),
                TaskRequest(
                    task_id=f"analysis1_{base_id}",
                    task_type=TaskType.ANALYSIS,
                    description="执行第一类分析",
                    input_data={},
                    dependencies=[f"query_{base_id}"],
                    priority=2
                ),
                TaskRequest(
                    task_id=f"analysis2_{base_id}",
                    task_type=TaskType.ANALYSIS,
                    description="执行第二类分析",
                    input_data={},
                    dependencies=[f"query_{base_id}"],
                    priority=2
                ),
                TaskRequest(
                    task_id=f"dashboard_{base_id}",
                    task_type=TaskType.VISUALIZATION,
                    description="创建综合仪表板",
                    input_data={"chart_type": "dashboard"},
                    dependencies=[f"analysis1_{base_id}", f"analysis2_{base_id}"],
                    priority=1
                )
            ]
        
        return tasks


class AgentSelector:
    """Agent选择器"""
    
    def __init__(self):
        self.agent_registry = {
            AgentType.DATA_QUERY: EnhancedDataQueryAgent,
            AgentType.ANALYSIS: EnhancedAnalysisAgent,
            AgentType.VISUALIZATION: EnhancedVisualizationAgent,
            AgentType.CONTENT_GENERATION: EnhancedContentGenerationAgent
        }
        
        self.agent_capabilities = {
            AgentType.DATA_QUERY: {
                "semantic_query", "multi_source", "sql_generation", "metadata_management"
            },
            AgentType.ANALYSIS: {
                "ml_prediction", "anomaly_detection", "clustering", "statistical_analysis"
            },
            AgentType.VISUALIZATION: {
                "smart_charts", "color_harmony", "layout_optimization", "storytelling"
            },
            AgentType.CONTENT_GENERATION: {
                "context_management", "style_adaptation", "quality_control", "personalization"
            }
        }
    
    async def select_agent(self, task: TaskRequest) -> AgentType:
        """选择最适合的Agent"""
        task_type_mapping = {
            TaskType.QUERY: AgentType.DATA_QUERY,
            TaskType.ANALYSIS: AgentType.ANALYSIS,
            TaskType.VISUALIZATION: AgentType.VISUALIZATION,
            TaskType.CONTENT_GENERATION: AgentType.CONTENT_GENERATION,
            TaskType.REPORT_GENERATION: AgentType.CONTENT_GENERATION,
            TaskType.DATA_PIPELINE: AgentType.DATA_QUERY,  # 由编排器处理
            TaskType.DASHBOARD: AgentType.VISUALIZATION
        }
        
        return task_type_mapping.get(task.task_type, AgentType.DATA_QUERY)
    
    async def create_agent(self, agent_type: AgentType, config: Dict[str, Any] = None) -> BaseAgent:
        """创建Agent实例"""
        agent_class = self.agent_registry[agent_type]
        
        # 创建Agent配置
        if config is None:
            config = {}
        
        agent_config = AgentConfig(
            agent_id=f"{agent_type.value}_{int(time.time())}",
            agent_type=agent_type,
            name=f"{agent_type.value.title()} Agent",
            description=f"Enhanced {agent_type.value} agent",
            **config
        )
        
        return agent_class(agent_config)


class WorkflowBuilder:
    """工作流构建器"""
    
    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.agent_selector = AgentSelector()
    
    async def build_workflow(self, user_request: str) -> Workflow:
        """构建工作流"""
        # 分析意图并分解任务
        tasks = await self.intent_analyzer.analyze_intent(user_request)
        
        # 创建工作流步骤
        steps = []
        parallel_groups = {}
        
        for task in tasks:
            # 选择Agent
            agent_type = await self.agent_selector.select_agent(task)
            
            # 创建步骤
            step = WorkflowStep(
                step_id=task.task_id,
                agent_type=agent_type,
                agent_config={
                    "timeout_seconds": task.timeout,
                    "retry_count": task.retry_count
                },
                input_mapping=await self._create_input_mapping(task),
                output_mapping=await self._create_output_mapping(task)
            )
            
            # 处理并行任务
            if len(task.dependencies) == 0:
                # 无依赖的任务可以并行执行
                parallel_group = "initial"
            elif self._can_parallelize(task, tasks):
                parallel_group = f"parallel_{task.dependencies[0]}"
            else:
                parallel_group = None
            
            step.parallel_group = parallel_group
            steps.append(step)
        
        # 确定执行模式
        execution_mode = await self._determine_execution_mode(tasks)
        
        workflow = Workflow(
            workflow_id=f"workflow_{int(time.time())}",
            name="Auto-generated Workflow",
            description=f"自动生成的工作流：{user_request}",
            steps=steps,
            execution_mode=execution_mode,
            error_handling={
                "retry_strategy": "exponential_backoff",
                "max_retries": 3,
                "fallback_enabled": True
            }
        )
        
        return workflow
    
    async def _create_input_mapping(self, task: TaskRequest) -> Dict[str, str]:
        """创建输入映射"""
        if task.task_type == TaskType.QUERY:
            return {
                "natural_language_query": "description",
                "data_source_id": "data_source_id"
            }
        elif task.task_type == TaskType.ANALYSIS:
            return {
                "data": "previous_result.data",
                "analysis_type": "analysis_type"
            }
        elif task.task_type == TaskType.VISUALIZATION:
            return {
                "data": "previous_result.data",
                "purpose": "purpose"
            }
        elif task.task_type == TaskType.CONTENT_GENERATION:
            return {
                "data": "aggregated_results",
                "content_type": "content_type"
            }
        
        return {}
    
    async def _create_output_mapping(self, task: TaskRequest) -> Dict[str, str]:
        """创建输出映射"""
        return {
            "result": "data",
            "metadata": "metadata",
            "success": "success"
        }
    
    def _can_parallelize(self, task: TaskRequest, all_tasks: List[TaskRequest]) -> bool:
        """判断任务是否可以并行化"""
        # 如果多个任务有相同的依赖，它们可以并行执行
        same_dependency_tasks = [
            t for t in all_tasks 
            if t.task_id != task.task_id and t.dependencies == task.dependencies
        ]
        return len(same_dependency_tasks) > 0
    
    async def _determine_execution_mode(self, tasks: List[TaskRequest]) -> ExecutionMode:
        """确定执行模式"""
        if len(tasks) == 1:
            return ExecutionMode.SEQUENTIAL
        
        # 检查是否有并行任务
        dependency_groups = {}
        for task in tasks:
            dep_key = ",".join(sorted(task.dependencies))
            if dep_key not in dependency_groups:
                dependency_groups[dep_key] = []
            dependency_groups[dep_key].append(task)
        
        has_parallel = any(len(group) > 1 for group in dependency_groups.values())
        has_dependencies = any(task.dependencies for task in tasks)
        
        if has_parallel and has_dependencies:
            return ExecutionMode.PIPELINE
        elif has_parallel:
            return ExecutionMode.PARALLEL
        else:
            return ExecutionMode.SEQUENTIAL


class ExecutionEngine:
    """执行引擎"""
    
    def __init__(self):
        self.agent_selector = AgentSelector()
        self.running_tasks = {}
        self.completed_tasks = {}
        self.task_results = {}
    
    async def execute_workflow(self, workflow: Workflow, context: Dict[str, Any] = None) -> Dict[str, ExecutionResult]:
        """执行工作流"""
        context = context or {}
        results = {}
        
        try:
            if workflow.execution_mode == ExecutionMode.SEQUENTIAL:
                results = await self._execute_sequential(workflow, context)
            elif workflow.execution_mode == ExecutionMode.PARALLEL:
                results = await self._execute_parallel(workflow, context)
            elif workflow.execution_mode == ExecutionMode.PIPELINE:
                results = await self._execute_pipeline(workflow, context)
            else:
                results = await self._execute_conditional(workflow, context)
            
        except Exception as e:
            # 错误处理
            error_result = ExecutionResult(
                task_id="workflow_error",
                success=False,
                error_message=str(e),
                execution_time=0.0,
                agent_used="orchestrator"
            )
            results["error"] = error_result
        
        return results
    
    async def _execute_sequential(self, workflow: Workflow, context: Dict[str, Any]) -> Dict[str, ExecutionResult]:
        """串行执行工作流"""
        results = {}
        current_context = context.copy()
        
        for step in workflow.steps:
            result = await self._execute_step(step, current_context, results)
            results[step.step_id] = result
            
            if result.success:
                # 更新上下文
                current_context.update(result.metadata)
                current_context["previous_result"] = result.result
            else:
                # 处理错误
                if not await self._handle_step_error(step, result, workflow):
                    break
        
        return results
    
    async def _execute_parallel(self, workflow: Workflow, context: Dict[str, Any]) -> Dict[str, ExecutionResult]:
        """并行执行工作流"""
        # 按并行组分组
        parallel_groups = {}
        for step in workflow.steps:
            group = step.parallel_group or "default"
            if group not in parallel_groups:
                parallel_groups[group] = []
            parallel_groups[group].append(step)
        
        results = {}
        
        for group_name, steps in parallel_groups.items():
            # 并行执行组内步骤
            step_tasks = [
                self._execute_step(step, context, results)
                for step in steps
            ]
            
            group_results = await asyncio.gather(*step_tasks, return_exceptions=True)
            
            # 处理结果
            for step, result in zip(steps, group_results):
                if isinstance(result, Exception):
                    result = ExecutionResult(
                        task_id=step.step_id,
                        success=False,
                        error_message=str(result),
                        agent_used=step.agent_type.value
                    )
                results[step.step_id] = result
        
        return results
    
    async def _execute_pipeline(self, workflow: Workflow, context: Dict[str, Any]) -> Dict[str, ExecutionResult]:
        """流水线执行工作流"""
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(workflow.steps)
        
        # 拓扑排序
        execution_order = self._topological_sort(dependency_graph)
        
        results = {}
        current_context = context.copy()
        
        for step_id in execution_order:
            step = next(s for s in workflow.steps if s.step_id == step_id)
            
            # 检查依赖是否完成
            dependencies_met = await self._check_dependencies(step, results)
            if not dependencies_met:
                results[step_id] = ExecutionResult(
                    task_id=step_id,
                    success=False,
                    error_message="Dependencies not met",
                    agent_used=step.agent_type.value
                )
                continue
            
            # 聚合依赖结果
            aggregated_input = await self._aggregate_dependency_results(step, results)
            current_context.update(aggregated_input)
            
            # 执行步骤
            result = await self._execute_step(step, current_context, results)
            results[step_id] = result
            
            if result.success:
                current_context["previous_result"] = result.result
        
        return results
    
    async def _execute_conditional(self, workflow: Workflow, context: Dict[str, Any]) -> Dict[str, ExecutionResult]:
        """条件执行工作流"""
        results = {}
        current_context = context.copy()
        
        for step in workflow.steps:
            # 检查执行条件
            if step.condition and not await self._evaluate_condition(step.condition, current_context):
                continue
            
            result = await self._execute_step(step, current_context, results)
            results[step.step_id] = result
            
            if result.success:
                current_context.update(result.metadata)
                current_context["previous_result"] = result.result
        
        return results
    
    async def _execute_step(self, step: WorkflowStep, context: Dict[str, Any], previous_results: Dict[str, ExecutionResult]) -> ExecutionResult:
        """执行单个步骤"""
        start_time = time.time()
        
        try:
            # 创建Agent
            agent = await self.agent_selector.create_agent(step.agent_type, step.agent_config)
            
            # 准备输入数据
            input_data = await self._prepare_step_input(step, context, previous_results)
            
            # 执行Agent
            if step.agent_type == AgentType.DATA_QUERY:
                result = await self._execute_query_agent(agent, input_data, context)
            elif step.agent_type == AgentType.ANALYSIS:
                result = await self._execute_analysis_agent(agent, input_data, context)
            elif step.agent_type == AgentType.VISUALIZATION:
                result = await self._execute_visualization_agent(agent, input_data, context)
            elif step.agent_type == AgentType.CONTENT_GENERATION:
                result = await self._execute_content_agent(agent, input_data, context)
            else:
                result = await agent.execute(input_data, context)
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                task_id=step.step_id,
                success=result.success,
                result=result.data,
                error_message=result.error_message or "",
                execution_time=execution_time,
                agent_used=agent.agent_id,
                metadata=result.metadata or {}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                task_id=step.step_id,
                success=False,
                error_message=str(e),
                execution_time=execution_time,
                agent_used=step.agent_type.value
            )
    
    async def _execute_query_agent(self, agent: EnhancedDataQueryAgent, input_data: Dict, context: Dict) -> AgentResult:
        """执行查询Agent"""
        if "natural_language_query" in input_data:
            # 使用语义查询
            semantic_request = SemanticQueryRequest(
                natural_language=input_data["natural_language_query"],
                data_source_ids=[input_data.get("data_source_id", 1)],
                context=context
            )
            return await agent.execute_semantic_query(semantic_request)
        else:
            # 使用传统查询
            return await agent.execute(input_data, context)
    
    async def _execute_analysis_agent(self, agent: EnhancedAnalysisAgent, input_data: Dict, context: Dict) -> AgentResult:
        """执行分析Agent"""
        if "ml_analysis" in context or "analysis_type" in input_data:
            # 使用机器学习分析
            ml_request = MLAnalysisRequest(
                data=input_data.get("data", []),
                analysis_type=input_data.get("analysis_type", "comprehensive")
            )
            return await agent.execute_ml_analysis(ml_request)
        else:
            # 使用传统分析
            return await agent.execute(input_data, context)
    
    async def _execute_visualization_agent(self, agent: EnhancedVisualizationAgent, input_data: Dict, context: Dict) -> AgentResult:
        """执行可视化Agent"""
        smart_request = SmartChartRequest(
            data=input_data.get("data", []),
            purpose=input_data.get("purpose", "explore"),
            audience=input_data.get("audience", "general"),
            context=context,
            interactive=input_data.get("interactive", False)
        )
        
        if input_data.get("chart_type") == "dashboard":
            # 创建仪表板
            return await agent.generate_dashboard([smart_request])
        else:
            return await agent.create_smart_chart(smart_request)
    
    async def _execute_content_agent(self, agent: EnhancedContentGenerationAgent, input_data: Dict, context: Dict) -> AgentResult:
        """执行内容生成Agent"""
        contextual_request = ContextualContentRequest(
            data=input_data.get("data", {}),
            content_type=input_data.get("content_type", "summary"),
            conversation_id=context.get("conversation_id"),
            context_history=context.get("history", []),
            style_requirements=input_data.get("style", {}),
            format=input_data.get("format", "text")
        )
        
        return await agent.execute_contextual(contextual_request)
    
    async def _prepare_step_input(self, step: WorkflowStep, context: Dict, previous_results: Dict) -> Dict:
        """准备步骤输入数据"""
        input_data = {}
        
        # 应用输入映射
        for target_key, source_key in step.input_mapping.items():
            if source_key in context:
                input_data[target_key] = context[source_key]
            elif "." in source_key:
                # 处理嵌套键
                value = self._get_nested_value(context, source_key)
                if value is not None:
                    input_data[target_key] = value
        
        return input_data
    
    def _get_nested_value(self, data: Dict, key_path: str) -> Any:
        """获取嵌套值"""
        keys = key_path.split(".")
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> Dict[str, List[str]]:
        """构建依赖图"""
        graph = {}
        for step in steps:
            graph[step.step_id] = []  # 这里需要从TaskRequest获取依赖信息
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """拓扑排序"""
        # 简化实现
        return list(graph.keys())
    
    async def _check_dependencies(self, step: WorkflowStep, results: Dict) -> bool:
        """检查依赖是否满足"""
        # 简化实现 - 实际需要检查具体依赖
        return True
    
    async def _aggregate_dependency_results(self, step: WorkflowStep, results: Dict) -> Dict:
        """聚合依赖结果"""
        aggregated = {}
        # 这里需要实现具体的结果聚合逻辑
        return aggregated
    
    async def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """评估执行条件"""
        # 使用沙盒安全执行条件表达式
        try:
            result = sandbox_manager.execute_expression(condition, context)
            return result.success and bool(result.result)
        except:
            return True  # 默认执行
    
    async def _handle_step_error(self, step: WorkflowStep, result: ExecutionResult, workflow: Workflow) -> bool:
        """处理步骤错误"""
        error_handling = workflow.error_handling
        
        if error_handling.get("retry_strategy") == "exponential_backoff":
            # 实现重试逻辑
            pass
        
        return error_handling.get("fallback_enabled", False)


class SmartOrchestrator(BaseAgent):
    """智能Agent编排器"""
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="smart_orchestrator",
                agent_type=AgentType.DATA_QUERY,  # 临时使用，实际应该是ORCHESTRATOR
                name="Smart Agent Orchestrator",
                description="智能Agent编排器，自动分析任务并协调多个Agent协作",
                timeout_seconds=600,  # 10分钟超时
                enable_caching=True,
                cache_ttl_seconds=1800
            )
        
        super().__init__(config)
        
        # 初始化组件
        self.workflow_builder = WorkflowBuilder()
        self.execution_engine = ExecutionEngine()
        self.active_workflows = {}
        
    async def orchestrate(self, user_request: str, context: Dict[str, Any] = None) -> AgentResult:
        """编排执行用户请求"""
        try:
            self.logger.info(
                "开始智能编排",
                agent_id=self.agent_id,
                user_request=user_request[:100] + "..." if len(user_request) > 100 else user_request
            )
            
            # 构建工作流
            workflow = await self.workflow_builder.build_workflow(user_request)
            
            # 执行工作流
            execution_results = await self.execution_engine.execute_workflow(workflow, context)
            
            # 汇总结果
            orchestration_result = await self._aggregate_results(execution_results, workflow)
            
            # 记录活跃工作流
            self.active_workflows[workflow.workflow_id] = {
                "workflow": workflow,
                "results": execution_results,
                "started_at": datetime.now(),
                "status": "completed"
            }
            
            return AgentResult(
                success=any(result.success for result in execution_results.values()),
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=orchestration_result,
                metadata={
                    "workflow_id": workflow.workflow_id,
                    "steps_executed": len(execution_results),
                    "successful_steps": sum(1 for r in execution_results.values() if r.success),
                    "total_execution_time": sum(r.execution_time for r in execution_results.values()),
                    "agents_used": list(set(r.agent_used for r in execution_results.values()))
                }
            )
            
        except Exception as e:
            error_msg = f"智能编排失败: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _aggregate_results(self, execution_results: Dict[str, ExecutionResult], workflow: Workflow) -> Dict[str, Any]:
        """汇总执行结果"""
        successful_results = {k: v for k, v in execution_results.items() if v.success}
        failed_results = {k: v for k, v in execution_results.items() if not v.success}
        
        # 构建最终结果
        aggregated = {
            "workflow_id": workflow.workflow_id,
            "workflow_name": workflow.name,
            "execution_summary": {
                "total_steps": len(execution_results),
                "successful_steps": len(successful_results),
                "failed_steps": len(failed_results),
                "success_rate": len(successful_results) / len(execution_results) if execution_results else 0
            },
            "results": {},
            "errors": [],
            "insights": []
        }
        
        # 聚合成功结果
        for step_id, result in successful_results.items():
            aggregated["results"][step_id] = {
                "data": result.result,
                "execution_time": result.execution_time,
                "agent": result.agent_used,
                "metadata": result.metadata
            }
        
        # 记录错误
        for step_id, result in failed_results.items():
            aggregated["errors"].append({
                "step_id": step_id,
                "error": result.error_message,
                "agent": result.agent_used
            })
        
        # 生成洞察
        aggregated["insights"] = await self._generate_orchestration_insights(execution_results, workflow)
        
        return aggregated
    
    async def _generate_orchestration_insights(self, results: Dict[str, ExecutionResult], workflow: Workflow) -> List[str]:
        """生成编排洞察"""
        insights = []
        
        total_time = sum(r.execution_time for r in results.values())
        successful_count = sum(1 for r in results.values() if r.success)
        
        insights.append(f"工作流包含 {len(results)} 个步骤，总执行时间 {total_time:.2f} 秒")
        
        if successful_count == len(results):
            insights.append("所有步骤执行成功，工作流完整完成")
        elif successful_count > 0:
            insights.append(f"{successful_count} 个步骤成功执行，{len(results) - successful_count} 个步骤失败")
        else:
            insights.append("工作流执行失败，所有步骤都未成功完成")
        
        # 性能洞察
        if total_time > 60:
            insights.append("执行时间较长，建议优化工作流或增加并行处理")
        
        # Agent使用统计
        agents_used = set(r.agent_used for r in results.values())
        insights.append(f"使用了 {len(agents_used)} 个不同的Agent：{', '.join(agents_used)}")
        
        return insights
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        if workflow_id not in self.active_workflows:
            return None
        
        workflow_info = self.active_workflows[workflow_id]
        return {
            "workflow_id": workflow_id,
            "name": workflow_info["workflow"].name,
            "status": workflow_info["status"],
            "started_at": workflow_info["started_at"].isoformat(),
            "steps": len(workflow_info["workflow"].steps),
            "completed_steps": len(workflow_info["results"]),
            "success_rate": sum(1 for r in workflow_info["results"].values() if r.success) / len(workflow_info["results"]) if workflow_info["results"] else 0
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        health = await super().health_check()
        
        health.update({
            "workflow_builder": "healthy",
            "execution_engine": "healthy",
            "active_workflows": len(self.active_workflows),
            "supported_agents": list(self.execution_engine.agent_selector.agent_registry.keys()),
            "orchestration_features": {
                "intent_analysis": True,
                "workflow_generation": True,
                "parallel_execution": True,
                "error_recovery": True
            }
        })
        
        return health
    
    async def cleanup(self):
        """清理资源"""
        await super().cleanup()
        
        # 清理过期的工作流
        current_time = datetime.now()
        expired_workflows = []
        
        for workflow_id, info in self.active_workflows.items():
            if (current_time - info["started_at"]).total_seconds() > 3600:  # 1小时过期
                expired_workflows.append(workflow_id)
        
        for workflow_id in expired_workflows:
            del self.active_workflows[workflow_id]