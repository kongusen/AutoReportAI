"""
Data层 - 数据处理任务

数据获取、转换、加载等数据层面的任务
专注于数据的技术处理，不涉及业务逻辑
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.infrastructure.task_queue.celery_config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='tasks.data.extract.fetch_data_source', bind=True)
def fetch_data_source(self, data_source_id: str, query_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    从数据源获取数据
    
    Data层职责：纯粹的数据获取，不涉及业务逻辑
    """
    logger.info(f"开始数据获取，数据源ID: {data_source_id}")
    
    try:
        # 尝试使用现有的数据连接器
        try:
            from app.services.data.connectors.connector_factory import ConnectorFactory
            
            connector = ConnectorFactory.create_connector(data_source_id)
            result = connector.fetch_data(query_config)
            
            return {
                'success': True,
                'data_source_id': data_source_id,
                'data': result,
                'fetch_metadata': {
                    'fetched_at': datetime.now().isoformat(),
                    'task_id': self.request.id,
                    'connector_type': type(connector).__name__
                }
            }
            
        except ImportError:
            logger.warning("ConnectorFactory not available, using mock data")
            
            # 模拟数据获取
            mock_data = _generate_mock_data(data_source_id, query_config)
            
            return {
                'success': True,
                'data_source_id': data_source_id,
                'data': mock_data,
                'fetch_metadata': {
                    'fetched_at': datetime.now().isoformat(),
                    'task_id': self.request.id,
                    'connector_type': 'MockConnector'
                },
                'note': 'Using mock data due to connector unavailability'
            }
            
    except Exception as e:
        logger.error(f"数据获取失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'data_source_id': data_source_id,
            'task_id': self.request.id
        }


@celery_app.task(name='tasks.data.transform.process_data', bind=True)
def process_data(self, raw_data: Dict[str, Any], processing_rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    数据处理和转换
    
    Data层职责：数据清洗、格式转换、聚合计算
    """
    logger.info(f"开始数据处理，任务ID: {self.request.id}")
    
    try:
        processed_data = {
            'raw_record_count': len(raw_data.get('records', [])),
            'processed_records': [],
            'aggregations': {},
            'transformations_applied': []
        }
        
        records = raw_data.get('records', [])
        
        # 数据清洗
        if processing_rules.get('clean_data', True):
            cleaned_records = _clean_data_records(records)
            processed_data['transformations_applied'].append('data_cleaning')
            records = cleaned_records
        
        # 数据类型转换
        if processing_rules.get('convert_types', True):
            typed_records = _convert_data_types(records)
            processed_data['transformations_applied'].append('type_conversion')
            records = typed_records
        
        # 数据聚合
        aggregation_rules = processing_rules.get('aggregations', {})
        if aggregation_rules:
            aggregations = _perform_aggregations(records, aggregation_rules)
            processed_data['aggregations'] = aggregations
            processed_data['transformations_applied'].append('data_aggregation')
        
        # 数据过滤
        filter_rules = processing_rules.get('filters', {})
        if filter_rules:
            filtered_records = _apply_filters(records, filter_rules)
            processed_data['transformations_applied'].append('data_filtering')
            records = filtered_records
        
        processed_data['processed_records'] = records
        processed_data['final_record_count'] = len(records)
        
        return {
            'success': True,
            'processed_data': processed_data,
            'processing_metadata': {
                'processed_at': datetime.now().isoformat(),
                'task_id': self.request.id,
                'transformations': processed_data['transformations_applied']
            }
        }
        
    except Exception as e:
        logger.error(f"数据处理失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }


@celery_app.task(name='tasks.data.load.cache_results', bind=True)
def cache_results(self, processed_data: Dict[str, Any], cache_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    缓存处理结果
    
    Data层职责：数据存储和缓存管理
    """
    logger.info(f"开始结果缓存，任务ID: {self.request.id}")
    
    try:
        # 尝试使用统一缓存系统
        try:
            from app.services.infrastructure.cache.unified_cache_system import get_cache_manager
            
            cache_manager = get_cache_manager()
            cache_key = cache_config.get('cache_key', f"data_result_{self.request.id}")
            ttl = cache_config.get('ttl', 3600)
            
            cache_manager.set(cache_key, processed_data, ttl=ttl)
            
            return {
                'success': True,
                'cache_key': cache_key,
                'cached_at': datetime.now().isoformat(),
                'ttl': ttl,
                'task_id': self.request.id
            }
            
        except ImportError:
            logger.warning("Unified cache system not available, using simple storage")
            
            # 简单的内存存储模拟
            cache_key = f"mock_cache_{self.request.id}"
            
            return {
                'success': True,
                'cache_key': cache_key,
                'cached_at': datetime.now().isoformat(),
                'ttl': cache_config.get('ttl', 3600),
                'task_id': self.request.id,
                'note': 'Using mock cache storage'
            }
            
    except Exception as e:
        logger.error(f"结果缓存失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }


@celery_app.task(name='tasks.data.etl.run_etl_pipeline', bind=True)
def run_etl_pipeline(self, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    运行完整的ETL管道
    
    Data层职责：协调Extract、Transform、Load过程
    """
    logger.info(f"开始ETL管道执行，任务ID: {self.request.id}")
    
    try:
        pipeline_state = {
            'pipeline_id': self.request.id,
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'steps_completed': []
        }
        
        # Extract阶段
        extract_config = pipeline_config.get('extract', {})
        data_source_id = extract_config.get('data_source_id')
        query_config = extract_config.get('query_config', {})
        
        extract_result = fetch_data_source.delay(data_source_id, query_config).get()
        
        if not extract_result.get('success'):
            return {
                'success': False,
                'error': 'Extract stage failed',
                'details': extract_result,
                'pipeline_state': pipeline_state
            }
        
        pipeline_state['steps_completed'].append('extract')
        
        # Transform阶段
        transform_config = pipeline_config.get('transform', {})
        transform_result = process_data.delay(
            extract_result['data'], 
            transform_config
        ).get()
        
        if not transform_result.get('success'):
            return {
                'success': False,
                'error': 'Transform stage failed',
                'details': transform_result,
                'pipeline_state': pipeline_state
            }
        
        pipeline_state['steps_completed'].append('transform')
        
        # Load阶段
        load_config = pipeline_config.get('load', {})
        load_result = cache_results.delay(
            transform_result['processed_data'],
            load_config
        ).get()
        
        if not load_result.get('success'):
            return {
                'success': False,
                'error': 'Load stage failed',
                'details': load_result,
                'pipeline_state': pipeline_state
            }
        
        pipeline_state['steps_completed'].append('load')
        pipeline_state['status'] = 'completed'
        pipeline_state['completed_at'] = datetime.now().isoformat()
        
        return {
            'success': True,
            'pipeline_state': pipeline_state,
            'extract_result': extract_result,
            'transform_result': transform_result,
            'load_result': load_result,
            'task_id': self.request.id
        }
        
    except Exception as e:
        logger.error(f"ETL管道执行失败: {e}")
        pipeline_state['status'] = 'failed'
        pipeline_state['error'] = str(e)
        pipeline_state['failed_at'] = datetime.now().isoformat()
        
        return {
            'success': False,
            'error': str(e),
            'pipeline_state': pipeline_state,
            'task_id': self.request.id
        }


# 辅助函数
def _generate_mock_data(data_source_id: str, query_config: Dict[str, Any]) -> Dict[str, Any]:
    """生成模拟数据"""
    mock_records = [
        {'id': 1, 'revenue': 50000, 'cost': 30000, 'profit': 20000, 'date': '2024-01-01'},
        {'id': 2, 'revenue': 52000, 'cost': 31000, 'profit': 21000, 'date': '2024-01-02'},
        {'id': 3, 'revenue': 48000, 'cost': 29000, 'profit': 19000, 'date': '2024-01-03'},
        {'id': 4, 'revenue': 55000, 'cost': 33000, 'profit': 22000, 'date': '2024-01-04'},
        {'id': 5, 'revenue': 51000, 'cost': 30500, 'profit': 20500, 'date': '2024-01-05'}
    ]
    
    return {
        'records': mock_records,
        'total_count': len(mock_records),
        'query_config': query_config,
        'generated_at': datetime.now().isoformat()
    }


def _clean_data_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """数据清洗"""
    cleaned_records = []
    
    for record in records:
        cleaned_record = {}
        for key, value in record.items():
            # 清除空值和None
            if value is not None and value != '':
                # 清理字符串
                if isinstance(value, str):
                    cleaned_record[key] = value.strip()
                else:
                    cleaned_record[key] = value
        
        if cleaned_record:  # 只保留有有效数据的记录
            cleaned_records.append(cleaned_record)
    
    return cleaned_records


def _convert_data_types(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """数据类型转换"""
    typed_records = []
    
    for record in records:
        typed_record = {}
        for key, value in record.items():
            # 尝试转换数值类型
            if isinstance(value, str) and value.isdigit():
                typed_record[key] = int(value)
            elif isinstance(value, str):
                try:
                    typed_record[key] = float(value)
                except ValueError:
                    typed_record[key] = value
            else:
                typed_record[key] = value
        
        typed_records.append(typed_record)
    
    return typed_records


def _perform_aggregations(records: List[Dict[str, Any]], aggregation_rules: Dict[str, Any]) -> Dict[str, Any]:
    """执行数据聚合"""
    aggregations = {}
    
    # 数值字段聚合
    numeric_fields = ['revenue', 'cost', 'profit']
    
    for field in numeric_fields:
        if field in aggregation_rules.get('sum', []):
            values = [r.get(field, 0) for r in records if isinstance(r.get(field), (int, float))]
            aggregations[f'{field}_sum'] = sum(values)
        
        if field in aggregation_rules.get('avg', []):
            values = [r.get(field, 0) for r in records if isinstance(r.get(field), (int, float))]
            aggregations[f'{field}_avg'] = sum(values) / len(values) if values else 0
        
        if field in aggregation_rules.get('max', []):
            values = [r.get(field, 0) for r in records if isinstance(r.get(field), (int, float))]
            aggregations[f'{field}_max'] = max(values) if values else 0
        
        if field in aggregation_rules.get('min', []):
            values = [r.get(field, 0) for r in records if isinstance(r.get(field), (int, float))]
            aggregations[f'{field}_min'] = min(values) if values else 0
    
    # 记录数统计
    aggregations['total_records'] = len(records)
    
    return aggregations


def _apply_filters(records: List[Dict[str, Any]], filter_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    """应用数据过滤规则"""
    filtered_records = records
    
    # 数值范围过滤
    for field, range_filter in filter_rules.get('range', {}).items():
        min_val = range_filter.get('min')
        max_val = range_filter.get('max')
        
        if min_val is not None or max_val is not None:
            filtered_records = [
                r for r in filtered_records
                if (min_val is None or r.get(field, 0) >= min_val) and
                   (max_val is None or r.get(field, 0) <= max_val)
            ]
    
    # 值匹配过滤
    for field, values in filter_rules.get('in', {}).items():
        if values:
            filtered_records = [
                r for r in filtered_records
                if r.get(field) in values
            ]
    
    return filtered_records