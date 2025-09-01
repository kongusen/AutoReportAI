"""
报告应用服务

Application Service负责：
1. 协调报告生成的业务流程
2. 整合Domain层的报告业务逻辑
3. 协调Data层的数据处理  
4. 管理报告生成的完整用例

遵循DDD原则，专注于应用层的协调职责
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass 
class ReportGenerationRequest:
    """报告生成请求"""
    template_id: str
    data_source_ids: List[str]
    user_id: str
    report_name: Optional[str] = None
    output_format: str = "html"
    execution_context: Optional[Dict[str, Any]] = None


@dataclass
class ReportGenerationResult:
    """报告生成结果"""
    success: bool
    report_id: Optional[str] = None
    celery_task_id: Optional[str] = None
    status: str = "unknown"
    message: Optional[str] = None
    error: Optional[str] = None


class ReportApplicationService:
    """
    报告应用服务
    
    负责协调报告生成的完整业务流程
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def generate_report(self, request: ReportGenerationRequest) -> ReportGenerationResult:
        """
        生成报告
        
        Application Service职责：
        1. 验证请求参数
        2. 协调Domain层的报告业务逻辑
        3. 启动报告生成编排器
        4. 返回执行结果
        """
        try:
            self.logger.info(f"开始生成报告: template={request.template_id}, user={request.user_id}")
            
            # 验证请求
            validation_result = await self._validate_report_request(request)
            if not validation_result['valid']:
                return ReportGenerationResult(
                    success=False,
                    status='validation_failed',
                    error=validation_result['error']
                )
            
            # 调用编排器启动报告生成工作流
            from ..orchestrators.report_orchestrator import ReportOrchestrator
            orchestrator = ReportOrchestrator()
            
            orchestration_result = await orchestrator.orchestrate_report_generation(
                template_id=request.template_id,
                data_source_ids=request.data_source_ids,
                execution_context=request.execution_context or {},
                user_id=request.user_id
            )
            
            return ReportGenerationResult(
                success=orchestration_result['success'],
                celery_task_id=orchestration_result.get('celery_task_id'),
                status=orchestration_result.get('status', 'started'),
                message='报告生成工作流已启动'
            )
            
        except Exception as e:
            self.logger.error(f"报告生成失败: {e}")
            return ReportGenerationResult(
                success=False,
                status='generation_failed', 
                error=str(e)
            )
    
    async def get_report_status(self, report_id: str) -> Dict[str, Any]:
        """
        获取报告状态
        
        协调Domain层和Infrastructure层获取报告状态
        """
        try:
            # TODO: 实现报告状态查询逻辑
            # 这里应该调用Domain层的报告服务查询状态
            
            return {
                'report_id': report_id,
                'status': 'pending',  # 占位符状态
                'progress': 0.0,
                'message': '报告正在生成中'
            }
            
        except Exception as e:
            self.logger.error(f"查询报告状态失败: {e}")
            return {
                'report_id': report_id,
                'status': 'error',
                'error': str(e)
            }
    
    async def _validate_report_request(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """
        验证报告生成请求
        
        Application Service层的基础验证，复杂业务验证在Domain层
        """
        try:
            # 基础参数验证
            if not request.template_id:
                return {'valid': False, 'error': '模板ID不能为空'}
            
            if not request.data_source_ids:
                return {'valid': False, 'error': '数据源不能为空'} 
            
            if not request.user_id:
                return {'valid': False, 'error': '用户ID不能为空'}
            
            # TODO: 调用Domain层进行业务验证
            # 例如：验证模板是否存在、用户权限、数据源可访问性等
            
            return {'valid': True}
            
        except Exception as e:
            self.logger.error(f"请求验证失败: {e}")
            return {'valid': False, 'error': f'验证失败: {str(e)}'}