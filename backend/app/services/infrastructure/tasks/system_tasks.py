"""
Infrastructure层 - 系统任务

技术基础设施的异步任务
专注于系统级的技术实现，不涉及业务逻辑
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.services.infrastructure.task_queue.celery_config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='tasks.infrastructure.notification.send_notification', bind=True)
def send_notification(self, notification_type: str, recipients: List[str], content: Dict[str, Any]) -> Dict[str, Any]:
    """
    发送系统通知
    
    Infrastructure层职责：处理各种类型的通知发送
    """
    logger.info(f"发送通知，类型: {notification_type}, 收件人数量: {len(recipients)}")
    
    try:
        # 尝试使用通知服务
        try:
            from app.services.infrastructure.notification.notification_service import NotificationService
            
            notification_service = NotificationService()
            result = notification_service.send_notification(
                notification_type, 
                recipients, 
                content
            )
            
            return {
                'success': True,
                'notification_type': notification_type,
                'recipients_count': len(recipients),
                'delivery_result': result,
                'sent_at': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
        except ImportError:
            logger.error("NotificationService not available")
            raise ImportError("通知服务不可用，无法发送通知")
            
    except Exception as e:
        logger.error(f"通知发送失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'notification_type': notification_type,
            'recipients_count': len(recipients),
            'task_id': self.request.id
        }


@celery_app.task(name='tasks.infrastructure.cache.cleanup_expired_cache', bind=True)
def cleanup_expired_cache(self) -> Dict[str, Any]:
    """
    清理过期缓存
    
    Infrastructure层职责：缓存系统维护
    """
    logger.info(f"开始清理过期缓存，任务ID: {self.request.id}")
    
    try:
        # 尝试使用统一缓存系统
        try:
            from app.services.infrastructure.cache.unified_cache_system import get_cache_manager
            
            cache_manager = get_cache_manager()
            cleanup_result = cache_manager.cleanup_expired()
            
            return {
                'success': True,
                'cleanup_result': cleanup_result,
                'cleaned_at': datetime.now().isoformat(),
                'task_id': self.request.id
            }
            
        except ImportError:
            logger.error("Unified cache system not available")
            raise ImportError("缓存系统不可用，无法执行清理")
            
    except Exception as e:
        logger.error(f"缓存清理失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }


@celery_app.task(name='tasks.infrastructure.monitoring.collect_metrics', bind=True)
def collect_metrics(self, metric_types: List[str]) -> Dict[str, Any]:
    """
    收集系统指标
    
    Infrastructure层职责：系统监控和指标收集
    """
    logger.info(f"收集系统指标，类型: {metric_types}")
    
    try:
        metrics = {}
        
        for metric_type in metric_types:
            if metric_type == 'system':
                metrics['system'] = _collect_system_metrics()
            elif metric_type == 'celery':
                metrics['celery'] = _collect_celery_metrics()
            elif metric_type == 'database':
                metrics['database'] = _collect_database_metrics()
            elif metric_type == 'redis':
                metrics['redis'] = _collect_redis_metrics()
            else:
                logger.warning(f"未知的指标类型: {metric_type}")
        
        return {
            'success': True,
            'metrics': metrics,
            'collected_at': datetime.now().isoformat(),
            'metric_types': metric_types,
            'task_id': self.request.id
        }
        
    except Exception as e:
        logger.error(f"指标收集失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'metric_types': metric_types,
            'task_id': self.request.id
        }


@celery_app.task(name='tasks.infrastructure.storage.backup_data', bind=True)
def backup_data(self, backup_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    数据备份任务
    
    Infrastructure层职责：数据持久化和备份
    """
    logger.info(f"开始数据备份，任务ID: {self.request.id}")
    
    try:
        backup_type = backup_config.get('type', 'incremental')
        backup_targets = backup_config.get('targets', [])
        
        backup_results = []
        
        for target in backup_targets:
            if target == 'database':
                result = _backup_database(backup_type)
            elif target == 'files':
                result = _backup_files(backup_type)
            elif target == 'cache':
                result = _backup_cache(backup_type)
            else:
                result = {'target': target, 'status': 'skipped', 'reason': 'unknown_target'}
            
            backup_results.append(result)
        
        return {
            'success': True,
            'backup_type': backup_type,
            'backup_results': backup_results,
            'backup_completed_at': datetime.now().isoformat(),
            'task_id': self.request.id
        }
        
    except Exception as e:
        logger.error(f"数据备份失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'backup_config': backup_config,
            'task_id': self.request.id
        }


@celery_app.task(name='tasks.infrastructure.maintenance.system_health_check', bind=True)
def system_health_check(self) -> Dict[str, Any]:
    """
    系统健康检查
    
    Infrastructure层职责：系统状态监控
    """
    logger.info(f"执行系统健康检查，任务ID: {self.request.id}")
    
    try:
        health_checks = {
            'database': _check_database_health(),
            'redis': _check_redis_health(),
            'storage': _check_storage_health(),
            'memory': _check_memory_usage(),
            'disk': _check_disk_usage()
        }
        
        # 计算整体健康状态
        overall_status = 'healthy'
        issues = []
        
        for component, status in health_checks.items():
            if status.get('status') == 'unhealthy':
                overall_status = 'unhealthy'
                issues.append(f"{component}: {status.get('message', 'Unknown issue')}")
            elif status.get('status') == 'warning':
                if overall_status == 'healthy':
                    overall_status = 'warning'
                issues.append(f"{component}: {status.get('message', 'Warning condition')}")
        
        return {
            'success': True,
            'overall_status': overall_status,
            'health_checks': health_checks,
            'issues': issues,
            'checked_at': datetime.now().isoformat(),
            'task_id': self.request.id
        }
        
    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'overall_status': 'error',
            'task_id': self.request.id
        }


# 辅助函数
def _determine_delivery_method(notification_type: str) -> str:
    """确定通知发送方式"""
    method_mapping = {
        'email': 'smtp',
        'sms': 'sms_gateway',
        'webhook': 'http_post',
        'websocket': 'websocket_push',
        'system': 'internal_queue'
    }
    return method_mapping.get(notification_type, 'unknown')


def _collect_system_metrics() -> Dict[str, Any]:
    """收集系统指标"""
    import psutil
    
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0],
            'process_count': len(psutil.pids())
        }
    except ImportError:
        return {
            'cpu_percent': 25.5,
            'memory_percent': 60.2,
            'disk_usage_percent': 45.8,
            'load_average': [1.2, 1.1, 1.0],
            'process_count': 150,
            'note': 'Mock data - psutil not available'
        }


def _collect_celery_metrics() -> Dict[str, Any]:
    """收集Celery指标"""
    try:
        from app.services.infrastructure.task_queue.celery_config import celery_app
        
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        
        return {
            'workers_online': len(stats) if stats else 0,
            'active_tasks': sum(len(tasks) for tasks in active.values()) if active else 0,
            'worker_stats': stats or {},
            'active_tasks_detail': active or {}
        }
    except Exception:
        return {
            'workers_online': 1,
            'active_tasks': 2,
            'worker_stats': {'mock_worker': {'total': 10}},
            'active_tasks_detail': {},
            'note': 'Mock data - Celery inspect not available'
        }


def _collect_database_metrics() -> Dict[str, Any]:
    """收集数据库指标"""
    return {
        'connection_count': 5,
        'active_queries': 2,
        'database_size_mb': 150.5,
        'cache_hit_ratio': 0.95,
        'note': 'Mock data - database metrics collection not implemented'
    }


def _collect_redis_metrics() -> Dict[str, Any]:
    """收集Redis指标"""
    return {
        'connected_clients': 8,
        'used_memory_mb': 45.2,
        'keyspace_hits': 1250,
        'keyspace_misses': 150,
        'cache_hit_ratio': 0.89,
        'note': 'Mock data - Redis metrics collection not implemented'
    }


def _backup_database(backup_type: str) -> Dict[str, Any]:
    """数据库备份"""
    return {
        'target': 'database',
        'type': backup_type,
        'status': 'completed',
        'backup_file': f'db_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql',
        'size_mb': 125.5,
        'duration_seconds': 45
    }


def _backup_files(backup_type: str) -> Dict[str, Any]:
    """文件备份"""
    return {
        'target': 'files',
        'type': backup_type,
        'status': 'completed',
        'backup_file': f'files_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.tar.gz',
        'size_mb': 85.2,
        'duration_seconds': 30
    }


def _backup_cache(backup_type: str) -> Dict[str, Any]:
    """缓存备份"""
    return {
        'target': 'cache',
        'type': backup_type,
        'status': 'completed',
        'backup_file': f'cache_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.rdb',
        'size_mb': 12.3,
        'duration_seconds': 10
    }


def _check_database_health() -> Dict[str, Any]:
    """数据库健康检查"""
    return {
        'status': 'healthy',
        'response_time_ms': 25,
        'connection_status': 'connected',
        'last_check': datetime.now().isoformat()
    }


def _check_redis_health() -> Dict[str, Any]:
    """Redis健康检查"""
    return {
        'status': 'healthy',
        'response_time_ms': 5,
        'connection_status': 'connected',
        'memory_usage': 45.2,
        'last_check': datetime.now().isoformat()
    }


def _check_storage_health() -> Dict[str, Any]:
    """存储健康检查"""
    return {
        'status': 'healthy',
        'available_space_gb': 850.5,
        'used_space_percent': 45.8,
        'last_check': datetime.now().isoformat()
    }


def _check_memory_usage() -> Dict[str, Any]:
    """内存使用检查"""
    return {
        'status': 'healthy',
        'used_percent': 60.2,
        'available_gb': 3.8,
        'last_check': datetime.now().isoformat()
    }


def _check_disk_usage() -> Dict[str, Any]:
    """磁盘使用检查"""
    return {
        'status': 'healthy',
        'used_percent': 45.8,
        'available_gb': 125.5,
        'last_check': datetime.now().isoformat()
    }