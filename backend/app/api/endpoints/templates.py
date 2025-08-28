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
from app.services.domain.template.services.template_domain_service import TemplateParser
import re
import logging

logger = logging.getLogger(__name__)

# 创建全局实例
template_parser = TemplateParser()

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
        ((TemplateModel.user_id == user_id) | (TemplateModel.is_public == True)) &
        (TemplateModel.is_active == True)
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
    if not template or not template.is_active or (template.user_id != current_user.id and not template.is_public):
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
    if not template or not template.is_active or template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    template = crud_template.update(
        db, 
        db_obj=template, 
        obj_in=template_update
    )
    
    # Convert to schema for proper serialization
    template_schema = TemplateSchema.model_validate(template)
    template_dict = template_schema.model_dump()
    template_dict['unique_id'] = str(template_dict.get('id'))
    
    return ApiResponse(
        success=True,
        data=template_dict,
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
    if not template or not template.is_active or template.user_id != current_user.id:
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
    if not template or not template.is_active or (template.user_id != current_user.id and not template.is_public):
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
    
    # Convert to schema for proper serialization
    template_schema = TemplateSchema.model_validate(new_template)
    template_dict = template_schema.model_dump()
    template_dict['unique_id'] = str(template_dict.get('id'))
    
    return ApiResponse(
        success=True,
        data=template_dict,
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
    
    # Convert to schema for proper serialization
    template_schema = TemplateSchema.model_validate(updated_template)
    template_dict = template_schema.model_dump()
    template_dict['unique_id'] = str(template_dict.get('id'))
    
    return ApiResponse(
        success=True,
        data=template_dict,
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
    if not template or not template.is_active or (template.user_id != current_user.id and not template.is_public):
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
                try:
                    # 处理二进制内容（hex编码）
                    if content and all(c in '0123456789ABCDEFabcdef' for c in content.replace(' ', '').replace('\n', '')):
                        # 是hex编码的二进制内容
                        binary_data = bytes.fromhex(content.replace(' ', '').replace('\n', ''))
                        temp_file.write(binary_data)
                    elif content.startswith('PK'):
                        # 直接的二进制内容（docx文件头）
                        temp_file.write(content.encode('latin-1'))
                    elif content:
                        # 文本内容，直接写入
                        temp_file.write(content.encode('utf-8'))
                    else:
                        # 空内容，创建基本的docx结构
                        temp_file.write(b'PK\x03\x04')  # 基本的zip文件头
                except Exception as content_error:
                    # 如果内容处理失败，使用基本内容
                    temp_file.write(content.encode('utf-8', errors='ignore') if content else b'')
                
                temp_path = temp_file.name
            
            try:
                # 使用改进的占位符提取器
                from app.services.domain.reporting.document_pipeline import TemplateParser
                enhanced_parser = TemplateParser()
                
                # 直接从十六进制内容提取占位符
                extracted_placeholders = enhanced_parser.extract_placeholders(content)
                
                # 转换为API响应格式
                for p in extracted_placeholders:
                    # 根据类型进行分类
                    placeholder_type = p.get("type", "text")
                    
                    # 映射类型到中文
                    type_mapping = {
                        "statistic": "统计",
                        "chart": "图表", 
                        "table": "表格",
                        "analysis": "分析",
                        "datetime": "日期时间",
                        "title": "标题",
                        "summary": "摘要",
                        "author": "作者",
                        "variable": "变量",
                        "chinese": "中文",
                        "text": "文本"
                    }
                    
                    display_type = type_mapping.get(placeholder_type, placeholder_type)
                    
                    placeholders.append({
                        "type": display_type,
                        "description": p.get("description", ""),
                        "placeholder_text": f"{{{{{p.get('name', '')}}}}}",
                        "requirements": {
                            "content_type": p.get("content_type", "text"),
                            "original_type": placeholder_type,
                            "required": p.get("required", True)
                        }
                    })
                
                logger.info(f"从DOCX模板提取到 {len(placeholders)} 个占位符")
            except Exception as parser_error:
                logger.error(f"DOCX占位符提取失败: {parser_error}")
                # 最后的fallback：返回提示信息
                placeholders.append({
                    "type": "错误",
                    "description": f"无法解析DOCX文档: {template.original_filename}。请检查文档格式或联系技术支持。",
                    "placeholder_text": "{{错误:解析失败}}",
                    "requirements": {
                        "error": str(parser_error),
                        "template_type": "docx"
                    }
                })
            finally:
                # 安全删除临时文件
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
                
        except Exception as e:
            logger.error(f"DOCX模板处理完全失败: {e}")
            # 完全降级：使用新解析器的文本模式
            try:
                from app.services.domain.reporting.document_pipeline import TemplateParser
                fallback_parser = TemplateParser()
                # 尝试直接从content中提取（可能是文本格式）
                fallback_placeholders = fallback_parser.extract_placeholders(content or "")
                
                for p in fallback_placeholders:
                    placeholders.append({
                        "type": p.get("type", "文本"),
                        "description": p.get("description", ""),
                        "placeholder_text": f"{{{{{p.get('name', '')}}}}}",
                        "requirements": {"fallback_mode": True}
                    })
            except Exception as fallback_error:
                logger.error(f"Fallback解析也失败: {fallback_error}")
                placeholders.append({
                    "type": "系统错误",
                    "description": f"系统无法解析模板文件，请联系技术支持。错误：{str(e)}",
                    "placeholder_text": "{{系统错误:无法解析}}"
                })
    else:
        # 使用新的解析器处理其他格式
        try:
            from app.services.domain.reporting.document_pipeline import TemplateParser
            text_parser = TemplateParser()
            extracted_placeholders = text_parser.extract_placeholders(content or "")
            
            for p in extracted_placeholders:
                placeholder_type = p.get("type", "text")
                
                # 映射类型到中文
                type_mapping = {
                    "statistic": "统计",
                    "chart": "图表", 
                    "table": "表格",
                    "analysis": "分析",
                    "datetime": "日期时间",
                    "title": "标题",
                    "summary": "摘要",
                    "author": "作者",
                    "variable": "变量",
                    "chinese": "中文",
                    "text": "文本"
                }
                
                display_type = type_mapping.get(placeholder_type, placeholder_type)
                
                placeholders.append({
                    "type": display_type,
                    "description": p.get("description", ""),
                    "placeholder_text": f"{{{{{p.get('name', '')}}}}}",
                    "requirements": {
                        "content_type": p.get("content_type", "text"),
                        "original_type": placeholder_type,
                        "required": p.get("required", True)
                    }
                })
        except Exception as text_parse_error:
            logger.error(f"文本模板解析失败: {text_parse_error}")
            # 基本的fallback
            placeholder_pattern = re.compile(r"\{\{([^:]+):([^}]+)\}\}")
            for match in placeholder_pattern.finditer(content or ""):
                placeholders.append({
                    "type": match.group(1).strip(),
                    "description": match.group(2).strip(), 
                    "placeholder_text": match.group(0)
                })
        
        # 新解析器已经包含所有格式支持，无需额外兼容处理
    
    # 计算各类型统计
    type_counts = {}
    content_type_stats = {}
    error_count = 0
    
    for p in placeholders:
        ptype = p.get("type", "未知")
        type_counts[ptype] = type_counts.get(ptype, 0) + 1
        
        if ptype in ["错误", "系统错误"]:
            error_count += 1
        
        # 统计内容类型
        content_type = p.get("requirements", {}).get("content_type", "unknown")
        content_type_stats[content_type] = content_type_stats.get(content_type, 0) + 1
    
    return ApiResponse(
        success=True,
        data={
            "template_type": template.template_type,
            "placeholders": placeholders,
            "total_count": len(placeholders),
            "stats_count": type_counts.get("统计", 0),
            "chart_count": type_counts.get("图表", 0),
            "table_count": type_counts.get("表格", 0),
            "analysis_count": type_counts.get("分析", 0),
            "datetime_count": type_counts.get("日期时间", 0),
            "title_count": type_counts.get("标题", 0),
            "variable_count": type_counts.get("变量", 0),
            "content_type_stats": content_type_stats,
            "has_errors": error_count > 0,
            "error_count": error_count,
            "type_distribution": type_counts
        },
        message="模板预览成功"
    )


# 混合占位符管理端点
@router.post("/{template_id}/placeholders/reparse", response_model=ApiResponse)
async def reparse_template_placeholders(
    template_id: str,
    force_reparse: bool = Query(False, description="是否强制重新解析"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重新解析模板占位符并存储到数据库"""
    # 验证模板权限
    template = crud_template.get(db, id=template_id)
    if not template or not template.is_active or (template.user_id != current_user.id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    try:
        # 使用混合占位符管理器
        from app.services.domain.placeholder.hybrid_placeholder_manager import create_hybrid_placeholder_manager
        manager = create_hybrid_placeholder_manager(db)
        
        # 解析并存储占位符
        result = manager.parse_and_store_placeholders(
            template_id=template_id,
            template_content=template.content or "",
            force_reparse=force_reparse
        )
        
        if result["success"]:
            return ApiResponse(
                success=True,
                data=result,
                message=result.get("message", "占位符解析完成")
            )
        else:
            return ApiResponse(
                success=False,
                message=result.get("error", "占位符解析失败"),
                data=result
            )
            
    except Exception as e:
        logger.error(f"重新解析占位符失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新解析占位符失败: {str(e)}"
        )


@router.get("/{template_id}/placeholders", response_model=ApiResponse)
async def get_template_placeholders(
    template_id: str,
    include_inactive: bool = Query(False, description="是否包含未激活的占位符"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模板的占位符配置列表"""
    # 验证模板权限
    template = crud_template.get(db, id=template_id)
    if not template or not template.is_active or (template.user_id != current_user.id and not template.is_public):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    try:
        from app.services.domain.placeholder.hybrid_placeholder_manager import create_hybrid_placeholder_manager
        manager = create_hybrid_placeholder_manager(db)
        
        # 获取占位符列表
        placeholders = manager.get_template_placeholders(
            template_id=template_id,
            include_inactive=include_inactive
        )
        
        # 计算统计信息
        total_count = len(placeholders)
        analyzed_count = sum(1 for p in placeholders if p.get("agent_analyzed", False))
        validated_count = sum(1 for p in placeholders if p.get("sql_validated", False))
        avg_confidence = (sum(p.get("confidence_score", 0) for p in placeholders) / total_count) if total_count > 0 else 0
        
        analytics = {
            "total_placeholders": total_count,
            "analyzed_placeholders": analyzed_count, 
            "sql_validated_placeholders": validated_count,
            "average_confidence_score": avg_confidence,
            "analysis_coverage": (analyzed_count / total_count * 100) if total_count > 0 else 0,
            "cache_hit_rate": 0  # TODO: 从缓存统计获取
        }
        
        return ApiResponse(
            success=True,
            data={
                "placeholders": placeholders,
                "analytics": analytics
            },
            message="获取占位符列表成功"
        )
        
    except Exception as e:
        logger.error(f"获取占位符列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取占位符列表失败: {str(e)}"
        )


@router.put("/{template_id}/placeholders/{placeholder_id}", response_model=ApiResponse)
async def update_placeholder(
    template_id: str,
    placeholder_id: str,
    placeholder_update: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新占位符配置"""
    # 验证模板权限
    template = crud_template.get(db, id=template_id)
    if not template or not template.is_active or template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在或无权限访问"
        )
    
    try:
        from app.crud.crud_template_placeholder import template_placeholder as crud_placeholder
        from app.schemas.template_placeholder import TemplatePlaceholderUpdate
        
        # 验证占位符存在
        placeholder = crud_placeholder.get(db, id=placeholder_id)
        if not placeholder or placeholder.template_id != template_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="占位符不存在"
            )
        
        # 创建更新schema
        update_data = TemplatePlaceholderUpdate(**placeholder_update)
        
        # 执行更新
        updated_placeholder = crud_placeholder.update(
            db, db_obj=placeholder, obj_in=update_data
        )
        
        return ApiResponse(
            success=True,
            data=crud_placeholder._serialize_placeholder(updated_placeholder) if hasattr(crud_placeholder, '_serialize_placeholder') else updated_placeholder.__dict__,
            message="占位符更新成功"
        )
        
    except Exception as e:
        logger.error(f"更新占位符失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新占位符失败: {str(e)}"
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
    if not template or not template.is_active or (template.user_id != current_user.id and not template.is_public):
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
            try:
                # 处理二进制内容（hex编码）
                if content and all(c in '0123456789ABCDEFabcdef' for c in content.replace(' ', '').replace('\n', '')):
                    # 是hex编码的二进制内容
                    binary_data = bytes.fromhex(content.replace(' ', '').replace('\n', ''))
                    temp_input.write(binary_data)
                elif content.startswith('PK'):
                    # 直接的二进制内容（docx文件头）
                    temp_input.write(content.encode('latin-1'))
                elif content:
                    # 文本内容，直接写入
                    temp_input.write(content.encode('utf-8'))
                else:
                    # 空内容，创建基本的docx结构
                    temp_input.write(b'PK\x03\x04')  # 基本的zip文件头
            except Exception as content_error:
                # 如果内容处理失败，使用基本内容
                temp_input.write(content.encode('utf-8', errors='ignore') if content else b'')
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
    if not template or not template.is_active or (template.user_id != current_user.id and not template.is_public):
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
                try:
                    # 处理二进制内容（hex编码）
                    if content and all(c in '0123456789ABCDEFabcdef' for c in content.replace(' ', '').replace('\n', '')):
                        # 是hex编码的二进制内容
                        binary_data = bytes.fromhex(content.replace(' ', '').replace('\n', ''))
                        temp_file.write(binary_data)
                    elif content.startswith('PK'):
                        # 直接的二进制内容（docx文件头）
                        temp_file.write(content.encode('latin-1'))
                    elif content:
                        # 文本内容，直接写入
                        temp_file.write(content.encode('utf-8'))
                    else:
                        # 空内容，创建基本的docx结构
                        temp_file.write(b'PK\x03\x04')  # 基本的zip文件头
                except Exception as content_error:
                    # 如果内容处理失败，使用基本内容
                    temp_file.write(content.encode('utf-8', errors='ignore') if content else b'')
                
                temp_path = temp_file.name
            
            try:
                placeholder_data = template_parser.parse_doc_placeholders(temp_path)
                placeholders = (
                    placeholder_data.get("stats_placeholders", []) + 
                    placeholder_data.get("chart_placeholders", [])
                )
            except Exception as parser_error:
                # 如果DOC解析器失败，尝试从原始内容中提取占位符
                placeholders = []
                try:
                    # 如果是hex编码的内容，先解码
                    text_content = content
                    if content and all(c in '0123456789ABCDEFabcdef' for c in content.replace(' ', '').replace('\n', '')):
                        try:
                            binary_data = bytes.fromhex(content.replace(' ', '').replace('\n', ''))
                            text_content = binary_data.decode('utf-8', errors='ignore')
                        except:
                            text_content = content
                    
                    # 使用正则表达式提取占位符
                    import re
                    placeholder_pattern = re.compile(r"\{\{([^:]+):([^}]+)\}\}")
                    for match in placeholder_pattern.finditer(text_content):
                        placeholders.append({
                            "placeholder_type": match.group(1).strip(),
                            "description": match.group(2).strip(),
                            "placeholder_text": match.group(0)
                        })
                except:
                    # 最后的fallback：返回默认占位符信息
                    placeholders = [{
                        "placeholder_type": "文档",
                        "description": f"DOCX模板文件: {template.original_filename}",
                        "placeholder_text": "{{文档:DOCX内容}}"
                    }]
            finally:
                # 安全删除临时文件
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
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


# =====================================================================
# 以下是从 template_optimization.py 和 intelligent_placeholders.py 
# 合并过来的优化功能，替代重复的API端点
# =====================================================================

@router.post("/{template_id}/analyze-placeholders", response_model=ApiResponse)
async def analyze_template_placeholders(
    template_id: str,
    force_reparse: bool = Query(False, description="是否强制重新解析占位符"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """分析模板占位符并存储配置（从template_optimization.py迁移）"""
    try:
        # 验证模板权限
        template = crud_template.get(db, id=template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if template.user_id != user_id and not template.is_public:
            raise HTTPException(status_code=403, detail="无权限访问此模板")
        
        # 使用增强模板解析器
        from app.services.domain.template.enhanced_template_parser import EnhancedTemplateParser
        parser = EnhancedTemplateParser(db)
        
        # 解析并存储占位符
        parse_result = await parser.parse_and_store_template_placeholders(
            template_id, template.content, force_reparse
        )
        
        if not parse_result["success"]:
            raise HTTPException(status_code=400, detail=parse_result["error"])
        
        return ApiResponse(
            success=True,
            data=parse_result,
            message="占位符分析完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析占位符失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/{template_id}/placeholders", response_model=ApiResponse)
async def get_template_placeholders(
    template_id: str,
    include_inactive: bool = Query(False, description="是否包含非活跃占位符"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模板占位符配置（合并功能）"""
    try:
        # 验证模板权限
        template = crud_template.get(db, id=template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if template.user_id != user_id and not template.is_public:
            raise HTTPException(status_code=403, detail="无权限访问此模板")
        
        # 获取占位符配置
        from app.services.domain.placeholder import create_placeholder_config_service
        placeholder_service = create_placeholder_config_service(db)
        
        placeholders = await placeholder_service.get_placeholder_configs(
            template_id, include_inactive
        )
        
        return ApiResponse(
            success=True,
            data={
                "template_id": template_id,
                "total_placeholders": len(placeholders),
                "active_placeholders": len([p for p in placeholders if p.get("is_active", True)]),
                "placeholders": placeholders
            },
            message="获取占位符配置成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取占位符配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.post("/{template_id}/analyze-with-agent", response_model=ApiResponse)
async def analyze_with_agent(
    template_id: str,
    data_source_id: str = Query(..., description="数据源ID"),
    force_reanalyze: bool = Query(False, description="是否强制重新分析"),
    optimization_level: str = Query("enhanced", description="优化级别：basic/enhanced/intelligent/learning"),
    target_expectations: Optional[str] = Query(None, description="期望结果描述（JSON格式）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """使用智能Agent分析占位符（基于统一上下文系统）"""
    import json
    try:
        # 验证权限
        template = crud_template.get(db, id=template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        from app.crud.crud_data_source import crud_data_source
        data_source = crud_data_source.get(db, id=data_source_id)
        if not data_source:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if template.user_id != user_id and not template.is_public:
            raise HTTPException(status_code=403, detail="无权限访问此模板")
        
        # 解析目标期望
        expectations_dict = None
        if target_expectations:
            try:
                expectations_dict = json.loads(target_expectations)
            except json.JSONDecodeError:
                logger.warning(f"无法解析目标期望: {target_expectations}")
        
        # 使用统一API适配器
        from app.services.iaop.integration.unified_api_adapter import get_unified_api_adapter
        adapter = get_unified_api_adapter(db_session=db, integration_mode=optimization_level)
        
        # 执行增强的Agent分析
        analysis_result = await adapter.analyze_with_agent_enhanced(
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=str(user_id),
            force_reanalyze=force_reanalyze,
            optimization_level=optimization_level,
            target_expectations=expectations_dict
        )
        
        return ApiResponse(
            success=analysis_result.get('success', False),
            data=analysis_result.get('data'),
            message="智能Agent分析完成" if analysis_result.get('success') else f"分析失败: {analysis_result.get('error', '未知错误')}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"智能Agent分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/{template_id}/readiness", response_model=ApiResponse)
async def check_template_readiness(
    template_id: str,
    data_source_id: Optional[str] = Query(None, description="数据源ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查模板就绪状态（合并功能）"""
    try:
        # 验证模板权限
        template = crud_template.get(db, id=template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if template.user_id != user_id and not template.is_public:
            raise HTTPException(status_code=403, detail="无权限访问此模板")
        
        # 使用增强模板解析器检查就绪状态
        from app.services.domain.template.enhanced_template_parser import EnhancedTemplateParser
        parser = EnhancedTemplateParser(db)
        
        readiness_info = await parser.check_template_ready_for_execution(template_id)
        
        return ApiResponse(
            success=True,
            data=readiness_info,
            message="模板就绪状态检查完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查模板就绪状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}")


@router.post("/{template_id}/invalidate-cache", response_model=ApiResponse)
async def invalidate_template_cache(
    template_id: str,
    cache_level: Optional[str] = Query(None, description="缓存级别: template, placeholder, agent_analysis, data_extraction"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """清除模板缓存（从template_optimization.py迁移）"""
    try:
        # 验证模板权限
        template = crud_template.get(db, id=template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if template.user_id != user_id and not template.is_public:
            raise HTTPException(status_code=403, detail="无权限访问此模板")
        
        # 使用统一缓存服务清除缓存
        from app.services.domain.placeholder.unified_cache_service import UnifiedCacheService
        cache_service = UnifiedCacheService(db)
        
        cleared_count = await cache_service.invalidate_by_template(template_id)
        
        return ApiResponse(
            success=True,
            data={"cleared_cache_entries": cleared_count},
            message=f"缓存清除完成，共清除 {cleared_count} 个缓存条目"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"清除失败: {str(e)}")


@router.get("/{template_id}/cache-statistics", response_model=ApiResponse)
async def get_template_cache_statistics(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模板缓存统计（从template_optimization.py迁移）"""
    try:
        # 验证模板权限
        template = crud_template.get(db, id=template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if template.user_id != user_id and not template.is_public:
            raise HTTPException(status_code=403, detail="无权限访问此模板")
        
        # 获取缓存统计
        from app.services.domain.placeholder.unified_cache_service import UnifiedCacheService
        cache_service = UnifiedCacheService(db)
        
        cache_stats = await cache_service.get_cache_statistics()
        
        return ApiResponse(
            success=True,
            data=cache_stats,
            message="缓存统计获取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


# =====================================================================
# 占位符ETL脚本管理端点 - 支持前端ETLScriptManager组件
# =====================================================================

@router.put("/{template_id}/placeholders/{placeholder_id}", response_model=ApiResponse)
async def update_placeholder_config(
    template_id: str,
    placeholder_id: str,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新占位符配置"""
    try:
        # 验证模板权限
        template = crud_template.get(db, id=template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if template.user_id != user_id and not template.is_public:
            raise HTTPException(status_code=403, detail="无权限访问此模板")
        
        # 更新占位符配置
        from app.services.domain.placeholder import create_placeholder_config_service
        placeholder_service = create_placeholder_config_service(db)
        
        updated_placeholder = await placeholder_service.update_placeholder_config(
            placeholder_id, updates
        )
        
        return ApiResponse(
            success=True,
            data=updated_placeholder,
            message="占位符配置更新成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新占位符配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.post("/placeholders/{placeholder_id}/test-query", response_model=ApiResponse)
async def test_placeholder_query(
    placeholder_id: str,
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试占位符SQL查询"""
    try:
        data_source_id = request_data.get("data_source_id")
        sql_query = request_data.get("sql_query")
        
        if not data_source_id or not sql_query:
            raise HTTPException(status_code=400, detail="缺少必要参数：data_source_id 和 sql_query")
        
        # 验证数据源权限
        from app.crud.crud_data_source import crud_data_source
        data_source = crud_data_source.get(db, id=data_source_id)
        if not data_source:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if data_source.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权限访问此数据源")
        
        # 执行测试查询
        from app.services.data.connectors.connector_factory import create_connector
        from datetime import datetime
        
        start_time = datetime.now()
        
        try:
            connector = create_connector(data_source)
            result = await connector.execute_query(sql_query)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 构造测试结果
            test_result = {
                "id": f"test_{placeholder_id}_{int(datetime.now().timestamp())}",
                "placeholder_id": placeholder_id,
                "data_source_id": data_source_id,
                "raw_query_result": result,
                "processed_value": result,
                "formatted_text": str(result) if result else "",
                "execution_sql": sql_query,
                "execution_time_ms": int(execution_time),
                "row_count": len(result) if isinstance(result, list) else 1 if result else 0,
                "success": True,
                "error_message": None,
                "cache_key": f"test_{placeholder_id}",
                "expires_at": datetime.now().isoformat(),
                "hit_count": 1,
                "last_hit_at": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            return ApiResponse(
                success=True,
                data=test_result,
                message="SQL查询测试成功"
            )
            
        except Exception as query_error:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 构造失败结果
            test_result = {
                "id": f"test_{placeholder_id}_{int(datetime.now().timestamp())}",
                "placeholder_id": placeholder_id,
                "data_source_id": data_source_id,
                "raw_query_result": None,
                "processed_value": None,
                "formatted_text": "",
                "execution_sql": sql_query,
                "execution_time_ms": int(execution_time),
                "row_count": 0,
                "success": False,
                "error_message": str(query_error),
                "cache_key": f"test_{placeholder_id}",
                "expires_at": datetime.now().isoformat(),
                "hit_count": 1,
                "last_hit_at": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            return ApiResponse(
                success=False,
                data=test_result,
                message=f"SQL查询测试失败: {str(query_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试SQL查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.post("/placeholders/{placeholder_id}/validate-sql", response_model=ApiResponse)
async def validate_placeholder_sql(
    placeholder_id: str,
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """验证占位符SQL查询"""
    try:
        data_source_id = request_data.get("data_source_id")
        
        if not data_source_id:
            raise HTTPException(status_code=400, detail="缺少必要参数：data_source_id")
        
        # 验证数据源权限
        from app.crud.crud_data_source import crud_data_source
        data_source = crud_data_source.get(db, id=data_source_id)
        if not data_source:
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if data_source.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权限访问此数据源")
        
        # 获取占位符配置
        from app.services.domain.placeholder import create_placeholder_config_service
        placeholder_service = create_placeholder_config_service(db)
        
        placeholder_config = await placeholder_service.get_placeholder_config(placeholder_id)
        if not placeholder_config:
            raise HTTPException(status_code=404, detail="占位符不存在")
        
        generated_sql = placeholder_config.get("generated_sql")
        if not generated_sql:
            raise HTTPException(status_code=400, detail="占位符没有生成的SQL查询")
        
        # 验证SQL语法
        try:
            from app.services.data.connectors.connector_factory import create_connector
            connector = create_connector(data_source)
            
            # 执行SQL验证（使用EXPLAIN或类似的方法，不实际执行查询）
            validation_result = await connector.validate_query(generated_sql)
            
            # 更新占位符的验证状态
            updates = {
                "sql_validated": validation_result.get("valid", False),
                "confidence_score": validation_result.get("confidence", 0.8)
            }
            
            await placeholder_service.update_placeholder_config(placeholder_id, updates)
            
            return ApiResponse(
                success=True,
                data={
                    "placeholder_id": placeholder_id,
                    "sql_valid": validation_result.get("valid", False),
                    "validation_message": validation_result.get("message", ""),
                    "confidence_score": validation_result.get("confidence", 0.8)
                },
                message="SQL验证完成"
            )
            
        except Exception as validation_error:
            # 更新占位符的验证状态为失败
            updates = {
                "sql_validated": False,
                "confidence_score": 0.3
            }
            
            await placeholder_service.update_placeholder_config(placeholder_id, updates)
            
            return ApiResponse(
                success=False,
                data={
                    "placeholder_id": placeholder_id,
                    "sql_valid": False,
                    "validation_message": str(validation_error),
                    "confidence_score": 0.3
                },
                message=f"SQL验证失败: {str(validation_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证SQL失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


@router.get("/placeholders/{placeholder_id}/execution-history", response_model=ApiResponse)
async def get_placeholder_execution_history(
    placeholder_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取占位符执行历史"""
    try:
        # 获取占位符配置以验证权限
        from app.services.domain.placeholder import create_placeholder_config_service
        placeholder_service = create_placeholder_config_service(db)
        
        placeholder_config = await placeholder_service.get_placeholder_config(placeholder_id)
        if not placeholder_config:
            raise HTTPException(status_code=404, detail="占位符不存在")
        
        # 验证模板权限
        template_id = placeholder_config.get("template_id")
        template = crud_template.get(db, id=template_id)
        if not template:
            raise HTTPException(status_code=404, detail="关联模板不存在")
        
        user_id = current_user.id
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        if template.user_id != user_id and not template.is_public:
            raise HTTPException(status_code=403, detail="无权限访问此占位符")
        
        # 获取执行历史（这里模拟数据，实际应该从缓存或日志表中获取）
        from datetime import datetime, timedelta
        import random
        
        execution_history = []
        for i in range(min(limit, 5)):  # 限制返回数量
            history_entry = {
                "id": f"history_{placeholder_id}_{i}",
                "placeholder_id": placeholder_id,
                "data_source_id": "mock_data_source",
                "raw_query_result": None,
                "processed_value": None,
                "formatted_text": f"Mock result {i+1}",
                "execution_sql": placeholder_config.get("generated_sql", "SELECT 1"),
                "execution_time_ms": random.randint(50, 500),
                "row_count": random.randint(1, 100),
                "success": random.choice([True, True, True, False]),  # 75% 成功率
                "error_message": None if random.choice([True, True, True, False]) else "Mock error message",
                "cache_key": f"cache_{placeholder_id}_{i}",
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
                "hit_count": random.randint(1, 10),
                "last_hit_at": (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat(),
                "created_at": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat()
            }
            execution_history.append(history_entry)
        
        return ApiResponse(
            success=True,
            data=execution_history,
            message="获取执行历史成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")
