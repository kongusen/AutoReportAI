"""
表结构元数据服务
负责管理表结构的业务语义信息和元数据
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.table_schema import TableSchema, ColumnSchema


class SchemaMetadataService:
    """表结构元数据服务"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
    
    def update_table_business_info(
        self, 
        table_schema_id: str, 
        business_info: Dict[str, Any]
    ) -> bool:
        """
        更新表的业务信息
        
        Args:
            table_schema_id: 表结构ID
            business_info: 业务信息
            
        Returns:
            更新是否成功
        """
        try:
            table_schema = self.db_session.query(TableSchema).filter(
                TableSchema.id == table_schema_id
            ).first()
            
            if not table_schema:
                return False
            
            # 更新业务信息
            if "business_category" in business_info:
                table_schema.business_category = business_info["business_category"]
            if "data_freshness" in business_info:
                table_schema.data_freshness = business_info["data_freshness"]
            if "update_frequency" in business_info:
                table_schema.update_frequency = business_info["update_frequency"]
            
            table_schema.updated_at = datetime.utcnow()
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"更新表业务信息失败: {e}")
            return False
    
    def update_column_business_info(
        self, 
        column_schema_id: str, 
        business_info: Dict[str, Any]
    ) -> bool:
        """
        更新列的业务信息
        
        Args:
            column_schema_id: 列结构ID
            business_info: 业务信息
            
        Returns:
            更新是否成功
        """
        try:
            column_schema = self.db_session.query(ColumnSchema).filter(
                ColumnSchema.id == column_schema_id
            ).first()
            
            if not column_schema:
                return False
            
            # 更新业务信息
            if "business_name" in business_info:
                column_schema.business_name = business_info["business_name"]
            if "business_description" in business_info:
                column_schema.business_description = business_info["business_description"]
            if "semantic_category" in business_info:
                column_schema.semantic_category = business_info["semantic_category"]
            
            column_schema.updated_at = datetime.utcnow()
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"更新列业务信息失败: {e}")
            return False
    
    def update_data_quality_info(
        self, 
        table_schema_id: str, 
        quality_info: Dict[str, Any]
    ) -> bool:
        """
        更新数据质量信息
        
        Args:
            table_schema_id: 表结构ID
            quality_info: 质量信息
            
        Returns:
            更新是否成功
        """
        try:
            table_schema = self.db_session.query(TableSchema).filter(
                TableSchema.id == table_schema_id
            ).first()
            
            if not table_schema:
                return False
            
            # 更新质量信息
            if "data_quality_score" in quality_info:
                table_schema.data_quality_score = quality_info["data_quality_score"]
            if "completeness_rate" in quality_info:
                table_schema.completeness_rate = quality_info["completeness_rate"]
            if "accuracy_rate" in quality_info:
                table_schema.accuracy_rate = quality_info["accuracy_rate"]
            
            table_schema.updated_at = datetime.utcnow()
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"更新数据质量信息失败: {e}")
            return False
    
    def update_column_data_quality_info(
        self, 
        column_schema_id: str, 
        quality_info: Dict[str, Any]
    ) -> bool:
        """
        更新列的数据质量信息
        
        Args:
            column_schema_id: 列结构ID
            quality_info: 质量信息
            
        Returns:
            更新是否成功
        """
        try:
            column_schema = self.db_session.query(ColumnSchema).filter(
                ColumnSchema.id == column_schema_id
            ).first()
            
            if not column_schema:
                return False
            
            # 更新质量信息
            if "null_count" in quality_info:
                column_schema.null_count = quality_info["null_count"]
            if "unique_count" in quality_info:
                column_schema.unique_count = quality_info["unique_count"]
            if "distinct_count" in quality_info:
                column_schema.distinct_count = quality_info["distinct_count"]
            if "min_value" in quality_info:
                column_schema.min_value = str(quality_info["min_value"])
            if "max_value" in quality_info:
                column_schema.max_value = str(quality_info["max_value"])
            if "avg_value" in quality_info:
                column_schema.avg_value = str(quality_info["avg_value"])
            if "data_patterns" in quality_info:
                column_schema.data_patterns = quality_info["data_patterns"]
            if "sample_values" in quality_info:
                column_schema.sample_values = quality_info["sample_values"]
            
            column_schema.updated_at = datetime.utcnow()
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"更新列数据质量信息失败: {e}")
            return False
    
    def batch_update_business_info(
        self, 
        data_source_id: str, 
        updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量更新业务信息
        
        Args:
            data_source_id: 数据源ID
            updates: 更新列表
            
        Returns:
            更新结果
        """
        success_count = 0
        error_count = 0
        errors = []
        
        for update in updates:
            try:
                if update.get("type") == "table":
                    success = self.update_table_business_info(
                        update["id"], 
                        update["business_info"]
                    )
                elif update.get("type") == "column":
                    success = self.update_column_business_info(
                        update["id"], 
                        update["business_info"]
                    )
                else:
                    success = False
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"更新失败: {update.get('id')}")
                    
            except Exception as e:
                error_count += 1
                errors.append(f"更新异常: {update.get('id')} - {str(e)}")
        
        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors
        }
    
    def get_business_metadata(self, data_source_id: str) -> Dict[str, Any]:
        """
        获取业务元数据
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            业务元数据
        """
        try:
            # 获取表业务信息
            tables = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True
                )
            ).all()
            
            business_metadata = {
                "tables": [],
                "categories": {},
                "semantic_patterns": {}
            }
            
            for table in tables:
                table_info = {
                    "id": str(table.id),
                    "name": table.table_name,
                    "business_category": table.business_category,
                    "data_freshness": table.data_freshness,
                    "update_frequency": table.update_frequency,
                    "data_quality_score": table.data_quality_score,
                    "columns": []
                }
                
                # 获取列信息
                columns = self.db_session.query(ColumnSchema).filter(
                    ColumnSchema.table_schema_id == table.id
                ).all()
                
                for column in columns:
                    column_info = {
                        "id": str(column.id),
                        "name": column.column_name,
                        "business_name": column.business_name,
                        "semantic_category": column.semantic_category,
                        "data_type": column.normalized_type.value
                    }
                    table_info["columns"].append(column_info)
                
                business_metadata["tables"].append(table_info)
                
                # 统计分类信息
                if table.business_category:
                    if table.business_category not in business_metadata["categories"]:
                        business_metadata["categories"][table.business_category] = []
                    business_metadata["categories"][table.business_category].append(table.table_name)
            
            return business_metadata
            
        except Exception as e:
            self.logger.error(f"获取业务元数据失败: {e}")
            return {"error": str(e)}
    
    def export_metadata(self, data_source_id: str, format: str = "json") -> Dict[str, Any]:
        """
        导出元数据
        
        Args:
            data_source_id: 数据源ID
            format: 导出格式
            
        Returns:
            导出的元数据
        """
        try:
            metadata = self.get_business_metadata(data_source_id)
            
            if format.lower() == "json":
                return {
                    "success": True,
                    "format": "json",
                    "data": metadata
                }
            elif format.lower() == "csv":
                # 转换为CSV格式
                csv_data = self._convert_to_csv(metadata)
                return {
                    "success": True,
                    "format": "csv",
                    "data": csv_data
                }
            else:
                return {
                    "success": False,
                    "error": f"不支持的导出格式: {format}"
                }
                
        except Exception as e:
            self.logger.error(f"导出元数据失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _convert_to_csv(self, metadata: Dict[str, Any]) -> str:
        """转换为CSV格式"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表信息
        writer.writerow(["表名", "业务分类", "数据新鲜度", "更新频率", "质量评分"])
        for table in metadata.get("tables", []):
            writer.writerow([
                table["name"],
                table.get("business_category", ""),
                table.get("data_freshness", ""),
                table.get("update_frequency", ""),
                table.get("data_quality_score", "")
            ])
        
        # 写入列信息
        writer.writerow([])
        writer.writerow(["表名", "列名", "业务名称", "语义分类", "数据类型"])
        for table in metadata.get("tables", []):
            for column in table.get("columns", []):
                writer.writerow([
                    table["name"],
                    column["name"],
                    column.get("business_name", ""),
                    column.get("semantic_category", ""),
                    column.get("data_type", "")
                ])
        
        return output.getvalue()
    
    def import_metadata(self, data_source_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入元数据
        
        Args:
            data_source_id: 数据源ID
            metadata: 元数据
            
        Returns:
            导入结果
        """
        try:
            success_count = 0
            error_count = 0
            errors = []
            
            for table_info in metadata.get("tables", []):
                try:
                    # 查找表
                    table = self.db_session.query(TableSchema).filter(
                        and_(
                            TableSchema.data_source_id == data_source_id,
                            TableSchema.table_name == table_info["name"]
                        )
                    ).first()
                    
                    if table:
                        # 更新表业务信息
                        business_info = {
                            "business_category": table_info.get("business_category"),
                            "data_freshness": table_info.get("data_freshness"),
                            "update_frequency": table_info.get("update_frequency")
                        }
                        
                        if self.update_table_business_info(str(table.id), business_info):
                            success_count += 1
                        else:
                            error_count += 1
                            errors.append(f"更新表失败: {table_info['name']}")
                    
                    # 更新列信息
                    for column_info in table_info.get("columns", []):
                        if table:
                            column = self.db_session.query(ColumnSchema).filter(
                                and_(
                                    ColumnSchema.table_schema_id == table.id,
                                    ColumnSchema.column_name == column_info["name"]
                                )
                            ).first()
                            
                            if column:
                                business_info = {
                                    "business_name": column_info.get("business_name"),
                                    "semantic_category": column_info.get("semantic_category")
                                }
                                
                                if self.update_column_business_info(str(column.id), business_info):
                                    success_count += 1
                                else:
                                    error_count += 1
                                    errors.append(f"更新列失败: {table_info['name']}.{column_info['name']}")
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"处理表异常: {table_info.get('name', 'unknown')} - {str(e)}")
            
            return {
                "success": True,
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors
            }
            
        except Exception as e:
            self.logger.error(f"导入元数据失败: {e}")
            return {"success": False, "error": str(e)}
