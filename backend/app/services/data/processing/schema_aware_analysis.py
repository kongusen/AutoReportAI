"""
基于表结构的智能数据分析服务
利用表结构信息进行更智能的数据分析和处理
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.models.table_schema import TableSchema, ColumnSchema, ColumnType
# Lazy import to avoid circular dependency
# from app.services.data.schemas import SchemaQueryService, SchemaAnalysisService
from .analysis import DataAnalysisService


class SchemaAwareAnalysisService:
    """基于表结构的智能数据分析服务"""
    
    def __init__(self, db_session: Session = None):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        # Lazy initialization to avoid circular imports
        self._schema_query_service = None
        self._schema_analysis_service = None
        if db_session:
            self.data_analysis_service = DataAnalysisService(db_session)
        else:
            self.data_analysis_service = None
    
    async def _get_ai_facade(self):
        """获取统一AI门面实例"""
        if not hasattr(self, '_ai_facade') or self._ai_facade is None:
            # Unified AI facade migrated to agents
            from app.services.infrastructure.agents import execute_agent_task
            self._ai_facade = execute_agent_task
        return self._ai_facade
    
    @property
    def schema_query_service(self):
        """React Agent架构的Schema查询服务"""
        if self._schema_query_service is None:
            from app.services.data.schemas import SchemaQueryService
            self._schema_query_service = SchemaQueryService(self.db_session)
        return self._schema_query_service
    
    async def get_schema_analysis_service(self, table_names=None):
        """获取Schema分析服务 - 基于ServiceOrchestrator实现"""
        try:
            # 使用统一AI门面进行Schema分析
            ai_facade = await self._get_ai_facade()
            
            # 构建Schema数据
            schema_data = {
                "table_names": table_names or [],
                "analysis_scope": "all" if not table_names else "selected",
                "user_id": getattr(self, 'user_id', 'system')
            }
            
            # 使用Schema分析服务
            result = await ai_facade.analyze_schema(
                user_id=schema_data["user_id"],
                schema_data=schema_data,
                analysis_depth="standard"
            )
            
            return result.get("result", "") if isinstance(result, dict) else str(result)
        except Exception as e:
            self.logger.error(f"Schema分析失败: {str(e)}")
            return f"Schema分析暂时不可用: {str(e)}"
    
    async def analyze_data_source_with_schema(self, data_source_id: str) -> Dict[str, Any]:
        """
        基于表结构信息分析数据源
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            分析结果
        """
        try:
            # 获取表结构信息
            table_schemas = self.schema_query_service.get_table_schemas(data_source_id)
            
            if not table_schemas:
                return {"success": False, "error": "未找到表结构信息，请先进行表结构发现"}
            
            # 执行基础数据分析
            basic_analysis = self.data_analysis_service.analyze(data_source_id)
            
            # 执行表结构分析
            schema_analysis = await self._analyze_schema_structure(table_schemas)
            
            # 执行业务语义分析
            semantic_analysis = await self.schema_analysis_service.analyze_business_semantics(data_source_id)
            
            # 执行数据质量分析
            quality_analysis = await self.schema_analysis_service.analyze_data_quality(data_source_id)
            
            # 生成智能建议
            recommendations = self._generate_intelligent_recommendations(
                basic_analysis, schema_analysis, semantic_analysis, quality_analysis
            )
            
            return {
                "success": True,
                "basic_analysis": basic_analysis,
                "schema_analysis": schema_analysis,
                "semantic_analysis": semantic_analysis,
                "quality_analysis": quality_analysis,
                "recommendations": recommendations
            }
            
        except Exception as e:
            self.logger.error(f"基于表结构的数据分析失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_schema_structure(self, table_schemas: List[TableSchema]) -> Dict[str, Any]:
        """分析表结构特征"""
        
        analysis_result = {
            "total_tables": len(table_schemas),
            "table_types": {},
            "column_distribution": {},
            "data_type_distribution": {},
            "relationship_analysis": {},
            "complexity_score": 0.0
        }
        
        total_columns = 0
        data_type_counts = {}
        
        for table_schema in table_schemas:
            # 获取表的列信息
            columns = self.schema_query_service.get_table_columns(str(table_schema.id))
            total_columns += len(columns)
            
            # 统计数据类型分布
            for column in columns:
                data_type = column.normalized_type.value
                data_type_counts[data_type] = data_type_counts.get(data_type, 0) + 1
            
            # 分析表复杂度
            complexity_score = self._calculate_table_complexity(table_schema, columns)
            analysis_result["complexity_score"] += complexity_score
        
        # 计算平均复杂度
        if table_schemas:
            analysis_result["complexity_score"] /= len(table_schemas)
        
        # 数据类型分布
        analysis_result["data_type_distribution"] = data_type_counts
        analysis_result["total_columns"] = total_columns
        
        # 分析表关系
        analysis_result["relationship_analysis"] = await self._analyze_table_relationships(table_schemas)
        
        return analysis_result
    
    def _calculate_table_complexity(self, table_schema: TableSchema, columns: List[ColumnSchema]) -> float:
        """计算表复杂度分数"""
        
        complexity_score = 0.0
        
        # 基于列数量
        column_count = len(columns)
        if column_count > 50:
            complexity_score += 30
        elif column_count > 20:
            complexity_score += 20
        elif column_count > 10:
            complexity_score += 10
        
        # 基于数据类型多样性
        data_types = set(col.normalized_type for col in columns)
        complexity_score += len(data_types) * 5
        
        # 基于主键和索引
        primary_keys = sum(1 for col in columns if col.is_primary_key)
        indexed_columns = sum(1 for col in columns if col.is_indexed)
        complexity_score += (primary_keys + indexed_columns) * 3
        
        # 基于表大小
        if table_schema.estimated_row_count:
            if table_schema.estimated_row_count > 1000000:
                complexity_score += 20
            elif table_schema.estimated_row_count > 100000:
                complexity_score += 15
            elif table_schema.estimated_row_count > 10000:
                complexity_score += 10
        
        return min(complexity_score, 100.0)
    
    async def _analyze_table_relationships(self, table_schemas: List[TableSchema]) -> Dict[str, Any]:
        """分析表关系"""
        
        # 获取表关系
        relationships = []
        for table_schema in table_schemas:
            related_tables = self.schema_query_service.get_related_tables(str(table_schema.id))
            relationships.extend(related_tables)
        
        return {
            "total_relationships": len(relationships),
            "relationship_types": self._count_relationship_types(relationships),
            "most_connected_tables": self._find_most_connected_tables(relationships, table_schemas)
        }
    
    def _count_relationship_types(self, relationships: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计关系类型"""
        
        type_counts = {}
        for rel in relationships:
            rel_type = rel.get("relationship_type", "unknown")
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
        
        return type_counts
    
    def _find_most_connected_tables(self, relationships: List[Dict[str, Any]], table_schemas: List[TableSchema]) -> List[Dict[str, Any]]:
        """查找连接最多的表"""
        
        table_connections = {}
        
        # 统计每个表的连接数
        for rel in relationships:
            table_id = rel.get("table_id")
            if table_id:
                table_connections[table_id] = table_connections.get(table_id, 0) + 1
        
        # 排序并返回前5个
        sorted_tables = sorted(table_connections.items(), key=lambda x: x[1], reverse=True)[:5]
        
        result = []
        for table_id, connection_count in sorted_tables:
            table_name = next((ts.table_name for ts in table_schemas if str(ts.id) == table_id), "Unknown")
            result.append({
                "table_name": table_name,
                "connection_count": connection_count
            })
        
        return result
    
    def _generate_intelligent_recommendations(
        self, 
        basic_analysis: Dict[str, Any],
        schema_analysis: Dict[str, Any],
        semantic_analysis: Dict[str, Any],
        quality_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成智能建议"""
        
        recommendations = []
        
        # 基于表结构复杂度的建议
        complexity_score = schema_analysis.get("complexity_score", 0)
        if complexity_score > 70:
            recommendations.append("表结构复杂度较高，建议考虑表拆分或优化设计")
        elif complexity_score < 20:
            recommendations.append("表结构相对简单，可以考虑增加必要的索引和约束")
        
        # 基于数据类型的建议
        data_type_dist = schema_analysis.get("data_type_distribution", {})
        if data_type_dist.get("unknown", 0) > 0:
            recommendations.append("发现未知数据类型，建议检查并标准化数据类型")
        
        # 基于数据质量的建议
        quality_score = quality_analysis.get("analysis", {}).get("overall_score", 0)
        if quality_score < 60:
            recommendations.append("数据质量评分较低，建议进行数据质量改进")
        
        # 基于业务语义的建议
        business_categories = semantic_analysis.get("analysis", {}).get("business_categories", {})
        if len(business_categories) > 10:
            recommendations.append("业务分类较多，建议进行业务域划分和标准化")
        
        # 基于表关系的建议
        relationship_count = schema_analysis.get("relationship_analysis", {}).get("total_relationships", 0)
        if relationship_count == 0:
            recommendations.append("未发现表关系，建议检查外键约束和关联设计")
        elif relationship_count > 50:
            recommendations.append("表关系较多，建议优化关联查询性能")
        
        return recommendations
    
    async def get_optimized_query_suggestions(self, data_source_id: str, query_intent: str) -> List[Dict[str, Any]]:
        """
        基于表结构信息生成优化的查询建议
        
        Args:
            data_source_id: 数据源ID
            query_intent: 查询意图描述
            
        Returns:
            查询建议列表
        """
        try:
            # 获取表结构信息
            table_schemas = self.schema_query_service.get_table_schemas(data_source_id)
            
            if not table_schemas:
                return []
            
            # 分析查询意图
            intent_analysis = self._analyze_query_intent(query_intent)
            
            # 匹配相关表
            relevant_tables = self._find_relevant_tables(table_schemas, intent_analysis)
            
            # 生成查询建议
            suggestions = []
            for table_info in relevant_tables:
                suggestion = self._generate_query_suggestion(table_info, intent_analysis)
                if suggestion:
                    suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"生成查询建议失败: {e}")
            return []
    
    def _analyze_query_intent(self, query_intent: str) -> Dict[str, Any]:
        """分析查询意图"""
        
        intent_lower = query_intent.lower()
        
        # 关键词映射
        keywords = {
            "用户": ["user", "customer", "member", "account"],
            "订单": ["order", "transaction", "purchase", "sale"],
            "产品": ["product", "item", "goods", "sku"],
            "时间": ["time", "date", "created", "updated"],
            "统计": ["count", "sum", "avg", "statistics"],
            "分析": ["analysis", "report", "dashboard"]
        }
        
        detected_keywords = []
        for category, words in keywords.items():
            for word in words:
                if word in intent_lower:
                    detected_keywords.append(category)
                    break
        
        return {
            "keywords": detected_keywords,
            "is_statistical": any(word in intent_lower for word in ["统计", "count", "sum", "avg"]),
            "is_analytical": any(word in intent_lower for word in ["分析", "analysis", "report"])
        }
    
    def _find_relevant_tables(self, table_schemas: List[TableSchema], intent_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查找相关表"""
        
        relevant_tables = []
        keywords = intent_analysis.get("keywords", [])
        
        for table_schema in table_schemas:
            relevance_score = 0
            
            # 基于表名匹配
            table_name = table_schema.table_name.lower()
            for keyword in keywords:
                if keyword.lower() in table_name:
                    relevance_score += 10
            
            # 基于业务分类匹配
            if table_schema.business_category:
                for keyword in keywords:
                    if keyword.lower() in table_schema.business_category.lower():
                        relevance_score += 8
            
            # 基于列名匹配
            columns = self.schema_query_service.get_table_columns(str(table_schema.id))
            for column in columns:
                column_name = column.column_name.lower()
                for keyword in keywords:
                    if keyword.lower() in column_name:
                        relevance_score += 5
            
            if relevance_score > 0:
                relevant_tables.append({
                    "table_schema": table_schema,
                    "columns": columns,
                    "relevance_score": relevance_score
                })
        
        # 按相关性排序
        relevant_tables.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant_tables[:5]  # 返回前5个最相关的表
    
    def _generate_query_suggestion(self, table_info: Dict[str, Any], intent_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """生成查询建议"""
        
        table_schema = table_info["table_schema"]
        columns = table_info["columns"]
        
        # 根据意图类型生成不同的查询建议
        if intent_analysis.get("is_statistical"):
            return self._generate_statistical_query(table_schema, columns)
        elif intent_analysis.get("is_analytical"):
            return self._generate_analytical_query(table_schema, columns)
        else:
            return self._generate_basic_query(table_schema, columns)
    
    def _generate_statistical_query(self, table_schema: TableSchema, columns: List[ColumnSchema]) -> Dict[str, Any]:
        """生成统计查询建议"""
        
        # 查找数值类型的列
        numeric_columns = [col for col in columns if col.normalized_type in [
            ColumnType.INT, ColumnType.BIGINT, ColumnType.FLOAT, 
            ColumnType.DOUBLE, ColumnType.DECIMAL
        ]]
        
        if not numeric_columns:
            return None
        
        # 查找时间类型的列
        time_columns = [col for col in columns if col.normalized_type in [
            ColumnType.DATE, ColumnType.DATETIME, ColumnType.TIMESTAMP
        ]]
        
        query_template = f"SELECT "
        if time_columns:
            query_template += f"{time_columns[0].column_name}, "
        
        for i, col in enumerate(numeric_columns[:3]):  # 最多3个数值列
            query_template += f"SUM({col.column_name}) as total_{col.column_name}, "
            query_template += f"AVG({col.column_name}) as avg_{col.column_name}, "
            query_template += f"COUNT({col.column_name}) as count_{col.column_name}"
            if i < len(numeric_columns[:3]) - 1:
                query_template += ", "
        
        query_template += f" FROM {table_schema.table_name}"
        
        if time_columns:
            query_template += f" GROUP BY {time_columns[0].column_name}"
        
        return {
            "type": "statistical",
            "table_name": table_schema.table_name,
            "query": query_template,
            "description": f"统计 {table_schema.table_name} 表的数值字段",
            "columns_used": [col.column_name for col in numeric_columns[:3] + time_columns[:1]]
        }
    
    def _generate_analytical_query(self, table_schema: TableSchema, columns: List[ColumnSchema]) -> Dict[str, Any]:
        """生成分析查询建议"""
        
        # 查找关键列
        id_columns = [col for col in columns if "id" in col.column_name.lower()]
        name_columns = [col for col in columns if "name" in col.column_name.lower()]
        time_columns = [col for col in columns if col.normalized_type in [
            ColumnType.DATE, ColumnType.DATETIME, ColumnType.TIMESTAMP
        ]]
        
        query_template = f"SELECT "
        
        # 添加ID列
        if id_columns:
            query_template += f"{id_columns[0].column_name}, "
        
        # 添加名称列
        if name_columns:
            query_template += f"{name_columns[0].column_name}, "
        
        # 添加时间列
        if time_columns:
            query_template += f"{time_columns[0].column_name}, "
        
        # 添加其他重要列
        other_columns = [col for col in columns if col not in id_columns + name_columns + time_columns][:3]
        for col in other_columns:
            query_template += f"{col.column_name}, "
        
        query_template = query_template.rstrip(", ") + f" FROM {table_schema.table_name}"
        
        # 添加时间过滤
        if time_columns:
            query_template += f" WHERE {time_columns[0].column_name} >= '2024-01-01'"
        
        query_template += " ORDER BY "
        if time_columns:
            query_template += f"{time_columns[0].column_name} DESC"
        elif id_columns:
            query_template += f"{id_columns[0].column_name}"
        
        return {
            "type": "analytical",
            "table_name": table_schema.table_name,
            "query": query_template,
            "description": f"分析 {table_schema.table_name} 表的数据趋势",
            "columns_used": [col.column_name for col in id_columns[:1] + name_columns[:1] + time_columns[:1] + other_columns]
        }
    
    def _generate_basic_query(self, table_schema: TableSchema, columns: List[ColumnSchema]) -> Dict[str, Any]:
        """生成基础查询建议"""
        
        # 选择前5个列
        selected_columns = columns[:5]
        
        query_template = f"SELECT "
        for i, col in enumerate(selected_columns):
            query_template += col.column_name
            if i < len(selected_columns) - 1:
                query_template += ", "
        
        query_template += f" FROM {table_schema.table_name} LIMIT 100"
        
        return {
            "type": "basic",
            "table_name": table_schema.table_name,
            "query": query_template,
            "description": f"查看 {table_schema.table_name} 表的基础数据",
            "columns_used": [col.column_name for col in selected_columns]
        }
    
    async def analyze_data_structure(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析数据结构
        
        Args:
            data: 数据列表
            
        Returns:
            数据结构分析结果
        """
        try:
            if not data:
                return {
                    "row_count": 0,
                    "column_types": {},
                    "error": "No data provided"
                }
            
            df = pd.DataFrame(data)
            
            # 分析列类型
            column_types = {}
            for col in df.columns:
                dtype = str(df[col].dtype)
                if dtype.startswith('int'):
                    column_types[col] = 'int64'
                elif dtype.startswith('float'):
                    column_types[col] = 'float64'
                elif dtype == 'bool':
                    column_types[col] = 'boolean'
                elif dtype == 'datetime64[ns]':
                    column_types[col] = 'datetime'
                else:
                    column_types[col] = 'object'
            
            # 基本统计信息
            basic_stats = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "column_types": column_types,
                "memory_usage": df.memory_usage(deep=True).sum(),
                "null_counts": df.isnull().sum().to_dict(),
                "data_summary": df.describe(include='all').to_dict() if len(df) > 0 else {}
            }
            
            return basic_stats
            
        except Exception as e:
            self.logger.error(f"数据结构分析失败: {e}")
            return {
                "row_count": 0,
                "column_types": {},
                "error": f"Data analysis failed: {str(e)}"
            }


# Schema Aware Analysis Service factory function
def create_schema_aware_analysis_service(db_session: Session, user_id: str) -> SchemaAwareAnalysisService:
    """创建用户专属的Schema感知分析服务"""
    return SchemaAwareAnalysisService(db_session, user_id)
