"""
Application层 - 任务应用服务 - DDD架构v2.0

基于新DDD架构的任务应用服务，集成TaskExecutionService和Agents系统
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from app.models.task import Task, TaskExecution, TaskStatus, ReportPeriod, ProcessingMode, AgentWorkflowType
from app.models.user import User
from app.models.data_source import DataSource  
from app.models.template import Template
from app.services.application.base_application_service import (
    TransactionalApplicationService, 
    ApplicationResult, 
    PaginationRequest, 
    PaginationResult
)
from app.services.application.tasks.task_execution_service import TaskExecutionService
# Use lazy loading for domain services to avoid circular imports
# Temporarily removed to fix circular imports
# from app.services.infrastructure.task_queue.tasks import validate_placeholders_task, scheduled_task_runner
from app.services.infrastructure.task_queue.celery_config import celery_app
from app.services.infrastructure.task_queue.tasks import execute_report_task
from app.core.exceptions import ValidationError, NotFoundError
from app.utils.time_context import TimeContextManager

logger = logging.getLogger(__name__)

class TaskApplicationService(TransactionalApplicationService):
    """任务应用服务 - DDD架构v2.0版本，集成新的执行能力"""
    
    def __init__(self):
        super().__init__("TaskApplicationService")
        self.task_execution_service = TaskExecutionService()
        self.time_context_manager = TimeContextManager()
        
        # Lazy-loaded domain services to avoid circular imports
        self._task_execution_domain_service = None
        self._placeholder_analysis_domain_service = None
    
    @property
    def task_execution_domain_service(self):
        """Lazy load task execution domain service"""
        if self._task_execution_domain_service is None:
            from app.services.domain.tasks.services.task_execution_domain_service import TaskExecutionDomainService
            self._task_execution_domain_service = TaskExecutionDomainService()
        return self._task_execution_domain_service
    
    @property
    def placeholder_analysis_domain_service(self):
        """Lazy load placeholder analysis domain service"""
        if self._placeholder_analysis_domain_service is None:
            from app.services.domain.placeholder.services.placeholder_analysis_domain_service import PlaceholderAnalysisDomainService
            self._placeholder_analysis_domain_service = PlaceholderAnalysisDomainService()
        return self._placeholder_analysis_domain_service
    
    def create_task(
        self,
        db: Session,
        user_id: str,
        name: str,
        template_id: str,
        data_source_id: str,
        description: Optional[str] = None,
        schedule: Optional[str] = None,
        recipients: Optional[List[str]] = None,
        is_active: bool = True,
        processing_mode: ProcessingMode = ProcessingMode.INTELLIGENT,
        workflow_type: AgentWorkflowType = AgentWorkflowType.SIMPLE_REPORT,
        max_context_tokens: int = 32000,
        enable_compression: bool = True
    ) -> ApplicationResult[Task]:
        """
        创建新任务

        Args:
            db: 数据库会话
            user_id: 用户ID
            name: 任务名称
            template_id: 模板ID
            data_source_id: 数据源ID
            description: 任务描述
            schedule: 调度表达式
            recipients: 通知邮箱列表
            is_active: 是否启用
            processing_mode: 处理模式
            workflow_type: Agent工作流类型
            max_context_tokens: 最大上下文令牌数
            enable_compression: 是否启用压缩

        Returns:
            ApplicationResult[Task]: 创建结果
        """
        # 验证必需参数
        validation_result = self.validate_required_params(
            user_id=user_id,
            name=name,
            template_id=template_id,
            data_source_id=data_source_id
        )
        if not validation_result.success:
            return validation_result
        
        def _create_task_internal():
            # 验证用户存在
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return ApplicationResult.not_found_result(f"用户 {user_id} 不存在")
            
            # 验证模板存在
            template = db.query(Template).filter(Template.id == template_id).first()
            if not template:
                return ApplicationResult.not_found_result(f"模板 {template_id} 不存在")
                
            # 验证数据源存在
            data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
            if not data_source:
                return ApplicationResult.not_found_result(f"数据源 {data_source_id} 不存在")
            
            # 基于调度表达式推断报告周期
            final_report_period = self._infer_report_period_from_cron(schedule)

            # 验证调度表达式（如果提供）
            if schedule:
                try:
                    from croniter import croniter
                    if not croniter.is_valid(schedule):
                        return ApplicationResult.validation_error_result(
                            f"无效的Cron表达式: {schedule}",
                            ["调度表达式格式不正确"]
                        )
                except ImportError:
                    self.logger.warning("croniter模块不可用，跳过cron验证")
            
            # 创建任务 - 确保 UUID 字段使用正确的类型
            from uuid import UUID as UUIDType

            # 转换UUID并记录调试信息
            owner_uuid = UUIDType(user_id) if isinstance(user_id, str) else user_id
            template_uuid = UUIDType(template_id) if isinstance(template_id, str) else template_id
            data_source_uuid = UUIDType(data_source_id) if isinstance(data_source_id, str) else data_source_id

            self.logger.info(f"创建任务，UUID转换: owner_id={owner_uuid}, template_id={template_uuid}, data_source_id={data_source_uuid}")

            task = Task(
                name=name,
                description=description,
                owner_id=owner_uuid,
                template_id=template_uuid,
                data_source_id=data_source_uuid,
                report_period=final_report_period,
                schedule=schedule,
                recipients=recipients or [],
                is_active=is_active,
                status=TaskStatus.PENDING,
                processing_mode=processing_mode,
                workflow_type=workflow_type,
                max_context_tokens=max_context_tokens,
                enable_compression=enable_compression
            )
            
            db.add(task)
            db.flush()  # 将挂起的更改刷新到数据库，但不提交事务
            db.refresh(task)  # 现在可以安全地刷新对象
            
            # 异步验证模板占位符（可选）
            if is_active:
                try:
                    # 延迟导入以避免循环导入
                    from app.services.infrastructure.task_queue.tasks import validate_placeholders_task

                    validate_placeholders_task.delay(
                        template_id=template_id,
                        data_source_id=data_source_id,
                        user_id=user_id
                    )
                    self.logger.info(f"占位符验证任务已排队，任务ID: {task.id}")
                except ImportError as e:
                    self.logger.warning(f"无法导入占位符验证任务，跳过异步验证，任务ID: {task.id}, 错误: {e}")
                except Exception as e:
                    self.logger.warning(f"排队占位符验证失败，任务ID: {task.id}, 错误: {e}")
            
            return ApplicationResult.success_result(
                data=task,
                message=f"任务 '{name}' 创建成功"
            )
        
        return self.execute_in_transaction(db, "create_task", _create_task_internal)
    
    async def analyze_task_with_domain_services(
        self,
        db: Session,
        task_id: int,
        user_id: str
    ) -> ApplicationResult[Dict[str, Any]]:
        """
        使用领域服务分析任务 - 展示正确的DDD架构使用agents的方式
        
        业务逻辑流程：
        1. 应用服务编排业务流程
        2. 领域服务执行纯业务逻辑
        3. 基础设施层agents执行技术实现
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            ApplicationResult[Dict]: 分析结果
        """
        async def _analyze_task_internal():
            # 1. 获取任务信息
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                return ApplicationResult.not_found_result(f"任务 {task_id} 不存在或无权限")
            
            # 2. 构建任务定义 - 应用层组装数据
            task_definition = {
                "task_id": task.id,
                "name": task.name,
                "description": task.description,
                "template_id": str(task.template_id),
                "data_source_ids": [str(task.data_source_id)],
                "processing_mode": task.processing_mode.value if task.processing_mode else "simple",
                "workflow_type": task.workflow_type.value if task.workflow_type else "simple_report",
                "template_info": self._get_template_info(db, task.template_id),
                "data_source_info": self._get_data_source_info(db, task.data_source_id)
            }
            
            # 3. 使用领域服务分析任务执行需求 - 纯业务逻辑
            execution_context = {
                "user_id": user_id,
                "current_time": datetime.now(),
                "environment": "development"  # 这里可以从配置获取
            }
            
            execution_requirements = self.task_execution_domain_service.analyze_task_execution_requirements(
                task_definition, execution_context
            )
            
            # 4. 验证执行可行性 - 纯业务逻辑
            available_resources = {
                "cpu_cores": 4,
                "memory_mb": 8192,
                "storage_mb": 10240,
                "network_bandwidth": "high"
            }
            
            feasibility_check = self.task_execution_domain_service.validate_task_execution_feasibility(
                task_definition, available_resources, execution_context
            )
            
            # 5. 分析占位符需求 - 纯业务逻辑
            placeholder_analysis = None
            if task_definition["processing_mode"] == "intelligent":
                business_context = {
                    "template_type": task_definition.get("template_info", {}).get("type", "general"),
                    "data_scope": task_definition.get("data_source_info", {}).get("scope", "full"),
                    "execution_urgency": "normal"
                }
                
                placeholder_analysis = await self.placeholder_analysis_domain_service.analyze_placeholder_business_requirements(
                    f"分析任务 {task.name} 的占位符需求",
                    business_context
                )
            
            # 6. 构建分析结果
            analysis_result = {
                "task_info": {
                    "id": task.id,
                    "name": task.name,
                    "status": task.status.value if task.status else "unknown"
                },
                "execution_requirements": execution_requirements,
                "feasibility_check": feasibility_check,
                "placeholder_analysis": placeholder_analysis,
                "recommendations": self._generate_task_recommendations(
                    execution_requirements, feasibility_check, placeholder_analysis
                ),
                "estimated_agents_needed": self._estimate_agents_needed(task_definition, execution_requirements)
            }
            
            return ApplicationResult.success_result(
                data=analysis_result,
                message=f"任务 {task.name} 分析完成"
            )
        
        return await self.handle_domain_exceptions_async("analyze_task_with_domain_services", _analyze_task_internal)
    
    def execute_task_through_agents(
        self,
        db: Session,
        task_id: int,
        user_id: str,
        execution_plan: Optional[Dict[str, Any]] = None
    ) -> ApplicationResult[Dict[str, Any]]:
        """
        通过agents执行任务 - 展示正确的基础设施层agents使用方式
        
        架构层次：
        1. 应用服务(此方法) - 编排业务流程
        2. 领域服务 - 执行业务逻辑和规则
        3. 基础设施层agents - 执行技术实现
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            execution_plan: 执行计划(可选)
            
        Returns:
            ApplicationResult[Dict]: 执行结果
        """
        def _execute_task_internal():
            # 1. 获取任务并验证权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                return ApplicationResult.not_found_result(f"任务 {task_id} 不存在或无权限")
            
            # 2. 使用领域服务创建执行计划
            if not execution_plan:
                task_definition = self._build_task_definition(db, task)
                execution_requirements = self.task_execution_domain_service.analyze_task_execution_requirements(
                    task_definition, {"user_id": user_id}
                )
                
                execution_plan = self.task_execution_domain_service.create_task_execution_plan(
                    task_definition, execution_requirements, {"timeout": 300}
                )
            
            # 3. 调用基础设施层agents执行技术实现
            # 注意：这里应该通过基础设施层的agent provider来调用agents
            try:
                from app.services.infrastructure.agents.agent_provider import get_agent_provider
                
                agent_provider = get_agent_provider()
                
                # 执行各个步骤，每个步骤使用对应的agent
                execution_results = []
                for step in execution_plan.get("execution_steps", []):
                    step_result = self._execute_step_with_agents(
                        agent_provider, step, task, execution_plan
                    )
                    execution_results.append(step_result)
                    
                    # 如果步骤失败，根据回滚策略处理
                    if not step_result.get("success", False):
                        rollback_result = self._handle_step_failure(
                            agent_provider, step, execution_plan, execution_results
                        )
                        if rollback_result.get("should_abort", False):
                            break
                
                # 4. 汇总执行结果
                overall_success = all(result.get("success", False) for result in execution_results)
                
                final_result = {
                    "task_id": task_id,
                    "execution_plan_id": execution_plan.get("plan_id"),
                    "overall_success": overall_success,
                    "step_results": execution_results,
                    "execution_summary": {
                        "total_steps": len(execution_results),
                        "successful_steps": sum(1 for r in execution_results if r.get("success", False)),
                        "failed_steps": sum(1 for r in execution_results if not r.get("success", False))
                    },
                    "agents_used": list(set(
                        agent for result in execution_results 
                        for agent in result.get("agents_used", [])
                    ))
                }
                
                return ApplicationResult.success_result(
                    data=final_result,
                    message=f"任务执行完成，成功率: {final_result['execution_summary']['successful_steps']}/{final_result['execution_summary']['total_steps']}"
                )
                
            except ImportError:
                # 如果agents不可用，降级到传统执行方式
                self.logger.warning("基础设施层agents不可用，使用传统执行方式")
                return self._execute_task_traditional_way(db, task, user_id)
        
        return self.handle_domain_exceptions("execute_task_through_agents", _execute_task_internal)
    
    def execute_task_immediately(
        self, 
        db: Session, 
        task_id: int,
        user_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        立即执行任务
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 执行用户ID
            execution_context: 执行上下文
            
        Returns:
            Dict: 执行结果信息
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            if not task.is_active:
                raise ValidationError(f"Task {task_id} is not active")
            
            # 检查是否有正在进行的执行
            ongoing_execution = db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id,
                TaskExecution.execution_status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
            ).first()
            
            if ongoing_execution:
                return {
                    "status": "already_running",
                    "message": f"Task {task_id} is already being executed",
                    "execution_id": str(ongoing_execution.execution_id)
                }
            
            # 构建执行上下文
            context = execution_context or {}
            context.update({
                "trigger": "manual",
                "triggered_by": user_id,
                "triggered_at": datetime.utcnow().isoformat()
            })
            
            # 提交Celery任务
            celery_result = execute_report_task.delay(task_id, context)
            
            logger.info(f"Task {task_id} execution queued with Celery task ID: {celery_result.id}")
            
            return {
                "status": "queued",
                "message": f"Task {task_id} has been queued for execution",
                "celery_task_id": celery_result.id,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error(f"Failed to execute task {task_id}: {str(e)}")
            raise
    
    def get_task_status(
        self, 
        db: Session, 
        task_id: int, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取任务执行状态
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Dict: 任务状态信息
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 获取最新的执行记录
            latest_execution = db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id
            ).order_by(TaskExecution.created_at.desc()).first()
            
            if not latest_execution:
                return {
                    "task_id": task_id,
                    "status": task.status.value,
                    "message": "No executions found",
                    "progress": 0
                }
            
            # 获取Celery任务状态（如果存在）
            celery_status = None
            celery_info = {}
            if latest_execution.celery_task_id:
                try:
                    celery_result = AsyncResult(latest_execution.celery_task_id, app=celery_app)
                    celery_status = celery_result.status
                    if celery_result.info:
                        celery_info = celery_result.info
                except Exception as e:
                    logger.warning(f"Failed to get Celery status for task {latest_execution.celery_task_id}: {e}")
            
            # 确保所有字段都可以序列化
            def safe_serialize(value):
                """安全序列化，避免TypeError"""
                if value is None:
                    return None
                if isinstance(value, (str, int, float, bool)):
                    return value
                if isinstance(value, dict):
                    return {k: safe_serialize(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [safe_serialize(item) for item in value]
                try:
                    return str(value)
                except Exception:
                    return None

            return {
                "task_id": task_id,
                "execution_id": str(latest_execution.execution_id) if latest_execution.execution_id else None,
                "status": latest_execution.execution_status.value if latest_execution.execution_status else "unknown",
                "progress": latest_execution.progress_percentage or 0,
                "current_step": latest_execution.current_step or "",
                "started_at": latest_execution.started_at.isoformat() if latest_execution.started_at else None,
                "completed_at": latest_execution.completed_at.isoformat() if latest_execution.completed_at else None,
                "duration": latest_execution.total_duration or 0,
                "error_details": safe_serialize(latest_execution.error_details),
                "celery_status": celery_status,
                "celery_info": safe_serialize(celery_info),
                "execution_result": safe_serialize(latest_execution.execution_result)
            }
            
        except Exception as e:
            logger.error(f"Failed to get task status for task {task_id}: {str(e)}")
            raise
    
    def get_task_executions(
        self,
        db: Session,
        task_id: int,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取任务执行历史
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            limit: 返回记录数量限制
            
        Returns:
            List[Dict]: 执行历史列表
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 获取执行历史
            executions = db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id
            ).order_by(TaskExecution.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "execution_id": str(execution.execution_id),
                    "status": execution.execution_status.value,
                    "progress": execution.progress_percentage,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "duration": execution.total_duration,
                    "error_details": execution.error_details,
                    "current_step": execution.current_step,
                    "workflow_type": execution.workflow_type.value if execution.workflow_type else None,
                    "created_at": execution.created_at.isoformat()
                }
                for execution in executions
            ]
            
        except Exception as e:
            logger.error(f"Failed to get task executions for task {task_id}: {str(e)}")
            raise
    
    def update_task(
        self,
        db: Session,
        task_id: int,
        user_id: str,
        **update_data
    ) -> Task:
        """
        更新任务（带完整验证）

        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            **update_data: 更新数据

        Returns:
            Task: 更新后的任务对象
        """
        try:
            # 1. 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")

            # 2. 字段白名单
            allowed_fields = {
                'name', 'description', 'schedule', 'report_period',
                'recipients', 'is_active', 'processing_mode', 'workflow_type',
                'max_context_tokens', 'enable_compression'
            }

            # 3. 验证和应用更新
            validated_updates = {}
            scheduler_needs_update = False

            for field, value in update_data.items():
                if field not in allowed_fields:
                    logger.warning(f"❌ 字段 {field} 不允许更新")
                    continue

                # === 字段特定验证 ===

                # 3.1 验证任务名称
                if field == 'name':
                    if not value or not isinstance(value, str):
                        raise ValidationError("任务名称不能为空")
                    if len(value) > 200:
                        raise ValidationError("任务名称不能超过200个字符")
                    # 检查同名任务
                    existing = db.query(Task).filter(
                        Task.owner_id == user_id,
                        Task.name == value,
                        Task.id != task_id
                    ).first()
                    if existing:
                        raise ValidationError(f"任务名称 '{value}' 已存在")
                    validated_updates[field] = value

                # 3.2 验证 Cron 表达式
                elif field == 'schedule':
                    if value is not None:
                        try:
                            from croniter import croniter
                            if not croniter.is_valid(value):
                                raise ValidationError(f"无效的Cron表达式: {value}")
                            # 验证表达式格式
                            if len(value.split()) != 5:
                                raise ValidationError("Cron表达式必须包含5个字段 (分 时 日 月 周)")
                        except ImportError:
                            logger.warning("croniter 不可用，跳过 cron 验证")

                        # 推断报告周期
                        inferred_period = self._infer_report_period_from_cron(value)
                        validated_updates['report_period'] = inferred_period
                        scheduler_needs_update = True
                        logger.info(f"🔄 根据 cron 表达式推断报告周期: {inferred_period.value}")

                    validated_updates[field] = value

                # 3.3 验证收件人列表
                elif field == 'recipients':
                    if value is not None:
                        if not isinstance(value, list):
                            raise ValidationError("recipients 必须是列表")
                        # 验证邮箱格式
                        import re
                        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                        for email in value:
                            if not re.match(email_pattern, email):
                                raise ValidationError(f"无效的邮箱地址: {email}")
                    validated_updates[field] = value

                # 3.4 验证处理模式
                elif field == 'processing_mode':
                    if value not in [mode.value for mode in ProcessingMode]:
                        raise ValidationError(f"无效的处理模式: {value}，可选值: {[m.value for m in ProcessingMode]}")
                    # 转换为枚举
                    validated_updates[field] = ProcessingMode(value)

                # 3.5 验证工作流类型
                elif field == 'workflow_type':
                    if value not in [wf.value for wf in AgentWorkflowType]:
                        raise ValidationError(f"无效的工作流类型: {value}，可选值: {[w.value for w in AgentWorkflowType]}")
                    validated_updates[field] = AgentWorkflowType(value)

                # 3.6 验证报告周期
                elif field == 'report_period':
                    if value not in [period.value for period in ReportPeriod]:
                        raise ValidationError(f"无效的报告周期: {value}，可选值: {[p.value for p in ReportPeriod]}")
                    validated_updates[field] = ReportPeriod(value)

                # 3.7 验证上下文令牌数
                elif field == 'max_context_tokens':
                    if not isinstance(value, int) or value < 1000 or value > 128000:
                        raise ValidationError("max_context_tokens 必须在 1000-128000 之间")
                    validated_updates[field] = value

                # 3.8 验证布尔值字段
                elif field in ('is_active', 'enable_compression'):
                    if not isinstance(value, bool):
                        raise ValidationError(f"{field} 必须是布尔值")
                    validated_updates[field] = value

                    # is_active 变更需要更新调度器
                    if field == 'is_active':
                        scheduler_needs_update = True

                # 其他字段直接应用
                else:
                    validated_updates[field] = value

            # 4. 应用验证后的更新
            for field, value in validated_updates.items():
                setattr(task, field, value)

            task.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(task)

            # 5. 同步调度器（如果需要）
            if scheduler_needs_update:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._sync_task_to_scheduler(task))
                    else:
                        loop.run_until_complete(self._sync_task_to_scheduler(task))
                except RuntimeError:
                    # 如果没有事件循环，创建一个新的
                    asyncio.run(self._sync_task_to_scheduler(task))

            logger.info(f"✅ 任务 {task_id} 更新成功，更新了 {len(validated_updates)} 个字段")
            return task

        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"❌ 更新任务 {task_id} 失败: {str(e)}")
            db.rollback()
            raise

    async def _sync_task_to_scheduler(self, task: Task):
        """同步任务到调度器"""
        try:
            from app.core.unified_scheduler import get_scheduler
            scheduler = await get_scheduler()

            if task.is_active and task.schedule:
                # 添加或更新调度
                await scheduler.add_or_update_task(task.id, task.schedule)
                logger.info(f"✅ 任务 {task.id} 已同步到调度器")
            elif not task.is_active:
                # 从调度器移除
                await scheduler.remove_task(task.id)
                logger.info(f"✅ 任务 {task.id} 已从调度器移除")
        except Exception as e:
            logger.error(f"⚠️ 同步任务 {task.id} 到调度器失败: {e}")
    
    def delete_task(
        self,
        db: Session,
        task_id: int,
        user_id: str
    ) -> bool:
        """
        删除任务
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 取消正在进行的执行
            ongoing_executions = db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id,
                TaskExecution.execution_status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
            ).all()
            
            for execution in ongoing_executions:
                if execution.celery_task_id:
                    try:
                        celery_app.control.revoke(execution.celery_task_id, terminate=True)
                        logger.info(f"Revoked Celery task {execution.celery_task_id}")
                    except Exception as e:
                        logger.warning(f"Failed to revoke Celery task {execution.celery_task_id}: {e}")
                
                execution.execution_status = TaskStatus.CANCELLED
                execution.completed_at = datetime.utcnow()
            
            # 删除任务（级联删除执行记录）
            db.delete(task)
            db.commit()
            
            logger.info(f"Task {task_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {str(e)}")
            db.rollback()
            raise
    
    def schedule_task(
        self,
        db: Session,
        task_id: int,
        schedule: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        设置任务调度
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            schedule: Cron表达式
            user_id: 用户ID
            
        Returns:
            Dict: 调度结果
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 验证Cron表达式
            try:
                from croniter import croniter
                if not croniter.is_valid(schedule):
                    raise ValidationError(f"Invalid cron expression: {schedule}")
            except ImportError:
                logger.warning("croniter not available, skipping cron validation")
            
            # 更新调度
            task.schedule = schedule
            task.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Task {task_id} schedule updated to: {schedule}")
            
            return {
                "task_id": task_id,
                "schedule": schedule,
                "status": "scheduled",
                "message": "Task schedule updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule task {task_id}: {str(e)}")
            db.rollback()
            raise
    
    def validate_task_configuration(
        self,
        db: Session,
        task_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        验证任务配置（包括占位符）
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Dict: 验证结果
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 异步验证占位符
            try:
                from app.services.infrastructure.task_queue.tasks import validate_placeholders_task
                validation_result = validate_placeholders_task.delay(
                    template_id=str(task.template_id),
                    data_source_id=str(task.data_source_id),
                    user_id=user_id
                )
            except ImportError as e:
                logger.warning(f"Cannot import validate_placeholders_task: {e}")
                return {
                    "task_id": task_id,
                    "status": "validation_unavailable",
                    "message": "Validation service is temporarily unavailable"
                }
            
            logger.info(f"Validation task queued for task {task_id}: {validation_result.id}")
            
            return {
                "task_id": task_id,
                "validation_task_id": validation_result.id,
                "status": "validation_queued",
                "message": "Task validation has been queued"
            }
            
        except Exception as e:
            logger.error(f"Failed to validate task {task_id}: {str(e)}")
            raise

    async def execute_task_with_claude_code(
        self,
        db: Session,
        task_id: int,
        user_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用新的Claude Code架构执行任务
        
        Args:
            db: 数据库会话
            task_id: 任务ID
            user_id: 用户ID
            execution_context: 执行上下文
            
        Returns:
            Dict: 执行结果
        """
        try:
            # 验证任务存在和权限
            task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
            if not task:
                raise NotFoundError(f"Task {task_id} not found or access denied")
            
            # 获取任务相关信息
            template = db.query(Template).filter(Template.id == task.template_id).first()
            data_source = db.query(DataSource).filter(DataSource.id == task.data_source_id).first()
            
            if not template or not data_source:
                raise NotFoundError("Template or DataSource not found")
            
            # 使用新的agents系统
            from app.api.utils.agent_context_helpers import create_task_execution_context
            
            # 准备任务数据
            task_data = {
                "task_id": task_id,
                "task_name": task.name,
                "template_id": str(task.template_id),
                "data_source_id": str(task.data_source_id),
                "report_period": task.report_period.value,
                "processing_mode": task.processing_mode.value,
                "workflow_type": task.workflow_type.value,
                "template_info": {
                    "name": template.name if hasattr(template, 'name') else 'Unknown Template',
                    "content": template.content if hasattr(template, 'content') else "",
                    "type": getattr(template, 'template_type', 'report')
                },
                "data_source_config": {
                    "name": data_source.name,
                    "source_type": str(data_source.source_type),
                    "database": getattr(data_source, 'doris_database', 'unknown')
                }
            }
            
            execution_options = {
                "processing_mode": task.processing_mode.value,
                "max_tokens": getattr(task, 'max_context_tokens', 32000),
                "enable_compression": getattr(task, 'enable_compression', True)
            }
            
            # 创建任务执行上下文
            context = create_task_execution_context(
                task_name=task.name,
                task_description=f"执行任务: {task.name} - {task.workflow_type.value}报告生成",
                task_data=task_data,
                execution_options=execution_options
            )
            
            # 执行agents任务
            try:
                from app.services.infrastructure.agents import execute_agent_task
                agent_result = await execute_agent_task(
                    task_name="task_execution",
                    task_description=f"执行任务: {task.name} - {task.workflow_type.value}报告生成",
                    context_data=context,
                    additional_data={
                        "task_id": task_id,
                        "task_name": task.name,
                        "template_id": str(task.template_id),
                        "data_source_id": str(task.data_source_id),
                        "data_source_config": {
                            "name": data_source.name,
                            "source_type": str(data_source.source_type)
                        },
                        "report_period": task.report_period.value,
                        "processing_mode": task.processing_mode.value,
                        "workflow_type": task.workflow_type.value,
                        "execution_context": execution_context or {}
                    }
                )
            except ImportError as e:
                logger.warning(f"Cannot import execute_agent_task: {e}")
                agent_result = {
                    "status": "fallback_execution",
                    "message": "Agents system unavailable, using fallback execution",
                    "success": True
                }
            
            logger.info(f"Agents system task execution completed for task {task_id}")
            
            return {
                "task_id": task_id,
                "execution_id": f"task_{task_id}_{datetime.now().timestamp()}",
                "status": "completed",
                "results": agent_result,
                "architecture": "agents_v2"
            }
            
        except Exception as e:
            logger.error(f"Claude Code task execution failed for task {task_id}: {str(e)}")
            raise
    
    async def generate_sql_with_claude_code(
        self,
        user_id: str,
        query_description: str,
        table_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用Claude Code架构生成SQL
        
        Args:
            user_id: 用户ID
            query_description: 查询描述
            table_info: 表信息
            
        Returns:
            Dict: 生成结果
        """
        try:
            # 使用新的agents系统
            from app.api.utils.agent_context_helpers import create_sql_generation_context
            
            # 准备表结构信息
            table_schemas = []
            if table_info:
                for table_name, table_data in table_info.items():
                    schema_dict = {
                        "table_name": table_name,
                        "columns": table_data.get("columns", []),
                        "relationships": table_data.get("relationships", []),
                        "indexes": table_data.get("indexes", []),
                        "constraints": table_data.get("constraints", []),
                        "statistics": table_data.get("statistics", {}),
                        "sample_data": table_data.get("sample_data", [])
                    }
                    table_schemas.append(schema_dict)
            
            # 创建SQL生成上下文
            context = create_sql_generation_context(
                query_description=query_description,
                table_schemas=table_schemas,
                query_parameters={"user_id": user_id}
            )
            
            # 执行SQL生成任务
            try:
                from app.services.infrastructure.agents import execute_agent_task
                agent_result = await execute_agent_task(
                    task_name="sql_generation",
                    task_description=f"生成SQL查询: {query_description}",
                    context_data=context,
                    additional_data={
                        "table_info": table_info,
                        "user_id": user_id
                    }
                )
            except ImportError as e:
                logger.warning(f"Cannot import execute_agent_task for SQL generation: {e}")
                agent_result = {
                    "status": "fallback_sql_generation",
                    "message": "Agents system unavailable for SQL generation",
                    "success": False
                }
            
            return {
                "query_description": query_description,
                "results": agent_result,
                "architecture": "agents_v2"
            }
            
        except Exception as e:
            logger.error(f"Claude Code SQL generation failed: {str(e)}")
            raise
    
    async def analyze_data_with_claude_code(
        self,
        user_id: str,
        dataset: Dict[str, Any],
        analysis_type: str = "exploratory"
    ) -> Dict[str, Any]:
        """
        使用新的LLM编排服务分析数据
        
        Args:
            user_id: 用户ID
            dataset: 数据集
            analysis_type: 分析类型
            
        Returns:
            Dict: 分析结果
        """
        try:
            # 使用新的LLM编排服务
            from app.services.application.llm import get_llm_orchestration_service
            
            # 准备数据信息描述
            columns_info = dataset.get("columns", [])
            sample_data = dataset.get("sample_data", [])
            statistics = dataset.get("statistics", {})
            
            # 构建业务问题描述
            if analysis_type == "exploratory":
                business_question = "对这个数据集进行探索性数据分析，识别主要模式、趋势和异常值"
            elif analysis_type == "correlation":
                business_question = "分析数据集中各变量之间的相关关系和依赖模式"
            elif analysis_type == "summary":
                business_question = "提供数据集的统计摘要和关键洞察"
            else:
                business_question = f"执行{analysis_type}类型的数据分析"
            
            # 构建上下文信息
            context_info = {
                "dataset_info": {
                    "columns": columns_info,
                    "sample_data": sample_data,
                    "statistics": statistics,
                    "size": len(dataset.get("data", [])) if "data" in dataset else 0
                },
                "analysis_type": analysis_type,
                "requested_insights": [
                    "数据质量评估",
                    "主要趋势识别",
                    "异常值检测",
                    "关键统计特征",
                    "业务洞察建议"
                ]
            }
            
            # 获取编排服务并执行分析
            service = get_llm_orchestration_service()
            result = await service.analyze_data_requirements(
                user_id=user_id,
                business_question=business_question,
                context_info=context_info
            )
            
            if not result.get('success'):
                raise Exception(f"数据分析失败: {result.get('error', '未知错误')}")
            
            # 格式化返回结果
            return {
                "success": True,
                "dataset_info": {
                    "columns": columns_info,
                    "size": len(dataset.get("data", [])) if "data" in dataset else 0,
                    "sample_data_count": len(sample_data)
                },
                "analysis_type": analysis_type,
                "analysis_results": {
                    "analysis": result.get('analysis', ''),
                    "recommended_approach": result.get('recommended_approach', ''),
                    "confidence": result.get('confidence', 0.8)
                },
                "insights": {
                    "llm_participated": True,
                    "analysis_method": "six_stage_orchestration",
                    "timestamp": datetime.now().isoformat()
                },
                "architecture": "llm_orchestration_v2"
            }
            
        except Exception as e:
            logger.error(f"Claude Code data analysis failed: {str(e)}")
            raise


    # =================================================================
    # DDD架构v2.0 - 辅助方法
    # =================================================================

    def _infer_report_period_from_cron(self, cron_expression: Optional[str]) -> ReportPeriod:
        """基于cron表达式推断报告周期"""
        if not cron_expression or not isinstance(cron_expression, str):
            return ReportPeriod.MONTHLY

        try:
            # 解析cron表达式的5个字段: m h dom mon dow
            parts = cron_expression.strip().split()
            if len(parts) < 5:
                return ReportPeriod.MONTHLY

            minute, hour, day_of_month, month, day_of_week = parts[:5]

            # 如果指定了星期几（非 *），判定为每周
            if day_of_week and day_of_week != '*':
                return ReportPeriod.WEEKLY

            # 如果指定了月份（非 *），通常为每年
            if month and month != '*':
                return ReportPeriod.YEARLY

            # 如果指定了某一天（非 *），通常为每月
            if day_of_month and day_of_month != '*':
                return ReportPeriod.MONTHLY

            # 其余默认按每日
            return ReportPeriod.DAILY

        except Exception as e:
            self.logger.warning(f"解析cron表达式失败: {e}, 使用默认周期: monthly")
            return ReportPeriod.MONTHLY
    
    def _get_template_info(self, db: Session, template_id: str) -> Dict[str, Any]:
        """获取模板信息"""
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return {}
        
        return {
            "id": template.id,
            "name": template.name,
            "type": template.type if hasattr(template, 'type') else "general",
            "content": template.content if hasattr(template, 'content') else "",
            "size": len(template.content) if hasattr(template, 'content') and template.content else 0
        }
    
    def _get_data_source_info(self, db: Session, data_source_id: str) -> Dict[str, Any]:
        """获取数据源信息"""
        data_source = db.query(DataSource).filter(DataSource.id == data_source_id).first()
        if not data_source:
            return {}
        
        return {
            "id": data_source.id,
            "name": data_source.name,
            "type": data_source.source_type.value if data_source.source_type else "unknown",
            "scope": "full",  # 这里可以基于实际数据源配置
            "capabilities": {
                "supports_aggregation": True,
                "supports_time_queries": True,
                "supports_joins": True
            }
        }
    
    def _generate_task_recommendations(
        self, 
        execution_requirements: Dict[str, Any], 
        feasibility_check: Dict[str, Any], 
        placeholder_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成任务建议"""
        recommendations = []
        
        # 基于可行性检查
        if not feasibility_check.get("is_feasible", True):
            recommendations.append("任务当前不可执行，需要解决阻塞问题")
        
        # 基于复杂度
        complexity = execution_requirements.get("complexity", "simple")
        if complexity in ["complex", "highly_complex"]:
            recommendations.append("建议分批执行或增加监控点")
        
        # 基于占位符分析
        if placeholder_analysis:
            priority = placeholder_analysis.get("priority", "normal")
            if priority == "high":
                recommendations.append("建议优先处理此任务的占位符")
        
        # 基于资源需求
        resource_req = execution_requirements.get("resource_requirements", {})
        if resource_req.get("memory_mb", 0) > 4096:
            recommendations.append("任务需要大量内存，建议在资源充足时执行")
        
        return recommendations
    
    def _estimate_agents_needed(
        self, 
        task_definition: Dict[str, Any], 
        execution_requirements: Dict[str, Any]
    ) -> List[str]:
        """估算需要的agents"""
        agents_needed = ["task_coordination_agent"]
        
        # 基于处理模式
        if task_definition.get("processing_mode") == "intelligent":
            agents_needed.append("placeholder_analysis_agent")
        
        # 基于工作流类型
        workflow_type = task_definition.get("workflow_type", "simple_report")
        if workflow_type == "complex_analysis":
            agents_needed.extend(["data_analysis_agent", "report_generation_agent"])
        elif workflow_type == "multi_step_report":
            agents_needed.append("report_generation_agent")
        
        # 基于数据源
        if len(task_definition.get("data_source_ids", [])) > 1:
            agents_needed.append("data_integration_agent")
        
        return agents_needed
    
    def _build_task_definition(self, db: Session, task: Task) -> Dict[str, Any]:
        """构建任务定义"""
        return {
            "task_id": task.id,
            "name": task.name,
            "description": task.description,
            "template_id": str(task.template_id),
            "data_source_ids": [str(task.data_source_id)],
            "processing_mode": task.processing_mode.value if task.processing_mode else "simple",
            "workflow_type": task.workflow_type.value if task.workflow_type else "simple_report",
            "template_info": self._get_template_info(db, task.template_id),
            "data_source_info": self._get_data_source_info(db, task.data_source_id)
        }
    
    def _execute_step_with_agents(
        self, 
        agent_provider, 
        step: Dict[str, Any], 
        task: Task, 
        execution_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用agents执行单个步骤"""
        step_id = step.get("step_id")
        agents_required = step.get("agents_required", [])
        
        self.logger.info(f"执行步骤 {step_id}，需要agents: {agents_required}")
        
        step_result = {
            "step_id": step_id,
            "success": False,
            "agents_used": [],
            "execution_time": 0,
            "output": {},
            "errors": []
        }
        
        try:
            start_time = datetime.now()
            
            # 模拟调用基础设施层agents
            for agent_name in agents_required:
                if hasattr(agent_provider, f"get_{agent_name}"):
                    agent = getattr(agent_provider, f"get_{agent_name}")()
                    
                    # 调用agent执行具体任务
                    agent_result = self._call_agent_for_step(agent, step, task, execution_plan)
                    step_result["agents_used"].append(agent_name)
                    step_result["output"][agent_name] = agent_result
                else:
                    # 如果agent不存在，记录但不阻止执行
                    self.logger.warning(f"Agent {agent_name} 不可用，跳过")
                    step_result["errors"].append(f"Agent {agent_name} 不可用")
            
            end_time = datetime.now()
            step_result["execution_time"] = (end_time - start_time).total_seconds()
            step_result["success"] = len(step_result["errors"]) == 0
            
        except Exception as e:
            step_result["errors"].append(str(e))
            self.logger.error(f"步骤 {step_id} 执行失败: {e}")
        
        return step_result
    
    def _call_agent_for_step(
        self, 
        agent, 
        step: Dict[str, Any], 
        task: Task, 
        execution_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用agent执行具体步骤"""
        # 这里是与基础设施层agents的接口
        # 实际实现时需要根据具体的agent接口进行调用
        
        step_type = step.get("type", "unknown")
        
        if step_type == "preparation":
            return {"status": "prepared", "message": "任务准备完成"}
        elif step_type == "data_processing":
            return {"status": "data_acquired", "records": 100, "message": "数据获取完成"}
        elif step_type == "business_logic":
            return {"status": "processed", "placeholders": 5, "message": "占位符处理完成"}
        elif step_type == "output_generation":
            return {"status": "generated", "file_path": "/tmp/report.html", "message": "报告生成完成"}
        else:
            return {"status": "completed", "message": f"步骤 {step_type} 执行完成"}
    
    def _handle_step_failure(
        self, 
        agent_provider, 
        failed_step: Dict[str, Any], 
        execution_plan: Dict[str, Any], 
        previous_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """处理步骤失败"""
        rollback_strategy = execution_plan.get("rollback_strategy", {})
        
        # 简化的回滚逻辑
        if rollback_strategy.get("fallback_options"):
            return {"should_abort": False, "action": "retry_with_fallback"}
        else:
            return {"should_abort": True, "action": "abort_execution"}
    
    def _execute_task_traditional_way(
        self, 
        db: Session, 
        task: Task, 
        user_id: str
    ) -> ApplicationResult[Dict[str, Any]]:
        """传统方式执行任务（降级方案）"""
        self.logger.info(f"使用传统方式执行任务 {task.id}")
        
        # 调用现有的任务执行服务
        result = self.task_execution_service.execute_task(
            db, task.id, user_id, {}
        )
        
        return ApplicationResult.success_result(
            data={"traditional_execution": True, "result": result},
            message="任务通过传统方式执行完成"
        )


logger.info("✅ Task Application Service DDD架构v2.0 loaded with proper domain/infrastructure separation")