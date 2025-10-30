"""集中管理所有提示词和消息配置"""
from typing import Dict, Any
from dataclasses import dataclass, field

@dataclass
class MessageTemplate:
    """消息模板"""
    template: str
    variables: list = field(default_factory=list)
    
    def format(self, **kwargs) -> str:
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            return f"[Template error: {e}]"

class PromptConfigManager:
    """配置管理器"""
    
    MESSAGES = {
        # 任务生命周期
        "task_started": MessageTemplate("任务开始执行"),
        "task_completed": MessageTemplate("任务完成 - 用时 {duration:.1f}秒"),
        "task_cancelled": MessageTemplate("任务已被用户取消"),
        "task_failed": MessageTemplate("任务执行失败: {reason}"),

        # 初始化阶段
        "init_completed": MessageTemplate("任务初始化完成"),
        "init_progress": MessageTemplate("任务初始化中..."),

        # Schema 初始化
        "schema_init_log": MessageTemplate("📋 初始化 Schema Context for data_source={data_source_id}"),
        "schema_init_started": MessageTemplate("正在初始化数据表结构上下文（Top-{top_k}）..."),
        "schema_init_completed": MessageTemplate("✅ Schema Context 初始化完成，缓存了 {table_count} 个表"),
        "schema_init_progress": MessageTemplate("数据表结构缓存完成（{table_count} 个表）"),
        "schema_init_failed": MessageTemplate("⚠️ Schema Context 初始化失败: {error}"),
        "schema_init_fallback": MessageTemplate("💡 将在没有 Schema Context 的情况下继续执行..."),

        # 占位符检查
        "placeholder_status_check": MessageTemplate("正在检查占位符状态..."),
        "placeholder_status_summary": MessageTemplate("模板内容中发现 {total_content} 个占位符，数据库中已有 {total_existing} 个占位符记录"),

        # 占位符创建
        "placeholders_found": MessageTemplate("发现 {count} 个新占位符"),
        "placeholders_creating": MessageTemplate("发现 {count} 个新占位符，正在创建记录..."),
        "placeholders_creating_log": MessageTemplate("Creating {count} new placeholder records"),

        # 占位符分析
        "placeholder_needs_analysis": MessageTemplate("需要分析 {need_analysis} 个占位符（共 {total} 个）..."),
        "placeholder_all_ready": MessageTemplate("所有 {count} 个占位符已就绪，跳过分析阶段..."),
        "placeholder_no_placeholders": MessageTemplate("模板无占位符，跳过分析阶段..."),
        "placeholder_analysis_start": MessageTemplate("正在逐个分析 {count} 个占位符..."),
        "placeholder_analysis_progress": MessageTemplate("正在分析占位符: {name} ({current}/{total})"),
        "placeholder_analysis_celery": MessageTemplate("🔄 使用 Celery 任务分析占位符: {name}"),

        # SQL 生成
        "sql_generation_success": MessageTemplate("✅ 占位符 {name} SQL生成成功{auto_fix_info} {validation_status}"),
        "sql_generation_success_batch": MessageTemplate("✅ 占位符 {name} SQL生成成功{auto_fix_info} {validation_status} (批次: {batch_current}/{batch_size})"),
        "sql_generation_batch_commit": MessageTemplate("📦 批量提交 {count} 个占位符到数据库"),
        "sql_generation_failed": MessageTemplate("❌ 占位符 {name} SQL生成失败: {error}"),
        "sql_generation_failed_progress": MessageTemplate("占位符 {name} SQL生成失败"),
        "sql_rejected_chinese": MessageTemplate("占位符 {name} 生成的SQL疑似中文说明或非SQL文本，已拒绝: {sql_preview}"),

        # 占位符处理异常
        "placeholder_exception": MessageTemplate("❌ 处理占位符 {name} 时异常: {error}"),
        "placeholder_exception_progress": MessageTemplate("占位符 {name} 处理异常"),

        # ETL 处理
        "etl_start": MessageTemplate("开始执行占位符ETL处理..."),
        "etl_progress": MessageTemplate("正在执行ETL处理..."),
        "etl_completed": MessageTemplate("ETL处理完成"),

        # 报告生成
        "report_generation_start": MessageTemplate("开始生成报告文件..."),
        "report_generation_progress": MessageTemplate("正在生成报告..."),
        "report_generation_failed": MessageTemplate("报告生成失败: {error}"),
        "report_generation_success": MessageTemplate("报告生成成功"),
    }
    
    CONSTANTS = {
        "schema_context_top_k": 10,
        "placeholder_batch_size": 5,
        "quality_threshold": 0.6,
    }
    
    @classmethod
    def get_message(cls, key: str, **kwargs) -> str:
        template = cls.MESSAGES.get(key)
        if not template:
            return f"[Missing: {key}]"
        return template.format(**kwargs)
    
    @classmethod
    def get_constant(cls, key: str, default: Any = None) -> Any:
        return cls.CONSTANTS.get(key, default)
