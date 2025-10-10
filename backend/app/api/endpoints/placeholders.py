"""
统一的基于Agent基础设施的占位符API
充分利用现有的Agent系统、Domain服务和基础设施层能力
"""

import logging
from typing import Any, Dict, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio

from app import crud
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.base import APIResponse
from app.schemas.template_placeholder import (
    TemplatePlaceholder,
    TemplatePlaceholderCreate,
    TemplatePlaceholderUpdate
)
from app.schemas.frontend_adapters import (
    adapt_placeholder_for_frontend, adapt_error_for_frontend,
    adapt_analysis_progress_for_frontend
)
from app.utils.error_validation import (
    ParameterValidator, ValidationResult, ErrorResponseBuilder
)
from app.middleware.error_handling import APIErrorHandler, create_error_response

# 核心：使用现有的Agent基础设施
from app.services.infrastructure.agents.facade import AgentFacade
from app.services.infrastructure.agents.types import (
    AgentInput,
    PlaceholderSpec,
    SchemaInfo,
    TaskContext,
    AgentConstraints,
)

# Domain层业务服务
from app.services.domain.placeholder.services.placeholder_analysis_domain_service import (
    PlaceholderAnalysisDomainService
)

# Application层服务协调
from app.services.application.placeholder.placeholder_service import PlaceholderApplicationService

from app.core.container import container

logger = logging.getLogger(__name__)
router = APIRouter()

class PlaceholderOrchestrationService:
    """
    占位符编排服务
    协调Domain层业务逻辑和Infrastructure层Agent系统
    """

    def __init__(self):
        # 使用现有的完整Agent系统
        self.agent_facade = AgentFacade(container)

        # Domain层业务服务
        self.domain_service = PlaceholderAnalysisDomainService()

        # Application层服务
        self.app_service = PlaceholderApplicationService()

        # Schema缓存 - 避免重复获取
        self._schema_cache = {}
        self._cache_ttl = 300  # 5分钟缓存

        logger.info("🚀 占位符编排服务初始化，基于完整Agent基础设施")

    async def analyze_placeholder_with_full_pipeline(
        self,
        placeholder_name: str,
        placeholder_text: str,
        template_id: str,
        data_source_id: str = None,
        template_context: Dict[str, Any] = None,
        user_id: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用完整的Agent Pipeline进行占位符分析

        Pipeline包括：
        1. Domain层业务需求分析
        2. Schema查询 (使用SchemaListColumnsTool)
        3. 智能SQL生成 (使用SQLDraftTool + 语义识别)
        4. SQL验证优化 (使用SQLValidateTool + SQLRefineTool)
        5. 可选SQL执行测试 (使用SQLExecuteTool)
        6. 结果持久化和缓存
        """

        try:
            logger.info(f"🔍 启动完整Agent Pipeline分析: {placeholder_name}")

            # ==========================================
            # 前置检查: 周期性占位符特殊处理
            # ==========================================
            if self._is_period_placeholder(placeholder_text):
                logger.info(f"🕐 检测到周期性占位符，使用专门处理逻辑: {placeholder_name}")
                period_result = await self._handle_period_placeholder(
                    placeholder_name=placeholder_name,
                    placeholder_text=placeholder_text,
                    template_id=template_id,
                    template_context=template_context,
                    **kwargs
                )

                # 包装周期性占位符结果为APIResponse格式
                logger.info(f"🔧 period_result类型: {type(period_result)}, 内容预览: {str(period_result)[:200]}")
                if period_result.get("status") == "success":
                    try:
                        # 构建与普通占位符相同的前端适配结果
                        placeholder_dict = {
                            "name": placeholder_name,
                            "text": placeholder_text,
                            "kind": "period",
                            "priority": "normal",
                            "confidence_score": period_result.get("confidence_score", 1.0)
                        }

                        logger.info(f"🔧 调用 adapt_placeholder_for_frontend，输入: {placeholder_dict}")
                        adapted_placeholder = adapt_placeholder_for_frontend(placeholder_dict)
                        logger.info(f"🔧 adapt_placeholder_for_frontend 返回成功")

                        logger.info(f"🔧 调用 adapt_analysis_progress_for_frontend")
                        progress_info = adapt_analysis_progress_for_frontend(
                            current_step=1,
                            total_steps=1,
                            step_name="周期计算完成",
                            status="completed",
                            progress_percent=100.0
                        )
                        logger.info(f"🔧 adapt_analysis_progress_for_frontend 返回成功")

                    except Exception as adapt_error:
                        logger.error(f"🔧 前端适配函数调用失败: {adapt_error}")
                        import traceback
                        logger.error(f"🔧 适配错误堆栈: {traceback.format_exc()}")
                        raise adapt_error  # 不使用简化结构，直接抛出错误

                    try:
                        # 构建测试结果，用于前端测试结果组件显示
                        test_result_for_frontend = {
                            "success": True,
                            "result_type": "period_value",
                            "computed_value": period_result.get("analysis_result", {}).get("computed_value"),
                            "period_info": {
                                "start_date": period_result.get("analysis_result", {}).get("period_meta", {}).get("start_date"),
                                "end_date": period_result.get("analysis_result", {}).get("period_meta", {}).get("end_date"),
                                "period_type": period_result.get("analysis_result", {}).get("period_meta", {}).get("period"),
                                "display_value": period_result.get("analysis_result", {}).get("computed_value")
                            },
                            "message": f"周期计算完成，时间段：{period_result.get('analysis_result', {}).get('computed_value', '')}",
                            "execution_time_ms": 10
                        }

                        # 构建原始结果
                        raw_result = {
                            "placeholder": adapted_placeholder.dict() if hasattr(adapted_placeholder, 'dict') else adapted_placeholder,
                            "progress": progress_info.dict() if hasattr(progress_info, 'dict') else progress_info,
                            "analysis_result": period_result.get("analysis_result"),
                            "generated_sql": period_result.get("generated_sql"),
                            "test_result": test_result_for_frontend,  # 添加测试结果用于前端显示
                            "business_validation": {},  # 周期性占位符不需要业务验证
                            "analyzed_at": period_result.get("analyzed_at")
                        }

                        # 递归序列化所有datetime对象
                        frontend_result = self._serialize_datetime_objects(raw_result)
                        logger.info(f"🔧 构建 frontend_result 成功")
                    except Exception as result_error:
                        logger.error(f"🔧 构建 frontend_result 失败: {result_error}")
                        import traceback
                        logger.error(f"🔧 结果构建错误堆栈: {traceback.format_exc()}")
                        raise result_error  # 不使用简化结构，直接抛出错误

                    try:
                        logger.info(f"🔧 即将返回字典格式结果")
                        # 返回字典格式，而不是APIResponse对象
                        # 构建测试结果，包含计算出的周期值
                        test_result = {
                            "success": True,
                            "result_type": "period_value",
                            "computed_value": period_result.get("analysis_result", {}).get("computed_value"),
                            "period_info": {
                                "start_date": period_result.get("analysis_result", {}).get("period_meta", {}).get("start_date"),
                                "end_date": period_result.get("analysis_result", {}).get("period_meta", {}).get("end_date"),
                                "period_type": period_result.get("analysis_result", {}).get("period_meta", {}).get("period"),
                                "display_value": period_result.get("analysis_result", {}).get("computed_value")
                            },
                            "message": f"周期计算完成，时间段：{period_result.get('analysis_result', {}).get('computed_value', '')}"
                        }

                        dict_result = {
                            "status": "success",
                            "placeholder_name": placeholder_name,
                            "generated_sql": period_result.get("generated_sql", {}),
                            "analysis_result": period_result.get("analysis_result", {}),
                            "test_result": test_result,  # 添加测试结果用于前端显示
                            "confidence_score": period_result.get("confidence_score", 1.0),
                            "analyzed_at": period_result.get("analyzed_at"),
                            "context_used": {
                                "template_context": bool(template_context),
                                "period_calculation": True,
                                "pipeline_type": "period_handler"
                            },
                            "frontend_data": frontend_result  # 保留前端需要的数据
                        }
                        logger.info(f"🔧 字典格式结果创建成功")
                        return dict_result
                    except Exception as api_error:
                        logger.error(f"🔧 结果创建失败: {api_error}")
                        import traceback
                        logger.error(f"🔧 结果创建错误堆栈: {traceback.format_exc()}")
                        raise api_error
                else:
                    # 错误情况，返回字典格式
                    error_result = {
                        "status": "error",
                        "placeholder_name": placeholder_name,
                        "error": period_result.get("error", "周期性占位符处理失败"),
                        "generated_sql": {"sql": "", placeholder_name: ""},
                        "analysis_result": {
                            "description": "周期性占位符处理失败",
                            "analysis_type": "period_placeholder_error",
                            "suggestions": ["检查模板上下文", "验证时间参数"]
                        },
                        "confidence_score": 0.0,
                        "analyzed_at": period_result.get("analyzed_at"),
                        "context_used": {
                            "template_context": bool(template_context),
                            "period_calculation": False,
                            "pipeline_type": "period_handler_error"
                        }
                    }
                    return error_result

            # ==========================================
            # 第1步: Domain层业务需求分析
            # ==========================================
            # 规范化 template_context：
            # - 若为字符串（整份模板内容），提取“包含占位符的段落”作为 snippet，供下游参考
            # - 若非字典，仍保留 snippet，但用于调度/时间推断的 template_context 字段转为空字典，避免 .get 报错
            template_context_snippet = None
            if isinstance(template_context, str):
                try:
                    template_context_snippet = self._extract_placeholder_snippet(
                        template_context or "",
                        placeholder_text or "",
                        placeholder_name or ""
                    )
                except Exception as e:
                    logger.warning(f"提取模板段落失败: {e}")
                logger.warning(f"template_context 为字符串，已提取段落作为 snippet")
                template_context = {}
            elif template_context and not isinstance(template_context, dict):
                logger.warning(f"template_context 非字典类型({type(template_context)}), 已自动转换为空字典以确保安全")
                template_context = {}

            business_context = {
                "template_id": template_id,
                "data_source_id": data_source_id,
                "template_context": template_context or {},
                "execution_context": kwargs.get("execution_context", {}),
                "time_column": kwargs.get("time_column"),
                "data_range": kwargs.get("data_range", "day")
            }

            business_requirements = await self.domain_service.analyze_placeholder_business_requirements(
                placeholder_text=placeholder_text,
                business_context=business_context,
                user_id=user_id
            )

            logger.info(f"✅ 业务需求分析完成: {business_requirements.get('business_type')}")

            # ==========================================
            # 第2步: 构建Agent输入，利用现有工具链
            # ==========================================

            # 确定语义类型（用于SQLDraftTool的智能生成）
            semantic_type = self._map_business_to_semantic_type(business_requirements)

            # 构建Schema信息（通过DataSourceContext获取真实表结构）
            schema_info = await self._get_schema_from_data_source_context(user_id, data_source_id)
            logger.info(f"🔍 [AgentInput构建] Schema信息获取完成: 表数量={len(schema_info.tables) if schema_info else 0}")
            logger.debug(f"🔍 [AgentInput构建] 表名详情: {schema_info.tables if schema_info else []}")  # 改为debug级别

            # 构建任务上下文 - 为placeholder API提供默认调度信息
            from datetime import datetime, timedelta
            from app.utils.time_context import TimeContextManager

            # 为placeholder API提供默认的cron表达式和时间窗口
            default_cron = "0 9 * * *"  # 每天上午9点
            current_time = datetime.now()

            # 如果没有提供任务调度信息，使用默认值
            task_schedule = kwargs.get("task_schedule")
            if not task_schedule or not task_schedule.get("cron_expression"):
                # 构建默认调度信息
                time_manager = TimeContextManager()
                time_context = time_manager.build_task_time_context(default_cron, current_time)

                task_schedule = {
                    "cron_expression": default_cron,
                    "timezone": kwargs.get("timezone", "Asia/Shanghai"),
                    "execution_time": current_time.isoformat(),
                    "start_date": time_context.get("data_start_time"),
                    "end_date": time_context.get("data_end_time"),
                }

                logger.info(f"🕒 为placeholder API生成默认调度: {default_cron}, "
                           f"时间窗口: {task_schedule['start_date']} ~ {task_schedule['end_date']}")

            task_context = TaskContext(
                timezone=task_schedule.get("timezone", "Asia/Shanghai"),
                window={
                    "data_source_id": data_source_id,
                    "time_column": kwargs.get("time_column"),
                    "data_range": kwargs.get("data_range", "day"),
                    "task_schedule": task_schedule,
                    "start_date": task_schedule.get("start_date"),
                    "end_date": task_schedule.get("end_date"),
                    "cron_expression": task_schedule.get("cron_expression"),
                    "execution_time": task_schedule.get("execution_time")
                }
            )

            # 加载模板内容以提供更完整的上下文
            template_content = ""
            try:
                from app.db.session import get_db_session
                from app import crud

                with get_db_session() as db:
                    template_obj = crud.template.get(db, id=template_id)
                    if template_obj:
                        template_content = template_obj.content or ""
                        logger.info(f"✅ 加载模板内容: {len(template_content)} 字符")
                    else:
                        logger.warning(f"⚠️ 未找到模板: {template_id}")
            except Exception as e:
                logger.warning(f"⚠️ 加载模板内容失败: {e}")

            # 构建Agent输入 - 包含完整上下文信息
            agent_input = AgentInput(
                user_prompt=f"分析占位符'{placeholder_name}': {placeholder_text}",
                placeholder=PlaceholderSpec(
                    id=placeholder_name,
                    description=placeholder_text,
                    type=semantic_type,
                    granularity=business_requirements.get("time_sensitivity", "daily")
                ),
                schema=schema_info,
                context=task_context,
                constraints=AgentConstraints(
                    sql_only=True,
                    output_kind="sql",
                    max_attempts=3,
                    policy_row_limit=kwargs.get("row_limit", 1000)
                ),
                template_id=template_id,
                data_source={
                    "data_source_id": data_source_id,
                    "semantic_type": semantic_type,  # 传给SQLDraftTool
                    "business_requirements": business_requirements,
                    "tables": schema_info.tables if schema_info else [],  # 传递表信息
                    "available_tables": schema_info.tables if schema_info else [],  # 传递可用表信息
                },
                task_driven_context={
                    "template_context": template_context or {},
                    "template_context_snippet": template_context_snippet,
                    "template_content": template_content,  # 添加模板内容
                    "business_context": business_context,
                    "requirements": kwargs.get("requirements", ""),
                    "top_n": business_requirements.get("top_n"),  # 用于ranking类型

                    # 📋 重要：占位符上下文段落（为模型提供精确的文本上下文）
                    "placeholder_context_snippet": template_context_snippet,
                    "surrounding_text": template_context_snippet,  # 为模型提供周围文本信息
                    "context_extraction_success": bool(template_context_snippet),

                    # ⏰ 重要：时间调度和统计范围信息
                    "cron_expression": task_schedule.get("cron_expression", "0 9 * * *"),
                    "time_range": {
                        "start_date": task_schedule.get("start_date"),
                        "end_date": task_schedule.get("end_date"),
                        "time_column": kwargs.get("time_column"),
                        "timezone": task_schedule.get("timezone", "Asia/Shanghai")
                    },
                    "scheduling_info": {
                        "execution_time": task_schedule.get("execution_time"),
                        "schedule_type": self._infer_schedule_type(task_schedule.get("cron_expression", "0 9 * * *")),
                        "previous_period_desc": self._describe_previous_period(task_schedule.get("cron_expression", "0 9 * * *"))
                    },

                    # 🔍 Schema信息传递（确保模型能看到表结构）
                    "schema_context": {
                        "available_tables": schema_info.tables if schema_info else [],
                        "table_count": len(schema_info.tables) if schema_info else 0,
                        "schema_source": "DataSourceContextBuilder"
                    },

                    "placeholder_contexts": [  # 添加占位符上下文数组
                        {
                            "placeholder_name": placeholder_name,
                            "placeholder_text": placeholder_text,
                            "semantic_type": semantic_type,
                            "surrounding_context": template_context_snippet,  # 占位符周围的文本
                            "parsed_params": {
                                "top_n": business_requirements.get("top_n"),
                                "time_sensitivity": business_requirements.get("time_sensitivity")
                            }
                        }
                    ]
                },
                user_id=user_id
            )

            # ==========================================
            # 第3步: 执行Agent Pipeline - 使用任务验证智能模式
            # ==========================================
            logger.info(f"🤖 执行Agent Pipeline，语义类型: {semantic_type}")

            # 🎯 使用任务验证智能模式 - 统一的SQL验证和生成系统
            logger.info(f"🎯 使用任务验证智能模式 - 自动SQL健康检查与智能回退")

            agent_result = await self.agent_facade.execute_task_validation(agent_input)

            # 🔧 添加调试信息
            logger.info(f"🔧 [Debug] Agent执行结果: success={agent_result.success}")
            logger.info(f"🔧 [Debug] Agent result type: {type(agent_result.result)}")
            logger.info(f"🔧 [Debug] Agent metadata type: {type(agent_result.metadata)}")
            if agent_result.result:
                logger.info(f"🔧 [Debug] Agent result内容(前100字符): {str(agent_result.result)[:100]}")
            if isinstance(agent_result.metadata, dict):
                logger.info(f"🔧 [Debug] Agent metadata keys: {list(agent_result.metadata.keys())}")

            if not agent_result.success:
                logger.error(f"❌ Agent Pipeline执行失败: {agent_result.metadata}")

                # 🔄 新增：智能恢复机制
                recovery_result = await self._attempt_pipeline_recovery(
                    agent_input, agent_result, placeholder_name, semantic_type
                )

                # 安全地检查恢复结果
                if isinstance(recovery_result, dict) and recovery_result.get("recovered"):
                    logger.info(f"✅ Agent Pipeline已恢复: {recovery_result['method']}")
                    # 使用恢复后的结果继续处理
                    agent_result = recovery_result["result"]
                else:
                    # 尝试部分成功返回：若存在候选SQL，直接返回给前端显示，测试结果显示验证/执行状态
                    try:
                        meta = agent_result.metadata if isinstance(agent_result.metadata, dict) else {}
                        candidate_sql = agent_result.result or meta.get('final_sql') or meta.get('partial_result') or meta.get('current_sql')
                        if candidate_sql and isinstance(candidate_sql, str) and candidate_sql.strip():
                            # 构建增强的测试结果，确保前端能正确显示失败信息
                            existing_test_result = meta.get('test_result', {})
                            error_message = meta.get('error', '验证/执行未完成')

                            test_result = {
                                "executed": existing_test_result.get("executed", False),
                                "success": existing_test_result.get("executed", False) and existing_test_result.get("rows") is not None,
                                "rows": existing_test_result.get("rows", []),
                                "columns": existing_test_result.get("columns", []),
                                "row_count": existing_test_result.get("row_count", 0),
                                "data": existing_test_result.get("rows", []),  # 前端期望的字段名
                                "message": existing_test_result.get("message", error_message),
                                "error": error_message if not existing_test_result.get("executed", False) else existing_test_result.get("error"),
                                "execution_time_ms": existing_test_result.get("execution_time_ms", 0)
                            }

                            # 构造部分成功结果（status=partial）
                            partial = {
                                "status": "partial",
                                "placeholder_name": placeholder_name,
                                "generated_sql": {
                                    placeholder_name: candidate_sql,
                                    "sql": candidate_sql,
                                },
                                "test_result": test_result,
                                "analysis_result": {
                                    "description": "部分完成：已生成SQL，验证/执行信息如下",
                                    "analysis_type": "partial_agent_pipeline",
                                    "semantic_type": semantic_type,
                                    "analysis_summary": meta.get("analysis_summary", "已生成SQL，等待用户确认或后续执行")
                                },
                                "confidence_score": meta.get("quality_score", 0.7),
                                "analyzed_at": datetime.now().isoformat()
                            }

                            # 适配前端格式（与成功路径一致）
                            placeholder_dict = {
                                "text": placeholder_text,
                                "kind": partial.get("analysis_result", {}).get("semantic_type", "statistical"),
                                "confidence": partial.get("confidence_score", 0.7),
                                "needs_reanalysis": False
                            }
                            try:
                                adapted_placeholder = adapt_placeholder_for_frontend(placeholder_dict)
                            except Exception:
                                adapted_placeholder = type("_Shim", (), {"dict": lambda self=None: {
                                    "text": placeholder_text,
                                    "kind": placeholder_dict.get("kind", "statistical"),
                                    "display_name": placeholder_dict.get("kind", "statistical"),
                                    "description": "",
                                    "status": "completed",
                                    "confidence": placeholder_dict.get("confidence", 0.7),
                                    "needs_reanalysis": False,
                                    "badge_color": "default",
                                    "icon": None,
                                    "tooltip": None
                                }})()

                            progress_info = adapt_analysis_progress_for_frontend(
                                current_step=3,
                                total_steps=4,
                                step_name="已生成SQL，待执行",
                                status="running",
                                progress_percent=75.0
                            )

                            frontend_result = {
                                "placeholder": adapted_placeholder.dict(),
                                "progress": progress_info.dict(),
                                "analysis_result": partial.get("analysis_result"),
                                "generated_sql": partial.get("generated_sql"),
                                "test_result": partial.get("test_result"),
                                "analyzed_at": partial.get("analyzed_at")
                            }

                            frontend_result = _orchestration_service._serialize_datetime_objects(frontend_result)
                            return APIResponse(
                                success=True,
                                data=frontend_result,
                                message=f"已生成SQL（部分完成）: {placeholder_name}"
                            )
                    except Exception as e:
                        logger.warning(f"构建部分成功结果失败: {e}")

                    # 恢复失败且无候选SQL：返回增强的错误信息
                    return self._create_enhanced_error_result(
                        placeholder_name,
                        agent_result.metadata if isinstance(agent_result.metadata, dict) else {},
                        recovery_result.get("recovery_attempts", []) if isinstance(recovery_result, dict) else []
                    )

            # ==========================================
            # 第4步: 结果处理和增强
            # ==========================================

            # 从Agent结果中提取SQL和元数据
            generated_sql = agent_result.result
            agent_metadata = agent_result.metadata if isinstance(agent_result.metadata, dict) else {}

            # 🔧 添加成功路径调试信息
            logger.info(f"🔧 [Debug] 进入成功处理分支")
            logger.info(f"🔧 [Debug] 提取的SQL: {generated_sql}")
            logger.info(f"🔧 [Debug] agent_metadata keys: {list(agent_metadata.keys()) if agent_metadata else 'empty'}")

            # 🔍 调试：查看execution_summary和observations的内容
            if "execution_summary" in agent_metadata:
                logger.info(f"🔍 [Debug] execution_summary: {agent_metadata['execution_summary']}")
            if "observations" in agent_metadata:
                logger.info(f"🔍 [Debug] observations: {agent_metadata['observations']}")

            # 提取测试结果（如果有）
            # 🔑 关键修复：从execution_summary或observations中提取SQL执行结果
            test_result = agent_metadata.get("test_result")

            # 策略1: 从execution_summary提取
            if not test_result and "execution_summary" in agent_metadata:
                exec_summary = agent_metadata.get("execution_summary", "")
                logger.info(f"🔍 [Debug] 尝试从execution_summary提取，内容: {exec_summary}")
                # 检查是否包含成功执行的关键词
                if isinstance(exec_summary, str) and ("成功" in exec_summary or "返回" in exec_summary or "rows" in exec_summary.lower()):
                    test_result = {
                        "executed": True,
                        "success": True,
                        "message": exec_summary,
                        "source": "execution_summary"
                    }
                    logger.info(f"✅ [Debug] 从execution_summary提取到测试结果")

            # 策略2: 从observations提取（observations是字符串列表）
            if not test_result and "observations" in agent_metadata:
                observations = agent_metadata.get("observations", [])
                logger.info(f"🔍 [Debug] 检查observations，类型: {type(observations)}, 数量: {len(observations) if isinstance(observations, list) else 'N/A'}")

                # observations是字符串列表，查找包含"sql.execute"或"执行SQL"的记录
                for idx, obs in enumerate(observations):
                    obs_str = str(obs)
                    if "sql.execute" in obs_str or "执行SQL" in obs_str or "MySQL查询执行成功" in obs_str:
                        # 判断是否成功
                        is_success = "成功" in obs_str or "返回" in obs_str
                        test_result = {
                            "executed": True,
                            "success": is_success,
                            "message": obs_str,
                            "source": f"observations[{idx}]"
                        }
                        logger.info(f"✅ [Debug] 从observations[{idx}]提取到测试结果: {obs_str[:100]}")
                        break

            # 策略3: 如果PTAV成功但没有明确的test_result，推断为已执行成功
            if not test_result and agent_result.success and generated_sql:
                # Agent成功返回了SQL，且是PTAV模式（有observations），推断已执行
                if agent_metadata.get("observations"):
                    test_result = {
                        "executed": True,
                        "success": True,
                        "message": "Agent Pipeline成功生成并验证SQL",
                        "source": "inferred_from_success"
                    }
                    logger.info(f"✅ [Debug] 从Agent成功状态推断测试结果")

            # 最后的默认值
            if not test_result:
                test_result = {
                    "executed": False,
                    "success": False,
                    "message": "未找到SQL执行结果"
                }
                logger.warning(f"⚠️ [Debug] 未能从agent_metadata中提取测试结果")

            # Domain层业务规则验证
            validation_result = self.domain_service.validate_placeholder_business_rules(
                placeholder_text=placeholder_text,
                template_context=template_context or {},
                data_source_context={"data_source_id": data_source_id}
            )

            # 构建完整结果
            result = {
                "status": "success",
                "placeholder_name": placeholder_name,
                "generated_sql": {
                    placeholder_name: generated_sql,
                    "sql": generated_sql,
                },
                "test_result": test_result,  # 新增：包含执行结果
                "analysis_result": {
                    "description": "基于完整Agent基础设施的智能分析",
                    "analysis_type": "full_agent_pipeline",
                    "semantic_type": semantic_type,
                    "business_requirements": business_requirements,
                    "analysis_summary": agent_metadata.get("analysis_summary", "Agent Pipeline分析完成"),
                    "suggestions": agent_metadata.get("suggestions", []),
                    "execution_stats": {
                        "tools_used": agent_metadata.get("tools_used", []),
                        "execution_time_ms": agent_metadata.get("execution_time_ms", 0),
                        "agent_facade_used": True,
                        "domain_service_used": True,
                        "steps_executed": agent_metadata.get("steps_executed", [])
                    }
                },
                "business_validation": validation_result,
                "confidence_score": self._calculate_confidence_score(agent_result, business_requirements),
                "analyzed_at": datetime.now().isoformat(),
                "context_used": {
                    "template_context": bool(template_context),
                    "data_source_info": bool(data_source_id),
                    "business_analysis": True,
                    "agent_pipeline": True,
                    "tools_chain": agent_metadata.get("tools_used", [])
                }
            }

            logger.info(f"✅ 完整Agent Pipeline分析成功: {placeholder_name}")
            logger.info(f"🔧 [Debug] 最终返回结果keys: {list(result.keys())}")
            logger.info(f"🔧 [Debug] generated_sql结构: {type(result.get('generated_sql'))}")
            return result

        except Exception as e:
            logger.error(f"❌ Agent Pipeline分析异常: {e}")
            return self._create_error_result(placeholder_name, str(e))

    def _map_business_to_semantic_type(self, business_requirements: Dict[str, Any]) -> str:
        """将业务需求映射到Agent工具的语义类型"""
        business_type = business_requirements.get("business_type", "").lower()
        semantic_intent = business_requirements.get("semantic_intent", "").lower()

        # 映射到SQLDraftTool支持的语义类型
        if "ranking" in business_type or "top" in semantic_intent or "排行" in semantic_intent:
            return "ranking"
        elif "compare" in business_type or "对比" in semantic_intent or "比较" in semantic_intent:
            return "compare"
        elif "period" in business_type or "周期" in semantic_intent or "时间" in semantic_intent:
            return "period"
        elif "chart" in business_type or "图表" in semantic_intent:
            return "chart"
        else:
            return "stat"  # 默认统计类型

    def _calculate_confidence_score(self, agent_result, business_requirements: Dict[str, Any]) -> float:
        """计算置信度分数"""
        base_score = 0.8

        # Agent执行成功加分
        if agent_result.success:
            base_score += 0.1

        # 业务需求明确度加分
        if business_requirements.get("priority") == "high":
            base_score += 0.05

        # 语义识别准确性加分
        if business_requirements.get("semantic_intent"):
            base_score += 0.05

        return min(base_score, 1.0)

    def _infer_schedule_type(self, cron_expression: str) -> str:
        """根据cron表达式推断调度类型"""
        try:
            parts = cron_expression.split()
            if len(parts) < 5:
                return "daily"

            minute, hour, dom, month, dow = parts[:5]

            # 指定了星期（如 0 9 * * 1），视为每周
            if dow not in ('*', '?'):
                return "weekly"
            # 指定了日期（如 0 9 1 * *），视为每月
            if dom not in ('*', '?'):
                return "monthly"
            # 指定了月份（如 0 0 1 1 *），视为每年
            if month not in ('*', '?'):
                return "yearly"
            return "daily"
        except Exception:
            return "daily"

    def _describe_previous_period(self, cron_expression: str) -> str:
        """描述前一个统计周期"""
        schedule_type = self._infer_schedule_type(cron_expression)

        descriptions = {
            "daily": "统计昨天的数据 (前一天)",
            "weekly": "统计上周的数据 (上周一至上周日)",
            "monthly": "统计上个月的数据 (上月1日至上月最后一天)",
            "yearly": "统计去年的数据 (去年1月1日至12月31日)"
        }

        return descriptions.get(schedule_type, "统计前一个周期的数据")

    async def _get_schema_from_data_source_context(self, user_id: str, data_source_id: str = None) -> SchemaInfo:
        """通过DataSourceContext获取Schema信息，带缓存机制"""
        logger.info(f"🔍 [Schema获取] 开始获取Schema: user_id={user_id}, data_source_id={data_source_id}")

        if not data_source_id:
            logger.warning("🔍 [Schema获取] 没有数据源ID，返回空Schema让SchemaListColumnsTool自动处理")
            return SchemaInfo(tables=[], columns={})

        # 检查缓存
        cache_key = f"{user_id}:{data_source_id}"
        from datetime import datetime
        current_time = datetime.now()

        if cache_key in self._schema_cache:
            cached_data, cache_time = self._schema_cache[cache_key]
            if (current_time - cache_time).total_seconds() < self._cache_ttl:
                logger.info(f"🔍 [Schema缓存] 使用缓存的Schema信息: 表数量={len(cached_data.tables)}")
                return cached_data

        try:
            from app.services.application.context.data_source_context_server import DataSourceContextBuilder
            logger.info(f"🔍 [Schema获取] 开始调用DataSourceContextBuilder")

            # 使用现有的DataSourceContextBuilder
            data_source_builder = DataSourceContextBuilder()
            context_result = await data_source_builder.build_data_source_context(
                user_id=user_id,
                data_source_id=data_source_id,
                force_refresh=False,
                names_only=True
            )

            logger.info(f"🔍 [Schema获取] DataSourceContextBuilder结果: success={context_result and context_result.get('success')}")
            if context_result:
                logger.info(f"🔍 [Schema获取] 上下文结果键: {list(context_result.keys())}")
                logger.info(f"🔍 [Schema获取] tables数据: {context_result.get('tables', [])[:2]}...")  # 只打印前2个

            if context_result and context_result.get("success"):
                # 仅提取表名，列信息留待 schema.get_columns 获取（两步Schema）
                tables_payload = context_result.get("tables", [])
                logger.info(f"🔍 [Schema获取] 获取到 {len(tables_payload)} 个表（仅返回表名，列信息延后获取）")

                tables = []
                for table_info in tables_payload:
                    table_name = table_info.get("table_name", "")
                    if table_name:
                        tables.append(table_name)

                final_schema = SchemaInfo(tables=tables, columns={})
                logger.info(f"🔍 [Schema获取] 最终构建Schema: 表={len(tables)}, 列信息延后")
                logger.debug(f"🔍 [Schema获取] 表名列表: {tables}")  # 改为debug级别

                # 缓存结果
                self._schema_cache[cache_key] = (final_schema, current_time)
                logger.debug(f"🔍 [Schema缓存] 已缓存Schema信息: {cache_key}")

                return final_schema
            else:
                logger.warning(f"🔍 [Schema获取] DataSourceContext构建失败或不成功")

        except Exception as e:
            logger.error(f"🔍 [Schema获取] 通过DataSourceContext获取Schema失败: {e}")
            import traceback
            logger.error(f"🔍 [Schema获取] 错误堆栈: {traceback.format_exc()}")

        # 回退：返回空Schema让SchemaListColumnsTool自动处理
        logger.warning("🔍 [Schema获取] 回退到空Schema，让SchemaListColumnsTool自动处理")
        return SchemaInfo(tables=[], columns={})

    def _serialize_datetime_objects(self, obj):
        """递归序列化datetime对象为ISO格式字符串"""
        from datetime import datetime, date

        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_datetime_objects(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime_objects(item) for item in obj]
        else:
            return obj

    def _is_period_placeholder(self, placeholder_text: str) -> bool:
        """检查是否为周期性占位符"""
        text_lower = placeholder_text.lower()
        period_keywords = ["周期", "日期", "时间", "period", "date", "统计周期", "报告周期", "数据周期"]
        return any(keyword in text_lower for keyword in period_keywords)

    async def _handle_period_placeholder(
        self,
        placeholder_name: str,
        placeholder_text: str,
        template_id: str,
        template_context: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """处理周期性占位符"""
        try:
            # 导入周期处理器
            from app.services.domain.placeholder.core.handlers.period_handler import PeriodHandler
            from app.utils.time_context import TimeContextManager

            logger.info(f"🕐 开始处理周期性占位符: {placeholder_text}")
            logger.info(f"🔧 输入参数 - placeholder_name: {placeholder_name}, template_id: {template_id}")
            logger.info(f"🔧 template_context类型: {type(template_context)}, 内容: {template_context}")
            logger.info(f"🔧 kwargs内容: {kwargs}")

            # 构建时间上下文
            time_ctx = {}
            logger.info(f"🔧 开始构建时间上下文")

            # 如果有模板上下文，尝试从中提取时间信息
            if template_context:
                logger.info(f"🔧 处理template_context，类型: {type(template_context)}")

                # 确保template_context是字典
                if not isinstance(template_context, dict):
                    logger.error(f"🔧 template_context不是字典类型: {type(template_context)}")
                    template_context = {}

                # 确保schedule是字典格式
                schedule = template_context.get("schedule") if isinstance(template_context, dict) else None
                logger.info(f"🔧 schedule类型: {type(schedule)}, 内容: {schedule}")

                if isinstance(schedule, dict):
                    time_ctx["schedule"] = schedule
                    time_ctx["cron_expression"] = schedule.get("cron_expression")
                elif isinstance(schedule, str):
                    # 如果schedule是字符串，假设它是cron表达式
                    time_ctx["cron_expression"] = schedule
                    time_ctx["schedule"] = {"cron_expression": schedule}
                else:
                    time_ctx["schedule"] = {}

                # 其他时间参数
                if isinstance(template_context, dict):
                    if template_context.get("execution_time"):
                        time_ctx["execution_time"] = template_context["execution_time"]
                    if template_context.get("start_date"):
                        time_ctx["start_date"] = template_context["start_date"]
                    if template_context.get("end_date"):
                        time_ctx["end_date"] = template_context["end_date"]

            # 从kwargs中获取额外的时间参数
            data_range = kwargs.get("data_range", "day")
            time_ctx.update({
                "data_range": data_range,
                "time_column": kwargs.get("time_column")
            })

            # 如果没有具体的时间信息，使用默认的当前时间处理
            if not time_ctx.get("execution_time"):
                from datetime import datetime
                time_ctx["execution_time"] = datetime.now().isoformat()

            # 基于data_range生成默认的cron表达式（如果没有提供）
            if not time_ctx.get("cron_expression"):
                if data_range == "day":
                    time_ctx["cron_expression"] = "0 9 * * *"  # 每天9点
                elif data_range == "week":
                    time_ctx["cron_expression"] = "0 9 * * 1"  # 每周一9点
                elif data_range == "month":
                    time_ctx["cron_expression"] = "0 9 1 * *"  # 每月1日9点

                # 更新schedule字典
                if "schedule" not in time_ctx:
                    time_ctx["schedule"] = {}
                time_ctx["schedule"]["cron_expression"] = time_ctx.get("cron_expression")

            # 使用周期处理器计算结果
            logger.info(f"🔧 调用PeriodHandler，time_ctx: {time_ctx}")

            period_handler = PeriodHandler()
            computed_result = await period_handler.compute(placeholder_text, time_ctx)

            logger.info(f"✅ 周期性占位符处理完成: {computed_result}")

            # 构建返回结果
            result = {
                "status": "success",
                "placeholder_name": placeholder_name,
                "generated_sql": {
                    placeholder_name: "",  # 周期性占位符不需要SQL
                    "sql": "",
                },
                "analysis_result": {
                    "description": "周期性占位符直接计算",
                    "analysis_type": "period_placeholder",
                    "semantic_type": "period",
                    "computed_value": computed_result.get("value", ""),
                    "period_meta": computed_result.get("meta", {}),
                    "analysis_summary": f"周期性占位符 '{placeholder_text}' 已计算完成",
                    "execution_stats": {
                        "tools_used": ["period_handler"],
                        "execution_time_ms": 10,
                        "agent_facade_used": False,
                        "period_handler_used": True
                    }
                },
                "confidence_score": 1.0,  # 周期计算有很高的准确性
                "analyzed_at": datetime.now().isoformat(),
                "context_used": {
                    "template_context": bool(template_context),
                    "period_calculation": True,
                    "time_context": time_ctx
                }
            }

            return result

        except Exception as e:
            import traceback
            logger.error(f"❌ 周期性占位符处理失败: {e}")
            logger.error(f"🔧 完整异常信息: {traceback.format_exc()}")
            return self._create_error_result(placeholder_name, f"周期性占位符处理失败: {str(e)}")

    async def _attempt_pipeline_recovery(
        self,
        agent_input,
        failed_result,
        placeholder_name: str,
        semantic_type: str
    ) -> Dict[str, Any]:
        """智能Pipeline恢复机制"""
        recovery_attempts = []
        logger.info(f"🔄 开始Agent Pipeline恢复，语义类型: {semantic_type}")

        # 尝试1: 检查是否是SQL验证问题
        if self._is_sql_validation_failure(failed_result):
            recovery_attempts.append("sql_validation_bypass")
            logger.info("🔄 尝试SQL验证容错恢复")

            try:
                # 修改约束条件，允许更宽松的验证
                relaxed_input = agent_input
                if hasattr(relaxed_input, 'constraints'):
                    # 启用验证容错模式
                    relaxed_input.constraints.validation_mode = "tolerant"
                    relaxed_input.constraints.bypass_minor_errors = True

                # 重新执行 - 使用任务验证智能模式
                recovery_result = await self.agent_facade.execute_task_validation(relaxed_input)
                if recovery_result.success:
                    return {
                        "recovered": True,
                        "method": "sql_validation_bypass",
                        "result": recovery_result,
                        "recovery_attempts": recovery_attempts
                    }

            except Exception as e:
                logger.warning(f"🔄 SQL验证容错恢复失败: {e}")

        # 尝试2: 简化语义类型
        if semantic_type != "stat":
            recovery_attempts.append("semantic_simplification")
            logger.info("🔄 尝试简化语义类型恢复")

            try:
                # 简化为基础统计类型
                simplified_input = agent_input
                if hasattr(simplified_input, 'placeholder'):
                    simplified_input.placeholder.type = "stat"

                recovery_result = await self.agent_facade.execute_task_validation(simplified_input)
                if recovery_result.success:
                    return {
                        "recovered": True,
                        "method": "semantic_simplification",
                        "result": recovery_result,
                        "recovery_attempts": recovery_attempts
                    }

            except Exception as e:
                logger.warning(f"🔄 语义简化恢复失败: {e}")

        # 尝试3: 任务验证智能模式已经包含了智能回退，不需要额外的恢复机制
        recovery_attempts.append("task_validation_intelligent_built_in")
        logger.info("🔄 任务验证智能模式已内置回退机制，跳过额外恢复")

        # 既然使用了execute_task_validation，它已经包含了PTAV回退机制
        # 如果还失败，说明是更根本性的问题，应该直接返回错误
        logger.warning("🔄 任务验证智能模式失败，可能是配置或连接问题")

        return {
            "recovered": False,
            "recovery_attempts": recovery_attempts,
            "reason": "execute_task_validation已内置智能回退，无需额外恢复机制"
        }

    def _is_sql_validation_failure(self, failed_result) -> bool:
        """检查是否是SQL验证失败"""
        if not hasattr(failed_result, 'metadata') or not failed_result.metadata:
            return False

        error_info = failed_result.metadata
        # 安全地处理APIResponse对象
        if isinstance(error_info, dict):
            error_message = error_info.get("error", "")
            reasoning = error_info.get("reasoning", "")
        elif hasattr(error_info, '__dict__'):
            # 如果是APIResponse等对象，尝试访问属性
            error_message = getattr(error_info, 'error', "") or str(error_info)
            reasoning = getattr(error_info, 'reasoning', "")
        else:
            # 回退到字符串表示
            error_message = str(error_info)
            reasoning = ""

        sql_validation_keywords = [
            "sql.validate", "语法错误", "括号", "DATE_SUB", "DATE_ADD",
            "SQL语句", "语法正确性", "验证失败"
        ]

        return any(keyword in str(error_message) + str(reasoning)
                  for keyword in sql_validation_keywords)

    async def _generate_basic_sql_fallback(
        self,
        placeholder_name: str,
        user_prompt: str,
        schema_info,
        user_id: str
    ) -> Dict[str, Any]:
        """基础SQL生成回退机制 - 已禁用，遵循单一职责原则"""
        logger.error("🔄 [恢复机制] SQLDraftTool已删除，恢复机制不再支持SQL生成")
        return {
            "success": False,
            "error": "Agent计划生成失败，且恢复机制已禁用。请检查Agent配置和计划生成逻辑。"
        }

    def _create_error_result(self, placeholder_name: str, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "status": "error",
            "placeholder_name": placeholder_name,
            "generated_sql": {"sql": "", placeholder_name: ""},
            "error": error_message,
            "confidence_score": 0.0,
            "analyzed_at": datetime.now().isoformat(),
            "analysis_result": {
                "description": "Agent Pipeline执行失败",
                "analysis_type": "error_fallback",
                "suggestions": ["请检查输入参数", "验证数据源连接"]
            }
        }

    def _create_enhanced_error_result(
        self,
        placeholder_name: str,
        error_metadata: Dict[str, Any],
        recovery_attempts: List[str] = None
    ) -> Dict[str, Any]:
        """创建增强的错误结果，包含恢复尝试信息"""
        # 确保 error_metadata 是字典类型
        if not isinstance(error_metadata, dict):
            error_metadata = {"error": str(error_metadata), "reasoning": ""}

        error_message = error_metadata.get("error", "Agent执行失败")
        reasoning = error_metadata.get("reasoning", "")

        # 根据错误类型提供更具体的建议
        suggestions = ["请检查输入参数", "验证数据源连接"]

        if "sql.validate" in str(error_metadata):
            suggestions.extend([
                "SQL语法可能存在问题，建议简化查询条件",
                "检查占位符描述是否准确",
                "考虑使用基础统计类型而非复杂语义"
            ])

        if "DATE_SUB" in str(error_metadata) or "括号" in str(error_metadata):
            suggestions.extend([
                "SQL中的日期函数语法需要检查",
                "括号匹配可能存在问题"
            ])

        return {
            "status": "error",
            "placeholder_name": placeholder_name,
            "generated_sql": {"sql": "", placeholder_name: ""},
            "error": error_message,
            "error_details": {
                "reasoning": reasoning,
                "recovery_attempts": recovery_attempts or [],
                "error_type": self._classify_error_type(error_metadata)
            },
            "confidence_score": 0.0,
            "analyzed_at": datetime.now().isoformat(),
            "analysis_result": {
                "description": f"Agent Pipeline执行失败: {reasoning[:100]}..." if len(reasoning) > 100 else reasoning,
                "analysis_type": "enhanced_error_fallback",
                "suggestions": suggestions,
                "recovery_info": {
                    "attempts_made": len(recovery_attempts) if recovery_attempts else 0,
                    "recoverable": self._is_recoverable_error(error_metadata),
                    "next_actions": ["尝试简化占位符描述", "检查数据源配置", "联系技术支持"]
                }
            }
        }

    def _classify_error_type(self, error_metadata: Dict[str, Any]) -> str:
        """分类错误类型"""
        error_str = str(error_metadata).lower()

        if "sql" in error_str and "validate" in error_str:
            return "sql_validation_error"
        elif "schema" in error_str:
            return "schema_error"
        elif "connection" in error_str or "database" in error_str:
            return "connection_error"
        elif "timeout" in error_str:
            return "timeout_error"
        else:
            return "general_error"

    def _extract_placeholder_snippet(self, template_text: str, placeholder_text: str, placeholder_name: str) -> str:
        """从整份模板文本中提取“包含占位符的段落/邻近行”。

        规则：
        - 以换行分段，找到包含 placeholder_text 或 placeholder_name 的行
        - 向上/向下扩展到最近的空行（段落边界）
        - 如未命中，则返回前500字符的预览
        """
        try:
            if not template_text:
                return ""
            lines = template_text.splitlines()
            keys = [k for k in [placeholder_text, placeholder_name, placeholder_name and f"{{{{{placeholder_name}}}}}"] if k]
            hit_idx = -1
            for i, ln in enumerate(lines):
                for k in keys:
                    if k and k in ln:
                        hit_idx = i
                        break
                if hit_idx >= 0:
                    break
            if hit_idx < 0:
                # 未命中，返回前500字符
                return (template_text[:500] + ("…" if len(template_text) > 500 else ""))

            # 扩展到段落边界（空行）
            start = hit_idx
            while start > 0 and lines[start].strip() != "" and lines[start-1].strip() != "":
                start -= 1
            end = hit_idx
            while end + 1 < len(lines) and lines[end].strip() != "" and lines[end+1].strip() != "":
                end += 1
            snippet_lines = lines[start:end+1]
            # 再向两侧补充一行上下文
            if start > 0:
                snippet_lines.insert(0, lines[start-1])
            if end + 1 < len(lines):
                snippet_lines.append(lines[end+1])
            snippet = "\n".join(snippet_lines).strip()
            return snippet
        except Exception:
            return (template_text[:500] + ("…" if len(template_text) > 500 else ""))

    def _is_recoverable_error(self, error_metadata: Dict[str, Any]) -> bool:
        """判断错误是否可恢复"""
        error_str = str(error_metadata).lower()

        # SQL验证错误通常可恢复
        if "sql" in error_str and "validate" in error_str:
            return True

        # 超时错误可恢复
        if "timeout" in error_str:
            return True

        # 连接错误一般不可恢复
        if "connection" in error_str:
            return False

        return True

# 全局服务实例
_orchestration_service = PlaceholderOrchestrationService()

# ================================================================================
# API路由定义 - 充分利用Agent基础设施
# ================================================================================

@router.get("/", response_model=APIResponse[List[TemplatePlaceholder]])
async def get_placeholders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    template_id: str = Query(None, description="按模板ID过滤"),
) -> APIResponse[List[TemplatePlaceholder]]:
    """获取占位符列表"""
    try:
        logger.info(f"获取占位符列表: template_id={template_id}")
        if template_id:
            placeholders = crud.template_placeholder.get_by_template(
                db=db, template_id=template_id
            )
        else:
            placeholders = crud.template_placeholder.get_multi(
                db=db, skip=skip, limit=limit
            )

        # 直接返回TemplatePlaceholder格式，不使用前端适配器
        template_placeholders = []
        for p in placeholders:
            # 确保所有必需字段都存在（包括agent_config用于返回test_result）
            template_placeholder = TemplatePlaceholder(
                id=p.id,
                template_id=p.template_id,
                placeholder_name=p.placeholder_name,
                placeholder_text=p.placeholder_text or p.placeholder_name,
                placeholder_type=p.placeholder_type or "statistical",
                content_type=p.content_type or "text",
                agent_analyzed=p.agent_analyzed or False,
                target_database=p.target_database,
                target_table=p.target_table,
                required_fields=p.required_fields,
                generated_sql=p.generated_sql,
                sql_validated=p.sql_validated or False,
                execution_order=p.execution_order or 1,
                cache_ttl_hours=p.cache_ttl_hours or 24,
                is_required=p.is_required if p.is_required is not None else True,
                is_active=p.is_active if p.is_active is not None else True,
                agent_workflow_id=p.agent_workflow_id,
                agent_config=p.agent_config or {},  # 🔑 包含test_result等信息
                description=p.description,
                confidence_score=p.confidence_score or 0.0,
                content_hash=p.content_hash,
                original_type=p.original_type,
                extracted_description=p.extracted_description,
                parsing_metadata=p.parsing_metadata,
                created_at=p.created_at,
                updated_at=p.updated_at,
                analyzed_at=p.analyzed_at
            )
            template_placeholders.append(template_placeholder)

        return APIResponse(
            success=True,
            data=template_placeholders,
            message="获取占位符列表成功"
        )
    except Exception as e:
        logger.error(f"获取占位符列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取占位符列表失败")

@router.get("/{placeholder_id}", response_model=APIResponse[TemplatePlaceholder])
async def get_placeholder(
    placeholder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TemplatePlaceholder]:
    """获取单个占位符详情"""
    try:
        placeholder = crud.template_placeholder.get(db=db, id=placeholder_id)
        if not placeholder:
            raise HTTPException(status_code=404, detail="占位符不存在")

        return APIResponse(
            success=True,
            data=TemplatePlaceholder.from_orm(placeholder),
            message="获取占位符详情成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取占位符详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取占位符详情失败")

@router.post("/", response_model=APIResponse[TemplatePlaceholder])
async def create_placeholder(
    placeholder_in: TemplatePlaceholderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TemplatePlaceholder]:
    """创建新占位符"""
    try:
        placeholder = crud.template_placeholder.create(
            db=db, obj_in=placeholder_in
        )
        return APIResponse(
            success=True,
            data=TemplatePlaceholder.from_orm(placeholder),
            message="创建占位符成功"
        )
    except Exception as e:
        logger.error(f"创建占位符失败: {e}")
        raise HTTPException(status_code=500, detail="创建占位符失败")

@router.put("/{placeholder_id}", response_model=APIResponse[TemplatePlaceholder])
async def update_placeholder(
    placeholder_id: str,
    placeholder_in: TemplatePlaceholderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TemplatePlaceholder]:
    """更新占位符"""
    try:
        placeholder = crud.template_placeholder.get(db=db, id=placeholder_id)
        if not placeholder:
            raise HTTPException(status_code=404, detail="占位符不存在")

        placeholder = crud.template_placeholder.update(
            db=db, db_obj=placeholder, obj_in=placeholder_in
        )
        return APIResponse(
            success=True,
            data=TemplatePlaceholder.from_orm(placeholder),
            message="更新占位符成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新占位符失败: {e}")
        raise HTTPException(status_code=500, detail="更新占位符失败")

@router.delete("/{placeholder_id}", response_model=APIResponse[bool])
async def delete_placeholder(
    placeholder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[bool]:
    """删除占位符"""
    try:
        placeholder = crud.template_placeholder.get(db=db, id=placeholder_id)
        if not placeholder:
            raise HTTPException(status_code=404, detail="占位符不存在")

        crud.template_placeholder.remove(db=db, id=placeholder_id)
        return APIResponse(
            success=True,
            data=True,
            message="删除占位符成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除占位符失败: {e}")
        raise HTTPException(status_code=500, detail="删除占位符失败")

# ================================================================================
# 核心功能：基于完整Agent基础设施的占位符分析
# ================================================================================

@router.post("/analyze", response_model=APIResponse[Dict[str, Any]])
async def analyze_placeholder_with_agent_pipeline(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """
    使用完整Agent基础设施进行占位符分析

    包括完整的工具链：
    - SchemaListColumnsTool: 自动查询数据库结构
    - SQLDraftTool: 智能SQL生成（支持语义类型）
    - SQLValidateTool: SQL验证
    - SQLRefineTool: SQL优化
    - 可选SQLExecuteTool: SQL执行测试

    支持的参数:
    - placeholder_name: 占位符名称
    - placeholder_text: 占位符文本
    - template_id: 模板ID
    - data_source_id: 数据源ID (可选)
    - template_context: 模板上下文 (可选)
    - time_column: 时间列名 (可选，将自动检测)
    - data_range: 数据范围 (默认: day)
    - requirements: 额外需求 (可选)
    - execute_sql: 是否执行SQL测试 (默认: false)
    - row_limit: 行数限制 (默认: 1000)
    """
    try:
        # 使用统一验证器验证参数
        validation_results = []

        # 验证必需字段
        required_validation = ParameterValidator.validate_required_fields(
            request, ["placeholder_name", "placeholder_text", "template_id"]
        )
        validation_results.append(required_validation)

        # 验证template_id格式
        if request.get("template_id"):
            template_id_validation = ParameterValidator.validate_uuid(
                request.get("template_id"), "template_id"
            )
            validation_results.append(template_id_validation)

        # 验证placeholder_name长度
        if request.get("placeholder_name"):
            name_validation = ParameterValidator.validate_string_length(
                request.get("placeholder_name"), "placeholder_name", 1, 100
            )
            validation_results.append(name_validation)

        # 检查验证结果
        error_response = ErrorResponseBuilder.build_validation_error_response(validation_results)
        if error_response:
            raise HTTPException(
                status_code=400,
                detail=error_response.user_friendly_message
            )

        placeholder_name = request.get("placeholder_name")
        placeholder_text = request.get("placeholder_text")
        template_id = request.get("template_id")

        logger.info(f"🚀 启动Agent Pipeline分析: {placeholder_name}")

        # 使用完整的Agent基础设施进行分析
        # 兼容：如果前端显式传入 sql 或 current_sql，且请求 execute_sql=true，则将其映射到 data_source.sql_to_test
        # 这样Agent会自动进入 SQL 验证/执行路径，避免 missing_current_sql
        forwarded_kwargs = {k: v for k, v in request.items() if k not in [
            'placeholder_name', 'placeholder_text', 'template_id',
            'data_source_id', 'template_context'
        ]}

        # 统一 SQL 字段收集
        incoming_sql = request.get("sql") or request.get("current_sql")
        if incoming_sql:
            # 将 SQL 透传到上下文，供 Facade/Orchestrator 提取
            forwarded_kwargs["current_sql"] = incoming_sql

        result = await _orchestration_service.analyze_placeholder_with_full_pipeline(
            placeholder_name=placeholder_name,
            placeholder_text=placeholder_text,
            template_id=template_id,
            data_source_id=request.get("data_source_id"),
            template_context=request.get("template_context"),
            user_id=str(current_user.id),
            **forwarded_kwargs
        )

        # 统一结果为字典，防止上游误返回Pydantic对象
        if not isinstance(result, dict):
            try:
                if hasattr(result, 'dict') and callable(result.dict):
                    result = result.dict()
                elif hasattr(result, 'model_dump') and callable(result.model_dump):
                    result = result.model_dump()
                else:
                    result = {"status": "error", "error": "invalid_result_type", "raw": str(result)}
            except Exception:
                result = {"status": "error", "error": "invalid_result_type"}

        # 序列化结果中的datetime对象，防止JSON序列化错误
        result = _orchestration_service._serialize_datetime_objects(result)

        # 自动保存分析结果到数据库
        # 策略：只要生成了SQL（无论是否验证通过），都保存SQL和验证结果
        # 这样前端刷新后可以看到SQL和测试状态，agent可以根据测试结果决定是否修正
        should_persist = False
        if isinstance(result.get("generated_sql"), dict):
            should_persist = bool(result.get("generated_sql", {}).get("sql"))
        elif isinstance(result.get("generated_sql"), str):
            should_persist = bool(result.get("generated_sql", "").strip())

        logger.info(f"🔍 [Debug] 保存检查 - should_persist={should_persist}, result.status={result.get('status')}, has_sql={bool(result.get('generated_sql'))}")

        saved_placeholder_obj = None
        if should_persist:  # 只要有SQL就保存（包括验证失败的SQL）
            try:
                saved_placeholder_obj = await _save_placeholder_result(
                    db=db,
                    template_id=template_id,
                    placeholder_name=placeholder_name,
                    placeholder_text=placeholder_text,
                    result=result
                )
                # 将数据库ID添加到结果中
                if saved_placeholder_obj:
                    result["placeholder_id"] = saved_placeholder_obj.id
                    result["placeholder_db_saved"] = True
                    logger.info(f"✅ 占位符已保存到数据库: {placeholder_name} (ID: {saved_placeholder_obj.id})")
            except Exception as save_error:
                logger.warning(f"保存占位符结果失败: {save_error}")
                result["placeholder_db_saved"] = False
                # 不影响主流程

        # 适配前端格式（兼容周期性占位符：存在 frontend_data 也视为成功）
        status_ok = (result.get("status") == "success") or bool(result.get("frontend_data"))
        if status_ok:
                # 检查是否有预构建的前端数据（来自周期性占位符）
                if result.get("frontend_data"):
                    # 使用预构建的前端数据
                    frontend_result = result.get("frontend_data")
                else:
                    # 构建占位符显示信息（常规Agent Pipeline结果）
                    placeholder_dict = {
                        "text": placeholder_text,
                        "kind": result.get("analysis_result", {}).get("semantic_type", "statistical"),
                        "confidence": result.get("confidence_score", 0.8),
                        "needs_reanalysis": False
                    }
                    try:
                        adapted_placeholder = adapt_placeholder_for_frontend(placeholder_dict)
                    except Exception:
                        # 回退：构造最简占位符以避免前端渲染失败
                        adapted_placeholder = type("_Shim", (), {"dict": lambda self=None: {
                            "text": placeholder_text,
                            "kind": placeholder_dict.get("kind", "statistical"),
                            "display_name": placeholder_dict.get("kind", "statistical"),
                            "description": "",
                            "status": "completed",
                            "confidence": placeholder_dict.get("confidence", 0.8),
                            "needs_reanalysis": False,
                            "badge_color": "default",
                            "icon": None,
                            "tooltip": None
                        }})()

                    # 构建分析进度信息
                    progress_info = adapt_analysis_progress_for_frontend(
                        current_step=4,
                        total_steps=4,
                        step_name="分析完成",
                        status="completed",
                        progress_percent=100.0
                    )

                    # 整合结果（包含test_result用于前端验证显示和agent修正决策）
                    frontend_result = {
                        "placeholder": adapted_placeholder.dict(),
                        "progress": progress_info.dict(),
                        "analysis_result": result.get("analysis_result"),
                        "generated_sql": result.get("generated_sql"),
                        "test_result": result.get("test_result"),  # 🔑 关键：包含测试结果
                        "business_validation": result.get("business_validation"),
                        "analyzed_at": result.get("analyzed_at")
                    }

                # 对整个frontend_result再次序列化datetime对象
                frontend_result = _orchestration_service._serialize_datetime_objects(frontend_result)

                # 🔧 调试最终返回
                logger.info(f"🔧 [Debug] 即将返回APIResponse，frontend_result keys: {list(frontend_result.keys())}")
                logger.info(f"🔧 [Debug] frontend_result.generated_sql type: {type(frontend_result.get('generated_sql'))}")

                return APIResponse(
                    success=True,
                    data=frontend_result,
                    message=f"Agent Pipeline分析成功: {placeholder_name}"
                )
        else:
            # 错误情况使用错误适配器
            # 先序列化result中的datetime对象
            serialized_result = _orchestration_service._serialize_datetime_objects(result)

            error_info = adapt_error_for_frontend(
                error_message=serialized_result.get("error", "分析失败"),
                error_type="analysis",
                error_code="placeholder_analysis_failed",
                details=serialized_result
            )

            return APIResponse(
                success=False,
                data=error_info.dict(),
                message=f"Agent Pipeline分析失败: {placeholder_name}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent Pipeline分析失败: {e}")
        # 创建错误适配信息（带容错）
        try:
            error_info = adapt_error_for_frontend(
                error_message=str(e),
                error_type="agent_service",
                error_code="agent_service_unavailable",
                details={
                    "agent_context": {
                        "placeholder_name": placeholder_name,
                        "template_id": template_id,
                        "user_id": str(current_user.id)
                    },
                    "error_type": type(e).__name__
                }
            )
            data_payload = error_info.dict()
            user_msg = error_info.user_friendly_message
        except Exception as adapt_exc:
            logger.error(f"错误适配失败: {adapt_exc}")
            data_payload = {
                "error_code": "agent_service_unavailable",
                "error_message": str(e),
                "user_friendly_message": "AI分析暂不可用，请稍后重试",
                "error_type": "agent_service",
                "severity": "error",
            }
            user_msg = data_payload["user_friendly_message"]

        return APIResponse(
            success=False,
            data=data_payload,
            message=user_msg
        )


@router.post("/batch-analyze", response_model=APIResponse[Dict[str, Any]])
async def batch_analyze_with_agent_pipeline(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """批量使用Agent Pipeline分析模板中的所有占位符"""
    try:
        template_id = request.get("template_id")
        data_source_id = request.get("data_source_id")

        if not template_id:
            raise HTTPException(status_code=400, detail="缺少template_id参数")

        logger.info(f"🔄 批量Agent Pipeline分析: template_id={template_id}")

        # 获取模板中的所有占位符
        placeholders = crud.template_placeholder.get_by_template(
            db=db, template_id=template_id
        )

        results = []
        success_count = 0

        for placeholder in placeholders:
            try:
                result = await _orchestration_service.analyze_placeholder_with_full_pipeline(
                    placeholder_name=placeholder.placeholder_name,
                    placeholder_text=placeholder.placeholder_text,
                    template_id=template_id,
                    data_source_id=data_source_id,
                    user_id=str(current_user.id)
                )
                # 统一字典化
                if not isinstance(result, dict):
                    try:
                        if hasattr(result, 'dict') and callable(result.dict):
                            result = result.dict()
                        elif hasattr(result, 'model_dump') and callable(result.model_dump):
                            result = result.model_dump()
                        else:
                            result = {"status": "error", "error": "invalid_result_type", "raw": str(result)}
                    except Exception:
                        result = {"status": "error", "error": "invalid_result_type"}
                # 序列化结果中的datetime对象
                result = _orchestration_service._serialize_datetime_objects(result)
                results.append(result)
                if result.get("status") == "success":
                    success_count += 1
            except Exception as e:
                logger.error(f"批量分析单个占位符失败: {placeholder.placeholder_name}, {e}")
                results.append({
                    "status": "error",
                    "placeholder_name": placeholder.placeholder_name,
                    "error": str(e)
                })

        # 序列化所有结果中的datetime对象
        batch_data = {
            "template_id": template_id,
            "total_placeholders": len(placeholders),
            "success_count": success_count,
            "results": results,
            "analyzed_at": datetime.now().isoformat()
        }
        batch_data = _orchestration_service._serialize_datetime_objects(batch_data)

        return APIResponse(
            success=success_count > 0,
            data=batch_data,
            message=f"批量Agent Pipeline分析完成: {success_count}/{len(placeholders)} 成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量Agent Pipeline分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量分析失败: {str(e)}")

# ================================================================================
# SQL验证服务 - 独立功能
# ================================================================================

@router.post("/validate-sql", response_model=APIResponse[Dict[str, Any]])
async def validate_placeholder_sql(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """验证存储的占位符SQL并返回真实数据 - 独立功能"""
    try:
        from app.crud.crud_data_source import crud_data_source
        from app.services.data.validation.sql_validation_service import sql_validation_service

        sql_template = request.get("sql_template")
        data_source_id = request.get("data_source_id")
        placeholder_name = request.get("placeholder_name", "SQL验证")
        execution_mode = request.get("execution_mode", "test")
        fixed_date = request.get("fixed_date")
        days_offset = request.get("days_offset", -1)

        if not sql_template:
            raise HTTPException(status_code=400, detail="缺少sql_template参数")
        if not data_source_id:
            raise HTTPException(status_code=400, detail="缺少data_source_id参数")

        # 验证数据源权限
        ds = crud_data_source.get_user_data_source(db, data_source_id=data_source_id, user_id=current_user.id)
        if not ds:
            raise HTTPException(status_code=404, detail="数据源不存在或无权限访问")

        logger.info(f"🔍 占位符SQL验证请求: {placeholder_name}")

        # 执行验证
        result = await sql_validation_service.validate_and_execute_placeholder_sql(
            sql_template=sql_template,
            data_source_id=str(data_source_id),
            placeholder_name=placeholder_name,
            execution_mode=execution_mode,
            fixed_date=fixed_date,
            days_offset=days_offset
        )

        # 优化返回结构：将查询结果提到顶层，方便前端访问
        if result.get("success"):
            execution_result = result.get("execution_result", {})
            enhanced_result = {
                **result,
                # 🔑 将查询数据提到顶层，方便前端直接访问
                "rows": execution_result.get("rows", []),
                "row_count": execution_result.get("row_count", 0),
                "primary_value": execution_result.get("primary_value"),
                "columns": execution_result.get("metadata", {}).get("columns", []),
            }

            return APIResponse(
                success=True,
                data=enhanced_result,
                message=f"✅ SQL验证成功，返回 {enhanced_result['row_count']} 行数据"
            )
        else:
            return APIResponse(
                success=False,
                data=result,
                message=f"❌ SQL验证失败: {result.get('error', '未知错误')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 占位符SQL验证异常: {e}")
        raise HTTPException(status_code=500, detail=f"验证过程异常: {str(e)}")


@router.post("/batch-validate-sql", response_model=APIResponse[Dict[str, Any]])
async def batch_validate_placeholder_sqls(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """批量验证多个占位符SQL - 独立功能"""
    try:
        from app.crud.crud_data_source import crud_data_source
        from app.services.data.validation.sql_validation_service import sql_validation_service

        sql_templates = request.get("sql_templates", {})
        data_source_id = request.get("data_source_id")
        execution_mode = request.get("execution_mode", "test")
        fixed_date = request.get("fixed_date")

        if not sql_templates:
            raise HTTPException(status_code=400, detail="缺少sql_templates参数")
        if not data_source_id:
            raise HTTPException(status_code=400, detail="缺少data_source_id参数")

        # 验证数据源权限
        ds = crud_data_source.get_user_data_source(db, data_source_id=data_source_id, user_id=current_user.id)
        if not ds:
            raise HTTPException(status_code=404, detail="数据源不存在或无权限访问")

        logger.info(f"🔍 批量占位符SQL验证请求: {len(sql_templates)} 个")

        # 执行批量验证
        result = await sql_validation_service.batch_validate_placeholder_sqls(
            sql_templates=sql_templates,
            data_source_id=str(data_source_id),
            execution_mode=execution_mode,
            fixed_date=fixed_date
        )

        return APIResponse(
            success=result.get("success", False),
            data=result,
            message=f"批量验证完成: {result.get('summary', {}).get('successful_count', 0)} 成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量占位符SQL验证异常: {e}")
        raise HTTPException(status_code=500, detail=f"批量验证过程异常: {str(e)}")


# ================================================================================
# 兼容性接口 - 映射到Agent Pipeline
# ================================================================================

@router.post("/test-sql", response_model=APIResponse[Dict[str, Any]])
async def test_sql_with_agent(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[Dict[str, Any]]:
    """直接连接数据源执行SQL并返回结果（不使用Agent）。"""
    try:
        from app.crud.crud_data_source import crud_data_source
        from app.services.data.query.query_executor_service import query_executor_service

        sql = request.get("sql")
        data_source_id = request.get("data_source_id")
        placeholder_name = request.get("placeholder_name", "SQL测试")

        if not sql:
            raise HTTPException(status_code=400, detail="缺少SQL参数")

        if not data_source_id:
            raise HTTPException(status_code=400, detail="缺少数据源ID")

        # 鉴权：确认数据源属于当前用户且可用
        ds = crud_data_source.get_user_data_source(db, data_source_id=data_source_id, user_id=current_user.id)
        if not ds:
            raise HTTPException(status_code=404, detail="数据源不存在或无权限访问")

        logger.info(f"🧪 直接SQL测试（非Agent）: {placeholder_name}")

        # 执行查询（QueryExecutorService 已包含SQL安全校验，仅允许SELECT）
        result = await query_executor_service.execute_query(sql, {"data_source_id": str(data_source_id)})

        success = bool(result.get("success"))
        meta = result.get("metadata", {}) or {}
        data = result.get("data", []) or []

        # 统一前端期望的 test_result 结构
        test_result = {
            "success": success,
            "message": meta.get("message") or ("查询成功" if success else meta.get("error") or result.get("error") or "查询失败"),
            "data": data,  # 返回记录列表（list[dict]）
            "row_count": meta.get("row_count", len(data)),
            "execution_time_ms": int((meta.get("execution_time") or result.get("execution_time") or 0) * 1000),
            "columns": meta.get("columns", []),
        }

        # 序列化返回结构
        response_payload = _orchestration_service._serialize_datetime_objects({
            "placeholder_name": placeholder_name,
            "sql": sql,
            "test_result": test_result,
            "tested_at": datetime.now().isoformat(),
            "agent_executed": False
        })

        return APIResponse(
            success=success,
            data=response_payload,
            message="SQL执行成功" if success else (meta.get("error") or result.get("error") or "SQL执行失败")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"直接SQL测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")

# ================================================================================
# 辅助函数
# ================================================================================

@router.put("/{placeholder_id}/sql", response_model=APIResponse[TemplatePlaceholder])
async def update_placeholder_sql(
    placeholder_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[TemplatePlaceholder]:
    """
    更新占位符SQL配置

    支持字段：
    - generated_sql: SQL语句
    - execution_order: 执行顺序
    - cache_ttl_hours: 缓存TTL (小时)
    - is_active: 是否启用
    - placeholder_type: 类型 (统计/排名/对比等)
    - description: 描述
    """
    try:
        # 验证placeholder存在
        placeholder = crud.template_placeholder.get(db=db, id=placeholder_id)
        if not placeholder:
            raise HTTPException(status_code=404, detail="占位符不存在")

        # 验证权限（可选：检查模板所有者）

        # 构建更新数据
        update_data = {}

        # SQL相关字段
        if "generated_sql" in request:
            update_data["generated_sql"] = request["generated_sql"]
            update_data["sql_validated"] = False  # SQL改变后需要重新验证

        # 配置字段
        if "execution_order" in request:
            update_data["execution_order"] = int(request["execution_order"])

        if "cache_ttl_hours" in request:
            ttl = int(request["cache_ttl_hours"])
            if 1 <= ttl <= 24*30:  # 1小时到30天
                update_data["cache_ttl_hours"] = ttl

        if "is_active" in request:
            update_data["is_active"] = bool(request["is_active"])

        if "placeholder_type" in request:
            valid_types = ["统计", "排名", "对比", "趋势", "图表", "自定义"]
            if request["placeholder_type"] in valid_types:
                update_data["placeholder_type"] = request["placeholder_type"]

        if "description" in request:
            update_data["description"] = request["description"]

        # 执行更新
        placeholder_update = TemplatePlaceholderUpdate(**update_data)
        updated_placeholder = crud.template_placeholder.update(
            db=db, db_obj=placeholder, obj_in=placeholder_update
        )
        db.commit()

        logger.info(f"✅ 占位符SQL配置更新成功: {placeholder_id}")

        return APIResponse(
            success=True,
            data=updated_placeholder,
            message="占位符配置更新成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 更新占位符SQL配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/template/{template_id}/list", response_model=APIResponse[List[TemplatePlaceholder]])
async def get_template_placeholders(
    template_id: str,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[List[TemplatePlaceholder]]:
    """获取模板的所有占位符（用于编辑界面）"""
    try:
        placeholders = crud.template_placeholder.get_by_template(
            db=db,
            template_id=template_id,
            include_inactive=include_inactive
        )

        return APIResponse(
            success=True,
            data=placeholders,
            message=f"获取到 {len(placeholders)} 个占位符"
        )

    except Exception as e:
        logger.error(f"❌ 获取模板占位符失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


async def _save_placeholder_result(
    db: Session,
    template_id: str,
    placeholder_name: str,
    placeholder_text: str,
    result: Dict[str, Any]
):
    """保存Agent Pipeline分析结果到数据库"""
    try:
        logger.info(f"🔍 [Debug] 保存占位符开始: name='{placeholder_name}', template_id='{template_id}'")

        # 检查是否已存在
        existing = crud.template_placeholder.get_by_template_and_name(
            db=db, template_id=template_id, name=placeholder_name
        )

        if existing:
            logger.info(f"🔍 [Debug] 找到现有记录: id={existing.id}, placeholder_name='{existing.placeholder_name}'")
            if existing.generated_sql:
                logger.info(f"🔍 [Debug] 现有SQL: {existing.generated_sql[:100]}...")
            else:
                logger.info(f"🔍 [Debug] 现有SQL: None")
        else:
            logger.warning(f"⚠️ [Debug] 未找到现有记录，将创建新记录")

        generated_sql = result.get("generated_sql", {})
        if isinstance(generated_sql, dict):
            sql_content = generated_sql.get("sql", "")
        elif isinstance(generated_sql, str):
            sql_content = generated_sql.strip()
        else:
            sql_content = ""

        logger.info(f"🔍 [Debug] 提取的SQL内容长度: {len(sql_content)} 字符")
        if sql_content:
            logger.info(f"🔍 [Debug] SQL预览: {sql_content[:100]}...")

        analysis_result = result.get("analysis_result", {})
        semantic_type = analysis_result.get("semantic_type", "stat")

        # 提取测试结果状态
        test_result = result.get("test_result", {})
        sql_validated = test_result.get("executed", False) and test_result.get("success", False)

        logger.info(f"🔍 [Debug] 测试结果状态 - executed={test_result.get('executed')}, success={test_result.get('success')}, sql_validated={sql_validated}")

        # 构建要保存的数据（包括SQL验证状态和测试结果）
        placeholder_data = {
            "placeholder_name": placeholder_name,
            "placeholder_text": placeholder_text,
            "placeholder_type": "variable",
            "content_type": "text",
            "generated_sql": sql_content,
            "sql_validated": sql_validated,  # 🔑 保存验证状态
            "confidence_score": result.get("confidence_score", 0.8),
            "agent_analyzed": True,
            "is_active": True,
            "execution_order": 1,
            "cache_ttl_hours": 24,
            "description": f"Agent Pipeline分析({semantic_type}): {placeholder_name}",
            # 🔑 将test_result保存到agent_config中，供前端查询使用
            "agent_config": {
                "last_test_result": test_result,
                "last_analysis_result": analysis_result,
                "semantic_type": semantic_type
            }
        }

        saved_placeholder = None
        if existing:
            # 更新现有占位符
            logger.info(f"🔍 [Debug] 准备更新现有记录 id={existing.id}")
            placeholder_update = TemplatePlaceholderUpdate(**{
                k: v for k, v in placeholder_data.items()
                if k not in ["id", "template_id", "created_at", "updated_at"]
            })
            saved_placeholder = crud.template_placeholder.update(
                db=db, db_obj=existing, obj_in=placeholder_update
            )
            logger.info(f"🔍 [Debug] 更新成功: id={saved_placeholder.id}")
        else:
            # 创建新占位符
            logger.info(f"🔍 [Debug] 准备创建新记录")
            placeholder_create = TemplatePlaceholderCreate(
                template_id=template_id,
                **{k: v for k, v in placeholder_data.items()
                   if k not in ["id", "template_id", "created_at", "updated_at"]}
            )
            saved_placeholder = crud.template_placeholder.create(
                db=db, obj_in=placeholder_create
            )
            logger.info(f"🔍 [Debug] 创建成功: id={saved_placeholder.id}")

        logger.info(f"🔍 [Debug] 准备提交数据库事务...")
        db.commit()
        logger.info(f"✅ [Debug] 数据库事务提交成功")
        logger.info(f"✅ 保存Agent Pipeline结果成功: {placeholder_name}")
        return saved_placeholder

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 保存Agent Pipeline结果失败: {e}")
        logger.exception(e)  # 打印完整堆栈跟踪
        raise


# ================================================================================
# SSE 流式分析API - 解决前端超时问题
# ================================================================================

async def generate_analysis_progress(
    placeholder_name: str,
    placeholder_text: str,
    template_id: str,
    data_source_id: str = None,
    template_context: Dict[str, Any] = None,
    user_id: str = None,
    **kwargs
):
    """
    生成分析进度的SSE流
    在分析过程中发送阶段信息，避免前端超时
    """
    try:
        # 发送开始信号
        yield f"data: {json.dumps({'stage': 'started', 'message': f'开始分析占位符: {placeholder_name}', 'progress': 0})}\n\n"
        await asyncio.sleep(0.1)

        # 发送Schema分析阶段
        yield f"data: {json.dumps({'stage': 'schema_analysis', 'message': '正在获取数据库Schema信息...', 'progress': 20})}\n\n"
        await asyncio.sleep(0.5)

        # 发送SQL生成阶段
        yield f"data: {json.dumps({'stage': 'sql_generation', 'message': '正在生成SQL查询语句...', 'progress': 40})}\n\n"
        await asyncio.sleep(0.5)

        # 调用实际的分析逻辑
        result = await _orchestration_service.analyze_placeholder_with_full_pipeline(
            placeholder_name=placeholder_name,
            placeholder_text=placeholder_text,
            template_id=template_id,
            data_source_id=data_source_id,
            template_context=template_context,
            user_id=user_id,
            **kwargs
        )

        # 发送SQL验证阶段
        yield f"data: {json.dumps({'stage': 'sql_validation', 'message': '正在验证SQL语法和逻辑...', 'progress': 60})}\n\n"
        await asyncio.sleep(0.5)

        # 发送执行测试阶段（如果有）
        if result.get("test_result"):
            yield f"data: {json.dumps({'stage': 'sql_execution', 'message': '正在执行SQL测试...', 'progress': 80})}\n\n"
            await asyncio.sleep(0.5)

        # 发送完成信号
        yield f"data: {json.dumps({'stage': 'completed', 'message': '分析完成', 'progress': 100, 'result': result})}\n\n"

    except Exception as e:
        # 发送错误信号
        yield f"data: {json.dumps({'stage': 'error', 'message': f'分析失败: {str(e)}', 'progress': -1, 'error': str(e)})}\n\n"


@router.post("/analyze-stream")
async def analyze_placeholder_with_stream(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    流式占位符分析API - 通过SSE返回进度信息

    解决前端30秒超时问题，实时显示分析进度
    """
    try:
        # 参数验证
        placeholder_name = request.get("placeholder_name")
        placeholder_text = request.get("placeholder_text")
        template_id = request.get("template_id")

        if not all([placeholder_name, placeholder_text, template_id]):
            raise HTTPException(
                status_code=400,
                detail="缺少必需参数: placeholder_name, placeholder_text, template_id"
            )

        # 准备分析参数
        kwargs = {k: v for k, v in request.items() if k not in [
            'placeholder_name', 'placeholder_text', 'template_id',
            'data_source_id', 'template_context'
        ]}

        # 返回SSE流
        return StreamingResponse(
            generate_analysis_progress(
                placeholder_name=placeholder_name,
                placeholder_text=placeholder_text,
                template_id=template_id,
                data_source_id=request.get("data_source_id"),
                template_context=request.get("template_context"),
                user_id=str(current_user.id),
                **kwargs
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式分析启动失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动流式分析失败: {str(e)}")
