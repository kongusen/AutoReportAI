"""
Agent Orchestrator

Coordinates the execution of multiple agents to process complex tasks.
Replaces the high-level coordination logic from the intelligent_placeholder system.

Features:
- Sequential and parallel agent execution
- Task workflow management
- Error handling and recovery
- Result aggregation and processing
- Dynamic agent selection based on task requirements
"""

import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time

from .base import BaseAgent, AgentConfig, AgentResult, AgentType, agent_registry
from .data_query_agent import DataQueryAgent, QueryRequest
from .content_generation_agent import ContentGenerationAgent, ContentRequest
from .analysis_agent import AnalysisAgent, AnalysisRequest
from .visualization_agent import VisualizationAgent, ChartRequest


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskStep:
    """Individual task step in workflow"""
    step_id: str
    agent_type: AgentType
    input_data: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    optional: bool = False
    retry_count: int = 3
    timeout_seconds: int = 60


@dataclass
class WorkflowDefinition:
    """Workflow definition containing multiple task steps"""
    workflow_id: str
    name: str
    description: str
    steps: List[TaskStep]
    global_context: Dict[str, Any] = field(default_factory=dict)
    parallel_execution: bool = False
    continue_on_error: bool = False


@dataclass
class WorkflowResult:
    """Workflow execution result"""
    workflow_id: str
    status: WorkflowStatus
    results: Dict[str, AgentResult]
    start_time: float
    end_time: Optional[float] = None
    total_duration: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator(BaseAgent):
    """
    Orchestrates the execution of multiple agents to complete complex tasks
    """
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="agent_orchestrator",
                agent_type=AgentType.ORCHESTRATOR,
                name="Agent Orchestrator",
                description="Orchestrates execution of multiple agents",
                timeout_seconds=300,  # Longer timeout for complex workflows
                enable_caching=False  # Don't cache workflow results
            )
        
        super().__init__(config)
        self.registered_agents = {}
        self.workflow_templates = self._load_workflow_templates()
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize and register default agents"""
        # Create default agent instances
        data_agent = DataQueryAgent()
        content_agent = ContentGenerationAgent()
        analysis_agent = AnalysisAgent()
        viz_agent = VisualizationAgent()
        
        # Register agents
        self.registered_agents[AgentType.DATA_QUERY] = data_agent
        self.registered_agents[AgentType.CONTENT_GENERATION] = content_agent
        self.registered_agents[AgentType.ANALYSIS] = analysis_agent
        self.registered_agents[AgentType.VISUALIZATION] = viz_agent
        
        # Also register in global registry
        for agent in self.registered_agents.values():
            agent_registry.register_agent(agent)
    
    def _load_workflow_templates(self) -> Dict[str, WorkflowDefinition]:
        """Load predefined workflow templates"""
        return {
            "statistical_placeholder": WorkflowDefinition(
                workflow_id="statistical_placeholder",
                name="Statistical Placeholder Processing",
                description="Process statistical placeholders with data query and content generation",
                steps=[
                    TaskStep(
                        step_id="fetch_data",
                        agent_type=AgentType.DATA_QUERY,
                        input_data={},
                        depends_on=[]
                    ),
                    TaskStep(
                        step_id="analyze_data",
                        agent_type=AgentType.ANALYSIS,
                        input_data={},
                        depends_on=["fetch_data"]
                    ),
                    TaskStep(
                        step_id="generate_content",
                        agent_type=AgentType.CONTENT_GENERATION,
                        input_data={},
                        depends_on=["analyze_data"]
                    )
                ]
            ),
            
            "chart_placeholder": WorkflowDefinition(
                workflow_id="chart_placeholder",
                name="Chart Placeholder Processing",
                description="Process chart placeholders with data query, analysis, and visualization",
                steps=[
                    TaskStep(
                        step_id="fetch_data",
                        agent_type=AgentType.DATA_QUERY,
                        input_data={},
                        depends_on=[]
                    ),
                    TaskStep(
                        step_id="analyze_data",
                        agent_type=AgentType.ANALYSIS,
                        input_data={},
                        depends_on=["fetch_data"]
                    ),
                    TaskStep(
                        step_id="create_chart",
                        agent_type=AgentType.VISUALIZATION,
                        input_data={},
                        depends_on=["fetch_data"]
                    ),
                    TaskStep(
                        step_id="generate_description",
                        agent_type=AgentType.CONTENT_GENERATION,
                        input_data={},
                        depends_on=["analyze_data", "create_chart"],
                        optional=True
                    )
                ]
            ),
            
            "comprehensive_analysis": WorkflowDefinition(
                workflow_id="comprehensive_analysis",
                name="Comprehensive Data Analysis",
                description="Complete data analysis with statistics, charts, and content generation",
                steps=[
                    TaskStep(
                        step_id="fetch_data",
                        agent_type=AgentType.DATA_QUERY,
                        input_data={},
                        depends_on=[]
                    ),
                    TaskStep(
                        step_id="descriptive_analysis",
                        agent_type=AgentType.ANALYSIS,
                        input_data={"analysis_type": "descriptive"},
                        depends_on=["fetch_data"]
                    ),
                    TaskStep(
                        step_id="trend_analysis",
                        agent_type=AgentType.ANALYSIS,
                        input_data={"analysis_type": "trend"},
                        depends_on=["fetch_data"],
                        optional=True
                    ),
                    TaskStep(
                        step_id="create_summary_chart",
                        agent_type=AgentType.VISUALIZATION,
                        input_data={"chart_type": "bar"},
                        depends_on=["descriptive_analysis"]
                    ),
                    TaskStep(
                        step_id="create_trend_chart",
                        agent_type=AgentType.VISUALIZATION,
                        input_data={"chart_type": "line"},
                        depends_on=["trend_analysis"],
                        optional=True
                    ),
                    TaskStep(
                        step_id="generate_report",
                        agent_type=AgentType.CONTENT_GENERATION,
                        input_data={"content_type": "analysis"},
                        depends_on=["descriptive_analysis", "create_summary_chart"]
                    )
                ],
                parallel_execution=True,
                continue_on_error=True
            )
        }
    
    async def execute(
        self,
        input_data: Union[WorkflowDefinition, Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Execute a workflow or single placeholder processing task
        
        Args:
            input_data: WorkflowDefinition or dict with workflow/task parameters
            context: Additional context information
            
        Returns:
            AgentResult with workflow execution results
        """
        try:
            # Parse input data
            if isinstance(input_data, dict):
                # Check if this is a placeholder processing request
                if "placeholder_type" in input_data and "description" in input_data:
                    return await self._process_single_placeholder(input_data, context)
                else:
                    # Assume it's workflow parameters
                    workflow = self._create_workflow_from_dict(input_data)
            else:
                workflow = input_data
            
            self.logger.info(
                "Starting workflow execution",
                agent_id=self.agent_id,
                workflow_id=workflow.workflow_id,
                step_count=len(workflow.steps)
            )
            
            # Execute workflow
            workflow_result = await self._execute_workflow(workflow, context)
            
            return AgentResult(
                success=workflow_result.status == WorkflowStatus.COMPLETED,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=workflow_result,
                metadata={
                    "workflow_id": workflow.workflow_id,
                    "step_count": len(workflow.steps),
                    "execution_time": workflow_result.total_duration
                },
                error_message=workflow_result.error_message
            )
            
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _process_single_placeholder(
        self,
        placeholder_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Process a single placeholder using appropriate workflow template
        """
        placeholder_type = placeholder_data.get("placeholder_type", "")
        description = placeholder_data.get("description", "")
        data_source_id = placeholder_data.get("data_source_id")
        
        # Select appropriate workflow template
        if placeholder_type in ["统计", "分析"]:
            workflow_template = self.workflow_templates["statistical_placeholder"]
        elif placeholder_type == "图表":
            workflow_template = self.workflow_templates["chart_placeholder"]
        else:
            # Default to comprehensive analysis
            workflow_template = self.workflow_templates["comprehensive_analysis"]
        
        # Customize workflow with placeholder-specific data
        workflow = self._customize_workflow_for_placeholder(
            workflow_template, placeholder_data, context
        )
        
        return await self.execute(workflow, context)
    
    def _customize_workflow_for_placeholder(
        self,
        template: WorkflowDefinition,
        placeholder_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> WorkflowDefinition:
        """Customize workflow template for specific placeholder"""
        
        # Create a copy of the template
        import copy
        workflow = copy.deepcopy(template)
        
        # Update workflow ID and context
        workflow.workflow_id = f"{template.workflow_id}_{hash(str(placeholder_data))}"
        workflow.global_context.update(placeholder_data)
        if context:
            workflow.global_context.update(context)
        
        # Customize each step with placeholder-specific data
        for step in workflow.steps:
            if step.agent_type == AgentType.DATA_QUERY:
                step.input_data.update({
                    "data_source_id": placeholder_data.get("data_source_id"),
                    "query_type": "auto",
                    "description": placeholder_data.get("description", ""),
                    "limit": 1000
                })
            
            elif step.agent_type == AgentType.ANALYSIS:
                step.input_data.update({
                    "analysis_type": step.input_data.get("analysis_type", "descriptive"),
                    "parameters": placeholder_data.get("analysis_parameters", {})
                })
            
            elif step.agent_type == AgentType.CONTENT_GENERATION:
                step.input_data.update({
                    "content_type": step.input_data.get("content_type", "summary"),
                    "format": "text",
                    "tone": "professional",
                    "language": "zh-CN",
                    "max_length": 500
                })
            
            elif step.agent_type == AgentType.VISUALIZATION:
                step.input_data.update({
                    "chart_type": step.input_data.get("chart_type", "bar"),
                    "title": placeholder_data.get("description", ""),
                    "output_format": "png",
                    "width": 800,
                    "height": 600,
                    "theme": "professional"
                })
        
        return workflow
    
    async def _execute_workflow(
        self,
        workflow: WorkflowDefinition,
        context: Dict[str, Any] = None
    ) -> WorkflowResult:
        """Execute a complete workflow"""
        start_time = time.time()
        
        workflow_result = WorkflowResult(
            workflow_id=workflow.workflow_id,
            status=WorkflowStatus.RUNNING,
            results={},
            start_time=start_time
        )
        
        try:
            if workflow.parallel_execution:
                # Execute steps in parallel where possible
                results = await self._execute_parallel_workflow(workflow, context)
            else:
                # Execute steps sequentially
                results = await self._execute_sequential_workflow(workflow, context)
            
            workflow_result.results = results
            workflow_result.status = WorkflowStatus.COMPLETED
            workflow_result.end_time = time.time()
            workflow_result.total_duration = workflow_result.end_time - start_time
            
            # Check if any critical steps failed
            critical_failures = [
                step_id for step_id, result in results.items()
                if not result.success and not self._is_optional_step(workflow, step_id)
            ]
            
            if critical_failures and not workflow.continue_on_error:
                workflow_result.status = WorkflowStatus.FAILED
                workflow_result.error_message = f"Critical steps failed: {', '.join(critical_failures)}"
            
            self.logger.info(
                "Workflow execution completed",
                agent_id=self.agent_id,
                workflow_id=workflow.workflow_id,
                status=workflow_result.status.value,
                duration=workflow_result.total_duration,
                steps_completed=len([r for r in results.values() if r.success])
            )
            
        except Exception as e:
            workflow_result.status = WorkflowStatus.FAILED
            workflow_result.error_message = str(e)
            workflow_result.end_time = time.time()
            workflow_result.total_duration = workflow_result.end_time - start_time
            
            self.logger.error(
                "Workflow execution failed",
                agent_id=self.agent_id,
                workflow_id=workflow.workflow_id,
                error=str(e),
                duration=workflow_result.total_duration,
                exc_info=True
            )
        
        return workflow_result
    
    async def _execute_sequential_workflow(
        self,
        workflow: WorkflowDefinition,
        context: Dict[str, Any] = None
    ) -> Dict[str, AgentResult]:
        """Execute workflow steps sequentially"""
        results = {}
        step_outputs = {}
        
        # Sort steps by dependencies
        sorted_steps = self._topological_sort_steps(workflow.steps)
        
        for step in sorted_steps:
            try:
                # Check if dependencies are satisfied
                if not self._check_dependencies(step, results, workflow.continue_on_error):
                    if step.optional:
                        # Skip optional step with missing dependencies
                        results[step.step_id] = AgentResult(
                            success=False,
                            agent_id=self.agent_id,
                            agent_type=step.agent_type,
                            error_message="Skipped due to missing dependencies"
                        )
                        continue
                    else:
                        raise Exception(f"Dependencies not satisfied for step {step.step_id}")
                
                # Prepare input data with outputs from previous steps
                input_data = self._prepare_step_input_data(step, step_outputs, workflow.global_context)
                
                # Execute step
                agent = self._get_agent(step.agent_type)
                result = await agent.run(input_data, context)
                
                results[step.step_id] = result
                step_outputs[step.step_id] = result.data
                
                self.logger.debug(
                    "Step completed",
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    success=result.success,
                    execution_time=result.execution_time
                )
                
                # Stop on critical failure
                if not result.success and not step.optional and not workflow.continue_on_error:
                    break
                    
            except Exception as e:
                error_result = AgentResult(
                    success=False,
                    agent_id=self.agent_id,
                    agent_type=step.agent_type,
                    error_message=f"Step execution failed: {str(e)}"
                )
                results[step.step_id] = error_result
                
                self.logger.error(
                    "Step failed",
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    error=str(e),
                    exc_info=True
                )
                
                # Stop on critical failure
                if not step.optional and not workflow.continue_on_error:
                    break
        
        return results
    
    async def _execute_parallel_workflow(
        self,
        workflow: WorkflowDefinition,
        context: Dict[str, Any] = None
    ) -> Dict[str, AgentResult]:
        """Execute workflow steps in parallel where possible"""
        results = {}
        step_outputs = {}
        
        # Group steps by dependency levels
        dependency_levels = self._get_dependency_levels(workflow.steps)
        
        for level, steps in dependency_levels.items():
            # Execute all steps at this level in parallel
            tasks = []
            
            for step in steps:
                if self._check_dependencies(step, results, workflow.continue_on_error):
                    input_data = self._prepare_step_input_data(step, step_outputs, workflow.global_context)
                    agent = self._get_agent(step.agent_type)
                    task = agent.run(input_data, context)
                    tasks.append((step.step_id, step, task))
            
            # Wait for all tasks at this level to complete
            if tasks:
                completed_tasks = await asyncio.gather(
                    *[task for _, _, task in tasks],
                    return_exceptions=True
                )
                
                for i, ((step_id, step, _), result) in enumerate(zip(tasks, completed_tasks)):
                    if isinstance(result, Exception):
                        result = AgentResult(
                            success=False,
                            agent_id=self.agent_id,
                            agent_type=step.agent_type,
                            error_message=str(result)
                        )
                    
                    results[step_id] = result
                    if result.success:
                        step_outputs[step_id] = result.data
        
        return results
    
    def _topological_sort_steps(self, steps: List[TaskStep]) -> List[TaskStep]:
        """Sort steps by their dependencies using topological sort"""
        # Simple topological sort implementation
        step_dict = {step.step_id: step for step in steps}
        visited = set()
        sorted_steps = []
        
        def visit(step_id: str):
            if step_id in visited:
                return
            
            step = step_dict[step_id]
            for dep in step.depends_on:
                if dep in step_dict:
                    visit(dep)
            
            visited.add(step_id)
            sorted_steps.append(step)
        
        for step in steps:
            visit(step.step_id)
        
        return sorted_steps
    
    def _get_dependency_levels(self, steps: List[TaskStep]) -> Dict[int, List[TaskStep]]:
        """Group steps by their dependency levels"""
        step_dict = {step.step_id: step for step in steps}
        levels = {}
        step_levels = {}
        
        def get_level(step_id: str) -> int:
            if step_id in step_levels:
                return step_levels[step_id]
            
            step = step_dict[step_id]
            if not step.depends_on:
                level = 0
            else:
                level = max(get_level(dep) for dep in step.depends_on if dep in step_dict) + 1
            
            step_levels[step_id] = level
            return level
        
        for step in steps:
            level = get_level(step.step_id)
            if level not in levels:
                levels[level] = []
            levels[level].append(step)
        
        return levels
    
    def _check_dependencies(
        self,
        step: TaskStep,
        results: Dict[str, AgentResult],
        continue_on_error: bool = False
    ) -> bool:
        """Check if step dependencies are satisfied"""
        for dep_id in step.depends_on:
            if dep_id not in results:
                return False
            
            dep_result = results[dep_id]
            if not dep_result.success and not continue_on_error:
                return False
        
        return True
    
    def _prepare_step_input_data(
        self,
        step: TaskStep,
        step_outputs: Dict[str, Any],
        global_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare input data for step execution"""
        input_data = step.input_data.copy()
        
        # Add outputs from dependent steps
        for dep_id in step.depends_on:
            if dep_id in step_outputs:
                dep_output = step_outputs[dep_id]
                
                # Map specific outputs based on agent type
                if step.agent_type == AgentType.ANALYSIS and dep_id == "fetch_data":
                    if hasattr(dep_output, 'data'):
                        input_data["data"] = dep_output.data
                
                elif step.agent_type == AgentType.CONTENT_GENERATION:
                    if dep_id == "analyze_data" and hasattr(dep_output, 'results'):
                        input_data["data"] = dep_output.results
                    elif dep_id == "fetch_data" and hasattr(dep_output, 'data'):
                        input_data["data"] = dep_output.data
                
                elif step.agent_type == AgentType.VISUALIZATION and dep_id == "fetch_data":
                    if hasattr(dep_output, 'data'):
                        input_data["data"] = dep_output.data
        
        # Add global context, but filter out agent-specific parameters that don't belong
        allowed_global_params = {
            'template_id', 'template_name', 'template_content',
            'data_source_name', 'user_id', 'task_id', 'processing_config', 'output_config'
        }
        
        filtered_context = {k: v for k, v in global_context.items() if k in allowed_global_params}
        input_data.update(filtered_context)
        
        return input_data
    
    def _get_agent(self, agent_type: AgentType) -> BaseAgent:
        """Get agent instance for the specified type"""
        if agent_type not in self.registered_agents:
            raise Exception(f"No agent registered for type: {agent_type}")
        
        return self.registered_agents[agent_type]
    
    def _is_optional_step(self, workflow: WorkflowDefinition, step_id: str) -> bool:
        """Check if a step is optional"""
        for step in workflow.steps:
            if step.step_id == step_id:
                return step.optional
        return False
    
    def _create_workflow_from_dict(self, data: Dict[str, Any]) -> WorkflowDefinition:
        """Create workflow definition from dictionary"""
        # This is a simplified implementation
        # In practice, you might want more sophisticated workflow definition parsing
        
        workflow_id = data.get("workflow_id", "custom_workflow")
        template_name = data.get("template", "comprehensive_analysis")
        
        if template_name in self.workflow_templates:
            workflow = self.workflow_templates[template_name]
            workflow.workflow_id = workflow_id
            workflow.global_context.update(data.get("context", {}))
            return workflow
        else:
            raise Exception(f"Unknown workflow template: {template_name}")
    
    def register_agent(self, agent_type: AgentType, agent: BaseAgent):
        """Register a custom agent"""
        self.registered_agents[agent_type] = agent
        agent_registry.register_agent(agent)
        self.logger.info(f"Registered custom agent for type: {agent_type.value}")
    
    def get_workflow_templates(self) -> Dict[str, WorkflowDefinition]:
        """Get available workflow templates"""
        return self.workflow_templates
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for orchestrator and all registered agents"""
        health = await super().health_check()
        
        # Check all registered agents
        agent_health = {}
        for agent_type, agent in self.registered_agents.items():
            try:
                agent_health_result = await agent.health_check()
                agent_health[agent_type.value] = agent_health_result
            except Exception as e:
                agent_health[agent_type.value] = {
                    "healthy": False,
                    "error": str(e)
                }
                health["healthy"] = False
        
        health["registered_agents"] = agent_health
        health["workflow_templates"] = list(self.workflow_templates.keys())
        
        return health


# Create default orchestrator instance
orchestrator = AgentOrchestrator()