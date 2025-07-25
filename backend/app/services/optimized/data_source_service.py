"""
优化的数据源服务
统一数据源管理，支持连接测试和健康监控
"""

import asyncio
from typing import Dict, List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session

from app.crud.optimized.crud_data_source import crud_data_source
from app.models.optimized.data_source import DataSource, DataSourceType, ConnectionStatus
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate
from app.services.optimized.base_service import BaseService, ValidationError, ServiceException
from app.services.connectors.doris_connector import DorisConnector, DorisConfig


class DataSourceService(BaseService):
    """数据源服务"""
    
    def __init__(self):
        super().__init__(crud_data_source, "DataSource")
        # 延迟初始化连接器，避免在服务启动时就需要配置
        self.connectors = {}
    
    def _get_connector(self, data_source: DataSource):
        """根据数据源获取连接器"""
        if data_source.source_type == DataSourceType.DORIS:
            config = DorisConfig(
                fe_hosts=[data_source.connection_config.get("fe_host", "localhost")],
                be_hosts=[data_source.connection_config.get("be_host", "localhost")],
                database=data_source.connection_config.get("database", "default"),
                username=data_source.connection_config.get("username", "root"),
                password=data_source.connection_config.get("password", ""),
                query_port=data_source.connection_config.get("query_port", 9030),
                http_port=data_source.connection_config.get("http_port", 8030)
            )
            return DorisConnector(config)
        return None
    
    def _validate_create(self, obj_in: DataSourceCreate, user_id: Union[UUID, str] = None):
        """验证数据源创建"""
        # 验证连接配置
        if not obj_in.connection_config:
            raise ValidationError("连接配置不能为空", "connection_config")
        
        # 根据数据源类型验证配置
        if obj_in.source_type == DataSourceType.DORIS:
            required_fields = ["fe_host", "query_port", "username", "password", "database"]
        elif obj_in.source_type == DataSourceType.POSTGRESQL:
            required_fields = ["host", "port", "username", "password", "database"]
        elif obj_in.source_type == DataSourceType.MYSQL:
            required_fields = ["host", "port", "username", "password", "database"]
        else:
            required_fields = []
        
        for field in required_fields:
            if field not in obj_in.connection_config:
                raise ValidationError(f"缺少必要的连接参数: {field}", "connection_config")
    
    def _validate_update(self, db_obj: DataSource, obj_in: DataSourceUpdate, user_id: Union[UUID, str] = None):
        """验证数据源更新"""
        # 如果更新连接配置，需要重新验证
        if hasattr(obj_in, 'connection_config') and obj_in.connection_config:
            # 创建临时对象进行验证
            temp_create = DataSourceCreate(
                name=db_obj.name,
                source_type=db_obj.source_type,
                connection_config=obj_in.connection_config
            )
            self._validate_create(temp_create, user_id)
    
    async def test_connection(
        self,
        db: Session,
        *,
        data_source_id: Union[UUID, str],
        user_id: Union[UUID, str] = None
    ) -> Dict[str, any]:
        """测试数据源连接"""
        try:
            self._log_operation("test_connection", {"data_source_id": str(data_source_id)})
            
            # 获取数据源
            data_source = self.get_by_id(db, id=data_source_id, user_id=user_id)
            
            # 根据类型选择连接器
            connector = self._get_connector(data_source)
            if not connector:
                # 对于不支持的类型，使用基本连接测试
                result = await self._basic_connection_test(data_source)
            else:
                result = await connector.test_connection(data_source.connection_config)
            
            # 更新连接状态
            status = ConnectionStatus.CONNECTED if result["success"] else ConnectionStatus.FAILED
            error_msg = None if result["success"] else result.get("error", "连接失败")
            
            self.crud.update_connection_status(
                db,
                data_source_id=data_source_id,
                status=status,
                error_message=error_msg
            )
            
            return {
                "success": result["success"],
                "message": result.get("message", "连接测试完成"),
                "response_time": result.get("response_time", 0),
                "details": result.get("details", {})
            }
            
        except Exception as e:
            self._handle_error("test_connection", e, {"data_source_id": str(data_source_id)})
    
    async def _basic_connection_test(self, data_source: DataSource) -> Dict[str, any]:
        """基本连接测试"""
        import time
        start_time = time.time()
        
        try:
            if data_source.source_type in [DataSourceType.POSTGRESQL, DataSourceType.MYSQL]:
                import sqlalchemy
                engine = sqlalchemy.create_engine(data_source.connection_string)
                with engine.connect() as conn:
                    result = conn.execute(sqlalchemy.text("SELECT 1"))
                    result.fetchone()
                engine.dispose()
            else:
                # 其他类型的基本测试
                return {
                    "success": False,
                    "error": f"不支持的数据源类型: {data_source.source_type}",
                    "response_time": time.time() - start_time
                }
            
            return {
                "success": True,
                "message": "连接成功",
                "response_time": time.time() - start_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    def get_by_type(
        self,
        db: Session,
        *,
        source_type: DataSourceType,
        user_id: Union[UUID, str] = None,
        include_inactive: bool = False
    ) -> List[DataSource]:
        """根据类型获取数据源"""
        try:
            self._log_operation("get_by_type", {"source_type": source_type.value})
            return self.crud.get_by_type(
                db,
                source_type=source_type,
                user_id=user_id,
                include_inactive=include_inactive
            )
        except Exception as e:
            self._handle_error("get_by_type", e, {"source_type": source_type.value})
    
    def get_healthy_sources(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[DataSource]:
        """获取健康的数据源"""
        try:
            self._log_operation("get_healthy_sources")
            return self.crud.get_healthy_sources(db, user_id=user_id)
        except Exception as e:
            self._handle_error("get_healthy_sources", e)
    
    def get_database_sources(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> List[DataSource]:
        """获取数据库类型的数据源"""
        try:
            self._log_operation("get_database_sources")
            return self.crud.get_database_sources(db, user_id=user_id)
        except Exception as e:
            self._handle_error("get_database_sources", e)
    
    def get_connection_summary(
        self,
        db: Session,
        *,
        user_id: Union[UUID, str] = None
    ) -> Dict[str, any]:
        """获取连接状态摘要"""
        try:
            self._log_operation("get_connection_summary")
            return self.crud.get_connection_summary(db, user_id=user_id)
        except Exception as e:
            self._handle_error("get_connection_summary", e)
    
    async def batch_test_connections(
        self,
        db: Session,
        *,
        data_source_ids: List[Union[UUID, str]] = None,
        user_id: Union[UUID, str] = None
    ) -> Dict[str, any]:
        """批量测试连接"""
        try:
            self._log_operation("batch_test_connections", {"count": len(data_source_ids or [])})
            
            if not data_source_ids:
                # 测试用户所有数据源
                data_sources = self.get_list(db, user_id=user_id, limit=1000)
                data_source_ids = [ds.id for ds in data_sources]
            
            # 并发测试连接
            tasks = []
            for ds_id in data_source_ids:
                task = self.test_connection(db, data_source_id=ds_id, user_id=user_id)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            failed_count = len(results) - success_count
            
            return {
                "total_tested": len(results),
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": round((success_count / len(results)) * 100, 2) if results else 0,
                "results": [
                    {"data_source_id": str(ds_id), "result": result}
                    for ds_id, result in zip(data_source_ids, results)
                ]
            }
            
        except Exception as e:
            self._handle_error("batch_test_connections", e)
    
    def sync_schema_info(
        self,
        db: Session,
        *,
        data_source_id: Union[UUID, str],
        user_id: Union[UUID, str] = None
    ) -> Dict[str, any]:
        """同步数据源架构信息"""
        try:
            self._log_operation("sync_schema_info", {"data_source_id": str(data_source_id)})
            
            data_source = self.get_by_id(db, id=data_source_id, user_id=user_id)
            
            # 获取架构信息
            connector = self.connectors.get(data_source.source_type)
            if connector and hasattr(connector, 'get_schema_info'):
                schema_info = connector.get_schema_info(data_source.connection_config)
            else:
                schema_info = {"tables": [], "views": [], "message": "架构信息获取不支持此数据源类型"}
            
            # 更新元数据
            if not data_source.extra_metadata:
                data_source.extra_metadata = {}
            data_source.extra_metadata["schema_info"] = schema_info
            data_source.extra_metadata["last_schema_sync"] = self._get_current_timestamp()
            
            # 保存更新
            db.add(data_source)
            db.commit()
            db.refresh(data_source)
            
            return {
                "success": True,
                "message": "架构信息同步完成",
                "schema_info": schema_info
            }
            
        except Exception as e:
            self._handle_error("sync_schema_info", e, {"data_source_id": str(data_source_id)})
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# 创建服务实例
data_source_service = DataSourceService()