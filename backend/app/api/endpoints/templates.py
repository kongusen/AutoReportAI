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
import re
import logging
import json

logger = logging.getLogger(__name__)

# 创建全局实例
template_parser = TemplateParser()

router = APIRouter()


async def get_unified_api_adapter(request: Request, db_session: Session, integration_mode: str = "react_agent"):
    """
    获取统一API适配器 - 基于React Agent系统
    """
    try:
        from app.services.application.agents import get_workflow_orchestration_agent
        
        # 获取工作流编排代理 - 传递用户ID
        user_id = request.state.current_user.id if hasattr(request.state, 'current_user') else 'system'
        workflow_agent = await get_workflow_orchestration_agent(user_id=str(user_id))
        
        logger.info("使用React Agent系统的API适配器")
        
        class ReactAgentAPIAdapter:
            def __init__(self, workflow_agent, db: Session, mode: str):
                self.workflow_agent = workflow_agent
                self.db = db
                self.integration_mode = mode
                logger.info(f"React Agent API适配器已初始化: {mode}")
            
            async def analyze_with_agent_enhanced(
                self,
                template_id: str,
                data_source_id: str,
                user_id: str,
                force_reanalyze: bool = False,
                optimization_level: str = "enhanced",
                target_expectations: Optional[Dict] = None
            ):
                """使用React Agent系统进行模板占位符分析"""
                try:
                    logger.info(f"开始React Agent分析模板 {template_id}，数据源 {data_source_id}")
                    
                    # 构建执行上下文
                    execution_context = {
                        'user_id': user_id,
                        'template_id': template_id,
                        'data_source_id': data_source_id,
                        'force_reanalyze': force_reanalyze,
                        'optimization_level': optimization_level,
                        'target_expectations': target_expectations or {},
                        'integration_mode': self.integration_mode
                    }
                    
                    # 执行工作流编排
                    result = await self.workflow_agent.orchestrate_report_generation(
                        template_id=template_id,
                        data_source_ids=[data_source_id],
                        execution_context=execution_context
                    )
                    
                    if result.get('success'):
                        logger.info(f"React Agent模板分析完成: {template_id}")
                        return ApiResponse(
                            success=True,
                            data=result.get('results', {}),
                            message="智能Agent分析完成（React Agent系统）"
                        )
                    else:
                        logger.error(f"React Agent分析失败: {result.get('error')}")
                        return ApiResponse(
                            success=False,
                            error=result.get('error'),
                            message=f"分析失败: {result.get('error')}"
                        )
                        
                except Exception as e:
                    logger.error(f"React Agent分析异常: {e}")
                    return ApiResponse(
                        success=False,
                        error=str(e),
                        message=f"分析失败: {str(e)}"
                    )
        
        return ReactAgentAPIAdapter(workflow_agent, db_session, integration_mode)
        
    except Exception as e:
        logger.error(f"获取React Agent API适配器失败: {e}")
        logger.warning("回退到简化模式")
        
        # 使用纯数据库驱动的增强解析器
        class PureDatabaseAPIAdapterWrapper:
            def __init__(self, db: Session, mode: str):
                self.db = db
                self.integration_mode = mode
            
            async def analyze_with_agent_enhanced(
                self,
                template_id: str,
                data_source_id: str,
                user_id: str,
                force_reanalyze: bool = False,
                optimization_level: str = "enhanced",
                target_expectations: Optional[Dict] = None
            ):
                """使用纯数据库模式的模板分析"""
                try:
                    logger.info(f"使用纯数据库模式分析模板 {template_id}")
                    
                    from app.services.infrastructure.ai.agents import create_react_agent
                    
                    # 使用React Agent进行模板分析
                    agent = create_react_agent(user_id)
                    await agent.initialize()
                    
                    result = await agent.chat(f"分析模板占位符并生成SQL: template_id={template_id}, data_source_id={data_source_id}, force_reanalyze={force_reanalyze}")
                    
                    return ApiResponse(
                        success=True,
                        data=result,
                        message="模板分析完成（React Agent系统）"
                    )
                    
                except Exception as e:
                    logger.error(f"纯数据库模式分析失败: {e}")
                    return ApiResponse(
                        success=False,
                        error=str(e),
                        message=f"分析失败: {str(e)}"
                    )
        
        return PureDatabaseAPIAdapterWrapper(db_session, integration_mode)


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
    request: Request,
    template_id: str,
    data_source_id: str = Query(..., description="数据源ID"),
    force_reanalyze: bool = Query(False, description="强制重新分析"),
    optimization_level: str = Query("enhanced", description="优化级别"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析模板占位符 - 使用React Agent系统"""
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
        
        # 获取API适配器
        api_adapter = await get_unified_api_adapter(
            request=request,
            db_session=db,
            integration_mode="react_agent"
        )
        
        # 执行分析
        result = await api_adapter.analyze_with_agent_enhanced(
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=str(current_user.id),
            force_reanalyze=force_reanalyze,
            optimization_level=optimization_level
        )
        
        if result.get("success"):
            return ApiResponse(
                success=True,
                data=result.get("data", {}),
                message=result.get("message", "分析完成")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "分析失败")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模板占位符分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="模板分析失败"
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
        
        # 根据文件类型处理内容
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
        
        # 更新模板
        template_update = TemplateUpdate(
            content=content_text,
            original_filename=file.filename,
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
            message=f"模板文件上传成功，解析到 {len(structure.get('placeholders', []))} 个占位符"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模板文件上传失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="模板文件上传失败"
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
    request: Request,
    template_id: str,
    data_source_id: str = Query(..., description="数据源ID"),
    force_reanalyze: bool = Query(False, description="强制重新分析"),
    optimization_level: str = Query("enhanced", description="优化级别"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """使用AI Agent分析模板"""
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
        
        # 获取API适配器
        api_adapter = await get_unified_api_adapter(
            request=request,
            db_session=db,
            integration_mode="react_agent"
        )
        
        # 执行分析
        result = await api_adapter.analyze_with_agent_enhanced(
            template_id=template_id,
            data_source_id=data_source_id,
            user_id=str(current_user.id),
            force_reanalyze=force_reanalyze,
            optimization_level=optimization_level
        )
        
        logger.info(f"用户 {current_user.id} 使用Agent分析了模板 {template_id}")
        
        if result.get("success"):
            return ApiResponse(
                success=True,
                data=result.get("data", {}),
                message=result.get("message", "Agent分析完成")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Agent分析失败")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent模板分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent分析失败"
        )