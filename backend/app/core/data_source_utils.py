"""
数据源工具类
支持多种ID格式的解析和转换，以及大数据处理优化功能
"""

import re
import uuid
import logging
import time
from typing import Optional, Union, Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from unidecode import unidecode
import pandas as pd
import psutil
import gc

from ..models.data_source import DataSource
from ..models.user import User

logger = logging.getLogger(__name__)


def generate_slug(name: str, user_id: uuid.UUID, db: Session) -> str:
    """
    从名称生成用户友好的slug
    
    Args:
        name: 数据源名称
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        唯一的slug
    """
    # 基础slug生成
    base_slug = slugify(name)
    
    # 确保唯一性
    counter = 0
    slug = base_slug
    
    while True:
        existing = db.query(DataSource).filter(
            DataSource.user_id == user_id,
            DataSource.slug == slug
        ).first()
        
        if not existing:
            break
            
        counter += 1
        slug = f"{base_slug}-{counter}"
    
    return slug


def slugify(text: str) -> str:
    """
    将文本转换为URL友好的slug
    
    Args:
        text: 原始文本
        
    Returns:
        slug格式的字符串
    """
    # 转换为ASCII
    text = unidecode(text)
    
    # 转小写并替换空格和特殊字符
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)
    
    # 移除首尾的连字符
    text = text.strip('-')
    
    # 限制长度
    return text[:50]


def parse_data_source_id(
    identifier: Union[str, uuid.UUID], 
    user_id: uuid.UUID, 
    db: Session
) -> Optional[DataSource]:
    """
    解析数据源标识符，支持多种格式
    
    支持的格式：
    1. UUID: "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    2. Slug: "my-doris-db"  
    3. Name: "My Doris Database"
    4. Display Name: "我的Doris数据库"
    
    Args:
        identifier: 数据源标识符
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        数据源对象或None
    """
    if not identifier:
        return None
    
    # 如果已经是UUID对象
    if isinstance(identifier, uuid.UUID):
        return db.query(DataSource).filter(
            DataSource.id == identifier,
            DataSource.user_id == user_id
        ).first()
    
    identifier_str = str(identifier).strip()
    
    # 尝试解析为UUID
    try:
        uuid_obj = uuid.UUID(identifier_str)
        return db.query(DataSource).filter(
            DataSource.id == uuid_obj,
            DataSource.user_id == user_id
        ).first()
    except ValueError:
        pass
    
    # 尝试按slug查找
    result = db.query(DataSource).filter(
        DataSource.slug == identifier_str,
        DataSource.user_id == user_id
    ).first()
    
    if result:
        return result
    
    # 尝试按名称查找
    result = db.query(DataSource).filter(
        DataSource.name == identifier_str,
        DataSource.user_id == user_id
    ).first()
    
    if result:
        return result
    
    # 尝试按显示名称查找
    result = db.query(DataSource).filter(
        DataSource.display_name == identifier_str,
        DataSource.user_id == user_id
    ).first()
    
    return result


def get_user_friendly_id(data_source: DataSource) -> str:
    """
    获取用户友好的数据源ID
    
    Args:
        data_source: 数据源对象
        
    Returns:
        用户友好的ID
    """
    if data_source.slug:
        return data_source.slug
    elif data_source.display_name:
        return slugify(data_source.display_name)
    else:
        return slugify(data_source.name)


def format_data_source_info(data_source: DataSource) -> dict:
    """
    格式化数据源信息，包含多种ID格式
    
    Args:
        data_source: 数据源对象
        
    Returns:
        格式化的数据源信息
    """
    return {
        "id": str(data_source.id),  # UUID
        "slug": data_source.slug,   # 用户友好ID
        "name": data_source.name,   # 系统名称
        "display_name": data_source.display_name,  # 显示名称
        "user_friendly_id": get_user_friendly_id(data_source),  # 推荐使用的ID
        "source_type": data_source.source_type,
        "is_active": data_source.is_active,
        "created_at": data_source.created_at.isoformat() if data_source.created_at else None,
        "updated_at": data_source.updated_at.isoformat() if data_source.updated_at else None
    }


class DataSourceIDResolver:
    """数据源ID解析器"""
    
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
    
    def resolve(self, identifier: Union[str, uuid.UUID]) -> Optional[DataSource]:
        """解析数据源标识符"""
        return parse_data_source_id(identifier, self.user_id, self.db)
    
    def get_by_slug(self, slug: str) -> Optional[DataSource]:
        """根据slug获取数据源"""
        return self.db.query(DataSource).filter(
            DataSource.slug == slug,
            DataSource.user_id == self.user_id
        ).first()
    
    def generate_unique_slug(self, name: str) -> str:
        """生成唯一的slug"""
        return generate_slug(name, self.user_id, self.db)


class DataSourceConnectionManager:
    """数据源连接管理器 - 优化大数据处理"""
    
    def __init__(self):
        self._connections = {}
        self._connection_stats = {}
    
    def get_connection(self, data_source: DataSource) -> Engine:
        """获取数据源连接"""
        connection_key = f"{data_source.id}_{data_source.source_type}"
        
        if connection_key not in self._connections:
            try:
                if data_source.source_type == "sql":
                    engine = create_engine(
                        data_source.connection_string,
                        pool_size=5,
                        max_overflow=10,
                        pool_pre_ping=True,
                        pool_recycle=3600
                    )
                    self._connections[connection_key] = engine
                    self._connection_stats[connection_key] = {
                        "created_at": time.time(),
                        "query_count": 0,
                        "total_time": 0
                    }
                    logger.info(f"创建数据源连接: {data_source.name}")
                else:
                    logger.warning(f"不支持的数据源类型: {data_source.source_type}")
                    return None
            except Exception as e:
                logger.error(f"创建数据源连接失败: {e}")
                return None
        
        return self._connections.get(connection_key)
    
    def close_connection(self, data_source: DataSource):
        """关闭数据源连接"""
        connection_key = f"{data_source.id}_{data_source.source_type}"
        if connection_key in self._connections:
            try:
                self._connections[connection_key].dispose()
                del self._connections[connection_key]
                del self._connection_stats[connection_key]
                logger.info(f"关闭数据源连接: {data_source.name}")
            except Exception as e:
                logger.error(f"关闭数据源连接失败: {e}")
    
    def get_connection_stats(self, data_source: DataSource) -> Dict[str, Any]:
        """获取连接统计信息"""
        connection_key = f"{data_source.id}_{data_source.source_type}"
        return self._connection_stats.get(connection_key, {})
    
    def update_query_stats(self, data_source: DataSource, execution_time: float):
        """更新查询统计"""
        connection_key = f"{data_source.id}_{data_source.source_type}"
        if connection_key in self._connection_stats:
            stats = self._connection_stats[connection_key]
            stats["query_count"] += 1
            stats["total_time"] += execution_time
            stats["avg_time"] = stats["total_time"] / stats["query_count"]


class QueryOptimizer:
    """查询优化器 - 针对大数据处理优化"""
    
    @staticmethod
    def analyze_query_complexity(query: str) -> Dict[str, Any]:
        """分析查询复杂度"""
        complexity_score = 0
        complexity_factors = {}
        
        # 检查JOIN
        join_count = query.upper().count("JOIN")
        complexity_score += join_count * 2
        complexity_factors["joins"] = join_count
        
        # 检查子查询
        subquery_count = query.count("(SELECT")
        complexity_score += subquery_count * 3
        complexity_factors["subqueries"] = subquery_count
        
        # 检查聚合函数
        agg_functions = ["COUNT", "SUM", "AVG", "MAX", "MIN", "GROUP BY"]
        agg_count = sum(1 for func in agg_functions if func in query.upper())
        complexity_score += agg_count
        complexity_factors["aggregations"] = agg_count
        
        # 检查排序
        if "ORDER BY" in query.upper():
            complexity_score += 1
            complexity_factors["ordering"] = True
        
        # 检查DISTINCT
        if "DISTINCT" in query.upper():
            complexity_score += 1
            complexity_factors["distinct"] = True
        
        return {
            "complexity_score": complexity_score,
            "factors": complexity_factors,
            "level": "low" if complexity_score < 3 else "medium" if complexity_score < 8 else "high"
        }
    
    @staticmethod
    def suggest_query_optimizations(query: str, data_source: DataSource) -> List[str]:
        """建议查询优化"""
        suggestions = []
        query_upper = query.upper()
        
        # 建议添加LIMIT
        if "LIMIT" not in query_upper and "TOP" not in query_upper:
            suggestions.append("建议添加LIMIT子句以限制返回记录数")
        
        # 建议索引优化
        if "WHERE" in query_upper:
            suggestions.append("确保WHERE子句中的列有适当的索引")
        
        # 建议避免SELECT *
        if "SELECT *" in query_upper:
            suggestions.append("避免使用SELECT *，明确指定需要的列")
        
        # 建议JOIN优化
        if "JOIN" in query_upper:
            suggestions.append("确保JOIN条件中的列有索引")
        
        # 建议GROUP BY优化
        if "GROUP BY" in query_upper:
            suggestions.append("考虑在GROUP BY列上创建索引")
        
        return suggestions
    
    @staticmethod
    def estimate_memory_usage(query: str, estimated_rows: int) -> Dict[str, Any]:
        """估算内存使用量"""
        # 简单的内存估算
        base_memory_per_row = 1024  # 1KB per row (估算)
        
        # 根据查询类型调整
        if "GROUP BY" in query.upper():
            base_memory_per_row *= 2
        if "ORDER BY" in query.upper():
            base_memory_per_row *= 1.5
        if "DISTINCT" in query.upper():
            base_memory_per_row *= 1.2
        
        estimated_memory_mb = (estimated_rows * base_memory_per_row) / (1024 * 1024)
        
        return {
            "estimated_memory_mb": estimated_memory_mb,
            "estimated_rows": estimated_rows,
            "memory_per_row_bytes": base_memory_per_row,
            "recommendation": "normal" if estimated_memory_mb < 100 else "batch_processing" if estimated_memory_mb < 500 else "streaming"
        }


class BatchQueryExecutor:
    """批量查询执行器 - 处理大数据集"""
    
    def __init__(self, batch_size: int = 10000, memory_threshold: float = 0.8):
        self.batch_size = batch_size
        self.memory_threshold = memory_threshold
        self.connection_manager = DataSourceConnectionManager()
    
    async def execute_query_with_batching(self, 
                                        query: str, 
                                        data_source: DataSource,
                                        enable_memory_monitoring: bool = True) -> pd.DataFrame:
        """
        执行批量查询
        
        Args:
            query: SQL查询
            data_source: 数据源
            enable_memory_monitoring: 是否启用内存监控
            
        Returns:
            查询结果DataFrame
        """
        start_time = time.time()
        
        try:
            engine = self.connection_manager.get_connection(data_source)
            if not engine:
                raise ValueError("无法获取数据源连接")
            
            # 检查是否需要分批处理
            if self._should_use_batching(query):
                logger.info("使用批量处理模式")
                result = await self._execute_with_batching(query, engine, enable_memory_monitoring)
            else:
                logger.info("使用普通查询模式")
                result = pd.read_sql(text(query), engine)
            
            execution_time = time.time() - start_time
            self.connection_manager.update_query_stats(data_source, execution_time)
            
            logger.info(f"查询执行完成，耗时: {execution_time:.2f}秒，返回 {len(result)} 行")
            return result
            
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise e
    
    def _should_use_batching(self, query: str) -> bool:
        """判断是否应该使用批量处理"""
        complexity = QueryOptimizer.analyze_query_complexity(query)
        
        # 复杂查询使用批量处理
        if complexity["level"] == "high":
            return True
        
        # 大表查询使用批量处理
        if "LIMIT" not in query.upper() and "TOP" not in query.upper():
            return True
        
        return False
    
    async def _execute_with_batching(self, 
                                   query: str, 
                                   engine: Engine,
                                   enable_memory_monitoring: bool) -> pd.DataFrame:
        """执行批量查询"""
        results = []
        offset = 0
        batch_count = 0
        
        while True:
            # 构造批量查询
            batch_query = f"{query} LIMIT {self.batch_size} OFFSET {offset}"
            
            try:
                # 内存监控
                if enable_memory_monitoring:
                    memory_percent = psutil.virtual_memory().percent / 100
                    if memory_percent > self.memory_threshold:
                        logger.warning(f"内存使用率过高: {memory_percent:.1%}，触发垃圾回收")
                        gc.collect()
                        
                        # 如果内存仍然过高，暂停处理
                        if psutil.virtual_memory().percent / 100 > 0.9:
                            logger.error("内存使用率过高，停止批量处理")
                            break
                
                batch_result = pd.read_sql(text(batch_query), engine)
                batch_count += 1
                
                if len(batch_result) == 0:
                    break
                
                results.append(batch_result)
                offset += self.batch_size
                
                logger.debug(f"批次 {batch_count} 处理完成，记录数: {len(batch_result)}")
                
            except Exception as e:
                logger.error(f"批次 {batch_count + 1} 处理失败: {e}")
                break
        
        # 合并结果
        if results:
            final_result = pd.concat(results, ignore_index=True)
            logger.info(f"批量处理完成，总批次: {batch_count}，总记录数: {len(final_result)}")
            return final_result
        else:
            return pd.DataFrame()
    
    def get_optimal_batch_size(self, estimated_rows: int, available_memory_mb: int) -> int:
        """获取最优批次大小"""
        # 基于可用内存计算最优批次大小
        memory_per_row_kb = 1  # 估算每行1KB
        max_batch_size = (available_memory_mb * 1024) // memory_per_row_kb
        
        # 限制在合理范围内
        optimal_batch_size = min(max_batch_size, max(1000, min(50000, estimated_rows // 10)))
        
        logger.info(f"计算最优批次大小: {optimal_batch_size}，基于内存: {available_memory_mb}MB")
        return optimal_batch_size


# 创建全局实例
connection_manager = DataSourceConnectionManager()
query_optimizer = QueryOptimizer()
batch_executor = BatchQueryExecutor()