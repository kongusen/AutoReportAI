"""
优化的数据源API端点
"""

from typing import List, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.optimized.base_router import BaseRouter, APIResponse
from app.models.optimized.user import User
from app.models.optimized.data_source import DataSourceType, ConnectionStatus
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate, DataSourceResponse
from app.services.optimized import services


class DataSourceRouter(BaseRouter):
    """数据源路由"""
    
    def __init__(self):
        super().__init__(
            service=services.data_source,
            prefix="/data-sources",
            tags=["数据源管理"],
            response_model=DataSourceResponse,
            create_schema=DataSourceCreate,
            update_schema=DataSourceUpdate
        )
        
        # 注册自定义路由
        self._register_custom_routes()
    
    def _register_custom_routes(self):
        """注册自定义路由"""
        
        @self.router.post("/{id}/test-connection", response_model=APIResponse)
        async def test_connection(
            id: UUID,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """测试数据源连接"""
            try:
                result = await self.service.test_connection(
                    db, data_source_id=id, user_id=current_user.id
                )
                return APIResponse(
                    message="连接测试完成",
                    data=result
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"连接测试失败: {str(e)}"
                )
        
        @self.router.get("/types/{source_type}", response_model=APIResponse)
        async def get_by_type(
            source_type: DataSourceType,
            include_inactive: bool = Query(False, description="包含非活跃数据源"),
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """根据类型获取数据源"""
            try:
                data_sources = self.service.get_by_type(
                    db,
                    source_type=source_type,
                    user_id=current_user.id,
                    include_inactive=include_inactive
                )
                return APIResponse(data=data_sources)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取数据源失败: {str(e)}"
                )
        
        @self.router.get("/healthy", response_model=APIResponse)
        async def get_healthy_sources(
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """获取健康的数据源"""
            try:
                data_sources = self.service.get_healthy_sources(
                    db, user_id=current_user.id
                )
                return APIResponse(data=data_sources)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取健康数据源失败: {str(e)}"
                )
        
        @self.router.get("/database-sources", response_model=APIResponse)
        async def get_database_sources(
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """获取数据库类型的数据源"""
            try:
                data_sources = self.service.get_database_sources(
                    db, user_id=current_user.id
                )
                return APIResponse(data=data_sources)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取数据库数据源失败: {str(e)}"
                )
        
        @self.router.get("/summary", response_model=APIResponse)
        async def get_connection_summary(
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """获取连接状态摘要"""
            try:
                summary = self.service.get_connection_summary(
                    db, user_id=current_user.id
                )
                return APIResponse(data=summary)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"获取连接摘要失败: {str(e)}"
                )
        
        @self.router.post("/batch-test", response_model=APIResponse)
        async def batch_test_connections(
            data_source_ids: Optional[List[UUID]] = None,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """批量测试连接"""
            try:
                result = await self.service.batch_test_connections(
                    db,
                    data_source_ids=data_source_ids,
                    user_id=current_user.id
                )
                return APIResponse(
                    message="批量连接测试完成",
                    data=result
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"批量测试失败: {str(e)}"
                )
        
        @self.router.post("/{id}/sync-schema", response_model=APIResponse)
        async def sync_schema_info(
            id: UUID,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
            """同步数据源架构信息"""
            try:
                result = self.service.sync_schema_info(
                    db,
                    data_source_id=id,
                    user_id=current_user.id
                )
                return APIResponse(
                    message="架构信息同步完成",
                    data=result
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"架构同步失败: {str(e)}"
                )


# 创建路由器实例
data_source_router = DataSourceRouter()
router = data_source_router.get_router()