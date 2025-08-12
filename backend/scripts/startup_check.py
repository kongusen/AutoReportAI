#!/usr/bin/env python3
"""
AutoReportAI Backend 启动检查和初始化脚本
在后端启动前检查并自动修复常见的配置问题
"""
import sys
import os
import time
import subprocess
import logging
from urllib.parse import urlparse

import psycopg2
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 添加app目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StartupChecker:
    """启动检查器"""
    
    def __init__(self):
        self.db_url = str(settings.DATABASE_URL)
        self.redis_url = str(settings.REDIS_URL)
        self.max_retries = 30  # 最大重试次数
        self.retry_delay = 2   # 重试间隔（秒）

    def wait_for_service(self, service_name: str, check_func, max_retries=None):
        """等待服务可用"""
        max_retries = max_retries or self.max_retries
        
        logger.info(f"🔍 等待 {service_name} 服务...")
        
        for attempt in range(1, max_retries + 1):
            try:
                if check_func():
                    logger.info(f"✅ {service_name} 服务已就绪")
                    return True
            except Exception as e:
                logger.debug(f"  第 {attempt}/{max_retries} 次检查失败: {e}")
            
            if attempt < max_retries:
                logger.info(f"  {service_name} 未就绪，{self.retry_delay}秒后重试... ({attempt}/{max_retries})")
                time.sleep(self.retry_delay)
        
        logger.error(f"❌ {service_name} 服务在 {max_retries} 次重试后仍不可用")
        return False

    def check_database(self):
        """检查数据库连接"""
        try:
            parsed_url = urlparse(self.db_url)
            conn = psycopg2.connect(
                host=parsed_url.hostname,
                port=parsed_url.port or 5432,
                user=parsed_url.username,
                password=parsed_url.password,
                database=parsed_url.path.lstrip('/'),
                connect_timeout=5
            )
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"数据库检查失败: {e}")
            return False

    def check_redis(self):
        """检查Redis连接"""
        try:
            parsed_url = urlparse(self.redis_url)
            r = redis.Redis(
                host=parsed_url.hostname or 'localhost',
                port=parsed_url.port or 6379,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            r.ping()
            return True
        except Exception as e:
            logger.debug(f"Redis检查失败: {e}")
            return False

    def check_migrations_needed(self):
        """检查是否需要运行迁移"""
        try:
            engine = create_engine(self.db_url)
            with engine.connect() as conn:
                # 检查alembic_version表是否存在
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'alembic_version'
                    );
                """))
                
                has_alembic_table = result.scalar()
                
                if not has_alembic_table:
                    logger.info("📋 检测到新数据库，需要运行初始迁移")
                    return True
                
                # 检查是否有待应用的迁移
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                current_version = result.scalar()
                
                if not current_version:
                    logger.info("📋 数据库版本为空，需要运行迁移")
                    return True
                
                logger.info(f"📋 当前数据库版本: {current_version}")
                
                # 检查users表是否存在（基本表检查）
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    );
                """))
                
                has_users_table = result.scalar()
                if not has_users_table:
                    logger.info("📋 核心表不存在，需要运行迁移")
                    return True
                
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ 检查迁移状态时出错，将尝试运行迁移: {e}")
            return True

    def run_migrations(self):
        """运行数据库迁移"""
        logger.info("🔄 运行数据库迁移...")
        try:
            # 切换到正确的目录
            os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=120  # 2分钟超时
            )
            
            if result.returncode == 0:
                logger.info("✅ 数据库迁移完成")
                return True
            else:
                logger.error(f"❌ 数据库迁移失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ 数据库迁移超时")
            return False
        except Exception as e:
            logger.error(f"❌ 运行迁移时出错: {e}")
            return False

    def check_default_data_needed(self):
        """检查是否需要初始化默认数据"""
        try:
            engine = create_engine(self.db_url)
            with engine.connect() as conn:
                # 检查是否有管理员用户
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM users 
                        WHERE username = 'admin' AND is_superuser = true
                    );
                """))
                
                has_admin = result.scalar()
                
                if not has_admin:
                    logger.info("👤 未找到管理员用户，需要初始化默认数据")
                    return True
                
                # 检查是否有AI提供者配置
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM ai_providers 
                        WHERE provider_type = 'openai' AND is_active = true
                    );
                """))
                
                has_ai_provider = result.scalar()
                
                if not has_ai_provider:
                    logger.info("🤖 未找到AI提供者配置，需要初始化默认数据")
                    return True
                
                logger.info("✅ 默认数据已存在")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ 检查默认数据时出错，将尝试初始化: {e}")
            return True

    def initialize_default_data(self):
        """初始化默认数据"""
        logger.info("🔄 初始化默认数据...")
        try:
            result = subprocess.run(
                ["python", "scripts/init_db.py"],
                capture_output=True,
                text=True,
                timeout=60  # 1分钟超时
            )
            
            if result.returncode == 0:
                logger.info("✅ 默认数据初始化完成")
                return True
            else:
                logger.error(f"❌ 默认数据初始化失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ 默认数据初始化超时")
            return False
        except Exception as e:
            logger.error(f"❌ 初始化默认数据时出错: {e}")
            return False

    def run_full_check(self):
        """运行完整的启动检查"""
        logger.info("🚀 开始启动检查...")
        
        # 1. 等待数据库服务
        if not self.wait_for_service("数据库", self.check_database):
            logger.error("❌ 数据库服务不可用，无法启动")
            return False
        
        # 2. 等待Redis服务
        if not self.wait_for_service("Redis", self.check_redis):
            logger.error("❌ Redis服务不可用，无法启动")
            return False
        
        # 3. 检查并运行迁移
        if self.check_migrations_needed():
            if not self.run_migrations():
                logger.error("❌ 数据库迁移失败，无法启动")
                return False
        
        # 4. 检查并初始化默认数据
        if self.check_default_data_needed():
            if not self.initialize_default_data():
                logger.warning("⚠️ 默认数据初始化失败，但继续启动")
        
        logger.info("✅ 启动检查完成，系统已准备就绪")
        return True

def main():
    """主函数"""
    checker = StartupChecker()
    
    if checker.run_full_check():
        logger.info("🎉 启动检查成功完成")
        sys.exit(0)
    else:
        logger.error("💥 启动检查失败")
        sys.exit(1)

if __name__ == "__main__":
    main()