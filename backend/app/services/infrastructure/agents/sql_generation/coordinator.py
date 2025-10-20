"""
SQL生成协调器 - 实现SQL-First架构

核心职责：
1. 主动解决依赖（时间、Schema）
2. 调用结构化SQL生成器
3. 三层验证（语法 + Schema + DryRun）
4. 智能修复与降级保护
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .context import SQLContext, SQLDependencyState, SQLGenerationResult, SQLReadiness
from .generators import StructuredSQLGenerator
from .resolvers import SchemaResolver, TimeResolver
from .validators import SQLValidator, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class SQLGenerationConfig:
    """SQL生成协调器配置"""

    max_generation_attempts: int = 3
    max_fix_attempts: int = 2
    enable_dry_run_validation: bool = True
    feature_flag_key: str = "enable_sql_generation_coordinator"


class SQLGenerationCoordinator:
    """
    SQL生成协调器 - 统一管理SQL生成的完整流程

    架构优势：
    - 依赖前置：同步解决schema和时间依赖
    - 结构化输出：强制LLM返回JSON格式
    - 分层验证：语法→Schema→数据库三层保障
    - 智能修复：自动修正常见问题
    - 明确失败：生成失败直接报错，不做低质量降级
    """

    def __init__(
        self,
        container,
        llm_client,
        db_connector,
        config: Optional[SQLGenerationConfig] = None,
    ):
        self.container = container
        self.llm = llm_client
        self.db = db_connector
        self.config = config or SQLGenerationConfig()

        # 初始化组件
        self.time_resolver = TimeResolver(container)
        self.schema_resolver = SchemaResolver(container)
        self.generator = StructuredSQLGenerator(llm_client)
        self.validator = SQLValidator(db_connector, container)

        logger.info("✅ SQLGenerationCoordinator initialized (no template fallback)")

    async def generate(
        self,
        query: str,
        context_snapshot: Dict[str, Any],
    ) -> SQLGenerationResult:
        """
        主入口：生成并验证SQL

        Args:
            query: 用户查询文本（如"统计昨日销售额"）
            context_snapshot: 执行上下文快照（包含时间、schema等）

        Returns:
            SQLGenerationResult: 包含成功状态、SQL和元数据
        """
        logger.info(f"🚀 [SQLCoordinator] 开始生成SQL: {query[:100]}")

        # 构建SQL上下文
        sql_context = self._build_sql_context(query, context_snapshot)

        try:
            # ===== Phase 1: 依赖解决（主动同步） =====
            readiness = await self._resolve_dependencies(sql_context, context_snapshot)

            if readiness != SQLReadiness.READY:
                return self._handle_dependency_missing(sql_context, readiness)

            # ===== Phase 2: SQL生成（最多3次重试）=====
            for attempt in range(self.config.max_generation_attempts):
                logger.info(f"🔧 [SQLCoordinator] 第{attempt + 1}次生成尝试")

                sql_result = await self.generator.generate(
                    prompt=self._build_generation_prompt(sql_context, attempt),
                    attempt=attempt,
                )

                if not sql_result.success:
                    sql_context.previous_attempts.append(
                        {
                            "attempt": attempt + 1,
                            "error": sql_result.error,
                            "raw_output": sql_result.raw_output,
                        }
                    )
                    continue

                # ===== Phase 3: 验证 =====
                validation = await self.validator.validate(
                    sql=sql_result.sql,
                    schema=sql_context.schema,
                    context=context_snapshot,
                )

                if validation.is_valid:
                    logger.info("✅ [SQLCoordinator] SQL生成并验证成功")
                    return SQLGenerationResult.success_result(
                        sql=sql_result.sql,
                        metadata={
                            "attempt": attempt + 1,
                            "confidence": sql_result.confidence,
                            "explanation": sql_result.explanation,
                            "validation": validation.to_dict(),
                        },
                    )

                # ===== Phase 4: 智能修复 =====
                if validation.is_fixable and attempt < self.config.max_fix_attempts:
                    logger.info("🔧 [SQLCoordinator] 尝试自动修复SQL")
                    fixed_sql = await self._apply_intelligent_fixes(
                        sql=sql_result.sql,
                        issues=validation.issues,
                        context=sql_context,
                    )

                    if fixed_sql:
                        revalidation = await self.validator.validate(
                            sql=fixed_sql,
                            schema=sql_context.schema,
                            context=context_snapshot,
                        )

                        if revalidation.is_valid:
                            logger.info("✅ [SQLCoordinator] 修复后SQL验证成功")
                            return SQLGenerationResult.success_result(
                                sql=fixed_sql,
                                metadata={
                                    "attempt": attempt + 1,
                                    "fixed": True,
                                    "original_issues": validation.issues,
                                },
                            )

                # 记录失败尝试
                sql_context.previous_attempts.append(
                    {
                        "attempt": attempt + 1,
                        "sql": sql_result.sql,
                        "validation_issues": validation.issues,
                    }
                )

            # ===== 最终失败：明确报错 =====
            logger.error(f"❌ [SQLCoordinator] {self.config.max_generation_attempts}次尝试后仍无法生成有效SQL")

            # 构建详细的错误信息
            error_summary = self._build_error_summary(sql_context)

            return SQLGenerationResult.failed_result(
                error=error_summary["message"],
                debug_info=sql_context.previous_attempts,
                metadata={
                    "total_attempts": self.config.max_generation_attempts,
                    "failure_reasons": error_summary["reasons"],
                    "suggestions": error_summary["suggestions"],
                },
            )

        except Exception as exc:
            logger.error(f"❌ [SQLCoordinator] 异常: {exc}", exc_info=True)
            return SQLGenerationResult.failed_result(
                error=f"coordinator_exception: {exc}",
                metadata={"query": query},
            )

    async def _resolve_dependencies(
        self,
        sql_context: SQLContext,
        context_snapshot: Dict[str, Any],
    ) -> SQLReadiness:
        """
        主动解决SQL生成的依赖

        优先级：
        1. 时间窗口（time_window）
        2. Schema信息（tables + columns）
        """
        deps = sql_context.dependency_state

        # 1. 解决时间依赖
        if not deps.time_window:
            logger.info("🔍 [SQLCoordinator] 解决时间依赖")
            existing_window = (
                context_snapshot.get("window")
                or context_snapshot.get("time_window")
                or context_snapshot.get("time_context")
            )

            time_result = await self.time_resolver.resolve(
                query=sql_context.query,
                existing_window=existing_window,
            )

            if time_result.success:
                sql_context.time_window = time_result.window
                logger.info(f"✅ [SQLCoordinator] 时间窗口: {time_result.window}")
            else:
                logger.warning("⚠️ [SQLCoordinator] 时间窗口解决失败")
                return SQLReadiness.MISSING_TIME

        # 2. 解决Schema依赖
        if not deps.schema:
            logger.info("🔍 [SQLCoordinator] 解决Schema依赖")
            tables_hint = (
                context_snapshot.get("selected_tables")
                or context_snapshot.get("tables")
                or context_snapshot.get("column_details", {}).keys()
            )

            schema_result = await self.schema_resolver.resolve(
                context=context_snapshot,
                tables_hint=tables_hint,
            )

            if schema_result.success:
                sql_context.schema = schema_result.schema
                logger.info(f"✅ [SQLCoordinator] Schema: {len(schema_result.schema)}个表")
            else:
                logger.error(f"❌ [SQLCoordinator] Schema解决失败: {schema_result.error}")
                return SQLReadiness.MISSING_SCHEMA

        return SQLReadiness.READY

    def _build_sql_context(
        self,
        query: str,
        context_snapshot: Dict[str, Any],
    ) -> SQLContext:
        """构建SQL上下文"""
        sql_context = SQLContext(query=query)

        # 尝试从snapshot中提取已有的依赖
        if context_snapshot.get("time_context") or context_snapshot.get("window"):
            window = context_snapshot.get("window") or context_snapshot.get("time_context")
            if window:
                sql_context.time_window = window

        if context_snapshot.get("column_details") or context_snapshot.get("columns"):
            schema = context_snapshot.get("column_details") or context_snapshot.get("columns")
            if schema:
                sql_context.schema = schema

        return sql_context

    def _build_generation_prompt(
        self,
        sql_context: SQLContext,
        attempt: int,
    ) -> str:
        """
        构建SQL生成prompt

        策略：
        - 首次尝试：精简prompt，避免过度指导
        - 重试时：加入失败信息和调整策略
        """
        schema_desc = self._format_schema(sql_context.schema)
        time_desc = self._format_time_window(sql_context.time_window)

        base_prompt = f"""
# 任务：生成MySQL查询SQL

## 用户需求
{sql_context.query}

## 时间范围
{time_desc}

## 数据库Schema
{schema_desc}

## 输出要求
严格按照以下JSON格式返回：
{{
  "sql": "完整的SELECT语句（使用{{{{start_date}}}}, {{{{end_date}}}}占位符）",
  "explanation": "SQL逻辑说明",
  "tables_used": ["table1", "table2"],
  "confidence": 0.9
}}

## 规则
1. SQL必须使用Schema中存在的表和字段
2. 时间过滤使用{{{{start_date}}}}和{{{{end_date}}}}占位符
3. 避免复杂子查询，优先JOIN
4. 确保SQL可执行（SELECT...FROM...WHERE结构完整）
"""

        if attempt > 0 and sql_context.previous_attempts:
            last_attempt = sql_context.previous_attempts[-1]
            base_prompt += f"""

## 前次失败原因
{last_attempt.get('error') or last_attempt.get('validation_issues')}

## 调整策略
- 简化查询逻辑
- 确保字段名和表名准确匹配
- 检查括号和引号
"""

        return base_prompt

    def _format_schema(self, schema: Optional[Dict[str, Any]]) -> str:
        """格式化Schema为可读文本"""
        if not schema:
            return "（无Schema信息）"

        lines = []
        for table, columns in (schema or {}).items():
            if isinstance(columns, list):
                lines.append(f"**{table}**: {', '.join(columns[:15])}")
            elif isinstance(columns, dict):
                col_names = list(columns.keys())[:15]
                lines.append(f"**{table}**: {', '.join(col_names)}")

        return "\n".join(lines) if lines else "（无Schema信息）"

    def _format_time_window(self, time_window: Optional[Dict[str, Any]]) -> str:
        """格式化时间窗口"""
        if not time_window:
            return "使用{{start_date}}和{{end_date}}占位符"

        start = time_window.get("start_date") or time_window.get("start")
        end = time_window.get("end_date") or time_window.get("end")

        if start and end:
            return f"从 {start} 到 {end} （使用{{{{start_date}}}}, {{{{end_date}}}}占位符）"

        return "使用{{start_date}}和{{end_date}}占位符"

    async def _apply_intelligent_fixes(
        self,
        sql: str,
        issues: list[str],
        context: SQLContext,
    ) -> Optional[str]:
        """
        智能修复SQL

        策略：
        - 表名/字段名纠正（基于Schema）
        - 括号修复
        - DATE_SUB函数格式修复
        """
        try:
            fixed_sql = sql

            # 简单的表名替换（从issues中提取）
            for issue in issues:
                if "表名不存在" in issue and "→" in issue:
                    parts = issue.split("→")
                    if len(parts) == 2:
                        wrong_table = parts[0].split(":")[-1].strip()
                        correct_table = parts[1].replace("已替换为", "").strip()
                        import re

                        pattern = rf"\b{re.escape(wrong_table)}\b"
                        fixed_sql = re.sub(pattern, correct_table, fixed_sql)
                        logger.info(f"🔧 [SQLCoordinator] 修复表名: {wrong_table} → {correct_table}")

            # 括号修复
            if any("括号" in issue for issue in issues):
                open_count = fixed_sql.count("(")
                close_count = fixed_sql.count(")")
                if open_count > close_count:
                    fixed_sql += ")" * (open_count - close_count)
                    logger.info(f"🔧 [SQLCoordinator] 添加{open_count - close_count}个右括号")

            return fixed_sql if fixed_sql != sql else None

        except Exception as exc:
            logger.error(f"❌ [SQLCoordinator] 智能修复失败: {exc}")
            return None

    def _build_error_summary(self, sql_context: SQLContext) -> Dict[str, Any]:
        """构建详细的错误摘要"""
        reasons = []
        suggestions = []

        # 分析失败原因
        for attempt in sql_context.previous_attempts:
            if attempt.get("error"):
                reasons.append(f"尝试{attempt['attempt']}: {attempt['error']}")
            elif attempt.get("validation_issues"):
                issues = attempt["validation_issues"]
                reasons.append(f"尝试{attempt['attempt']}: 验证失败 - {'; '.join(issues[:2])}")

        # 生成建议
        if any("schema" in str(r).lower() for r in reasons):
            suggestions.append("检查数据库Schema是否正确加载")
            suggestions.append("确认表名和字段名是否存在")

        if any("syntax" in str(r).lower() or "括号" in str(r) for r in reasons):
            suggestions.append("SQL语法存在问题，可能需要调整LLM prompt")

        if any("json" in str(r).lower() for r in reasons):
            suggestions.append("LLM未能返回有效JSON，可能需要调整temperature参数")

        if not suggestions:
            suggestions.append("请检查用户需求是否明确")
            suggestions.append("尝试简化查询需求")

        message = f"SQL生成失败（{len(sql_context.previous_attempts)}次尝试）"
        if reasons:
            message += f": {reasons[-1]}"  # 显示最后一次失败原因

        return {
            "message": message,
            "reasons": reasons,
            "suggestions": suggestions,
        }

    def _handle_dependency_missing(
        self,
        sql_context: SQLContext,
        readiness: SQLReadiness,
    ) -> SQLGenerationResult:
        """处理依赖缺失"""
        if readiness == SQLReadiness.MISSING_TIME:
            return SQLGenerationResult.user_input_required(
                message="无法推断时间范围，请明确指定start_date和end_date",
                suggestions=["例如：统计2024-01-01到2024-01-31的数据"],
            )

        if readiness == SQLReadiness.MISSING_SCHEMA:
            return SQLGenerationResult.failed_result(
                error="无法获取数据库Schema信息",
                metadata={"hint": "请检查数据源配置和连接"},
            )

        return SQLGenerationResult.failed_result(
            error=f"未知的依赖问题: {readiness}",
        )
