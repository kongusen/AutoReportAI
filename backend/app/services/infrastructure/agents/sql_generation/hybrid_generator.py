"""
混合SQL生成器 - 结合SQL-First快速生成和PTAV灵活回退

策略：
1. Context完整 → SQL-First快速生成（1-2轮）
2. SQL-First失败 → PTAV循环回退（灵活应对）
3. Context不完整 → 直接PTAV（逐步补全依赖）

优势：兼具效率和灵活性
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .coordinator import SQLGenerationCoordinator, SQLGenerationConfig
from .context import SQLGenerationResult

logger = logging.getLogger(__name__)


class HybridSQLGenerator:
    """
    混合SQL生成器 - 智能选择生成策略

    根据Context完整性自动选择：
    - SQL-First: 快速、高效（Context完整时）
    - PTAV: 灵活、兜底（Context不完整或SQL-First失败时）
    """

    def __init__(self, container, llm_client, db_connector):
        self.container = container
        self.llm = llm_client
        self.db = db_connector

        # 初始化SQL-First协调器
        self.coordinator = SQLGenerationCoordinator(
            container=container,
            llm_client=llm_client,
            db_connector=db_connector,
            config=SQLGenerationConfig(
                max_generation_attempts=3,
                max_fix_attempts=2,
                enable_dry_run_validation=True,
            ),
        )

    async def generate(
        self,
        query: str,
        context_snapshot: Dict[str, Any],
        *,
        allow_ptav_fallback: bool = True,
    ) -> SQLGenerationResult:
        """
        智能SQL生成 - 自动选择最佳策略

        Args:
            query: 用户查询文本
            context_snapshot: 执行上下文快照
            allow_ptav_fallback: 是否允许PTAV回退（默认True）

        Returns:
            SQLGenerationResult: 生成结果
        """
        logger.info(f"🎯 [HybridGenerator] 开始智能SQL生成: {query[:100]}")

        # ===== Phase 1: Context完整性检查 =====
        completeness = self._check_context_completeness(context_snapshot)
        logger.info(
            f"📋 [HybridGenerator] Context完整性: "
            f"时间={completeness['has_time']}, "
            f"Schema={completeness['has_schema']}, "
            f"数据源={completeness['has_datasource']}"
        )

        # ===== Phase 2: 策略选择 =====
        if completeness["is_complete"]:
            logger.info("✅ [HybridGenerator] Context完整，使用SQL-First策略")

            # 尝试SQL-First快速生成
            try:
                result = await self.coordinator.generate(query, context_snapshot)

                if result.success:
                    logger.info("🚀 [HybridGenerator] SQL-First生成成功")
                    # 标记生成方法
                    result.metadata["generation_strategy"] = "sql_first"
                    return result

                # SQL-First失败但有明确错误
                logger.warning(f"⚠️ [HybridGenerator] SQL-First生成失败: {result.error}")

                if allow_ptav_fallback:
                    logger.info("🔄 [HybridGenerator] 启动PTAV回退")
                    return await self._ptav_fallback(
                        query=query,
                        context_snapshot=context_snapshot,
                        reason="sql_first_failed",
                        sql_first_error=result.error,
                    )
                else:
                    # 不允许回退，直接返回失败
                    result.metadata["generation_strategy"] = "sql_first_no_fallback"
                    return result

            except Exception as exc:
                logger.error(f"❌ [HybridGenerator] SQL-First异常: {exc}", exc_info=True)

                if allow_ptav_fallback:
                    logger.info("🔄 [HybridGenerator] SQL-First异常，启动PTAV回退")
                    return await self._ptav_fallback(
                        query=query,
                        context_snapshot=context_snapshot,
                        reason="sql_first_exception",
                        sql_first_error=str(exc),
                    )
                else:
                    return SQLGenerationResult.failed_result(
                        error=f"sql_first_exception: {exc}",
                        metadata={"generation_strategy": "sql_first_no_fallback"},
                    )

        else:
            # Context不完整
            missing = completeness["missing_fields"]
            logger.info(f"⚠️ [HybridGenerator] Context不完整（缺少: {', '.join(missing)}），直接使用PTAV")

            if allow_ptav_fallback:
                return await self._ptav_fallback(
                    query=query,
                    context_snapshot=context_snapshot,
                    reason="context_incomplete",
                    missing_fields=missing,
                )
            else:
                return SQLGenerationResult.failed_result(
                    error=f"context_incomplete: missing {', '.join(missing)}",
                    metadata={"missing_fields": missing, "generation_strategy": "none"},
                )

    def _check_context_completeness(self, context_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查Context完整性

        必需字段：
        1. 时间信息（time_window/window/time_context）
        2. Schema信息（column_details/columns/schema_context）
        3. 数据源配置（data_source）
        4. 数据源ID（data_source.id）
        """
        # 检查时间信息
        has_time = bool(
            context_snapshot.get("time_window")
            or context_snapshot.get("window")
            or context_snapshot.get("time_context")
            or (context_snapshot.get("task_driven_context", {}) or {}).get("time_window")
        )

        # 检查Schema信息
        has_schema = bool(
            context_snapshot.get("column_details")
            or context_snapshot.get("columns")
            or (context_snapshot.get("schema_context", {}) or {}).get("columns")
            or (context_snapshot.get("task_driven_context", {}) or {}).get("schema_context", {}).get("columns")
        )

        # 检查数据源配置
        data_source = context_snapshot.get("data_source")
        has_datasource = bool(data_source and isinstance(data_source, dict))

        # 检查数据源ID
        has_datasource_id = False
        if has_datasource:
            has_datasource_id = bool(data_source.get("id") or data_source.get("data_source_id"))

        # 汇总结果
        missing_fields = []
        if not has_time:
            missing_fields.append("time")
        if not has_schema:
            missing_fields.append("schema")
        if not has_datasource:
            missing_fields.append("data_source")
        elif not has_datasource_id:
            missing_fields.append("data_source.id")

        is_complete = len(missing_fields) == 0

        return {
            "is_complete": is_complete,
            "has_time": has_time,
            "has_schema": has_schema,
            "has_datasource": has_datasource,
            "has_datasource_id": has_datasource_id,
            "missing_fields": missing_fields,
        }

    async def _ptav_fallback(
        self,
        query: str,
        context_snapshot: Dict[str, Any],
        reason: str,
        **metadata,
    ) -> SQLGenerationResult:
        """
        PTAV回退模式 - 使用原有的灵活循环生成

        Args:
            query: 用户查询
            context_snapshot: 上下文快照
            reason: 回退原因
            **metadata: 额外的元数据（如sql_first_error）

        Returns:
            SQLGenerationResult: PTAV生成结果
        """
        logger.info(f"🔄 [HybridGenerator PTAV] 回退原因: {reason}")

        try:
            # 构建AgentInput（复用单占位符分析的成功模式）
            from ..types import AgentInput, TaskContext

            # 从context_snapshot提取信息
            task_driven_context = context_snapshot.get("task_driven_context", {})

            agent_input = AgentInput(
                user_prompt=f"SQL生成: {query}",
                context=TaskContext(task_time=0, timezone="Asia/Shanghai"),
                data_source=context_snapshot.get("data_source"),
                task_driven_context={
                    **task_driven_context,
                    "query": query,
                    "fallback_reason": reason,
                    "generation_mode": "ptav_fallback",
                },
                user_id=context_snapshot.get("user_id", "system"),
            )

            # 调用Orchestrator的PTAV循环
            from ..orchestrator import UnifiedOrchestrator

            orchestrator = UnifiedOrchestrator(self.container)
            ptav_result = await orchestrator.execute(agent_input, mode="ptav")

            # 转换AgentOutput为SQLGenerationResult
            if ptav_result.success:
                logger.info("✅ [HybridGenerator PTAV] PTAV生成成功")
                return SQLGenerationResult.success_result(
                    sql=ptav_result.content,
                    metadata={
                        "generation_strategy": "ptav_fallback",
                        "fallback_reason": reason,
                        "ptav_metadata": ptav_result.metadata,
                        **metadata,
                    },
                )
            else:
                logger.error(f"❌ [HybridGenerator PTAV] PTAV生成失败: {ptav_result.metadata}")
                return SQLGenerationResult.failed_result(
                    error="ptav_fallback_failed",
                    metadata={
                        "generation_strategy": "ptav_fallback",
                        "fallback_reason": reason,
                        "ptav_error": ptav_result.metadata,
                        **metadata,
                    },
                )

        except Exception as exc:
            logger.error(f"❌ [HybridGenerator PTAV] PTAV异常: {exc}", exc_info=True)
            return SQLGenerationResult.failed_result(
                error=f"ptav_exception: {exc}",
                metadata={
                    "generation_strategy": "ptav_fallback",
                    "fallback_reason": reason,
                    **metadata,
                },
            )


# ===== 便捷的集成函数 =====


async def generate_sql_with_hybrid_strategy(
    query: str,
    context_snapshot: Dict[str, Any],
    container,
    llm_client,
    db_connector,
) -> SQLGenerationResult:
    """
    便捷函数：使用混合策略生成SQL

    Example:
        result = await generate_sql_with_hybrid_strategy(
            query="统计昨日销售额",
            context_snapshot={
                "time_window": {...},
                "column_details": {...},
                "data_source": {...}
            },
            container=container,
            llm_client=llm,
            db_connector=db
        )
    """
    generator = HybridSQLGenerator(container, llm_client, db_connector)
    return await generator.generate(query, context_snapshot)
