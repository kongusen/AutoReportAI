"""
步骤执行器

执行计划中的工具步骤序列
维护执行上下文并产生观察记录
支持简单的重试和错误处理
"""

import time
import logging
from typing import Any, Dict, List

from .types import AgentInput
from .tools.registry import ToolRegistry
from .auth_context import auth_manager


class StepExecutor:
    """步骤执行器"""

    def __init__(self, container) -> None:
        """
        初始化执行器

        Args:
            container: backup系统的服务容器
        """
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)
        self.registry = ToolRegistry()
        self._setup_tools()
        # 高可用：工具调用重试配置
        self.max_tool_retries = 2
        self.retry_backoff_base = 0.5  # seconds

    def _setup_tools(self) -> None:
        """设置和注册工具"""
        # 导入核心工具 (稍后创建) - SQLDraftTool已删除
        from .tools.sql_tools import SQLValidateTool, SQLExecuteTool, SQLRefineTool, SQLPolicyTool
        from .tools.schema_tools import SchemaListColumnsTool, SchemaListTablesTool, SchemaGetColumnsTool
        from .tools.chart_tools import ChartSpecTool, WordChartGeneratorTool
        from .tools.time_tools import TimeWindowTool
        from .tools.data_quality_tools import DataQualityTool
        from .tools.workflow_tools import StatBasicWorkflowTool, StatRatioWorkflowTool, StatCategoryMixWorkflowTool

        # 注册基础工具 - 移除SQLDraftTool注册
        self.registry.register(SchemaListTablesTool(self.container))
        self.registry.register(SchemaListColumnsTool(self.container))
        self.registry.register(SchemaGetColumnsTool(self.container))
        # 不再注册统一查询工具，采用两步Schema（list_tables → get_columns）
        self.registry.register(SQLValidateTool(self.container))
        self.registry.register(SQLRefineTool(self.container))
        self.registry.register(SQLExecuteTool(self.container))
        self.registry.register(SQLPolicyTool(self.container))
        self.registry.register(ChartSpecTool(self.container))
        self.registry.register(WordChartGeneratorTool(self.container))
        self.registry.register(TimeWindowTool(self.container))
        self.registry.register(DataQualityTool(self.container))
        # 工作流工具（PTOF 复合工具）
        self.registry.register(StatBasicWorkflowTool(self.container))
        self.registry.register(StatRatioWorkflowTool(self.container))
        self.registry.register(StatCategoryMixWorkflowTool(self.container))

        self._logger.info(f"已注册 {len(self.registry._tools)} 个工具")

    async def execute(self, plan: Dict[str, Any], ai: AgentInput) -> Dict[str, Any]:
        """
        执行单步骤计划 - Plan-Tool-Active-Validate循环

        Args:
            plan: 单步骤执行计划
            ai: Agent输入上下文

        Returns:
            Dict: 执行结果，支持Agent继续决策
        """
        steps = plan.get("steps", [])
        if not steps:
            return {"success": False, "error": "no_steps", "context": {}}

        # 只执行第一个步骤 - 单步骤循环原则
        step = steps[0]
        observations = []

        # 从任务上下文中提取可选的语义与参数
        semantic_info = self._extract_semantic_info(ai)

        # 将约束传入上下文
        constraints_dict = None
        try:
            c = ai.constraints
            constraints_dict = {
                "sql_only": c.sql_only,
                "output_kind": c.output_kind,
                "max_attempts": c.max_attempts,
                "policy_row_limit": c.policy_row_limit,
                "quality_min_rows": c.quality_min_rows,
            }
        except Exception:
            constraints_dict = None

        # 获取 user_id
        user_id = ai.user_id or auth_manager.get_current_user_id() or "system"

        # 规范化数据源（兼容 data_source_id → id）
        ds = ai.data_source if isinstance(ai.data_source, dict) else (ai.data_source or {})
        try:
            if ds and isinstance(ds, dict) and ("data_source_id" in ds) and ("id" not in ds):
                ds = {**ds, "id": ds.get("data_source_id")}
        except Exception:
            pass

        # 构建执行上下文
        context = {
            "user_prompt": ai.user_prompt,
            "placeholder_description": ai.placeholder.description,
            "tables": ai.schema.tables,
            "columns": ai.schema.columns,
            "window": ai.context.window,
            "data_source": ds,
            "user_id": user_id,
            "constraints": constraints_dict,
            "semantic_type": semantic_info.get("semantic_type"),
            "top_n": semantic_info.get("top_n"),
            "template_context": None,
        }
        # 注入模板上下文和累积的schema信息（如可用）
        try:
            tdc = ai.task_driven_context or {}
            if isinstance(tdc, dict):
                # 优先使用 snippet，其次使用完整 template_context（dict 用于调度）
                if tdc.get("template_context_snippet"):
                    context["template_context"] = tdc.get("template_context_snippet")
                elif tdc.get("template_context"):
                    context["template_context"] = tdc.get("template_context")

                # 从task_driven_context获取累积的schema信息
                if tdc.get("column_details"):
                    context["column_details"] = tdc["column_details"]
                    self._logger.info(f"📋 [Executor] 从task_driven_context获取column_details: {len(tdc['column_details'])}张表")
                if tdc.get("schema_summary"):
                    context["schema_summary"] = tdc["schema_summary"]
                    self._logger.info(f"📋 [Executor] 从task_driven_context获取schema_summary: {len(tdc['schema_summary'])}字符")
                if tdc.get("recommended_time_column"):
                    context["recommended_time_column"] = tdc["recommended_time_column"]
                    self._logger.info(f"📋 [Executor] 从task_driven_context获取推荐时间列: {tdc['recommended_time_column']}")
                # 覆盖基础的tables和columns如果task_driven_context有更新的版本
                if tdc.get("tables"):
                    context["tables"] = tdc["tables"]
                if tdc.get("columns"):
                    context["columns"] = tdc["columns"]
        except Exception:
            pass

        self._logger.info(f"🔄 [单步骤执行] 开始执行: {step.get('action', 'tool_call')}")

        try:
            step_start = time.time()
            step_action = step.get("action", "tool_call")

            # SQL生成动作 - 直接调用LLM生成SQL（不通过工具）
            if step_action == "sql_generation":
                reason = step.get("reason", "Agent生成SQL")
                self._logger.info(f"🧠 [Agent思考] {reason}")

                # 构建SQL生成的完整上下文
                # 先做硬性前置条件检查（gating）
                missing_time = not (context.get("start_date") or (isinstance(context.get("window"), dict) and context.get("window", {}).get("start_date")))
                missing_schema = not context.get("schema_summary") and not (context.get("columns") and len(context.get("columns")) > 0)

                # 🔍 调试：检查schema信息状态
                self._logger.debug(f"🔍 [Schema检查] schema_summary存在: {bool(context.get('schema_summary'))}")
                self._logger.debug(f"🔍 [Schema检查] columns存在: {bool(context.get('columns'))}")
                if context.get("columns"):
                    self._logger.debug(f"🔍 [Schema检查] columns数量: {len(context.get('columns'))}")
                    self._logger.debug(f"🔍 [Schema检查] columns内容: {list(context.get('columns').keys()) if isinstance(context.get('columns'), dict) else context.get('columns')}")
                self._logger.info(f"🔍 [Schema检查] missing_schema判定: {missing_schema}")
                if missing_time:
                    observations.append("⚠️ 缺少时间范围，建议先计算时间窗口 time.window")
                    decision = {
                        "success": True,
                        "action": "gating",
                        "gating_redirect": "time.window",
                        "message": "缺少时间范围，已建议先执行 time.window",
                        "next_step_hint": "请先调用 time.window 计算统计时间范围"
                    }
                    # 返回让下一轮按建议执行
                    return {
                        "success": True,
                        "step_result": decision,
                        "context": context,
                        "observations": observations,
                        "decision_info": {
                            "step_completed": "gating",
                            "step_reason": "缺少时间范围",
                            "next_recommendations": ["调用 time.window 计算时间窗口"]
                        },
                        "execution_time": int((time.time() - step_start) * 1000)
                    }

                if missing_schema:
                    observations.append("⚠️ 缺少表列信息，建议先获取列信息 schema.get_columns")

                    # 预选一批最相关的表，便于下一步直接传入 schema.get_columns
                    try:
                        suggested_tables = self._suggest_tables_from_names(
                            context.get("tables") or [],
                            context.get("placeholder_description") or ""
                        )
                        if suggested_tables:
                            context["suggested_tables"] = suggested_tables
                    except Exception:
                        suggested_tables = []

                    decision = {
                        "success": True,
                        "action": "gating",
                        "gating_redirect": "schema.get_columns",
                        "message": "缺少表列信息，已建议先执行 schema.get_columns",
                        "next_step_hint": "请先调用 schema.get_columns 获取目标表列信息",
                        "suggested_tables": suggested_tables
                    }
                    return {
                        "success": True,
                        "step_result": decision,
                        "context": context,
                        "observations": observations,
                        "decision_info": {
                            "step_completed": "gating",
                            "step_reason": "缺少表列信息",
                            "next_recommendations": ([f"调用 schema.get_columns(tables={suggested_tables}) 获取列信息"] if suggested_tables else ["调用 schema.get_columns 获取列信息"]) 
                        },
                        "execution_time": int((time.time() - step_start) * 1000)
                    }

                # 前置综合分析（表/列/模板/时间/占位符），指导SQL生成
                if not context.get("pre_sql_analysis"):
                    try:
                        pre = await self._run_pre_sql_analysis(context, user_id)
                        if pre:
                            context["pre_sql_analysis"] = pre
                            observations.append("✅ 已完成前置分析，指导SQL生成")
                    except Exception:
                        pass

                sql_prompt = self._build_sql_generation_prompt(context, step.get("input", {}))

                # 选择LLM策略
                try:
                    llm_service = getattr(self.container, 'llm_service', None) or getattr(self.container, 'llm', None)
                    if not llm_service:
                        raise ValueError("LLM service not found in container")

                    # 根据上下文构建policy
                    from .llm_strategy_manager import llm_strategy_manager
                    llm_policy = llm_strategy_manager.build_llm_policy(
                        user_id=user_id,
                        stage="tool",
                        complexity="high",
                        tool_name="sql.draft",
                        output_kind="sql",
                        context=context
                    )

                    # 调用LLM生成结构化JSON，优先从 {"sql": "..."} 获取SQL
                    llm_text = await self._call_llm(llm_service, sql_prompt, user_id, llm_policy)
                    extracted_sql = ""
                    gen_struct = None
                    try:
                        from .utils.json_utils import parse_json_safely
                        gen_struct = parse_json_safely(llm_text)
                        if isinstance(gen_struct, dict) and isinstance(gen_struct.get("sql"), str):
                            extracted_sql = gen_struct["sql"].strip()
                    except Exception:
                        gen_struct = None
                    # 兼容回退：从文本中提取SQL
                    if not extracted_sql:
                        extracted_sql = self._extract_sql(llm_text)

                    if not extracted_sql:
                        # 回退到提示词，要求后续步骤继续
                        result = {
                            "success": False,
                            "action": "sql_generation",
                            "sql_generation_prompt": sql_prompt,
                            "error": "未能从LLM输出中提取SQL",
                            "llm_raw": llm_text,
                        }
                    else:
                        result = {
                            "success": True,
                            "action": "sql_generation",
                            "sql_generation_prompt": sql_prompt,
                            "current_sql": extracted_sql,
                            "sql": extracted_sql,
                            "generation_struct": gen_struct,
                            "message": "SQL已生成",
                            "next_step_hint": "调用sql.validate验证SQL"
                        }
                except Exception as e:
                    result = {
                        "success": False,
                        "action": "sql_generation",
                        "sql_generation_prompt": sql_prompt,
                        "error": f"llm_generation_failed: {str(e)}"
                    }

            # 工具调用动作
            else:
                tool_name = step.get("tool")
                tool_input = step.get("input", {})
                reason = step.get("reason", f"执行{tool_name}")

                tool = self.registry.get(tool_name)
                if not tool:
                    return {
                        "success": False,
                        "error": f"tool_not_found: {tool_name}",
                        "context": context,
                        "observations": [f"工具 {tool_name} 未找到"]
                    }

                # 合并上下文到工具输入
                enriched_input = {**tool_input, **context}

                # 🔧 为可能访问数据库的工具添加数据源连接配置
                if tool_name in ("schema.list_columns", "schema.get_columns", "sql.validate", "sql.execute",
                                 "workflow.stat_basic", "workflow.stat_ratio", "workflow.stat_category_mix") and ai.data_source:
                    data_source_id = ai.data_source.get("data_source_id")
                    user_id = ai.user_id

                    if data_source_id and user_id:
                        try:
                            # 获取用户数据源配置
                            if hasattr(self.container, 'user_data_source_service'):
                                data_source = await self.container.user_data_source_service.get_user_data_source(
                                    user_id=user_id,
                                    data_source_id=data_source_id
                                )

                                if data_source and hasattr(data_source, 'connection_config'):
                                    # 将连接配置添加到工具输入（统一使用 data_source 字段承载）
                                    # 兼容：保留原始 ai.data_source 供上游使用
                                    enriched_input["data_source"] = data_source.connection_config
                                    enriched_input["connection_config"] = data_source.connection_config
                                    self._logger.info(f"📋 [Executor] 为{tool_name}添加数据源连接配置: {data_source_id}")
                                else:
                                    self._logger.warning(f"📋 [Executor] 未找到数据源或连接配置: {data_source_id}")
                            else:
                                self._logger.warning(f"📋 [Executor] user_data_source_service不可用，无法获取连接配置")
                        except Exception as e:
                            self._logger.error(f"📋 [Executor] 获取数据源连接配置失败: {e}")
                    else:
                        self._logger.debug(f"📋 [Executor] 缺少data_source_id或user_id，跳过连接配置获取")

                # 🚨 额外保护：检查工具输入中的SQL字段是否为描述性文本
                for sql_field in ["current_sql", "sql"]:
                    if sql_field in enriched_input:
                        sql_value = enriched_input[sql_field]
                        if sql_value and self._is_description_text(sql_value):
                            self._logger.error(f"🚨 [输入保护] {tool_name}.{sql_field} 包含描述性文本: '{sql_value[:50]}'")
                            # 尝试从context中获取正确的SQL
                            if sql_field != "current_sql" and context.get("current_sql"):
                                corrected_sql = context["current_sql"]
                                if not self._is_description_text(corrected_sql):
                                    self._logger.info(f"✅ [输入修复] 使用context.current_sql修复{sql_field}: '{corrected_sql[:50]}...'")
                                    enriched_input[sql_field] = corrected_sql
                                else:
                                    self._logger.error(f"❌ [输入保护] context.current_sql也是描述性文本，无法修复")
                                    return {
                                        "success": False,
                                        "error": "invalid_sql_description",
                                        "message": f"工具 {tool_name} 的 {sql_field} 参数包含描述性文本，无法修复",
                                        "context": context,
                                        "observations": observations + [f"❌ {tool_name}.{sql_field} 参数错误"]
                                    }

                # 智能补全 - 选择目标表：
                # - 当调用 schema.list_columns 或 schema.get_columns 且未显式传入 tables 时，
                #   基于占位符与已发现表名自动选择目标表
                if tool_name in ("schema.list_columns", "schema.get_columns"):
                    try:
                        tables_input = enriched_input.get("tables") or []
                        if not tables_input:
                            candidates = []
                            # 已在上下文中的表名（第一步发现）
                            if isinstance(context.get("tables"), list):
                                candidates = context.get("tables")
                            # 兼容 AgentInput 中的 schema 表
                            if not candidates:
                                try:
                                    if ai.schema and isinstance(ai.schema.tables, list):
                                        candidates = ai.schema.tables
                                except Exception:
                                    pass

                            # 从占位符描述推断关键词
                            keywords = self._infer_table_keywords(getattr(ai.placeholder, 'description', ''))

                            selected: List[str] = []
                            # 基于关键词从候选表筛选
                            if candidates and keywords:
                                lowered = [k for k in keywords]
                                selected = [t for t in candidates if any(k in str(t).lower() for k in lowered)]

                            # 若无关键词或未命中，采用批次扫描策略
                            if candidates and not selected:
                                batch_size = int(enriched_input.get("batch_size") or 5)
                                offset = int(context.get("schema_scan_offset") or 0)
                                # 简单相似度：根据描述中的短词对表名进行包含匹配，优先匹配到的前若干个
                                tokens = self._extract_tokens(getattr(ai.placeholder, 'description', ''))
                                ranked = []
                                for t in candidates:
                                    name = str(t).lower()
                                    score = sum(1 for tok in tokens if tok and tok in name)
                                    ranked.append((score, t))
                                ranked.sort(key=lambda x: (-x[0], str(x[1])))
                                # 如果有得分>0的，取前 batch_size；否则按offset分批
                                positives = [t for s, t in ranked if s > 0]
                                if positives:
                                    selected = positives[:batch_size]
                                else:
                                    selected = candidates[offset:offset + batch_size]
                                    context["schema_scan_offset"] = offset + batch_size

                            # 若仍未选中，尝试从 reason / tool_input 中解析显式表名
                            if not selected:
                                explicit = self._extract_explicit_tables(reason, tool_input, candidates)
                                if explicit:
                                    selected = explicit

                            if selected:
                                enriched_input["tables"] = selected
                                self._logger.info(f"🧭 [Schema批次选择] 选择表: {selected}")
                    except Exception:
                        pass

                # 前置保障：校验类/策略类/执行类工具需要SQL
                if tool_name in ("sql.validate", "sql.policy", "sql.execute"):
                    sql_in = (enriched_input.get("current_sql") or enriched_input.get("sql") or "").strip()

                    # 🚨 新增：检查SQL是否为描述文本
                    if sql_in and self._is_description_text(sql_in):
                        self._logger.error(f"🚨 [工具保护] {tool_name} 收到描述文本而非SQL: '{sql_in[:50]}'")
                        return {
                            "success": False,
                            "error": "invalid_sql_input",
                            "message": f"工具 {tool_name} 收到描述文本而非SQL语句",
                            "context": context,
                            "observations": observations + [f"❌ {tool_name} 收到无效SQL输入"]
                        }

                    if not sql_in:
                        # 若有生成提示，尝试即时生成一次，避免空SQL验证
                        try:
                            gen_prompt = context.get("sql_generation_prompt")
                            if gen_prompt:
                                self._logger.info("🧩 [预生成SQL] 缺少current_sql，使用已存在的生成提示即时产出一版")
                                llm_service = getattr(self.container, 'llm_service', None) or getattr(self.container, 'llm', None)
                                llm_policy = None
                                llm_text = await self._call_llm(llm_service, gen_prompt, user_id)
                                extracted = ""
                                try:
                                    from .utils.json_utils import parse_json_safely
                                    gen_struct = parse_json_safely(llm_text)
                                    if isinstance(gen_struct, dict) and isinstance(gen_struct.get("sql"), str):
                                        extracted = gen_struct["sql"].strip()
                                except Exception:
                                    pass
                                if not extracted:
                                    extracted = self._extract_sql(llm_text)
                                if extracted:
                                    enriched_input["current_sql"] = extracted
                                    context["current_sql"] = extracted
                                else:
                                    return {
                                        "success": False,
                                        "error": "missing_current_sql",
                                        "message": "验证/执行需要SQL，但当前为空。请先执行sql_generation。",
                                        "observations": observations + ["⚠️ 缺少current_sql，且即时生成失败"],
                                        "context": context
                                    }
                            else:
                                return {
                                    "success": False,
                                    "error": "missing_current_sql",
                                    "message": "验证/执行需要SQL，但当前为空。请先执行sql_generation。",
                                    "observations": observations + ["⚠️ 缺少current_sql，建议先生成SQL"],
                                    "context": context
                                }
                        except Exception as _:
                            return {
                                "success": False,
                                "error": "missing_current_sql",
                                "message": "验证/执行需要SQL，但当前为空。请先执行sql_generation。",
                                "observations": observations + ["⚠️ 缺少current_sql，且即时生成出错"],
                                "context": context
                            }

                self._logger.info(f"🔧 [工具执行] {tool_name} - {reason}")
                result = await self._execute_tool_with_retry(tool_name, tool, enriched_input)

            step_duration = int((time.time() - step_start) * 1000)

            # 处理执行结果
            if result.get("success"):
                observations.append(f"✅ {reason} - 成功 ({step_duration}ms)")

                # 更新上下文状态
                self._update_context_state(context, result, step.get("tool"))
                # 裁剪上下文，保留对下一轮决策最有用的关键信息
                try:
                    self._reduce_context(context, step.get("tool"), result)
                except Exception:
                    pass

                # 为Agent提供决策支持信息
                decision_info = self._build_decision_info(result, step)

                return {
                    "success": True,
                    "step_result": result,
                    "context": context,
                    "observations": observations,
                    "decision_info": decision_info,
                    "execution_time": step_duration
                }
            else:
                error_msg = result.get("error", "未知错误")
                observations.append(f"❌ {reason} - 失败: {error_msg}")

                return {
                    "success": False,
                    "error": error_msg,
                    "step_result": result,
                    "context": context,
                    "observations": observations,
                    "execution_time": step_duration
                }

        except Exception as e:
            step_duration = int((time.time() - step_start) * 1000)
            error_msg = f"执行异常: {str(e)}"
            self._logger.error(f"🚨 [执行异常] {error_msg}")

            return {
                "success": False,
                "error": f"execution_exception: {str(e)}",
                "context": context,
                "observations": [f"❌ 执行异常: {error_msg} ({step_duration}ms)"],
                "execution_time": step_duration
            }

    def _build_sql_generation_prompt(self, context: Dict[str, Any], step_input: Dict[str, Any]) -> str:
        """构建SQL生成的完整提示词（JSON输出）"""

        # 提取上下文信息
        placeholder_desc = step_input.get("placeholder", {}).get("description", "")
        if not placeholder_desc:
            placeholder_desc = context.get("placeholder_description", "")

        schema_summary = context.get("schema_summary", "")
        # 优先从扁平字段取时间，其次从 window 取
        start_date = context.get("start_date", "")
        end_date = context.get("end_date", "")
        if (not start_date or not end_date) and isinstance(context.get("window"), dict):
            w = context.get("window") or {}
            start_date = start_date or w.get("start_date") or w.get("data_start_time") or ""
            end_date = end_date or w.get("end_date") or w.get("data_end_time") or ""
        semantic_type = context.get("semantic_type", "")
        top_n = context.get("top_n", "")

        # 添加调试日志
        self._logger.info(f"🔍 [SQL生成提示] placeholder_desc: {placeholder_desc}")
        self._logger.info(f"🔍 [SQL生成提示] schema_summary: {schema_summary[:200] if schema_summary else '无schema摘要'}...")
        self._logger.info(f"🔍 [SQL生成提示] 时间范围: {start_date} ~ {end_date}")
        self._logger.info(f"🔍 [SQL生成提示] semantic_type: {semantic_type}, top_n: {top_n}")

        # 不再硬编码推荐时间列，让Agent从实际表结构中智能选择
        rec_time_col = None  # 不给默认值，让Agent自己判断

        # 构建时间提示 - 强调使用占位符格式
        time_hint = ""
        if start_date and end_date:
            if start_date == end_date:
                time_hint = f"参考时间范围: {start_date}（单日）。重要：SQL中必须使用占位符格式 {{{{start_date}}}} 和 {{{{end_date}}}} 而不是具体日期。"
            else:
                time_hint = f"参考时间范围: {start_date} 到 {end_date}。重要：SQL中必须使用占位符格式 {{{{start_date}}}} 和 {{{{end_date}}}} 而不是具体日期。"
        else:
            time_hint = "时间范围: 未指定具体日期。SQL中必须使用占位符格式 {{start_date}} 和 {{end_date}} 进行时间过滤。"

        # 构建语义类型指导
        type_guidance = ""
        if semantic_type == "ranking" and top_n:
            type_guidance = f"这是排名类查询，需要按度量降序排序并取前{top_n}名"
        elif semantic_type == "compare":
            type_guidance = "这是对比类查询，需要输出基准值、对比值、差值和百分比变化"
        elif semantic_type == "statistical":
            type_guidance = "这是统计类查询，需要计算总计、平均值或计数"

        # 若没有schema摘要，至少提供表名列表，帮助LLM避免幻觉
        if not schema_summary:
            tables = context.get("tables") or []
            columns = context.get("columns") or {}

            if tables:
                preview = ", ".join(tables[:15]) + ("..." if len(tables) > 15 else "")
                schema_summary = f"可用数据表(部分): {preview}"

                # 如果有列信息，添加到schema摘要中
                if isinstance(columns, dict) and columns:
                    schema_details = []
                    for table, cols in columns.items():
                        if isinstance(cols, list) and cols:
                            cols_preview = ", ".join(cols[:10]) + ("..." if len(cols) > 10 else "")
                            schema_details.append(f"**{table}** ({len(cols)}列): {cols_preview}")
                    if schema_details:
                        schema_summary += "\n\n详细表结构:\n" + "\n".join(schema_details)

        # 若有已筛选的目标表，明确告知只能使用这些表
        selected_tables = context.get("selected_tables") or []
        allowed_tables_note = ""
        if selected_tables:
            allowed_tables_note = f"\n**严格限制可用表**: 你只能使用以下表名之一: {', '.join(selected_tables)}\n"
        prompt = f"""
# SQL查询生成任务

## 业务需求
**用户需求**: {placeholder_desc}
**查询类型**: {semantic_type if semantic_type else "统计查询"}
**时间上下文**: {time_hint if time_hint else "无特定时间范围"}

## 数据库架构
{schema_summary}
{allowed_tables_note}

## 查询指导
{type_guidance if type_guidance else "生成符合业务需求的统计查询"}

## 前置分析（结构化）
{context.get('pre_sql_analysis') or '（本次无前置分析）'}

## 输出要求（仅返回一个JSON对象，不要其他文本）
{{
  "sql": "以单行字符串返回完整SELECT语句，时间过滤必须使用占位符格式",
  "time": {{
    "column": "实际使用的时间列名",
    "range": {{"start_date": "{{{{start_date}}}}", "end_date": "{{{{end_date}}}}"}}
  }},
  "tables": ["涉及到的真实表名列表"],
  "measures": ["COUNT(*) as cnt", "可选其他度量"],
  "dimensions": ["可选维度列名"],
  "filters": [{{"field":"列名","op":"=|IN|BETWEEN|LIKE","value":"值或数组"}}],
  "assumptions": ["可选：对不确定信息的假设"],
  "notes": ["可选：任何注意事项"]
}}

## 重要规则
1. **表名列名**: 严格使用上述数据库架构中的真实表名和列名，禁止虚构
2. **时间字段选择**: 从表结构中智能选择合适的时间字段（通常是date、datetime或timestamp类型的字段）
3. **时间过滤格式（关键）**: 必须使用占位符格式，不要使用具体日期：
   - ✅ 正确: `WHERE dt >= {{{{start_date}}}} AND dt <= {{{{end_date}}}}`
   - ✅ 正确: `WHERE DATE(时间列) BETWEEN {{{{start_date}}}} AND {{{{end_date}}}}`
   - ❌ 错误: `WHERE dt >= '2025-09-27' AND dt <= '2025-09-27'`
   - ❌ 错误: `WHERE DATE(时间列) = '2025-09-27'`
4. **占位符格式**: 使用双大括号格式 {{{{start_date}}}} 和 {{{{end_date}}}}，这样生成的SQL模板可以后续替换为实际日期
5. **智能判断**: 通过字段名称、类型、注释来判断哪个是时间字段，不要硬编码

仅返回纯JSON，不要使用Markdown代码块。
        """
        return prompt.strip()

    async def _run_pre_sql_analysis(self, context: Dict[str, Any], user_id: str) -> str:
        """使用LLM对表/列/模板/时间/占位符进行一次结构化分析，输出JSON指导点。

        目标：选定目标表/时间列/关键过滤/度量与维度建议，避免后续SQL生成走偏。
        """
        llm_service = getattr(self.container, 'llm_service', None) or getattr(self.container, 'llm', None)
        if not llm_service:
            return ""

        # 组装简要列信息（仅选中表或最多3张表，每表最多20列）
        selected = context.get("selected_tables") or context.get("tables") or []
        selected = selected[:3] if isinstance(selected, list) else []
        details = context.get("column_details") or {}
        self._logger.info(f"📋 [Executor] SQL生成提示中使用详细字段信息: {len(details)}张表, 选中表: {selected}")
        cols_preview = {}
        for t in selected:
            tmap = details.get(t) or {}
            cols_preview[t] = [{"name": k, "type": (v.get("type") if isinstance(v, dict) else None), "comment": (v.get("comment") if isinstance(v, dict) else None)} for i, (k, v) in enumerate(tmap.items()) if i < 20]

        prompt = f"""
你是数据建模与SQL规划专家。请根据以下上下文生成一份“SQL生成前的结构化分析”（JSON对象），指导下一步SQL编写。

上下文：
- 占位符描述: {context.get('placeholder_description')}
- 可选表: {', '.join(selected) if selected else '(未提供)'}
- 推荐时间列: {context.get('recommended_time_column')}
- 时间范围: {context.get('start_date') or context.get('window', {}).get('start_date')} ~ {context.get('end_date') or context.get('window', {}).get('end_date')}
- 模板上下文: {str(context.get('template_context'))[:300] if context.get('template_context') else '(无)'}
- 选表列预览: {cols_preview}

请输出一个JSON对象：
{{
  "target_table": "建议使用的表名（必须在可选表中）",
  "time_column": "建议使用的时间列",
  "measures": ["COUNT(*) as ..." 或其他度量表达式],
  "filters": [{{"field":"列名","op":"=|IN|BETWEEN|LIKE","value":"值或数组"}}],
  "dimensions": ["维度列名"],
  "sql_skeleton": "可选，给出一个SQL骨架（FROM/WHERE/时间过滤/分组/聚合）",
  "notes": ["任何注意事项"]
}}
只返回JSON，不要其他说明。
"""

        try:
            # 尽量返回JSON
            if hasattr(llm_service, 'ask'):
                res = await llm_service.ask(user_id=user_id, prompt=prompt, response_format={"type": "json_object"})
                text = res.get("response", "") if isinstance(res, dict) else str(res)
            elif hasattr(llm_service, 'generate_response'):
                res = await llm_service.generate_response(prompt=prompt, user_id=user_id, response_format={"type": "json_object"})
                text = res.get("response", "") if isinstance(res, dict) else str(res)
            else:
                text = await llm_service(prompt)
            return text.strip()
        except Exception:
            return ""

    async def _call_llm(self, llm_service, prompt: str, user_id: str = "system", llm_policy: Dict[str, Any] | None = None) -> str:
        """统一调用LLM，尽量与Planner/Orchestrator保持一致接口。"""
        try:
            if hasattr(llm_service, 'ask'):
                result = await llm_service.ask(
                    user_id=user_id,
                    prompt=prompt,
                    response_format={"type": "json_object"},
                    llm_policy=llm_policy or {"stage": "tool", "output_kind": "sql"}
                )
                return result.get("response", "") if isinstance(result, dict) else str(result)
            elif hasattr(llm_service, 'generate_response'):
                result = await llm_service.generate_response(
                    prompt=prompt,
                    user_id=user_id,
                    response_format={"type": "json_object"},
                    llm_policy=llm_policy or {"stage": "tool", "output_kind": "sql"}
                )
                return result.get("response", "") if isinstance(result, dict) else str(result)
            elif callable(llm_service):
                return await llm_service(prompt)
            else:
                raise ValueError("Unsupported LLM service interface")
        except Exception as e:
            self._logger.error(f"LLM调用失败: {str(e)}")
            raise

    def _extract_sql(self, text: str) -> str:
        """从LLM文本中提取SQL，支持```sql```代码块或纯文本。"""
        try:
            t = (text or "").strip()
            if not t:
                return ""
            # 优先提取```sql```代码块
            import re
            code_fence = re.search(r"```sql\s*([\s\S]*?)```", t, re.IGNORECASE)
            if code_fence:
                candidate = code_fence.group(1).strip()
            else:
                # 去掉通用代码块
                generic_fence = re.search(r"```\s*([\s\S]*?)```", t)
                candidate = (generic_fence.group(1).strip() if generic_fence else t)

            # 去掉开头的注释行，仅保留以SELECT/WITH开头的主体
            lines = [ln for ln in candidate.splitlines() if ln.strip()]
            body = []
            started = False
            for ln in lines:
                ln_strip = ln.strip()
                up = ln_strip.upper()
                if not started and (up.startswith("SELECT") or up.startswith("WITH")):
                    started = True
                if started:
                    body.append(ln)
            sql = "\n".join(body).strip()
            # 清理尾随反引号/多余内容
            sql = sql.strip().strip('`').strip()
            return sql
        except Exception:
            return (text or "").strip()

    async def _execute_tool_with_retry(self, tool_name: str, tool, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具，带基本重试和结果标准化。"""
        import asyncio
        from .utils.json_utils import normalize_tool_result, is_transient_error

        last_result: Dict[str, Any] | None = None
        for attempt in range(self.max_tool_retries + 1):
            if attempt > 0:
                await asyncio.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
            try:
                raw = await tool.execute(input_data)
            except Exception as e:
                raw = {"success": False, "error": str(e)}

            result = normalize_tool_result(tool_name, raw)
            last_result = result

            # 成功或非瞬时错误则停止重试
            if result.get("success") and not result.get("error"):
                break
            if not is_transient_error(result.get("error")):
                break

        return last_result or {"success": False, "error": "unknown_error"}

    def _infer_table_keywords(self, description: str) -> List[str]:
        """从占位符描述中推断用于匹配表名的关键词。"""
        try:
            text = (description or "").lower()
            keywords: List[str] = []
            # 常见退货/退款场景关键词
            if any(k in text for k in ["退货", "退款", "return", "refund"]):
                keywords.extend(["refund", "return", "退货", "退款"])
            # 常见ODS/DW前缀不强制添加，由候选表匹配
            # 去重并保持顺序
            seen = set()
            ordered = []
            for k in keywords:
                if k not in seen:
                    ordered.append(k)
                    seen.add(k)
            return ordered
        except Exception:
            return []

    def _extract_tokens(self, text: str) -> List[str]:
        """提取用于相似度匹配的短词/缩写（简单分词与降噪）。"""
        try:
            t = (text or "").lower()
            # 基础分词：非字母数字拆分 + 去停用词 + 长度过滤
            import re
            raw = re.split(r"[^a-z0-9\u4e00-\u9fa5]+", t)
            stop = {"的", "和", "与", "总数", "统计", "数量", "个数", "信息", "数据", "表", "申请"}
            tokens = [w for w in raw if w and w not in stop and len(w) >= 2]
            # 添加常见缩写映射（可扩展）
            mapped: List[str] = []
            alias = {
                "refund": ["rf", "rfd"],
                "return": ["ret", "rtn"],
            }
            for w in tokens:
                mapped.append(w)
                for key, al in alias.items():
                    if w.startswith(key):
                        mapped.extend(al)
            # 去重
            seen: set[str] = set()
            ordered: List[str] = []
            for w in mapped:
                if w not in seen:
                    ordered.append(w)
                    seen.add(w)
            return ordered
        except Exception:
            return []

    def _extract_explicit_tables(self, reason: str, tool_input: Dict[str, Any], candidates: List[str]) -> List[str]:
        """从reason或输入中解析显式表名（例如包含 `获取 ods_refund 表`）。"""
        try:
            explicit: List[str] = []
            # 1) 直接从 tool_input.tables 读取（字符串或数组）
            if isinstance(tool_input.get("tables"), list) and tool_input["tables"]:
                return tool_input["tables"]
            if isinstance(tool_input.get("tables"), str) and tool_input["tables"].strip():
                return [tool_input["tables"].strip()]

            # 2) 从 reason 中正则提取单词，匹配候选表
            import re
            text = f"{reason or ''}"
            words = re.findall(r"[A-Za-z0-9_\.]+", text)
            lowered = {c.lower(): c for c in candidates}
            for w in words:
                lw = w.lower()
                if lw in lowered:
                    explicit.append(lowered[lw])
            # 去重保持顺序
            seen: set[str] = set()
            ordered: List[str] = []
            for t in explicit:
                if t not in seen:
                    ordered.append(t)
                    seen.add(t)
            return ordered
        except Exception:
            return []

    async def execute_single_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个工具 (用于调试和测试)

        Args:
            tool_name: 工具名称
            tool_input: 工具输入

        Returns:
            Dict: 工具执行结果
        """
        tool = self.registry.get(tool_name)
        if not tool:
            return {"success": False, "error": f"工具 {tool_name} 未找到"}

        try:
            result = await tool.execute(tool_input)
            return result
        except Exception as e:
            return {"success": False, "error": f"工具执行异常: {str(e)}"}

    def _is_description_text(self, sql: str) -> bool:
        """检测是否为描述文本而非SQL - 与SQLValidateTool保持一致"""
        if not sql or not isinstance(sql, str):
            return False

        sql_lower = sql.lower().strip()

        # 明显的描述性关键词
        description_keywords = [
            "当前候选", "候选sql", "sql内容", "已有sql", "现有sql",
            "待验证", "等待", "请", "需要", "建议", "应该",
            "候选的", "当前的", "生成的", "提供的", "返回的"
        ]

        # 如果包含描述性关键词但不包含SQL关键词，可能是描述文本
        has_description = any(keyword in sql_lower for keyword in description_keywords)
        has_sql_keywords = any(keyword in sql_lower for keyword in ["select", "from", "where", "insert", "update", "delete"])

        if has_description and not has_sql_keywords:
            return True

        # 如果是很短的文本且不包含SQL关键词，可能是描述
        if len(sql.strip()) < 50 and not has_sql_keywords:
            return True

        # 如果包含中文描述性词语
        chinese_description = ["当前", "候选", "内容", "描述", "信息", "数据", "结果"]
        has_chinese_desc = any(keyword in sql for keyword in chinese_description)
        if has_chinese_desc and not has_sql_keywords:
            return True

        return False

    def list_available_tools(self) -> List[str]:
        """列出可用工具"""
        return list(self.registry._tools.keys())

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """获取工具信息"""
        tool = self.registry.get(tool_name)
        if not tool:
            return {"exists": False}

        return {
            "exists": True,
            "name": tool.name,
            "description": getattr(tool, 'description', 'No description available'),
            "type": tool.__class__.__name__
        }

    def _extract_semantic_info(self, ai: AgentInput) -> Dict[str, Any]:
        """从AgentInput的task_driven_context中提取占位符语义信息（semantic_type、top_n）。"""
        info: Dict[str, Any] = {}
        try:
            tdc = ai.task_driven_context or {}
            # 优先使用占位符ID、其次描述，尽量匹配模板上下文中的placeholder_name
            ph_candidates = []
            try:
                if ai.placeholder.id:
                    ph_candidates.append(str(ai.placeholder.id))
            except Exception:
                pass
            try:
                if ai.placeholder.description:
                    ph_candidates.append(str(ai.placeholder.description))
            except Exception:
                pass
            # 去重
            ph_candidates = list(dict.fromkeys(ph_candidates))
            contexts = tdc.get("placeholder_contexts") or []
            match = None
            for c in contexts:
                pname = c.get("placeholder_name")
                if not pname:
                    continue
                if any(pname == cand or pname in cand or cand in pname for cand in ph_candidates):
                    match = c
                    break
            if match:
                info["semantic_type"] = match.get("semantic_type")
                params = match.get("parsed_params") or {}
                if isinstance(params, dict):
                    info["top_n"] = params.get("top_n")
        except Exception:
            pass
        return info

    def _update_context_state(self, context: Dict[str, Any], result: Dict[str, Any], tool_name: str) -> None:
        """更新执行上下文状态"""
        # 将工具执行结果合并到上下文
        if isinstance(result, dict):
            for key, value in result.items():
                if key not in ["success", "error", "action", "message"]:
                    context[key] = value

        # 特殊处理关键工具的结果
        if tool_name == "sql.validate":
            if result.get("issues"):
                context["validation_issues"] = result["issues"]
            if result.get("warnings"):
                context["validation_warnings"] = result["warnings"]
            if result.get("corrected_sql"):
                context["corrected_sql"] = result["corrected_sql"]
                # 自动采用修正后的SQL作为当前SQL，便于后续策略与执行
                try:
                    if result["corrected_sql"]:
                        context["current_sql"] = result["corrected_sql"]
                except Exception:
                    pass
            if result.get("agent_analysis"):
                context["agent_analysis"] = result["agent_analysis"]

        elif tool_name == "sql.execute":
            if result.get("rows"):
                context["execution_result"] = {
                    "rows": result["rows"],
                    "columns": result.get("columns", []),
                    "row_count": len(result["rows"])
                }
                context["sql_executed_successfully"] = True

        # 通用：若工具返回了sql字段，则将其设置为当前SQL（如sql.policy、workflow.* 等）
        try:
            if isinstance(result.get("sql"), str) and result.get("sql").strip():
                context["current_sql"] = result["sql"].strip()
        except Exception:
            pass

        # 通用：若工具返回了执行结果数据（rows/columns），也视为一次执行成功（如workflow.*内部已执行SQL）
        try:
            if isinstance(result.get("rows"), list):
                context["execution_result"] = {
                    "rows": result.get("rows", []),
                    "columns": result.get("columns", []),
                    "row_count": len(result.get("rows", []))
                }
                context["sql_executed_successfully"] = True
        except Exception:
            pass

        if tool_name == "schema.list_columns":
            if result.get("schema_summary"):
                context["schema_summary"] = result["schema_summary"]
            if result.get("columns"):
                context["columns"] = result["columns"]
            if result.get("column_details"):
                context["column_details"] = result["column_details"]
                self._logger.info(f"📋 [Executor] 存储schema.list_columns详细字段信息: {len(result['column_details'])}张表")

        elif tool_name == "schema.get_columns":
            self._logger.info(f"📋 [Executor] 处理schema.get_columns结果: success={result.get('success')}")
            self._logger.info(f"📋 [Executor] 结果包含的键: {list(result.keys()) if isinstance(result, dict) else 'Not dict'}")

            if result.get("schema_summary"):
                context["schema_summary"] = result["schema_summary"]
                self._logger.info(f"📋 [Executor] 存储schema_summary: {len(result['schema_summary'])}字符")
            if result.get("columns"):
                context["columns"] = result["columns"]
                self._logger.info(f"📋 [Executor] 存储columns: {len(result['columns'])}张表")
            if result.get("column_details"):
                context["column_details"] = result["column_details"]
                self._logger.info(f"📋 [Executor] 存储schema.get_columns详细字段信息: {len(result['column_details'])}张表")
                # 显示第一个表的详细信息作为样例
                if result['column_details']:
                    first_table = list(result['column_details'].keys())[0]
                    first_columns = result['column_details'][first_table]
                    self._logger.info(f"📋 [Executor] 样例表{first_table}的字段: {list(first_columns.keys())}")
            # 不再硬编码推荐时间列，让Agent通过查看实际数据来智能判断
            # Agent比我们的算法聪明，直接查5行数据就知道哪个是时间字段了
            try:
                self._logger.info("📋 [Executor] 跳过硬编码时间列推荐，让Agent通过数据查询智能判断")
                context["use_agent_time_column_detection"] = True
            except Exception:
                pass

            # 表再筛选：基于时间列、表名关键词、维度列命中对表进行排序与选择
            try:
                selected = self._rank_and_select_tables(context, result)
                if selected:
                    context["selected_tables"] = selected
                    # 将 tables 顺序调整为所选表优先
                    tlist = context.get("tables") or []
                    rest = [t for t in tlist if t not in selected]
                    context["tables"] = selected + rest

                    # 调整推荐时间列以适配首选目标表（优先保证可用性）
                    try:
                        top_table = selected[0]
                        # 首先尝试从详细字段中获取该表列集合，否则退回 columns 简表
                        t_details = (result.get("column_details") or {}).get(top_table) or {}
                        if isinstance(t_details, dict) and t_details:
                            table_cols = {c.lower() for c in t_details.keys()}
                        else:
                            table_cols = {c.lower() for c in (result.get("columns") or {}).get(top_table, [])}

                        rec = (context.get("recommended_time_column") or "").lower()

                        # 不再硬编码调整时间列，让Agent从实际数据中判断
                        self._logger.info(f"📋 [Executor] 跳过硬编码时间列调整，让Agent智能选择 (表: {top_table})")
                    except Exception:
                        pass
            except Exception:
                pass

        elif tool_name == "time.window":
            if result.get("start_date"):
                context["start_date"] = result["start_date"]
            if result.get("end_date"):
                context["end_date"] = result["end_date"]

        elif tool_name == "chart.spec":
            if result.get("chart_spec"):
                context["chart_spec"] = result["chart_spec"]

        elif tool_name == "word_chart_generator":
            if result.get("chart_image_path"):
                context["chart_image_path"] = result["chart_image_path"]

    def _build_decision_info(self, result: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
        """构建Agent决策支持信息"""
        decision_info = {
            "step_completed": step.get("action", "tool_call"),
            "step_reason": step.get("reason", ""),
            "next_recommendations": []
        }

        # 基于执行结果提供下一步建议
        if result.get("success"):
            action = step.get("action")
            tool_name = step.get("tool")

            # SQL生成完成建议
            if action == "sql_generation":
                decision_info["next_recommendations"] = [
                    "Agent应生成SQL语句",
                    "然后调用sql.validate验证SQL正确性",
                    "如有问题则修正SQL"
                ]

            # Schema信息获取完成建议
            elif tool_name == "schema.list_columns":
                decision_info["next_recommendations"] = [
                    "Schema信息已获取，可以开始生成SQL",
                    "建议使用sql_generation动作生成SQL",
                    "确保使用真实的表名和列名"
                ]

            elif tool_name == "schema.list_tables":
                decision_info["next_recommendations"] = [
                    "已列出可用表名",
                    "请选择与需求相关的表并调用schema.get_columns获取列信息",
                    "随后使用sql_generation生成SQL"
                ]

            elif tool_name == "schema.get_columns":
                decision_info["next_recommendations"] = [
                    "已获取目标表的列信息",
                    "建议使用sql_generation生成SQL",
                    "生成后调用sql.validate验证"
                ]

            # 时间窗口计算完成建议
            elif tool_name == "time.window":
                decision_info["next_recommendations"] = [
                    "时间窗口已计算完成",
                    "建议获取Schema信息或直接生成SQL",
                    "确保在SQL中添加时间过滤条件"
                ]

            # SQL验证完成建议
            elif tool_name == "sql.validate":
                if result.get("issues"):
                    decision_info["next_recommendations"] = [
                        "SQL验证发现问题，需要修正",
                        "建议重新生成SQL解决验证问题",
                        "或调用sql.refine工具修正SQL"
                    ]
                else:
                    decision_info["next_recommendations"] = [
                        "SQL验证通过，可以执行",
                        "建议调用sql.execute获取数据",
                        "然后检查数据质量"
                    ]

            # SQL执行完成建议
            elif tool_name == "sql.execute":
                if result.get("rows"):
                    decision_info["next_recommendations"] = [
                        "SQL执行成功，数据已获取",
                        "建议调用data.quality检查数据质量",
                        "如需图表则调用chart.spec生成配置"
                    ]
                else:
                    decision_info["next_recommendations"] = [
                        "SQL执行无结果，检查SQL逻辑",
                        "可能需要调整时间范围或过滤条件"
                    ]

            # 工作流工具完成建议
            elif tool_name in ("workflow.stat_basic", "workflow.stat_ratio", "workflow.stat_category_mix"):
                if result.get("rows"):
                    decision_info["next_recommendations"] = [
                        "工作流已返回统计结果",
                        "如需继续可进行data.quality或渲染图表",
                        "否则可结束本轮PTAV"
                    ]
                else:
                    decision_info["next_recommendations"] = [
                        "工作流未返回数据，检查生成的SQL与过滤条件",
                        "必要时重新生成或放宽条件"
                    ]

        else:
            # 执行失败的通用建议
            decision_info["next_recommendations"] = [
                "上一步执行失败，分析错误原因",
                "可能需要重新规划或调整策略",
                "检查输入参数和上下文是否正确"
            ]

        return decision_info

    def _rank_and_select_tables(self, context: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """根据列详情与占位符描述为表打分选择最相关的若干表。

        打分要素：
        - 若表包含推荐时间列 +5
        - 表名命中占位符关键词（refund/return/退货/退款等）每命中 +3
        - 表内列名/注释命中维度关键词（type/category/类别/商品/产品）每命中 +2（最多加6）
        - tokens 相似包含每命中 +1（最多加5）
        """
        from collections import defaultdict

        details = result.get("column_details") or {}
        columns_map = result.get("columns") or {}
        tables = list(columns_map.keys())
        if not tables:
            return []

        placeholder_desc = context.get("placeholder_description", "")
        # 关键词与token
        kw = set(self._infer_table_keywords(placeholder_desc))
        toks = set(self._extract_tokens(placeholder_desc))
        time_col = (context.get("recommended_time_column") or "").lower()

        def score_table(tname: str) -> int:
            s = 0
            lower_name = str(tname).lower()
            # 表名关键词
            for k in kw:
                if k in lower_name:
                    s += 3
            # tokens
            tok_hits = sum(1 for tok in toks if tok and tok in lower_name)
            s += min(tok_hits, 5)  # cap

            # 时间列命中
            tdetails = details.get(tname) or {}
            if time_col and time_col in {c.lower() for c in tdetails.keys()}:
                s += 5

            # 维度关键词命中
            dim_kws = ["type", "category", "kind", "class", "商品", "品类", "类别", "产品"]
            dim_hits = 0
            for col, meta in tdetails.items():
                name_l = col.lower()
                if any(dk in name_l for dk in dim_kws):
                    dim_hits += 1
                cmt = meta.get("comment")
                if isinstance(cmt, str) and any(dk in cmt for dk in dim_kws):
                    dim_hits += 1
                if dim_hits >= 3:  # cap
                    break
            s += min(dim_hits * 2, 6)
            return s

        ranked = sorted(tables, key=lambda t: (-score_table(t), t))
        top_k = min(3, len(ranked))
        return ranked[:top_k]

    def _suggest_tables_from_names(self, candidates: List[str], description: str, top_k: int = 3) -> List[str]:
        """在只有表名时的轻量推荐：基于关键词与tokens命中进行排序。"""
        try:
            kw = set(self._infer_table_keywords(description))
            toks = set(self._extract_tokens(description))
            def score(name: str) -> int:
                n = (name or "").lower()
                s = 0
                for k in kw:
                    if k in n:
                        s += 3
                s += min(sum(1 for t in toks if t and t in n), 5)
                return s
            ranked = sorted(candidates or [], key=lambda n: (-score(n), n))
            return ranked[:min(top_k, len(ranked))]
        except Exception:
            return (candidates or [])[:min(top_k, len(candidates or []))]

    def _reduce_context(self, context: Dict[str, Any], tool_name: str, result: Dict[str, Any] | None = None) -> None:
        """裁剪上下文，删除无关或过大的字段，保留对下一步决策有价值的关键信息。

        策略：
        - 永久保留：current_sql, sql_executed_successfully, execution_result(rows/columns/row_count),
          start_date, end_date, timezone, window(仅保留轻量键), tables(最多前50个), schema_summary,
          recommended_time_column, validation_issues/warnings（短文本）。
        - column_details：仅保留当前命中的表（如有）且每表最多前20列；否则删除以减小体积。
        - 删除：大型临时文本（agent_analysis, llm_raw 等）、schema_scan_offset 等内部光标。
        """
        if not isinstance(context, dict):
            return

        keep_keys = {
            "current_sql", "sql_executed_successfully", "execution_result",
            "start_date", "end_date", "timezone", "window", "tables",
            "schema_summary", "recommended_time_column",
            "validation_issues", "validation_warnings",
        }

        # 轻量化 window
        if isinstance(context.get("window"), dict):
            w = context["window"]
            light_w = {
                k: w.get(k) for k in ["start_date", "end_date", "time_column", "timezone", "cron_expression"] if k in w
            }
            context["window"] = light_w

        # tables 限制长度
        if isinstance(context.get("tables"), list) and len(context["tables"]) > 50:
            context["tables"] = context["tables"][:50]

        # execution_result 限制样本行数
        if isinstance(context.get("execution_result"), dict):
            er = context["execution_result"]
            rows = er.get("rows")
            if isinstance(rows, list) and len(rows) > 5:
                er["rows"] = rows[:5]
                er["row_count"] = er.get("row_count", len(rows))
            context["execution_result"] = er

        # column_details 仅保留命中的表且限制每表列数
        if isinstance(context.get("column_details"), dict):
            details = context["column_details"]
            selected_tables = []
            # 从 result 或 context 中推断命中的表
            if isinstance(result, dict):
                if isinstance(result.get("tables"), list):
                    selected_tables = result.get("tables")
            if not selected_tables and isinstance(context.get("tables"), list):
                selected_tables = context.get("tables")[:3]

            new_details = {}
            for t in selected_tables:
                cols = details.get(t)
                if isinstance(cols, dict):
                    # 每表最多保留20列的元信息
                    limited = {}
                    for i, (col, meta) in enumerate(cols.items()):
                        if i >= 20:
                            break
                        limited[col] = meta
                    new_details[t] = limited
            if new_details:
                context["column_details"] = new_details
            else:
                # 无命中则删除，避免过大
                context.pop("column_details", None)

        # 删除不必要的临时/大型键
        for k in ["agent_analysis", "llm_raw", "schema_scan_offset", "sql_generation_candidates"]:
            if k in context:
                context.pop(k, None)

        # 严格保留白名单（避免误删已有关键键）
        keys = list(context.keys())
        for k in keys:
            if k not in keep_keys and k not in {"column_details"}:
                # 不删除用于内部继续使用的若干键（如 constraints, data_source 等）
                if k in {"constraints", "data_source"}:
                    continue
                # 其他键若不是必须保留的，保留现状（避免打破兼容）。仅在上面针对大对象做裁剪。
                pass
