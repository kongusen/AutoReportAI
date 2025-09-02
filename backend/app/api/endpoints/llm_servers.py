"""
LLM服务器管理API端点

提供LLM服务器和模型的配置、监控、健康检查等API接口
"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.crud.crud_llm_server import crud_llm_server
from app.crud.crud_llm_model import crud_llm_model
from app.api import deps
from app.models.llm_server import LLMServer, LLMModel, ModelType
from app.core.architecture import ApiResponse
from app.schemas.llm_server import (
    LLMServerCreate,
    LLMServerUpdate,
    LLMServerResponse,
    LLMModelCreate,
    LLMModelUpdate,
    LLMModelResponse,
    LLMModelHealthCheck,
    LLMModelHealthResponse,
    LLMServerHealthResponse,
    LLMServerBatchOperation,
    LLMModelBatchOperation
)
from app.services.infrastructure.ai.llm.intelligent_selector import IntelligentLLMSelector
from app.services.infrastructure.notification.notification_service import get_notification_service

router = APIRouter()


# === LLM服务器管理 ===

@router.get("/", response_model=List[LLMServerResponse])
def get_llm_servers(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = Query(default=100, le=1000),
    is_active: Optional[bool] = None,
    is_healthy: Optional[bool] = None,
    current_user = Depends(deps.get_current_active_user)
):
    """获取LLM服务器列表"""
    query_filter = {}
    if is_active is not None:
        query_filter['is_active'] = is_active
    if is_healthy is not None:
        query_filter['is_healthy'] = is_healthy
    
    servers = crud_llm_server.get_multi_by_filter(
        db, skip=skip, limit=limit, **query_filter
    )
    
    # 添加统计信息
    for server in servers:
        stats = crud_llm_server.get_server_stats(db, server_id=server.id)
        server.models_count = stats.get('models_count')
        server.healthy_models_count = stats.get('healthy_models_count')
    
    return servers


@router.post("/", response_model=LLMServerResponse)
def create_llm_server(
    *,
    db: Session = Depends(deps.get_db),
    server_in: LLMServerCreate,
    current_user = Depends(deps.get_current_active_user)
):
    """创建新的LLM服务器"""
    # 检查URL是否已存在
    existing_server = crud_llm_server.get_by_base_url(db, base_url=server_in.base_url)
    if existing_server:
        raise HTTPException(
            status_code=400,
            detail="该URL的LLM服务器已存在"
        )
    
    server = crud_llm_server.create(db, obj_in=server_in)
    return server


@router.get("/{server_id}", response_model=LLMServerResponse)
def get_llm_server(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    current_user = Depends(deps.get_current_active_user)
):
    """获取特定LLM服务器"""
    server = crud_llm_server.get(db, id=server_id)
    if not server:
        raise HTTPException(
            status_code=404,
            detail="LLM服务器不存在"
        )
    
    # 添加统计信息
    stats = crud_llm_server.get_server_stats(db, server_id=server.id)
    server.models_count = stats.get('models_count')
    server.healthy_models_count = stats.get('healthy_models_count')
    
    return server


@router.put("/{server_id}", response_model=LLMServerResponse)
def update_llm_server(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    server_in: LLMServerUpdate,
    current_user = Depends(deps.get_current_active_user)
):
    """更新LLM服务器"""
    server = crud_llm_server.get(db, id=server_id)
    if not server:
        raise HTTPException(
            status_code=404,
            detail="LLM服务器不存在"
        )
    
    server = crud_llm_server.update(db, db_obj=server, obj_in=server_in)
    return server


@router.delete("/{server_id}", response_model=ApiResponse)
def delete_llm_server(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    current_user = Depends(deps.get_current_active_user)
):
    """删除LLM服务器"""
    server = crud_llm_server.get(db, id=server_id)
    if not server:
        raise HTTPException(
            status_code=404,
            detail="LLM服务器不存在"
        )
    
    # 先清理用户LLM偏好设置中对此服务器的引用
    from app.models.user_llm_preference import UserLLMPreference
    db.query(UserLLMPreference).filter(
        UserLLMPreference.default_llm_server_id == server_id
    ).update({"default_llm_server_id": None})
    db.commit()
    
    # 删除服务器及其关联的模型（CASCADE删除）
    crud_llm_server.remove(db, id=server_id)
    return ApiResponse(
        success=True,
        data={"server_id": server_id},
        message="LLM服务器已删除"
    )


# === LLM模型管理 ===

@router.get("/{server_id}/models", response_model=List[LLMModelResponse])
def get_server_models(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    is_active: Optional[bool] = None,
    model_type: Optional[ModelType] = None,
    current_user = Depends(deps.get_current_active_user)
):
    """获取LLM服务器的模型列表"""
    server = crud_llm_server.get(db, id=server_id)
    if not server:
        raise HTTPException(
            status_code=404,
            detail="LLM服务器不存在"
        )
    
    models = crud_llm_model.get_models_by_filter(
        db,
        server_id=server_id,
        is_active=is_active,
        model_type=model_type
    )
    
    return models


@router.post("/{server_id}/models", response_model=LLMModelResponse)
def create_server_model(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    model_in: LLMModelCreate,
    current_user = Depends(deps.get_current_active_user)
):
    """为LLM服务器添加模型"""
    server = crud_llm_server.get(db, id=server_id)
    if not server:
        raise HTTPException(
            status_code=404,
            detail="LLM服务器不存在"
        )
    
    # 检查模型是否已存在
    existing_model = crud_llm_model.get_by_name_and_server(
        db, server_id=server_id, model_name=model_in.name
    )
    if existing_model:
        raise HTTPException(
            status_code=400,
            detail="该服务器上已存在同名模型"
        )
    
    model_in.server_id = server_id
    model = crud_llm_model.create(db, obj_in=model_in)
    return model


@router.get("/models", response_model=List[LLMModelResponse])
def get_all_models(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = Query(default=100, le=1000),
    model_type: Optional[ModelType] = None,
    provider_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    supports_thinking: Optional[bool] = None,
    current_user = Depends(deps.get_current_active_user)
):
    """获取所有模型列表"""
    models = crud_llm_model.get_models_by_filter(
        db,
        model_type=model_type,
        provider_name=provider_name,
        is_active=is_active,
        supports_thinking=supports_thinking,
        skip=skip,
        limit=limit
    )
    
    return models


@router.put("/{server_id}/models/{model_id}", response_model=LLMModelResponse)
def update_server_model(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    model_id: int,
    model_in: LLMModelUpdate,
    current_user = Depends(deps.get_current_active_user)
):
    """更新LLM模型"""
    model = crud_llm_model.get(db, id=model_id)
    if not model or model.server_id != server_id:
        raise HTTPException(
            status_code=404,
            detail="模型不存在"
        )
    
    model = crud_llm_model.update(db, db_obj=model, obj_in=model_in)
    return model


@router.delete("/{server_id}/models/{model_id}", response_model=ApiResponse)
def delete_server_model(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    model_id: int,
    current_user = Depends(deps.get_current_active_user)
):
    """删除LLM模型"""
    model = crud_llm_model.get(db, id=model_id)
    if not model or model.server_id != server_id:
        raise HTTPException(
            status_code=404,
            detail="模型不存在"
        )
    
    crud_llm_model.remove(db, id=model_id)
    return ApiResponse(
        success=True,
        data={"model_id": model_id, "server_id": server_id},
        message="模型已删除"
    )


# === 健康检查和监控 ===

@router.post("/{server_id}/models/{model_id}/health", response_model=LLMModelHealthResponse)
async def check_model_health(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    model_id: int,
    health_check: Optional[LLMModelHealthCheck] = None,
    current_user = Depends(deps.get_current_active_user)
):
    """检查单个模型健康状态"""
    model = crud_llm_model.get(db, id=model_id)
    if not model or model.server_id != server_id:
        raise HTTPException(
            status_code=404,
            detail="模型不存在"
        )
    
    test_message = health_check.test_message if health_check else "你好"
    
    health_service = get_model_health_service()
    result = await health_service.test_model_health(db, model, test_message)
    
    return result


@router.get("/{server_id}/health", response_model=LLMServerHealthResponse)
async def check_server_health(
    *,
    db: Session = Depends(deps.get_db),
    server_id: int,
    test_message: str = "你好",
    current_user = Depends(deps.get_current_active_user)
):
    """检查LLM服务器及其所有模型的健康状态"""
    server = crud_llm_server.get(db, id=server_id)
    if not server:
        raise HTTPException(
            status_code=404,
            detail="LLM服务器不存在"
        )
    
    health_service = get_model_health_service()
    result = await health_service.test_server_health(db, server, test_message)
    
    return result


@router.post("/health-check-all", response_model=List[LLMServerHealthResponse])
async def health_check_all_servers(
    *,
    db: Session = Depends(deps.get_db),
    test_message: str = "你好",
    current_user = Depends(deps.get_current_active_user)
):
    """检查所有LLM服务器的健康状态"""
    health_service = get_model_health_service()
    results = await health_service.test_all_servers_health(db, test_message)
    
    return results


# === 批量操作 ===

@router.post("/servers/batch", response_model=Dict[str, Any])
def batch_server_operation(
    *,
    db: Session = Depends(deps.get_db),
    operation: LLMServerBatchOperation,
    current_user = Depends(deps.get_current_active_user)
):
    """批量操作LLM服务器"""
    results = {"success": [], "failed": []}
    
    try:
        if operation.operation == "activate":
            count = crud_llm_server.activate_servers(db, server_ids=operation.server_ids)
            results["success"] = operation.server_ids[:count]
        elif operation.operation == "deactivate":
            count = crud_llm_server.deactivate_servers(db, server_ids=operation.server_ids)
            results["success"] = operation.server_ids[:count]
        else:
            results["failed"] = [{"ids": operation.server_ids, "error": "不支持的操作"}]
            
    except Exception as e:
        results["failed"] = [{"ids": operation.server_ids, "error": str(e)}]
    
    return results


@router.post("/models/batch", response_model=Dict[str, Any])
def batch_model_operation(
    *,
    db: Session = Depends(deps.get_db),
    operation: LLMModelBatchOperation,
    current_user = Depends(deps.get_current_active_user)
):
    """批量操作LLM模型"""
    results = {"success": [], "failed": []}
    
    try:
        if operation.operation == "activate":
            count = crud_llm_model.activate_models(db, model_ids=operation.model_ids)
            results["success"] = operation.model_ids[:count]
        elif operation.operation == "deactivate":
            count = crud_llm_model.deactivate_models(db, model_ids=operation.model_ids)
            results["success"] = operation.model_ids[:count]
        else:
            results["failed"] = [{"ids": operation.model_ids, "error": "不支持的操作"}]
            
    except Exception as e:
        results["failed"] = [{"ids": operation.model_ids, "error": str(e)}]
    
    return results


# === 系统概览 ===

@router.get("/stats/overview")
def get_system_overview(
    *,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    """获取LLM服务器系统概览"""
    total_servers = crud_llm_server.count(db)
    active_servers = len(crud_llm_server.get_active_servers(db))
    healthy_servers = len(crud_llm_server.get_healthy_servers(db))
    
    # 模型统计
    model_stats = crud_llm_model.get_model_stats(db)
    
    return {
        "servers": {
            "total": total_servers,
            "active": active_servers,
            "healthy": healthy_servers,
            "health_rate": healthy_servers / total_servers if total_servers > 0 else 0.0
        },
        "models": {
            "total": model_stats.get("total_models", 0),
            "active": model_stats.get("active_models", 0),
            "healthy": model_stats.get("healthy_models", 0),
            "health_rate": model_stats.get("health_rate", 0.0),
            "type_distribution": model_stats.get("type_distribution", {}),
            "provider_distribution": model_stats.get("provider_distribution", {})
        },
        "timestamp": datetime.utcnow()
    }