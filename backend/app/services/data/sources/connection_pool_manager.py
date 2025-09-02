"""
数据库连接池管理器
管理SQL数据库连接池，提供连接复用和性能优化
"""

import logging
from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """数据库连接池管理器"""

    def __init__(self):
        self._pools: Dict[str, Engine] = {}
        self.logger = logger

    def get_engine(self, connection_string: str, pool_size: int = 10) -> Engine:
        """获取数据库引擎（优化连接池配置）"""
        pool_key = f"{connection_string}_{pool_size}"

        if pool_key not in self._pools:
            self.logger.info(f"Creating optimized connection pool for: {connection_string[:50]}...")
            self._pools[pool_key] = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=pool_size,          # 增加基础连接池大小
                max_overflow=20,              # 增加溢出连接数
                pool_pre_ping=True,           # 连接前检查
                pool_recycle=1800,            # 优化：30分钟回收连接
                pool_timeout=30,              # 获取连接超时时间
                pool_reset_on_return='commit', # 返回时重置连接状态
                echo=False,
                connect_args={
                    "options": "-c default_transaction_isolation=read_committed"
                } if "postgresql" in connection_string.lower() else {}
            )

        return self._pools[pool_key]

    def close_all_pools(self):
        """关闭所有连接池"""
        self.logger.info(f"Closing {len(self._pools)} connection pools")
        for engine in self._pools.values():
            engine.dispose()
        self._pools.clear()

    def get_pool_info(self) -> Dict[str, Any]:
        """获取连接池信息（增强监控）"""
        pool_details = []
        
        for pool_key, engine in self._pools.items():
            pool = engine.pool
            pool_details.append({
                "pool_key": pool_key[:50] + "..." if len(pool_key) > 50 else pool_key,
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
            })
        
        return {
            "total_pools": len(self._pools),
            "pool_details": pool_details,
            "total_connections": sum(p["size"] for p in pool_details),
            "active_connections": sum(p["checked_out"] for p in pool_details),
            "available_connections": sum(p["checked_in"] for p in pool_details),
            "pool_keys": list(self._pools.keys())
        }

    def remove_pool(self, connection_string: str, pool_size: int = 5):
        """移除指定的连接池"""
        pool_key = f"{connection_string}_{pool_size}"
        if pool_key in self._pools:
            self.logger.info(f"Removing connection pool: {pool_key}")
            self._pools[pool_key].dispose()
            del self._pools[pool_key]
