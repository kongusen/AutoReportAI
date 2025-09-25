"""
统一上下文协调器

整合三大核心构建器，为Agent系统提供完整、统一的上下文信息：
- 数据源上下文：表结构、字段特征、业务域分析
- 模板上下文：占位符语境、段落匹配、类型分析
- 任务上下文：时间范围推导、业务规则、执行参数

设计目标：
1. 为Agent提供一站式上下文服务
2. 智能缓存和并发获取上下文信息
3. 统一的错误处理和降级策略
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from .data_source_context_server import DataSourceContextBuilder
from .template_context_service import TemplateContextBuilder
from .task_context_service import TaskDrivenContextBuilder

logger = logging.getLogger(__name__)


@dataclass
class Context:
    """统一的上下文信息"""

    # 核心上下文组件
    data_source_context: Optional[Dict[str, Any]] = None
    template_context: Optional[Dict[str, Any]] = None
    task_context: Optional[Dict[str, Any]] = None

    # 元信息
    context_id: str = ""
    build_time: Optional[datetime] = None
    success: bool = False
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.build_time is None:
            self.build_time = datetime.now()

    def to_agent_format(self) -> Dict[str, Any]:
        """转换为Agent友好的完整上下文格式"""
        agent_context = {
            "context_id": self.context_id,
            "build_time": self.build_time.isoformat() if self.build_time else None,
            "success": self.success,
            "components": {}
        }

        # 数据源上下文
        if self.data_source_context:
            agent_context["components"]["data_source"] = self.data_source_context

        # 模板上下文
        if self.template_context:
            agent_context["components"]["template"] = self.template_context

        # 任务上下文
        if self.task_context:
            agent_context["components"]["task"] = self.task_context

        # 错误和警告
        if self.errors:
            agent_context["errors"] = self.errors
        if self.warnings:
            agent_context["warnings"] = self.warnings

        return agent_context

    def get_consolidated_context(self) -> Dict[str, Any]:
        """获取合并后的上下文信息，适用于Agent直接使用"""
        consolidated = {
            "context_meta": {
                "id": self.context_id,
                "build_time": self.build_time.isoformat() if self.build_time else None,
                "success": self.success
            }
        }

        # 合并数据源信息
        if self.data_source_context:
            consolidated.update({
                "database_context": self.data_source_context,
                "available_tables": self.data_source_context.get("tables", []),
                "schema_analysis": self.data_source_context.get("statistics", {})
            })

        # 合并模板信息
        if self.template_context:
            consolidated.update({
                "template_info": self.template_context.get("template_info", {}),
                "placeholder_contexts": self.template_context.get("placeholder_contexts", []),
                "template_summary": self.template_context.get("summary", {})
            })

        # 合并任务信息
        if self.task_context:
            consolidated.update({
                "user_id": self.task_context.get("user_id"),
                "data_source": self.task_context.get("data_source"),
                "task_info": self.task_context.get("task_id"),
                "current_placeholder": self.task_context.get("current_placeholder"),
                "time_context": self.task_context.get("time_context", {}),
                "sql_parameters": self.task_context.get("sql_parameters", {}),
                "business_rules": self.task_context.get("business_rules", []),
                "progress": self.task_context.get("progress", {})
            })

        return consolidated


class ContextCoordinator:
    """统一上下文协调器"""

    def __init__(self, container=None):
        self.container = container

        # 初始化三大构建器
        self.data_source_builder = DataSourceContextBuilder()
        self.template_builder = TemplateContextBuilder(container)
        self.task_builder = TaskDrivenContextBuilder(container)

        # 缓存机制（简单实现）
        self._context_cache: Dict[str, Context] = {}

    async def build_full_context(
        self,
        user_id: str,
        template_id: str,
        data_source_id: str,
        task_definition: Dict[str, Any],
        force_refresh: bool = False
    ) -> Context:
        """
        构建完整的统一上下文

        Args:
            user_id: 用户ID
            template_id: 模板ID
            data_source_id: 数据源ID
            task_definition: 任务定义
            force_refresh: 是否强制刷新缓存

        Returns:
            完整的统一上下文对象
        """
        context_id = f"{user_id}_{template_id}_{data_source_id}_{hash(str(task_definition))}"

        # 检查缓存
        if not force_refresh and context_id in self._context_cache:
            cached_context = self._context_cache[context_id]
            # 简单的缓存过期检查（5分钟）
            if cached_context.build_time and \
               (datetime.now() - cached_context.build_time).seconds < 300:
                logger.info(f"返回缓存的上下文: {context_id}")
                return cached_context

        logger.info(f"构建新的统一上下文: {context_id}")

        # 创建统一上下文对象
        context = Context(
            context_id=context_id,
            build_time=datetime.now()
        )

        # 并发获取三个上下文组件
        try:
            # 使用asyncio.gather并发执行
            results = await asyncio.gather(
                self._build_data_source_context(user_id, data_source_id),
                self._build_template_context(user_id, template_id),
                self._build_task_context(user_id, template_id, data_source_id, task_definition),
                return_exceptions=True
            )

            # 处理数据源上下文结果
            if isinstance(results[0], Exception):
                context.errors.append(f"数据源上下文构建失败: {results[0]}")
                logger.error(f"数据源上下文构建失败: {results[0]}")
            else:
                ds_result = results[0]
                # 仅当真实数据可用时写入上下文
                if isinstance(ds_result, dict) and ds_result.get("success") is False:
                    err = ds_result.get("error", "unknown_error")
                    context.errors.append(f"数据源上下文不可用: {err}")
                else:
                    context.data_source_context = ds_result

            # 处理模板上下文结果
            if isinstance(results[1], Exception):
                context.errors.append(f"模板上下文构建失败: {results[1]}")
                logger.error(f"模板上下文构建失败: {results[1]}")
            else:
                template_result = results[1]
                if template_result and template_result.get("success"):
                    context.template_context = template_result.get("template_context")
                else:
                    reason = template_result.get("error") if isinstance(template_result, dict) else "unknown"
                    context.warnings.append(f"模板上下文不可用或不完整: {reason}")

            # 处理任务上下文结果
            if isinstance(results[2], Exception):
                context.errors.append(f"任务上下文构建失败: {results[2]}")
                logger.error(f"任务上下文构建失败: {results[2]}")
            else:
                context.task_context = results[2].to_react_context() if results[2] else None

            # 判断整体成功状态
            context.success = (
                context.data_source_context is not None or
                context.template_context is not None or
                context.task_context is not None
            ) and len(context.errors) == 0

            # 缓存结果
            self._context_cache[context_id] = context

            return context

        except Exception as e:
            logger.error(f"统一上下文构建过程出现异常: {e}")
            context.errors.append(f"构建过程异常: {str(e)}")
            context.success = False
            return context

    async def _build_data_source_context(self, user_id: str, data_source_id: str) -> Optional[Dict[str, Any]]:
        """构建数据源上下文"""
        try:
            # 使用真实数据源服务构建上下文（无mock）
            ds_context = await self.data_source_builder.build_data_source_context(
                user_id=user_id,
                data_source_id=data_source_id,
                required_tables=None,
                force_refresh=False
            )
            return ds_context
        except Exception as e:
            logger.warning(f"数据源上下文构建失败: {e}")
            raise

    async def _build_template_context(
        self,
        user_id: str,
        template_id: str
    ) -> Optional[Dict[str, Any]]:
        """构建模板上下文"""
        try:
            return await self.template_builder.build_template_context(
                user_id=user_id,
                template_id=template_id
            )
        except Exception as e:
            logger.warning(f"模板上下文构建失败: {e}")
            raise

    async def _build_task_context(
        self,
        user_id: str,
        template_id: str,
        data_source_id: str,
        task_definition: Dict[str, Any]
    ) -> Optional[Any]:  # TaskDrivenContext
        """构建任务上下文"""
        try:
            return await self.task_builder.build_task_driven_context(
                user_id=user_id,
                template_id=template_id,
                data_source_id=data_source_id,
                task_definition=task_definition
            )
        except Exception as e:
            logger.warning(f"任务上下文构建失败: {e}")
            raise

    async def get_placeholder_context(
        self,
        user_id: str,
        template_id: str,
        data_source_id: str,
        placeholder_name: str,
        task_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        为特定占位符获取完整上下文

        Args:
            user_id: 用户ID
            template_id: 模板ID
            data_source_id: 数据源ID
            placeholder_name: 占位符名称
            task_config: 任务配置

        Returns:
            包含占位符完整上下文的字典
        """
        try:
            # 构建占位符特定的任务定义
            task_definition = {
                "task_id": f"placeholder_{placeholder_name}_{datetime.now().timestamp()}",
                "task_type": "custom_period",
                "placeholder_index": 0,  # 将根据placeholder_name调整
                "execution_context": {"placeholder_name": placeholder_name},
                "user_task_config": task_config or {}
            }

            # 构建完整上下文
            context = await self.build_full_context(
                user_id=user_id,
                template_id=template_id,
                data_source_id=data_source_id,
                task_definition=task_definition
            )

            if context.success:
                # 获取合并后的上下文，专门针对该占位符
                consolidated_context = context.get_consolidated_context()

                # 添加占位符特定信息
                consolidated_context["placeholder_focus"] = {
                    "name": placeholder_name,
                    "context_ready": True,
                    "data_source_ready": context.data_source_context is not None,
                    "template_ready": context.template_context is not None,
                    "task_ready": context.task_context is not None
                }

                return {
                    "success": True,
                    "placeholder_name": placeholder_name,
                    "context": consolidated_context,
                    "context_id": context.context_id
                }
            else:
                return {
                    "success": False,
                    "placeholder_name": placeholder_name,
                    "errors": context.errors,
                    "warnings": context.warnings
                }

        except Exception as e:
            logger.error(f"为占位符 {placeholder_name} 构建上下文失败: {e}")
            return {
                "success": False,
                "placeholder_name": placeholder_name,
                "error": f"上下文构建失败: {str(e)}"
            }

    def clear_cache(self):
        """清空上下文缓存"""
        self._context_cache.clear()
        logger.info("上下文缓存已清空")

    def get_cache_status(self) -> Dict[str, Any]:
        """获取缓存状态"""
        return {
            "cache_size": len(self._context_cache),
            "cached_contexts": list(self._context_cache.keys())
        }

    # === 上下文 -> AgentInput 桥接器（委托 agent_input.builder） ===
    def build_agent_input(
        self,
        context: Context,
        placeholder_name: str,
        *,
        output_kind: str = "sql",
        sql_only: bool = True,
        user_id: str = "system"
    ) -> Dict[str, Any]:
        from app.services.application.agent_input import AgentInputBuilder
        return AgentInputBuilder(self.container).build(
            context,
            placeholder_name=placeholder_name,
            output_kind=output_kind,
            sql_only=sql_only,
            user_id=user_id,
        )

    def _extract_schema(self, db_ctx: Dict[str, Any]):
        """从数据库上下文提取 tables/columns 及摘要。"""
        tables = []
        columns: Dict[str, List[str]] = {}
        meta = {"tables": 0, "columns": 0, "samples": []}

        tbls = db_ctx.get("tables") or []
        for t in tbls:
            name = t.get("table_name")
            if not name:
                continue
            tables.append(name)
            cols = [c.get("name") for c in (t.get("columns") or []) if c.get("name")]
            columns[name] = cols
            meta["samples"].append({"table": name, "columns_preview": cols[:5]})

        meta["tables"] = len(tables)
        meta["columns"] = sum(len(v) for v in columns.values())
        return tables, columns, meta

    def _derive_placeholder_spec(self, consolidated: Dict[str, Any], placeholder_name: str) -> (Dict[str, Any], Dict[str, Any]):
        """从模板上下文推导占位符规范（类型/说明）。"""
        tpl_ctx = consolidated.get("placeholder_contexts") or []
        ph = None
        for item in tpl_ctx:
            if item.get("placeholder_name") == placeholder_name:
                ph = item
                break

        # 类型映射：中文 → agents占位符类型
        type_map = {"统计类": "stat", "图表类": "chart", "周期类": "stat"}
        ph_type = type_map.get((ph or {}).get("type"), "stat")
        desc = (ph or {}).get("context_paragraph") or f"占位符 {placeholder_name}"

        spec = {
            "id": placeholder_name,
            "description": desc,
            "type": ph_type,
            "granularity": "daily"
        }
        meta = {
            "name": placeholder_name,
            "type_cn": (ph or {}).get("type"),
            "type": ph_type,
            "position": (ph or {}).get("position_info"),
        }
        return spec, meta

    def _compose_dynamic_user_prompt(
        self,
        consolidated: Dict[str, Any],
        placeholder_name: str,
        output_kind: str,
        ph_meta: Dict[str, Any]
    ) -> str:
        """结合占位符语境、任务时间、业务规则与schema摘要拼装动态提示词。"""
        template_info = consolidated.get("template_info", {})
        time_ctx = consolidated.get("time_context", {})
        rules = consolidated.get("business_rules", [])

        # schema简述
        db_ctx = consolidated.get("database_context") or {}
        tables = [t.get("table_name") for t in (db_ctx.get("tables") or []) if t.get("table_name")]
        tables_str = ", ".join(tables[:5]) + ("..." if len(tables) > 5 else "") if tables else "无"

        goal = f"为占位符《{placeholder_name}》生成{('SQL' if output_kind=='sql' else '所需结果')}"
        if output_kind == "chart":
            goal = f"为占位符《{placeholder_name}》生成图表所需的数据SQL与图表配置"
        elif output_kind == "report":
            goal = f"为占位符《{placeholder_name}》生成报告段落所需的数据与文本"

        time_hint = time_ctx.get("agent_instructions") or ""
        rules_hint = ("\n- ".join(rules)) if rules else ""

        lines = [
            f"任务: {goal}",
            f"模板: {template_info.get('name') or template_info.get('id') or ''}",
            f"语境: {ph_meta.get('type_cn') or ph_meta.get('type') or ''}",
            f"可用表: {tables_str}",
        ]
        if time_hint:
            lines.append(f"时间指令: {time_hint.strip()}")
        if rules_hint:
            lines.append(f"业务规则:\n- {rules_hint}")

        return "\n".join([l for l in lines if l])
