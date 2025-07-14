from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import sqlparse
from sqlalchemy import text
import re

@dataclass
class JoinConfig:
    """联表配置"""
    table: str
    join_type: str = "INNER"  # INNER, LEFT, RIGHT, FULL
    on_condition: str = ""
    alias: Optional[str] = None

@dataclass
class ColumnMapping:
    """字段映射配置"""
    source_column: str
    target_column: str
    data_type: str = "VARCHAR(255)"
    is_primary_key: bool = False
    is_foreign_key: bool = False
    reference_table: Optional[str] = None
    reference_column: Optional[str] = None

@dataclass
class WhereCondition:
    """条件配置"""
    column: str
    operator: str = "="
    value: Any = None
    logical_operator: str = "AND"  # AND, OR
    group: int = 0  # 条件分组

class SQLQueryBuilder:
    """SQL查询构建器，支持复杂的多表联查"""
    
    def __init__(self):
        self.base_query = ""
        self.joins = []
        self.columns = []
        self.where_conditions = []
        self.group_by = []
        self.order_by = []
        self.limit = None
        
    def set_base_query(self, table: str, columns: List[str] = None, alias: str = None):
        """设置基础查询"""
        if columns:
            cols = ", ".join(columns)
        else:
            cols = "*"
            
        table_name = f"{table} {alias}" if alias else table
        self.base_query = f"SELECT {cols} FROM {table_name}"
        return self
    
    def add_join(self, join_config: JoinConfig):
        """添加联表"""
        self.joins.append(join_config)
        return self
    
    def add_column_mapping(self, mapping: ColumnMapping):
        """添加字段映射"""
        if mapping.source_column != mapping.target_column:
            self.columns.append(f"{mapping.source_column} AS {mapping.target_column}")
        else:
            self.columns.append(mapping.source_column)
        return self
    
    def add_where_condition(self, condition: WhereCondition):
        """添加条件"""
        self.where_conditions.append(condition)
        return self
    
    def build(self) -> str:
        """构建最终SQL查询"""
        query_parts = [self.base_query]
        
        # 添加JOIN
        for join in self.joins:
            join_clause = f"{join.join_type} JOIN {join.table}"
            if join.alias:
                join_clause += f" {join.alias}"
            if join.on_condition:
                join_clause += f" ON {join.on_condition}"
            query_parts.append(join_clause)
        
        # 添加WHERE条件
        if self.where_conditions:
            where_clauses = []
            for condition in self.where_conditions:
                if isinstance(condition.value, str):
                    value_str = f"'{condition.value}'"
                else:
                    value_str = str(condition.value)
                
                where_clauses.append(f"{condition.column} {condition.operator} {value_str}")
            
            where_str = " WHERE " + " AND ".join(where_clauses)
            query_parts.append(where_str)
        
        # 添加GROUP BY
        if self.group_by:
            query_parts.append(f" GROUP BY {', '.join(self.group_by)}")
        
        # 添加ORDER BY
        if self.order_by:
            query_parts.append(f" ORDER BY {', '.join(self.order_by)}")
        
        # 添加LIMIT
        if self.limit:
            query_parts.append(f" LIMIT {self.limit}")
        
        return " ".join(query_parts)
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """验证SQL查询合法性"""
        try:
            parsed = sqlparse.parse(query)
            if not parsed:
                return {"valid": False, "error": "Empty query"}
            
            stmt = parsed[0]
            if stmt.get_type() != 'SELECT':
                return {"valid": False, "error": "Only SELECT queries are allowed"}
            
            # 检查危险操作
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
            query_upper = query.upper()
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    return {"valid": False, "error": f"Dangerous operation detected: {keyword}"}
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def extract_tables(self, query: str) -> List[str]:
        """从查询中提取涉及的表名"""
        # 简单的表名提取，实际项目中可以使用更复杂的SQL解析器
        table_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)|JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(table_pattern, query, re.IGNORECASE)
        tables = []
        for match in matches:
            tables.extend([t for t in match if t])
        return list(set(tables))

class WideTableBuilder:
    """宽表构建器"""
    
    def __init__(self, query_builder: SQLQueryBuilder):
        self.query_builder = query_builder
        
    def build_wide_table_query(self, 
                             base_table: str,
                             joins: List[JoinConfig],
                             mappings: List[ColumnMapping],
                             conditions: List[WhereCondition] = None) -> str:
        """构建宽表查询"""
        
        # 设置基础查询
        column_names = [f"{m.source_column} AS {m.target_column}" for m in mappings]
        self.query_builder.set_base_query(base_table, column_names)
        
        # 添加联表
        for join in joins:
            self.query_builder.add_join(join)
        
        # 添加条件
        if conditions:
            for condition in conditions:
                self.query_builder.add_where_condition(condition)
        
        return self.query_builder.build()
    
    def generate_schema(self, mappings: List[ColumnMapping]) -> Dict[str, Any]:
        """生成宽表schema"""
        schema = {
            "table_name": "",
            "columns": [],
            "primary_keys": [],
            "foreign_keys": []
        }
        
        for mapping in mappings:
            column_def = {
                "name": mapping.target_column,
                "type": mapping.data_type,
                "nullable": True
            }
            
            if mapping.is_primary_key:
                column_def["nullable"] = False
                schema["primary_keys"].append(mapping.target_column)
            
            if mapping.is_foreign_key and mapping.reference_table:
                schema["foreign_keys"].append({
                    "column": mapping.target_column,
                    "reference_table": mapping.reference_table,
                    "reference_column": mapping.reference_column
                })
            
            schema["columns"].append(column_def)
        
        return schema
