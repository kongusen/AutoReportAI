"""
AutoReportAI MCP Tools
MCP工具模块包
"""

# 导入已实现的模块
try:
    from .auth_tools import *
except ImportError:
    pass

try:
    from .data_source_tools import *
except ImportError:
    pass

try:
    from .template_tools import *
except ImportError:
    pass

try:
    from .task_tools import *
except ImportError:
    pass

try:
    from .report_tools import *
except ImportError:
    pass

# 暂时注释掉未实现的模块
# from .ai_provider_tools import *
# from .settings_tools import *
# from .user_tools import *
# from .workflow_tools import *

__all__ = [
    # Auth tools (已实现)
    "login", "logout", "get_current_user", "switch_user", "list_sessions",
    
    # Data source tools (已实现)
    "list_data_sources", "create_sql_data_source", "create_api_data_source",
    "upload_csv_data_source", "test_data_source", "sync_data_source", "delete_data_source",
    
    # Template tools (已实现)
    "list_templates", "create_text_template", "upload_template_file", "get_template",
    "update_template", "delete_template", "duplicate_template", "preview_template",
    
    # Task tools (已实现)
    "list_tasks", "create_task", "get_task", "update_task", "run_task",
    "enable_task", "disable_task", "delete_task", "get_task_logs", "get_task_status",
    
    # Report tools (已实现)
    "generate_report", "list_reports", "get_report", "download_report", "regenerate_report",
    "delete_report", "get_report_content", "batch_generate_reports",
    
    # AI provider tools (待实现)
    # "list_ai_providers", "create_ai_provider", "update_ai_provider",
    
    # Settings tools (待实现)
    # "get_system_settings", "update_system_settings", 
    
    # User tools (待实现)
    # "list_users", "create_user", "update_user", "delete_user", "reset_user_password",
    
    # Workflow tools (待实现)
    # "create_complete_workflow", "setup_daily_report", "setup_weekly_report",
]