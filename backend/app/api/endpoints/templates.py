from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.exceptions import (
    NotFoundError,
    AuthorizationError,
    ValidationError
)
from app.schemas.base import APIResponse, create_success_response, create_error_response

router = APIRouter()


@router.get(
    "/", 
    response_model=APIResponse[List[schemas.Template]],
    summary="获取模板列表",
    description="""
    获取用户可访问的模板列表，包括用户自己创建的模板和公共模板。
    
    **功能特性：**
    - 支持分页查询
    - 可选择是否包含公共模板
    - 按创建时间倒序排列
    - 返回模板基本信息和统计数据
    
    **使用场景：**
    - 模板管理页面展示
    - 报告生成时选择模板
    - 模板搜索和筛选
    """,
    responses={
        200: {
            "description": "成功获取模板列表",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "模板列表获取成功",
                        "data": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "name": "月度投诉分析报告",
                                "description": "月度投诉数据分析报告模板",
                                "template_type": "docx",
                                "is_public": False,
                                "created_at": "2024-01-01T10:00:00Z",
                                "updated_at": "2024-01-01T11:00:00Z",
                                "user_id": "user123",
                                "file_size": 2048,
                                "placeholder_count": 5
                            }
                        ]
                    }
                }
            }
        },
        401: {"description": "未授权访问"},
        422: {"description": "请求参数验证失败"}
    }
)
def read_templates(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    include_public: bool = True,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    获取模板列表
    
    Args:
        skip: 跳过的记录数，用于分页
        limit: 返回的记录数，最大1000
        include_public: 是否包含公共模板
        
    Returns:
        包含模板列表的API响应
    """
    templates = crud.template.get_multi(
        db,
        skip=skip,
        limit=limit,
        user_id=current_user.id,
        include_public=include_public,
    )
    return APIResponse[List[schemas.Template]](
        success=True,
        message="模板列表获取成功",
        data=templates
    )


@router.post(
    "/", 
    response_model=APIResponse[schemas.Template],
    summary="创建新模板",
    description="""
    创建一个新的报告模板。模板可以包含智能占位符，用于动态生成报告内容。
    
    **功能特性：**
    - 支持多种模板格式（docx, txt, html等）
    - 自动识别和解析智能占位符
    - 支持公共模板和私有模板
    - 自动计算模板统计信息
    
    **智能占位符格式：**
    - 统计类：`{{统计:投诉总数}}`
    - 区域类：`{{区域:主要投诉地区}}`
    - 周期类：`{{周期:本月}}`
    - 图表类：`{{图表:投诉趋势图}}`
    
    **使用场景：**
    - 创建标准化报告模板
    - 设计可复用的文档格式
    - 建立企业报告规范
    """,
    responses={
        201: {
            "description": "模板创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "模板创建成功",
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "月度投诉分析报告",
                            "description": "月度投诉数据分析报告模板",
                            "content": "本月共收到{{统计:投诉总数}}件投诉...",
                            "template_type": "docx",
                            "is_public": False,
                            "created_at": "2024-01-01T10:00:00Z",
                            "user_id": "user123",
                            "file_size": 256,
                            "placeholder_count": 2
                        }
                    }
                }
            }
        },
        400: {"description": "请求数据格式错误"},
        401: {"description": "未授权访问"},
        422: {"description": "数据验证失败"}
    }
)
def create_template(
    *,
    db: Session = Depends(deps.get_db),
    template_in: schemas.TemplateCreate,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    创建新模板
    
    Args:
        template_in: 模板创建数据，包含名称、描述、内容等信息
        
    Returns:
        包含新创建模板信息的API响应
        
    Raises:
        ValidationError: 当模板数据验证失败时
        AuthorizationError: 当用户无权限创建模板时
    """
    template = crud.template.create(db, obj_in=template_in, user_id=current_user.id)
    return APIResponse[schemas.Template](
        success=True,
        message="模板创建成功",
        data=template
    )


@router.post("/upload", response_model=APIResponse[schemas.Template])
async def upload_template(
    *,
    db: Session = Depends(deps.get_db),
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(...),
    is_public: bool = Form(False),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """上传模板文件"""
    # 读取文件内容
    content = await file.read()

    # 创建模板
    template_in = schemas.TemplateCreate(
        name=name,
        description=description,
        content=content.decode("utf-8"),
        template_type=file.content_type or "application/octet-stream",
        original_filename=file.filename,
        file_size=len(content),
        is_public=is_public,
    )

    template = crud.template.create(db, obj_in=template_in, user_id=current_user.id)
    return APIResponse[schemas.Template](
        success=True,
        message="模板上传成功",
        data=template
    )


@router.get("/{template_id}", response_model=APIResponse[schemas.Template])
def read_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: UUID,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """获取特定模板"""
    template = crud.template.get(db, id=str(template_id))
    if not template:
        raise NotFoundError(
            resource="模板",
            identifier=template_id
        )

    # 检查权限
    if not template.is_public and template.user_id != current_user.id:
        raise AuthorizationError(
            message="无权限访问此模板",
            details={"template_id": str(template_id), "user_id": current_user.id}
        )

    return APIResponse[schemas.Template](
        success=True,
        message="模板获取成功",
        data=template
    )


@router.put("/{template_id}", response_model=APIResponse[schemas.Template])
def update_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: UUID,
    template_in: schemas.TemplateUpdate,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """更新模板"""
    template = crud.template.get(db, id=str(template_id))
    if not template:
        raise NotFoundError(
            resource="模板",
            identifier=template_id
        )

    if template.user_id != current_user.id:
        raise AuthorizationError(
            message="无权限更新此模板",
            details={"template_id": str(template_id), "user_id": current_user.id}
        )

    template = crud.template.update(db, db_obj=template, obj_in=template_in)
    return APIResponse[schemas.Template](
        success=True,
        message="模板更新成功",
        data=template
    )


@router.delete("/{template_id}", response_model=APIResponse[schemas.Template])
def delete_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: UUID,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """删除模板"""
    template = crud.template.get(db, id=str(template_id))
    if not template:
        raise NotFoundError(
            resource="模板",
            identifier=template_id
        )

    if template.user_id != current_user.id:
        raise AuthorizationError(
            message="无权限删除此模板",
            details={"template_id": str(template_id), "user_id": current_user.id}
        )

    template = crud.template.remove(db, id=str(template_id))
    return APIResponse[schemas.Template](
        success=True,
        message="模板删除成功",
        data=template
    )
