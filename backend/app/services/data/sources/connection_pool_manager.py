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

    def get_engine(self, connection_string: str, pool_size: int = 5) -> Engine:
        """获取数据库引擎（带连接池）"""
        pool_key = f"{connection_string}_{pool_size}"

        if pool_key not in self._pools:
            self.logger.info(f"Creating new connection pool for: {connection_string}")
            self._pools[pool_key] = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=10,
                pool_pre_ping=True,  # 连接前检查
                pool_recycle=3600,  # 1小时回收连接
                echo=False,
            )

        return self._pools[pool_key]

    def close_all_pools(self):
        """关闭所有连接池"""
        self.logger.info(f"Closing {len(self._pools)} connection pools")
        for engine in self._pools.values():
            engine.dispose()
        self._pools.clear()

    def get_pool_info(self) -> Dict[str, Any]:
        """获取连接池信息"""
        return {
            "total_pools": len(self._pools),
            "pool_keys": list(self._pools.keys())
        }

    def remove_pool(self, connection_string: str, pool_size: int = 5):
        """移除指定的连接池"""
        pool_key = f"{connection_string}_{pool_size}"
        if pool_key in self._pools:
            self.logger.info(f"Removing connection pool: {pool_key}")
            self._pools[pool_key].dispose()
            del self._pools[pool_key]
