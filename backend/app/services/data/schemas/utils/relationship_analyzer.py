"""
表关系分析工具
负责分析表之间的关联关系和依赖关系
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.table_schema import TableSchema, ColumnSchema


class RelationshipAnalyzer:
    """表关系分析工具"""
    
    def find_relationships(
        self, 
        source_table: TableSchema, 
        target_table: TableSchema
    ) -> List[Dict[str, Any]]:
        """
        查找两个表之间的潜在关系
        
        Args:
            source_table: 源表
            target_table: 目标表
            
        Returns:
            关系列表
        """
        relationships = []
        
        # 获取表的列信息
        source_columns = self._get_table_columns(source_table)
        target_columns = self._get_table_columns(target_table)
        
        # 查找外键关系（基于命名约定）
        for source_col in source_columns:
            for target_col in target_columns:
                # 检查是否是外键关系
                if self._is_foreign_key_relationship(source_col, target_col, source_table, target_table):
                    relationships.append({
                        "source_column": source_col.column_name,
                        "target_column": target_col.column_name,
                        "type": "one_to_many",
                        "confidence": 0.8,
                        "description": f"{source_table.table_name}.{source_col.column_name} -> {target_table.table_name}.{target_col.column_name}"
                    })
        
        # 查找同名字段关系
        for source_col in source_columns:
            for target_col in target_columns:
                if (source_col.column_name == target_col.column_name and
                    source_col.normalized_type == target_col.normalized_type):
                    relationships.append({
                        "source_column": source_col.column_name,
                        "target_column": target_col.column_name,
                        "type": "many_to_many",
                        "confidence": 0.6,
                        "description": f"同名字段: {source_col.column_name}"
                    })
        
        return relationships
    
    def _get_table_columns(self, table_schema: TableSchema) -> List[ColumnSchema]:
        """
        获取表的列信息
        
        Args:
            table_schema: 表结构
            
        Returns:
            列列表
        """
        # 这里需要从数据库获取列信息
        # 在实际使用中，需要通过session查询
        # 由于这里没有session，我们返回空列表
        # 在实际使用时，应该通过SchemaAnalysisService传入session
        return []
    
    def _is_foreign_key_relationship(
        self, 
        source_col: ColumnSchema, 
        target_col: ColumnSchema,
        source_table: TableSchema,
        target_table: TableSchema
    ) -> bool:
        """
        判断两个列是否构成外键关系
        
        Args:
            source_col: 源列
            target_col: 目标列
            source_table: 源表
            target_table: 目标表
            
        Returns:
            是否构成外键关系
        """
        # 简单的命名约定检查
        source_name = source_col.column_name.lower()
        target_name = target_col.column_name.lower()
        
        # 检查是否是ID字段
        if "id" in source_name and "id" in target_name:
            # 检查表名是否在字段名中
            source_table_name = source_table.table_name.lower()
            target_table_name = target_table.table_name.lower()
            
            if (source_table_name in source_name and 
                target_table_name in target_name and
                source_col.normalized_type == target_col.normalized_type):
                return True
        
        # 检查常见的外键命名模式
        fk_patterns = [
            (f"{target_table.table_name.lower()}_id", "id"),
            (f"{target_table.table_name.lower()}_key", "key"),
            (f"{target_table.table_name.lower()}_pk", "pk")
        ]
        
        for fk_pattern, pk_pattern in fk_patterns:
            if (source_name == fk_pattern and target_name == pk_pattern and
                source_col.normalized_type == target_col.normalized_type):
                return True
        
        return False
    
    def analyze_dependency_graph(self, table_schemas: List[TableSchema]) -> Dict[str, Any]:
        """
        分析表依赖图
        
        Args:
            table_schemas: 表结构列表
            
        Returns:
            依赖图信息
        """
        dependency_graph = {
            "nodes": [],
            "edges": [],
            "cycles": [],
            "layers": []
        }
        
        # 构建节点
        for table_schema in table_schemas:
            dependency_graph["nodes"].append({
                "id": str(table_schema.id),
                "name": table_schema.table_name,
                "type": "table"
            })
        
        # 构建边（这里需要实际的列信息）
        # 在实际实现中，需要查询列信息并分析关系
        
        return dependency_graph
    
    def find_circular_dependencies(self, relationships: List[Dict[str, Any]]) -> List[List[str]]:
        """
        查找循环依赖
        
        Args:
            relationships: 关系列表
            
        Returns:
            循环依赖列表
        """
        # 使用深度优先搜索查找循环
        cycles = []
        visited = set()
        rec_stack = set()
        
        # 构建邻接表
        graph = {}
        for rel in relationships:
            source = rel["source_column"]
            target = rel["target_column"]
            if source not in graph:
                graph[source] = []
            graph[source].append(target)
        
        def dfs(node, path):
            if node in rec_stack:
                # 找到循环
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            if node in graph:
                for neighbor in graph[node]:
                    dfs(neighbor, path.copy())
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def suggest_optimizations(self, table_schemas: List[TableSchema]) -> List[str]:
        """
        建议优化方案
        
        Args:
            table_schemas: 表结构列表
            
        Returns:
            优化建议列表
        """
        suggestions = []
        
        # 分析表大小
        large_tables = [ts for ts in table_schemas if ts.estimated_row_count and ts.estimated_row_count > 1000000]
        if large_tables:
            suggestions.append(f"发现 {len(large_tables)} 个大表，建议考虑分区或分表")
        
        # 分析缺少索引的表
        # 这里需要实际的列信息来分析索引情况
        
        # 分析数据类型优化
        # 这里需要实际的列信息来分析数据类型
        
        return suggestions
