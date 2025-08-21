"""
表结构查询服务
提供表结构信息的查询和检索功能
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.table_schema import TableSchema, ColumnSchema, TableRelationship


class SchemaQueryService:
    """表结构查询服务"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
    
    def get_table_schemas(self, data_source_id: str) -> List[TableSchema]:
        """
        获取数据源的所有表结构
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            表结构列表
        """
        return self.db_session.query(TableSchema).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True
            )
        ).all()
    
    def get_table_schema(self, table_schema_id: str) -> Optional[TableSchema]:
        """
        获取特定表结构
        
        Args:
            table_schema_id: 表结构ID
            
        Returns:
            表结构信息
        """
        return self.db_session.query(TableSchema).filter(
            TableSchema.id == table_schema_id
        ).first()
    
    def get_table_by_name(self, data_source_id: str, table_name: str) -> Optional[TableSchema]:
        """
        根据表名获取表结构
        
        Args:
            data_source_id: 数据源ID
            table_name: 表名
            
        Returns:
            表结构信息
        """
        return self.db_session.query(TableSchema).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.table_name == table_name,
                TableSchema.is_active == True
            )
        ).first()
    
    def get_table_relationships(self, data_source_id: str) -> List[TableRelationship]:
        """
        获取数据源的表关系
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            表关系列表
        """
        return self.db_session.query(TableRelationship).filter(
            TableRelationship.data_source_id == data_source_id
        ).all()
    
    def get_table_columns(self, table_schema_id: str) -> List[ColumnSchema]:
        """
        获取表的列信息
        
        Args:
            table_schema_id: 表结构ID
            
        Returns:
            列信息列表
        """
        return self.db_session.query(ColumnSchema).filter(
            ColumnSchema.table_schema_id == table_schema_id
        ).all()
    
    def search_tables(
        self, 
        data_source_id: str, 
        search_term: str,
        category: Optional[str] = None
    ) -> List[TableSchema]:
        """
        搜索表
        
        Args:
            data_source_id: 数据源ID
            search_term: 搜索关键词
            category: 业务分类过滤
            
        Returns:
            匹配的表结构列表
        """
        query = self.db_session.query(TableSchema).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True
            )
        )
        
        # 添加搜索条件
        if search_term:
            query = query.filter(
                or_(
                    TableSchema.table_name.ilike(f"%{search_term}%"),
                    TableSchema.business_category.ilike(f"%{search_term}%")
                )
            )
        
        # 添加分类过滤
        if category:
            query = query.filter(TableSchema.business_category == category)
        
        return query.all()
    
    def search_columns(
        self, 
        data_source_id: str, 
        search_term: str,
        column_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索列
        
        Args:
            data_source_id: 数据源ID
            search_term: 搜索关键词
            column_type: 列类型过滤
            
        Returns:
            匹配的列信息列表
        """
        query = self.db_session.query(ColumnSchema, TableSchema).join(
            TableSchema,
            ColumnSchema.table_schema_id == TableSchema.id
        ).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True
            )
        )
        
        # 添加搜索条件
        if search_term:
            query = query.filter(
                or_(
                    ColumnSchema.column_name.ilike(f"%{search_term}%"),
                    ColumnSchema.business_name.ilike(f"%{search_term}%"),
                    ColumnSchema.semantic_category.ilike(f"%{search_term}%")
                )
            )
        
        # 添加类型过滤
        if column_type:
            query = query.filter(ColumnSchema.normalized_type == column_type)
        
        results = query.all()
        
        # 格式化结果
        formatted_results = []
        for column, table in results:
            formatted_results.append({
                "column_id": str(column.id),
                "column_name": column.column_name,
                "table_name": table.table_name,
                "table_id": str(table.id),
                "column_type": column.normalized_type,
                "business_name": column.business_name,
                "semantic_category": column.semantic_category
            })
        
        return formatted_results
    
    def get_business_categories(self, data_source_id: str) -> List[str]:
        """
        获取业务分类列表
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            业务分类列表
        """
        categories = self.db_session.query(TableSchema.business_category).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True,
                TableSchema.business_category.isnot(None)
            )
        ).distinct().all()
        
        return [cat[0] for cat in categories if cat[0]]
    
    def get_semantic_categories(self, data_source_id: str) -> List[str]:
        """
        获取语义分类列表
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            语义分类列表
        """
        categories = self.db_session.query(ColumnSchema.semantic_category).join(
            TableSchema,
            ColumnSchema.table_schema_id == TableSchema.id
        ).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True,
                ColumnSchema.semantic_category.isnot(None)
            )
        ).distinct().all()
        
        return [cat[0] for cat in categories if cat[0]]
    
    def get_schema_statistics(self, data_source_id: str) -> Dict[str, Any]:
        """
        获取表结构统计信息
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            统计信息
        """
        # 表统计
        total_tables = self.db_session.query(TableSchema).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True
            )
        ).count()
        
        analyzed_tables = self.db_session.query(TableSchema).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True,
                TableSchema.is_analyzed == True
            )
        ).count()
        
        # 列统计
        total_columns = self.db_session.query(ColumnSchema).join(
            TableSchema,
            ColumnSchema.table_schema_id == TableSchema.id
        ).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True
            )
        ).count()
        
        # 关系统计
        total_relationships = self.db_session.query(TableRelationship).filter(
            TableRelationship.data_source_id == data_source_id
        ).count()
        
        # 数据类型统计
        from sqlalchemy import func
        type_stats = self.db_session.query(
            ColumnSchema.normalized_type,
            func.count(ColumnSchema.id)
        ).join(
            TableSchema,
            ColumnSchema.table_schema_id == TableSchema.id
        ).filter(
            and_(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True
            )
        ).group_by(ColumnSchema.normalized_type).all()
        
        return {
            "total_tables": total_tables,
            "analyzed_tables": analyzed_tables,
            "total_columns": total_columns,
            "total_relationships": total_relationships,
            "type_distribution": {str(t[0]): t[1] for t in type_stats},
            "analysis_progress": (analyzed_tables / total_tables * 100) if total_tables > 0 else 0
        }
    
    def get_related_tables(self, table_schema_id: str) -> List[Dict[str, Any]]:
        """
        获取相关表
        
        Args:
            table_schema_id: 表结构ID
            
        Returns:
            相关表列表
        """
        # 查找以当前表为源的关系
        source_relationships = self.db_session.query(TableRelationship, TableSchema).join(
            TableSchema,
            TableRelationship.target_table_id == TableSchema.id
        ).filter(
            TableRelationship.source_table_id == table_schema_id
        ).all()
        
        # 查找以当前表为目标的关系
        target_relationships = self.db_session.query(TableRelationship, TableSchema).join(
            TableSchema,
            TableRelationship.source_table_id == TableSchema.id
        ).filter(
            TableRelationship.target_table_id == table_schema_id
        ).all()
        
        related_tables = []
        
        # 处理源关系
        for rel, table in source_relationships:
            related_tables.append({
                "table_id": str(table.id),
                "table_name": table.table_name,
                "relationship_type": rel.relationship_type,
                "source_column": rel.source_column,
                "target_column": rel.target_column,
                "confidence": rel.confidence_score,
                "direction": "target"
            })
        
        # 处理目标关系
        for rel, table in target_relationships:
            related_tables.append({
                "table_id": str(table.id),
                "table_name": table.table_name,
                "relationship_type": rel.relationship_type,
                "source_column": rel.target_column,
                "target_column": rel.source_column,
                "confidence": rel.confidence_score,
                "direction": "source"
            })
        
        return related_tables
