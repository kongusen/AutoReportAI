"""
任务协调代理

Application层的代理服务，负责协调数据处理任务和ETL工作流。
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskCoordinationAgent:
    """
    任务协调代理
    
    职责：
    1. 协调数据处理工作流
    2. 管理ETL管道执行
    3. 处理任务依赖和调度
    4. 协调Domain层和Infrastructure层服务
    """
    
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for Task Coordination Agent")
        self.user_id = user_id
        self.logger = logging.getLogger(self.__class__.__name__)
        # 延迟初始化各层的服务
        self._domain_services = {}
        self._infrastructure_services = {}
    
    async def coordinate_data_processing(
        self,
        pipeline_config: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        协调数据处理工作流
        
        Args:
            pipeline_config: 管道配置
            execution_context: 执行上下文
            
        Returns:
            协调结果
        """
        try:
            self.logger.info("开始协调数据处理工作流")
            
            workflow_context = {
                'workflow_id': execution_context.get('task_id'),
                'pipeline_type': pipeline_config.get('type', 'etl_pipeline'),
                'started_at': datetime.now().isoformat(),
                'execution_context': execution_context
            }
            
            # 1. 验证和准备数据源
            data_source_validation = await self._validate_data_sources(
                pipeline_config, execution_context
            )
            
            if not data_source_validation['valid']:
                return {
                    'success': False,
                    'error': 'Data source validation failed',
                    'validation_result': data_source_validation
                }
            
            # 2. 协调Domain层的数据处理逻辑
            domain_processing_result = await self._coordinate_domain_processing(
                pipeline_config, execution_context
            )
            
            # 3. 协调Infrastructure层的技术处理
            infrastructure_processing_result = await self._coordinate_infrastructure_processing(
                domain_processing_result, execution_context
            )
            
            # 4. 整合结果并返回
            return {
                'success': True,
                'workflow_context': workflow_context,
                'results': {
                    'data_source_validation': data_source_validation,
                    'domain_processing': domain_processing_result,
                    'infrastructure_processing': infrastructure_processing_result
                },
                'completed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"数据处理工作流协调失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
    
    async def coordinate_etl_pipeline(
        self,
        extract_config: Dict[str, Any],
        transform_config: Dict[str, Any],
        load_config: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        协调ETL管道执行
        
        Args:
            extract_config: 提取配置
            transform_config: 转换配置
            load_config: 加载配置
            execution_context: 执行上下文
            
        Returns:
            ETL执行结果
        """
        try:
            self.logger.info("开始协调ETL管道")
            
            # 整合ETL配置
            pipeline_config = {
                'type': 'etl_pipeline',
                'extract': extract_config,
                'transform': transform_config,
                'load': load_config
            }
            
            # 调用通用数据处理协调方法
            return await self.coordinate_data_processing(pipeline_config, execution_context)
            
        except Exception as e:
            self.logger.error(f"ETL管道协调失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
    
    async def _validate_data_sources(
        self, 
        pipeline_config: Dict[str, Any], 
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证数据源可用性"""
        try:
            # 获取Data层的数据源服务
            data_source_service = await self._get_data_service('data_source_validation')
            
            # 提取数据源配置
            extract_config = pipeline_config.get('extract', {})
            data_source_id = extract_config.get('data_source_id')
            
            if not data_source_id:
                return {
                    'valid': False,
                    'error': 'No data source specified',
                    'validation_details': {}
                }
            
            # 验证数据源
            validation_result = await data_source_service.validate_data_source_connectivity(
                data_source_id=data_source_id,
                validation_context=execution_context
            )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"数据源验证失败: {e}")
            return {
                'valid': False,
                'error': str(e),
                'validation_details': {}
            }
    
    async def _coordinate_domain_processing(
        self,
        pipeline_config: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """协调Domain层的数据处理逻辑"""
        try:
            # 获取Domain层的数据处理服务
            domain_processor = await self._get_domain_service('data_processing')
            
            # 协调Domain层的业务逻辑处理
            processing_result = await domain_processor.process_business_data(
                pipeline_config=pipeline_config,
                processing_context=execution_context
            )
            
            return processing_result
            
        except Exception as e:
            self.logger.error(f"Domain层数据处理协调失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'domain_processing_failed': True
            }
    
    async def _coordinate_infrastructure_processing(
        self,
        domain_result: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """协调Infrastructure层的技术处理"""
        try:
            # 获取Infrastructure层的处理服务
            infra_processor = await self._get_infrastructure_service('data_processing')
            
            # 协调Infrastructure层的技术处理
            processing_result = await infra_processor.process_technical_aspects(
                domain_result=domain_result,
                processing_context=execution_context
            )
            
            return processing_result
            
        except Exception as e:
            self.logger.error(f"Infrastructure层处理协调失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'infrastructure_processing_failed': True
            }
    
    async def _get_domain_service(self, service_type: str):
        """获取Domain层服务实例"""
        if service_type not in self._domain_services:
            if service_type == 'data_processing':
                from ...domain.analysis.services import get_data_analysis_domain_service
                self._domain_services[service_type] = await get_data_analysis_domain_service()
            else:
                raise ValueError(f"Unknown domain service type: {service_type}")
        
        return self._domain_services[service_type]
    
    async def _get_data_service(self, service_type: str):
        """获取Data层服务实例"""
        if service_type not in self._domain_services:
            if service_type == 'data_source_validation':
                from ...data.sources import get_data_source_service
                self._domain_services[service_type] = await get_data_source_service()
            else:
                raise ValueError(f"Unknown data service type: {service_type}")
        
        return self._domain_services[service_type]
    
    async def _get_infrastructure_service(self, service_type: str):
        """获取Infrastructure层服务实例"""
        if service_type not in self._infrastructure_services:
            if service_type == 'data_processing':
                from ...infrastructure.agents import get_data_transformation_agent
                self._infrastructure_services[service_type] = await get_data_transformation_agent()
            else:
                raise ValueError(f"Unknown infrastructure service type: {service_type}")
        
        return self._infrastructure_services[service_type]