"""
图表缓存服务 - 管理图表生成结果的缓存
"""

import hashlib
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.placeholder_chart_cache import PlaceholderChartCache
from app.models.template_placeholder import TemplatePlaceholder

logger = logging.getLogger(__name__)


class ChartCacheService:
    """图表缓存服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_cache_key(self, 
                          placeholder_text: str, 
                          data_source_id: str, 
                          sql_query: str = None,
                          execution_mode: str = 'test_with_chart') -> str:
        """生成缓存键"""
        # 使用占位符文本、数据源和SQL查询生成唯一键
        key_data = {
            'placeholder_text': placeholder_text.strip(),
            'data_source_id': data_source_id,
            'sql_query': sql_query.strip() if sql_query else '',
            'execution_mode': execution_mode
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        cache_key = hashlib.sha256(key_string.encode()).hexdigest()[:32]
        
        return f"chart_{cache_key}"
    
    def get_cached_result(self, 
                         placeholder_id: str,
                         data_source_id: str,
                         cache_key: str = None) -> Optional[PlaceholderChartCache]:
        """获取缓存的图表结果"""
        try:
            query = self.db.query(PlaceholderChartCache).filter(
                PlaceholderChartCache.placeholder_id == placeholder_id,
                PlaceholderChartCache.data_source_id == data_source_id,
                PlaceholderChartCache.is_valid == True
            )
            
            if cache_key:
                query = query.filter(PlaceholderChartCache.cache_key == cache_key)
            
            # 按创建时间降序，获取最新的缓存
            cache_entry = query.order_by(PlaceholderChartCache.created_at.desc()).first()
            
            if cache_entry and not cache_entry.is_expired:
                # 更新命中次数
                cache_entry.update_hit_count()
                self.db.commit()
                
                logger.info(f"图表缓存命中: {cache_key}, 命中次数: {cache_entry.hit_count}")
                return cache_entry
            
            elif cache_entry and cache_entry.is_expired:
                # 缓存过期，标记为无效
                cache_entry.invalidate()
                self.db.commit()
                logger.info(f"图表缓存过期: {cache_key}")
            
            return None
            
        except Exception as e:
            logger.error(f"获取图表缓存失败: {e}")
            return None
    
    def save_chart_result(self,
                         placeholder_id: str,
                         template_id: str,
                         data_source_id: str,
                         user_id: str,
                         result_data: Dict[str, Any],
                         cache_key: str,
                         cache_ttl_hours: int = 24) -> PlaceholderChartCache:
        """保存图表生成结果到缓存"""
        try:
            # 设置过期时间
            expires_at = datetime.utcnow() + timedelta(hours=cache_ttl_hours)
            
            # 创建缓存条目
            cache_entry = PlaceholderChartCache(
                placeholder_id=placeholder_id,
                template_id=template_id,
                data_source_id=data_source_id,
                user_id=user_id,
                
                # 阶段一：SQL和数据
                generated_sql=result_data.get('sql_query', ''),
                sql_metadata=result_data.get('sql_metadata', {}),
                raw_data=result_data.get('raw_data', []),
                processed_data=result_data.get('processed_data', []),
                data_quality_score=result_data.get('execution_metadata', {}).get('data_quality_score', 0.0),
                
                # 阶段二：图表配置
                chart_type=result_data.get('chart_type', 'bar_chart'),
                echarts_config=result_data.get('echarts_config', {}),
                chart_metadata=result_data.get('chart_config', {}).get('metadata', {}),
                
                # 执行信息
                execution_mode=result_data.get('execution_mode', 'test_with_chart'),
                execution_time_ms=int(result_data.get('processing_time_ms', 0)),
                sql_execution_time_ms=result_data.get('execution_metadata', {}).get('execution_time_ms', 0),
                chart_generation_time_ms=0,  # TODO: 可以从详细执行信息中提取
                
                # 状态
                is_valid=True,
                is_preview=result_data.get('execution_mode') == 'test_with_chart',
                stage_completed=result_data.get('stage', 'chart_complete'),
                
                # 缓存管理
                cache_key=cache_key,
                cache_ttl_hours=cache_ttl_hours,
                expires_at=expires_at,
                hit_count=0
            )
            
            # 保存到数据库
            self.db.add(cache_entry)
            self.db.commit()
            self.db.refresh(cache_entry)
            
            logger.info(f"图表结果已缓存: {cache_key}, 图表类型: {cache_entry.chart_type}")
            
            return cache_entry
            
        except Exception as e:
            logger.error(f"保存图表缓存失败: {e}")
            self.db.rollback()
            raise
    
    def update_cache_result(self,
                           cache_entry: PlaceholderChartCache,
                           updated_data: Dict[str, Any]) -> PlaceholderChartCache:
        """更新缓存结果"""
        try:
            # 更新相关字段
            if 'sql_query' in updated_data:
                cache_entry.generated_sql = updated_data['sql_query']
            
            if 'chart_config' in updated_data:
                cache_entry.echarts_config = updated_data['chart_config'].get('echarts_config', {})
                cache_entry.chart_metadata = updated_data['chart_config'].get('metadata', {})
            
            if 'execution_time_ms' in updated_data:
                cache_entry.execution_time_ms = updated_data['execution_time_ms']
            
            # 更新时间戳
            cache_entry.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(cache_entry)
            
            logger.info(f"图表缓存已更新: {cache_entry.cache_key}")
            
            return cache_entry
            
        except Exception as e:
            logger.error(f"更新图表缓存失败: {e}")
            self.db.rollback()
            raise
    
    def invalidate_cache(self, placeholder_id: str, data_source_id: str = None):
        """使指定占位符的缓存失效"""
        try:
            query = self.db.query(PlaceholderChartCache).filter(
                PlaceholderChartCache.placeholder_id == placeholder_id,
                PlaceholderChartCache.is_valid == True
            )
            
            if data_source_id:
                query = query.filter(PlaceholderChartCache.data_source_id == data_source_id)
            
            cache_entries = query.all()
            
            for entry in cache_entries:
                entry.invalidate()
            
            self.db.commit()
            
            logger.info(f"已使占位符缓存失效: {placeholder_id}, 影响条目: {len(cache_entries)}")
            
        except Exception as e:
            logger.error(f"使缓存失效失败: {e}")
            self.db.rollback()
    
    def cleanup_expired_cache(self, batch_size: int = 100) -> int:
        """清理过期缓存"""
        try:
            # 查找过期的缓存条目
            expired_entries = self.db.query(PlaceholderChartCache).filter(
                PlaceholderChartCache.expires_at < datetime.utcnow(),
                PlaceholderChartCache.is_valid == True
            ).limit(batch_size).all()
            
            for entry in expired_entries:
                entry.invalidate()
            
            self.db.commit()
            
            logger.info(f"已清理 {len(expired_entries)} 个过期图表缓存")
            
            return len(expired_entries)
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            self.db.rollback()
            return 0
    
    def get_cache_stats(self, placeholder_id: str = None) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            query = self.db.query(PlaceholderChartCache)
            
            if placeholder_id:
                query = query.filter(PlaceholderChartCache.placeholder_id == placeholder_id)
            
            # 总体统计
            total_count = query.count()
            valid_count = query.filter(PlaceholderChartCache.is_valid == True).count()
            expired_count = query.filter(PlaceholderChartCache.expires_at < datetime.utcnow()).count()
            
            # 命中率统计
            cache_entries = query.filter(PlaceholderChartCache.is_valid == True).all()
            total_hits = sum(entry.hit_count for entry in cache_entries)
            avg_hits = total_hits / len(cache_entries) if cache_entries else 0
            
            # 按图表类型分组统计
            chart_type_stats = {}
            for entry in cache_entries:
                chart_type = entry.chart_type
                if chart_type not in chart_type_stats:
                    chart_type_stats[chart_type] = {'count': 0, 'hits': 0}
                chart_type_stats[chart_type]['count'] += 1
                chart_type_stats[chart_type]['hits'] += entry.hit_count
            
            return {
                'total_entries': total_count,
                'valid_entries': valid_count,
                'expired_entries': expired_count,
                'hit_rate': f"{(valid_count / total_count * 100):.1f}%" if total_count > 0 else "0%",
                'total_hits': total_hits,
                'average_hits_per_entry': round(avg_hits, 2),
                'chart_type_distribution': chart_type_stats,
                'cache_efficiency': 'high' if avg_hits > 5 else 'medium' if avg_hits > 2 else 'low'
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {
                'error': str(e),
                'total_entries': 0,
                'valid_entries': 0
            }
    
    def get_placeholder_cache_history(self, placeholder_id: str, limit: int = 10) -> List[PlaceholderChartCache]:
        """获取占位符的缓存历史"""
        try:
            cache_entries = self.db.query(PlaceholderChartCache).filter(
                PlaceholderChartCache.placeholder_id == placeholder_id
            ).order_by(
                PlaceholderChartCache.created_at.desc()
            ).limit(limit).all()
            
            return cache_entries
            
        except Exception as e:
            logger.error(f"获取占位符缓存历史失败: {e}")
            return []


def get_chart_cache_service(db: Session) -> ChartCacheService:
    """获取图表缓存服务实例"""
    return ChartCacheService(db)