"""
LLM编排API端点
==============

提供LLM编排相关的REST API接口
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.application.llm import get_llm_orchestration_service

router = APIRouter()


# Request Models
class SQLGenerationRequest(BaseModel):
    """SQL生成请求"""
    query_description: str = Field(..., description="查询描述", example="查询最近30天的订单总数")
    timeout_seconds: int = Field(default=60, description="超时时间（秒）", ge=10, le=300)


class DataAnalysisRequest(BaseModel):
    """数据分析请求"""
    business_question: str = Field(..., description="业务问题", example="用户留存率如何变化？")
    context_info: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class ReportTemplateRequest(BaseModel):
    """报告模板生成请求"""
    report_type: str = Field(..., description="报告类型", example="销售分析")
    data_sources: List[str] = Field(..., description="数据源列表", example=["orders", "users", "products"])
    target_audience: str = Field(default="business_users", description="目标受众")


# Response Models
class SQLGenerationResponse(BaseModel):
    """SQL生成响应"""
    success: bool
    sql_query: str
    explanation: str
    confidence: float
    execution_time: float
    llm_participated: bool


class DataAnalysisResponse(BaseModel):
    """数据分析响应"""
    success: bool
    analysis: str
    recommended_approach: str
    confidence: float


class ReportTemplateResponse(BaseModel):
    """报告模板响应"""
    success: bool
    template: str
    suggestions: Dict[str, Any]
    confidence: float


class UserLLMStatusResponse(BaseModel):
    """用户LLM状态响应"""
    user_id: str
    can_use_llm: bool
    has_config: bool
    default_model: str
    recommendations: List[str]
    needs_setup: bool


# API Endpoints

@router.post("/sql/generate", response_model=SQLGenerationResponse)
async def generate_sql_query(
    request: SQLGenerationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    生成SQL查询语句
    
    基于自然语言描述，使用LLM生成对应的SQL查询语句。
    """
    service = get_llm_orchestration_service()
    
    result = await service.generate_sql_query(
        user_id=str(current_user.id),
        query_description=request.query_description,
        timeout_seconds=request.timeout_seconds
    )
    
    return SQLGenerationResponse(**result)


@router.post("/analysis/data-requirements", response_model=DataAnalysisResponse)
async def analyze_data_requirements(
    request: DataAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    分析数据需求
    
    基于业务问题，分析需要什么数据、如何获取数据等。
    """
    service = get_llm_orchestration_service()
    
    result = await service.analyze_data_requirements(
        user_id=str(current_user.id),
        business_question=request.business_question,
        context_info=request.context_info
    )
    
    return DataAnalysisResponse(**result)


@router.post("/reports/generate-template", response_model=ReportTemplateResponse)
async def generate_report_template(
    request: ReportTemplateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    生成报告模板
    
    基于报告类型和数据源，生成结构化的报告模板。
    """
    service = get_llm_orchestration_service()
    
    result = await service.generate_report_template(
        user_id=str(current_user.id),
        report_type=request.report_type,
        data_sources=request.data_sources,
        target_audience=request.target_audience
    )
    
    return ReportTemplateResponse(**result)


@router.get("/user/status", response_model=UserLLMStatusResponse)
async def get_user_llm_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取用户LLM服务状态
    
    检查用户是否配置了LLM服务，以及相关的配置信息。
    """
    service = get_llm_orchestration_service()
    
    status = await service.check_user_llm_status(str(current_user.id))
    
    return UserLLMStatusResponse(**status)


@router.post("/user/setup")
async def setup_user_llm(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    设置用户LLM配置
    
    为用户自动配置LLM服务，如果用户还没有配置的话。
    """
    service = get_llm_orchestration_service()
    
    # 检查是否需要设置
    status = await service.check_user_llm_status(str(current_user.id))
    
    if not status.get('needs_setup', True):
        return {
            "success": True,
            "message": "用户LLM配置已存在，无需重新设置",
            "status": status
        }
    
    # 后台执行设置
    async def setup_task():
        success = await service.setup_user_llm_if_needed(str(current_user.id))
        return success
    
    background_tasks.add_task(setup_task)
    
    return {
        "success": True,
        "message": "正在后台为用户设置LLM配置",
        "estimated_time": "几秒钟"
    }


@router.get("/system/status")
async def get_system_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取LLM编排系统状态
    
    需要管理员权限。
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限"
        )
    
    service = get_llm_orchestration_service()
    orchestrator = await service._get_orchestrator()
    
    status = await orchestrator.get_system_status()
    
    return {
        "system_status": status,
        "service_type": "llm_orchestration_service",
        "version": "1.0.0"
    }