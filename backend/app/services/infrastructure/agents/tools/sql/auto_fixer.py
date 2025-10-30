from __future__ import annotations

from loom.interfaces.tool import BaseTool
"""
SQL 自动修复工具

自动修复 SQL 查询中的常见问题
提供智能修复建议和自动修复功能
"""


import logging
import re
from typing import Any, Dict, List, Optional, Union, Tuple, Literal
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, Field


from ...types import ToolCategory, ContextInfo

logger = logging.getLogger(__name__)


class FixType(str, Enum):
    """修复类型"""
    SYNTAX = "syntax"           # 语法修复
    SEMANTIC = "semantic"       # 语义修复
    PERFORMANCE = "performance" # 性能修复
    STYLE = "style"            # 风格修复


class FixLevel(str, Enum):
    """修复级别"""
    AUTOMATIC = "automatic"     # 自动修复
    SUGGESTION = "suggestion"   # 建议修复
    MANUAL = "manual"          # 手动修复


@dataclass
class FixSuggestion:
    """修复建议"""
    fix_type: FixType
    fix_level: FixLevel
    description: str
    original_code: str
    fixed_code: str
    confidence: float  # 0-1 之间的置信度
    reason: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FixReport:
    """修复报告"""
    original_sql: str
    fixed_sql: str
    suggestions: List[FixSuggestion]
    applied_fixes: List[FixSuggestion]
    confidence_score: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SQLAutoFixerTool(BaseTool):
    """SQL 自动修复工具"""
    
    def __init__(self, container: Any):
        """
        Args:
            container: 服务容器
        """
        super().__init__()

        self.name = "sql_auto_fixer"

        self.category = ToolCategory.SQL

        self.description = "自动修复 SQL 查询中的常见问题" 
        self.container = container
        
        # 使用 Pydantic 定义参数模式（args_schema）
        class SQLAutoFixerArgs(BaseModel):
            sql: str = Field(description="要修复的 SQL 查询")
            connection_config: Dict[str, Any] = Field(description="数据源连接配置")
            fix_types: Optional[List[Literal["syntax", "semantic", "performance", "style"]]] = Field(
                default=["syntax", "semantic", "performance"], description="要执行的修复类型"
            )
            auto_apply: bool = Field(default=False, description="是否自动应用修复")
            confidence_threshold: float = Field(default=0.8, description="自动应用修复的置信度阈值")
            schema_info: Optional[Dict[str, Any]] = Field(default=None, description="Schema 信息（可选）")

        self.args_schema = SQLAutoFixerArgs
        
        # 常见错误模式
        self.error_patterns = {
            "missing_from": r'SELECT\s+.*?(?=\s+WHERE|\s+GROUP|\s+ORDER|\s+HAVING|\s+LIMIT|$)',
            "missing_where": r'UPDATE\s+.*?(?=\s+SET)',
            "missing_set": r'UPDATE\s+.*?(?=\s+WHERE|$)',
            "missing_values": r'INSERT\s+INTO\s+.*?(?=\s+VALUES|\s+SELECT)',
            "unmatched_parentheses": r'\([^)]*$',
            "unmatched_quotes": r'"[^"]*$|\'[^\']*$',
            "trailing_comma": r',\s*(?:WHERE|GROUP|ORDER|HAVING|LIMIT|$)',
            "missing_comma": r'\w+\s+\w+(?=\s+FROM|\s+WHERE|\s+GROUP|\s+ORDER)',
        }
        
        # 修复规则
        self.fix_rules = {
            "add_missing_from": self._fix_missing_from,
            "add_missing_where": self._fix_missing_where,
            "add_missing_set": self._fix_missing_set,
            "add_missing_values": self._fix_missing_values,
            "fix_parentheses": self._fix_parentheses,
            "fix_quotes": self._fix_quotes,
            "remove_trailing_comma": self._fix_trailing_comma,
            "add_missing_comma": self._fix_missing_comma,
            "optimize_joins": self._optimize_joins,
            "add_limit": self._add_limit,
            "fix_case": self._fix_case,
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式（基于 args_schema 生成）"""
        try:
            parameters = self.args_schema.model_json_schema()
        except Exception:
            parameters = self.args_schema.schema()  # type: ignore[attr-defined]
        return {
            "type": "function",
            "function": {
                "name": "sql_auto_fixer",
                "description": "自动修复 SQL 查询中的常见问题",
                "parameters": parameters,
            },
        }
    
    async def run(

    
        self,
        sql: str,
        connection_config: Dict[str, Any],
        fix_types: Optional[List[str]] = None,
        auto_apply: bool = False,
        confidence_threshold: float = 0.8,
        schema_info: Optional[Dict[str, Any]] = None,
        **kwargs
    

    
    ) -> Dict[str, Any]:
        """
        执行 SQL 修复
        
        Args:
            sql: 要修复的 SQL 查询
            connection_config: 数据源连接配置
            fix_types: 要执行的修复类型
            auto_apply: 是否自动应用修复
            confidence_threshold: 自动应用修复的置信度阈值
            schema_info: Schema 信息
            
        Returns:
            Dict[str, Any]: 修复结果
        """
        logger.info(f"🔧 [SQLAutoFixerTool] 修复 SQL")
        logger.info(f"   修复类型: {fix_types}")

    
    async def execute(self, **kwargs) -> Dict[str, Any]:

    
        """向后兼容的execute方法"""

    
        return await self.run(**kwargs)
        logger.info(f"   自动应用: {auto_apply}")
        
        try:
            # 获取 Schema 信息
            if schema_info is None:
                schema_info = await self._get_schema_info(connection_config)
            
            # 设置默认修复类型
            if fix_types is None:
                fix_types = ["syntax", "semantic", "performance"]
            
            # 分析 SQL 并生成修复建议
            suggestions = await self._analyze_and_suggest_fixes(
                sql, schema_info, fix_types
            )
            
            # 应用修复
            applied_fixes = []
            fixed_sql = sql
            
            if auto_apply:
                for suggestion in suggestions:
                    if suggestion.confidence >= confidence_threshold and \
                       suggestion.fix_level == FixLevel.AUTOMATIC:
                        fixed_sql = self._apply_fix(fixed_sql, suggestion)
                        applied_fixes.append(suggestion)
            
            # 计算整体置信度
            confidence_score = self._calculate_confidence_score(suggestions)
            
            report = FixReport(
                original_sql=sql,
                fixed_sql=fixed_sql,
                suggestions=suggestions,
                applied_fixes=applied_fixes,
                confidence_score=confidence_score
            )
            
            return {
                "success": True,
                "report": report,
                "metadata": {
                    "fix_types": fix_types,
                    "auto_apply": auto_apply,
                    "confidence_threshold": confidence_threshold,
                    "suggestions_count": len(suggestions),
                    "applied_fixes_count": len(applied_fixes)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ [SQLAutoFixerTool] 修复失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "report": None
            }
    
    async def _get_schema_info(self, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取 Schema 信息"""
        try:
            from ..schema.retrieval import create_schema_retrieval_tool

            # 🔥 修复：传递 connection_config 以便工具能正确初始化
            retrieval_tool = create_schema_retrieval_tool(
                self.container,
                connection_config=connection_config
            )

            result = await retrieval_tool.run(
                include_relationships=True,
                include_constraints=True,
                format="detailed"
            )
            
            if result.get("success"):
                return result.get("result", {})
            else:
                logger.warning(f"⚠️ 获取 Schema 信息失败: {result.get('error')}")
                return {}
                
        except Exception as e:
            logger.warning(f"⚠️ 获取 Schema 信息失败: {e}")
            return {}
    
    async def _analyze_and_suggest_fixes(
        self,
        sql: str,
        schema_info: Dict[str, Any],
        fix_types: List[str]
    ) -> List[FixSuggestion]:
        """分析 SQL 并生成修复建议"""
        suggestions = []
        
        # 语法修复
        if "syntax" in fix_types:
            syntax_suggestions = self._suggest_syntax_fixes(sql)
            suggestions.extend(syntax_suggestions)
        
        # 语义修复
        if "semantic" in fix_types:
            semantic_suggestions = self._suggest_semantic_fixes(sql, schema_info)
            suggestions.extend(semantic_suggestions)
        
        # 性能修复
        if "performance" in fix_types:
            performance_suggestions = self._suggest_performance_fixes(sql, schema_info)
            suggestions.extend(performance_suggestions)
        
        # 风格修复
        if "style" in fix_types:
            style_suggestions = self._suggest_style_fixes(sql)
            suggestions.extend(style_suggestions)
        
        return suggestions
    
    def _suggest_syntax_fixes(self, sql: str) -> List[FixSuggestion]:
        """建议语法修复"""
        suggestions = []
        
        # 检查缺少 FROM 子句
        if re.search(r'SELECT\s+.*?(?=\s+WHERE|\s+GROUP|\s+ORDER|\s+HAVING|\s+LIMIT|$)', sql, re.IGNORECASE):
            if 'FROM' not in sql.upper():
                suggestions.append(FixSuggestion(
                    fix_type=FixType.SYNTAX,
                    fix_level=FixLevel.AUTOMATIC,
                    description="添加缺少的 FROM 子句",
                    original_code=sql,
                    fixed_code=self._fix_missing_from(sql),
                    confidence=0.9,
                    reason="SELECT 语句必须包含 FROM 子句"
                ))
        
        # 检查缺少 WHERE 子句（UPDATE）
        if sql.upper().startswith('UPDATE') and 'WHERE' not in sql.upper():
            suggestions.append(FixSuggestion(
                fix_type=FixType.SYNTAX,
                fix_level=FixLevel.SUGGESTION,
                description="添加 WHERE 子句以防止更新所有行",
                original_code=sql,
                fixed_code=self._fix_missing_where(sql),
                confidence=0.8,
                reason="UPDATE 语句应该包含 WHERE 子句以避免意外更新所有行"
            ))
        
        # 检查缺少 SET 子句（UPDATE）
        if sql.upper().startswith('UPDATE') and 'SET' not in sql.upper():
            suggestions.append(FixSuggestion(
                fix_type=FixType.SYNTAX,
                fix_level=FixLevel.AUTOMATIC,
                description="添加缺少的 SET 子句",
                original_code=sql,
                fixed_code=self._fix_missing_set(sql),
                confidence=0.9,
                reason="UPDATE 语句必须包含 SET 子句"
            ))
        
        # 检查缺少 VALUES 子句（INSERT）
        if sql.upper().startswith('INSERT') and 'VALUES' not in sql.upper() and 'SELECT' not in sql.upper():
            suggestions.append(FixSuggestion(
                fix_type=FixType.SYNTAX,
                fix_level=FixLevel.AUTOMATIC,
                description="添加缺少的 VALUES 子句",
                original_code=sql,
                fixed_code=self._fix_missing_values(sql),
                confidence=0.9,
                reason="INSERT 语句必须包含 VALUES 或 SELECT 子句"
            ))
        
        # 检查括号匹配
        if not self._check_parentheses(sql):
            suggestions.append(FixSuggestion(
                fix_type=FixType.SYNTAX,
                fix_level=FixLevel.AUTOMATIC,
                description="修复括号匹配",
                original_code=sql,
                fixed_code=self._fix_parentheses(sql),
                confidence=0.8,
                reason="括号不匹配会导致语法错误"
            ))
        
        # 检查引号匹配
        if not self._check_quotes(sql):
            suggestions.append(FixSuggestion(
                fix_type=FixType.SYNTAX,
                fix_level=FixLevel.AUTOMATIC,
                description="修复引号匹配",
                original_code=sql,
                fixed_code=self._fix_quotes(sql),
                confidence=0.8,
                reason="引号不匹配会导致语法错误"
            ))
        
        # 检查尾随逗号
        if re.search(r',\s*(?:WHERE|GROUP|ORDER|HAVING|LIMIT|$)', sql, re.IGNORECASE):
            suggestions.append(FixSuggestion(
                fix_type=FixType.SYNTAX,
                fix_level=FixLevel.AUTOMATIC,
                description="移除尾随逗号",
                original_code=sql,
                fixed_code=self._fix_trailing_comma(sql),
                confidence=0.9,
                reason="尾随逗号会导致语法错误"
            ))
        
        return suggestions
    
    def _suggest_semantic_fixes(self, sql: str, schema_info: Dict[str, Any]) -> List[FixSuggestion]:
        """建议语义修复"""
        suggestions = []
        
        # 检查表名
        table_names = self._extract_table_names(sql)
        available_tables = [table.get("name", "") for table in schema_info.get("tables", [])]
        
        for table_name in table_names:
            if table_name and table_name not in available_tables:
                # 查找相似的表名
                similar_tables = self._find_similar_names(table_name, available_tables)
                if similar_tables:
                    suggestions.append(FixSuggestion(
                        fix_type=FixType.SEMANTIC,
                        fix_level=FixLevel.SUGGESTION,
                        description=f"表 '{table_name}' 不存在",
                        original_code=sql,
                        fixed_code=sql.replace(table_name, similar_tables[0]),
                        confidence=0.7,
                        reason=f"表 '{table_name}' 不存在，建议使用: {', '.join(similar_tables[:3])}"
                    ))
        
        # 检查列名
        column_names = self._extract_column_names(sql)
        available_columns = schema_info.get("columns", [])
        
        for column_name in column_names:
            if column_name and not self._column_exists(column_name, available_columns):
                # 查找相似的列名
                similar_columns = self._find_similar_column_names(column_name, available_columns)
                if similar_columns:
                    suggestions.append(FixSuggestion(
                        fix_type=FixType.SEMANTIC,
                        fix_level=FixLevel.SUGGESTION,
                        description=f"列 '{column_name}' 不存在",
                        original_code=sql,
                        fixed_code=sql.replace(column_name, similar_columns[0]),
                        confidence=0.6,
                        reason=f"列 '{column_name}' 不存在，建议使用: {', '.join(similar_columns[:3])}"
                    ))
        
        return suggestions
    
    def _suggest_performance_fixes(self, sql: str, schema_info: Dict[str, Any]) -> List[FixSuggestion]:
        """建议性能修复"""
        suggestions = []
        
        sql_upper = sql.upper()
        
        # 检查是否有 LIMIT
        if "SELECT" in sql_upper and "LIMIT" not in sql_upper:
            suggestions.append(FixSuggestion(
                fix_type=FixType.PERFORMANCE,
                fix_level=FixLevel.SUGGESTION,
                description="添加 LIMIT 子句限制结果数量",
                original_code=sql,
                fixed_code=self._add_limit(sql),
                confidence=0.8,
                reason="添加 LIMIT 子句可以提高查询性能"
            ))
        
        # 检查是否有 WHERE 条件
        if "SELECT" in sql_upper and "WHERE" not in sql_upper and "JOIN" not in sql_upper:
            suggestions.append(FixSuggestion(
                fix_type=FixType.PERFORMANCE,
                fix_level=FixLevel.SUGGESTION,
                description="添加 WHERE 条件过滤数据",
                original_code=sql,
                fixed_code=sql + " WHERE condition",
                confidence=0.7,
                reason="添加适当的 WHERE 条件可以减少扫描的数据量"
            ))
        
        # 检查子查询
        if sql_upper.count("SELECT") > 1:
            suggestions.append(FixSuggestion(
                fix_type=FixType.PERFORMANCE,
                fix_level=FixLevel.SUGGESTION,
                description="考虑使用 JOIN 替代子查询",
                original_code=sql,
                fixed_code=sql,  # 这里需要更复杂的逻辑
                confidence=0.6,
                reason="JOIN 通常比子查询性能更好"
            ))
        
        return suggestions
    
    def _suggest_style_fixes(self, sql: str) -> List[FixSuggestion]:
        """建议风格修复"""
        suggestions = []
        
        # 检查关键字大小写
        if not self._is_keywords_uppercase(sql):
            suggestions.append(FixSuggestion(
                fix_type=FixType.STYLE,
                fix_level=FixLevel.AUTOMATIC,
                description="将 SQL 关键字转换为大写",
                original_code=sql,
                fixed_code=self._fix_case(sql),
                confidence=0.9,
                reason="SQL 关键字使用大写是良好的编程习惯"
            ))
        
        # 检查末尾分号
        if sql.strip().endswith(';'):
            suggestions.append(FixSuggestion(
                fix_type=FixType.STYLE,
                fix_level=FixLevel.AUTOMATIC,
                description="移除末尾的分号",
                original_code=sql,
                fixed_code=sql.rstrip().rstrip(';'),
                confidence=0.8,
                reason="在大多数情况下，末尾的分号是不必要的"
            ))
        
        return suggestions
    
    def _fix_missing_from(self, sql: str) -> str:
        """修复缺少的 FROM 子句"""
        # 简化实现，实际应该更智能
        return sql + " FROM table_name"
    
    def _fix_missing_where(self, sql: str) -> str:
        """修复缺少的 WHERE 子句"""
        return sql + " WHERE condition"
    
    def _fix_missing_set(self, sql: str) -> str:
        """修复缺少的 SET 子句"""
        return sql + " SET column = value"
    
    def _fix_missing_values(self, sql: str) -> str:
        """修复缺少的 VALUES 子句"""
        return sql + " VALUES (value1, value2, ...)"
    
    def _fix_parentheses(self, sql: str) -> str:
        """修复括号匹配"""
        # 简化实现
        open_count = sql.count('(')
        close_count = sql.count(')')
        
        if open_count > close_count:
            return sql + ')' * (open_count - close_count)
        elif close_count > open_count:
            return '(' * (close_count - open_count) + sql
        
        return sql
    
    def _fix_quotes(self, sql: str) -> str:
        """修复引号匹配"""
        # 简化实现
        single_quotes = sql.count("'")
        double_quotes = sql.count('"')
        
        if single_quotes % 2 == 1:
            sql += "'"
        if double_quotes % 2 == 1:
            sql += '"'
        
        return sql
    
    def _fix_trailing_comma(self, sql: str) -> str:
        """修复尾随逗号"""
        return re.sub(r',\s*(?:WHERE|GROUP|ORDER|HAVING|LIMIT|$)', r'\1', sql, flags=re.IGNORECASE)
    
    def _fix_missing_comma(self, sql: str) -> str:
        """修复缺少的逗号"""
        # 简化实现
        return sql
    
    def _optimize_joins(self, sql: str) -> str:
        """优化 JOIN"""
        # 简化实现
        return sql
    
    def _add_limit(self, sql: str) -> str:
        """添加 LIMIT 子句"""
        return sql + " LIMIT 100"
    
    def _fix_case(self, sql: str) -> str:
        """修复关键字大小写"""
        sql_keywords = [
            "SELECT", "FROM", "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT",
            "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP",
            "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN",
            "UNION", "UNION ALL", "INTERSECT", "EXCEPT",
            "AND", "OR", "NOT", "IN", "EXISTS", "BETWEEN", "LIKE", "IS NULL", "IS NOT NULL",
            "COUNT", "SUM", "AVG", "MIN", "MAX", "DISTINCT"
        ]
        
        result = sql
        for keyword in sql_keywords:
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            result = re.sub(pattern, keyword, result, flags=re.IGNORECASE)
        
        return result
    
    def _check_parentheses(self, sql: str) -> bool:
        """检查括号匹配"""
        stack = []
        for char in sql:
            if char == '(':
                stack.append(char)
            elif char == ')':
                if not stack:
                    return False
                stack.pop()
        return len(stack) == 0
    
    def _check_quotes(self, sql: str) -> bool:
        """检查引号匹配"""
        single_quotes = sql.count("'")
        double_quotes = sql.count('"')
        return single_quotes % 2 == 0 and double_quotes % 2 == 0
    
    def _is_keywords_uppercase(self, sql: str) -> bool:
        """检查关键字是否为大写"""
        sql_keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT"]
        for keyword in sql_keywords:
            if keyword.lower() in sql.lower() and keyword not in sql:
                return False
        return True
    
    def _extract_table_names(self, sql: str) -> List[str]:
        """提取表名"""
        table_names = []
        
        # FROM 子句
        from_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        from_matches = re.findall(from_pattern, sql, re.IGNORECASE)
        table_names.extend(from_matches)
        
        # JOIN 子句
        join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_matches = re.findall(join_pattern, sql, re.IGNORECASE)
        table_names.extend(join_matches)
        
        return list(set(table_names))
    
    def _extract_column_names(self, sql: str) -> List[str]:
        """提取列名"""
        column_names = []
        
        # SELECT 子句中的列
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        select_match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            columns = [col.strip() for col in select_clause.split(',')]
            for col in columns:
                if ' AS ' in col.upper():
                    col = col.split(' AS ')[0].strip()
                if '(' in col and ')' in col:
                    continue
                column_names.append(col)
        
        return list(set(column_names))
    
    def _column_exists(self, column_name: str, available_columns: List[Dict[str, Any]]) -> bool:
        """检查列是否存在"""
        for col in available_columns:
            if col.get("name", "").lower() == column_name.lower():
                return True
        return False
    
    def _find_similar_names(self, name: str, available_names: List[str]) -> List[str]:
        """查找相似名称"""
        similar = []
        name_lower = name.lower()
        
        for available_name in available_names:
            if name_lower in available_name.lower() or available_name.lower() in name_lower:
                similar.append(available_name)
        
        return similar[:5]  # 返回前5个相似名称
    
    def _find_similar_column_names(self, column_name: str, available_columns: List[Dict[str, Any]]) -> List[str]:
        """查找相似列名"""
        similar = []
        column_lower = column_name.lower()
        
        for col in available_columns:
            col_name = col.get("name", "").lower()
            if column_lower in col_name or col_name in column_lower:
                similar.append(col.get("name", ""))
        
        return similar[:5]  # 返回前5个相似列名
    
    def _apply_fix(self, sql: str, suggestion: FixSuggestion) -> str:
        """应用修复"""
        return suggestion.fixed_code
    
    def _calculate_confidence_score(self, suggestions: List[FixSuggestion]) -> float:
        """计算整体置信度"""
        if not suggestions:
            return 1.0
        
        total_confidence = sum(suggestion.confidence for suggestion in suggestions)
        return total_confidence / len(suggestions)


def create_sql_auto_fixer_tool(container: Any) -> SQLAutoFixerTool:
    """
    创建 SQL 自动修复工具
    
    Args:
        container: 服务容器
        
    Returns:
        SQLAutoFixerTool 实例
    """
    return SQLAutoFixerTool(container)


# 导出
__all__ = [
    "SQLAutoFixerTool",
    "FixType",
    "FixLevel",
    "FixSuggestion",
    "FixReport",
    "create_sql_auto_fixer_tool",
]