"""
数据库会话管理器
提供智能的数据库会话管理和依赖注入功能
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any
from threading import local
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal, get_db_session
from app.core.config import settings

logger = logging.getLogger(__name__)

# 线程本地存储，用于管理每个线程的数据库会话
_thread_local = local()


class DatabaseSessionManager:
    """数据库会话管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._active_sessions: Dict[str, Session] = {}
    
    @contextmanager
    def get_session(self, session_id: Optional[str] = None) -> Generator[Session, None, None]:
        """
        获取数据库会话的上下文管理器
        
        Args:
            session_id: 会话标识符，用于会话复用
            
        Yields:
            数据库会话实例
        """
        session = None
        session_created = False
        
        try:
            # 尝试复用现有会话
            if session_id and session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                self.logger.debug(f"Reusing existing session: {session_id}")
            else:
                # 创建新会话
                session = SessionLocal()
                session_created = True
                
                if session_id:
                    self._active_sessions[session_id] = session
                    self.logger.debug(f"Created new session: {session_id}")
            
            # 测试连接健康状态
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            
            yield session
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database session error: {e}")
            if session:
                session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Unexpected session error: {e}")
            if session:
                session.rollback()
            raise
        finally:
            # 清理会话
            if session_created and session:
                try:
                    session.close()
                    if session_id and session_id in self._active_sessions:
                        del self._active_sessions[session_id]
                except Exception as e:
                    self.logger.error(f"Error closing session: {e}")
    
    def get_or_create_session(self, existing_session: Optional[Session] = None) -> Session:
        """
        获取或创建数据库会话
        
        Args:
            existing_session: 现有的数据库会话
            
        Returns:
            数据库会话实例
        """
        if existing_session is not None:
            return existing_session
        
        # 检查线程本地存储中是否有会话
        if hasattr(_thread_local, 'db_session') and _thread_local.db_session:
            return _thread_local.db_session
        
        # 创建新会话
        session = SessionLocal()
        _thread_local.db_session = session
        return session
    
    def set_thread_session(self, session: Session):
        """设置线程本地数据库会话"""
        _thread_local.db_session = session
    
    def clear_thread_session(self):
        """清除线程本地数据库会话"""
        if hasattr(_thread_local, 'db_session'):
            if _thread_local.db_session:
                try:
                    _thread_local.db_session.close()
                except Exception as e:
                    self.logger.error(f"Error closing thread session: {e}")
            _thread_local.db_session = None
    
    def health_check(self) -> Dict[str, Any]:
        """数据库会话管理器健康检查"""
        try:
            with self.get_session() as session:
                from sqlalchemy import text
                result = session.execute(text("SELECT 1")).scalar()
                
                return {
                    "status": "healthy",
                    "active_sessions": len(self._active_sessions),
                    "database_responsive": result == 1,
                    "connection_pool_size": session.bind.pool.size(),
                    "checked_out_connections": session.bind.pool.checkedout()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "active_sessions": len(self._active_sessions)
            }


# 全局会话管理器实例
session_manager = DatabaseSessionManager()


def get_session_manager() -> DatabaseSessionManager:
    """获取数据库会话管理器"""
    return session_manager


@contextmanager
def managed_session(session_id: Optional[str] = None) -> Generator[Session, None, None]:
    """便捷的数据库会话上下文管理器"""
    with session_manager.get_session(session_id) as session:
        yield session


def ensure_session(session: Optional[Session] = None) -> Session:
    """确保获得有效的数据库会话"""
    return session_manager.get_or_create_session(session)


class SessionContextManager:
    """会话上下文管理器，用于长期会话管理"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session: Optional[Session] = None
    
    def __enter__(self) -> Session:
        self.session = SessionLocal()
        session_manager._active_sessions[self.session_id] = self.session
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            try:
                if exc_type:
                    self.session.rollback()
                else:
                    self.session.commit()
            except Exception as e:
                logger.error(f"Error in session context exit: {e}")
                self.session.rollback()
            finally:
                self.session.close()
                if self.session_id in session_manager._active_sessions:
                    del session_manager._active_sessions[self.session_id]