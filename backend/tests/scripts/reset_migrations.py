#!/usr/bin/env python3
"""
重置数据库迁移状态的脚本
"""
import os
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def reset_migrations():
    """重置迁移状态"""
    try:
        # 创建数据库连接
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            # 删除alembic_version表
            conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
            
            # 重新创建alembic_version表，使用更长的版本字段
            conn.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(255) NOT NULL,
                    PRIMARY KEY (version_num)
                )
            """))
            
            # 提交事务
            conn.commit()
            
        print("✅ 迁移状态已重置")
        
    except Exception as e:
        print(f"❌ 重置失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_migrations() 