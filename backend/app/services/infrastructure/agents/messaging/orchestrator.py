"""任务消息编排器 - 动态生成所有消息"""
from typing import Optional, Dict, Any
from .config import PromptConfigManager

class TaskMessageOrchestrator:
    """消息编排器"""

    def __init__(self):
        self.config = PromptConfigManager()

    # ===== 任务生命周期 =====
    def task_started(self) -> str:
        return self.config.get_message("task_started")

    def task_completed(self, duration: float) -> str:
        return self.config.get_message("task_completed", duration=duration)

    def task_cancelled(self) -> str:
        return self.config.get_message("task_cancelled")

    def task_failed(self, reason: str) -> str:
        return self.config.get_message("task_failed", reason=reason)

    # ===== 初始化阶段 =====
    def init_completed(self) -> str:
        return self.config.get_message("init_completed")

    def init_progress(self) -> str:
        return self.config.get_message("init_progress")

    # ===== Schema 初始化 =====
    def schema_init_log(self, data_source_id: str) -> str:
        return self.config.get_message("schema_init_log", data_source_id=data_source_id)

    def schema_init_started(self, top_k: Optional[int] = None) -> str:
        top_k = top_k or self.config.get_constant("schema_context_top_k", 10)
        return self.config.get_message("schema_init_started", top_k=top_k)

    def schema_init_completed(self, table_count: int) -> str:
        return self.config.get_message("schema_init_completed", table_count=table_count)

    def schema_init_progress(self, table_count: int) -> str:
        return self.config.get_message("schema_init_progress", table_count=table_count)

    def schema_init_failed(self, error: Exception) -> str:
        return self.config.get_message("schema_init_failed", error=str(error))

    def schema_init_fallback(self) -> str:
        return self.config.get_message("schema_init_fallback")

    # ===== 占位符检查 =====
    def placeholder_status_check(self) -> str:
        return self.config.get_message("placeholder_status_check")

    def placeholder_status_summary(self, total_content: int, total_existing: int) -> str:
        return self.config.get_message("placeholder_status_summary",
                                       total_content=total_content,
                                       total_existing=total_existing)

    # ===== 占位符创建 =====
    def placeholders_found(self, count: int) -> str:
        return self.config.get_message("placeholders_found", count=count)

    def placeholders_creating(self, count: int) -> str:
        return self.config.get_message("placeholders_creating", count=count)

    def placeholders_creating_log(self, count: int) -> str:
        return self.config.get_message("placeholders_creating_log", count=count)

    # ===== 占位符分析 =====
    def placeholder_needs_analysis(self, need_analysis: int, total: int) -> str:
        return self.config.get_message("placeholder_needs_analysis",
                                       need_analysis=need_analysis,
                                       total=total)

    def placeholder_all_ready(self, count: int) -> str:
        return self.config.get_message("placeholder_all_ready", count=count)

    def placeholder_no_placeholders(self) -> str:
        return self.config.get_message("placeholder_no_placeholders")

    def placeholder_analysis_start(self, count: int) -> str:
        return self.config.get_message("placeholder_analysis_start", count=count)

    def placeholder_analysis_progress(self, name: str, current: int, total: int) -> str:
        return self.config.get_message("placeholder_analysis_progress",
                                       name=name,
                                       current=current,
                                       total=total)

    def placeholder_analysis_celery(self, name: str) -> str:
        return self.config.get_message("placeholder_analysis_celery", name=name)

    # ===== SQL 生成 =====
    def sql_generation_success(self, name: str, auto_fix_info: str = "", validation_status: str = "") -> str:
        return self.config.get_message("sql_generation_success",
                                       name=name,
                                       auto_fix_info=auto_fix_info,
                                       validation_status=validation_status)

    def sql_generation_success_batch(self, name: str, batch_current: int, batch_size: int,
                                     auto_fix_info: str = "", validation_status: str = "") -> str:
        return self.config.get_message("sql_generation_success_batch",
                                       name=name,
                                       batch_current=batch_current,
                                       batch_size=batch_size,
                                       auto_fix_info=auto_fix_info,
                                       validation_status=validation_status)

    def sql_generation_batch_commit(self, count: int) -> str:
        return self.config.get_message("sql_generation_batch_commit", count=count)

    def sql_generation_failed(self, name: str, error: str) -> str:
        return self.config.get_message("sql_generation_failed", name=name, error=error)

    def sql_generation_failed_progress(self, name: str) -> str:
        return self.config.get_message("sql_generation_failed_progress", name=name)

    def sql_rejected_chinese(self, name: str, sql_preview: str) -> str:
        return self.config.get_message("sql_rejected_chinese", name=name, sql_preview=sql_preview)

    # ===== 占位符处理异常 =====
    def placeholder_exception(self, name: str, error: str) -> str:
        return self.config.get_message("placeholder_exception", name=name, error=error)

    def placeholder_exception_progress(self, name: str) -> str:
        return self.config.get_message("placeholder_exception_progress", name=name)

    # ===== ETL 处理 =====
    def etl_start(self) -> str:
        return self.config.get_message("etl_start")

    def etl_progress(self) -> str:
        return self.config.get_message("etl_progress")

    def etl_completed(self) -> str:
        return self.config.get_message("etl_completed")

    # ===== 报告生成 =====
    def report_generation_start(self) -> str:
        return self.config.get_message("report_generation_start")

    def report_generation_progress(self) -> str:
        return self.config.get_message("report_generation_progress")

    def report_generation_failed(self, error: str) -> str:
        return self.config.get_message("report_generation_failed", error=error)

    def report_generation_success(self) -> str:
        return self.config.get_message("report_generation_success")
