"""
占位符管理API路由

提供占位符的测试查询、执行历史等功能
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api import deps
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.base import APIResponse
from app.services.template.placeholder_config_service import PlaceholderConfigService

logger = logging.getLogger(__name__)
router = APIRouter()


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

        # 执行测试查询
        placeholder_service = PlaceholderConfigService(db)
        test_result = await placeholder_service.test_placeholder_query(
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

        # 获取执行历史
        placeholder_service = PlaceholderConfigService(db)
        history = await placeholder_service.get_execution_history(
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

        # 执行重新分析
        placeholder_service = PlaceholderConfigService(db)
        analysis_result = await placeholder_service.reanalyze_placeholder(
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