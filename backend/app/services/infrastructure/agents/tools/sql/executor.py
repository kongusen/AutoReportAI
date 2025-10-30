from __future__ import annotations

from loom.interfaces.tool import BaseTool
"""
SQL 执行工具

执行 SQL 查询并返回结果
支持查询执行、结果处理和错误处理
"""


import logging
import time
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueryType(str, Enum):
    """查询类型"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    ALTER = "ALTER"
    DROP = "DROP"
    OTHER = "OTHER"


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    query_type: QueryType
    rows_affected: int
    execution_time: float
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExecutionOptions:
    """执行选项"""
    timeout: float = 30.0
    max_rows: Optional[int] = None
    fetch_size: int = 1000
    auto_commit: bool = True
    isolation_level: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SQLExecutorTool(BaseTool):
    """SQL 执行工具"""
    
    def __init__(self, container: Any, connection_config: Optional[Dict[str, Any]] = None):
        """
        Args:
            container: 服务容器
            connection_config: 数据源连接配置（在初始化时注入，LLM 不需要传递）
        """
        super().__init__()

        self.name = "sql_executor"

        self.category = ToolCategory.SQL

        self.description = "执行 SQL 查询并返回结果"
        self.container = container
        self._connection_config = connection_config  # 🔥 保存连接配置
        self._data_source_service = None
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class SQLExecutorArgs(BaseModel):
            sql: str = Field(description="要执行的 SQL 查询")
            timeout: float = Field(default=30.0, description="执行超时时间（秒）")
            max_rows: Optional[int] = Field(default=None, description="最大返回行数")
            fetch_size: int = Field(default=1000, description="每次获取的行数")
            auto_commit: bool = Field(default=True, description="是否自动提交")
            isolation_level: Optional[str] = Field(default=None, description="事务隔离级别")
            validate_before_execute: bool = Field(default=True, description="执行前是否验证 SQL")

        self.args_schema = SQLExecutorArgs
    
    async def _get_data_source_service(self):
        """获取数据源服务"""
        if self._data_source_service is None:
            self._data_source_service = getattr(
                self.container, 'data_source', None
            ) or getattr(self.container, 'data_source_service', None)
        return self._data_source_service
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "sql_executor",
                "description": "执行 SQL 查询并返回结果",
                "parameters": parameters,
            },
        }
    
    async def run(
        self,
        sql: str,
        timeout: float = 30.0,
        max_rows: Optional[int] = None,
        fetch_size: int = 1000,
        auto_commit: bool = True,
        isolation_level: Optional[str] = None,
        validate_before_execute: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 SQL 查询

        Args:
            sql: 要执行的 SQL 查询
            timeout: 执行超时时间
            max_rows: 最大返回行数
            fetch_size: 每次获取的行数
            auto_commit: 是否自动提交
            isolation_level: 事务隔离级别
            validate_before_execute: 执行前是否验证 SQL

        Returns:
            Dict[str, Any]: 执行结果
        """
        logger.info(f"🚀 [SQLExecutorTool] 执行 SQL")
        logger.info(f"   SQL 长度: {len(sql)} 字符")
        logger.info(f"   超时时间: {timeout} 秒")

        # 🔥 优先使用初始化时注入的 connection_config；允许从 kwargs 临时传入以便验证/测试
        connection_config = self._connection_config or kwargs.get("connection_config")
        if not connection_config:
            return {
                "success": False,
                "error": "未配置数据源连接，请在初始化工具时提供 connection_config",
                "result": None
            }

        start_time = time.time()
        
        try:
            # 获取数据源服务
            data_source_service = await self._get_data_source_service()
            if not data_source_service:
                return {
                    "success": False,
                    "error": "数据源服务不可用",
                    "result": None
                }
            
            # 执行前验证
            if validate_before_execute:
                validation_result = await self._validate_sql(
                    sql, connection_config,
                    context=kwargs.get("context"),
                    task_context=kwargs.get("task_context"),
                    template_context=kwargs.get("template_context")
                )
                if not validation_result.get("success"):
                    return {
                        "success": False,
                        "error": f"SQL 验证失败: {validation_result.get('error')}",
                        "result": None
                    }
            else:
                # 快速校验：在未开启验证时，也做一次轻量的可行性检查，避免将中文/思考文本当 SQL 执行
                if not self._is_plausible_sql(sql):
                    return {
                        "success": False,
                        "error": "检测到非SQL文本（可能为思考内容/说明），已跳过执行",
                        "result": None
                    }
            
            # 确定查询类型
            query_type = self._determine_query_type(sql)
            
            # 兼容性重写：Doris 不支持 FILTER 语法，自动重写为 SUM(CASE WHEN ... THEN 1 ELSE 0 END)
            sql = self._rewrite_incompatible_syntax(sql, connection_config)

            # 构建执行选项
            options = ExecutionOptions(
                timeout=timeout,
                max_rows=max_rows,
                fetch_size=fetch_size,
                auto_commit=auto_commit,
                isolation_level=isolation_level
            )
            
            # 执行查询
            result = await self._execute_query(
                data_source_service, connection_config, sql, options, query_type
            )
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "result": result,
                "metadata": {
                    "execution_time": execution_time,
                    "query_type": query_type.value,
                    "sql_length": len(sql),
                    "timeout": timeout
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ [SQLExecutorTool] 执行失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None,
                "metadata": {
                    "execution_time": execution_time,
                    "sql_length": len(sql)
                }
            }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """向后兼容的execute方法"""
        return await self.run(**kwargs)
    
    async def _validate_sql(self, sql: str, connection_config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """验证 SQL"""
        try:
            from .validator import create_sql_validator_tool
            
            validator_tool = create_sql_validator_tool(self.container)
            
            # 透传可用上下文，便于时间占位符解析
            pass_kwargs = {
                "sql": sql,
                "connection_config": connection_config,
                "validation_level": "basic",
                "check_syntax": True,
                "check_semantics": False,
                "check_performance": False,
            }
            for k in ("context", "task_context", "template_context"):
                if k in kwargs and kwargs[k] is not None:
                    pass_kwargs[k] = kwargs[k]

            result = await validator_tool.execute(**pass_kwargs)
            
            if result.get("success"):
                report = result.get("report")
                if report and report.get("is_valid"):
                    return {"success": True}
                else:
                    errors = report.get("errors", []) if report else []
                    error_messages = [error.get("message", "") for error in errors]
                    return {
                        "success": False,
                        "error": "; ".join(error_messages)
                    }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "验证失败")
                }
                
        except Exception as e:
            logger.warning(f"⚠️ SQL 验证失败: {e}")
            return {"success": True}  # 验证失败时继续执行
    
    def _determine_query_type(self, sql: str) -> QueryType:
        """确定查询类型"""
        sql_upper = sql.strip().upper()
        
        if sql_upper.startswith("SELECT"):
            return QueryType.SELECT
        elif sql_upper.startswith("INSERT"):
            return QueryType.INSERT
        elif sql_upper.startswith("UPDATE"):
            return QueryType.UPDATE
        elif sql_upper.startswith("DELETE"):
            return QueryType.DELETE
        elif sql_upper.startswith("CREATE"):
            return QueryType.CREATE
        elif sql_upper.startswith("ALTER"):
            return QueryType.ALTER
        elif sql_upper.startswith("DROP"):
            return QueryType.DROP
        else:
            return QueryType.OTHER

    def _is_plausible_sql(self, sql: str) -> bool:
        """轻量级SQL可行性检查，过滤明显的非SQL文本。"""
        text = sql.strip()
        if not text:
            return False
        # 常见SQL起始关键字
        starters = ("SELECT", "WITH", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "EXPLAIN")
        if not text[:10].upper().startswith(starters):
            return False
        # 粗略检查是否包含中文，若大量中文且无关键字，判定为非SQL
        if any('\u4e00' <= ch <= '\u9fff' for ch in text[:80]):
            # 若包含中文但也包含 FROM/WHERE 等结构，则仍允许
            upper = text.upper()
            if not any(k in upper for k in (" FROM ", " WHERE ", " JOIN ", " INTO ", " VALUES ")):
                return False
        return True

    def _rewrite_incompatible_syntax(self, sql: str, connection_config: Dict[str, Any]) -> str:
        """将部分不兼容 Doris 的语法重写为等价表达。

        - 重写 COUNT(*) FILTER (WHERE cond) 为 SUM(CASE WHEN cond THEN 1 ELSE 0 END)
        """
        try:
            db_type = (connection_config or {}).get("type") or (connection_config or {}).get("database_type")
            if not db_type or str(db_type).lower() != "doris":
                return sql

            s = sql
            upper = s.upper()
            if "FILTER (WHERE" in upper:
                # 简单（非完美）重写：只处理 COUNT(*) FILTER (WHERE <cond>)
                import re
                pattern = r"COUNT\s*\(\s*\*\s*\)\s*FILTER\s*\(\s*WHERE\s*(.*?)\)"
                def repl(m):
                    cond = m.group(1)
                    return f"SUM(CASE WHEN {cond} THEN 1 ELSE 0 END)"
                s = re.sub(pattern, repl, s, flags=re.IGNORECASE | re.DOTALL)
            return s
        except Exception:
            return sql
    
    async def _execute_query(
        self,
        data_source_service: Any,
        connection_config: Dict[str, Any],
        sql: str,
        options: ExecutionOptions,
        query_type: QueryType
    ) -> ExecutionResult:
        """执行查询"""
        start_time = time.time()
        
        try:
            # 构建查询参数
            query_params = {
                "connection_config": connection_config,
                "sql": sql,
                "limit": options.max_rows,
                "timeout": options.timeout
            }
            
            # 执行查询
            result = await data_source_service.run_query(**query_params)
            
            execution_time = time.time() - start_time
            
            if result.get("success"):
                # 处理成功结果
                return self._process_success_result(result, query_type, execution_time)
            else:
                # 处理失败结果
                return self._process_error_result(result, query_type, execution_time)
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 查询执行异常: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                query_type=query_type,
                rows_affected=0,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _process_success_result(
        self,
        result: Dict[str, Any],
        query_type: QueryType,
        execution_time: float
    ) -> ExecutionResult:
        """处理成功结果"""
        rows = result.get("rows", []) or result.get("data", [])
        columns = result.get("columns", [])
        
        # 计算影响的行数
        rows_affected = 0
        if query_type in [QueryType.INSERT, QueryType.UPDATE, QueryType.DELETE]:
            rows_affected = result.get("rows_affected", len(rows))
        elif query_type == QueryType.SELECT:
            rows_affected = len(rows)
        
        # 处理数据
        data = None
        if query_type == QueryType.SELECT and rows:
            data = self._format_result_data(rows, columns)
        
        # 提取警告
        warnings = result.get("warnings", [])
        if isinstance(warnings, str):
            warnings = [warnings]
        
        return ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            query_type=query_type,
            rows_affected=rows_affected,
            execution_time=execution_time,
            data=data,
            columns=columns,
            warnings=warnings,
            metadata={
                "result_keys": list(result.keys()),
                "has_data": data is not None,
                "data_count": len(data) if data else 0
            }
        )
    
    def _process_error_result(
        self,
        result: Dict[str, Any],
        query_type: QueryType,
        execution_time: float
    ) -> ExecutionResult:
        """处理错误结果"""
        error_message = result.get("error", "未知错误")
        
        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            query_type=query_type,
            rows_affected=0,
            execution_time=execution_time,
            error_message=error_message,
            warnings=result.get("warnings", [])
        )
    
    def _format_result_data(
        self,
        rows: List[Any],
        columns: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """格式化结果数据"""
        if not rows:
            return []
        
        # 如果没有列名，尝试从第一行推断
        if not columns:
            if rows and isinstance(rows[0], dict):
                columns = list(rows[0].keys())
            else:
                columns = [f"column_{i}" for i in range(len(rows[0]) if rows else 0)]
        
        formatted_data = []
        
        for row in rows:
            if isinstance(row, dict):
                # 已经是字典格式
                formatted_data.append(row)
            elif isinstance(row, (list, tuple)):
                # 列表/元组格式，转换为字典
                row_dict = {}
                for i, value in enumerate(row):
                    column_name = columns[i] if i < len(columns) else f"column_{i}"
                    row_dict[column_name] = value
                formatted_data.append(row_dict)
            else:
                # 单个值
                formatted_data.append({columns[0]: row})
        
        return formatted_data
    
    async def execute_batch(
        self,
        sql_statements: List[str],
        connection_config: Dict[str, Any],
        options: Optional[ExecutionOptions] = None
    ) -> List[ExecutionResult]:
        """批量执行 SQL 语句"""
        if options is None:
            options = ExecutionOptions()
        
        results = []
        
        for sql in sql_statements:
            try:
                result = await self.execute(
                    sql=sql,
                    connection_config=connection_config,
                    timeout=options.timeout,
                    max_rows=options.max_rows,
                    fetch_size=options.fetch_size,
                    auto_commit=options.auto_commit,
                    isolation_level=options.isolation_level,
                    validate_before_execute=True
                )
                
                if result.get("success"):
                    results.append(result["result"])
                else:
                    # 创建失败结果
                    results.append(ExecutionResult(
                        status=ExecutionStatus.FAILED,
                        query_type=QueryType.OTHER,
                        rows_affected=0,
                        execution_time=0,
                        error_message=result.get("error", "执行失败")
                    ))
                    
            except Exception as e:
                logger.error(f"❌ 批量执行失败: {e}")
                results.append(ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    query_type=QueryType.OTHER,
                    rows_affected=0,
                    execution_time=0,
                    error_message=str(e)
                ))
        
        return results
    
    async def explain_query(
        self,
        sql: str,
        connection_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解释查询执行计划"""
        try:
            # 添加 EXPLAIN 前缀
            explain_sql = f"EXPLAIN {sql}"
            
            result = await self.execute(
                sql=explain_sql,
                connection_config=connection_config,
                validate_before_execute=False
            )
            
            if result.get("success"):
                execution_result = result["result"]
                return {
                    "success": True,
                    "explain_plan": execution_result.data,
                    "metadata": {
                        "execution_time": execution_result.execution_time,
                        "query_type": execution_result.query_type.value
                    }
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error"),
                    "explain_plan": None
                }
                
        except Exception as e:
            logger.error(f"❌ 解释查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "explain_plan": None
            }


def create_sql_executor_tool(
    container: Any,
    connection_config: Optional[Dict[str, Any]] = None
) -> SQLExecutorTool:
    """
    创建 SQL 执行工具

    Args:
        container: 服务容器
        connection_config: 数据源连接配置（在初始化时注入）

    Returns:
        SQLExecutorTool 实例
    """
    return SQLExecutorTool(container, connection_config=connection_config)


# 导出
__all__ = [
    "SQLExecutorTool",
    "ExecutionStatus",
    "QueryType",
    "ExecutionResult",
    "ExecutionOptions",
    "create_sql_executor_tool",
]