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
    create_placeholder_router,
    create_placeholder_config_service
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
    使用新的占位符SQL构建Agent分析单个占位符
    
    这个端点现在使用新的Agent系统而不是旧的统一架构
    """
    try:
        # 使用新的占位符SQL构建Agent系统
        # 直接使用IAOP专业化代理
        from app.services.iaop.agents.specialized.sql_generation_agent import SQLGenerationAgent as PlaceholderSQLAnalyzer
        
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

        # 获取数据源ID（从模板或请求中获取）
        data_source_id = request_data.get("data_source_id") or template.data_source_id
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

        # 创建新的Agent分析器
        analyzer = PlaceholderSQLAnalyzer(db_session=db, user_id=str(current_user.id))
        
        # 执行分析
        result = await analyzer.analyze_placeholder(
            placeholder_id=str(placeholder_uuid),
            placeholder_text=placeholder.placeholder_name,
            data_source_id=str(data_source_id),
            placeholder_type=placeholder.placeholder_type,
            template_id=str(template.id),
            force_reanalyze=request_data.get('force_reanalyze', False)
        )
        
        if result.success:
            return APIResponse(
                code=200,
                message="占位符分析成功",
                data={
                    "placeholder_id": str(placeholder_uuid),
                    "placeholder_name": placeholder.placeholder_name,
                    "generated_sql": result.generated_sql,
                    "confidence": result.confidence,
                    "semantic_type": result.semantic_type,
                    "semantic_subtype": result.semantic_subtype,
                    "data_intent": result.data_intent,
                    "target_table": result.target_table,
                    "explanation": result.explanation,
                    "suggestions": result.suggestions,
                    "metadata": result.metadata,
                    "analysis_timestamp": result.analysis_timestamp.isoformat()
                }
            )
        else:
            return APIResponse(
                code=400,
                message=f"占位符分析失败: {result.error_message}",
                data={
                    "placeholder_id": str(placeholder_uuid),
                    "error_message": result.error_message,
                    "error_context": result.error_context
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
    
    使用新的Agent系统和门面服务并行处理所有占位符
    """
    try:
        # 使用新的门面服务
        # 直接使用IAOP核心平台
        from app.services.iaop.agents.specialized.placeholder_parser_agent import PlaceholderParserAgent
        
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

        # 创建门面服务并分析模板占位符
        facade = create_placeholder_analysis_facade(db)
        result = await facade.analyze_template_placeholders(
            template_id=str(template_uuid),
            user_id=str(current_user.id),
            force_reanalyze=request_data.get('force_reanalyze', False)
        )
        
        return APIResponse(
            code=200 if result['success'] else 400,
            message=result['message'],
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


@router.post("/{placeholder_id}/validate-sql", response_model=APIResponse)
async def validate_placeholder_sql(
    placeholder_id: str,
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    验证占位符SQL查询
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

        # 检查是否有生成的SQL
        if not placeholder.generated_sql:
            return APIResponse(
                success=False,
                message="占位符没有生成的SQL查询",
                data={
                    "valid": False,
                    "error": "占位符尚未分析或未生成SQL"
                }
            )

        # 验证SQL语法和执行
        config_service = create_placeholder_config_service(db)
        validation_result = await config_service.validate_placeholder_sql(
            placeholder_id=str(placeholder_uuid),
            data_source_id=data_source_id
        )

        return APIResponse(
            success=True,
            message="SQL验证完成",
            data=validation_result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证占位符SQL失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SQL验证失败: {str(e)}"
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