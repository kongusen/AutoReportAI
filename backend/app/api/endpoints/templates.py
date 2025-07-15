from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/", response_model=List[schemas.Template])
def read_templates(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    include_public: bool = True,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """获取模板列表"""
    templates = crud.template.get_multi(
        db, 
        skip=skip, 
        limit=limit, 
        user_id=current_user.id,
        include_public=include_public
    )
    return templates


@router.post("/", response_model=schemas.Template)
def create_template(
    *,
    db: Session = Depends(deps.get_db),
    template_in: schemas.TemplateCreate,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """创建模板"""
    template = crud.template.create(db, obj_in=template_in, user_id=current_user.id)
    return template


@router.post("/upload", response_model=schemas.Template)
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
        content=content.decode('utf-8'),
        template_type=file.content_type or 'application/octet-stream',
        original_filename=file.filename,
        file_size=len(content),
        is_public=is_public
    )
    
    template = crud.template.create(db, obj_in=template_in, user_id=current_user.id)
    return template


@router.get("/{template_id}", response_model=schemas.Template)
def read_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: UUID,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """获取特定模板"""
    template = crud.template.get(db, id=str(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 检查权限
    if not template.is_public and template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return template


@router.put("/{template_id}", response_model=schemas.Template)
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
        raise HTTPException(status_code=404, detail="Template not found")
    
    if template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    template = crud.template.update(db, db_obj=template, obj_in=template_in)
    return template


@router.delete("/{template_id}", response_model=schemas.Template)
def delete_template(
    *,
    db: Session = Depends(deps.get_db),
    template_id: UUID,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """删除模板"""
    template = crud.template.get(db, id=str(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    template = crud.template.remove(db, id=str(template_id))
    return template
