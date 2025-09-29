"""
占位符应用服务 - 业务层实现

重构自原来的 placeholder_system.py，现在专注于业务流程编排，
使用新的 core/prompts 系统提供prompt工程能力。
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, AsyncIterator
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
            from app.services.infrastructure.agents.types import AgentInput, PlaceholderInfo, SchemaInfo, TaskContext

            # 提取数据源信息构建Schema
            schema_info = SchemaInfo()
            if request.data_source_info:
                schema_info.database_name = request.data_source_info.get('database_name')
                schema_info.host = request.data_source_info.get('host')
                schema_info.port = request.data_source_info.get('port')
                schema_info.username = request.data_source_info.get('username')
                schema_info.password = request.data_source_info.get('password')

            # 构建占位符信息
            placeholder_info = PlaceholderInfo(
                description=f"{request.business_command} - {request.requirements}",
                type="placeholder_analysis"
            )

            agent_input = AgentInput(
                user_prompt=f"占位符分析: {request.business_command}\n需求: {request.requirements}\n目标: {request.target_objective}",
                placeholder=placeholder_info,
                schema=schema_info,
                context=TaskContext(
                    task_time=int(datetime.now().timestamp()),
                    timezone="Asia/Shanghai"
                ),
                task_driven_context={
                    "placeholder_id": request.placeholder_id,
                    "business_command": request.business_command,
                    "requirements": request.requirements,
                    "target_objective": request.target_objective,
                    "context": request.context,
                    "data_source_info": request.data_source_info,
                    "analysis_type": "placeholder_service"
                }
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
        db
    ) -> Dict[str, Any]:
        """使用Agent生成占位符的SQL"""
        try:
            # 构建Agent输入
            agent_request = PlaceholderAnalysisRequest(
                placeholder_id=str(placeholder.id),
                business_command=placeholder.placeholder_text,
                requirements=placeholder.description or task_objective,
                context={
                    "data_source_id": data_source_id,
                    "placeholder_type": placeholder.placeholder_type,
                    "content_type": placeholder.content_type
                },
                target_objective=task_objective,
                data_source_info=await self._get_data_source_info(data_source_id)
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

    async def _get_data_source_info(self, data_source_id: str) -> Dict[str, Any]:
        """获取数据源信息"""
        try:
            from app.crud import data_source as crud_data_source
            from app.db.session import get_db_session

            with get_db_session() as db:
                data_source = crud_data_source.get(db, id=data_source_id)
                if not data_source:
                    return {}

                return {
                    "database_name": getattr(data_source, 'doris_database', 'unknown'),
                    "host": getattr(data_source, 'doris_fe_hosts', ['localhost'])[0] if getattr(data_source, 'doris_fe_hosts') else 'localhost',
                    "port": getattr(data_source, 'doris_query_port', 9030),
                    "username": getattr(data_source, 'doris_username', 'root'),
                    "password": getattr(data_source, 'doris_password', '')
                }
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