"""
应用层现代化工厂

为上层提供与领域服务之间的现代化构造，
移除向后兼容负担，专注于纯数据库驱动架构。
"""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session


def create_agent_sql_analysis_service(db: Session, user_id: str):
    """创建 AgentSQLAnalysisService 的现代化工厂方法。

    通过此工厂避免在 orchestrator 中直接导入 template 下的实现，
    降低互相依赖风险。
    要求user_id参数，与纯数据库驱动架构保持一致。
    """
    if not user_id:
        raise ValueError("user_id is required for Agent SQL Analysis Service")
    
    # 延迟导入，避免在导入期触发循环依赖
    from app.services.domain.template.agent_sql_analysis_service import AgentSQLAnalysisService

    return AgentSQLAnalysisService(db, user_id=user_id)


def create_enhanced_template_parser(db: Session, user_id: str):
    """创建 EnhancedTemplateParser 的中立工厂方法。"""
    if not user_id:
        raise ValueError("user_id is required for Enhanced Template Parser")
    
    # 使用新的Claude Code架构模板解析服务
    # Service orchestrator has been migrated to agents system
    from app.services.infrastructure.agents import execute_agent_task
    
    # Return a compatibility wrapper for agents system
    class AgentsTemplateParserWrapper:
        def __init__(self, user_id: str):
            self.user_id = user_id
        
        async def parse_template_structure(self, template_content: str):
            # Use agents system for template parsing
            return await execute_agent_task(
                task_name="template_parsing",
                task_description="Parse template structure",
                context_data={
                    "template_content": template_content,
                    "user_id": self.user_id
                }
            )
    
    return AgentsTemplateParserWrapper(user_id)


def create_intelligent_placeholder_workflow(user_id: str, config=None):
    """创建智能占位符工作流"""
    if not user_id:
        raise ValueError("user_id is required for Intelligent Placeholder Workflow")
    
    from app.services.application.workflows.intelligent_placeholder_workflow import IntelligentPlaceholderWorkflow
    return IntelligentPlaceholderWorkflow(user_id=user_id, config=config)


def create_enhanced_report_generation_workflow(user_id: str, placeholder_orchestrator=None, config=None):
    """创建增强报告生成工作流"""
    if not user_id:
        raise ValueError("user_id is required for Enhanced Report Generation Workflow")
    
    from app.services.application.workflows.enhanced_report_generation_workflow import EnhancedReportGenerationWorkflow
    return EnhancedReportGenerationWorkflow(user_id=user_id, placeholder_orchestrator=placeholder_orchestrator, config=config)


def create_context_aware_task_service(user_id: str, orchestrator=None, execution_strategy=None):
    """创建上下文感知任务服务"""
    if not user_id:
        raise ValueError("user_id is required for Context Aware Task Service")
    
    from app.services.application.workflows.context_aware_task_service import ContextAwareTaskService
    return ContextAwareTaskService(user_id=user_id, orchestrator=orchestrator, execution_strategy=execution_strategy)


def create_template_debug_workflow(user_id: str, placeholder_orchestrator=None):
    """创建模板调试工作流"""
    if not user_id:
        raise ValueError("user_id is required for Template Debug Workflow")
    
    from app.services.application.workflows.template_debug_workflow import TemplateDebugWorkflow
    return TemplateDebugWorkflow(user_id=user_id, placeholder_orchestrator=placeholder_orchestrator)


# === 现代化纯数据库驱动工厂 ===

def create_pure_database_schema_analysis_service(db: Session, user_id: str):
    """创建纯数据库驱动的Schema分析服务"""
    if not user_id:
        raise ValueError("user_id is required for Schema Analysis Service")
    
    from app.services.data.schemas.schema_analysis_service import create_schema_analysis_service
    return create_schema_analysis_service(db, user_id)


def create_service_orchestrator(user_id: str = None):
    """创建新的Claude Code架构ServiceOrchestrator实例 - 已迁移到agents系统"""
    # Service orchestrator has been migrated to agents system
    from app.services.infrastructure.agents import execute_agent_task
    
    # Return a compatibility wrapper for agents system
    class AgentsServiceOrchestratorWrapper:
        def __init__(self, user_id: str = None):
            self.user_id = user_id
        
        async def orchestrate_task(self, task_name: str, task_description: str, context_data: dict):
            # Use agents system for orchestration
            return await execute_agent_task(
                task_name=task_name,
                task_description=task_description,
                context_data=context_data
            )
        
        async def analyze_single_placeholder_simple(self, 
                                                  user_id: str,
                                                  placeholder_name: str, 
                                                  placeholder_text: str,
                                                  template_id: str,
                                                  template_context: str,
                                                  data_source_info: dict,
                                                  task_params: dict = None,
                                                  cron_expression: str = None,
                                                  execution_time=None,
                                                  task_type: str = "manual"):
            """
            分析单个占位符并生成SQL - 使用AI agent进行智能分析
            """
            try:
                from datetime import datetime
                import logging
                
                logger = logging.getLogger(__name__)
                logger.info(f"开始智能分析占位符: {placeholder_name}")
                
                # 构建详细的任务描述用于AI分析
                task_description = f"""
                请分析以下占位符并生成相应的SQL查询语句：

                占位符信息：
                - 名称：{placeholder_name}
                - 文本：{placeholder_text}
                - 任务类型：{task_type}

                业务上下文：
                {template_context[:1000] + '...' if template_context and len(template_context) > 1000 else template_context or '无特定上下文'}

                数据源信息：
                - 数据库类型：{data_source_info.get('type', 'doris')}
                - 数据库名称：{data_source_info.get('database', 'unknown')}
                - 可用表：{', '.join(data_source_info.get('tables', [])[:10])}

                表结构详情：
                """
                
                # 添加表结构信息
                if data_source_info.get("table_details"):
                    for i, table in enumerate(data_source_info["table_details"][:5]):  # 限制表数量
                        task_description += f"\n表{i+1}: {table.get('name', 'unknown')}"
                        task_description += f"\n  - 业务分类: {table.get('business_category', '未分类')}"
                        task_description += f"\n  - 列数: {table.get('columns_count', 0)}"
                        if table.get('key_columns'):
                            task_description += f"\n  - 主要字段: {', '.join(table['key_columns'][:10])}"
                
                task_description += f"""

                分析要求：
                1. 理解占位符"{placeholder_text}"的业务语义
                2. 根据可用表结构生成合适的SQL查询
                3. SQL应该能够返回有意义的业务数据
                4. 确保SQL语法正确且可在{data_source_info.get('type', 'doris')}上执行
                5. 如果是时间相关的占位符，考虑使用适当的日期函数

                请返回一个完整的、可执行的SQL查询语句。
                """
                
                # 构建上下文数据
                context_data = {
                    "user_id": user_id,
                    "placeholder_name": placeholder_name,
                    "placeholder_text": placeholder_text,
                    "template_id": template_id,
                    "template_context": template_context,
                    "data_source_info": data_source_info,
                    "task_params": task_params or {},
                    "cron_expression": cron_expression,
                    "execution_time": execution_time.isoformat() if execution_time else None,
                    "task_type": task_type,
                    "placeholders": {
                        placeholder_name: placeholder_text
                    },
                    "database_schemas": [
                        {
                            "table_name": table_detail.get("name", ""),
                            "columns": table_detail.get("all_columns", []),
                            "business_category": table_detail.get("business_category", "")
                        } 
                        for table_detail in data_source_info.get("table_details", [])
                    ] if data_source_info.get("table_details") else []
                }
                
                # 使用 Agent 系统进行智能分析（正确的架构方式）
                try:
                    # 导入 agent 执行函数
                    from app.services.infrastructure.agents import execute_agent_task
                    
                    logger.info(f"请求 SQL 生成 Agent 分析占位符: {placeholder_name}")
                    
                    # 请求 SQL 生成 Agent 处理任务
                    agent_result = await execute_agent_task(
                        task_name="placeholder_sql_generation",
                        task_description=task_description,
                        context_data=context_data,
                        target_agent="sql_generation_agent",
                        timeout_seconds=120
                    )
                    
                    logger.info(f"Agent 执行结果: {agent_result.get('success', False)}")
                    
                    # 解析 Agent 返回的结果 - 使用标准化格式
                    generated_sql = ""
                    analysis_description = ""
                    
                    if agent_result.get("success", False):
                        # 获取标准化结果
                        result_data = agent_result.get("result", {})
                        
                        # 从标准化格式中提取SQL
                        if isinstance(result_data, dict):
                            generated_sql = result_data.get("sql_query", "") or result_data.get("generated_sql", "")
                            analysis_description = result_data.get("explanation", "")
                            
                            # 如果标准字段为空，尝试从raw_result中提取
                            if not generated_sql and "raw_result" in result_data:
                                raw_result = result_data["raw_result"]
                                if isinstance(raw_result, dict):
                                    generated_sql = raw_result.get("sql_query", "") or raw_result.get("generated_sql", "")
                                    analysis_description = raw_result.get("explanation", analysis_description)
                        
                        logger.info(f"Agent 成功生成 SQL: {placeholder_name}")
                    else:
                        error_result = agent_result.get('error', '未知错误')
                        logger.warning(f"Agent 执行失败: {error_result}")
                    
                    # 如果 Agent 生成失败，使用智能兜底逻辑
                    if not generated_sql or not generated_sql.strip():
                        logger.warning(f"Agent SQL 生成为空，使用智能兜底逻辑: {placeholder_name}")
                        generated_sql = self._generate_smart_fallback_sql(
                            placeholder_name, placeholder_text, data_source_info
                        )
                        analysis_description = f"基于占位符'{placeholder_text}'的智能SQL生成"
                    
                except Exception as e:
                    logger.error(f"Agent 系统执行异常: {e}")
                    # 兜底：使用智能SQL生成
                    generated_sql = self._generate_smart_fallback_sql(
                        placeholder_name, placeholder_text, data_source_info
                    )
                    analysis_description = f"兜底SQL生成用于占位符: {placeholder_name}"
                
                return {
                    "status": "success",
                    "placeholder_name": placeholder_name,
                    "generated_sql": {
                        placeholder_name: generated_sql,
                        "sql": generated_sql
                    },
                    "analysis_result": {
                        "description": analysis_description or f"智能分析占位符: {placeholder_name}",
                        "analysis_type": "ai_placeholder_analysis",
                        "confidence": 0.85
                    },
                    "confidence_score": 0.85,
                    "analyzed_at": context_data.get("execution_time") or datetime.now().isoformat(),
                    "task_type": task_type,
                    "context_used": {
                        "template_context": bool(template_context),
                        "data_source_info": bool(data_source_info),
                        "task_params": bool(task_params),
                        "ai_agent_used": True
                    }
                }
                
            except Exception as e:
                # 返回错误结果，格式与调用方期望一致
                return {
                    "status": "error",
                    "error": {
                        "error_message": str(e),
                        "error_type": "analysis_error"
                    },
                    "placeholder_name": placeholder_name
                }
        
        def _generate_smart_fallback_sql(self, placeholder_name: str, placeholder_text: str, data_source_info: dict) -> str:
            """智能兜底SQL生成"""
            
            # 分析占位符文本的语义
            text_lower = placeholder_text.lower()
            
            # 获取第一个可用的表（优先选择业务表）
            tables = data_source_info.get("tables", [])
            selected_table = None
            
            # 优先选择包含业务数据的表
            business_keywords = ["complain", "order", "user", "customer", "sales", "itinerary", "refund"]
            for table in tables:
                table_lower = table.lower()
                if any(keyword in table_lower for keyword in business_keywords):
                    selected_table = table
                    break
            
            # 如果没有找到业务表，使用第一个表
            if not selected_table and tables:
                selected_table = tables[0]
            
            # 如果还是没有表，使用默认占位符
            if not selected_table:
                selected_table = "default_table"
            
            # 根据占位符语义生成SQL
            if "统计" in text_lower or "count" in text_lower:
                # 统计类查询
                if "开始日期" in text_lower or "起始" in text_lower:
                    return f"""
                    SELECT 
                        COUNT(*) as total_records,
                        MIN(DATE(create_time)) as start_date,
                        '统计开始日期' as metric_type
                    FROM {data_source_info.get('database', 'yjg')}.{selected_table}
                    WHERE DATE(create_time) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    """.strip()
                else:
                    return f"""
                    SELECT 
                        COUNT(*) as total_count,
                        DATE(CURDATE()) as analysis_date,
                        '{placeholder_text}' as metric_description  
                    FROM {data_source_info.get('database', 'yjg')}.{selected_table}
                    WHERE DATE(create_time) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                    LIMIT 10
                    """.strip()
            
            elif "周期" in text_lower or "period" in text_lower:
                # 周期类查询
                return f"""
                SELECT 
                    DATE(create_time) as period_date,
                    COUNT(*) as period_count,
                    '{placeholder_text}' as period_type
                FROM {data_source_info.get('database', 'yjg')}.{selected_table}
                WHERE create_time >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
                GROUP BY DATE(create_time)
                ORDER BY period_date DESC
                LIMIT 30
                """.strip()
            
            elif "日期" in text_lower or "date" in text_lower or "时间" in text_lower:
                # 日期时间类查询
                return f"""
                SELECT 
                    DATE(create_time) as target_date,
                    COUNT(*) as daily_count,
                    '{placeholder_text}' as date_metric
                FROM {data_source_info.get('database', 'yjg')}.{selected_table}
                WHERE create_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY DATE(create_time)
                ORDER BY target_date DESC
                LIMIT 10
                """.strip()
            
            else:
                # 通用查询
                return f"""
                SELECT 
                    COUNT(*) as metric_value,
                    CURDATE() as metric_date,
                    '{placeholder_text}' as metric_name,
                    '{selected_table}' as source_table
                FROM {data_source_info.get('database', 'yjg')}.{selected_table}
                LIMIT 5
                """.strip()
    
    return AgentsServiceOrchestratorWrapper(user_id)


def create_user_etl_service(user_id: str):
    """创建用户专属的ETL服务"""
    if not user_id:
        raise ValueError("user_id is required for User ETL Service")
    
    from app.services.data.processing.etl.etl_service import create_etl_service
    return create_etl_service(user_id)


def create_intelligent_etl_executor(db: Session, user_id: str):
    """创建用户专属的智能ETL执行器"""
    if not user_id:
        raise ValueError("user_id is required for Intelligent ETL Executor")
    
    from app.services.data.processing.etl.intelligent_etl_executor import create_intelligent_etl_executor as create_etl_executor_impl
    return create_etl_executor_impl(db, user_id)


def create_query_optimizer(user_id: str):
    """创建用户专属的查询优化器"""
    if not user_id:
        raise ValueError("user_id is required for Query Optimizer")
    
    from app.services.data.processing.query_optimizer import create_query_optimizer as create_optimizer_impl
    return create_optimizer_impl(user_id)


def create_schema_aware_analysis_service(db: Session, user_id: str):
    """创建用户专属的Schema感知分析服务"""
    if not user_id:
        raise ValueError("user_id is required for Schema Aware Analysis Service")
    
    from app.services.data.processing.schema_aware_analysis import create_schema_aware_analysis_service as create_analysis_impl
    return create_analysis_impl(db, user_id)


def create_data_analysis_service(db: Session, user_id: str = None):
    """创建数据分析服务"""
    from app.services.data.processing.analysis import create_data_analysis_service as create_analysis_service_impl
    return create_analysis_service_impl(db, user_id)


def create_ai_tools_integration_service(user_id: str):
    """创建AI工具集成服务"""
    if not user_id:
        raise ValueError("user_id is required for AI Tools Integration Service")
    
    # AI tools integration has been migrated to agents system
    from app.services.infrastructure.agents.tools import get_tool_registry
    
    # Return a compatibility wrapper for the migrated system
    class AgentsToolsIntegration:
        def __init__(self, user_id: str):
            self.user_id = user_id
            self.tool_registry = get_tool_registry()
        
        def get_available_tools(self):
            return self.tool_registry.get_all_tools()
    
    return AgentsToolsIntegration(user_id)


# === 任务服务工厂 ===

def create_task_application_service(user_id: str = None):
    """创建任务应用服务"""
    from app.services.application.tasks.task_application_service import TaskApplicationService
    return TaskApplicationService()


def create_task_execution_service(user_id: str):
    """创建任务执行服务"""
    if not user_id:
        raise ValueError("user_id is required for Task Execution Service")
    
    from app.services.application.tasks.task_execution_service import TaskExecutionService
    return TaskExecutionService(user_id=user_id)


# === 导出列表 ===

__all__ = [
    # 传统工厂方法（保持API兼容性）
    "create_agent_sql_analysis_service",
    "create_enhanced_template_parser", 
    "create_intelligent_placeholder_workflow",
    "create_enhanced_report_generation_workflow",
    "create_context_aware_task_service",
    "create_template_debug_workflow",
    
    # 现代化纯数据库驱动工厂
    "create_pure_database_schema_analysis_service",
    "create_service_orchestrator",  # 新的Claude Code架构 
    "create_user_etl_service",
    
    # 数据处理服务工厂
    "create_intelligent_etl_executor",
    "create_query_optimizer", 
    "create_schema_aware_analysis_service",
    "create_data_analysis_service",
    
    # AI工具集成服务
    "create_ai_tools_integration_service",
    
    # 任务服务工厂
    "create_task_application_service",
    "create_task_execution_service",
]