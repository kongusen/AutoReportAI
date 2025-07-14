#!/usr/bin/env python3
"""
测试 EnhancedDataSource 和 ETLJob 的外键关系
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.enhanced_data_source import EnhancedDataSource
from app.models.etl_job import ETLJob
from app.models.data_source import DataSource
from app.core.config import settings

def test_relationships():
    """测试外键关系"""
    print("开始测试 EnhancedDataSource 和 ETLJob 的外键关系...")
    
    # 创建测试数据库连接
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 创建会话
    db = SessionLocal()
    
    try:
        # 创建测试数据
        print("1. 创建测试数据...")
        
        # 创建普通数据源
        data_source = DataSource(
            name="test_data_source",
            connection_string="sqlite:///test.db"
        )
        db.add(data_source)
        db.commit()
        
        # 创建增强数据源
        enhanced_source = EnhancedDataSource(
            name="test_enhanced_source",
            source_type="sql",
            connection_string="sqlite:///enhanced_test.db"
        )
        db.add(enhanced_source)
        db.commit()
        
        print(f"✓ 创建普通数据源: ID={data_source.id}")
        print(f"✓ 创建增强数据源: ID={enhanced_source.id}")
        
        # 创建 ETL Job 关联到普通数据源
        etl_job1 = ETLJob(
            name="test_etl_job_1",
            source_data_source_id=data_source.id,
            destination_table_name="test_table_1",
            source_query="SELECT * FROM test"
        )
        db.add(etl_job1)
        
        # 创建 ETL Job 关联到增强数据源
        etl_job2 = ETLJob(
            name="test_etl_job_2",
            enhanced_source_id=enhanced_source.id,
            destination_table_name="test_table_2",
            source_query="SELECT * FROM enhanced_test"
        )
        db.add(etl_job2)
        
        db.commit()
        
        print(f"✓ 创建 ETL Job 1 (关联普通数据源): ID={etl_job1.id}")
        print(f"✓ 创建 ETL Job 2 (关联增强数据源): ID={etl_job2.id}")
        
        # 测试关系查询
        print("\n2. 测试关系查询...")
        
        # 查询增强数据源的所有 ETL Jobs
        enhanced_source_jobs = db.query(ETLJob).filter(
            ETLJob.enhanced_source_id == enhanced_source.id
        ).all()
        print(f"✓ 增强数据源 {enhanced_source.id} 有 {len(enhanced_source_jobs)} 个 ETL Jobs")
        
        # 查询普通数据源的所有 ETL Jobs
        data_source_jobs = db.query(ETLJob).filter(
            ETLJob.source_data_source_id == data_source.id
        ).all()
        print(f"✓ 普通数据源 {data_source.id} 有 {len(data_source_jobs)} 个 ETL Jobs")
        
        # 测试反向关系
        print("\n3. 测试反向关系...")
        
        # 从增强数据源获取所有 ETL Jobs
        enhanced_source_with_jobs = db.query(EnhancedDataSource).filter(
            EnhancedDataSource.id == enhanced_source.id
        ).first()
        print(f"✓ 增强数据源 {enhanced_source.id} 通过反向关系有 {len(enhanced_source_with_jobs.etl_jobs)} 个 ETL Jobs")
        
        print("\n✅ 所有测试通过！外键关系配置正确。")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_relationships()
