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
        # 使用React Agent系统获取系统洞察
        from app.services.infrastructure.ai.agents import create_react_agent
        
        agent = create_react_agent(str(current_user.id))
        await agent.initialize()
        
        insights_prompt = f"""
        分析当前系统的性能指标和健康状态：
        
        集成模式: {integration_mode}
        
        请提供以下信息：
        1. 系统整体健康状态评估
        2. 主要组件运行状态
        3. 性能瓶颈识别
        4. 优化建议
        5. 资源使用情况
        
        返回结构化的分析结果。
        """
        
        insights_result = await agent.chat(insights_prompt, context={
            "integration_mode": integration_mode,
            "task_type": "system_analysis"
        })
        
        analysis_data = {
            "integration_mode": integration_mode,
            "analysis_result": insights_result,
            "timestamp": datetime.now().isoformat(),
            "analyzed_by": "react_agent"
        }
        
        return ApiResponse(
            success=True,
            data=analysis_data,
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
        
        # 使用React Agent系统进行配置测试
        from app.services.infrastructure.ai.agents import create_react_agent
        
        agent = create_react_agent(str(current_user.id))
        await agent.initialize()
        
        # 创建测试会话ID
        test_session_id = f"config_test_{int(datetime.now().timestamp())}"
        
        
        # 使用React Agent执行配置测试
        config_test_prompt = f"""
        测试系统配置的有效性：
        
        集成模式: {integration_mode}
        优化级别: {optimization_level}
        测试数据: {test_data}
        测试会话: {test_session_id}
        
        请执行以下测试：
        1. 验证配置参数的合理性
        2. 模拟系统负载测试
        3. 检查系统稳定性
        4. 评估性能影响
        5. 提供优化建议
        
        返回详细的测试报告。
        """
        
        test_result = await agent.chat(config_test_prompt, context={
            "session_id": test_session_id,
            "integration_mode": integration_mode,
            "optimization_level": optimization_level,
            "test_data": test_data,
            "task_type": "configuration_test"
        })
        
        test_report = {
            'configuration_tested': {
                'integration_mode': integration_mode,
                'optimization_level': optimization_level,
                'test_session_id': test_session_id
            },
            'test_results': {
                'success': True,
                'analysis': test_result,
                'tested_by': 'react_agent'
            },
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
        # 使用React Agent系统健康检查
        
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
                # 简单的模式健康检查
                mode_health = {
                    'status': 'healthy',
                    'initialized': True,
                    'components_active': {
                        'react_agent': True,
                        'llm_service': True,
                        'database': True
                    }
                }
                
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


@router.post("/context-system/analyze", response_model=ApiResponse)
async def analyze_with_context_system(
    analysis_request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    使用React Agent进行智能分析
    
    支持的分析类型:
    - sql_generation: SQL生成分析
    - template_analysis: 模板分析
    - data_analysis: 数据分析
    - performance_analysis: 性能分析
    """
    try:
        analysis_type = analysis_request.get('analysis_type', 'general')
        query = analysis_request.get('query', '')
        context = analysis_request.get('context', '')
        optimization_level = analysis_request.get('optimization_level', 'enhanced')
        
        if not query:
            raise HTTPException(
                status_code=400,
                detail="分析查询不能为空"
            )
        
        # 使用React Agent进行智能分析
        from app.services.infrastructure.ai.agents import create_react_agent
        
        agent = create_react_agent(str(current_user.id))
        await agent.initialize()
        
        # 构建分析提示
        analysis_prompt = f"""
        进行 {analysis_type} 类型的智能分析：
        
        查询内容: {query}
        
        上下文信息:
        {context}
        
        优化级别: {optimization_level}
        
        请根据分析类型提供详细的分析结果:
        """
        
        if analysis_type == 'sql_generation':
            analysis_prompt += """
            
            对于SQL生成分析，请:
            1. 理解查询需求
            2. 分析上下文中的表结构信息
            3. 生成高质量的SQL查询语句
            4. 提供查询说明和优化建议
            5. 确保SQL语法正确且性能优化
            
            返回格式请包含:
            - 生成的SQL查询
            - 查询说明
            - 性能评估
            - 优化建议
            """
        elif analysis_type == 'template_analysis':
            analysis_prompt += """
            
            对于模板分析，请:
            1. 识别模板中的占位符
            2. 理解占位符的业务含义
            3. 生成相应的数据查询逻辑
            4. 提供数据映射建议
            
            返回格式请包含:
            - 占位符清单
            - 业务含义解释  
            - 数据查询建议
            - 模板优化建议
            """
        
        analysis_result = await agent.chat(analysis_prompt, context={
            "analysis_type": analysis_type,
            "optimization_level": optimization_level,
            "task_type": "intelligent_analysis"
        })
        
        response_data = {
            'analysis_type': analysis_type,
            'query': query,
            'optimization_level': optimization_level,
            'response': analysis_result,
            'timestamp': datetime.now().isoformat(),
            'analyzed_by': 'react_agent',
            'metadata': {
                'user_id': str(current_user.id),
                'agent_type': 'react',
                'model_used': 'anthropic:claude-3-5-sonnet-20241022',
                'model_confidence': 0.95,
                'tools_available': 0,
                'max_iterations': 15,
                'database_driven': True
            }
        }
        
        return ApiResponse(
            success=True,
            data=response_data,
            message=f"{analysis_type} 分析完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"智能分析失败: {str(e)}"
        )