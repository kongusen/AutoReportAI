"""
Schema检查器服务

负责深度检查和分析数据库Schema结构、关系和优化机会
"""

import logging
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ColumnType(Enum):
    """列类型"""
    INTEGER = "integer"
    STRING = "string"
    DECIMAL = "decimal"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    UNKNOWN = "unknown"


class IndexType(Enum):
    """索引类型"""
    PRIMARY = "primary"
    UNIQUE = "unique"
    INDEX = "index"
    FULLTEXT = "fulltext"
    COMPOSITE = "composite"


class RelationType(Enum):
    """关系类型"""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"
    SELF_REFERENCE = "self_reference"


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    type: ColumnType
    nullable: bool
    default_value: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_table: Optional[str] = None
    foreign_column: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class IndexInfo:
    """索引信息"""
    name: str
    type: IndexType
    table: str
    columns: List[str]
    is_unique: bool = False
    size_estimate: Optional[int] = None
    cardinality: Optional[int] = None
    comment: Optional[str] = None


@dataclass
class RelationshipInfo:
    """关系信息"""
    name: str
    type: RelationType
    parent_table: str
    parent_column: str
    child_table: str
    child_column: str
    on_delete: Optional[str] = None
    on_update: Optional[str] = None


@dataclass
class TableInfo:
    """表信息"""
    name: str
    schema: str
    columns: List[ColumnInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    relationships: List[RelationshipInfo] = field(default_factory=list)
    row_count_estimate: int = 0
    size_estimate: int = 0  # KB
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class SchemaAnalysisResult:
    """Schema分析结果"""
    schema_name: str
    tables: List[TableInfo]
    overall_health_score: float
    complexity_score: float
    optimization_opportunities: List[str]
    potential_issues: List[str]
    statistics: Dict[str, Any]
    metadata: Dict[str, Any]


class SchemaInspectorService:
    """Schema检查器服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Schema分析规则
        self.analysis_rules = {
            "naming_conventions": {
                "table_patterns": [r"^[a-z][a-z0-9_]*$", r"^[A-Z][A-Za-z0-9]*$"],
                "column_patterns": [r"^[a-z][a-z0-9_]*$", r"^[a-z][a-zA-Z0-9]*$"],
                "index_patterns": [r"^idx_.*$", r"^ix_.*$", r"^index_.*$"]
            },
            "performance_thresholds": {
                "max_columns_per_table": 50,
                "max_indexes_per_table": 10,
                "max_table_size_mb": 1000,
                "min_index_cardinality": 10
            },
            "design_patterns": {
                "audit_columns": ["created_at", "updated_at", "deleted_at"],
                "common_fk_patterns": ["_id", "Id", "_key", "Key"],
                "reserved_words": ["order", "group", "select", "from", "where"]
            }
        }

    async def inspect_schema(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查和分析数据库Schema
        
        Args:
            schema_info: Schema信息
            
        Returns:
            Schema分析结果字典
        """
        try:
            schema_name = schema_info.get("schema_name", "default")
            self.logger.info(f"开始Schema检查: {schema_name}")
            
            # 解析表结构信息
            tables = self._parse_table_structures(schema_info)
            
            # 分析表关系
            relationships = self._analyze_relationships(tables)
            
            # 检查索引优化
            index_analysis = self._analyze_indexes(tables)
            
            # 评估Schema复杂度
            complexity_score = self._calculate_complexity_score(tables, relationships)
            
            # 分析命名规范
            naming_analysis = self._analyze_naming_conventions(tables)
            
            # 检查数据类型优化
            data_type_analysis = self._analyze_data_types(tables)
            
            # 识别性能瓶颈
            performance_issues = self._identify_performance_issues(tables, relationships)
            
            # 生成优化建议
            optimization_opportunities = self._generate_optimization_opportunities(
                tables, relationships, index_analysis, naming_analysis, 
                data_type_analysis, performance_issues
            )
            
            # 识别潜在问题
            potential_issues = self._identify_potential_issues(
                tables, relationships, naming_analysis, performance_issues
            )
            
            # 计算整体健康评分
            health_score = self._calculate_health_score(
                tables, complexity_score, len(optimization_opportunities), len(potential_issues)
            )
            
            # 生成统计信息
            statistics = self._generate_statistics(tables, relationships)
            
            result = {
                "schema_name": schema_name,
                "table_count": len(tables),
                "relationship_count": len(relationships),
                "complexity_score": complexity_score,
                "overall_health_score": health_score,
                "tables": [self._table_to_dict(table) for table in tables],
                "relationships": [self._relationship_to_dict(rel) for rel in relationships],
                "index_analysis": index_analysis,
                "naming_analysis": naming_analysis,
                "data_type_analysis": data_type_analysis,
                "performance_issues": performance_issues,
                "optimization_opportunities": optimization_opportunities,
                "potential_issues": potential_issues,
                "statistics": statistics,
                "inspection_complete": True,
                "metadata": {
                    "inspection_timestamp": datetime.now().isoformat(),
                    "rules_applied": len(self.analysis_rules),
                    "analysis_depth": "comprehensive",
                    "database_type": schema_info.get("database_type", "unknown")
                }
            }
            
            self.logger.info(
                f"Schema检查完成: 表={len(tables)}, 关系={len(relationships)}, "
                f"复杂度={complexity_score:.2f}, 健康评分={health_score:.2f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Schema检查失败: {e}")
            raise ValueError(f"Schema检查失败: {str(e)}")

    def _parse_table_structures(self, schema_info: Dict[str, Any]) -> List[TableInfo]:
        """解析表结构信息"""
        tables = []
        
        table_data = schema_info.get("tables", [])
        if isinstance(table_data, dict):
            # 如果tables是字典格式，转换为列表
            table_data = [{"name": k, **v} for k, v in table_data.items()]
        
        for table_dict in table_data:
            table = TableInfo(
                name=table_dict.get("name", "unnamed_table"),
                schema=schema_info.get("schema_name", "default"),
                row_count_estimate=table_dict.get("row_count", 0),
                size_estimate=table_dict.get("size_kb", 0),
                comment=table_dict.get("comment")
            )
            
            # 解析列信息
            columns_data = table_dict.get("columns", [])
            for col_dict in columns_data:
                column = ColumnInfo(
                    name=col_dict.get("name", "unnamed_column"),
                    type=self._parse_column_type(col_dict.get("type", "unknown")),
                    nullable=col_dict.get("nullable", True),
                    default_value=col_dict.get("default"),
                    max_length=col_dict.get("max_length"),
                    is_primary_key=col_dict.get("is_primary_key", False),
                    is_foreign_key=col_dict.get("is_foreign_key", False),
                    foreign_table=col_dict.get("foreign_table"),
                    foreign_column=col_dict.get("foreign_column"),
                    comment=col_dict.get("comment")
                )
                table.columns.append(column)
            
            # 解析索引信息
            indexes_data = table_dict.get("indexes", [])
            for idx_dict in indexes_data:
                index = IndexInfo(
                    name=idx_dict.get("name", "unnamed_index"),
                    type=self._parse_index_type(idx_dict.get("type", "index")),
                    table=table.name,
                    columns=idx_dict.get("columns", []),
                    is_unique=idx_dict.get("is_unique", False),
                    cardinality=idx_dict.get("cardinality"),
                    comment=idx_dict.get("comment")
                )
                table.indexes.append(index)
            
            tables.append(table)
        
        return tables

    def _parse_column_type(self, type_str: str) -> ColumnType:
        """解析列类型"""
        type_str = type_str.lower()
        
        if any(t in type_str for t in ["int", "integer", "bigint", "smallint", "tinyint"]):
            return ColumnType.INTEGER
        elif any(t in type_str for t in ["varchar", "char", "string"]):
            return ColumnType.STRING
        elif any(t in type_str for t in ["decimal", "numeric", "float", "double"]):
            return ColumnType.DECIMAL
        elif any(t in type_str for t in ["datetime", "timestamp", "date", "time"]):
            return ColumnType.DATETIME
        elif any(t in type_str for t in ["bool", "boolean"]):
            return ColumnType.BOOLEAN
        elif any(t in type_str for t in ["text", "longtext", "mediumtext"]):
            return ColumnType.TEXT
        elif "json" in type_str:
            return ColumnType.JSON
        elif any(t in type_str for t in ["blob", "binary", "varbinary"]):
            return ColumnType.BINARY
        else:
            return ColumnType.UNKNOWN

    def _parse_index_type(self, type_str: str) -> IndexType:
        """解析索引类型"""
        type_str = type_str.lower()
        
        if "primary" in type_str:
            return IndexType.PRIMARY
        elif "unique" in type_str:
            return IndexType.UNIQUE
        elif "fulltext" in type_str:
            return IndexType.FULLTEXT
        else:
            return IndexType.INDEX

    def _analyze_relationships(self, tables: List[TableInfo]) -> List[RelationshipInfo]:
        """分析表关系"""
        relationships = []
        
        for table in tables:
            for column in table.columns:
                if column.is_foreign_key and column.foreign_table:
                    # 确定关系类型
                    rel_type = self._determine_relationship_type(
                        table.name, column.name, 
                        column.foreign_table, column.foreign_column or "id"
                    )
                    
                    relationship = RelationshipInfo(
                        name=f"fk_{table.name}_{column.name}",
                        type=rel_type,
                        parent_table=column.foreign_table,
                        parent_column=column.foreign_column or "id",
                        child_table=table.name,
                        child_column=column.name
                    )
                    relationships.append(relationship)
        
        return relationships

    def _determine_relationship_type(
        self, 
        child_table: str, 
        child_column: str,
        parent_table: str, 
        parent_column: str
    ) -> RelationType:
        """确定关系类型"""
        
        # 自引用检查
        if child_table == parent_table:
            return RelationType.SELF_REFERENCE
        
        # 基于列名模式推断关系类型
        if child_column.endswith("_id") or child_column.endswith("Id"):
            if "user" in child_column.lower() or "owner" in child_column.lower():
                return RelationType.ONE_TO_MANY
        
        # 默认为一对多关系
        return RelationType.ONE_TO_MANY

    def _analyze_indexes(self, tables: List[TableInfo]) -> Dict[str, Any]:
        """分析索引"""
        total_indexes = 0
        primary_indexes = 0
        unique_indexes = 0
        composite_indexes = 0
        missing_indexes = []
        redundant_indexes = []
        
        for table in tables:
            total_indexes += len(table.indexes)
            
            # 统计索引类型
            for index in table.indexes:
                if index.type == IndexType.PRIMARY:
                    primary_indexes += 1
                elif index.type == IndexType.UNIQUE:
                    unique_indexes += 1
                
                if len(index.columns) > 1:
                    composite_indexes += 1
            
            # 检查缺失的索引
            fk_columns = [col for col in table.columns if col.is_foreign_key]
            indexed_columns = {col for idx in table.indexes for col in idx.columns}
            
            for fk_col in fk_columns:
                if fk_col.name not in indexed_columns:
                    missing_indexes.append({
                        "table": table.name,
                        "column": fk_col.name,
                        "reason": "外键列缺少索引"
                    })
            
            # 检查冗余索引（简化逻辑）
            single_column_indexes = [idx for idx in table.indexes if len(idx.columns) == 1]
            if len(single_column_indexes) > 5:  # 阈值检查
                redundant_indexes.append({
                    "table": table.name,
                    "reason": f"可能存在过多单列索引({len(single_column_indexes)}个)"
                })
        
        return {
            "total_indexes": total_indexes,
            "primary_indexes": primary_indexes,
            "unique_indexes": unique_indexes,
            "composite_indexes": composite_indexes,
            "missing_indexes": missing_indexes,
            "redundant_indexes": redundant_indexes,
            "average_indexes_per_table": total_indexes / len(tables) if tables else 0
        }

    def _calculate_complexity_score(
        self, 
        tables: List[TableInfo], 
        relationships: List[RelationshipInfo]
    ) -> float:
        """计算Schema复杂度评分"""
        
        if not tables:
            return 0.0
        
        # 基础复杂度：基于表数量
        table_complexity = min(len(tables) / 20.0, 1.0)
        
        # 列复杂度：基于平均列数
        total_columns = sum(len(table.columns) for table in tables)
        avg_columns = total_columns / len(tables)
        column_complexity = min(avg_columns / 15.0, 1.0)
        
        # 关系复杂度：基于关系数量
        relationship_complexity = min(len(relationships) / (len(tables) * 2), 1.0)
        
        # 索引复杂度：基于索引数量
        total_indexes = sum(len(table.indexes) for table in tables)
        index_complexity = min(total_indexes / (len(tables) * 3), 1.0)
        
        # 加权平均
        overall_complexity = (
            table_complexity * 0.25 +
            column_complexity * 0.3 +
            relationship_complexity * 0.25 +
            index_complexity * 0.2
        )
        
        return round(overall_complexity, 2)

    def _analyze_naming_conventions(self, tables: List[TableInfo]) -> Dict[str, Any]:
        """分析命名规范"""
        import re
        
        naming_issues = []
        naming_score = 1.0
        
        table_patterns = self.analysis_rules["naming_conventions"]["table_patterns"]
        column_patterns = self.analysis_rules["naming_conventions"]["column_patterns"]
        
        for table in tables:
            # 检查表名规范
            table_name_valid = any(re.match(pattern, table.name) for pattern in table_patterns)
            if not table_name_valid:
                naming_issues.append({
                    "type": "table_naming",
                    "table": table.name,
                    "issue": "表名不符合命名规范"
                })
                naming_score -= 0.1
            
            # 检查列名规范
            for column in table.columns:
                column_name_valid = any(re.match(pattern, column.name) for pattern in column_patterns)
                if not column_name_valid:
                    naming_issues.append({
                        "type": "column_naming",
                        "table": table.name,
                        "column": column.name,
                        "issue": "列名不符合命名规范"
                    })
                    naming_score -= 0.05
                
                # 检查保留字
                if column.name.lower() in self.analysis_rules["design_patterns"]["reserved_words"]:
                    naming_issues.append({
                        "type": "reserved_word",
                        "table": table.name,
                        "column": column.name,
                        "issue": "使用了SQL保留字"
                    })
                    naming_score -= 0.1
        
        return {
            "naming_score": max(naming_score, 0.0),
            "naming_issues": naming_issues,
            "tables_with_issues": len(set(issue.get("table") for issue in naming_issues)),
            "convention_compliance": len([t for t in tables if self._check_table_naming_compliance(t)]) / len(tables) if tables else 1.0
        }

    def _check_table_naming_compliance(self, table: TableInfo) -> bool:
        """检查表命名规范合规性"""
        import re
        patterns = self.analysis_rules["naming_conventions"]["table_patterns"]
        return any(re.match(pattern, table.name) for pattern in patterns)

    def _analyze_data_types(self, tables: List[TableInfo]) -> Dict[str, Any]:
        """分析数据类型优化"""
        type_suggestions = []
        type_distribution = {}
        
        for table in tables:
            for column in table.columns:
                # 统计数据类型分布
                type_key = column.type.value
                type_distribution[type_key] = type_distribution.get(type_key, 0) + 1
                
                # 检查数据类型优化机会
                if column.type == ColumnType.STRING and column.max_length:
                    if column.max_length > 1000:
                        type_suggestions.append({
                            "table": table.name,
                            "column": column.name,
                            "current_type": f"STRING({column.max_length})",
                            "suggestion": "考虑使用TEXT类型",
                            "reason": "字符串长度过长"
                        })
                
                elif column.type == ColumnType.UNKNOWN:
                    type_suggestions.append({
                        "table": table.name,
                        "column": column.name,
                        "current_type": "UNKNOWN",
                        "suggestion": "明确数据类型定义",
                        "reason": "数据类型未知"
                    })
        
        return {
            "type_distribution": type_distribution,
            "type_suggestions": type_suggestions,
            "unknown_types_count": type_distribution.get("unknown", 0),
            "optimization_potential": len(type_suggestions)
        }

    def _identify_performance_issues(
        self, 
        tables: List[TableInfo], 
        relationships: List[RelationshipInfo]
    ) -> List[Dict[str, Any]]:
        """识别性能问题"""
        issues = []
        
        thresholds = self.analysis_rules["performance_thresholds"]
        
        for table in tables:
            # 检查表列数
            if len(table.columns) > thresholds["max_columns_per_table"]:
                issues.append({
                    "type": "too_many_columns",
                    "table": table.name,
                    "current_value": len(table.columns),
                    "threshold": thresholds["max_columns_per_table"],
                    "severity": "medium",
                    "description": f"表 {table.name} 有 {len(table.columns)} 列，可能影响性能"
                })
            
            # 检查索引数量
            if len(table.indexes) > thresholds["max_indexes_per_table"]:
                issues.append({
                    "type": "too_many_indexes",
                    "table": table.name,
                    "current_value": len(table.indexes),
                    "threshold": thresholds["max_indexes_per_table"],
                    "severity": "low",
                    "description": f"表 {table.name} 有 {len(table.indexes)} 个索引，可能影响写入性能"
                })
            
            # 检查表大小
            if table.size_estimate > thresholds["max_table_size_mb"] * 1024:  # 转换为KB
                issues.append({
                    "type": "large_table",
                    "table": table.name,
                    "current_value": table.size_estimate,
                    "threshold": thresholds["max_table_size_mb"] * 1024,
                    "severity": "high",
                    "description": f"表 {table.name} 大小 {table.size_estimate/1024:.1f}MB，建议分区或归档"
                })
            
            # 检查缺少主键
            has_primary_key = any(col.is_primary_key for col in table.columns)
            if not has_primary_key:
                issues.append({
                    "type": "missing_primary_key",
                    "table": table.name,
                    "severity": "high",
                    "description": f"表 {table.name} 缺少主键"
                })
        
        return issues

    def _generate_optimization_opportunities(
        self,
        tables: List[TableInfo],
        relationships: List[RelationshipInfo],
        index_analysis: Dict[str, Any],
        naming_analysis: Dict[str, Any],
        data_type_analysis: Dict[str, Any],
        performance_issues: List[Dict[str, Any]]
    ) -> List[str]:
        """生成优化机会"""
        opportunities = []
        
        # 索引优化
        if index_analysis["missing_indexes"]:
            opportunities.append(f"为 {len(index_analysis['missing_indexes'])} 个外键列添加索引")
        
        if index_analysis["redundant_indexes"]:
            opportunities.append(f"检查并清理 {len(index_analysis['redundant_indexes'])} 个可能冗余的索引")
        
        # 命名规范优化
        if naming_analysis["naming_issues"]:
            opportunities.append(f"改善 {len(naming_analysis['naming_issues'])} 个命名规范问题")
        
        # 数据类型优化
        if data_type_analysis["type_suggestions"]:
            opportunities.append(f"优化 {len(data_type_analysis['type_suggestions'])} 个数据类型定义")
        
        # 性能优化
        high_severity_issues = [issue for issue in performance_issues if issue.get("severity") == "high"]
        if high_severity_issues:
            opportunities.append(f"解决 {len(high_severity_issues)} 个高优先级性能问题")
        
        # 关系优化
        if len(relationships) < len(tables) * 0.3:
            opportunities.append("考虑完善表间关系定义，提高数据一致性")
        
        # 审计字段
        tables_without_audit = [
            table for table in tables 
            if not any(col.name in self.analysis_rules["design_patterns"]["audit_columns"] 
                      for col in table.columns)
        ]
        if tables_without_audit and len(tables_without_audit) > len(tables) * 0.5:
            opportunities.append("考虑为主要业务表添加审计字段(created_at, updated_at)")
        
        return opportunities

    def _identify_potential_issues(
        self,
        tables: List[TableInfo],
        relationships: List[RelationshipInfo], 
        naming_analysis: Dict[str, Any],
        performance_issues: List[Dict[str, Any]]
    ) -> List[str]:
        """识别潜在问题"""
        issues = []
        
        # 性能问题
        critical_issues = [issue for issue in performance_issues if issue.get("severity") == "high"]
        if critical_issues:
            issues.extend([issue["description"] for issue in critical_issues])
        
        # 设计问题
        if len(relationships) == 0 and len(tables) > 1:
            issues.append("数据库中存在多个表但未定义任何关系，可能存在设计问题")
        
        # 命名问题
        if naming_analysis["naming_score"] < 0.7:
            issues.append("命名规范合规性较低，可能影响代码维护性")
        
        # 数据完整性
        tables_without_pk = [
            table for table in tables 
            if not any(col.is_primary_key for col in table.columns)
        ]
        if tables_without_pk:
            issues.append(f"{len(tables_without_pk)} 个表缺少主键，可能影响数据完整性")
        
        # 复杂度问题
        complex_tables = [
            table for table in tables 
            if len(table.columns) > 30 or len(table.indexes) > 8
        ]
        if complex_tables:
            issues.append(f"{len(complex_tables)} 个表结构复杂，建议考虑拆分")
        
        return issues

    def _calculate_health_score(
        self, 
        tables: List[TableInfo], 
        complexity_score: float,
        optimization_count: int, 
        issue_count: int
    ) -> float:
        """计算整体健康评分"""
        
        if not tables:
            return 0.0
        
        base_score = 1.0
        
        # 复杂度影响（复杂度越高，分数越低）
        complexity_penalty = complexity_score * 0.3
        
        # 优化机会影响
        optimization_penalty = min(optimization_count * 0.05, 0.3)
        
        # 问题影响
        issue_penalty = min(issue_count * 0.1, 0.4)
        
        # 表结构合理性加成
        avg_columns = sum(len(table.columns) for table in tables) / len(tables)
        if 5 <= avg_columns <= 15:  # 合理的列数范围
            base_score += 0.1
        
        # 索引合理性检查
        tables_with_indexes = [table for table in tables if table.indexes]
        if len(tables_with_indexes) / len(tables) > 0.8:  # 80%以上的表有索引
            base_score += 0.1
        
        health_score = base_score - complexity_penalty - optimization_penalty - issue_penalty
        
        return round(max(min(health_score, 1.0), 0.0), 2)

    def _generate_statistics(
        self, 
        tables: List[TableInfo], 
        relationships: List[RelationshipInfo]
    ) -> Dict[str, Any]:
        """生成统计信息"""
        
        if not tables:
            return {}
        
        # 基础统计
        total_columns = sum(len(table.columns) for table in tables)
        total_indexes = sum(len(table.indexes) for table in tables)
        total_size = sum(table.size_estimate for table in tables)
        
        # 列类型分布
        type_counts = {}
        for table in tables:
            for column in table.columns:
                type_key = column.type.value
                type_counts[type_key] = type_counts.get(type_key, 0) + 1
        
        # 索引类型分布
        index_type_counts = {}
        for table in tables:
            for index in table.indexes:
                type_key = index.type.value
                index_type_counts[type_key] = index_type_counts.get(type_key, 0) + 1
        
        return {
            "total_tables": len(tables),
            "total_columns": total_columns,
            "total_indexes": total_indexes,
            "total_relationships": len(relationships),
            "total_size_kb": total_size,
            "average_columns_per_table": round(total_columns / len(tables), 1),
            "average_indexes_per_table": round(total_indexes / len(tables), 1),
            "column_type_distribution": type_counts,
            "index_type_distribution": index_type_counts,
            "largest_table": max(tables, key=lambda t: t.size_estimate).name if tables else None,
            "most_complex_table": max(tables, key=lambda t: len(t.columns)).name if tables else None,
            "tables_with_relationships": len(set(
                rel.parent_table for rel in relationships
            ).union(set(rel.child_table for rel in relationships))),
            "relationship_density": len(relationships) / len(tables) if tables else 0
        }

    def _table_to_dict(self, table: TableInfo) -> Dict[str, Any]:
        """将TableInfo转换为字典"""
        return {
            "name": table.name,
            "schema": table.schema,
            "column_count": len(table.columns),
            "index_count": len(table.indexes),
            "relationship_count": len(table.relationships),
            "row_count_estimate": table.row_count_estimate,
            "size_estimate_kb": table.size_estimate,
            "comment": table.comment,
            "columns": [self._column_to_dict(col) for col in table.columns],
            "indexes": [self._index_to_dict(idx) for idx in table.indexes]
        }

    def _column_to_dict(self, column: ColumnInfo) -> Dict[str, Any]:
        """将ColumnInfo转换为字典"""
        return {
            "name": column.name,
            "type": column.type.value,
            "nullable": column.nullable,
            "default_value": column.default_value,
            "max_length": column.max_length,
            "is_primary_key": column.is_primary_key,
            "is_foreign_key": column.is_foreign_key,
            "foreign_table": column.foreign_table,
            "foreign_column": column.foreign_column,
            "comment": column.comment
        }

    def _index_to_dict(self, index: IndexInfo) -> Dict[str, Any]:
        """将IndexInfo转换为字典"""
        return {
            "name": index.name,
            "type": index.type.value,
            "columns": index.columns,
            "is_unique": index.is_unique,
            "cardinality": index.cardinality,
            "comment": index.comment
        }

    def _relationship_to_dict(self, relationship: RelationshipInfo) -> Dict[str, Any]:
        """将RelationshipInfo转换为字典"""
        return {
            "name": relationship.name,
            "type": relationship.type.value,
            "parent_table": relationship.parent_table,
            "parent_column": relationship.parent_column,
            "child_table": relationship.child_table,
            "child_column": relationship.child_column,
            "on_delete": relationship.on_delete,
            "on_update": relationship.on_update
        }

    def get_analysis_rules(self) -> Dict[str, Any]:
        """获取分析规则"""
        return self.analysis_rules.copy()

    def update_analysis_rules(self, new_rules: Dict[str, Any]) -> None:
        """更新分析规则"""
        for category, rules in new_rules.items():
            if category in self.analysis_rules:
                self.analysis_rules[category].update(rules)
            else:
                self.analysis_rules[category] = rules
        
        self.logger.info(f"分析规则已更新: {list(new_rules.keys())}")


# 全局实例
schema_inspector_service = SchemaInspectorService()