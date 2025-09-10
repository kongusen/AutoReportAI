from contextlib import contextmanager
from typing import Generator
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings, get_database_pool_config

logger = logging.getLogger(__name__)

# 获取优化的连接池配置
pool_config = get_database_pool_config()

# 创建引擎时添加调试选项
engine_kwargs = {
    "url": settings.DATABASE_URL,
    **pool_config
}

# 在开发环境启用SQL日志
if settings.ENVIRONMENT_TYPE == "local":
    engine_kwargs["echo"] = settings.DEBUG

logger.info(f"创建数据库引擎，连接池配置: pool_size={pool_config['pool_size']}, max_overflow={pool_config['max_overflow']}")
engine = create_engine(**engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI依赖注入使用的数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """上下文管理器版本的数据库会话，带重试机制"""
    import time
    from sqlalchemy import text
    from sqlalchemy.exc import DisconnectionError, TimeoutError as SQLTimeoutError
    
    db = None
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # 连接健康检查
            db.execute(text("SELECT 1"))
            
            logger.debug(f"数据库会话创建成功 (尝试 {attempt + 1}/{max_retries})")
            yield db
            break
            
        except (DisconnectionError, SQLTimeoutError) as e:
            logger.warning(f"数据库会话创建失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            
            if db:
                try:
                    db.close()
                except:
                    pass
                db = None
            
            if attempt < max_retries - 1:
                logger.info(f"等待 {retry_delay} 秒后重试创建数据库会话...")
                time.sleep(retry_delay)
                retry_delay *= 1.5
                continue
            else:
                logger.error(f"数据库会话在 {max_retries} 次尝试后仍然失败")
                raise RuntimeError("Database session failed after retries")
                
        except Exception as e:
            logger.error(f"数据库会话创建时出现意外错误: {e}")
            if db:
                try:
                    db.rollback()
                except:
                    pass
            raise
            
        finally:
            if db:
                try:
                    db.close()
                except Exception as e:
                    logger.warning(f"关闭数据库会话时出错: {e}")


def get_db_health_status():
    """获取数据库健康状态"""
    try:
        with get_db_session() as db:
            from sqlalchemy import text
            result = db.execute(text("SELECT version()"))
            version = result.scalar()
            return {
                "status": "healthy",
                "version": version,
                "pool_size": engine.pool.size(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "checked_in": engine.pool.checkedin()
            }
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e),
            "pool_size": getattr(engine.pool, 'size', lambda: 0)(),
            "checked_out": getattr(engine.pool, 'checkedout', lambda: 0)(),
            "overflow": getattr(engine.pool, 'overflow', lambda: 0)(),
            "checked_in": getattr(engine.pool, 'checkedin', lambda: 0)()
        }
