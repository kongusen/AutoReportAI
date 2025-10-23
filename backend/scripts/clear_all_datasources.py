#!/usr/bin/env python3
"""
清空所有数据源

使用场景：
- 重置数据源配置
- 更换 ENCRYPTION_KEY 后清理旧数据
- 开发测试环境重置

使用方法:
    python scripts/clear_all_datasources.py --confirm    # 确认后清空
    python scripts/clear_all_datasources.py --dry-run    # 仅查看，不删除
"""

import sys
import os
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.data_source import DataSource
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def show_datasources():
    """显示所有数据源"""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        data_sources = db.query(DataSource).all()

        print("\n" + "=" * 60)
        print(f"当前数据源总数: {len(data_sources)}")
        print("=" * 60 + "\n")

        if not data_sources:
            print("没有找到任何数据源")
            return []

        for i, ds in enumerate(data_sources, 1):
            print(f"{i}. {ds.name}")
            print(f"   ID: {ds.id}")
            print(f"   类型: {ds.source_type}")
            print(f"   创建时间: {ds.created_at}")

            if ds.source_type == "doris":
                print(f"   连接: {ds.doris_username}@{ds.doris_fe_hosts[0] if ds.doris_fe_hosts else 'N/A'}:{ds.doris_query_port}")
                print(f"   数据库: {ds.doris_database}")

            print()

        return data_sources

    finally:
        db.close()


def clear_datasources(dry_run=False):
    """清空所有数据源"""

    if dry_run:
        print("\n" + "=" * 60)
        print("【预览模式】以下数据源将被删除:")
        print("=" * 60)
        show_datasources()
        print("\n提示: 使用 --confirm 参数执行实际删除")
        return

    print("\n" + "=" * 60)
    print("⚠️  警告：即将删除所有数据源")
    print("=" * 60)

    data_sources = show_datasources()

    if not data_sources:
        print("\n没有需要删除的数据源")
        return

    print(f"\n共 {len(data_sources)} 个数据源将被永久删除")
    print("此操作不可恢复！")

    confirmation = input("\n请输入 'DELETE ALL' 确认删除: ").strip()

    if confirmation != "DELETE ALL":
        print("\n❌ 操作已取消")
        return

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 删除所有数据源
        deleted_count = db.query(DataSource).delete()
        db.commit()

        print(f"\n✅ 成功删除 {deleted_count} 个数据源")
        print("\n提示:")
        print("1. 确保 ENCRYPTION_KEY 环境变量已正确设置")
        print("2. 重启应用以加载新的配置")
        print("3. 重新创建数据源")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 删除失败: {e}")
        raise
    finally:
        db.close()


def verify_encryption_key():
    """验证当前的 ENCRYPTION_KEY 配置"""
    print("\n" + "=" * 60)
    print("ENCRYPTION_KEY 配置验证")
    print("=" * 60)

    from cryptography.fernet import Fernet

    # 显示当前密钥
    current_key = settings.ENCRYPTION_KEY
    print(f"\n当前 ENCRYPTION_KEY:")
    print(f"  完整值: {current_key}")
    print(f"  前缀:   {current_key[:20]}...")
    print(f"  后缀:   ...{current_key[-10:]}")
    print(f"  长度:   {len(current_key)} 字符")

    # 检查来源
    env_key = os.getenv("ENCRYPTION_KEY")
    if env_key:
        print(f"\n✅ 来源: 环境变量")
        if env_key == current_key:
            print(f"   环境变量值与当前值一致")
        else:
            print(f"   ⚠️  警告: 环境变量值与当前值不一致!")
    else:
        print(f"\n⚠️  来源: 默认值 (config.py)")
        print(f"   建议: 在 .env 文件中设置 ENCRYPTION_KEY")

    # 检查环境类型
    print(f"\n环境类型: {settings.ENVIRONMENT_TYPE}")

    # 验证密钥格式
    try:
        cipher = Fernet(current_key.encode())
        print(f"\n✅ ENCRYPTION_KEY 格式正确")

        # 测试加密/解密
        test_data = "test_password_123"
        encrypted = cipher.encrypt(test_data.encode())
        decrypted = cipher.decrypt(encrypted).decode()

        if decrypted == test_data:
            print(f"✅ 加密/解密功能正常")
        else:
            print(f"❌ 加密/解密测试失败")

    except Exception as e:
        print(f"\n❌ ENCRYPTION_KEY 格式错误: {e}")
        print(f"   请使用以下命令生成新密钥:")
        print(f"   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")


def check_env_file():
    """检查 .env 文件中的 ENCRYPTION_KEY"""
    print("\n" + "=" * 60)
    print(".env 文件检查")
    print("=" * 60)

    env_files = [
        "autorport-dev/.env",
        ".env",
        "backend/.env"
    ]

    for env_file in env_files:
        env_path = Path(backend_path).parent / env_file

        if env_path.exists():
            print(f"\n文件: {env_file}")
            print(f"  路径: {env_path}")

            try:
                with open(env_path, 'r') as f:
                    content = f.read()

                if "ENCRYPTION_KEY" in content:
                    # 提取 ENCRYPTION_KEY 行
                    for line in content.split('\n'):
                        if line.strip().startswith('ENCRYPTION_KEY'):
                            print(f"  配置: {line.strip()}")
                            break
                else:
                    print(f"  ⚠️  未设置 ENCRYPTION_KEY")

            except Exception as e:
                print(f"  ❌ 读取失败: {e}")
        else:
            print(f"\n文件: {env_file}")
            print(f"  ❌ 不存在")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清空所有数据源")
    parser.add_argument("--confirm", action="store_true", help="确认执行删除操作")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不执行实际删除")
    parser.add_argument("--list", action="store_true", help="仅列出所有数据源")
    parser.add_argument("--verify-key", action="store_true", help="验证 ENCRYPTION_KEY 配置")
    parser.add_argument("--check-env", action="store_true", help="检查 .env 文件配置")

    args = parser.parse_args()

    if args.list:
        show_datasources()

    elif args.verify_key:
        verify_encryption_key()

    elif args.check_env:
        check_env_file()

    elif args.dry_run:
        clear_datasources(dry_run=True)

    elif args.confirm:
        print("\n⚠️  准备清空所有数据源...")
        clear_datasources(dry_run=False)

    else:
        print("清空数据源脚本")
        print("\n使用方法:")
        print("  --list       : 列出所有数据源")
        print("  --verify-key : 验证 ENCRYPTION_KEY 配置")
        print("  --check-env  : 检查 .env 文件")
        print("  --dry-run    : 预览将要删除的数据源")
        print("  --confirm    : 确认执行删除操作")
        print("\n推荐流程:")
        print("  1. python scripts/clear_all_datasources.py --verify-key")
        print("  2. python scripts/clear_all_datasources.py --check-env")
        print("  3. python scripts/clear_all_datasources.py --list")
        print("  4. python scripts/clear_all_datasources.py --dry-run")
        print("  5. python scripts/clear_all_datasources.py --confirm")
        print("\n⚠️  警告: 删除操作不可恢复，请谨慎使用!")
