"""
占位符分析API端点

为前端提供占位符分析的REST API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.ai.facades.placeholder_analysis_facade import create_placeholder_analysis_facade

router = APIRouter()


# ====== 请求和响应模型 ======

class PlaceholderAnalysisRequest(BaseModel):
    """占位符分析请求"""
    template_id: str
    force_reanalyze: bool = False


class BatchPlaceholderRequest(BaseModel):
    """批量占位符分析请求"""
    placeholder_ids: List[str]
    force_reanalyze: bool = False


class TaskPlaceholderRequest(BaseModel):
    """任务占位符检查请求"""
    placeholder_ids: List[str]
    task_id: Optional[str] = None


class PlaceholderAnalysisResponse(BaseModel):
    """占位符分析响应"""
    success: bool
    message: str
    total_count: int
    analyzed_count: int
    failed_count: int = 0
    results: List[Dict[str, Any]] = []
    summary: Optional[Dict[str, Any]] = None


class PlaceholderStatusResponse(BaseModel):
    """占位符状态响应"""
    total_count: int
    analyzed_count: int
    pending_count: int
    error_count: int
    placeholders: List[Dict[str, Any]] = []


class TaskPlaceholderResponse(BaseModel):
    """任务占位符响应"""
    total_count: int
    ready_count: int
    need_analysis_count: int
    all_ready: bool
    results: List[Dict[str, Any]] = []


# ====== 模版占位符分析端点 ======

@router.post("/templates/{template_id}/placeholders/analyze", 
             response_model=PlaceholderAnalysisResponse)
async def analyze_template_placeholders(
    template_id: str,
    request: PlaceholderAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    分析模版中的所有占位符
    
    用于上传模版后在占位符页面主动调用分析
    """
    
    try:
        facade = create_placeholder_analysis_facade(db)
        
        result = await facade.analyze_template_placeholders(
            template_id=template_id,
            user_id=str(current_user.id),
            force_reanalyze=request.force_reanalyze
        )
        
        return PlaceholderAnalysisResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"占位符分析失败: {str(e)}"
        )


@router.get("/templates/{template_id}/placeholders/status",
            response_model=PlaceholderStatusResponse)
async def get_template_placeholder_status(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取模版占位符的分析状态
    
    用于在占位符页面展示各占位符的分析状态
    """
    
    try:
        facade = create_placeholder_analysis_facade(db)
        
        result = await facade.get_template_placeholder_status(template_id)
        
        return PlaceholderStatusResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取占位符状态失败: {str(e)}"
        )


# ====== 任务执行相关端点 ======

@router.post("/tasks/placeholders/check", 
             response_model=TaskPlaceholderResponse)
async def check_task_placeholders_sql(
    request: TaskPlaceholderRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    检查任务中的占位符是否都有可用的SQL
    
    用于任务执行前检查，确保所有占位符都已分析
    """
    
    try:
        facade = create_placeholder_analysis_facade(db)
        
        result = await facade.batch_ensure_placeholders_sql_for_task(
            placeholder_ids=request.placeholder_ids,
            user_id=str(current_user.id),
            task_id=request.task_id
        )
        
        return TaskPlaceholderResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查任务占位符失败: {str(e)}"
        )


@router.get("/placeholders/{placeholder_id}/sql")
async def get_placeholder_sql(
    placeholder_id: str,
    task_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取单个占位符的SQL
    
    用于任务执行时获取占位符的SQL用于ETL
    如果没有现成的SQL会自动分析生成
    """
    
    try:
        facade = create_placeholder_analysis_facade(db)
        
        result = await facade.ensure_placeholder_sql_for_task(
            placeholder_id=placeholder_id,
            user_id=str(current_user.id),
            task_id=task_id
        )
        
        if result.get('success'):
            return {
                "success": True,
                "placeholder_id": placeholder_id,
                "sql": result.get('sql'),
                "confidence": result.get('confidence', 0.0),
                "target_table": result.get('target_table'),
                "source": result.get('source'),  # "stored" | "generated"
                "metadata": {
                    "semantic_type": result.get('semantic_type'),
                    "explanation": result.get('explanation'),
                    "last_analysis_at": result.get('last_analysis_at'),
                    "analysis_timestamp": result.get('analysis_timestamp')
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": result.get('error', 'SQL获取失败'),
                    "needs_analysis": result.get('needs_analysis', True)
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取占位符SQL失败: {str(e)}"
        )


# ====== 单个占位符操作端点 ======

@router.post("/placeholders/{placeholder_id}/analyze")
async def analyze_single_placeholder(
    placeholder_id: str,
    force_reanalyze: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    分析单个占位符
    
    用于单独分析某个占位符
    """
    
    try:
        facade = create_placeholder_analysis_facade(db)
        
        # 先获取占位符信息
        from app.services.ai.facades.placeholder_analysis_facade import PlaceholderAnalysisFacade
        facade_instance = PlaceholderAnalysisFacade(db)
        placeholder_info = await facade_instance._get_placeholder_info(placeholder_id)
        
        if not placeholder_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="找不到指定的占位符"
            )
        
        # 执行分析
        from app.services.ai.agents.placeholder_sql_agent import PlaceholderSQLAnalyzer
        analyzer = PlaceholderSQLAnalyzer(db_session=db, user_id=str(current_user.id))
        
        result = await analyzer.analyze_placeholder(
            placeholder_id=placeholder_id,
            placeholder_text=placeholder_info['placeholder_name'],
            data_source_id=placeholder_info['data_source_id'],
            placeholder_type=placeholder_info['placeholder_type'],
            template_id=placeholder_info.get('template_id'),
            force_reanalyze=force_reanalyze
        )
        
        return {
            "success": result.success,
            "placeholder_id": placeholder_id,
            "result": result.to_dict() if result.success else None,
            "error": result.error_message if not result.success else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析占位符失败: {str(e)}"
        )


@router.get("/placeholders/{placeholder_id}/status")
async def get_placeholder_status(
    placeholder_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取单个占位符的分析状态
    """
    
    try:
        from app.services.ai.agents.placeholder_sql_agent import PlaceholderSQLAnalyzer
        analyzer = PlaceholderSQLAnalyzer(db_session=db, user_id=str(current_user.id))
        
        result = await analyzer.check_stored_sql(placeholder_id)
        
        return {
            "placeholder_id": placeholder_id,
            "has_sql": result.get('has_sql', False),
            "sql": result.get('sql') if result.get('has_sql') else None,
            "last_analysis_at": result.get('last_analysis_at'),
            "confidence": result.get('confidence', 0.0),
            "target_table": result.get('target_table'),
            "status": "analyzed" if result.get('has_sql') else "pending"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取占位符状态失败: {str(e)}"
        )


# ====== 批量操作端点 ======

@router.post("/placeholders/batch-analyze")
async def batch_analyze_placeholders(
    request: BatchPlaceholderRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    批量分析指定的占位符
    """
    
    try:
        from app.services.ai.agents.placeholder_sql_agent import PlaceholderSQLAnalyzer
        analyzer = PlaceholderSQLAnalyzer(db_session=db, user_id=str(current_user.id))
        
        # 构建批量请求
        analysis_requests = []
        for placeholder_id in request.placeholder_ids:
            # 获取占位符信息
            from app.services.ai.facades.placeholder_analysis_facade import PlaceholderAnalysisFacade
            facade_instance = PlaceholderAnalysisFacade(db)
            placeholder_info = await facade_instance._get_placeholder_info(placeholder_id)
            
            if placeholder_info:
                analysis_requests.append({
                    'placeholder_id': placeholder_id,
                    'placeholder_text': placeholder_info['placeholder_name'],
                    'placeholder_type': placeholder_info['placeholder_type'],
                    'data_source_id': placeholder_info['data_source_id'],
                    'template_id': placeholder_info.get('template_id'),
                    'force_reanalyze': request.force_reanalyze
                })
        
        if not analysis_requests:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="没有找到有效的占位符信息"
            )
        
        # 执行批量分析
        results = await analyzer.batch_analyze(analysis_requests)
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        return {
            "success": True,
            "total_count": len(results),
            "analyzed_count": len(successful_results),
            "failed_count": len(failed_results),
            "results": [r.to_dict() for r in results]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量分析占位符失败: {str(e)}"
        )


# ====== 系统状态端点 ======

@router.get("/system/placeholder-analysis/stats")
async def get_placeholder_analysis_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取占位符分析系统统计信息
    """
    
    try:
        from app.models.template_placeholder import TemplatePlaceholder
        
        # 统计占位符总数
        total_placeholders = db.query(TemplatePlaceholder).count()
        
        # 统计已分析的占位符
        analyzed_placeholders = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.generated_sql.isnot(None)
        ).count()
        
        # 统计最近分析的占位符
        from datetime import datetime, timedelta
        recent_analyzed = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.last_analysis_at >= datetime.now() - timedelta(days=7)
        ).count()
        
        return {
            "total_placeholders": total_placeholders,
            "analyzed_placeholders": analyzed_placeholders,
            "pending_placeholders": total_placeholders - analyzed_placeholders,
            "analysis_coverage": round(analyzed_placeholders / total_placeholders * 100, 2) if total_placeholders > 0 else 0,
            "recent_analyzed": recent_analyzed,
            "system_status": "healthy"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统统计失败: {str(e)}"
        )