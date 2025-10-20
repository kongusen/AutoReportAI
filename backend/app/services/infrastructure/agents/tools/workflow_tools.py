"""
工作流工具集合（PTOF 复合工具）

将固定的多步骤流程封装为“工具”，供PTAV主循环直接调度。
当前实现：
- workflow.stat_basic   标准计数统计（支持时间范围/可选过滤）
- workflow.stat_ratio   比例统计（同一SQL合并：分子/分母/占比）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import Tool


class _ToolBundle:
    """按需创建原子工具实例，复用相同container。"""

    def __init__(self, container) -> None:
        from .schema_tools import SchemaListTablesTool, SchemaGetColumnsTool
        from .time_tools import TimeWindowTool
        from .sql_tools import SQLValidateTool, SQLPolicyTool, SQLExecuteTool

        self.list_tables = SchemaListTablesTool(container)
        self.get_columns = SchemaGetColumnsTool(container)
        self.time_window = TimeWindowTool(container)
        self.sql_validate = SQLValidateTool(container)
        self.sql_policy = SQLPolicyTool(container)
        self.sql_execute = SQLExecuteTool(container)


class _LLMHelpers:
    def __init__(self, container, logger: logging.Logger) -> None:
        self.container = container
        self.logger = logger

    async def call_llm(self, prompt: str, user_id: str = "system", llm_policy: Optional[Dict[str, Any]] = None) -> str:
        llm_service = getattr(self.container, 'llm_service', None) or getattr(self.container, 'llm', None)
        if not llm_service:
            raise ValueError("LLM service not found in container")
        try:
            # 兼容 ask / generate_response 两种接口
            if hasattr(llm_service, 'ask'):
                res = await llm_service.ask(user_id=user_id, prompt=prompt, response_format={"type": "json_object"}, llm_policy=llm_policy or {"stage": "tool", "output_kind": "sql"})
                return res.get("response", "") if isinstance(res, dict) else str(res)
            if hasattr(llm_service, 'generate_response'):
                res = await llm_service.generate_response(prompt=prompt, user_id=user_id, response_format={"type": "json_object"}, llm_policy=llm_policy or {"stage": "tool", "output_kind": "sql"})
                return res.get("response", "") if isinstance(res, dict) else str(res)
            if callable(llm_service):
                return await llm_service(prompt)
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise
        raise ValueError("Unsupported LLM service interface")

    def extract_sql(self, text: str) -> str:
        """从LLM输出中提取SQL，支持```sql```代码块或纯文本。"""
        try:
            t = (text or "").strip()
            if not t:
                return ""
            import re
            m = re.search(r"```sql\s*([\s\S]*?)```", t, re.IGNORECASE)
            candidate = m.group(1).strip() if m else t
            # 去掉通用代码块包裹
            if not m:
                g = re.search(r"```\s*([\s\S]*?)```", t)
                if g:
                    candidate = g.group(1).strip()
            # 只保留从 SELECT/WITH 开始的部分
            lines = [ln for ln in candidate.splitlines() if ln.strip()]
            body, started = [], False
            for ln in lines:
                s = ln.strip()
                u = s.upper()
                if not started and (u.startswith("SELECT") or u.startswith("WITH")):
                    started = True
                if started:
                    body.append(ln)
            sql = "\n".join(body).strip()
            return sql
        except Exception:
            return (text or "").strip()


class _SchemaSelector:
    @staticmethod
    def _infer_table_keywords(description: str) -> List[str]:
        text = (description or "").lower()
        kws: List[str] = []
        if any(k in text for k in ["退货", "退款", "return", "refund"]):
            kws.extend(["refund", "return", "退货", "退款"])
        return list(dict.fromkeys(kws))

    @staticmethod
    def _extract_tokens(description: str) -> List[str]:
        import re
        t = (description or "").lower()
        raw = re.split(r"[^a-z0-9\u4e00-\u9fa5]+", t)
        stop = {"的", "和", "与", "总数", "统计", "数量", "个数", "信息", "数据", "表", "申请"}
        tokens = [w for w in raw if w and w not in stop and len(w) >= 2]
        alias = {"refund": ["rf", "rfd"], "return": ["ret", "rtn"]}
        mapped: List[str] = []
        for w in tokens:
            mapped.append(w)
            for key, al in alias.items():
                if w.startswith(key):
                    mapped.extend(al)
        return list(dict.fromkeys(mapped))

    def select_tables(self, candidates: List[str], placeholder_description: str, batch_size: int = 5) -> List[str]:
        if not candidates:
            return []
        keywords = self._infer_table_keywords(placeholder_description)
        selected: List[str] = []
        if keywords:
            lowered = [k for k in keywords]
            matched = [t for t in candidates if any(k in str(t).lower() for k in lowered)]
            # 优先返回单表，避免LLM生成复杂SQL
            selected = [matched[0]] if matched else []
        if not selected:
            toks = self._extract_tokens(placeholder_description)
            ranked = []
            for t in candidates:
                name = str(t).lower()
                score = sum(1 for tok in toks if tok and tok in name)
                ranked.append((score, t))
            ranked.sort(key=lambda x: (-x[0], str(x[1])))
            positives = [t for s, t in ranked if s > 0]
            # 优先返回单表（最匹配的），只有在明确需要多表时才返回多表
            selected = [positives[0]] if positives else [candidates[0]] if candidates else []
        return selected


class StatBasicWorkflowTool(Tool):
    """标准计数统计工作流（PTOF 复合工具）"""

    def __init__(self, container) -> None:
        super().__init__()
        self.name = "workflow.stat_basic"
        self.description = "标准计数统计（时间范围 + 可选过滤）"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)
        self._tools = _ToolBundle(container)
        self._llm = _LLMHelpers(container, self._logger)
        self._selector = _SchemaSelector()

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            user_id = input_data.get("user_id", "system")
            data_source = input_data.get("data_source", {})
            window = input_data.get("window", {})
            placeholder_desc = input_data.get("placeholder_description", "")
            batch_size = int(input_data.get("batch_size", 5))

            observations: List[str] = []

            # 1) 时间窗口（若缺失则计算）
            if not (window and (window.get("start_date") or window.get("task_schedule"))):
                tw = await self._tools.time_window.execute({
                    "task_time": input_data.get("task_time"),
                    "granularity": input_data.get("granularity", "daily"),
                    "timezone": input_data.get("timezone", "Asia/Shanghai"),
                })
                if tw.get("success"):
                    window = {"start_date": tw["window"].get("start"), "end_date": tw["window"].get("end"), "time_column": input_data.get("time_column")}
                    observations.append("✅ 计算时间窗口成功")
                else:
                    observations.append("⚠️ 时间窗口缺失，继续尝试")

            # 2) 列出表
            tables = input_data.get("tables") or []
            if not tables:
                lt = await self._tools.list_tables.execute({"data_source": data_source})
                if not lt.get("success"):
                    return {"success": False, "error": f"list_tables_failed: {lt.get('error')}", "observations": observations}
                tables = lt.get("tables", [])
                observations.append(f"✅ 获取表名成功: {len(tables)}")

            # 3) 选择目标表并获取列
            selected_tables = input_data.get("spec", {}).get("table_hint") or input_data.get("tables_selected") or []
            if not selected_tables:
                selected_tables = self._selector.select_tables(tables, placeholder_desc, batch_size=batch_size)
            gc = await self._tools.get_columns.execute({
                "tables": selected_tables,
                "data_source": data_source,
            })
            if not gc.get("success"):
                return {"success": False, "error": f"get_columns_failed: {gc.get('error')}", "observations": observations}
            schema_summary = gc.get("schema_summary", "")
            observations.append(f"✅ 获取列信息成功: {len(gc.get('columns', {}))} 张表")

            # 4) 生成SQL（计数统计）- 基于真实Schema动态生成，使用占位符时间格式
            if not schema_summary or not selected_tables:
                return {"success": False, "error": "insufficient_schema_info", "message": "缺少有效的表结构信息，无法生成SQL", "observations": observations}

            # 动态生成指导语句，移除硬编码的业务假设
            available_tables_info = f"可用表: {', '.join(selected_tables)}"
            guidance = (
                f"基于用户需求和真实数据库架构生成统计SQL；"
                f"严格使用以下表和列: {available_tables_info}；"
                f"生成COUNT统计查询；以JSON对象返回，key为sql，不要解释。"
            )

            sql_prompt = f"""
# 数据统计SQL生成

## 用户需求
{placeholder_desc or '统计数据总数'}

## 可用数据库架构
{schema_summary}

## 生成要求（仅返回JSON对象，不要其他文本）
- **保持简单**: 只生成满足用户需求的最简单SQL查询
- **单表优先**: 优先使用单张表，避免不必要的JOIN或复杂聚合
- **精确匹配需求**: 严格按照用户描述生成SQL，避免添加用户未明确要求的额外统计维度
- 必须使用上述真实存在的表名与列名
- **时间过滤统一规范**: 查询必须使用日期范围 dt >= {{start_date}} AND dt <= {{end_date}} 进行过滤
- **环比查询**: 对于环比查询，使用 {{prev_start_date}} 和 {{prev_end_date}}
- **百分比计算**: 对于计算占比或百分比的查询，SQL本身不要包含 CONCAT 或 '%' 符号，只返回 ROUND(...) 计算出的纯数字
- **不要添加额外的计算列**: 只返回用户明确要求的指标
- 返回形如：{{"sql": "SELECT ..."}}

## 输出格式
仅返回一个JSON对象：{{"sql": "SELECT ..."}}

重要提醒：所有时间相关的过滤都使用占位符格式（如 {{start_date}}），不要使用具体的日期值。
"""

            llm_text = await self._llm.call_llm(sql_prompt, user_id=user_id)
            # 优先解析JSON结构
            try:
                import json
                data = json.loads(llm_text)
                sql = data.get("sql") if isinstance(data, dict) else None
            except Exception:
                sql = None
            if not sql:
                sql = self._llm.extract_sql(llm_text)
            if not sql:
                return {
                    "success": False,
                    "error": "sql_generation_empty",
                    "observations": observations,
                    "sql_prompt": sql_prompt,
                    "should_replan": True,  # 建议重新规划
                    "replan_reason": "SQL生成失败，可能需要重新分析Schema或调整策略"
                }
            observations.append("✅ 生成SQL成功")

            # 保存原始带占位符的SQL
            placeholder_sql = sql

            # 5) 验证阶段：将占位符替换为真实时间进行测试
            # 使用时间窗口中的真实日期替换占位符
            test_sql = sql
            if window and window.get("start_date") and window.get("end_date"):
                test_sql = test_sql.replace("{{start_date}}", f"'{window['start_date']}'")
                test_sql = test_sql.replace("{{end_date}}", f"'{window['end_date']}'")
                observations.append(f"✅ 替换占位符进行验证: {window['start_date']} ~ {window['end_date']}")

            v = await self._tools.sql_validate.execute({
                "sql": test_sql,  # 使用替换后的SQL进行验证
                "user_id": user_id,
                "data_source": data_source,
                "semantic_type": "statistical",
            })
            if not v.get("success") and not v.get("corrected_sql"):
                return {"success": False, "error": f"sql_validate_failed: {v.get('error')}", "issues": v.get("issues", []), "observations": observations, "sql": placeholder_sql}

            # 如果验证器修正了SQL，需要将修正应用到占位符版本
            if v.get("corrected_sql") and v.get("corrected_sql") != test_sql:
                # 将修正后的SQL转换回占位符格式
                corrected_sql = v.get("corrected_sql")
                if window and window.get("start_date") and window.get("end_date"):
                    corrected_sql = corrected_sql.replace(f"'{window['start_date']}'", "{{start_date}}")
                    corrected_sql = corrected_sql.replace(f"'{window['end_date']}'", "{{end_date}}")
                placeholder_sql = corrected_sql
                test_sql = v.get("corrected_sql")

            observations.append("✅ SQL验证通过/已修正")

            p = await self._tools.sql_policy.execute({"sql": test_sql, "user_id": user_id, "data_source": data_source})
            if not p.get("success"):
                return {"success": False, "error": f"sql_policy_failed: {p.get('error')}", "observations": observations, "sql": placeholder_sql}

            # 策略修正也需要转换回占位符格式
            if p.get("sql") and p.get("sql") != test_sql:
                policy_sql = p.get("sql")
                if window and window.get("start_date") and window.get("end_date"):
                    policy_sql = policy_sql.replace(f"'{window['start_date']}'", "{{start_date}}")
                    policy_sql = policy_sql.replace(f"'{window['end_date']}'", "{{end_date}}")
                placeholder_sql = policy_sql
                test_sql = p.get("sql")

            observations.append("✅ 应用策略成功")

            ex = await self._tools.sql_execute.execute({"sql": test_sql, "user_id": user_id, "data_source": data_source})
            if not ex.get("success"):
                return {"success": False, "error": f"sql_execute_failed: {ex.get('error')}", "observations": observations, "sql": placeholder_sql}
            rows = ex.get("rows", [])
            cols = ex.get("columns", [])
            count_value = None
            try:
                if rows and cols:
                    count_value = rows[0][0]
            except Exception:
                count_value = None

            return {
                "success": True,
                "sql": placeholder_sql,  # 返回带占位符的原始SQL
                "rows": rows,
                "columns": cols,
                "metric": "count",
                "value": count_value,
                "observations": observations,
                "test_sql": test_sql,  # 额外返回验证时使用的SQL，便于调试
                "validation_passed": True
            }

        except Exception as e:
            self._logger.error(f"StatBasic工作流执行异常: {e}")
            return {"success": False, "error": str(e)}


class StatRatioWorkflowTool(Tool):
    """比例统计工作流（PTOF 复合工具）

    生成单SQL：分子/分母/占比（尽可能在数据库端计算）。
    """

    def __init__(self, container) -> None:
        super().__init__()
        self.name = "workflow.stat_ratio"
        self.description = "比例统计（单SQL：分子/分母/占比）"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)
        self._tools = _ToolBundle(container)
        self._llm = _LLMHelpers(container, self._logger)
        self._selector = _SchemaSelector()

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            user_id = input_data.get("user_id", "system")
            data_source = input_data.get("data_source", {})
            window = input_data.get("window", {})
            placeholder_desc = input_data.get("placeholder_description", "")
            batch_size = int(input_data.get("batch_size", 5))

            observations: List[str] = []

            # 1) 时间窗口
            if not (window and (window.get("start_date") or window.get("task_schedule"))):
                tw = await self._tools.time_window.execute({
                    "task_time": input_data.get("task_time"),
                    "granularity": input_data.get("granularity", "daily"),
                    "timezone": input_data.get("timezone", "Asia/Shanghai"),
                })
                if tw.get("success"):
                    window = {"start_date": tw["window"].get("start"), "end_date": tw["window"].get("end"), "time_column": input_data.get("time_column")}
                    observations.append("✅ 计算时间窗口成功")

            # 2) 列出表
            tables = input_data.get("tables") or []
            if not tables:
                lt = await self._tools.list_tables.execute({"data_source": data_source})
                if not lt.get("success"):
                    return {"success": False, "error": f"list_tables_failed: {lt.get('error')}", "observations": observations}
                tables = lt.get("tables", [])
                observations.append(f"✅ 获取表名成功: {len(tables)}")

            # 3) 选择表 + 获取列
            selected_tables = input_data.get("spec", {}).get("table_hint") or input_data.get("tables_selected") or []
            if not selected_tables:
                selected_tables = self._selector.select_tables(tables, placeholder_desc, batch_size=batch_size)
            gc = await self._tools.get_columns.execute({
                "tables": selected_tables,
                "data_source": data_source,
            })
            if not gc.get("success"):
                return {"success": False, "error": f"get_columns_failed: {gc.get('error')}", "observations": observations}
            schema_summary = gc.get("schema_summary", "")
            observations.append(f"✅ 获取列信息成功: {len(gc.get('columns', {}))} 张表")

            # 4) 生成SQL（分子/分母/占比，单SQL）- 使用占位符时间格式

            sql_prompt = f"""
# 比例统计 SQL 生成

## 需求
{placeholder_desc or '统计某类退货单数量占总退货单数量的比例'}

## 数据库架构
{schema_summary}

## 要求（仅返回JSON对象，不要其他文本）
- 生成单条可执行SQL，输出以下列：cnt_target, cnt_total, ratio
- 使用 SUM(CASE WHEN ...) AS cnt_target，COUNT(*) AS cnt_total
- ratio = cnt_target / NULLIF(cnt_total, 0)
- **时间过滤统一规范**: 查询必须使用日期范围 dt >= {{start_date}} AND dt <= {{end_date}} 进行过滤
- **环比查询**: 对于环比查询，使用 {{prev_start_date}} 和 {{prev_end_date}}
- **百分比计算**: SQL本身不要包含 CONCAT 或 '%' 符号，只返回 ROUND(...) 计算出的纯数字
- 使用真实存在的表名与列名；返回形如：{{"sql": "SELECT ..."}}

重要提醒：所有时间相关的过滤都使用占位符格式（如 {{start_date}}），不要使用具体的日期值。
"""

            llm_text = await self._llm.call_llm(sql_prompt, user_id=user_id)
            try:
                import json
                data = json.loads(llm_text)
                sql = data.get("sql") if isinstance(data, dict) else None
            except Exception:
                sql = None
            if not sql:
                sql = self._llm.extract_sql(llm_text)
            if not sql:
                return {"success": False, "error": "sql_generation_empty", "observations": observations, "sql_prompt": sql_prompt}
            observations.append("✅ 生成SQL成功")

            # 保存原始带占位符的SQL
            placeholder_sql = sql

            # 5) 验证阶段：将占位符替换为真实时间进行测试
            test_sql = sql
            if window and window.get("start_date") and window.get("end_date"):
                test_sql = test_sql.replace("{{start_date}}", f"'{window['start_date']}'")
                test_sql = test_sql.replace("{{end_date}}", f"'{window['end_date']}'")
                observations.append(f"✅ 替换占位符进行验证: {window['start_date']} ~ {window['end_date']}")

            v = await self._tools.sql_validate.execute({
                "sql": test_sql,  # 使用替换后的SQL进行验证
                "user_id": user_id,
                "data_source": data_source,
                "semantic_type": "statistical",
            })
            if not v.get("success") and not v.get("corrected_sql"):
                return {"success": False, "error": f"sql_validate_failed: {v.get('error')}", "issues": v.get("issues", []), "observations": observations, "sql": placeholder_sql}

            # 如果验证器修正了SQL，需要将修正应用到占位符版本
            if v.get("corrected_sql") and v.get("corrected_sql") != test_sql:
                corrected_sql = v.get("corrected_sql")
                if window and window.get("start_date") and window.get("end_date"):
                    corrected_sql = corrected_sql.replace(f"'{window['start_date']}'", "{{start_date}}")
                    corrected_sql = corrected_sql.replace(f"'{window['end_date']}'", "{{end_date}}")
                placeholder_sql = corrected_sql
                test_sql = v.get("corrected_sql")

            observations.append("✅ SQL验证通过/已修正")

            p = await self._tools.sql_policy.execute({"sql": test_sql, "user_id": user_id, "data_source": data_source})
            if not p.get("success"):
                return {"success": False, "error": f"sql_policy_failed: {p.get('error')}", "observations": observations, "sql": placeholder_sql}

            # 策略修正也需要转换回占位符格式
            if p.get("sql") and p.get("sql") != test_sql:
                policy_sql = p.get("sql")
                if window and window.get("start_date") and window.get("end_date"):
                    policy_sql = policy_sql.replace(f"'{window['start_date']}'", "{{start_date}}")
                    policy_sql = policy_sql.replace(f"'{window['end_date']}'", "{{end_date}}")
                placeholder_sql = policy_sql
                test_sql = p.get("sql")

            observations.append("✅ 应用策略成功")

            ex = await self._tools.sql_execute.execute({"sql": test_sql, "user_id": user_id, "data_source": data_source})
            if not ex.get("success"):
                return {"success": False, "error": f"sql_execute_failed: {ex.get('error')}", "observations": observations, "sql": placeholder_sql}
            rows = ex.get("rows", [])
            cols = ex.get("columns", [])

            # 解析结果
            metrics = {"cnt_target": None, "cnt_total": None, "ratio": None}
            try:
                if rows and cols:
                    lc = [c.lower() for c in cols]
                    # 尝试按列名取值
                    def get_col(name: str) -> Optional[int]:
                        if name in lc:
                            idx = lc.index(name)
                            return rows[0][idx]
                        return None
                    metrics["cnt_target"] = get_col("cnt_target")
                    metrics["cnt_total"] = get_col("cnt_total")
                    metrics["ratio"] = get_col("ratio")
                    # 回退：若列名不匹配，尝试前两列推断
                    if metrics["cnt_target"] is None and len(cols) >= 2:
                        metrics["cnt_target"] = rows[0][0]
                        metrics["cnt_total"] = rows[0][1]
                        try:
                            t = float(metrics["cnt_target"] or 0)
                            d = float(metrics["cnt_total"] or 0)
                            metrics["ratio"] = (t / d) if d else 0.0
                        except Exception:
                            metrics["ratio"] = None
            except Exception:
                pass

            return {
                "success": True,
                "sql": placeholder_sql,  # 返回带占位符的原始SQL
                "rows": rows,
                "columns": cols,
                "metrics": metrics,
                "observations": observations,
                "test_sql": test_sql,  # 额外返回验证时使用的SQL，便于调试
                "validation_passed": True
            }

        except Exception as e:
            self._logger.error(f"StatRatio工作流执行异常: {e}")
            return {"success": False, "error": str(e)}


class StatCategoryMixWorkflowTool(Tool):
    """分类构成/占比 工作流（PTOF 复合工具）

    支持 includes（显式类目）、other_bucket（其他补集）、union_groups（合并组）、topn（可选），
    在可能的情况下生成单SQL：CASE WHEN + GROUP BY，一次返回各分类的 cnt/ratio。
    """

    def __init__(self, container) -> None:
        super().__init__()
        self.name = "workflow.stat_category_mix"
        self.description = "分类构成/占比（支持其他/合并组/TopN）"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)
        self._tools = _ToolBundle(container)
        self._llm = _LLMHelpers(container, self._logger)
        self._selector = _SchemaSelector()

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            user_id = input_data.get("user_id", "system")
            data_source = input_data.get("data_source", {})
            window = input_data.get("window", {})
            placeholder_desc = input_data.get("placeholder_description", "")
            batch_size = int(input_data.get("batch_size", 5))

            # category_set 通用参数（均为可选，未提供则交由LLM推断）
            category_set = (input_data.get("spec") or {}).get("category_set", {})
            dimension = category_set.get("dimension") or input_data.get("category_dimension") or "product_type"
            includes: List[str] = category_set.get("includes", input_data.get("includes", [])) or []
            other_bucket: bool = bool(category_set.get("other_bucket", input_data.get("other_bucket", True)))
            union_groups: List[Dict[str, Any]] = category_set.get("union_groups", input_data.get("union_groups", [])) or []
            topn: Optional[int] = category_set.get("topn") or input_data.get("topn")

            observations: List[str] = []

            # 1) 时间窗口
            if not (window and (window.get("start_date") or window.get("task_schedule"))):
                tw = await self._tools.time_window.execute({
                    "task_time": input_data.get("task_time"),
                    "granularity": input_data.get("granularity", "daily"),
                    "timezone": input_data.get("timezone", "Asia/Shanghai"),
                })
                if tw.get("success"):
                    window = {"start_date": tw["window"].get("start"), "end_date": tw["window"].get("end"), "time_column": input_data.get("time_column")}
                    observations.append("✅ 计算时间窗口成功")

            # 2) 列出表
            tables = input_data.get("tables") or []
            if not tables:
                lt = await self._tools.list_tables.execute({"data_source": data_source})
                if not lt.get("success"):
                    return {"success": False, "error": f"list_tables_failed: {lt.get('error')}", "observations": observations}
                tables = lt.get("tables", [])
                observations.append(f"✅ 获取表名成功: {len(tables)}")

            # 3) 选择表 + 获取列
            selected_tables = input_data.get("tables_selected") or []
            if not selected_tables:
                selected_tables = self._selector.select_tables(tables, placeholder_desc, batch_size=batch_size)
            gc = await self._tools.get_columns.execute({
                "tables": selected_tables,
                "data_source": data_source,
            })
            if not gc.get("success"):
                return {"success": False, "error": f"get_columns_failed: {gc.get('error')}", "observations": observations}
            schema_summary = gc.get("schema_summary", "")
            observations.append(f"✅ 获取列信息成功: {len(gc.get('columns', {}))} 张表")

            # 4) 生成SQL（分类构成/占比）
            time_hint = ""
            if window and window.get("start_date") and window.get("end_date"):
                time_hint = f"时间范围: {window['start_date']} ~ {window['end_date']}"
            time_col = window.get("time_column") if window else None

            includes_desc = f"指定分类: {', '.join(includes)}" if includes else "指定分类: (未指定)"
            other_desc = "需要‘其他’补集: 是" if other_bucket else "需要‘其他’补集: 否"
            union_desc = f"合并组: {', '.join([g.get('name') for g in union_groups])}" if union_groups else "合并组: (无)"
            topn_desc = f"TopN: {topn}" if topn else "TopN: (未指定)"

            sql_prompt = f"""
# 分类构成/占比 SQL 生成

## 需求
{placeholder_desc or '按分类输出数量与占比'}
维度: {dimension}
{includes_desc}
{other_desc}
{union_desc}
{topn_desc}
{time_hint or '无明确时间范围'}

## 数据库架构
{schema_summary}

## 要求（仅返回JSON对象，不要其他文本）
- 生成单条可执行SQL，输出列：category, cnt, ratio
- category字段需满足：
  - 若提供includes：这些分类必须单独呈现；
  - 若需要其他补集：未包含在includes内的全部分类归为'其他'；
  - 若提供union_groups：各合并组作为额外分类，名称为其name；
  - 若提供topN：选取计数前N的分类，其余合并为'其他'（当includes为空时优先生效）。
- ratio = cnt / NULLIF(SUM(cnt) OVER (), 0)
- WHERE 子句必须包含基于 {time_col} 的时间范围过滤
- 使用真实存在的表名与列名；返回形如：{{"sql": "SELECT ..."}}。
"""

            llm_text = await self._llm.call_llm(sql_prompt, user_id=user_id)
            try:
                import json
                data = json.loads(llm_text)
                sql = data.get("sql") if isinstance(data, dict) else None
            except Exception:
                sql = None
            if not sql:
                sql = self._llm.extract_sql(llm_text)
            if not sql:
                return {"success": False, "error": "sql_generation_empty", "observations": observations, "sql_prompt": sql_prompt}
            observations.append("✅ 生成SQL成功")

            # 保存原始带占位符的SQL
            placeholder_sql = sql

            # 5) 验证阶段：将占位符替换为真实时间进行测试
            test_sql = sql
            if window and window.get("start_date") and window.get("end_date"):
                test_sql = test_sql.replace("{{start_date}}", f"'{window['start_date']}'")
                test_sql = test_sql.replace("{{end_date}}", f"'{window['end_date']}'")
                observations.append(f"✅ 替换占位符进行验证: {window['start_date']} ~ {window['end_date']}")

            v = await self._tools.sql_validate.execute({
                "sql": test_sql,  # 使用替换后的SQL进行验证
                "user_id": user_id,
                "data_source": data_source,
                "semantic_type": "statistical",
            })
            if not v.get("success") and not v.get("corrected_sql"):
                return {"success": False, "error": f"sql_validate_failed: {v.get('error')}", "issues": v.get("issues", []), "observations": observations, "sql": placeholder_sql}

            # 如果验证器修正了SQL，需要将修正应用到占位符版本
            if v.get("corrected_sql") and v.get("corrected_sql") != test_sql:
                corrected_sql = v.get("corrected_sql")
                if window and window.get("start_date") and window.get("end_date"):
                    corrected_sql = corrected_sql.replace(f"'{window['start_date']}'", "{{start_date}}")
                    corrected_sql = corrected_sql.replace(f"'{window['end_date']}'", "{{end_date}}")
                placeholder_sql = corrected_sql
                test_sql = v.get("corrected_sql")

            observations.append("✅ SQL验证通过/已修正")

            p = await self._tools.sql_policy.execute({"sql": test_sql, "user_id": user_id, "data_source": data_source})
            if not p.get("success"):
                return {"success": False, "error": f"sql_policy_failed: {p.get('error')}", "observations": observations, "sql": placeholder_sql}

            # 策略修正也需要转换回占位符格式
            if p.get("sql") and p.get("sql") != test_sql:
                policy_sql = p.get("sql")
                if window and window.get("start_date") and window.get("end_date"):
                    policy_sql = policy_sql.replace(f"'{window['start_date']}'", "{{start_date}}")
                    policy_sql = policy_sql.replace(f"'{window['end_date']}'", "{{end_date}}")
                placeholder_sql = policy_sql
                test_sql = p.get("sql")

            observations.append("✅ 应用策略成功")

            ex = await self._tools.sql_execute.execute({"sql": test_sql, "user_id": user_id, "data_source": data_source})
            if not ex.get("success"):
                return {"success": False, "error": f"sql_execute_failed: {ex.get('error')}", "observations": observations, "sql": placeholder_sql}
            rows = ex.get("rows", [])
            cols = ex.get("columns", [])

            return {
                "success": True,
                "sql": placeholder_sql,  # 返回带占位符的原始SQL
                "rows": rows,
                "columns": cols,
                "dimension": dimension,
                "includes": includes,
                "other_bucket": other_bucket,
                "union_groups": union_groups,
                "topn": topn,
                "observations": observations,
                "test_sql": test_sql,  # 额外返回验证时使用的SQL，便于调试
                "validation_passed": True
            }

        except Exception as e:
            self._logger.error(f"StatCategoryMix工作流执行异常: {e}")
            return {"success": False, "error": str(e)}
