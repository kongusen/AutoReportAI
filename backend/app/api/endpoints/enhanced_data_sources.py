from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.enhanced_data_source import (
    DataSourceType,
    EnhancedDataSource,
    SQLQueryType,
)
from app.services.sql_query_builder import (
    ColumnMapping,
    JoinConfig,
    SQLQueryBuilder,
    WhereCondition,
)

router = APIRouter()


class DataSourceTypeEnum(str, Enum):
    sql = "sql"
    csv = "csv"
    api = "api"
    push = "push"


class SQLQueryTypeEnum(str, Enum):
    single_table = "single_table"
    multi_table = "multi_table"
    custom_view = "custom_view"


class EnhancedDataSourceCreate(BaseModel):
    name: str = Field(..., description="数据源名称")
    source_type: DataSourceTypeEnum
    connection_string: Optional[str] = None
    sql_query_type: SQLQueryTypeEnum = SQLQueryTypeEnum.single_table
    base_query: Optional[str] = None
    join_config: Optional[List[dict]] = None
    column_mapping: Optional[List[dict]] = None
    where_conditions: Optional[List[dict]] = None
    wide_table_name: Optional[str] = None
    api_url: Optional[str] = None
    api_method: Optional[str] = "GET"
    api_headers: Optional[dict] = None
    api_body: Optional[dict] = None
    push_endpoint: Optional[str] = None
    push_auth_config: Optional[dict] = None


class EnhancedDataSourceUpdate(BaseModel):
    name: Optional[str] = None
    connection_string: Optional[str] = None
    base_query: Optional[str] = None
    join_config: Optional[List[dict]] = None
    column_mapping: Optional[List[dict]] = None
    where_conditions: Optional[List[dict]] = None
    wide_table_name: Optional[str] = None
    is_active: Optional[bool] = None


class EnhancedDataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    sql_query_type: str
    wide_table_name: Optional[str]
    is_active: bool
    last_sync_time: Optional[str]

    class Config:
        from_attributes = True


@router.post("/", response_model=EnhancedDataSourceResponse)
def create_enhanced_data_source(
    *,
    db: Session = Depends(deps.get_db),
    data_source_in: EnhancedDataSourceCreate,
):
    """创建增强版数据源"""
    # 检查名称是否已存在
    if (
        db.query(EnhancedDataSource)
        .filter(EnhancedDataSource.name == data_source_in.name)
        .first()
    ):
        raise HTTPException(status_code=400, detail="数据源名称已存在")

    # 验证SQL查询
    if (
        data_source_in.source_type == DataSourceTypeEnum.sql
        and data_source_in.base_query
    ):
        builder = SQLQueryBuilder()
        validation = builder.validate_query(data_source_in.base_query)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400, detail=f"SQL查询验证失败: {validation['error']}"
            )

    data_source = EnhancedDataSource(
        name=data_source_in.name,
        source_type=data_source_in.source_type,
        connection_string=data_source_in.connection_string,
        sql_query_type=data_source_in.sql_query_type,
        base_query=data_source_in.base_query,
        join_config=data_source_in.join_config,
        column_mapping=data_source_in.column_mapping,
        where_conditions=data_source_in.where_conditions,
        wide_table_name=data_source_in.wide_table_name,
        api_url=data_source_in.api_url,
        api_method=data_source_in.api_method,
        api_headers=data_source_in.api_headers,
        api_body=data_source_in.api_body,
        push_endpoint=data_source_in.push_endpoint,
        push_auth_config=data_source_in.push_auth_config,
    )

    db.add(data_source)
    db.commit()
    db.refresh(data_source)

    return data_source


@router.get("/", response_model=List[EnhancedDataSourceResponse])
def read_enhanced_data_sources(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    source_type: Optional[DataSourceTypeEnum] = None,
    is_active: Optional[bool] = None,
):
    """获取增强版数据源列表"""
    query = db.query(EnhancedDataSource)

    if source_type:
        query = query.filter(EnhancedDataSource.source_type == source_type)
    if is_active is not None:
        query = query.filter(EnhancedDataSource.is_active == is_active)

    data_sources = query.offset(skip).limit(limit).all()
    return data_sources


@router.get("/{data_source_id}", response_model=EnhancedDataSourceResponse)
def read_enhanced_data_source(
    *,
    db: Session = Depends(deps.get_db),
    data_source_id: int,
):
    """获取指定增强版数据源"""
    data_source = (
        db.query(EnhancedDataSource)
        .filter(EnhancedDataSource.id == data_source_id)
        .first()
    )
    if not data_source:
        raise HTTPException(status_code=404, detail="数据源未找到")
    return data_source


@router.put("/{data_source_id}", response_model=EnhancedDataSourceResponse)
def update_enhanced_data_source(
    *,
    db: Session = Depends(deps.get_db),
    data_source_id: int,
    data_source_in: EnhancedDataSourceUpdate,
):
    """更新增强版数据源"""
    data_source = (
        db.query(EnhancedDataSource)
        .filter(EnhancedDataSource.id == data_source_id)
        .first()
    )
    if not data_source:
        raise HTTPException(status_code=404, detail="数据源未找到")

    update_data = data_source_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(data_source, field, value)

    db.add(data_source)
    db.commit()
    db.refresh(data_source)

    return data_source


@router.post("/{data_source_id}/build-query")
def build_wide_table_query(
    *,
    db: Session = Depends(deps.get_db),
    data_source_id: int,
):
    """构建宽表查询"""
    data_source = (
        db.query(EnhancedDataSource)
        .filter(EnhancedDataSource.id == data_source_id)
        .first()
    )
    if not data_source:
        raise HTTPException(status_code=404, detail="数据源未找到")

    if data_source.source_type != DataSourceTypeEnum.sql:
        raise HTTPException(status_code=400, detail="仅SQL数据源支持宽表查询构建")

    try:
        builder = SQLQueryBuilder()

        # 构建查询
        if data_source.join_config:
            joins = [JoinConfig(**join) for join in data_source.join_config]
        else:
            joins = []

        if data_source.column_mapping:
            mappings = [
                ColumnMapping(**mapping) for mapping in data_source.column_mapping
            ]
        else:
            mappings = []

        if data_source.where_conditions:
            conditions = [
                WhereCondition(**condition)
                for condition in data_source.where_conditions
            ]
        else:
            conditions = []

        # 提取基础表名
        base_table = "base_table"  # 这里应该从base_query中提取

        # 构建宽表查询
        wide_table_builder = builder
        query = wide_table_builder.build()

        return {
            "query": query,
            "tables_involved": builder.extract_tables(query),
            "validation": builder.validate_query(query),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"查询构建失败: {str(e)}")


@router.post("/{data_source_id}/validate-sql")
def validate_sql_query(
    *,
    db: Session = Depends(deps.get_db),
    data_source_id: int,
    query: str = Query(..., description="要验证的SQL查询"),
):
    """验证SQL查询"""
    builder = SQLQueryBuilder()
    validation = builder.validate_query(query)

    return validation
