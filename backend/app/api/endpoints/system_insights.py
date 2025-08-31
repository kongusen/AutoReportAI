"""
系统洞察API - 提供统一上下文系统的性能监控和洞察
"""

from typing import Any, Dict, Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.architecture import ApiResponse
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/context-system/performance", response_model=ApiResponse)
async def get_context_system_performance(
    integration_mode: str = Query("intelligent", description="集成模式"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取统一上下文系统的性能指标
    """
    try:
        # REMOVED: IAOP import - integration.unified_api_adapter import get_unified_api_adapter
        adapter = get_unified_api_adapter(db_session=db, integration_mode=integration_mode)
        
        # 获取系统洞察
        insights_result = await adapter.get_system_insights()
        
        if not insights_result.get('success'):
            return ApiResponse(
                success=False,
                data={},
                message=f"获取系统洞察失败: {insights_result.get('error', '未知错误')}"
            )
        
        return ApiResponse(
            success=True,
            data=insights_result.get('data'),
            message="系统性能指标获取成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取系统性能指标失败: {str(e)}"
        )


@router.get("/context-system/optimization-settings", response_model=ApiResponse)
async def get_optimization_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取上下文优化配置
    """
    try:
        # 获取默认配置
        default_settings = {
            'integration_modes': [
                {
                    'mode': 'basic',
                    'name': '基础模式',
                    'description': '仅使用智能上下文管理，适合简单场景',
                    'features': ['智能上下文推理', '基础错误处理']
                },
                {
                    'mode': 'enhanced',
                    'name': '增强模式',
                    'description': '添加渐进式优化引擎，适合中等复杂场景',
                    'features': ['智能上下文推理', '渐进式优化', '性能监控']
                },
                {
                    'mode': 'intelligent',
                    'name': '智能模式',
                    'description': '全功能集成，适合复杂业务场景',
                    'features': ['智能上下文推理', '渐进式优化', '学习系统', '自适应调整']
                },
                {
                    'mode': 'learning',
                    'name': '学习模式',
                    'description': '启用主动学习，系统会持续改进',
                    'features': ['全部智能功能', '主动学习', '模式识别', '知识积累']
                }
            ],
            'optimization_levels': [
                {
                    'level': 'basic',
                    'name': '基础优化',
                    'description': '基本的上下文补全和错误修正'
                },
                {
                    'level': 'enhanced',
                    'name': '增强优化',
                    'description': '智能推理和上下文增强'
                },
                {
                    'level': 'iterative',
                    'name': '迭代优化',
                    'description': '多轮迭代改进，直到达到满意效果'
                },
                {
                    'level': 'intelligent',
                    'name': '智能优化',
                    'description': '基于学习的自适应优化'
                }
            ],
            'current_defaults': {
                'integration_mode': 'intelligent',
                'optimization_level': 'enhanced',
                'max_optimization_iterations': 5,
                'confidence_threshold': 0.8,
                'enable_learning': True,
                'enable_performance_monitoring': True
            }
        }
        
        return ApiResponse(
            success=True,
            data=default_settings,
            message="优化配置获取成功"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取优化配置失败: {str(e)}"
        )


@router.post("/context-system/test-configuration", response_model=ApiResponse)
async def test_context_system_configuration(
    test_config: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    测试上下文系统配置
    
    允许用户测试不同的集成模式和优化级别
    """
    try:
        integration_mode = test_config.get('integration_mode', 'intelligent')
        optimization_level = test_config.get('optimization_level', 'enhanced')
        test_data = test_config.get('test_data', {})
        
        # REMOVED: IAOP import - integration.unified_api_adapter import get_unified_api_adapter
        adapter = get_unified_api_adapter(db_session=db, integration_mode=integration_mode)
        
        # 创建测试上下文
        test_session_id = f"config_test_{int(datetime.now().timestamp())}"
        
        # REMOVED: IAOP import - context.unified_context_system import create_unified_context_system
        test_system = create_unified_context_system(
            db_session=db,
            integration_mode=integration_mode,
            enable_performance_monitoring=True
        )
        
        # 执行测试
        test_result = await test_system.create_execution_context(
            session_id=test_session_id,
            user_id=str(current_user.id),
            request_data=test_data,
            business_intent=test_data.get('business_intent', 'Configuration test'),
            data_source_context=test_data.get('data_source_context', {})
        )
        
        # 构建测试报告
        test_report = {
            'configuration_tested': {
                'integration_mode': integration_mode,
                'optimization_level': optimization_level
            },
            'test_results': {
                'success': test_result.success,
                'confidence_score': test_result.confidence_score,
                'optimization_applied': test_result.optimization_applied,
                'learning_applied': test_result.learning_applied,
                'processing_time_ms': test_result.processing_details.get('total_processing_time', 0)
            },
            'system_capabilities': {
                'context_intelligence': test_result.context is not None,
                'optimization_engine': test_result.optimization_applied,
                'learning_system': test_result.learning_applied,
                'performance_monitoring': True
            },
            'recommendations': test_result.recommendations,
            'test_timestamp': datetime.now().isoformat()
        }
        
        return ApiResponse(
            success=True,
            data=test_report,
            message="配置测试完成"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"配置测试失败: {str(e)}"
        )


@router.get("/context-system/health", response_model=ApiResponse)
async def get_context_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取统一上下文系统健康状态
    """
    try:
        # REMOVED: IAOP import - integration.unified_api_adapter import get_unified_api_adapter
        
        health_status = {
            'overall_status': 'healthy',
            'components': {},
            'checks': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # 测试不同集成模式的健康状态
        integration_modes = ['basic', 'enhanced', 'intelligent', 'learning']
        
        for mode in integration_modes:
            try:
                adapter = get_unified_api_adapter(db_session=db, integration_mode=mode)
                # 简单的健康检查
                mode_health = {
                    'status': 'healthy',
                    'initialized': True,
                    'components_active': {}
                }
                
                # 检查各组件
                if hasattr(adapter.unified_system, 'context_manager'):
                    mode_health['components_active']['context_manager'] = True
                    
                if hasattr(adapter.unified_system, 'optimization_engine') and adapter.unified_system.optimization_engine:
                    mode_health['components_active']['optimization_engine'] = True
                    
                if hasattr(adapter.unified_system, 'learning_system') and adapter.unified_system.learning_system:
                    mode_health['components_active']['learning_system'] = True
                
                health_status['components'][mode] = mode_health
                health_status['checks'].append(f"{mode} mode: OK")
                
            except Exception as e:
                health_status['components'][mode] = {
                    'status': 'error',
                    'error': str(e)
                }
                health_status['checks'].append(f"{mode} mode: ERROR - {str(e)}")
                health_status['overall_status'] = 'degraded'
        
        return ApiResponse(
            success=True,
            data=health_status,
            message="系统健康检查完成"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )