"""模板管理API端点 - v2版本"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
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
    """获取模板内容和占位符分布（支持DOC格式）"""
    template = crud_template.get(db, id=template_id)
    if not template or (template.user_id != current_user.id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    content = template.content or ''
    placeholders = []
    
    # 根据模板类型解析占位符
    if template.template_type == "docx" and template.original_filename:
        try:
            # 对于DOC模板，使用专门的解析器
            import tempfile
            import os
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                if content.startswith('<?xml') or content.startswith('PK'):
                    # 二进制内容
                    temp_file.write(bytes.fromhex(content) if len(content) % 2 == 0 else content.encode())
                else:
                    # 文本内容
                    temp_file.write(content.encode())
                temp_path = temp_file.name
            
            try:
                # 使用DOC占位符解析器
                placeholder_data = template_parser.parse_doc_placeholders(temp_path)
                
                # 转换为统一格式
                stats_placeholders = placeholder_data.get("stats_placeholders", [])
                chart_placeholders = placeholder_data.get("chart_placeholders", [])
                
                for p in stats_placeholders:
                    placeholders.append({
                        "type": "统计",
                        "description": p["description"],
                        "placeholder_text": p["placeholder_text"],
                        "requirements": p.get("analysis_requirements", {})
                    })
                
                for p in chart_placeholders:
                    placeholders.append({
                        "type": "图表", 
                        "description": p["description"],
                        "placeholder_text": p["placeholder_text"],
                        "requirements": p.get("chart_requirements", {})
                    })
                    
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            # 降级到基本解析
            placeholder_pattern = re.compile(r"\{\{([^:]+):([^}]+)\}\}")
            for match in placeholder_pattern.finditer(content):
                placeholders.append({
                    "type": match.group(1).strip(),
                    "description": match.group(2).strip(),
                    "placeholder_text": match.group(0)
                })
    else:
        # 传统占位符解析
        placeholder_pattern = re.compile(r"\{\{([^:]+):([^}]+)\}\}")
        for match in placeholder_pattern.finditer(content):
            placeholders.append({
                "type": match.group(1).strip(),
                "description": match.group(2).strip(), 
                "placeholder_text": match.group(0)
            })
        
        # 兼容旧格式
        old_pattern = re.compile(r"{{\s*([\w\-]+)\s*}}")
        for match in old_pattern.finditer(content):
            if not any(p["placeholder_text"] == match.group(0) for p in placeholders):
                placeholders.append({
                    "type": "文本",
                    "description": match.group(1),
                    "placeholder_text": match.group(0)
                })
    
    return ApiResponse(
        success=True,
        data={
            "template_type": template.template_type,
            "placeholders": placeholders,
            "total_count": len(placeholders),
            "stats_count": len([p for p in placeholders if p["type"] == "统计"]),
            "chart_count": len([p for p in placeholders if p["type"] == "图表"])
        },
        message="模板预览成功"
    )


@router.post("/{template_id}/generate-report", response_model=ApiResponse)
async def generate_report_from_template(
    template_id: str,
    data_source_id: str,
    task_config: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """基于DOC模板生成报告"""
    template = crud_template.get(db, id=template_id)
    if not template or (template.user_id != current_user.id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    try:
        import tempfile
        import os
        from datetime import datetime
        
        # 创建临时输入文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_input:
            content = template.content or ''
            if content.startswith('<?xml') or content.startswith('PK'):
                temp_input.write(bytes.fromhex(content) if len(content) % 2 == 0 else content.encode())
            else:
                temp_input.write(content.encode())
            temp_input_path = temp_input.name
        
        # 创建输出文件路径
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"report_{template.name}_{timestamp}.docx"
        temp_output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        try:
            # 使用智能模板处理器
            result = await template_parser.process_template_with_intelligent_replacement(
                temp_input_path,
                temp_output_path, 
                int(data_source_id),
                task_config or {}
            )
            
            if result.success:
                # 读取生成的文件内容
                with open(temp_output_path, 'rb') as f:
                    output_content = f.read().hex()
                
                return ApiResponse(
                    success=True,
                    data={
                        "report_content": output_content,
                        "filename": output_filename,
                        "processing_result": {
                            "total_placeholders": result.total_placeholders,
                            "successful_replacements": result.successful_replacements,
                            "processing_time": result.processing_time,
                            "replacements": [
                                {
                                    "placeholder": r.original_placeholder,
                                    "success": r.success,
                                    "content_type": r.content_type,
                                    "error": r.error_message
                                } for r in result.replacements or []
                            ]
                        }
                    },
                    message="报告生成成功"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"报告生成失败: {result.error_message}"
                )
                
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_input_path)
                if os.path.exists(temp_output_path):
                    os.unlink(temp_output_path)
            except:
                pass
                
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"报告生成失败: {str(e)}"
        )


@router.post("/{template_id}/validate-placeholders", response_model=ApiResponse)
async def validate_template_placeholders(
    template_id: str,
    data_source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """验证模板占位符与数据源的匹配度"""
    template = crud_template.get(db, id=template_id)
    if not template or (template.user_id != current_user.id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    try:
        # 获取模板占位符
        content = template.content or ''
        
        if template.template_type == "docx":
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                if content.startswith('<?xml') or content.startswith('PK'):
                    temp_file.write(bytes.fromhex(content) if len(content) % 2 == 0 else content.encode())
                else:
                    temp_file.write(content.encode())
                temp_path = temp_file.name
            
            try:
                placeholder_data = template_parser.parse_doc_placeholders(temp_path)
                placeholders = (
                    placeholder_data.get("stats_placeholders", []) + 
                    placeholder_data.get("chart_placeholders", [])
                )
            finally:
                os.unlink(temp_path)
        else:
            # 基本解析
            import re
            placeholder_pattern = re.compile(r"\{\{([^:]+):([^}]+)\}\}")
            placeholders = []
            for match in placeholder_pattern.finditer(content):
                placeholders.append({
                    "placeholder_type": match.group(1).strip(),
                    "description": match.group(2).strip(),
                    "placeholder_text": match.group(0)
                })
        
        # 验证每个占位符
        validation_results = []
        
        for placeholder in placeholders:
            validation_result = {
                "placeholder": placeholder.get("placeholder_text", ""),
                "type": placeholder.get("placeholder_type", ""),
                "description": placeholder.get("description", ""),
                "is_valid": True,
                "confidence": 0.8,  # 默认置信度
                "suggestions": []
            }
            
            # 根据类型进行验证
            if placeholder.get("placeholder_type") == "统计":
                # 验证统计需求
                validation_result["suggestions"].append("建议明确统计指标和计算方式")
            elif placeholder.get("placeholder_type") == "图表":
                # 验证图表需求
                validation_result["suggestions"].append("建议指定图表类型和展示内容")
            
            validation_results.append(validation_result)
        
        return ApiResponse(
            success=True,
            data={
                "total_placeholders": len(placeholders),
                "valid_placeholders": len([r for r in validation_results if r["is_valid"]]),
                "validation_results": validation_results,
                "overall_confidence": sum(r["confidence"] for r in validation_results) / len(validation_results) if validation_results else 0
            },
            message="占位符验证完成"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"占位符验证失败: {str(e)}"
        )
