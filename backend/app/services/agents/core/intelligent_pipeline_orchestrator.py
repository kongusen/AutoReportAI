"""
Intelligent Pipeline Orchestrator

Centralizes the template-placeholder-datasource-analysis-report pipeline
using the agents system as the core processing engine.

This replaces the distributed logic across multiple services with a unified
agent-driven approach while maintaining API compatibility.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time

from ..base import BaseAgent, AgentConfig, AgentResult, AgentType
from ..orchestration import AgentOrchestrator, WorkflowDefinition, TaskStep, WorkflowResult


logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline processing stages"""
    TEMPLATE_ANALYSIS = "template_analysis"
    PLACEHOLDER_EXTRACTION = "placeholder_extraction"
    DATA_SOURCE_VALIDATION = "data_source_validation"
    DATA_RETRIEVAL = "data_retrieval"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_GENERATION = "content_generation"
    VISUALIZATION = "visualization"
    REPORT_ASSEMBLY = "report_assembly"
    QUALITY_ASSURANCE = "quality_assurance"
    FINALIZATION = "finalization"


@dataclass
class PipelineContext:
    """Pipeline execution context"""
    template_id: str
    data_source_id: str
    user_id: str
    template_type: str = "docx"
    output_format: str = "docx"
    optimization_level: str = "standard"
    batch_size: int = 10000
    enable_caching: bool = True
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Comprehensive pipeline execution result"""
    success: bool
    pipeline_id: str
    context: PipelineContext
    stage_results: Dict[PipelineStage, AgentResult] = field(default_factory=dict)
    final_output: Optional[bytes] = None
    output_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    error_message: Optional[str] = None
    quality_score: float = 0.0


class IntelligentPipelineOrchestrator(BaseAgent):
    """
    Orchestrates the complete report generation pipeline using agents
    """
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="intelligent_pipeline_orchestrator",
                agent_type=AgentType.ORCHESTRATOR,
                name="Intelligent Pipeline Orchestrator",
                description="Orchestrates complete template-to-report pipeline using agents",
                timeout_seconds=600,  # 10 minutes for complex reports
                enable_caching=True,
                cache_ttl_seconds=1800  # 30 minutes cache
            )
        
        super().__init__(config)
        self.agent_orchestrator = AgentOrchestrator()
        self.pipeline_definitions = self._create_pipeline_definitions()
    
    def _create_pipeline_definitions(self) -> Dict[str, WorkflowDefinition]:
        """Create pipeline workflow definitions"""
        return {
            "standard_report_pipeline": WorkflowDefinition(
                workflow_id="standard_report_pipeline",
                name="Standard Report Generation Pipeline",
                description="Complete pipeline for standard report generation",
                steps=[
                    # Stage 1: Template Analysis
                    TaskStep(
                        step_id="analyze_template",
                        agent_type=AgentType.ANALYSIS,
                        input_data={"analysis_type": "template_structure"},
                        depends_on=[]
                    ),
                    
                    # Stage 2: Placeholder Extraction
                    TaskStep(
                        step_id="extract_placeholders",
                        agent_type=AgentType.CONTENT_GENERATION,
                        input_data={"task": "placeholder_extraction"},
                        depends_on=["analyze_template"]
                    ),
                    
                    # Stage 3: Data Source Validation
                    TaskStep(
                        step_id="validate_data_source",
                        agent_type=AgentType.DATA_QUERY,
                        input_data={"operation": "validate_connection"},
                        depends_on=[]
                    ),
                    
                    # Stage 4: Data Retrieval (Parallel with template analysis)
                    TaskStep(
                        step_id="retrieve_data",
                        agent_type=AgentType.DATA_QUERY,
                        input_data={"operation": "fetch_data"},
                        depends_on=["validate_data_source", "extract_placeholders"]
                    ),
                    
                    # Stage 5: Data Analysis
                    TaskStep(
                        step_id="analyze_data",
                        agent_type=AgentType.ANALYSIS,
                        input_data={"analysis_type": "comprehensive"},
                        depends_on=["retrieve_data"]
                    ),
                    
                    # Stage 6: Content Generation
                    TaskStep(
                        step_id="generate_content",
                        agent_type=AgentType.CONTENT_GENERATION,
                        input_data={"content_type": "placeholder_replacement"},
                        depends_on=["analyze_data"]
                    ),
                    
                    # Stage 7: Visualization (Optional, parallel)
                    TaskStep(
                        step_id="create_visualizations",
                        agent_type=AgentType.VISUALIZATION,
                        input_data={"chart_type": "auto"},
                        depends_on=["analyze_data"],
                        optional=True
                    ),
                    
                    # Stage 8: Report Assembly
                    TaskStep(
                        step_id="assemble_report",
                        agent_type=AgentType.CONTENT_GENERATION,
                        input_data={"task": "document_assembly"},
                        depends_on=["generate_content", "create_visualizations"]
                    ),
                    
                    # Stage 9: Quality Assurance
                    TaskStep(
                        step_id="quality_check",
                        agent_type=AgentType.ANALYSIS,
                        input_data={"analysis_type": "quality_assessment"},
                        depends_on=["assemble_report"],
                        optional=True
                    )
                ],
                parallel_execution=True,
                continue_on_error=True
            ),
            
            "high_performance_pipeline": WorkflowDefinition(
                workflow_id="high_performance_pipeline",
                name="High Performance Pipeline",
                description="Optimized pipeline for large datasets and complex reports",
                steps=[
                    # Optimized with streaming and batch processing
                    TaskStep(
                        step_id="streaming_data_retrieval",
                        agent_type=AgentType.DATA_QUERY,
                        input_data={"operation": "streaming_fetch", "batch_size": 5000},
                        depends_on=[]
                    ),
                    
                    TaskStep(
                        step_id="parallel_analysis",
                        agent_type=AgentType.ANALYSIS,
                        input_data={"analysis_type": "batch_processing"},
                        depends_on=["streaming_data_retrieval"]
                    ),
                    
                    TaskStep(
                        step_id="optimized_content_generation",
                        agent_type=AgentType.CONTENT_GENERATION,
                        input_data={"optimization": "memory_efficient"},
                        depends_on=["parallel_analysis"]
                    ),
                    
                    TaskStep(
                        step_id="efficient_visualization",
                        agent_type=AgentType.VISUALIZATION,
                        input_data={"optimization": "performance"},
                        depends_on=["parallel_analysis"],
                        optional=True
                    ),
                    
                    TaskStep(
                        step_id="streaming_assembly",
                        agent_type=AgentType.CONTENT_GENERATION,
                        input_data={"task": "streaming_assembly"},
                        depends_on=["optimized_content_generation", "efficient_visualization"]
                    )
                ],
                parallel_execution=True,
                continue_on_error=False
            )
        }
    
    async def execute(
        self,
        input_data: Union[PipelineContext, Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Execute the complete report generation pipeline
        """
        start_time = time.time()
        
        try:
            # Parse input
            if isinstance(input_data, dict):
                pipeline_context = PipelineContext(**input_data)
            else:
                pipeline_context = input_data
            
            pipeline_id = f"pipeline_{hash(str(pipeline_context))}_{int(start_time)}"
            
            self.logger.info(
                f"Starting intelligent pipeline execution",
                agent_id=self.agent_id,
                pipeline_id=pipeline_id,
                template_id=pipeline_context.template_id,
                optimization_level=pipeline_context.optimization_level
            )
            
            # Select appropriate pipeline based on optimization level
            if pipeline_context.optimization_level == "high_performance":
                workflow = self.pipeline_definitions["high_performance_pipeline"]
            else:
                workflow = self.pipeline_definitions["standard_report_pipeline"]
            
            # Customize workflow with context
            customized_workflow = self._customize_pipeline_workflow(workflow, pipeline_context)
            
            # Execute pipeline through orchestrator
            orchestration_result = await self.agent_orchestrator.execute(
                customized_workflow, 
                context or {}
            )
            
            # Process results
            if orchestration_result.success:
                pipeline_result = await self._process_pipeline_results(
                    pipeline_id, pipeline_context, orchestration_result.data, start_time
                )
            else:
                pipeline_result = PipelineResult(
                    success=False,
                    pipeline_id=pipeline_id,
                    context=pipeline_context,
                    execution_time=time.time() - start_time,
                    error_message=orchestration_result.error_message or "Pipeline execution failed"
                )
            
            return AgentResult(
                success=pipeline_result.success,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=pipeline_result,
                metadata={
                    "pipeline_id": pipeline_id,
                    "stages_completed": len(pipeline_result.stage_results),
                    "quality_score": pipeline_result.quality_score,
                    "optimization_level": pipeline_context.optimization_level
                },
                error_message=pipeline_result.error_message,
                execution_time=pipeline_result.execution_time
            )
            
        except Exception as e:
            error_msg = f"Pipeline execution failed: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
    
    def _customize_pipeline_workflow(
        self, 
        workflow: WorkflowDefinition, 
        context: PipelineContext
    ) -> WorkflowDefinition:
        """Customize workflow with pipeline context"""
        import copy
        customized = copy.deepcopy(workflow)
        
        # Update global context
        customized.global_context.update({
            "template_id": context.template_id,
            "data_source_id": context.data_source_id,
            "user_id": context.user_id,
            "template_type": context.template_type,
            "output_format": context.output_format,
            "batch_size": context.batch_size,
            "optimization_level": context.optimization_level,
            **context.custom_config
        })
        
        # Customize each step based on context
        for step in customized.steps:
            if step.agent_type == AgentType.DATA_QUERY:
                step.input_data.update({
                    "data_source_id": context.data_source_id,
                    "batch_size": context.batch_size,
                    "enable_caching": context.enable_caching
                })
            
            elif step.agent_type == AgentType.ANALYSIS:
                step.input_data.update({
                    "optimization_level": context.optimization_level
                })
            
            elif step.agent_type == AgentType.CONTENT_GENERATION:
                step.input_data.update({
                    "template_id": context.template_id,
                    "output_format": context.output_format
                })
            
            elif step.agent_type == AgentType.VISUALIZATION:
                step.input_data.update({
                    "output_format": "png",
                    "optimization": context.optimization_level
                })
        
        return customized
    
    async def _process_pipeline_results(
        self,
        pipeline_id: str,
        context: PipelineContext,
        workflow_result: WorkflowResult,
        start_time: float
    ) -> PipelineResult:
        """Process and aggregate pipeline results"""
        
        stage_results = {}
        quality_scores = []
        
        # Map workflow step results to pipeline stages
        stage_mapping = {
            "analyze_template": PipelineStage.TEMPLATE_ANALYSIS,
            "extract_placeholders": PipelineStage.PLACEHOLDER_EXTRACTION,
            "validate_data_source": PipelineStage.DATA_SOURCE_VALIDATION,
            "retrieve_data": PipelineStage.DATA_RETRIEVAL,
            "streaming_data_retrieval": PipelineStage.DATA_RETRIEVAL,
            "analyze_data": PipelineStage.DATA_ANALYSIS,
            "parallel_analysis": PipelineStage.DATA_ANALYSIS,
            "generate_content": PipelineStage.CONTENT_GENERATION,
            "optimized_content_generation": PipelineStage.CONTENT_GENERATION,
            "create_visualizations": PipelineStage.VISUALIZATION,
            "efficient_visualization": PipelineStage.VISUALIZATION,
            "assemble_report": PipelineStage.REPORT_ASSEMBLY,
            "streaming_assembly": PipelineStage.REPORT_ASSEMBLY,
            "quality_check": PipelineStage.QUALITY_ASSURANCE
        }
        
        for step_id, result in workflow_result.results.items():
            if step_id in stage_mapping:
                stage = stage_mapping[step_id]
                stage_results[stage] = result
                
                # Extract quality scores if available
                if result.success and hasattr(result.data, 'quality_score'):
                    quality_scores.append(result.data.quality_score)
        
        # Extract final output from report assembly
        final_output = None
        output_path = None
        
        if PipelineStage.REPORT_ASSEMBLY in stage_results:
            assembly_result = stage_results[PipelineStage.REPORT_ASSEMBLY]
            if assembly_result.success and hasattr(assembly_result.data, 'file_path'):
                output_path = assembly_result.data.file_path
                
                # Read output file if available
                try:
                    import os
                    if output_path and os.path.exists(output_path):
                        with open(output_path, 'rb') as f:
                            final_output = f.read()
                except Exception as e:
                    self.logger.warning(f"Failed to read output file: {e}")
        
        # Calculate overall quality score
        quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Determine success based on critical stages
        critical_stages = [
            PipelineStage.DATA_RETRIEVAL,
            PipelineStage.CONTENT_GENERATION,
            PipelineStage.REPORT_ASSEMBLY
        ]
        
        success = all(
            stage in stage_results and stage_results[stage].success 
            for stage in critical_stages
        )
        
        return PipelineResult(
            success=success,
            pipeline_id=pipeline_id,
            context=context,
            stage_results=stage_results,
            final_output=final_output,
            output_path=output_path,
            metadata={
                "workflow_id": workflow_result.workflow_id,
                "total_stages": len(stage_results),
                "successful_stages": len([r for r in stage_results.values() if r.success]),
                "pipeline_type": context.optimization_level,
                "template_type": context.template_type
            },
            execution_time=time.time() - start_time,
            quality_score=quality_score,
            error_message=None if success else "One or more critical pipeline stages failed"
        )
    
    async def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get status of a running or completed pipeline"""
        # This would integrate with a pipeline tracking system
        # For now, return a basic structure
        return {
            "pipeline_id": pipeline_id,
            "status": "unknown",
            "current_stage": None,
            "progress_percentage": 0,
            "estimated_completion_time": None
        }
    
    async def cancel_pipeline(self, pipeline_id: str) -> bool:
        """Cancel a running pipeline"""
        # This would integrate with the workflow cancellation system
        self.logger.info(f"Pipeline cancellation requested: {pipeline_id}")
        return False  # Not implemented yet
    
    def get_supported_optimizations(self) -> List[str]:
        """Get list of supported optimization levels"""
        return ["standard", "high_performance", "memory_optimized"]
    
    def get_pipeline_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available pipeline templates"""
        return {
            name: {
                "name": definition.name,
                "description": definition.description,
                "steps": len(definition.steps),
                "parallel_execution": definition.parallel_execution
            }
            for name, definition in self.pipeline_definitions.items()
        }


# Global pipeline orchestrator instance
pipeline_orchestrator = IntelligentPipelineOrchestrator()