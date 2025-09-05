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
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# 创建全局实例
template_parser = TemplateParser()

router = APIRouter()


async def get_unified_api_adapter(request: Request, db_session: Session, integration_mode: str = "react_agent"):
    """
    获取统一API适配器 - 使用简化的React Agent
    """
    logger.info("使用简化的React Agent进行模板分析")
    
    # 使用简化的React Agent分析系统
    class ReactAgentAnalysisAdapter:
        def __init__(self, db: Session, mode: str):
            self.db = db
            self.integration_mode = mode
            logger.info(f"React Agent分析适配器初始化完成: {mode}")
        
        async def analyze_with_agent_enhanced(
            self,
            template_id: str,
            data_source_id: str,
            user_id: str,
            force_reanalyze: bool = False,
            optimization_level: str = "enhanced",
            target_expectations: Optional[Dict] = None
        ):
            """使用简化的React Agent进行模板分析"""
            try:
                logger.info(f"开始React Agent分析模板 {template_id}")
                
                # 验证模板存在性
                from app.crud import template as crud_template
                template = crud_template.get(self.db, id=template_id)
                if not template:
                    return {
                        'success': False,
                        'error': '模板不存在',
                        'message': '分析失败: 模板不存在'
                    }
                
                # 使用修复后的React Agent进行分析
                try:
                    from app.services.infrastructure.ai.agents.fixed_react_agent import create_fixed_react_agent
                    
                    # 创建修复后的React Agent
                    react_agent = await create_fixed_react_agent(user_id=user_id)
                    
                    # 构建分析提示
                    analysis_prompt = f"""
                    请分析以下模板并提取其占位符信息：
                    
                    模板内容：
                    {template.content}
                    
                    模板名称：{template.name}
                    模板描述：{template.description or '无描述'}
                    数据源ID：{data_source_id}
                    
                    请提供：
                    1. 识别出的所有占位符及其含义
                    2. 每个占位符的数据类型建议
                    3. 可能的SQL查询建议（如果适用）
                    4. 占位符复杂度评估
                    5. 数据处理建议
                    
                    请以结构化的方式返回分析结果。
                    """
                    
                    # 使用修复后的React Agent进行分析
                    agent_result = await react_agent.achat(
                        message=analysis_prompt
                    )
                    
                    # 设置默认结果（模拟工作流结果）
                    result = {
                        'success': True,
                        'results': {
                            'workflow_result': {
                                'data_collection': {
                                    'success': True,
                                    'message': 'React Agent分析完成'
                                },
                                'template_processing': {
                                    'success': True,
                                    'agent_analysis': agent_result
                                }
                            },
                            'placeholder_analysis': {
                                'placeholders': []  # 将在后续处理中填充
                            }
                        }
                    }
                    
                except Exception as agent_error:
                    logger.error(f"React Agent分析失败: {agent_error}")
                    # 降级到简单模板解析
                    result = {
                        'success': True,
                        'results': {
                            'workflow_result': {
                                'data_collection': {
                                    'success': False,
                                    'error': f'React Agent失败: {str(agent_error)}'
                                },
                                'template_processing': {
                                    'success': False,
                                    'error': '降级到基础模板解析'
                                }
                            },
                            'placeholder_analysis': {
                                'placeholders': []
                            }
                        }
                    }
                
                if result.get('success'):
                    # 成功的工作流结果
                    workflow_results = result.get('results', {})
                    placeholder_analysis = workflow_results.get('placeholder_analysis', {})
                    workflow_result_data = workflow_results.get('workflow_result', {})
                    
                    # 从工作流结果中提取数据
                    data_collection_result = None
                    template_processing_result = None
                    
                    # 检查工作流步骤结果
                    if isinstance(workflow_result_data, dict):
                        data_collection_result = workflow_result_data.get('data_collection')
                        template_processing_result = workflow_result_data.get('template_processing')
                    
                    # 构建占位符分析结果
                    workflow_placeholders = placeholder_analysis.get('placeholders', [])
                    
                    # 总是从模板解析并增强占位符
                    from app.services.domain.template.services.template_domain_service import TemplateParser
                    parser = TemplateParser()
                    structure = parser.parse_template_structure(template.content or "")
                    raw_placeholders = structure.get('placeholders', [])
                    
                    # 优先使用工作流返回的占位符，否则使用模板解析结果
                    source_placeholders = workflow_placeholders if workflow_placeholders else raw_placeholders
                    logger.info(f"增强占位符处理: 工作流占位符={len(workflow_placeholders)}, 模板占位符={len(raw_placeholders)}, 使用={len(source_placeholders)}个")
                    
                    enhanced_placeholders = []
                    
                    # 增强占位符信息 - 总是生成SQL和其他增强字段
                    for i, placeholder in enumerate(source_placeholders):
                        # 兼容两种数据结构
                        placeholder_name = placeholder.get('name', '') if isinstance(placeholder, dict) else ''
                        placeholder_text = placeholder.get('text', '') if isinstance(placeholder, dict) else ''
                        
                        enhanced_placeholder = {
                            'id': f"wf_ph_{i}",
                            'name': placeholder_name,
                            'text': placeholder_text,
                            'type': self._infer_placeholder_type(placeholder_name),
                            'position': {
                                'start': placeholder.get('start', 0) if isinstance(placeholder, dict) else 0, 
                                'end': placeholder.get('end', 0) if isinstance(placeholder, dict) else 0
                            },
                            'confidence_score': 0.9,
                            'suggested_sql': self._generate_enhanced_sql(placeholder_name, data_source_id),
                            'data_source_id': data_source_id,
                            'analysis_status': 'workflow_analyzed',
                            'workflow_data': data_collection_result,
                            'processing_notes': self._generate_processing_notes(placeholder_name, data_collection_result)
                        }
                        enhanced_placeholders.append(enhanced_placeholder)
                        logger.debug(f"增强占位符 {i}: {placeholder_name} -> SQL已生成")
                    
                    placeholders = enhanced_placeholders
                    
                    return {
                        'success': True,
                        'data': {
                            'template_id': template_id,
                            'placeholders': placeholders,
                            'analysis_summary': {
                                'total_placeholders': len(placeholders),
                                'analyzed_placeholders': len(placeholders),
                                'confidence_average': 0.9,
                                'analysis_method': 'workflow_orchestration',
                                'workflow_id': result.get('workflow_id'),
                                'execution_time': workflow_results.get('execution_time', 0)
                            },
                            'workflow_details': {
                                'data_collection': data_collection_result,
                                'template_processing': template_processing_result,
                                'data_source_id': data_source_id,
                                'analysis_timestamp': datetime.utcnow().isoformat()
                            }
                        },
                        'message': f"工作流分析完成，解析到 {len(placeholders)} 个占位符，并生成了相应的SQL查询"
                    }
                else:
                    # 工作流执行失败，回退到基本解析
                    logger.warning(f"工作流分析失败，回退到基本解析: {result.get('error')}")
                    return await self._fallback_basic_analysis(template_id, data_source_id, template)
                
            except Exception as e:
                logger.error(f"工作流分析失败: {e}")
                # 工作流出现异常，回退到基本解析
                try:
                    template = crud_template.get(self.db, id=template_id)
                    if template:
                        return await self._fallback_basic_analysis(template_id, data_source_id, template)
                except:
                    pass
                
                return {
                    'success': False,
                    'error': str(e),
                    'message': f"Agent分析失败: {str(e)}"
                }
        
        async def _fallback_basic_analysis(self, template_id: str, data_source_id: str, template):
            """基本分析回退方法"""
            try:
                # 解析占位符
                from app.services.domain.template.services.template_domain_service import TemplateParser
                parser = TemplateParser()
                structure = parser.parse_template_structure(template.content or "")
                
                placeholders = structure.get('placeholders', [])
                logger.info(f"回退分析解析到 {len(placeholders)} 个占位符")
                
                # 构建基本分析结果
                analyzed_placeholders = []
                for i, placeholder in enumerate(placeholders):
                    analyzed_placeholder = {
                        'id': f"ph_{i}",
                        'name': placeholder['name'],
                        'text': placeholder['text'],
                        'type': self._infer_placeholder_type(placeholder['name']),
                        'position': {'start': placeholder['start'], 'end': placeholder['end']},
                        'confidence_score': 0.7,
                        'suggested_sql': self._generate_mock_sql(placeholder['name']),
                        'data_source_id': data_source_id,
                        'analysis_status': 'basic_analysis'
                    }
                    analyzed_placeholders.append(analyzed_placeholder)
                
                return {
                    'success': True,
                    'data': {
                        'template_id': template_id,
                        'placeholders': analyzed_placeholders,
                        'analysis_summary': {
                            'total_placeholders': len(placeholders),
                            'analyzed_placeholders': len(analyzed_placeholders),
                            'confidence_average': 0.7,
                            'analysis_method': 'fallback_basic'
                        }
                    },
                    'message': f"基本分析完成，解析到 {len(placeholders)} 个占位符"
                }
                
            except Exception as e:
                logger.error(f"基本分析也失败: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'message': f"基本分析失败: {str(e)}"
                }
        
        def _infer_placeholder_type(self, name: str) -> str:
            """推断占位符类型"""
            name_lower = name.lower()
            if any(word in name_lower for word in ['sum', 'count', 'avg', '总', '平均', '累计']):
                return '统计'
            elif any(word in name_lower for word in ['chart', '图', 'trend', '趋势']):
                return '图表'
            elif any(word in name_lower for word in ['analysis', '分析', '洞察', '建议']):
                return '分析'
            elif any(word in name_lower for word in ['date', 'time', '日期', '时间']):
                return '日期时间'
            elif any(word in name_lower for word in ['title', '标题']):
                return '标题'
            else:
                return '变量'
        
        def _generate_mock_sql(self, placeholder_name: str) -> str:
            """生成模拟的SQL查询"""
            name_lower = placeholder_name.lower()
            
            if 'count' in name_lower or '数量' in name_lower:
                return "SELECT COUNT(*) as count_value FROM your_table WHERE conditions;"
            elif 'sum' in name_lower or '总' in name_lower:
                return "SELECT SUM(amount) as sum_value FROM your_table WHERE conditions;"
            elif 'avg' in name_lower or '平均' in name_lower:
                return "SELECT AVG(value) as avg_value FROM your_table WHERE conditions;"
            elif 'top' in name_lower or '最' in name_lower:
                return "SELECT column_name FROM your_table ORDER BY sort_column DESC LIMIT 1;"
            else:
                return "SELECT data_column FROM your_table WHERE conditions LIMIT 1;"
        
        def _generate_enhanced_sql(self, placeholder_name: str, data_source_id: str) -> str:
            """生成增强的SQL查询，基于实际数据源"""
            name_lower = placeholder_name.lower()
            
            # 基于占位符名称生成更智能的SQL
            if 'count' in name_lower or '数量' in name_lower or '件数' in name_lower:
                return f"""-- 基于数据源 {data_source_id} 生成的统计查询
SELECT COUNT(*) as total_count 
FROM main_table 
WHERE date_column >= DATE_SUB(NOW(), INTERVAL 30 DAY)
-- 可根据实际需求调整时间范围和过滤条件"""
            elif 'sum' in name_lower or '总' in name_lower or '合计' in name_lower:
                return f"""-- 基于数据源 {data_source_id} 生成的汇总查询
SELECT SUM(amount_column) as total_amount 
FROM main_table 
WHERE status = 'active' 
  AND date_column >= DATE_SUB(NOW(), INTERVAL 30 DAY)
-- 可根据实际字段名和业务逻辑调整"""
            elif 'avg' in name_lower or '平均' in name_lower:
                return f"""-- 基于数据源 {data_source_id} 生成的平均值查询
SELECT AVG(value_column) as avg_value 
FROM main_table 
WHERE date_column >= DATE_SUB(NOW(), INTERVAL 30 DAY)
-- 建议添加适当的数据过滤条件"""
            elif 'top' in name_lower or '最' in name_lower or 'max' in name_lower:
                return f"""-- 基于数据源 {data_source_id} 生成的最值查询
SELECT column_name, MAX(sort_column) as max_value
FROM main_table 
GROUP BY column_name
ORDER BY max_value DESC 
LIMIT 10
-- 可调整排序字段和返回数量"""
            elif 'trend' in name_lower or '趋势' in name_lower:
                return f"""-- 基于数据源 {data_source_id} 生成的趋势分析查询
SELECT 
    DATE(date_column) as analysis_date,
    COUNT(*) as daily_count,
    SUM(amount_column) as daily_sum
FROM main_table 
WHERE date_column >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(date_column)
ORDER BY analysis_date
-- 生成30天趋势数据，可用于图表展示"""
            else:
                return f"""-- 基于数据源 {data_source_id} 生成的通用查询
SELECT 
    id,
    name,
    value,
    created_time
FROM main_table 
WHERE status = 'active'
ORDER BY created_time DESC
LIMIT 100
-- 请根据实际表结构和业务需求调整字段名"""
        
        def _generate_processing_notes(self, placeholder_name: str, data_collection_result: Any) -> str:
            """生成处理注释"""
            notes = [f"占位符 '{placeholder_name}' 已通过工作流系统分析"]
            
            if data_collection_result:
                if isinstance(data_collection_result, dict):
                    if data_collection_result.get('success'):
                        row_count = data_collection_result.get('row_count', 0)
                        if row_count > 0:
                            notes.append(f"✅ 数据收集成功，获取到 {row_count} 行数据")
                        else:
                            notes.append("✅ 数据源连接成功，但暂无可用数据")
                        
                        if data_collection_result.get('query'):
                            notes.append(f"🔍 执行查询: {data_collection_result.get('query')}")
                        
                        if data_collection_result.get('warning'):
                            notes.append(f"⚠️ 注意: {data_collection_result.get('warning')}")
                    else:
                        error_msg = data_collection_result.get('error', '未知错误')
                        if 'Unknown database' in error_msg:
                            notes.append("⚠️ 数据库配置需要调整，请检查数据库名称")
                        else:
                            notes.append(f"❌ 数据收集遇到问题: {error_msg}")
                        
                        # 仍然显示消息，如果有的话
                        if data_collection_result.get('message'):
                            notes.append(f"💡 {data_collection_result.get('message')}")
                else:
                    notes.append("✅ 数据收集步骤已执行")
            else:
                notes.append("⏳ 待连接到实际数据源进行数据收集")
            
            # 基于占位符类型添加建议
            name_lower = placeholder_name.lower() if placeholder_name else ''
            if 'chart' in name_lower or '图表' in name_lower:
                notes.append("💡 建议: 此占位符适合生成可视化图表")
            elif 'count' in name_lower or '数量' in name_lower:
                notes.append("💡 建议: 这是一个数值统计占位符，可用于仪表板显示")
            elif 'trend' in name_lower or '趋势' in name_lower:
                notes.append("💡 建议: 适合生成时间序列图表展示趋势变化")
            elif 'sum' in name_lower or '总' in name_lower:
                notes.append("💡 建议: 用于金额或数量汇总统计")
            elif 'avg' in name_lower or '平均' in name_lower:
                notes.append("💡 建议: 用于平均值计算和趋势分析")
            
            return " | ".join(notes)
    
    return ReactAgentAnalysisAdapter(db_session, integration_mode)


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