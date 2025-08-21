"""
占位符管理API路由

基于新分层架构的占位符处理API
提供占位符的分析、测试查询、执行历史等功能
"""

import logging
from typing import Any, Dict, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api import deps
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.base import APIResponse

# 使用统一的占位符处理系统
from app.services.domain.placeholder import (
    PlaceholderRequest, 
    PlaceholderResponse, 
    ResultSource,
    PlaceholderConfigService,
    PlaceholderRouter,
    PlaceholderBatchRouter,
    PlaceholderServiceContainer,
    create_placeholder_router
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{placeholder_id}/analyze", response_model=APIResponse)
async def analyze_placeholder_with_new_architecture(
    placeholder_id: str,
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    使用新架构分析单个占位符
    
    支持完整的 Agent分析 -> 缓存 -> 规则fallback 流程
    """
    try:
        # 验证占位符ID
        try:
            placeholder_uuid = UUID(placeholder_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无效的占位符ID格式"
            )

        # 获取占位符配置
        from app.models.template_placeholder import TemplatePlaceholder
        placeholder = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.id == placeholder_uuid
        ).first()
        if not placeholder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="占位符不存在"
            )

        # 检查权限（通过模板所有权）
        template = crud.template.get(db, id=placeholder.template_id)
        if not template or template.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此占位符"
            )

        # 获取数据源ID
        data_source_id = request_data.get("data_source_id")
        if not data_source_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="缺少数据源ID"
            )

        # 验证数据源权限
        data_source = crud.data_source.get(db, id=UUID(data_source_id))
        if not data_source or data_source.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此数据源"
            )

        # 创建占位符请求
        placeholder_request = PlaceholderRequest(
            placeholder_id=str(placeholder_uuid),
            placeholder_name=placeholder.placeholder_name,
            placeholder_type=placeholder.placeholder_type,
            data_source_id=data_source_id,
            user_id=str(current_user.id),
            force_reanalyze=request_data.get("force_reanalyze", False),
            execution_time=datetime.fromisoformat(
                request_data.get("execution_time", datetime.now().isoformat())
            ),
            metadata=request_data.get("metadata", {})
        )

        # 使用新架构处理占位符
        router_service = create_placeholder_router(db, str(current_user.id))
        response = await router_service.process_placeholder(placeholder_request)

        return APIResponse(
            success=response.success,
            message="占位符分析完成" if response.success else "占位符分析失败",
            data={
                "placeholder_id": placeholder_id,
                "placeholder_name": placeholder.placeholder_name,
                "value": response.value,
                "source": response.source.value,
                "execution_time_ms": response.execution_time_ms,
                "confidence": response.confidence,
                "error_message": response.error_message,
                "metadata": response.metadata
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"占位符分析失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析失败: {str(e)}"
        )


@router.post("/template/{template_id}/analyze-all", response_model=APIResponse)
async def analyze_template_placeholders_batch(
    template_id: str,
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量分析模板的所有占位符
    
    使用新架构并行处理所有占位符
    """
    try:
        # 验证模板ID
        try:
            template_uuid = UUID(template_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无效的模板ID格式"
            )

        # 检查模板权限
        template = crud.template.get(db, id=template_uuid)
        if not template or template.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此模板"
            )

        # 获取数据源ID
        data_source_id = request_data.get("data_source_id")
        if not data_source_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="缺少数据源ID"
            )

        # 验证数据源权限
        data_source = crud.data_source.get(db, id=UUID(data_source_id))
        if not data_source or data_source.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此数据源"
            )

        # 使用新架构批量处理
        batch_router = create_batch_router(db, str(current_user.id))
        
        execution_context = {
            "execution_time": request_data.get("execution_time", datetime.now().isoformat()),
            "metadata": request_data.get("metadata", {})
        }
        
        result = await batch_router.process_template_placeholders(
            template_id=str(template_uuid),
            data_source_id=data_source_id,
            user_id=str(current_user.id),
            force_reanalyze=request_data.get("force_reanalyze", False),
            execution_context=execution_context
        )

        return APIResponse(
            success=result["success"],
            message="批量分析完成" if result["success"] else "批量分析失败",
            data=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量分析失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量分析失败: {str(e)}"
        )


@router.get("/system/health", response_model=APIResponse)
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取占位符处理系统健康状态
    """
    try:
        service_container = create_placeholder_service(db, str(current_user.id))
        health_status = await service_container.health_check()
        
        return APIResponse(
            success=True,
            message="系统健康检查完成",
            data=health_status
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查失败: {str(e)}"
        )


@router.post("/{placeholder_id}/test-query", response_model=APIResponse)
async def test_placeholder_query(
    placeholder_id: str,
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试占位符查询
    """
    try:
        # 验证占位符ID
        try:
            placeholder_uuid = UUID(placeholder_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无效的占位符ID格式"
            )

        # 获取占位符配置
        from app.models.template_placeholder import TemplatePlaceholder
        placeholder = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.id == placeholder_uuid
        ).first()
        if not placeholder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="占位符不存在"
            )

        # 检查权限（通过模板所有权）
        template = crud.template.get(db, id=placeholder.template_id)
        if not template or template.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此占位符"
            )

        # 获取数据源ID（从请求数据或占位符配置中获取）
        data_source_id = request_data.get("data_source_id")
        if not data_source_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="缺少数据源ID"
            )

        # 验证数据源权限
        data_source = crud.data_source.get(db, id=UUID(data_source_id))
        if not data_source or data_source.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此数据源"
            )

        # 执行测试查询（使用统一的配置服务）
        config_service = create_placeholder_config_service(db)
        test_result = await config_service.test_placeholder_query(
            placeholder_id=str(placeholder_uuid),
            data_source_id=data_source_id,
            config_override=request_data.get("config", {})
        )

        return APIResponse(
            success=True,
            message="查询测试完成",
            data=test_result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试占位符查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试查询失败: {str(e)}"
        )


@router.get("/{placeholder_id}/execution-history", response_model=APIResponse)
async def get_placeholder_execution_history(
    placeholder_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取占位符执行历史
    """
    try:
        # 验证占位符ID
        try:
            placeholder_uuid = UUID(placeholder_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无效的占位符ID格式"
            )

        # 获取占位符配置
        from app.models.template_placeholder import TemplatePlaceholder
        placeholder = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.id == placeholder_uuid
        ).first()
        if not placeholder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="占位符不存在"
            )

        # 检查权限（通过模板所有权）
        template = crud.template.get(db, id=placeholder.template_id)
        if not template or template.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此占位符"
            )

        # 获取执行历史（使用统一的配置服务）
        config_service = create_placeholder_config_service(db)
        history = await config_service.get_execution_history(
            placeholder_id=str(placeholder_uuid),
            limit=limit
        )

        return APIResponse(
            success=True,
            message="获取执行历史成功",
            data=history
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取占位符执行历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取执行历史失败: {str(e)}"
        )


@router.post("/{placeholder_id}/reanalyze", response_model=APIResponse)
async def reanalyze_placeholder(
    placeholder_id: str,
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    重新分析占位符
    """
    try:
        # 验证占位符ID
        try:
            placeholder_uuid = UUID(placeholder_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无效的占位符ID格式"
            )

        # 获取占位符配置
        from app.models.template_placeholder import TemplatePlaceholder
        placeholder = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.id == placeholder_uuid
        ).first()
        if not placeholder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="占位符不存在"
            )

        # 检查权限（通过模板所有权）
        template = crud.template.get(db, id=placeholder.template_id)
        if not template or template.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此占位符"
            )

        # 获取数据源ID
        data_source_id = request_data.get("data_source_id")
        if not data_source_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="缺少数据源ID"
            )

        # 验证数据源权限
        data_source = crud.data_source.get(db, id=UUID(data_source_id))
        if not data_source or data_source.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此数据源"
            )

        # 执行重新分析（使用统一的配置服务）
        config_service = create_placeholder_config_service(db)
        analysis_result = await config_service.reanalyze_placeholder(
            placeholder_id=str(placeholder_uuid),
            data_source_id=data_source_id,
            force_refresh=request_data.get("force_refresh", True)
        )

        return APIResponse(
            success=True,
            message="重新分析完成",
            data=analysis_result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新分析占位符失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新分析失败: {str(e)}"
        )