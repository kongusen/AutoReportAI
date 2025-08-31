"""
调度器管理器

统一管理所有调度器
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .refresh_scheduler import RefreshScheduler
from .task_scheduler import TaskScheduler  
from .cron_scheduler import CronScheduler

logger = logging.getLogger(__name__)

class SchedulerManager:
    """调度器管理器"""
    
    def __init__(self):
        self.refresh_scheduler = RefreshScheduler()
        self.task_scheduler = TaskScheduler()
        self.cron_scheduler = CronScheduler()
        
        self._running = False
        
        logger.info("调度器管理器初始化完成")
    
    async def start_all(self):
        """启动所有调度器"""
        if self._running:
            return
            
        try:
            await asyncio.gather(
                self.refresh_scheduler.start(),
                self.task_scheduler.start(),
                self.cron_scheduler.start()
            )
            
            self._running = True
            logger.info("所有调度器已启动")
            
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            raise
    
    async def stop_all(self):
        """停止所有调度器"""
        if not self._running:
            return
            
        try:
            await asyncio.gather(
                self.refresh_scheduler.stop(),
                self.task_scheduler.stop(), 
                self.cron_scheduler.stop()
            )
            
            self._running = False
            logger.info("所有调度器已停止")
            
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计"""
        try:
            refresh_stats = await self.refresh_scheduler.get_scheduler_stats()
            task_stats = await self.task_scheduler.get_stats()
            
            return {
                'manager_running': self._running,
                'refresh_scheduler': refresh_stats,
                'task_scheduler': task_stats,
                'cron_scheduler': {
                    'jobs_count': len(self.cron_scheduler._jobs),
                    'running': self.cron_scheduler._running
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取全局统计失败: {e}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            refresh_health = await self.refresh_scheduler.health_check()
            
            # 简化其他调度器的健康检查
            task_health = {
                'status': 'healthy' if self.task_scheduler._running else 'error',
                'issues': [] if self.task_scheduler._running else ['任务调度器未运行']
            }
            
            cron_health = {
                'status': 'healthy' if self.cron_scheduler._running else 'error', 
                'issues': [] if self.cron_scheduler._running else ['Cron调度器未运行']
            }
            
            # 汇总健康状态
            all_healthy = all([
                refresh_health['status'] == 'healthy',
                task_health['status'] == 'healthy',
                cron_health['status'] == 'healthy'
            ])
            
            overall_status = 'healthy' if all_healthy else 'degraded'
            
            all_issues = []
            all_issues.extend(refresh_health.get('issues', []))
            all_issues.extend(task_health.get('issues', []))
            all_issues.extend(cron_health.get('issues', []))
            
            return {
                'overall_status': overall_status,
                'subsystems': {
                    'refresh_scheduler': refresh_health,
                    'task_scheduler': task_health,
                    'cron_scheduler': cron_health
                },
                'total_issues': len(all_issues),
                'issues': all_issues
            }
            
        except Exception as e:
            return {
                'overall_status': 'error',
                'issues': [f"健康检查失败: {str(e)}"],
                'subsystems': {}
            }
    
    async def shutdown(self):
        """关闭管理器"""
        await self.stop_all()
        logger.info("调度器管理器已关闭")

# 全局调度器管理器
_scheduler_manager: Optional[SchedulerManager] = None

def get_scheduler_manager() -> SchedulerManager:
    """获取全局调度器管理器"""
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
    return _scheduler_manager