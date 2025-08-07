"""ETL作业管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.etl_job import ETLJob
from app.schemas.etl_job import ETLJobCreate, ETLJobUpdate, ETLJobResponse
from app.crud.crud_etl_job import crud_etl_job

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_etl_jobs(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    data_source_id: Optional[int] = Query(None, description="数据源ID"),
    enabled: Optional[bool] = Query(None, description="是否启用"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取ETL作业列表"""
    query = db.query(ETLJob).filter(ETLJob.user_id == current_user.id)
    
    if data_source_id:
        query = query.filter(ETLJob.data_source_id == data_source_id)
    
    if enabled is not None:
        query = query.filter(ETLJob.enabled == enabled)
    
    if search:
        query = query.filter(ETLJob.name.contains(search))
    
    total = query.count()
    etl_jobs = query.offset(skip).limit(limit).all()
    etl_job_schemas = [ETLJobResponse.model_validate(ej) for ej in etl_jobs]
    etl_job_dicts = [ej.model_dump() | {"unique_id": str(ej.id)} for ej in etl_job_schemas]
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=etl_job_dicts,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_etl_job(
    etl_job: ETLJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建ETL作业"""
    etl_job_obj = crud_etl_job.create_with_user(
        db, 
        obj_in=etl_job, 
        user_id=current_user.id
    )
    etl_job_schema = ETLJobResponse.model_validate(etl_job_obj)
    etl_job_dict = etl_job_schema.model_dump()
    etl_job_dict['unique_id'] = str(etl_job_dict.get('id'))
    return {"id": etl_job_dict["id"], **etl_job_dict}


@router.get("/{etl_job_id}", response_model=ApiResponse)
async def get_etl_job(
    etl_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取特定ETL作业"""
    etl_job = crud_etl_job.get(db, id=etl_job_id)
    if not etl_job or etl_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ETL作业不存在或无权限访问"
        )
    etl_job_schema = ETLJobResponse.model_validate(etl_job)
    etl_job_dict = etl_job_schema.model_dump()
    etl_job_dict['unique_id'] = str(etl_job_dict.get('id'))
    return ApiResponse(
        success=True,
        data=etl_job_dict,
        message="获取ETL作业成功"
    )


@router.put("/{etl_job_id}", response_model=ApiResponse)
async def update_etl_job(
    etl_job_id: str,
    etl_job_update: ETLJobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新ETL作业"""
    etl_job = crud_etl_job.get(db, id=etl_job_id)
    if not etl_job or etl_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ETL作业不存在或无权限访问"
        )
    
    etl_job = crud_etl_job.update(
        db, 
        db_obj=etl_job, 
        obj_in=etl_job_update
    )
    
    return ApiResponse(
        success=True,
        data=etl_job,
        message="ETL作业更新成功"
    )


@router.delete("/{etl_job_id}", response_model=ApiResponse)
async def delete_etl_job(
    etl_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除ETL作业"""
    etl_job = crud_etl_job.get(db, id=etl_job_id)
    if not etl_job or etl_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ETL作业不存在或无权限访问"
        )
    
    crud_etl_job.remove(db, id=etl_job_id)
    
    return ApiResponse(
        success=True,
        data={"etl_job_id": etl_job_id},
        message="ETL作业删除成功"
    )


@router.post("/{etl_job_id}/run", response_model=ApiResponse)
async def run_etl_job(
    etl_job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """运行ETL作业"""
    etl_job = crud_etl_job.get(db, id=etl_job_id)
    if not etl_job or etl_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ETL作业不存在或无权限访问"
        )
    
    # 在后台运行ETL作业
    background_tasks.add_task(
        run_etl_job_task,
        etl_job_id=etl_job_id
    )
    
    return ApiResponse(
        success=True,
        data={
            "etl_job_id": etl_job_id,
            "status": "running",
            "message": "ETL作业已开始运行"
        },
        message="ETL作业已开始运行"
    )


@router.post("/{etl_job_id}/enable", response_model=ApiResponse)
async def enable_etl_job(
    etl_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """启用ETL作业"""
    etl_job = crud_etl_job.get(db, id=etl_job_id)
    if not etl_job or etl_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ETL作业不存在或无权限访问"
        )
    
    etl_job.enabled = True
    db.commit()
    db.refresh(etl_job)
    
    return ApiResponse(
        success=True,
        data=etl_job,
        message="ETL作业已启用"
    )


@router.post("/{etl_job_id}/disable", response_model=ApiResponse)
async def disable_etl_job(
    etl_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """禁用ETL作业"""
    etl_job = crud_etl_job.get(db, id=etl_job_id)
    if not etl_job or etl_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ETL作业不存在或无权限访问"
        )
    
    etl_job.enabled = False
    db.commit()
    db.refresh(etl_job)
    
    return ApiResponse(
        success=True,
        data=etl_job,
        message="ETL作业已禁用"
    )


@router.get("/{etl_job_id}/status", response_model=ApiResponse)
async def get_etl_job_status(
    etl_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取ETL作业状态"""
    etl_job = crud_etl_job.get(db, id=etl_job_id)
    if not etl_job or etl_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ETL作业不存在或无权限访问"
        )
    
    # 这里应该实现实际的状态查询逻辑
    return ApiResponse(
        success=True,
        data={
            "etl_job_id": etl_job_id,
            "status": "idle",
            "last_run": None,
            "next_run": None
        },
        message="获取ETL作业状态成功"
    )


async def run_etl_job_task(etl_job_id: str):
    """后台运行ETL作业"""
    import asyncio
    from datetime import datetime
    from uuid import UUID
    from ...services.data_processing.query_optimizer import query_optimizer
    from ...crud.crud_etl_job import etl_job as crud_etl_job
    from ...db.session import get_db_session
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting ETL job execution: {etl_job_id}")
        
        # 获取ETL作业信息
        with get_db_session() as db:
            etl_job = crud_etl_job.get(db, id=UUID(etl_job_id))
            if not etl_job:
                logger.error(f"ETL job not found: {etl_job_id}")
                return
            
            # 获取数据源信息
            data_source = etl_job.data_source
            if not data_source:
                logger.error(f"Data source not found for ETL job: {etl_job_id}")
                return
        
        # 构建查询参数
        filters = {}
        aggregations = []
        
        # 使用查询优化器执行ETL查询
        result = await query_optimizer.optimize_and_execute(
            data_source=data_source,
            base_query=etl_job.source_query,
            filters=filters,
            aggregations=aggregations
        )
        
        logger.info(
            f"ETL job completed: {etl_job_id}, "
            f"processed {result.rows_returned} rows in {result.execution_time:.2f}s"
        )
        
        # 这里可以添加结果存储逻辑
        # 例如：将结果写入目标表 etl_job.destination_table_name
        
        # 更新ETL作业状态
        with get_db_session() as db:
            etl_job = crud_etl_job.get(db, id=UUID(etl_job_id))
            if etl_job:
                # 可以添加last_run_time等字段的更新
                pass
        
    except Exception as e:
        logger.error(f"ETL job execution failed: {etl_job_id}, error: {str(e)}")
        # 这里可以添加错误状态更新逻辑
