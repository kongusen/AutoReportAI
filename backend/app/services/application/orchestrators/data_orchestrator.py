"""
数据处理编排器

负责编排数据相关的业务流程：
1. Data层：数据获取、转换、加载
2. Domain层：数据验证和业务规则检查
3. Infrastructure层：缓存和通知

专门处理复杂的ETL和数据分析工作流
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataOrchestrator:
    """
    数据处理编排器
    
    编排数据处理的完整业务流程，协调Data层和其他层的服务
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def orchestrate_data_processing(
        self, 
        pipeline_config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        编排数据处理流程
        
        这是一个复杂的ETL工作流：
        1. 验证数据源配置 (Domain)
        2. 提取数据 (Data)
        3. 转换和清洗数据 (Data)
        4. 加载到目标存储 (Data)
        5. 通知处理结果 (Infrastructure)
        """
        self.logger.info(f"开始编排数据处理流程: user={user_id}")
        
        try:
            # 启动Application层的数据处理编排任务
            celery_task_result = await self._start_data_processing_task(
                pipeline_config=pipeline_config,
                user_id=user_id
            )
            
            return {
                'success': True,
                'celery_task_id': celery_task_result.get('task_id'),
                'status': 'data_workflow_started',
                'message': '数据处理工作流已启动'
            }
            
        except Exception as e:
            self.logger.error(f"数据处理编排失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'data_orchestration_failed'
            }
    
    async def orchestrate_etl_pipeline(
        self,
        extract_config: Dict[str, Any],
        transform_config: Dict[str, Any], 
        load_config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        编排ETL管道
        
        专门处理Extract-Transform-Load工作流
        """
        self.logger.info(f"开始编排ETL管道: user={user_id}")
        
        try:
            pipeline_config = {
                'extract': extract_config,
                'transform': transform_config,
                'load': load_config,
                'user_id': user_id,
                'orchestrator': 'DataOrchestrator',
                'type': 'etl_pipeline'
            }
            
            return await self.orchestrate_data_processing(
                pipeline_config=pipeline_config,
                user_id=user_id
            )
            
        except Exception as e:
            self.logger.error(f"ETL管道编排失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'etl_orchestration_failed'
            }
    
    async def _start_data_processing_task(
        self, 
        pipeline_config: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        启动数据处理任务
        
        调用Application层的数据编排任务
        """
        try:
            # 准备任务参数
            task_config = {
                'user_id': user_id,
                'pipeline_config': pipeline_config,
                'orchestrator': 'DataOrchestrator',
                'started_at': datetime.now().isoformat()
            }
            
            # 调用Application层的数据编排任务
            from ..tasks.orchestration_tasks import orchestrate_data_processing
            
            result = orchestrate_data_processing.delay(task_config)
            
            return {
                'task_id': result.id,
                'status': 'started'
            }
            
        except Exception as e:
            self.logger.error(f"启动数据处理任务失败: {e}")
            raise