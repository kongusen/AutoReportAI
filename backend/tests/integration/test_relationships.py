#!/usr/bin/env python3
"""
测试 EnhancedDataSource 和 ETLJob 的外键关系（全新系统设计）
"""

import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.models.data_source import DataSource

# 导入所有模型，确保关系能够正确解析
from app.models.enhanced_data_source import EnhancedDataSource
from app.models.etl_job import ETLJob
from app.models.placeholder_mapping import PlaceholderMapping
from app.models.template import Template
from app.models.user import User


def test_relationships():
    """测试外键关系"""
    print("开始测试 EnhancedDataSource 和 ETLJob 的外键关系（全新系统）...")

    # 创建测试数据库连接
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 创建会话
    db = SessionLocal()

    try:
        # 创建测试数据
        print("1. 创建增强数据源...")

        # 创建增强数据源
        enhanced_source = EnhancedDataSource(
            name="test_enhanced_source",
            source_type="sql",
            connection_string="sqlite:///enhanced_test.db",
        )
        db.add(enhanced_source)
        db.commit()

        print(f"✓ 创建增强数据源: ID={enhanced_source.id}")

        # 创建 ETL Job 关联到增强数据源
        print("2. 创建 ETL Job...")
        etl_job = ETLJob(
            name="test_etl_job",
            enhanced_source_id=enhanced_source.id,
            destination_table_name="test_table",
            source_query="SELECT * FROM enhanced_test",
        )
        db.add(etl_job)
        db.commit()

        print(f"✓ 创建 ETL Job: ID={etl_job.id}")

        # 测试关系查询
        print("\n3. 测试关系查询...")

        # 查询增强数据源的所有 ETL Jobs
        enhanced_source_jobs = (
            db.query(ETLJob)
            .filter(ETLJob.enhanced_source_id == enhanced_source.id)
            .all()
        )
        print(
            f"✓ 增强数据源 {enhanced_source.id} 有 {len(enhanced_source_jobs)} 个 ETL Jobs"
        )

        # 测试反向关系
        print("\n4. 测试反向关系...")

        # 从增强数据源获取所有 ETL Jobs
        enhanced_source_with_jobs = (
            db.query(EnhancedDataSource)
            .filter(EnhancedDataSource.id == enhanced_source.id)
            .first()
        )
        print(
            f"✓ 增强数据源 {enhanced_source.id} 通过反向关系有 {len(enhanced_source_with_jobs.etl_jobs)} 个 ETL Jobs"
        )

        # 验证关系正确性
        assert len(enhanced_source_with_jobs.etl_jobs) == 1
        assert enhanced_source_with_jobs.etl_jobs[0].id == etl_job.id
        assert (
            enhanced_source_with_jobs.etl_jobs[0].enhanced_source_id
            == enhanced_source.id
        )

        print("\n✅ 所有测试通过！EnhancedDataSource 和 ETLJob 外键关系配置正确。")
        print("✅ 系统已完全迁移到增强数据源，不再使用旧的 data_source 关系。")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_relationships()
