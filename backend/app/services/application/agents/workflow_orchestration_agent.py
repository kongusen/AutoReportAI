"""
Application层工作流编排智能代理

符合DDD Application层的工作流编排代理，负责协调复杂的跨领域工作流：

核心职责：
1. 编排跨Domain层的复杂工作流
2. 协调多个Application服务的协作
3. 管理长期运行的业务流程
4. 处理工作流状态和生命周期

业务定位：
- Application层业务编排
- 调用Domain层服务和Infrastructure层AI
- 不包含具体技术实现细节
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowPriority(Enum):
    """工作流优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class WorkflowStep:
    """工作流步骤"""
    def __init__(self, 
                 step_id: str,
                 name: str,
                 service_name: str,
                 method_name: str,
                 input_params: Dict[str, Any] = None,
                 dependencies: List[str] = None,
                 timeout: int = 300):
        self.step_id = step_id
        self.name = name
        self.service_name = service_name
        self.method_name = method_name
        self.input_params = input_params or {}
        self.dependencies = dependencies or []
        self.timeout = timeout
        self.status = WorkflowStatus.PENDING
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None


class WorkflowContext:
    """工作流上下文"""
    def __init__(self, 
                 workflow_id: str,
                 name: str,
                 description: str = "",
                 priority: WorkflowPriority = WorkflowPriority.MEDIUM,
                 timeout: int = 3600):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.priority = priority
        self.timeout = timeout
        self.status = WorkflowStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.steps: Dict[str, WorkflowStep] = {}
        self.execution_context: Dict[str, Any] = {}
        self.error_count = 0
        self.retry_count = 0
        self.max_retries = 3


class WorkflowOrchestrationAgent:
    """
    Application层工作流编排智能代理
    
    核心职责：
    1. 管理复杂的跨领域业务工作流
    2. 协调Application服务和Domain服务
    3. 处理工作流的生命周期和状态管理
    4. 提供工作流监控和错误处理
    
    业务定位：
    - Application层业务协调
    - 调用Domain层和Infrastructure层服务
    - 不直接操作技术基础设施
    """
    
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for Workflow Orchestration Agent")
        self.user_id = user_id
        self.active_workflows: Dict[str, WorkflowContext] = {}
        self.completed_workflows: Dict[str, WorkflowContext] = {}
        self.workflow_templates: Dict[str, List[Dict]] = {}
        
        # 统计信息
        self.total_workflows_executed = 0
        self.successful_workflows = 0
        self.failed_workflows = 0
        
        # 注册默认工作流模板
        self._register_default_templates()
        
        logger.info("工作流编排智能代理初始化完成")
    
    def _register_default_templates(self):
        """注册默认工作流模板"""
        
        # 占位符处理工作流
        self.workflow_templates["placeholder_processing"] = [
            {
                "step_id": "context_analysis",
                "name": "上下文分析",
                "service_name": "context_aware_service",
                "method_name": "analyze_context",
                "dependencies": []
            },
            {
                "step_id": "ai_processing",
                "name": "AI处理",
                "service_name": "ai_execution_engine",
                "method_name": "execute_placeholder_task",
                "dependencies": ["context_analysis"]
            },
            {
                "step_id": "result_validation",
                "name": "结果验证",
                "service_name": "task_service",
                "method_name": "validate_result",
                "dependencies": ["ai_processing"]
            }
        ]
        
        # 报告生成工作流
        self.workflow_templates["report_generation"] = [
            {
                "step_id": "data_collection",
                "name": "数据收集",
                "service_name": "data_orchestrator",
                "method_name": "collect_data",
                "dependencies": []
            },
            {
                "step_id": "template_processing",
                "name": "模板处理",
                "service_name": "report_orchestrator", 
                "method_name": "process_template",
                "dependencies": ["data_collection"]
            },
            {
                "step_id": "report_compilation",
                "name": "报告编译",
                "service_name": "report_service",
                "method_name": "compile_report",
                "dependencies": ["template_processing"]
            }
        ]
        
        # 复杂数据分析工作流
        self.workflow_templates["complex_analysis"] = [
            {
                "step_id": "data_preparation",
                "name": "数据准备",
                "service_name": "data_orchestrator",
                "method_name": "prepare_data",
                "dependencies": []
            },
            {
                "step_id": "context_enhancement",
                "name": "上下文增强",
                "service_name": "context_aware_service",
                "method_name": "enhance_context",
                "dependencies": ["data_preparation"]
            },
            {
                "step_id": "ai_analysis",
                "name": "AI分析",
                "service_name": "ai_execution_engine",
                "method_name": "execute_ai_task",
                "dependencies": ["context_enhancement"]
            },
            {
                "step_id": "business_validation",
                "name": "业务验证",
                "service_name": "task_coordination_agent",
                "method_name": "validate_business_rules",
                "dependencies": ["ai_analysis"]
            }
        ]
    
    async def create_workflow_from_template(
        self,
        template_name: str,
        workflow_name: str,
        input_params: Dict[str, Any],
        workflow_id: str = None,
        priority: WorkflowPriority = WorkflowPriority.MEDIUM
    ) -> WorkflowContext:
        """
        从模板创建工作流
        
        Args:
            template_name: 模板名称
            workflow_name: 工作流名称
            input_params: 输入参数
            workflow_id: 工作流ID（可选）
            priority: 优先级
            
        Returns:
            工作流上下文
        """
        if template_name not in self.workflow_templates:
            raise ValueError(f"未找到工作流模板: {template_name}")
        
        if workflow_id is None:
            import uuid
            workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        # 创建工作流上下文
        workflow = WorkflowContext(
            workflow_id=workflow_id,
            name=workflow_name,
            description=f"基于模板 {template_name} 创建的工作流",
            priority=priority
        )
        
        workflow.execution_context.update(input_params)
        
        # 从模板创建步骤
        template_steps = self.workflow_templates[template_name]
        for step_config in template_steps:
            step = WorkflowStep(
                step_id=step_config["step_id"],
                name=step_config["name"],
                service_name=step_config["service_name"],
                method_name=step_config["method_name"],
                input_params=step_config.get("input_params", {}),
                dependencies=step_config.get("dependencies", []),
                timeout=step_config.get("timeout", 300)
            )
            workflow.steps[step.step_id] = step
        
        self.active_workflows[workflow_id] = workflow
        
        logger.info(f"从模板 {template_name} 创建工作流: {workflow_id}")
        
        return workflow
    
    async def create_custom_workflow(
        self,
        workflow_name: str,
        steps: List[Dict[str, Any]],
        input_params: Dict[str, Any],
        workflow_id: str = None,
        priority: WorkflowPriority = WorkflowPriority.MEDIUM
    ) -> WorkflowContext:
        """
        创建自定义工作流
        
        Args:
            workflow_name: 工作流名称
            steps: 步骤配置列表
            input_params: 输入参数
            workflow_id: 工作流ID（可选）
            priority: 优先级
            
        Returns:
            工作流上下文
        """
        if workflow_id is None:
            import uuid
            workflow_id = f"custom_workflow_{uuid.uuid4().hex[:8]}"
        
        workflow = WorkflowContext(
            workflow_id=workflow_id,
            name=workflow_name,
            description="自定义工作流",
            priority=priority
        )
        
        workflow.execution_context.update(input_params)
        
        # 创建步骤
        for step_config in steps:
            step = WorkflowStep(
                step_id=step_config["step_id"],
                name=step_config["name"],
                service_name=step_config["service_name"],
                method_name=step_config["method_name"],
                input_params=step_config.get("input_params", {}),
                dependencies=step_config.get("dependencies", []),
                timeout=step_config.get("timeout", 300)
            )
            workflow.steps[step.step_id] = step
        
        self.active_workflows[workflow_id] = workflow
        
        logger.info(f"创建自定义工作流: {workflow_id}")
        
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            执行结果
        """
        if workflow_id not in self.active_workflows:
            raise ValueError(f"未找到工作流: {workflow_id}")
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.utcnow()
        
        logger.info(f"开始执行工作流: {workflow_id}")
        
        try:
            # 执行工作流
            result = await self._execute_workflow_steps(workflow)
            
            # 更新状态
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            
            # 移到已完成列表
            self.completed_workflows[workflow_id] = workflow
            del self.active_workflows[workflow_id]
            
            # 更新统计
            self.total_workflows_executed += 1
            self.successful_workflows += 1
            
            logger.info(f"工作流执行完成: {workflow_id}")
            
            return {
                "workflow_id": workflow_id,
                "status": "success",
                "result": result,
                "execution_time": (workflow.completed_at - workflow.started_at).total_seconds(),
                "steps_executed": len([s for s in workflow.steps.values() if s.status == WorkflowStatus.COMPLETED])
            }
            
        except Exception as e:
            # 错误处理
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.utcnow()
            
            # 移到已完成列表
            self.completed_workflows[workflow_id] = workflow
            del self.active_workflows[workflow_id]
            
            # 更新统计
            self.total_workflows_executed += 1
            self.failed_workflows += 1
            
            logger.error(f"工作流执行失败: {workflow_id}, 错误: {e}")
            
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "execution_time": (workflow.completed_at - workflow.started_at).total_seconds() if workflow.completed_at else 0,
                "steps_executed": len([s for s in workflow.steps.values() if s.status == WorkflowStatus.COMPLETED])
            }
    
    async def _execute_workflow_steps(self, workflow: WorkflowContext) -> Dict[str, Any]:
        """执行工作流步骤"""
        executed_steps = set()
        results = {}
        
        # 按依赖关系执行步骤
        while len(executed_steps) < len(workflow.steps):
            # 查找可以执行的步骤
            executable_steps = []
            
            for step_id, step in workflow.steps.items():
                if step_id not in executed_steps and step.status == WorkflowStatus.PENDING:
                    # 检查依赖是否满足
                    dependencies_satisfied = all(
                        dep_id in executed_steps for dep_id in step.dependencies
                    )
                    if dependencies_satisfied:
                        executable_steps.append(step)
            
            if not executable_steps:
                # 检查是否有循环依赖或无法满足的依赖
                remaining_steps = [s for s in workflow.steps.values() if s.step_id not in executed_steps]
                if remaining_steps:
                    raise Exception(f"存在循环依赖或无法满足的依赖: {[s.step_id for s in remaining_steps]}")
                break
            
            # 并行执行可执行的步骤
            step_tasks = []
            for step in executable_steps:
                step_tasks.append(self._execute_single_step(step, workflow, results))
            
            # 等待步骤完成
            step_results = await asyncio.gather(*step_tasks, return_exceptions=True)
            
            # 处理步骤结果
            for step, step_result in zip(executable_steps, step_results):
                if isinstance(step_result, Exception):
                    step.status = WorkflowStatus.FAILED
                    step.error = str(step_result)
                    workflow.error_count += 1
                    
                    # 检查是否应该中止工作流
                    if workflow.error_count >= 3:  # 错误数量过多
                        raise Exception(f"工作流错误过多，中止执行: {step_result}")
                else:
                    step.status = WorkflowStatus.COMPLETED
                    step.result = step_result
                    results[step.step_id] = step_result
                    executed_steps.add(step.step_id)
                
                step.completed_at = datetime.utcnow()
        
        return results
    
    async def _execute_single_step(
        self, 
        step: WorkflowStep, 
        workflow: WorkflowContext,
        previous_results: Dict[str, Any]
    ) -> Any:
        """执行单个步骤"""
        step.status = WorkflowStatus.RUNNING
        step.started_at = datetime.utcnow()
        
        logger.debug(f"执行步骤: {step.step_id} ({step.name})")
        
        try:
            # 准备输入参数
            input_params = step.input_params.copy()
            input_params.update(workflow.execution_context)
            
            # 添加依赖步骤的结果
            for dep_id in step.dependencies:
                if dep_id in previous_results:
                    input_params[f"{dep_id}_result"] = previous_results[dep_id]
            
            # 调用服务（这里是模拟调用）
            result = await self._call_service(
                step.service_name,
                step.method_name,
                input_params
            )
            
            logger.debug(f"步骤执行成功: {step.step_id}")
            return result
            
        except Exception as e:
            logger.error(f"步骤执行失败: {step.step_id}, 错误: {e}")
            raise
    
    async def _call_service(
        self, 
        service_name: str, 
        method_name: str, 
        params: Dict[str, Any]
    ) -> Any:
        """调用真实服务"""
        try:
            logger.debug(f"调用服务: {service_name}.{method_name}")
            
            if service_name == "ai_execution_engine":
                from app.services.infrastructure.ai.service_orchestrator import get_service_orchestrator
                engine = get_service_orchestrator()
                
                if method_name == "execute_placeholder_task":
                    # 执行占位符处理任务
                    return await engine.execute_task(
                        task_context=params.get('task_context'),
                        execution_steps=params.get('execution_steps', [])
                    )
                elif method_name == "execute_ai_task":
                    # 执行AI任务
                    return await engine.execute_task(
                        task_context=params.get('task_context'),
                        execution_steps=params.get('execution_steps', [])
                    )
                    
            elif service_name == "context_aware_service":
                from app.services.application.services.context_aware_service import ContextAwareService
                service = ContextAwareService()
                
                if method_name == "analyze_context":
                    # 上下文分析
                    return await service.analyze_context(
                        content=params.get('content', ''),
                        user_context=params.get('user_context', {}),
                        business_requirements=params.get('business_requirements', {})
                    )
                elif method_name == "enhance_context":
                    # 上下文增强
                    return await service.enhance_context_with_intelligence(
                        base_context=params.get('base_context', {}),
                        enhancement_requirements=params.get('enhancement_requirements', {})
                    )
                    
            elif service_name == "task_service":
                from app.services.application.services.task_service import TaskService
                service = TaskService()
                
                if method_name == "validate_result":
                    # 结果验证
                    return await service.validate_task_result(
                        task_result=params.get('task_result'),
                        validation_criteria=params.get('validation_criteria', {})
                    )
                    
            elif service_name == "data_orchestrator":
                from app.services.data.processing.etl.etl_service import ETLService
                etl_service = ETLService(user_id=self.user_id)
                
                if method_name == "collect_data":
                    # 数据收集 - 确保数据源ID正确传递
                    data_source_id = params.get('data_source_id')
                    if not data_source_id and params.get('data_source_ids'):
                        # 从数据源ID列表中取第一个
                        data_source_id = params.get('data_source_ids')[0]
                    
                    logger.info(f"数据收集步骤: data_source_id={data_source_id}")
                    
                    return await etl_service.extract_data(
                        data_source_id=data_source_id,
                        query_config=params.get('query_config', {})
                    )
                elif method_name == "prepare_data":
                    # 数据准备
                    return await etl_service.transform_data(
                        raw_data=params.get('raw_data'),
                        transformation_config=params.get('transformation_config', {})
                    )
                    
            elif service_name == "report_orchestrator":
                from app.services.application.services.report_service import ReportApplicationService
                report_service = ReportApplicationService()
                
                if method_name == "process_template":
                    # 模板处理 - 使用报告状态查询方法
                    report_id = params.get('template_id')
                    if report_id:
                        result = await report_service.get_report_status(report_id)
                        return {
                            "success": True,
                            "data": result,
                            "message": "模板处理完成"
                        }
                    else:
                        return {
                            "success": False,
                            "error": "缺少template_id参数",
                            "message": "模板处理失败"
                        }
                    
            elif service_name == "report_service":
                from app.services.application.services.report_service import ReportApplicationService
                report_service = ReportApplicationService()
                
                if method_name == "compile_report":
                    # 报告编译 - 使用现有的报告生成方法
                    from app.services.application.services.report_service import ReportGenerationRequest
                    
                    # 构建报告生成请求
                    request = ReportGenerationRequest(
                        template_id=params.get('template_id', ''),
                        data_source_ids=params.get('data_source_ids', []),
                        user_id=self.user_id,
                        report_name=params.get('report_name'),
                        output_format=params.get('output_format', 'html'),
                        execution_context=params.get('execution_context', {})
                    )
                    
                    result = await report_service.generate_report(request)
                    return {
                        "success": result.success,
                        "data": {
                            "report_id": result.report_id,
                            "task_id": result.celery_task_id,
                            "status": result.status
                        },
                        "message": result.message or "报告编译完成",
                        "error": result.error
                    }
                    
            elif service_name == "task_coordination_agent":
                from app.services.application.agents.task_coordination_agent import TaskCoordinationAgent
                agent = TaskCoordinationAgent()
                
                if method_name == "validate_business_rules":
                    # 业务规则验证
                    return await agent.validate_business_rules(
                        analysis_result=params.get('analysis_result'),
                        business_context=params.get('business_context', {})
                    )
                    
            else:
                logger.warning(f"未知服务: {service_name}")
                return {
                    "error": f"Unknown service: {service_name}",
                    "service": service_name,
                    "method": method_name
                }
                
        except Exception as e:
            logger.error(f"服务调用失败: {service_name}.{method_name}, 错误: {e}")
            return {
                "error": str(e),
                "service": service_name,
                "method": method_name,
                "status": "failed"
            }
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """暂停工作流"""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = WorkflowStatus.PAUSED
        
        logger.info(f"暂停工作流: {workflow_id}")
        return True
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """恢复工作流"""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        if workflow.status == WorkflowStatus.PAUSED:
            workflow.status = WorkflowStatus.RUNNING
            logger.info(f"恢复工作流: {workflow_id}")
            return True
        
        return False
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流"""
        if workflow_id not in self.active_workflows:
            return False
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.utcnow()
        
        # 移到已完成列表
        self.completed_workflows[workflow_id] = workflow
        del self.active_workflows[workflow_id]
        
        logger.info(f"取消工作流: {workflow_id}")
        return True
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        workflow = None
        
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
        elif workflow_id in self.completed_workflows:
            workflow = self.completed_workflows[workflow_id]
        
        if not workflow:
            return None
        
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "priority": workflow.priority.value,
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "total_steps": len(workflow.steps),
            "completed_steps": len([s for s in workflow.steps.values() if s.status == WorkflowStatus.COMPLETED]),
            "failed_steps": len([s for s in workflow.steps.values() if s.status == WorkflowStatus.FAILED]),
            "error_count": workflow.error_count,
            "retry_count": workflow.retry_count
        }
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """获取代理统计信息"""
        return {
            "agent_name": "WorkflowOrchestrationAgent",
            "version": "1.0.0-ddd",
            "architecture": "DDD Application Layer",
            "active_workflows": len(self.active_workflows),
            "completed_workflows": len(self.completed_workflows),
            "total_workflows_executed": self.total_workflows_executed,
            "successful_workflows": self.successful_workflows,
            "failed_workflows": self.failed_workflows,
            "success_rate": self.successful_workflows / max(self.total_workflows_executed, 1),
            "available_templates": list(self.workflow_templates.keys()),
            "template_count": len(self.workflow_templates)
        }
    
    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """列出活跃工作流"""
        return [
            self.get_workflow_status(workflow_id)
            for workflow_id in self.active_workflows.keys()
        ]
    
    def list_workflow_templates(self) -> List[Dict[str, Any]]:
        """列出工作流模板"""
        templates = []
        for name, steps in self.workflow_templates.items():
            templates.append({
                "template_name": name,
                "step_count": len(steps),
                "steps": [
                    {
                        "step_id": step["step_id"],
                        "name": step["name"],
                        "service": step["service_name"],
                        "dependencies": step.get("dependencies", [])
                    }
                    for step in steps
                ]
            })
        return templates
    
    async def orchestrate_report_generation(
        self,
        template_id: str,
        data_source_ids: List[str],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        编排报告生成工作流
        
        Args:
            template_id: 模板ID
            data_source_ids: 数据源ID列表
            execution_context: 执行上下文
            
        Returns:
            工作流执行结果
        """
        try:
            logger.info(f"开始编排报告生成工作流: template_id={template_id}")
            
            # 创建报告生成工作流
            workflow_name = f"Report_Generation_{template_id[:8]}"
            input_params = {
                'template_id': template_id,
                'data_source_ids': data_source_ids,
                'execution_context': execution_context,
                'user_id': self.user_id,
                'optimization_level': execution_context.get('optimization_level', 'enhanced'),
                'force_reanalyze': execution_context.get('force_reanalyze', False)
            }
            
            # 使用报告生成工作流模板
            workflow = await self.create_workflow_from_template(
                template_name="report_generation",
                workflow_name=workflow_name,
                input_params=input_params,
                priority=WorkflowPriority.HIGH
            )
            
            # 执行工作流
            result = await self.execute_workflow(workflow.workflow_id)
            
            if result.get('status') == 'success':
                # 解析模板占位符作为报告生成的一部分
                placeholder_analysis = await self._analyze_template_placeholders(
                    template_id, data_source_ids[0] if data_source_ids else None
                )
                
                return {
                    'success': True,
                    'results': {
                        'workflow_result': result.get('result', {}),
                        'placeholder_analysis': placeholder_analysis,
                        'template_id': template_id,
                        'data_source_ids': data_source_ids,
                        'execution_time': result.get('execution_time', 0)
                    },
                    'workflow_id': workflow.workflow_id
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'workflow_id': workflow.workflow_id
                }
                
        except Exception as e:
            logger.error(f"报告生成工作流编排失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _analyze_template_placeholders(
        self, 
        template_id: str, 
        data_source_id: str = None
    ) -> Dict[str, Any]:
        """分析模板占位符"""
        try:
            from app.services.domain.template.services.template_domain_service import TemplateParser
            from app.crud import template as crud_template
            from app.db.session import SessionLocal
            
            # 获取模板内容
            db = SessionLocal()
            try:
                template = crud_template.get(db, id=template_id)
                if not template:
                    raise ValueError(f"模板不存在: {template_id}")
                
                template_content = template.content or ""
            finally:
                db.close()
            
            # 解析模板结构
            parser = TemplateParser()
            structure = parser.parse_template_structure(template_content)
            
            return {
                'template_id': template_id,
                'data_source_id': data_source_id,
                'placeholders_found': len(structure.get('placeholders', [])),
                'placeholders': structure.get('placeholders', []),
                'sections': structure.get('sections', []),
                'variables': structure.get('variables', {}),
                'complexity_score': structure.get('complexity_score', 0),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"模板占位符分析失败: {e}")
            return {
                'template_id': template_id,
                'data_source_id': data_source_id,
                'error': str(e),
                'placeholders_found': 0,
                'placeholders': []
            }