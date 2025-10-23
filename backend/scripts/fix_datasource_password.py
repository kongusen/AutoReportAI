#!/usr/bin/env python3
"""
修复数据源密码问题
将加密密码更新为明文，或重新加密
"""

import sys
import os
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.security_utils import encrypt_data
from app.models.data_source import DataSource


def fix_datasource_passwords():
    """修复数据源密码"""

    # 创建数据库连接
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 获取所有数据源
        data_sources = db.query(DataSource).all()

        print(f"找到 {len(data_sources)} 个数据源")

        for ds in data_sources:
            print(f"\n数据源: {ds.name} (ID: {ds.id})")
            print(f"  类型: {ds.source_type}")

            if ds.source_type == "doris":
                current_password = ds.doris_password
                print(f"  当前密码长度: {len(current_password) if current_password else 0}")
                print(f"  密码前缀: {current_password[:10] if current_password else 'None'}...")

                # 询问用户是否要更新
                action = input(f"  选择操作:\n"
                             f"    1. 输入明文密码（不加密）\n"
                             f"    2. 输入明文密码并加密\n"
                             f"    3. 跳过\n"
                             f"  请选择 (1/2/3): ").strip()

                if action == "1":
                    new_password = input("  请输入明文密码: ").strip()
                    if new_password:
                        ds.doris_password = new_password
                        db.commit()
                        print(f"  ✅ 已更新为明文密码")

                elif action == "2":
                    new_password = input("  请输入明文密码: ").strip()
                    if new_password:
                        encrypted = encrypt_data(new_password)
                        ds.doris_password = encrypted
                        db.commit()
                        print(f"  ✅ 已加密并更新密码")
                        print(f"  加密后: {encrypted[:20]}...")

                else:
                    print("  ⏭️  跳过")

        print("\n✅ 密码修复完成")

    except Exception as e:
        print(f"❌ 错误: {e}")
        db.rollback()
    finally:
        db.close()


def test_connection():
    """测试数据源连接"""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        data_sources = db.query(DataSource).filter(
            DataSource.source_type == "doris"
        ).all()

        print("\n" + "="*50)
        print("测试数据源连接")
        print("="*50)

        for ds in data_sources:
            print(f"\n数据源: {ds.name}")
            print(f"  Host: {ds.doris_fe_hosts[0] if ds.doris_fe_hosts else 'N/A'}")
            print(f"  Port: {ds.doris_query_port}")
            print(f"  Database: {ds.doris_database}")
            print(f"  Username: {ds.doris_username}")
            print(f"  密码长度: {len(ds.doris_password) if ds.doris_password else 0}")

            # 尝试连接
            try:
                from app.services.data.connectors.doris_connector import DorisConnector
                import asyncio

                connector = DorisConnector.from_data_source(ds)

                async def test():
                    await connector.connect()
                    result = await connector.test_connection()
                    await connector.disconnect()
                    return result

                result = asyncio.run(test())

                if result.get("success"):
                    print(f"  ✅ 连接成功")
                else:
                    print(f"  ❌ 连接失败: {result.get('error')}")

            except Exception as e:
                print(f"  ❌ 连接测试失败: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="修复数据源密码问题")
    parser.add_argument("--test", action="store_true", help="测试数据源连接")
    parser.add_argument("--fix", action="store_true", help="修复数据源密码")

    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.fix:
        fix_datasource_passwords()
    else:
        print("请使用 --fix 修复密码，或 --test 测试连接")
        print("示例:")
        print("  python scripts/fix_datasource_password.py --fix")
        print("  python scripts/fix_datasource_password.py --test")
