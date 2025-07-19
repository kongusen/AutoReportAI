from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.schemas.base import APIResponse, create_success_response, create_error_response

router = APIRouter(tags=["数据源"])


@router.post(
    "/",
    response_model=schemas.DataSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建数据源",
    description="""
    创建新的数据源配置。
    
    ## 支持的数据源类型
    
    ### 数据库类型
    - **mysql**: MySQL数据库
    - **postgresql**: PostgreSQL数据库
    - **sqlite**: SQLite数据库
    - **oracle**: Oracle数据库
    - **sqlserver**: SQL Server数据库
    
    ### API类型
    - **rest**: REST API
    - **graphql**: GraphQL API
    - **soap**: SOAP API
    
    ### 文件类型
    - **csv**: CSV文件
    - **excel**: Excel文件
    - **json**: JSON文件
    - **xml**: XML文件
    
    ## 配置参数
    每种数据源类型需要不同的配置参数，详见请求体示例。
    
    ## 安全性
    - 敏感信息（如密码）会自动加密存储
    - 支持连接池和SSL连接
    - 提供连接测试功能
    """,
    responses={
        201: {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "MySQL生产数据库",
                        "type": "database",
                        "status": "active",
                        "config": {
                            "host": "localhost",
                            "port": 3306,
                            "database": "production",
                            "username": "user"
                        },
                        "created_at": "2023-12-01T10:00:00Z",
                        "updated_at": "2023-12-01T10:00:00Z"
                    }
                }
            }
        },
        400: {
            "description": "配置错误",
            "content": {
                "application/json": {
                    "example": {"detail": "数据库连接参数无效"}
                }
            }
        }
    }
)
async def create_data_source(
    data_source: schemas.DataSourceCreate,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> schemas.DataSourceResponse:
    """
    Create a new data source.
    """
    # Check if data source with this name already exists
    existing_source = crud.data_source.get_by_name(db, name=data_source.name)
    if existing_source:
        raise HTTPException(
            status_code=400,
            detail="A data source with this name already exists.",
        )

    data_source = crud.data_source.create(db=db, obj_in=data_source)
    return APIResponse[schemas.DataSource](
        success=True,
        message="数据源创建成功",
        data=data_source
    )


@router.get(
    "/",
    response_model=List[schemas.DataSourceResponse],
    summary="获取数据源列表",
    description="""
    获取当前用户的所有数据源列表。
    
    ## 查询参数
    - **skip**: 跳过的记录数（分页）
    - **limit**: 返回的记录数（分页）
    - **type**: 数据源类型过滤（database, api, file）
    - **status**: 状态过滤（active, inactive, error）
    
    ## 返回值
    - 数据源列表，包含基本信息和连接状态
    
    ## 示例
    ```bash
    curl -X GET "http://localhost:8000/api/v1/data-sources?limit=10&type=database" \\
      -H "Authorization: Bearer <token>"
    ```
    """,
    responses={
        200: {
            "description": "获取成功",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "MySQL生产数据库",
                            "type": "database",
                            "status": "active",
                            "config": {
                                "host": "localhost",
                                "port": 3306,
                                "database": "production"
                            },
                            "created_at": "2023-12-01T10:00:00Z",
                            "updated_at": "2023-12-01T10:00:00Z"
                        }
                    ]
                }
            }
        }
    }
)
async def get_data_sources(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    type: Optional[str] = Query(None, description="数据源类型"),
    status: Optional[str] = Query(None, description="状态过滤"),
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> List[schemas.DataSourceResponse]:
    """
    Retrieve data sources.
    """
    sources = crud.data_source.get_multi(db, skip=skip, limit=limit)
    return APIResponse[List[schemas.DataSource]](
        success=True,
        message="数据源列表获取成功",
        data=sources
    )


@router.get("/{source_id}", response_model=APIResponse[schemas.DataSource])
def get_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
):
    """
    Get a specific data source by ID.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    return APIResponse[schemas.DataSource](
        success=True,
        message="数据源获取成功",
        data=source
    )


@router.put("/{source_id}", response_model=APIResponse[schemas.DataSource])
def update_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
    source_in: schemas.DataSourceUpdate,
):
    """
    Update a data source.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    # Check if updating name conflicts with existing
    if source_in.name and source_in.name != source.name:
        existing_source = crud.data_source.get_by_name(db, name=source_in.name)
        if existing_source:
            raise HTTPException(
                status_code=400,
                detail="A data source with this name already exists.",
            )

    updated_source = crud.data_source.update(db=db, db_obj=source, obj_in=source_in)
    return APIResponse[schemas.DataSource](
        success=True,
        message="数据源更新成功",
        data=updated_source
    )


@router.delete("/{source_id}", response_model=APIResponse[schemas.DataSource])
def delete_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
):
    """
    Delete a data source.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    deleted_source = crud.data_source.remove(db=db, id=source_id)
    return APIResponse[schemas.DataSource](
        success=True,
        message="数据源删除成功",
        data=deleted_source
    )


@router.post(
    "/{data_source_id}/test",
    response_model=schemas.ConnectionTestResponse,
    summary="测试数据源连接",
    description="""
    测试指定数据源的连接是否正常。
    
    ## 测试内容
    - 连接可达性
    - 认证信息验证
    - 权限检查
    - 数据读取测试
    
    ## 返回值
    - **success**: 连接是否成功
    - **message**: 测试结果消息
    - **details**: 详细的测试信息
    - **latency**: 连接延迟（毫秒）
    """,
    responses={
        200: {
            "description": "测试完成",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "value": {
                                "success": True,
                                "message": "连接测试成功",
                                "details": {
                                    "host": "localhost",
                                    "port": 3306,
                                    "database": "production",
                                    "tables_count": 15
                                },
                                "latency": 45
                            }
                        },
                        "failure": {
                            "value": {
                                "success": False,
                                "message": "连接失败：无法连接到数据库",
                                "details": {
                                    "error": "Connection timeout",
                                    "host": "localhost",
                                    "port": 3306
                                },
                                "latency": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def test_data_source_connection(
    data_source_id: str,
    current_user: models.User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> schemas.ConnectionTestResponse:
    """
    Test the connection to a data source.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        from app.services.data_processing import DataRetrievalService

        # Create service instance
        data_service = DataRetrievalService()

        # Test connection based on source type
        if source.source_type.value == "sql":
            if not source.connection_string:
                raise ValueError("SQL data source requires connection string")

            # Validate connection string
            from app.core.security_utils import validate_connection_string

            validate_connection_string(source.connection_string)

            # Test connection
            from sqlalchemy import create_engine, text

            engine = create_engine(source.connection_string)
            with engine.connect() as conn:
                # Simple test query
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            test_result = {"msg": "SQL data source connection test successful"}
            return APIResponse[schemas.Msg](
                success=True,
                message="数据源连接测试成功",
                data=test_result
            )

        elif source.source_type.value == "csv":
            if not source.file_path:
                raise ValueError("CSV data source requires file path")

            # Test file access
            import os

            if not os.path.exists(source.file_path):
                raise ValueError(f"CSV file not found: {source.file_path}")

            # Test file reading
            import pandas as pd

            df = pd.read_csv(source.file_path, nrows=1)  # Read just first row

            test_result = {"msg": f"CSV data source connection test successful. Found {len(df.columns)} columns"}
            return APIResponse[schemas.Msg](
                success=True,
                message="数据源连接测试成功",
                data=test_result
            )

        elif source.source_type.value == "api":
            if not source.api_url:
                raise ValueError("API data source requires URL")

            # Test API connection
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=source.api_method or "GET",
                    url=source.api_url,
                    headers=source.api_headers,
                    json=source.api_body,
                    timeout=10.0,
                )
                response.raise_for_status()

            test_result = {"msg": "API data source connection test successful"}
            return APIResponse[schemas.Msg](
                success=True,
                message="数据源连接测试成功",
                data=test_result
            )
        else:
            raise ValueError(f"Unsupported data source type: {source.source_type}")

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Data source connection test failed: {str(e)}"
        )


@router.get("/{source_id}/preview", response_model=APIResponse[dict])
async def preview_data_source(
    *,
    db: Session = Depends(deps.get_db),
    source_id: int,
    limit: int = 10,
):
    """
    Preview data from a data source.
    """
    source = crud.data_source.get(db=db, id=source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        from app.services.data_processing import DataRetrievalService

        # Create service instance
        data_service = DataRetrievalService()

        # Get preview data based on source type
        if source.source_type.value == "sql":
            if not source.connection_string:
                raise ValueError("SQL data source requires connection string")

            # Validate connection string
            from app.core.security_utils import validate_connection_string

            validate_connection_string(source.connection_string)

            # Get preview data
            from sqlalchemy import create_engine, text

            engine = create_engine(source.connection_string)

            # Use the defined query if available, otherwise show tables
            if source.db_query:
                query = f"SELECT * FROM ({source.db_query}) subquery LIMIT {limit}"
            else:
                # Try to get table names
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 10"

            import pandas as pd

            df = pd.read_sql(query, engine)

            preview_data = {
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
                "row_count": len(df),
            }
            return APIResponse[dict](
                success=True,
                message="数据源预览获取成功",
                data=preview_data
            )

        elif source.source_type.value == "csv":
            if not source.file_path:
                raise ValueError("CSV data source requires file path")

            # Get preview data
            import pandas as pd

            df = pd.read_csv(source.file_path, nrows=limit)

            preview_data = {
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
                "row_count": len(df),
            }
            return APIResponse[dict](
                success=True,
                message="数据源预览获取成功",
                data=preview_data
            )

        elif source.source_type.value == "api":
            if not source.api_url:
                raise ValueError("API data source requires URL")

            # Get preview data
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=source.api_method or "GET",
                    url=source.api_url,
                    headers=source.api_headers,
                    json=source.api_body,
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

            # Handle different API response formats
            if isinstance(data, list):
                preview_data = data[:limit]
                columns = list(preview_data[0].keys()) if preview_data else []
            elif isinstance(data, dict):
                # If it's a dict, try to find the data array
                if "data" in data:
                    preview_data = data["data"][:limit]
                    columns = list(preview_data[0].keys()) if preview_data else []
                else:
                    preview_data = [data]
                    columns = list(data.keys())
            else:
                preview_data = [{"value": data}]
                columns = ["value"]

            api_preview_data = {
                "columns": columns,
                "data": preview_data,
                "row_count": len(preview_data),
            }
            return APIResponse[dict](
                success=True,
                message="数据源预览获取成功",
                data=api_preview_data
            )
        else:
            raise ValueError(f"Unsupported data source type: {source.source_type}")

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Data source preview failed: {str(e)}"
        )
