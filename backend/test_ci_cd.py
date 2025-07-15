#!/usr/bin/env python3
"""
CI/CD 优化测试脚本
专为持续集成环境设计的快速验证测试
"""

import sys
import os
import time
import subprocess
from typing import Dict, List

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy import create_engine, inspect
from app.db.base import Base
from app.core.config import settings

class CICDTester:
    """CI/CD优化测试器"""
    
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.start_time = time.time()
        self.test_results = []
    
    def log_result(self, test_name: str, passed: bool, duration: float = None):
        """记录测试结果"""
        if duration is None:
            duration = time.time() - self.start_time
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "duration": duration
        })
        status = "✅" if passed else "❌"
        print(f"{status} {test_name} ({duration:.2f}s)")
    
    def test_database_connectivity(self) -> bool:
        """测试数据库连接"""
        try:
            conn = self.engine.connect()
            conn.close()
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    def test_migrations(self) -> bool:
        """测试数据库状态 - 验证表结构"""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            # 验证必需表存在
            required_tables = ['enhanced_data_sources', 'etl_jobs']
            for table in required_tables:
                if table not in tables:
                    print(f"Missing table: {table}")
                    return False
            
            print("✅ Database tables validation passed")
            return True
        except Exception as e:
            print(f"Database validation failed: {e}")
            return False
    
    def test_schema_consistency(self) -> bool:
        """测试Schema一致性"""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['enhanced_data_sources', 'etl_jobs']
            for table in required_tables:
                if table not in tables:
                    return False
            
            # 验证ETLJobs表结构
            etl_columns = {c['name']: c for c in inspector.get_columns('etl_jobs')}
            
            # 检查必需字段
            required_fields = ['enhanced_source_id', 'name', 'source_query', 'destination_table_name']
            for field in required_fields:
                if field not in etl_columns:
                    return False
            
            # 检查enhanced_source_id为非空
            if etl_columns['enhanced_source_id']['nullable']:
                return False
            
            return True
        except Exception as e:
            print(f"Schema consistency test failed: {e}")
            return False
    
    def test_foreign_key_integrity(self) -> bool:
        """测试外键完整性"""
        try:
            from sqlalchemy.orm import sessionmaker
            from app.models.enhanced_data_source import EnhancedDataSource
            from app.models.etl_job import ETLJob
            from app.models.data_source import DataSourceType
            
            SessionLocal = sessionmaker(bind=self.engine)
            db = SessionLocal()
            
            # 创建测试数据源
            source = EnhancedDataSource(
                name="ci_test_source",
                source_type=DataSourceType.sql,
                connection_string="postgresql://test:test@localhost/test"
            )
            db.add(source)
            db.commit()
            
            # 创建测试ETL作业
            job = ETLJob(
                name="ci_test_job",
                enhanced_source_id=source.id,
                destination_table_name="test_table",
                source_query="SELECT 1 as test"
            )
            db.add(job)
            db.commit()
            
            # 验证关系
            assert job.enhanced_source_id == source.id
            assert len(source.etl_jobs) >= 1
            
            # 清理
            db.delete(job)
            db.delete(source)
            db.commit()
            db.close()
            
            return True
        except Exception as e:
            print(f"Foreign key integrity test failed: {e}")
            return False
    
    def test_performance_baseline(self) -> bool:
        """测试性能基线"""
        try:
            from sqlalchemy.orm import sessionmaker
            from app.models.enhanced_data_source import EnhancedDataSource
            from app.models.etl_job import ETLJob
            from app.models.data_source import DataSourceType
            
            SessionLocal = sessionmaker(bind=self.engine)
            db = SessionLocal()
            
            start = time.time()
            
            # 批量创建测试数据
            sources = []
            for i in range(10):
                source = EnhancedDataSource(
                    name=f"perf_test_{i}",
                    source_type=DataSourceType.sql,
                    connection_string="postgresql://test:test@localhost/test"
                )
                sources.append(source)
            
            db.add_all(sources)
            db.commit()
            
            # 批量创建ETL作业
            jobs = []
            for source in sources:
                for j in range(3):
                    job = ETLJob(
                        name=f"perf_job_{source.id}_{j}",
                        enhanced_source_id=source.id,
                        destination_table_name=f"test_table_{j}",
                        source_query="SELECT 1"
                    )
                    jobs.append(job)
            
            db.add_all(jobs)
            db.commit()
            
            # 验证查询性能
            total_sources = db.query(EnhancedDataSource).count()
            total_jobs = db.query(ETLJob).count()
            
            duration = time.time() - start
            
            # 清理
            db.query(ETLJob).delete()
            db.query(EnhancedDataSource).delete()
            db.commit()
            db.close()
            
            # 性能要求：10个数据源+30个作业 < 5秒
            return duration < 5.0 and total_sources >= 10 and total_jobs >= 30
            
        except Exception as e:
            print(f"Performance baseline test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """测试错误处理"""
        try:
            from sqlalchemy.orm import sessionmaker
            from app.models.etl_job import ETLJob
            from sqlalchemy.exc import IntegrityError
            
            SessionLocal = sessionmaker(bind=self.engine)
            db = SessionLocal()
            
            # 测试外键约束
            try:
                invalid_job = ETLJob(
                    name="invalid_test",
                    enhanced_source_id=99999,  # 不存在的ID
                    destination_table_name="test",
                    source_query="SELECT 1"
                )
                db.add(invalid_job)
                db.commit()
                db.close()
                return False  # 应该抛出异常
            except IntegrityError:
                db.rollback()
                db.close()
                return True
            
        except Exception as e:
            print(f"Error handling test failed: {e}")
            return False
    
    def run_ci_tests(self) -> Dict:
        """运行所有CI测试"""
        print("🚀 开始CI/CD优化测试...")
        print("=" * 50)
        
        tests = [
            ("Database Connectivity", self.test_database_connectivity),
            ("Database Migrations", self.test_migrations),
            ("Schema Consistency", self.test_schema_consistency),
            ("Foreign Key Integrity", self.test_foreign_key_integrity),
            ("Performance Baseline", self.test_performance_baseline),
            ("Error Handling", self.test_error_handling),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            start = time.time()
            try:
                result = test_func()
                duration = time.time() - start
                self.log_result(test_name, result, duration)
                
                if result:
                    passed += 1
                else:
                    failed += 1
                    
            except Exception as e:
                duration = time.time() - start
                self.log_result(test_name, False, duration)
                print(f"   Error: {e}")
                failed += 1
        
        total_duration = time.time() - self.start_time
        
        print("=" * 50)
        print(f"📊 CI/CD测试结果:")
        print(f"   通过: {passed}")
        print(f"   失败: {failed}")
        print(f"   总耗时: {total_duration:.2f}s")
        
        if failed == 0:
            print("✅ 所有CI/CD测试通过！")
        else:
            print("❌ CI/CD测试失败！")
        
        return {
            "passed": passed,
            "failed": failed,
            "total_duration": total_duration,
            "tests": self.test_results
        }


def main():
    """主函数"""
    tester = CICDTester()
    result = tester.run_ci_tests()
    
    # 如果测试失败，退出码为1
    if result["failed"] > 0:
        sys.exit(1)
    
    return result


if __name__ == "__main__":
    main()
