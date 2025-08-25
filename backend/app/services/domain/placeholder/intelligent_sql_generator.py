"""
智能SQL生成器

基于占位符语义分析结果，生成更准确和有意义的SQL查询
充分利用存储的表结构上下文信息
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from .semantic_analyzer import PlaceholderSemanticType, SemanticAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class SQLGenerationResult:
    """SQL生成结果"""

    sql: str
    confidence: float
    explanation: str
    parameters: Dict[str, Any]
    metadata: Dict[str, Any]
    suggestions: List[str]

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.metadata is None:
            self.metadata = {}
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class TableContext:
    """表上下文信息 - 增强版，充分利用存储的表结构信息"""

    table_name: str
    columns: List[Dict[str, Any]]
    business_category: Optional[str] = None
    estimated_rows: int = 0
    primary_keys: List[str] = None
    date_columns: List[str] = None

    # 新增：充分利用存储的表结构信息
    data_freshness: Optional[str] = None  # 数据新鲜度
    update_frequency: Optional[str] = None  # 更新频率
    data_quality_score: Optional[float] = None  # 数据质量评分
    completeness_rate: Optional[float] = None  # 完整率
    accuracy_rate: Optional[float] = None  # 准确率

    # 列级别的语义信息
    semantic_columns: Dict[str, List[str]] = None  # 按语义分类的列
    business_columns: Dict[str, List[str]] = None  # 按业务分类的列

    def __post_init__(self):
        if self.primary_keys is None:
            self.primary_keys = []
        if self.date_columns is None:
            self.date_columns = []
        if self.semantic_columns is None:
            self.semantic_columns = {}
        if self.business_columns is None:
            self.business_columns = {}


class IntelligentSQLGenerator:
    """智能SQL生成器 - 增强版"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._init_templates()
        self._init_semantic_patterns()

    def _init_templates(self):
        """初始化SQL模板"""

        # 时间相关SQL模板
        self.temporal_templates = {
            "start_date": {
                "parameter": "SELECT '{start_date}' as period_start_date",
                "from_config": "SELECT start_date FROM reporting_config WHERE period_name = '{period_name}'",
                "calculated": "SELECT DATE_SUB(CURDATE(), INTERVAL {days} DAY) as start_date",
            },
            "end_date": {
                "parameter": "SELECT '{end_date}' as period_end_date",
                "from_config": "SELECT end_date FROM reporting_config WHERE period_name = '{period_name}'",
                "calculated": "SELECT CURDATE() as end_date",
            },
            "year": {
                "current": "SELECT YEAR(CURDATE()) as current_year",
                "from_date": "SELECT YEAR(date_column) as year FROM {table}",
                "parameter": "SELECT {year} as year",
            },
            "month": {
                "current": "SELECT MONTH(CURDATE()) as current_month",
                "from_date": "SELECT MONTH(date_column) as month FROM {table}",
                "parameter": "SELECT {month} as month",
            },
        }

        # 统计相关SQL模板
        self.statistical_templates = {
            "count": "SELECT COUNT(*) as total_count FROM {table} {where_clause}",
            "sum": "SELECT SUM({column}) as total_sum FROM {table} {where_clause}",
            "average": "SELECT AVG({column}) as average_value FROM {table} {where_clause}",
            "percentage": """
                SELECT 
                    (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table})) as percentage
                FROM {table} {where_clause}
            """,
        }

    def _init_semantic_patterns(self):
        """初始化语义模式匹配"""

        # 语义分类到业务含义的映射
        self.semantic_mappings = {
            "id": {
                "keywords": ["id", "id_card", "identity", "cert_no", "user_id", "customer_id"],
                "business_meaning": "唯一标识符",
                "sql_hint": "DISTINCT",
            },
            "name": {
                "keywords": ["name", "title", "label", "description"],
                "business_meaning": "名称描述",
                "sql_hint": "GROUP BY",
            },
            "time": {
                "keywords": ["date", "time", "dt", "created", "updated", "timestamp"],
                "business_meaning": "时间信息",
                "sql_hint": "DATE_FORMAT",
            },
            "amount": {
                "keywords": ["amount", "money", "price", "cost", "fee", "total"],
                "business_meaning": "金额数值",
                "sql_hint": "SUM/AVG",
            },
            "count": {
                "keywords": ["count", "number", "quantity", "qty"],
                "business_meaning": "数量统计",
                "sql_hint": "COUNT",
            },
            "region": {
                "keywords": ["region", "area", "city", "province", "country"],
                "business_meaning": "地区信息",
                "sql_hint": "DISTINCT",
            },
            "status": {
                "keywords": ["status", "state", "flag", "type"],
                "business_meaning": "状态标识",
                "sql_hint": "GROUP BY",
            },
        }

    def generate_sql(
        self,
        semantic_result: SemanticAnalysisResult,
        table_context: TableContext,
        placeholder_name: str = "",
        additional_context: Dict[str, Any] = None,
    ) -> SQLGenerationResult:
        """根据语义分析结果生成SQL - 增强版"""

        self.logger.debug(f"开始生成SQL: {placeholder_name}, 类型: {semantic_result.primary_type}")

        additional_context = additional_context or {}

        # 预处理表上下文，提取语义信息
        self._enhance_table_context(table_context)

        # 根据主要类型选择生成策略
        if semantic_result.primary_type == PlaceholderSemanticType.TEMPORAL:
            return self._generate_temporal_sql(semantic_result, table_context, placeholder_name, additional_context)
        elif semantic_result.primary_type == PlaceholderSemanticType.STATISTICAL:
            return self._generate_statistical_sql(semantic_result, table_context, placeholder_name, additional_context)
        elif semantic_result.primary_type == PlaceholderSemanticType.DIMENSIONAL:
            return self._generate_dimensional_sql(semantic_result, table_context, placeholder_name, additional_context)
        else:
            return self._generate_fallback_sql(semantic_result, table_context, placeholder_name, additional_context)

    def _enhance_table_context(self, table_context: TableContext):
        """增强表上下文信息，提取语义分类"""

        # 按语义分类组织列
        for col in table_context.columns:
            col_name = col.get("name", "").lower()
            semantic_category = col.get("semantic_category", "")
            business_name = col.get("business_name", "")

            # 根据语义分类分组（安全处理None值）
            if semantic_category:
                semantic_category_lower = semantic_category.lower()
                if semantic_category_lower not in table_context.semantic_columns:
                    table_context.semantic_columns[semantic_category_lower] = []
                table_context.semantic_columns[semantic_category_lower].append(col["name"])

            # 根据业务名称分组
            if business_name:
                if business_name not in table_context.business_columns:
                    table_context.business_columns[business_name] = []
                table_context.business_columns[business_name].append(col["name"])

            # 智能识别语义分类
            for semantic_type, pattern in self.semantic_mappings.items():
                if any(keyword in col_name for keyword in pattern["keywords"]):
                    if semantic_type not in table_context.semantic_columns:
                        table_context.semantic_columns[semantic_type] = []
                    table_context.semantic_columns[semantic_type].append(col["name"])

    def _generate_temporal_sql(
        self,
        semantic_result: SemanticAnalysisResult,
        table_context: TableContext,
        placeholder_name: str,
        additional_context: Dict[str, Any],
    ) -> SQLGenerationResult:
        """生成时间相关SQL - 增强版"""

        sub_type = semantic_result.sub_type
        confidence = 0.8
        parameters = {}
        suggestions = []

        # 优先使用存储的语义分类信息
        time_columns = table_context.semantic_columns.get("time", [])
        if not time_columns and table_context.date_columns:
            time_columns = table_context.date_columns

        # 根据子类型生成不同的SQL
        if sub_type == "start_date":
            if time_columns:
                # 使用表中的时间列获取开始日期
                time_col = time_columns[0]
                sql = f"SELECT MIN({time_col}) as start_date FROM {table_context.table_name}"
                explanation = f"从表 {table_context.table_name} 的 {time_col} 列获取最早日期作为开始日期"
                confidence = 0.9
            else:
                # 参数化方式
                sql = "SELECT '{period_start_date}' as start_date"
                parameters = {"period_start_date": "统计周期开始日期参数，格式：YYYY-MM-DD"}
                explanation = "获取统计周期的开始日期，通过参数传入具体日期值"
                confidence = 0.7

            suggestions = ["建议在ETL流程中设置具体的开始日期参数", "可以考虑从配置表中读取周期配置信息"]

        elif sub_type == "end_date":
            if time_columns:
                # 使用表中的时间列获取结束日期
                time_col = time_columns[0]
                sql = f"SELECT MAX({time_col}) as end_date FROM {table_context.table_name}"
                explanation = f"从表 {table_context.table_name} 的 {time_col} 列获取最晚日期作为结束日期"
                confidence = 0.9
            else:
                sql = "SELECT '{period_end_date}' as end_date"
                parameters = {"period_end_date": "统计周期结束日期参数，格式：YYYY-MM-DD"}
                explanation = "获取统计周期的结束日期，通过参数传入具体日期值"
                confidence = 0.7

            suggestions = ["建议在ETL流程中设置具体的结束日期参数", "可以考虑使用当前日期作为默认结束日期"]

        elif sub_type == "year":
            if time_columns:
                time_col = time_columns[0]
                sql = f"SELECT YEAR({time_col}) as year FROM {table_context.table_name} LIMIT 1"
                explanation = f"从表 {table_context.table_name} 的 {time_col} 列提取年份"
                confidence = 0.8
            else:
                sql = "SELECT YEAR(CURDATE()) as current_year"
                explanation = "获取当前年份"
                confidence = 0.6

        elif sub_type == "month":
            if time_columns:
                time_col = time_columns[0]
                sql = f"SELECT MONTH({time_col}) as month FROM {table_context.table_name} LIMIT 1"
                explanation = f"从表 {table_context.table_name} 的 {time_col} 列提取月份"
                confidence = 0.8
            else:
                sql = "SELECT MONTH(CURDATE()) as current_month"
                explanation = "获取当前月份"
                confidence = 0.6

        else:
            # 通用时间查询
            if time_columns:
                time_col = time_columns[0]
                sql = f"SELECT {time_col} FROM {table_context.table_name} ORDER BY {time_col} DESC LIMIT 1"
                explanation = f"获取表 {table_context.table_name} 的最新时间"
                confidence = 0.7
            else:
                sql = f"SELECT DATE(NOW()) as current_date"
                explanation = "获取当前日期"
                confidence = 0.5

        # 根据数据质量信息调整建议
        if table_context.data_quality_score and table_context.data_quality_score < 0.8:
            suggestions.append(f"数据质量评分较低({table_context.data_quality_score:.2f})，建议检查数据完整性")

        if table_context.completeness_rate and table_context.completeness_rate < 0.9:
            suggestions.append(f"数据完整率较低({table_context.completeness_rate:.2f})，建议处理缺失值")

        metadata = {
            "semantic_type": semantic_result.primary_type.value,
            "sub_type": sub_type,
            "table_used": table_context.table_name,
            "time_columns_available": time_columns,
            "data_quality_score": table_context.data_quality_score,
            "completeness_rate": table_context.completeness_rate,
            "business_category": table_context.business_category,
        }

        return SQLGenerationResult(
            sql=sql,
            confidence=confidence,
            explanation=explanation,
            parameters=parameters,
            metadata=metadata,
            suggestions=suggestions,
        )

    def _generate_statistical_sql(
        self,
        semantic_result: SemanticAnalysisResult,
        table_context: TableContext,
        placeholder_name: str,
        additional_context: Dict[str, Any],
    ) -> SQLGenerationResult:
        """生成统计相关SQL - 增强版"""

        sub_type = semantic_result.sub_type or "count"
        table_name = table_context.table_name

        # 构建WHERE子句
        where_clause = self._build_where_clause(table_context, additional_context)

        # 根据子类型选择SQL模板
        if sub_type == "count":
            if "去重" in placeholder_name or "distinct" in placeholder_name.lower():
                # 优先使用语义分类的ID字段
                id_columns = table_context.semantic_columns.get("id", [])
                if not id_columns:
                    id_columns = table_context.semantic_columns.get("identifier", [])

                distinct_column = id_columns[0] if id_columns else self._find_distinct_column(table_context)

                if distinct_column:
                    sql = f"SELECT COUNT(DISTINCT {distinct_column}) as distinct_count FROM {table_name}{where_clause}"
                    explanation = f"计算表 {table_name} 中 {distinct_column} 字段的去重数量"
                    confidence = 0.9
                else:
                    sql = f"SELECT COUNT(*) as total_count FROM {table_name}{where_clause}"
                    explanation = f"计算表 {table_name} 的总记录数（未找到合适的去重字段）"
                    confidence = 0.7
            else:
                sql = f"SELECT COUNT(*) as total_count FROM {table_name}{where_clause}"
                explanation = f"计算表 {table_name} 的总记录数"
                confidence = 0.9

        elif sub_type == "sum":
            # 优先使用语义分类的金额字段
            amount_columns = table_context.semantic_columns.get("amount", [])
            numeric_column = amount_columns[0] if amount_columns else self._find_numeric_column(table_context)

            if numeric_column:
                sql = f"SELECT SUM({numeric_column}) as total_sum FROM {table_name}{where_clause}"
                explanation = f"计算表 {table_name} 中 {numeric_column} 字段的总和"
                confidence = 0.8
            else:
                sql = f"SELECT COUNT(*) as total_count FROM {table_name}{where_clause}"
                explanation = f"未找到数值列，改为统计记录数"
                confidence = 0.6

        elif sub_type == "average":
            # 优先使用语义分类的金额字段
            amount_columns = table_context.semantic_columns.get("amount", [])
            numeric_column = amount_columns[0] if amount_columns else self._find_numeric_column(table_context)

            if numeric_column:
                sql = f"SELECT AVG({numeric_column}) as average_value FROM {table_name}{where_clause}"
                explanation = f"计算表 {table_name} 中 {numeric_column} 字段的平均值"
                confidence = 0.8
            else:
                sql = f"SELECT COUNT(*) as total_count FROM {table_name}{where_clause}"
                explanation = f"未找到数值列，改为统计记录数"
                confidence = 0.6

        else:
            sql = f"SELECT COUNT(*) as total_count FROM {table_name}{where_clause}"
            explanation = f"执行基础计数统计"
            confidence = 0.7

        parameters = {}
        if "{region}" in sql:
            parameters["region"] = "地区过滤参数"
        if "{year}" in sql:
            parameters["year"] = "年份过滤参数"

        suggestions = []
        if not where_clause:
            suggestions.append("建议添加时间范围过滤以提高查询性能")

        # 根据表大小和数据质量提供建议
        if table_context.estimated_rows > 1000000:
            suggestions.append("大表查询，建议添加索引或分区过滤")

        if table_context.data_quality_score and table_context.data_quality_score < 0.8:
            suggestions.append(f"数据质量评分较低({table_context.data_quality_score:.2f})，建议验证统计结果")

        if table_context.update_frequency:
            suggestions.append(f"数据更新频率: {table_context.update_frequency}")

        metadata = {
            "semantic_type": semantic_result.primary_type.value,
            "sub_type": sub_type,
            "table_used": table_name,
            "where_clause": where_clause,
            "estimated_rows": table_context.estimated_rows,
            "data_quality_score": table_context.data_quality_score,
            "business_category": table_context.business_category,
            "semantic_columns_used": table_context.semantic_columns,
        }

        return SQLGenerationResult(
            sql=sql,
            confidence=confidence,
            explanation=explanation,
            parameters=parameters,
            metadata=metadata,
            suggestions=suggestions,
        )

    def _generate_dimensional_sql(
        self,
        semantic_result: SemanticAnalysisResult,
        table_context: TableContext,
        placeholder_name: str,
        additional_context: Dict[str, Any],
    ) -> SQLGenerationResult:
        """生成维度相关SQL - 增强版"""

        sub_type = semantic_result.sub_type
        table_name = table_context.table_name

        if sub_type == "region":
            # 优先使用语义分类的地区字段
            region_columns = table_context.semantic_columns.get("region", [])
            region_column = region_columns[0] if region_columns else self._find_region_column(table_context)

            if region_column:
                sql = f"SELECT DISTINCT {region_column} as region_name FROM {table_name} ORDER BY {region_column}"
                explanation = f"获取表 {table_name} 中所有不同的地区"
                confidence = 0.8
            else:
                sql = f"SELECT '未指定地区' as region_name"
                explanation = "未找到地区相关字段，返回默认值"
                confidence = 0.3

        elif sub_type == "category":
            # 优先使用语义分类的状态字段
            status_columns = table_context.semantic_columns.get("status", [])
            category_column = status_columns[0] if status_columns else self._find_category_column(table_context)

            if category_column:
                sql = f"SELECT DISTINCT {category_column} as category_name FROM {table_name} ORDER BY {category_column}"
                explanation = f"获取表 {table_name} 中所有不同的分类"
                confidence = 0.8
            else:
                sql = f"SELECT '未指定分类' as category_name"
                explanation = "未找到分类相关字段，返回默认值"
                confidence = 0.3
        else:
            # 通用维度查询
            sql = f"SELECT * FROM {table_name} LIMIT 1"
            explanation = f"获取表 {table_name} 的示例数据"
            confidence = 0.5

        metadata = {
            "semantic_type": semantic_result.primary_type.value,
            "sub_type": sub_type,
            "table_used": table_name,
            "available_columns": [col["name"] for col in table_context.columns],
            "semantic_columns": table_context.semantic_columns,
            "business_category": table_context.business_category,
        }

        return SQLGenerationResult(
            sql=sql, confidence=confidence, explanation=explanation, parameters={}, metadata=metadata, suggestions=[]
        )

    def _generate_fallback_sql(
        self,
        semantic_result: SemanticAnalysisResult,
        table_context: TableContext,
        placeholder_name: str,
        additional_context: Dict[str, Any],
    ) -> SQLGenerationResult:
        """生成回退SQL - 增强版"""

        table_name = table_context.table_name

        # 基于占位符名称的简单推测
        if "数量" in placeholder_name or "count" in placeholder_name.lower():
            sql = f"SELECT COUNT(*) as total_count FROM {table_name}"
            explanation = "基于占位符名称推测，执行计数查询"
            confidence = 0.6
        elif "日期" in placeholder_name or "date" in placeholder_name.lower():
            time_columns = table_context.semantic_columns.get("time", [])
            if time_columns:
                time_col = time_columns[0]
                sql = f"SELECT {time_col} FROM {table_name} ORDER BY {time_col} DESC LIMIT 1"
                explanation = f"获取最新的日期值"
                confidence = 0.7
            else:
                sql = "SELECT CURDATE() as current_date"
                explanation = "未找到日期字段，返回当前日期"
                confidence = 0.4
        else:
            sql = f"SELECT COUNT(*) as total_count FROM {table_name}"
            explanation = "执行默认的计数查询"
            confidence = 0.3

        metadata = {
            "semantic_type": semantic_result.primary_type.value,
            "fallback_reason": "未能准确识别占位符类型",
            "table_used": table_name,
            "business_category": table_context.business_category,
            "available_semantic_columns": table_context.semantic_columns,
        }

        return SQLGenerationResult(
            sql=sql,
            confidence=confidence,
            explanation=explanation,
            parameters={},
            metadata=metadata,
            suggestions=["建议优化占位符命名以提高识别准确度"],
        )

    def _build_where_clause(self, table_context: TableContext, additional_context: Dict[str, Any]) -> str:
        """构建WHERE子句 - 增强版"""

        where_conditions = []

        # 检查是否需要地区过滤
        region_columns = table_context.semantic_columns.get("region", [])
        region_column = region_columns[0] if region_columns else self._find_region_column(table_context)
        if region_column and additional_context.get("filter_by_region"):
            where_conditions.append(f"{region_column} = '{{region}}'")

        # 检查是否需要时间过滤
        time_columns = table_context.semantic_columns.get("time", [])
        date_column = (
            time_columns[0] if time_columns else (table_context.date_columns[0] if table_context.date_columns else None)
        )
        if date_column and additional_context.get("filter_by_time"):
            where_conditions.append(f"{date_column} >= '{{start_date}}' AND {date_column} <= '{{end_date}}'")

        if where_conditions:
            return " WHERE " + " AND ".join(where_conditions)

        return ""

    def _find_distinct_column(self, table_context: TableContext) -> Optional[str]:
        """查找合适的去重字段 - 增强版"""

        # 优先使用语义分类的ID字段
        id_columns = table_context.semantic_columns.get("id", [])
        if id_columns:
            return id_columns[0]

        # 其次查找主键
        if table_context.primary_keys:
            return table_context.primary_keys[0]

        # 最后查找包含id的字段
        for col in table_context.columns:
            col_name = col.get("name", "").lower()
            if "id" in col_name:
                return col["name"]

        return None

    def _find_numeric_column(self, table_context: TableContext) -> Optional[str]:
        """查找数值类型字段 - 增强版"""

        # 优先使用语义分类的金额字段
        amount_columns = table_context.semantic_columns.get("amount", [])
        if amount_columns:
            return amount_columns[0]

        numeric_types = ["int", "integer", "bigint", "decimal", "float", "double", "numeric", "number"]

        for col in table_context.columns:
            col_type = col.get("type", "").lower()
            if any(num_type in col_type for num_type in numeric_types):
                return col["name"]

        return None

    def _find_region_column(self, table_context: TableContext) -> Optional[str]:
        """查找地区相关字段 - 增强版"""

        # 优先使用语义分类的地区字段
        region_columns = table_context.semantic_columns.get("region", [])
        if region_columns:
            return region_columns[0]

        region_keywords = ["region", "area", "city", "province", "county", "district", "地区", "区域", "城市", "省份"]

        for col in table_context.columns:
            col_name = col.get("name", "").lower()
            if any(keyword in col_name for keyword in region_keywords):
                return col["name"]

        return None

    def _find_category_column(self, table_context: TableContext) -> Optional[str]:
        """查找分类相关字段 - 增强版"""

        # 优先使用语义分类的状态字段
        status_columns = table_context.semantic_columns.get("status", [])
        if status_columns:
            return status_columns[0]

        category_keywords = ["category", "type", "class", "kind", "分类", "类别", "种类"]

        for col in table_context.columns:
            col_name = col.get("name", "").lower()
            if any(keyword in col_name for keyword in category_keywords):
                return col["name"]

        return None


def create_intelligent_sql_generator() -> IntelligentSQLGenerator:
    """创建智能SQL生成器实例"""
    return IntelligentSQLGenerator()
