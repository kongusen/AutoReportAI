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

router = APIRouter()


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
    """获取特定数据源"""
    try:
        ds_uuid = UUID(data_source_id)
    except Exception:
        raise HTTPException(status_code=422, detail="数据源ID格式错误")
    data_source = crud_data_source.get(db, id=ds_uuid)
    if not data_source or data_source.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
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
    """更新数据源"""
    try:
        ds_uuid = UUID(data_source_id)
    except Exception:
        raise HTTPException(status_code=422, detail="数据源ID格式错误")
    data_source = crud_data_source.get(db, id=ds_uuid)
    if not data_source or data_source.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
    
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
    """删除数据源"""
    try:
        ds_uuid = UUID(data_source_id)
    except Exception:
        raise HTTPException(status_code=422, detail="数据源ID格式错误")
    data_source = crud_data_source.get(db, id=ds_uuid)
    if not data_source or data_source.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
    
    crud_data_source.remove(db, id=ds_uuid)
    
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
    """测试数据源连接"""
    import time
    from ...services.data_source_service import data_source_service
    
    try:
        ds_uuid = UUID(data_source_id)
    except Exception:
        raise HTTPException(status_code=422, detail="数据源ID格式错误")
    data_source = crud_data_source.get(db, id=ds_uuid)
    if not data_source or data_source.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
    
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
    """同步数据源"""
    try:
        ds_uuid = UUID(data_source_id)
    except Exception:
        raise HTTPException(status_code=422, detail="数据源ID格式错误")
    data_source = crud_data_source.get(db, id=ds_uuid)
    if not data_source or data_source.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
    
    # 这里应该实现实际的数据同步逻辑
    # 暂时返回模拟结果
    return ApiResponse(
        success=True,
        data={
            "sync_status": "success",
            "records_synced": 100,
            "data_source_name": data_source.name
        },
        message="数据源同步成功"
    )


@router.post("/upload", response_model=ApiResponse)
async def upload_data_source_file(
    file: UploadFile = File(...),
    name: str = Query(..., description="数据源名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上传文件作为数据源"""
    # 这里应该实现文件上传和处理逻辑
    # 暂时返回模拟结果
    data_source_data = DataSourceCreate(
        name=name,
        source_type="csv",
        connection_string=f"/uploads/{file.filename}",
        is_active=True
    )
    
    data_source_obj = crud_data_source.create_with_user(
        db, 
        obj_in=data_source_data, 
        user_id=current_user.id
    )
    
    return ApiResponse(
        success=True,
        data=data_source_obj,
        message="文件上传并创建数据源成功"
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
    """
    try:
        ds_uuid = UUID(data_source_id)
    except Exception:
        raise HTTPException(status_code=422, detail="数据源ID格式错误")
    data_source = crud_data_source.get(db, id=ds_uuid)
    if not data_source or data_source.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
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
