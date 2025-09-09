"""模板管理API端点 - 基于React Agent系统"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.architecture import ApiResponse, PaginatedResponse
from app.core.permissions import require_permission, ResourceType, PermissionLevel
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.template import Template as TemplateModel
from app.schemas.template import TemplateCreate, TemplateUpdate, Template as TemplateSchema, TemplatePreview
from app.crud import template as crud_template
from app.services.domain.template.services.template_domain_service import TemplateParser
from app.services.infrastructure.ai.service_orchestrator import get_service_orchestrator
import re
import logging
import json
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# 创建全局实例
template_parser = TemplateParser()

router = APIRouter()


# 旧的get_unified_api_adapter函数已被移除，使用新的Claude Code架构
@router.get("", response_model=PaginatedResponse[TemplateSchema])
async def list_templates(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模板列表"""
    try:
        logger.info(f"获取用户 {current_user.id} 的模板列表，搜索: {search}")
        
        # 获取模板列表
        templates, total = crud_template.get_templates_with_pagination(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            search=search
        )
        
        # 转换为schema对象
        template_schemas = [TemplateSchema.model_validate(template) for template in templates]
        
        return PaginatedResponse(
            items=template_schemas,
            total=total,
            page=skip // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit,
            has_next=skip + limit < total,
            has_prev=skip > 0
        )
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模板列表失败"
        )


@router.get("/{template_id}", response_model=ApiResponse[TemplateSchema])
async def get_template(
    request: Request,
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取特定模板"""
    try:
        template = crud_template.get_by_id_and_user(
            db=db, 
            id=template_id, 
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        return ApiResponse(
            success=True,
            data=template,
            message="获取模板成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模板失败"
        )


@router.post("", response_model=ApiResponse[TemplateSchema])
async def create_template(
    request: Request,
    template_in: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新模板"""
    try:
        # 创建模板
        template = crud_template.create_with_owner(
            db=db,
            obj_in=template_in,
            owner_id=current_user.id
        )
        
        logger.info(f"用户 {current_user.id} 创建了模板 {template.id}")
        
        return ApiResponse(
            success=True,
            data=template,
            message="模板创建成功"
        )
    except Exception as e:
        logger.error(f"创建模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建模板失败"
        )


@router.put("/{template_id}", response_model=ApiResponse[TemplateSchema])
async def update_template(
    request: Request,
    template_id: str,
    template_in: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新模板"""
    try:
        template = crud_template.get_by_id_and_user(
            db=db, 
            id=template_id, 
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        # 更新模板
        template = crud_template.update(
            db=db,
            db_obj=template,
            obj_in=template_in
        )
        
        logger.info(f"用户 {current_user.id} 更新了模板 {template_id}")
        
        return ApiResponse(
            success=True,
            data=template,
            message="模板更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新模板失败"
        )


@router.delete("/{template_id}", response_model=ApiResponse[Dict])
async def delete_template(
    request: Request,
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除模板"""
    try:
        template = crud_template.get_by_id_and_user(
            db=db, 
            id=template_id, 
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        # 删除模板
        crud_template.remove(db=db, id=template_id)
        
        logger.info(f"用户 {current_user.id} 删除了模板 {template_id}")
        
        return ApiResponse(
            success=True,
            data={"deleted_id": template_id},
            message="模板删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模板失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除模板失败"
        )


@router.post("/{template_id}/analyze", response_model=ApiResponse[Dict])
async def analyze_template_placeholders(
    template_id: str,
    data_source_id: str = Query(..., description="数据源ID"),
    force_reanalyze: bool = Query(False, description="强制重新分析"),
    optimization_level: str = Query("enhanced", description="优化级别"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析模板占位符 - 使用新的Claude Code架构"""
    try:
        # 验证模板存在性
        template = crud_template.get_by_id_and_user(
            db=db,
            id=template_id,
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        # 获取数据源信息
        from app.crud import data_source as crud_data_source
        data_source_info = None
        if data_source_id:
            data_source = crud_data_source.get(db, id=data_source_id)
            if data_source:
                data_source_info = {
                    "type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                    "database": getattr(data_source, 'doris_database', 'unknown'),
                    "name": data_source.name
                }
        
        # 使用新的服务编排器 - Claude Code架构
        orchestrator = get_service_orchestrator()
        
        result = await orchestrator.analyze_template_simple(
            user_id=str(current_user.id),
            template_id=template_id,
            template_content=template.content,
            data_source_info=data_source_info
        )
        
        logger.info(f"用户 {current_user.id} 使用Claude Code架构分析了模板 {template_id}")
        
        return ApiResponse(
            success=True,
            data=result,
            message="模板分析完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Claude Code架构模板分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析失败: {str(e)}"
        )


@router.get("/{template_id}/analyze/stream")
async def analyze_template_streaming(
    template_id: str,
    data_source_id: str = Query(..., description="数据源ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式分析模板 - 实时进度反馈"""
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate():
        try:
            # 验证模板存在性
            template = crud_template.get_by_id_and_user(
                db=db,
                id=template_id,
                user_id=current_user.id
            )
            
            if not template:
                yield f"data: {json.dumps({'type': 'error', 'error': {'error_message': '模板不存在', 'error_type': 'not_found'}})}\n\n"
                return
            
            # 获取数据源信息
            from app.crud import data_source as crud_data_source
            data_source_info = None
            if data_source_id:
                data_source = crud_data_source.get(db, id=data_source_id)
                if data_source:
                    data_source_info = {
                        "type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                        "database": getattr(data_source, 'doris_database', 'unknown'),
                        "name": data_source.name
                    }
            
            # 使用新的服务编排器进行流式分析
            orchestrator = get_service_orchestrator()
            
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'template_id': template_id, 'user_id': str(current_user.id)})}\n\n"
            
            async for message in orchestrator.analyze_template_streaming(
                user_id=str(current_user.id),
                template_id=template_id,
                template_content=template.content,
                data_source_info=data_source_info
            ):
                yield f"data: {json.dumps(message)}\n\n"
            
            # 发送完成事件
            yield f"data: {json.dumps({'type': 'complete', 'message': '分析完成'})}\n\n"
                
        except Exception as e:
            logger.error(f"流式分析失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': {'error_message': str(e), 'error_type': 'streaming_error'}})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache", 
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.get("/{template_id}/preview", response_model=ApiResponse[TemplatePreview])
async def preview_template(
    request: Request,
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """预览模板内容和占位符"""
    try:
        # 验证模板存在性
        template = crud_template.get_by_id_and_user(
            db=db,
            id=template_id,
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        # 解析模板结构
        structure = template_parser.parse_template_structure(template.content or "")
        
        # 构建预览数据
        preview_data = TemplatePreview(
            template_id=template.id,
            content=template.content,
            html_content=template.content,  # 可以在这里添加HTML转换逻辑
            placeholders=structure.get('placeholders', []),
            metadata={
                'name': template.name,
                'description': template.description,
                'template_type': template.template_type,
                'original_filename': template.original_filename,
                'file_size': template.file_size,
                'complexity_score': structure.get('complexity_score', 0),
                'sections': structure.get('sections', []),
                'variables': structure.get('variables', {})
            }
        )
        
        logger.info(f"用户 {current_user.id} 预览了模板 {template_id}")
        
        return ApiResponse(
            success=True,
            data=preview_data,
            message="模板预览获取成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模板预览失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="模板预览失败"
        )


@router.post("/{template_id}/upload", response_model=ApiResponse[TemplateSchema])
async def upload_template_file(
    request: Request,
    template_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传模板文件并更新内容"""
    try:
        # 验证模板存在性
        template = crud_template.get_by_id_and_user(
            db=db,
            id=template_id,
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        # 验证文件类型
        allowed_extensions = {'.docx', '.doc', '.txt', '.html', '.md'}
        file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型。支持的类型: {', '.join(allowed_extensions)}"
            )
        
        # 读取文件内容
        content = await file.read()
        file_size = len(content)
        
        # 1. 先保存原始文件到存储系统
        file_info = None
        content_text = ""
        
        try:
            from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
            from io import BytesIO
            
            storage_service = get_hybrid_storage_service()
            
            # 保存原始文件
            file_info = storage_service.upload_file(
                file_data=BytesIO(content),
                original_filename=file.filename,
                file_type="templates",
                content_type=file.content_type
            )
            
            logger.info(f"文件保存到存储系统: {file_info.get('file_path')}")
            
        except Exception as e:
            logger.error(f"保存文件到存储系统失败: {str(e)}")
            # 如果存储失败，仍然继续处理，但记录错误
        
        # 2. 解析文件内容用于占位符分析
        if file_extension in ['.docx', '.doc']:
            try:
                from docx import Document
                import io
                
                # 解析docx文档
                doc = Document(io.BytesIO(content))
                
                # 提取文本内容
                full_text = []
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        full_text.append(paragraph.text)
                
                # 提取表格内容
                for table in doc.tables:
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            if cell.text.strip():
                                row_text.append(cell.text.strip())
                        if row_text:
                            full_text.append(" | ".join(row_text))
                
                content_text = "\n\n".join(full_text) if full_text else f"[空文档: {file.filename}]"
                
            except Exception as e:
                logger.error(f"解析docx文件失败: {str(e)}")
                content_text = f"[文档解析失败: {file.filename}]\n错误信息: {str(e)}"
        else:
            content_text = content.decode('utf-8', errors='ignore')
        
        # 3. 更新模板记录
        template_update = TemplateUpdate(
            content=content_text,
            original_filename=file.filename,
            file_path=file_info.get("file_path") if file_info else None,
            file_size=file_size,
            template_type=file_extension.lstrip('.')
        )
        
        updated_template = crud_template.update(
            db=db,
            db_obj=template,
            obj_in=template_update
        )
        
        logger.info(f"用户 {current_user.id} 上传了模板文件 {file.filename} 到模板 {template_id}")
        
        # 自动触发占位符分析
        try:
            structure = template_parser.parse_template_structure(content_text)
            logger.info(f"自动解析了模板 {template_id} 的占位符: {len(structure.get('placeholders', []))} 个")
        except Exception as parse_error:
            logger.warning(f"自动占位符解析失败: {parse_error}")
        
        return ApiResponse(
            success=True,
            data=updated_template,
            message=f"模板文件上传成功，解析到 {len(structure.get('placeholders', []))} 个占位符" if 'structure' in locals() else "模板文件上传成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模板文件上传失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="模板文件上传失败"
        )


@router.get("/{template_id}/download")
async def download_template_file(
    request: Request,
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载模板原始文件"""
    try:
        # 验证模板存在性
        template = crud_template.get_by_id_and_user(
            db=db,
            id=template_id,
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        # 检查是否有文件路径
        if not template.file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板没有关联的文件"
            )
        
        # 从存储系统下载文件
        try:
            from app.services.infrastructure.storage.hybrid_storage_service import get_hybrid_storage_service
            from fastapi.responses import StreamingResponse
            import io
            
            storage_service = get_hybrid_storage_service()
            
            # 检查文件是否存在
            if not storage_service.file_exists(template.file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="文件在存储系统中不存在"
                )
            
            # 下载文件
            file_data, backend_type = storage_service.download_file(template.file_path)
            
            # 确定Content-Type
            content_type = "application/octet-stream"
            if template.original_filename:
                if template.original_filename.endswith(".docx"):
                    content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif template.original_filename.endswith(".doc"):
                    content_type = "application/msword"
                elif template.original_filename.endswith(".pdf"):
                    content_type = "application/pdf"
                elif template.original_filename.endswith(".txt"):
                    content_type = "text/plain"
                elif template.original_filename.endswith(".html"):
                    content_type = "text/html"
            
            # 创建响应
            file_stream = io.BytesIO(file_data)
            
            logger.info(f"用户 {current_user.id} 下载模板文件: {template.name} ({template.original_filename})")
            
            return StreamingResponse(
                file_stream,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{template.original_filename or f"template_{template_id}"}"',
                    "X-Storage-Backend": backend_type,
                    "X-Template-ID": template_id
                }
            )
            
        except Exception as storage_error:
            logger.error(f"从存储系统下载文件失败: {storage_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件下载失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模板文件下载失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="模板文件下载失败"
        )


@router.post("/{template_id}/placeholders/reparse", response_model=ApiResponse[Dict])
async def reparse_template_placeholders(
    request: Request,
    template_id: str,
    force_reparse: bool = Query(False, description="强制重新解析"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新解析模板占位符"""
    try:
        # 验证模板存在性
        template = crud_template.get_by_id_and_user(
            db=db,
            id=template_id,
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        # 解析模板结构
        structure = template_parser.parse_template_structure(template.content or "")
        
        logger.info(f"用户 {current_user.id} 重新解析了模板 {template_id} 的占位符: {len(structure.get('placeholders', []))} 个")
        
        return ApiResponse(
            success=True,
            data={
                "template_id": template_id,
                "placeholders": structure.get('placeholders', []),
                "sections": structure.get('sections', []),
                "variables": structure.get('variables', {}),
                "complexity_score": structure.get('complexity_score', 0),
                "force_reparse": force_reparse
            },
            message=f"占位符重新解析完成，共发现 {len(structure.get('placeholders', []))} 个占位符"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新解析占位符失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重新解析占位符失败"
        )


@router.post("/{template_id}/analyze-with-agent", response_model=ApiResponse[Dict])
async def analyze_with_agent(
    template_id: str,
    data_source_id: str = Query(..., description="数据源ID"),
    force_reanalyze: bool = Query(False, description="强制重新分析"),
    optimization_level: str = Query("enhanced", description="优化级别"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """使用AI Agent分析模板 - 已升级到Claude Code架构"""
    try:
        # 验证模板存在性
        template = crud_template.get_by_id_and_user(
            db=db,
            id=template_id,
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        # 获取数据源信息
        from app.crud import data_source as crud_data_source
        data_source_info = None
        if data_source_id:
            data_source = crud_data_source.get(db, id=data_source_id)
            if data_source:
                data_source_info = {
                    "type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                    "database": getattr(data_source, 'doris_database', 'unknown'),
                    "name": data_source.name
                }
        
        # 使用新的服务编排器 - Claude Code架构
        orchestrator = get_service_orchestrator()
        
        result = await orchestrator.analyze_template_simple(
            user_id=str(current_user.id),
            template_id=template_id,
            template_content=template.content,
            data_source_info=data_source_info
        )
        
        logger.info(f"用户 {current_user.id} 使用Claude Code架构分析了模板 {template_id}")
        
        return ApiResponse(
            success=True,
            data=result,
            message="Agent分析完成"
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent模板分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent分析失败"
        )


@router.post("/{template_id}/analyze-v2", response_model=ApiResponse[Dict])
async def analyze_template_with_claude_code_architecture(
    template_id: str,
    data_source_id: str = Query(..., description="数据源ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """使用新的Claude Code架构分析模板"""
    try:
        # 验证模板存在性
        template = crud_template.get_by_id_and_user(
            db=db,
            id=template_id,
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )
        
        # 获取数据源信息
        from app.crud import data_source as crud_data_source
        data_source_info = None
        if data_source_id:
            data_source = crud_data_source.get(db, id=data_source_id)
            if data_source:
                data_source_info = {
                    "type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                    "database": getattr(data_source, 'doris_database', 'unknown'),
                    "name": data_source.name
                }
        
        # 使用新的服务编排器
        orchestrator = get_service_orchestrator()
        
        result = await orchestrator.analyze_template_simple(
            user_id=str(current_user.id),
            template_id=template_id,
            template_content=template.content,
            data_source_info=data_source_info
        )
        
        logger.info(f"用户 {current_user.id} 使用新架构分析了模板 {template_id}")
        
        return ApiResponse(
            success=True,
            data=result,
            message="使用Claude Code架构分析完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"新架构模板分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"新架构分析失败: {str(e)}"
        )


@router.get("/{template_id}/analyze-v2/stream")
async def analyze_template_streaming_with_claude_code_architecture(
    template_id: str,
    data_source_id: str = Query(..., description="数据源ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式分析模板 - 使用新架构"""
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate():
        try:
            # 验证模板存在性
            template = crud_template.get_by_id_and_user(
                db=db,
                id=template_id,
                user_id=current_user.id
            )
            
            if not template:
                yield f"data: {json.dumps({'error': '模板不存在'})}\n\n"
                return
            
            # 获取数据源信息
            from app.crud import data_source as crud_data_source
            data_source_info = None
            if data_source_id:
                data_source = crud_data_source.get(db, id=data_source_id)
                if data_source:
                    data_source_info = {
                        "type": data_source.source_type.value if hasattr(data_source.source_type, 'value') else str(data_source.source_type),
                        "database": getattr(data_source, 'doris_database', 'unknown'),
                        "name": data_source.name
                    }
            
            # 使用新的服务编排器进行流式分析
            orchestrator = get_service_orchestrator()
            
            async for message in orchestrator.analyze_template_streaming(
                user_id=str(current_user.id),
                template_id=template_id,
                template_content=template.content,
                data_source_info=data_source_info
            ):
                yield f"data: {json.dumps(message)}\n\n"
                
        except Exception as e:
            logger.error(f"流式分析失败: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )