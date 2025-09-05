"""
AutoReportAI Agent 统一调用机制

基于设计文档的完整Agent系统实现：
- 集成所有子Agent：占位符→SQL转换、任务补充、图表生成、SQL验证、多上下文集成
- 统一调用接口：提供简单的API供上层业务调用
- 工作流编排：按照设计的五大流程执行
- 智能决策：根据任务类型自动选择合适的处理流程
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

# 导入所有子Agent
from .placeholder_to_sql_agent import (
    PlaceholderToSqlAgent, 
    PlaceholderContext,
    TimeContext,
    DataSourceContext,
    TaskContext,
    create_placeholder_to_sql_agent
)
from .task_supplement_agent import (
    TaskSupplementAgent,
    PlaceholderSupplementRequest,
    SupplementReason,
    SupplementPriority,
    create_task_supplement_agent
)
from .sql_testing_validator import (
    SqlTestingValidator,
    ValidationLevel,
    ValidationResult,
    TestCase,
    create_sql_testing_validator
)
from .multi_context_integrator import (
    MultiContextIntegrator,
    ContextType,
    ContextPriority,
    create_multi_context_integrator
)
from .tool_based_agent import (
    ToolBasedAgent,
    create_tool_based_agent
)

from ..llm.step_based_model_selector import (
    create_step_based_model_selector
)

logger = logging.getLogger(__name__)


class WorkflowType(Enum):
    """工作流类型"""
    PLACEHOLDER_TO_SQL = "placeholder_to_sql"           # 占位符→SQL转换流程
    TASK_SUPPLEMENT = "task_supplement"                 # 任务补充机制流程
    CHART_GENERATION = "chart_generation"               # 图表生成流程
    SQL_TESTING = "sql_testing"                        # SQL测试验证流程
    MULTI_CONTEXT_INTEGRATION = "multi_context"        # 多上下文集成流程
    FULL_PIPELINE = "full_pipeline"                    # 完整流水线


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentRequest:
    """Agent请求"""
    request_id: str
    workflow_type: WorkflowType
    parameters: Dict[str, Any]
    priority: str = "medium"  # low, medium, high, critical
    timeout_seconds: int = 300
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Agent响应"""
    request_id: str
    status: ExecutionStatus
    workflow_type: WorkflowType
    
    # 结果数据
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # 执行统计
    execution_time_seconds: float = 0.0
    steps_completed: int = 0
    steps_total: int = 0
    
    # 资源使用
    model_calls: int = 0
    tokens_used: int = 0
    cost_estimate: float = 0.0
    
    # 置信度和质量指标
    confidence_score: float = 0.0
    quality_score: float = 0.0
    
    # 元数据
    timestamp: datetime = field(default_factory=datetime.now)
    processing_details: Dict[str, Any] = field(default_factory=dict)


class AutoReportAIAgent:
    """AutoReportAI Agent 统一调用系统"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        
        # 初始化所有子Agent
        self.placeholder_sql_agent = create_placeholder_to_sql_agent(user_id)
        self.task_supplement_agent = create_task_supplement_agent(user_id)
        self.sql_validator = create_sql_testing_validator(user_id)
        self.context_integrator = create_multi_context_integrator(user_id)
        self.tool_agent = create_tool_based_agent(user_id)
        
        # 模型选择器
        self.model_selector = create_step_based_model_selector()
        
        # 执行历史
        self.execution_history: List[AgentResponse] = []
        
        # 当前运行的请求
        self.running_requests: Dict[str, AgentResponse] = {}
    
    async def execute_request(self, request: AgentRequest) -> AgentResponse:
        """
        执行Agent请求 - 统一入口点
        """
        request_id = request.request_id
        start_time = datetime.now()
        
        # 创建响应对象
        response = AgentResponse(
            request_id=request_id,
            status=ExecutionStatus.RUNNING,
            workflow_type=request.workflow_type
        )
        
        self.running_requests[request_id] = response
        
        try:
            logger.info(f"开始执行Agent请求 {request_id} ({request.workflow_type.value})")
            
            # 根据工作流类型调度到相应的处理函数
            if request.workflow_type == WorkflowType.PLACEHOLDER_TO_SQL:
                result = await self._execute_placeholder_to_sql_workflow(request)
            elif request.workflow_type == WorkflowType.TASK_SUPPLEMENT:
                result = await self._execute_task_supplement_workflow(request)
            elif request.workflow_type == WorkflowType.CHART_GENERATION:
                result = await self._execute_chart_generation_workflow(request)
            elif request.workflow_type == WorkflowType.SQL_TESTING:
                result = await self._execute_sql_testing_workflow(request)
            elif request.workflow_type == WorkflowType.MULTI_CONTEXT_INTEGRATION:
                result = await self._execute_multi_context_workflow(request)
            elif request.workflow_type == WorkflowType.FULL_PIPELINE:
                result = await self._execute_full_pipeline_workflow(request)
            else:
                raise ValueError(f"不支持的工作流类型: {request.workflow_type}")
            
            # 更新响应
            response.result = result
            response.status = ExecutionStatus.COMPLETED
            response.confidence_score = result.get("confidence_score", 0.5)
            response.quality_score = result.get("quality_score", 0.5)
            
            logger.info(f"Agent请求 {request_id} 执行成功")
            
        except Exception as e:
            logger.error(f"Agent请求 {request_id} 执行失败: {e}")
            response.status = ExecutionStatus.FAILED
            response.error_message = str(e)
            response.result = {"error": str(e)}
        
        finally:
            # 计算执行时间
            response.execution_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # 移除运行中的请求
            self.running_requests.pop(request_id, None)
            
            # 添加到执行历史
            self.execution_history.append(response)
        
        return response
    
    async def _execute_placeholder_to_sql_workflow(self, request: AgentRequest) -> Dict[str, Any]:
        """执行占位符→SQL转换流程"""
        
        params = request.parameters
        
        # 构建上下文对象
        placeholder_context = PlaceholderContext(
            placeholder_name=params.get("placeholder_name", ""),
            placeholder_description=params.get("placeholder_description", ""),
            placeholder_type=params.get("placeholder_type", "metric"),
            expected_data_type=params.get("expected_data_type", "number"),
            current_value=params.get("current_value"),
            is_empty=params.get("is_empty", True)
        )
        
        data_source_context = DataSourceContext(
            source_id=params.get("source_id", ""),
            source_type=params.get("source_type", "doris"),
            database_name=params.get("database_name", ""),
            available_tables=params.get("available_tables", []),
            table_schemas=params.get("table_schemas", {}),
            connection_info=params.get("connection_info", {})
        )
        
        task_context = TaskContext(
            task_id=params.get("task_id", ""),
            task_name=params.get("task_name", ""),
            task_description=params.get("task_description", ""),
            business_domain=params.get("business_domain", "general"),
            report_type=params.get("report_type", "dashboard")
        )
        
        time_context = None
        if params.get("time_context"):
            time_context = TimeContext(**params["time_context"])
        
        # 执行转换
        sql_result = await self.placeholder_sql_agent.convert_placeholder_to_sql(
            placeholder_context=placeholder_context,
            data_source_context=data_source_context,
            task_context=task_context,
            time_context=time_context
        )
        
        return {
            "sql_query": sql_result.sql_query,
            "explanation": sql_result.explanation,
            "confidence_score": sql_result.confidence_score,
            "used_tables": sql_result.used_tables,
            "used_columns": sql_result.used_columns,
            "time_filters": sql_result.time_filters,
            "validation_errors": sql_result.validation_errors or [],
            "correction_attempts": sql_result.correction_attempts,
            "workflow": "placeholder_to_sql"
        }
    
    async def _execute_task_supplement_workflow(self, request: AgentRequest) -> Dict[str, Any]:
        """执行任务补充机制流程"""
        
        params = request.parameters
        
        # 构建占位符上下文列表
        placeholders = []
        for p_data in params.get("placeholders", []):
            placeholder = PlaceholderContext(**p_data)
            placeholders.append(placeholder)
        
        # 构建其他上下文
        task_context = TaskContext(**params.get("task_context", {}))
        data_source_context = DataSourceContext(**params.get("data_source_context", {}))
        
        # 检测需要补充的占位符
        supplement_requests = await self.task_supplement_agent.detect_supplements_needed(
            template_id=params.get("template_id", ""),
            placeholders=placeholders,
            task_context=task_context,
            data_source_context=data_source_context
        )
        
        # 批量补充占位符
        if supplement_requests:
            batch_result = await self.task_supplement_agent.supplement_batch_placeholders(
                requests=supplement_requests,
                max_concurrent=params.get("max_concurrent", 3)
            )
            
            return {
                "total_requests": batch_result.total_requests,
                "successful_supplements": batch_result.successful_supplements,
                "failed_supplements": batch_result.failed_supplements,
                "overall_confidence": batch_result.overall_confidence,
                "processing_time_seconds": batch_result.processing_time_seconds,
                "individual_results": [
                    {
                        "placeholder_id": r.placeholder_id,
                        "success": r.success,
                        "sql_query": r.sql_query,
                        "confidence_score": r.confidence_score
                    } for r in batch_result.individual_results
                ],
                "workflow": "task_supplement"
            }
        else:
            return {
                "total_requests": 0,
                "successful_supplements": 0,
                "failed_supplements": 0,
                "overall_confidence": 1.0,
                "message": "没有发现需要补充的占位符",
                "workflow": "task_supplement"
            }
    
    async def _execute_chart_generation_workflow(self, request: AgentRequest) -> Dict[str, Any]:
        """执行图表生成流程"""
        
        # 使用工具Agent进行图表生成
        chart_request = f"""
        请根据以下数据生成图表：
        数据: {request.parameters.get("data", [])}
        图表类型: {request.parameters.get("chart_type", "bar")}
        标题: {request.parameters.get("title", "Chart")}
        样式选项: {request.parameters.get("styling_options", {})}
        """
        
        tool_result = await self.tool_agent.process_request(
            user_request=chart_request,
            context=request.parameters
        )
        
        return {
            "chart_generation_result": tool_result,
            "workflow": "chart_generation"
        }
    
    async def _execute_sql_testing_workflow(self, request: AgentRequest) -> Dict[str, Any]:
        """执行SQL测试验证流程"""
        
        params = request.parameters
        
        # 准备测试用例
        test_cases = []
        for tc_data in params.get("test_cases", []):
            test_case = TestCase(**tc_data)
            test_cases.append(test_case)
        
        # 执行SQL验证
        validation_result = await self.sql_validator.validate_sql(
            sql_query=params.get("sql_query", ""),
            data_source_context=params.get("data_source_context", {}),
            validation_level=ValidationLevel(params.get("validation_level", "standard")),
            test_cases=test_cases if test_cases else None
        )
        
        return {
            "validation_id": validation_result.validation_id,
            "status": validation_result.status.value,
            "errors": [
                {
                    "error_id": e.error_id,
                    "error_type": e.error_type,
                    "severity": e.severity.value,
                    "message": e.message,
                    "suggestion": e.suggestion
                } for e in validation_result.errors
            ],
            "warnings": [
                {
                    "error_id": w.error_id,
                    "message": w.message,
                    "suggestion": w.suggestion
                } for w in validation_result.warnings
            ],
            "corrected_sql": validation_result.corrected_sql,
            "correction_attempts": validation_result.correction_attempts,
            "execution_time_ms": validation_result.execution_time_ms,
            "confidence_score": 1.0 if validation_result.status.value == "passed" else 0.5,
            "workflow": "sql_testing"
        }
    
    async def _execute_multi_context_workflow(self, request: AgentRequest) -> Dict[str, Any]:
        """执行多上下文集成流程"""
        
        params = request.parameters
        
        # 添加上下文到集成器
        for ctx_data in params.get("contexts", []):
            self.context_integrator.add_context(
                context_id=ctx_data["context_id"],
                context_type=ContextType(ctx_data["context_type"]),
                content=ctx_data["content"],
                priority=ContextPriority(ctx_data.get("priority", "medium")),
                expiry_hours=ctx_data.get("expiry_hours"),
                dependencies=ctx_data.get("dependencies")
            )
        
        # 添加上下文关系
        for rel_data in params.get("relationships", []):
            self.context_integrator.add_relationship(**rel_data)
        
        # 执行上下文集成
        integration_result = await self.context_integrator.integrate_contexts(
            target_task=params.get("target_task", ""),
            required_context_types=[ContextType(t) for t in params.get("required_context_types", [])],
            custom_weights={ContextType(k): v for k, v in params.get("custom_weights", {}).items()}
        )
        
        return {
            "integration_id": integration_result.integration_id,
            "integrated_context": integration_result.integrated_context,
            "used_contexts": integration_result.used_contexts,
            "context_weights": integration_result.context_weights,
            "integration_confidence": integration_result.integration_confidence,
            "processing_time_seconds": integration_result.processing_time_seconds,
            "warnings": integration_result.warnings,
            "workflow": "multi_context_integration"
        }
    
    async def _execute_full_pipeline_workflow(self, request: AgentRequest) -> Dict[str, Any]:
        """执行完整流水线流程"""
        
        params = request.parameters
        pipeline_results = {}
        
        try:
            # 步骤1: 多上下文集成
            if params.get("enable_context_integration", True):
                logger.info("执行多上下文集成步骤")
                context_request = AgentRequest(
                    request_id=f"{request.request_id}_context",
                    workflow_type=WorkflowType.MULTI_CONTEXT_INTEGRATION,
                    parameters=params.get("context_integration_params", {})
                )
                context_result = await self._execute_multi_context_workflow(context_request)
                pipeline_results["context_integration"] = context_result
            
            # 步骤2: 任务补充机制
            if params.get("enable_task_supplement", True):
                logger.info("执行任务补充步骤")
                supplement_request = AgentRequest(
                    request_id=f"{request.request_id}_supplement",
                    workflow_type=WorkflowType.TASK_SUPPLEMENT,
                    parameters=params.get("task_supplement_params", {})
                )
                supplement_result = await self._execute_task_supplement_workflow(supplement_request)
                pipeline_results["task_supplement"] = supplement_result
            
            # 步骤3: 占位符→SQL转换
            if params.get("enable_placeholder_sql", True):
                logger.info("执行占位符→SQL转换步骤")
                sql_request = AgentRequest(
                    request_id=f"{request.request_id}_sql",
                    workflow_type=WorkflowType.PLACEHOLDER_TO_SQL,
                    parameters=params.get("placeholder_sql_params", {})
                )
                sql_result = await self._execute_placeholder_to_sql_workflow(sql_request)
                pipeline_results["placeholder_to_sql"] = sql_result
            
            # 步骤4: SQL测试验证
            if params.get("enable_sql_testing", True) and pipeline_results.get("placeholder_to_sql"):
                logger.info("执行SQL测试验证步骤")
                
                # 使用前一步的SQL结果
                sql_query = pipeline_results["placeholder_to_sql"].get("sql_query", "")
                if sql_query:
                    testing_params = params.get("sql_testing_params", {})
                    testing_params["sql_query"] = sql_query
                    
                    testing_request = AgentRequest(
                        request_id=f"{request.request_id}_testing",
                        workflow_type=WorkflowType.SQL_TESTING,
                        parameters=testing_params
                    )
                    testing_result = await self._execute_sql_testing_workflow(testing_request)
                    pipeline_results["sql_testing"] = testing_result
            
            # 步骤5: 图表生成
            if params.get("enable_chart_generation", True):
                logger.info("执行图表生成步骤")
                chart_request = AgentRequest(
                    request_id=f"{request.request_id}_chart",
                    workflow_type=WorkflowType.CHART_GENERATION,
                    parameters=params.get("chart_generation_params", {})
                )
                chart_result = await self._execute_chart_generation_workflow(chart_request)
                pipeline_results["chart_generation"] = chart_result
            
            # 计算总体置信度
            confidence_scores = []
            for step_result in pipeline_results.values():
                if isinstance(step_result, dict) and "confidence_score" in step_result:
                    confidence_scores.append(step_result["confidence_score"])
                elif isinstance(step_result, dict) and "integration_confidence" in step_result:
                    confidence_scores.append(step_result["integration_confidence"])
                elif isinstance(step_result, dict) and "overall_confidence" in step_result:
                    confidence_scores.append(step_result["overall_confidence"])
            
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
            
            return {
                "pipeline_results": pipeline_results,
                "steps_completed": len(pipeline_results),
                "overall_confidence": overall_confidence,
                "workflow": "full_pipeline"
            }
            
        except Exception as e:
            logger.error(f"完整流水线执行失败: {e}")
            return {
                "pipeline_results": pipeline_results,
                "steps_completed": len(pipeline_results),
                "overall_confidence": 0.0,
                "error": str(e),
                "workflow": "full_pipeline"
            }
    
    def get_execution_status(self, request_id: str) -> Optional[AgentResponse]:
        """获取执行状态"""
        # 检查正在运行的请求
        if request_id in self.running_requests:
            return self.running_requests[request_id]
        
        # 检查历史记录
        for response in self.execution_history:
            if response.request_id == request_id:
                return response
        
        return None
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """获取Agent统计信息"""
        
        # 执行统计
        total_requests = len(self.execution_history)
        successful_requests = sum(1 for r in self.execution_history if r.status == ExecutionStatus.COMPLETED)
        
        # 工作流类型统计
        workflow_counts = {}
        for response in self.execution_history:
            wf_type = response.workflow_type.value
            workflow_counts[wf_type] = workflow_counts.get(wf_type, 0) + 1
        
        # 性能统计
        execution_times = [r.execution_time_seconds for r in self.execution_history if r.execution_time_seconds > 0]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # 置信度统计
        confidence_scores = [r.confidence_score for r in self.execution_history if r.confidence_score > 0]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            "execution_statistics": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": successful_requests / max(total_requests, 1),
                "currently_running": len(self.running_requests)
            },
            "workflow_distribution": workflow_counts,
            "performance_metrics": {
                "average_execution_time": avg_execution_time,
                "average_confidence_score": avg_confidence
            },
            "sub_agent_statistics": {
                "placeholder_sql_agent": self.placeholder_sql_agent.get_conversion_statistics(),
                "task_supplement_agent": self.task_supplement_agent.get_supplement_statistics(),
                "sql_validator": self.sql_validator.get_validation_statistics(),
                "context_integrator": self.context_integrator.get_context_summary(),
                "model_selector": self.model_selector.get_selection_statistics()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.user_id,
            "sub_agents": {},
            "system_metrics": {}
        }
        
        try:
            # 检查各子Agent的健康状态
            # 这里可以添加具体的健康检查逻辑
            health_status["sub_agents"] = {
                "placeholder_sql_agent": "healthy",
                "task_supplement_agent": "healthy", 
                "sql_validator": "healthy",
                "context_integrator": "healthy",
                "tool_agent": "healthy"
            }
            
            # 系统指标
            health_status["system_metrics"] = {
                "running_requests": len(self.running_requests),
                "total_executions": len(self.execution_history),
                "context_count": len(self.context_integrator.contexts),
                "memory_usage": "normal"  # 可以添加实际内存监控
            }
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status


def create_autoreport_ai_agent(user_id: str) -> AutoReportAIAgent:
    """创建AutoReportAI Agent实例"""
    if not user_id:
        raise ValueError("user_id is required for AutoReportAIAgent")
    return AutoReportAIAgent(user_id)


# 便捷函数

async def process_placeholder_to_sql(
    user_id: str,
    placeholder_name: str,
    placeholder_description: str,
    task_context: Dict[str, Any],
    data_source_context: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """便捷的占位符→SQL转换函数"""
    
    agent = create_autoreport_ai_agent(user_id)
    
    request = AgentRequest(
        request_id=f"placeholder_sql_{uuid.uuid4().hex[:8]}",
        workflow_type=WorkflowType.PLACEHOLDER_TO_SQL,
        parameters={
            "placeholder_name": placeholder_name,
            "placeholder_description": placeholder_description,
            "task_context": task_context,
            "data_source_context": data_source_context,
            **kwargs
        }
    )
    
    response = await agent.execute_request(request)
    
    if response.status == ExecutionStatus.COMPLETED:
        return response.result
    else:
        raise Exception(f"处理失败: {response.error_message}")


async def supplement_placeholders(
    user_id: str,
    template_id: str,
    placeholders: List[Dict[str, Any]],
    task_context: Dict[str, Any],
    data_source_context: Dict[str, Any]
) -> Dict[str, Any]:
    """便捷的占位符补充函数"""
    
    agent = create_autoreport_ai_agent(user_id)
    
    request = AgentRequest(
        request_id=f"supplement_{uuid.uuid4().hex[:8]}",
        workflow_type=WorkflowType.TASK_SUPPLEMENT,
        parameters={
            "template_id": template_id,
            "placeholders": placeholders,
            "task_context": task_context,
            "data_source_context": data_source_context
        }
    )
    
    response = await agent.execute_request(request)
    
    if response.status == ExecutionStatus.COMPLETED:
        return response.result
    else:
        raise Exception(f"补充失败: {response.error_message}")


async def run_full_pipeline(
    user_id: str,
    pipeline_config: Dict[str, Any]
) -> Dict[str, Any]:
    """便捷的完整流水线执行函数"""
    
    agent = create_autoreport_ai_agent(user_id)
    
    request = AgentRequest(
        request_id=f"pipeline_{uuid.uuid4().hex[:8]}",
        workflow_type=WorkflowType.FULL_PIPELINE,
        parameters=pipeline_config
    )
    
    response = await agent.execute_request(request)
    
    if response.status == ExecutionStatus.COMPLETED:
        return response.result
    else:
        raise Exception(f"流水线执行失败: {response.error_message}")