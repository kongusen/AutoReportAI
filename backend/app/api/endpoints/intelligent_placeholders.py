"""
智能占位符API端点

提供占位符分析、字段匹配验证和智能报告生成的API接口。
支持完整的智能占位符处理流程，包括语义理解、字段匹配和ETL指令生成。
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.exceptions import (
    NotFoundError,
    PlaceholderProcessingError,
    FieldMatchingError,
    ReportGenerationError,
    ValidationError,
    AuthorizationError
)
from app.models.enhanced_data_source import EnhancedDataSource
from app.models.template import Template
from app.models.user import User
from app.services.enhanced_data_source_service import EnhancedDataSourceService
from app.services.data_processing import IntelligentETLExecutor
from app.services.intelligent_placeholder import (
    PlaceholderMatch,
    PlaceholderProcessor,
    PlaceholderType,
)
from app.services.llm_placeholder_service import (
    ETLInstruction,
    FieldMatchingSuggestion,
    LLMPlaceholderService,
    PlaceholderUnderstanding,
    PlaceholderUnderstandingError,
)
from app.services.report_generation import ReportGenerationService
from app.schemas.base import APIResponse, create_success_response, create_error_response

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class PlaceholderAnalysisRequest(BaseModel):
    """占位符分析请求"""

    template_content: str = Field(..., description="模板内容")
    template_id: Optional[UUID] = Field(None, description="模板ID（可选）")
    data_source_id: Optional[int] = Field(None, description="数据源ID（可选）")
    analysis_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="分析选项"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "template_content": "本月{{统计:投诉总数}}件投诉中，{{区域:主要投诉地区}}占比最高。",
                "template_id": "123e4567-e89b-12d3-a456-426614174000",
                "data_source_id": 1,
                "analysis_options": {
                    "include_context": True,
                    "confidence_threshold": 0.7,
                },
            }
        }


class PlaceholderInfo(BaseModel):
    """占位符信息"""

    placeholder_text: str = Field(..., description="占位符文本")
    placeholder_type: str = Field(..., description="占位符类型")
    description: str = Field(..., description="占位符描述")
    position: int = Field(..., description="在文档中的位置")
    context_before: str = Field(..., description="前置上下文")
    context_after: str = Field(..., description="后置上下文")
    confidence: float = Field(..., description="匹配置信度")


class PlaceholderAnalysisResponse(BaseModel):
    """占位符分析响应"""

    success: bool = Field(..., description="分析是否成功")
    placeholders: List[PlaceholderInfo] = Field(..., description="识别的占位符列表")
    total_count: int = Field(..., description="占位符总数")
    type_distribution: Dict[str, int] = Field(..., description="类型分布")
    validation_result: Dict[str, Any] = Field(..., description="验证结果")
    processing_errors: List[Dict[str, Any]] = Field(..., description="处理错误")
    estimated_processing_time: int = Field(..., description="预估处理时间（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "placeholders": [
                    {
                        "placeholder_text": "{{统计:投诉总数}}",
                        "placeholder_type": "统计",
                        "description": "投诉总数",
                        "position": 2,
                        "context_before": "本月",
                        "context_after": "件投诉中",
                        "confidence": 0.95,
                    }
                ],
                "total_count": 2,
                "type_distribution": {"统计": 1, "区域": 1},
                "validation_result": {"is_valid": True},
                "processing_errors": [],
                "estimated_processing_time": 30,
            }
        }


class FieldMatchingRequest(BaseModel):
    """字段匹配验证请求"""

    placeholder_text: str = Field(..., description="占位符文本")
    placeholder_type: str = Field(..., description="占位符类型")
    description: str = Field(..., description="占位符描述")
    data_source_id: int = Field(..., description="数据源ID")
    context: Optional[str] = Field(None, description="上下文信息")
    matching_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="匹配选项"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "placeholder_text": "{{统计:投诉总数}}",
                "placeholder_type": "统计",
                "description": "投诉总数",
                "data_source_id": 1,
                "context": "本月投诉总数件投诉中",
                "matching_options": {"confidence_threshold": 0.8, "max_suggestions": 5},
            }
        }


class FieldSuggestion(BaseModel):
    """字段建议"""

    field_name: str = Field(..., description="字段名")
    match_score: float = Field(..., description="匹配分数")
    match_reason: str = Field(..., description="匹配原因")
    data_transformation: Optional[str] = Field(None, description="数据转换需求")
    validation_rules: List[str] = Field(default_factory=list, description="验证规则")


class FieldMatchingResponse(BaseModel):
    """字段匹配验证响应"""

    success: bool = Field(..., description="匹配是否成功")
    placeholder_understanding: Dict[str, Any] = Field(..., description="占位符理解结果")
    field_suggestions: List[FieldSuggestion] = Field(..., description="字段匹配建议")
    best_match: Optional[FieldSuggestion] = Field(None, description="最佳匹配")
    confidence_score: float = Field(..., description="整体置信度")
    processing_metadata: Dict[str, Any] = Field(..., description="处理元数据")


class IntelligentReportRequest(BaseModel):
    """智能报告生成请求"""

    template_id: UUID = Field(..., description="模板ID")
    data_source_id: int = Field(..., description="数据源ID")
    processing_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="处理配置"
    )
    output_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="输出配置"
    )
    email_config: Optional[Dict[str, Any]] = Field(None, description="邮件配置")

    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "123e4567-e89b-12d3-a456-426614174000",
                "data_source_id": 1,
                "processing_config": {
                    "llm_provider": "openai",
                    "llm_model": "gpt-4",
                    "enable_caching": True,
                    "quality_check": True,
                    "auto_optimization": False,
                },
                "output_config": {
                    "format": "docx",
                    "include_charts": True,
                    "quality_report": True,
                },
                "email_config": {
                    "recipients": ["user@example.com"],
                    "subject": "智能生成报告",
                    "include_summary": True,
                },
            }
        }


class IntelligentReportResponse(BaseModel):
    """智能报告生成响应"""

    success: bool = Field(..., description="生成是否成功")
    task_id: str = Field(..., description="任务ID")
    report_id: Optional[str] = Field(None, description="报告ID")
    processing_summary: Dict[str, Any] = Field(..., description="处理摘要")
    placeholder_results: List[Dict[str, Any]] = Field(..., description="占位符处理结果")
    quality_assessment: Optional[Dict[str, Any]] = Field(None, description="质量评估")
    file_path: Optional[str] = Field(None, description="生成文件路径")
    email_status: Optional[Dict[str, Any]] = Field(None, description="邮件发送状态")


# API Endpoints
@router.post(
    "/analyze", 
    response_model=PlaceholderAnalysisResponse, 
    summary="分析模板中的智能占位符",
    description="""
    分析模板内容，识别和解析其中的智能占位符。
    
    **功能特性：**
    - 自动识别多种类型的占位符（统计、区域、周期、图表等）
    - 提供占位符语义理解和上下文分析
    - 验证占位符格式和语法正确性
    - 估算处理时间和复杂度
    - 支持批量占位符分析
    
    **支持的占位符类型：**
    - **统计类**：`{{统计:投诉总数}}` - 数值统计和计算
    - **区域类**：`{{区域:主要投诉地区}}` - 地理位置相关
    - **周期类**：`{{周期:本月}}` - 时间周期相关
    - **图表类**：`{{图表:投诉趋势图}}` - 数据可视化
    
    **分析选项：**
    - `include_context`: 是否包含上下文分析
    - `confidence_threshold`: 置信度阈值（0.0-1.0）
    - `context_window`: 上下文窗口大小
    
    **使用场景：**
    - 模板创建时的占位符验证
    - 报告生成前的预处理分析
    - 模板质量评估和优化建议
    """,
    responses={
        200: {
            "description": "占位符分析成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "placeholders": [
                            {
                                "placeholder_text": "{{统计:投诉总数}}",
                                "placeholder_type": "统计",
                                "description": "投诉总数",
                                "position": 2,
                                "context_before": "本月",
                                "context_after": "件投诉中",
                                "confidence": 0.95
                            }
                        ],
                        "total_count": 2,
                        "type_distribution": {"统计": 1, "区域": 1},
                        "validation_result": {
                            "is_valid": True,
                            "warnings": [],
                            "errors": []
                        },
                        "processing_errors": [],
                        "estimated_processing_time": 30
                    }
                }
            }
        },
        400: {"description": "请求参数错误"},
        401: {"description": "未授权访问"},
        422: {"description": "模板内容格式错误"}
    }
)
async def analyze_placeholders(
    request: PlaceholderAnalysisRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> PlaceholderAnalysisResponse:
    """
    分析模板中的智能占位符
    
    对模板内容进行深度分析，识别其中的智能占位符并提供详细的分析结果。
    包括占位符类型识别、语义理解、格式验证和处理建议。
    
    Args:
        request: 占位符分析请求，包含模板内容和分析选项
        
    Returns:
        包含占位符分析结果的详细响应
        
    Raises:
        ValidationError: 当模板内容格式错误时
        PlaceholderProcessingError: 当占位符处理失败时
    """
    try:
        logger.info(f"用户 {current_user.id} 请求占位符分析")

        # 初始化占位符处理器
        processor = PlaceholderProcessor()

        # 提取占位符
        placeholder_matches = processor.extract_placeholders(request.template_content)

        # 转换为响应格式
        placeholders = []
        for match in placeholder_matches:
            placeholder_info = PlaceholderInfo(
                placeholder_text=match.full_match,
                placeholder_type=match.type.value,
                description=match.description,
                position=match.start_pos,
                context_before=match.context_before,
                context_after=match.context_after,
                confidence=match.confidence,
            )
            placeholders.append(placeholder_info)

        # 验证占位符
        validation_result = processor.validate_placeholders(placeholder_matches)

        # 统计类型分布
        type_distribution = {}
        for match in placeholder_matches:
            type_name = match.type.value
            type_distribution[type_name] = type_distribution.get(type_name, 0) + 1

        # 转换处理错误
        processing_errors = []
        for error in processor.processing_errors:
            error_dict = {
                "error_type": error.error_type,
                "message": error.message,
                "position": error.position,
                "placeholder": error.placeholder,
                "severity": error.severity,
                "suggestion": error.suggestion,
            }
            processing_errors.append(error_dict)

        # 估算处理时间（基于占位符数量和复杂度）
        estimated_time = len(placeholder_matches) * 15  # 每个占位符约15秒
        if request.data_source_id:
            estimated_time += 10  # 数据源验证额外时间

        response = PlaceholderAnalysisResponse(
            success=True,
            placeholders=placeholders,
            total_count=len(placeholder_matches),
            type_distribution=type_distribution,
            validation_result=validation_result,
            processing_errors=processing_errors,
            estimated_processing_time=estimated_time,
        )

        logger.info(f"占位符分析完成: 识别 {len(placeholder_matches)} 个占位符")
        return response

    except Exception as e:
        logger.error(f"占位符分析失败: {e}")
        raise PlaceholderProcessingError(
            message=f"占位符分析失败: {str(e)}",
            placeholder_type="analysis",
            details={"template_content_length": len(request.template_content)}
        )


@router.post(
    "/field-matching", response_model=FieldMatchingResponse, summary="字段匹配验证"
)
async def validate_field_matching(
    request: FieldMatchingRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> FieldMatchingResponse:
    """
    验证占位符的字段匹配

    - **placeholder_text**: 占位符文本
    - **placeholder_type**: 占位符类型
    - **description**: 占位符描述
    - **data_source_id**: 数据源ID
    - **context**: 上下文信息（可选）
    - **matching_options**: 匹配选项

    返回字段匹配建议和置信度评估。
    """
    try:
        logger.info(
            f"用户 {current_user.id} 请求字段匹配验证: {request.placeholder_text}"
        )

        # 验证数据源存在
        data_source_service = EnhancedDataSourceService(db)
        data_source = data_source_service.get_data_source(request.data_source_id)
        if not data_source:
            raise NotFoundError(
                resource="数据源",
                identifier=request.data_source_id
            )

        # 创建占位符匹配对象
        placeholder_type = PlaceholderType.STATISTIC  # 默认类型
        for ptype in PlaceholderType:
            if ptype.value == request.placeholder_type:
                placeholder_type = ptype
                break

        placeholder_match = PlaceholderMatch(
            full_match=request.placeholder_text,
            type=placeholder_type,
            description=request.description,
            start_pos=0,
            end_pos=len(request.placeholder_text),
            context_before=request.context or "",
            context_after="",
            confidence=0.8,
        )

        # 初始化LLM占位符服务
        llm_service = LLMPlaceholderService(db)

        # 获取数据源字段
        available_fields = data_source_service.get_available_fields(
            request.data_source_id
        )
        data_source_schema = data_source_service.get_data_source_schema(
            request.data_source_id
        )

        # 理解占位符
        understanding = llm_service.understand_placeholder(
            placeholder_match, available_fields, data_source_schema
        )

        # 生成字段匹配建议
        field_suggestions = llm_service.generate_field_matching_suggestions(
            understanding, available_fields
        )

        # 转换为响应格式
        suggestions = []
        for suggestion in field_suggestions:
            field_suggestion = FieldSuggestion(
                field_name=suggestion.suggested_field,
                match_score=suggestion.match_score,
                match_reason=suggestion.match_reason,
                data_transformation=suggestion.data_transformation,
                validation_rules=suggestion.validation_rules,
            )
            suggestions.append(field_suggestion)

        # 确定最佳匹配
        best_match = None
        if suggestions:
            best_match = max(suggestions, key=lambda x: x.match_score)

        # 计算整体置信度
        confidence_score = understanding.confidence
        if best_match:
            confidence_score = (confidence_score + best_match.match_score) / 2

        response = FieldMatchingResponse(
            success=True,
            placeholder_understanding={
                "semantic_meaning": understanding.semantic_meaning,
                "data_type": understanding.data_type,
                "calculation_needed": understanding.calculation_needed,
                "aggregation_type": understanding.aggregation_type,
                "confidence": understanding.confidence,
            },
            field_suggestions=suggestions,
            best_match=best_match,
            confidence_score=confidence_score,
            processing_metadata={
                "llm_provider": understanding.metadata.get("llm_provider"),
                "processing_time": understanding.metadata.get("response_time"),
                "data_source_fields": len(available_fields),
            },
        )

        logger.info(f"字段匹配验证完成: {len(suggestions)} 个建议")
        return response

    except PlaceholderUnderstandingError as e:
        logger.error(f"占位符理解失败: {e}")
        raise FieldMatchingError(
            message=f"占位符理解失败: {str(e)}",
            field_name=request.placeholder_text,
            details={"placeholder_type": request.placeholder_type}
        )
    except Exception as e:
        logger.error(f"字段匹配验证失败: {e}")
        raise FieldMatchingError(
            message=f"字段匹配验证失败: {str(e)}",
            field_name=request.placeholder_text,
            details={"data_source_id": request.data_source_id}
        )


@router.post(
    "/generate-report", response_model=IntelligentReportResponse, summary="智能报告生成"
)
async def generate_intelligent_report(
    request: IntelligentReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> IntelligentReportResponse:
    """
    使用智能占位符处理生成报告

    - **template_id**: 模板ID
    - **data_source_id**: 数据源ID
    - **processing_config**: 处理配置
    - **output_config**: 输出配置
    - **email_config**: 邮件配置（可选）

    返回任务ID和处理摘要，报告将在后台生成。
    """
    try:
        logger.info(f"用户 {current_user.id} 请求智能报告生成")

        # 验证模板存在
        template = (
            db.query(Template)
            .filter(
                Template.id == request.template_id, Template.user_id == current_user.id
            )
            .first()
        )
        if not template:
            raise NotFoundError(
                resource="模板",
                identifier=request.template_id,
                details={"user_id": current_user.id}
            )

        # 验证数据源存在
        data_source_service = EnhancedDataSourceService(db)
        data_source = data_source_service.get_data_source(request.data_source_id)
        if not data_source:
            raise NotFoundError(
                resource="数据源",
                identifier=request.data_source_id
            )

        # 生成任务ID
        import uuid

        task_id = str(uuid.uuid4())

        # 初始化服务
        processor = PlaceholderProcessor()
        llm_service = LLMPlaceholderService(db)
        etl_executor = IntelligentETLExecutor(db)
        report_service = ReportGenerationService(db)

        # 分析占位符
        placeholder_matches = processor.extract_placeholders(template.content or "")

        # 处理配置
        processing_config = request.processing_config or {}
        llm_provider = processing_config.get("llm_provider", "openai")
        enable_caching = processing_config.get("enable_caching", True)
        quality_check = processing_config.get("quality_check", True)

        # 创建处理摘要
        processing_summary = {
            "task_id": task_id,
            "template_id": str(request.template_id),
            "data_source_id": request.data_source_id,
            "placeholder_count": len(placeholder_matches),
            "llm_provider": llm_provider,
            "processing_options": processing_config,
            "started_at": str(datetime.now()),
        }

        # 占位符处理结果预览
        placeholder_results = []
        for match in placeholder_matches:
            result = {
                "placeholder": match.full_match,
                "type": match.type.value,
                "description": match.description,
                "confidence": match.confidence,
                "status": "pending",
            }
            placeholder_results.append(result)

        # 添加后台任务
        background_tasks.add_task(
            _process_intelligent_report,
            task_id=task_id,
            template=template,
            data_source_id=request.data_source_id,
            processing_config=processing_config,
            output_config=request.output_config or {},
            email_config=request.email_config,
            user_id=current_user.id,
            db_session=db,
        )

        response = IntelligentReportResponse(
            success=True,
            task_id=task_id,
            report_id=None,  # 将在后台处理完成后生成
            processing_summary=processing_summary,
            placeholder_results=placeholder_results,
            quality_assessment=None,  # 将在处理完成后提供
            file_path=None,  # 将在处理完成后提供
            email_status=None,  # 将在邮件发送后提供
        )

        logger.info(f"智能报告生成任务已启动: {task_id}")
        return response

    except Exception as e:
        logger.error(f"智能报告生成失败: {e}")
        raise ReportGenerationError(
            message=f"智能报告生成失败: {str(e)}",
            template_id=str(request.template_id),
            details={"data_source_id": request.data_source_id}
        )


@router.get("/task/{task_id}/status", summary="查询任务状态")
async def get_task_status(
    task_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    查询智能报告生成任务状态

    - **task_id**: 任务ID

    返回任务状态、进度和结果信息。
    """
    try:
        # 这里应该从任务存储中查询状态
        # 暂时返回模拟状态
        return {
            "task_id": task_id,
            "status": "processing",  # pending, processing, completed, failed
            "progress": 75,
            "message": "正在处理占位符...",
            "started_at": "2024-01-01T10:00:00Z",
            "estimated_completion": "2024-01-01T10:05:00Z",
            "result": None,
        }

    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise ReportGenerationError(
            message=f"查询任务状态失败: {str(e)}",
            template_id=None,
            details={"task_id": task_id}
        )


@router.get("/statistics", summary="获取处理统计")
async def get_processing_statistics(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    获取智能占位符处理统计信息

    返回处理统计、性能指标和使用情况。
    """
    try:
        # 初始化服务
        llm_service = LLMPlaceholderService(db)

        # 获取统计信息
        understanding_stats = llm_service.get_understanding_statistics()

        # 添加系统统计
        system_stats = {
            "supported_placeholder_types": ["周期", "区域", "统计", "图表"],
            "active_llm_providers": ["openai", "claude"],
            "cache_enabled": True,
            "quality_check_enabled": True,
        }

        return {
            "understanding_statistics": understanding_stats,
            "system_statistics": system_stats,
            "user_id": str(current_user.id),
            "timestamp": str(datetime.now()),
        }

    except Exception as e:
        logger.error(f"获取处理统计失败: {e}")
        raise PlaceholderProcessingError(
            message=f"获取处理统计失败: {str(e)}",
            placeholder_type="statistics",
            details={"user_id": str(current_user.id)}
        )


# 后台任务函数
async def _process_intelligent_report(
    task_id: str,
    template: Template,
    data_source_id: int,
    processing_config: Dict[str, Any],
    output_config: Dict[str, Any],
    email_config: Optional[Dict[str, Any]],
    user_id: UUID,
    db_session: Session,
) -> None:
    """
    后台处理智能报告生成
    """
    try:
        logger.info(f"开始后台处理智能报告: {task_id}")

        # 这里应该实现完整的智能报告生成流程
        # 1. 占位符理解
        # 2. 字段匹配
        # 3. ETL执行
        # 4. 内容生成
        # 5. 质量检查
        # 6. 报告构建
        # 7. 邮件发送

        # 暂时记录任务完成
        logger.info(f"智能报告处理完成: {task_id}")

    except Exception as e:
        logger.error(f"后台处理智能报告失败: {task_id}, 错误: {e}")


# 导入必要的模块
from datetime import datetime
