"""
图表测试API - 支持模板占位符的完整图表生成测试
"""

from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.architecture import ApiResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.iaop.orchestration.two_stage_chart_orchestrator import get_two_stage_chart_orchestrator

router = APIRouter()


class ChartTestRequest(BaseModel):
    """图表测试请求"""
    placeholder_text: str
    data_source_id: str
    template_id: Optional[str] = None
    execution_mode: str = "test_with_chart"  # sql_only | test_with_chart
    chart_type_hint: Optional[str] = None  # bar_chart, pie_chart, line_chart, etc.


class ChartTestResponse(BaseModel):
    """图表测试响应"""
    success: bool
    stage: str
    execution_mode: str
    data: Dict[str, Any]
    processing_time_ms: float
    error: Optional[str] = None
    next_actions: Optional[list] = None


@router.post("/test-chart", response_model=ApiResponse)
async def test_chart_generation(
    request: ChartTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试图表生成
    
    支持两种模式：
    - sql_only: 仅生成SQL查询
    - test_with_chart: 生成SQL并执行，返回完整图表配置
    """
    try:
        # 获取两阶段编排器
        orchestrator = get_two_stage_chart_orchestrator(db)
        
        # 执行图表生成测试
        result = await orchestrator.execute_for_template_placeholder(
            placeholder_text=request.placeholder_text,
            data_source_id=request.data_source_id,
            user_id=str(current_user.id),
            template_id=request.template_id,
            execution_mode=request.execution_mode
        )
        
        # 如果提供了图表类型提示，添加到语义分析中
        if request.chart_type_hint and 'data' in result:
            if 'semantic_analysis' not in result['data']:
                result['data']['semantic_analysis'] = {}
            result['data']['semantic_analysis']['chart_type_hint'] = request.chart_type_hint
        
        return ApiResponse(
            success=result.get('success', False),
            data=result,
            message="图表测试执行完成" if result.get('success') else f"图表测试失败: {result.get('error', '未知错误')}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"图表测试执行异常: {str(e)}"
        )


@router.post("/placeholders/{placeholder_id}/test-chart", response_model=ApiResponse) 
async def test_placeholder_chart(
    placeholder_id: str,
    request: Dict[str, Any],
    optimization_level: str = Query("enhanced", description="优化级别：basic/enhanced/intelligent/learning"),
    target_expectation: Optional[str] = Query(None, description="期望结果描述"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    为指定占位符测试图表生成（基于统一上下文系统）
    
    兼容现有的ETLScriptManager组件调用，但使用新的智能上下文管理
    """
    try:
        # 获取数据源ID和执行模式
        data_source_id = request.get('data_source_id')
        execution_mode = request.get('execution_mode', 'test_with_chart')
        
        if not data_source_id:
            raise HTTPException(status_code=400, detail="缺少data_source_id参数")
        
        # 获取占位符信息
        from app.models.template_placeholder import TemplatePlaceholder
        placeholder = db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.id == placeholder_id
        ).first()
        
        if not placeholder:
            raise HTTPException(status_code=404, detail="占位符不存在")
        
        # 检查占位符类型，只有图表类占位符才支持图表生成
        is_chart_placeholder = placeholder.content_type in ['chart', 'image'] or placeholder.placeholder_type in ['chart', 'visualization']
        
        # 根据占位符类型决定执行模式
        if not is_chart_placeholder:
            # 非图表占位符，执行SQL查询但不生成图表
            if execution_mode == 'test_with_chart':
                execution_mode = 'test_with_data'  # 使用智能SQL生成模式
        
        # 对于test_with_data模式，使用统一API适配器进行智能处理
        if execution_mode == 'test_with_data':
            from app.services.iaop.integration.unified_api_adapter import get_unified_api_adapter
            adapter = get_unified_api_adapter(db_session=db, integration_mode=optimization_level)
            
            # 执行增强的test_with_data
            result = await adapter.test_with_data_enhanced(
                placeholder_text=placeholder.placeholder_name,
                data_source_id=data_source_id,
                user_id=str(current_user.id),
                template_id=str(placeholder.template_id) if placeholder.template_id else None,
                target_expectation=target_expectation,
                optimization_level=optimization_level
            )
            
            return ApiResponse(
                success=result.get('success', False),
                data=result,
                message="智能占位符测试完成" if result.get('success') else "测试失败，请检查配置和期望"
            )
        else:
            # 其他模式使用原有的两阶段编排器
            orchestrator = get_two_stage_chart_orchestrator(db)
            
            # 执行图表生成测试
            result = await orchestrator.execute_for_template_placeholder(
                placeholder_text=placeholder.placeholder_name,
                data_source_id=data_source_id,
                user_id=str(current_user.id),
                template_id=str(placeholder.template_id) if placeholder.template_id else None,
                execution_mode=execution_mode
            )
        
        # 为非图表占位符添加类型说明
        if not is_chart_placeholder and result.get('success'):
            result['data']['placeholder_type_info'] = {
                'is_chart_placeholder': False,
                'content_type': placeholder.content_type,
                'placeholder_type': placeholder.placeholder_type,
                'message': '当前占位符不是图表类型，仅执行SQL查询测试'
            }
        
        # 如果测试成功且是完整模式，可以选择保存SQL到数据库
        if result.get('success') and execution_mode == 'test_with_chart':
            sql_query = result.get('data', {}).get('sql_query', '')
            if sql_query and sql_query != placeholder.generated_sql:
                # 可选：自动更新生成的SQL
                # placeholder.generated_sql = sql_query
                # placeholder.last_analysis_at = datetime.utcnow()
                # db.commit()
                pass
        
        # 格式化响应以兼容前端ETLScriptManager期望的格式
        if result.get('success'):
            # 提取目标数据库和表信息
            sql_metadata = result.get('data', {}).get('sql_metadata', {})
            execution_metadata = result.get('data', {}).get('execution_metadata', {})
            raw_data = result.get('data', {}).get('raw_data', [])
            
            # 从SQL元数据中提取目标表信息
            target_table = sql_metadata.get('target_table', '')
            if not target_table:
                # 尝试从SQL查询中提取表名
                sql_query = result.get('data', {}).get('sql_query', '')
                if 'online_retail' in sql_query.lower():
                    target_table = 'online_retail'
            
            # 从数据源上下文或执行元数据中提取数据库信息
            target_database = 'doris'  # 根据当前配置默认为doris
            
            # 计算实际结果值（如果是COUNT查询）
            actual_result_value = None
            if raw_data and len(raw_data) > 0:
                first_row = raw_data[0]
                if isinstance(first_row, dict):
                    # 尝试获取COUNT类查询的结果
                    for key, value in first_row.items():
                        if 'count' in key.lower() or 'total' in key.lower():
                            actual_result_value = str(value)
                            break
                    # 如果没找到count类字段，使用第一个数值字段
                    if actual_result_value is None:
                        for key, value in first_row.items():
                            if isinstance(value, (int, float)):
                                actual_result_value = str(value)
                                break
            
            formatted_data = {
                # 基础执行信息
                'success': True,
                'execution_time_ms': result.get('processing_time_ms', 0),
                'sql_executed': result.get('data', {}).get('sql_query', ''),
                
                # 数据信息
                'raw_data': raw_data,
                'row_count': len(raw_data),
                'actual_result_value': actual_result_value,  # 实际查询结果值
                
                # 数据库和表信息
                'target_database': target_database,
                'target_table': target_table,
                
                # 图表信息（如果是完整测试模式且是图表类占位符）
                'chart_config': result.get('data', {}).get('chart_config') if is_chart_placeholder else None,
                'chart_type': result.get('data', {}).get('chart_type') if is_chart_placeholder else None,
                'echarts_config': result.get('data', {}).get('echarts_config') if is_chart_placeholder else None,
                'chart_ready': result.get('data', {}).get('chart_ready', False) if is_chart_placeholder else False,
                
                # 占位符类型信息
                'is_chart_placeholder': is_chart_placeholder,
                'placeholder_type_info': result.get('data', {}).get('placeholder_type_info'),
                
                # 测试摘要
                'test_summary': result.get('data', {}).get('test_summary'),
                
                # 格式化文本（用于前端显示）
                'formatted_text': _generate_formatted_text(result, is_chart_placeholder, raw_data, actual_result_value),
                
                # 完整原始结果
                'full_result': result
            }
        else:
            formatted_data = {
                'success': False,
                'error_message': result.get('error', '测试失败'),
                'execution_time_ms': result.get('processing_time_ms', 0),
                'sql_executed': result.get('data', {}).get('sql_query', ''),
                'troubleshooting': result.get('troubleshooting', []),
                'partial_success': result.get('partial_success', False),
                'success_stages': result.get('success_stages', []),
                'is_chart_placeholder': is_chart_placeholder,
                'placeholder_type_info': {
                    'is_chart_placeholder': is_chart_placeholder,
                    'content_type': placeholder.content_type,
                    'placeholder_type': placeholder.placeholder_type,
                    'expected_mode': 'chart_generation' if is_chart_placeholder else 'sql_query'
                },
                'full_result': result
            }
        
        return ApiResponse(
            success=result.get('success', False),
            data=formatted_data,
            message="占位符图表测试完成" if result.get('success') else "测试失败，请检查配置"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"占位符图表测试异常: {str(e)}"
        )


def _generate_formatted_text(result: Dict[str, Any], is_chart_placeholder: bool, raw_data: list, actual_result_value: str) -> str:
    """生成格式化显示文本"""
    try:
        if result.get('data', {}).get('chart_ready'):
            chart_type = result.get('data', {}).get('chart_type', '图表')
            data_points = len(raw_data)
            return f"生成 {chart_type}，包含 {data_points} 个数据点"
        elif actual_result_value:
            return f"查询结果: {actual_result_value}"
        else:
            return "SQL测试成功"
    except Exception as e:
        return "SQL测试成功"


@router.get("/chart-types", response_model=ApiResponse)
async def get_supported_chart_types():
    """获取支持的图表类型"""
    chart_types = [
        {
            "key": "bar_chart",
            "name": "柱状图", 
            "description": "适合比较不同类别的数据",
            "data_requirements": ["分类字段", "数值字段"],
            "best_for": ["销售对比", "数量统计", "排名显示"]
        },
        {
            "key": "pie_chart",
            "name": "饼图",
            "description": "显示数据的占比分布",
            "data_requirements": ["分类字段", "数值字段"],
            "best_for": ["比例分析", "组成结构", "市场份额"]
        },
        {
            "key": "line_chart", 
            "name": "折线图",
            "description": "显示数据随时间的变化趋势",
            "data_requirements": ["时间字段", "数值字段"],
            "best_for": ["趋势分析", "时间序列", "增长跟踪"]
        },
        {
            "key": "scatter_chart",
            "name": "散点图",
            "description": "显示两个变量之间的关系",
            "data_requirements": ["两个数值字段"],
            "best_for": ["关系分析", "分布模式", "相关性探索"]
        },
        {
            "key": "radar_chart",
            "name": "雷达图",
            "description": "多维度数据的综合展示",
            "data_requirements": ["多个数值维度"],
            "best_for": ["能力评估", "多指标对比", "综合分析"]
        },
        {
            "key": "funnel_chart",
            "name": "漏斗图", 
            "description": "显示业务流程的转化情况",
            "data_requirements": ["流程阶段", "数值字段"],
            "best_for": ["转化分析", "流程监控", "效率评估"]
        }
    ]
    
    return ApiResponse(
        success=True,
        data={
            "chart_types": chart_types,
            "total_count": len(chart_types),
            "default_type": "bar_chart"
        },
        message="获取图表类型列表成功"
    )