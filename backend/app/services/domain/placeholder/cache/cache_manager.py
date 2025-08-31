"""
缓存管理器

统一管理所有占位符相关的缓存
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from .result_cache import ResultCache
from .context_cache import ContextCache
from .execution_cache import ExecutionCache
from ..models import DocumentContext, BusinessContext, TimeContext

logger = logging.getLogger(__name__)

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, 
                 result_cache_config: Optional[Dict[str, Any]] = None,
                 context_cache_config: Optional[Dict[str, Any]] = None,
                 execution_cache_config: Optional[Dict[str, Any]] = None):
        """
        初始化缓存管理器
        
        Args:
            result_cache_config: 结果缓存配置
            context_cache_config: 上下文缓存配置
            execution_cache_config: 执行缓存配置
        """
        # 初始化各个缓存
        self.result_cache = ResultCache(**(result_cache_config or {}))
        self.context_cache = ContextCache(**(context_cache_config or {}))
        self.execution_cache = ExecutionCache(**(execution_cache_config or {}))
        
        # 缓存管理器统计
        self.manager_stats = {
            'initialization_time': datetime.now(),
            'total_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        logger.info("缓存管理器初始化完成")
    
    # ========== 结果缓存操作 ==========
    
    async def get_analysis_result(self, 
                                 placeholder_content: str,
                                 context_data: Dict[str, Any],
                                 additional_params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """获取分析结果缓存"""
        self.manager_stats['total_operations'] += 1
        
        result = await self.result_cache.get(placeholder_content, context_data, additional_params)
        
        if result:
            self.manager_stats['cache_hits'] += 1
            logger.debug(f"分析结果缓存命中: {placeholder_content[:50]}...")
        else:
            self.manager_stats['cache_misses'] += 1
            logger.debug(f"分析结果缓存未命中: {placeholder_content[:50]}...")
        
        return result
    
    async def set_analysis_result(self, 
                                 placeholder_content: str,
                                 context_data: Dict[str, Any],
                                 result_data: Dict[str, Any],
                                 ttl_seconds: Optional[int] = None,
                                 additional_params: Dict[str, Any] = None):
        """设置分析结果缓存"""
        self.manager_stats['total_operations'] += 1
        
        await self.result_cache.set(
            placeholder_content=placeholder_content,
            context_data=context_data,
            result_data=result_data,
            ttl_seconds=ttl_seconds,
            additional_params=additional_params
        )
        
        logger.debug(f"分析结果已缓存: {placeholder_content[:50]}...")
    
    async def invalidate_analysis_results(self, pattern: str):
        """使分析结果缓存失效"""
        await self.result_cache.invalidate_by_pattern(pattern)
        logger.info(f"已使匹配模式的分析结果失效: {pattern}")
    
    # ========== 上下文缓存操作 ==========
    
    async def get_document_context(self, 
                                  document_id: str,
                                  version: Optional[str] = None) -> Optional[DocumentContext]:
        """获取文档上下文缓存"""
        self.manager_stats['total_operations'] += 1
        
        result = await self.context_cache.get_document_context(document_id, version)
        
        if result:
            self.manager_stats['cache_hits'] += 1
            logger.debug(f"文档上下文缓存命中: {document_id}")
        else:
            self.manager_stats['cache_misses'] += 1
            logger.debug(f"文档上下文缓存未命中: {document_id}")
        
        return result
    
    async def set_document_context(self, 
                                  document_id: str,
                                  context: DocumentContext,
                                  ttl_seconds: Optional[int] = None):
        """设置文档上下文缓存"""
        self.manager_stats['total_operations'] += 1
        
        await self.context_cache.set_document_context(
            document_id=document_id,
            context=context,
            ttl_seconds=ttl_seconds
        )
        
        logger.debug(f"文档上下文已缓存: {document_id}")
    
    async def get_business_context(self, 
                                  business_id: str,
                                  domain: Optional[str] = None) -> Optional[BusinessContext]:
        """获取业务上下文缓存"""
        self.manager_stats['total_operations'] += 1
        
        result = await self.context_cache.get_business_context(business_id, domain)
        
        if result:
            self.manager_stats['cache_hits'] += 1
            logger.debug(f"业务上下文缓存命中: {business_id}")
        else:
            self.manager_stats['cache_misses'] += 1
            logger.debug(f"业务上下文缓存未命中: {business_id}")
        
        return result
    
    async def set_business_context(self, 
                                  business_id: str,
                                  context: BusinessContext,
                                  ttl_seconds: Optional[int] = None):
        """设置业务上下文缓存"""
        self.manager_stats['total_operations'] += 1
        
        await self.context_cache.set_business_context(
            business_id=business_id,
            context=context,
            ttl_seconds=ttl_seconds
        )
        
        logger.debug(f"业务上下文已缓存: {business_id}")
    
    async def invalidate_context_by_type(self, context_type: str):
        """根据类型使上下文缓存失效"""
        await self.context_cache.invalidate_by_type(context_type)
        logger.info(f"已使 {context_type} 类型的上下文缓存失效")
    
    # ========== 执行缓存操作 ==========
    
    async def add_execution_record(self, 
                                  placeholder_id: str,
                                  execution_id: str,
                                  execution_time_ms: float,
                                  success: bool,
                                  result_preview: Optional[str] = None,
                                  error_message: Optional[str] = None,
                                  context_hash: str = "",
                                  sql_query_hash: Optional[str] = None,
                                  performance_metrics: Dict[str, Any] = None):
        """添加执行记录"""
        self.manager_stats['total_operations'] += 1
        
        await self.execution_cache.add_execution_record(
            placeholder_id=placeholder_id,
            execution_id=execution_id,
            execution_time_ms=execution_time_ms,
            success=success,
            result_preview=result_preview,
            error_message=error_message,
            context_hash=context_hash,
            sql_query_hash=sql_query_hash,
            performance_metrics=performance_metrics
        )
        
        logger.debug(f"执行记录已添加: {placeholder_id} ({execution_time_ms}ms)")
    
    async def get_execution_history(self, 
                                   placeholder_id: str,
                                   limit: int = 10) -> List[Dict[str, Any]]:
        """获取执行历史"""
        self.manager_stats['total_operations'] += 1
        
        records = await self.execution_cache.get_execution_history(placeholder_id, limit)
        
        # 转换为字典格式
        return [
            {
                'execution_id': record.execution_id,
                'timestamp': record.timestamp.isoformat(),
                'execution_time_ms': record.execution_time_ms,
                'success': record.success,
                'result_preview': record.result_preview,
                'error_message': record.error_message,
                'performance_metrics': record.performance_metrics
            }
            for record in records
        ]
    
    async def get_performance_insights(self) -> Dict[str, Any]:
        """获取性能洞察"""
        performance_summary = await self.execution_cache.get_performance_summary()
        recent_executions = await self.execution_cache.get_recent_executions(hours=24, limit=50)
        
        # 分析最近执行的趋势
        if recent_executions:
            success_rate_24h = sum(1 for r in recent_executions if r.success) / len(recent_executions)
            avg_time_24h = sum(r.execution_time_ms for r in recent_executions) / len(recent_executions)
        else:
            success_rate_24h = 0
            avg_time_24h = 0
        
        return {
            'overall_summary': performance_summary,
            'last_24_hours': {
                'total_executions': len(recent_executions),
                'success_rate': success_rate_24h,
                'avg_execution_time_ms': avg_time_24h
            },
            'insights': self._generate_performance_insights(performance_summary, recent_executions)
        }
    
    def _generate_performance_insights(self, 
                                     summary: Dict[str, Any],
                                     recent_executions: List[Any]) -> List[str]:
        """生成性能洞察"""
        insights = []
        
        # 成功率分析
        if summary.get('avg_success_rate', 0) < 0.9:
            insights.append("整体成功率偏低，建议检查占位符配置和数据源连接")
        
        # 性能分析
        avg_time = summary.get('avg_execution_time_ms', 0)
        if avg_time > 1000:
            insights.append("平均执行时间较长，建议优化SQL查询或增加缓存")
        elif avg_time < 50:
            insights.append("执行性能良好")
        
        # 分布分析
        perf_dist = summary.get('performance_distribution', {})
        slow_count = perf_dist.get('slow_placeholders', 0)
        total_count = summary.get('total_placeholders', 0)
        
        if total_count > 0 and slow_count / total_count > 0.2:
            insights.append(f"有 {slow_count} 个占位符执行较慢，占比 {slow_count/total_count*100:.1f}%")
        
        # 最近趋势分析
        if recent_executions:
            error_executions = [r for r in recent_executions if not r.success]
            if len(error_executions) > len(recent_executions) * 0.1:
                insights.append("最近24小时错误率较高，建议检查系统状态")
        
        return insights
    
    # ========== 管理操作 ==========
    
    async def clear_all_caches(self):
        """清空所有缓存"""
        await asyncio.gather(
            self.result_cache.clear(),
            self.context_cache.clear(),
            self.execution_cache.clear_all()
        )
        logger.info("所有缓存已清空")
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """获取全局统计信息"""
        result_stats = self.result_cache.get_stats()
        context_stats = self.context_cache.get_stats()
        execution_stats = self.execution_cache.get_cache_stats()
        
        return {
            'manager_stats': self.manager_stats.copy(),
            'result_cache': result_stats,
            'context_cache': context_stats,
            'execution_cache': execution_stats,
            'summary': {
                'total_cache_entries': (
                    result_stats.get('cache_size', 0) +
                    context_stats.get('cache_size', 0) +
                    execution_stats.get('global_stats', {}).get('total_records', 0)
                ),
                'overall_hit_rate': self.manager_stats['cache_hits'] / max(1, self.manager_stats['total_operations'])
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        # 并行检查所有缓存的健康状态
        result_health, context_health, execution_health = await asyncio.gather(
            self.result_cache.health_check(),
            self.context_cache.health_check(),
            self.execution_cache.health_check()
        )
        
        # 汇总健康状态
        all_healthy = all([
            result_health['status'] == 'healthy',
            context_health['status'] == 'healthy',
            execution_health['status'] == 'healthy'
        ])
        
        overall_status = 'healthy' if all_healthy else 'degraded'
        
        # 收集所有问题
        all_issues = []
        all_issues.extend(result_health.get('issues', []))
        all_issues.extend(context_health.get('issues', []))
        all_issues.extend(execution_health.get('issues', []))
        
        return {
            'overall_status': overall_status,
            'subsystems': {
                'result_cache': result_health,
                'context_cache': context_health,
                'execution_cache': execution_health
            },
            'total_issues': len(all_issues),
            'issues': all_issues,
            'manager_uptime': (datetime.now() - self.manager_stats['initialization_time']).total_seconds()
        }
    
    def shutdown(self):
        """关闭缓存管理器"""
        self.result_cache.shutdown()
        self.context_cache.shutdown()
        self.execution_cache.shutdown()
        logger.info("缓存管理器已关闭")

# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None

def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

def initialize_cache_manager(
    result_cache_config: Optional[Dict[str, Any]] = None,
    context_cache_config: Optional[Dict[str, Any]] = None,
    execution_cache_config: Optional[Dict[str, Any]] = None
) -> CacheManager:
    """初始化全局缓存管理器"""
    global _cache_manager
    _cache_manager = CacheManager(
        result_cache_config=result_cache_config,
        context_cache_config=context_cache_config,
        execution_cache_config=execution_cache_config
    )
    return _cache_manager