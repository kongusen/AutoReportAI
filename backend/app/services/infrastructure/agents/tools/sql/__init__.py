"""
SQL 工具库

提供 SQL 生成、验证、列检查、自动修复和执行功能
"""

from .generator import (
    SQLGeneratorTool,
    QueryType,
    JoinType,
    QueryRequest,
    QueryResult,
    create_sql_generator_tool
)

from .validator import (
    SQLValidatorTool,
    ValidationLevel,
    ValidationResult,
    ValidationIssue,
    ValidationReport,
    create_sql_validator_tool
)

from .column_checker import (
    SQLColumnCheckerTool,
    ColumnCheckType,
    CheckResult,
    ColumnCheckIssue,
    ColumnCheckReport,
    create_sql_column_checker_tool
)

from .auto_fixer import (
    SQLAutoFixerTool,
    FixType,
    FixLevel,
    FixSuggestion,
    FixReport,
    create_sql_auto_fixer_tool
)

from .executor import (
    SQLExecutorTool,
    ExecutionStatus,
    QueryType as ExecutorQueryType,
    ExecutionResult,
    ExecutionOptions,
    create_sql_executor_tool
)

# 导出
__all__ = [
    # Generator
    "SQLGeneratorTool",
    "QueryType",
    "JoinType",
    "QueryRequest",
    "QueryResult",
    "create_sql_generator_tool",
    
    # Validator
    "SQLValidatorTool",
    "ValidationLevel",
    "ValidationResult",
    "ValidationIssue",
    "ValidationReport",
    "create_sql_validator_tool",
    
    # Column Checker
    "SQLColumnCheckerTool",
    "ColumnCheckType",
    "CheckResult",
    "ColumnCheckIssue",
    "ColumnCheckReport",
    "create_sql_column_checker_tool",
    
    # Auto Fixer
    "SQLAutoFixerTool",
    "FixType",
    "FixLevel",
    "FixSuggestion",
    "FixReport",
    "create_sql_auto_fixer_tool",
    
    # Executor
    "SQLExecutorTool",
    "ExecutionStatus",
    "ExecutorQueryType",
    "ExecutionResult",
    "ExecutionOptions",
    "create_sql_executor_tool",
]