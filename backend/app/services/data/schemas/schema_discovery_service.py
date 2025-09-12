"""
表结构发现服务
负责从数据源发现表结构信息并存储到数据库
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.data_source import DataSource
from app.models.table_schema import TableSchema, ColumnSchema
from app.services.data.connectors.doris_connector import DorisConnector
from app.core.exceptions import (
    NotFoundError,
    DatabaseError,
    ExternalServiceError,
    DataRetrievalError
)
from .utils.type_normalizer import TypeNormalizer
from .transaction_manager import TransactionManager, IsolationLevel


class SchemaDiscoveryService:
    """表结构发现服务"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self.type_normalizer = TypeNormalizer()
        self.transaction_manager = TransactionManager(db_session)
    
    async def discover_and_store_schemas(self, data_source_id: str) -> Dict[str, Any]:
        """
        发现并存储数据源的所有表结构 - 使用高级事务管理
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            发现结果
        """
        try:
            # 使用READ COMMITTED隔离级别，避免长时间锁定
            async with self.transaction_manager.transaction(
                isolation_level=IsolationLevel.READ_COMMITTED,
                timeout=1800  # 30分钟超时
            ) as session:
                
                # 获取数据源
                data_source = session.query(DataSource).filter(
                    DataSource.id == data_source_id
                ).first()
                
                if not data_source:
                    raise NotFoundError("数据源", data_source_id)
                
                # 根据数据源类型选择连接器
                if data_source.source_type.value == "doris":
                    return await self._discover_doris_schemas_with_transaction(data_source, session)
                else:
                    raise ExternalServiceError(f"不支持的数据源类型: {data_source.source_type.value}")
                
        except (NotFoundError, ExternalServiceError):
            raise  # Re-raise known exceptions
        except Exception as e:
            self.logger.error(f"发现表结构失败: {e}")
            raise DatabaseError(f"表结构发现失败: {str(e)}")
    
    async def _discover_doris_schemas_with_transaction(self, data_source: DataSource, session: Session) -> Dict[str, Any]:
        """发现Doris数据源的表结构 - 使用事务管理器版本"""
        
        connector = None
        stored_tables = []
        failed_tables = []
        
        try:
            # 创建Doris连接器
            from app.services.data.connectors.connector_factory import create_connector
            connector = create_connector(data_source)
            
            await connector.connect()
            
            # 测试连接
            connection_test = await connector.test_connection()
            if not connection_test.get("success"):
                return {"success": False, "error": f"连接失败: {connection_test.get('error')}"}
            
            # 获取所有表
            tables = await connector.get_tables()
            if not tables:
                return {"success": False, "error": "未发现任何表"}
            
            self.logger.info(f"开始处理 {len(tables)} 个表的结构信息，使用高级事务管理")
            
            # 先清理该数据源的旧表结构信息
            await self._cleanup_old_schemas_in_session(data_source.id, session)
            
            # 使用批量处理器
            async with self.transaction_manager.batch_operation(
                batch_size=5,  # 每次处理5个表
                isolation_level=IsolationLevel.READ_COMMITTED
            ) as batch_processor:
                
                for table_name in tables:
                    await batch_processor.add(
                        self._process_single_table,
                        data_source, table_name, connector, session, stored_tables, failed_tables
                    )
            
            return {
                "success": True,
                "message": f"成功发现并存储 {len(stored_tables)} 个表的结构信息",
                "tables_count": len(stored_tables),
                "failed_count": len(failed_tables),
                "stored_tables": [table.table_name for table in stored_tables],
                "failed_tables": [{"table": fail["table"], "error": fail["error"]} for fail in failed_tables],
                "statistics": {
                    "total_tables": len(tables),
                    "success_rate": len(stored_tables) / len(tables) * 100 if tables else 0
                },
                "transaction_stats": self.transaction_manager.get_transaction_status()
            }
                
        except Exception as e:
            self.logger.error(f"发现Doris表结构失败: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            # 确保连接器被正确关闭
            if connector:
                try:
                    await connector.disconnect()
                except Exception as disconnect_error:
                    self.logger.warning(f"关闭连接器时出错: {disconnect_error}")
    
    async def _discover_doris_schemas(self, data_source: DataSource) -> Dict[str, Any]:
        """发现Doris数据源的表结构 - 改进事务管理"""
        
        connector = None
        stored_tables = []
        failed_tables = []
        
        try:
            # 创建Doris连接器
            from app.services.data.connectors.connector_factory import create_connector
            connector = create_connector(data_source)
            
            await connector.connect()
            
            # 测试连接
            connection_test = await connector.test_connection()
            if not connection_test.get("success"):
                return {"success": False, "error": f"连接失败: {connection_test.get('error')}"}
            
            # 获取所有表
            tables = await connector.get_tables()
            if not tables:
                return {"success": False, "error": "未发现任何表"}
            
            # 开始批量事务处理
            self.logger.info(f"开始处理 {len(tables)} 个表的结构信息，采用批量事务模式")
            
            # 先清理该数据源的旧表结构信息
            await self._cleanup_old_schemas(data_source.id)
            
            # 批量处理表结构，每批处理10个表
            batch_size = 10
            for i in range(0, len(tables), batch_size):
                batch_tables = tables[i:i + batch_size]
                batch_results = await self._process_table_batch(
                    data_source, batch_tables, connector
                )
                
                stored_tables.extend(batch_results["stored"])
                failed_tables.extend(batch_results["failed"])
            
            # 最终提交
            try:
                self.db_session.commit()
                self.logger.info(f"成功提交所有表结构信息: {len(stored_tables)} 个表")
            except Exception as commit_error:
                self.logger.error(f"提交事务失败: {commit_error}")
                self.db_session.rollback()
                return {
                    "success": False, 
                    "error": f"数据库提交失败: {str(commit_error)}"
                }
                
            return {
                "success": True,
                "message": f"成功发现并存储 {len(stored_tables)} 个表的结构信息",
                "tables_count": len(stored_tables),
                "failed_count": len(failed_tables),
                "stored_tables": [table.table_name for table in stored_tables],
                "failed_tables": [{"table": fail["table"], "error": fail["error"]} for fail in failed_tables],
                "statistics": {
                    "total_tables": len(tables),
                    "success_rate": len(stored_tables) / len(tables) * 100 if tables else 0
                }
            }
                
        except Exception as e:
            self.logger.error(f"发现Doris表结构失败: {e}")
            # 确保回滚事务
            try:
                self.db_session.rollback()
            except:
                pass
            return {"success": False, "error": str(e)}
        
        finally:
            # 确保连接器被正确关闭
            if connector:
                try:
                    await connector.disconnect()
                except Exception as disconnect_error:
                    self.logger.warning(f"关闭连接器时出错: {disconnect_error}")
    
    async def _store_table_schema(
        self, 
        data_source: DataSource, 
        table_name: str, 
        schema_info: Dict[str, Any]
    ) -> TableSchema:
        """存储表结构信息"""
        
        # 检查是否已存在
        existing_schema = self.db_session.query(TableSchema).filter(
            and_(
                TableSchema.data_source_id == data_source.id,
                TableSchema.table_name == table_name
            )
        ).first()
        
        if existing_schema:
            # 更新现有记录
            existing_schema.columns_info = schema_info.get("columns", [])
            existing_schema.updated_at = datetime.utcnow()
            table_schema = existing_schema
        else:
            # 创建新记录
            table_schema = TableSchema(
                data_source_id=data_source.id,
                table_name=table_name,
                columns_info=schema_info.get("columns", []),
                is_active=True,
                is_analyzed=False
            )
            self.db_session.add(table_schema)
        
        # 先提交表结构，确保有ID
        self.db_session.commit()
        
        # 存储列信息
        await self._store_column_schemas(table_schema, schema_info.get("columns", []))
        
        # 再次提交列信息
        self.db_session.commit()
        return table_schema
    
    async def _store_column_schemas(
        self, 
        table_schema: TableSchema, 
        columns_info: List[Dict[str, Any]]
    ):
        """存储列结构信息"""
        
        for col_info in columns_info:
            # 检查列是否已存在
            existing_column = self.db_session.query(ColumnSchema).filter(
                and_(
                    ColumnSchema.table_schema_id == table_schema.id,
                    ColumnSchema.column_name == col_info.get("name")
                )
            ).first()
            
            # 标准化数据类型
            normalized_type = self.type_normalizer.normalize_type(col_info.get("type", ""))
            
            column_data = {
                "column_name": col_info.get("name"),
                "column_type": col_info.get("type", ""),
                "normalized_type": normalized_type.value if hasattr(normalized_type, 'value') else str(normalized_type),  # 兼容字符串和枚举
                "is_nullable": col_info.get("nullable", True),
                "is_primary_key": col_info.get("key", "") == "PRI",
                "default_value": col_info.get("default"),
                "column_size": self.type_normalizer.extract_column_size(col_info.get("type", "")),
                "precision": self.type_normalizer.extract_precision(col_info.get("type", "")),
                "scale": self.type_normalizer.extract_scale(col_info.get("type", "")),
                "comment": col_info.get("comment", "")  # 新增注释字段存储
            }
            
            if existing_column:
                # 更新现有列
                for key, value in column_data.items():
                    setattr(existing_column, key, value)
                existing_column.updated_at = datetime.utcnow()
            else:
                # 创建新列
                column_schema = ColumnSchema(
                    table_schema_id=table_schema.id,
                    **column_data
                )
                self.db_session.add(column_schema)
    
    async def _update_table_statistics(
        self, 
        table_schema: TableSchema, 
        stats_info: Dict[str, Any]
    ):
        """更新表统计信息"""
        
        # 转换numpy类型为Python原生类型
        rows = stats_info.get("rows")
        data_length = stats_info.get("data_length")
        
        table_schema.estimated_row_count = int(rows) if rows is not None else None
        table_schema.table_size_bytes = int(data_length) if data_length is not None else None
        table_schema.last_analyzed = datetime.utcnow()
        
        self.db_session.commit()
    
    async def _cleanup_old_schemas(self, data_source_id: str):
        """清理旧的表结构信息"""
        try:
            # 软删除：标记为非活跃状态，而不是物理删除
            old_schemas = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True
                )
            ).all()
            
            for schema in old_schemas:
                schema.is_active = False
                schema.updated_at = datetime.utcnow()
            
            self.logger.info(f"标记 {len(old_schemas)} 个旧表结构为非活跃状态")
            
        except Exception as e:
            self.logger.error(f"清理旧表结构失败: {e}")
            raise
    
    async def _process_table_batch(
        self, 
        data_source: DataSource, 
        table_names: List[str], 
        connector
    ) -> Dict[str, List]:
        """批量处理表结构"""
        stored_tables = []
        failed_tables = []
        
        # 创建批量保存点
        savepoint_name = f"batch_{hash(tuple(table_names))}"
        
        try:
            # 开始保存点事务
            self.db_session.execute(f"SAVEPOINT {savepoint_name}")
            
            for table_name in table_names:
                try:
                    # 获取表结构
                    schema_info = await connector.get_table_schema(table_name)
                    if "error" not in schema_info:
                        # 存储表结构
                        table_schema = await self._store_table_schema(
                            data_source, table_name, schema_info
                        )
                        stored_tables.append(table_schema)
                        
                        # 获取表统计信息（如果连接器支持的话）
                        if hasattr(connector, 'get_table_statistics'):
                            try:
                                stats_info = await connector.get_table_statistics(table_name)
                                if "error" not in stats_info:
                                    await self._update_table_statistics(table_schema, stats_info)
                            except Exception as stats_e:
                                self.logger.warning(f"获取表 {table_name} 统计信息失败: {stats_e}")
                    else:
                        failed_tables.append({
                            "table": table_name,
                            "error": schema_info.get("error", "未知错误")
                        })
                        
                except Exception as e:
                    self.logger.warning(f"处理表 {table_name} 时出错: {e}")
                    failed_tables.append({
                        "table": table_name,
                        "error": str(e)
                    })
            
            # 如果批量处理成功，释放保存点
            self.db_session.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            self.logger.debug(f"批量处理成功: {len(stored_tables)} 个表，{len(failed_tables)} 个失败")
            
        except Exception as batch_error:
            # 批量处理失败，回滚到保存点
            try:
                self.db_session.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                self.logger.error(f"批量处理失败，已回滚到保存点: {batch_error}")
                # 将整批表都标记为失败
                for table_name in table_names:
                    if table_name not in [fail["table"] for fail in failed_tables]:
                        failed_tables.append({
                            "table": table_name,
                            "error": f"批量处理失败: {str(batch_error)}"
                        })
                stored_tables = []  # 清空已存储列表
            except Exception as rollback_error:
                self.logger.error(f"回滚到保存点失败: {rollback_error}")
                raise
        
        return {
            "stored": stored_tables,
            "failed": failed_tables
        }
    
    async def _verify_data_consistency(self, data_source_id: str) -> Dict[str, Any]:
        """验证数据一致性"""
        try:
            # 检查数据源是否存在
            data_source = self.db_session.query(DataSource).filter(
                DataSource.id == data_source_id
            ).first()
            
            if not data_source:
                return {"consistent": False, "error": "数据源不存在"}
            
            # 检查表结构信息的完整性
            table_schemas = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True
                )
            ).all()
            
            consistency_issues = []
            
            for schema in table_schemas:
                # 检查必要字段是否完整
                if not schema.table_name:
                    consistency_issues.append(f"表结构 {schema.id} 缺少表名")
                
                if not schema.columns_info:
                    consistency_issues.append(f"表 {schema.table_name} 缺少列信息")
                
                # 检查列信息的完整性
                if schema.columns_info:
                    for col in schema.columns_info:
                        if not col.get("name") or not col.get("type"):
                            consistency_issues.append(f"表 {schema.table_name} 存在不完整的列信息")
                            break
            
            return {
                "consistent": len(consistency_issues) == 0,
                "issues": consistency_issues,
                "total_tables": len(table_schemas),
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"数据一致性检查失败: {e}")
            return {"consistent": False, "error": str(e)}
    
    async def refresh_schema(self, data_source_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        刷新数据源的表结构信息
        
        Args:
            data_source_id: 数据源ID
            force_refresh: 是否强制刷新（忽略一致性检查）
        
        Returns:
            刷新结果
        """
        if not force_refresh:
            # 先检查数据一致性
            consistency_check = await self._verify_data_consistency(data_source_id)
            if consistency_check.get("consistent", False):
                self.logger.info(f"数据源 {data_source_id} 数据一致性良好，跳过刷新")
                return {
                    "success": True,
                    "message": "数据一致性良好，无需刷新",
                    "skipped": True,
                    "consistency_check": consistency_check
                }
        
        # 执行完整的表结构发现流程
        return await self.discover_and_store_schemas(data_source_id)
    
    async def repair_schema_inconsistencies(self, data_source_id: str) -> Dict[str, Any]:
        """
        修复数据一致性问题
        
        Args:
            data_source_id: 数据源ID
        
        Returns:
            修复结果
        """
        try:
            self.logger.info(f"开始修复数据源 {data_source_id} 的一致性问题")
            
            # 检查一致性
            consistency_check = await self._verify_data_consistency(data_source_id)
            
            if consistency_check.get("consistent", False):
                return {
                    "success": True,
                    "message": "数据一致性良好，无需修复",
                    "repaired": False,
                    "consistency_check": consistency_check
                }
            
            # 记录发现的问题
            issues = consistency_check.get("issues", [])
            self.logger.warning(f"发现 {len(issues)} 个数据一致性问题: {issues}")
            
            repair_actions = []
            
            # 修复没有列信息的表
            incomplete_tables = []
            for issue in issues:
                if "缺少列信息" in issue:
                    table_name = issue.split("表 ")[1].split(" ")[0]
                    incomplete_tables.append(table_name)
            
            if incomplete_tables:
                repair_result = await self._repair_incomplete_tables(data_source_id, incomplete_tables)
                repair_actions.append({
                    "action": "repair_incomplete_tables",
                    "tables": incomplete_tables,
                    "result": repair_result
                })
            
            # 清理无效记录
            cleanup_result = await self._cleanup_invalid_records(data_source_id)
            repair_actions.append({
                "action": "cleanup_invalid_records",
                "result": cleanup_result
            })
            
            # 再次验证一致性
            final_check = await self._verify_data_consistency(data_source_id)
            
            return {
                "success": True,
                "message": f"修复完成，处理了 {len(repair_actions)} 个修复动作",
                "repaired": True,
                "initial_issues": len(issues),
                "repair_actions": repair_actions,
                "final_consistency": final_check,
                "improvement": len(issues) - len(final_check.get("issues", []))
            }
            
        except Exception as e:
            self.logger.error(f"修复数据一致性失败: {e}")
            try:
                self.db_session.rollback()
            except:
                pass
            return {"success": False, "error": str(e)}
    
    async def _repair_incomplete_tables(self, data_source_id: str, table_names: List[str]) -> Dict[str, Any]:
        """修复缺少列信息的表"""
        try:
            # 获取数据源
            data_source = self.db_session.query(DataSource).filter(
                DataSource.id == data_source_id
            ).first()
            
            if not data_source:
                return {"success": False, "error": "数据源不存在"}
            
            # 重新获取这些表的结构信息
            from app.services.data.connectors.connector_factory import create_connector
            connector = create_connector(data_source)
            
            await connector.connect()
            try:
                repaired_tables = []
                failed_tables = []
                
                for table_name in table_names:
                    try:
                        schema_info = await connector.get_table_schema(table_name)
                        if "error" not in schema_info:
                            # 更新表的列信息
                            table_schema = self.db_session.query(TableSchema).filter(
                                and_(
                                    TableSchema.data_source_id == data_source_id,
                                    TableSchema.table_name == table_name,
                                    TableSchema.is_active == True
                                )
                            ).first()
                            
                            if table_schema:
                                table_schema.columns_info = schema_info.get("columns", [])
                                table_schema.updated_at = datetime.utcnow()
                                repaired_tables.append(table_name)
                        else:
                            failed_tables.append(table_name)
                    except Exception as e:
                        self.logger.warning(f"修复表 {table_name} 失败: {e}")
                        failed_tables.append(table_name)
                
                self.db_session.commit()
                return {
                    "success": True,
                    "repaired_tables": repaired_tables,
                    "failed_tables": failed_tables,
                    "count": len(repaired_tables)
                }
                
            finally:
                await connector.disconnect()
                
        except Exception as e:
            self.logger.error(f"修复不完整表失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _cleanup_invalid_records(self, data_source_id: str) -> Dict[str, Any]:
        """清理无效记录"""
        try:
            cleaned_schemas = 0
            cleaned_columns = 0
            
            # 清理没有表名的表结构记录
            invalid_schemas = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.table_name.is_(None)
                )
            ).all()
            
            for schema in invalid_schemas:
                schema.is_active = False
                schema.updated_at = datetime.utcnow()
                cleaned_schemas += 1
            
            # 清理没有关联表结构的列记录
            from sqlalchemy import exists
            orphaned_columns = self.db_session.query(ColumnSchema).filter(
                ~exists().where(
                    and_(
                        TableSchema.id == ColumnSchema.table_schema_id,
                        TableSchema.data_source_id == data_source_id,
                        TableSchema.is_active == True
                    )
                )
            ).all()
            
            for column in orphaned_columns:
                self.db_session.delete(column)
                cleaned_columns += 1
            
            self.db_session.commit()
            
            return {
                "success": True,
                "cleaned_schemas": cleaned_schemas,
                "cleaned_columns": cleaned_columns,
                "total_cleaned": cleaned_schemas + cleaned_columns
            }
            
        except Exception as e:
            self.logger.error(f"清理无效记录失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _cleanup_old_schemas_in_session(self, data_source_id: str, session: Session):
        """在指定会话中清理旧的表结构信息"""
        try:
            old_schemas = session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True
                )
            ).all()
            
            for schema in old_schemas:
                schema.is_active = False
                schema.updated_at = datetime.utcnow()
            
            self.logger.info(f"在会话中标记 {len(old_schemas)} 个旧表结构为非活跃状态")
            
        except Exception as e:
            self.logger.error(f"在会话中清理旧表结构失败: {e}")
            raise
    
    async def _process_single_table(
        self, 
        data_source: DataSource, 
        table_name: str, 
        connector, 
        session: Session,
        stored_tables: list,
        failed_tables: list
    ):
        """处理单个表的结构信息"""
        try:
            # 获取表结构
            schema_info = await connector.get_table_schema(table_name)
            if "error" not in schema_info:
                # 存储表结构
                table_schema = await self._store_table_schema_in_session(
                    data_source, table_name, schema_info, session
                )
                stored_tables.append(table_schema)
                
                # 获取表统计信息（如果连接器支持的话）
                if hasattr(connector, 'get_table_statistics'):
                    try:
                        stats_info = await connector.get_table_statistics(table_name)
                        if "error" not in stats_info:
                            await self._update_table_statistics_in_session(table_schema, stats_info, session)
                    except Exception as stats_e:
                        self.logger.warning(f"获取表 {table_name} 统计信息失败: {stats_e}")
            else:
                failed_tables.append({
                    "table": table_name,
                    "error": schema_info.get("error", "未知错误")
                })
                
        except Exception as e:
            self.logger.warning(f"处理表 {table_name} 时出错: {e}")
            failed_tables.append({
                "table": table_name,
                "error": str(e)
            })
    
    async def _store_table_schema_in_session(
        self, 
        data_source: DataSource, 
        table_name: str, 
        schema_info: Dict[str, Any],
        session: Session
    ) -> TableSchema:
        """在指定会话中存储表结构"""
        
        # 检查是否已存在该表的结构信息
        existing_schema = session.query(TableSchema).filter(
            and_(
                TableSchema.data_source_id == data_source.id,
                TableSchema.table_name == table_name
            )
        ).first()
        
        # 准备表结构数据
        schema_data = {
            "table_name": table_name,
            "columns_info": schema_info.get("columns", []),
            "total_columns": len(schema_info.get("columns", [])),
            "is_active": True,
            "is_analyzed": True,
            "updated_at": datetime.utcnow()
        }
        
        if existing_schema:
            # 更新现有记录
            for key, value in schema_data.items():
                setattr(existing_schema, key, value)
            table_schema = existing_schema
        else:
            # 创建新记录
            table_schema = TableSchema(
                data_source_id=data_source.id,
                **schema_data
            )
            session.add(table_schema)
        
        # 存储列信息
        await self._store_column_schemas_in_session(table_schema, schema_info.get("columns", []), session)
        
        return table_schema
    
    async def _store_column_schemas_in_session(
        self, 
        table_schema: TableSchema, 
        columns_info: List[Dict[str, Any]],
        session: Session
    ):
        """在指定会话中存储列结构信息"""
        
        for col_info in columns_info:
            # 检查列是否已存在
            existing_column = session.query(ColumnSchema).filter(
                and_(
                    ColumnSchema.table_schema_id == table_schema.id,
                    ColumnSchema.column_name == col_info.get("name")
                )
            ).first()
            
            # 标准化数据类型
            normalized_type = self.type_normalizer.normalize_type(col_info.get("type", ""))
            
            column_data = {
                "column_name": col_info.get("name"),
                "column_type": col_info.get("type", ""),
                "normalized_type": normalized_type.value if hasattr(normalized_type, 'value') else str(normalized_type),
                "is_nullable": col_info.get("nullable", True),
                "is_primary_key": col_info.get("key", "") == "PRI",
                "default_value": col_info.get("default"),
                "column_size": self.type_normalizer.extract_column_size(col_info.get("type", "")),
                "precision": self.type_normalizer.extract_precision(col_info.get("type", "")),
                "scale": self.type_normalizer.extract_scale(col_info.get("type", "")),
                "comment": col_info.get("comment", "")  # 新增注释字段存储
            }
            
            if existing_column:
                # 更新现有列
                for key, value in column_data.items():
                    setattr(existing_column, key, value)
                existing_column.updated_at = datetime.utcnow()
            else:
                # 创建新列
                column_schema = ColumnSchema(
                    table_schema_id=table_schema.id,
                    **column_data
                )
                session.add(column_schema)
    
    async def _update_table_statistics_in_session(
        self, 
        table_schema: TableSchema, 
        stats_info: Dict[str, Any],
        session: Session
    ):
        """在指定会话中更新表统计信息"""
        
        # 转换numpy类型为Python原生类型
        rows = stats_info.get("rows")
        data_length = stats_info.get("data_length")
        
        table_schema.estimated_row_count = int(rows) if rows is not None else None
        table_schema.table_size_bytes = int(data_length) if data_length is not None else None
        table_schema.last_analyzed = datetime.utcnow()
    
    def get_discovery_status(self, data_source_id: str) -> Dict[str, Any]:
        """
        获取表结构发现状态
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            发现状态信息
        """
        try:
            table_count = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True
                )
            ).count()
            
            analyzed_count = self.db_session.query(TableSchema).filter(
                and_(
                    TableSchema.data_source_id == data_source_id,
                    TableSchema.is_active == True,
                    TableSchema.is_analyzed == True
                )
            ).count()
            
            return {
                "success": True,
                "total_tables": table_count,
                "analyzed_tables": analyzed_count,
                "discovery_complete": table_count > 0
            }
            
        except Exception as e:
            self.logger.error(f"获取发现状态失败: {e}")
            return {"success": False, "error": str(e)}
