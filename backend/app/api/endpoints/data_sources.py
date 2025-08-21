"""数据源管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel, require_owner
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.data_source import DataSource as DataSourceModel
from app.schemas.data_source import DataSourceCreate, DataSourceUpdate, DataSource as DataSourceSchema
from app.crud.crud_data_source import crud_data_source
from app.core.dependencies import get_current_user
from app.crud.crud_data_source import get_wide_table_data
from app.core.data_source_utils import parse_data_source_id, format_data_source_info
import logging
import time

router = APIRouter()
logger = logging.getLogger(__name__)


def resolve_data_source_id(data_source_id: str, user_id: UUID, db: Session) -> DataSourceModel:
    """
    解析数据源ID并返回数据源对象
    支持UUID、slug、name、display_name等格式
    """
    data_source = parse_data_source_id(data_source_id, user_id, db)
    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
    return data_source


async def _discover_and_cache_schema(data_source: DataSourceModel):
    """发现并缓存数据源的表结构"""
    try:
        logger.info(f"开始发现数据源表结构: {data_source.name}")
        
        from app.services.data.schemas.schema_discovery_service import SchemaDiscoveryService
        
        # 使用后台任务发现表结构，避免阻塞用户请求
        import asyncio
        
        async def discover_schema():
            try:
                from app.db.session import get_db_session
                with get_db_session() as db:
                    service = SchemaDiscoveryService(db)
                    result = await service.discover_and_store_schemas(str(data_source.id))
                    if result.get("success"):
                        logger.info(f"表结构发现完成: {data_source.name}, 发现 {result.get('tables_count', 0)} 个表")
                    else:
                        logger.warning(f"表结构发现失败: {data_source.name}, 错误: {result.get('error')}")
            except Exception as e:
                logger.error(f"表结构发现失败: {data_source.name}, 错误: {e}")
        
        # 在后台执行表结构发现
        asyncio.create_task(discover_schema())
        
    except Exception as e:
        logger.error(f"启动表结构发现任务失败: {data_source.name}, 错误: {e}")


@router.get("/", response_model=ApiResponse)
async def get_data_sources(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    source_type: Optional[str] = Query(None, description="数据源类型"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取数据源列表"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    query = db.query(DataSourceModel).filter(DataSourceModel.user_id == user_id)
    
    if source_type:
        query = query.filter(DataSourceModel.source_type == source_type)
    
    if is_active is not None:
        query = query.filter(DataSourceModel.is_active == is_active)
    
    if search:
        query = query.filter(DataSourceModel.name.contains(search))
    
    total = query.count()
    data_sources = query.offset(skip).limit(limit).all()
    data_source_schemas = [DataSourceSchema.model_validate(ds) for ds in data_sources]
    data_source_dicts = [ds.model_dump() | {"unique_id": str(ds.id)} for ds in data_source_schemas]
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=data_source_dicts,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_data_source(
    data_source: DataSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建数据源"""
    from uuid import UUID
    try:
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        data_source_obj = crud_data_source.create_with_user(
            db, 
            obj_in=data_source, 
            user_id=user_id
        )
        
        # 异步启动表结构发现任务
        await _discover_and_cache_schema(data_source_obj)
        
        data_source_schema = DataSourceSchema.model_validate(data_source_obj)
        data_source_dict = data_source_schema.model_dump()
        data_source_dict['unique_id'] = str(data_source_dict.get('id'))
        return {"id": data_source_dict["id"], **data_source_dict}
    except IntegrityError as e:
        db.rollback()
        return ApiResponse(
            success=False,
            error="数据源名称已存在，请更换名称",
            message="数据源创建失败"
        )
    except Exception as e:
        db.rollback()
        return ApiResponse(
            success=False,
            error=str(e),
            message="数据源创建失败"
        )


@router.get("/{data_source_id}", response_model=ApiResponse)
async def get_data_source(
    data_source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取特定数据源，支持多种ID格式"""
    # 使用新的ID解析系统
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    data_source_schema = DataSourceSchema.model_validate(data_source)
    data_source_dict = data_source_schema.model_dump()
    data_source_dict['unique_id'] = str(data_source_dict.get('id'))
    return ApiResponse(
        success=True,
        data=data_source_dict,
        message="获取数据源成功"
    )


@router.put("/{data_source_id}", response_model=ApiResponse)
async def update_data_source(
    data_source_id: str,
    data_source_update: DataSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新数据源，支持多种ID格式"""
    # 使用新的ID解析系统
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    
    data_source = crud_data_source.update(
        db, 
        db_obj=data_source, 
        obj_in=data_source_update
    )
    data_source_schema = DataSourceSchema.model_validate(data_source)
    data_source_dict = data_source_schema.model_dump()
    data_source_dict['unique_id'] = str(data_source_dict.get('id'))
    return ApiResponse(
        success=True,
        data=data_source_dict,
        message="数据源更新成功"
    )


@router.delete("/{data_source_id}", response_model=ApiResponse)
async def delete_data_source(
    data_source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除数据源，支持多种ID格式"""
    # 使用新的ID解析系统
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    
    crud_data_source.remove(db, id=data_source.id)
    
    return ApiResponse(
        success=True,
        data={"data_source_id": data_source_id},
        message="数据源删除成功"
    )


@router.post("/{data_source_id}/test", response_model=ApiResponse)
async def test_data_source(
    data_source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试数据源连接，支持多种ID格式"""
    import time
    from ...services.data_sources import data_source_service
    
    # 使用新的ID解析系统
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    
    try:
        # 使用数据源服务进行真实连接测试
        start_time = time.time()
        test_result = await data_source_service.test_connection(str(data_source.id))
        response_time = time.time() - start_time
        
        if test_result.get("success", False):
            return ApiResponse(
                success=True,
                data={
                    "connection_status": "success",
                    "response_time": round(response_time, 3),
                    "data_source_name": data_source.name,
                    "message": test_result.get("message", "Connection successful"),
                    "details": test_result
                },
                message="数据源连接测试成功"
            )
        else:
            return ApiResponse(
                success=False,
                data={
                    "connection_status": "failed",
                    "response_time": round(response_time, 3),
                    "data_source_name": data_source.name,
                    "error": test_result.get("error", "Unknown error")
                },
                message="数据源连接测试失败"
            )
    except Exception as e:
        return ApiResponse(
            success=False,
            data={
                "connection_status": "error",
                "response_time": 0,
                "data_source_name": data_source.name,
                "error": str(e)
            },
            message=f"数据源连接测试出错: {str(e)}"
        )


@router.post("/{data_source_id}/sync", response_model=ApiResponse)
async def sync_data_source(
    data_source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """同步数据源，支持多种ID格式"""
    # 使用新的ID解析系统
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    
    # 实际执行数据源同步逻辑
    try:
        from ...services.data_sources import data_source_service
        sync_result = await data_source_service.sync_data_source(str(data_source.id))
        
        if sync_result.get("success"):
            return ApiResponse(
                success=True,
                data={
                    "sync_status": "success",
                    "records_synced": sync_result.get("records_count", 0),
                    "data_source_name": data_source.name,
                    "details": sync_result
                },
                message="数据源同步成功"
            )
        else:
            return ApiResponse(
                success=False,
                data={
                    "sync_status": "failed",
                    "data_source_name": data_source.name,
                    "error": sync_result.get("error", "未知错误")
                },
                message="数据源同步失败"
            )
    except Exception as e:
        return ApiResponse(
            success=False,
            data={
                "sync_status": "error",
                "data_source_name": data_source.name,
                "error": str(e)
            },
            message=f"数据源同步出错: {str(e)}"
        )


@router.put("/{data_source_id}/upload", response_model=ApiResponse)
async def upload_data_source_file(
    data_source_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上传文件内容到已创建的数据源，支持多种ID格式"""
    # 使用新的ID解析系统
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    
    # 读取文件内容
    content = await file.read()
    
    # 根据文件扩展名确定数据源类型
    file_extension = file.filename.split('.')[-1].lower() if file.filename else 'csv'
    source_type_map = {
        'csv': 'csv',
        'xlsx': 'excel',
        'xls': 'excel',
        'json': 'api',
        'sql': 'sql'
    }
    source_type = source_type_map.get(file_extension, 'csv')
    
    # 更新数据源
    update_data = {
        "source_type": source_type,
        "connection_string": f"/uploads/{current_user.id}/{file.filename}",
        "original_filename": file.filename,
        "file_size": len(content)
    }
    
    # TODO: 实际保存文件到磁盘/对象存储
    # 这里应该将文件保存到用户专属目录
    
    updated_data_source = crud_data_source.update(
        db, db_obj=data_source, obj_in=update_data
    )
    
    return ApiResponse(
        success=True,
        data=updated_data_source,
        message="数据源文件上传成功"
    )


@router.get("/{data_source_id}/wide-table", response_model=ApiResponse)
async def get_wide_table(
    data_source_id: str,
    limit: int = Query(100, ge=1, le=1000, description="每页条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定数据源的宽表数据（支持分页）
    支持多种ID格式：UUID、slug、name、display_name
    """
    # 使用新的ID解析系统
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    table_name = data_source.table_name
    if not table_name:
        raise HTTPException(status_code=400, detail="数据源未配置表名")
    try:
        fields, rows = get_wide_table_data(db, table_name, limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"宽表数据查询失败: {str(e)}")
    return ApiResponse(
        success=True,
        data={"fields": fields, "rows": rows, "limit": limit, "offset": offset},
        message="宽表数据获取成功"
    )


@router.get("/{data_source_id}/tables", response_model=ApiResponse)
async def get_data_source_tables(
    data_source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取数据源的表列表
    支持多种ID格式：UUID、slug、name、display_name
    """
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    
    try:
        from app.services.data.connectors.connector_factory import create_connector
        
        start_time = time.time()
        connector = create_connector(data_source)
        await connector.connect()
        
        try:
            # 获取表列表
            tables = await connector.get_tables()
            
            # 获取数据库列表
            databases = await connector.get_databases()
            
            response_time = time.time() - start_time
            
            return ApiResponse(
                success=True,
                data={
                    "tables": tables,
                    "databases": databases,
                    "total_tables": len(tables),
                    "total_databases": len(databases),
                    "response_time": round(response_time, 3),
                    "data_source_name": data_source.name
                },
                message=f"成功获取 {len(tables)} 个表"
            )
            
        finally:
            await connector.disconnect()
            
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        return ApiResponse(
            success=False,
            data={"error": str(e)},
            message="获取表列表失败"
        )


@router.get("/{data_source_id}/tables/{table_name}/schema", response_model=ApiResponse)
async def get_table_schema(
    data_source_id: str,
    table_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定表的结构信息
    支持多种ID格式：UUID、slug、name、display_name
    """
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    
    try:
        from app.services.data.connectors.connector_factory import create_connector
        
        start_time = time.time()
        connector = create_connector(data_source)
        await connector.connect()
        
        try:
            # 获取表结构
            schema_info = await connector.get_table_schema(table_name)
            response_time = time.time() - start_time
            
            if "error" in schema_info:
                return ApiResponse(
                    success=False,
                    data={"error": schema_info["error"]},
                    message=f"获取表 {table_name} 结构失败"
                )
            
            return ApiResponse(
                success=True,
                data={
                    "table_name": table_name,
                    "schema": schema_info,
                    "response_time": round(response_time, 3),
                    "data_source_name": data_source.name
                },
                message=f"成功获取表 {table_name} 的结构信息"
            )
            
        finally:
            await connector.disconnect()
            
    except Exception as e:
        logger.error(f"获取表结构失败: {e}")
        return ApiResponse(
            success=False,
            data={"error": str(e)},
            message=f"获取表 {table_name} 结构失败"
        )


@router.get("/{data_source_id}/fields", response_model=ApiResponse)
async def get_data_source_fields(
    data_source_id: str,
    table_name: Optional[str] = Query(None, description="指定表名，不指定则获取所有字段"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取数据源的字段列表
    支持多种ID格式：UUID、slug、name、display_name
    """
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    
    try:
        from app.services.data.connectors.connector_factory import create_connector
        
        start_time = time.time()
        connector = create_connector(data_source)
        await connector.connect()
        
        try:
            # 获取字段列表
            fields = await connector.get_fields(table_name)
            response_time = time.time() - start_time
            
            return ApiResponse(
                success=True,
                data={
                    "fields": fields,
                    "table_name": table_name,
                    "total_fields": len(fields),
                    "response_time": round(response_time, 3),
                    "data_source_name": data_source.name
                },
                message=f"成功获取 {len(fields)} 个字段"
            )
            
        finally:
            await connector.disconnect()
            
    except Exception as e:
        logger.error(f"获取字段列表失败: {e}")
        return ApiResponse(
            success=False,
            data={"error": str(e)},
            message="获取字段列表失败"
        )


@router.post("/{data_source_id}/query", response_model=ApiResponse)
async def execute_query(
    data_source_id: str,
    query_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    在数据源上执行SQL查询
    支持多种ID格式：UUID、slug、name、display_name
    """
    data_source = resolve_data_source_id(data_source_id, current_user.id, db)
    
    sql = query_data.get("sql", "").strip()
    if not sql:
        return ApiResponse(
            success=False,
            data={"error": "SQL查询不能为空"},
            message="SQL查询不能为空"
        )
    
    # 安全检查：只允许SELECT查询
    if not sql.upper().startswith("SELECT"):
        return ApiResponse(
            success=False,
            data={"error": "只允许SELECT查询"},
            message="安全限制：只允许SELECT查询"
        )
    
    try:
        from app.services.data.connectors.connector_factory import create_connector
        
        start_time = time.time()
        connector = create_connector(data_source)
        await connector.connect()
        
        try:
            # 执行查询
            result = await connector.execute_query(sql)
            response_time = time.time() - start_time
            
            if hasattr(result, 'data') and not result.data.empty:
                data_dict = result.data.to_dict('records')
                columns = result.data.columns.tolist()
                
                return ApiResponse(
                    success=True,
                    data={
                        "rows": data_dict,
                        "columns": columns,
                        "row_count": len(data_dict),
                        "response_time": round(response_time, 3),
                        "execution_time": getattr(result, 'execution_time', response_time),
                        "data_source_name": data_source.name
                    },
                    message=f"查询成功，返回 {len(data_dict)} 行数据"
                )
            else:
                return ApiResponse(
                    success=True,
                    data={
                        "rows": [],
                        "columns": [],
                        "row_count": 0,
                        "response_time": round(response_time, 3),
                        "data_source_name": data_source.name
                    },
                    message="查询成功，无数据返回"
                )
            
        finally:
            await connector.disconnect()
            
    except Exception as e:
        logger.error(f"执行查询失败: {e}")
        return ApiResponse(
            success=False,
            data={"error": str(e), "sql": sql},
            message="查询执行失败"
        )
