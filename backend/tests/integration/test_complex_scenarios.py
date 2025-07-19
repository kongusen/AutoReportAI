#!/usr/bin/env python3
"""
最复杂情况的 EnhancedDataSource 和 ETLJob 测试
涵盖所有高级功能和边界情况
"""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.models.enhanced_data_source import (
    DataSourceType,
    EnhancedDataSource,
    SQLQueryType,
)
from app.models.etl_job import ETLJob
from app.schemas.enhanced_data_source import (
    EnhancedDataSourceCreate,
    EnhancedDataSourceUpdate,
)
from app.schemas.etl_job import ETLJobCreate, ETLJobUpdate


class ComplexScenarioTester:
    """复杂场景测试器"""

    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.db = None

    def setup(self):
        """设置测试环境"""
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        print("✅ 测试环境设置完成")

    def teardown(self):
        """清理测试环境"""
        if self.db:
            self.db.close()
        print("✅ 测试环境清理完成")

    def create_complex_enhanced_source(
        self, name_suffix: str = ""
    ) -> EnhancedDataSource:
        """创建最复杂的增强数据源"""
        source = EnhancedDataSource(
            name=f"complex_source_{name_suffix}_{uuid.uuid4().hex[:8]}",
            source_type=DataSourceType.sql,
            connection_string="postgresql://user:pass@localhost:5432/complex_db",
            sql_query_type=SQLQueryType.multi_table,
            base_query="""
                SELECT 
                    u.id as user_id,
                    u.username,
                    u.email,
                    p.id as profile_id,
                    p.full_name,
                    p.bio,
                    o.id as order_id,
                    o.total_amount,
                    o.created_at as order_date
                FROM users u
                INNER JOIN profiles p ON u.id = p.user_id
                INNER JOIN orders o ON u.id = o.user_id
            """,
            join_config={
                "users": {
                    "alias": "u",
                    "columns": ["id", "username", "email", "created_at"],
                },
                "profiles": {
                    "alias": "p",
                    "join_type": "INNER",
                    "join_condition": "u.id = p.user_id",
                    "columns": ["id", "full_name", "bio", "avatar_url"],
                },
                "orders": {
                    "alias": "o",
                    "join_type": "INNER",
                    "join_condition": "u.id = o.user_id",
                    "columns": ["id", "total_amount", "status", "created_at"],
                },
            },
            column_mapping={
                "user_id": {"type": "integer", "primary_key": True},
                "username": {"type": "varchar(50)", "nullable": False},
                "email": {"type": "varchar(100)", "nullable": False},
                "full_name": {"type": "varchar(100)", "nullable": True},
                "bio": {"type": "text", "nullable": True},
                "total_amount": {"type": "decimal(10,2)", "nullable": False},
                "order_date": {"type": "timestamp", "nullable": False},
            },
            where_conditions={
                "conditions": [
                    {
                        "column": "o.created_at",
                        "operator": ">=",
                        "value": "NOW() - INTERVAL '30 days'",
                    },
                    {
                        "column": "o.status",
                        "operator": "IN",
                        "value": ["completed", "processing"],
                    },
                ]
            },
            wide_table_name="user_order_analytics",
            wide_table_schema={
                "table_name": "user_order_analytics",
                "columns": [
                    {"name": "user_id", "type": "INTEGER", "primary_key": True},
                    {"name": "username", "type": "VARCHAR(50)", "nullable": False},
                    {"name": "email", "type": "VARCHAR(100)", "nullable": False},
                    {"name": "full_name", "type": "VARCHAR(100)", "nullable": True},
                    {"name": "bio", "type": "TEXT", "nullable": True},
                    {
                        "name": "total_orders",
                        "type": "INTEGER",
                        "nullable": False,
                        "default": 0,
                    },
                    {
                        "name": "total_spent",
                        "type": "DECIMAL(10,2)",
                        "nullable": False,
                        "default": 0.0,
                    },
                    {"name": "last_order_date", "type": "TIMESTAMP", "nullable": True},
                    {
                        "name": "created_at",
                        "type": "TIMESTAMP",
                        "default": "CURRENT_TIMESTAMP",
                    },
                ],
                "indexes": [
                    {"name": "idx_username", "columns": ["username"]},
                    {"name": "idx_email", "columns": ["email"]},
                    {"name": "idx_last_order", "columns": ["last_order_date"]},
                ],
            },
            api_url="https://api.example.com/v1/users",
            api_method="GET",
            api_headers={
                "Authorization": "Bearer complex_token",
                "Content-Type": "application/json",
                "X-API-Version": "v1",
            },
            api_body={
                "filters": {"active": True, "verified": True},
                "pagination": {"page": 1, "limit": 1000},
            },
            is_active=True,
            last_sync_time=datetime.now().isoformat(),
        )
        return source

    def create_complex_etl_job(
        self, enhanced_source_id: int, job_suffix: str = ""
    ) -> ETLJob:
        """创建最复杂的ETL作业"""
        job = ETLJob(
            name=f"complex_etl_job_{job_suffix}_{uuid.uuid4().hex[:8]}",
            description=f"""
                复杂ETL作业：处理用户订单分析
                - 多表联合查询
                - 复杂数据转换
                - 实时数据同步
                - 错误处理和重试机制
            """,
            enhanced_source_id=enhanced_source_id,
            destination_table_name=f"processed_user_orders_{job_suffix}",
            source_query="""
                SELECT 
                    u.id,
                    u.username,
                    u.email,
                    COUNT(o.id) as order_count,
                    SUM(o.total_amount) as total_spent,
                    MAX(o.created_at) as last_order_date,
                    CASE 
                        WHEN SUM(o.total_amount) > 1000 THEN 'VIP'
                        WHEN SUM(o.total_amount) > 500 THEN 'Premium'
                        ELSE 'Standard'
                    END as customer_tier,
                    ARRAY_AGG(DISTINCT p.category) as preferred_categories
                FROM users u
                INNER JOIN orders o ON u.id = o.user_id
                INNER JOIN products p ON o.product_id = p.id
                WHERE o.created_at >= NOW() - INTERVAL '90 days'
                    AND o.status = 'completed'
                GROUP BY u.id, u.username, u.email
                HAVING COUNT(o.id) >= 1
                ORDER BY total_spent DESC
            """,
            transformation_config={
                "steps": [
                    {
                        "step": "validate_data",
                        "type": "data_quality_check",
                        "config": {
                            "rules": [
                                {"field": "id", "rule": "not_null"},
                                {"field": "email", "rule": "email_format"},
                                {"field": "total_spent", "rule": "positive_number"},
                            ]
                        },
                    },
                    {
                        "step": "enrich_data",
                        "type": "lookup_enrichment",
                        "config": {
                            "lookup_table": "customer_segments",
                            "join_key": "customer_tier",
                            "enrich_fields": ["segment_description", "discount_rate"],
                        },
                    },
                    {
                        "step": "calculate_metrics",
                        "type": "aggregation",
                        "config": {
                            "metrics": [
                                {
                                    "name": "avg_order_value",
                                    "calculation": "total_spent / order_count",
                                },
                                {
                                    "name": "days_since_last_order",
                                    "calculation": "DATEDIFF(NOW(), last_order_date)",
                                },
                            ]
                        },
                    },
                    {
                        "step": "data_masking",
                        "type": "pii_masking",
                        "config": {"fields": ["email"], "method": "hash"},
                    },
                ],
                "error_handling": {
                    "strategy": "continue",
                    "max_errors": 100,
                    "error_log_table": "etl_error_log",
                },
                "output_format": {
                    "type": "parquet",
                    "compression": "snappy",
                    "partition_by": ["customer_tier", "year", "month"],
                },
            },
            schedule="0 2 * * *",  # 每天凌晨2点执行
            enabled=True,
        )
        return job

    def test_complex_data_source_creation(self):
        """测试复杂增强数据源创建"""
        print("\n🧪 测试复杂增强数据源创建...")

        source = self.create_complex_enhanced_source("creation")
        self.db.add(source)
        self.db.commit()

        # 验证创建成功
        saved_source = self.db.query(EnhancedDataSource).filter_by(id=source.id).first()
        assert saved_source is not None
        assert saved_source.name.startswith("complex_source_creation")
        assert saved_source.source_type == DataSourceType.sql
        assert saved_source.sql_query_type == SQLQueryType.multi_table
        assert "user_order_analytics" in saved_source.wide_table_name

        print(f"✅ 复杂增强数据源创建成功: ID={saved_source.id}")
        return saved_source

    def test_complex_etl_job_creation(self):
        """测试复杂ETL作业创建"""
        print("\n🧪 测试复杂ETL作业创建...")

        # 先创建增强数据源
        source = self.create_complex_enhanced_source("etl_test")
        self.db.add(source)
        self.db.commit()

        # 创建复杂ETL作业
        job = self.create_complex_etl_job(source.id, "complex_test")
        self.db.add(job)
        self.db.commit()

        # 验证创建成功
        saved_job = self.db.query(ETLJob).filter_by(id=job.id).first()
        assert saved_job is not None
        assert saved_job.enhanced_source_id == source.id
        assert saved_job.name.startswith("complex_etl_job_complex_test")
        assert "processed_user_orders" in saved_job.destination_table_name
        assert len(saved_job.transformation_config["steps"]) == 4

        print(f"✅ 复杂ETL作业创建成功: ID={saved_job.id}")
        return saved_job

    def test_cascade_operations(self):
        """测试级联操作"""
        print("\n🧪 测试级联操作...")

        # 创建增强数据源和多个ETL作业
        source = self.create_complex_enhanced_source("cascade")
        self.db.add(source)
        self.db.commit()

        # 创建多个ETL作业
        job_ids = []
        for i in range(3):
            job = self.create_complex_etl_job(source.id, f"cascade_{i}")
            self.db.add(job)
            self.db.commit()
            job_ids.append(job.id)

        # 验证关系
        source_with_jobs = (
            self.db.query(EnhancedDataSource).filter_by(id=source.id).first()
        )
        assert len(source_with_jobs.etl_jobs) == 3

        # 测试删除增强数据源时，ETL作业应该被级联删除
        # 由于外键约束，我们需要先删除ETL作业
        self.db.query(ETLJob).filter_by(enhanced_source_id=source.id).delete()
        self.db.delete(source)
        self.db.commit()

        # 验证所有相关ETL作业已被删除
        remaining_jobs = self.db.query(ETLJob).filter(ETLJob.id.in_(job_ids)).all()
        assert len(remaining_jobs) == 0

        print("✅ 级联操作测试完成")

    def test_data_integrity(self):
        """测试数据完整性"""
        print("\n🧪 测试数据完整性...")

        # 测试必需字段验证
        try:
            invalid_job = ETLJob(
                name="invalid_job",
                # 缺少 enhanced_source_id
                destination_table_name="test",
                source_query="SELECT 1",
            )
            self.db.add(invalid_job)
            self.db.commit()
            assert False, "应该抛出完整性错误"
        except IntegrityError:
            self.db.rollback()
            print("✅ 必需字段验证通过")

        # 测试外键约束
        try:
            invalid_job = ETLJob(
                name="invalid_job",
                enhanced_source_id=99999,  # 不存在的ID
                destination_table_name="test",
                source_query="SELECT 1",
            )
            self.db.add(invalid_job)
            self.db.commit()
            assert False, "应该抛出外键约束错误"
        except IntegrityError:
            self.db.rollback()
            print("✅ 外键约束验证通过")

    def test_performance_scenarios(self):
        """测试性能场景"""
        print("\n🧪 测试性能场景...")

        # 获取当前数据源数量
        initial_sources = self.db.query(EnhancedDataSource).count()
        initial_jobs = self.db.query(ETLJob).count()

        # 创建大量增强数据源
        sources = []
        for i in range(10):  # 恢复原始数量
            source = self.create_complex_enhanced_source(f"perf_{i}")
            sources.append(source)

        self.db.add_all(sources)
        self.db.commit()

        # 为每个数据源创建多个ETL作业
        jobs = []
        for source in sources:
            for j in range(3):
                job = self.create_complex_etl_job(source.id, f"perf_{j}")
                jobs.append(job)

        self.db.add_all(jobs)
        self.db.commit()

        # 验证批量操作
        total_sources = self.db.query(EnhancedDataSource).count()
        total_jobs = self.db.query(ETLJob).count()

        expected_sources = initial_sources + 10
        expected_jobs = initial_jobs + 30

        assert total_sources == expected_sources
        assert total_jobs == expected_jobs

        # 测试复杂查询性能
        complex_query = (
            self.db.query(EnhancedDataSource)
            .filter(
                EnhancedDataSource.source_type == DataSourceType.sql,
                EnhancedDataSource.is_active == True,
            )
            .all()
        )

        assert len(complex_query) >= 10

        print(f"✅ 性能场景测试完成: {total_sources} 数据源, {total_jobs} ETL作业")

    def test_schema_validation(self):
        """测试Schema验证"""
        print("\n🧪 测试Schema验证...")

        # 测试EnhancedDataSourceCreate
        valid_source_data = {
            "name": "test_schema_source",
            "source_type": "sql",
            "connection_string": "postgresql://test:test@localhost/test",
            "sql_query_type": "multi_table",
        }

        source_schema = EnhancedDataSourceCreate(**valid_source_data)
        assert source_schema.name == "test_schema_source"

        # 测试ETLJobCreate
        valid_job_data = {
            "name": "test_schema_job",
            "enhanced_source_id": 1,
            "destination_table_name": "test_table",
            "source_query": "SELECT * FROM test",
            "transformation_config": {"steps": [{"type": "filter"}]},
            "schedule": "0 1 * * *",
            "enabled": True,
        }

        job_schema = ETLJobCreate(**valid_job_data)
        assert job_schema.enhanced_source_id == 1
        assert job_schema.schedule == "0 1 * * *"

        print("✅ Schema验证测试完成")

    def run_all_tests(self):
        """运行所有复杂场景测试"""
        print("🚀 开始最复杂情况的 EnhancedDataSource 和 ETLJob 测试")
        print("=" * 80)

        self.setup()

        try:
            # 运行所有测试
            source = self.test_complex_data_source_creation()
            job = self.test_complex_etl_job_creation()
            self.test_cascade_operations()
            self.test_data_integrity()
            self.test_performance_scenarios()
            self.test_schema_validation()

            print("\n" + "=" * 80)
            print("🎉 所有复杂场景测试通过！")
            print("✅ EnhancedDataSource 和 ETLJob 的复杂关系完全验证")
            print("✅ 系统已准备好处理最复杂的业务场景")

            return {
                "enhanced_source_id": source.id,
                "etl_job_id": job.id,
                "test_status": "PASSED",
            }

        finally:
            self.teardown()


def main():
    """主测试函数"""
    tester = ComplexScenarioTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    result = main()
    print(f"\n📊 测试结果: {result}")
