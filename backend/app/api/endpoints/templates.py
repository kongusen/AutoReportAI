"""模板管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.template import Template as TemplateModel
from app.schemas.template import TemplateCreate, TemplateUpdate, Template as TemplateSchema
from app.crud import template as crud_template
from app.services.template_parser_service import template_parser
import re

router = APIRouter()


@router.get("/", response_model=ApiResponse)
async def get_templates(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    template_type: Optional[str] = Query(None, description="模板类型"),
    is_public: Optional[bool] = Query(None, description="是否公开"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模板列表"""
    user_id = current_user.id
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    query = db.query(TemplateModel).filter(
        (TemplateModel.user_id == user_id) | (TemplateModel.is_public == True)
    )
    
    if template_type:
        query = query.filter(TemplateModel.template_type == template_type)
    
    if is_public is not None:
        query = query.filter(TemplateModel.is_public == is_public)
    
    if search:
        query = query.filter(TemplateModel.name.contains(search))
    
    total = query.count()
    templates = query.offset(skip).limit(limit).all()
    template_schemas = [TemplateSchema.model_validate(t) for t in templates]
    template_dicts = [t.model_dump() | {"unique_id": str(t.id)} for t in template_schemas]
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=template_dicts,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建模板"""
    template_obj = crud_template.create_with_user(
        db, 
        obj_in=template, 
        user_id=current_user.id
    )
    template_schema = TemplateSchema.model_validate(template_obj)
    template_dict = template_schema.model_dump()
    template_dict['unique_id'] = str(template_dict.get('id'))
    return {"id": template_dict["id"], **template_dict}


@router.get("/{template_id}", response_model=ApiResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取特定模板"""
    template = crud_template.get(db, id=template_id)
    if not template or (template.user_id != current_user.id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    template_schema = TemplateSchema.model_validate(template)
    template_dict = template_schema.model_dump()
    template_dict['unique_id'] = str(template_dict.get('id'))
    return ApiResponse(
        success=True,
        data=template_dict,
        message="获取模板成功"
    )


@router.put("/{template_id}", response_model=ApiResponse)
async def update_template(
    template_id: str,
    template_update: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新模板"""
    template = crud_template.get(db, id=template_id)
    if not template or template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    template = crud_template.update(
        db, 
        db_obj=template, 
        obj_in=template_update
    )
    
    return ApiResponse(
        success=True,
        data=template,
        message="模板更新成功"
    )


@router.delete("/{template_id}", response_model=ApiResponse)
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除模板"""
    template = crud_template.get(db, id=template_id)
    if not template or template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    crud_template.remove(db, id=template_id)
    
    return ApiResponse(
        success=True,
        data={"template_id": template_id},
        message="模板删除成功"
    )


@router.post("/{template_id}/duplicate", response_model=ApiResponse)
async def duplicate_template(
    template_id: str,
    new_name: Optional[str] = Query(None, description="新模板名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """复制模板"""
    template = crud_template.get(db, id=template_id)
    if not template or (template.user_id != current_user.id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    # 创建新模板
    new_template_data = TemplateCreate(
        name=new_name or f"{template.name} (副本)",
        description=template.description,
        template_type=template.template_type,
        content=template.content,
        is_public=False,
        is_active=True
    )
    
    new_template = crud_template.create_with_user(
        db, 
        obj_in=new_template_data, 
        user_id=current_user.id
    )
    
    return ApiResponse(
        success=True,
        data=new_template,
        message="模板复制成功"
    )


@router.put("/{template_id}/upload", response_model=ApiResponse)
async def upload_template_file(
    template_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上传模板文件内容到已创建的模板"""
    # 验证模板存在且属于当前用户
    template = crud_template.get_user_template(db, template_id=template_id, user_id=current_user.id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail="模板不存在或无权限访问"
        )
    
    # 读取文件内容
    content = await file.read()
    
    # 根据文件扩展名确定模板类型
    file_extension = file.filename.split('.')[-1].lower() if file.filename else 'txt'
    template_type_map = {
        'docx': 'docx',
        'doc': 'docx',
        'xlsx': 'xlsx',
        'xls': 'xlsx',
        'html': 'html',
        'htm': 'html',
        'pdf': 'pdf',
        'txt': 'text'
    }
    template_type = template_type_map.get(file_extension, 'text')
    
    # 更新模板内容
    update_data = {
        "content": content.decode('utf-8') if template_type in ['text', 'html'] else content.hex(),
        "template_type": template_type,
        "original_filename": file.filename,
        "file_size": len(content)
    }
    
    updated_template = crud_template.update(db, db_obj=template, obj_in=update_data)
    
    return ApiResponse(
        success=True,
        data=updated_template,
        message="模板文件上传成功"
    )


@router.get("/{template_id}/preview", response_model=ApiResponse)
async def preview_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模板内容和占位符分布"""
    template = crud_template.get(db, id=template_id)
    if not template or (template.user_id != current_user.id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    content = template.content or ''
    # 提取 {{name}} 形式的占位符
    placeholder_pattern = re.compile(r"{{\s*([\w\-]+)\s*}}")
    found = set(m.group(1) for m in placeholder_pattern.finditer(content))
    placeholders = []
    for name in found:
        placeholders.append({"name": name, "found": True})
    return ApiResponse(
        success=True,
        data={
            "content": content,
            "placeholders": placeholders
        },
        message="模板预览成功"
    )
