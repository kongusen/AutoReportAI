"""
学习系统API端点

提供错误记录、用户反馈收集、知识库查询等功能的API接口
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...api.deps import get_current_user, get_db, get_learning_service
from ...models.user import User
from ...services.learning_service import (
    ErrorCategory,
    ErrorSeverity,
    FeedbackType,
    LearningService,
)

router = APIRouter()


# Pydantic模型定义


class ErrorRecordRequest(BaseModel):
    """错误记录请求"""

    category: str = Field(..., description="错误分类")
    severity: str = Field(..., description="错误严重程度")
    message: str = Field(..., description="错误消息")
    placeholder_text: Optional[str] = Field(None, description="占位符文本")
    placeholder_type: Optional[str] = Field(None, description="占位符类型")
    placeholder_description: Optional[str] = Field(None, description="占位符描述")
    context_before: Optional[str] = Field(None, description="前置上下文")
    context_after: Optional[str] = Field(None, description="后置上下文")
    data_source_id: Optional[int] = Field(None, description="数据源ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="附加数据")


class ErrorRecordResponse(BaseModel):
    """错误记录响应"""

    error_id: str = Field(..., description="错误ID")
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")


class FeedbackRequest(BaseModel):
    """用户反馈请求"""

    feedback_type: str = Field(..., description="反馈类型")
    placeholder_text: str = Field(..., description="占位符文本")
    original_result: str = Field(..., description="原始结果")
    corrected_result: Optional[str] = Field(None, description="纠正后的结果")
    suggested_field: Optional[str] = Field(None, description="建议的字段")
    confidence_rating: Optional[int] = Field(
        None, ge=1, le=5, description="置信度评分 (1-5)"
    )
    comments: Optional[str] = Field(None, description="评论")
    error_id: Optional[str] = Field(None, description="关联的错误ID")


class FeedbackResponse(BaseModel):
    """用户反馈响应"""

    feedback_id: str = Field(..., description="反馈ID")
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")


class KnowledgeQueryRequest(BaseModel):
    """知识库查询请求"""

    placeholder_text: str = Field(..., description="占位符文本")
    placeholder_type: str = Field(..., description="占位符类型")
    data_source_id: int = Field(..., description="数据源ID")
    context: Optional[str] = Field(None, description="上下文信息")


class KnowledgeQueryResponse(BaseModel):
    """知识库查询响应"""

    suggestions: List[Dict[str, Any]] = Field(..., description="建议列表")
    total_count: int = Field(..., description="建议总数")


class LearningSuccessRequest(BaseModel):
    """学习成功案例请求"""

    placeholder_text: str = Field(..., description="占位符文本")
    placeholder_type: str = Field(..., description="占位符类型")
    matched_field: str = Field(..., description="匹配的字段")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="置信度分数")
    data_source_id: int = Field(..., description="数据源ID")
    processing_time: float = Field(..., description="处理时间")


class ErrorStatisticsResponse(BaseModel):
    """错误统计响应"""

    total_errors: int = Field(..., description="错误总数")
    category_distribution: Dict[str, int] = Field(..., description="分类分布")
    severity_distribution: Dict[str, int] = Field(..., description="严重程度分布")
    time_distribution: Dict[str, int] = Field(..., description="时间分布")
    placeholder_type_distribution: Dict[str, int] = Field(
        ..., description="占位符类型分布"
    )
    error_rate_trend: List[Dict[str, Any]] = Field(..., description="错误率趋势")


class LearningMetricsResponse(BaseModel):
    """学习指标响应"""

    cache_statistics: Dict[str, Any] = Field(..., description="缓存统计")
    feedback_statistics: Dict[str, Any] = Field(..., description="反馈统计")
    learning_rule_statistics: Dict[str, Any] = Field(..., description="学习规则统计")
    knowledge_base_statistics: Dict[str, Any] = Field(..., description="知识库统计")
    learning_effectiveness: Dict[str, float] = Field(..., description="学习效果")


# API端点


@router.post("/errors/record", response_model=ErrorRecordResponse)
async def record_error(
    request: ErrorRecordRequest,
    current_user: User = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> ErrorRecordResponse:
    """
    记录错误信息
    """
    try:
        # 验证枚举值
        try:
            category = ErrorCategory(request.category)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"无效的错误分类: {request.category}"
            )

        try:
            severity = ErrorSeverity(request.severity)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"无效的错误严重程度: {request.severity}"
            )

        # 记录错误
        error_id = await learning_service.record_error(
            category=category,
            severity=severity,
            message=request.message,
            placeholder_text=request.placeholder_text or "",
            placeholder_type=request.placeholder_type or "",
            placeholder_description=request.placeholder_description or "",
            context_before=request.context_before or "",
            context_after=request.context_after or "",
            data_source_id=request.data_source_id,
            user_id=current_user.id,
            session_id=request.session_id,
            additional_data=request.additional_data,
        )

        return ErrorRecordResponse(
            error_id=error_id,
            success=bool(error_id),
            message="错误记录成功" if error_id else "错误记录失败",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录错误失败: {str(e)}")


@router.post("/feedback/submit", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> FeedbackResponse:
    """
    提交用户反馈
    """
    try:
        # 验证反馈类型
        try:
            feedback_type = FeedbackType(request.feedback_type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"无效的反馈类型: {request.feedback_type}"
            )

        # 收集反馈
        feedback_id = await learning_service.collect_user_feedback(
            user_id=current_user.id,
            feedback_type=feedback_type,
            placeholder_text=request.placeholder_text,
            original_result=request.original_result,
            corrected_result=request.corrected_result,
            suggested_field=request.suggested_field,
            confidence_rating=request.confidence_rating,
            comments=request.comments,
            error_id=request.error_id,
        )

        return FeedbackResponse(
            feedback_id=feedback_id,
            success=bool(feedback_id),
            message="反馈提交成功" if feedback_id else "反馈提交失败",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")


@router.post("/knowledge/query", response_model=KnowledgeQueryResponse)
async def query_knowledge_base(
    request: KnowledgeQueryRequest,
    current_user: User = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> KnowledgeQueryResponse:
    """
    查询知识库获取建议
    """
    try:
        suggestions = await learning_service.query_knowledge_base(
            placeholder_text=request.placeholder_text,
            placeholder_type=request.placeholder_type,
            data_source_id=request.data_source_id,
            context=request.context,
        )

        return KnowledgeQueryResponse(
            suggestions=suggestions, total_count=len(suggestions)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询知识库失败: {str(e)}")


@router.post("/learning/success")
async def record_learning_success(
    request: LearningSuccessRequest,
    current_user: User = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> Dict[str, str]:
    """
    记录学习成功案例
    """
    try:
        await learning_service.learn_from_success(
            placeholder_text=request.placeholder_text,
            placeholder_type=request.placeholder_type,
            matched_field=request.matched_field,
            confidence_score=request.confidence_score,
            data_source_id=request.data_source_id,
            processing_time=request.processing_time,
        )

        return {"message": "成功案例记录完成"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录成功案例失败: {str(e)}")


@router.get("/statistics/errors", response_model=ErrorStatisticsResponse)
async def get_error_statistics(
    days: int = Query(7, ge=1, le=365, description="统计天数"),
    category: Optional[str] = Query(None, description="错误分类过滤"),
    severity: Optional[str] = Query(None, description="严重程度过滤"),
    current_user: User = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> ErrorStatisticsResponse:
    """
    获取错误统计信息
    """
    try:
        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        time_range = (start_time, end_time)

        # 验证过滤参数
        category_filter = None
        if category:
            try:
                category_filter = ErrorCategory(category)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"无效的错误分类: {category}"
                )

        severity_filter = None
        if severity:
            try:
                severity_filter = ErrorSeverity(severity)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"无效的错误严重程度: {severity}"
                )

        # 获取统计信息
        stats = await learning_service.get_error_statistics(
            time_range=time_range, category=category_filter, severity=severity_filter
        )

        return ErrorStatisticsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取错误统计失败: {str(e)}")


@router.get("/metrics", response_model=LearningMetricsResponse)
async def get_learning_metrics(
    current_user: User = Depends(get_current_user),
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningMetricsResponse:
    """
    获取学习指标
    """
    try:
        metrics = await learning_service.get_learning_metrics()
        return LearningMetricsResponse(**metrics)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取学习指标失败: {str(e)}")


@router.get("/errors/categories")
async def get_error_categories(
    current_user: User = Depends(get_current_user),
) -> Dict[str, List[str]]:
    """
    获取错误分类和严重程度选项
    """
    return {
        "categories": [category.value for category in ErrorCategory],
        "severities": [severity.value for severity in ErrorSeverity],
        "feedback_types": [feedback_type.value for feedback_type in FeedbackType],
    }


@router.get("/health")
async def health_check(
    learning_service: LearningService = Depends(get_learning_service),
) -> Dict[str, Any]:
    """
    学习服务健康检查
    """
    try:
        # 检查服务状态
        metrics = await learning_service.get_learning_metrics()

        return {
            "status": "healthy",
            "auto_learning_enabled": learning_service.auto_learning_enabled,
            "knowledge_base_entries": metrics.get("knowledge_base_statistics", {}).get(
                "total_entries", 0
            ),
            "cached_mappings": metrics.get("cache_statistics", {}).get(
                "total_mappings", 0
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
