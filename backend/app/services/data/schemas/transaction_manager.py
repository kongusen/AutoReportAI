"""
数据库事务管理器
提供高级事务管理功能，包括保存点、隔离级别管理和自动重试
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, AsyncGenerator
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import asyncio


class IsolationLevel(Enum):
    """事务隔离级别"""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


class TransactionManager:
    """事务管理器"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self._savepoints = []  # 保存点栈
        self._transaction_start_time = None
        
    @asynccontextmanager
    async def transaction(
        self, 
        isolation_level: Optional[IsolationLevel] = None,
        readonly: bool = False,
        timeout: int = 300  # 5分钟超时
    ) -> AsyncGenerator[Session, None]:
        """
        高级事务上下文管理器
        
        Args:
            isolation_level: 事务隔离级别
            readonly: 是否为只读事务
            timeout: 事务超时时间(秒)
        """
        self._transaction_start_time = datetime.utcnow()
        original_isolation = None
        
        try:
            # 设置事务隔离级别
            if isolation_level:
                # 获取当前隔离级别
                result = self.db_session.execute(text("SHOW transaction_isolation"))
                original_isolation = result.scalar()
                
                # 设置新隔离级别
                self.db_session.execute(
                    text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level.value}")
                )
                self.logger.debug(f"设置事务隔离级别: {isolation_level.value}")
            
            # 设置只读事务
            if readonly:
                self.db_session.execute(text("SET TRANSACTION READ ONLY"))
                self.logger.debug("设置为只读事务")
            
            # 开始事务
            self.db_session.begin()
            self.logger.debug("事务开始")
            
            # 设置超时监控
            timeout_task = None
            if timeout > 0:
                timeout_task = asyncio.create_task(self._monitor_timeout(timeout))
            
            try:
                yield self.db_session
                
                # 检查事务是否超时
                if timeout_task and not timeout_task.done():
                    timeout_task.cancel()
                
                # 提交事务
                self.db_session.commit()
                self.logger.debug("事务提交成功")
                
            except Exception as e:
                # 回滚事务
                try:
                    self.db_session.rollback()
                    self.logger.warning(f"事务回滚: {e}")
                except Exception as rollback_error:
                    self.logger.error(f"事务回滚失败: {rollback_error}")
                raise
            finally:
                # 清理超时任务
                if timeout_task and not timeout_task.done():
                    timeout_task.cancel()
                
        except Exception as e:
            self.logger.error(f"事务管理失败: {e}")
            raise
        finally:
            # 恢复原始隔离级别
            if original_isolation and isolation_level:
                try:
                    self.db_session.execute(
                        text(f"SET SESSION TRANSACTION ISOLATION LEVEL {original_isolation}")
                    )
                except Exception as e:
                    self.logger.warning(f"恢复隔离级别失败: {e}")
            
            # 清理保存点栈
            self._savepoints.clear()
            self._transaction_start_time = None
    
    async def _monitor_timeout(self, timeout: int):
        """监控事务超时"""
        await asyncio.sleep(timeout)
        self.logger.error(f"事务超时 ({timeout}秒)，强制回滚")
        try:
            self.db_session.rollback()
        except Exception as e:
            self.logger.error(f"超时回滚失败: {e}")
    
    def create_savepoint(self, name: Optional[str] = None) -> str:
        """
        创建保存点
        
        Args:
            name: 保存点名称，如果不提供则自动生成
            
        Returns:
            保存点名称
        """
        if not name:
            name = f"sp_{len(self._savepoints) + 1}_{int(datetime.utcnow().timestamp())}"
        
        try:
            self.db_session.execute(text(f"SAVEPOINT {name}"))
            self._savepoints.append(name)
            self.logger.debug(f"创建保存点: {name}")
            return name
        except Exception as e:
            self.logger.error(f"创建保存点失败: {e}")
            raise
    
    def rollback_to_savepoint(self, name: str):
        """
        回滚到指定保存点
        
        Args:
            name: 保存点名称
        """
        try:
            if name not in self._savepoints:
                raise ValueError(f"保存点 {name} 不存在")
            
            self.db_session.execute(text(f"ROLLBACK TO SAVEPOINT {name}"))
            
            # 移除该保存点之后的所有保存点
            try:
                index = self._savepoints.index(name)
                self._savepoints = self._savepoints[:index + 1]
            except ValueError:
                pass
            
            self.logger.debug(f"回滚到保存点: {name}")
            
        except Exception as e:
            self.logger.error(f"回滚到保存点失败: {e}")
            raise
    
    def release_savepoint(self, name: str):
        """
        释放保存点
        
        Args:
            name: 保存点名称
        """
        try:
            if name not in self._savepoints:
                raise ValueError(f"保存点 {name} 不存在")
            
            self.db_session.execute(text(f"RELEASE SAVEPOINT {name}"))
            self._savepoints.remove(name)
            self.logger.debug(f"释放保存点: {name}")
            
        except Exception as e:
            self.logger.error(f"释放保存点失败: {e}")
            raise
    
    def get_transaction_status(self) -> Dict[str, Any]:
        """获取事务状态"""
        try:
            # 获取事务状态
            result = self.db_session.execute(text("SELECT txid_current_if_assigned()"))
            transaction_id = result.scalar()
            
            duration = None
            if self._transaction_start_time:
                duration = (datetime.utcnow() - self._transaction_start_time).total_seconds()
            
            return {
                "transaction_id": transaction_id,
                "in_transaction": transaction_id is not None,
                "savepoints_count": len(self._savepoints),
                "active_savepoints": self._savepoints.copy(),
                "duration_seconds": duration,
                "start_time": self._transaction_start_time.isoformat() if self._transaction_start_time else None
            }
            
        except Exception as e:
            self.logger.error(f"获取事务状态失败: {e}")
            return {"error": str(e)}
    
    @asynccontextmanager
    async def batch_operation(
        self, 
        batch_size: int = 100,
        isolation_level: Optional[IsolationLevel] = None
    ) -> AsyncGenerator['BatchProcessor', None]:
        """
        批量操作上下文管理器
        
        Args:
            batch_size: 批量大小
            isolation_level: 事务隔离级别
        """
        async with self.transaction(isolation_level=isolation_level) as session:
            processor = BatchProcessor(session, batch_size, self.logger)
            yield processor
            
            # 处理剩余的批次
            await processor.flush()


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, session: Session, batch_size: int, logger: logging.Logger):
        self.session = session
        self.batch_size = batch_size
        self.logger = logger
        self._current_batch = []
        self._processed_count = 0
    
    async def add(self, operation_func, *args, **kwargs):
        """
        添加操作到批次
        
        Args:
            operation_func: 操作函数
            *args, **kwargs: 函数参数
        """
        self._current_batch.append((operation_func, args, kwargs))
        
        if len(self._current_batch) >= self.batch_size:
            await self._process_batch()
    
    async def _process_batch(self):
        """处理当前批次"""
        if not self._current_batch:
            return
        
        batch_start_time = datetime.utcnow()
        success_count = 0
        failed_operations = []
        
        for operation_func, args, kwargs in self._current_batch:
            try:
                await operation_func(*args, **kwargs)
                success_count += 1
            except Exception as e:
                failed_operations.append({
                    "function": operation_func.__name__,
                    "args": args,
                    "kwargs": kwargs,
                    "error": str(e)
                })
                self.logger.warning(f"批量操作失败: {operation_func.__name__}, 错误: {e}")
        
        # 统计信息
        duration = (datetime.utcnow() - batch_start_time).total_seconds()
        self._processed_count += len(self._current_batch)
        
        self.logger.info(f"批量处理完成: 成功 {success_count}, 失败 {len(failed_operations)}, 耗时 {duration:.2f}s")
        
        # 清空当前批次
        self._current_batch = []
        
        if failed_operations:
            self.logger.warning(f"批量处理中有 {len(failed_operations)} 个操作失败")
    
    async def flush(self):
        """处理剩余的批次"""
        if self._current_batch:
            await self._process_batch()
        
        self.logger.info(f"批量处理总计: {self._processed_count} 个操作")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计"""
        return {
            "processed_count": self._processed_count,
            "pending_count": len(self._current_batch),
            "batch_size": self.batch_size
        }