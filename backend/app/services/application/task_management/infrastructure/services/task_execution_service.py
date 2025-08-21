"""
Task Execution Service Implementation

任务执行服务实现
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ...application.interfaces.task_execution_interface import TaskExecutionInterface
from ...domain.entities.task_entity import TaskEntity, TaskExecution
from ....application.orchestration.workflow_engine import WorkflowEngine, StepHandler

logger = logging.getLogger(__name__)


class ReportGenerationStepHandler(StepHandler):
    """报告生成步骤处理器"""
    
    async def execute(self, step_def, context, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行报告生成步骤"""
        try:
            # 动态导入避免循环依赖
            from app.services.application.task_management.execution.unified_pipeline import unified_report_generation_pipeline
            
            task_id = inputs.get("task_id")
            user_id = inputs.get("user_id")
            
            if not task_id or not user_id:
                raise ValueError("Missing required parameters: task_id or user_id")
            
            # 执行统一报告生成流水线
            result = unified_report_generation_pipeline(
                task_id=int(task_id),
                user_id=user_id,
                mode="auto",
                execution_context=context
            )
            
            return {
                "success": result.get("success", result.get("status") == "completed"),
                "data": result.get("data", {}),
                "report_path": result.get("report_path"),
                "pipeline_mode": result.get("pipeline_mode"),
                "execution_time": result.get("execution_time", 0)
            }
            
        except Exception as e:
            logger.error(f"Report generation step failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class DataAnalysisStepHandler(StepHandler):
    """数据分析步骤处理器"""
    
    async def execute(self, step_def, context, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据分析步骤"""
        try:
            # 这里可以集成数据分析领域服务
            from ...domain.services.data_analysis_domain_service import DataAnalysisDomainService
            
            analysis_service = DataAnalysisDomainService()
            
            # 模拟数据分析
            data_source_id = inputs.get("data_source_id")
            analysis_type = inputs.get("analysis_type", "descriptive")
            
            # 实际实现中需要获取数据并分析
            result = {
                "analysis_type": analysis_type,
                "data_source_id": data_source_id,
                "results": {
                    "summary": "Data analysis completed successfully",
                    "metrics": {
                        "total_records": 1000,
                        "processed_records": 950,
                        "quality_score": 0.95
                    }
                }
            }
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Data analysis step failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class TaskExecutionService(TaskExecutionInterface):
    """任务执行服务实现"""
    
    def __init__(self):
        self.workflow_engine = WorkflowEngine()
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self._setup_step_handlers()
    
    def _setup_step_handlers(self):
        """设置步骤处理器"""
        self.workflow_engine.register_step_handler(
            "report_generation",
            ReportGenerationStepHandler()
        )
        self.workflow_engine.register_step_handler(
            "data_analysis",
            DataAnalysisStepHandler()
        )
    
    async def execute(self, task: TaskEntity, execution: TaskExecution,
                     context: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        try:
            # 记录执行开始
            self.active_executions[execution.execution_id] = {
                "task_id": task.id,
                "execution_id": execution.execution_id,
                "status": "running",
                "started_at": datetime.utcnow(),
                "progress": 0
            }
            
            # 根据任务类型创建工作流
            workflow_def = self._create_workflow_definition(task, context)
            
            if not workflow_def:
                raise ValueError(f"Unsupported task type: {task.task_type}")
            
            # 准备输入数据
            workflow_inputs = self._prepare_workflow_inputs(task, execution, context)
            
            # 执行工作流
            workflow_execution = await self.workflow_engine.execute_workflow(
                workflow_def, workflow_inputs
            )
            
            # 更新执行状态
            self.active_executions[execution.execution_id]["status"] = "completed"
            self.active_executions[execution.execution_id]["progress"] = 100
            
            if workflow_execution.is_completed():
                return {
                    "success": True,
                    "data": workflow_execution.context.outputs,
                    "workflow_id": workflow_execution.workflow_def.workflow_id,
                    "execution_time": workflow_execution.duration
                }
            else:
                return {
                    "success": False,
                    "error": workflow_execution.error_message or "Workflow execution failed",
                    "workflow_id": workflow_execution.workflow_def.workflow_id
                }
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            
            # 更新执行状态
            if execution.execution_id in self.active_executions:
                self.active_executions[execution.execution_id]["status"] = "failed"
                self.active_executions[execution.execution_id]["error"] = str(e)
            
            return {
                "success": False,
                "error": str(e)
            }
        
        finally:
            # 清理完成的执行记录（可选）
            if execution.execution_id in self.active_executions:
                exec_info = self.active_executions[execution.execution_id]
                if exec_info["status"] in ["completed", "failed"]:
                    # 保留一段时间后清理
                    asyncio.create_task(self._cleanup_execution(execution.execution_id))
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        try:
            if execution_id not in self.active_executions:
                return False
            
            # 这里应该实际取消正在运行的工作流
            # 简化实现，直接标记为已取消
            self.active_executions[execution_id]["status"] = "cancelled"
            self.active_executions[execution_id]["cancelled_at"] = datetime.utcnow()
            
            logger.info(f"Execution cancelled: {execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel execution {execution_id}: {e}")
            return False
    
    async def get_execution_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        try:
            # 查找任务的活跃执行
            for exec_id, exec_info in self.active_executions.items():
                if exec_info["task_id"] == task_id:
                    return {
                        "execution_id": exec_id,
                        "task_id": task_id,
                        "status": exec_info["status"],
                        "progress": exec_info.get("progress", 0),
                        "started_at": exec_info["started_at"].isoformat(),
                        "error": exec_info.get("error"),
                        "current_step": exec_info.get("current_step", "Processing...")
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get execution status for task {task_id}: {e}")
            return None
    
    async def get_execution_progress(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行进度"""
        try:
            if execution_id not in self.active_executions:
                return None
            
            exec_info = self.active_executions[execution_id]
            return {
                "execution_id": execution_id,
                "progress": exec_info.get("progress", 0),
                "status": exec_info["status"],
                "current_step": exec_info.get("current_step", "Processing..."),
                "estimated_completion": exec_info.get("estimated_completion"),
                "steps_completed": exec_info.get("steps_completed", 0),
                "total_steps": exec_info.get("total_steps", 1)
            }
            
        except Exception as e:
            logger.error(f"Failed to get execution progress {execution_id}: {e}")
            return None
    
    async def get_execution_logs(self, execution_id: str) -> List[Dict[str, Any]]:
        """获取执行日志"""
        try:
            # 这里应该从日志存储中获取实际日志
            # 简化实现，返回模拟日志
            if execution_id not in self.active_executions:
                return []
            
            exec_info = self.active_executions[execution_id]
            logs = [
                {
                    "timestamp": exec_info["started_at"].isoformat(),
                    "level": "INFO",
                    "message": "Execution started",
                    "step": "initialization"
                }
            ]
            
            if exec_info["status"] == "completed":
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "Execution completed successfully",
                    "step": "finalization"
                })
            elif exec_info["status"] == "failed":
                logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "ERROR",
                    "message": exec_info.get("error", "Execution failed"),
                    "step": "error_handling"
                })
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get execution logs {execution_id}: {e}")
            return []
    
    def _create_workflow_definition(self, task: TaskEntity, context: Dict[str, Any]):
        """创建工作流定义"""
        from ....application.orchestration.workflow_engine import (
            WorkflowDefinition, StepDefinition, StepType
        )
        
        if task.task_type == "report_generation":
            return WorkflowDefinition(
                workflow_id=f"report_generation_{task.id}",
                name="Report Generation Workflow",
                description="Generate report based on template and data source",
                steps=[
                    StepDefinition(
                        step_id="generate_report",
                        step_type=StepType.ACTION,
                        name="Generate Report",
                        description="Execute report generation pipeline",
                        handler="report_generation",
                        parameters={
                            "task_id": task.id,
                            "user_id": task.owner_id,
                            "template_id": task.template_id,
                            "data_source_id": task.data_source_id
                        },
                        timeout_seconds=3600,
                        max_retries=2
                    )
                ]
            )
        
        elif task.task_type == "data_analysis":
            return WorkflowDefinition(
                workflow_id=f"data_analysis_{task.id}",
                name="Data Analysis Workflow",
                description="Perform data analysis on specified data source",
                steps=[
                    StepDefinition(
                        step_id="analyze_data",
                        step_type=StepType.ACTION,
                        name="Analyze Data",
                        description="Execute data analysis",
                        handler="data_analysis",
                        parameters={
                            "task_id": task.id,
                            "data_source_id": task.data_source_id,
                            "analysis_type": task.configuration.get("analysis_type", "descriptive")
                        },
                        timeout_seconds=1800,
                        max_retries=1
                    )
                ]
            )
        
        return None
    
    def _prepare_workflow_inputs(self, task: TaskEntity, execution: TaskExecution,
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """准备工作流输入"""
        return {
            "task_id": task.id,
            "execution_id": execution.execution_id,
            "task_type": task.task_type,
            "task_configuration": task.configuration,
            "task_parameters": task.parameters,
            "user_id": task.owner_id,
            "template_id": task.template_id,
            "data_source_id": task.data_source_id,
            "execution_context": context
        }
    
    async def _cleanup_execution(self, execution_id: str, delay_seconds: int = 300):
        """清理执行记录"""
        await asyncio.sleep(delay_seconds)  # 等待5分钟
        
        if execution_id in self.active_executions:
            del self.active_executions[execution_id]
            logger.info(f"Cleaned up execution record: {execution_id}")