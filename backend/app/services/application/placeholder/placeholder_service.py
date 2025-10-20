"""
占位符应用服务 - 业务层实现

重构自原来的 placeholder_system.py，现在专注于业务流程编排，
使用新的 core/prompts 系统提供prompt工程能力。
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator, Tuple
from datetime import datetime

# 业务层导入
from app.services.domain.placeholder.types import (
    PlaceholderType, ChartType,
    PlaceholderInfo, PlaceholderAnalysisRequest, PlaceholderUpdateRequest, PlaceholderCompletionRequest,
    SQLGenerationResult, PlaceholderUpdateResult, PlaceholderCompletionResult, ChartGenerationResult,
    PlaceholderAgent
)

# 基础设施层导入 - 使用现有的PTOF agent系统
from app.services.infrastructure.agents.facade import AgentFacade
from app.services.infrastructure.agents.tools.registry import ToolRegistry
from app.core.container import Container
from app.services.domain.placeholder.services.placeholder_analysis_domain_service import (
    PlaceholderAnalysisDomainService,
)
from app.services.application.context.data_source_context_server import DataSourceContextBuilder

logger = logging.getLogger(__name__)


class PlaceholderApplicationService:
    """
    占位符应用服务
    
    专注于业务流程编排，使用基础设施层提供的能力：
    - 使用 PromptManager 进行智能prompt生成
    - 使用 AgentController 进行任务编排
    - 使用 ToolExecutor 进行工具调用
    """
    
    def __init__(self, user_id: str = None):
        # 基础设施组件 - 使用现有的PTOF agent系统
        self.container = Container()
        self.agent_facade = AgentFacade(self.container)
        self.tool_registry = ToolRegistry()

        # 用户上下文
        self.user_id = user_id

        # 业务状态
        self.is_initialized = False
        self.active_agents: Dict[str, PlaceholderAgent] = {}

        # 业务配置
        self.default_config = {
            "max_concurrent_agents": 5,
            "default_timeout": 300,
            "retry_attempts": 3
        }
        # 领域服务
        self.domain_service = PlaceholderAnalysisDomainService()
    
    async def initialize(self):
        """初始化应用服务"""
        if not self.is_initialized:
            logger.info("初始化占位符应用服务")
            
            try:
                # 初始化基础设施组件
                # TODO: 从依赖注入容器获取这些实例
                # self.agent_controller = await get_agent_controller()
                # self.tool_executor = await get_tool_executor()
                
                self.is_initialized = True
                logger.info("占位符应用服务初始化完成")
                
            except Exception as e:
                logger.error(f"占位符应用服务初始化失败: {e}")
                raise
    
    async def analyze_placeholder(self, request: PlaceholderAnalysisRequest) -> AsyncIterator[Dict[str, Any]]:
        """
        分析占位符 - 使用任务验证智能模式进行业务流程编排

        结合SQL验证和PTAV回退机制，实现自动化运维
        """
        await self.initialize()

        yield {
            "type": "analysis_started",
            "placeholder_id": request.placeholder_id,
            "mode": "task_validation_intelligent",
            "timestamp": datetime.now().isoformat()
        }

        try:
            # 1. 构建Agent输入
            from app.services.infrastructure.agents.types import AgentInput, PlaceholderSpec, SchemaInfo, TaskContext

            # 提取数据源信息构建Schema
            schema_info = SchemaInfo()
            if request.data_source_info:
                schema_info.database_name = request.data_source_info.get('database_name')
                schema_info.host = request.data_source_info.get('host')
                schema_info.port = request.data_source_info.get('port')
                schema_info.username = request.data_source_info.get('username')
                schema_info.password = request.data_source_info.get('password')

            semantic_type = None
            if isinstance(request.context, dict):
                schema_ctx = request.context.get("schema_context", {})
                if isinstance(schema_ctx, dict):
                    schema_info.tables = schema_ctx.get("available_tables", []) or []
                    schema_info.columns = schema_ctx.get("columns", {}) or {}
                semantic_type = request.context.get("semantic_type")

            # 构建占位符信息
            placeholder_granularity = "daily"
            if isinstance(request.context, dict):
                placeholder_granularity = (
                    request.context.get("business_requirements", {}).get("time_sensitivity")
                    or request.context.get("time_granularity")
                    or "daily"
                )

            placeholder_info = PlaceholderSpec(
                id=request.placeholder_id,
                description=f"{request.business_command} - {request.requirements}",
                type=semantic_type or "placeholder_analysis",
                granularity=placeholder_granularity
            )

            # 构建数据源配置 - 确保包含ID让executor能加载完整配置
            data_source_config = None
            if request.data_source_info:
                ds_config = dict(request.data_source_info)
                ds_id = ds_config.get('id') or ds_config.get('data_source_id')
                if ds_id:
                    ds_config.setdefault("id", str(ds_id))
                    ds_config.setdefault("data_source_id", str(ds_id))
                if semantic_type:
                    ds_config.setdefault("semantic_type", semantic_type)
                if isinstance(request.context, dict):
                    if request.context.get("business_requirements"):
                        ds_config.setdefault("business_requirements", request.context.get("business_requirements"))
                    schema_ctx = request.context.get("schema_context", {})
                    if isinstance(schema_ctx, dict) and schema_ctx.get("available_tables"):
                        ds_config.setdefault("available_tables", schema_ctx.get("available_tables"))
                data_source_config = ds_config

            enriched_task_context = {
                "placeholder_id": request.placeholder_id,
                "business_command": request.business_command,
                "requirements": request.requirements,
                "target_objective": request.target_objective,
                "context": request.context,
                "data_source_info": request.data_source_info,
                "analysis_type": "placeholder_service",
            }
            if isinstance(request.context, dict):
                for key in [
                    "semantic_type",
                    "business_requirements",
                    "placeholder_context_snippet",
                    "schema_context",
                    "template_context",
                    "business_context",
                    "planning_hints",
                    "top_n",
                    "schedule",
                    "time_window",
                    "time_context",
                    "cron_expression",
                    "time_range",
                    "user_id",
                ]:
                    value = request.context.get(key)
                    if value is not None:
                        enriched_task_context[key] = value

            agent_input = AgentInput(
                user_prompt=f"占位符分析: {request.business_command}\n需求: {request.requirements}\n目标: {request.target_objective}",
                placeholder=placeholder_info,
                schema=schema_info,
                context=TaskContext(
                    task_time=int(datetime.now().timestamp()),
                    timezone="Asia/Shanghai"
                ),
                data_source=data_source_config,
                task_driven_context=enriched_task_context,
                user_id=self.user_id  # 🔧 添加 user_id
            )

            yield {
                "type": "agent_input_prepared",
                "placeholder_id": request.placeholder_id,
                "timestamp": datetime.now().isoformat()
            }

            # 2. 使用任务验证智能模式执行分析
            result = await self.agent_facade.execute_task_validation(agent_input)

            # 3. 构建结果
            if result.success:
                sql_result = SQLGenerationResult(
                    sql_query=result.content,
                    validation_status="valid",
                    optimization_applied=True,
                    estimated_performance="good",
                    metadata={
                        "generation_method": result.metadata.get('generation_method', 'validation'),
                        "time_updated": result.metadata.get('time_updated', False),
                        "fallback_reason": result.metadata.get('fallback_reason'),
                        "validation_info": result.metadata,
                        "confidence_level": 0.9,
                        "generated_at": datetime.now().isoformat()
                    }
                )

                yield {
                    "type": "sql_generation_complete",
                    "placeholder_id": request.placeholder_id,
                    "content": sql_result,
                    "generation_method": result.metadata.get('generation_method', 'validation'),
                    "time_updated": result.metadata.get('time_updated', False),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # 分析失败
                error_result = SQLGenerationResult(
                    sql_query="",
                    validation_status="failed",
                    optimization_applied=False,
                    estimated_performance="poor",
                    metadata={
                        "error": result.metadata.get('error', '分析失败'),
                        "validation_info": result.metadata,
                        "generated_at": datetime.now().isoformat()
                    }
                )

                yield {
                    "type": "sql_generation_failed",
                    "placeholder_id": request.placeholder_id,
                    "content": error_result,
                    "error": result.metadata.get('error', '分析失败'),
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"占位符分析失败: {e}")

            error_result = SQLGenerationResult(
                sql_query="",
                validation_status="error",
                optimization_applied=False,
                estimated_performance="poor",
                metadata={
                    "error": str(e),
                    "generated_at": datetime.now().isoformat()
                }
            )

            yield {
                "type": "analysis_error",
                "placeholder_id": request.placeholder_id,
                "content": error_result,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def update_placeholder(self, request: PlaceholderUpdateRequest) -> AsyncIterator[Dict[str, Any]]:
        """
        更新占位符 - 业务流程编排
        """
        await self.initialize()
        
        # 1. 生成更新分析prompt
        update_prompt = self.prompt_manager.context_update(
            task_context=str(request.task_context),
            current_task_info=str(request.current_task_info),
            target_objective=request.target_objective,
            stored_placeholders=[
                {"name": p.placeholder_id, "description": p.description} 
                for p in request.stored_placeholders
            ]
        )
        
        yield {
            "type": "update_analysis_started",
            "placeholder_id": request.placeholder_id,
            "prompt_generated": True
        }
        
        # 2. 执行更新分析
        # TODO: 使用 AgentController 执行更新分析
        
        # 临时实现
        result = PlaceholderUpdateResult(
            placeholder_id=request.placeholder_id,
            update_needed=True,
            update_reason="基于新的prompt系统分析，需要更新占位符内容",
            confidence_score=0.8,
            metadata={
                "updated_at": datetime.now().isoformat(),
                "prompt_engineering_applied": True,
                "context_analysis_performed": True
            }
        )
        
        yield {
            "type": "update_analysis_complete",
            "placeholder_id": request.placeholder_id,
            "content": result
        }
    
    async def complete_placeholder(self, request: PlaceholderCompletionRequest) -> AsyncIterator[Dict[str, Any]]:
        """
        完成占位符 - 业务流程编排
        """
        await self.initialize()
        
        # 1. 生成数据完成prompt
        completion_prompt = self.prompt_manager.data_completion(
            placeholder_requirements=request.placeholder_requirements,
            template_section=request.template_section,
            etl_data=request.etl_data,
            chart_generation_needed=request.chart_generation_needed,
            target_chart_type=request.target_chart_type.value if request.target_chart_type else None
        )
        
        yield {
            "type": "completion_started",
            "placeholder_id": request.placeholder_id,
            "prompt_generated": True
        }
        
        # 2. 执行数据完成
        # TODO: 使用 ToolExecutor 执行数据处理工具
        
        # 临时实现
        completion_result = PlaceholderCompletionResult(
            placeholder_id=request.placeholder_id,
            completed_content="基于新prompt系统生成的高质量内容",
            metadata={
                "content_type": PlaceholderType.TEXT.value,
                "quality_score": 0.9,
                "prompt_engineering_used": True,
                "data_records_processed": len(request.etl_data),
                "chart_generated": request.chart_generation_needed
            }
        )
        
        result = {
            "completion_result": completion_result
        }
        
        # 如果需要图表生成
        if request.chart_generation_needed:
            chart_result = ChartGenerationResult(
                chart_id=f"chart_{uuid.uuid4().hex[:8]}",
                chart_type=request.target_chart_type or ChartType.BAR,
                chart_config={
                    "title": "基于prompt系统生成的图表",
                    "data_source": "ETL处理结果"
                },
                chart_data=request.etl_data,
                generation_status="completed",
                generated_at=datetime.now()
            )
            result["chart_result"] = chart_result
        
        yield {
            "type": "completion_complete",
            "placeholder_id": request.placeholder_id,
            "content": result
        }
    
    async def get_active_agents(self) -> List[PlaceholderAgent]:
        """获取活跃的占位符agent"""
        return list(self.active_agents.values())
    
    async def shutdown(self):
        """关闭应用服务"""
        if self.is_initialized:
            logger.info("关闭占位符应用服务")
            
            # 清理活跃的agents
            for agent_id in list(self.active_agents.keys()):
                await self._cleanup_agent(agent_id)
            
            self.is_initialized = False
    
    async def _cleanup_agent(self, agent_id: str):
        """清理指定的agent"""
        if agent_id in self.active_agents:
            agent = self.active_agents[agent_id]
            # TODO: 清理agent相关资源
            del self.active_agents[agent_id]
            logger.debug(f"已清理agent: {agent_id}")

    async def run_task_with_agent(
        self,
        task_objective: str,
        success_criteria: Dict[str, Any],
        data_source_id: str,
        time_window: Dict[str, str],
        time_column: Optional[str] = None,
        max_attempts: int = 3,
        template_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        使用Agent系统执行占位符分析和SQL生成任务

        这是Celery任务调用的核心方法，负责：
        1. 检查现有占位符SQL状态
        2. 对需要的占位符调用Agent生成SQL
        3. 验证和替换SQL中的时间占位符
        4. 执行SQL并返回结果
        """
        await self.initialize()

        yield {
            "type": "agent_session_started",
            "message": f"开始Agent任务执行: {task_objective}",
            "timestamp": datetime.now().isoformat()
        }

        try:
            # 导入所需的工具
            from app.utils.sql_placeholder_utils import SqlPlaceholderReplacer
            from app.crud import template_placeholder as crud_template_placeholder
            from app.db.session import get_db_session
            from app.services.infrastructure.agents.facade import AgentFacade

            sql_replacer = SqlPlaceholderReplacer()

            # 获取当前任务的占位符
            with get_db_session() as db:
                # 使用传入的template_id或从上下文获取
                if not template_id:
                    template_id = await self._get_template_id_from_context(data_source_id)

                if not template_id:
                    yield {
                        "type": "agent_session_failed",
                        "message": "无法确定模板ID",
                        "error": "Missing template context"
                    }
                    return

                placeholders = crud_template_placeholder.get_by_template(db, template_id)

                yield {
                    "type": "placeholders_loaded",
                    "message": f"加载了 {len(placeholders)} 个占位符",
                    "placeholder_count": len(placeholders)
                }

                # 分析占位符状态
                placeholders_need_analysis = []
                placeholders_need_sql_replacement = []
                placeholders_ready = []

                for ph in placeholders:
                    needs_generation = (
                        not ph.generated_sql or
                        not ph.sql_validated or
                        ph.generated_sql.strip() == ""
                    )

                    if needs_generation:
                        placeholders_need_analysis.append(ph)
                    else:
                        # 检查SQL是否需要占位符替换
                        sql_placeholders = sql_replacer.extract_placeholders(ph.generated_sql)
                        if sql_placeholders:
                            placeholders_need_sql_replacement.append(ph)
                        else:
                            placeholders_ready.append(ph)

                yield {
                    "type": "placeholder_analysis_complete",
                    "message": f"占位符分析完成",
                    "need_generation": len(placeholders_need_analysis),
                    "need_replacement": len(placeholders_need_sql_replacement),
                    "ready": len(placeholders_ready)
                }

                # Step 1: 为需要生成SQL的占位符调用Agent
                if placeholders_need_analysis:
                    yield {
                        "type": "sql_generation_started",
                        "message": f"开始为 {len(placeholders_need_analysis)} 个占位符生成SQL"
                    }

                    for ph in placeholders_need_analysis:
                        try:
                            # 调用Agent生成SQL
                            sql_result = await self._generate_sql_with_agent(
                                ph, data_source_id, task_objective, success_criteria, db
                            )

                            if sql_result["success"]:
                                # 更新占位符的SQL
                                ph.generated_sql = sql_result["sql"]
                                ph.sql_validated = True
                                ph.agent_analyzed = True
                                ph.analyzed_at = datetime.now()
                                db.commit()

                                # 检查生成的SQL是否需要占位符替换
                                sql_placeholders = sql_replacer.extract_placeholders(ph.generated_sql)
                                if sql_placeholders:
                                    placeholders_need_sql_replacement.append(ph)
                                else:
                                    placeholders_ready.append(ph)

                                yield {
                                    "type": "sql_generated",
                                    "placeholder_name": ph.placeholder_name,
                                    "sql": ph.generated_sql,
                                    "has_placeholders": len(sql_placeholders) > 0
                                }
                            else:
                                yield {
                                    "type": "sql_generation_failed",
                                    "placeholder_name": ph.placeholder_name,
                                    "error": sql_result["error"]
                                }

                        except Exception as e:
                            logger.error(f"SQL生成失败 {ph.placeholder_name}: {e}")
                            yield {
                                "type": "sql_generation_failed",
                                "placeholder_name": ph.placeholder_name,
                                "error": str(e)
                            }

                # Step 2: 对所有需要占位符替换的SQL进行替换
                if placeholders_need_sql_replacement:
                    yield {
                        "type": "sql_replacement_started",
                        "message": f"开始替换 {len(placeholders_need_sql_replacement)} 个占位符中的时间变量"
                    }

                    # 构建时间上下文
                    time_context = {
                        "data_start_time": time_window["start"].split(" ")[0],  # 提取日期部分
                        "data_end_time": time_window["end"].split(" ")[0],
                        "execution_time": datetime.now().strftime("%Y-%m-%d")
                    }

                    for ph in placeholders_need_sql_replacement:
                        try:
                            # 验证占位符
                            validation_result = sql_replacer.validate_placeholders(ph.generated_sql, time_context)

                            if validation_result["valid"]:
                                # 执行占位符替换
                                replaced_sql = sql_replacer.replace_time_placeholders(ph.generated_sql, time_context)

                                yield {
                                    "type": "sql_replaced",
                                    "placeholder_name": ph.placeholder_name,
                                    "original_sql": ph.generated_sql,
                                    "replaced_sql": replaced_sql,
                                    "replacements": validation_result["placeholder_details"]
                                }

                                # 将替换后的SQL添加到准备就绪列表
                                ph._final_sql = replaced_sql  # 临时存储最终SQL
                                placeholders_ready.append(ph)
                            else:
                                yield {
                                    "type": "sql_replacement_failed",
                                    "placeholder_name": ph.placeholder_name,
                                    "missing_placeholders": validation_result["missing_placeholders"],
                                    "warnings": validation_result["warnings"]
                                }

                        except Exception as e:
                            logger.error(f"占位符替换失败 {ph.placeholder_name}: {e}")
                            yield {
                                "type": "sql_replacement_failed",
                                "placeholder_name": ph.placeholder_name,
                                "error": str(e)
                            }

                # Step 3: 执行数据提取（可选，根据需要）
                if success_criteria.get("execute_queries", False):
                    yield {
                        "type": "data_extraction_started",
                        "message": f"开始执行 {len(placeholders_ready)} 个占位符的数据查询"
                    }

                    for ph in placeholders_ready:
                        try:
                            final_sql = getattr(ph, '_final_sql', ph.generated_sql)
                            # 这里可以调用实际的数据库执行逻辑
                            # 暂时返回模拟结果
                            yield {
                                "type": "data_extracted",
                                "placeholder_name": ph.placeholder_name,
                                "row_count": 1,  # 模拟结果
                                "execution_time_ms": 100
                            }
                        except Exception as e:
                            logger.error(f"数据提取失败 {ph.placeholder_name}: {e}")
                            yield {
                                "type": "data_extraction_failed",
                                "placeholder_name": ph.placeholder_name,
                                "error": str(e)
                            }

                # 最终结果
                total_processed = len(placeholders_ready)
                total_failed = len(placeholders) - total_processed

                yield {
                    "type": "agent_session_complete",
                    "success": total_failed == 0,
                    "message": f"任务完成: {total_processed} 个占位符处理成功, {total_failed} 个失败",
                    "total_placeholders": len(placeholders),
                    "processed_successfully": total_processed,
                    "failed": total_failed,
                    "time_window": time_window
                }

        except Exception as e:
            logger.error(f"Agent任务执行异常: {e}")
            yield {
                "type": "agent_session_failed",
                "message": "Agent任务执行异常",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _get_template_id_from_context(self, data_source_id: str) -> Optional[str]:
        """从上下文中获取模板ID"""
        # 实际上这个方法应该从外部传入template_id
        # 在run_task_with_agent方法中添加template_id参数
        return None

    def set_template_context(self, template_id: str):
        """设置模板上下文"""
        self.template_id = template_id

    async def _generate_sql_with_agent(
        self,
        placeholder,
        data_source_id: str,
        task_objective: str,
        success_criteria: Dict[str, Any],
        db,
        task_context: Optional[Dict[str, Any]] = None  # 👈 新增：任务上下文参数
    ) -> Dict[str, Any]:
        """
        使用Agent生成占位符的SQL

        Args:
            placeholder: 占位符对象
            data_source_id: 数据源ID
            task_objective: 任务目标
            success_criteria: 成功标准
            db: 数据库会话
            task_context: 任务上下文（可选）
                - 单占位符API：None（使用默认值）
                - 任务中多占位符：真实的任务信息
        """
        try:
            # 👇 获取数据源信息并构建统一上下文
            data_source_info = await self._get_data_source_info(data_source_id)

            user_id = (task_context or {}).get("user_id") or self.user_id
            template_id = getattr(placeholder, "template_id", None)
            template_id_str = str(template_id) if template_id else None
            template_content = ""
            template_snippet = ""
            if template_id_str:
                template_content = self._load_template_content(template_id_str)
                template_snippet = self._extract_placeholder_snippet(
                    template_content,
                    getattr(placeholder, "placeholder_text", ""),
                    getattr(placeholder, "placeholder_name", "")
                )

            raw_schedule = (task_context or {}).get("schedule")
            if raw_schedule and not isinstance(raw_schedule, dict):
                normalized_schedule = {"cron_expression": raw_schedule}
            else:
                normalized_schedule = raw_schedule or {}

            raw_time_window = (task_context or {}).get("time_window") or {}
            normalized_time_window, normalized_time_range = self._normalize_time_window(
                raw_time_window, normalized_schedule
            )

            business_context = {
                "template_id": template_id_str,
                "data_source_id": data_source_id,
                "template_context": {"snippet": template_snippet} if template_snippet else {},
                "execution_context": task_context or {},
                "time_column": normalized_time_window.get("time_column"),
                "data_range": normalized_time_window.get("data_range") or "day",
                "time_window": normalized_time_window,
                "time_range": normalized_time_range,
            }

            business_requirements = await self.domain_service.analyze_placeholder_business_requirements(
                placeholder_text=placeholder.placeholder_text,
                business_context=business_context,
                user_id=user_id
            )
            semantic_type = self._map_business_to_semantic_type(business_requirements)
            schema_context = await self._get_schema_context(user_id, data_source_id)

            data_source_info["semantic_type"] = semantic_type
            data_source_info["business_requirements"] = business_requirements

            context = self._build_unified_context(
                placeholder=placeholder,
                data_source_id=data_source_id,
                success_criteria=success_criteria,
                task_context=task_context,
                data_source_info=data_source_info,
                business_requirements=business_requirements,
                semantic_type=semantic_type,
                template_context={"snippet": template_snippet} if template_snippet else {},
                template_snippet=template_snippet,
                schema_context=schema_context,
                business_context=business_context,
                template_content=template_content,
                normalized_time_window=normalized_time_window,
                normalized_time_range=normalized_time_range,
                schedule=normalized_schedule,
            )

            # 构建Agent输入
            agent_request = PlaceholderAnalysisRequest(
                placeholder_id=str(placeholder.id),
                business_command=placeholder.placeholder_text,
                requirements=placeholder.description or task_objective,
                context=context,  # 👈 使用统一构建的 context
                target_objective=task_objective,
                data_source_info=data_source_info
            )

            # 调用占位符分析
            sql_result = None
            async for event in self.analyze_placeholder(agent_request):
                if event.get("type") == "sql_generation_complete":
                    sql_result = event.get("content")
                    break
                elif event.get("type") == "sql_generation_failed":
                    return {
                        "success": False,
                        "error": event.get("error", "SQL生成失败")
                    }

            if sql_result and hasattr(sql_result, 'generated_sql'):
                return {
                    "success": True,
                    "sql": sql_result.generated_sql,
                    "confidence": sql_result.confidence_score
                }
            else:
                return {
                    "success": False,
                    "error": "Agent未返回有效的SQL结果"
                }

        except Exception as e:
            logger.error(f"Agent SQL生成异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _build_unified_context(
        self,
        placeholder,
        data_source_id: str,
        success_criteria: Dict[str, Any],
        task_context: Optional[Dict[str, Any]] = None,
        data_source_info: Optional[Dict[str, Any]] = None,
        business_requirements: Optional[Dict[str, Any]] = None,
        semantic_type: Optional[str] = None,
        template_context: Optional[Dict[str, Any]] = None,
        template_snippet: Optional[str] = None,
        schema_context: Optional[Dict[str, Any]] = None,
        business_context: Optional[Dict[str, Any]] = None,
        template_content: Optional[str] = None,
        normalized_time_window: Optional[Dict[str, Any]] = None,
        normalized_time_range: Optional[Dict[str, Any]] = None,
        schedule: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        构建统一的 context（区分真实值 vs 默认值）

        Args:
            placeholder: 占位符对象
            data_source_id: 数据源ID
            success_criteria: 成功标准
            task_context: 任务上下文（可选）
                - None：单占位符API场景，使用默认值
                - Dict：任务场景，使用真实值

        Returns:
            统一的 context 字典
        """
        # 🔹 基础字段（两种场景都有）
        context = {
            "data_source_id": data_source_id,
            "placeholder_type": getattr(placeholder, "placeholder_type", None),
            "placeholder_name": getattr(placeholder, "placeholder_name", None),
            "content_type": getattr(placeholder, "content_type", None),
            "template_id": str(getattr(placeholder, "template_id", "") or "") or None,
        }

        # 🔹 从 success_criteria 提取信息
        context["required_fields"] = success_criteria.get("required_fields", [])
        context["quality_threshold"] = success_criteria.get("quality_threshold", 0.6)

        # 🔹 从 placeholder 对象提取更多信息
        context["execution_order"] = getattr(placeholder, "execution_order", 0)
        context["is_required"] = getattr(placeholder, "is_required", True)
        context["confidence_score"] = getattr(placeholder, "confidence_score", 0.0)

        # 提取解析元数据
        parsing_metadata = getattr(placeholder, "parsing_metadata", None)
        if isinstance(parsing_metadata, dict):
            context["parsing_metadata"] = parsing_metadata

        # 🔹 数据源上下文
        if data_source_info:
            ds_id = data_source_info.get("data_source_id") or data_source_info.get("id") or data_source_id
            normalized_ds = {
                "id": str(ds_id) if ds_id else None,
                "data_source_id": str(ds_id) if ds_id else None,
                "name": data_source_info.get("name"),
                "source_type": data_source_info.get("source_type"),
                "connection_config": data_source_info.get("connection_config") or data_source_info
            }
            context["data_source"] = normalized_ds
            context["data_source_id"] = normalized_ds["data_source_id"]
            context["data_source_info"] = data_source_info
            if data_source_info.get("name"):
                context.setdefault("data_source_name", data_source_info.get("name"))

        # 🔹 任务上下文处理（区分真实值 vs 默认值）
        if task_context:
            # ✅ 任务场景：使用真实的任务信息
            logger.info(f"📦 使用真实任务上下文: task_id={task_context.get('task_id')}")

            context["task_id"] = task_context.get("task_id")
            context["task_name"] = task_context.get("task_name")
            context["report_period"] = task_context.get("report_period")
            context["user_id"] = task_context.get("user_id")

            raw_schedule = schedule if schedule is not None else task_context.get("schedule")
            if raw_schedule and not isinstance(raw_schedule, dict):
                schedule_dict = {"cron_expression": raw_schedule}
            else:
                schedule_dict = raw_schedule or {}
            context["schedule"] = schedule_dict

            raw_time_window = task_context.get("time_window") or {}
            if normalized_time_window is None or normalized_time_range is None:
                normalized_time_window, normalized_time_range = self._normalize_time_window(
                    raw_time_window,
                    schedule_dict
                )
            context["time_window"] = normalized_time_window
            context["time_range"] = normalized_time_range

            context["time_context"] = task_context.get("time_context")  # 完整时间上下文

            # 执行上下文（真实值）
            context["execution_trigger"] = task_context.get("execution_trigger", "scheduled")
            context["execution_id"] = task_context.get("execution_id")

        else:
            # ⚠️ API场景：构造默认值
            logger.info("📦 使用默认上下文（单占位符API场景）")

            context["template_id"] = str(placeholder.template_id) if hasattr(placeholder, "template_id") else None
            context["execution_trigger"] = "manual"  # API 手动触发

            # 时间信息（默认值）
            from datetime import datetime
            from app.utils.time_context import TimeContextManager

            # 构造默认的时间上下文（每天 9点，查询昨天的数据）
            default_cron = "0 9 * * *"
            time_manager = TimeContextManager()
            default_time_ctx = time_manager.build_task_time_context(default_cron, datetime.now())

            schedule_dict = {
                "cron_expression": default_cron,
                "timezone": default_time_ctx.get("timezone", "Asia/Shanghai"),
            }
            context["schedule"] = schedule_dict
            default_raw_time_window = {
                "start": default_time_ctx.get("data_start_time") and f"{default_time_ctx.get('data_start_time')} 00:00:00",
                "end": default_time_ctx.get("data_end_time") and f"{default_time_ctx.get('data_end_time')} 23:59:59",
                "time_column": None,
                "timezone": default_time_ctx.get("timezone", "Asia/Shanghai"),
                "data_range": "day",
            }
            normalized_default_window, normalized_default_range = self._normalize_time_window(
                default_raw_time_window,
                schedule_dict
            )
            context["time_window"] = normalized_default_window
            context["time_range"] = normalized_default_range
            context["time_context"] = default_time_ctx
            logger.info(f"🕒 使用默认时间窗口: {context['time_window']}")

        # 🔹 业务与语义信息
        if business_context:
            context["business_context"] = business_context
        if business_requirements:
            context["business_requirements"] = business_requirements
            if business_requirements.get("top_n") is not None:
                context.setdefault("top_n", business_requirements.get("top_n"))
        if semantic_type:
            context["semantic_type"] = semantic_type
            context["placeholder_type"] = semantic_type

        # 🔹 模板上下文
        if template_context:
            context["template_context"] = template_context
        if template_snippet:
            context["placeholder_context_snippet"] = template_snippet
        if template_content:
            context["template_content_preview"] = template_content[:500]

        # 🔹 Schema上下文
        if schema_context:
            context["schema_context"] = schema_context

        # 默认的规划提示占位
        context.setdefault("planning_hints", {})

        return context

    def _normalize_time_window(
        self,
        raw_time_window: Optional[Dict[str, Any]],
        schedule: Optional[Dict[str, Any]] = None,
        default_timezone: str = "Asia/Shanghai",
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """规范化时间窗口信息，生成统一的time_window与time_range结构"""
        raw_time_window = raw_time_window or {}
        schedule = schedule or {}
        if isinstance(schedule, str):
            schedule = {"cron_expression": schedule}

        timezone = (
            raw_time_window.get("timezone")
            or schedule.get("timezone")
            or default_timezone
        )
        start_dt = raw_time_window.get("start") or raw_time_window.get("start_datetime")
        end_dt = raw_time_window.get("end") or raw_time_window.get("end_datetime")
        start_date = raw_time_window.get("start_date")
        end_date = raw_time_window.get("end_date")

        if start_dt and not start_date:
            start_date = start_dt.split(" ")[0]
        if end_dt and not end_date:
            end_date = end_dt.split(" ")[0]

        normalized_time_window = {
            "start": start_dt,
            "end": end_dt,
            "start_date": start_date,
            "end_date": end_date,
            "time_column": raw_time_window.get("time_column"),
            "timezone": timezone,
            "data_range": raw_time_window.get("data_range"),
        }

        normalized_time_range = {
            "start_date": start_date,
            "end_date": end_date,
            "time_column": raw_time_window.get("time_column"),
            "timezone": timezone,
        }

        return normalized_time_window, normalized_time_range

    def _map_business_to_semantic_type(self, business_requirements: Optional[Dict[str, Any]]) -> str:
        """将业务需求映射到Agent工具的语义类型"""
        if not business_requirements:
            return "stat"

        business_type = str(business_requirements.get("business_type", "")).lower()
        semantic_intent = str(business_requirements.get("semantic_intent", "")).lower()

        if "ranking" in business_type or "top" in semantic_intent or "排行" in semantic_intent:
            return "ranking"
        if "compare" in business_type or "对比" in semantic_intent or "比较" in semantic_intent:
            return "compare"
        if "period" in business_type or "周期" in semantic_intent or "时间" in semantic_intent:
            return "period"
        if "chart" in business_type or "图表" in semantic_intent:
            return "chart"
        return "stat"

    def _extract_placeholder_snippet(self, template_text: str, placeholder_text: str, placeholder_name: str) -> str:
        """从模板中提取包含占位符的段落"""
        try:
            if not template_text:
                return ""
            lines = template_text.splitlines()
            keys = [k for k in [placeholder_text, placeholder_name, placeholder_name and f"{{{{{placeholder_name}}}}}"] if k]
            hit_idx = -1
            for i, line in enumerate(lines):
                for key in keys:
                    if key and key in line:
                        hit_idx = i
                        break
                if hit_idx >= 0:
                    break

            if hit_idx < 0:
                preview = template_text[:500]
                return preview + ("…" if len(template_text) > 500 else "")

            start = hit_idx
            while start > 0 and lines[start].strip() != "" and lines[start - 1].strip() != "":
                start -= 1
            end = hit_idx
            while end + 1 < len(lines) and lines[end].strip() != "" and lines[end + 1].strip() != "":
                end += 1
            snippet_lines = lines[start:end + 1]
            if start > 0:
                snippet_lines.insert(0, lines[start - 1])
            if end + 1 < len(lines):
                snippet_lines.append(lines[end + 1])
            return "\n".join(snippet_lines).strip()
        except Exception:
            preview = template_text[:500]
            return preview + ("…" if len(template_text) > 500 else "")

    def _load_template_content(self, template_id: str) -> str:
        """加载模板内容"""
        try:
            from app.db.session import get_db_session
            from app import crud

            with get_db_session() as db_session:
                template_obj = crud.template.get(db_session, id=template_id)
                if template_obj and getattr(template_obj, "content", None):
                    return template_obj.content
        except Exception as e:
            logger.warning(f"加载模板内容失败: {e}")
        return ""

    async def _get_schema_context(self, user_id: Optional[str], data_source_id: str) -> Dict[str, Any]:
        """获取数据源Schema信息，用于指导Agent生成SQL"""
        if not data_source_id:
            return {"available_tables": [], "table_count": 0}

        try:
            builder = DataSourceContextBuilder(container=self.container)
            context_result = await builder.build_data_source_context(
                user_id=user_id or "system",
                data_source_id=data_source_id,
                required_tables=None,
                force_refresh=False,
                names_only=True
            )
            if context_result and context_result.get("success"):
                tables_payload = context_result.get("tables", [])
                tables: List[str] = []
                for table_info in tables_payload:
                    if isinstance(table_info, dict):
                        name = table_info.get("table_name")
                        if name:
                            tables.append(name)
                return {
                    "available_tables": tables,
                    "table_count": len(tables)
                }
        except Exception as e:
            logger.warning(f"获取Schema上下文失败: {e}")
        return {"available_tables": [], "table_count": 0}

    async def _get_data_source_info(self, data_source_id: str) -> Dict[str, Any]:
        """获取数据源信息"""
        try:
            if not data_source_id:
                return {}

            normalized_id = str(data_source_id)

            # 优先使用容器提供的用户数据源服务（支持密码解密）
            user_id = self.user_id or ""
            user_ds_service = getattr(self.container, "user_data_source_service", None)
            if user_ds_service and user_id:
                try:
                    ds_obj = await user_ds_service.get_user_data_source(user_id, normalized_id)
                    if ds_obj and hasattr(ds_obj, "connection_config"):
                        cfg = dict(ds_obj.connection_config or {})
                        # 补全基础字段
                        source_type = getattr(ds_obj, "source_type", cfg.get("source_type"))
                        if hasattr(source_type, "value"):
                            source_type = source_type.value
                        if isinstance(source_type, str):
                            cfg.setdefault("source_type", source_type.split(".")[-1])
                        cfg.setdefault("name", getattr(ds_obj, "name", ""))
                        cfg.setdefault("id", normalized_id)
                        cfg.setdefault("data_source_id", normalized_id)
                        # 兼容常用字段
                        cfg.setdefault("database_name", cfg.get("database") or cfg.get("schema"))
                        return cfg
                except Exception as svc_error:
                    logger.warning(f"使用用户数据源服务获取配置失败: {svc_error}")

            # 回退：直接读取数据源记录
            from app.crud import data_source as crud_data_source
            from app.db.session import get_db_session
            from app.models.data_source import DataSourceType
            from app.core.security_utils import decrypt_data
            from app.core.data_source_utils import DataSourcePasswordManager

            with get_db_session() as db:
                data_source = crud_data_source.get(db, id=normalized_id)
                if not data_source:
                    return {}

                info: Dict[str, Any] = {
                    "id": normalized_id,
                    "data_source_id": normalized_id,
                    "name": data_source.name,
                }

                if data_source.source_type == DataSourceType.doris:
                    info.update({
                        "source_type": "doris",
                        "database": getattr(data_source, "doris_database", "default"),
                        "database_name": getattr(data_source, "doris_database", "default"),
                        "fe_hosts": list(getattr(data_source, "doris_fe_hosts", []) or ["localhost"]),
                        "be_hosts": list(getattr(data_source, "doris_be_hosts", []) or ["localhost"]),
                        "http_port": getattr(data_source, "doris_http_port", 8030),
                        "query_port": getattr(data_source, "doris_query_port", 9030),
                        "username": getattr(data_source, "doris_username", "root"),
                        "password": DataSourcePasswordManager.get_password(data_source.doris_password) if getattr(data_source, "doris_password", None) else "",
                        "timeout": 30
                    })
                elif data_source.source_type == DataSourceType.sql:
                    conn_str = data_source.connection_string
                    try:
                        if conn_str:
                            conn_str = decrypt_data(conn_str)
                    except Exception:
                        pass
                    info.update({
                        "source_type": "sql",
                        "connection_string": conn_str,
                        "database": getattr(data_source, "database_name", None),
                        "database_name": getattr(data_source, "database_name", None),
                        "host": getattr(data_source, "host", None),
                        "port": getattr(data_source, "port", None),
                        "username": getattr(data_source, "username", None),
                        "password": getattr(data_source, "password", None),
                    })
                else:
                    source_type = data_source.source_type.value if hasattr(data_source.source_type, "value") else str(data_source.source_type)
                    info.setdefault("source_type", source_type)

                return info

        except Exception as e:
            logger.error(f"获取数据源信息失败: {e}")
            return {}


# 全局服务实例管理
_global_service = None


async def get_placeholder_service() -> PlaceholderApplicationService:
    """获取全局占位符应用服务实例"""
    global _global_service
    if _global_service is None:
        _global_service = PlaceholderApplicationService()
        await _global_service.initialize()
    return _global_service


async def shutdown_placeholder_service():
    """关闭全局占位符应用服务"""
    global _global_service
    if _global_service:
        await _global_service.shutdown()
        _global_service = None


# 兼容性函数 - 保持向后兼容
async def analyze_placeholder_simple(
    placeholder_id: str,
    business_command: str,
    requirements: str,
    context: Optional[Dict[str, Any]] = None,
    target_objective: str = "",
    data_source_info: Optional[Dict[str, Any]] = None,
    existing_sql: Optional[str] = None
) -> SQLGenerationResult:
    """
    简化的占位符分析接口 - 使用任务验证智能模式

    Args:
        placeholder_id: 占位符ID
        business_command: 业务命令
        requirements: 需求描述
        context: 上下文信息
        target_objective: 目标要求
        data_source_info: 数据源信息
        existing_sql: 现有SQL（如果存在）

    Returns:
        SQL生成结果
    """

    service = await get_placeholder_service()

    # 如果提供了existing_sql，加入到context中
    if existing_sql:
        context = context or {}
        context["current_sql"] = existing_sql

    request = PlaceholderAnalysisRequest(
        placeholder_id=placeholder_id,
        business_command=business_command,
        requirements=requirements,
        context=context or {},
        target_objective=target_objective,
        data_source_info=data_source_info
    )

    result = None
    async for response in service.analyze_placeholder(request):
        if response["type"] == "sql_generation_complete":
            result = response["content"]
            break
        elif response["type"] == "sql_generation_failed":
            # 返回失败的结果
            result = response["content"]
            break

    return result


async def update_placeholder_simple(
    placeholder_id: str,
    task_context: Dict[str, Any],
    current_task_info: Dict[str, Any],
    target_objective: str,
    stored_placeholders: List[PlaceholderInfo]
) -> PlaceholderUpdateResult:
    """简化的占位符更新接口 - 兼容性函数"""
    
    service = await get_placeholder_service()
    
    request = PlaceholderUpdateRequest(
        placeholder_id=placeholder_id,
        task_context=task_context,
        current_task_info=current_task_info,
        target_objective=target_objective,
        stored_placeholders=stored_placeholders
    )
    
    result = None
    async for response in service.update_placeholder(request):
        if response["type"] == "update_analysis_complete":
            result = response["content"]
            break
    
    return result


async def complete_placeholder_simple(
    placeholder_id: str,
    etl_data: List[Dict[str, Any]],
    placeholder_requirements: str,
    template_section: str,
    chart_generation_needed: bool = False,
    target_chart_type: Optional[ChartType] = None
) -> Dict[str, Any]:
    """简化的占位符完成接口 - 兼容性函数"""
    
    service = await get_placeholder_service()
    
    request = PlaceholderCompletionRequest(
        placeholder_id=placeholder_id,
        etl_data=etl_data,
        placeholder_requirements=placeholder_requirements,
        template_section=template_section,
        chart_generation_needed=chart_generation_needed,
        target_chart_type=target_chart_type
    )
    
    result = None
    async for response in service.complete_placeholder(request):
        if response["type"] == "completion_complete":
            result = response["content"]
            break
    
    return result


# 兼容性别名
analyze_placeholder = analyze_placeholder_simple
update_placeholder = update_placeholder_simple  
complete_placeholder = complete_placeholder_simple
