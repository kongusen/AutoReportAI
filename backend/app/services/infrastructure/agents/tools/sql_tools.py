"""
SQL 工具集（规范化）

提供标准的 SQL 生成与 SQL 执行工具类，以供 Agent/编排/工具系统调用。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..core.tools.registry import BaseTool
from ..types import ToolSafetyLevel


@dataclass
class DatabaseSchema:
    """数据库schema"""
    tables: Dict[str, Dict[str, str]]  # table_name -> {column_name: column_type}
    relationships: List[Dict[str, str]]  # foreign key relationships
    sample_data: Dict[str, List[Dict]]  # table_name -> sample rows


class SQLGeneratorTool(BaseTool):
    """SQL 生成工具（规范化实现）"""

    def __init__(self):
        super().__init__(
            name="sql_generator",
            description="根据自然语言需求生成SQL查询"
        )

        # 模拟数据库schema
        self.schema = DatabaseSchema(
            tables={
                "users": {
                    "id": "int",
                    "name": "varchar",
                    "email": "varchar",
                    "age": "int",
                    "department_id": "int",
                    "created_at": "datetime",
                },
                "departments": {
                    "id": "int",
                    "name": "varchar",
                    "manager_id": "int",
                    "budget": "decimal",
                },
                "orders": {
                    "id": "int",
                    "user_id": "int",
                    "product_name": "varchar",
                    "amount": "decimal",
                    "order_date": "datetime",
                },
            },
            relationships=[
                {"from": "users.department_id", "to": "departments.id"},
                {"from": "orders.user_id", "to": "users.id"},
                {"from": "departments.manager_id", "to": "users.id"},
            ],
            sample_data={
                "users": [
                    {"id": 1, "name": "张三", "email": "zhang@test.com", "age": 25, "department_id": 1},
                    {"id": 2, "name": "李四", "email": "li@test.com", "age": 30, "department_id": 2},
                ],
                "departments": [
                    {"id": 1, "name": "技术部", "manager_id": 1, "budget": 100000},
                    {"id": 2, "name": "销售部", "manager_id": 2, "budget": 80000},
                ],
            },
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL生成"""

        objective = input_data.get("objective", "")
        previous_sql = input_data.get("previous_sql")
        issues_to_fix = input_data.get("issues_to_fix", [])

        if previous_sql and issues_to_fix:
            sql_query = await self._fix_sql(previous_sql, issues_to_fix, objective)
            generation_type = "修正"
        else:
            sql_query = await self._generate_sql(objective)
            generation_type = "首次生成"

        return {
            "sql_query": sql_query,
            "generation_type": generation_type,
            "schema_used": list(self.schema.tables.keys()),
            "success": True,
            "timestamp": datetime.now().isoformat(),
        }

    async def _generate_sql(self, objective: str) -> str:
        objective_lower = objective.lower()

        if "用户" in objective and "年龄" in objective and "平均" in objective:
            return (
                "SELECT AVG(age) as average_age, COUNT(*) as user_count\n"
                "FROM users\n"
                "WHERE age IS NOT NULL;\n"
            )
        elif "部门" in objective and "员工数量" in objective:
            return (
                "SELECT d.name as department_name, COUNT(u.id) as employee_count\n"
                "FROM departments d\n"
                "LEFT JOIN users u ON d.id = u.department_id\n"
                "GROUP BY d.id, d.name\n"
                "ORDER BY employee_count DESC;\n"
            )
        elif "订单" in objective and "总金额" in objective:
            return (
                "SELECT u.name as user_name, SUM(o.amount) as total_amount\n"
                "FROM users u\n"
                "JOIN orders o ON u.id = o.user_id\n"
                "GROUP BY u.id, u.name\n"
                "ORDER BY total_amount DESC;\n"
            )
        elif ("高年龄" in objective) or ("年龄较高" in objective) or ("年龄大于" in objective):
            return (
                "SELECT name, age, email\n"
                "FROM users\n"
                "WHERE age > 25\n"
                "ORDER BY age DESC;\n"
            )
        else:
            return "SELECT * FROM users LIMIT 10;\n"

    async def _fix_sql(self, previous_sql: str, issues: List[str], objective: str) -> str:
        fixed_sql = previous_sql
        for issue in issues:
            if "缺少必需字段" in issue and "department_name" in issue:
                if "departments d" not in fixed_sql and "department" in objective:
                    fixed_sql = fixed_sql.replace(
                        "FROM users",
                        "FROM users u JOIN departments d ON u.department_id = d.id",
                    ).replace(
                        "SELECT name", "SELECT u.name, d.name as department_name"
                    )
            elif "结果行数" in issue and "少于预期" in issue:
                if "WHERE age >" in fixed_sql:
                    fixed_sql = fixed_sql.replace("WHERE age > 25", "WHERE age > 20")
                elif "LIMIT" in fixed_sql:
                    fixed_sql = fixed_sql.replace("LIMIT 10", "LIMIT 50")
            elif "结果行数" in issue and "超过预期" in issue:
                if "WHERE" not in fixed_sql:
                    fixed_sql = fixed_sql.replace("FROM users", "FROM users WHERE age IS NOT NULL")
                elif "LIMIT" not in fixed_sql:
                    fixed_sql = fixed_sql.replace(";", " LIMIT 20;")
        return fixed_sql

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return "objective" in input_data

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "requirements": {"type": "string"},
                "context": {"type": "object"},
                "previous_sql": {"type": "string"},
                "issues_to_fix": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["objective"],
        }

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql_query": {"type": "string"},
                "generation_type": {"type": "string"},
                "schema_used": {"type": "array", "items": {"type": "string"}},
                "success": {"type": "boolean"},
                "timestamp": {"type": "string"},
            },
            "required": ["sql_query", "success"],
        }

    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.CAUTIOUS

    def get_capabilities(self) -> List[str]:
        return ["sql_generation", "analysis_mapping"]


class SQLExecutorTool(BaseTool):
    """SQL 执行工具（规范化实现）"""

    def __init__(self):
        super().__init__(
            name="sql_executor",
            description="执行SQL查询并返回结果",
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        sql_query: str = (input_data.get("sql_query") or "").strip()
        if not sql_query:
            raise ValueError("No SQL query provided")

        # 连接/执行逻辑：优先使用 data_source_id；其次使用 connector 配置；否则尝试默认连接
        parameters: Optional[Dict[str, Any]] = input_data.get("parameters")
        ds_id: Optional[str] = input_data.get("data_source_id")
        connector_cfg: Optional[Dict[str, Any]] = input_data.get("connector")

        # 安全校验：只允许 SELECT
        sql_upper = sql_query.upper().strip()
        if not sql_upper.startswith("SELECT"):
            return {
                "sql_query": sql_query,
                "success": False,
                "error": "Only SELECT statements are allowed",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            if ds_id:
                # 使用已注册数据源
                from app.services.data.connectors.connector_factory import create_connector
                from app.crud.crud_data_source import crud_data_source
                from app.db.session import get_db_session
                with get_db_session() as db:
                    data_source = crud_data_source.get(db, id=ds_id)
                    if not data_source:
                        raise ValueError(f"Data source not found: {ds_id}")
                    connector = create_connector(data_source)
                    await connector.connect()
                    try:
                        qres = await connector.execute_query(sql_query, parameters)
                    finally:
                        await connector.disconnect()
            elif connector_cfg and isinstance(connector_cfg, dict):
                # 临时连接配置（如: {source_type:'sql', connection_string:'...'} 或 doris 配置）
                from app.services.data.connectors.connector_factory import create_connector_from_config
                from app.models.data_source import DataSourceType
                from app.core.security_utils import decrypt_data
                from sqlalchemy import create_engine, text as _sql_text
                import pandas as _pd
                src_type = connector_cfg.get("source_type") or connector_cfg.get("type") or "sql"
                # 将字符串映射为枚举，兼容传入 'sql'/'doris' 等
                try:
                    if isinstance(src_type, str):
                        src_enum = DataSourceType[src_type] if src_type in DataSourceType.__members__ else DataSourceType(src_type)
                    else:
                        src_enum = src_type
                except Exception:
                    # 兜底到 SQL
                    src_enum = DataSourceType.sql
                name = connector_cfg.get("name") or "adhoc"
                connector = create_connector_from_config(src_enum, name, connector_cfg)
                await connector.connect()
                try:
                    qres = await connector.execute_query(sql_query, parameters)
                finally:
                    await connector.disconnect()

                # fallback: 若执行不成功且为sqlite连接，使用无池化直连尝试一次
                if (not getattr(qres, 'success', False)) and isinstance(connector_cfg.get('connection_string'), str):
                    try:
                        conn_str = decrypt_data(connector_cfg.get('connection_string'))
                        if isinstance(conn_str, str) and conn_str.startswith('sqlite:///'):
                            eng = create_engine(conn_str)  # 使用默认池设置，避免 QueuePool 与 sqlite 的兼容问题
                            df = _pd.read_sql(sql_query, eng, params=parameters)
                            qres = type(qres)(data=df, execution_time=qres.execution_time, success=True, error_message=None, metadata={"fallback": "direct_sqlite"})
                    except Exception:
                        pass
            else:
                return {
                    "sql_query": sql_query,
                    "success": False,
                    "error": "Missing connection info: provide data_source_id or connector config",
                    "timestamp": datetime.now().isoformat(),
                }

            # 统一 QueryResult -> columns/rows
            if hasattr(qres, "data"):
                df = qres.data
                columns = df.columns.tolist()
                rows = [list(row) for row in df.itertuples(index=False, name=None)]
                return {
                    "sql_query": sql_query,
                    "success": qres.success,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "execution_time": qres.execution_time,
                    "timestamp": datetime.now().isoformat(),
                    "error": qres.error_message,
                }
            else:
                # 回退（极少数连接器实现不返回 DataFrame）
                return {
                    "sql_query": sql_query,
                    "success": True,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "execution_time": 0.0,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            return {
                "sql_query": sql_query,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return "sql_query" in input_data

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql_query": {"type": "string"},
                "parameters": {"type": "object"},
                "data_source_id": {"type": "string"},
                "connector": {"type": "object"},
                "timeout": {"type": "number"},
                "limit": {"type": "integer"},
            },
            "required": ["sql_query"],
        }

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql_query": {"type": "string"},
                "columns": {"type": "array", "items": {"type": "string"}},
                "rows": {"type": "array", "items": {"type": "array"}},
                "row_count": {"type": "integer"},
                "execution_time": {"type": "number"},
                "success": {"type": "boolean"},
                "error": {"type": "string"},
            },
            "required": ["success"],
        }

    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.CAUTIOUS

    def get_capabilities(self) -> List[str]:
        return ["sql_execution", "query_validation"]
