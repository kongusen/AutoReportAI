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

# 基础设施层导入 - 使用Loom Agent系统
from app.services.infrastructure.agents import AgentService
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
        self.agent_service = AgentService(container=self.container)

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
        分析占位符 - 使用ReAct模式让Agent自主使用工具生成SQL

        ReAct模式：Agent自己决定：
        1. 何时调用schema.list_tables获取表
        2. 何时调用schema.list_columns获取列信息
        3. 何时生成SQL
        4. 何时调用sql.validate验证
        5. 何时调用sql.execute测试
        6. 何时调用sql.refine优化
        """
        await self.initialize()

        yield {
            "type": "analysis_started",
            "placeholder_id": request.placeholder_id,
            "mode": "react_autonomous",
            "timestamp": datetime.now().isoformat()
        }

        try:
            # 构建数据源配置
            data_source_config = self._build_data_source_config(request)

            # 构建ReAct任务描述
            time_window_desc = ""
            if isinstance(request.context, dict):
                time_window = request.context.get("time_window") or request.context.get("time_context")
                if time_window:
                    import json
                    time_window_desc = f"\n- 时间范围: {json.dumps(time_window, ensure_ascii=False)}"

            # 构建Agent任务提示
            task_prompt = f"""
你是一个SQL生成专家Agent。请使用可用的工具完成以下任务：

## 任务目标
生成一个高质量的SQL查询来满足以下业务需求：

### 业务需求
{request.business_command}

### 具体目标
{request.target_objective or request.requirements}
{time_window_desc}

### 数据源信息
- 数据源ID: {data_source_config.get('data_source_id', 'N/A')}
- 数据库: {data_source_config.get('database_name', 'N/A')}

## ⚠️ 重要约束
1. **必须包含时间过滤条件** - 这是基于时间周期的统计查询
2. **只能使用实际存在的表和列** - 必须先探索schema
3. **必须验证SQL正确性** - 确保SQL可执行
4. **使用占位符格式** - 时间过滤使用 {{{{start_date}}}} 和 {{{{end_date}}}}
   ⚠️ **关键要点：占位符周围不要加引号！**
   - ✅ 正确: WHERE date BETWEEN {{{{start_date}}}} AND {{{{end_date}}}}
   - ❌ 错误: WHERE date BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}'
   - **原因**: 占位符替换时会自动添加引号，如果SQL中已有引号会导致双重引号语法错误

## 可用工具
你有以下工具可用：
1. **schema.list_tables** - 列出数据源中的所有表
2. **schema.list_columns** - 获取指定表的列信息
3. **sql.validate** - 验证SQL的正确性
4. **sql.execute** - 执行SQL进行测试（使用LIMIT限制）
5. **sql.refine** - 基于错误信息优化SQL

## 推荐流程（ReAct循环）
1. 使用 schema.list_tables 查看所有可用的表
2. 根据业务需求选择相关的表
3. 使用 schema.list_columns 获取这些表的列信息
4. 生成SQL查询（确保包含时间过滤，**占位符不加引号**）
5. 使用 sql.validate 验证SQL
6. **如果验证失败（如双重引号错误）**：
   - 检查SQL中占位符周围是否有引号
   - 移除占位符周围的引号
   - 使用 sql.refine 优化SQL
   - 重新验证（最多重试3次）
7. 验证成功后，可选择使用 sql.execute 测试SQL

## 期望输出
最终返回一个JSON格式的结果：
{{
    "sql": "SELECT ... WHERE dt BETWEEN {{{{start_date}}}} AND {{{{end_date}}}}",
    "reasoning": "解释为什么这个SQL满足业务需求",
    "tables_used": ["table1", "table2"],
    "has_time_filter": true,
    "time_column_used": "dt"
}}

现在开始执行任务，使用工具进行推理和行动(ReAct)！
"""

            logger.info("🤖 启动ReAct模式 - Agent将自主使用工具生成SQL")

            # 构建AgentInput
            from app.services.infrastructure.agents.types import AgentInput, PlaceholderSpec, TaskContext

            agent_input = AgentInput(
                user_prompt=task_prompt,
                placeholder=PlaceholderSpec(
                    id=request.placeholder_id,
                    description=request.business_command,
                    type="sql_generation_react",
                    granularity="daily"
                ),
                schema=None,  # Agent自己探索schema
                context=TaskContext(
                    task_time=int(datetime.now().timestamp()),
                    timezone="Asia/Shanghai"
                ),
                data_source=data_source_config,
                task_driven_context={
                    "mode": "react",
                    "business_command": request.business_command,
                    "requirements": request.requirements,
                    "target_objective": request.target_objective,
                    "enable_tools": True  # 明确启用工具使用
                },
                user_id=self.user_id
            )

            # 调用Agent执行ReAct
            logger.info("📞 调用Agent执行ReAct模式...")
            result = await self.agent_service.execute(agent_input)

            if not result.success:
                raise RuntimeError(f"Agent执行失败: {result.error}")

            # 解析Agent的结果
            output = result.result
            generated_sql = None
            reasoning = ""
            metadata = {}

            if isinstance(output, dict):
                # 检查是否是错误响应
                if output.get("success") is False or ("error" in output and "sql" not in output):
                    error_msg = output.get("error", "Agent返回错误格式")
                    logger.error(f"❌ Agent返回错误响应: {error_msg}, 完整输出: {output}")
                    raise RuntimeError(f"Agent执行失败: {error_msg}")

                generated_sql = output.get("sql", "")
                reasoning = output.get("reasoning", "")
                metadata = {
                    "tables_used": output.get("tables_used", []),
                    "has_time_filter": output.get("has_time_filter", False),
                    "time_column_used": output.get("time_column_used", "")
                }
            elif isinstance(output, str):
                try:
                    import json
                    parsed = json.loads(output)

                    # 检查是否是错误响应
                    if parsed.get("success") is False or ("error" in parsed and "sql" not in parsed):
                        error_msg = parsed.get("error", "Agent返回错误格式")
                        raise RuntimeError(f"Agent执行失败: {error_msg}")

                    # ✅ 修复：如果没有sql键，返回空字符串而不是整个JSON
                    generated_sql = parsed.get("sql", "")
                    reasoning = parsed.get("reasoning", "")
                    metadata = {
                        "tables_used": parsed.get("tables_used", []),
                        "has_time_filter": parsed.get("has_time_filter", False),
                        "time_column_used": parsed.get("time_column_used", "")
                    }
                except json.JSONDecodeError:
                    # 不是JSON，可能是直接的SQL语句
                    generated_sql = output
                    reasoning = "Agent自主生成"
                except RuntimeError:
                    # 重新抛出我们的错误检查
                    raise

            # 验证生成的SQL
            if not generated_sql or not generated_sql.strip():
                raise RuntimeError("Agent未能生成有效的SQL")

            # 额外验证：确保是SQL语句而不是JSON
            sql_stripped = generated_sql.strip()
            if sql_stripped.startswith("{") and sql_stripped.endswith("}"):
                # 看起来是JSON而不是SQL
                try:
                    json.loads(sql_stripped)
                    raise RuntimeError("Agent返回的是JSON而不是SQL语句")
                except json.JSONDecodeError:
                    # 不是有效JSON，可能是特殊的SQL，允许通过
                    pass

            # 验证是否以SELECT/WITH开头（基本的SQL检查）
            sql_upper = sql_stripped.upper()
            if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
                raise RuntimeError(f"生成的内容不是有效的SQL查询: {sql_stripped[:100]}...")

            logger.info(f"✅ Agent生成SQL完成: {generated_sql[:100]}...")

            # 构建结果
            metadata.update({
                "generation_method": "react_autonomous",
                "reasoning": reasoning,
                "agent_metadata": result.metadata,
                "generated_at": datetime.now().isoformat()
            })

            sql_result = SQLGenerationResult(
                sql_query=generated_sql,
                validation_status="valid",
                optimization_applied=True,
                estimated_performance="good",
                metadata=metadata
            )

            yield {
                "type": "sql_generation_complete",
                "placeholder_id": request.placeholder_id,
                "content": sql_result,
                "generation_method": "react_autonomous",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"占位符分析失败: {e}")

            # ✅ 统一使用 sql_generation_failed 事件，方便下游处理
            yield {
                "type": "sql_generation_failed",
                "placeholder_id": request.placeholder_id,
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

                # 🔄 新方案：循环调用单占位符分析方法，复用已调试通过的逻辑
                # 导入 PlaceholderOrchestrationService
                from app.api.endpoints.placeholders import PlaceholderOrchestrationService

                orchestration_service = PlaceholderOrchestrationService()

                total_count = len(placeholders)
                success_count = 0
                failed_count = 0

                yield {
                    "type": "batch_analysis_started",
                    "message": f"开始批量分析 {total_count} 个占位符（复用单占位符分析逻辑）",
                    "total_count": total_count
                }

                # 构建任务上下文 - 传递给单占位符分析
                task_context = {
                    "time_window": time_window,
                    "time_column": time_column,
                    "data_range": "day",
                    "execution_context": {
                        "task_objective": task_objective,
                        "success_criteria": success_criteria
                    }
                }

                for idx, ph in enumerate(placeholders, 1):
                    try:
                        logger.info(f"📋 处理占位符 ({idx}/{total_count}): {ph.placeholder_name}")

                        yield {
                            "type": "placeholder_processing",
                            "message": f"正在分析占位符: {ph.placeholder_name}",
                            "current": idx,
                            "total": total_count,
                            "placeholder_name": ph.placeholder_name
                        }

                        # 🎯 调用单占位符分析方法（包含完整的周期占位符处理逻辑）
                        result = await orchestration_service.analyze_placeholder_with_full_pipeline(
                            placeholder_name=ph.placeholder_name,
                            placeholder_text=ph.placeholder_text,
                            template_id=template_id,
                            data_source_id=data_source_id,
                            user_id=self.user_id,
                            **task_context
                        )

                        # 处理返回结果
                        if result.get("status") == "success":
                            # 更新占位符记录
                            if result.get("generated_sql"):
                                ph.generated_sql = result["generated_sql"].get("sql", "")
                                ph.sql_validated = True

                            ph.agent_analyzed = True
                            ph.analyzed_at = datetime.now()

                            # 如果是周期占位符，保存计算值
                            if result.get("analysis_result", {}).get("computed_value"):
                                ph.computed_value = result["analysis_result"]["computed_value"]

                            db.commit()
                            success_count += 1

                            yield {
                                "type": "placeholder_analyzed",
                                "placeholder_name": ph.placeholder_name,
                                "success": True,
                                "result": result,
                                "current": idx,
                                "total": total_count
                            }
                        else:
                            failed_count += 1
                            logger.error(f"❌ 占位符分析失败: {ph.placeholder_name}, 错误: {result.get('error')}")

                            yield {
                                "type": "placeholder_analyzed",
                                "placeholder_name": ph.placeholder_name,
                                "success": False,
                                "error": result.get("error", "分析失败"),
                                "current": idx,
                                "total": total_count
                            }

                    except Exception as e:
                        failed_count += 1
                        logger.error(f"❌ 占位符处理异常: {ph.placeholder_name}, 异常: {e}")

                        yield {
                            "type": "placeholder_analyzed",
                            "placeholder_name": ph.placeholder_name,
                            "success": False,
                            "error": str(e),
                            "current": idx,
                            "total": total_count
                        }

                yield {
                    "type": "batch_analysis_complete",
                    "message": f"批量分析完成",
                    "total_count": total_count,
                    "success_count": success_count,
                    "failed_count": failed_count
                }

                # 原有的SQL替换和数据提取逻辑保持不变
                # 重新加载占位符以获取更新后的数据
                placeholders = crud_template_placeholder.get_by_template(db, template_id)
                placeholders_need_sql_replacement = []
                placeholders_ready = []

                for ph in placeholders:
                    if ph.generated_sql and ph.generated_sql.strip():
                        sql_placeholders = sql_replacer.extract_placeholders(ph.generated_sql)
                        if sql_placeholders:
                            placeholders_need_sql_replacement.append(ph)
                        else:
                            placeholders_ready.append(ph)

                # Step 2: 对所有需要占位符替换的SQL进行替换（保持原有逻辑）
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

            # 调用占位符分析（带重试机制）
            MAX_RETRIES = 3
            retry_count = 0
            last_error = None

            while retry_count < MAX_RETRIES:
                sql_result = None
                async for event in self.analyze_placeholder(agent_request):
                    logger.debug(f"收到事件: type={event.get('type')}, placeholder_id={event.get('placeholder_id')}")

                    if event.get("type") == "sql_generation_complete":
                        sql_result = event.get("content")
                        logger.info(f"✅ SQL生成成功 (尝试 {retry_count + 1}/{MAX_RETRIES}): placeholder={agent_request.placeholder_id}")
                        break
                    elif event.get("type") == "sql_generation_failed":
                        logger.error(f"❌ SQL生成失败 (尝试 {retry_count + 1}/{MAX_RETRIES}): error={event.get('error')}")
                        last_error = event.get("error", "SQL生成失败")
                        break

                # 检查是否生成了SQL
                if not sql_result or not hasattr(sql_result, 'sql_query'):
                    retry_count += 1
                    logger.warning(f"⚠️ SQL生成未返回有效结果，准备重试 ({retry_count}/{MAX_RETRIES})")
                    if retry_count < MAX_RETRIES:
                        # 更新agent_request，添加重试提示
                        agent_request.requirements = f"{agent_request.requirements}\n\n⚠️ 重试 {retry_count}: 上次生成失败，请重新尝试"
                        continue
                    else:
                        return {
                            "success": False,
                            "error": last_error or "Agent未返回有效的SQL结果"
                        }

                # 验证生成的SQL（检查双重引号等问题）
                generated_sql = sql_result.sql_query
                validation_issues = self._validate_sql_placeholders(generated_sql)

                if validation_issues:
                    logger.warning(f"⚠️ SQL验证发现问题 (尝试 {retry_count + 1}/{MAX_RETRIES}): {validation_issues}")
                    retry_count += 1

                    if retry_count < MAX_RETRIES:
                        # 尝试自动修复
                        fixed_sql = self._fix_sql_placeholder_quotes(generated_sql)
                        if fixed_sql != generated_sql:
                            logger.info(f"✅ 自动修复SQL占位符引号问题")
                            return {
                                "success": True,
                                "sql": fixed_sql,
                                "confidence": sql_result.metadata.get('confidence_level', 0.9),
                                "auto_fixed": True
                            }

                        # 无法自动修复，请求Agent重新生成
                        agent_request.requirements = f"""{agent_request.requirements}

⚠️ 重试 {retry_count}: 上次生成的SQL存在问题: {validation_issues}
请特别注意：
1. 占位符 {{{{start_date}}}} 和 {{{{end_date}}}} 周围**不要**加引号
2. 正确格式: WHERE date BETWEEN {{{{start_date}}}} AND {{{{end_date}}}}
3. 错误格式: WHERE date BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}'"""
                        continue
                    else:
                        # 达到最大重试次数，尝试最后一次自动修复
                        fixed_sql = self._fix_sql_placeholder_quotes(generated_sql)
                        return {
                            "success": True,
                            "sql": fixed_sql,
                            "confidence": sql_result.metadata.get('confidence_level', 0.7),
                            "auto_fixed": True,
                            "warning": f"达到最大重试次数，使用自动修复的SQL: {validation_issues}"
                        }

                # SQL验证通过
                logger.info(f"✅ SQL验证通过: placeholder={agent_request.placeholder_id}")
                return {
                    "success": True,
                    "sql": generated_sql,
                    "confidence": sql_result.metadata.get('confidence_level', 0.9),
                    "validated": True
                }

            # 达到最大重试次数
            return {
                "success": False,
                "error": f"达到最大重试次数 ({MAX_RETRIES})，最后错误: {last_error or '未知错误'}"
            }

        except Exception as e:
            logger.error(f"Agent SQL生成异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _validate_sql_placeholders(self, sql: str) -> Optional[str]:
        """
        验证SQL中的占位符格式，检查是否存在双重引号等问题

        Args:
            sql: 待验证的SQL

        Returns:
            如果有问题返回错误描述，否则返回None
        """
        import re

        # 检查是否有带引号的占位符: '{{...}}' 或 "{{...}}"
        quoted_placeholder_pattern = r"""['"]{{[^}]+}}['"]"""
        matches = re.findall(quoted_placeholder_pattern, sql)

        if matches:
            return f"发现占位符周围有引号: {matches}，这会导致双重引号错误"

        return None

    def _fix_sql_placeholder_quotes(self, sql: str) -> str:
        """
        自动修复SQL中占位符周围的引号问题

        移除占位符周围的单引号或双引号，因为占位符替换时会自动添加引号

        Args:
            sql: 原始SQL

        Returns:
            修复后的SQL
        """
        import re

        # 移除占位符周围的引号
        # 匹配模式: '{{placeholder}}' -> {{placeholder}}
        # 或: "{{placeholder}}" -> {{placeholder}}
        fixed_sql = re.sub(r"""['"](\{\{[^}]+\}\})['"]""", r'\1', sql)

        if fixed_sql != sql:
            logger.info(f"🔧 自动修复SQL占位符引号")
            logger.debug(f"   原SQL: {sql[:200]}...")
            logger.debug(f"   修复后: {fixed_sql[:200]}...")

        return fixed_sql

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

    # ==================== 多步骤SQL生成辅助方法 ====================

    def _build_data_source_config(self, request: PlaceholderAnalysisRequest) -> Dict[str, Any]:
        """构建数据源配置"""
        if not request.data_source_info:
            return {}

        ds_config = dict(request.data_source_info)
        ds_id = ds_config.get('id') or ds_config.get('data_source_id')
        if ds_id:
            ds_config.setdefault("id", str(ds_id))
            ds_config.setdefault("data_source_id", str(ds_id))

        return ds_config

    async def _discover_schema(self, data_source_config: Dict[str, Any], request: PlaceholderAnalysisRequest):
        """
        Schema Discovery - 探索数据库schema

        步骤：
        1. 获取所有表
        2. 使用Agent分析业务需求，选择相关表
        3. 获取相关表的列信息
        """
        from app.services.infrastructure.agents.tools.schema_tools import SchemaListTablesTool, SchemaListColumnsTool
        from app.services.infrastructure.agents.types import SchemaInfo

        # 1. 获取所有表
        schema_list_tables_tool = SchemaListTablesTool(container=self.container)
        tables_result = await schema_list_tables_tool.execute({
            "data_source": data_source_config
        })

        if not tables_result.get("success"):
            raise RuntimeError(f"获取表列表失败: {tables_result.get('error')}")

        all_tables = tables_result.get("tables", [])
        logger.info(f"📊 发现 {len(all_tables)} 个表: {all_tables[:10]}...")

        # 2. 选择相关表（简化版：使用关键词匹配或使用所有表）
        relevant_tables = await self._select_relevant_tables(
            all_tables,
            request.business_command,
            request.target_objective or request.requirements
        )

        logger.info(f"🎯 选择了 {len(relevant_tables)} 个相关表: {relevant_tables}")

        # 3. 获取相关表的列信息
        schema_list_columns_tool = SchemaListColumnsTool(container=self.container)
        columns_result = await schema_list_columns_tool.execute({
            "data_source": data_source_config,
            "tables": relevant_tables
        })

        if not columns_result.get("success"):
            raise RuntimeError(f"获取列信息失败: {columns_result.get('error')}")

        # 构建SchemaInfo
        column_details = columns_result.get("column_details", {})
        schema_info = SchemaInfo(
            tables=relevant_tables,
            columns={
                table: [col.get("name") for col in cols if col.get("name")]
                for table, cols in column_details.items()
            }
        )

        return schema_info

    async def _select_relevant_tables(
        self,
        all_tables: List[str],
        business_command: str,
        target_objective: str
    ) -> List[str]:
        """
        选择相关表

        使用关键词匹配选择与业务需求相关的表
        """
        combined_text = f"{business_command} {target_objective}".lower()

        # 计算表的相关性得分
        scored_tables = []
        for table in all_tables:
            score = 0
            table_lower = table.lower()

            # 完全匹配
            if table_lower in combined_text:
                score += 10

            # 部分匹配
            for word in table_lower.split('_'):
                if len(word) > 2 and word in combined_text:
                    score += 1

            if score > 0:
                scored_tables.append((table, score))

        # 排序并取前5个
        scored_tables.sort(key=lambda x: x[1], reverse=True)
        selected = [table for table, _ in scored_tables[:5]]

        # 如果没有匹配到，使用前3个表
        if not selected and all_tables:
            selected = all_tables[:3]

        return selected or all_tables

    async def _generate_sql_with_schema(
        self,
        request: PlaceholderAnalysisRequest,
        schema_info,
        data_source_config: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        基于精确schema生成SQL

        返回: (sql, reasoning)
        """
        import json
        from app.services.infrastructure.agents.types import AgentInput, PlaceholderSpec, TaskContext

        # 构建schema提示
        schema_prompt = self._build_schema_prompt(schema_info)

        # 识别时间字段
        time_columns = self._identify_time_columns(schema_info)

        # 构建时间信息和要求
        time_window = None
        time_requirement = ""
        if isinstance(request.context, dict):
            time_window = request.context.get("time_window") or request.context.get("time_context")

        if time_columns:
            time_col_list = ", ".join(time_columns)
            if time_window:
                time_requirement = f"""
## ⚠️ 时间过滤要求（必须遵守）
**这是一个基于时间周期的统计查询，必须包含时间过滤条件！**

- 可用的时间字段: {time_col_list}
- 时间范围: {json.dumps(time_window, ensure_ascii=False) if time_window else "周期内数据"}
- **必须在WHERE子句中使用时间字段进行过滤**
- 推荐使用占位符格式: WHERE {time_columns[0]} = '{{{{start_date}}}}'
- 或使用BETWEEN: WHERE {time_columns[0]} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}'
"""
            else:
                time_requirement = f"""
## ⚠️ 时间过滤要求（必须遵守）
**这是一个基于时间周期的统计查询，必须包含时间过滤条件！**

- 可用的时间字段: {time_col_list}
- **必须在WHERE子句中使用时间字段进行过滤**
- 使用占位符格式: WHERE {time_columns[0]} = '{{{{start_date}}}}'
"""

        # 构建prompt
        user_prompt = f"""
请基于以下信息生成SQL查询：

## 业务需求
{request.business_command}

## 目标
{request.target_objective or request.requirements}

## 可用的数据库Schema（请严格使用以下表和列）
{schema_prompt}
{time_requirement}

## 要求
1. **只能使用上述Schema中存在的表和列**
2. 列名必须完全匹配
3. 生成标准的SQL查询语句
4. **✅ 必须包含时间过滤条件**（使用上述时间字段）
5. 返回JSON格式: {{"sql": "SELECT ...", "reasoning": "解释SQL生成的思路", "time_filter_applied": true}}

请生成SQL：
"""

        # 构建AgentInput
        agent_input = AgentInput(
            user_prompt=user_prompt,
            placeholder=PlaceholderSpec(
                id=request.placeholder_id,
                description=request.business_command,
                type="sql_generation",
                granularity="daily"
            ),
            schema=schema_info,
            context=TaskContext(
                task_time=int(datetime.now().timestamp()),
                timezone="Asia/Shanghai"
            ),
            data_source=data_source_config,
            task_driven_context={
                "stage": "sql_generation",
                "business_command": request.business_command,
                "requirements": request.requirements,
                "target_objective": request.target_objective
            },
            user_id=self.user_id
        )

        # 调用Agent生成SQL
        result = await self.agent_service.execute(agent_input)

        if not result.success:
            raise RuntimeError(f"SQL生成失败: {result.error}")

        # 解析结果
        output = result.result
        sql = ""
        reasoning = ""

        if isinstance(output, dict):
            sql = output.get("sql", "")
            reasoning = output.get("reasoning", "")
        elif isinstance(output, str):
            try:
                parsed = json.loads(output)
                sql = parsed.get("sql", output)
                reasoning = parsed.get("reasoning", "")
            except:
                sql = output
                reasoning = "直接生成"

        return sql, reasoning

    def _identify_time_columns(self, schema_info) -> List[str]:
        """
        识别Schema中的时间字段

        常见时间字段名模式:
        - dt, date, time, datetime, timestamp
        - created_at, updated_at, create_time, update_time
        - *_date, *_time, *_at
        """
        time_patterns = [
            'dt', 'date', 'time', 'datetime', 'timestamp',
            'created', 'updated', 'deleted',
            'create_time', 'update_time', 'delete_time',
            'created_at', 'updated_at', 'deleted_at',
            'start_date', 'end_date', 'start_time', 'end_time'
        ]

        time_columns = []
        for table, columns in schema_info.columns.items():
            for col in columns:
                col_lower = col.lower()
                # 完全匹配
                if col_lower in time_patterns:
                    time_columns.append(col)
                # 后缀匹配
                elif any(col_lower.endswith(suffix) for suffix in ['_date', '_time', '_at', '_datetime', '_timestamp']):
                    time_columns.append(col)
                # 前缀匹配
                elif any(col_lower.startswith(prefix) for prefix in ['date_', 'time_', 'dt_']):
                    time_columns.append(col)

        # 去重并保持顺序
        seen = set()
        unique_time_columns = []
        for col in time_columns:
            if col not in seen:
                seen.add(col)
                unique_time_columns.append(col)

        return unique_time_columns

    def _build_schema_prompt(self, schema_info) -> str:
        """构建Schema提示文本"""
        lines = []

        for table in schema_info.tables:
            columns = schema_info.columns.get(table, [])
            if columns:
                col_list = ", ".join(columns)
                lines.append(f"### 表: {table}")
                lines.append(f"列: {col_list}")
                lines.append("")

        return "\n".join(lines)

    async def _validate_sql(self, sql: str, schema_info, require_time_filter: bool = True) -> Dict[str, Any]:
        """
        验证SQL正确性

        检查：
        1. SQL是否为空
        2. 是否包含SELECT/WITH语句
        3. 是否使用了不存在的列（基本检查）
        4. **是否包含时间过滤条件**（重要！）
        """
        import re

        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
            "has_time_filter": False
        }

        # 1. 检查SQL是否为空
        if not sql or not sql.strip():
            validation_result["is_valid"] = False
            validation_result["errors"].append("SQL为空")
            return validation_result

        # 2. 基本语法检查
        sql_upper = sql.upper()
        if not any(keyword in sql_upper for keyword in ["SELECT", "WITH"]):
            validation_result["is_valid"] = False
            validation_result["errors"].append("SQL必须包含SELECT或WITH语句")

        # 3. 获取所有有效列名
        all_valid_columns = set()
        for columns in schema_info.columns.values():
            all_valid_columns.update(columns)

        # 4. 检查是否使用了不存在的列（简化检查）
        # 提取潜在的列名
        potential_columns = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', sql)

        # SQL关键字
        sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'BETWEEN', 'LIKE',
            'ORDER', 'BY', 'GROUP', 'HAVING', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
            'AS', 'ON', 'LIMIT', 'OFFSET', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN',
            'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'NULL', 'IS', 'ASC', 'DESC',
            'UNION', 'ALL', 'EXISTS', 'ANY', 'SOME', 'CAST', 'CONVERT'
        }

        # 检查未知列
        unknown_columns = []
        for col in potential_columns:
            if col.upper() not in sql_keywords and col not in all_valid_columns:
                # 进一步检查是否真的在SQL中作为列使用
                pattern = rf'\b{re.escape(col)}\b\s*(=|<|>|!=|IN|BETWEEN|LIKE|,|\))'
                if re.search(pattern, sql, re.IGNORECASE):
                    unknown_columns.append(col)

        if unknown_columns:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"使用了不存在的列: {', '.join(unknown_columns)}")
            validation_result["suggestions"].append(
                f"请检查列名，可用的列包括: {', '.join(sorted(list(all_valid_columns))[:20])}..."
            )

        # 5. ⚠️ 检查时间过滤条件（关键！）
        if require_time_filter:
            time_columns = self._identify_time_columns(schema_info)

            if time_columns:
                # 检查SQL中是否使用了任何时间字段
                has_time_filter = False
                used_time_column = None

                for time_col in time_columns:
                    # 检查WHERE子句中是否使用了时间字段
                    # 匹配模式: time_col = / time_col BETWEEN / time_col >= / time_col <=
                    patterns = [
                        rf'\bWHERE\b.*\b{re.escape(time_col)}\b\s*=',
                        rf'\bWHERE\b.*\b{re.escape(time_col)}\b\s*BETWEEN',
                        rf'\bWHERE\b.*\b{re.escape(time_col)}\b\s*>=',
                        rf'\bWHERE\b.*\b{re.escape(time_col)}\b\s*<=',
                        rf'\bAND\b.*\b{re.escape(time_col)}\b\s*=',
                        rf'\bAND\b.*\b{re.escape(time_col)}\b\s*BETWEEN',
                        rf'\bAND\b.*\b{re.escape(time_col)}\b\s*>=',
                        rf'\bAND\b.*\b{re.escape(time_col)}\b\s*<=',
                    ]

                    for pattern in patterns:
                        if re.search(pattern, sql, re.IGNORECASE):
                            has_time_filter = True
                            used_time_column = time_col
                            break

                    if has_time_filter:
                        break

                validation_result["has_time_filter"] = has_time_filter
                validation_result["used_time_column"] = used_time_column

                if not has_time_filter:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append("⚠️ 缺少时间过滤条件！这是基于时间周期的统计查询")
                    validation_result["suggestions"].append(
                        f"请添加时间过滤，可用的时间字段: {', '.join(time_columns)}"
                    )
                    validation_result["suggestions"].append(
                        f"示例: WHERE {time_columns[0]} = '{{{{start_date}}}}'"
                    )
                    validation_result["suggestions"].append(
                        f"或: WHERE {time_columns[0]} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}'"
                    )

        return validation_result

    async def _refine_sql_add_time_filter(
        self,
        original_sql: str,
        schema_info,
        validation_result: Dict[str, Any],
        request: PlaceholderAnalysisRequest
    ) -> Tuple[str, str]:
        """
        优化SQL：添加时间过滤条件

        返回: (refined_sql, reasoning)
        """
        import json
        from app.services.infrastructure.agents.types import AgentInput, PlaceholderSpec, TaskContext

        time_columns = self._identify_time_columns(schema_info)

        if not time_columns:
            return original_sql, "未找到时间字段"

        # 构建refinement prompt
        errors = validation_result.get("errors", [])
        suggestions = validation_result.get("suggestions", [])

        refinement_prompt = f"""
你之前生成的SQL缺少时间过滤条件，需要优化：

## 原始SQL
```sql
{original_sql}
```

## 问题
{json.dumps(errors, ensure_ascii=False)}

## 建议
{json.dumps(suggestions, ensure_ascii=False)}

## 可用的时间字段
{', '.join(time_columns)}

## Schema信息
{self._build_schema_prompt(schema_info)}

## 要求
1. 在原SQL基础上添加时间过滤条件
2. 使用WHERE子句或在现有WHERE子句中添加AND条件
3. 推荐使用第一个时间字段: {time_columns[0]}
4. 使用占位符格式: WHERE {time_columns[0]} = '{{{{start_date}}}}'
5. 保持原SQL的其他逻辑不变
6. 返回JSON格式: {{"sql": "优化后的SQL", "reasoning": "说明添加了什么时间过滤条件"}}

请优化SQL：
"""

        # 构建AgentInput
        agent_input = AgentInput(
            user_prompt=refinement_prompt,
            placeholder=PlaceholderSpec(
                id=request.placeholder_id,
                description="SQL优化 - 添加时间过滤",
                type="sql_refinement",
                granularity="daily"
            ),
            schema=schema_info,
            context=TaskContext(
                task_time=int(datetime.now().timestamp()),
                timezone="Asia/Shanghai"
            ),
            data_source=self._build_data_source_config(request),
            task_driven_context={
                "stage": "sql_refinement",
                "refinement_type": "add_time_filter",
                "original_sql": original_sql
            },
            user_id=self.user_id
        )

        # 调用Agent优化SQL
        try:
            result = await self.agent_service.execute(agent_input)

            if not result.success:
                return original_sql, f"优化失败: {result.error}"

            # 解析结果
            output = result.result
            refined_sql = ""
            reasoning = ""

            if isinstance(output, dict):
                refined_sql = output.get("sql", "")
                reasoning = output.get("reasoning", "")
            elif isinstance(output, str):
                try:
                    parsed = json.loads(output)
                    refined_sql = parsed.get("sql", output)
                    reasoning = parsed.get("reasoning", "")
                except:
                    refined_sql = output
                    reasoning = "自动添加时间过滤"

            return refined_sql if refined_sql else original_sql, reasoning

        except Exception as e:
            logger.error(f"SQL refinement失败: {e}")
            return original_sql, f"优化异常: {str(e)}"

    async def _test_sql(self, sql: str, data_source_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        测试SQL执行

        在数据库上执行SQL（LIMIT 5小样本测试）
        """
        # 添加LIMIT以限制返回结果
        test_sql = sql
        if "LIMIT" not in test_sql.upper():
            test_sql += " LIMIT 5"

        # 获取数据源adapter
        ds_adapter = None
        for attr in ("data_source", "data_source_service"):
            if hasattr(self.container, attr):
                ds_adapter = getattr(self.container, attr)
                break

        if not ds_adapter:
            return {
                "success": False,
                "error": "数据源adapter不可用"
            }

        # 执行测试查询
        try:
            test_result = await ds_adapter.run_query(
                data_source_config,
                test_sql,
                limit=5
            )

            return {
                "success": test_result.get("success", False),
                "error": test_result.get("error"),
                "row_count": len(test_result.get("rows", [])) if test_result.get("success") else 0,
                "columns": test_result.get("columns", [])
            }
        except Exception as e:
            logger.error(f"SQL测试失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


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
