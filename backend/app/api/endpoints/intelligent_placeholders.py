"""智能占位符API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import re

from app.core.architecture import ApiResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.template import Template
from app.models.data_source import DataSource
from app.crud import template as crud_template
from app.crud.crud_data_source import crud_data_source

router = APIRouter()


@router.post("/analyze", response_model=ApiResponse)
async def analyze_template_placeholders(
    template_id: str = Query(..., description="模板ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """分析模板中的占位符"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 获取模板
    template = crud_template.get(db, id=template_id)
    if not template or (template.user_id != user_id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    content = template.content or ''
    
    # 提取占位符
    placeholder_pattern = re.compile(r"{{\s*([\w\-_]+)\s*}}")
    matches = placeholder_pattern.finditer(content)
    
    placeholders = []
    for i, match in enumerate(matches):
        placeholder_name = match.group(1)
        start_pos = match.start()
        end_pos = match.end()
        
        # 获取上下文
        context_start = max(0, start_pos - 50)
        context_end = min(len(content), end_pos + 50)
        context_before = content[context_start:start_pos]
        context_after = content[end_pos:context_end]
        
        # 推断占位符类型
        placeholder_type = infer_placeholder_type(placeholder_name, context_before, context_after)
        
        placeholders.append({
            "placeholder_text": match.group(0),
            "placeholder_name": placeholder_name,
            "placeholder_type": placeholder_type,
            "description": generate_placeholder_description(placeholder_name, placeholder_type),
            "position": start_pos,
            "context_before": context_before,
            "context_after": context_after,
            "confidence": 0.8  # 模拟置信度
        })
    
    # 统计占位符类型分布
    type_distribution = {}
    for placeholder in placeholders:
        ptype = placeholder["placeholder_type"]
        type_distribution[ptype] = type_distribution.get(ptype, 0) + 1
    
    return ApiResponse(
        success=True,
        data={
            "placeholders": placeholders,
            "total_count": len(placeholders),
            "type_distribution": type_distribution,
            "validation_result": {"valid": True},
            "processing_errors": [],
            "estimated_processing_time": len(placeholders) * 0.1
        },
        message="占位符分析完成"
    )


@router.post("/field-matching", response_model=ApiResponse)
async def match_placeholder_fields(
    template_id: str = Query(..., description="模板ID"),
    data_source_id: str = Query(..., description="数据源ID"),
    placeholder_name: str = Query(..., description="占位符名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """为占位符匹配数据源字段"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 验证模板和数据源权限
    template = crud_template.get(db, id=template_id)
    if not template or (template.user_id != user_id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    try:
        ds_uuid = UUID(data_source_id)
    except Exception:
        raise HTTPException(status_code=422, detail="数据源ID格式错误")
    
    data_source = crud_data_source.get(db, id=ds_uuid)
    if not data_source or data_source.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
    
    # 模拟字段匹配逻辑
    # 在实际应用中，这里应该分析数据源的字段结构
    mock_fields = [
        "name", "email", "phone", "address", "company", "title", 
        "date", "amount", "quantity", "price", "total", "description"
    ]
    
    field_suggestions = []
    for field in mock_fields:
        # 计算匹配分数（简单的字符串相似度）
        match_score = calculate_similarity(placeholder_name.lower(), field.lower())
        if match_score > 0.3:  # 只返回相似度较高的字段
            field_suggestions.append({
                "field_name": field,
                "match_score": match_score,
                "match_reason": f"字段名称与占位符 '{placeholder_name}' 相似",
                "data_transformation": None,
                "validation_rules": [f"字段 {field} 不能为空"]
            })
    
    # 按匹配分数排序
    field_suggestions.sort(key=lambda x: x["match_score"], reverse=True)
    
    best_match = field_suggestions[0] if field_suggestions else None
    
    return ApiResponse(
        success=True,
        data={
            "placeholder_understanding": {
                "name": placeholder_name,
                "inferred_type": infer_placeholder_type(placeholder_name, "", ""),
                "context": "模板占位符字段匹配"
            },
            "field_suggestions": field_suggestions[:5],  # 返回前5个建议
            "best_match": best_match,
            "confidence_score": best_match["match_score"] if best_match else 0,
            "processing_metadata": {
                "data_source_name": data_source.name,
                "template_name": template.name,
                "analysis_time": "2024-01-01T12:00:00Z"
            }
        },
        message="字段匹配完成"
    )


@router.post("/generate-report", response_model=ApiResponse)
async def generate_intelligent_report(
    template_id: str,
    data_source_id: str,
    processing_config: Optional[Dict[str, Any]] = None,
    output_config: Optional[Dict[str, Any]] = None,
    email_config: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """使用智能占位符生成报告"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 验证权限
    template = crud_template.get(db, id=template_id)
    if not template or (template.user_id != user_id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    try:
        ds_uuid = UUID(data_source_id)
    except Exception:
        raise HTTPException(status_code=422, detail="数据源ID格式错误")
    
    data_source = crud_data_source.get(db, id=ds_uuid)
    if not data_source or data_source.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限访问"
        )
    
    # 生成任务ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # 模拟报告生成过程
    # 在实际应用中，这里应该启动后台任务
    
    return ApiResponse(
        success=True,
        data={
            "task_id": task_id,
            "report_id": None,  # 报告生成完成后会有ID
            "processing_summary": {
                "template_name": template.name,
                "data_source_name": data_source.name,
                "placeholders_processed": 0,
                "estimated_completion": "2024-01-01T12:05:00Z"
            },
            "placeholder_results": [],
            "quality_assessment": {
                "completeness": 0.95,
                "accuracy": 0.90,
                "consistency": 0.88
            },
            "file_path": None,  # 生成完成后会有文件路径
            "email_status": email_config and {
                "sent": False,
                "recipients": email_config.get("recipients", []),
                "scheduled_time": None
            }
        },
        message="智能报告生成任务已提交"
    )


@router.get("/task/{task_id}/status", response_model=ApiResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取智能占位符任务状态"""
    # 模拟任务状态查询
    # 在实际应用中，这里应该查询真实的任务状态
    
    return ApiResponse(
        success=True,
        data={
            "task_id": task_id,
            "status": "completed",  # pending, processing, completed, failed
            "progress": 100,
            "message": "报告生成完成",
            "result": {
                "report_id": "report_123",
                "file_path": f"/reports/{task_id}.docx",
                "download_url": f"/api/v1/reports/download/{task_id}"
            },
            "error": None,
            "started_at": "2024-01-01T12:00:00Z",
            "completed_at": "2024-01-01T12:05:00Z"
        },
        message="任务状态查询成功"
    )


@router.get("/statistics", response_model=ApiResponse)
async def get_placeholder_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取智能占位符使用统计"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    # 模拟统计数据
    # 在实际应用中，这里应该查询真实的统计数据
    
    return ApiResponse(
        success=True,
        data={
            "total_templates_analyzed": 25,
            "total_placeholders_found": 150,
            "most_common_types": {
                "text": 80,
                "number": 35,
                "date": 25,
                "image": 10
            },
            "accuracy_rate": 0.92,
            "processing_time_avg": 2.5,
            "user_satisfaction": 4.3,
            "recent_activity": [
                {
                    "template_name": "销售报告模板",
                    "placeholders_count": 12,
                    "processed_at": "2024-01-01T11:30:00Z"
                },
                {
                    "template_name": "客户分析模板", 
                    "placeholders_count": 8,
                    "processed_at": "2024-01-01T10:15:00Z"
                }
            ]
        },
        message="统计数据获取成功"
    )


def infer_placeholder_type(name: str, context_before: str, context_after: str) -> str:
    """推断占位符类型"""
    name_lower = name.lower()
    
    # 日期类型
    if any(keyword in name_lower for keyword in ['date', 'time', 'created', 'updated', '日期', '时间']):
        return 'date'
    
    # 数字类型
    if any(keyword in name_lower for keyword in ['amount', 'price', 'total', 'count', 'number', '金额', '价格', '总计', '数量']):
        return 'number'
    
    # 图片类型
    if any(keyword in name_lower for keyword in ['image', 'img', 'photo', 'picture', '图片', '照片']):
        return 'image'
    
    # 表格类型
    if any(keyword in name_lower for keyword in ['table', 'list', 'data', '表格', '列表', '数据']):
        return 'table'
    
    # 默认为文本类型
    return 'text'


def generate_placeholder_description(name: str, ptype: str) -> str:
    """生成占位符描述"""
    type_descriptions = {
        'text': f"文本占位符 '{name}'，用于显示文本内容",
        'number': f"数字占位符 '{name}'，用于显示数值数据",
        'date': f"日期占位符 '{name}'，用于显示日期时间信息",
        'image': f"图片占位符 '{name}'，用于插入图片内容",
        'table': f"表格占位符 '{name}'，用于显示表格数据"
    }
    return type_descriptions.get(ptype, f"占位符 '{name}'")


def calculate_similarity(str1: str, str2: str) -> float:
    """计算字符串相似度（简单实现）"""
    if str1 == str2:
        return 1.0
    
    # 简单的字符串包含检查
    if str1 in str2 or str2 in str1:
        return 0.8
    
    # 计算公共字符数
    common_chars = set(str1) & set(str2)
    total_chars = set(str1) | set(str2)
    
    if not total_chars:
        return 0.0
    
    return len(common_chars) / len(total_chars)